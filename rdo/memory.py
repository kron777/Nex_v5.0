"""Development Pattern Memory + the learning loop (RDO spec v1.4 §24, Part VIII).

Two durable stores (append-only JSONL / per-cycle JSON, mirroring the Watcher's
ledger pattern — reuse, don't rebuild):

  * `PatternMemory` — reusable lessons from completed cycles. A pattern NEVER
    becomes a universal rule just because it worked once: confidence is bounded,
    exceptions are retained, and corroboration raises confidence only slowly.
  * `CycleStore` — full cycle records, so a cycle can be resumed and, later,
    compared against what actually happened.

The learning functions compare the RDO's PREDICTIONS against ACTUAL development
outcomes (did it miss obligations? over-expand? recommend unnecessary complexity?
mis-estimate effort?) and emit candidate lessons. `accuracy_series` reports
per-cycle metrics across time — but makes no acceleration claim until enough
cycles exist to support one.
"""
from __future__ import annotations

import dataclasses
import json
import os
from typing import Dict, List, Optional

from watcher.evidence import utc_now

from .model import (CycleRecord, EXECUTED_VERIFIED, IMPORTED_RETROSPECTIVE,
                    NATIVE_PLANNING, Pattern)

MIN_CYCLES_FOR_TREND = 3
CONFIDENCE_CAP = 0.9
CONFIDENCE_STEP = 0.1
_PATTERN_FIELDS = {f.name for f in dataclasses.fields(Pattern)}


def _confidence(base: float, observed_count: int, disconfirmed_count: int) -> float:
    """Confidence as a PURE, order-independent function of the deduplicated event
    counts, with a SINGLE clamp to [0, CONFIDENCE_CAP]. This is what makes confidence
    reconstructible deterministically from the event history (founder constraint)."""
    raw = base + CONFIDENCE_STEP * (observed_count - 1) - CONFIDENCE_STEP * disconfirmed_count
    return round(max(0.0, min(CONFIDENCE_CAP, raw)), 3)


class PatternMemory:
    def __init__(self, path: str) -> None:
        self.path = path
        self._current: Dict[str, Pattern] = {}
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    d = json.loads(line)
                    p = Pattern(**{k: v for k, v in d.items() if k in _PATTERN_FIELDS})
                    if not p.confirmations:                    # tolerate pre-field records
                        p.confirmations = [p.provenance]
                    self._recompute(p)                         # derive counts/confidence authoritatively
                    self._current[p.key] = p

    def add(self, pattern: Pattern) -> Pattern:
        """Add a new pattern, or CORROBORATE an existing one. Corroboration is
        deduplicated by provenance — the same source cannot raise confidence twice.
        Confidence is recomputed from the deduplicated counts, never mutated in place."""
        ex = self._current.get(pattern.key)
        if ex is None:
            pattern.base_confidence = min(pattern.confidence, CONFIDENCE_CAP)
            if not pattern.confirmations:
                pattern.confirmations = [pattern.provenance]
            self._current[pattern.key] = pattern
            cur = pattern
        else:
            if pattern.provenance not in ex.confirmations:      # dedup corroboration by source
                ex.confirmations.append(pattern.provenance)
            for x in pattern.exceptions:
                if x not in ex.exceptions:
                    ex.exceptions.append(x)
            cur = ex
        self._recompute(cur)
        self._append(cur)
        return cur

    def _recompute(self, p: Pattern) -> None:
        p.observed_count = len(p.confirmations)
        p.disconfirmed_count = len(p.disconfirmations)
        p.confidence = _confidence(p.base_confidence, p.observed_count, p.disconfirmed_count)

    @staticmethod
    def _reliable(p: Pattern) -> bool:
        """Reliable AS GUIDANCE only with positive confidence and net positive support.
        A decayed/zero pattern is retained (patterns()) but not offered (applicable())."""
        return p.confidence > 0.0 and p.observed_count > p.disconfirmed_count

    def _append(self, pattern: Pattern) -> None:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(pattern.to_dict(), default=str) + "\n")

    def refute(self, key: str, evidence: str) -> Optional[Pattern]:
        """Record DISCONFIRMING evidence: a later cycle disagreed. Deduplicated by
        evidence (the same evidence cannot penalize twice), lowers confidence via the
        pure recompute (floored at 0) and keeps the disconfirming note. The mechanism
        the prior version lacked — confidence was monotonic. No-op on an unknown key."""
        p = self._current.get(key)
        if p is None:
            return None
        if evidence in p.disconfirmations:                      # dedup disconfirmation
            return p
        p.disconfirmations.append(evidence)
        note = f"disconfirmed: {evidence}"
        if note not in p.exceptions:
            p.exceptions.append(note)
        self._recompute(p)
        self._append(p)
        return p

    def patterns(self) -> List[Pattern]:
        """ALL patterns, including decayed/zero-confidence ones (for inspection)."""
        return list(self._current.values())

    def applicable(self, context: str) -> List[Pattern]:
        """Patterns OFFERED as guidance: keyword-matched AND reliable. (Matching is
        keyword-based — a documented limitation; it cannot yet distinguish genuine
        transfer from superficial resemblance. Zero-confidence patterns are excluded
        here but remain in patterns() for inspection.)"""
        ctx = context.lower()
        return [p for p in self._current.values()
                if self._reliable(p)
                and (not p.applicability or any(w in ctx for w in p.applicability.lower().split()))]


