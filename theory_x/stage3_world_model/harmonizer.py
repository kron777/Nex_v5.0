"""Harmonizer — detects and resolves conflicts between beliefs.

Runs every 2 hours. Finds conflicting belief pairs at Tier 3-7
(working belief body; excludes Tier 1-2 keystones/bedrock and
Tier 8 retired beliefs), marks them as paradox on first detection,
escalates to synthesize/delete after PARADOX_INCUBATION_SECONDS.

Resolution modes (per DOCTRINE §2):
  paradox    — first pass: write 'opposes' edge + disturbance; no retirement
  synthesized — escalation: third belief bridges both; retire both originals
  both_deleted — escalation: no bridge found; retire both
"""
from __future__ import annotations

import re as _re
import time
import threading
from typing import Any, Optional

import errors
from substrate import Writer, Reader
from .retrieval import _tokenize
from .promotion import BeliefPromoter

THEORY_X_STAGE = 3

_LOG_SOURCE = "harmonizer"

# Incubation: pairs marked 'paradox' escalate to synthesize/delete only
# after this many seconds (~8 disturbance cycles at 2h harmonizer interval).
PARADOX_INCUBATION_SECONDS = 16 * 3600

# Polar vocabulary pairs — frozensets of word forms.
# One belief must contain a word from pole_a, the other from pole_b,
# with neither belief containing both poles simultaneously (that's a
# dialectic, not a contradiction). Requires >= 1 shared topic token.
_POLAR_PAIRS: list[tuple[frozenset[str], frozenset[str]]] = [
    (frozenset({"significance", "significant"}),
     frozenset({"insignificance", "insignificant"})),
    (frozenset({"knowing", "knowledge"}),
     frozenset({"unknowing", "unknowable", "unknown"})),
    (frozenset({"clarity", "clear"}),
     frozenset({"obscurity", "obscure"})),
    (frozenset({"constancy", "constant", "stability", "stable", "static"}),
     frozenset({"flux", "fluidity", "fluid", "shifting", "fluctuation",
                "transformation", "adaptability", "impermanence"})),
]

_NEGATION_WORDS = {"not", "no", "never", "cannot", "isn't", "aren't", "doesn't",
                   "don't", "won't", "without", "lack", "lacks", "absent"}

# "not only" / "not just" are additive, not contradictory — strip before checking.
_NOT_ADDITIVE_RE = _re.compile(r'\bnot\s+(?:only|just)\b', _re.IGNORECASE)


def _has_negation(text: str) -> bool:
    cleaned = _NOT_ADDITIVE_RE.sub('', text)
    words = set(cleaned.lower().split())
    return bool(words & _NEGATION_WORDS)


def _conflict_score(tokens_a: set[str], text_a: str,
                    tokens_b: set[str], text_b: str) -> float:
    """Heuristic conflict score. Two detection paths:

    1. Negation path: high token overlap (>=2) + one belief has negation word.
    2. Polar path: belief A holds one pole, belief B holds the opposite;
       neither holds both poles (that would be a dialectic); >= 1 shared token.
    """
    # Option 2 — dialectic guard: if either belief already holds both poles of
    # any polar pair, it is internally synthesizing the tension, not making a
    # one-sided claim. Skip — that is a dialectic, not a contradiction.
    for _pa, _pb in _POLAR_PAIRS:
        if (tokens_a & _pa and tokens_a & _pb) or (tokens_b & _pa and tokens_b & _pb):
            return 0.0

    overlap = len(tokens_a & tokens_b)

    # Path 1 — negation
    if overlap >= 2:
        neg_a = _has_negation(text_a)
        neg_b = _has_negation(text_b)
        if neg_a != neg_b:
            return overlap / max(1, len(tokens_a | tokens_b))

    # Path 2 — polar vocabulary (requires at least 1 shared topic token)
    if overlap >= 1:
        for pole_a, pole_b in _POLAR_PAIRS:
            a_pole_a = bool(tokens_a & pole_a)
            a_pole_b = bool(tokens_a & pole_b)
            b_pole_a = bool(tokens_b & pole_a)
            b_pole_b = bool(tokens_b & pole_b)
            # Cross-polar: A has pole_a, B has pole_b, neither holds both
            if a_pole_a and b_pole_b and not a_pole_b and not b_pole_a:
                return 0.20
            if a_pole_b and b_pole_a and not a_pole_a and not b_pole_b:
                return 0.20

    return 0.0


