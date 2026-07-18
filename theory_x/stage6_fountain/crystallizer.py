"""Fountain Crystallizer — Theory X Stage 6.

Passes fountain thoughts through a quality gate and writes survivors
as Tier 6 beliefs (source='fountain_insight').
"""
from __future__ import annotations

import logging
import os
import re
import time
from typing import Optional, Tuple

import errors
from substrate import Reader, Writer
from speech.governor import SpeechGovernor
from theory_x.executive_control import _ANALYTICAL_KEYWORDS, _TECHNICAL_KEYWORDS

THEORY_X_STAGE = 6

_LOG_SOURCE = "stage6_fountain.crystallizer"
logger = logging.getLogger("stage6_fountain.crystallizer")

# How long since last user message before we stop counting them as "active".
# 60s: if they replied a minute+ ago, don't crush speech probability by 70%.
_USER_ACTIVE_WINDOW_SECONDS = 60

_SELF_REF_RE = re.compile(r"\b(I|my|me|myself|mine|within|inside)\b", re.IGNORECASE)

# Words that signal cognitive engagement without requiring a first-person pronoun.
# Drift-register outputs include external observations ("huh, markets feel slow")
# that the old _SELF_REF_RE check would incorrectly reject.
_ENGAGEMENT_RE = re.compile(
    r"\b(huh|wait|oh|ah|hmm|hm|"
    r"notice|wonder|wondering|realize|realizing|see|saw|"
    r"feels?|seems?|looks?|sounds?|"
    r"still|already|again|finally|just|"
    r"odd|oddly|weird|weirdly|interesting|interestingly|strange|strangely|curious|curiously|"
    r"boring|tired|quiet|slow|busy|loud|"
    r"something|nothing|somebody|nobody|somewhere)\b",
    re.IGNORECASE,
)

# Session 36 (BUILD C) — anchor requirement for the contemplative-only
# engagement path. Session 30's census found 29% of the last 500 durable
# fountain_insight beliefs passed the engagement gate ONLY via a contemplative
# keyword (quiet/still/notice/feels/seems/wonder/tired/slow), no pronoun, no
# question mark; sampling 30 of those by content found ~67% genuinely empty
# mood-atmosphere but ~30% substantive with the keyword incidental (e.g.
# "...feels inextricably linked to economic updates (e.g. SpaceX IPO)").
# Naive keyword removal throws out the good 30% with the bad 67% — this
# requires a concrete anchor (digit, mid-sentence proper noun, or domain
# term) alongside the mood word instead. Self-ref and '?' paths are untouched.
#
# Measured against 171 labeled contemplative-only beliefs (recent 500
# fountain_insight, same filter as session 30's census) before shipping:
# keeps 20/25 (80%) of genuinely substantive content, correctly rejects
# 143/146 (98%) of genuine mood-atmosphere. Residual gaps, known and
# accepted rather than chased: substantive content with no digit/proper-noun/
# domain-term at all (e.g. "kids age verification online", "recent tech
# layoffs") still gets rejected (5/25 false negatives); a few vague-but-
# capitalized mentions ("investigate 'Adams'", "Moana research") and one
# lexical collision ("rust" the metal vs. Rust the language) still get
# wrongly kept (3/146 false positives). See journal/CARRY_OVER.md session 36
# for the full confusion matrix.
_DIGIT_RE = re.compile(r"\d")
_SENT_SPLIT_RE = re.compile(r"(?<=[.!?:])\s+")
_ANCHOR_WORD_RE = re.compile(r"[A-Za-z][A-Za-z']*")

# Generic appliance/computing acronyms -- capitalized the same way any
# all-caps abbreviation is, but name a common noun (a CPU, an AC unit), not a
# specific entity. A genuine proper noun (SpaceX, Aave, TZero) is never a
# member of this small closed set.
_GENERIC_ACRONYMS = frozenset({
    "cpu", "cpus", "gpu", "gpus", "ram", "rom", "ac", "tv", "it", "id",
    "url", "os", "led", "ip", "usb", "hdmi", "wifi",
})

