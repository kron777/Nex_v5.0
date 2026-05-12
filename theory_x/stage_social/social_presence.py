"""SocialPresence — Phase 38 (SOCIAL_PRESENCE_PROTOCOL.md).

SentienceNode: NEX modeling her own social presence (S5.5 SocialCognition
reframed inward). Per-tick: snapshot() reads recent outputs + interactions
across messages, speech_queue, beliefs, and sessions; computes voice/style
and engagement metrics; generates templated self-reports; writes one row.

Audit findings:
- speech_queue lives in beliefs.db (column: queued_at REAL)
- messages uses `timestamp` INTEGER (not created_at)
- Self-authored belief sources: fountain_insight, synergized, voice_fallback,
  counterfactual, precipitated_from_dynamic
- affect_state is single-row replace → avg_arousal_during_outputs proxies
  to the current arousal value
"""
from __future__ import annotations

import json
import re
import threading
import time
from collections import Counter
from typing import Any, Optional

import errors

_LOG_SOURCE = "social_presence"

# Self-authored belief sources (verified in Phase 38 audit)
_SELF_AUTHORED_SOURCES = (
    "fountain_insight",
    "synergized",
    "voice_fallback",
    "counterfactual",
    "precipitated_from_dynamic",
)
_SELF_AUTHORED_SQL = ", ".join(f"'{s}'" for s in _SELF_AUTHORED_SOURCES)


def _generate_tags(content: str) -> list:
    if not content or not content.strip():
        return []
    try:
        from theory_x.tag_protocol.tag_ops import generate
        return generate(content)
    except Exception:
        return []


