"""Plays numpy audio arrays through system speakers via sounddevice."""
from __future__ import annotations

import logging

import numpy as np

log = logging.getLogger("nex5.speech.player")


class Player:
    def play(self, audio: np.ndarray, sample_rate: int) -> None:
        try:
            import sounddevice as sd
            sd.play(audio, sample_rate, blocking=True)
            sd.wait()
        except Exception as e:
            log.error("Playback failed: %s", e)
            raise

    def stop(self) -> None:
        """Stop any active sounddevice playback stream."""
        try:
            import sounddevice as sd
            sd.stop()
        except Exception as e:
            # No active stream (or no audio device) is not a shutdown failure.
            log.debug("Playback stop requested: %s", e)
