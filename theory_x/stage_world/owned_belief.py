"""Owned-belief expectations -- build B's one valence-capable producer.

She pre-registers, about one of her OWN beliefs, "this still holds at T". It is
the only in-scope claim that has all three things valence needs at once: a
stated confidence (the belief's own), a basis that is hers (the belief itself,
authored), and a real cost of being wrong (a claim about what she holds is
self-constitutive: band 4, refused at write time on any non-authored basis).

"Holds" is defined by the mechanisms that actually undo a belief in this code,
captured at made_at so the reconciler compares against the frozen claim:
    exists            the row is still there (signal_cleanup / probes delete)
    not paused        the harmonizer pauses both sides of a contradiction
    tier not weaker   decay_pass and decisive_contradiction demote (tier +1/+2;
                      a higher tier number is weaker); harmonizer moves to 8
(erosion_stage is captured but is not part of "holds": erosion.py advances a
belief toward nex_core as it becomes hers -- assimilation, not an undo.)
The reconciler (build B PR2) judges this at resolve_at; producers write 'open'.

Selection is UNIFORM over eligible beliefs (authored, unlocked, unpaused,
use_count >= N, not already under an open expectation) -- the producer never
picks easy ones. Whether the claims are ever actually tested is measured by
expectations.falsifiability(), not by the raw confirmation rate.

Dark by default: runs only with NEX5_OWNED_BELIEF=1. It writes only its own table.
"""
from __future__ import annotations

import json
import logging
import os
import random
import time
from typing import Optional

from substrate import connect, Row
from substrate.paths import DbPath
from theory_x.stage_world.frozen_at_made import (
    FROZEN_INSERT_COLS, FROZEN_PLACEHOLDERS, SELF_CONSTITUTIVE, basis_entry,
    ensure_frozen_columns, frozen_values,
)

log = logging.getLogger("theory_x.stage_world.owned_belief")

CONVERSATIONS_DB = DbPath("conversations")
BELIEFS_DB = DbPath("beliefs")

MIN_OBSERVATIONS = int(os.environ.get("NEX5_OWNED_BELIEF_MIN_OBS", "3"))
HORIZON_S = int(os.environ.get("NEX5_OWNED_BELIEF_HORIZON_S", str(48 * 3600)))
EVERY_S = int(os.environ.get("NEX5_OWNED_BELIEF_EVERY_S", "3600"))

_SCHEMA = (
    "CREATE TABLE IF NOT EXISTS owned_belief_expectations ("
    "id INTEGER PRIMARY KEY AUTOINCREMENT, "
    "made_at REAL NOT NULL, "
    "belief_id INTEGER NOT NULL, "
    "claimed_state TEXT NOT NULL, "       # JSON: the frozen 'holds' snapshot
    "resolve_at REAL NOT NULL, "
    "state TEXT NOT NULL DEFAULT 'open', "
    "resolved_at REAL, "
    "resolved_by TEXT, "
    "observed_state TEXT, "
    "confidence REAL, confidence_basis TEXT, tolerance REAL, tolerance_basis TEXT, "
    "stakes_at_made REAL, stakes_active_at_made INTEGER, groove_cost_at_made REAL, "
    "basis_snapshot TEXT, cost_band INTEGER, salience_k REAL, "
    "frozen TEXT)"
)
_IDX = ("CREATE INDEX IF NOT EXISTS idx_obe_state_resolve "
        "ON owned_belief_expectations(state, resolve_at)")


def enabled() -> bool:
    return os.environ.get("NEX5_OWNED_BELIEF") == "1"


def ensure_schema(db_path=None) -> None:
    cx = connect(str(db_path or CONVERSATIONS_DB), timeout=10)
    try:
        cx.execute(_SCHEMA)
        cx.execute(_IDX)
        ensure_frozen_columns(cx, "owned_belief_expectations")
        cx.commit()
    finally:
        cx.close()


def eligible_ids(beliefs_db=None, exclude=()) -> list:
    cx = connect(f"file:{beliefs_db or BELIEFS_DB}?mode=ro", uri=True, timeout=10)
    try:
        ids = [r[0] for r in cx.execute(
            "SELECT id FROM beliefs WHERE source_kind = 'authored' AND locked = 0 "
            "AND paused = 0 AND use_count >= ?", (MIN_OBSERVATIONS,))]
    finally:
        cx.close()
    excluded = set(exclude)
    return [i for i in ids if i not in excluded]


