"""Speech configuration."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class SpeechConfig:
    enabled: bool = True
    voice: str = "af_sarah"
    quiet_start_hour: int = 23
    quiet_end_hour: int = 7
    quiet_hours_enabled: bool = True
    speed: float = 1.0
    min_chars: int = 10
    max_chars: int = 500
    poll_interval_sec: float = 1.0
    cache_dir: str = os.path.expanduser("~/.cache/nex5/speech")

    @classmethod
    def from_env(cls) -> "SpeechConfig":
        c = cls()
        c.enabled = os.getenv("NEX5_SPEECH_ENABLED", "true").lower() == "true"
        c.voice = os.getenv("NEX5_SPEECH_VOICE", c.voice)
        c.quiet_hours_enabled = (
            os.getenv("NEX5_QUIET_HOURS", "true").lower() == "true"
        )
        return c

    def in_quiet_hours(self, hour: int) -> bool:
        if not self.quiet_hours_enabled:
            return False
        if self.quiet_start_hour <= self.quiet_end_hour:
            return self.quiet_start_hour <= hour < self.quiet_end_hour
        return hour >= self.quiet_start_hour or hour < self.quiet_end_hour
