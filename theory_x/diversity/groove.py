"""Groove Spotter — detects rut formation via n-gram repetition and centroid tightening."""
from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from collections import Counter
from typing import Optional

import numpy as np

from theory_x.diversity.embeddings import embed

log = logging.getLogger("theory_x.diversity.groove")

WINDOW_SIZE = 20
NGRAM_REPEAT_THRESHOLD = 3
CENTROID_TIGHTEN_THRESHOLD = 0.40
EXACT_REPEAT_MIN = 2
COOLDOWN_HOURS = 2

_STOPWORDS = frozenset({
    "the", "a", "an", "of", "to", "in", "on", "at", "for",
    "and", "or", "but", "is", "are", "was", "were", "be",
    "me", "my", "i", "it", "its", "this", "that", "with",
    "by", "as", "from",
})


def _is_stopword_bigram(bigram: str) -> bool:
    words = bigram.split()
    return all(w in _STOPWORDS for w in words)


def _trigrams(text: str) -> list[str]:
    words = re.findall(r"[a-z']+", text.lower())
    return [" ".join(words[i:i+3]) for i in range(len(words) - 2)]


class GrooveSpotter:
    def __init__(self, beliefs_writer, beliefs_reader):
        self._writer = beliefs_writer
        self._reader = beliefs_reader

    def detect_all(self) -> list[dict]:
        rows = self._reader.read(
            "SELECT id, content FROM beliefs "
            "WHERE source IN ('fountain_insight', 'synergized') "
            "ORDER BY created_at DESC LIMIT ?",
            (WINDOW_SIZE * 2,),
        )
        if len(rows) < 5:
            return []

        window = list(rows[:WINDOW_SIZE])
        alerts = []

        exact_alert = self._detect_exact_repetition(window)
        if exact_alert:
            alerts.append(exact_alert)
            self._push_cooldown(exact_alert)

        ngram_alert = self._check_ngrams(window)
        if ngram_alert:
            alerts.append(ngram_alert)
            if ngram_alert["severity"] >= 0.5:
                self._push_cooldown(ngram_alert)

        template_alert = self._detect_template_repetition(window)
        if template_alert:
            alerts.append(template_alert)
            if template_alert["severity"] >= 0.5:
                self._push_cooldown(template_alert)

        centroid_alert = self._check_centroid_tightening(window, list(rows[WINDOW_SIZE:]))
        if centroid_alert:
            alerts.append(centroid_alert)

        return alerts

    def _check_ngrams(self, window: list) -> Optional[dict]:
        from collections import Counter
        all_ngrams: list[str] = []
        for row in window:
            all_ngrams.extend(_trigrams(row["content"]))
        if not all_ngrams:
            return None
        counts = Counter(all_ngrams)
        top_pattern, top_count = counts.most_common(1)[0]
        if top_count < NGRAM_REPEAT_THRESHOLD:
            return None
        excess = max(0, top_count - NGRAM_REPEAT_THRESHOLD + 1)
        severity = min(1.0, 0.5 + excess * 0.1)
        ids = json.dumps([r["id"] for r in window[:5]])
        self._writer.write(
            "INSERT INTO groove_alerts "
            "(detected_at, alert_type, severity, pattern, sample_belief_ids, window_size) "
            "VALUES (?, 'ngram_repetition', ?, ?, ?, ?)",
            (time.time(), severity, top_pattern, ids, WINDOW_SIZE),
        )
        log.info("Groove alert: ngram_repetition pattern=%r severity=%.2f", top_pattern, severity)
        return {"alert_type": "ngram_repetition", "pattern": top_pattern, "severity": severity}

    def _detect_exact_repetition(self, window: list) -> Optional[dict]:
        """Alert when the same exact sentence appears ≥3 times in the window."""
        contents = [r["content"] for r in window]
        counts = Counter(contents)
        for content, n in counts.most_common(1):
            if n >= EXACT_REPEAT_MIN:
                severity = min(1.0, 0.5 + (n - 2) * 0.2)
                ids = json.dumps([r["id"] for r in window if r["content"] == content])
                self._writer.write(
                    "INSERT INTO groove_alerts "
                    "(detected_at, alert_type, severity, pattern, sample_belief_ids, window_size) "
                    "VALUES (?, 'exact_repetition', ?, ?, ?, ?)",
                    (time.time(), severity, content[:100], ids, len(window)),
                )
                log.info(
                    "Groove alert: exact_repetition n=%d severity=%.2f content=%r",
                    n, severity, content[:60],
                )
                return {
                    "alert_type": "exact_repetition",
                    "severity": severity,
                    "pattern": content,
                    "n": n,
                }
        return None

    def _detect_template_repetition(self, window: list) -> Optional[dict]:
        """Detect when 3+ fires share 3+ content bigrams (template-style repetition)."""
        bigram_fires: dict[str, set] = {}
        for row in window:
            tokens = re.findall(r"[a-z']+", (row.get("content") or "").lower())
            bigrams = {f"{tokens[i]} {tokens[i+1]}" for i in range(len(tokens) - 1)}
            for bg in bigrams:
                bigram_fires.setdefault(bg, set()).add(row["id"])

        shared = {
            bg: fires for bg, fires in bigram_fires.items()
            if len(fires) >= 2 and not _is_stopword_bigram(bg)
        }
        if not shared:
            return None

        fire_pairs: Counter = Counter()
        shared_bigrams_for_pair: dict = {}
        fires_list = list(window)
        for i, f1 in enumerate(fires_list):
            for f2 in fires_list[i + 1:]:
                common = [
                    bg for bg, fires in shared.items()
                    if f1["id"] in fires and f2["id"] in fires
                ]
                if len(common) >= 3:
                    key = frozenset([f1["id"], f2["id"]])
                    fire_pairs[key] += 1
                    shared_bigrams_for_pair[key] = common

        if not fire_pairs:
            return None

        templated_ids: set = set()
        sample_bigrams: list = []
        for pair in fire_pairs.most_common():
            k = pair[0]
            templated_ids.update(k)
            if not sample_bigrams:
                sample_bigrams = shared_bigrams_for_pair[k][:3]

        if len(templated_ids) < 3:
            return None

        severity = min(1.0, 0.5 + (len(templated_ids) - 3) * 0.1)
        pattern = " / ".join(sample_bigrams)
        ids = json.dumps(list(templated_ids))
        self._writer.write(
            "INSERT INTO groove_alerts "
            "(detected_at, alert_type, severity, pattern, sample_belief_ids, window_size) "
            "VALUES (?, 'template_repetition', ?, ?, ?, ?)",
            (time.time(), severity, pattern[:100], ids, len(window)),
        )
        log.info(
            "Groove alert: template_repetition n_fires=%d severity=%.2f pattern=%r",
            len(templated_ids), severity, pattern,
        )
        return {
            "alert_type": "template_repetition",
            "severity": severity,
            "pattern": pattern,
            "sample_belief_ids": ids,
            "window_size": len(window),
        }

    def _push_cooldown(self, alert: dict) -> None:
        """Write a cooldown entry so the crystallizer blocks this content."""
        if alert.get("severity", 0) < 0.5:
            return
        pattern = alert.get("pattern", "")
        if not pattern:
            return
        content_hash = hashlib.sha256(pattern.encode()).hexdigest()
        cooldown_until = time.time() + COOLDOWN_HOURS * 3600
        try:
            self._writer.write(
                "INSERT INTO signal_cooldown "
                "(content_hash, content, cooldown_until, reason, created_at) "
                "VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(content_hash) DO UPDATE SET "
                "cooldown_until=excluded.cooldown_until, reason=excluded.reason",
                (content_hash, pattern[:500], cooldown_until,
                 alert["alert_type"], time.time()),
            )
            log.info(
                "Cooldown written: type=%s severity=%.2f until=+%dh",
                alert["alert_type"], alert["severity"], COOLDOWN_HOURS,
            )
        except Exception as exc:
            log.warning("Failed to write cooldown: %s", exc)

    def _check_centroid_tightening(self, current_window: list, prev_window: list) -> Optional[dict]:
        if len(prev_window) < 5:
            return None
        try:
            cur_vecs = np.stack([embed(r["content"]) for r in current_window])
            prev_vecs = np.stack([embed(r["content"]) for r in prev_window])
        except Exception:
            return None

        cur_centroid = cur_vecs.mean(axis=0)
        prev_centroid = prev_vecs.mean(axis=0)

        cur_spread = float(np.mean(np.linalg.norm(cur_vecs - cur_centroid, axis=1)))
        prev_spread = float(np.mean(np.linalg.norm(prev_vecs - prev_centroid, axis=1)))

        if prev_spread == 0:
            return None
        tightening = (prev_spread - cur_spread) / prev_spread
        if tightening < CENTROID_TIGHTEN_THRESHOLD:
            return None

        severity = min(1.0, tightening)
        ids = json.dumps([r["id"] for r in current_window[:5]])
        self._writer.write(
            "INSERT INTO groove_alerts "
            "(detected_at, alert_type, severity, pattern, sample_belief_ids, window_size) "
            "VALUES (?, 'centroid_tightening', ?, ?, ?, ?)",
            (time.time(), severity,
             f"spread {prev_spread:.3f}→{cur_spread:.3f}", ids, WINDOW_SIZE),
        )
        log.info("Groove alert: centroid_tightening severity=%.2f", severity)
        return {"alert_type": "centroid_tightening", "severity": severity}
