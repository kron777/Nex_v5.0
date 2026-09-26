"""Warrant recorder — START RECORDING earned-ness (NEX5_WARRANT_RECORD, default OFF).

Warrant failed its 2026-09-26 gate because the graph does not record earned-ness:
survival covered 7.6% of beliefs, sustained use 1.6%. This module only RECORDS —
append-only side tables in beliefs.db, a background thread, no change to what
she thinks, retrieves or says — so warrant can be re-validated once signal accrues.

1. SURVIVAL — belief_survival (append-only): one row per belief per check,
   (belief_id, ts, check_type, passed, tier). check_type 'conflict_window'.
   The live harmonizer cannot supply this: its scan is `ORDER BY tier ASC LIMIT
   200` and T3 holds ~9.5k counterfactual_node templates, so every run examines
   the SAME 200 T3 templates and never reaches T5-T7. Logging its passes would
   credit only generic templates. So this runs a SHADOW check with the
   harmonizer's own detector (_conflict_score, threshold 0.15) over a rotating
   id-cursor window stratified across T3 / T5-6 / T7 — every unlocked, unpaused
   belief is eventually checked, T7 included. Read-only: it never marks,
   retires or writes an edge.

2. USE DAYS — belief_use_day (belief_id, day) PK, INSERT OR IGNORE, plus the
   incremental counter belief_use_days (belief_id, days, first_day, last_day).
   Fed by cursor from the records of a belief actually being used:
   fountain_retrieval_log (her fire retrievals — kept across restarts by the
   same flag, see generator.py), fountain_events.anchor_belief_id,
   synergizer_log (synthesis parents), belief_lineage parents, arc_members joins.
   NOT fed from last_referenced_at: only corroboration stamps it (feed metadata).
   First run back-fills from whatever history those sources hold.

Cursors live in warrant_record_cursor. FAIL-SAFE: every cycle is wrapped; an
error is recorded and the cycle skipped. HONESTY: these are records of use and
of surviving a conflict check — the raw material of "how earned", not a feeling.
"""
from __future__ import annotations

import os
import threading
import time
from typing import Optional

__all__ = ["WarrantRecorder", "write_batch", "shadow_conflict_check"]

_LOG_SOURCE = "warrant_recorder"
_DAY = 86400
_BANDS = ((3, 3), (5, 6), (7, 7))
_PER_BAND = 100
_CONFLICT_THRESHOLD = 0.15          # harmonizer.scan_for_conflicts
_SURVIVAL_INTERVAL_S = 3600
_USE_INTERVAL_S = 900
_FIRST_DELAY_S = 300
_USE_BATCH = 20000

_DDL = (
    "CREATE TABLE IF NOT EXISTS belief_survival ("
    " id INTEGER PRIMARY KEY AUTOINCREMENT, belief_id INTEGER NOT NULL,"
    " ts REAL NOT NULL, check_type TEXT NOT NULL, passed INTEGER NOT NULL,"
    " tier INTEGER)",
    "CREATE INDEX IF NOT EXISTS idx_belief_survival_belief ON belief_survival(belief_id)",
    "CREATE TABLE IF NOT EXISTS belief_use_day ("
    " belief_id INTEGER NOT NULL, day INTEGER NOT NULL, PRIMARY KEY (belief_id, day))",
    "CREATE TABLE IF NOT EXISTS belief_use_days ("
    " belief_id INTEGER PRIMARY KEY, days INTEGER NOT NULL, first_day INTEGER,"
    " last_day INTEGER, updated_at REAL)",
    "CREATE TABLE IF NOT EXISTS warrant_record_cursor ("
    " name TEXT PRIMARY KEY, value REAL NOT NULL)",
)


def write_batch(writer, stmts: list) -> None:
    """write_many when the writer has it; the TaggingBeliefWriter wrapper on
    beliefs does not, so fall back to sequential writes."""
    if not stmts:
        return
    wm = getattr(writer, "write_many", None)
    if wm is not None:
        wm(stmts)
    else:
        for sql, params in stmts:
            writer.write(sql, params)


