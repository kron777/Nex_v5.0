"""The expectations ledger and its single reconciler -- build B (intentional valence).

Producers make claims and keep their rich bodies (self_predictions,
world_predictions, predictions [surprise], owned_belief_expectations). This
module is the ONE place a claim is adjudicated:

    ingest     a header row per producer row, state 'open', every judging field
               copied from the producer's frozen-at-made columns
    reconcile  gather the producer's evidence, compute the discrepancy ONCE, and
               from that one number the verdict and the salience
    valence    signed, bounded, per expectation (event_valence), only when the
               claim is admissible: stated confidence > 0.5, owned basis
               (>= 0.5 authored/witnessed in the FROZEN basis snapshot), and a
               cost band >= 1. Band 0 is exactly 0.
    learning   (NEX5_EXPECT_LEARN, OFF) moves the confidence of the basis
               beliefs -- on ANY basis, external included; not coupled to valence
    mood       (NEX5_EXPECT_MOOD, OFF) affect_state reads a capped nudge from
               event_valence; event_valence never reads mood

The schema enforces the single writer: a header can only be inserted 'open',
and any state change whose resolved_by isn't 'reconciler' aborts and logs
(nex_guard). commitment and goal subjects are rejected the same way until those
faculties exist (a goal expectation must be about a MILESTONE, never the goal).

Scope (Beam, final): one valence-capable producer (owned-belief), surprise
admissible in principle, self/world learning-only. Bands 2-3 untested here.
"""
from __future__ import annotations

import json
import logging
import os
import time
from typing import Optional

from substrate import connect, Row
from substrate.paths import DbPath

log = logging.getLogger("theory_x.stage_world.expectations")

CONVERSATIONS_DB = DbPath("conversations")
DYNAMIC_DB = DbPath("dynamic")
BELIEFS_DB = DbPath("beliefs")

RECONCILER = "reconciler"
SUBJECTS = ("self", "world", "surprise", "commitment", "goal")
DEFERRED_SUBJECTS = ("commitment", "goal")
STATES = ("open", "confirmed", "violated", "unresolved", "withdrawn", "superseded",
          "breached", "released")
LABEL_BASES = ("exact_label", "strict_direction")   # R2: magnitude-free kinds
OWNED_KINDS = ("authored", "self")                  # authored + witnessed (D's kinds)
EVIDENCE_GRACE_S = 2 * 3600       # horizon passed this long with no evidence -> unresolved
CONFIRM_POSITIVE = 0.05           # a confirm at band >= 1: small, never paid for the easy
LEARN_VIOLATE = 0.03              # R7 s, distributed over the basis rows
LEARN_CONFIRM = 0.015
CONF_FLOOR, CONF_CEIL = 0.05, 0.99
MOOD_GAIN = 0.1                   # event_valence -> affect valence
MOOD_CAP = 0.05                   # |nudge| per affect tick, hard cap

# producer table -> (db, subject, horizon kind)
PRODUCERS = {
    "self_predictions": ("conversations", "self", "timer"),
    "world_predictions": ("conversations", "world", "timer"),
    "predictions": ("dynamic", "surprise", "window"),
    "owned_belief_expectations": ("conversations", "self", "timer"),
}


def learning_on() -> bool:
    return os.environ.get("NEX5_EXPECT_LEARN") == "1"


def mood_on() -> bool:
    return os.environ.get("NEX5_EXPECT_MOOD") == "1"


def reconciler_on() -> bool:
    return os.environ.get("NEX5_RECONCILER") == "1"


def _db(name):
    return str({"conversations": CONVERSATIONS_DB, "dynamic": DYNAMIC_DB,
                "beliefs": BELIEFS_DB}[name])


# ---------------------------------------------------------------- pure math --

def ownership(basis) -> float:
    """R4: share of the frozen basis that is hers (authored + witnessed)."""
    basis = list(basis or [])
    if not basis:
        return 0.0
    return sum(1 for b in basis if b.get("source_kind") in OWNED_KINDS) / len(basis)


def basis_kind(basis) -> str:
    basis = list(basis or [])
    if not basis:
        return "none"
    return "owned" if ownership(basis) >= 0.5 else "external"


