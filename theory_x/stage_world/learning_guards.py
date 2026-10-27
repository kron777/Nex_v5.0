"""Guards on the learning channel's external-basis mode (Beam: learning stays ON).

Learning is not ownership-scaled (R7), so expectations resting on sensed material
move the confidence of her own beliefs with no valence trace. "External drift >
owned drift" stays visible (observational) but is no longer the guard. The guards:

  G1  PER-BELIEF CAP (NEX5_LEARN_CAP, dark). Before an external-basis delta d is
      applied to a belief whose source_kind is in OWNED_KINDS (authored, self):
      if cumulative_external(X) + |d| > 0.02 it is SKIPPED -- never clipped, never
      partially applied -- and logged as a skipped row (no factor) plus one
      deduplicated finding. cumulative_external is the live SIGNED sum of the
      belief's external-basis deltas and of the subtractions applied to it, both
      read from the logs (never a separate accumulator). Owned-basis learning is
      uncapped. A per-belief BACKSTOP: it would not have caught 27 Oct (largest
      per-belief cumulative 0.003) -- that incident was population-level (G4).
  G2  RATIO, two tiers. Observational: external > owned over the trailing 24h,
      any margin, always shown. Action (NEX5_LEARN_RATIO_SUBTRACT, dark): external
      >= 2x owned at EVERY evaluation tick across a fully covered trailing 24h ->
      that window's external contribution is subtracted exactly, REVIEW-REQUIRED,
      reversible, idempotent per window id. No undo event, no valence, no
      resolution: it corrects a learning step; it is not a substantive event.
  G3  SIGN SYMMETRY: up/down split and the current run length of external-basis
      deltas. Persistent one-directional = trailing 7d, n >= 50, >= 3 days of
      data, >= 95% one sign AND a current run >= 50: a ratchet, a finding
      regardless of magnitude.
  G4  BASIS COMPOSITION, in two places: (a) the FROZEN basis_snapshots of the
      expectations made, split by producer; (b) the surprise producer's SAMPLING
      POOL (her ten most recent beliefs), which skews first. Sustained skew = the
      last 3 daily readings of either all >= 0.6.

Subtraction rule (Part 2, NEX5_LEARN_ATTRIBUTION_SUBTRACT, dark): per belief over
the trailing 24h aggregate, ATTRIBUTION FAILURE = its net movement is external-
sourced (|net external| > eps) while |net owned| <= eps, eps = half the smallest
owned step ever observed. Magnitude alone never triggers it. A scheduled
counterfactual reconstruction flags MATERIAL when removing external contributions
moves a belief across a confidence threshold the code actually decides on:
0.15 (retrieval, drive_emergence, novel_association), 0.4 (time_fetch), 0.5
(refinement_engine, synergizer, Beam's ownership line), 0.6 (emergent_drives).
(Tier ordering, affinity >= 4 eligibility and commit/abstain read tier or
keywords, not confidence; confidence-RANK comparisons are not evaluated.)
"""
from __future__ import annotations

import json
import logging
import os
import time
from typing import Optional

from substrate import connect

log = logging.getLogger("theory_x.stage_world.learning_guards")

EXTERNAL_CAP = 0.02
OWNED_KINDS = ("authored", "self")
RATIO = 2.0
WINDOW_S = 86400.0
TICK_S = 900.0
TICK_COVERAGE = 0.9                    # share of expected ticks a "fully covered" 24h needs
RATCHET_DAYS, RATCHET_N, RATCHET_SHARE, RATCHET_RUN = 3, 50, 0.95, 50
SKEW_DAYS, SKEW_MIN = 3, 0.6
DECISION_THRESHOLDS = (0.15, 0.4, 0.5, 0.6)
POOL_SIZE = 10                         # predictive_substrate._RECENT_BELIEF_COUNT


def cap_on() -> bool:
    return os.environ.get("NEX5_LEARN_CAP") == "1"


def ratio_subtract_on() -> bool:
    return os.environ.get("NEX5_LEARN_RATIO_SUBTRACT") == "1"


def attribution_subtract_on() -> bool:
    return os.environ.get("NEX5_LEARN_ATTRIBUTION_SUBTRACT") == "1"


def _x():
    from theory_x.stage_world import expectations
    return expectations


def _db(name):
    return _x()._db(name)


def _ro(name):
    return connect(f"file:{_db(name)}?mode=ro", uri=True, timeout=10)


