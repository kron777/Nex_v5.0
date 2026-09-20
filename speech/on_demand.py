"""On-demand speech — say ONE line now, through the same Kokoro backend and
Player the queue consumer already uses.

Nothing here re-implements TTS: it calls consumer.backend.synth() and
consumer.player.play(), exactly as SpeechQueueConsumer._speak_one does. The only
differences are that it is triggered by a request instead of the queue, it runs
on its own daemon thread so the HTTP call returns immediately, and it PREEMPTS
whatever is currently playing (sounddevice has one output stream, so starting a
new play stops the old one) — an asked-for line should not wait behind her
unprompted queue.

Stopping: the consumer's flush() only marks PENDING queue rows 'skipped'; it
cannot stop audio already in the speakers. sounddevice.stop() can, so that is
what stop() calls — it cuts whatever is playing, hers or ours.

Her queue is untouched: nothing here reads or writes speech_queue.
FAIL-SAFE: the worker catches everything, so a synth/playback failure can never
take down the consumer daemon or the request thread.
"""
from __future__ import annotations

import logging
import threading
import time

log = logging.getLogger("nex5.speech.on_demand")

MAX_CHARS = 2000        # a chat reply, not a document

_lock = threading.Lock()
_state = {"speaking": False, "started_at": None, "chars": 0, "error": None}


def is_speaking() -> bool:
    with _lock:
        return bool(_state["speaking"])


def snapshot() -> dict:
    with _lock:
        return dict(_state)


def validate(text) -> tuple[bool, str]:
    """(ok, error). Empty/non-string/oversized text is rejected -> HTTP 400."""
    if not isinstance(text, str) or not text.strip():
        return False, "empty text"
    if len(text) > MAX_CHARS:
        return False, f"text too long ({len(text)} > {MAX_CHARS} chars)"
    return True, ""


def resolve_voice(consumer) -> str:
    """The same voice the consumer would use: live VoiceState if set, else the
    configured voice (af_sarah). Fail-safe: the configured voice."""
    try:
        vs = getattr(consumer, "_voice_state", None)
        if vs is not None:
            name = vs.current_name()
            if name:
                return name
    except Exception:
        pass
    try:
        return consumer.config.voice
    except Exception:
        return "af_sarah"


def stop() -> bool:
    """Cut playback now. True if sounddevice accepted the stop."""
    ok = False
    try:
        import sounddevice as sd
        sd.stop()
        ok = True
    except Exception as e:
        log.error("stop failed: %s", e)
    with _lock:
        _state["speaking"] = False
    return ok


def _worker(consumer, text: str, voice: str) -> None:
    try:
        # Synthesize FIRST, then preempt: don't cut her off to sit in silence
        # while Kokoro works.
        audio, sr = consumer.backend.synth(text, voice=voice)
        try:
            import sounddevice as sd
            sd.stop()
        except Exception:
            pass
        consumer.player.play(audio, sr)      # blocking, on this thread
        with _lock:
            _state["error"] = None
    except Exception as e:                   # never propagate: daemon-safe
        log.error("on-demand synth/play failed: %s", e)
        with _lock:
            _state["error"] = str(e)
    finally:
        with _lock:
            _state["speaking"] = False


def speak_async(consumer, text: str, voice: str = None) -> tuple[bool, str]:
    """Start speaking `text` now on a daemon thread. (ok, error)."""
    ok, err = validate(text)
    if not ok:
        return False, err
    if consumer is None:
        return False, "speech consumer not running"
    v = voice or resolve_voice(consumer)
    with _lock:
        _state.update(speaking=True, started_at=time.time(),
                      chars=len(text), error=None)
    t = threading.Thread(target=_worker, args=(consumer, text, v),
                         name="nex5.speech.on_demand", daemon=True)
    t.start()
    return True, ""
