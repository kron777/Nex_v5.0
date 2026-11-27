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
import math
import os
import re
from typing import Dict, List, Optional

from watcher.evidence import utc_now

from .model import (CycleRecord, EXECUTED_VERIFIED, IMPORTED_RETROSPECTIVE,
                    NATIVE_PLANNING, RECON_UNKNOWN, REUSE_EXISTING,
                    SIGNATURE_MATCHED, PARTIAL, MISSING, Pattern,
                    has_valid_reuse_review, _has_traceable_evidence)

MIN_CYCLES_FOR_TREND = 3
CONFIDENCE_CAP = 0.9


def _bounded_confidence(value) -> float:
    """Return a finite confidence in [0.0, CONFIDENCE_CAP].

    Finite numeric values outside the range are clamped. Booleans, non-numeric
    values, and non-finite floats are rejected rather than persisted as evidence.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("pattern confidence must be a finite number")
    if isinstance(value, int):
        # Avoid float overflow for arbitrarily large Python integers.
        if value <= 0:
            return 0.0
        if value >= CONFIDENCE_CAP:
            return CONFIDENCE_CAP
        return float(value)
    if not math.isfinite(value):
        raise ValueError("pattern confidence must be a finite number")
    return max(0.0, min(value, CONFIDENCE_CAP))


CONFIDENCE_CAP = 0.9
CONFIDENCE_STEP = 0.1


def _confidence(base: float, observed_count: int, disconfirmed_count: int) -> float:
    """Pure, order-independent heuristic confidence from deduplicated event counts."""
    base = _bounded_confidence(base)
    if (isinstance(observed_count, bool) or not isinstance(observed_count, int)
            or observed_count < 0):
        raise ValueError("pattern observed_count must be a non-negative integer")
    if (isinstance(disconfirmed_count, bool) or not isinstance(disconfirmed_count, int)
            or disconfirmed_count < 0):
        raise ValueError("pattern disconfirmed_count must be a non-negative integer")
    raw = base + CONFIDENCE_STEP * (observed_count - 1) - CONFIDENCE_STEP * disconfirmed_count
    return _bounded_confidence(round(raw, 3))




class PatternMemory:
    """Append-only pattern memory with deduplicated corroboration and refutation.

    The event lists are authoritative. Confidence is recomputed from bounded
    base confidence and event counts. Every write revalidates mutable aliases.
    """
    def __init__(self, path: str) -> None:
        self.path = path
        self._current: Dict[str, Pattern] = {}
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as fh:
                lines = fh.readlines()
            fields = {f.name for f in dataclasses.fields(Pattern)}
            for index, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    if index == len(lines) - 1:
                        continue
                    raise
                p = Pattern(**{k: v for k, v in data.items() if k in fields})
                old_confidence = _bounded_confidence(p.confidence)
                if "base_confidence" not in data:
                    tokens = [x.strip() for x in str(p.provenance).split(";") if x.strip()]
                    if not p.confirmations:
                        p.confirmations = (tokens if len(tokens) == p.observed_count
                                           else ([p.provenance] if p.provenance else []))
                    p.base_confidence = _bounded_confidence(
                        old_confidence - CONFIDENCE_STEP * max(0, p.observed_count - 1)
                                    + CONFIDENCE_STEP * p.disconfirmed_count
                    )
                else:
                    p.base_confidence = _bounded_confidence(p.base_confidence)
                if not p.confirmations and p.provenance:
                    p.confirmations = [p.provenance]
                p.confirmations = self._clean_events(p.confirmations, "confirmation")
                p.disconfirmations = self._clean_events(p.disconfirmations, "disconfirmation")
                self._recompute(p)
                previous = self._current.get(p.key)
                if previous is not None:
                    if previous.exact_scope != p.exact_scope:
                        raise ValueError("persisted pattern key collision has conflicting scope modes")
                    if p.exact_scope:
                        old_scope = " ".join(previous.applicability.split()).lower()
                        new_scope = " ".join(p.applicability.split()).lower()
                        if old_scope != new_scope:
                            raise ValueError("persisted pattern key collision has conflicting exact scopes")
                self._current[p.key] = p

    @staticmethod
    def _clean_events(events, label: str) -> List[str]:
        if not isinstance(events, list):
            raise ValueError(f"pattern {label} events must be a list")
        out = []
        for event in events:
            if not isinstance(event, str) or not event.strip():
                raise ValueError(f"pattern {label} events must be non-empty strings")
            event = event.strip()
            if event not in out:
                out.append(event)
        return out

    @staticmethod
    def _reliable(pattern: Pattern) -> bool:
        return pattern.confidence > 0.0 and pattern.observed_count > pattern.disconfirmed_count

    def _recompute(self, pattern: Pattern) -> None:
        pattern.base_confidence = _bounded_confidence(pattern.base_confidence)
        pattern.confirmations = self._clean_events(pattern.confirmations, "confirmation")
        pattern.disconfirmations = self._clean_events(pattern.disconfirmations, "disconfirmation")
        pattern.observed_count = len(pattern.confirmations)
        pattern.disconfirmed_count = len(pattern.disconfirmations)
        pattern.confidence = _confidence(
            pattern.base_confidence, pattern.observed_count, pattern.disconfirmed_count
        )

    def add(self, pattern: Pattern) -> Pattern:
        """Add or corroborate one provenance event. Exact replay is idempotent."""
        if not isinstance(pattern.exact_scope, bool):
            raise ValueError("pattern exact_scope must be a boolean")
        if pattern.exact_scope and (
            not isinstance(pattern.applicability, str) or not pattern.applicability.strip()
        ):
            raise ValueError("exact-scope patterns require a non-blank applicability")
        incoming_confidence = _bounded_confidence(pattern.confidence)
        incoming_base = _bounded_confidence(pattern.base_confidence)
        incoming = [x.strip() for x in str(pattern.provenance).split(";") if x.strip()]
        if not incoming:
            raise ValueError("pattern provenance must contain a non-empty source")
        existing = self._current.get(pattern.key)
        if existing is not None:
            # A key collision must never widen or silently change an exact-scope lesson.
            if not isinstance(existing.exact_scope, bool):
                raise ValueError("existing pattern exact_scope must be a boolean")
            if existing.exact_scope != pattern.exact_scope:
                raise ValueError("pattern key collision has conflicting scope modes")
            if existing.exact_scope:
                if (not isinstance(existing.applicability, str)
                        or not existing.applicability.strip()):
                    raise ValueError("existing exact-scope pattern requires non-blank applicability")
                old_scope = " ".join(existing.applicability.split()).lower()
                new_scope = " ".join(pattern.applicability.split()).lower()
                if old_scope != new_scope:
                    raise ValueError("pattern key collision has conflicting exact scopes")
        if existing is None:
            if incoming_base == 0.3 and incoming_confidence != 0.3:
                incoming_base = incoming_confidence
            pattern.base_confidence = incoming_base
            if not pattern.confirmations:
                pattern.confirmations = ["; ".join(incoming)]
            self._recompute(pattern)
            self._current[pattern.key] = pattern
            self._append(pattern)
            return pattern

        # Validate all caller-visible mutable state before changing it.
        original_confidence = existing.confidence
        normalized_confidence = _bounded_confidence(original_confidence)
        normalized_base = _bounded_confidence(existing.base_confidence)
        confidence_normalized = original_confidence != normalized_confidence
        if not isinstance(existing.provenance, str):
            raise ValueError("pattern provenance must be a string")
        old_origins = [x.strip() for x in existing.provenance.split(";") if x.strip()]
        old_confirmations = self._clean_events(existing.confirmations, "confirmation")
        old_disconfirmations = self._clean_events(existing.disconfirmations, "disconfirmation")
        new_origins = [x for x in incoming if x not in old_origins]
        next_confirmations = list(old_confirmations)
        if new_origins:
            event = "; ".join(new_origins)
            if event not in next_confirmations:
                next_confirmations.append(event)
        next_exceptions = list(existing.exceptions)
        exception_set_before = list(next_exceptions)
        for item in pattern.exceptions:
            if item not in next_exceptions:
                next_exceptions.append(item)
        exceptions_changed = next_exceptions != exception_set_before

        # A finite out-of-range alias is normalized at the public boundary. Treat
        # the clamped value as the new base so it remains durable on idempotent replay.
        if confidence_normalized:
            normalized_base = normalized_confidence
        existing.base_confidence = normalized_base
        existing.confirmations = next_confirmations
        existing.disconfirmations = old_disconfirmations
        if new_origins:
            existing.provenance = "; ".join(old_origins + new_origins)
        existing.exceptions = next_exceptions
        self._recompute(existing)
        if new_origins or exceptions_changed or confidence_normalized:
            self._append(existing)
        return existing

    def _append(self, pattern: Pattern) -> None:
        pattern.confidence = _bounded_confidence(pattern.confidence)
        pattern.base_confidence = _bounded_confidence(pattern.base_confidence)
        pattern.confirmations = self._clean_events(pattern.confirmations, "confirmation")
        pattern.disconfirmations = self._clean_events(pattern.disconfirmations, "disconfirmation")
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(pattern.to_dict(), default=str) + "\n")

    def refute(self, key: str, evidence: str) -> Optional[Pattern]:
        """Record new disconfirming evidence; duplicate evidence cannot penalize twice."""
        pattern = self._current.get(key)
        if pattern is None:
            return None
        _bounded_confidence(pattern.confidence)  # validate aliases before mutation
        base = _bounded_confidence(pattern.base_confidence)
        confirmations = self._clean_events(pattern.confirmations, "confirmation")
        disconfirmations = self._clean_events(pattern.disconfirmations, "disconfirmation")
        if not isinstance(evidence, str) or not evidence.strip():
            raise ValueError("disconfirming evidence must be a non-empty string")
        evidence = evidence.strip()
        if evidence in disconfirmations:
            return pattern
        exceptions = list(pattern.exceptions)
        note = f"disconfirmed: {evidence}"
        if note not in exceptions:
            exceptions.append(note)
        pattern.base_confidence = base
        pattern.confirmations = confirmations
        pattern.disconfirmations = disconfirmations + [evidence]
        pattern.exceptions = exceptions
        self._recompute(pattern)
        self._append(pattern)
        return pattern

    def patterns(self) -> List[Pattern]:
        return list(self._current.values())

    def applicable(self, context: str) -> List[Pattern]:
        ctx = " ".join(context.split()).lower()
        for pattern in self._current.values():
            if not isinstance(pattern.exact_scope, bool):
                raise ValueError("pattern exact_scope must be a boolean")
            if pattern.exact_scope and (
                not isinstance(pattern.applicability, str) or not pattern.applicability.strip()
            ):
                raise ValueError("exact-scope patterns require a non-blank applicability")
        return [p for p in self._current.values()
                if self._reliable(p)
                and (ctx == " ".join(p.applicability.split()).lower() if p.exact_scope is True else
                     (not p.applicability
                      or any(w in ctx for w in p.applicability.lower().split())))]


class CycleStore:
    def __init__(self, dir_path: str) -> None:
        self.dir = dir_path
        os.makedirs(dir_path, exist_ok=True)

    def _cycle_path(self, cycle_id: str) -> str:
        # Cycle IDs become filenames. Keep them portable and prevent caller-
        # supplied separators, traversal components, and unbounded names.
        if (not isinstance(cycle_id, str) or
                not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", cycle_id)):
            raise ValueError("cycle id must be 1-128 portable filename characters")
        return os.path.join(self.dir, f"cycle_{cycle_id}.json")

    def save(self, cycle: CycleRecord) -> str:
        p = self._cycle_path(cycle.id)
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(cycle.to_dict(), fh, indent=2, default=str)
        return p

    def load(self, cycle_id: str) -> CycleRecord:
        with open(self._cycle_path(cycle_id), "r", encoding="utf-8") as fh:
            return CycleRecord(**json.load(fh))

    def list_ids(self) -> List[str]:
        return sorted(f[6:-5] for f in os.listdir(self.dir)
                      if f.startswith("cycle_") and f.endswith(".json"))


# ---- the learning loop ----

def _valid_effort(value) -> bool:
    """Accept only non-negative numbers safely representable as finite floats."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(value) and value >= 0
    except (OverflowError, TypeError, ValueError):
        # Python integers are unbounded; float-based metrics must fail closed
        # rather than crash when an integer is too large to convert.
        return False


