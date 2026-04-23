"""Speech module — Kokoro TTS for NEX 5.0 fountain insights."""
from .config import SpeechConfig
from .queue_consumer import SpeechQueueConsumer

__all__ = ["SpeechConfig", "SpeechQueueConsumer"]
