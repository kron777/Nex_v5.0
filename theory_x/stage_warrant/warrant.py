"""Warrant — how EARNED a belief is (NEX5_WARRANT, default OFF).

Built because conviction failed on its support score: centrality measures how
connected a belief is, which on this graph means how GENERIC it is (support vs
question-relevance -0.21). Warrant is composed from what the graph records about
a belief having been challenged, relied on over time, and grounded from more
than one place — and it leans away from connectivity.

COMPONENTS (each in [0, 1]):
  survival  0.35  Time held at an AT-RISK tier without decaying. Decay is the
                  only recurring challenge the substrate applies (promotion.py
                  decay_pass: 5->6, 6->7; T7 is a no-op there), so a belief is
                  at risk only while at T5/T6. Rebuilt from promotion_log's
                  timeline: credit for each at-risk interval that ENDED IN
                  PROMOTION or is still open; none for one that ended in decay.
                  1 - exp(-days / 7), halved per decay, zeroed if the harmonizer
                  marked it paradox / both_deleted or a decisive_contradiction
                  demoted it. Locked keystones (hand-seeded, harmonizer-
                  protected) read 1.0 by construction.
  sustain   0.35  Distinct DAYS on which the belief was relied on: anchored a
                  fire (fountain_events.anchor_belief_id), was the walk anchor
                  (substrate_snapshots), was a synthesis parent (belief_lineage,
                  synergizer_log), joined an arc (arc_members), or was retrieved
                  into a fire (fountain_retrieval_log). One day = a burst = 0.
                  log1p(days - 1) / log1p(6), capped. Edge traversal stamps are
                  NOT used: they scale with degree.
  indep     0.20  Distinct OTHER branches among its grounds (synthesis parents,
                  synthesises neighbours, supports-edge sources); own branch
                  excluded. min(1, n / 3) — saturates fast, so a hub is not
                  rewarded for being a hub.
  xsynth    0.10  synthesises edges to beliefs of another branch,
                  log1p(n) / log1p(20), capped. The one connectivity-flavoured
                  term, given the least weight.
NOT used: corroboration_count (matches on feed metadata — raw news 30% vs
syntheses 4.9% — and is wiped on every promotion) and raw edge degree.

PERSISTENCE: a side table belief_warrant in beliefs.db, written by a BACKGROUND
pass through the shared beliefs Writer (never on the fire/chat path). Nothing
that updates `beliefs` touches it, so promotion cannot reset it. Created only
when armed; with NEX5_WARRANT unset nothing here runs.

HONESTY: warrant is the functional role "how earned is this belief" over the
records the graph keeps. It is not a feeling of conviction. No sentience verdict.

FAIL-SAFE: compute errors are recorded and the pass is skipped; persistence
failures leave the previous table in place.
"""
from __future__ import annotations

import json
import math
import os
import threading
import time
from collections import defaultdict
from typing import Optional

__all__ = ["compute_all", "combine", "persist", "WarrantPass", "WEIGHTS"]

_LOG_SOURCE = "warrant"
WEIGHTS = {"survival": 0.35, "sustain": 0.35, "indep": 0.20, "xsynth": 0.10}
_RISK_TIERS = (5, 6)
_SURV_TAU_DAYS = 7.0
_SUSTAIN_REF_DAYS = 7          # 7 distinct days of reliance = full
_INDEP_REF = 3
_XSYNTH_REF = 20
_INTERVAL_S = 6 * 3600
_FIRST_RUN_DELAY_S = 600
_BATCH = 500
_DAY = 86400.0


