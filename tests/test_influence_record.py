"""Phase 0 M0.5 — tests for the default-OFF InfluenceRecord causal-trace overlay.

The contract under test (see influence_record.py):
  * DEFAULT OFF: no-op, no file, returns None.
  * ZERO BEHAVIOURAL DELTA: a faithful reproduction of each producer seam yields
    a byte-identical output and byte-identical "DB writes" with the overlay OFF
    vs ON — the only difference is the side-channel trace file, which exists only
    when ON and is never a substrate DB.
  * SIDE-CHANNEL + FAIL-SAFE: the sink is a dedicated trace file, never one of the
    six substrate DBs; any sink error is swallowed.
  * EVIDENCE LADDER: directly-observed inputs are L3 in fixture context and L4
    only when the live runtime declares itself (context='runtime').

These exercise the overlay module and faithful seam harnesses. The real edited
seams are inert by default (flag unset), so the full existing suite is the
regression evidence that the integration changes nothing out of the box.
"""
import json
import os

import pytest

import influence_record as ir
from influence_record import InfluenceTracer, InfluenceEntry


@pytest.fixture(autouse=True)
def _isolate_tracer(tmp_path, monkeypatch):
    # Never touch the real env flag or the real sink during tests.
    monkeypatch.delenv("NEX5_INFLUENCE_TRACE", raising=False)
    monkeypatch.delenv("NEX5_INFLUENCE_TRACE_PATH", raising=False)
    monkeypatch.delenv("NEX5_INFLUENCE_TRACE_CONTEXT", raising=False)
    ir.reset_tracer()
    yield
    ir.reset_tracer()


def _sink(tmp_path):
    return tmp_path / "trace.jsonl"


# --------------------------------------------------------------- default OFF
def test_default_is_off(monkeypatch):
    # No flag set -> the module-level tracer is disabled.
    assert ir.tracer().enabled is False


def test_disabled_records_nothing_and_writes_no_file(tmp_path):
    t = InfluenceTracer(sink_path=_sink(tmp_path), enabled=False)
    assert t.record_fountain_fire("a thought", mode_name="DEFAULT") is None
    assert t.record_chat_turn(prompt="hi", reply="hello") is None
    assert not _sink(tmp_path).exists()


# ------------------------------------------------- zero behavioural delta
def _fountain_seam(generate, *, mode_name, last_fire_ts, total_fires, db):
    """Faithful reproduction of theory_x/stage6_fountain/__init__.py:fountain_loop
    seam — identical control flow to the wired integration."""
    thought = generate()
    if thought:
        db.append(("log", thought[:100]))
    try:
        tr = ir.tracer()
        if tr.enabled and thought:
            tr.record_fountain_fire(thought, mode_name=mode_name, readiness=None,
                                    last_fire_ts=last_fire_ts, total_fires=total_fires)
    except Exception:
        pass
    return thought, db


def _chat_seam(compose, *, prompt, register, session_id, voice_ok, tool_used, db):
    """Faithful reproduction of gui/server.py:api_chat seam."""
    text = compose(prompt)
    if session_id is not None:
        db.append(("messages", session_id, "nex", text, register))
    try:
        tr = ir.tracer()
        if tr.enabled:
            tr.record_chat_turn(prompt=prompt, reply=text, register=register,
                                session_id=session_id, voice_ok=voice_ok,
                                tool_used=tool_used)
    except Exception:
        pass
    return text, db


def test_fountain_seam_output_and_db_identical_off_vs_on(tmp_path):
    gen = lambda: "she notices the morning light"
    # OFF
    ir.set_tracer(InfluenceTracer(sink_path=tmp_path / "off.jsonl", enabled=False))
    out_off, db_off = _fountain_seam(gen, mode_name="DEFAULT", last_fire_ts=1.0,
                                     total_fires=7, db=[])
    # ON
    ir.set_tracer(InfluenceTracer(sink_path=tmp_path / "on.jsonl", enabled=True))
    out_on, db_on = _fountain_seam(gen, mode_name="DEFAULT", last_fire_ts=1.0,
                                   total_fires=7, db=[])
    # The system's own behaviour (output + DB writes) is byte-identical.
    assert out_off == out_on
    assert db_off == db_on
    # The ONLY difference is the side-channel trace, present only when ON.
    assert not (tmp_path / "off.jsonl").exists()
    assert (tmp_path / "on.jsonl").exists()


