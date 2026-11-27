"""Stage 4 (RDO v1.3 §16) — read-only belief audit.

A SOURCE-GROUNDED, read-only map of NEX's belief lifecycle — origin, persistence, update,
relationship, consumption and influence — with provenance (file:line) for every finding and an
honest, traceable gap map. It reads the repository only; it issues no live-DB query, write,
injection, config change or restart. Facts that only the live machine can establish (row counts,
the actual confidence distribution, what is firing now) are recorded as honest HOST placeholders,
never guessed.

Reuses: `reconcile._grep` (the same read-only grep the reconciler uses) for evidence, and the
Watcher's `Evidence` / `host_placeholder` vocabulary for provenance and honest unknowns. It does
NOT modify the Watcher or NEX.
"""
from __future__ import annotations

import os
import subprocess
from typing import Dict, List, Optional

from watcher.evidence import Evidence, host_placeholder


def _grep(pattern: str, repo_dir: str, path: Optional[str], max_hits: int = 3) -> List[str]:
    """Read-only evidence grep — the same shape as `reconcile._grep`, extended to include `.sql`
    so the externalised belief schema (`substrate/schema/beliefs.sql`) is visible. Returns up to
    `max_hits` repo-relative `file:line:match` strings; never writes anything."""
    target = os.path.join(repo_dir, path) if path else repo_dir
    if not os.path.exists(target):
        return []
    try:
        res = subprocess.run(
            ["grep", "-rnIH", "-E", pattern, "--include=*.py", "--include=*.md",
             "--include=*.json", "--include=*.sql", "--exclude-dir=__pycache__",
             "--exclude-dir=.git", "--exclude-dir=.venv", "--exclude-dir=.cycles", target],
            capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    lines = [ln for ln in res.stdout.splitlines() if ln.strip()]
    return [ln.replace(repo_dir.rstrip("/") + "/", "", 1) for ln in lines[:max_hits]]

# Declarative audit specification: (phase, subject, pattern, path, evidence_class, interpretation).
# Each row is checked read-only against the real tree; the match lines are the provenance.
_SPEC = [
    # ---- stores / persistence ----
    ("persistence", "store.beliefs", r"CREATE TABLE IF NOT EXISTS beliefs",
     "substrate/schema/beliefs.sql", "static", "the primary belief store (content, confidence, source, created_at)"),
    ("persistence", "store.belief_edges", r"CREATE TABLE IF NOT EXISTS belief_edges",
     "substrate/schema/beliefs.sql", "static", "typed belief-to-belief relationships"),
    ("persistence", "store.belief_blacklist", r"CREATE TABLE IF NOT EXISTS belief_blacklist",
     "substrate/schema/beliefs.sql", "static", "suppressed/forbidden belief content"),
    ("persistence", "store.belief_activation", r"CREATE TABLE IF NOT EXISTS belief_activation",
     "substrate/init_db.py", "static", "per-belief recency (last_touched_at)"),
    ("persistence", "schema.confidence", r"confidence\s+REAL",
     "substrate/schema/beliefs.sql", "static", "confidence is a first-class persisted column"),
    ("persistence", "schema.created_at", r"created_at\s+INTEGER",
     "substrate/schema/beliefs.sql", "static", "creation time is persisted"),
    # ---- origin / creation ----
    ("origin", "creation.write_paths", r"INSERT (OR [A-Z]+ )?INTO beliefs",
     "substrate", "implemented", "where beliefs are created/written"),
    ("origin", "creation.source_column", r"source\s+TEXT",
     "substrate/schema/beliefs.sql", "static", "each belief records its origin stream in `source`"),
    # ---- provenance ----
    ("provenance", "provenance.source_kind", r"def kind_for|source_kind",
     "substrate/source_kind.py", "implemented", "per-stream provenance, stamped at the write boundary"),
    # ---- update / lifecycle ----
    ("update", "update.write_boundary", r"UPDATE beliefs",
     "substrate", "implemented", "belief rows are updated here (confidence/source corrections)"),
    ("update", "update.recency_touch", r"last_touched_at",
     "substrate/init_db.py", "static", "recency is updated via belief_activation"),
    # ---- relationships ----
    ("relationship", "edges.typed", r"edge_type\s+TEXT NOT NULL CHECK",
     "substrate/schema/beliefs.sql", "static", "belief_edges are typed: supports/opposes/synthesises/cross_domain/refines"),
    # ---- influence ----
    ("influence", "influence.belief_boost", r"belief_boost",
     "theory_x", "implemented", "a priority-boost lever on beliefs"),
    ("influence", "influence.generation_bias", r"FROM beliefs|belief.*(boost|bias|weight)",
     "theory_x/stage6_fountain", "implemented", "generation/retrieval is biased by beliefs"),
]


def _finding(phase: str, subject: str, pattern: str, path: str, cls: str,
             interp: str, repo_dir: str) -> dict:
    hits = _grep(pattern, repo_dir, path if path else None)
    ev = Evidence(subject=subject, data={"pattern": pattern, "hits": hits}, origin="cloud",
                  evidence_class=cls if hits else "unknown",
                  source_ref=path or repo_dir, modifier=None if hits else "unverified",
                  interpretation=interp)
    return {"phase": phase, "subject": subject, "status": "tracked" if hits else "not_found",
            "evidence": hits, "evidence_class": ev.evidence_class, "origin": ev.origin,
            "source_ref": ev.source_ref, "interpretation": interp}


def _beliefs_table_columns(repo_dir: str) -> List[str]:
    """Read-only: the column names declared in the `beliefs` CREATE TABLE block (NOT other tables
    in the same schema file), so a lifecycle-tracking gap is checked against the belief store itself."""
    import re
    path = os.path.join(repo_dir, "substrate/schema/beliefs.sql")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        txt = fh.read()
    m = re.search(r"CREATE TABLE IF NOT EXISTS beliefs\s*\((.*?)\)\s*;", txt, re.S)
    if not m:
        return []
    cols: List[str] = []
    for line in m.group(1).splitlines():
        tok = line.strip().strip(",").split()
        if tok and tok[0].isidentifier() and tok[0].upper() not in ("PRIMARY", "UNIQUE", "CHECK", "FOREIGN"):
            cols.append(tok[0])
    return cols


def audit(repo_dir: str = ".") -> dict:
    """Run the read-only, source-grounded belief-lifecycle audit."""
    findings = [_finding(*row, repo_dir) for row in _SPEC]
    by_phase: Dict[str, List[dict]] = {}
    for f in findings:
        by_phase.setdefault(f["phase"], []).append(f)

    # precise consumer signal: files that actually READ the belief store (SQL reads), not every
    # file that merely mentions the word "beliefs"
    consumers = _grep(r"FROM beliefs|JOIN beliefs|read_belief", repo_dir, "theory_x", max_hits=2000)
    consumer_files = sorted({ln.split(":", 1)[0] for ln in consumers})

    # live-state facts are HOST-only: record honest placeholders, never a guess
    host = [
        host_placeholder("live.belief_row_count", "host: sqlite3 'file:beliefs.db?mode=ro'",
                         "live belief count is host-only (read-only DB); not observed from the cloud"),
        host_placeholder("live.confidence_distribution", "host: SELECT confidence FROM beliefs",
                         "the actual confidence distribution is host-only"),
        host_placeholder("live.active_firing", "host: a live trace",
                         "which beliefs are being read/activated at runtime is host-only (NEX in standby)"),
    ]
    return {
        "stage": "RDO v1.3 §16 Stage 4 — read-only belief audit",
        "lifecycle": by_phase,
        "phase_order": ["origin", "persistence", "provenance", "update", "relationship",
                        "influence", "consumption"],
        "consumption": {"consumer_file_count": len(consumer_files),
                        "sample": consumer_files[:12]},
        "host_only_unknowns": [h.to_dict() for h in host],
        "findings_total": len(findings),
        "tracked": sum(1 for f in findings if f["status"] == "tracked"),
    }


def gap_map(repo_dir: str = ".", audit_result: dict | None = None) -> dict:
    """Derive the traceable gap map: untracked influence surface, lifecycle-tracking gaps,
    inconsistencies and unresolved questions — each with its own provenance."""
    a = audit_result or audit(repo_dir)
    gaps: List[dict] = []

    # 1. lifecycle-tracking check (don't assume absence from a differing column name): inspect the
    #    BELIEFS table's own columns. NEX tracks updates via promote/demote timestamps + a log, not
    #    an `updated_at` column — so this is NOT a gap. Recorded as a resolved, evidenced finding.
    cols = _beliefs_table_columns(repo_dir)
    tracking_cols = [c for c in cols if c in (
        "updated_at", "status", "last_updated", "last_promoted_at", "last_demoted_at",
        "promotion_log", "last_referenced_at", "erosion_stage", "reinforce_count")]
    gaps.append({
        "gap": "belief_update_tracking", "severity": "tracking",
        "finding": ("belief lifecycle IS tracked in the row, via " + ", ".join(tracking_cols)
                    if tracking_cols else
                    "the beliefs table has no update/lifecycle tracking column — updates are untimestamped"),
        "evidence": [f"beliefs columns: {cols}"],
        "resolved": bool(tracking_cols),
    })

    # 2. belief_boost influence is decision-INERT -> a mechanism that exists but does not act
    inert = _grep(r"decision-INERT|do NOT build", repo_dir, "tools/check_belief_headroom.py")
    gaps.append({
        "gap": "belief_boost_inert", "severity": "inconsistency",
        "finding": "belief_boost is an influence lever that exists in schema/consumers but is documented "
                   "decision-INERT ('do NOT build'); presence does not imply effect",
        "evidence": inert, "resolved": False,
    })

    # 3. large, partially-tracked influence surface -> untracked influences (candidate, needs review)
    consumer_n = a["consumption"]["consumer_file_count"]
    gaps.append({
        "gap": "untracked_influence_surface", "severity": "unresolved",
        "finding": f"{consumer_n} source files read beliefs; the Watcher runtime graph tracks only a "
                   f"subset of belief->behaviour influence edges — the remainder is an untracked "
                   f"influence surface to review (not proof of a defect)",
        "evidence": a["consumption"]["sample"], "resolved": False,
    })

    # 4. provenance completeness is a host/runtime question (writes that bypass source stamping)
    gaps.append({
        "gap": "provenance_completeness_unverified", "severity": "unresolved",
        "finding": "source_kind is stamped at the write boundary, but whether every live write sets a "
                   "source (no NULL/unstamped rows) is a HOST-only question — unknown from the cloud",
        "evidence": _grep(r"def kind_for|stamped at the write boundary", repo_dir, "substrate/source_kind.py"),
        "resolved": False, "host_only": True,
    })

    return {
        "stage": "RDO v1.3 §16 Stage 4 — belief audit gap map",
        "gaps": gaps,
        "open_gaps": sum(1 for g in gaps if not g.get("resolved")),
        "note": "read-only, source-grounded; host-only items are flagged, never guessed",
    }
