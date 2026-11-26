"""Reconciliation — check discovered obligations against the REAL repository,
read-only, before any work is proposed (RDO spec v1.4 §13 step 5, §30).

This step locates source anchors before work is proposed. For each obligation
with a known mechanism *signature*, the reconciler searches the actual tree:
all signatures match -> `signature_matched`; some -> `partial`; none ->
`missing`; unavailable scan/no signature -> `unknown`. A signature match is
only a source anchor. `reuse_existing` is reserved for a separate
semantic-satisfaction review.

It also deduplicates obligations. Candidate dependency edges are pruned only
when a separate semantic-satisfaction review establishes that the target already
meets the obligation; source-anchor matches alone do not remove dependencies.
"""
from __future__ import annotations

import dataclasses
import os
import subprocess
from typing import Callable, Dict, List, Optional

from .model import (MISSING, PARTIAL, RECON_UNKNOWN, REUSE_EXISTING, SIGNATURE_MATCHED,
                    Obligation, Relationship, has_valid_reuse_review)


@dataclasses.dataclass(frozen=True)
class Signature:
    """A grep pattern (optionally scoped to a path) that locates a source anchor.
    All required signatures matching => signature_matched, not semantic reuse."""
    pattern: str
    path: Optional[str] = None
    label: str = ""


def _grep(pattern: str, repo_dir: str, path: Optional[str], max_hits: int = 3) -> Optional[List[str]]:
    """Return matches, [] for a successful no-match, or None when the scan is unavailable.

    GNU grep uses exit 1 for a complete no-match and 2+ for errors. The scan
    searches all text-readable file types (-I skips binary files), rather than a
    hard-coded extension allowlist. Partial stdout from a failing scan is never
    accepted as complete evidence.
    """
    target = os.path.join(repo_dir, path) if path else repo_dir
    if not os.path.exists(target):
        return None
    try:
        # Run grep in the byte-oriented C locale. Under a multibyte UTF-8
        # locale GNU grep may classify invalid UTF-8 text as binary and -I
        # will suppress it. C locale keeps byte-oriented matching while -I
        # still excludes files containing binary NUL bytes.
        grep_env = dict(os.environ)
        grep_env["LC_ALL"] = "C"
        res = subprocess.run(
            ["grep", "-rnI", "-E", pattern, "--exclude-dir=__pycache__", "--exclude-dir=.git",
             "--exclude-dir=.venv", target],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=30, env=grep_env,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    lines = [ln for ln in res.stdout.splitlines() if ln.strip()]
    if res.returncode == 1 and not lines:
        return []
    if res.returncode != 0 or (res.returncode == 1 and lines):
        return None
    # GNU grep omits the filename when an explicitly named file is the
    # sole search target. Restore it so evidence remains traceable to the
    # exact source/test file, just as it is for directory-scoped searches.
    if os.path.isfile(target):
        lines = [f"{path}:{ln}" for ln in lines]
    # make paths repo-relative for stable evidence
    out = []
    for ln in lines[:max_hits]:
        out.append(ln.replace(repo_dir.rstrip("/") + "/", "", 1))
    return out


def reconcile(ob: Obligation, repo_dir: str,
              signatures: Optional[List[Signature]]) -> str:
    """Set source-anchor status from the current tree; semantic review is separate."""
    # Any new scan invalidates a prior semantic-review assertion and stale anchors.
    ob.recon_semantic_verified = False
    ob.recon_semantic_review_evidence = []
    ob.recon_evidence = []
    if not signatures:
        ob.recon_status = RECON_UNKNOWN
        ob.confidence = "inferred"
        ob.note = (ob.note + " ; no reconciliation signature — status is an inference").strip(" ;")
        return RECON_UNKNOWN
    hits, evidence = 0, []
    unavailable = []
    for sig in signatures:
        found = _grep(sig.pattern, repo_dir, sig.path)
        if found is None:
            unavailable.append(sig.label or sig.pattern)
            continue
        if found:
            hits += 1
            evidence.append(f"[{sig.label or sig.pattern}] " + found[0])
    if unavailable:
        ob.recon_status = RECON_UNKNOWN
        ob.recon_evidence = evidence
        ob.confidence = "inferred"
        ob.note = (ob.note + " ; reconciliation scan unavailable for: " +
                   ", ".join(unavailable)).strip(" ;")
        return RECON_UNKNOWN
    if hits == len(signatures):
        ob.recon_status = SIGNATURE_MATCHED
    elif hits > 0:
        ob.recon_status = PARTIAL
    else:
        ob.recon_status = MISSING
    ob.recon_evidence = evidence
    ob.confidence = "measured"
    return ob.recon_status


def make_reconciler(repo_dir: str,
                    signatures_map: Dict[str, List[Signature]]) -> Callable[[Obligation], str]:
    """A reconcile callback bound to a repo + signature map, for the extrapolator."""
    def _fn(ob: Obligation) -> str:
        return reconcile(ob, repo_dir, signatures_map.get(ob.key))
    return _fn


def dedup(obligations: List[Obligation]) -> Dict[str, Obligation]:
    """Merge obligations sharing a canonical key, accumulating provenance."""
    out: Dict[str, Obligation] = {}
    for ob in obligations:
        ex = out.get(ob.key)
        if ex is None:
            out[ob.key] = ob
        elif ob.provenance not in ex.provenance:
            ex.provenance += f"; {ob.provenance}"
    return out


def prune_false_dependencies(obligations: Dict[str, Obligation],
                             relationships: List[Relationship]) -> List[dict]:
    """Prune a dependency only when its target has an explicit semantic-review
    record in addition to matched source evidence. Returns the pruned edge notes."""
    pruned: List[dict] = []
    for rel in relationships:
        if rel.kind != "depends_on":
            continue
        tgt = obligations.get(rel.dst)
        if (tgt is not None and tgt.recon_status == REUSE_EXISTING
                and has_valid_reuse_review(tgt)):
            rel.kind = "reuses"
            rel.note = (f"dependency satisfied by existing mechanism "
                        f"({tgt.recon_evidence[0] if tgt.recon_evidence else 'reconciled'}); "
                        f"not net-new work")
            pruned.append({"src": rel.src, "dst": rel.dst, "reason": rel.note})
    return pruned


def summarize(obligations: Dict[str, Obligation]) -> Dict[str, List[str]]:
    buckets: Dict[str, List[str]] = {REUSE_EXISTING: [], SIGNATURE_MATCHED: [],
                                     PARTIAL: [], MISSING: [], RECON_UNKNOWN: []}
    for ob in obligations.values():
        if ob.recon_status == REUSE_EXISTING and not has_valid_reuse_review(ob):
            buckets[RECON_UNKNOWN].append(ob.key)
        else:
            buckets.setdefault(ob.recon_status, []).append(ob.key)
    return buckets
