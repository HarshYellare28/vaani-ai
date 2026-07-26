"""SQLite persistence — sessions and per-attempt SLP data records.

Single-user-per-install for now, but the schema is built for the SLP/clinic
roadmap: every attempt is a structured data point (transcript, result, similarity,
duration, language confidence) that an analytics layer can aggregate over time.

Migrations are additive (ALTER TABLE ADD COLUMN) so an existing vaani.db upgrades
in place without losing history.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from itertools import groupby
from pathlib import Path
from typing import Iterable, Optional

from .decision import Decision
from .models import Assessment

# Drill corpus, generated from the SLP placards spreadsheet by
# scripts/import_placards.py (900 Hindi + 100 English, with level + category).
_WORDS_JSON = Path(__file__).resolve().parent / "data" / "words.json"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL,
    created_at TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS words (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    text         TEXT    NOT NULL,
    language     TEXT    NOT NULL,            -- 'en-US' | 'hi-IN'
    romanization TEXT,                        -- e.g. 'maa' (Hindi)
    meaning      TEXT,                        -- English gloss (Hindi)
    word_type    TEXT,                        -- 'noun' | 'verb' | ...
    category     TEXT,                        -- semantic group (bilingual label)
    level        INTEGER NOT NULL DEFAULT 1,  -- difficulty tier (1 easy → 3 hard)
    group_num    INTEGER NOT NULL DEFAULT 1,  -- 30-word batch within the level
    order_idx    INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS sessions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT    NOT NULL,
    ended_at   TEXT,
    status     TEXT    NOT NULL DEFAULT 'active',  -- 'active' | 'ended'
    language   TEXT,                               -- session language
    level      INTEGER,                            -- difficulty level practiced
    group_num  INTEGER,                            -- word group practiced
    user_id    INTEGER REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS attempts (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id           INTEGER NOT NULL REFERENCES sessions(id),
    word_id              INTEGER REFERENCES words(id),
    target_word          TEXT    NOT NULL,
    target_language      TEXT    NOT NULL,
    transcript           TEXT,                 -- what Sarvam heard
    result_label         TEXT,                 -- correct|incorrect|no_speech
    similarity           REAL,                 -- 0.0–1.0 transcript↔target
    audio_duration_sec   REAL,                 -- attempt length (fluency proxy)
    language_detected    TEXT,
    language_probability REAL,
    attempt_no           INTEGER NOT NULL DEFAULT 1,  -- retries on this word
    action               TEXT,                 -- decision action
    created_at           TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_attempts_session ON attempts(session_id);
CREATE INDEX IF NOT EXISTS idx_words_lang_level ON words(language, level);
"""

# Columns added after the original schema — applied to existing DBs by _migrate.
_ATTEMPT_COLS = {
    "result_label": "result_label TEXT",
    "similarity": "similarity REAL",
    "audio_duration_sec": "audio_duration_sec REAL",
    "language_detected": "language_detected TEXT",
    "language_probability": "language_probability REAL",
    "attempt_no": "attempt_no INTEGER NOT NULL DEFAULT 1",
}

_WORD_COLS = {
    "romanization": "romanization TEXT",
    "meaning": "meaning TEXT",
    "word_type": "word_type TEXT",
    "category": "category TEXT",
    "group_num": "group_num INTEGER NOT NULL DEFAULT 1",
}

_SESSION_COLS = {
    "language": "language TEXT",
    "level": "level INTEGER",
    "group_num": "group_num INTEGER",
    "user_id": "user_id INTEGER",
}

_GROUP_SIZE = 30


def _load_seed_words() -> list[dict]:
    """The full drill corpus from data/words.json (see scripts/import_placards.py)."""
    if _WORDS_JSON.exists():
        return json.loads(_WORDS_JSON.read_text("utf-8"))
    return []