def adjudicate(tolerance_basis: str, tolerance, salience_k, discrepancy: float):
    """(state, ratio, salience) from ONE discrepancy. The verdict never depends
    on K; K only scales magnitude (R1). Label kinds have no magnitude (R2)."""
    if discrepancy is None:
        raise ValueError("adjudicate needs evidence; empty windows are 'unresolved'")
    if tolerance_basis in LABEL_BASES:
        d = 1.0 if discrepancy else 0.0
        return ("violated" if d else "confirmed"), None, d
    if tolerance is None or tolerance <= 0:
        raise ValueError(f"{tolerance_basis!r} needs a positive tolerance")
    ratio = abs(discrepancy) / tolerance
    state = "violated" if ratio > 1.0 else "confirmed"
    k = salience_k or 4.0
    return state, ratio, max(0.0, min(1.0, ratio / k))


def valence(state, salience, cost_band, own, confidence_basis, confidence):
    """(event_valence, admitted, reason). Admission is a gate, never a weight on
    confidence (R3); stakes = cost band; band 0 is exactly 0."""
    if state not in ("confirmed", "violated"):
        return 0.0, 0, "no_verdict"
    if cost_band is None:          # made before cost bands were recorded
        return 0.0, 0, "band_unrecorded"
    if not cost_band:
        return 0.0, 0, "band_0"
    if not (confidence_basis == "stated_p" and confidence is not None and confidence > 0.5):
        return 0.0, 0, "confidence_not_admitted"
    if own < 0.5:
        return 0.0, 0, "external_basis"
    band = cost_band / 4.0
    if state == "violated":
        return -1.0 * salience * band * own, 1, "violated"
    return CONFIRM_POSITIVE * band * own, 1, "confirmed"


# ------------------------------------------------------------------- ingest --

def _claimed(table, r) -> dict:
    if table == "self_predictions":
        return {"kind": r["kind"], "predicted": r["predicted"], "arm": r["source"]}
    if table == "world_predictions":
        return {"asset": r["asset"], "direction": r["direction"],
                "baseline_price": r["baseline_price"], "arm": r["source"]}
    if table == "predictions":
        return {"prediction_type": r["prediction_type"], "within_distance": r["tolerance"]}
    return json.loads(r["claimed_state"])


def _stream(table, r) -> str:
    if table == "self_predictions":
        return f"self_prediction.{r['kind']}.{r['source']}"
    if table == "world_predictions":
        return f"world_prediction.{r['source']}"
    if table == "predictions":
        return f"predictive_substrate.{r['prediction_type']}"
    return "owned_belief"


def _horizon(table, r) -> float:
    return float(r["target_window_end"] if table == "predictions" else r["resolve_at"])


def ingest(now: Optional[float] = None) -> int:
    """Header every frozen producer row not yet in the ledger, state 'open'."""
    cx = connect(_db("conversations"), timeout=30)
    cx.row_factory = Row
    n = 0
    try:
        for table, (dbname, subject, hkind) in PRODUCERS.items():
            if subject in DEFERRED_SUBJECTS:   # declared, never produced (yet)
                continue
            last = cx.execute("SELECT COALESCE(MAX(producer_row_id), 0) FROM expectations "
                              "WHERE producer = ?", (table,)).fetchone()[0]
            src = cx if dbname == "conversations" else connect(_db(dbname), timeout=30)
            src.row_factory = Row
            try:
                if not _has_table(src, table):
                    continue
                rows = src.execute(f"SELECT * FROM {table} WHERE id > ? AND frozen = 'at_made' "
                                   "ORDER BY id", (last,)).fetchall()
            finally:
                if src is not cx:
                    src.close()
            for r in rows:
                basis = json.loads(r["basis_snapshot"]) if r["basis_snapshot"] else []
                cx.execute(
                    "INSERT INTO expectations (subject, producer, producer_row_id, made_at, "
                    "claimed_state, confidence, confidence_basis, tolerance, tolerance_basis, "
                    "salience_k, cost_band, basis_snapshot, ownership, basis_kind, "
                    "producer_stream, horizon_at, horizon_kind) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (subject, table, r["id"], r["made_at"], json.dumps(_claimed(table, r)),
                     r["confidence"], r["confidence_basis"], r["tolerance"],
                     r["tolerance_basis"], r["salience_k"], r["cost_band"],
                     json.dumps(basis), ownership(basis), basis_kind(basis),
                     _stream(table, r), _horizon(table, r), hkind))
                n += 1
        cx.commit()
    finally:
        cx.close()
    return n


