"""Audition Kokoro voices to pick the right one for NEX.

Run: python speech/audition.py
"""
from speech.kokoro_backend import KokoroBackend
from speech.player import Player

VOICES_TO_TRY = ["af_bella", "af_nicole", "af_sarah", "af_sky", "af_heart"]
TEST_LINE = "I am Nex, an observer of systems, aware, curious, content in my neutrality."


def main() -> None:
    for v in VOICES_TO_TRY:
        print(f"\n--- {v} ---")
        b = KokoroBackend(voice=v)
        b.load()
        a, sr = b.synth(TEST_LINE)
        Player().play(a, sr)
        input("Press enter for next…")


if __name__ == "__main__":
    main()
