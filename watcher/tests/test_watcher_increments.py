"""Behaviour tests for the next-cycle increments: snapshots, connection ledger,
regression detection, longitudinal series, and cloud+host combined evidence.

All fixtures are isolated (temp dirs); nothing here touches NEX."""
import json

import pytest

from watcher.evidence import Evidence
from watcher.host import host_results_template, load_host_results
from watcher.collector import collect_combined
from watcher.architecture import Edge, RuntimeGraph, build_runtime_graph
from watcher.ledger import ConnectionLedger, LedgerError, seed_from_graph
from watcher.longitudinal import Series, cycle_timeline
from watcher.regression import detect, summarize
from watcher.snapshot import (diff_snapshots, load_snapshot, records_from_snapshot,
                              snapshot_dict, take_snapshot)


def _rec(subject, data, cls="static", origin="cloud", modifier=None):
    return Evidence(subject, data, origin, cls, "test", modifier=modifier)


# ---- snapshots: before/after ----

def test_snapshot_roundtrip_and_diff(tmp_path):
    before = [_rec("a", {"v": 1}), _rec("tool:x", {"verified_class": "passive"})]
    after = [_rec("a", {"v": 2}), _rec("b", {"v": 9})]  # a changed, b added, tool:x removed
    p = take_snapshot(before, "baseline", str(tmp_path), stage="s0")
    snap = load_snapshot(p)
    assert snap["stage"] == "s0" and snap["count"] == 2
    # reconstruct preserves the records
    rr = records_from_snapshot(snap)
    assert {r.subject for r in rr} == {"a", "tool:x"}
    d = diff_snapshots(snap, snapshot_dict(after, "treatment"))
    assert d["added"] == ["b"] and d["removed"] == ["tool:x"]
    assert any(c["subject"] == "a" and "data" in c["fields"] for c in d["changed"])


# ---- connection ledger: append-only lifecycle ----

def test_ledger_lifecycle_and_illegal_transition(tmp_path):
    led = ConnectionLedger(str(tmp_path / "ledger.jsonl"))
    led.record("x->y", "DECLARED")
    led.record("x->y", "SOURCE_CONFIRMED", evidence_refs=["src.py"])
    led.record("x->y", "TEST_WRITTEN", evidence_refs=["tests/test_x.py"])
    led.record("x->y", "TEST_PASSED", evidence_refs=["tests/test_x.py"])
    assert led.current_state("x->y") == "TEST_PASSED"
    # Even with host provenance and a trace, runtime cannot be the first lifecycle state.
    with pytest.raises(LedgerError, match="must be DECLARED/BLOCKED"):
        led.record("fresh->z", "RUNTIME_OBSERVED", origin="host",
                   evidence_refs=["trace:host-runtime-fresh"])
    # persistence: a new ledger over the same file sees history
    led2 = ConnectionLedger(str(tmp_path / "ledger.jsonl"))
    assert led2.current_state("x->y") == "TEST_PASSED"
    assert len(led2.history("x->y")) == 4


def test_ledger_seed_from_graph_keeps_runtime_unclaimed(tmp_path):
    led = ConnectionLedger(str(tmp_path / "l.jsonl"))
    graph = build_runtime_graph()
    seed_from_graph(led, graph)
    states = led.current_states()
    # a test_verified edge reaches TEST_PASSED; nothing reaches RUNTIME_OBSERVED (STANDBY)
    assert states["reconciler->beliefs.confidence"] == "TEST_PASSED"
    test_edge = next(e for e in graph.edges
                     if f"{e.src}->{e.dst}" == "reconciler->beliefs.confidence")
    history = led.history("reconciler->beliefs.confidence")
    test_entries = [h for h in history if h["to_state"] in ("TEST_WRITTEN", "TEST_PASSED")]
    assert test_edge.test_ref
    assert all(h["evidence_refs"] == [test_edge.test_ref] for h in test_entries)
    assert "RUNTIME_OBSERVED" not in states.values()
    # the scoped prompt-content relationship is source-confirmed, but remains
    # untested and unobserved at runtime; the broader feedback loop is still a hypothesis.
    assert states["affect_state->chat_assembly"] == "SOURCE_CONFIRMED"


def test_graph_rejects_test_verified_edge_without_test_reference():
    from watcher.architecture import Edge, RuntimeGraph
    graph = RuntimeGraph()
    with pytest.raises(ValueError, match="traceable test_ref"):
        graph.add(Edge("a", "b", "scoped source claim", True, True, False,
                       source_ref="src.py:1", test_ref=""))


# ---- regression detection ----