# ---------------------------------------------------------------------- G1 --

def cumulative_external(cx, belief_id) -> float:
    """Signed: the belief's external-basis deltas plus the (negative)
    subtractions applied to it and not reverted -- read live from the logs."""
    added = cx.execute("SELECT COALESCE(SUM(after - before), 0) FROM expectation_learning_log "
                       "WHERE belief_id = ? AND basis_kind != 'owned'", (belief_id,)).fetchone()[0]
    subtracted = cx.execute("SELECT COALESCE(SUM(after - before), 0) FROM learning_subtractions "
                            "WHERE belief_id = ? AND reverted_at IS NULL",
                            (belief_id,)).fetchone()[0]
    return float(added) + float(subtracted)


def cap_blocks(cx, e, belief_id, source_kind, delta, now) -> bool:
    """True when an external-basis delta must be SKIPPED (G1). The caller logs
    the skipped row; the finding is written here, once per belief until a
    subtraction reopens headroom."""
    if not cap_on() or e["basis_kind"] == "owned" or source_kind not in OWNED_KINDS:
        return False
    cum = cumulative_external(cx, belief_id)
    if cum + abs(delta) <= EXTERNAL_CAP:
        return False
    last_hit = cx.execute("SELECT MAX(ts) FROM learning_cap_hits WHERE belief_id = ?",
                          (belief_id,)).fetchone()[0]
    last_sub = cx.execute("SELECT MAX(ts) FROM learning_subtractions WHERE belief_id = ?",
                          (belief_id,)).fetchone()[0]
    if last_hit is None or (last_sub is not None and last_sub > last_hit):
        cx.execute("INSERT INTO learning_cap_hits (ts, belief_id, expectation_id, contribution) "
                   "VALUES (?, ?, ?, ?)", (now, belief_id, e["id"], cum))
        log.warning("external cap hit: belief %s (cumulative %.4f + %.4f > %.2f)",
                    belief_id, cum, abs(delta), EXTERNAL_CAP)
    return True


def over_cap() -> list:
    """Beliefs whose standing external contribution already exceeds the cap --
    report at flip time; the cap then freezes them (no further external delta)."""
    cx = _ro("conversations")
    try:
        ids = [r[0] for r in cx.execute("SELECT DISTINCT belief_id FROM expectation_learning_log "
                                        "WHERE basis_kind != 'owned' AND source_kind IN "
                                        "('authored', 'self')")]
        return [(b, c) for b in ids if abs(c := cumulative_external(cx, b)) > EXTERNAL_CAP]
    finally:
        cx.close()


# ------------------------------------------------------------------ G2 ticks --

def _window_sums(cx, lo, hi):
    rows = cx.execute("SELECT after - before, basis_kind FROM expectation_learning_log "
                      "WHERE source_kind IN ('authored', 'self') AND ts > ? AND ts <= ?",
                      (lo, hi)).fetchall()
    ext = sum(abs(d) for d, k in rows if k != "owned")
    own = sum(abs(d) for d, k in rows if k == "owned")
    return ext, own


def _pool_share() -> Optional[float]:
    bx = _ro("beliefs")
    try:
        kinds = [r[0] for r in bx.execute("SELECT source_kind FROM beliefs ORDER BY created_at "
                                          "DESC LIMIT ?", (POOL_SIZE,))]
    finally:
        bx.close()
    return sum(k not in OWNED_KINDS for k in kinds) / len(kinds) if kinds else None


def record_tick(now: Optional[float] = None) -> dict:
    """One evaluation tick (each reconciler pass): the trailing-24h external and
    owned drift on owned-kind beliefs, and the sampling pool's external share."""
    now = time.time() if now is None else now
    cx = connect(_db("conversations"), timeout=10)
    try:
        ext, own = _window_sums(cx, now - WINDOW_S, now)
        share = _pool_share()
        cx.execute("INSERT INTO learning_guard_ticks (ts, external, owned, pool_external_share) "
                   "VALUES (?, ?, ?, ?)", (now, ext, own, share))
        cx.commit()
    finally:
        cx.close()
    return {"external": ext, "owned": own, "pool_external_share": share}


