"""python -m speech test [TEXT]  — synthesize and play a sample."""
import sys


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0] != "test":
        print("Usage: python -m speech test [text]")
        sys.exit(1)

    text = " ".join(args[1:]) if len(args) > 1 else (
        "I am Nex, an observer of systems, aware, curious, content in my neutrality."
    )

    from speech.config import SpeechConfig
    from speech.kokoro_backend import KokoroBackend
    from speech.player import Player

    cfg = SpeechConfig.from_env()
    backend = KokoroBackend(voice=cfg.voice, speed=cfg.speed)
    print(f"Loading Kokoro (voice={cfg.voice})…")
    backend.load()
    print(f"Synthesizing: {text!r}")
    audio, sr = backend.synth(text)
    print(f"Playing {len(audio)/sr:.1f}s of audio at {sr}Hz…")
    Player().play(audio, sr)
    print("Done.")


if __name__ == "__main__":
    main()
