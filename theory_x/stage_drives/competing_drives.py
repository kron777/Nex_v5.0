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
_TENSION_THRESHOLD = 0.25
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

        # Placeholders for measures not yet computed
        sense_freshness = 0.5  # default
        affect_variance = 0.0  # affect is single-row
        novelty_magnitude = 0.5  # default
        seed_contradiction = 0.0  # rare, deferred
        content_complexity = 0.5  # default

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

        total = coh + exp + integ + self_pres + cur
        if total <= 0:
            weights = {k: 0.2 for k in ["coherence","exploration","integration",
                                        "self_preservation","curiosity"]}
        else:
            weights = {
                "coherence":         coh / total,
                "exploration":       exp / total,
                "integration":       integ / total,
                "self_preservation": self_pres / total,
                "curiosity":         cur / total,
            }

        inputs_snapshot = {
            "src_synergized": round(srcs["synergized"], 3),
            "src_sense":      round(srcs["sense"], 3),
            "own_count":      int(srcs["own_count"]),
            "groove":         round(groove, 3),
            "contradiction":  round(contradiction, 3),
            "comp_arcs":      round(comp_arcs, 3),
            "branch_inst":    round(branch_inst, 3),
            "problems":       round(problems, 3),
            "probes":         round(probes, 3),
            "signals_total":  int(sig["total"]),
            "signals_cross":  int(sig["cross_domain"]),
            "signals_new":    int(sig["new_entity"]),
        }
        return weights, inputs_snapshot

    def _detect_tensions(self, weights: dict[str, float]) -> list[tuple[str, str]]:
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
        weights, inputs = self._compute_weights()
        tensions = self._detect_tensions(weights)

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
        """Return tension-resolution prompt block, or empty string."""
        with self._lock:
            weights = dict(self._weights)
            tensions = list(self._tension_pairs)

        # Only surface when there's actual tension
        if not tensions:
            return ""

        # Build the active-drives block
        active = [(d, w) for d, w in weights.items() if w > _TENSION_THRESHOLD]
        active.sort(key=lambda x: -x[1])
        if len(active) < 2:
            return ""

        lines = ["You are experiencing tension between competing drives right now:"]
        for d, w in active:
            desc = _DRIVE_DESCRIPTIONS.get(d, "")
            lines.append(f"  - {d.replace('_',' ').title()} ({w:.2f}): {desc}")
        lines.append("Navigate this moment. Not by resolving toward one drive.")
        lines.append("By showing how you hold all of this.")
        return "\n".join(lines)
