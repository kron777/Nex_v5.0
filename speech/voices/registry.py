"""Voice registry — introspects Kokoro install for available voices."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

DEFAULT_VOICE = "af_bella"

_ACCENT_MAP = {
    "a": "American",
    "b": "British",
}

_GENDER_MAP = {
    "f": "female",
    "m": "male",
}


@dataclass
class Voice:
    id: str            # e.g., "af_sarah"
    display_name: str  # e.g., "Sarah"
    accent: str        # e.g., "American"
    gender: str        # e.g., "female"


def _parse_voice_id(voice_id: str) -> Optional[Voice]:
    """Parse a Kokoro voice ID like 'af_sarah' into a Voice dataclass."""
    try:
        prefix, name = voice_id.split("_", 1)
        if len(prefix) != 2:
            return None
        accent = _ACCENT_MAP.get(prefix[0].lower())
        gender = _GENDER_MAP.get(prefix[1].lower())
        if accent is None or gender is None:
            return None  # non-English voice (ef_, jf_, zf_, etc.)
        return Voice(
            id=voice_id,
            display_name=name.capitalize(),
            accent=accent,
            gender=gender,
        )
    except Exception:
        return None


def _find_voice_dir() -> Optional[Path]:
    """Locate the Kokoro voice directory on this system."""
    # HuggingFace hub cache (most common install)
    hf_hub = Path.home() / ".cache" / "huggingface" / "hub"
    if hf_hub.is_dir():
        # models--hexgrad--Kokoro-82M/snapshots/<hash>/voices
        for model_dir in hf_hub.glob("models--hexgrad--Kokoro-*"):
            snapshots = model_dir / "snapshots"
            if snapshots.is_dir():
                for snap in sorted(snapshots.iterdir()):
                    voices_dir = snap / "voices"
                    if voices_dir.is_dir():
                        return voices_dir

    # Direct installs
    for candidate in [
        Path.home() / ".cache" / "kokoro" / "voices",
        Path.home() / ".local" / "share" / "kokoro" / "voices",
        Path("/opt/kokoro/voices"),
    ]:
        if candidate.is_dir():
            return candidate

    return None


def enumerate_voices() -> list[Voice]:
    """Return all available English voices, or a safe fallback list."""
    voice_dir = _find_voice_dir()
    voices: list[Voice] = []

    if voice_dir:
        for path in voice_dir.glob("*.pt"):
            parsed = _parse_voice_id(path.stem)
            if parsed:
                voices.append(parsed)

    # Dedup by id
    seen: set[str] = set()
    unique: list[Voice] = []
    for v in voices:
        if v.id not in seen:
            seen.add(v.id)
            unique.append(v)

    # Fallback to known-good list if enumeration found nothing
    if not unique:
        for kid in [
            "af_sarah", "af_nicole", "af_sky",
            "am_adam", "am_michael",
            "bf_emma", "bf_isabella",
            "bm_george", "bm_lewis",
        ]:
            v = _parse_voice_id(kid)
            if v:
                unique.append(v)

    def _sort_key(v: Voice) -> tuple:
        accent_rank = {"American": 0, "British": 1}.get(v.accent, 99)
        gender_rank = {"female": 0, "male": 1}.get(v.gender, 99)
        return (accent_rank, gender_rank, v.display_name)

    unique.sort(key=_sort_key)
    return unique


def get_voice(voice_id: str) -> Voice:
    """Look up a voice by ID, falling back to default."""
    for v in enumerate_voices():
        if v.id == voice_id:
            return v
    return _parse_voice_id(DEFAULT_VOICE) or Voice(
        id=DEFAULT_VOICE, display_name="Sarah", accent="American", gender="female"
    )