def record_actual(cycle: CycleRecord, actual: Dict) -> CycleRecord:
    """Attach real outcomes. `actual` keys (all optional):
        missed:[keys], unnecessary:[keys], reuse_wrong:[keys],
        effort_actual:<n>, notes:str, regressions:[...]"""
    if "effort_actual" in actual:
        effort = actual["effort_actual"]
        if not _valid_effort(effort):
            raise ValueError("effort_actual must be a finite, non-negative number")
    for field in ("missed", "unnecessary", "reuse_wrong", "regressions"):
        if field in actual and not isinstance(actual[field], list):
            raise ValueError(f"{field} must be a list when reported")
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
    if not _valid_effort(predicted_effort):
        predicted_effort = None
    if not _valid_effort(actual_effort):
        actual_effort = None
    disc = {
        "under_expansion_missed": a.get("missed"),            # None = not reported; [] = reported zero
        "over_expansion_unnecessary": a.get("unnecessary"),
        "inappropriate_reuse": a.get("reuse_wrong"),
        "regressions": a.get("regressions"),
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
    if (_has_traceable_evidence(disc.get("regressions"))
            and isinstance(cycle.objective, str) and cycle.objective.strip()):
        out.append(Pattern(
            key="regression_risk:" + "_".join(str(cycle.objective).lower().split()),
            provenance=f"cycle:{cid}",
            statement="A development outcome recorded a regression in this objective; require "
                      "explicit regression analysis and evidence before treating a similar "
                      "change as safe.",
            applicability=cycle.objective, confidence=0.3, exact_scope=True,
            exceptions=["one regression is scoped evidence, not a universal prohibition"]))
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
    discovered = len(obligations)
    duplicates = sum(1 for o in obligations if ";" in str(o.get("provenance", "")))
    reuse_claims = len(cycle.reused)
    # Legacy records without an explicit signature-match count remain unknown;
    # a historical reuse claim is not retroactively treated as a signature match.
    if "signature_matches" in cycle.verification:
        signature_matches = cycle.verification["signature_matches"]
    else:
        legacy_matches = cycle.signature_matches
        if (isinstance(legacy_matches, list) and
                all(isinstance(item, str) and item.strip() for item in legacy_matches)):
            signature_matches = len(legacy_matches) if legacy_matches else None
        else:
            signature_matches = None
    if (not isinstance(signature_matches, int) or isinstance(signature_matches, bool)
            or signature_matches < 0):
        signature_matches = None
    signature_backed = cycle.verification.get(
        "signature_matches_backed_by_file_evidence")
    if (not isinstance(signature_backed, int) or isinstance(signature_backed, bool)
            or signature_backed < 0 or signature_matches is None
            or signature_backed > signature_matches):
        # Inconsistent counts are unknown, never a coverage ratio above 100%.
        signature_backed = None
    coverage_complete = cycle.verification.get(
        "all_signature_matches_have_file_evidence")
    if (not isinstance(coverage_complete, bool) or signature_matches is None
            or signature_matches <= 0 or signature_backed is None
            or coverage_complete != (signature_backed == signature_matches)):
        coverage_complete = None
    def _has_completed_reconciliation(obligation: dict) -> bool:
        status = obligation.get("recon_status", RECON_UNKNOWN)
        if status == REUSE_EXISTING:
            return has_valid_reuse_review(obligation)
        return status in (SIGNATURE_MATCHED, MISSING, PARTIAL)

    reconciled = sum(1 for o in obligations if _has_completed_reconciliation(o))
    d = compare(cycle) if cycle.actual is not None else {}
    missed = d.get("under_expansion_missed")
    raw_actual_effort = (cycle.actual.get("effort_actual")
                          if cycle.actual is not None else None)
    actual_effort = raw_actual_effort if _valid_effort(raw_actual_effort) else None
    raw_predicted_effort = cycle.predicted.get("effort")
    predicted_effort = (raw_predicted_effort
                        if _valid_effort(raw_predicted_effort) else None)
    actual_field_map = {
        "missed": "under_expansion_missed",
        "unnecessary": "over_expansion_unnecessary",
        "reuse_wrong": "inappropriate_reuse",
        "regressions": "regressions",
    }
    outcome_fields_reported = [
        field for field, metric in actual_field_map.items()
        if cycle.actual is not None and isinstance(d.get(metric), list)
    ]
    outcome_complete = cycle.actual is not None and len(outcome_fields_reported) == len(actual_field_map)
    return {
        "cycle": cycle.id,
        "kind": cycle.kind,
        "outcome_recorded": cycle.actual is not None,
        "outcome_fields_reported": outcome_fields_reported,
        "outcome_complete": outcome_complete,
        # PROCESS (now)
        "obligations_discovered": len(obligations),
        "duplicate_discovery_rate": (round(duplicates / discovered, 3) if discovered else None),
        "reuse_claims": reuse_claims,
        "signature_matches": signature_matches,
        "signature_evidence_coverage": (
            round(signature_backed / signature_matches, 3)
            if isinstance(signature_matches, (int, float)) and signature_matches > 0
            and isinstance(signature_backed, (int, float)) else None),
        "signature_evidence_coverage_complete": coverage_complete,
        "reconciliation_status_coverage": (round(reconciled / discovered, 3) if discovered else None),  # completed scan/review status, not precision
        # OUTCOME (need actuals)
        "missed_obligation_count": (len(missed) if isinstance(missed, list) else None),
        "prediction_error_effort": (
            d.get("effort_error") if actual_effort is not None and
            predicted_effort is not None else None),
        "rework": (len(d["regressions"]) if isinstance(d.get("regressions"), list) else None),
        "engineering_effort": actual_effort,
        "predicted_effort": predicted_effort,
        "outcome_status": ("complete" if outcome_complete else
                           "partial" if cycle.actual is not None else "pending"),
    }


_MEASURE_KEYS = ("reconciliation_status_coverage", "missed_obligation_count",
                 "duplicate_discovery_rate", "signature_evidence_coverage", "prediction_error_effort",
                 "rework", "engineering_effort", "signature_evidence_coverage_complete")
_MEASURE_LABELS = {
    "reconciliation_status_coverage": "reconciliation_status_coverage (fraction with a completed reconciliation status; not precision)",
    "missed_obligation_count": "missed_obligation_count",
    "duplicate_discovery_rate": "duplicate_discovery_rate",
    "signature_evidence_coverage": "signature_evidence_coverage (configured source-anchor coverage, not semantic accuracy)",
    "prediction_error_effort": "prediction_error_effort",
    "rework": "rework",
    "engineering_effort": "engineering_effort (actual only)",
    "signature_evidence_coverage_complete": "signature_evidence_coverage_complete (all signature matches have file anchors; not execution success)",
}


def metrics_series(cycles: List[CycleRecord]) -> Dict:
    """Report process/outcome measures while restricting efficiency comparisons to
    the largest like-for-like executed engineering-pattern group.

    Executed records are not automatically comparable merely because they are
    completed. Native plans and imported retrospectives remain outside the
    execution pool; incomplete outcome fields remain UNKNOWN.
    """
    rows = [cycle_metrics(c) for c in cycles]
    by_kind: Dict[str, int] = {}
    for row in rows:
        by_kind[row["kind"]] = by_kind.get(row["kind"], 0) + 1

    outcome_complete = [row for row in rows if row["outcome_complete"]]
    completed_executed = [
        cycle for cycle in cycles
        if cycle.kind == EXECUTED_VERIFIED and cycle.actual is not None
    ]

    # Engineering-pattern attribution is the explicit comparability boundary.
    # Unspecified patterns are intentionally isolated rather than pooled.
    comparable_groups: Dict[str, List[str]] = {}
    for cycle in completed_executed:
        pattern = cycle.engineering_pattern
        group_key = pattern if pattern and pattern != "unspecified" else f"unclassified:{cycle.id}"
        comparable_groups.setdefault(group_key, []).append(cycle.id)

    largest_comparable_group = max(
        (len(group) for group in comparable_groups.values()), default=0
    )
    largest_groups = sorted(
        key for key, group in comparable_groups.items()
        if len(group) == largest_comparable_group and largest_comparable_group > 0
    )
    # If different patterns tie for largest, do not combine them or choose
    # one silently; the efficiency pool stays empty pending a clearer comparison.
    selected_group = largest_groups[0] if len(largest_groups) == 1 else None
    row_by_id = {row["cycle"]: row for row in rows}
    selected_ids = comparable_groups.get(selected_group, []) if selected_group else []
    efficiency_pool = [
        cycle_id for cycle_id in selected_ids
        if row_by_id[cycle_id]["outcome_complete"]
        and _valid_effort(row_by_id[cycle_id]["engineering_effort"])
    ]
    efficiency_ids = set(efficiency_pool)

    def _denominator(measure: str) -> dict:
        contributing = [row for row in rows if row.get(measure) is not None]
        return {
            "contributing_cycles": [row["cycle"] for row in contributing],
            "n": len(contributing),
            "missing": len(rows) - len(contributing),
        }

    denominators = {measure: _denominator(measure) for measure in _MEASURE_KEYS}
    return {
        "measures": [_MEASURE_LABELS[measure] for measure in _MEASURE_KEYS],
        "measure_keys": list(_MEASURE_KEYS),
        "per_cycle": rows,
        "cycles_by_kind": by_kind,
        "comparability": {
            "process_measures_available_for": "every cycle the RDO ran (native + executed)",
            "outcome_measures_available_for": [row["cycle"] for row in outcome_complete],
            "genuinely_comparable_by_engineering_pattern": comparable_groups,
            "selected_efficiency_comparison_group": selected_group,
            "efficiency_comparison_pool": efficiency_pool,
            "excluded_from_efficiency": {
                "imported_retrospective": [
                    row["cycle"] for row in rows if row["kind"] == IMPORTED_RETROSPECTIVE
                ],
                "native_planning_no_actuals": [
                    row["cycle"] for row in rows
                    if row["kind"] == NATIVE_PLANNING and not row["outcome_complete"]
                ],
                "executed_outside_selected_group_or_incomplete": [
                    cycle.id for cycle in completed_executed if cycle.id not in efficiency_ids
                ],
            },
        },
        "denominators": denominators,
        "completed_executed_cycles": len(completed_executed),
        "largest_comparable_group": largest_comparable_group,
        "efficiency_eligible_cycles": len(efficiency_pool),
        "trend_claim": (
            f"NO efficiency/acceleration claim: only {len(efficiency_pool)} like-for-like "
            f"executed+verified RDO-guided cycle(s); need >= {MIN_CYCLES_FOR_TREND} comparable "
            "cycles. Imported retrospectives, planning-only cycles, other engineering patterns "
            "and incomplete outcomes are NOT pooled."
            if len(efficiency_pool) < MIN_CYCLES_FOR_TREND
            else "enough like-for-like executed+verified cycles to begin assessing a trend; "
                 "report values, not hype"
        ),
        "note": "Process measures remain available across cycles; outcome measures need recorded "
                "actuals; efficiency compares only the largest unambiguous like-for-like executed "
                "engineering-pattern group with complete outcomes and valid effort.",
    }



def accuracy_series(cycles: List[CycleRecord]) -> Dict:
    """Per-cycle series that distinguishes pending, partial and complete outcomes."""
    rows: List[Dict] = []
    for c in cycles:
        if c.actual is None:
            rows.append({"cycle": c.id, "status": "pending"})
            continue
        d = compare(c)
        required = ("under_expansion_missed", "over_expansion_unnecessary",
                    "inappropriate_reuse", "regressions")
        complete = all(isinstance(d.get(k), list) for k in required)
        rows.append({
            "cycle": c.id,
            "status": "complete" if complete else "partial",
            "missed": (len(d["under_expansion_missed"])
                       if isinstance(d.get("under_expansion_missed"), list) else None),
            "unnecessary": (len(d["over_expansion_unnecessary"])
                            if isinstance(d.get("over_expansion_unnecessary"), list) else None),
            "inappropriate_reuse": (len(d["inappropriate_reuse"])
                                    if isinstance(d.get("inappropriate_reuse"), list) else None),
            "effort_error": d.get("effort_error"),
            "unknown_measures": [k for k in required if not isinstance(d.get(k), list)],
        })
    completed = [r for r in rows if r.get("status") == "complete"]
    return {
        "series": rows,
        "completed_cycles": len(completed),
        "trend_claim": ("insufficient data — need at least "
                        f"{MIN_CYCLES_FOR_TREND} completed cycles; no acceleration claimed"
                        if len(completed) < MIN_CYCLES_FOR_TREND
                        else "enough cycles to begin assessing a trend (report values, not hype)"),
    }

# Stage 6 evidence-provenance learning loop; outcomes remain UNKNOWN until recorded.

def comparability_assessment(cycles: List[CycleRecord]) -> Dict:
    """A lightweight per-cycle comparability signature (founder item 4). Sharing a coarse
    work_type does NOT make objectives comparable; this derives the dimensions that matter
    and groups by engineering_pattern. Better a small honest comparison group than a large
    artificial one."""
    rows = []
    for c in cycles:
        if c.kind != EXECUTED_VERIFIED or c.actual is None:
            continue
        a, v = c.actual, c.verification
        # migration/DB involvement is taken from the AUTHORITATIVE engineering_pattern tag,
        # not keyword-matched (config's notes mention 'migration' incidentally — a false positive).
        is_migration = c.engineering_pattern == "migration_guard"
        rows.append({
            "cycle": c.id,
            "engineering_pattern": c.engineering_pattern,
            "obligations_built": len(a.get("obligations_built", [])),
            "reuse_vs_new": f"{len(c.reused)} reused / {len(a.get('obligations_built', []))} new",
            "migration_or_runtime": is_migration,
            "verification_tests": v.get("tests") or v.get("equivalence_tests"),
            "db_fixture_involved": is_migration,
        })
    groups: Dict[str, List[str]] = {}
    for r in rows:
        groups.setdefault(r["engineering_pattern"], []).append(r["cycle"])
    return {
        "per_cycle": rows,
        "groups_by_engineering_pattern": groups,
        "largest_genuinely_comparable_group": max((len(v) for v in groups.values()), default=0),
        "finding": "sharing work_type='test_guard' did NOT make the three guards comparable: two are "
                   "migration guards (DB fixtures + the real migration runner) and one is an "
                   "invariant guard (source scan, no DB). The honest comparable group is the 2 "
                   "migration guards, not 3 — a smaller honest set, not a larger artificial one.",
    }


_OUTCOME_MEASURES = ("missed_obligation_count", "prediction_error_effort", "rework")
_PROCESS_MEASURES = ("expansion_grounded_fraction", "duplicate_discovery_rate",
                     "reuse_accuracy", "verification_success")

def transfer_observations(cycles: List[CycleRecord]) -> Dict:
    """Report observed cross-cycle transfer without manufacturing a match.

    A prediction is matched only when effort is known and every obligation/reuse
    discrepancy category was explicitly reported empty. Missing categories leave
    the match UNKNOWN (None), not implicitly successful.
    """
    execs = [c for c in cycles if c.kind == EXECUTED_VERIFIED and c.actual is not None]
    rows = []
    required = {
        "missed": "under_expansion_missed",
        "unnecessary": "over_expansion_unnecessary",
        "inappropriate_reuse": "inappropriate_reuse",
    }
    for cycle in execs:
        data = compare(cycle)
        complete = (data.get("effort_error") is not None
                    and all(isinstance(data.get(key), list) for key in required.values()))
        counts = {
            name: (len(data[key]) if isinstance(data.get(key), list) else None)
            for name, key in required.items()
        }
        matched = None
        if complete:
            matched = (data["effort_error"] == 0
                       and all(count == 0 for count in counts.values()))
        rows.append({
            "cycle": cycle.id,
            "predicted_effort": cycle.predicted.get("effort"),
            "actual_effort": cycle.actual.get("effort_actual"),
            "effort_error": data.get("effort_error"),
            "missed_obligations": counts["missed"],
            "unnecessary_obligations": counts["unnecessary"],
            "inappropriate_reuse": counts["inappropriate_reuse"],
            "prediction_matched": matched,
        })
    matched_cycles = [row["cycle"] for row in rows if row["prediction_matched"] is True]
    contradicted_cycles = [row["cycle"] for row in rows if row["prediction_matched"] is False]
    unknown_cycles = [row["cycle"] for row in rows if row["prediction_matched"] is None]
    return {
        "executed_cycles": rows,
        "matched_cycles": matched_cycles,
        "contradicted_cycles": contradicted_cycles,
        "unknown_cycles": unknown_cycles,
        "observation": "Observed matched cycles: " + (", ".join(matched_cycles) or "none established")
                       + "; contradicted cycles: " + (", ".join(contradicted_cycles) or "none established")
                       + "; unknown cycles: " + (", ".join(unknown_cycles) or "none") +
                       ". These are observations, NOT proof of a general improvement trend.",
        "caveat": "Transfer is currently applied in reasoning (reconcile-first + anticipate-the-hidden-"
                  "obligation), not autonomously by Pattern Memory's keyword matcher. Incomplete evidence "
                  "does not count as a match; small samples are not statistical proof. Predictions are "
                  "never rewritten after the fact.",
    }

def prediction_accuracy(cycle: CycleRecord) -> Optional[Dict]:
    """Score only when all discrepancy dimensions were explicitly reported.

    Missing actuals and omitted discrepancy categories remain UNKNOWN; omission is
    not proof of zero missed/unnecessary/inappropriate-reuse outcomes. A measured
    empty list is the explicit zero case. Over-generation cannot improve accuracy.
    """
    if cycle.actual is None:
        return None
    d = compare(cycle)
    keys = {
        "missed": "under_expansion_missed",
        "unnecessary": "over_expansion_unnecessary",
        "inappropriate_reuse": "inappropriate_reuse",
    }
    unknown = [name for name, key in keys.items() if not isinstance(d.get(key), list)]
    counts = {
        name: len(d[key]) if isinstance(d.get(key), list) else None
        for name, key in keys.items()
    }
    if unknown:
        return {
            "status": "incomplete", "correct": None,
            "missed": counts["missed"], "unnecessary": counts["unnecessary"],
            "inappropriate_reuse": counts["inappropriate_reuse"],
            "effort_error": d.get("effort_error"), "accuracy": None,
            "unknown_measures": unknown,
            "note": "incomplete actual evidence; omitted categories remain UNKNOWN, not zero",
        }
    predicted_net_new = cycle.predicted.get("net_new_count", len(cycle.missing))
    if (isinstance(predicted_net_new, bool) or not isinstance(predicted_net_new, int)
            or predicted_net_new < 0):
        return {
            "status": "incomplete", "correct": None,
            "missed": counts["missed"], "unnecessary": counts["unnecessary"],
            "inappropriate_reuse": counts["inappropriate_reuse"],
            "effort_error": d.get("effort_error"), "accuracy": None,
            "unknown_measures": ["predicted_net_new_count"],
            "note": "predicted count unavailable or invalid; accuracy remains UNKNOWN",
        }
    correct = max(0, predicted_net_new - counts["unnecessary"])
    denom = correct + counts["missed"] + counts["unnecessary"] + counts["inappropriate_reuse"]
    return {
        "status": "recorded", "correct": correct,
        "missed": counts["missed"], "unnecessary": counts["unnecessary"],
        "inappropriate_reuse": counts["inappropriate_reuse"],
        "effort_error": d.get("effort_error"),
        "accuracy": (round(correct / denom, 3) if denom else None),
        "unknown_measures": [],
        "note": "missed + unnecessary + inappropriate reuse reduce accuracy; over-generation never raises it",
    }

def learning_provenance(cycle: CycleRecord) -> str:
    """Classify provenance without treating a label as proof of human identity.

    A caller-supplied reviewer is attributed provenance, not independently verified
    identity. Controlled test/demonstration reviews are kept in their own category.
    Watcher verification is independently sourced and remains separate from both.
    """
    a = cycle.actual or {}
    kind = a.get("review_kind")
    if kind == "watcher_verified_execution":
        return "independent_watcher_verified"
    if kind == "controlled_fixture_review":
        return "controlled_fixture_review"
    if a.get("reviewer"):
        review_type = "planning_review" if kind == "planning_review" else "execution_review"
        return f"reviewer_attributed:{review_type}"
    if cycle.actual is None:
        return "unknown_no_outcome"
    if cycle.kind == EXECUTED_VERIFIED:
        return "executed_verified_outcome"
    return "automated_self_assessment"

def reopening_candidates(cycle: CycleRecord, new_evidence: List[Dict]) -> List[Dict]:
    """New evidence can reopen a previously deferred or apparently-resolved branch. Each item is
    {key, observation, now?, blocker_cleared?}. Reopen only on CONCRETE contradicting evidence;
    UNKNOWN/insufficient evidence does not reopen (no manufactured certainty)."""
    by_key = {o["key"]: o for o in cycle.obligations}
    frontier_keys = {f["key"] for f in cycle.frontier}
    out: List[Dict] = []
    for ev in new_evidence or []:
        k, obs = ev.get("key"), ev.get("observation", "")
        if not obs or ev.get("now") == "unknown":
            out.append({"key": k, "reopen": False, "reason": "insufficient/UNKNOWN evidence — not reopened"})
        elif (k in by_key
              and by_key[k].get("recon_status") in ("reuse_existing", "signature_matched")
              and ev.get("now") == "missing"):
            prior = by_key[k].get("recon_status")
            out.append({
                "key": k, "reopen": True,
                "reason": ("previously reviewed reuse now observed missing"
                           if prior == "reuse_existing"
                           else "previous source match now observed missing; semantic review remains open"),
                "evidence": obs,
            })
        elif k in frontier_keys and ev.get("blocker_cleared"):
            out.append({"key": k, "reopen": True, "reason": "deferred branch's blocker reported cleared", "evidence": obs})
        else:
            out.append({"key": k, "reopen": False, "reason": "no matching deferred/resolved branch"})
    return out

def learning_loop(cycles: List[CycleRecord], new_evidence: Optional[List[Dict]] = None,
                  reopen_cycle: Optional[CycleRecord] = None) -> Dict:
    """The assembled Stage-6 learning loop over real stage evidence. Per-cycle accuracy + provenance
    with explicit UNKNOWNs and contradictory-evidence flags; aggregate accuracy only over recorded
    outcomes; reopening on new evidence. Planning reviews are never counted as execution outcomes."""
    per: List[Dict] = []
    reviewer_attributed = controlled_fixture = executed_verified = watcher_verified = automated = unknown = 0
    for c in cycles:
        prov = learning_provenance(c)
        acc = prediction_accuracy(c)
        contradiction = None
        if c.actual is not None:
            d = compare(c)
            missed = d.get("under_expansion_missed")
            unnecessary = d.get("over_expansion_unnecessary")
            if isinstance(missed, list) and isinstance(unnecessary, list):
                overlap = set(missed) & set(unnecessary)
                contradiction = sorted(overlap) or None  # same obligation both missed AND unnecessary
        per.append({
            "cycle": c.id, "kind": c.kind, "provenance": prov,
            "outcome_status": "recorded" if c.actual is not None else "UNKNOWN (pending)",
            "accuracy": acc, "contradictory_evidence": contradiction,
        })
        if prov.startswith("reviewer_attributed:"):
            reviewer_attributed += 1
        elif prov == "controlled_fixture_review":
            controlled_fixture += 1
        elif prov == "independent_watcher_verified":
            watcher_verified += 1
        elif prov == "executed_verified_outcome":
            executed_verified += 1
        elif prov == "unknown_no_outcome":
            unknown += 1
        else:
            automated += 1
    # Controlled fixtures exercise the pipeline but are not development outcomes
    # and must not influence its aggregate accuracy.
    eligible_accuracy = [
        p for p in per
        if p["provenance"] != "controlled_fixture_review"
        and p["accuracy"] is not None
        and p["accuracy"].get("accuracy") is not None
    ]
    accs = [p["accuracy"]["accuracy"] for p in eligible_accuracy]
    controlled_fixtures_excluded = sum(
        1 for p in per if p["provenance"] == "controlled_fixture_review"
    )
    return {
        "per_cycle": per,
        "provenance_split": {
            "reviewer_attributed": reviewer_attributed,
            "controlled_fixture_review": controlled_fixture,
            "executed_verified_outcome": executed_verified,
            "independent_watcher_verified": watcher_verified,
            "automated_self_assessment": automated,
            "unknown_no_outcome": unknown,
        },
        "mean_prediction_accuracy": (round(sum(accs) / len(accs), 3) if accs else None),
        "accuracy_basis": (f"{len(accs)} non-fixture cycle(s) with complete recorded discrepancy categories; "
                           f"{controlled_fixtures_excluded} controlled fixture(s) excluded; "
                           "incomplete outcomes remain UNKNOWN, not fabricated"),
        "controlled_fixtures_excluded": controlled_fixtures_excluded,
        "series": accuracy_series(cycles),
        "comparability": comparability_assessment(cycles),
        "reopening": reopening_candidates(reopen_cycle, new_evidence) if (reopen_cycle and new_evidence) else [],
        "anti_gaming": ("accuracy penalises missed, unnecessary and inappropriate-reuse obligations; "
                        "incomplete actuals remain UNKNOWN. Reviewer-attributed inputs and controlled "
                        "fixtures are separate from independently verified execution outcomes."),
    }

