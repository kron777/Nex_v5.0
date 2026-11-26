"""Regression detection between two snapshots.

A regression is a change in the WRONG direction between a baseline snapshot and a
later one: evidence got weaker, a verified connection fell back, a passive tool
turned active, or a tracked subject disappeared. This is observation, not
intervention — the Watcher flags regressions for review; it never edits NEX to
"fix" one.

Severities: `critical` (a safety-relevant reversal — e.g. a tool that was passive
is now active), `warning` (evidence weakened, a cycle dropped a level), `info`
(a subject went missing, which may just be scope).
"""
from __future__ import annotations

from typing import Dict, List

from .snapshot import _by_subject

# evidence strength, strongest -> weakest
_CLASS_RANK = {"measured": 4, "implemented": 3, "static": 2, "inferred": 1, "unknown": 0}
# runtime-graph cycle level strength
_LEVEL_RANK = {"runtime_observed": 3, "test_verified": 2, "source_implemented": 1, "hypothesis": 0}


def _finding(subject, kind, severity, before, after, note) -> dict:
    return {"subject": subject, "kind": kind, "severity": severity,
            "before": before, "after": after, "note": note}


def detect(before: dict, after: dict) -> List[dict]:
    """Return a list of regression findings comparing `before` -> `after` snapshots."""
    b, a = _by_subject(before), _by_subject(after)
    out: List[dict] = []

    # 1) subject disappeared
    for subj in sorted(set(b) - set(a)):
        out.append(_finding(subj, "subject_missing", "info",
                            b[subj].get("evidence_class"), None,
                            "subject present in baseline but absent now (scope change or loss)"))

    for subj in sorted(set(a) & set(b)):
        bc, ac = b[subj].get("evidence_class"), a[subj].get("evidence_class")
        # 2) evidence class weakened
        if _CLASS_RANK.get(ac, 0) < _CLASS_RANK.get(bc, 0):
            out.append(_finding(subj, "evidence_weakened", "warning", bc, ac,
                                f"evidence class fell {bc} -> {ac}"))

        # 3) safety: a tool that was passive is now active (adapters subjects)
        bd, ad = b[subj].get("data") or {}, a[subj].get("data") or {}
        if isinstance(bd, dict) and isinstance(ad, dict):
            bcls = bd.get("verified_class") or bd.get("class")
            acls = ad.get("verified_class") or ad.get("class")
            if bcls == "passive" and acls == "active":
                out.append(_finding(subj, "tool_passive_to_active", "critical",
                                    bcls, acls,
                                    "a tool classified passive is now active — side-effect review needed"))

        # 4) runtime-graph feedback cycles dropped a level
        if subj == "runtime_graph" and isinstance(bd, dict) and isinstance(ad, dict):
            out += _cycle_regressions(bd, ad)

        # 5) a gained blocking/dark modifier
        bm, am = b[subj].get("modifier"), a[subj].get("modifier")
        if bm != am and am in ("blocked", "dark"):
            out.append(_finding(subj, "modifier_gained", "warning", bm, am,
                                f"subject gained a '{am}' modifier"))
    return out


def _cycle_key(c: dict) -> frozenset:
    return frozenset(c.get("cycle", []))


def _cycle_regressions(before_data: dict, after_data: dict) -> List[dict]:
    out: List[dict] = []
    bcyc = {_cycle_key(c): c for c in before_data.get("feedback_cycles", [])}
    acyc = {_cycle_key(c): c for c in after_data.get("feedback_cycles", [])}
    for key, bc in bcyc.items():
        name = " -> ".join(bc.get("cycle", []))
        if key not in acyc:
            out.append(_finding(f"cycle:{name}", "cycle_missing", "warning",
                                bc.get("status"), None, "feedback cycle no longer detected"))
            continue
        ac = acyc[key]
        if _LEVEL_RANK.get(ac.get("status"), 0) < _LEVEL_RANK.get(bc.get("status"), 0):
            out.append(_finding(f"cycle:{name}", "cycle_level_dropped", "warning",
                                bc.get("status"), ac.get("status"),
                                "feedback-cycle confidence level dropped"))
    return out


def summarize(findings: List[dict]) -> Dict[str, int]:
    out = {"critical": 0, "warning": 0, "info": 0}
    for f in findings:
        out[f["severity"]] = out.get(f["severity"], 0) + 1
    return out