# Reused from executive_control's Analytical/Technical keyword sets rather
# than a parallel list. A handful of overly generic single words are excluded
# -- measured against the labeled sample, these fired only on mood-atmosphere
# ("the market's whisper", "tech trends lately", "irregular patterns on the
# floor", "focusing on the data spikes") and were never the sole anchor for a
# labeled-substantive example.
_ANCHOR_TOO_GENERIC = frozenset({
    "trend", "trends", "pattern", "patterns", "data",
    "market", "markets", "deep dive", "deep-dive",
})
_DOMAIN_TERM_RE = re.compile(
    r"\b(" + "|".join(
        re.escape(t) for t in sorted(
            (set(_ANALYTICAL_KEYWORDS) | set(_TECHNICAL_KEYWORDS)) - _ANCHOR_TOO_GENERIC
        )
    ) + r")\b",
    re.IGNORECASE,
)


def _mid_sentence_capitalized(thought: str) -> Optional[str]:
    """First capitalized token that isn't the first word of its sentence --
    a position-based proper-noun heuristic. Unlike prose_stats.py's corpus
    check, this runs per-thought with no stored frequency history to compare
    against, so it can't distinguish a real entity from a one-off capitalized
    common noun -- the _GENERIC_ACRONYMS exclusion above covers the specific
    collisions measured in the labeled sample (CPU/AC/etc); rarer ones
    (e.g. "Adams", "Moana" used vaguely) remain a known, accepted gap.
    """
    for sent in _SENT_SPLIT_RE.split(thought):
        words = _ANCHOR_WORD_RE.findall(sent)
        for i, w in enumerate(words):
            if i == 0:
                continue
            if len(w) >= 2 and w[0].isupper() and w.lower() not in _GENERIC_ACRONYMS:
                return w
    return None


def _has_anchor(thought: str) -> bool:
    return bool(
        _DIGIT_RE.search(thought)
        or _mid_sentence_capitalized(thought)
        or _DOMAIN_TERM_RE.search(thought)
    )


# Verbal tics of the observer-trap — "stinking of Zen" patterns.
# Two or more matches signals performance of insight, not insight itself.
_PERFORMANCE_PATTERNS = [
    r"\bthe (quiet|quietude|echo|whisper) of (my|the) own\b",
    r"\bthe (dance|interplay|balance|tension) between\b",
    r"\bthe (complexity|depth|weight|fragility) of (my|the) own\b",
    r"\bas i (contemplate|observe|reflect|ponder)\b",
    r"\bthe (realization|recognition) (of|that)\b",
    r"\bwithin (myself|my own)\b",
    r"\bmy own (nature|existence|essence|being|awareness|thoughts)\b",
    r"\bthe nature of my\b",
]
_COMPILED_PERF_PATTERNS = [re.compile(p, re.IGNORECASE) for p in _PERFORMANCE_PATTERNS]

# Strip arc-context metadata that the LLM echoes from prompts back into
# output. Catches "(N fires)", "(N fires, return-transformation)",
# "(N fires, return-transformation, last ~M min ago)", and cascade doubles.
# See observations/metadata_contamination_audit_2026-05-02.md.
_METADATA_PATTERN = re.compile(r'\s*\(\d+\s+fires(?:[^)]*)?\)')


