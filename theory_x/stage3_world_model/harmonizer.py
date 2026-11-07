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

import os
import re as _re
import time
import threading
from typing import Any, Optional

import errors
from theory_x.stage3_world_model.undo_log import log_undo
from substrate import Writer, Reader
from .retrieval import _tokenize
from .promotion import BeliefPromoter

THEORY_X_STAGE = 3

_LOG_SOURCE = "harmonizer"

# Incubation: pairs marked 'paradox' escalate to synthesize/delete only
# after this many seconds (~8 disturbance cycles at 2h harmonizer interval).
PARADOX_INCUBATION_SECONDS = 16 * 3600

# 2026-11-07: scan_for_conflicts() samples LIMIT 200 of a pool that has grown
# to 3,700+ (tier 3 alone is 600+, tiers 5-7 are never reached at all).
# Escalation depends on the SAME pair being re-detected on a LATER scan --
# as the pool outgrew the window, that became vanishingly unlikely, and
# escalation silently stalled (measured live: 40 pairs stuck at 'paradox'
# for up to 277h against the 16h threshold). NEX5_HARMONIZER_PARADOX_FIX
# (default OFF) adds a SEPARATE pass that re-checks already-flagged pairs
# directly by id, independent of whether the capped scan resamples them.
# Does not change scan_for_conflicts() or resolve() themselves, and flag-off
# reproduces run_scan_and_resolve()'s exact existing behaviour.
_PARADOX_FIX_FLAG = "NEX5_HARMONIZER_PARADOX_FIX"

# SENTIENCE_PROGRAM Phase D 2026-11-07 (dark): at escalation, keep both
# beliefs and record the contradiction as a held tension instead of
# retiring/synthesizing them. See resolve()/_hold_as_tension().
_HELD_TENSION_FLAG = "NEX5_HELD_TENSION"

# 2026-11-08 (dark): _conflict_score() requires >=1-2 SHARED TOKENS before it
# will ever flag a conflict -- two beliefs that are genuinely opposed but
# share no literal words (paraphrase, synonym) are invisible to it,
# structurally, regardless of how clearly opposed they are. NEX5_SEMANTIC_CONFLICT
# (default OFF) adds a second path, tried ONLY when the token path finds
# nothing (score == 0.0), using the sentence-embedding model already loaded
# elsewhere in the codebase (theory_x/diversity/embeddings.py, cached by
# belief id) instead of token overlap to establish "same topic," then the
# SAME negation-sign-disagreement signal the token path already uses
# (_has_negation, which never needed token overlap in the first place). Pure
# addition: never runs when the token path already found something, so it
# cannot change any score or conflict the token path already catches; flag
# off is byte-identical to today.
_SEMANTIC_CONFLICT_FLAG = "NEX5_SEMANTIC_CONFLICT"
# PROVISIONAL (no live measurement yet): embeddings.cosine() is normalised
# to [0,1] (0.5 = orthogonal, 1.0 = identical). 0.65 is a guess at "clearly
# the same topic," not a measured bar -- re-derive once there is a live
# round to check it against, same status as this file's other guessed
# constants (PARADOX_INCUBATION_SECONDS, _TENSION_CAP).
_SEMANTIC_CONFLICT_TOPIC_THRESHOLD = 0.65
# PROVISIONAL (no live measurement yet): cap on concurrently OPEN held
# tensions. Beyond the cap, a new escalation falls back to the original
# retire/synthesize path rather than growing the open set unbounded --
# the spec's own named failure mode ("tensions accumulate... clog
# retrieval"). Re-derive once there is a live rate to measure against.
_TENSION_CAP = 50
# PROVISIONAL: an open tension older than this is auto-resolved by decay()
# as a retention fallback, even with no other resolution. Not currently
# invoked by any live loop (see decay()'s docstring) -- exercised by tests
# and by whoever later wires decay() into _harmonizer_loop.
_TENSION_STALE_DAYS = 30

# 2026-11-08 (dark): tick()'s "active_paradox" counts ALL-TIME rows with
# resolution='paradox', including pairs that have SINCE escalated to
# synthesized/both_deleted/held_tension -- a later row for the same pair
# doesn't remove or supersede the earlier count. Measured live 2026-11-07:
# 73 all-time vs 40 actually still open. This directly feeds the already-
# live, unflagged format_for_prompt() line ("Holding N unresolved tensions
# in the belief graph"), so the number she can surface in chat is wrong
# right now. NEX5_HARMONIZER_TENSION_COUNT_FIX (default OFF) swaps in
# _open_paradox_pairs()'s correct "latest event per pair is still paradox"
# count. Flagged rather than left unflagged for the same reason as the
# LIMIT-200 fix: this feeds live, unflagged chat-surfaced text, so an
# unflagged fix would change that text on ANY future restart, including an
# unplanned one, not just a deliberate one made after r77 closes.
_ACTIVE_COUNT_FIX_FLAG = "NEX5_HARMONIZER_TENSION_COUNT_FIX"

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