class CycleStore:
    def __init__(self, dir_path: str) -> None:
        self.dir = dir_path
        os.makedirs(dir_path, exist_ok=True)

    def save(self, cycle: CycleRecord) -> str:
        p = os.path.join(self.dir, f"cycle_{cycle.id}.json")
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(cycle.to_dict(), fh, indent=2, default=str)
        return p

    def load(self, cycle_id: str) -> CycleRecord:
        with open(os.path.join(self.dir, f"cycle_{cycle_id}.json"), "r", encoding="utf-8") as fh:
            return CycleRecord(**json.load(fh))

    def list_ids(self) -> List[str]:
        return sorted(f[6:-5] for f in os.listdir(self.dir)
                      if f.startswith("cycle_") and f.endswith(".json"))


# ---- the learning loop ----

def record_actual(cycle: CycleRecord, actual: Dict) -> CycleRecord:
    """Attach real outcomes. `actual` keys (all optional):
        missed:[keys], unnecessary:[keys], reuse_wrong:[keys],
        effort_actual:<n>, notes:str, regressions:[...]"""
    cycle.actual = dict(actual)
    cycle.actual.setdefault("recorded_at", utc_now())
    return cycle


def compare(cycle: CycleRecord) -> Dict:
    """Predicted vs actual discrepancies (RDO §24)."""
    if cycle.actual is None:
        return {"status": "pending", "note": "no actual outcome recorded yet"}
    a = cycle.actual
    predicted_effort = cycle.predicted.get("effort")
    actual_effort = a.get("effort_actual")
    disc = {
        "under_expansion_missed": a.get("missed", []),            # necessary work we didn't discover
        "over_expansion_unnecessary": a.get("unnecessary", []),   # work we proposed but wasn't needed
        "inappropriate_reuse": a.get("reuse_wrong", []),          # claimed reuse that didn't hold
        "regressions": a.get("regressions", []),
        "effort_predicted": predicted_effort,
        "effort_actual": actual_effort,
        "effort_error": (None if predicted_effort is None or actual_effort is None
                         else round(actual_effort - predicted_effort, 3)),
    }
    return disc


def derive_lessons(cycle: CycleRecord, disc: Dict) -> List[Pattern]:
    """Turn discrepancies into candidate patterns (low starting confidence,
    provenance = this cycle). Never universal from one cycle."""
    out: List[Pattern] = []
    cid = cycle.id
    if disc.get("under_expansion_missed"):
        out.append(Pattern(
            key="under_expansion", provenance=f"cycle:{cid}",
            statement="Expansion missed necessary obligations in this domain; broaden the "
                      "relevant expansion rules.",
            applicability=cycle.objective, confidence=0.3,
            exceptions=["only observed once; may be domain-specific"]))
    if disc.get("over_expansion_unnecessary"):
        out.append(Pattern(
            key="over_expansion", provenance=f"cycle:{cid}",
            statement="Expansion proposed obligations that proved unnecessary; tighten stopping "
                      "rules / require stronger justification before packaging.",
            applicability=cycle.objective, confidence=0.3,
            exceptions=["a deferred item is not the same as an unnecessary one"]))
    if disc.get("inappropriate_reuse"):
        out.append(Pattern(
            key="reuse_signature_too_loose", provenance=f"cycle:{cid}",
            statement="A reconciliation signature matched a mechanism that did not actually "
                      "satisfy the obligation; make the signature stricter.",
            applicability=cycle.objective, confidence=0.3,
            exceptions=["partial matches should stay 'partial', not 'reuse'"]))
    ee = disc.get("effort_error")
    if ee is not None and abs(ee) >= 1:
        out.append(Pattern(
            key="effort_estimate_bias", provenance=f"cycle:{cid}",
            statement=f"Effort estimate was off by {ee}; recalibrate estimates for this work type.",
            applicability=cycle.objective, confidence=0.3,
            exceptions=["one data point is not a calibration"]))
    return out


