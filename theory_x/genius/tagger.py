"""Genius Tagger — deploys the calibrated v2 score as a continuous
substrate signal.

GENIUS_SCORE_v2.md §7. The score in theory_x.genius.score_v2 was fit
against Jon's 103 hand-flagged training examples (Mode A striking vs
Mode B/C ordinary, per the three-mode framing in JOURNAL_2026-05-27).
Weights live in genius_score_weights.json. This daemon applies them
to every fountain_event and writes the result to genius_tags.

Phase 1 — LOG-ONLY. No behavioral effect on any other node. Future
consumers (retrieval bias, fountain prompt context, theory's organ
outputs) read genius_tags as substrate; they do not exist yet.

Boot behavior:
  - First run: backfill recent fountain_events (last 14d by default)
    that have no row in genius_tags for the current weights_version.
  - Continuous: every interval (60s default), score and write any
    new fountain_events in the past 180s with no row.

Re-fit handling:
  - Weights file is reloaded each tick (cheap mtime check). When Jon
    re-fits and writes new weights with a bumped version string, the
    next tick picks them up and starts emitting rows under the new
    version; old rows are preserved (UNIQUE(fountain_event_id,
    weights_version) allows both).

Integration pattern matches SubstrateHarmonic / HoldingZoneResolver:
  - Daemon thread spawned via start_loop(interval=60)
  - tick() callable directly for testing
  - SentienceNode protocol: name, tick, decay, state
  - Errors recorded via central errors channel, never propagated
"""
from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Optional

import errors

from theory_x.genius import score_v2

THEORY_X_STAGE = "genius"

_LOG_SOURCE = "genius.tagger"
_DEFAULT_INTERVAL = 60.0
_DEFAULT_BACKFILL_HOURS = 14 * 24   # last 14 days
_CONTINUOUS_LOOKBACK_SECONDS = 180  # query window during steady-state ticks
_BATCH_LOG_EVERY = 200              # log progress during backfill every N fires
_PRIOR_FIRES_WINDOW = 50            # F2 (anti_template) compares against last 50

_WEIGHTS_PATH = score_v2.WEIGHTS_PATH


