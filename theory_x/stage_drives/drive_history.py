"""DriveHistory — voice-profile analyzer.

Periodic daemon (every hour) reads drive_activations + correlated
fountain_events, finds vocabulary signatures per conflict-pair.

For each conflict pair that has fired N times, computes:
  - frequency: count of occurrences
  - signature_vocabulary: words that appear more often in fountain_events
    when this conflict is active vs when it's not
  - resolution_pattern: short narrative summary (deterministic for now)

Writes to voice_profile table. Idempotent — re-run safely.

Per §0 doctrine: substrate solves; LLM speaks.
Per spec §V drive_history.py: detects emerging 'signature' ways
NEX resolves tension.
"""
from __future__ import annotations

import json
import re
import threading
import time
from collections import Counter
from typing import Any, Optional

import errors
from substrate import Reader, Writer

__all__ = ["DriveHistory"]

THEORY_X_STAGE = "drives"

_LOG_SOURCE = "drive_history"

_TICK_INTERVAL_S = 3600   # 1 hour
_MIN_FREQUENCY  = 5       # min occurrences before a pattern is logged
_VOCAB_TOP_N    = 12      # top distinctive words per pair
_STOPWORDS = frozenset({
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "shall", "can", "not", "this",
    "that", "these", "those", "it", "its", "i", "we", "you", "they",
    "he", "she", "as", "if", "so", "no", "my", "our", "their", "feels",
    "feel", "today", "this", "between", "through",
})


def _tokens(text: str) -> list[str]:
    words = re.sub(r"[^\w\s]", " ", text.lower()).split()
    return [w for w in words if w not in _STOPWORDS and len(w) > 2]


def _pair_key(pair: tuple) -> str:
    """Canonical key for a conflict pair (sorted)."""
    a, b = pair
    return "_vs_".join(sorted([a, b]))