def _semantic_conflict_score(id_a: int, text_a: str, id_b: int, text_b: str) -> float:
    """Dark behind NEX5_SEMANTIC_CONFLICT. Catches a conflict _conflict_score
    cannot see by construction: two beliefs opposed in meaning but sharing
    no tokens at all (paraphrase, synonym, zero literal overlap). Embedding
    cosine similarity stands in for "same topic" (what token overlap does
    in the token path); _has_negation (text-level, no token overlap needed)
    still carries the polarity signal. Same-topic + same-polarity is
    agreement, not conflict, and correctly scores 0.0."""
    if os.environ.get(_SEMANTIC_CONFLICT_FLAG) != "1":
        return 0.0
    try:
        from theory_x.diversity.embeddings import embed_belief, cosine
        sim = cosine(embed_belief(id_a, text_a), embed_belief(id_b, text_b))
    except Exception as exc:
        errors.record(f"semantic conflict score error: {exc}", source=_LOG_SOURCE, exc=exc)
        return 0.0
    if sim < _SEMANTIC_CONFLICT_TOPIC_THRESHOLD:
        return 0.0  # not even the same topic -- unrelated, not opposed
    if _has_negation(text_a) == _has_negation(text_b):
        return 0.0  # same topic, same polarity -- agreement
    return sim


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
                if score == 0.0:
                    # Only tried when the token path found nothing -- never
                    # overrides or changes a score the token path produced.
                    score = _semantic_conflict_score(
                        a["id"], a["content"], b["id"], b["content"],
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
        """Escalated resolution.

        Called only after PARADOX_INCUBATION_SECONDS has elapsed since the
        pair was first marked paradox.

        Returns: 'synthesized', 'both_deleted', 'held_tension', or 'error'.
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
        log_undo(self._beliefs_writer, "paused", (belief_id_a, belief_id_b),
                 cause_ref=f"harmonizer_resolve:{belief_id_a},{belief_id_b}")

        # SENTIENCE_PROGRAM Phase D (dark, NEX5_HELD_TENSION): instead of
        # retiring/synthesizing, keep both beliefs and record the
        # contradiction as a held tension. Flag unset -> unchanged below.
        if os.environ.get(_HELD_TENSION_FLAG) == "1":
            return self._hold_as_tension(belief_id_a, belief_id_b)

        return self._retire_both_or_synthesize(belief_id_a, belief_id_b, row_a, row_b)

    def _retire_both_or_synthesize(
        self, belief_id_a: int, belief_id_b: int, row_a: Any, row_b: Any
    ) -> str:
        """The original resolve() body, unchanged: seek a synthesis bridge,
        else retire both. Called when NEX5_HELD_TENSION is unset, and as the
        held-tension path's own cap-exceeded fallback (see _hold_as_tension)."""
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
            self._log_retired(belief_id_a, belief_id_b, "synthesized")
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
            self._log_retired(belief_id_a, belief_id_b, "both_deleted")
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

    # ── Phase D: held tension (dark, NEX5_HELD_TENSION) ────────────────────────

    def _open_tension_count(self) -> int:
        try:
            row = self._dynamic_reader.read_one(
                "SELECT COUNT(*) AS n FROM held_tensions WHERE resolved_at IS NULL"
            )
            return int(row["n"]) if row else 0
        except Exception as exc:
            errors.record(f"_open_tension_count error: {exc}", source=_LOG_SOURCE, exc=exc)
            return 0

    def _hold_as_tension(self, belief_id_a: int, belief_id_b: int) -> str:
        """Both beliefs survive: unpause them (undoing resolve()'s transient
        pause), change nothing else about them, and record the contradiction
        as an open held_tensions row. Falls back to the original
        retire/synthesize path if the cap is already reached, so a pair is
        never left in limbo with no outcome at all."""
        if self._open_tension_count() >= _TENSION_CAP:
            errors.record(
                f"held-tension cap ({_TENSION_CAP}) reached; falling back to "
                f"retire/synthesize for ({belief_id_a}, {belief_id_b})",
                source=_LOG_SOURCE, level="WARNING",
            )
            try:
                row_a = self._beliefs_reader.read_one(
                    "SELECT id, content, tier, confidence FROM beliefs WHERE id = ?",
                    (belief_id_a,))
                row_b = self._beliefs_reader.read_one(
                    "SELECT id, content, tier, confidence FROM beliefs WHERE id = ?",
                    (belief_id_b,))
            except Exception as exc:
                errors.record(f"held-tension fallback read error: {exc}",
                              source=_LOG_SOURCE, exc=exc)
                return "error"
            if row_a is None or row_b is None:
                return "error"
            return self._retire_both_or_synthesize(belief_id_a, belief_id_b, row_a, row_b)

        self._beliefs_writer.write(
            "UPDATE beliefs SET paused = 0 WHERE id IN (?, ?)",
            (belief_id_a, belief_id_b),
        )
        log_undo(self._beliefs_writer, "unpaused", (belief_id_a, belief_id_b),
                 cause_ref=f"harmonizer_held_tension:{belief_id_a},{belief_id_b}")
        self._dynamic_writer.write(
            "INSERT INTO held_tensions (belief_id_a, belief_id_b, created_at) "
            "VALUES (?, ?, ?)",
            (min(belief_id_a, belief_id_b), max(belief_id_a, belief_id_b), time.time()),
        )
        self._dynamic_writer.write(
            "INSERT INTO harmonizer_events "
            "(ts, belief_id_a, belief_id_b, resolution) "
            "VALUES (?, ?, ?, 'held_tension')",
            (time.time(), belief_id_a, belief_id_b),
        )
        errors.record(
            f"harmonizer held tension ({belief_id_a}, {belief_id_b}) -- both survive",
            source=_LOG_SOURCE, level="INFO",
        )
        return "held_tension"

    def _resolve_tension(self, tension_id: int, reason: str) -> None:
        self._dynamic_writer.write(
            "UPDATE held_tensions SET resolved_at = ?, resolved_reason = ? WHERE id = ?",
            (time.time(), reason, tension_id),
        )

    def sweep_resolved_tensions(self, now: Optional[float] = None) -> int:
        """Auto-resolve open held tensions whose basis has gone away: either
        side left the live pool (promoted to keystone or already retired by
        another path -- 'belief_left_pool'), or the tension has simply aged
        past _TENSION_STALE_DAYS with no other resolution ('stale_retention').
        Returns count resolved. Not currently invoked by any live loop --
        see decay()'s docstring."""
        now = now if now is not None else time.time()
        try:
            rows = self._dynamic_reader.read(
                "SELECT id, belief_id_a, belief_id_b, created_at FROM held_tensions "
                "WHERE resolved_at IS NULL"
            )
        except Exception as exc:
            errors.record(f"sweep_resolved_tensions read error: {exc}",
                          source=_LOG_SOURCE, exc=exc)
            return 0
        resolved = 0
        stale_cutoff = _TENSION_STALE_DAYS * 86400
        for r in rows:
            if not (self._still_eligible(r["belief_id_a"]) and self._still_eligible(r["belief_id_b"])):
                self._resolve_tension(r["id"], "belief_left_pool")
                resolved += 1
            elif now - r["created_at"] >= stale_cutoff:
                self._resolve_tension(r["id"], "stale_retention")
                resolved += 1
        return resolved

    def _log_retired(self, a: int, b: int, how: str) -> None:
        """Retirement unpauses both and moves them to tier 8 (the weakest) -- a
        demotion that never stamps last_demoted_at, so only the log sees it."""
        ref = f"harmonizer_retire:{how}:{a},{b}"
        log_undo(self._beliefs_writer, "unpaused", (a, b), cause_ref=ref)
        log_undo(self._beliefs_writer, "demoted", (a, b), cause_ref=ref)

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

        acted += self._escalate_stale_paradoxes()
        return acted

    # ── Direct re-check of already-flagged pairs (the LIMIT-200 fix) ───────────

    def _open_paradox_pairs(self) -> list[tuple[int, int, float]]:
        """(belief_id_a, belief_id_b, paradox_ts) for every unordered pair whose
        MOST RECENT harmonizer_events row is 'paradox' -- i.e. flagged but not
        yet escalated or superseded. Computed directly from the event log, not
        from scan_for_conflicts()'s capped sample."""
        if self._dynamic_reader is None:
            return []
        try:
            rows = self._dynamic_reader.read(
                "SELECT belief_id_a, belief_id_b, resolution, ts "
                "FROM harmonizer_events ORDER BY ts"
            )
        except Exception as exc:
            errors.record(f"_open_paradox_pairs read error: {exc}", source=_LOG_SOURCE, exc=exc)
            return []
        latest: dict[tuple[int, int], tuple[str, float]] = {}
        for r in rows:
            key = (r["belief_id_a"], r["belief_id_b"])
            key = (min(key), max(key))
            latest[key] = (r["resolution"], r["ts"])
        return [(k[0], k[1], v[1]) for k, v in latest.items() if v[0] == "paradox"]

    def _still_eligible(self, belief_id: int) -> bool:
        """Same liveness test scan_for_conflicts() applies -- tier 3-7,
        unlocked, unpaused. A pair found via _open_paradox_pairs() may have
        had one side promoted to a keystone, or already retired by another
        path, since it was marked; such a pair is no longer a live tension
        and must NOT be force-resolved here."""
        try:
            row = self._beliefs_reader.read_one(
                "SELECT tier, locked, paused FROM beliefs WHERE id = ?", (belief_id,)
            )
        except Exception:
            return False
        if row is None:
            return False
        return 3 <= row["tier"] <= 7 and not row["locked"] and not row["paused"]

    def _escalate_stale_paradoxes(self) -> int:
        """Dark by default (_PARADOX_FIX_FLAG). Escalates every open paradox
        pair past incubation regardless of whether scan_for_conflicts()
        resampled it this pass -- see the flag's module-level comment for why
        that resampling can no longer be relied on. Flag unset: no-op, exact
        prior behaviour."""
        if os.environ.get(_PARADOX_FIX_FLAG) != "1":
            return 0
        acted = 0
        now = time.time()
        for a_id, b_id, ts in self._open_paradox_pairs():
            if now - ts < PARADOX_INCUBATION_SECONDS:
                continue
            if not (self._still_eligible(a_id) and self._still_eligible(b_id)):
                continue  # no longer a live tension; leave it be
            result = self.resolve(a_id, b_id)
            if result != "error":
                acted += 1
                errors.record(
                    f"harmonizer direct-escalated ({a_id}, {b_id}) → {result} "
                    f"after {(now - ts)/3600:.1f}h (paradox-fix pass)",
                    source=_LOG_SOURCE, level="INFO",
                )
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
                if os.environ.get(_ACTIVE_COUNT_FIX_FLAG) == "1":
                    active = len(self._open_paradox_pairs())
                else:
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
        """Nothing currently calls Harmonizer.decay() (verified by grep,
        2026-11-07) -- _harmonizer_loop calls run_scan_and_resolve()/tick()
        only, same as before this change. Filling this in does not make it
        reachable from the live process; it only gives the Phase D retention
        sweep (sweep_resolved_tensions(), see held_tensions) somewhere to
        live via the generic SentienceNode interface, for a test or a future,
        separately-decided wiring to call. Background loop otherwise manages
        its own timing."""
        try:
            self.sweep_resolved_tensions(now=now)
        except Exception as exc:
            errors.record(f"harmonizer decay error: {exc}", source=_LOG_SOURCE, exc=exc)

    def state(self, now: Optional[float] = None) -> dict:
        with self._lock:
            return {
                "name": self.name,
                "active_paradox": self._cached["active_paradox"],
                "total_events": self._cached["total_events"],
                "last_event_ts": self._cached["last_event_ts"],
                "cache_age_s": round((now or time.time()) - self._cache_ts, 1),
            }

    def _content_specific_tension_line(self) -> str:
        """Phase D (NEX5_HELD_TENSION): name the actual held beliefs instead
        of a bare count. '' if the flag is off or no open tension exists --
        callers fall through to the pre-existing generic line unchanged."""
        if os.environ.get(_HELD_TENSION_FLAG) != "1":
            return ""
        try:
            row = self._dynamic_reader.read_one(
                "SELECT belief_id_a, belief_id_b FROM held_tensions "
                "WHERE resolved_at IS NULL ORDER BY created_at DESC LIMIT 1"
            )
        except Exception as exc:
            errors.record(f"_content_specific_tension_line read error: {exc}",
                          source=_LOG_SOURCE, exc=exc)
            return ""
        if row is None:
            return ""
        try:
            row_a = self._beliefs_reader.read_one(
                "SELECT content FROM beliefs WHERE id = ?", (row["belief_id_a"],))
            row_b = self._beliefs_reader.read_one(
                "SELECT content FROM beliefs WHERE id = ?", (row["belief_id_b"],))
        except Exception:
            return ""
        if row_a is None or row_b is None:
            return ""

        def _clip(text: str, n: int = 90) -> str:
            text = text.strip()
            return text if len(text) <= n else text[:n].rsplit(" ", 1)[0] + "…"

        return (f"I notice I hold both: \"{_clip(row_a['content'])}\" "
                f"and \"{_clip(row_b['content'])}\".")

    def format_for_prompt(self) -> str:
        """Return brief summary of active tensions for INSIDE route injection.

        Returns '' when quiet — no false 'look at me' output.
        Only speaks when there is something meaningful to surface.
        """
        tension_line = self._content_specific_tension_line()
        if tension_line:
            return tension_line

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