def test_chat_seam_output_and_db_identical_off_vs_on(tmp_path):
    compose = lambda p: f"reply to: {p}"
    ir.set_tracer(InfluenceTracer(sink_path=tmp_path / "off.jsonl", enabled=False))
    out_off, db_off = _chat_seam(compose, prompt="how are you?", register="PLAIN",
                                 session_id="s1", voice_ok=True, tool_used=None, db=[])
    ir.set_tracer(InfluenceTracer(sink_path=tmp_path / "on.jsonl", enabled=True))
    out_on, db_on = _chat_seam(compose, prompt="how are you?", register="PLAIN",
                               session_id="s1", voice_ok=True, tool_used=None, db=[])
    assert out_off == out_on
    assert db_off == db_on
    assert not (tmp_path / "off.jsonl").exists()
    assert (tmp_path / "on.jsonl").exists()


def test_overlay_does_not_mutate_observed_values(tmp_path):
    t = InfluenceTracer(sink_path=_sink(tmp_path), enabled=True)
    thought = "an immutable thought"
    before = thought
    t.record_fountain_fire(thought, mode_name="DEFAULT", readiness=0.7,
                           last_fire_ts=1.0, total_fires=1)
    assert thought == before and thought is before
    prompt, reply = "q", "a"
    t.record_chat_turn(prompt=prompt, reply=reply, register="PLAIN")
    assert prompt == "q" and reply == "a"


# ------------------------------------------------------------ record structure
def test_fountain_record_structure_and_digest(tmp_path):
    t = InfluenceTracer(sink_path=_sink(tmp_path), enabled=True)
    rec = t.record_fountain_fire("hello world", mode_name="DREAM", readiness=0.5,
                                 last_fire_ts=123.0, total_fires=42)
    assert rec["produced"] == "fountain_fire"
    assert rec["output"]["kind"] == "thought"
    assert rec["output"]["digest"] == ir._digest("hello world")
    assert rec["output"]["length"] == len("hello world")
    assert rec["cycle_id"] == "fire:42"
    # directly-observed inputs are L3 in fixture context
    mode = [e for e in rec["inputs"] if e["kind"] == "mode"][0]
    assert mode["evidence_level"] == "L3"
    assert mode["evidence_class"] == "implemented"
    # belief-level attribution is honestly UNKNOWN
    assert any("belief-level attribution" in u for u in rec["unresolved"])


def test_chat_record_structure(tmp_path):
    t = InfluenceTracer(sink_path=_sink(tmp_path), enabled=True)
    rec = t.record_chat_turn(prompt="what is real?", reply="what persists",
                             register="PHILOSOPHICAL", session_id="sess-9",
                             voice_ok=True, tool_used=None)
    assert rec["produced"] == "chat_turn"
    assert rec["output"]["kind"] == "reply"
    assert rec["cycle_id"] == "chat:sess-9"
    pm = [e for e in rec["inputs"] if e["kind"] == "user_message"][0]
    assert pm["value_digest"] == ir._digest("what is real?")
    # tool_used is None -> that input is L0/UNKNOWN, not asserted as observed
    tu = [e for e in rec["inputs"] if e["kind"] == "tool_result"][0]
    assert tu["evidence_level"] == "L0"