def shadow_conflict_check(rows: list) -> dict:
    """{belief_id: passed} for a window of {id, content} rows, using the
    harmonizer's detector pairwise within the window. Pure function."""
    from theory_x.stage3_world_model.harmonizer import _conflict_score
    from theory_x.stage3_world_model.retrieval import _tokenize
    toks = {r["id"]: _tokenize(r["content"] or "") for r in rows}
    failed = set()
    for i, a in enumerate(rows):
        for b in rows[i + 1:]:
            if _conflict_score(toks[a["id"]], a["content"] or "",
                               toks[b["id"]], b["content"] or "") >= _CONFLICT_THRESHOLD:
                failed.add(a["id"]); failed.add(b["id"])
    return {r["id"]: r["id"] not in failed for r in rows}


class WarrantRecorder:
    name = "warrant_recorder"

    def __init__(self, beliefs_writer, beliefs_reader, dynamic_reader,
                 survival_interval_s: int = _SURVIVAL_INTERVAL_S,
                 use_interval_s: int = _USE_INTERVAL_S,
                 first_delay_s: int = _FIRST_DELAY_S) -> None:
        self._w = beliefs_writer
        self._br = beliefs_reader
        self._dr = dynamic_reader
        self._si = survival_interval_s
        self._ui = use_interval_s
        self._delay = first_delay_s
        self._ready = False
        self._stats = {"survival_rows": 0, "use_pairs": 0, "last_error": None}

    # ── plumbing ────────────────────────────────────────────────────────────
    def _ensure(self) -> None:
        if not self._ready:
            for ddl in _DDL:
                self._w.write(ddl)
            self._ready = True

    def _cursor(self, name: str, default: float = 0.0) -> float:
        r = self._br.read_one("SELECT value FROM warrant_record_cursor WHERE name=?", (name,))
        return float(r["value"]) if r else default

    def _set_cursors(self, vals: dict) -> None:
        write_batch(self._w, [(
            "INSERT INTO warrant_record_cursor (name, value) VALUES (?, ?) "
            "ON CONFLICT(name) DO UPDATE SET value=excluded.value", (k, v))
            for k, v in vals.items()])

    # ── 1. survival ─────────────────────────────────────────────────────────
    def survival_cycle(self, now: Optional[float] = None) -> int:
        self._ensure()
        now = time.time() if now is None else now
        window, cursors = [], {}
        for lo, hi in _BANDS:
            key = f"surv_t{lo}{hi}"
            cur = self._cursor(key)
            q = ("SELECT id, content, tier FROM beliefs WHERE tier BETWEEN ? AND ? "
                 "AND locked = 0 AND paused = 0 AND id > ? ORDER BY id LIMIT ?")
            rows = [dict(r) for r in self._br.read(q, (lo, hi, int(cur), _PER_BAND))]
            if len(rows) < _PER_BAND:                       # end of band: wrap
                seen = {x["id"] for x in rows}
                rows += [dict(r) for r in self._br.read(q, (lo, hi, -1, _PER_BAND - len(rows)))
                         if r["id"] not in seen]
            if rows:
                cursors[key] = float(rows[-1]["id"])        # last id taken, in order
            window += rows
        if not window:
            return 0
        verdict = shadow_conflict_check(window)
        tier = {r["id"]: r["tier"] for r in window}
        write_batch(self._w, [(
            "INSERT INTO belief_survival (belief_id, ts, check_type, passed, tier) "
            "VALUES (?, ?, 'conflict_window', ?, ?)", (bid, now, int(ok), tier[bid]))
            for bid, ok in verdict.items()])
        self._set_cursors(cursors)
        self._stats["survival_rows"] += len(verdict)
        return len(verdict)

    # ── 2. use days ─────────────────────────────────────────────────────────
    def use_cycle(self, now: Optional[float] = None) -> int:
        self._ensure()
        now = time.time() if now is None else now
        pairs, cur_new = set(), {}

        def take(key, rows, id_key, bid_keys, ts_key):
            last = None
            for r in rows:
                for k in bid_keys:
                    if r[k] is not None:
                        pairs.add((int(r[k]), int(float(r[ts_key]) // _DAY)))
                last = r[id_key]
            if last is not None:
                cur_new[key] = float(last)

        c = self._cursor("use_retrieval_id")
        take("use_retrieval_id", self._dr.read(
            "SELECT id, belief_id, ts FROM fountain_retrieval_log WHERE id > ? "
            "ORDER BY id LIMIT ?", (int(c), _USE_BATCH)), "id", ("belief_id",), "ts")
        c = self._cursor("use_anchor_id")
        take("use_anchor_id", self._dr.read(
            "SELECT id, anchor_belief_id, ts FROM fountain_events WHERE id > ? "
            "AND anchor_belief_id IS NOT NULL ORDER BY id LIMIT ?", (int(c), _USE_BATCH)),
            "id", ("anchor_belief_id",), "ts")
        c = self._cursor("use_synergizer_id")
        take("use_synergizer_id", self._br.read(
            "SELECT id, belief_id_a, belief_id_b, ts FROM synergizer_log WHERE id > ? "
            "ORDER BY id LIMIT ?", (int(c), _USE_BATCH)),
            "id", ("belief_id_a", "belief_id_b"), "ts")
        c = self._cursor("use_lineage_ts")
        take("use_lineage_ts", self._br.read(
            "SELECT created_at, parent_id FROM belief_lineage WHERE created_at > ? "
            "ORDER BY created_at LIMIT ?", (c, _USE_BATCH)),
            "created_at", ("parent_id",), "created_at")
        c = self._cursor("use_arc_ts")
        take("use_arc_ts", self._br.read(
            "SELECT joined_at, belief_id FROM arc_members WHERE joined_at > ? "
            "ORDER BY joined_at LIMIT ?", (c, _USE_BATCH)),
            "joined_at", ("belief_id",), "joined_at")

        if pairs:
            write_batch(self._w, [(
                "INSERT OR IGNORE INTO belief_use_day (belief_id, day) VALUES (?, ?)", p)
                for p in sorted(pairs)])
            ids = sorted({b for b, _ in pairs})
            for i in range(0, len(ids), 500):
                chunk = ids[i:i + 500]
                ph = ",".join("?" * len(chunk))
                self._w.write(
                    "INSERT INTO belief_use_days (belief_id, days, first_day, last_day, updated_at) "
                    f"SELECT belief_id, COUNT(*), MIN(day), MAX(day), ? FROM belief_use_day "
                    f"WHERE belief_id IN ({ph}) GROUP BY belief_id "
                    "ON CONFLICT(belief_id) DO UPDATE SET days=excluded.days, "
                    "first_day=excluded.first_day, last_day=excluded.last_day, "
                    "updated_at=excluded.updated_at", (now, *chunk))
        self._set_cursors(cur_new)
        self._stats["use_pairs"] += len(pairs)
        return len(pairs)

    # ── loop ────────────────────────────────────────────────────────────────
    def _loop(self) -> None:
        import errors
        time.sleep(self._delay)
        next_surv = 0.0
        while True:
            t = time.time()
            try:
                n = self.use_cycle(t)
                if n:
                    errors.record(f"warrant recorder: {n} (belief, day) use pairs",
                                  source=_LOG_SOURCE, level="INFO")
            except Exception as exc:
                self._stats["last_error"] = str(exc)
                errors.record(f"warrant recorder use cycle failed (non-fatal): {exc}",
                              source=_LOG_SOURCE, exc=exc)
            if t >= next_surv:
                try:
                    n = self.survival_cycle(t)
                    errors.record(f"warrant recorder: {n} survival checks",
                                  source=_LOG_SOURCE, level="INFO")
                except Exception as exc:
                    self._stats["last_error"] = str(exc)
                    errors.record(f"warrant recorder survival cycle failed (non-fatal): {exc}",
                                  source=_LOG_SOURCE, exc=exc)
                next_surv = t + self._si
            time.sleep(self._ui)

    def start_loop(self) -> None:
        if os.environ.get("NEX5_WARRANT_RECORD") != "1":
            return
        threading.Thread(target=self._loop, daemon=True, name="warrant_recorder").start()

    def state(self, now: Optional[float] = None) -> dict:
        return {"name": self.name, **self._stats}