class SocialPresence:
    """SentienceNode: NEX modeling her own social presence.

    Per SOCIAL_PRESENCE_PROTOCOL.md §2. Per-tick: snapshot() reads recent
    outputs and interactions, computes voice/style + engagement metrics,
    generates templated self-reports, writes one row to
    social_presence_snapshots.
    """

    # §8 calibration constants
    _TICK_INTERVAL_S         = 300
    _OUTPUT_WINDOW_S         = 300
    _VOCAB_TOP_N             = 10
    _TOPIC_TOP_N             = 5
    _LATENCY_WINDOW_S        = 1800
    _ACTIVE_SESSION_WINDOW_S = 3600

    # Inline stopwords — common English function words
    _STOPWORDS = frozenset({
        "the", "a", "an", "and", "or", "but", "if", "is", "are",
        "was", "were", "be", "been", "being", "of", "to", "in",
        "on", "at", "for", "with", "by", "from", "as", "that",
        "this", "it", "its", "i", "me", "my", "you", "your",
        "he", "she", "they", "them", "we", "us", "our",
        "have", "has", "had", "do", "does", "did", "not", "no",
        "so", "yet", "than", "then", "such", "what",
        "which", "who", "when", "where", "why", "how",
        "there", "here", "just", "also", "very", "would", "could",
        "should", "will", "may", "might", "can", "about", "into",
        "through", "each", "more", "most", "other", "some", "all",
        "their", "its", "any", "these", "those", "am",
    })

    name: str = "social_presence"

    def __init__(
        self,
        dynamic_reader,
        dynamic_writer,
        beliefs_reader,
        conversations_reader,
        interval_seconds: float = _TICK_INTERVAL_S,
    ) -> None:
        self._dr = dynamic_reader
        self._dw = dynamic_writer
        self._br = beliefs_reader
        self._cr = conversations_reader
        self._interval = interval_seconds

        self._stop: Optional[threading.Event] = None
        self._thread: Optional[threading.Thread] = None

        self._tick_count: int = 0
        self._total_snapshots: int = 0
        self._last_tick_at: float = 0.0

        # Vocab distinctiveness baseline — loaded once at init
        self._baseline_tokens: frozenset = frozenset()
        self._load_baseline()

    def _load_baseline(self) -> None:
        try:
            rows = self._br.read(
                "SELECT content FROM beliefs ORDER BY id ASC LIMIT 1000"
            )
            tokens: set[str] = set()
            for r in rows:
                tokens.update(self._tokenize(r["content"] or ""))
            self._baseline_tokens = frozenset(tokens)
        except Exception:
            self._baseline_tokens = frozenset()

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
                f"social_presence snapshot error: {exc}",
                source=_LOG_SOURCE, exc=exc,
            )

        self._tick_count += 1
        errors.record(
            f"SocialPresence tick {self._tick_count}: snapshot_id={snap_id}",
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
            target=_run, name="social_presence", daemon=True,
        )
        self._thread.start()
        errors.record(
            f"social_presence loop started (interval={int(interval)}s)",
            source=_LOG_SOURCE, level="INFO",
        )

    def stop(self) -> None:
        if self._stop is not None:
            self._stop.set()

    # ── Text helpers ──────────────────────────────────────────────────────────

    def _tokenize(self, text: str) -> list[str]:
        """Lowercase, strip punctuation, split on whitespace, filter stopwords."""
        if not text:
            return []
        text = text.lower()
        text = re.sub(r"[^a-z0-9\s]", " ", text)
        return [t for t in text.split() if t and t not in self._STOPWORDS and len(t) > 1]

    def _compute_vocab_distinctiveness(self, recent_tokens: set[str]) -> float:
        """Jaccard divergence: 1 - |recent ∩ baseline| / |recent ∪ baseline|."""
        if not recent_tokens:
            return 0.0
        if not self._baseline_tokens:
            return 1.0
        intersection = len(recent_tokens & self._baseline_tokens)
        union = len(recent_tokens | self._baseline_tokens)
        return 1.0 - (intersection / union) if union > 0 else 0.0

    @staticmethod
    def _avg_sentence_length(texts: list[str]) -> float:
        """Mean word count per sentence across all texts."""
        lengths = []
        for text in texts:
            sentences = re.split(r"[.!?]+", text)
            for s in sentences:
                words = s.split()
                if words:
                    lengths.append(len(words))
        return sum(lengths) / len(lengths) if lengths else 0.0

    @staticmethod
    def _question_ratio(texts: list[str]) -> float:
        """Fraction of texts that contain a `?`."""
        if not texts:
            return 0.0
        questions = sum(1 for t in texts if "?" in t)
        return questions / len(texts)

    # ── Voice / style aspect ──────────────────────────────────────────────────

    def _voice_style(self) -> dict:
        """§3.1 — observed voice + style metrics from recent outputs."""
        cutoff = time.time() - self._OUTPUT_WINDOW_S

        # Collect outputs: assistant messages
        msg_rows = self._cr.read(
            "SELECT content FROM messages "
            "WHERE role = 'nex' AND timestamp > ?",
            (int(cutoff),),
        )
        # Speech queue (in beliefs.db, queued_at REAL)
        sq_rows = self._br.read(
            "SELECT content FROM speech_queue WHERE queued_at > ?",
            (cutoff,),
        )
        # Self-authored beliefs
        belief_rows = self._br.read(
            f"SELECT content FROM beliefs "
            f"WHERE source IN ({_SELF_AUTHORED_SQL}) AND created_at > ?",
            (int(cutoff),),
        )

        all_texts = [
            r["content"] for r in list(msg_rows) + list(sq_rows) + list(belief_rows)
            if r["content"] and r["content"].strip()
        ]
        total_count = len(all_texts)

        avg_sentence_len = self._avg_sentence_length(all_texts)
        question_ratio = self._question_ratio(all_texts)

        # Vocabulary
        all_tokens: list[str] = []
        for text in all_texts:
            all_tokens.extend(self._tokenize(text))
        recent_token_set = set(all_tokens)
        token_freq = Counter(all_tokens)
        top_words = [
            {"word": word, "count": cnt}
            for word, cnt in token_freq.most_common(self._VOCAB_TOP_N)
        ]
        vocab_distinctiveness = self._compute_vocab_distinctiveness(recent_token_set)

        # avg_arousal: proxy to current affect_state row (single-row replace pattern)
        avg_arousal = 0.0
        try:
            row = self._cr.read_one("SELECT arousal FROM affect_state WHERE id = 1")
            if row and row["arousal"] is not None:
                avg_arousal = float(row["arousal"])
        except Exception:
            pass

        return {
            "total_output_count_5m": total_count,
            "avg_sentence_length_words": avg_sentence_len,
            "question_ratio": question_ratio,
            "vocab_distinctiveness": vocab_distinctiveness,
            "avg_arousal_during_outputs": avg_arousal,
            "vocabulary_top_words": top_words,
        }

    # ── Engagement patterns aspect ────────────────────────────────────────────

    def _engagement(self) -> dict:
        """§3.3 — observed engagement patterns from interaction history."""
        now = time.time()
        cutoff_5m = int(now) - self._OUTPUT_WINDOW_S
        cutoff_latency = int(now) - self._LATENCY_WINDOW_S
        cutoff_session = int(now) - self._ACTIVE_SESSION_WINDOW_S

        # Response count last 5m
        resp_row = self._cr.read_one(
            "SELECT COUNT(*) AS n FROM messages "
            "WHERE role = 'nex' AND timestamp > ?",
            (cutoff_5m,),
        )
        response_count = int(resp_row["n"]) if resp_row else 0

        # Active conversations last hour
        active_row = self._cr.read_one(
            "SELECT COUNT(DISTINCT session_id) AS n FROM messages "
            "WHERE timestamp > ?",
            (cutoff_session,),
        )
        active_count = int(active_row["n"]) if active_row else 0

        active_sess_rows = self._cr.read(
            "SELECT DISTINCT session_id FROM messages WHERE timestamp > ? LIMIT 20",
            (cutoff_session,),
        )
        active_sessions = [r["session_id"] for r in active_sess_rows]

        # Average response latency: pair assistant turns with preceding user turns
        latency_rows = self._cr.read(
            "SELECT session_id, role, timestamp FROM messages "
            "WHERE timestamp > ? ORDER BY session_id, timestamp",
            (cutoff_latency,),
        )
        latencies: list[float] = []
        if latency_rows:
            # Group by session
            sessions: dict[str, list[tuple[str, int]]] = {}
            for r in latency_rows:
                sid = r["session_id"]
                if sid not in sessions:
                    sessions[sid] = []
                sessions[sid].append((r["role"], int(r["timestamp"])))
            for turns in sessions.values():
                last_user_ts: Optional[int] = None
                for role, ts in turns:
                    if role == "user":
                        last_user_ts = ts
                    elif role == "assistant" and last_user_ts is not None:
                        gap = ts - last_user_ts
                        if 0 <= gap < 3600:  # sanity cap at 1h
                            latencies.append(float(gap))
                        last_user_ts = None
        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

        # Topic diversity: distinct tag themes from recent self-authored beliefs
        tag_rows = self._br.read(
            f"SELECT tags FROM beliefs "
            f"WHERE source IN ({_SELF_AUTHORED_SQL}) AND created_at > ? "
            "ORDER BY created_at DESC LIMIT 20",
            (cutoff_5m,),
        )
        theme_freq: dict[str, int] = {}
        for r in tag_rows:
            try:
                for tag in json.loads(r["tags"] or "[]"):
                    theme_freq[tag] = theme_freq.get(tag, 0) + 1
            except Exception:
                continue
        recent_topics = sorted(theme_freq, key=theme_freq.get, reverse=True)[
            : self._TOPIC_TOP_N
        ]
        topic_diversity = len(theme_freq)

        return {
            "response_count_5m": response_count,
            "avg_response_latency_s": avg_latency,
            "active_conversation_count": active_count,
            "topic_diversity": topic_diversity,
            "recent_topics": recent_topics,
            "active_sessions": active_sessions,
        }

    # ── Self-report templates ─────────────────────────────────────────────────

    def _build_voice_self_report(self, voice: dict) -> str:
        if voice["total_output_count_5m"] == 0:
            return "No recent outputs in the last 5 minutes."
        words_str = ", ".join(
            f"'{w['word']}'" for w in voice["vocabulary_top_words"][:5]
        ) if voice["vocabulary_top_words"] else "none"
        return (
            f"Recent voice: tone arousal {voice['avg_arousal_during_outputs']:.2f}, "
            f"sentences averaging {voice['avg_sentence_length_words']:.0f} words, "
            f"questions {voice['question_ratio']:.0%} of recent outputs. "
            f"Dominant words: {words_str}."
        )

    def _build_engagement_self_report(self, engagement: dict) -> str:
        topics_str = ", ".join(engagement["recent_topics"][:3]) or "none"
        return (
            f"Currently engaged in {engagement['active_conversation_count']} "
            f"active conversations. Average response latency "
            f"{engagement['avg_response_latency_s']:.1f} seconds. "
            f"{engagement['response_count_5m']} responses in the last 5 minutes. "
            f"Recent focus: {topics_str}."
        )

    # ── Snapshot ──────────────────────────────────────────────────────────────

    def _snapshot(self) -> int:
        state = self.current_state()
        v = state["voice_style"]
        e = state["engagement"]

        combined = (
            (v["self_report"] or "") + " " +
            (e["self_report"] or "") + " " +
            " ".join(w["word"] for w in v["vocabulary_top_words"][:5])
        )
        tags = json.dumps(_generate_tags(combined.strip()))

        row_id = self._dw.write(
            "INSERT INTO social_presence_snapshots ("
            "taken_at, total_output_count_5m, avg_sentence_length_words, "
            "question_ratio, vocab_distinctiveness, avg_arousal_during_outputs, "
            "vocabulary_top_words_json, voice_self_report, "
            "response_count_5m, avg_response_latency_s, "
            "active_conversation_count, topic_diversity, "
            "recent_topics_json, active_sessions_json, "
            "engagement_self_report, tags"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                state["taken_at"],
                v["total_output_count_5m"],
                v["avg_sentence_length_words"],
                v["question_ratio"],
                v["vocab_distinctiveness"],
                v["avg_arousal_during_outputs"],
                json.dumps(v["vocabulary_top_words"]),
                v["self_report"],
                e["response_count_5m"],
                e["avg_response_latency_s"],
                e["active_conversation_count"],
                e["topic_diversity"],
                json.dumps(e["recent_topics"]),
                json.dumps(e["active_sessions"]),
                e["self_report"],
                tags,
            ),
        )
        return int(row_id) if row_id else 0

    # ── Live read API ─────────────────────────────────────────────────────────

    def current_state(self) -> dict:
        """Full social-presence view, computed live. Never written to disk here."""
        v = self._voice_style()
        e = self._engagement()
        v["self_report"] = self._build_voice_self_report(v)
        e["self_report"] = self._build_engagement_self_report(e)
        return {
            "taken_at": time.time(),
            "voice_style": v,
            "engagement": e,
        }

    def current_summary(self) -> str:
        """Combined self-reports as a single narrative — no LLM per §0."""
        try:
            s = self.current_state()
            v_report = s["voice_style"].get("self_report", "")
            e_report = s["engagement"].get("self_report", "")
            parts = [p for p in (v_report, e_report) if p]
            return " ".join(parts)
        except Exception as exc:
            errors.record(
                f"social_presence current_summary error: {exc}",
                source=_LOG_SOURCE,
            )
            return ""

    # ── Public read helpers ───────────────────────────────────────────────────

    def recent_snapshots(self, limit: int = 20) -> list[dict]:
        rows = self._dr.read(
            "SELECT * FROM social_presence_snapshots "
            "ORDER BY taken_at DESC LIMIT ?",
            (limit,),
        )
        return [dict(r) for r in rows]

    def snapshot_at(self, t: float) -> Optional[dict]:
        rows = self._dr.read(
            "SELECT * FROM social_presence_snapshots "
            "ORDER BY ABS(taken_at - ?) ASC LIMIT 1",
            (t,),
        )
        return dict(rows[0]) if rows else None

    def voice_history(self, window_s: int = 3600) -> list[dict]:
        cutoff = time.time() - window_s
        rows = self._dr.read(
            "SELECT taken_at, total_output_count_5m, avg_sentence_length_words, "
            "question_ratio, vocab_distinctiveness, avg_arousal_during_outputs "
            "FROM social_presence_snapshots WHERE taken_at >= ? "
            "ORDER BY taken_at ASC",
            (cutoff,),
        )
        return [dict(r) for r in rows]

    def engagement_history(self, window_s: int = 3600) -> list[dict]:
        cutoff = time.time() - window_s
        rows = self._dr.read(
            "SELECT taken_at, response_count_5m, avg_response_latency_s, "
            "active_conversation_count, topic_diversity "
            "FROM social_presence_snapshots WHERE taken_at >= ? "
            "ORDER BY taken_at ASC",
            (cutoff,),
        )
        return [dict(r) for r in rows]