def _open_belief_ids(cx) -> set:
    return {r[0] for r in cx.execute(
        "SELECT belief_id FROM owned_belief_expectations WHERE state = 'open'")}


def make_owned_belief_expectation(db_path=None, beliefs_db=None,
                                  rng: Optional[random.Random] = None,
                                  now: Optional[float] = None) -> dict:
    """Pre-register one expectation over a uniformly drawn eligible belief."""
    db_path = str(db_path or CONVERSATIONS_DB)
    ensure_schema(db_path)
    now = time.time() if now is None else now
    cx = connect(db_path, timeout=10)
    try:
        candidates = eligible_ids(beliefs_db, exclude=_open_belief_ids(cx))
    finally:
        cx.close()
    if not candidates:
        return {"skipped": "no_eligible_belief"}
    bid = (rng or random).choice(candidates)

    bx = connect(f"file:{beliefs_db or BELIEFS_DB}?mode=ro", uri=True, timeout=10)
    bx.row_factory = Row
    try:
        b = bx.execute("SELECT id, tier, paused, erosion_stage, confidence, source_kind "
                       "FROM beliefs WHERE id = ?", (bid,)).fetchone()
    finally:
        bx.close()
    if b is None:
        return {"skipped": "belief_vanished"}
    claimed = {"belief_id": b["id"], "holds": True, "tier": b["tier"],
               "paused": b["paused"], "erosion_stage": b["erosion_stage"]}
    frozen = frozen_values(
        b["confidence"], "stated_p", 0.0, "exact_label",
        basis=[basis_entry(b["id"], b["source_kind"], b["confidence"])],
        cost_band=SELF_CONSTITUTIVE)
    cx = connect(db_path, timeout=10)
    try:
        cur = cx.execute(
            "INSERT INTO owned_belief_expectations "
            "(made_at, belief_id, claimed_state, resolve_at, state, "
            + FROZEN_INSERT_COLS + ") VALUES (?, ?, ?, ?, 'open', "
            + FROZEN_PLACEHOLDERS + ")",
            (now, b["id"], json.dumps(claimed), now + HORIZON_S, *frozen))
        cx.commit()
        eid = cur.lastrowid
    finally:
        cx.close()
    log.info("owned_belief: pre-registered #%s belief=%s conf=%.2f of %d eligible",
             eid, b["id"], b["confidence"], len(candidates))
    return {"id": eid, "belief_id": b["id"], "eligible": len(candidates)}


def due(db_path=None, now: Optional[float] = None) -> bool:
    """At most one new expectation per EVERY_S."""
    db_path = str(db_path or CONVERSATIONS_DB)
    now = time.time() if now is None else now
    ensure_schema(db_path)
    cx = connect(db_path, timeout=10)
    try:
        last = cx.execute("SELECT MAX(made_at) FROM owned_belief_expectations").fetchone()[0]
    finally:
        cx.close()
    return last is None or now - last >= EVERY_S


def confirmation_rate_canary(db_path=None) -> dict:
    """Fraction of resolved owned-belief expectations that were confirmed.

    LOGGED ONLY -- flag is always False. At a base rate ~1.0 (nothing undoes an
    authored belief on a young store) a high rate is arithmetic, and it prints
    the same number a gaming selector would: an ambiguity, not a finding. The
    evidential number is expectations.falsifiability() (violations among windows
    in which an undo was actually attempted)."""
    db_path = str(db_path or CONVERSATIONS_DB)
    ensure_schema(db_path)
    cx = connect(db_path, timeout=10)
    try:
        rows = dict(cx.execute(
            "SELECT state, COUNT(*) FROM owned_belief_expectations "
            "WHERE state IN ('confirmed', 'violated') GROUP BY state").fetchall())
    finally:
        cx.close()
    n = sum(rows.values())
    rate = rows.get("confirmed", 0) / n if n else None
    return {"resolved": n, "confirmed": rows.get("confirmed", 0), "rate": rate,
            "flag": False}