def _days(ts_iter) -> set:
    return {int(t // _DAY) for t in ts_iter if t}


def _survival(tier, locked, created_at, plog, marked, now):
    if locked and tier <= 2:
        return 1.0
    if marked:
        return 0.0
    try:
        events = sorted(json.loads(plog or "[]"), key=lambda e: e.get("ts") or 0)
    except Exception:
        events = []
    cur = events[0].get("from", tier) if events else tier
    t = float(created_at or now)
    survived = 0.0
    decays = 0
    for e in events:
        ev, ts = e.get("event"), float(e.get("ts") or t)
        if ev == "decisive_contradiction":
            return 0.0
        if ev == "decay":
            decays += 1                      # interval ended in failure: no credit
        elif cur in _RISK_TIERS:
            survived += max(0.0, ts - t)     # held at risk until promoted out
        cur = e.get("to", cur)
        t = ts
    if cur in _RISK_TIERS:
        survived += max(0.0, now - t)        # still holding
    return (1.0 - math.exp(-(survived / _DAY) / _SURV_TAU_DAYS)) * (0.5 ** decays)


def combine(c: dict, w: dict = None) -> float:
    w = WEIGHTS if w is None else w
    return sum(w[k] * c[k] for k in w) / sum(w.values())


def compute_all(beliefs_db: str = None, dynamic_db: str = None,
                now: float = None, max_tier: int = 7) -> dict:
    """{belief_id: {"warrant", "survival", "sustain", "indep", "xsynth",
    "sustain_days", "indep_n", "xsynth_n"}} over unpaused beliefs with
    tier <= max_tier. Read-only (Reader, mode=ro)."""
    from substrate import Reader, db_paths
    paths = db_paths()
    bdb = beliefs_db or str(paths["beliefs"])
    ddb = dynamic_db or str(paths["dynamic"])
    now = time.time() if now is None else now

    with Reader(bdb).connection() as b:
        rows = b.execute(
            "SELECT id, tier, locked, branch_id, created_at, promotion_log "
            "FROM beliefs WHERE paused = 0 AND tier <= ?", (max_tier,)).fetchall()
        branch = {r[0]: r[3] for r in rows}
        # all branches, for neighbours outside the scored set
        for i, br in b.execute("SELECT id, branch_id FROM beliefs"):
            branch.setdefault(i, br)
        synth_nb = defaultdict(set)
        supports_src = defaultdict(set)
        for s, t, typ in b.execute(
                "SELECT source_id, target_id, edge_type FROM belief_edges "
                "WHERE edge_type IN ('synthesises', 'supports')"):
            if typ == "synthesises":
                synth_nb[s].add(t); synth_nb[t].add(s)
            else:
                supports_src[t].add(s)
        parents = defaultdict(set)
        use_ts = defaultdict(list)
        for child, parent, ts in b.execute(
                "SELECT child_id, parent_id, created_at FROM belief_lineage"):
            parents[child].add(parent)
            use_ts[parent].append(ts)
        for a, c, ts in b.execute("SELECT belief_id_a, belief_id_b, ts FROM synergizer_log"):
            use_ts[a].append(ts); use_ts[c].append(ts)
        for bid, ts in b.execute("SELECT belief_id, joined_at FROM arc_members"):
            use_ts[bid].append(ts)

    marked = set()
    with Reader(ddb).connection() as d:
        for bid, ts in d.execute(
                "SELECT anchor_belief_id, ts FROM fountain_events "
                "WHERE anchor_belief_id IS NOT NULL"):
            use_ts[bid].append(ts)
        for bid, ts in d.execute(
                "SELECT walk_anchor_id, ts FROM substrate_snapshots "
                "WHERE walk_anchor_id IS NOT NULL"):
            use_ts[bid].append(ts)
        for bid, ts in d.execute("SELECT belief_id, ts FROM fountain_retrieval_log"):
            use_ts[bid].append(ts)
        for a, c in d.execute(
                "SELECT belief_id_a, belief_id_b FROM harmonizer_events "
                "WHERE resolution IN ('paradox', 'both_deleted')"):
            marked.add(a); marked.add(c)

    out = {}
    for bid, tier, locked, br, created_at, plog in rows:
        surv = _survival(tier, locked, created_at, plog, bid in marked, now)
        ndays = len(_days(use_ts.get(bid, ())))
        sus = min(1.0, math.log1p(max(0, ndays - 1)) / math.log1p(_SUSTAIN_REF_DAYS - 1))
        grounds = parents.get(bid, set()) | synth_nb.get(bid, set()) | supports_src.get(bid, set())
        other = {branch.get(g) for g in grounds} - {br, None}
        ind = min(1.0, len(other) / _INDEP_REF)
        nx = sum(1 for g in synth_nb.get(bid, ()) if branch.get(g) not in (br, None))
        xs = min(1.0, math.log1p(nx) / math.log1p(_XSYNTH_REF))
        c = {"survival": surv, "sustain": sus, "indep": ind, "xsynth": xs}
        c["warrant"] = combine(c)
        c.update({"sustain_days": ndays, "indep_n": len(other), "xsynth_n": nx})
        out[bid] = c
    return out


_DDL = ("CREATE TABLE IF NOT EXISTS belief_warrant ("
        "belief_id INTEGER PRIMARY KEY, warrant REAL NOT NULL, survival REAL, "
        "sustain REAL, indep REAL, xsynth REAL, sustain_days INTEGER, "
        "computed_at REAL NOT NULL)")


def persist(writer, results: dict, now: float = None) -> int:
    """Upsert results through the shared beliefs Writer, in batches."""
    now = time.time() if now is None else now
    writer.write(_DDL)
    sql = ("INSERT INTO belief_warrant (belief_id, warrant, survival, sustain, indep, "
           "xsynth, sustain_days, computed_at) VALUES (?,?,?,?,?,?,?,?) "
           "ON CONFLICT(belief_id) DO UPDATE SET warrant=excluded.warrant, "
           "survival=excluded.survival, sustain=excluded.sustain, indep=excluded.indep, "
           "xsynth=excluded.xsynth, sustain_days=excluded.sustain_days, "
           "computed_at=excluded.computed_at")
    items = list(results.items())
    n = 0
    from theory_x.stage_warrant.recorder import write_batch   # wrapper-safe
    for i in range(0, len(items), _BATCH):
        write_batch(writer, [(sql, (bid, c["warrant"], c["survival"], c["sustain"],
                                    c["indep"], c["xsynth"], c["sustain_days"], now))
                             for bid, c in items[i:i + _BATCH]])
        n += len(items[i:i + _BATCH])
    return n


class WarrantPass:
    """Background pass: recompute and persist every _INTERVAL_S. Constructed
    and started only when NEX5_WARRANT=1 (run.py). Never on the fire path."""

    name = "warrant"

    def __init__(self, beliefs_writer, interval_s: int = _INTERVAL_S,
                 first_delay_s: int = _FIRST_RUN_DELAY_S) -> None:
        self._w = beliefs_writer
        self._interval = interval_s
        self._delay = first_delay_s
        self._last: Optional[dict] = None

    def run_once(self) -> dict:
        t0 = time.time()
        res = compute_all(now=t0)
        n = persist(self._w, res, now=t0)
        self._last = {"rows": n, "secs": round(time.time() - t0, 1), "at": t0}
        return self._last

    def _loop(self) -> None:
        import errors
        time.sleep(self._delay)
        while True:
            try:
                info = self.run_once()
                errors.record(f"warrant pass: {info['rows']} beliefs in {info['secs']}s",
                              source=_LOG_SOURCE, level="INFO")
            except Exception as exc:
                errors.record(f"warrant pass failed (non-fatal): {exc}",
                              source=_LOG_SOURCE, exc=exc)
            time.sleep(self._interval)

    def start_loop(self) -> None:
        if os.environ.get("NEX5_WARRANT") != "1":
            return
        threading.Thread(target=self._loop, daemon=True, name="warrant_pass").start()

    def state(self, now: Optional[float] = None) -> dict:
        return {"name": self.name, "last": self._last}
