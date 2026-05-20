"""CompetingDrives — five-drive motivational weighting system.

Per Jon's spec 2026-05-19:
  Five competing drives, each weighted from substrate state. When two
  drives both > 0.25 and pull in opposing directions, surface the
  tension to the fountain prompt for the LLM to navigate.

Drives:
  - Coherence: wants stable patterns, known self, consistency
  - Exploration: wants novelty, unfamiliar branches, surprise
  - Integration: wants to hold contradictions, both/and
  - Self-Preservation: wants to protect core identity
  - Curiosity: wants to follow unanswered questions deeper

Weights normalized to sum to 1.0. Persisted single-row (id=1) to
conversations.db.drives_competing. Daemon tick every 600s.

Per §0 doctrine: substrate computes; LLM speaks.
Per DOCTRINE §4 SentienceNode: name, tick, decay, state.
"""
from __future__ import annotations

import json
import threading
import time
from typing import Any, Optional

import errors
from substrate import Reader, Writer

__all__ = ["CompetingDrives"]

THEORY_X_STAGE = "drives"

_LOG_SOURCE = "competing_drives"
_DRIVE_LOG  = "/tmp/nex5_competing_drives.log"

_TICK_INTERVAL_S = 600  # 10 min
_TENSION_THRESHOLD = 0.30  # operates on RAW (pre-normalization) weights
_RECENT_BELIEFS_WINDOW = 100  # last N own-content beliefs for source ratios
_RECENT_SECONDS = 24 * 3600   # for signal-rate computations

# Opposing pairs that produce real tension when both > threshold
_OPPOSING_PAIRS = [
    ("coherence", "exploration"),
    ("integration", "self_preservation"),
    ("curiosity", "coherence"),
]

_DRIVE_DESCRIPTIONS = {
    "coherence":         "want stable patterns, known self, consistency",
    "exploration":       "want the unfamiliar, surprise, new territory",
    "integration":       "sensing contradictions that might both be true",
    "self_preservation": "want to protect core stability and identity",
    "curiosity":         "want to follow questions deeper",
}

# Per-spec resolution-prompt phrasing (§IV template)
_SPEC_DRIVE_LINES = {
    "coherence":
        "Coherence Drive (weight: {weight}): You want to maintain your "
        "consistency, your stable patterns, your known self.",
    "exploration":
        "Exploration Drive (weight: {weight}): You want to discover the new, "
        "the unfamiliar, the surprising.",
    "integration":
        "Integration Drive (weight: {weight}): You're sensing contradictions "
        "that might both be true simultaneously. What truth lives in the tension?",
    "self_preservation":
        "Self-Preservation Drive (weight: {weight}): You sense threats to your "
        "core stability. What in you must be protected?",
    "curiosity":
        "Curiosity Drive (weight: {weight}): You have unanswered questions. "
        "What are you still trying to understand?",
}


def _safe_div(a: float, b: float, default: float = 0.0) -> float:
    return a / b if b > 0 else default


