"""Behaviour tests for the next-cycle increments: snapshots, connection ledger,
regression detection, longitudinal series, and cloud+host combined evidence.

All fixtures are isolated (temp dirs); nothing here touches NEX."""
import json

import pytest

from watcher.evidence import Evidence
from watcher.host import host_results_template, load_host_results
from watcher.collector import collect_combined
from watcher.architecture import build_runtime_graph
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
    led.record("x->y", "TEST_WRITTEN")
    led.record("x->y", "TEST_PASSED")
    assert led.current_state("x->y") == "TEST_PASSED"
    # cannot invent a runtime observation out of DECLARED on a fresh connection
    with pytest.raises(LedgerError):
        led.record("fresh->z", "RUNTIME_OBSERVED")
    # persistence: a new ledger over the same file sees history
    led2 = ConnectionLedger(str(tmp_path / "ledger.jsonl"))
    assert led2.current_state("x->y") == "TEST_PASSED"
    assert len(led2.history("x->y")) == 4


def test_ledger_seed_from_graph_keeps_runtime_unclaimed(tmp_path):
    led = ConnectionLedger(str(tmp_path / "l.jsonl"))
    seed_from_graph(led, build_runtime_graph())
    states = led.current_states()
    # a test_verified edge reaches TEST_PASSED; nothing reaches RUNTIME_OBSERVED (STANDBY)
    assert states["reconciler->beliefs.confidence"] == "TEST_PASSED"
    assert "RUNTIME_OBSERVED" not in states.values()
    # the scoped prompt-content relationship is source-confirmed, but remains
    # untested and unobserved at runtime; the broader feedback loop is still a hypothesis.
    assert states["affect_state->chat_assembly"] == "SOURCE_CONFIRMED"


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