def ratio_status(now: Optional[float] = None) -> dict:
    now = time.time() if now is None else now
    cx = _ro("conversations")
    try:
        ext, own = _window_sums(cx, now - WINDOW_S, now)
        ticks = cx.execute("SELECT ts, external, owned FROM learning_guard_ticks "
                           "WHERE ts > ? AND ts <= ? ORDER BY ts", (now - WINDOW_S, now)).fetchall()
    finally:
        cx.close()
    covered = bool(ticks) and ticks[0][0] <= now - WINDOW_S + 2 * TICK_S and \
        len(ticks) >= TICK_COVERAGE * WINDOW_S / TICK_S
    sustained = covered and all(e > 0 and e >= RATIO * o for _, e, o in ticks)
    return {"external": ext, "owned": own, "observational": ext > own, "ticks": len(ticks),
            "covered_24h": covered, "sustained_2x": sustained}


# ----------------------------------------------------------- subtractions --

def _owned_eps(cx) -> float:
    m = cx.execute("SELECT MIN(ABS(after - before)) FROM expectation_learning_log "
                   "WHERE basis_kind = 'owned' AND after != before").fetchone()[0]
    return 0.5 * float(m) if m else 0.5 * 0.05 * 0.015 / POOL_SIZE   # theoretical min step


def attribution_failures(now: Optional[float] = None) -> dict:
    """Per belief, trailing 24h aggregate: net external movement while net owned ~= 0."""
    now = time.time() if now is None else now
    cx = _ro("conversations")
    try:
        eps = _owned_eps(cx)
        rows = cx.execute(
            "SELECT belief_id, SUM(CASE WHEN basis_kind != 'owned' THEN after - before ELSE 0 END), "
            "SUM(CASE WHEN basis_kind = 'owned' THEN after - before ELSE 0 END) "
            "FROM expectation_learning_log WHERE source_kind IN ('authored', 'self') "
            "AND ts > ? AND ts <= ? GROUP BY belief_id", (now - WINDOW_S, now)).fetchall()
    finally:
        cx.close()
    failed = [b for b, ne, no in rows if abs(ne) > eps and abs(no) <= eps]
    return {"eps": eps, "beliefs": len(rows), "failed": failed}


def subtract(belief_ids, lo, hi, trigger, window_id, now: Optional[float] = None) -> int:
    """Remove EXACTLY the not-yet-subtracted external-basis deltas in (lo, hi]
    from each belief: confidence becomes the replay with those deltas excluded and
    everything else (earlier subtractions included) carried through. Idempotent
    per (window_id, belief). Writes no undo event, no valence, no resolution."""
    now = time.time() if now is None else now
    X = _x()
    cx = connect(_db("conversations"), timeout=30)
    n = 0
    try:
        done = set()
        for (ids,) in cx.execute("SELECT delta_ids FROM learning_subtractions "
                                 "WHERE reverted_at IS NULL"):
            done.update(json.loads(ids))
        bx = connect(_db("beliefs"), timeout=30)
        try:
            for bid in belief_ids:
                if cx.execute("SELECT 1 FROM learning_subtractions WHERE window_id = ? AND "
                              "belief_id = ?", (window_id, bid)).fetchone():
                    continue
                ids = {r[0] for r in cx.execute(
                    "SELECT id FROM expectation_learning_log WHERE belief_id = ? AND "
                    "basis_kind != 'owned' AND ts > ? AND ts <= ? AND COALESCE(skipped, 0) = 0",
                    (bid, lo, hi))} - done
                cur = bx.execute("SELECT confidence FROM beliefs WHERE id = ?", (bid,)).fetchone()
                if not ids or cur is None:
                    continue
                r = X.replay(bid, cur[0], lambda row, ids=ids: row["id"] in ids, False)
                if not r["reconstructable"]:
                    continue
                bx.execute("UPDATE beliefs SET confidence = ? WHERE id = ?", (r["confidence"], bid))
                cx.execute("INSERT INTO learning_subtractions (ts, belief_id, window_start, "
                           "window_end, window_id, trigger, before, after, delta_ids, "
                           "review_required) VALUES (?,?,?,?,?,?,?,?,?,1)",
                           (now, bid, lo, hi, window_id, trigger, cur[0], r["confidence"],
                            json.dumps(sorted(ids))))
                n += 1
            bx.commit()
        finally:
            bx.close()
        cx.commit()
    finally:
        cx.close()
    if n:
        log.warning("learning guard: %s subtracted external contribution from %d beliefs "
                    "(window %s) -- REVIEW REQUIRED", trigger, n, window_id)
    return n


