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
    ) -> None:
        self._writer = beliefs_writer
        self._reader = beliefs_reader
        self._promoter = promoter
        self._conversations_reader = conversations_reader
        self._problem_memory = problem_memory
        self._dynamic_reader = dynamic_reader
        self._mode_state = mode_state
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

    def crystallize(
        self,
        thought: str,
        fountain_event_id: int,
        ts: float,
        droplet: Optional[str] = None,
    ) -> Optional[int]:
        ok, reason = self._quality_check(thought, droplet=droplet)
        if not ok:
            errors.record(
                f"Fountain crystallization rejected ({reason}): {thought[:60]}",
                source=_LOG_SOURCE,
                level="INFO",
            )
            return None

        mode = self._mode_state.current() if self._mode_state else None
        category = mode.crystallization_category if mode else "fountain_insight"

        belief_id = self._writer.write(
            "INSERT INTO beliefs "
            "(content, tier, confidence, created_at, source, branch_id, locked) "
            "VALUES (?, 6, 0.70, ?, ?, 'systems', 0)",
            (thought, ts, category),
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
        rows = self._reader.read(
            "SELECT 1 FROM signal_cooldown "
            "WHERE content=? AND cooldown_until > ? LIMIT 1",
            (content, time.time()),
        )
        return bool(rows)

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

        Accepts first-person self-reference, questions, noticing/wonder
        vocabulary, and evaluative framing. Rejects pure external echoes
        (raw feed content with no cognitive framing).
        """
        if _SELF_REF_RE.search(thought):
            return True
        if "?" in thought:
            return True
        if _ENGAGEMENT_RE.search(thought):
            return True
        return False

    def _quality_check(self, thought: str, droplet: Optional[str] = None) -> Tuple[bool, str]:
        if not thought:
            return False, "empty"

        if len(thought) < 20:
            return False, "too_short"

        if len(thought) > 300:
            return False, "too_long"

        if not self._has_engagement(thought):
            return False, "no_engagement"

        # Blacklist check
        try:
            if self._promoter is not None:
                if self._promoter.is_blacklisted(thought):
                    return False, "blacklisted"
            else:
                bl_rows = self._reader.read("SELECT pattern FROM belief_blacklist")
                tl = thought.lower()
                for row in bl_rows:
                    if row["pattern"].lower() in tl:
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
                return False, "semantic_repeat"
        except Exception:
            pass

        # Cooldown table — groove spotter writes here when it detects a rut
        try:
            if self._is_on_cooldown(thought):
                errors.record(
                    f"Crystallizer REJECTED (cooldown): {thought[:80]}",
                    source=_LOG_SOURCE, level="INFO",
                )
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
                    return False, "droplet_repetition"
            except Exception:
                pass

        return True, "ok"
