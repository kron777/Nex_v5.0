"""Frozen-at-made fields for prediction rows (build B, phase 0).

A prediction's confidence, its tolerance (the standard it will be judged by)
and the stakes in force when it was made must be recorded WHEN IT IS MADE and
never touched again. A judge who picks the standard after seeing the outcome
always finds the outcome acceptable; and a snapshot that wasn't taken can't be
reconstructed later -- so an epoch that didn't record these is permanently
uncomputable. These columns start that record.

Columns, added to self_predictions, world_predictions, predictions (surprise)
and owned_belief_expectations:
    confidence             P(the predicted outcome), as the PRODUCER stated it
    confidence_basis       'stated_p'    the producer emitted a probability
                           'coin'        the random control (0.5)
                           'none_stated' the producer states no probability;
                                         confidence is NULL, not invented
    tolerance              how far the actual may sit from the claim and still
                           count as confirmed, in tolerance_basis units
    tolerance_basis        'exact_label'      actual must equal predicted
                           'strict_direction' price must move strictly the
                                              claimed way (flat = wrong)
    stakes_at_made         L4 drift ratio (stakes_appraisal.appraise) -- a
                           stored snapshot, never a live join
    stakes_active_at_made  1 if that ratio was over its threshold
    groove_cost_at_made    L4 groove-onset cost (stakes_appraisal.appraise_groove)
                           (the two L4 fields are the groove program's; they are
                           NOT the valence stakes -- that is cost_band)
    basis_snapshot         JSON [{belief_id, source_kind, confidence}] of the
                           beliefs the claim rests on, as they were at made_at.
                           Ownership and learning resolve against THIS, never a
                           live join (learning mutates the live rows). [] = no
                           belief basis (self/world probes).
    cost_band              cost of being wrong, a fixed ordinal set by the
                           producer for this row: 0 nothing follows, 1 a belief
                           gets revised, 2 operational, 3 relational, 4 self-
                           constitutive (only on an all-authored basis, checked
                           here at write time)
    salience_k             K for salience = clamp(|d|/tolerance / K, 0, 1)
    frozen                 'at_made' (this record) | 'legacy_unfrozen' (rows
                           written before it existed: their fields stay NULL)

Enforced, not trusted: a BEFORE UPDATE trigger aborts any change to a frozen
field on an 'at_made' row.
"""
from __future__ import annotations

import json
import logging

FROZEN_COLUMNS = (
    ("confidence", "REAL"),
    ("confidence_basis", "TEXT"),
    ("tolerance", "REAL"),
    ("tolerance_basis", "TEXT"),
    ("stakes_at_made", "REAL"),
    ("stakes_active_at_made", "INTEGER"),
    ("groove_cost_at_made", "REAL"),
    ("basis_snapshot", "TEXT"),
    ("cost_band", "INTEGER"),
    ("salience_k", "REAL"),
    ("frozen", "TEXT"),
)
FROZEN_INSERT_COLS = ", ".join(name for name, _ in FROZEN_COLUMNS)
FROZEN_PLACEHOLDERS = ", ".join("?" for _ in FROZEN_COLUMNS)

COIN = 0.5
DEFAULT_K = 4.0
COST_BANDS = (0, 1, 2, 3, 4)
SELF_CONSTITUTIVE = 4

log = logging.getLogger("theory_x.stage_world.frozen_at_made")


def _freeze_trigger(table: str) -> str:
    fields = ", ".join(name for name, _ in FROZEN_COLUMNS)
    changed = " OR ".join(f"NEW.{n} IS NOT OLD.{n}" for n, _ in FROZEN_COLUMNS)
    return (
        f"CREATE TRIGGER trg_{table}_frozen_at_made "
        f"BEFORE UPDATE OF {fields} ON {table} "
        f"WHEN OLD.frozen = 'at_made' AND ({changed}) "
        f"BEGIN SELECT RAISE(ABORT, '{table}: frozen-at-made field changed'); END"
    )


def ensure_frozen_columns(conn, table: str) -> None:
    """Add any missing frozen columns to an existing table; rows that predate them
    are marked legacy_unfrozen (once, when the marker column is added). Then the
    freeze trigger. Caller commits."""
    have = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
    missing = [(n, k) for n, k in FROZEN_COLUMNS if n not in have]
    for name, kind in missing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {kind}")
    if "frozen" not in have:
        conn.execute(f"UPDATE {table} SET frozen = 'legacy_unfrozen' WHERE frozen IS NULL")
    # Recreated every time so it always guards the current column list.
    conn.execute(f"DROP TRIGGER IF EXISTS trg_{table}_frozen_at_made")
    conn.execute(_freeze_trigger(table))


def snapshot_stakes(dynamic_db=None, beliefs_db=None) -> tuple:
    """(stakes_at_made, stakes_active_at_made, groove_cost_at_made) right now.
    Both appraisals are read-only and fail-safe (0 on error)."""
    from theory_x.stage_tom.stakes_appraisal import appraise, appraise_groove
    drift = appraise(dynamic_db)
    groove = appraise_groove(beliefs_db)
    return (float(drift.get("ratio", 0.0)), int(bool(drift.get("stakes_active"))),
            float(groove.get("cost", 0.0)))


def basis_entry(belief_id, source_kind, confidence) -> dict:
    return {"belief_id": int(belief_id), "source_kind": source_kind,
            "confidence": None if confidence is None else float(confidence)}


def frozen_values(confidence, confidence_basis: str, tolerance: float,
                  tolerance_basis: str, stakes=None, *, basis=(), cost_band: int,
                  salience_k: float = DEFAULT_K) -> tuple:
    """Row values in FROZEN_COLUMNS order, stakes snapshotted now unless given.

    basis: basis_entry dicts. cost_band 4 (self-constitutive) is refused unless
    every basis row is authored -- a headline can't become a claim about what
    she is (D's floor, one layer up)."""
    if cost_band not in COST_BANDS:
        raise ValueError(f"cost_band must be one of {COST_BANDS}, got {cost_band!r}")
    basis = list(basis)
    if cost_band == SELF_CONSTITUTIVE and (
            not basis or any(b.get("source_kind") != "authored" for b in basis)):
        log.error("REJECTED band-4 expectation on a non-authored basis: %s", basis)
        raise ValueError("cost band 4 requires an all-authored basis")
    if confidence_basis == "none_stated":
        confidence = None
    s = stakes if stakes is not None else snapshot_stakes()
    return (confidence, confidence_basis, float(tolerance), tolerance_basis,
            s[0], s[1], s[2], json.dumps(basis), int(cost_band), float(salience_k),
            "at_made")
