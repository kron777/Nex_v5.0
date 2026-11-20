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


def test_live_learning_loop_is_implemented():
    cyc = _cycles()
    impl = [c for c in cyc if c["status"] == "implemented"]
    assert impl, "the live learning<->beliefs loop must appear as an implemented cycle"
    joined = [" ".join(c["cycle"]) for c in impl]
    assert any("beliefs.confidence" in j and "reconciler" in j for j in joined)
    assert all("affect_state" not in c["cycle"] for c in impl)


def test_mood_loop_stays_hypothesis():
    cyc = _cycles()
    for c in cyc:
        if "affect_state" in c["cycle"]:
            assert c["status"] == "HYPOTHESIS", "mood loop must never be promoted to fact"
    # and the hypothesis edges carry an explicit note
    g = build_runtime_graph()
    hyp_edges = [e for e in g.edges if e.src == "affect_state" or e.dst == "beliefs.confidence"
                 and e.evidence_class == "inferred"]
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