class DriveHistory:
    name: str = "drive_history"

    def __init__(
        self,
        conversations_writer: Writer,
        conversations_reader: Reader,
        dynamic_reader: Reader,
        tick_interval_s: int = _TICK_INTERVAL_S,
    ) -> None:
        self._cw = conversations_writer
        self._cr = conversations_reader
        self._dr = dynamic_reader
        self._interval = tick_interval_s

    def start_loop(self) -> None:
        t = threading.Thread(
            target=self._loop, daemon=True, name="drive_history_tick"
        )
        t.start()

    def _loop(self) -> None:
        while True:
            try:
                self._analyze_once()
            except Exception as exc:
                errors.record(
                    f"drive_history tick error: {exc}",
                    source=_LOG_SOURCE, exc=exc,
                )
            time.sleep(self._interval)

    def _analyze_once(self) -> None:
        """Scan drive_activations, group by conflict-pair, compute vocab signatures."""
        # 1) Pull every drive_activation row with at least one conflict
        rows = self._cr.read(
            "SELECT id, fountain_event_id, timestamp, active_conflicts "
            "FROM drive_activations "
            "WHERE active_conflicts IS NOT NULL "
            "  AND active_conflicts != '[]' "
            "ORDER BY id DESC LIMIT 5000"
        )
        rows = list(rows or [])
        if not rows:
            return

        # 2) Build event_id -> pair_keys map; also gather non-conflict event_ids
        active_event_ids: dict[str, list[int]] = {}
        all_active_eids: set = set()
        for r in rows:
            try:
                conflicts = json.loads(r["active_conflicts"] or "[]")
            except Exception:
                continue
            eid = r["fountain_event_id"]
            if eid is None:
                continue
            for pair in conflicts:
                if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                    continue
                key = _pair_key(tuple(pair))
                active_event_ids.setdefault(key, []).append(int(eid))
                all_active_eids.add(int(eid))

        if not active_event_ids:
            return

        # 3) Pull a baseline of non-conflict fountain events (background corpus)
        try:
            bg_rows = self._dr.read(
                "SELECT id, thought FROM fountain_events "
                "WHERE thought IS NOT NULL AND thought != '' "
                "ORDER BY id DESC LIMIT 500"
            )
            bg_rows = list(bg_rows or [])
        except Exception:
            bg_rows = []

        bg_tokens: Counter = Counter()
        bg_total = 0
        for br in bg_rows:
            if int(br["id"]) in all_active_eids:
                continue
            toks = _tokens(br["thought"] or "")
            bg_tokens.update(toks)
            bg_total += len(toks)

        # 4) For each pair, compute its vocabulary signature
        now = time.time()
        for key, eids in active_event_ids.items():
            freq = len(eids)
            if freq < _MIN_FREQUENCY:
                continue
            # Pull thoughts of those events
            placeholders = ",".join("?" * len(eids))
            try:
                evt_rows = self._dr.read(
                    f"SELECT thought FROM fountain_events "
                    f"WHERE id IN ({placeholders}) "
                    f"  AND thought IS NOT NULL AND thought != ''",
                    tuple(eids),
                )
                evt_rows = list(evt_rows or [])
            except Exception:
                continue

            pair_tokens: Counter = Counter()
            pair_total = 0
            for er in evt_rows:
                toks = _tokens(er["thought"] or "")
                pair_tokens.update(toks)
                pair_total += len(toks)

            if pair_total == 0:
                continue

            # Distinctiveness: log-ratio of pair-freq vs background-freq
            signature = []
            for word, count in pair_tokens.most_common(50):
                if count < 2:
                    continue
                pair_rate = count / pair_total
                bg_rate = (bg_tokens.get(word, 0) / bg_total) if bg_total > 0 else 0
                # Smoothed log-ratio
                ratio = (pair_rate + 1e-6) / (bg_rate + 1e-6)
                signature.append((word, count, round(ratio, 3)))

            # Sort by ratio desc, take top
            signature.sort(key=lambda x: -x[2])
            top = signature[:_VOCAB_TOP_N]

            # Resolution pattern: deterministic narrative summary
            pattern = self._summarize_pattern(key, top, freq)

            # Upsert into voice_profile
            try:
                self._cw.write(
                    "INSERT INTO voice_profile "
                    "(drive_pair, resolution_pattern, frequency, "
                    " signature_vocabulary, updated_at) "
                    "VALUES (?, ?, ?, ?, ?) "
                    "ON CONFLICT(drive_pair) DO UPDATE SET "
                    " resolution_pattern=excluded.resolution_pattern, "
                    " frequency=excluded.frequency, "
                    " signature_vocabulary=excluded.signature_vocabulary, "
                    " updated_at=excluded.updated_at",
                    (key, pattern, freq,
                     json.dumps([{"word": w, "count": c, "ratio": r}
                                 for w, c, r in top]),
                     now),
                )
            except Exception as exc:
                errors.record(f"voice_profile upsert error: {exc}",
                              source=_LOG_SOURCE, exc=exc)

    def _summarize_pattern(self, pair_key: str,
                           top_vocab: list, freq: int) -> str:
        """Deterministic short description of how this pair tends to resolve."""
        if not top_vocab:
            return f"{pair_key}: {freq} occurrences; no distinctive vocabulary yet."
        words = ", ".join(w for w, _, _ in top_vocab[:6])
        return f"{pair_key}: {freq} occurrences; signature words: {words}."

    # ── SentienceNode-ish protocol ────────────────────────────────────────────

    def state(self, now: Optional[float] = None) -> dict:
        try:
            rows = self._cr.read(
                "SELECT drive_pair, frequency FROM voice_profile "
                "ORDER BY frequency DESC LIMIT 5"
            )
            return {
                "name": self.name,
                "top_pairs": [
                    {"pair": r["drive_pair"], "freq": int(r["frequency"])}
                    for r in (rows or [])
                ],
            }
        except Exception:
            return {"name": self.name, "top_pairs": []}