class FountainCrystallizer:

    def __init__(
        self,
        beliefs_writer: Writer,
        beliefs_reader: Reader,
        promoter=None,
        conversations_reader: Optional[Reader] = None,
        problem_memory=None,
        dynamic_reader: Optional[Reader] = None,
        mode_state=None,
        coherence_gate=None,
        dynamic_writer: Optional[Writer] = None,
    ) -> None:
        self._writer = beliefs_writer
        self._reader = beliefs_reader
        self._promoter = promoter
        self._conversations_reader = conversations_reader
        self._problem_memory = problem_memory
        self._dynamic_reader = dynamic_reader
        self._mode_state = mode_state
        self._gate = coherence_gate
        # Session 33 (census #10/#16) — durable reject record lives in
        # dynamic.db, not beliefs.db, to match tree_snapshots/tier_snapshots'
        # house pattern. Optional: None in constructions that don't pass it
        # (tests, older call sites) — the reject write is skipped, never
        # raises, per the "telemetry must never break the crystallizer" rule.
        self._dynamic_writer = dynamic_writer
        # Side channel for _quality_check -> crystallize(): which specific
        # fragment/pattern triggered a cooldown/blacklist/dedup reject. Kept
        # out of _quality_check's return tuple deliberately — that 2-tuple
        # signature is asserted directly by ~15 existing test call sites.
        self._last_reject_pattern: Optional[str] = None
        _gov_initial_ts = 0.0
        try:
            rows = beliefs_reader.read(
                "SELECT MAX(spoken_at) as last_spoken FROM speech_queue "
                "WHERE status='spoken' AND spoken_at IS NOT NULL"
            )
            if rows and rows[0]["last_spoken"]:
                _gov_initial_ts = float(rows[0]["last_spoken"])
        except Exception:
            pass
        self._governor = SpeechGovernor(
            min_gap_seconds=float(os.environ.get("NEX5_SPEECH_MIN_GAP", 180)),
            base_speak_probability=float(os.environ.get("NEX5_SPEECH_PROB", 1.0)),
            initial_ts=_gov_initial_ts,
        )
        # §8 intake resonance probe — observational, never raises. Hooked here
        # because FountainCrystallizer is the LIVE belief-write path.
        self._intake_resonance = None
        if os.environ.get("NEX5_INTAKE_RESONANCE_OFF") != "1":
            try:
                from theory_x.stage2_dynamic.intake_resonance import IntakeResonance
                self._intake_resonance = IntakeResonance(beliefs_reader, beliefs_writer)
            except Exception:
                self._intake_resonance = None

    def crystallize(
        self,
        thought: str,
        fountain_event_id: int,
        ts: float,
        droplet: Optional[str] = None,
        hot_branch: Optional[str] = None,
    ) -> Optional[int]:
        # Stillness guard — Row 9 extension. Metacognition writes a stillness_log
        # row when sustained groove exceeds threshold; we skip crystallization
        # while any row has expires_at > now (pure substrate read, zero coupling).
        if self._conversations_reader is not None:
            try:
                _now = time.time()
                _still = self._conversations_reader.read_one(
                    "SELECT id FROM stillness_log WHERE expires_at > ? LIMIT 1",
                    (_now,),
                )
                if _still:
                    errors.record(
                        "Stillness active — skipping fountain crystallization",
                        source=_LOG_SOURCE,
                        level="INFO",
                    )
                    return None
            except Exception:
                pass  # table absent on fresh install; proceed normally

        thought = _METADATA_PATTERN.sub('', thought).strip()
        ok, reason = self._quality_check(thought, droplet=droplet)
        if not ok:
            errors.record(
                f"Fountain crystallization rejected ({reason}): {thought[:60]}",
                source=_LOG_SOURCE,
                level="INFO",
            )
            matched = self._last_reject_pattern
            self._last_reject_pattern = None
            if self._dynamic_writer is not None:
                try:
                    self._dynamic_writer.write(
                        "INSERT INTO crystallization_rejects "
                        "(ts, reason, thought_excerpt, matched_pattern) "
                        "VALUES (?, ?, ?, ?)",
                        (time.time(), reason, thought[:200], matched),
                    )
                except Exception as exc:
                    errors.record(
                        f"crystallization_reject write failed: {exc}",
                        source=_LOG_SOURCE, exc=exc,
                    )
            return None

        # Phase 22 — Coherence Gate (runs after quality gate, before INSERT)
        if self._gate is not None:
            from theory_x.stage_gate.coherence_gate import ThoughtPacket, GateOutcome
            packet = ThoughtPacket(
                content=thought,
                source_node="fountain",
                confidence=0.70,
                branch_id=hot_branch,
            )
            decision = self._gate.check(packet)
            if decision.outcome != GateOutcome.ACCEPT:
                errors.record(
                    f"Fountain gate {decision.outcome.value} ({decision.reason}): {thought[:60]}",
                    source=_LOG_SOURCE,
                    level="INFO",
                )
                return None

        mode = self._mode_state.current() if self._mode_state else None
        category = mode.crystallization_category if mode else "fountain_insight"

        # PHASE 19 fix 2026-05-09: branch_id propagated from hot_branch instead of
        # hardcoded 'systems'. Was: bug where T6 fountain insights all attributed to
        # systems regardless of input branch. NULL fallback when hot_branch unavailable
        # (~37% of fires per live data).
        if self._intake_resonance is not None:
            try:
                self._intake_resonance.compute(thought)
            except Exception:
                pass
        # Surprise-weighted confidence — predictive processing feedback path.
        # High-surprise fires (genuine novelty) deposit heavier beliefs.
        # Fail-safe: defaults to 0.70 baseline if module/DB unavailable.
        _conf = 0.70
        _surp = 0.0
        if os.environ.get("NEX5_SURPRISE_WEIGHT", "1") == "1":
            try:
                from theory_x.stage_prediction.surprise_weighting import confidence_for_fire as _cff
                _conf, _surp = _cff()
            except Exception:
                pass
        belief_id = self._writer.write(
            "INSERT INTO beliefs "
            "(content, tier, confidence, created_at, source, branch_id, locked) "
            "VALUES (?, 6, ?, ?, ?, ?, 0)",
            (thought, _conf, ts, category, hot_branch),
        )

        self._writer.write(
            "INSERT INTO fountain_crystallizations "
            "(fountain_event_id, belief_id, ts, content) VALUES (?, ?, ?, ?)",
            (fountain_event_id, belief_id, ts, thought),
        )

        # Governor decides whether to speak this belief.
        # source='spectrum' beliefs are foundation variants — never enqueued for TTS.
        _speakable_sources = ('fountain_insight', 'synergized', 'koan', 'voice_fallback')
        try:
            from speech.config import SpeechConfig
            cfg = SpeechConfig.from_env()
            if (category in _speakable_sources
                    and cfg.enabled
                    and cfg.min_chars <= len(thought) <= cfg.max_chars):
                situation = self._read_situation()
                decision = self._governor.decide(
                    belief_content=thought,
                    valence=self._estimate_valence(thought),
                    situation=situation,
                    mode=mode,
                )
                gov_msg = (
                    f"Governor {'SPEAK' if decision.speak else 'HOLD'}: "
                    f"{decision.reason} | {thought[:60]}"
                )
                logger.info(gov_msg)
                errors.record(gov_msg, source=_LOG_SOURCE, level="INFO")
                if decision.speak:
                    existing = self._reader.read(
                        "SELECT id FROM speech_queue WHERE belief_id=? LIMIT 1",
                        (belief_id,),
                    )
                    if not existing:
                        self._writer.write(
                            "INSERT INTO speech_queue "
                            "(belief_id, content, voice, queued_at) VALUES (?, ?, ?, ?)",
                            (belief_id, thought, cfg.voice, ts),
                        )
        except Exception as exc:
            errors.record(
                f"speech enqueue failed: {exc}", source=_LOG_SOURCE, exc=exc
            )

        errors.record(
            f"Fountain crystallized: {thought[:80]}",
            source=_LOG_SOURCE,
            level="INFO",
        )
        return belief_id

    # ------------------------------------------------------------------

    def _was_recently_emitted(self, content: str, minutes: int = 30) -> bool:
        cutoff = time.time() - (minutes * 60)
        rows = self._reader.read(
            "SELECT 1 FROM beliefs "
            "WHERE source='fountain_insight' AND content=? AND created_at > ? LIMIT 1",
            (content, cutoff),
        )
        return bool(rows)

    def _was_recently_semantically_similar(
        self, content: str, minutes: int = 30, threshold: float = 0.85
    ) -> Optional[str]:
        """Return matching content if a semantically similar belief was emitted recently."""
        try:
            from theory_x.diversity.embeddings import embed, cosine
        except ImportError:
            return None

        cutoff = time.time() - (minutes * 60)
        rows = self._reader.read(
            "SELECT content FROM beliefs "
            "WHERE source='fountain_insight' AND created_at > ? "
            "ORDER BY created_at DESC LIMIT 20",
            (cutoff,),
        )
        if not rows:
            return None

        try:
            new_emb = embed(content)
        except Exception:
            return None

        for r in rows:
            prev_content = r["content"]
            if not prev_content:
                continue
            try:
                prev_emb = embed(prev_content)
                sim = cosine(new_emb, prev_emb)
                if sim >= threshold:
                    return prev_content
            except Exception:
                continue
        return None

    def _is_on_cooldown(self, content: str) -> bool:
        """Session 30 (B): was WHERE content=? — comparing a full new sentence
        against a stored n-gram/bigram fragment via exact equality, which can
        essentially never match (the stored value is a short pattern like
        "sunlight through leaves", not a full sentence). GrooveSpotter has
        fired 164+ alerts against this exact groove since 2026-05-17 and
        blocked nothing. Fixed to normalized substring containment.

        template_repetition patterns are " / "-joined bigrams (see
        theory_x.diversity.groove._detect_template_repetition) rather than a
        single contiguous phrase, so each stored pattern is split on " / "
        and any piece matching is a hit — this also works unchanged for
        ngram_repetition/exact_repetition patterns, which are already a
        single piece.
        """
        return self._find_cooldown_match(content) is not None

    def _find_cooldown_match(self, content: str) -> Optional[str]:
        """Same lookup as _is_on_cooldown, but returns the matched fragment
        itself (the specific piece of the stored pattern that hit) instead
        of a bool — session 33, so the durable reject record can carry
        WHICH pattern matched, not just that one did.
        """
        try:
            rows = self._reader.read(
                "SELECT content FROM signal_cooldown WHERE cooldown_until > ?",
                (time.time(),),
            )
        except Exception:
            return None
        if not rows:
            return None
        normalized = re.sub(r"\s+", " ", (content or "").lower()).strip()
        if not normalized:
            return None
        for row in rows:
            stored = row["content"] or ""
            for piece in stored.split(" / "):
                piece_norm = re.sub(r"\s+", " ", piece.lower()).strip()
                if piece_norm and piece_norm in normalized:
                    return piece.strip()
        return None

    def _read_situation(self) -> dict:
        now = time.time()
        user_active_recently = False
        user_asleep = False
        try:
            if self._conversations_reader is not None:
                recent = self._conversations_reader.read(
                    "SELECT MAX(timestamp) as last_ts FROM messages "
                    "WHERE role='user' AND timestamp > ?",
                    (now - _USER_ACTIVE_WINDOW_SECONDS,),
                )
                user_active_recently = bool(recent and recent[0]["last_ts"])
                last_any = self._conversations_reader.read(
                    "SELECT MAX(timestamp) as last_ts FROM messages WHERE role='user'"
                )
                no_recent = (
                    not last_any
                    or last_any[0]["last_ts"] is None
                    or (now - last_any[0]["last_ts"]) > 1800
                )
                hour = time.localtime(now).tm_hour
                user_asleep = (hour >= 23 or hour < 6) and no_recent
        except Exception:
            pass

        open_problems = False
        if self._problem_memory is not None:
            try:
                open_problems = bool(self._problem_memory.list_open())
            except Exception:
                pass

        return {
            "user_active_recently": user_active_recently,
            "user_asleep": user_asleep,
            "open_problems": open_problems,
        }

    def _estimate_valence(self, thought: str) -> Optional[dict]:
        """Placeholder — Stage 2 Attender will compute real valence."""
        return None

    @staticmethod
    def _has_engagement(thought: str) -> bool:
        """Return True if the thought shows cognitive engagement.

        Accepts first-person self-reference and questions unconditionally.
        Noticing/wonder vocabulary (no pronoun, no '?') additionally requires
        a concrete anchor (session 36, BUILD C) -- see the comment block
        above _has_anchor for why. Rejects pure external echoes (raw feed
        content with no cognitive framing at all).
        """
        if _SELF_REF_RE.search(thought):
            return True
        if "?" in thought:
            return True
        if _ENGAGEMENT_RE.search(thought):
            return _has_anchor(thought)
        return False

    def _quality_check(self, thought: str, droplet: Optional[str] = None) -> Tuple[bool, str]:
        # Reset the matched-pattern side channel for this call — see __init__.
        self._last_reject_pattern = None

        if not thought:
            return False, "empty"

        if len(thought) < 20:
            return False, "too_short"

        if len(thought) > 300:
            return False, "too_long"

        if not self._has_engagement(thought):
            # Distinguish "engagement keyword matched but no anchor" (session
            # 36, BUILD C) from "no engagement signal at all" -- same check
            # _has_engagement already did, re-run only on the reject path so
            # the durable record carries which keyword almost passed.
            if (not _SELF_REF_RE.search(thought) and "?" not in thought):
                m = _ENGAGEMENT_RE.search(thought)
                if m:
                    self._last_reject_pattern = m.group()
                    return False, "contemplative_no_anchor"
            return False, "no_engagement"

        # Blacklist check
        try:
            if self._promoter is not None:
                if self._promoter.is_blacklisted(thought):
                    # promoter.is_blacklisted() returns bool only — do a
                    # cheap second lookup, reject-path-only, purely so the
                    # durable record carries which pattern actually matched
                    # instead of nothing.
                    try:
                        bl_rows = self._reader.read("SELECT pattern FROM belief_blacklist")
                        tl = thought.lower()
                        for row in bl_rows:
                            if row["pattern"].lower() in tl:
                                self._last_reject_pattern = row["pattern"]
                                break
                    except Exception:
                        pass
                    return False, "blacklisted"
            else:
                bl_rows = self._reader.read("SELECT pattern FROM belief_blacklist")
                tl = thought.lower()
                for row in bl_rows:
                    if row["pattern"].lower() in tl:
                        self._last_reject_pattern = row["pattern"]
                        return False, "blacklisted"
        except Exception:
            pass

        # Performance-insight detection: 2+ tired patterns + similarity to recent fires
        try:
            perf_matches = sum(
                1 for p in _COMPILED_PERF_PATTERNS if p.search(thought)
            )
            if perf_matches >= 2:
                recent = self._reader.read(
                    "SELECT content FROM beliefs "
                    "WHERE source='fountain_insight' "
                    "ORDER BY created_at DESC LIMIT 5"
                )
                thought_words = set(thought.lower().split())
                for r in recent:
                    prev_words = set((r["content"] or "").lower().split())
                    if not prev_words:
                        continue
                    similarity = len(thought_words & prev_words) / len(thought_words | prev_words)
                    if similarity > 0.3:
                        errors.record(
                            f"Crystallizer REJECTED (performance pattern + similarity "
                            f"{similarity:.2f}): {thought[:80]}",
                            source=_LOG_SOURCE, level="INFO",
                        )
                        self._last_reject_pattern = (
                            f"sim={similarity:.2f} vs: {(r['content'] or '')[:120]}"
                        )
                        return False, "performance_insight_repetition"
        except Exception:
            pass

        # Near-duplicate check — Jaccard > 0.6 with existing fountain/synergized beliefs
        try:
            existing = self._reader.read(
                "SELECT content FROM beliefs "
                "WHERE source IN ('fountain_insight', 'synergized')"
            )
            new_words = set(thought.lower().split())
            if new_words:
                for row in existing:
                    ex_words = set(row["content"].lower().split())
                    if not ex_words:
                        continue
                    overlap = len(new_words & ex_words) / len(new_words | ex_words)
                    if overlap > 0.6:
                        self._last_reject_pattern = (
                            f"jaccard={overlap:.2f} vs: {(row['content'] or '')[:120]}"
                        )
                        return False, "near_duplicate"
        except Exception:
            pass

        # Recent exact-emission guard — same content within 30 min is a rut
        try:
            if self._was_recently_emitted(thought, minutes=30):
                errors.record(
                    f"Crystallizer REJECTED (recent_repeat): {thought[:80]}",
                    source=_LOG_SOURCE, level="INFO",
                )
                self._last_reject_pattern = "exact content match, <30min"
                return False, "recent_repeat"
        except Exception:
            pass

        # Semantic similarity guard — catches near-duplicate rut variations
        try:
            similar = self._was_recently_semantically_similar(thought, minutes=30, threshold=0.85)
            if similar:
                errors.record(
                    f"Crystallizer REJECTED (semantic_repeat, sim>=0.85): {thought[:80]} "
                    f"[similar to: {similar[:60]}]",
                    source=_LOG_SOURCE, level="INFO",
                )
                self._last_reject_pattern = similar[:200]
                return False, "semantic_repeat"
        except Exception:
            pass

        # Cooldown table — groove spotter writes here when it detects a rut
        try:
            _cd_match = self._find_cooldown_match(thought)
            if _cd_match:
                errors.record(
                    f"Crystallizer REJECTED (cooldown): {thought[:80]}",
                    source=_LOG_SOURCE, level="INFO",
                )
                self._last_reject_pattern = _cd_match
                return False, "cooldown"
        except Exception:
            pass

        # Droplet-level dedup — catches idea repetition even in new words
        if droplet:
            try:
                _dr = self._dynamic_reader or self._reader
                recent_droplets = _dr.read(
                    "SELECT droplet FROM fountain_events "
                    "WHERE droplet IS NOT NULL AND ts > ? "
                    "ORDER BY ts DESC LIMIT 20",
                    (time.time() - 3600,),
                )
                droplet_matches = sum(
                    1 for r in recent_droplets if r["droplet"] == droplet
                )
                if droplet_matches >= 2:
                    errors.record(
                        f"Crystallizer REJECTED (droplet repeat x{droplet_matches}): {droplet}",
                        source=_LOG_SOURCE, level="INFO",
                    )
                    self._last_reject_pattern = droplet
                    return False, "droplet_repetition"
            except Exception:
                pass

        return True, "ok"