def revert_subtraction(subtraction_id: int, now: Optional[float] = None) -> None:
    """Undo a subtraction additively (later learning stays as it happened)."""
    now = time.time() if now is None else now
    cx = connect(_db("conversations"), timeout=30)
    try:
        bid, before, after, reverted = cx.execute(
            "SELECT belief_id, before, after, reverted_at FROM learning_subtractions WHERE id=?",
            (subtraction_id,)).fetchone()
        if reverted is not None:
            return
        bx = connect(_db("beliefs"), timeout=30)
        try:
            bx.execute("UPDATE beliefs SET confidence = confidence + ? WHERE id = ?",
                       (before - after, bid))
            bx.commit()
        finally:
            bx.close()
        cx.execute("UPDATE learning_subtractions SET reverted_at = ? WHERE id = ?",
                   (now, subtraction_id))
        cx.commit()
    finally:
        cx.close()


def run(now: Optional[float] = None) -> dict:
    """The nightly pass: G2 action tier and the attribution rule, each only
    when its own flag is on."""
    now = time.time() if now is None else now
    day = time.strftime("%Y-%m-%d", time.gmtime(now))
    out = {"ratio": ratio_status(now), "attribution": attribution_failures(now),
           "subtracted": 0}
    if out["ratio"]["sustained_2x"] and ratio_subtract_on():
        cx = _ro("conversations")
        try:
            ids = [r[0] for r in cx.execute(
                "SELECT DISTINCT belief_id FROM expectation_learning_log WHERE basis_kind != "
                "'owned' AND source_kind IN ('authored', 'self') AND ts > ?", (now - WINDOW_S,))]
        finally:
            cx.close()
        out["subtracted"] += subtract(ids, now - WINDOW_S, now, "ratio_2x_24h", f"ratio:{day}", now)
    if out["attribution"]["failed"] and attribution_subtract_on():
        out["subtracted"] += subtract(out["attribution"]["failed"], now - WINDOW_S, now,
                                      "attribution_failure", f"attribution:{day}", now)
    return out


# ---------------------------------------------------------------------- G3 --

def sign_symmetry(now: Optional[float] = None, days: int = 7) -> dict:
    now = time.time() if now is None else now
    cx = _ro("conversations")
    try:
        rows = cx.execute("SELECT ts, after - before FROM expectation_learning_log WHERE "
                          "basis_kind != 'owned' AND after != before AND ts > ? ORDER BY id",
                          (now - days * 86400,)).fetchall()
    finally:
        cx.close()
    up = sum(d > 0 for _, d in rows)
    down = len(rows) - up
    up24 = sum(d > 0 for t, d in rows if t > now - 86400)
    down24 = sum(d < 0 for t, d in rows if t > now - 86400)
    run = 0
    for _, d in reversed(rows):
        if run and (d > 0) != last_up:
            break
        last_up, run = d > 0, run + 1
    span = (now - rows[0][0]) / 86400 if rows else 0.0
    share = max(up, down) / len(rows) if rows else None
    ratchet = bool(len(rows) >= RATCHET_N and span >= RATCHET_DAYS
                   and share >= RATCHET_SHARE and run >= RATCHET_RUN)
    return {"up": up, "down": down, "up_24h": up24, "down_24h": down24, "n": len(rows),
            "run": run, "span_days": round(span, 2), "majority_share": share, "ratchet": ratchet}


# ---------------------------------------------------------------------- G4 --

def composition(now: Optional[float] = None, window_s: float = 86400) -> dict:
    """External share (a) in the frozen snapshots of expectations made in the
    window, per producer, and (b) in the surprise producer's sampling pool
    (mean of the ticks in the window)."""
    now = time.time() if now is None else now
    cx = _ro("conversations")
    try:
        snaps = cx.execute("SELECT producer, basis_snapshot FROM expectations WHERE producer IN "
                           "('predictions', 'owned_belief_expectations') AND made_at > ? AND "
                           "made_at <= ?", (now - window_s, now)).fetchall()
        pool = cx.execute("SELECT AVG(pool_external_share) FROM learning_guard_ticks WHERE "
                          "ts > ? AND ts <= ?", (now - window_s, now)).fetchone()[0]
        history = {name: [r[0] for r in cx.execute(
            "SELECT value FROM expectation_canary_log WHERE name = ? AND value IS NOT NULL "
            "ORDER BY id DESC LIMIT ?", (name, SKEW_DAYS - 1))][::-1]
            for name in ("composition.surprise", "composition.pool")}
    finally:
        cx.close()
    counts = {"predictions": [0, 0], "owned_belief_expectations": [0, 0]}
    for producer, snap in snaps:
        for b in json.loads(snap or "[]"):
            counts[producer][0] += 1
            counts[producer][1] += b.get("source_kind") not in OWNED_KINDS
    share = {p: (ext / tot if tot else None) for p, (tot, ext) in counts.items()}
    out = {"surprise": share["predictions"], "owned_belief": share["owned_belief_expectations"],
           "pool": pool, "skew": False, "series": {}}
    for name, cur in (("composition.surprise", out["surprise"]), ("composition.pool", pool)):
        seq = history[name] + ([cur] if cur is not None else [])
        out["series"][name] = seq
        if len(seq) >= SKEW_DAYS and all(v >= SKEW_MIN for v in seq[-SKEW_DAYS:]):
            out["skew"] = True
    return out