# ----------------------------------------------------------- runtime vs fixture
def test_runtime_context_is_L4_fixture_is_L3(tmp_path):
    fx = InfluenceTracer(sink_path=tmp_path / "f.jsonl", enabled=True, context="fixture")
    rt = InfluenceTracer(sink_path=tmp_path / "r.jsonl", enabled=True, context="runtime")
    r_fx = fx.record_fountain_fire("t", mode_name="DEFAULT")
    r_rt = rt.record_fountain_fire("t", mode_name="DEFAULT")
    lvl_fx = [e for e in r_fx["inputs"] if e["kind"] == "mode"][0]["evidence_level"]
    lvl_rt = [e for e in r_rt["inputs"] if e["kind"] == "mode"][0]["evidence_level"]
    assert lvl_fx == "L3" and lvl_rt == "L4"


def test_context_defaults_to_fixture_not_runtime(monkeypatch):
    # Without the explicit runtime declaration, L4 is never asserted.
    monkeypatch.setenv("NEX5_INFLUENCE_TRACE", "1")
    t = InfluenceTracer()
    assert t.context == "fixture"
    monkeypatch.setenv("NEX5_INFLUENCE_TRACE_CONTEXT", "runtime")
    assert t.context == "runtime"


# -------------------------------------------------------------- append + sink
def test_append_only_jsonl(tmp_path):
    sink = _sink(tmp_path)
    t = InfluenceTracer(sink_path=sink, enabled=True)
    t.record_fountain_fire("one", mode_name="A")
    t.record_chat_turn(prompt="p", reply="two")
    lines = [l for l in sink.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 2
    assert json.loads(lines[0])["produced"] == "fountain_fire"
    assert json.loads(lines[1])["produced"] == "chat_turn"


def test_sink_is_never_a_substrate_db(monkeypatch):
    monkeypatch.delenv("NEX5_INFLUENCE_TRACE_PATH", raising=False)
    sink = InfluenceTracer().sink_path
    assert sink.name == "influence_trace.jsonl"
    assert sink.parent.name == "logs"
    from substrate.paths import db_paths
    db_files = {str(p) for p in db_paths().values()}
    assert str(sink) not in db_files
    assert not str(sink).endswith(".db")


def test_env_flag_toggles_enabled(monkeypatch):
    monkeypatch.setenv("NEX5_INFLUENCE_TRACE", "1")
    assert InfluenceTracer().enabled is True
    monkeypatch.setenv("NEX5_INFLUENCE_TRACE", "off")
    assert InfluenceTracer().enabled is False
    monkeypatch.setenv("NEX5_INFLUENCE_TRACE", "true")
    assert InfluenceTracer().enabled is True


# ------------------------------------------------------------------ fail-safe
def test_failsafe_on_bad_sink_returns_none(tmp_path):
    # sink path whose parent cannot be created (a file is in the way)
    blocker = tmp_path / "blocker"
    blocker.write_text("x")
    bad = InfluenceTracer(sink_path=blocker / "sub" / "trace.jsonl", enabled=True)
    # must not raise; returns None
    assert bad.record_fountain_fire("t", mode_name="A") is None


def test_no_fire_output_none_records_nothing(tmp_path):
    t = InfluenceTracer(sink_path=_sink(tmp_path), enabled=True)
    assert t.record_fountain_fire(None, mode_name="A") is None
    assert not _sink(tmp_path).exists()


def test_singleton_set_and_reset(tmp_path):
    custom = InfluenceTracer(sink_path=_sink(tmp_path), enabled=True)
    ir.set_tracer(custom)
    assert ir.tracer() is custom
    ir.reset_tracer()
    assert ir.tracer() is not custom
    assert isinstance(ir.tracer(), InfluenceTracer)


def test_evidence_ladder_maps_to_watcher_vocabulary():
    # the L-ladder stays reconcilable with the Watcher evidence_class vocabulary
    assert ir.L_TO_EVIDENCE_CLASS[ir.L0_UNKNOWN] == "unknown"
    assert ir.L_TO_EVIDENCE_CLASS[ir.L4_RUNTIME] == "measured"
    e = InfluenceEntry(source="s", kind="k", evidence_level=ir.L2_STATIC)
    assert e.to_dict()["evidence_class"] == "static"