def test_regression_flags_tool_passive_to_active_and_weakening():
    before = snapshot_dict([
        _rec("tool:probe", {"verified_class": "passive"}),
        _rec("m", {"n": 1}, cls="measured"),
    ], "before")
    after = snapshot_dict([
        _rec("tool:probe", {"verified_class": "active"}),   # critical
        _rec("m", {"n": 1}, cls="inferred"),                # weakened
    ], "after")
    findings = detect(before, after)
    kinds = {f["kind"]: f for f in findings}
    assert kinds["tool_passive_to_active"]["severity"] == "critical"
    assert kinds["evidence_weakened"]["severity"] == "warning"
    assert summarize(findings)["critical"] == 1


def test_regression_flags_cycle_level_drop():
    g_before = {"feedback_cycles": [{"cycle": ["a", "b", "a"], "status": "test_verified"}]}
    g_after = {"feedback_cycles": [{"cycle": ["a", "b", "a"], "status": "hypothesis"}]}
    before = snapshot_dict([_rec("runtime_graph", g_before, cls="implemented")], "b")
    after = snapshot_dict([_rec("runtime_graph", g_after, cls="implemented")], "a")
    findings = detect(before, after)
    assert any(f["kind"] == "cycle_level_dropped" for f in findings)


# ---- longitudinal series ----

def test_series_trend_tracks_origin_across_stages():
    s0 = snapshot_dict([_rec("host:live_db_metadata", None, cls="unknown",
                             origin="host", modifier="unverified")], "s0", stage="pre")
    s1 = snapshot_dict([_rec("host:live_db_metadata", {"rows": 10}, cls="measured",
                             origin="host")], "s1", stage="post")
    series = Series([s1, s0])  # given out of order; Series sorts by taken_at
    trend = series.trend("host:live_db_metadata")
    assert [p["present"] for p in trend] == [True, True]
    assert trend[0]["origin"] == "host" and trend[-1]["evidence_class"] in ("unknown", "measured")
    assert series.compare_stages("s0", "s1")["changed"]


def test_cycle_timeline_reads_runtime_graph():
    gd = {"feedback_cycles": [{"cycle": ["r", "b", "r"], "status": "test_verified"}]}
    snap = snapshot_dict([_rec("runtime_graph", gd, cls="implemented")], "s0", stage="x")
    tl = cycle_timeline(Series([snap]))
    assert tl[0]["cycles"]["r -> b -> r"] == "test_verified"


# ---- host ingestion + combined, origins preserved ----

def test_host_template_and_load(tmp_path):
    tpl = host_results_template()
    assert "checkouts_drift" in tpl and tpl["checkouts_drift"]["data"] is None
    # fill one row, leave others null
    tpl["runtime_identity"]["data"] = {"state": "STANDBY"}
    tpl["runtime_identity"]["note"] = "no live process"
    p = tmp_path / "host.json"
    p.write_text(json.dumps(tpl))
    loaded = load_host_results(str(p))
    assert set(loaded) == {"runtime_identity"}  # null rows dropped, helper keys stripped
    assert "_commands" not in loaded["runtime_identity"]


def test_collect_combined_preserves_origins():
    recs = collect_combined(".", host_results={"runtime_identity": {
        "data": {"state": "STANDBY"}, "evidence_class": "measured", "source_ref": "host"}})
    origins = {r.origin for r in recs}
    assert origins == {"cloud", "host"}
    host_recs = [r for r in recs if r.origin == "host"]
    # the returned one is measured; the un-returned host requests are honest placeholders
    assert any(r.subject == "host:runtime_identity" and r.evidence_class == "measured"
               for r in host_recs)
    assert any(r.evidence_class == "unknown" and r.modifier == "unverified"
               for r in host_recs)

@pytest.mark.parametrize("state", [
    "SOURCE_CONFIRMED", "TEST_WRITTEN", "TEST_PASSED",
    "TEST_FAILED", "RUNTIME_OBSERVED", "REGRESSED",
])
def test_evidence_bearing_ledger_states_reject_missing_references(tmp_path, state):
    led = ConnectionLedger(str(tmp_path / f"{state.lower()}.jsonl"))
    origin = "host" if state == "RUNTIME_OBSERVED" else "cloud"

    with pytest.raises(LedgerError, match="requires nonblank evidence_refs"):
        led.record("x->y", state, origin=origin)


def test_ledger_rejects_non_list_evidence_references(tmp_path):
    led = ConnectionLedger(str(tmp_path / "bad-refs.jsonl"))

    with pytest.raises(LedgerError, match="evidence_refs must be a list"):
        led.record("x->y", "DECLARED", evidence_refs="trace:1")


