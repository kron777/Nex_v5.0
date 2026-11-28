"""Shutdown regressions for long-running predictor loops."""
import threading
from unittest.mock import patch

from theory_x.stage_world import prediction_generator as pg
from theory_x.stage_world import self_prediction as sp
from theory_x.stage_world import world_loop


def test_world_prediction_does_not_start_voice_work_after_stop_during_resolve():
    stop = threading.Event()
    loop = world_loop.WorldPredictionLoop(conversations_writer=object())

    def resolve_then_stop(**_kwargs):
        stop.set()
        return {}

    with patch.object(world_loop.wp, "resolve_due", side_effect=resolve_then_stop), patch.object(
        pg, "make_voice_prediction"
    ) as make_voice:
        loop.tick(stop_event=stop)

    make_voice.assert_not_called()


def test_world_prediction_does_not_write_after_stop_during_voice_call():
    started = threading.Event()
    release = threading.Event()
    stop = threading.Event()
    result = {}

    def blocked_voice(*_args, **_kwargs):
        started.set()
        release.wait(timeout=3.0)
        return "up"

    def run():
        result.update(pg.make_voice_prediction(
            "bitcoin",
            3600,
            db_path=":memory:",
            stop_event=stop,
        ))

    with patch.object(pg.wp, "fetch_price", return_value=100.0), patch.object(
        pg, "_ask_voice_direction", side_effect=blocked_voice
    ), patch.object(pg.wp, "make_prediction") as make_prediction:
        thread = threading.Thread(target=run)
        thread.start()
        assert started.wait(timeout=2.0)
        stop.set()
        release.set()
        thread.join(timeout=2.0)

    assert not thread.is_alive()
    assert result.get("error") == "shutdown_requested"
    make_prediction.assert_not_called()


def test_self_prediction_does_not_write_after_stop_during_status_read():
    started = threading.Event()
    release = threading.Event()
    stop = threading.Event()
    result = {}

    def blocked_status():
        started.set()
        release.wait(timeout=3.0)
        return {"readiness_score": 0.5, "total_fires": 10}

    def run():
        result.update(sp.make_self_prediction(
            conversations_writer=object(),
            stop_event=stop,
        ))

    with patch.object(sp, "ensure_schema"), patch.object(
        sp, "_read_status", side_effect=blocked_status
    ), patch.object(sp, "_writer_transaction") as writer_transaction:
        thread = threading.Thread(target=run)
        thread.start()
        assert started.wait(timeout=2.0)
        stop.set()
        release.set()
        thread.join(timeout=2.0)

    assert not thread.is_alive()
    assert result.get("error") == "shutdown_requested"
    writer_transaction.assert_not_called()


def test_self_prediction_tick_stops_before_starting_next_stage():
    stop = threading.Event()
    loop = sp.SelfPredictionLoop(conversations_writer=object())

    def make_and_stop(*_args, **_kwargs):
        stop.set()
        return {"error": "shutdown_requested"}

    with patch.object(sp, "resolve_due", return_value=0), patch.object(
        sp, "adapt_threshold", return_value=None
    ), patch.object(sp, "make_self_prediction", side_effect=make_and_stop), patch.object(
        sp, "resolve_authored"
    ) as resolve_authored:
        loop.tick(stop_event=stop)

    resolve_authored.assert_not_called()