# --------------------------------------------------- scheduled reconstruction --

def counterfactual_material() -> dict:
    X = _x()
    cx = _ro("conversations")
    try:
        ids = [r[0] for r in cx.execute("SELECT DISTINCT belief_id FROM expectation_learning_log "
                                        "WHERE basis_kind != 'owned' AND source_kind IN "
                                        "('authored', 'self')")]
    finally:
        cx.close()
    bx = _ro("beliefs")
    try:
        cur = {i: bx.execute("SELECT confidence FROM beliefs WHERE id=?", (i,)).fetchone()
               for i in ids}
    finally:
        bx.close()
    material = []
    for bid, row in cur.items():
        if row is None:
            continue
        r = X.reconstruct_without_external(bid, row[0])
        if not r["reconstructable"]:
            continue
        crossed = [t for t in DECISION_THRESHOLDS if (row[0] >= t) != (r["confidence"] >= t)]
        if crossed:
            material.append({"belief_id": bid, "actual": row[0],
                             "without_external": r["confidence"], "crosses": crossed})
    return {"checked": len(ids), "material": material}


def canary_rows(now: Optional[float] = None) -> list:
    now = time.time() if now is None else now
    cx = _ro("conversations")
    try:
        hits = cx.execute("SELECT COUNT(DISTINCT belief_id) FROM learning_cap_hits").fetchone()[0]
        pending = cx.execute("SELECT COUNT(*) FROM learning_subtractions WHERE "
                             "review_required = 1 AND reverted_at IS NULL").fetchone()[0]
    finally:
        cx.close()
    over = over_cap()
    r = ratio_status(now)
    a = attribution_failures(now)
    s = sign_symmetry(now)
    c = composition(now)
    m = counterfactual_material()
    return [
        ("external_cap_hits", float(hits), hits, hits > 0, f"G1 cap {EXTERNAL_CAP}; flag "
         f"{'ON' if cap_on() else 'OFF (external channel UNCAPPED)'}"),
        ("over_cap_now", float(len(over)), len(over), bool(over), json.dumps(over[:10])),
        ("ratio_observational", r["external"], r["ticks"], r["observational"],
         f"external {r['external']:.4f} vs owned {r['owned']:.4f} (24h) -- observational"),
        ("ratio_2x_sustained", float(r["sustained_2x"]), r["ticks"], r["sustained_2x"],
         f"every tick >= 2x over a covered 24h: covered={r['covered_24h']}"),
        ("attribution_failure", float(len(a["failed"])), a["beliefs"], bool(a["failed"]),
         f"eps={a['eps']:.6f}; beliefs whose 24h movement is external-only"),
        ("subtractions_pending_review", float(pending), pending, pending > 0,
         "subtracted, REVIEW-REQUIRED, reversible"),
        ("sign_symmetry", s["majority_share"], s["n"], s["ratchet"],
         f"7d up/down {s['up']}/{s['down']}, 24h {s['up_24h']}/{s['down_24h']}, "
         f"run {s['run']}, span {s['span_days']}d"),
        ("composition.surprise", c["surprise"], 0, c["skew"], "frozen snapshots, surprise"),
        ("composition.owned_belief", c["owned_belief"], 0, False, "frozen snapshots, owned"),
        ("composition.pool", c["pool"], 0, c["skew"], "sampling pool: 10 most recent beliefs"),
        ("counterfactual_material", float(len(m["material"])), m["checked"],
         bool(m["material"]), json.dumps(m["material"][:10])),
    ]