def test_runtime_observation_ledger_requires_host_origin_and_evidence_refs(tmp_path):
    led = ConnectionLedger(str(tmp_path / "runtime-ledger.jsonl"))
    led.record("x->y", "DECLARED")
    led.record("x->y", "SOURCE_CONFIRMED", evidence_refs=["src.py"])

    with pytest.raises(LedgerError, match="host origin"):
        led.record("x->y", "RUNTIME_OBSERVED", origin="cloud",
                   evidence_refs=["trace:runtime-1"])
    with pytest.raises(LedgerError, match="evidence_refs"):
        led.record("x->y", "RUNTIME_OBSERVED", origin="host")

    refs = ["trace:host-runtime-1"]
    entry = led.record("x->y", "RUNTIME_OBSERVED", origin="host", evidence_refs=refs)
    refs.append("mutated-after-append")
    entry["evidence_refs"].append("mutated-return-value")
    entry["to_state"] = "BLOCKED"
    history = led.history("x->y")
    history[-1]["evidence_refs"].append("mutated-history-view")
    entries = led.entries
    entries.clear()

    assert led.current_state("x->y") == "RUNTIME_OBSERVED"
    assert led.history("x->y")[-1]["evidence_refs"] == ["trace:host-runtime-1"]


def test_runtime_graph_rejects_unbacked_runtime_observation():
    def edge(**overrides):
        values = dict(
            src="a", dst="b", label="test-edge",
            source_implemented=True, test_verified=False, runtime_observed=True,
            source_ref="src.py", runtime_origin="host", runtime_ref="trace:host-1",
        )
        values.update(overrides)
        return Edge(**values)

    with pytest.raises(ValueError, match="runtime_origin"):
        RuntimeGraph().add(edge(runtime_origin="cloud"))
    with pytest.raises(ValueError, match="runtime_ref"):
        RuntimeGraph().add(edge(runtime_ref=" "))
    with pytest.raises(ValueError, match="source_implemented"):
        RuntimeGraph().add(edge(source_implemented=False, source_ref=""))


def test_seed_from_graph_records_only_explicit_host_runtime_evidence(tmp_path):
    graph = RuntimeGraph()
    graph.add(Edge(
        "a", "b", "observed edge",
        source_implemented=True, test_verified=False, runtime_observed=True,
        source_ref="src.py", runtime_origin="host", runtime_ref="trace:host-runtime-2",
    ))
    ledger = ConnectionLedger(str(tmp_path / "runtime-seed.jsonl"))

    seed_from_graph(ledger, graph)

    runtime_entries = [entry for entry in ledger.history("a->b")
                       if entry["to_state"] == "RUNTIME_OBSERVED"]
    assert len(runtime_entries) == 1
    assert runtime_entries[0]["origin"] == "host"
    assert runtime_entries[0]["evidence_refs"] == ["trace:host-runtime-2"]
    reloaded = ConnectionLedger(str(tmp_path / "runtime-seed.jsonl"))
    assert reloaded.history("a->b")[-1]["evidence_refs"] == ["trace:host-runtime-2"]


@pytest.mark.parametrize("refs", [[None], [1], [""], ["   "], ["ok", None]])
def test_ledger_rejects_malformed_reference_items_even_for_non_evidence_states(tmp_path, refs):
    led = ConnectionLedger(str(tmp_path / "malformed-items.jsonl"))

    with pytest.raises(LedgerError, match="nonblank strings"):
        led.record("x->y", "DECLARED", evidence_refs=refs)


def test_failed_ledger_append_does_not_advance_in_memory_state(tmp_path, monkeypatch):
    import builtins
    from watcher import ledger as ledger_module

    path = tmp_path / "ledger.jsonl"
    led = ConnectionLedger(str(path))
    led.record("x->y", "DECLARED")
    original_open = builtins.open

    def fail_append(target, mode="r", *args, **kwargs):
        if str(target) == str(path) and "a" in mode:
            raise OSError("simulated append failure")
        return original_open(target, mode, *args, **kwargs)

    monkeypatch.setattr(ledger_module, "open", fail_append, raising=False)

    with pytest.raises(OSError, match="simulated append failure"):
        led.record("x->y", "SOURCE_CONFIRMED", evidence_refs=["src.py"])

    assert led.current_state("x->y") == "DECLARED"
    assert [entry["to_state"] for entry in led.history("x->y")] == ["DECLARED"]
    assert ConnectionLedger(str(path)).current_state("x->y") == "DECLARED"