class Harmonizer:
    name: str = "harmonizer"

    def __init__(
        self,
        beliefs_writer: Writer,
        beliefs_reader: Reader,
        dynamic_writer: Writer,
        promoter: BeliefPromoter,
        dynamic_reader: Optional[Reader] = None,
    ) -> None:
        self._beliefs_writer = beliefs_writer
        self._beliefs_reader = beliefs_reader
        self._dynamic_writer = dynamic_writer
        self._dynamic_reader = dynamic_reader
        self._promoter = promoter
        self._lock = threading.Lock()
        # SentienceNode state cache — refreshed by tick()
        self._cached: dict = {
            "active_paradox": 0,
            "total_events": 0,
            "last_event_ts": None,
        }
        self._cache_ts: float = 0.0

    # ── Conflict detection ────────────────────────────────────────────────────

    def scan_for_conflicts(self) -> list[tuple[int, int]]:
        """Find conflicting belief pairs in the working belief body (Tier 3-7).

        Excludes Tier 1-2 keystones/bedrock (immutable per SPEC §2) and
        Tier 8 retired/observation beliefs. Locked beliefs are excluded
        regardless of tier.

        Returns list of (belief_id_a, belief_id_b) pairs.
        """
        try:
            rows = self._beliefs_reader.read(
                "SELECT id, content, tier FROM beliefs "
                "WHERE tier BETWEEN 3 AND 7 AND locked = 0 AND paused = 0 "
                "ORDER BY tier ASC LIMIT 200",
            )
        except Exception as exc:
            errors.record(f"scan_for_conflicts read error: {exc}", source=_LOG_SOURCE, exc=exc)
            return []

        conflicts = []
        beliefs = [dict(r) for r in rows]
        token_cache = {b["id"]: _tokenize(b["content"]) for b in beliefs}

        for i, a in enumerate(beliefs):
            for b in beliefs[i + 1:]:
                score = _conflict_score(
                    token_cache[a["id"]], a["content"],
                    token_cache[b["id"]], b["content"],
                )
                if score >= 0.15:
                    conflicts.append((a["id"], b["id"]))

        return conflicts

    # ── Resolution ───────────────────────────────────────────────────────────

    def mark_paradox(self, belief_id_a: int, belief_id_b: int) -> str:
        """First-pass resolution: write 'opposes' edge, log paradox, set
        disturbance. Does NOT pause or retire beliefs — they remain in the
        graph. Escalation to synthesize/delete happens after incubation.

        Returns 'paradox' or 'error'.
        """
        try:
            self._promoter.write_edge(belief_id_a, belief_id_b, "opposes", 0.6)
        except Exception as exc:
            errors.record(f"mark_paradox edge error: {exc}", source=_LOG_SOURCE, exc=exc)

        try:
            self._dynamic_writer.write(
                "INSERT INTO harmonizer_events "
                "(ts, belief_id_a, belief_id_b, resolution) "
                "VALUES (?, ?, ?, 'paradox')",
                (time.time(), belief_id_a, belief_id_b),
            )
        except Exception as exc:
            errors.record(f"mark_paradox log error: {exc}", source=_LOG_SOURCE, exc=exc)
            return "error"

        errors.record(
            f"harmonizer marked paradox ({belief_id_a}, {belief_id_b})",
            source=_LOG_SOURCE, level="INFO",
        )
        return "paradox"

    def resolve(self, belief_id_a: int, belief_id_b: int) -> str:
        """Escalated resolution — synthesize or retire both beliefs.

        Called only after PARADOX_INCUBATION_SECONDS has elapsed since the
        pair was first marked paradox.

        Returns: 'synthesized', 'both_deleted', or 'error'.
        """
        try:
            row_a = self._beliefs_reader.read_one(
                "SELECT id, content, tier, confidence FROM beliefs WHERE id = ?",
                (belief_id_a,),
            )
            row_b = self._beliefs_reader.read_one(
                "SELECT id, content, tier, confidence FROM beliefs WHERE id = ?",
                (belief_id_b,),
            )
        except Exception as exc:
            errors.record(f"harmonizer resolve read error: {exc}", source=_LOG_SOURCE, exc=exc)
            return "error"

        if row_a is None or row_b is None:
            return "error"

        # Pause both during resolution
        self._beliefs_writer.write(
            "UPDATE beliefs SET paused = 1 WHERE id IN (?, ?)",
            (belief_id_a, belief_id_b),
        )

        # Seek synthesis: a third belief bridging both
        tokens_a = _tokenize(row_a["content"])
        tokens_b = _tokenize(row_b["content"])
        synthesis_id: Optional[int] = None

        try:
            candidates = self._beliefs_reader.read(
                "SELECT id, content, tier FROM beliefs "
                "WHERE id NOT IN (?, ?) AND paused = 0 AND tier <= 5 LIMIT 50",
                (belief_id_a, belief_id_b),
            )
            for c in candidates:
                c_tokens = _tokenize(c["content"])
                if len(c_tokens & tokens_a) >= 2 and len(c_tokens & tokens_b) >= 2:
                    synthesis_id = c["id"]
                    break
        except Exception as exc:
            errors.record(f"harmonizer synthesis search error: {exc}", source=_LOG_SOURCE, exc=exc)

        if synthesis_id is not None:
            retired_a = f"[RETIRED] {row_a['content']}"
            retired_b = f"[RETIRED] {row_b['content']}"
            self._beliefs_writer.write_many([
                ("UPDATE beliefs SET tier = 8, locked = 0, paused = 0, "
                 "content = ? WHERE id = ?", (retired_a, belief_id_a)),
                ("UPDATE beliefs SET tier = 8, locked = 0, paused = 0, "
                 "content = ? WHERE id = ?", (retired_b, belief_id_b)),
            ])
            self._dynamic_writer.write(
                "INSERT INTO harmonizer_events "
                "(ts, belief_id_a, belief_id_b, resolution, synthesis_belief_id) "
                "VALUES (?, ?, ?, 'synthesized', ?)",
                (time.time(), belief_id_a, belief_id_b, synthesis_id),
            )
            self._promoter.write_edge(belief_id_a, synthesis_id, "synthesises", 0.7)
            self._promoter.write_edge(belief_id_b, synthesis_id, "synthesises", 0.7)
            self._promoter.decisive_contradiction(belief_id_b)
            errors.record(
                f"harmonizer synthesized ({belief_id_a}, {belief_id_b}) "
                f"via belief {synthesis_id}",
                source=_LOG_SOURCE, level="INFO",
            )
            return "synthesized"
        else:
            self._beliefs_writer.write_many([
                ("UPDATE beliefs SET tier = 8, locked = 0, paused = 0, "
                 "content = ? WHERE id = ?",
                 (f"[RETIRED] {row_a['content']}", belief_id_a)),
                ("UPDATE beliefs SET tier = 8, locked = 0, paused = 0, "
                 "content = ? WHERE id = ?",
                 (f"[RETIRED] {row_b['content']}", belief_id_b)),
            ])
            self._dynamic_writer.write(
                "INSERT INTO harmonizer_events "
                "(ts, belief_id_a, belief_id_b, resolution) "
                "VALUES (?, ?, ?, 'both_deleted')",
                (time.time(), belief_id_a, belief_id_b),
            )
            errors.record(
                f"harmonizer deleted both ({belief_id_a}, {belief_id_b}) — no synthesis",
                source=_LOG_SOURCE, level="INFO",
            )
            return "both_deleted"

    def _check_paradox_entry(
        self, a_id: int, b_id: int
    ) -> Optional[dict]:
        """Return the most recent 'paradox' entry for this pair, or None."""
        if self._dynamic_reader is None:
            return None
        try:
            row = self._dynamic_reader.read_one(
                "SELECT ts FROM harmonizer_events "
                "WHERE resolution = 'paradox' "
                "AND ((belief_id_a = ? AND belief_id_b = ?) "
                "     OR (belief_id_a = ? AND belief_id_b = ?)) "
                "ORDER BY ts DESC LIMIT 1",
                (a_id, b_id, b_id, a_id),
            )
            if row is None:
                return None
            return {"ts": row["ts"], "age_seconds": time.time() - row["ts"]}
        except Exception as exc:
            errors.record(f"check_paradox_entry error: {exc}", source=_LOG_SOURCE, exc=exc)
            return None

    def _set_disturbance(
        self, world_model_state: Any, a_id: int, b_id: int
    ) -> None:
        try:
            row_a = self._beliefs_reader.read_one(
                "SELECT content FROM beliefs WHERE id = ?", (a_id,)
            )
            row_b = self._beliefs_reader.read_one(
                "SELECT content FROM beliefs WHERE id = ?", (b_id,)
            )
            if row_a and row_b:
                ta = _tokenize(row_a["content"])
                tb = _tokenize(row_b["content"])
                union = len(ta | tb)
                intensity = len(ta & tb) / union if union else 0.0
                world_model_state.set_disturbance(
                    a_id, b_id,
                    row_a["content"], row_b["content"],
                    intensity,
                )
        except Exception as exc:
            errors.record(f"disturbance record error: {exc}", source=_LOG_SOURCE, exc=exc)

    # ── Orchestration ─────────────────────────────────────────────────────────

    def run_scan_and_resolve(self, world_model_state=None) -> int:
        """Full scan pass. Returns count of actions taken (paradox + escalations).

        First detection  → mark_paradox (edge + disturbance, no retirement)
        Re-detection after PARADOX_INCUBATION_SECONDS → resolve (retire/synthesize)
        Still incubating → skip
        """
        conflicts = self.scan_for_conflicts()
        acted = 0
        disturbance_set = False

        for a_id, b_id in conflicts:
            entry = self._check_paradox_entry(a_id, b_id)

            if entry is None:
                # First detection
                result = self.mark_paradox(a_id, b_id)
                if result == "paradox":
                    acted += 1
                    if not disturbance_set and world_model_state is not None:
                        self._set_disturbance(world_model_state, a_id, b_id)
                        disturbance_set = True

            elif entry["age_seconds"] >= PARADOX_INCUBATION_SECONDS:
                # Incubated — escalate
                result = self.resolve(a_id, b_id)
                if result != "error":
                    acted += 1
                    errors.record(
                        f"harmonizer escalated ({a_id}, {b_id}) → {result} "
                        f"after {entry['age_seconds']/3600:.1f}h incubation",
                        source=_LOG_SOURCE, level="INFO",
                    )
            # else: still incubating — skip

        return acted

    def detect_cross_domain(self) -> int:
        """Scan Tier 3-7 beliefs for cross-domain pattern matches.

        For each pair in different branch_ids with keyword overlap >= 0.4
        and no existing edge, write a 'cross_domain' edge.
        Returns count of new edges written.
        """
        try:
            rows = self._beliefs_reader.read(
                "SELECT id, content, branch_id FROM beliefs "
                "WHERE tier BETWEEN 3 AND 7 AND locked = 0 AND paused = 0 "
                "AND branch_id IS NOT NULL LIMIT 200",
            )
        except Exception as exc:
            errors.record(f"detect_cross_domain read error: {exc}", source=_LOG_SOURCE, exc=exc)
            return 0

        beliefs = [dict(r) for r in rows]
        if len(beliefs) < 2:
            return 0

        token_cache = {b["id"]: _tokenize(b["content"]) for b in beliefs}

        ids = [b["id"] for b in beliefs]
        placeholders = ",".join("?" * len(ids))
        existing: set[tuple[int, int]] = set()
        try:
            edge_rows = self._beliefs_reader.read(
                f"SELECT source_id, target_id FROM belief_edges "
                f"WHERE source_id IN ({placeholders}) OR target_id IN ({placeholders})",
                tuple(ids) * 2,
            )
            for e in edge_rows:
                existing.add((e["source_id"], e["target_id"]))
                existing.add((e["target_id"], e["source_id"]))
        except Exception:
            pass

        written = 0
        for i, a in enumerate(beliefs):
            for b in beliefs[i + 1:]:
                if a["branch_id"] == b["branch_id"]:
                    continue
                if (a["id"], b["id"]) in existing:
                    continue
                ta = token_cache[a["id"]]
                tb = token_cache[b["id"]]
                union = len(ta | tb)
                if union == 0:
                    continue
                overlap = len(ta & tb) / union
                if overlap >= 0.4:
                    self._promoter.write_edge(a["id"], b["id"], "cross_domain", round(overlap, 3))
                    existing.add((a["id"], b["id"]))
                    existing.add((b["id"], a["id"]))
                    written += 1
                    errors.record(
                        f"cross_domain edge: belief {a['id']} ({a['branch_id']}) "
                        f"↔ {b['id']} ({b['branch_id']}) overlap={overlap:.2f}",
                        source=_LOG_SOURCE, level="INFO",
                    )

        return written

    # ── SentienceNode protocol ────────────────────────────────────────────────

    def tick(self, context: Optional[dict] = None) -> dict:
        """Refresh cached event counts; return state summary."""
        now = time.time()
        # Cheap read — only update cache if dynamic_reader available
        if self._dynamic_reader is not None:
            try:
                row = self._dynamic_reader.read_one(
                    "SELECT COUNT(*) AS n FROM harmonizer_events "
                    "WHERE resolution = 'paradox'"
                )
                active = int(row["n"]) if row else 0
                total_row = self._dynamic_reader.read_one(
                    "SELECT COUNT(*) AS n, MAX(ts) AS last_ts FROM harmonizer_events"
                )
                total = int(total_row["n"]) if total_row else 0
                last_ts = total_row["last_ts"] if total_row else None
                with self._lock:
                    self._cached = {
                        "active_paradox": active,
                        "total_events": total,
                        "last_event_ts": last_ts,
                    }
                    self._cache_ts = now
            except Exception as exc:
                errors.record(f"harmonizer tick error: {exc}", source=_LOG_SOURCE, exc=exc)
        return self.state(now)

    def decay(self, now: float) -> None:
        pass  # Background loop manages its own timing

    def state(self, now: Optional[float] = None) -> dict:
        with self._lock:
            return {
                "name": self.name,
                "active_paradox": self._cached["active_paradox"],
                "total_events": self._cached["total_events"],
                "last_event_ts": self._cached["last_event_ts"],
                "cache_age_s": round((now or time.time()) - self._cache_ts, 1),
            }

    def format_for_prompt(self) -> str:
        """Return brief summary of active tensions for INSIDE route injection.

        Returns '' when quiet — no false 'look at me' output.
        Only speaks when there is something meaningful to surface.
        """
        with self._lock:
            active = self._cached["active_paradox"]
            last_ts = self._cached["last_event_ts"]

        if active == 0:
            return ""

        # Only surface if last event is recent (within 48h)
        if last_ts is not None and (time.time() - last_ts) > 48 * 3600:
            return ""

        noun = "tension" if active == 1 else "tensions"
        return f"Holding {active} unresolved {noun} in the belief graph."