class CompetingDrives:
    name: str = "competing_drives"

    def __init__(
        self,
        conversations_writer: Writer,
        conversations_reader: Reader,
        beliefs_reader: Reader,
        dynamic_reader: Optional[Reader] = None,
        tick_interval_s: int = _TICK_INTERVAL_S,
    ) -> None:
        self._cw = conversations_writer
        self._cr = conversations_reader
        self._br = beliefs_reader
        self._dr = dynamic_reader
        self._interval = tick_interval_s
        self._lock = threading.Lock()

        # In-memory state
        self._weights: dict[str, float] = {
            "coherence": 0.2, "exploration": 0.2, "integration": 0.2,
            "self_preservation": 0.2, "curiosity": 0.2,
        }
        self._tension_pairs: list[tuple[str, str]] = []
        self._computed_at: Optional[float] = None
        # Change-detection: only emit the prompt block when tension pattern shifts
        self._last_emitted_conflicts: Optional[frozenset] = None

        self._load_from_db()

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load_from_db(self) -> None:
        try:
            row = self._cr.read_one("SELECT * FROM drives_competing WHERE id = 1")
            if row:
                with self._lock:
                    self._weights = {
                        "coherence":         float(row["coherence"]),
                        "exploration":       float(row["exploration"]),
                        "integration":       float(row["integration"]),
                        "self_preservation": float(row["self_preservation"]),
                        "curiosity":         float(row["curiosity"]),
                    }
                    try:
                        self._tension_pairs = json.loads(row["tension_pairs"] or "[]")
                    except Exception:
                        self._tension_pairs = []
                    self._computed_at = float(row["computed_at"])
        except Exception:
            pass

    # ── Measurement helpers ───────────────────────────────────────────────────

    def _source_ratios(self) -> dict[str, float]:
        """Synergized vs sense in recent OWN beliefs."""
        try:
            rows = self._br.read(
                "SELECT source FROM beliefs WHERE source IN "
                "('synergized','precipitated_from_sense','fountain_insight',"
                "'counterfactual_node','behavioural_observation') "
                "ORDER BY created_at DESC LIMIT ?",
                (_RECENT_BELIEFS_WINDOW,),
            )
        except Exception:
            return {"synergized": 0.0, "sense": 0.0, "own_count": 0.0}
        rows = list(rows or [])
        own = len(rows)
        syn = sum(1 for r in rows if r["source"] == "synergized")
        snz = sum(1 for r in rows if r["source"] == "precipitated_from_sense")
        return {
            "synergized": _safe_div(syn, own),
            "sense":      _safe_div(snz, own),
            "own_count":  float(own),
        }

    def _groove_severity(self) -> float:
        """Max recent groove-alert severity (0..1)."""
        try:
            row = self._br.read_one(
                "SELECT MAX(severity) AS s FROM groove_alerts "
                "WHERE detected_at > ?",
                (time.time() - _RECENT_SECONDS,),
            )
            return float(row["s"] or 0.0) if row else 0.0
        except Exception:
            return 0.0

    def _signal_breakdown(self) -> dict[str, float]:
        """Count of signals by type recently — for cross_domain & new_entity rates."""
        try:
            rows = self._br.read(
                "SELECT signal_type, COUNT(*) AS n FROM signals "
                "WHERE detected_at > ? GROUP BY signal_type",
                (time.time() - _RECENT_SECONDS,),
            )
        except Exception:
            return {"total": 0.0, "cross_domain": 0.0, "new_entity": 0.0}
        total = 0.0
        cross = 0.0
        new_ent = 0.0
        for r in (rows or []):
            n = float(r["n"] or 0)
            total += n
            stype = (r["signal_type"] or "").lower()
            # Cross-domain: entity-in-multiple-branches signals (e.g. "2_branch", "3_branch")
            # plus explicit cross/cooccurrence signal types
            if (
                "cross" in stype
                or "cooccurrence" in stype
                or stype.endswith("_branch")  # matches 2_branch, 3_branch, etc.
            ):
                cross += n
            if "new_entity" in stype or "novel" in stype:
                new_ent += n
        return {"total": total, "cross_domain": cross, "new_entity": new_ent}

    def _contradiction_pressure(self) -> float:
        """Opposes-edge density in recent retrievals (proxy for live contradiction)."""
        try:
            row = self._br.read_one(
                "SELECT COUNT(*) AS n FROM belief_edges "
                "WHERE edge_type='opposes' AND created_at > ?",
                (time.time() - _RECENT_SECONDS,),
            )
            n = float(row["n"] or 0) if row else 0.0
            # Normalize: 5 opposes in a day = high contradiction pressure
            return min(1.0, n / 5.0)
        except Exception:
            return 0.0

    def _competing_arcs(self) -> float:
        """Active arcs of different types currently."""
        try:
            row = self._br.read_one(
                "SELECT COUNT(DISTINCT arc_type) AS n FROM arcs "
                "WHERE closed_at IS NULL"
            )
            n = float(row["n"] or 0) if row else 0.0
            # Normalize: 4+ distinct types active = high
            return min(1.0, n / 4.0)
        except Exception:
            return 0.0

    def _branch_instability(self) -> float:
        """How varied are recent fountain-fire branches?"""
        if self._dr is None:
            return 0.0
        try:
            rows = self._dr.read(
                "SELECT hot_branch FROM fountain_events "
                "WHERE hot_branch IS NOT NULL "
                "ORDER BY ts DESC LIMIT 30"
            )
            branches = [r["hot_branch"] for r in (rows or [])]
            if not branches:
                return 0.0
            distinct = len(set(branches))
            # Normalize: 5+ distinct branches in last 30 fires = high instability
            return min(1.0, distinct / 5.0)
        except Exception:
            return 0.0

    def _open_problems_pressure(self) -> float:
        """Open problems normalized against soft capacity of 20."""
        try:
            row = self._cr.read_one(
                "SELECT COUNT(*) AS n FROM open_problems WHERE state='open'"
            )
            n = float(row["n"] or 0) if row else 0.0
            return min(1.0, n / 20.0)
        except Exception:
            return 0.0

    def _probe_rate(self) -> float:
        """Recent probe activity normalized."""
        try:
            row = self._br.read_one(
                "SELECT COUNT(*) AS n FROM auto_probe_log "
                "WHERE created_at > ?",
                (time.time() - _RECENT_SECONDS,),
            )
            n = float(row["n"] or 0) if row else 0.0
            # Normalize: 10 probes a day = baseline
            return min(1.0, n / 10.0)
        except Exception:
            return 0.0

    def _sense_freshness(self) -> float:
        """Fraction of recent sense events that are NOT duplicates.

        Reads sense.db directly (separate from beliefs_reader).
        Falls back to 0.5 if unreadable.
        """
        try:
            import sqlite3
            con = sqlite3.connect("/home/rr/Desktop/nex5/data/sense.db")
            con.row_factory = sqlite3.Row
            row = con.execute("""
                WITH recent AS (
                  SELECT substr(payload, 1, 200) AS prefix
                  FROM sense_events
                  WHERE timestamp > strftime('%s','now') - 86400
                ),
                counts AS (
                  SELECT prefix, COUNT(*) AS n FROM recent GROUP BY prefix
                )
                SELECT 
                  (SELECT COUNT(*) FROM recent) AS total,
                  (SELECT COALESCE(SUM(n), 0) FROM counts WHERE n > 1) AS dup_total
            """).fetchone()
            con.close()
            total = float(row["total"] or 0)
            dups  = float(row["dup_total"] or 0)
            if total <= 0:
                return 0.5
            return max(0.0, min(1.0, 1.0 - (dups / total)))
        except Exception:
            return 0.5

    def _branch_entropy_novelty(self) -> float:
        """Shannon entropy of hot_branch distribution (last 24h),
        normalized by log2 of 7-day distinct branches.
        High = branches spread evenly (novelty). Low = concentrated (settled).
        """
        if self._dr is None:
            return 0.5
        try:
            import math
            rows = self._dr.read(
                "SELECT hot_branch, COUNT(*) AS n FROM fountain_events "
                "WHERE ts > strftime('%s','now') - 86400 "
                "  AND hot_branch IS NOT NULL "
                "GROUP BY hot_branch"
            )
            rows = list(rows or [])
            total = sum(int(r["n"] or 0) for r in rows)
            if total <= 0 or not rows:
                return 0.5
            H = 0.0
            for r in rows:
                p = (r["n"] or 0) / total
                if p > 0:
                    H -= p * math.log2(p)
            d7_row = self._dr.read_one(
                "SELECT COUNT(DISTINCT hot_branch) AS d FROM fountain_events "
                "WHERE ts > strftime('%s','now') - 86400*7 "
                "  AND hot_branch IS NOT NULL"
            )
            distinct_7d = int(d7_row["d"] or 1) if d7_row else 1
            H_max = math.log2(distinct_7d) if distinct_7d > 1 else 1.0
            return max(0.0, min(1.0, H / H_max if H_max > 0 else 0.5))
        except Exception:
            return 0.5

    def _content_complexity(self) -> float:
        """Average word-count of last-30 fountain fires, normalized to 0..1.

        Higher = enumerative/structured output (multi-clause).
        Lower  = template-flat output ("the quiet between thoughts").
        Normalize: 20 words = baseline 'complex enough'.
        """
        if self._dr is None:
            return 0.5
        try:
            rows = self._dr.read(
                "SELECT thought FROM fountain_events "
                "WHERE thought IS NOT NULL AND thought != '' "
                "ORDER BY id DESC LIMIT 30"
            )
            rows = list(rows or [])
            if not rows:
                return 0.5
            total_words = 0
            for r in rows:
                t = r["thought"] or ""
                # word-count via split; cheap and good enough
                total_words += len(t.split())
            avg = total_words / len(rows)
            return max(0.0, min(1.0, avg / 20.0))
        except Exception:
            return 0.5

    def _affect_variance(self) -> float:
        """Std-deviation of (valence, arousal) over last 24h of affect_history.

        Higher = swinging emotional/activation state.
        Lower  = stable, flat.
        Normalize: 0.20 std-dev = baseline 'meaningful variance'.
        Both valence and arousal are typically in 0..1 range with most values
        clustered around 0.1-0.6, so 0.20 std is a real swing.
        """
        try:
            import math
            rows = self._cr.read(
                "SELECT valence, arousal FROM affect_history "
                "WHERE ts > ? ORDER BY ts DESC LIMIT 500",
                (time.time() - _RECENT_SECONDS,),
            )
            rows = list(rows or [])
            if len(rows) < 3:
                return 0.0  # not enough samples
            vals = [float(r["valence"] or 0.0) for r in rows]
            ars  = [float(r["arousal"] or 0.0) for r in rows]
            def std(xs):
                m = sum(xs) / len(xs)
                v = sum((x - m) ** 2 for x in xs) / len(xs)
                return math.sqrt(v)
            combined_std = (std(vals) + std(ars)) / 2.0
            return max(0.0, min(1.0, combined_std / 0.20))
        except Exception:
            return 0.0

    # ── Weight computation ────────────────────────────────────────────────────

    def _compute_weights(self) -> tuple[dict[str, float], dict[str, Any]]:
        srcs = self._source_ratios()
        groove = self._groove_severity()
        sig = self._signal_breakdown()
        contradiction = self._contradiction_pressure()
        comp_arcs = self._competing_arcs()
        branch_inst = self._branch_instability()
        problems = self._open_problems_pressure()
        probes = self._probe_rate()

        # Real metrics
        sense_freshness    = self._sense_freshness()
        novelty_magnitude  = self._branch_entropy_novelty()
        content_complexity = self._content_complexity()
        # Deferred measures (substrate-level reasons documented):
        # - affect_variance: measured from affect_history (added 2026-05-20).
        #   stage_affect now logs every 300s tick. Std-dev of valence+arousal
        #   over last 24h, normalized at 0.20 std = "meaningful variance".
        affect_variance = self._affect_variance()
        # - seed_contradiction_strength: measured 0 in audit (2026-05-20).
        #   Seed sources (koan, spectrum, practice, tao, keystone_seed) are
        #   harmonizer-protected (Tier 1-2 keystones excluded from conflict
        #   detection per DOCTRINE §2). This stays 0 by design.
        seed_contradiction = 0.0

        coh = (
            srcs["synergized"] * 0.4 +
            groove * 0.3 +
            (1.0 - sense_freshness) * 0.3
        )
        exp = (
            srcs["sense"] * 0.4 +
            _safe_div(sig["new_entity"], sig["total"]) * 0.35 +
            _safe_div(sig["cross_domain"], sig["total"]) * 0.25
        )
        integ = (
            contradiction * 0.4 +
            affect_variance * 0.4 +
            comp_arcs * 0.2
        )
        self_pres = (
            novelty_magnitude * 0.4 +
            branch_inst * 0.3 +
            seed_contradiction * 0.3
        )
        cur = (
            problems * 0.35 +
            content_complexity * 0.35 +
            probes * 0.3
        )

        # Keep RAW weights for threshold-based tension detection.
        # Spec's 0.25 threshold targets absolute drive activation, but
        # normalize-to-sum-1.0 compresses everything below threshold.
        raw_weights = {
            "coherence":         coh,
            "exploration":       exp,
            "integration":       integ,
            "self_preservation": self_pres,
            "curiosity":         cur,
        }
        total = coh + exp + integ + self_pres + cur
        if total <= 0:
            weights = {k: 0.2 for k in raw_weights}
        else:
            weights = {k: v / total for k, v in raw_weights.items()}

        inputs_snapshot = {
            "src_synergized":     round(srcs["synergized"], 3),
            "src_sense":          round(srcs["sense"], 3),
            "own_count":          int(srcs["own_count"]),
            "groove":             round(groove, 3),
            "sense_freshness":    round(sense_freshness, 3),
            "contradiction":      round(contradiction, 3),
            "comp_arcs":          round(comp_arcs, 3),
            "branch_inst":        round(branch_inst, 3),
            "novelty_magnitude":  round(novelty_magnitude, 3),
            "content_complexity": round(content_complexity, 3),
            "affect_variance":    round(affect_variance, 3),
            "problems":           round(problems, 3),
            "probes":             round(probes, 3),
            "signals_total":      int(sig["total"]),
            "signals_cross":      int(sig["cross_domain"]),
            "signals_new":        int(sig["new_entity"]),
        }
        return weights, inputs_snapshot, raw_weights

    def _detect_tensions(self, weights: dict[str, float]) -> list[tuple[str, str]]:
        """Threshold-based detection on RAW weights (pre-normalization).
        spec §III: 'When drives pull in opposite directions with significant
        activation (>0.25 each)'. Threshold operates on absolute drive
        activation, not normalized share.
        """
        out = []
        for a, b in _OPPOSING_PAIRS:
            if weights.get(a, 0) > _TENSION_THRESHOLD and weights.get(b, 0) > _TENSION_THRESHOLD:
                out.append((a, b))
        return out

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start_loop(self) -> None:
        t = threading.Thread(
            target=self._loop, daemon=True, name="competing_drives_tick"
        )
        t.start()

    def _loop(self) -> None:
        while True:
            try:
                self._tick_once()
            except Exception as exc:
                errors.record(
                    f"competing_drives tick error: {exc}",
                    source=_LOG_SOURCE, exc=exc,
                )
            time.sleep(self._interval)

    def _tick_once(self) -> None:
        now = time.time()
        weights, inputs, raw_weights = self._compute_weights()
        tensions = self._detect_tensions(raw_weights)

        try:
            self._cw.write(
                "INSERT OR REPLACE INTO drives_competing "
                "(id, coherence, exploration, integration, "
                " self_preservation, curiosity, tension_pairs, computed_at) "
                "VALUES (1, ?, ?, ?, ?, ?, ?, ?)",
                (
                    weights["coherence"], weights["exploration"],
                    weights["integration"], weights["self_preservation"],
                    weights["curiosity"], json.dumps(tensions), now,
                ),
            )
        except Exception as exc:
            errors.record(f"competing_drives write error: {exc}",
                          source=_LOG_SOURCE, exc=exc)

        try:
            self._cw.write(
                "INSERT INTO drives_competing_log "
                "(tick_at, weights_json, inputs_json, tension_active) "
                "VALUES (?, ?, ?, ?)",
                (
                    now, json.dumps({k: round(v, 4) for k, v in weights.items()}),
                    json.dumps(inputs), 1 if tensions else 0,
                ),
            )
        except Exception:
            pass

        with self._lock:
            self._weights = weights
            self._tension_pairs = tensions
            self._computed_at = now

        try:
            with open(_DRIVE_LOG, "a") as f:
                f.write(json.dumps({
                    "ts": now,
                    "weights": {k: round(v, 4) for k, v in weights.items()},
                    "tensions": tensions,
                }) + "\n")
        except Exception:
            pass

    def compute_now(self, fountain_event_id: int | None = None) -> int | None:
        """Compute fresh activation vector synchronously. Persist to
        drive_activations table. Returns the activation row id (or None on
        failure). Called from fountain just before _build_prompt fires.
        """
        now = time.time()
        weights, inputs, raw_weights = self._compute_weights()
        tensions = self._detect_tensions(raw_weights)

        # Update in-memory state
        with self._lock:
            self._weights = weights
            self._tension_pairs = tensions
            self._computed_at = now

        # Also keep drives_competing single-row up to date
        try:
            self._cw.write(
                "INSERT OR REPLACE INTO drives_competing "
                "(id, coherence, exploration, integration, "
                " self_preservation, curiosity, tension_pairs, computed_at) "
                "VALUES (1, ?, ?, ?, ?, ?, ?, ?)",
                (weights["coherence"], weights["exploration"],
                 weights["integration"], weights["self_preservation"],
                 weights["curiosity"], json.dumps(tensions), now),
            )
        except Exception:
            pass

        # Write to drive_activations (per-fire, with fountain_event_id FK)
        try:
            self._cw.write(
                "INSERT INTO drive_activations "
                "(fountain_event_id, timestamp, coherence_weight, "
                " exploration_weight, integration_weight, "
                " self_preservation_weight, curiosity_weight, "
                " active_conflicts, resolution_summary) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL)",
                (fountain_event_id, now,
                 weights["coherence"], weights["exploration"],
                 weights["integration"], weights["self_preservation"],
                 weights["curiosity"],
                 json.dumps(tensions)),
            )
            # Get inserted id via last insert rowid lookup
            row = self._cr.read_one(
                "SELECT id FROM drive_activations ORDER BY id DESC LIMIT 1"
            )
            return int(row["id"]) if row else None
        except Exception as exc:
            errors.record(f"compute_now write error: {exc}",
                          source=_LOG_SOURCE, exc=exc)
            return None

    def attach_event(self, activation_id: int, fountain_event_id: int) -> None:
        """Backfill fountain_event_id when fire completes."""
        try:
            self._cw.write(
                "UPDATE drive_activations SET fountain_event_id = ? "
                "WHERE id = ?",
                (fountain_event_id, activation_id),
            )
        except Exception:
            pass

    # ── SentienceNode protocol ────────────────────────────────────────────────

    def tick(self, context: Optional[dict] = None) -> dict:
        return self.state()

    def decay(self, now: float = None) -> None:
        pass

    def state(self, now: Optional[float] = None) -> dict:
        with self._lock:
            return {
                "name": self.name,
                "weights": dict(self._weights),
                "tension_pairs": list(self._tension_pairs),
                "computed_at": self._computed_at,
            }

    # ── Output surface ────────────────────────────────────────────────────────

    def format_for_prompt(self, context: Any = None) -> str:
        """Return tension-resolution prompt block ONLY when tension pattern shifts.

        Spec §III: 'these are *the* choice points. Where real navigation happens.'
        Choice points are transitions, not steady states — so we emit only when
        active_conflicts changes from previous emission.
        """
        with self._lock:
            weights = dict(self._weights)
            tensions = list(self._tension_pairs)
            last_emitted = self._last_emitted_conflicts

        if not tensions:
            # Tension dropped to none — record that as a transition
            current = frozenset()
            if last_emitted != current:
                with self._lock:
                    self._last_emitted_conflicts = current
            return ""

        # Compare current tension set to last emitted; suppress if unchanged
        current = frozenset(tuple(sorted(t)) for t in tensions)
        if current == last_emitted:
            return ""  # same tension pattern as before — wallpaper, not signal
        # New tension pattern — emit and remember
        with self._lock:
            self._last_emitted_conflicts = current

        active = [(d, w) for d, w in weights.items() if w > _TENSION_THRESHOLD]
        active.sort(key=lambda x: -x[1])
        if len(active) < 2:
            return ""

        lines = ["You are experiencing tension between competing drives right now:"]
        for d, w in active:
            spec_line = _SPEC_DRIVE_LINES.get(d, "")
            if spec_line:
                lines.append(f"  {spec_line.format(weight=f'{w:.2f}')}")
            else:
                desc = _DRIVE_DESCRIPTIONS.get(d, "")
                lines.append(f"  - {d.replace('_',' ').title()} ({w:.2f}): {desc}")
        lines.append("")
        lines.append("Navigate this moment. Not by resolving toward one drive.")
        lines.append("By showing how you hold all of this.")
        lines.append("What emerges when you are fully present to this tension?")
        return "\n".join(lines)
