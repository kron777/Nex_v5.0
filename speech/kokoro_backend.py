"""Kokoro TTS wrapper. Loads model once, synthesizes on demand."""
from __future__ import annotations

import logging
import os
from typing import Optional

import numpy as np

log = logging.getLogger("nex5.speech.kokoro")


class KokoroBackend:
    def __init__(self, voice: str = "af_bella", speed: float = 1.0) -> None:
        self.voice = voice
        self.speed = speed
        self._pipeline: Optional[object] = None

    def load(self) -> None:
        if self._pipeline is not None:
            return
        try:
            from kokoro import KPipeline
            # Pass repo_id explicitly so Kokoro uses the local HF cache
            # even when TRANSFORMERS_OFFLINE=1 / HF_HUB_OFFLINE=1 is set.
            # Run speech/download_model.py once to pre-populate the cache.
            self._pipeline = KPipeline(lang_code="a",
                                       repo_id="hexgrad/Kokoro-82M")
            log.info("Kokoro loaded with voice=%s", self.voice)
        except Exception as e:
            log.error(
                "Kokoro load failed: %s\n"
                "If this is a first-time load, run:\n"
                "  .venv/bin/python speech/download_model.py\n"
                "to pre-download model weights.",
                e,
            )
            raise

    def synth(self, text: str) -> tuple[np.ndarray, int]:
        """Returns (audio_float32_mono, sample_rate=24000)."""
        if self._pipeline is None:
            self.load()
        generator = self._pipeline(text, voice=self.voice, speed=self.speed)
        chunks = []
        for _, _, audio in generator:
            chunks.append(audio)
        if not chunks:
            raise RuntimeError("Kokoro produced no audio")
        audio = np.concatenate(chunks)
        return audio.astype(np.float32), 24000