def _assign_group_nums(words: list[dict]) -> list[int]:
    """Return a group_num for each word, computed by bucketing 30 per (language, level)."""
    indexed = list(enumerate(words))
    indexed.sort(key=lambda x: (
        x[1].get("language", ""),
        x[1].get("level", 1),
        x[1].get("order_idx", x[0]),
    ))
    group_num_map: dict[int, int] = {}
    for _, bucket in groupby(indexed, key=lambda x: (x[1].get("language", ""), x[1].get("level", 1))):
        for rank, (orig_idx, _) in enumerate(bucket):
            group_num_map[orig_idx] = (rank // _GROUP_SIZE) + 1
    return [group_num_map.get(i, 1) for i in range(len(words))]


def _display(row: dict) -> str:
    """UI gloss line under the word: 'maa · mother' (Hindi) or '' (English)."""
    rom, mean = row.get("romanization"), row.get("meaning")
    if rom and mean:
        return f"{rom} · {mean}"
    return rom or mean or ""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Database:
    def __init__(self, path: str = "vaani.db"):
        self._path = path
        self.init_schema()
        self.seed_users()  # must exist before _migrate attributes old sessions to user 1
        self._migrate()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self._path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")   # concurrent reads during writes
        conn.execute("PRAGMA busy_timeout=5000")  # wait up to 5s instead of erroring
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    # ── schema / migration / seed ────────────────────────────────────
    def init_schema(self) -> None:
        with self._conn() as conn:
            conn.executescript(_SCHEMA)

    def _migrate(self) -> None:
        """Additively bring an older vaani.db up to the current schema."""
        with self._conn() as conn:
            def cols(table: str) -> set[str]:
                return {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}

            for col, ddl in _ATTEMPT_COLS.items():
                if col not in cols("attempts"):
                    conn.execute(f"ALTER TABLE attempts ADD COLUMN {ddl}")

            for col, ddl in _WORD_COLS.items():
                if col not in cols("words"):
                    conn.execute(f"ALTER TABLE words ADD COLUMN {ddl}")
                    if col == "group_num":
                        # Recompute group_num for all existing words
                        rows = conn.execute(
                            "SELECT id, language, level, order_idx FROM words "
                            "ORDER BY language, level, order_idx, id"
                        ).fetchall()
                        updates = []
                        for _, bucket in groupby(rows, key=lambda r: (r[1], r[2])):
                            for rank, row in enumerate(bucket):
                                updates.append(((rank // _GROUP_SIZE) + 1, row[0]))
                        if updates:
                            conn.executemany(
                                "UPDATE words SET group_num = ? WHERE id = ?", updates
                            )
                        conn.execute(
                            "CREATE INDEX IF NOT EXISTS idx_words_lang_level_group "
                            "ON words(language, level, group_num)"
                        )

            for col, ddl in _SESSION_COLS.items():
                if col not in cols("sessions"):
                    conn.execute(f"ALTER TABLE sessions ADD COLUMN {ddl}")

            # Attribute pre-migration sessions to the first user (if any)
            conn.execute(
                "UPDATE sessions SET user_id = (SELECT MIN(id) FROM users) "
                "WHERE user_id IS NULL AND (SELECT COUNT(*) FROM users) > 0"
            )

    # ── users ─────────────────────────────────────────────────────────
    def seed_users(self) -> None:
        """Idempotent: seeds one default patient if the users table is empty."""
        with self._conn() as conn:
            if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]:
                return
            conn.execute(
                "INSERT INTO users (name, created_at) VALUES (?, ?)", ("Patient", _now())
            )

    def list_users(self) -> list[dict]:
        with self._conn() as conn:
            return [dict(r) for r in conn.execute(
                "SELECT id, name, created_at FROM users ORDER BY id"
            )]

    def create_user(self, name: str) -> int:
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO users (name, created_at) VALUES (?, ?)", (name, _now())
            )
            return cur.lastrowid

    # ── words ─────────────────────────────────────────────────────────
    def seed_words(self, words: Optional[Iterable[dict]] = None) -> None:
        """Seed the corpus, and re-seed when the corpus gains a new language.

        Seeding used to be skipped whenever the table was non-empty, so adding
        a language to words.json never reached an existing install — it just
        never appeared in the picker. Keying on the language set instead means
        a new language lands on upgrade, while ordinary word edits stay a
        no-op. reset_words detaches attempts rather than deleting them, so
        practice history survives either way.
        """
        corpus = list(words) if words is not None else _load_seed_words()
        with self._conn() as conn:
            present = {
                r[0] for r in conn.execute("SELECT DISTINCT language FROM words")
            }
        if present and not {w["language"] for w in corpus} - present:
            return
        self.reset_words(corpus)

    def reset_words(self, words: Optional[Iterable[dict]] = None) -> int:
        """Replace the entire drill corpus from dicts (defaults to words.json).
        Existing attempts are detached from old words (word_id → NULL) so
        practice history survives. Returns the number of words seeded.
        """
        words = list(words) if words is not None else _load_seed_words()
        group_nums = _assign_group_nums(words)
        with self._conn() as conn:
            conn.execute("UPDATE attempts SET word_id = NULL")
            conn.execute("DELETE FROM words")
            conn.execute("DELETE FROM sqlite_sequence WHERE name = 'words'")
            conn.executemany(
                """INSERT INTO words
                   (text, language, romanization, meaning, word_type,
                    category, level, group_num, order_idx)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    (w["text"], w["language"], w.get("romanization"),
                     w.get("meaning"), w.get("word_type"), w.get("category"),
                     int(w.get("level", 1)), group_nums[i], int(w.get("order_idx", i)))
                    for i, w in enumerate(words)
                ],
            )
        return len(words)

    def list_words(
        self,
        language: Optional[str] = None,
        level: Optional[int] = None,
        group_num: Optional[int] = None,
    ) -> list[dict]:
        sql = ("SELECT id, text, language, romanization, meaning, word_type, "
               "category, level, group_num, order_idx FROM words")
        conds, params = [], []
        if language:
            conds.append("language = ?")
            params.append(language)
        if level is not None:
            conds.append("level = ?")
            params.append(level)
        if group_num is not None:
            conds.append("group_num = ?")
            params.append(group_num)
        if conds:
            sql += " WHERE " + " AND ".join(conds)
        sql += " ORDER BY level, group_num, order_idx, id"
        with self._conn() as conn:
            rows = [dict(r) for r in conn.execute(sql, params)]
        for r in rows:
            r["display"] = _display(r)
        return rows

    def languages(self) -> list[dict]:
        """Distinct languages with word counts — drives the language picker."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT language, COUNT(*) AS word_count FROM words "
                "GROUP BY language ORDER BY language"
            ).fetchall()
        return [dict(r) for r in rows]

    def levels(self, language: str) -> list[dict]:
        """Levels available for a language, with word counts — drives the
        level picker. Ordered easy → hard."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT level, COUNT(*) AS word_count FROM words "
                "WHERE language = ? GROUP BY level ORDER BY level",
                (language,),
            ).fetchall()
        return [dict(r) for r in rows]

    def groups(self, language: str, level: int, user_id: int) -> list[dict]:
        """Groups for a language+level with per-user score data.

        Returns each group's word_count plus (for the given user):
          attempts, correct, words_correct (unique words answered correctly ≥ once).
        """
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT
                    w.group_num,
                    COUNT(DISTINCT w.id)                                        AS word_count,
                    COUNT(ua.id)                                                AS attempts,
                    COALESCE(SUM(CASE WHEN ua.result_label = 'correct' THEN 1 ELSE 0 END), 0)
                                                                                AS correct,
                    COUNT(DISTINCT CASE WHEN ua.result_label = 'correct' THEN ua.word_id END)
                                                                                AS words_correct
                FROM words w
                LEFT JOIN (
                    SELECT a.id, a.word_id, a.result_label
                    FROM attempts a
                    JOIN sessions s ON a.session_id = s.id
                    WHERE s.user_id = ?
                ) ua ON ua.word_id = w.id
                WHERE w.language = ? AND w.level = ?
                GROUP BY w.group_num
                ORDER BY w.group_num
                """,
                (user_id, language, level),
            ).fetchall()
        return [dict(r) for r in rows]

    # ── sessions ─────────────────────────────────────────────────────
    def end_stale_sessions(self) -> int:
        """Close any sessions left 'active' (abandoned by a refresh)."""
        with self._conn() as conn:
            cur = conn.execute(
                """UPDATE sessions
                       SET status = 'ended',
                           ended_at = COALESCE(
                               (SELECT MAX(created_at) FROM attempts
                                 WHERE attempts.session_id = sessions.id),
                               started_at)
                     WHERE status = 'active'"""
            )
            return cur.rowcount

    def create_session(
        self,
        language: Optional[str] = None,
        level: Optional[int] = None,
        user_id: Optional[int] = None,
        group_num: Optional[int] = None,
    ) -> int:
        self.end_stale_sessions()  # single active session at a time
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO sessions (started_at, status, language, level, group_num, user_id) "
                "VALUES (?, 'active', ?, ?, ?, ?)",
                (_now(), language, level, group_num, user_id),
            )
            return cur.lastrowid

    def end_session(self, session_id: int) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE sessions SET ended_at = ?, status = 'ended' "
                "WHERE id = ? AND status = 'active'",
                (_now(), session_id),
            )

    # ── attempts ─────────────────────────────────────────────────────
    def attempt_count(self, session_id: int, target_word: str) -> int:
        with self._conn() as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM attempts WHERE session_id = ? AND target_word = ?",
                (session_id, target_word),
            ).fetchone()[0]

    def record_attempt(
        self,
        session_id: int,
        assessment: Assessment,
        decision: Decision,
        word_id: Optional[int] = None,
    ) -> int:
        attempt_no = self.attempt_count(session_id, assessment.target_word) + 1
        with self._conn() as conn:
            cur = conn.execute(
                """INSERT INTO attempts (
                    session_id, word_id, target_word, target_language,
                    transcript, result_label, similarity, audio_duration_sec,
                    language_detected, language_probability, attempt_no,
                    action, created_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    session_id, word_id, assessment.target_word, assessment.language,
                    assessment.transcript, assessment.result_label,
                    assessment.similarity, assessment.audio_duration_sec,
                    assessment.language_detected, assessment.language_probability,
                    attempt_no, decision.action.value,
                    _now(),
                ),
            )
            return cur.lastrowid

    # ── reporting ────────────────────────────────────────────────────
    def session_summary(self, session_id: int) -> dict:
        with self._conn() as conn:
            row = conn.execute(
                """SELECT
                       COUNT(*)                              AS attempts,
                       COUNT(DISTINCT target_word)           AS words_seen,
                       SUM(result_label = 'correct')         AS correct,
                       AVG(similarity)                       AS avg_similarity,
                       AVG(audio_duration_sec)               AS avg_duration
                   FROM attempts WHERE session_id = ?""",
                (session_id,),
            ).fetchone()
        return {k: row[k] for k in row.keys()}
