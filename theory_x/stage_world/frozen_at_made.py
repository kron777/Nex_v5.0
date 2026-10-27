"""Frozen-at-made fields for prediction rows (build B, phase 0).

A prediction's confidence, its tolerance (the standard it will be judged by)
and the stakes in force when it was made must be recorded WHEN IT IS MADE and
never touched again. A judge who picks the standard after seeing the outcome
always finds the outcome acceptable; and a snapshot that wasn't taken can't be
reconstructed later -- so an epoch that didn't record these is permanently
uncomputable. These columns start that record.

Columns, added to self_predictions and world_predictions:
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
    frozen                 'at_made' (this record) | 'legacy_unfrozen' (rows
                           written before it existed: their fields stay NULL)

Enforced, not trusted: a BEFORE UPDATE trigger aborts any change to a frozen
field on an 'at_made' row.
"""
from __future__ import annotations

FROZEN_COLUMNS = (
    ("confidence", "REAL"),
    ("confidence_basis", "TEXT"),
    ("tolerance", "REAL"),
    ("tolerance_basis", "TEXT"),
    ("stakes_at_made", "REAL"),
    ("stakes_active_at_made", "INTEGER"),
    ("groove_cost_at_made", "REAL"),
    ("frozen", "TEXT"),
)
FROZEN_INSERT_COLS = ", ".join(name for name, _ in FROZEN_COLUMNS)
FROZEN_PLACEHOLDERS = ", ".join("?" for _ in FROZEN_COLUMNS)

COIN = 0.5


def _freeze_trigger(table: str) -> str:
    fields = ", ".join(name for name, _ in FROZEN_COLUMNS)
    changed = " OR ".join(f"NEW.{n} IS NOT OLD.{n}" for n, _ in FROZEN_COLUMNS)
    return (
        f"CREATE TRIGGER IF NOT EXISTS trg_{table}_frozen_at_made "
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
    conn.execute(_freeze_trigger(table))


def snapshot_stakes(dynamic_db=None, beliefs_db=None) -> tuple:
    """(stakes_at_made, stakes_active_at_made, groove_cost_at_made) right now.
    Both appraisals are read-only and fail-safe (0 on error)."""
    from theory_x.stage_tom.stakes_appraisal import appraise, appraise_groove
    drift = appraise(dynamic_db)
    groove = appraise_groove(beliefs_db)
    return (float(drift.get("ratio", 0.0)), int(bool(drift.get("stakes_active"))),
            float(groove.get("cost", 0.0)))


def frozen_values(confidence, confidence_basis: str, tolerance: float,
                  tolerance_basis: str, stakes=None) -> tuple:
    """Row values in FROZEN_COLUMNS order, stakes snapshotted now unless given."""
    if confidence_basis == "none_stated":
        confidence = None
    s = stakes if stakes is not None else snapshot_stakes()
    return (confidence, confidence_basis, float(tolerance), tolerance_basis,
            s[0], s[1], s[2], "at_made")
