"""Cooperative shutdown regressions for CounterfactualNode."""
import threading
from types import SimpleNamespace
from unittest.mock import MagicMock

from theory_x.stage_counterfactual import CounterfactualNode
from theory_x.stage_gate.coherence_gate import GateOutcome


def _problem_reader():
    reader = MagicMock()
    reader.read.return_value = [{
        "id": 17,
        "title": "Explore a meaningful open question",
        "description": "A bounded description for the counterfactual scan.",
        "created_at": 1.0,
        "tags": "test",
    }]
    return reader


def _candidate():
    return {
        "content": "A grounded candidate belief for this open problem.",
        "confidence": 0.7,
        "branch_id": "cognition",
    }


def test_counterfactual_stops_after_blocked_fetch_returns():
    started = threading.Event()
    release = threading.Event()
    stop = threading.Event()
    time_fetch = MagicMock()
    refinement = MagicMock()

    def blocked_fetch(*_args, **_kwargs):
        started.set()
        release.wait(timeout=3.0)
        return [_candidate()]

    time_fetch.fetch_from_beliefs.side_effect = blocked_fetch
    node = CounterfactualNode(
        beliefs_reader=MagicMock(),
        beliefs_writer=MagicMock(),
        conversations_reader=_problem_reader(),
        conversations_writer=MagicMock(),
        coherence_gate=MagicMock(),
        time_fetch=time_fetch,
        refinement_engine=refinement,
    )

    thread = threading.Thread(
        target=node._process_one,
        kwargs={"stop_event": stop},
    )
    thread.start()
    assert started.wait(timeout=2.0)
    stop.set()
    release.set()
    thread.join(timeout=2.0)

    assert not thread.is_alive()
    refinement.run.assert_not_called()
    node._gate.check.assert_not_called()
    node._beliefs_writer.write.assert_not_called()


def test_counterfactual_does_not_insert_belief_after_stop_during_gate_check():
    entered_gate = threading.Event()
    release_gate = threading.Event()
    stop = threading.Event()
    time_fetch = MagicMock()
    time_fetch.fetch_from_beliefs.return_value = [_candidate()]
    refinement = MagicMock()
    refinement.run.return_value = [{
        "candidate": _candidate(),
        "score": 4,
        "buildable": True,
    }]

    def blocked_gate(_packet):
        entered_gate.set()
        release_gate.wait(timeout=3.0)
        return SimpleNamespace(outcome=GateOutcome.ACCEPT)

    gate = MagicMock()
    gate.check.side_effect = blocked_gate
    beliefs_writer = MagicMock()
    node = CounterfactualNode(
        beliefs_reader=MagicMock(),
        beliefs_writer=beliefs_writer,
        conversations_reader=_problem_reader(),
        conversations_writer=MagicMock(),
        coherence_gate=gate,
        time_fetch=time_fetch,
        refinement_engine=refinement,
    )

    thread = threading.Thread(
        target=node._process_one,
        kwargs={"stop_event": stop},
    )
    thread.start()
    assert entered_gate.wait(timeout=2.0)
    stop.set()
    release_gate.set()
    thread.join(timeout=2.0)

    assert not thread.is_alive()
    gate.check.assert_called_once()
    beliefs_writer.write.assert_not_called()


def test_counterfactual_tick_does_not_start_when_already_stopped():
    stop = threading.Event()
    stop.set()
    node = CounterfactualNode(
        beliefs_reader=MagicMock(),
        beliefs_writer=MagicMock(),
        conversations_reader=MagicMock(),
        conversations_writer=MagicMock(),
        coherence_gate=MagicMock(),
        time_fetch=MagicMock(),
        refinement_engine=MagicMock(),
    )
    node._process_one = MagicMock()

    node.tick(stop_event=stop)

    node._process_one.assert_not_called()
