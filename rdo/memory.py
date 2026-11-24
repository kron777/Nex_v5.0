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

import json
import os
from typing import Dict, List, Optional

from watcher.evidence import utc_now

from .model import (CycleRecord, EXECUTED_VERIFIED, IMPORTED_RETROSPECTIVE,
                    NATIVE_PLANNING, Pattern)

MIN_CYCLES_FOR_TREND = 3
CONFIDENCE_CAP = 0.9


class PatternMemory:
    def __init__(self, path: str) -> None:
        self.path = path
        self._current: Dict[str, Pattern] = {}
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line:
                        d = json.loads(line)
                        self._current[d["key"]] = Pattern(**d)

    def add(self, pattern: Pattern) -> Pattern:
        """Add or corroborate once per recorded provenance token.

        Exact cycle replay is idempotent. A new recorded origin is retained and
        counted once, but distinct provenance alone does not prove independent
        underlying evidence; that interpretation remains a human judgement.
        """
        incoming = [x.strip() for x in str(pattern.provenance).split(";") if x.strip()]
        ex = self._current.get(pattern.key)
        if ex is not None:
            existing = [x.strip() for x in str(ex.provenance).split(";") if x.strip()]
            new = [x for x in incoming if x not in existing]
            for x in pattern.exceptions:
                if x not in ex.exceptions:
                    ex.exceptions.append(x)
            if not new:
                return ex
            ex.provenance = "; ".join(existing + new)
            ex.observed_count += 1
            ex.confidence = min(CONFIDENCE_CAP, round(ex.confidence + 0.1, 3))
            cur = ex
        else:
            pattern.confidence = min(pattern.confidence, CONFIDENCE_CAP)
            pattern.provenance = "; ".join(incoming)
            self._current[pattern.key] = pattern
            cur = pattern
        self._append(cur)
        return cur

    def _append(self, pattern: Pattern) -> None:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(pattern.to_dict(), default=str) + "\n")

    def patterns(self) -> List[Pattern]:
        return list(self._current.values())

    def applicable(self, context: str) -> List[Pattern]:
        ctx = context.lower()
        return [p for p in self._current.values()
                if not p.applicability or any(w in ctx for w in p.applicability.lower().split())]


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
    actual_effort = (cycle.actual.get("effort_actual")
                     if cycle.actual is not None else None)
    return {
        "cycle": cycle.id,
        "kind": cycle.kind,
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
        "engineering_effort": actual_effort,
        "predicted_effort": cycle.predicted.get("effort"),
        "outcome_status": ("recorded" if cycle.actual is not None else "pending"),
    }


_OUTCOME_MEASURES = ("missed_obligation_count", "prediction_error_effort", "rework",
                     "engineering_effort")
_PROCESS_MEASURES = ("expansion_grounded_fraction", "duplicate_discovery_rate",
                     "reuse_accuracy", "verification_success")
_MEASURE_KEYS = ("expansion_grounded_fraction", "missed_obligation_count",
                 "duplicate_discovery_rate", "reuse_accuracy", "prediction_error_effort",
                 "rework", "engineering_effort", "verification_success")
_MEASURE_LABELS = {
    "expansion_grounded_fraction": "expansion_grounded_fraction (precision proxy)",
    "missed_obligation_count": "missed_obligation_count",
    "duplicate_discovery_rate": "duplicate_discovery_rate",
    "reuse_accuracy": "reuse_accuracy",
    "prediction_error_effort": "prediction_error_effort",
    "rework": "rework",
    "engineering_effort": "engineering_effort (actual only)",
    "verification_success": "verification_success",
}


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

    def _denominator(measure: str) -> dict:
        contributing = [r for r in rows if r.get(measure) is not None]
        return {"contributing_cycles": [r["cycle"] for r in contributing],
                "n": len(contributing), "missing": len(rows) - len(contributing)}

    denominators = {m: _denominator(m) for m in _MEASURE_KEYS}
    return {
        "measures": [_MEASURE_LABELS[m] for m in _MEASURE_KEYS],
        "measure_keys": list(_MEASURE_KEYS),
        "per_cycle": rows,
        "cycles_by_kind": by_kind,
        "comparability": {
            "process_measures_available_for": "every cycle the RDO ran (native + executed)",
            "outcome_measures_available_for": [r["cycle"] for r in outcome_complete],
            "efficiency_comparison_pool": [r["cycle"] for r in efficiency_eligible],
            "excluded_from_efficiency": {
                "imported_retrospective": [r["cycle"] for r in rows
                                           if r["kind"] == IMPORTED_RETROSPECTIVE],
                "native_planning_no_actuals": [r["cycle"] for r in rows
                                               if r["kind"] == NATIVE_PLANNING and not r["outcome_complete"]],
            },
        },
        "denominators": denominators,
        "efficiency_eligible_cycles": len(efficiency_eligible),
        "trend_claim": (
            f"NO efficiency/acceleration claim: only {len(efficiency_eligible)} executed+verified "
            f"RDO-guided cycle(s); need >= {MIN_CYCLES_FOR_TREND} comparable cycles. An imported "
            f"retrospective and a planning-only cycle are NOT comparable to a completed cycle."
            if len(efficiency_eligible) < MIN_CYCLES_FOR_TREND
            else "enough comparable executed+verified cycles to begin assessing a trend; report "
                 "values, not hype"),
        "note": "process measures every cycle; outcome measures need executed work + recorded "
                "actuals; efficiency compares only executed+verified cycles of comparable kind.",
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