def _has_table(cx, name) -> bool:
    return cx.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                      (name,)).fetchone() is not None


# ------------------------------------------------------------------ evidence --
# Each returns (discrepancy, evidence_dict) or (None, why) when there is no
# evidence (yet). A None never reaches adjudicate().

def _evidence_self(cx, row_id):
    r = cx.execute("SELECT predicted, actual FROM self_predictions WHERE id=?",
                   (row_id,)).fetchone()
    if r is None or r["actual"] is None:
        return None, {"why": "no actual yet"}
    return (0.0 if r["actual"] == r["predicted"] else 1.0), {"actual": r["actual"]}


def _evidence_world(cx, row_id):
    r = cx.execute("SELECT direction, baseline_price, price_at_resolve, outcome "
                   "FROM world_predictions WHERE id=?", (row_id,)).fetchone()
    if r is None or r["price_at_resolve"] is None or r["outcome"] not in ("correct", "wrong"):
        return None, {"why": "no resolving price"}
    p, b = r["price_at_resolve"], r["baseline_price"]
    moved = "up" if p > b else ("down" if p < b else "flat")
    return (0.0 if moved == r["direction"] else 1.0), {"moved": moved, "price": p}


def _evidence_surprise(row_id):
    dx = connect(_db("dynamic"), timeout=30)
    dx.row_factory = Row
    try:
        p = dx.execute("SELECT verified_at, surprise_score FROM predictions WHERE id=?",
                       (row_id,)).fetchone()
        if p is None or p["verified_at"] is None:
            return None, {"why": "not verified yet"}
        ev = dx.execute("SELECT actual_content FROM surprise_events WHERE prediction_id=? "
                        "ORDER BY id DESC LIMIT 1", (row_id,)).fetchone()
    finally:
        dx.close()
    # R6: (score 1.0, no actual content) is predictive_substrate's EMPTY WINDOW --
    # nothing happened to compare against. That is no evidence, never a violation.
    if p["surprise_score"] is None or (
            p["surprise_score"] >= 1.0 and (ev is None or ev["actual_content"] is None)):
        return None, {"why": "empty_window", "sentinel": True}
    return float(p["surprise_score"]), {"surprise_score": p["surprise_score"]}


def _evidence_owned(cx, row_id):
    r = cx.execute("SELECT belief_id, claimed_state FROM owned_belief_expectations WHERE id=?",
                   (row_id,)).fetchone()
    claimed = json.loads(r["claimed_state"])
    bx = connect(f"file:{_db('beliefs')}?mode=ro", uri=True, timeout=30)
    bx.row_factory = Row
    try:
        b = bx.execute("SELECT tier, paused, erosion_stage FROM beliefs WHERE id=?",
                       (r["belief_id"],)).fetchone()
    finally:
        bx.close()
    if b is None:
        observed = {"exists": False}
        holds = False
    else:
        observed = {"exists": True, "tier": b["tier"], "paused": b["paused"],
                    "erosion_stage": b["erosion_stage"]}
        holds = (not b["paused"] and b["tier"] <= claimed["tier"]
                 and b["erosion_stage"] == claimed["erosion_stage"])
    return (0.0 if holds else 1.0), observed


# ---------------------------------------------------------------- reconcile --

