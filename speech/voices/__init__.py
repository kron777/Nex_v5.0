"""Voice registry and state for NEX speech output."""
from speech.voices.registry import Voice, enumerate_voices, get_voice, DEFAULT_VOICE
from speech.voices.state import VoiceState, build_voice_state

__all__ = [
    "Voice", "enumerate_voices", "get_voice", "DEFAULT_VOICE",
    "VoiceState", "build_voice_state",
]
