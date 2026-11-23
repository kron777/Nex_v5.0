"""Stage 4 (RDO v1.3 §16) — read-only belief audit.

Verifies the source-grounded belief-lifecycle audit against the real repository: every lifecycle
phase is evidenced with provenance, host-only facts are honest placeholders (never guessed), the
gap map is traceable and does NOT assert a false gap, and the tooling is read-only.
"""
import json
import os
import subprocess
import sys

from rdo import belief_audit as ba


def test_every_lifecycle_phase_is_evidenced():
    a = ba.audit(".")
    # origin, persistence, provenance, update, relationship, influence are all mapped
    for phase in ("origin", "persistence", "provenance", "update", "relationship", "influence"):
        assert a["lifecycle"].get(phase), f"phase {phase} has no findings"
    # every spec finding resolved to real file:line evidence
    assert a["tracked"] == a["findings_total"]
    for f in sum(a["lifecycle"].values(), []):
        assert f["evidence"], f"{f['subject']} has no evidence"
        assert ":" in f["evidence"][0]          # file:line provenance


def test_provenance_on_every_finding():
    a = ba.audit(".")
    for f in sum(a["lifecycle"].values(), []):
        assert f["origin"] == "cloud" and f["source_ref"]       # where the evidence came from
        assert f["evidence_class"] in ("static", "implemented")  # source-grounded, not runtime


def test_host_only_facts_are_flagged_not_guessed():
    a = ba.audit(".")
    subs = {h["subject"] for h in a["host_only_unknowns"]}
    assert "live.belief_row_count" in subs and "live.confidence_distribution" in subs
    for h in a["host_only_unknowns"]:
        assert h["origin"] == "host" and h["evidence_class"] == "unknown"
        assert h["modifier"] == "unverified" and h["data"] is None   # never a guessed value


def test_belief_stores_and_typed_relationships_found():
    a = ba.audit(".")
    subs = {f["subject"]: f for f in sum(a["lifecycle"].values(), [])}
    for store in ("store.beliefs", "store.belief_edges", "store.belief_activation"):
        assert subs[store]["status"] == "tracked"
    # NEX belief_edges are already typed (supports/opposes/synthesises/...)
    assert subs["edges.typed"]["status"] == "tracked"


def test_consumption_surface_measured():
    a = ba.audit(".")
    assert a["consumption"]["consumer_file_count"] > 0      # real belief readers exist
    assert all("beliefs" not in s or s.endswith(".py") for s in a["consumption"]["sample"])


def test_gap_map_does_not_assert_a_false_gap():
    # belief lifecycle IS tracked in-row (last_promoted_at/last_demoted_at/promotion_log/...),
    # so the update-tracking gap must be RESOLVED, not falsely reported as missing.
    g = ba.gap_map(".")
    update_gap = next(x for x in g["gaps"] if x["gap"] == "belief_update_tracking")
    assert update_gap["resolved"] is True
    cols = ba._beliefs_table_columns(".")
    assert "last_promoted_at" in cols and "promotion_log" in cols


def test_gap_map_real_gaps_have_evidence():
    g = ba.gap_map(".")
    assert g["open_gaps"] >= 1
    byname = {x["gap"]: x for x in g["gaps"]}
    # the documented decision-INERT inconsistency is a real, evidenced open gap
    inert = byname["belief_boost_inert"]
    assert inert["resolved"] is False and inert["evidence"]
    assert "INERT" in inert["evidence"][0] or "do NOT build" in inert["evidence"][0]
    # host-only provenance completeness is flagged as such, not guessed
    assert byname["provenance_completeness_unverified"].get("host_only") is True


def test_audit_is_read_only():
    # the audit never imports sqlite3 and never opens a file for writing — it only greps + reads
    src = open(os.path.join(os.path.dirname(ba.__file__), "belief_audit.py"), encoding="utf-8").read()
    assert "import sqlite3" not in src
    import re
    for m in re.finditer(r"open\(([^)]*)\)", src):
        assert '"w"' not in m.group(1) and "'w'" not in m.group(1) and '"a"' not in m.group(1)
    # running the audit creates no files in the working tree
    before = set(os.listdir("."))
    ba.audit(".")
    ba.gap_map(".")
    assert set(os.listdir(".")) == before


def test_evidence_is_traceable_repo_relative():
    a = ba.audit(".")
    for f in sum(a["lifecycle"].values(), []):
        for ev in f["evidence"]:
            path = ev.split(":", 1)[0]
            assert not os.path.isabs(path)                 # repo-relative, traceable
            # the cited file exists (schema/code evidence is real)
            assert os.path.exists(path) or path.endswith(".sql")


def test_stage4_end_to_end_and_resume(tmp_path):
    from rdo.report import run_stage4_belief_audit
    d = str(tmp_path / "s4")
    res = run_stage4_belief_audit(repo_dir=".", workdir=d)
    assert res["lifecycle_phases_evidenced"].startswith("14/")
    assert res["open_gaps"] >= 1 and res["consumer_file_count"] > 0
    assert ("belief_update_tracking", "tracking", True) in res["gap_summary"]
    # durable analysis persists and resumes in a fresh process
    code = (f"import json; d=json.load(open({os.path.join(d, 'belief_audit.json')!r})); "
            "print(json.dumps({'phases':len(d['audit']['lifecycle']),'open':d['gap_map']['open_gaps']}))")
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["open"] == res["open_gaps"] and out["phases"] >= 6