def reconcile(now: Optional[float] = None) -> dict:
    """The single writer of every resolution."""
    now = time.time() if now is None else now
    ingested = ingest(now)
    cx = connect(_db("conversations"), timeout=30)
    cx.row_factory = Row
    stats = {"ingested": ingested, "confirmed": 0, "violated": 0, "unresolved": 0,
             "valence_nonzero": 0, "learned": 0}
    try:
        due = cx.execute("SELECT * FROM expectations WHERE state = 'open' AND horizon_at <= ? "
                         "ORDER BY id", (now,)).fetchall()
        for e in due:
            table, rid = e["producer"], e["producer_row_id"]
            if table == "self_predictions":
                d, ev = _evidence_self(cx, rid)
            elif table == "world_predictions":
                d, ev = _evidence_world(cx, rid)
            elif table == "predictions":
                d, ev = _evidence_surprise(rid)
            else:
                d, ev = _evidence_owned(cx, rid)
            if d is None:
                if ev.get("sentinel") or now >= e["horizon_at"] + EVIDENCE_GRACE_S:
                    _resolve(cx, e, "unresolved", now, None, None, None, ev)
                    stats["unresolved"] += 1
                continue
            state, ratio, sal = adjudicate(e["tolerance_basis"], e["tolerance"],
                                           e["salience_k"], d)
            _resolve(cx, e, state, now, d, ratio, sal, ev)
            stats[state] += 1
            v, admitted, reason = valence(state, sal, e["cost_band"], e["ownership"],
                                          e["confidence_basis"], e["confidence"])
            cx.execute("INSERT INTO event_valence (expectation_id, ts, valence, admitted, "
                       "reason, state, salience, cost_band, ownership) "
                       "VALUES (?,?,?,?,?,?,?,?,?)",
                       (e["id"], now, v, admitted, reason, state, sal, e["cost_band"],
                        e["ownership"]))
            if v != 0.0:
                stats["valence_nonzero"] += 1
                # The mood channel's only input. Written always; READ only when
                # NEX5_EXPECT_MOOD is on (affect_state).
                cx.execute("INSERT INTO affect_nudges (expectation_id, ts, valence) "
                           "VALUES (?,?,?)", (e["id"], now, v))
            if learning_on():
                stats["learned"] += _learn(cx, e, state, sal, now)
        cx.commit()
    finally:
        cx.close()
    if any(stats[k] for k in ("confirmed", "violated", "unresolved")):
        log.info("reconciler: %s", stats)
    return stats


def _resolve(cx, e, state, now, d, ratio, sal, evidence):
    cx.execute("UPDATE expectations SET state=?, resolved_at=?, resolved_by=?, discrepancy=?, "
               "ratio=?, salience=?, evidence=? WHERE id=?",
               (state, now, RECONCILER, d, ratio, sal, json.dumps(evidence), e["id"]))
    if e["producer"] == "owned_belief_expectations":
        cx.execute("UPDATE owned_belief_expectations SET state=?, resolved_at=?, "
                   "resolved_by=?, observed_state=? WHERE id=?",
                   (state, now, RECONCILER, json.dumps(evidence), e["producer_row_id"]))


def _learn(cx, e, state, sal, now) -> int:
    """R7: distribute a fixed step across the basis rows (resolved against the
    FROZEN snapshot). Runs on any basis -- learning is not valence. Seeded and
    locked rows are never touched. Confirms consolidate only at band >= 1.

    Ownership deliberately does NOT scale the step here: it would zero learning
    on an external basis, which R7 and the three-cell test require to move."""
    basis = json.loads(e["basis_snapshot"] or "[]")
    if not basis or state not in ("confirmed", "violated"):
        return 0
    if state == "confirmed" and not e["cost_band"]:
        return 0
    bx = connect(_db("beliefs"), timeout=30)
    try:
        rows = []
        for b in basis:
            if b.get("source_kind") == "seeded":
                continue
            live = bx.execute("SELECT confidence, locked FROM beliefs WHERE id=?",
                              (b["belief_id"],)).fetchone()
            if live is None or live[1]:
                continue
            rows.append((b["belief_id"], live[0]))
        if not rows:
            return 0
        n = len(rows)
        factor = (1.0 - LEARN_VIOLATE * sal / n) if state == "violated" \
            else (1.0 + LEARN_CONFIRM / n)
        for bid, before in rows:
            after = max(CONF_FLOOR, min(CONF_CEIL, before * factor))
            bx.execute("UPDATE beliefs SET confidence=? WHERE id=?", (after, bid))
            cx.execute("INSERT INTO expectation_learning_log (expectation_id, belief_id, ts, "
                       "before, after) VALUES (?,?,?,?,?)", (e["id"], bid, now, before, after))
        bx.commit()
        return n
    finally:
        bx.close()


# --------------------------------------------------------------- mood channel --

