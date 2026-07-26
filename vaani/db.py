"""SQLite persistence — sessions and per-attempt SLP data records.

Single-user-per-install for now, but the schema is built for the SLP/clinic
roadmap: every attempt is a structured data point (transcript, result, similarity,
duration, language confidence) that an analytics layer can aggregate over time.

Migrations are additive (ALTER TABLE ADD COLUMN) so an existing vaani.db upgrades
in place without losing history.
"""

from __future__ import annotations

import json
import random
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
    user_id    INTEGER REFERENCES users(id),
    mode       TEXT    NOT NULL DEFAULT 'static'    -- 'static' | 'dynamic' (LLM judge)
);

CREATE TABLE IF NOT EXISTS attempts (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id           INTEGER NOT NULL REFERENCES sessions(id),
    word_id              INTEGER REFERENCES words(id),
    target_word          TEXT    NOT NULL,
    target_language      TEXT    NOT NULL,
    transcript           TEXT,                 -- mode=transcribe (normalised; scores in static mode)
    transcript_verbatim  TEXT,                 -- mode=verbatim (disfluencies kept; scores in dynamic mode)
    result_label         TEXT,                 -- correct|incorrect|no_speech
    similarity           REAL,                 -- 0.0–1.0 transcript↔target
    audio_duration_sec   REAL,                 -- attempt length (fluency proxy)
    language_detected    TEXT,
    language_probability REAL,
    attempt_no           INTEGER NOT NULL DEFAULT 1,  -- retries on this word
    action               TEXT,                 -- decision action
    judge_error_type     TEXT,                 -- dynamic mode only: clinical error taxonomy
    judge_next_word_id   INTEGER REFERENCES words(id),  -- dynamic mode only
    judge_note           TEXT,                 -- dynamic mode only: clinical reasoning, SLP-facing
    created_at           TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS assignments (
    user_id     INTEGER PRIMARY KEY REFERENCES users(id),  -- one active assignment per patient
    language    TEXT    NOT NULL,
    level       INTEGER NOT NULL,
    group_num   INTEGER NOT NULL,
    mode        TEXT    NOT NULL DEFAULT 'static',  -- 'static' | 'dynamic'
    assigned_at TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_attempts_session ON attempts(session_id);
CREATE INDEX IF NOT EXISTS idx_words_lang_level ON words(language, level);
"""

# Columns added after the original schema — applied to existing DBs by _migrate.
_ATTEMPT_COLS = {
    "transcript_verbatim": "transcript_verbatim TEXT",
    "result_label": "result_label TEXT",
    "similarity": "similarity REAL",
    "audio_duration_sec": "audio_duration_sec REAL",
    "language_detected": "language_detected TEXT",
    "language_probability": "language_probability REAL",
    "attempt_no": "attempt_no INTEGER NOT NULL DEFAULT 1",
    "judge_error_type": "judge_error_type TEXT",
    "judge_next_word_id": "judge_next_word_id INTEGER",
    "judge_note": "judge_note TEXT",
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
    "mode": "mode TEXT NOT NULL DEFAULT 'static'",
}

_ASSIGNMENT_COLS = {
    "mode": "mode TEXT NOT NULL DEFAULT 'static'",
}

_GROUP_SIZE = 30

# Demo roster — no self-signup; the SLP is assumed to have already enrolled
# these patients. Picked from a dropdown, not typed, so the demo never depends
# on someone typing a name correctly on stage.
_SEED_PATIENTS = ["Asha Rao", "Vikram Nair", "Lakshmi Iyer"]


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

            for col, ddl in _ASSIGNMENT_COLS.items():
                if col not in cols("assignments"):
                    conn.execute(f"ALTER TABLE assignments ADD COLUMN {ddl}")

            # Attribute pre-migration sessions to the first user (if any)
            conn.execute(
                "UPDATE sessions SET user_id = (SELECT MIN(id) FROM users) "
                "WHERE user_id IS NULL AND (SELECT COUNT(*) FROM users) > 0"
            )

            # Top up the demo roster on an existing DB (e.g. one seeded before
            # _SEED_PATIENTS existed, with just the old placeholder "Patient").
            # By name, not count, so it's a no-op once everyone's present.
            present_names = {r[0] for r in conn.execute("SELECT name FROM users")}
            missing = [n for n in _SEED_PATIENTS if n not in present_names]
            if missing:
                conn.executemany(
                    "INSERT INTO users (name, created_at) VALUES (?, ?)",
                    [(name, _now()) for name in missing],
                )

    # ── users ─────────────────────────────────────────────────────────
    def seed_users(self) -> None:
        """Idempotent: seeds the demo patient roster if the users table is empty."""
        with self._conn() as conn:
            if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]:
                return
            conn.executemany(
                "INSERT INTO users (name, created_at) VALUES (?, ?)",
                [(name, _now()) for name in _SEED_PATIENTS],
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

    # ── assignments ──────────────────────────────────────────────────
    # One row per patient — "what they're practicing today". The SLP sets it;
    # the patient app has no picker, it just plays back whatever's here.
    # mode='static': fixed language+level+group, scored on the transcribe
    # transcript (repeat-practice, high-volume). mode='dynamic': language +
    # a starting level only — the LLM judge scores on the verbatim transcript
    # and picks each next word (focused, adaptive).
    def set_assignment(
        self, user_id: int, language: str, level: int, group_num: int, mode: str = "static",
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO assignments (user_id, language, level, group_num, mode, assigned_at)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(user_id) DO UPDATE SET
                       language = excluded.language, level = excluded.level,
                       group_num = excluded.group_num, mode = excluded.mode,
                       assigned_at = excluded.assigned_at""",
                (user_id, language, level, group_num, mode, _now()),
            )

    def get_assignment(self, user_id: int) -> Optional[dict]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT user_id, language, level, group_num, mode, assigned_at "
                "FROM assignments WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        return dict(row) if row else None

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
        mode: str = "static",
    ) -> int:
        self.end_stale_sessions()  # single active session at a time
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO sessions (started_at, status, language, level, group_num, user_id, mode) "
                "VALUES (?, 'active', ?, ?, ?, ?, ?)",
                (_now(), language, level, group_num, user_id, mode),
            )
            return cur.lastrowid

    def get_session(self, session_id: int) -> Optional[dict]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT id, language, level, group_num, user_id, mode "
                "FROM sessions WHERE id = ?",
                (session_id,),
            ).fetchone()
        return dict(row) if row else None

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
                    transcript, transcript_verbatim, result_label, similarity,
                    audio_duration_sec, language_detected, language_probability,
                    attempt_no, action, judge_error_type, judge_next_word_id,
                    judge_note, created_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    session_id, word_id, assessment.target_word, assessment.language,
                    assessment.transcript, assessment.transcript_verbatim,
                    assessment.result_label, assessment.similarity,
                    assessment.audio_duration_sec,
                    assessment.language_detected, assessment.language_probability,
                    attempt_no, decision.action.value,
                    assessment.judge_error_type, assessment.judge_next_word_id,
                    assessment.judge_note,
                    _now(),
                ),
            )
            return cur.lastrowid

    def times_correct(self, user_id: int, word_id: int) -> int:
        with self._conn() as conn:
            return conn.execute(
                """SELECT COUNT(*) FROM attempts a JOIN sessions s ON a.session_id = s.id
                   WHERE s.user_id = ? AND a.word_id = ? AND a.result_label = 'correct'""",
                (user_id, word_id),
            ).fetchone()[0]

    def candidate_words(
        self, language: str, user_id: int, exclude_word_id: Optional[int] = None, limit: int = 10,
    ) -> list[dict]:
        """Words in `language` this patient hasn't already nailed twice —
        round-robined across categories so the dynamic judge has real
        cross-category options (the "switch category on repeated errors"
        policy is meaningless without them)."""
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT w.id, w.text, w.language, w.romanization, w.meaning,
                       w.word_type, w.category, w.level,
                       COALESCE(SUM(CASE WHEN a.result_label = 'correct' THEN 1 ELSE 0 END), 0)
                           AS times_correct
                FROM words w
                LEFT JOIN attempts a
                    ON a.word_id = w.id
                    AND a.session_id IN (SELECT id FROM sessions WHERE user_id = ?)
                WHERE w.language = ?
                GROUP BY w.id
                HAVING times_correct < 2
                ORDER BY w.category, w.level
                """,
                (user_id, language),
            ).fetchall()
        pool = [dict(r) for r in rows if r["id"] != exclude_word_id]

        # Round-robin across categories so a short candidate list still spans
        # the corpus, instead of exhausting one category first.
        by_category: dict[str, list[dict]] = {}
        for w in pool:
            by_category.setdefault(w["category"] or "", []).append(w)
        for words in by_category.values():
            random.shuffle(words)

        candidates: list[dict] = []
        cats = list(by_category.keys())
        random.shuffle(cats)
        i = 0
        while len(candidates) < limit and any(by_category.values()):
            cat = cats[i % len(cats)]
            if by_category[cat]:
                candidates.append(by_category[cat].pop())
            i += 1
        for w in candidates:
            w["display"] = _display(w)
        return candidates

    def patient_recent_attempts(self, user_id: int, limit: int = 5) -> list[dict]:
        """Last few attempts across ALL of this patient's sessions, with word
        metadata — lets the dynamic judge see a trend (repeated word_type/
        category misses, lengthening durations) rather than judging each
        attempt in isolation. Spans sessions on purpose, not just the one in
        progress: persisted in sqlite, so a trend from yesterday still
        informs today's first word, surviving an app restart same as
        everything else here."""
        with self._conn() as conn:
            rows = conn.execute(
                """SELECT a.target_word, a.result_label, a.audio_duration_sec,
                          w.word_type, w.category, w.level
                   FROM attempts a
                   JOIN sessions s ON a.session_id = s.id
                   LEFT JOIN words w ON a.word_id = w.id
                   WHERE s.user_id = ?
                   ORDER BY a.created_at DESC
                   LIMIT ?""",
                (user_id, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    def list_attempts(self, user_id: int, limit: int = 100) -> list[dict]:
        """A patient's attempts newest-first, across all sessions — the SLP's
        record. Both transcripts included: `transcript` (normalised, scores in
        static mode) and `transcript_verbatim` (scores in dynamic mode). Judge
        fields are null for static-mode attempts."""
        with self._conn() as conn:
            rows = conn.execute(
                """SELECT a.id, a.target_word, a.target_language, a.transcript,
                          a.transcript_verbatim, a.result_label, a.similarity,
                          a.audio_duration_sec, a.attempt_no, a.created_at,
                          s.mode, a.judge_error_type, a.judge_note
                   FROM attempts a
                   JOIN sessions s ON a.session_id = s.id
                   WHERE s.user_id = ?
                   ORDER BY a.created_at DESC
                   LIMIT ?""",
                (user_id, limit),
            ).fetchall()
        return [dict(r) for r in rows]

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