class GeniusTagger:
    """SentienceNode that scores fountain fires with the v2 score.

    Reads fountain_events (dynamic.db) + T6 beliefs (beliefs.db).
    Writes one row per (fountain_event_id, weights_version) to
    conversations.db.genius_tags. Log-only phase 1 — no behavioural
    effect on other nodes.
    """

    name: str = "genius_tagger"

    def __init__(
        self,
        conversations_writer,
        conversations_reader,
        dynamic_reader,
        beliefs_reader,
        weights_path: Optional[Path] = None,
        backfill_hours: int = _DEFAULT_BACKFILL_HOURS,
    ) -> None:
        self._writer = conversations_writer
        self._conv_reader = conversations_reader
        self._dyn_reader = dynamic_reader
        self._bel_reader = beliefs_reader
        self._weights_path = Path(weights_path) if weights_path else _WEIGHTS_PATH
        self._backfill_hours = backfill_hours

        self._stop: Optional[threading.Event] = None
        self._thread: Optional[threading.Thread] = None

        # Cached weights (reloaded on mtime change)
        self._weights: Optional[dict[str, Any]] = None
        self._weights_mtime: float = 0.0

        # Cached T6 beliefs window (refreshed periodically; F3 input)
        self._t6_cache: list[dict[str, Any]] = []
        self._t6_cache_at: float = 0.0
        self._t6_cache_ttl = 600.0  # refresh every 10 min

        # Stats
        self._tick_count: int = 0
        self._tagged_total: int = 0
        self._tagged_striking: int = 0
        self._backfill_done: bool = False
        self._last_score: Optional[float] = None
        self._last_class: Optional[str] = None

    # ── SentienceNode protocol ────────────────────────────────────────────────

    def tick(self, context: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """Score new fountain fires and write rows. Never raises."""
        self._tick_count += 1
        ts_now = time.time()
        weights = self._load_weights()
        if weights is None:
            return self._stats()

        try:
            if not self._backfill_done:
                self._backfill(weights, ts_now)
                self._backfill_done = True
            else:
                self._tag_window(weights, ts_now, _CONTINUOUS_LOOKBACK_SECONDS)
        except Exception as exc:
            errors.record(
                f"genius_tagger tick failed: {exc}",
                source=_LOG_SOURCE, level="WARNING", exc=exc,
            )
        return self._stats()

    def decay(self) -> None:
        """SentienceNode protocol stub — no decay state to maintain."""
        return None

    @property
    def state(self) -> dict[str, Any]:
        return self._stats()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start_loop(self, interval_seconds: float = _DEFAULT_INTERVAL) -> None:
        """Spawn daemon thread that calls tick() every interval."""
        self._stop = threading.Event()

        def _run() -> None:
            # First tick fires immediately so backfill begins at boot
            try:
                self.tick()
            except Exception as exc:
                errors.record(
                    f"genius_tagger initial tick failed: {exc}",
                    source=_LOG_SOURCE, level="WARNING", exc=exc,
                )
            while not self._stop.is_set():
                self._stop.wait(interval_seconds)
                if not self._stop.is_set():
                    self.tick()

        self._thread = threading.Thread(
            target=_run, name="genius_tagger", daemon=True,
        )
        self._thread.start()
        errors.record(
            f"Genius tagger loop started (interval={int(interval_seconds)}s)",
            source=_LOG_SOURCE, level="INFO",
        )

    def stop_loop(self) -> None:
        if self._stop is not None:
            self._stop.set()

    # ── Weights loading ───────────────────────────────────────────────────────

    def _load_weights(self) -> Optional[dict[str, Any]]:
        """Load + cache weights. Reload on mtime change (no restart needed)."""
        try:
            mtime = os.path.getmtime(self._weights_path)
        except OSError:
            if self._weights is None:
                errors.record(
                    f"genius_tagger: weights file not found at {self._weights_path}; "
                    "run `.venv/bin/python3 -m theory_x.genius.score_v2` first",
                    source=_LOG_SOURCE, level="WARNING",
                )
            return self._weights  # may be None on first failed load

        if self._weights is not None and mtime <= self._weights_mtime:
            return self._weights

        try:
            with open(self._weights_path) as f:
                data = json.load(f)
            # Sanity check expected fields
            for key in ("version", "weights", "bias", "threshold"):
                if key not in data:
                    raise ValueError(f"weights file missing key: {key}")
            if len(data["weights"]) != 5:
                raise ValueError(
                    f"expected 5 weights, got {len(data['weights'])}"
                )
            self._weights = data
            self._weights_mtime = mtime
            errors.record(
                f"genius_tagger: loaded weights version='{data['version']}' "
                f"threshold={data['threshold']:.2f} "
                f"(training_acc={data.get('training_accuracy', 0):.1%})",
                source=_LOG_SOURCE, level="INFO",
            )
            return self._weights
        except Exception as exc:
            errors.record(
                f"genius_tagger: failed to load weights: {exc}",
                source=_LOG_SOURCE, level="WARNING", exc=exc,
            )
            return self._weights  # fall back to last good

    # ── T6 belief cache (F3 input) ────────────────────────────────────────────

    def _get_t6_beliefs(self, ts_now: float) -> list[dict[str, Any]]:
        if (ts_now - self._t6_cache_at) < self._t6_cache_ttl and self._t6_cache:
            return self._t6_cache
        cutoff = ts_now - 14 * 86400
        try:
            rows = self._bel_reader.read(
                "SELECT id, content, tier, created_at FROM beliefs "
                "WHERE tier = 6 AND created_at > ?",
                (cutoff,),
            )
            self._t6_cache = [dict(r) for r in (rows or [])]
            self._t6_cache_at = ts_now
        except Exception as exc:
            errors.record(
                f"genius_tagger: T6 cache refresh failed: {exc}",
                source=_LOG_SOURCE, level="WARNING", exc=exc,
            )
            # keep last good cache
        return self._t6_cache

    # ── Tagging ───────────────────────────────────────────────────────────────

    def _existing_tag_ids(self, version: str, since_ts: Optional[float]) -> set[int]:
        """Return set of fountain_event_ids already tagged under this version."""
        try:
            if since_ts is None:
                rows = self._conv_reader.read(
                    "SELECT fountain_event_id FROM genius_tags "
                    "WHERE weights_version = ?",
                    (version,),
                )
            else:
                rows = self._conv_reader.read(
                    "SELECT fountain_event_id FROM genius_tags "
                    "WHERE weights_version = ? AND tagged_at > ?",
                    (version, since_ts),
                )
            return {int(r["fountain_event_id"]) for r in (rows or [])}
        except Exception as exc:
            errors.record(
                f"genius_tagger: existing-tag query failed: {exc}",
                source=_LOG_SOURCE, level="WARNING", exc=exc,
            )
            return set()

    def _load_fires_window(self, since_ts: float) -> list[dict[str, Any]]:
        try:
            rows = self._dyn_reader.read(
                "SELECT id, ts, thought, hot_branch "
                "FROM fountain_events WHERE ts > ? ORDER BY ts ASC",
                (since_ts,),
            )
            return [dict(r) for r in (rows or [])]
        except Exception as exc:
            errors.record(
                f"genius_tagger: fountain_events read failed: {exc}",
                source=_LOG_SOURCE, level="WARNING", exc=exc,
            )
            return []

    def _score_fire(
        self,
        fire: dict[str, Any],
        prior_thoughts: list[str],
        t6_beliefs: list[dict[str, Any]],
        weights: dict[str, Any],
    ) -> tuple[float, str]:
        """Compute features, apply weights, return (score, class)."""
        feats = score_v2.compute_features(fire, prior_thoughts, t6_beliefs)
        w = weights["weights"]
        b = weights["bias"]
        z = sum(w[j] * feats[j] for j in range(len(w))) + b
        score = score_v2.sigmoid(z)
        cls = "STRIKING" if score >= weights["threshold"] else "ordinary"
        return score, cls

    def _write_tag(
        self,
        fire_id: int,
        score: float,
        cls: str,
        version: str,
        ts_now: float,
    ) -> None:
        try:
            self._writer.write(
                "INSERT OR IGNORE INTO genius_tags "
                "(fountain_event_id, score, class, weights_version, tagged_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (fire_id, float(score), cls, version, ts_now),
            )
            self._tagged_total += 1
            if cls == "STRIKING":
                self._tagged_striking += 1
            self._last_score = score
            self._last_class = cls
        except Exception as exc:
            errors.record(
                f"genius_tagger: write_tag failed for fire {fire_id}: {exc}",
                source=_LOG_SOURCE, level="WARNING", exc=exc,
            )

    def _backfill(self, weights: dict[str, Any], ts_now: float) -> None:
        """First-run backfill: tag every fire in the backfill window that
        is not already tagged for this weights_version."""
        version = str(weights["version"])
        since_ts = ts_now - self._backfill_hours * 3600
        fires = self._load_fires_window(since_ts)
        if not fires:
            errors.record(
                f"genius_tagger: backfill found no fountain_events in "
                f"last {self._backfill_hours}h",
                source=_LOG_SOURCE, level="INFO",
            )
            return
        already = self._existing_tag_ids(version, since_ts=None)
        t6 = self._get_t6_beliefs(ts_now)

        to_tag = [f for f in fires if int(f["id"]) not in already]
        if not to_tag:
            errors.record(
                f"genius_tagger: backfill — all {len(fires)} fires in window "
                f"already tagged under version '{version}'",
                source=_LOG_SOURCE, level="INFO",
            )
            return

        errors.record(
            f"genius_tagger: backfill starting — {len(to_tag)} fires to tag "
            f"({len(fires)} in window, {len(already)} already tagged) "
            f"under version '{version}'",
            source=_LOG_SOURCE, level="INFO",
        )

        # Walk fires in ts order; prior_thoughts is the last N before each
        thoughts_in_order = [f["thought"] for f in fires]
        ids_in_order = [int(f["id"]) for f in fires]
        to_tag_set = {int(f["id"]) for f in to_tag}
        processed = 0
        striking = 0
        for i, fire in enumerate(fires):
            fid = int(fire["id"])
            if fid not in to_tag_set:
                continue
            prior = thoughts_in_order[max(0, i - _PRIOR_FIRES_WINDOW):i]
            score, cls = self._score_fire(fire, prior, t6, weights)
            self._write_tag(fid, score, cls, version, ts_now)
            processed += 1
            if cls == "STRIKING":
                striking += 1
            if processed % _BATCH_LOG_EVERY == 0:
                errors.record(
                    f"genius_tagger: backfill progress {processed}/{len(to_tag)} "
                    f"({striking} striking so far)",
                    source=_LOG_SOURCE, level="INFO",
                )

        errors.record(
            f"genius_tagger: backfill complete — {processed} tagged, "
            f"{striking} striking ({striking/max(1,processed):.1%})",
            source=_LOG_SOURCE, level="INFO",
        )

    def _tag_window(
        self,
        weights: dict[str, Any],
        ts_now: float,
        lookback_seconds: float,
    ) -> None:
        """Continuous mode: tag any new fires in the lookback window."""
        version = str(weights["version"])
        since_ts = ts_now - lookback_seconds
        # Pull a bit more context for prior_thoughts (last 50 fires before window)
        context_since = ts_now - 6 * 3600  # 6h is enough for 50-fire prior context
        fires = self._load_fires_window(context_since)
        if not fires:
            return
        already = self._existing_tag_ids(version, since_ts=context_since - 1)
        t6 = self._get_t6_beliefs(ts_now)
        thoughts_in_order = [f["thought"] for f in fires]

        new_count = 0
        for i, fire in enumerate(fires):
            fid = int(fire["id"])
            if fid in already:
                continue
            if float(fire["ts"]) < since_ts:
                # Older than lookback window — must have been tagged already
                # under a different version; skip (don't re-tag old fires
                # during continuous mode — backfill handles that)
                continue
            prior = thoughts_in_order[max(0, i - _PRIOR_FIRES_WINDOW):i]
            score, cls = self._score_fire(fire, prior, t6, weights)
            self._write_tag(fid, score, cls, version, ts_now)
            new_count += 1
        if new_count:
            errors.record(
                f"genius_tagger: tagged {new_count} new fires "
                f"(version={version})",
                source=_LOG_SOURCE, level="DEBUG",
            )

    # ── Status ────────────────────────────────────────────────────────────────

    def _stats(self) -> dict[str, Any]:
        return {
            "tick_count": self._tick_count,
            "tagged_total": self._tagged_total,
            "tagged_striking": self._tagged_striking,
            "backfill_done": self._backfill_done,
            "weights_version": (
                self._weights.get("version") if self._weights else None
            ),
            "threshold": (
                self._weights.get("threshold") if self._weights else None
            ),
            "last_score": self._last_score,
            "last_class": self._last_class,
        }
