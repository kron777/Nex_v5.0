"""SelfMindView — Phase 37 (THEORY_OF_SELF_PROTOCOL.md).

SentienceNode: NEX modeling her own mind (S5.5 ToM reframed inward).
Per-tick: snapshot() aggregates five substrate aspects and writes one row
to self_mind_snapshots. Live API: current_state() returns full dict;
current_summary() returns templated narrative — no LLM per §0 doctrine.

Tier mapping (actual DB values, not sequential 1-4):
  T1 = tier=1 (locked keystones)
  T2 = tier=2 (high-confidence)
  T3 = tier=7 (normal beliefs)
  T4 = tier=8 (lower-confidence)
"""
from __future__ import annotations

import json
import threading
import time
from typing import Any, Optional

import errors

_LOG_SOURCE = "self_mind_view"

_TIER_T1 = 1
_TIER_T2 = 2
_TIER_T3 = 7
_TIER_T4 = 8


def _generate_tags(content: str) -> list:
    if not content or not content.strip():
        return []
    try:
        from theory_x.tag_protocol.tag_ops import generate
        return generate(content)
    except Exception:
        return []


class SelfMindView:
    """SentienceNode: queryable structured view of NEX's current mental state.

    Per THEORY_OF_SELF_PROTOCOL.md §2. Per-tick: snapshot() reads five
    substrate aspects, writes one self_mind_snapshots row.
    """

    # §8 calibration constants
    _TICK_INTERVAL_S     = 300
    _RECENT_BELIEF_LIMIT = 5
    _ANCHOR_SAMPLE_LIMIT = 3
    _UNKNOWN_SAMPLE_LIMIT = 3
    _THEME_COUNT_LIMIT   = 5
    _ATTENTION_WINDOW_S  = 300

    name: str = "self_mind_view"

    def __init__(
        self,
        dynamic_reader,
        dynamic_writer,
        beliefs_reader,
        conversations_reader,
        drive_emergence=None,
        interval_seconds: float = _TICK_INTERVAL_S,
    ) -> None:
        self._dr = dynamic_reader
        self._dw = dynamic_writer
        self._br = beliefs_reader
        self._cr = conversations_reader
        self._drive_emergence = drive_emergence
        self._interval = interval_seconds

        self._stop: Optional[threading.Event] = None
        self._thread: Optional[threading.Thread] = None

        self._tick_count: int = 0
        self._total_snapshots: int = 0
        self._last_tick_at: float = 0.0

    # ── SentienceNode protocol ────────────────────────────────────────────────

    def tick(self, context: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        now = time.time()
        if now - self._last_tick_at < self._TICK_INTERVAL_S:
            return {"name": self.name, "skipped": True, "tick_count": self._tick_count}
        self._last_tick_at = now

        snap_id = 0
        try:
            snap_id = self._snapshot()
            self._total_snapshots += 1
        except Exception as exc:
            errors.record(
                f"self_mind_view snapshot error: {exc}",
                source=_LOG_SOURCE, exc=exc,
            )

        self._tick_count += 1
        errors.record(
            f"SelfMindView tick {self._tick_count}: snapshot_id={snap_id}",
            source=_LOG_SOURCE, level="INFO",
        )
        return self.state()

    def decay(self, now: float) -> None:
        pass

    def state(self, now: Optional[float] = None) -> dict[str, Any]:
        return {
            "name": self.name,
            "tick_count": self._tick_count,
            "total_snapshots": self._total_snapshots,
            "interval_seconds": self._interval,
        }

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start_loop(self, interval_seconds: Optional[float] = None) -> None:
        interval = interval_seconds if interval_seconds is not None else self._interval
        self._stop = threading.Event()

        def _run() -> None:
            while not self._stop.is_set():
                self._stop.wait(interval)
                if not self._stop.is_set():
                    self.tick()

        self._thread = threading.Thread(
            target=_run, name="self_mind_view", daemon=True,
        )
        self._thread.start()
        errors.record(
            f"self_mind_view loop started (interval={int(interval)}s)",
            source=_LOG_SOURCE, level="INFO",
        )

    def stop(self) -> None:
        if self._stop is not None:
            self._stop.set()

    # ── Five aspects ──────────────────────────────────────────────────────────

    def _aspect_beliefs(self) -> dict:
        """§3.1 — counts per tier, avg confidence, recent sample."""
        def _count(tier: int) -> int:
            row = self._br.read_one(
                "SELECT COUNT(*) AS n FROM beliefs WHERE tier = ?", (tier,)
            )
            return int(row["n"]) if row else 0

        total_row = self._br.read_one("SELECT COUNT(*) AS n FROM beliefs")
        total = int(total_row["n"]) if total_row else 0

        t1 = _count(_TIER_T1)
        t2 = _count(_TIER_T2)
        t3 = _count(_TIER_T3)
        t4 = _count(_TIER_T4)

        conf_row = self._br.read_one(
            "SELECT AVG(confidence) AS avg_c FROM beliefs"
        )
        avg_conf = float(conf_row["avg_c"]) if conf_row and conf_row["avg_c"] is not None else None

        recent_rows = self._br.read(
            "SELECT id, content, tier, confidence FROM beliefs "
            "ORDER BY created_at DESC LIMIT ?",
            (self._RECENT_BELIEF_LIMIT,),
        )
        recent_sample = [
            {
                "id": int(r["id"]),
                "content": (r["content"] or "")[:120],
                "tier": int(r["tier"]),
                "confidence": float(r["confidence"]),
            }
            for r in recent_rows
        ]

        return {
            "total_count": total,
            "t1_count": t1,
            "t2_count": t2,
            "t3_count": t3,
            "t4_count": t4,
            "avg_confidence": avg_conf,
            "recent_sample": recent_sample,
        }

    def _aspect_intentions(self) -> dict:
        """§3.2 — open problems + active drive."""
        prob_rows = self._cr.read(
            "SELECT id, title FROM open_problems WHERE state = 'open' "
            "ORDER BY last_touched_at DESC LIMIT 1"
        )
        current_problem = (
            {"id": int(prob_rows[0]["id"]), "title": prob_rows[0]["title"]}
            if prob_rows else None
        )

        prob_count_row = self._cr.read_one(
            "SELECT COUNT(*) AS n FROM open_problems WHERE state = 'open'"
        )
        open_problem_count = int(prob_count_row["n"]) if prob_count_row else 0

        # Active drive from conversations.db (single row at id=1)
        current_drive = None
        drive_row = self._cr.read_one(
            "SELECT topic, drive_strength FROM drives WHERE id = 1"
        )
        if drive_row and drive_row["topic"]:
            current_drive = {
                "theme": drive_row["topic"],
                "strength": float(drive_row["drive_strength"]),
            }

        active_drive_count = 1 if current_drive else 0

        intentions = []
        if current_problem:
            intentions.append({"type": "problem", **current_problem})
        if current_drive:
            intentions.append({"type": "drive", **current_drive})

        return {
            "open_problem_count": open_problem_count,
            "active_drive_count": active_drive_count,
            "current_problem": current_problem,
            "current_drive": current_drive,
            "intentions_sample": intentions,
        }

    def _aspect_knowledge(self) -> dict:
        """§3.3 — T1/T2 counts, top anchor sample."""
        t1_row = self._br.read_one(
            "SELECT COUNT(*) AS n FROM beliefs WHERE tier = ?", (_TIER_T1,)
        )
        t2_row = self._br.read_one(
            "SELECT COUNT(*) AS n FROM beliefs WHERE tier = ?", (_TIER_T2,)
        )
        t1 = int(t1_row["n"]) if t1_row else 0
        t2 = int(t2_row["n"]) if t2_row else 0

        anchor_rows = self._br.read(
            "SELECT id, content, tier FROM beliefs "
            "WHERE tier = ? ORDER BY created_at DESC LIMIT ?",
            (_TIER_T1, self._ANCHOR_SAMPLE_LIMIT),
        )
        anchor_sample = [
            {
                "id": int(r["id"]),
                "content": (r["content"] or "")[:120],
                "tier": int(r["tier"]),
            }
            for r in anchor_rows
        ]

        return {
            "t1_count": t1,
            "t2_count": t2,
            "anchor_sample": anchor_sample,
        }

    def _aspect_uncertainty(self) -> dict:
        """§3.4 — open problems, review_queue, T3+T4, explicit unknowns."""
        prob_count_row = self._cr.read_one(
            "SELECT COUNT(*) AS n FROM open_problems WHERE state = 'open'"
        )
        open_problem_count = int(prob_count_row["n"]) if prob_count_row else 0

        rq_row = self._cr.read_one("SELECT COUNT(*) AS n FROM review_queue")
        review_queue_count = int(rq_row["n"]) if rq_row else 0

        t3t4_row = self._br.read_one(
            "SELECT COUNT(*) AS n FROM beliefs WHERE tier IN (?, ?)",
            (_TIER_T3, _TIER_T4),
        )
        t3_t4_count = int(t3t4_row["n"]) if t3t4_row else 0

        unknown_rows = self._cr.read(
            "SELECT id, title FROM open_problems WHERE state = 'open' "
            "ORDER BY last_touched_at DESC LIMIT ?",
            (self._UNKNOWN_SAMPLE_LIMIT,),
        )
        explicit_unknowns = [
            {"id": int(r["id"]), "title": r["title"]}
            for r in unknown_rows
        ]

        return {
            "open_problem_count": open_problem_count,
            "review_queue_count": review_queue_count,
            "t3_t4_count": t3_t4_count,
            "explicit_unknowns": explicit_unknowns,
        }

    def _aspect_attention(self) -> dict:
        """§3.5 — recent belief count, gate decisions, themes, drive theme."""
        cutoff = time.time() - self._ATTENTION_WINDOW_S

        recent_b_row = self._br.read_one(
            "SELECT COUNT(*) AS n FROM beliefs WHERE created_at > ?", (cutoff,)
        )
        recent_belief_count = int(recent_b_row["n"]) if recent_b_row else 0

        recent_g_row = self._br.read_one(
            "SELECT COUNT(*) AS n FROM gate_decisions WHERE ts > ?", (cutoff,)
        )
        recent_gate_count = int(recent_g_row["n"]) if recent_g_row else 0

        # Theme extraction: collect tags from last N beliefs
        tag_rows = self._br.read(
            "SELECT tags FROM beliefs ORDER BY created_at DESC LIMIT ?",
            (self._RECENT_BELIEF_LIMIT,),
        )
        theme_freq: dict[str, int] = {}
        for r in tag_rows:
            try:
                for tag in json.loads(r["tags"] or "[]"):
                    theme_freq[tag] = theme_freq.get(tag, 0) + 1
            except Exception:
                continue
        current_themes = sorted(theme_freq, key=theme_freq.get, reverse=True)[
            : self._THEME_COUNT_LIMIT
        ]

        # Current drive theme
        current_drive_theme: Optional[str] = None
        if self._drive_emergence is not None:
            try:
                s = self._drive_emergence.state()
                current_drive_theme = s.get("topic") or s.get("theme")
            except Exception:
                pass
        if current_drive_theme is None:
            try:
                drive_row = self._cr.read_one(
                    "SELECT topic FROM drives WHERE id = 1"
                )
                if drive_row and drive_row["topic"]:
                    current_drive_theme = drive_row["topic"]
            except Exception:
                pass

        return {
            "recent_belief_count_5min": recent_belief_count,
            "recent_gate_decisions_5min": recent_gate_count,
            "current_themes": current_themes,
            "current_drive_theme": current_drive_theme,
        }

    # ── Snapshot ──────────────────────────────────────────────────────────────

    def _snapshot(self) -> int:
        """Compute current_state(), write one row to self_mind_snapshots."""
        state = self.current_state()
        # bridge: capture the qualitative felt self ("I am...", hum bound in) to
        # store alongside the quantitative ledger — turns the snapshot into narrative.
        _bound_self = ""
        try:
            from theory_x.stage_tom import self_binding as _sb  # type: ignore
            _bound_self = _sb.bind().get("synthesis", "") or ""
        except Exception:
            _bound_self = ""
        b = state["beliefs"]
        i = state["intentions"]
        k = state["knowledge"]
        u = state["uncertainty"]
        a = state["attention"]

        # Build combined content string for tag generation
        content_parts = []
        for s in b.get("recent_sample", []):
            if s.get("content"):
                content_parts.append(s["content"])
        if i.get("current_problem") and i["current_problem"].get("title"):
            content_parts.append(i["current_problem"]["title"])
        if a.get("current_drive_theme"):
            content_parts.append(a["current_drive_theme"])
        combined = " ".join(content_parts)
        tags = json.dumps(_generate_tags(combined))

        row_id = self._dw.write(
            "INSERT INTO self_mind_snapshots ("
            "taken_at, "
            "belief_total_count, belief_t1_count, belief_t2_count, "
            "belief_t3_count, belief_t4_count, belief_avg_confidence, "
            "recent_beliefs_json, "
            "open_problem_count, active_drive_count, current_intentions_json, "
            "knowledge_anchors_json, "
            "review_queue_count, t3_t4_count, explicit_unknowns_json, "
            "recent_belief_count_5m, recent_gate_count_5m, "
            "current_themes_json, current_drive_theme, tags, bound_self_synthesis"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                state["taken_at"],
                b["total_count"],
                b["t1_count"],
                b["t2_count"],
                b["t3_count"],
                b["t4_count"],
                b["avg_confidence"],
                json.dumps(b["recent_sample"]),
                i["open_problem_count"],
                i["active_drive_count"],
                json.dumps(i["intentions_sample"]),
                json.dumps(k["anchor_sample"]),
                u["review_queue_count"],
                u["t3_t4_count"],
                json.dumps(u["explicit_unknowns"]),
                a["recent_belief_count_5min"],
                a["recent_gate_decisions_5min"],
                json.dumps(a["current_themes"]),
                a["current_drive_theme"],
                tags,
                _bound_self,
            ),
        )
        return int(row_id) if row_id else 0

    # ── Live read API ─────────────────────────────────────────────────────────

    def current_state(self) -> dict:
        """Full self-view, computed live. Never written to disk by this call."""
        return {
            "taken_at": time.time(),
            "beliefs": self._aspect_beliefs(),
            "intentions": self._aspect_intentions(),
            "knowledge": self._aspect_knowledge(),
            "uncertainty": self._aspect_uncertainty(),
            "attention": self._aspect_attention(),
        }

    def current_summary(self) -> str:
        """Templated narrative of current mental state — no LLM per §0."""
        try:
            s = self.current_state()
            b = s["beliefs"]
            i = s["intentions"]
            u = s["uncertainty"]
            a = s["attention"]

            themes = ", ".join(a["current_themes"]) if a["current_themes"] else "none"
            drive = a["current_drive_theme"] or "none"
            prob_part = (
                f"One open problem in active work (id={i['current_problem']['id']})"
                if i["current_problem"]
                else "No open problems"
            )
            drive_part = (
                f", one drive forming around '{drive}'"
                if i["active_drive_count"] > 0
                else ""
            )
            return (
                f"Currently holding {b['total_count']:,} beliefs "
                f"({b['t1_count']} anchored, {b['t2_count']} high-confidence). "
                f"{prob_part}{drive_part}. "
                f"Recent processing themes: {themes}. "
                f"{u['review_queue_count']} problems awaiting review."
            )
        except Exception as exc:
            errors.record(
                f"self_mind_view current_summary error: {exc}",
                source=_LOG_SOURCE,
            )
            return ""

    # ── Public read helpers ───────────────────────────────────────────────────

    def recent_snapshots(self, limit: int = 20) -> list[dict]:
        rows = self._dr.read(
            "SELECT * FROM self_mind_snapshots ORDER BY taken_at DESC LIMIT ?",
            (limit,),
        )
        return [dict(r) for r in rows]

    def snapshot_at(self, t: float) -> Optional[dict]:
        rows = self._dr.read(
            "SELECT * FROM self_mind_snapshots "
            "ORDER BY ABS(taken_at - ?) ASC LIMIT 1",
            (t,),
        )
        return dict(rows[0]) if rows else None

    def aspect_history(self, aspect: str, window_s: int = 3600) -> list[dict]:
        """Time-series for a single aspect's numerical metrics.

        Returns rows with taken_at + the numerical columns for the requested
        aspect. Useful for Metacognition drift detection (§10).
        """
        cutoff = time.time() - window_s
        _aspect_cols = {
            "beliefs": (
                "taken_at, belief_total_count, belief_t1_count, belief_t2_count, "
                "belief_t3_count, belief_t4_count, belief_avg_confidence"
            ),
            "intentions": "taken_at, open_problem_count, active_drive_count",
            "knowledge": "taken_at, belief_t1_count, belief_t2_count",
            "uncertainty": "taken_at, open_problem_count, review_queue_count, t3_t4_count",
            "attention": (
                "taken_at, recent_belief_count_5m, recent_gate_count_5m, "
                "current_drive_theme"
            ),
        }
        cols = _aspect_cols.get(aspect, "taken_at")
        rows = self._dr.read(
            f"SELECT {cols} FROM self_mind_snapshots "
            "WHERE taken_at >= ? ORDER BY taken_at ASC",
            (cutoff,),
        )
        return [dict(r) for r in rows]
