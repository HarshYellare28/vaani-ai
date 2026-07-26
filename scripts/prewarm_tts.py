"""Pre-generate every TTS clip a language needs, so the drill never waits.

Each Bulbul call is a 2-3s round trip that lands *after* ASR, squarely inside
the patient's wait for feedback. The corpus is finite and the feedback lines
are templates, so the whole set can be synthesized ahead of time into the
content-addressed cache that SarvamTTS reads from.

Per word that's: the prompt audio, plus the spoken "incorrect" and "no speech"
lines (both embed the word). The "correct" line is invariant, so it's one clip
per language.

Safe to re-run: cached clips are skipped, so a partial run just resumes.

Usage:
    python scripts/prewarm_tts.py hi-IN --limit 30  # one group's worth (recommended before a demo)
    python scripts/prewarm_tts.py kn-IN              # one language (12 words)
    python scripts/prewarm_tts.py                    # everything in the corpus (slow — 900+ words for Hindi)
"""

from __future__ import annotations

import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vaani.config import Config          # noqa: E402
from vaani.db import Database            # noqa: E402
from vaani.i18n import feedback_templates, speaker_for  # noqa: E402
from vaani.tts import SarvamTTS          # noqa: E402


def utterances_for(db: Database, language: str, limit: int | None = None) -> list[str]:
    """Every distinct string the drill can speak in this language.

    Three clips per word plus one invariant "correct" line, so Hindi's 900-word
    corpus is ~2,700 calls — use `limit` to warm only the words a session will
    actually reach (a drill group is 30).
    """
    fb = feedback_templates(language)
    out = [fb["correct"]]
    words = db.list_words(language=language)
    if limit is not None:
        words = words[:limit]
    for w in words:
        out.append(w["text"])
        out.append(fb["incorrect"].format(word=w["text"]))
        out.append(fb["no_speech"].format(word=w["text"]))
    # dict.fromkeys preserves order while dropping duplicates
    return list(dict.fromkeys(out))


def synth_with_retry(tts: SarvamTTS, text: str, lang: str, speaker: str | None,
                     tries: int = 3) -> str:
    """Synthesize, retrying on the throttling Sarvam applies to bursts.

    Sustained parallel requests make it stall until the client timeout rather
    than returning 429, and the same text succeeds seconds later. Retrying with
    backoff turns those into hits instead of gaps in the cache.
    """
    for attempt in range(1, tries + 1):
        try:
            return tts.synthesize(text, language_code=lang, speaker=speaker)
        except Exception:
            if attempt == tries:
                raise
            time.sleep(2 ** attempt)
    raise AssertionError("unreachable")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("languages", nargs="*", help="e.g. hi-IN (default: all)")
    # 6+ concurrent requests started timing out against Sarvam mid-run; 3 is
    # steady. Re-running is cheap either way — cached clips are skipped.
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--limit", type=int, default=None,
                    help="cap words per language (a drill group is 30)")
    args = ap.parse_args()

    config = Config.from_env()
    db = Database(config.db_path)
    tts = SarvamTTS(config, cache_dir="audio_out/tts")

    langs = args.languages or [r["language"] for r in db.languages()]
    total_new = total_cached = 0

    for lang in langs:
        texts = utterances_for(db, lang, args.limit)
        speaker = speaker_for(lang)
        todo = [t for t in texts
                if not Path(tts.cache_path(t, lang, speaker=speaker)).exists()]
        cached = len(texts) - len(todo)
        total_cached += cached
        print(f"{lang}: {len(texts)} utterances, {cached} already cached, "
              f"{len(todo)} to synthesize")

        if not todo:
            continue
        started = time.time()
        done = failed = 0
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futures = {
                ex.submit(synth_with_retry, tts, t, lang, speaker): t
                for t in todo
            }
            for f in as_completed(futures):
                try:
                    f.result()
                    done += 1
                except Exception as e:            # keep going; report at the end
                    failed += 1
                    print(f"  FAILED {futures[f]!r}: {e}")
                print(f"\r  {done + failed}/{len(todo)}", end="", flush=True)
        total_new += done
        print(f"\r  {done} synthesized, {failed} failed "
              f"in {time.time() - started:.0f}s")

    print(f"\ncache: {total_new} new, {total_cached} already present "
          f"-> audio_out/tts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
