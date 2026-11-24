"""Core Watcher behaviour: evidence schema, runtime graph + cycles, readers,
registry, tool classification, provenance."""
import json

import pytest

from watcher.adapters import classify_tool, collect as adapters_collect
from watcher.architecture import (build_runtime_graph, read_dag, read_mind_map,
                                  runtime_graph_evidence)
from watcher.evidence import Evidence, host_placeholder
from watcher.provenance import collect_repo_provenance, detect_drift
from watcher.registry import ingest_registry


# ---- evidence schema ----

def test_evidence_rejects_bad_fields():
    with pytest.raises(ValueError):
        Evidence("s", 1, origin="bogus", evidence_class="measured", source_ref="x")
    with pytest.raises(ValueError):
        Evidence("s", 1, origin="cloud", evidence_class="bogus", source_ref="x")


def test_host_placeholder_is_honest():
    e = host_placeholder("x", "host", "note")
    assert e.origin == "host" and e.evidence_class == "unknown" and e.modifier == "unverified"
    assert e.data is None  # never a guessed value


# ---- runtime graph: the two feedback loops ----

def _cycles():
    return runtime_graph_evidence(build_runtime_graph()).data["feedback_cycles"]


def test_live_learning_loop_is_test_verified_not_runtime():
    # The live learning<->beliefs loop has code AND tests, but NEX is in STANDBY,
    # so it is NOT yet runtime_observed. The three dimensions must stay distinct.
    cyc = _cycles()
    tv = [c for c in cyc if c["status"] == "test_verified"]
    assert tv, "the live learning<->beliefs loop must appear as a test_verified cycle"
    joined = [" ".join(c["cycle"]) for c in tv]
    assert any("beliefs.confidence" in j and "reconciler" in j for j in joined)
    for c in tv:
        assert "affect_state" not in c["cycle"]
        assert c["source_implemented"] and c["test_verified"]
        assert c["runtime_observed"] is False  # never claimed observed while off


def test_mood_loop_stays_hypothesis():
    cyc = _cycles()
    mood = [c for c in cyc if "affect_state" in c["cycle"]]
    assert mood, "the candidate mood loop should still be detected as a cycle"
    for c in mood:
        assert c["status"] == "hypothesis", "mood loop must never be promoted to fact"
        assert c["runtime_observed"] is False
    # the hypothesis edges carry an explicit note and are NOT source_implemented
    g = build_runtime_graph()
    hyp_edges = [e for e in g.edges if e.level == "hypothesis"]
    assert hyp_edges and all(not e.source_implemented for e in hyp_edges)
    assert any(e.note and "HYPOTHESIS" in e.note for e in g.edges)


# ---- readers (do not modify source) ----

def test_readers_parse(tmp_path):
    mm = tmp_path / "mm.yaml"
    mm.write_text("nodes:\n  - id: a\n    layer: ring\n    evidence: static\n")
    dag = tmp_path / "d.json"
    dag.write_text(json.dumps({"nodes": {"L1": {"layer": 1, "status": "built", "prereqs": []}}}))
    me = read_mind_map(str(mm))
    de = read_dag(str(dag))
    assert me.evidence_class == "static" and me.data["node_count"] == 1
    assert de.data["by_status"] == {"built": 1}


# ---- registry ----

def test_registry_flags_active_windows(tmp_path):
    obs = tmp_path / "obs"
    obs.mkdir()
    (obs / "r77.md").write_text("done")
    (obs / "r78_PREREGISTRATION.md").write_text("pending")  # prereg, no report -> active
    (obs / "r77_baselines").mkdir()
    e = ingest_registry(str(obs))
    assert "r78" in e.data["active_or_pending"]
    assert "r77" in e.data["reported"]
    assert e.data["experiments"]["r77"]["baselines"] is True


# ---- tool classification ----

def test_classify_tool_active_vs_passive(tmp_path):
    active = tmp_path / "a.py"
    active.write_text("import sqlite3\nc.execute('INSERT INTO beliefs VALUES (1)')\nc.commit()\n")
    passive = tmp_path / "p.py"
    passive.write_text('"""READ-ONLY."""\nc=connect("file:x?mode=ro")\nc.execute("SELECT 1")\n')
    assert classify_tool(str(active)).data["class"] == "active"
    assert classify_tool(str(passive)).data["class"] == "passive"


def test_adapters_collect_flags_disagreements():
    recs = adapters_collect(".")
    assert recs, "should classify known tools in the real repo"
    # probe_runner is verified active
    pr = [r for r in recs if r.subject.endswith("probe_runner.py")]
    assert pr and pr[0].data["verified_class"] == "active"


# ---- provenance ----

def test_provenance_real_repo_and_host_placeholder():
    prov = collect_repo_provenance(".")
    assert any(r.subject == "checkout.HEAD" and r.data for r in prov)
    drift = detect_drift(".")
    # the deployed/home checkouts are recorded as host-only, never guessed
    host = [r for r in drift if r.origin == "host"]
    assert host and host[0].evidence_class == "unknown"

def test_git_empty_success_is_measured_but_failure_is_unknown(monkeypatch):
    from types import SimpleNamespace
    import watcher.provenance as provenance

    monkeypatch.setattr(provenance.subprocess, "run",
                        lambda *a, **k: SimpleNamespace(returncode=0, stdout="", stderr=""))
    assert provenance._git(".", "remote", "-v") == ""
    measured = provenance.collect_repo_provenance(".")
    assert all(r.evidence_class == "measured" for r in measured)
    dirty = next(r for r in measured if r.subject == "checkout.dirty")
    assert dirty.data is False

    monkeypatch.setattr(provenance.subprocess, "run",
                        lambda *a, **k: SimpleNamespace(returncode=128, stdout="", stderr="fatal"))
    assert provenance._git(".", "rev-parse", "HEAD") is None
    failed = provenance.collect_repo_provenance(".")
    head = next(r for r in failed if r.subject == "checkout.HEAD")
    dirty = next(r for r in failed if r.subject == "checkout.dirty")
    assert head.evidence_class == "unknown" and head.modifier == "unverified"
    assert dirty.evidence_class == "unknown" and dirty.data is None



def test_runtime_graph_edges_have_scoped_source_and_test_evidence():
    graph = build_runtime_graph()
    assert len(graph.edges) == 14  # twelve source-backed edges + two hypotheses
    source_edges = [edge for edge in graph.edges if edge.source_implemented]
    assert len(source_edges) == 12
    assert all(edge.source_ref and edge.claim and edge.scope and edge.caveat
               for edge in source_edges)
    assert all(edge.runtime_observed is False for edge in graph.edges)
    # Test verification is an edge-specific claim, not a blanket graph assertion.
    assert all(edge.test_ref for edge in source_edges if edge.test_verified)
    ownership_gate = next(edge for edge in source_edges
                          if edge.src == "ownership" and edge.dst == "valence_gate")
    assert ownership_gate.test_verified is False
    assert ownership_gate.test_ref == ""
    assert "focused threshold test" in ownership_gate.caveat
    # Bundled producer claims are narrowed to the evidence actually asserted.
    producer = next(edge for edge in source_edges
                    if edge.src == "beliefs.confidence")
    assert producer.dst == "owned_belief_expectations"
    assert "Internal-surprise" in producer.caveat