def cycle_metrics(cycle: CycleRecord) -> Dict:
    """Comparable per-cycle measures (RDO §24). PROCESS measures are computable now
    from the cycle record; OUTCOME measures need recorded actuals and are `None`
    (pending) until then — never fabricated."""
    obligations = cycle.obligations
    discovered = len(obligations) or 1
    duplicates = sum(1 for o in obligations if ";" in str(o.get("provenance", "")))
    reuse_claims = len(cycle.reused)
    reuse_verified = cycle.verification.get("reuse_claims_backed_by_file_evidence")
    grounded = sum(1 for o in obligations if o.get("recon_status") in
                   ("reuse_existing", "missing", "partial"))
    d = compare(cycle) if cycle.actual is not None else {}
    missed = d.get("under_expansion_missed")
    return {
        "cycle": cycle.id,
        "kind": cycle.kind,
        "work_type": cycle.work_type,
        "outcome_complete": cycle.actual is not None,
        # PROCESS (now)
        "obligations_discovered": len(obligations),
        "duplicate_discovery_rate": round(duplicates / discovered, 3),
        "reuse_claims": reuse_claims,
        "reuse_accuracy": (round(reuse_verified / reuse_claims, 3)
                           if reuse_verified is not None and reuse_claims else None),
        "verification_success": cycle.verification.get("all_reuse_backed"),
        "expansion_grounded_fraction": round(grounded / discovered, 3),  # proxy for precision
        # OUTCOME (need actuals)
        "missed_obligation_count": (len(missed) if missed is not None else None),
        "prediction_error_effort": d.get("effort_error"),
        "rework": (len(d.get("regressions", [])) if cycle.actual is not None else None),
        "engineering_effort": (cycle.actual.get("effort_actual") if cycle.actual
                               else cycle.predicted.get("effort")),
        "outcome_status": ("recorded" if cycle.actual is not None else "pending"),
    }


_OUTCOME_MEASURES = ("missed_obligation_count", "prediction_error_effort", "rework")
_PROCESS_MEASURES = ("expansion_grounded_fraction", "duplicate_discovery_rate",
                     "reuse_accuracy", "verification_success")


def metrics_series(cycles: List[CycleRecord]) -> Dict:
    """The 8 comparable measures across cycles, with EXPLICIT denominators,
    comparability and missing values (founder constraint). Efficiency comparison
    uses ONLY executed+verified RDO-guided cycles — an imported retrospective is
    never counted as a completed cycle, and a native planning cycle with no
    executed work contributes process measures only. No acceleration trend is
    computed from incomplete or incomparable data."""
    rows = [cycle_metrics(c) for c in cycles]
    by_kind: Dict[str, int] = {}
    for r in rows:
        by_kind[r["kind"]] = by_kind.get(r["kind"], 0) + 1
    outcome_complete = [r for r in rows if r["outcome_complete"]]
    # efficiency-eligible: RDO ran it AND work was executed+verified (exclude imported)
    efficiency_eligible = [r for r in rows if r["kind"] == EXECUTED_VERIFIED and r["outcome_complete"]]
    # genuinely COMPARABLE = same work_type (a refactor is not a test-guard); group them,
    # and treat the largest same-type group as the real comparable set.
    comparable_by_work_type: Dict[str, List[str]] = {}
    for r in efficiency_eligible:
        comparable_by_work_type.setdefault(r["work_type"], []).append(r["cycle"])
    largest_comparable = max((len(v) for v in comparable_by_work_type.values()), default=0)

    def _denominator(measure: str) -> dict:
        contributing = [r for r in rows if r.get(measure) is not None]
        return {"contributing_cycles": [r["cycle"] for r in contributing],
                "n": len(contributing), "missing": len(rows) - len(contributing)}

    denominators = {m: _denominator(m) for m in (_PROCESS_MEASURES + _OUTCOME_MEASURES)}
    return {
        "measures": ["expansion_grounded_fraction (precision proxy)", "missed_obligation_count",
                     "duplicate_discovery_rate", "reuse_accuracy", "prediction_error_effort",
                     "rework", "engineering_effort", "verification_success"],
        "per_cycle": rows,
        "cycles_by_kind": by_kind,
        "comparability": {
            "process_measures_available_for": "every cycle the RDO ran (native + executed)",
            "outcome_measures_available_for": [r["cycle"] for r in outcome_complete],
            "completed_executed_cycles": [r["cycle"] for r in efficiency_eligible],
            "genuinely_comparable_by_work_type": comparable_by_work_type,
            "efficiency_comparison_pool": comparable_by_work_type.get("test_guard", []),
            "excluded_from_efficiency": {
                "imported_retrospective": [r["cycle"] for r in rows
                                           if r["kind"] == IMPORTED_RETROSPECTIVE],
                "native_planning_no_actuals": [r["cycle"] for r in rows
                                               if r["kind"] == NATIVE_PLANNING and not r["outcome_complete"]],
            },
        },
        "denominators": denominators,
        "completed_executed_cycles": len(efficiency_eligible),
        "largest_comparable_group": largest_comparable,
        "effort_unit": ("obligation/test-file count (coarse). Elapsed active engineering time and "
                        "verification effort are NOT reliably available here (work spans interrupted "
                        "turns), so they are recorded as missing rather than estimated."),
        "trend_claim": (
            f"NO efficiency/acceleration claim: the largest genuinely-comparable (same work_type) "
            f"group is {largest_comparable} cycle(s); need >= {MIN_CYCLES_FOR_TREND}. Completed "
            f"executed cycles ({len(efficiency_eligible)}) span >1 work_type and are not all comparable."
            if largest_comparable < MIN_CYCLES_FOR_TREND
            else f"the largest comparable (same work_type) group is {largest_comparable} cycles — enough "
                 f"to BEGIN assessing a trend; report values, not hype. n is small; not statistical proof."),
        "note": "process measures every cycle; outcome measures need executed work + recorded "
                "actuals; efficiency compares only executed+verified cycles of comparable kind.",
    }


