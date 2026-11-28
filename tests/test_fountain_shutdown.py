"""Shutdown regressions for FountainGenerator's long generation path."""
import threading
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from theory_x.stage6_fountain.generator import FountainGenerator


def _generator(voice):
    with patch.dict("os.environ", {
        "NEX5_QUALITY_SYNTH": "0",
        "NEX5_SELF_NARRATIVE": "0",
        "NEX5_STAGE_TRACE": "0",
    }):
        sense_writer = MagicMock()
        dynamic_writer = MagicMock()
        generator = FountainGenerator(
            sense_writer=sense_writer,
            dynamic_writer=dynamic_writer,
            voice_client=voice,
            dynamic_reader=MagicMock(),
            beliefs_writer=MagicMock(),
            beliefs_reader=MagicMock(),
            problem_memory=None,
            sense_reader=MagicMock(),
            conversations_reader=MagicMock(),
        )
    # Constructor performs idempotent schema writes; isolate the generation path.
    sense_writer.reset_mock()
    dynamic_writer.reset_mock()
    generator._emphasis_engine = None
    generator._condenser = None
    generator._problem_memory = None
    generator._maybe_substrate_voice = MagicMock(return_value=None)
    generator._build_prompt = MagicMock(return_value=("A prepared prompt.", []))
    generator._evaluator.score = MagicMock(return_value=0.95)
    generator._evaluator.is_ready = MagicMock(return_value=True)
    return generator


def _dynamic_state():
    state = MagicMock()
    state.status.return_value = {"branches": []}
    return state


def test_fountain_discards_voice_response_if_stop_arrives_during_generation():
    started = threading.Event()
    release = threading.Event()
    stop = threading.Event()
    voice = MagicMock()

    def blocked_speak(*_args, **_kwargs):
        started.set()
        release.wait(timeout=3.0)
        return SimpleNamespace(text="A complete thought that would otherwise be recorded.")

    voice.speak.side_effect = blocked_speak
    generator = _generator(voice)
    generator._sense_writer.reset_mock()
    generator._dynamic_writer.reset_mock()

    with patch.dict("os.environ", {
        "NEX5_RECONCILE": "0",
        "NEX5_SUBSTRATE_EMIT": "0",
        "NEX5_STAGE_TRACE": "0",
        "NEX5_SENSE_OVERWHELM_N": "0",
    }):
        result = {}
        thread = threading.Thread(
            target=lambda: result.update(
                value=generator.generate(
                    _dynamic_state(), generator._beliefs_reader,
                    stop_event=stop,
                )
            )
        )
        thread.start()
        assert started.wait(timeout=3.0)
        stop.set()
        release.set()
        thread.join(timeout=3.0)

    assert not thread.is_alive()
    assert result.get("value") is None
    generator._sense_writer.write.assert_not_called()
    generator._dynamic_writer.write.assert_not_called()


def test_fountain_does_not_call_voice_if_stop_arrives_during_prompt_assembly():
    started = threading.Event()
    release = threading.Event()
    stop = threading.Event()
    voice = MagicMock()
    generator = _generator(voice)

    def blocked_prompt(*_args, **_kwargs):
        started.set()
        release.wait(timeout=3.0)
        return "A prepared prompt.", []

    generator._build_prompt = blocked_prompt
    with patch.dict("os.environ", {
        "NEX5_RECONCILE": "0",
        "NEX5_SUBSTRATE_EMIT": "0",
        "NEX5_STAGE_TRACE": "0",
        "NEX5_SENSE_OVERWHELM_N": "0",
    }):
        result = {}
        thread = threading.Thread(
            target=lambda: result.update(
                value=generator.generate(
                    _dynamic_state(), generator._beliefs_reader,
                    stop_event=stop,
                )
            )
        )
        thread.start()
        assert started.wait(timeout=3.0)
        stop.set()
        release.set()
        thread.join(timeout=3.0)

    assert not thread.is_alive()
    assert result.get("value") is None
    voice.speak.assert_not_called()
    generator._sense_writer.write.assert_not_called()
    generator._dynamic_writer.write.assert_not_called()


def test_fountain_generate_does_not_enter_core_when_already_stopped():
    stop = threading.Event()
    stop.set()
    generator = _generator(MagicMock())
    generator._generate = MagicMock()

    result = generator.generate(
        _dynamic_state(), generator._beliefs_reader, stop_event=stop
    )

    assert result is None
    generator._generate.assert_not_called()