def mood_nudge(since: float, until: float, db_path=None) -> float:
    """The capped affect-valence nudge from event_valence in (since, until].
    One-way: this is read BY affect_state; nothing here reads mood."""
    cx = connect(f"file:{db_path or _db('conversations')}?mode=ro", uri=True, timeout=10)
    try:
        total = cx.execute("SELECT COALESCE(SUM(valence), 0) FROM affect_nudges "
                           "WHERE ts > ? AND ts <= ?", (since, until)).fetchone()[0]
    finally:
        cx.close()
    return max(-MOOD_CAP, min(MOOD_CAP, MOOD_GAIN * float(total)))


# ------------------------------------------------------------------ canaries --

def stakes_histogram(db_path=None) -> dict:
    """Per cost band: resolved rows, and how many carried non-zero valence."""
    cx = connect(f"file:{db_path or _db('conversations')}?mode=ro", uri=True, timeout=10)
    try:
        out = {}
        for band, n, nz in cx.execute(
                "SELECT cost_band, COUNT(*), SUM(valence != 0) FROM event_valence "
                "GROUP BY cost_band ORDER BY cost_band"):
            out[band] = {"resolved": n, "valence_nonzero": nz or 0}
        return out
    finally:
        cx.close()


def canaries(now: Optional[float] = None, window_s: float = 86400) -> list:
    """The four canaries, each (name, value, n, flag, detail)."""
    now = time.time() if now is None else now
    from theory_x.stage_world.owned_belief import confirmation_rate_canary
    c = confirmation_rate_canary()
    out = [("confirmation_rate", c["rate"], c["resolved"], c["flag"], "owned-belief")]

    h = stakes_histogram()
    band0_leak = sum(v["valence_nonzero"] for b, v in h.items() if not b)
    opened = sum(v["valence_nonzero"] for b, v in h.items() if b)
    total = sum(v["resolved"] for v in h.values())
    out.append(("stakes_gate", float(opened), total,
                bool(band0_leak or (total >= 20 and not opened)),
                json.dumps({"histogram": h, "band0_nonzero": band0_leak})))

    cx = connect(f"file:{_db('conversations')}?mode=ro", uri=True, timeout=10)
    try:
        rows = dict(cx.execute(
            "SELECT state = 'unresolved', COUNT(*) FROM expectations "
            "WHERE resolved_at > ? GROUP BY 1", (now - window_s,)).fetchall())
    finally:
        cx.close()
    n = sum(rows.values())
    rate = rows.get(1, 0) / n if n else None
    out.append(("unresolved_rate", rate, n, bool(n >= 20 and rate > 0.5),
                "most windows empty = degraded signal"))

    bx = connect(f"file:{_db('beliefs')}?mode=ro", uri=True, timeout=10)
    try:
        mean = bx.execute("SELECT AVG(confidence) FROM beliefs WHERE source_kind='authored' "
                          "AND locked=0").fetchone()[0]
    finally:
        bx.close()
    cx = connect(_db("conversations"), timeout=10)
    try:
        prev = [r[0] for r in cx.execute(
            "SELECT value FROM expectation_canary_log WHERE name='confidence_drift' "
            "ORDER BY id DESC LIMIT 4")][::-1]
    finally:
        cx.close()
    seq = prev + ([mean] if mean is not None else [])
    falling = len(seq) >= 5 and all(b < a for a, b in zip(seq, seq[1:]))
    out.append(("confidence_drift", mean, len(seq), falling,
                "mean authored confidence; 5 straight falls = learning step too large"))
    return out


def record_canaries(now: Optional[float] = None) -> str:
    now = time.time() if now is None else now
    rows = canaries(now)
    cx = connect(_db("conversations"), timeout=10)
    try:
        for name, value, n, flag, detail in rows:
            cx.execute("INSERT INTO expectation_canary_log (ts, name, value, n, flag, detail) "
                       "VALUES (?,?,?,?,?,?)", (now, name, value, n, int(flag), detail))
        cx.commit()
    finally:
        cx.close()
    flagged = [r[0] for r in rows if r[3]]
    parts = [f"{r[0]}={'n/a' if r[1] is None else round(r[1], 3)} (n={r[2]})" for r in rows]
    msg = "; ".join(parts) + (f" -- CANARY: {', '.join(flagged)}" if flagged else "")
    (log.warning if flagged else log.info)("expectation canaries: %s", msg)
    return msg