def transfer_observations(cycles: List[CycleRecord]) -> Dict:
    """Record cross-cycle knowledge-transfer OBSERVATIONS explicitly, without
    inflating any score (founder constraint). Reports each executed cycle's
    predicted-vs-actual and whether the prediction matched; states plainly that
    these are observed instances, not proof of a trend, and that transfer currently
    lives in the reasoning, not autonomously in the keyword matcher."""
    execs = [c for c in cycles if c.kind == EXECUTED_VERIFIED and c.actual is not None]
    rows = []
    for c in execs:
        d = compare(c)
        matched = d.get("effort_error") == 0 and not d.get("under_expansion_missed")
        rows.append({
            "cycle": c.id,
            "predicted_effort": c.predicted.get("effort"),
            "actual_effort": c.actual.get("effort_actual"),
            "effort_error": d.get("effort_error"),
            "missed_obligations": len(d.get("under_expansion_missed") or []),
            "prediction_matched": matched,
        })
    return {
        "executed_cycles": rows,
        "observation": "Cycle 1 missed an obligation (actual effort exceeded prediction); later "
                       "cycles matched prediction. An OBSERVED instance of cross-cycle knowledge "
                       "transfer — NOT proof of a general improvement trend.",
        "caveat": "Transfer is applied in the reasoning (reconcile-first + anticipate-the-hidden-"
                  "obligation), not yet driven autonomously by Pattern Memory's keyword matcher. "
                  "n is small; even three matched cycles are not statistical proof. Predictions "
                  "are never rewritten after the fact.",
    }


def accuracy_series(cycles: List[CycleRecord]) -> Dict:
    """Per-cycle learning metrics across time. Reports the series; makes NO
    acceleration claim until there are enough cycles to support one."""
    rows: List[Dict] = []
    for c in cycles:
        if c.actual is None:
            rows.append({"cycle": c.id, "status": "pending"})
            continue
        d = compare(c)
        rows.append({
            "cycle": c.id,
            "missed": len(d["under_expansion_missed"]),
            "unnecessary": len(d["over_expansion_unnecessary"]),
            "inappropriate_reuse": len(d["inappropriate_reuse"]),
            "effort_error": d["effort_error"],
        })
    completed = [r for r in rows if r.get("status") != "pending"]
    return {
        "series": rows,
        "completed_cycles": len(completed),
        "trend_claim": ("insufficient data — need at least "
                        f"{MIN_CYCLES_FOR_TREND} completed cycles; no acceleration claimed"
                        if len(completed) < MIN_CYCLES_FOR_TREND
                        else "enough cycles to begin assessing a trend (report values, not hype)"),
    }
