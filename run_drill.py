"""CLI runner — exercise the full static-drill pipeline on a WAV file.

Usage:
    # 1. Generate the prompt audio for a target word (play it to the patient):
    python run_drill.py prompt "water" --lang en-US

    # 2. After recording the patient's attempt to a WAV, score it:
    python run_drill.py score "water" path/to/attempt.wav --lang en-US

This lets you test end-to-end with real audio before the Flutter client
exists. Fill in .env first (copy from .env.example).
"""

from __future__ import annotations

import argparse

from vaani import StaticDrill, setup_logging


def main() -> None:
    setup_logging()
    parser = argparse.ArgumentParser(description="Vaani static drill runner")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_prompt = sub.add_parser("prompt", help="synthesize the target word")
    p_prompt.add_argument("word")
    p_prompt.add_argument("--lang", default="hi-IN", help="TTS language code")

    p_score = sub.add_parser("score", help="score a recorded attempt")
    p_score.add_argument("word")
    p_score.add_argument("attempt_wav")
    p_score.add_argument(
        "--lang", default="hi-IN",
        help="session language (hi-IN / en-US)",
    )

    args = parser.parse_args()
    drill = StaticDrill()

    if args.cmd == "prompt":
        path = drill.prompt_word(args.word, language_code=args.lang)
        print(f"Prompt audio written to: {path}")
        return

    # score
    result = drill.evaluate_attempt(args.word, args.attempt_wav, language=args.lang)
    a, d = result.assessment, result.decision
    print(f"\nTarget word:   {a.target_word}  ({a.language})")
    print(f"Sarvam heard:  {a.transcript!r}")
    print(f"\n— Assessment —")
    print(f"  Result:       {a.result_label}")
    print(f"  Similarity:   {a.similarity:.2f}")
    print(f"  Duration:     {a.audio_duration_sec:.1f}s")
    print(f"  Detected lang:{a.language_detected}  (p={a.language_probability})")
    print(f"\n— Decision —")
    print(f"  Action:   {d.action.value}")
    print(f"  Feedback: {d.feedback_text}")
    print(f"  Audio:    {result.feedback_audio_path}")


if __name__ == "__main__":
    main()
