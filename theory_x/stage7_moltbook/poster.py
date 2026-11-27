"""Poster loop: reads fountain_events, queues, posts to moltbook every 30 min.

Two daemons in one class:
  * enqueue_tick(): copies new fountain rows into moltbook_post_queue (skip stillness)
  * post_tick():    if 30 min since last post, pick best candidate, post it

Both safe to call repeatedly. Idempotent on thought_id.
"""
from __future__ import annotations
import logging
import re
from substrate import Reader, Writer, Row, IntegrityError
import threading
import time
from pathlib import Path
from typing import Any

from theory_x.stage7_moltbook.client import (
    MoltbookClient, ApiError, RateLimited, MoltbookError
)
from theory_x.stage7_moltbook.submolt_picker import (
    pick_submolt, load_available_submolts, FALLBACK
)

log = logging.getLogger("theory_x.stage7_moltbook.poster")

from substrate.paths import DbPath  # resolves NEX5_DATA_DIR at use time (test hygiene)
DYNAMIC_DB = DbPath("dynamic")
BELIEFS_DB = DbPath("beliefs")
TICK_SECONDS = 60                  # how often each loop wakes up
POST_INTERVAL_SECONDS = 30 * 60    # server cap: 1 post / 30 min
QUEUE_WINDOW_SECONDS = 30 * 60     # only consider thoughts queued within last 30 min
TITLE_MAX_CHARS = 200              # moltbook title limit (defensive)
CONTENT_MAX_CHARS = 4000           # post body limit (defensive)

# Quality gate — she posts her OWN thoughts, not feed echoes. Source is her
# crystallized fountain_insight beliefs (already gate-passed); these filters
# strip the feed-derived ones that still carry that source tag.
_HWM_KEY = "moltbook_last_belief_id"     # daemon_kv high-water mark
ENQUEUE_LOOKBACK_SECONDS = 24 * 3600     # never backfill beliefs older than this
LONG_THRESHOLD = 280                     # chars; above this, feed-entity content is dropped
DEDUP_JACCARD = 0.55                     # theme-overlap above this = near-duplicate, skip
DEDUP_RECENT_N = 12                      # compare against this many recent queued/posted

_JSON_PREFIX = ("[", "{", '"')
_FEED_MARKER = re.compile(r"\(per a feed item\)", re.I)
# feed-report openers: "The item ...", "This statement ...", plus
# "The/This <x> ... suggests/discusses/highlights/..."
_FEED_OPENER = re.compile(
    r"^\s*(the|this)\s+(item|announcement|article|report|news|statement|piece|"
    r"study|survey|release|development|post)\b"
    r"|^\s*(the|this)\b[^.]{0,60}\b(suggests|discusses|highlights|describes|"
    r"underscores|points to|mentions|reports|reveals|indicates)\b",
    re.I)
# feed-entity signals used ONLY to drop LONG thoughts (a genuine short thought
# that happens to name a company is fine; a 500-char breach summary is not).
_FEED_ENTITY = re.compile(
    r"\b(attackers?|vulnerabilit\w+|misconfiguration|exploit\w*|breach\w*|"
    r"codebase|repositor\w+|protocol|interest rate|central bank|market\w*|"
    r"blockchain|crypto\w*|treasury|jailbreak\w*)\b|\$\d|\d{3,}",
    re.I)
_WORD_RE = re.compile(r"[a-z0-9]{3,}")
_STOP = frozenset("the and for are was has had not but with into over from this that "
                  "how what who when where which more most just now here there they "
                  "them their his her its our you your".split())


def _content_tokens(text: str) -> set:
    return {t for t in _WORD_RE.findall((text or "").lower()) if t not in _STOP}


def _is_quality(content: str) -> bool:
    """True iff this crystallized belief is her genuine voice, not feed content."""
    if not content or not content.strip():
        return False
    t = content.lstrip()
    if t[:1] in _JSON_PREFIX:            # price / JSON dumps
        return False
    if _FEED_MARKER.search(content):     # "(per a feed item)"
        return False
    if _FEED_OPENER.search(t):           # "The item suggests...", report echoes
        return False
    # Long + feed-entity content = a feed summary with a reflective tail (drop).
    if len(content) > LONG_THRESHOLD and _FEED_ENTITY.search(content):
        return False
    return True


def _derive_title(content: str, maxlen: int = TITLE_MAX_CHARS) -> str:
    """First sentence as the title (== content for a short single-sentence
    thought); word-boundary ellipsis if the first sentence is very long."""
    first = re.split(r"(?<=[.?!])\s+", content.strip(), 1)[0].strip()
    if len(first) <= maxlen:
        return first
    return content[:maxlen].rsplit(" ", 1)[0].rstrip(" ,;:—-") + "…"


def _too_similar(tokens: set, recent_token_sets: list) -> bool:
    """Light theme dedup: Jaccard token overlap vs recent queued/posted."""
    if not tokens:
        return False
    for prev in recent_token_sets:
        if not prev:
            continue
        inter = len(tokens & prev)
        union = len(tokens | prev)
        if union and inter / union >= DEDUP_JACCARD:
            return True
    return False


class PostLoop:
    """Runs two ticks on a single thread. Owns a per-thread sqlite connection."""

    def __init__(
        self,
        client: MoltbookClient,
        db_path: Path | str = DYNAMIC_DB,
        *,
        dynamic_reader: Reader | None = None,
        dynamic_writer: Writer | None = None,
        beliefs_reader: Reader | None = None,
    ):
        self.client = client
        self.db_path = Path(db_path)
        self._dynamic_reader = dynamic_reader or Reader(self.db_path)
        self._dynamic_writer = dynamic_writer
        self._beliefs_reader = beliefs_reader or Reader(BELIEFS_DB)
        self._stop = threading.Event()
        self._available_submolts: set[str] = set()
        self._submolts_loaded_at: float = 0.0

    # -- public --

    def run(self):
        log.info("PostLoop starting (dry_run=%s)", self.client.dry_run)
        self._refresh_submolts(force=True)
        while not self._stop.is_set():
            try:
                self.enqueue_tick()
            except Exception as e:
                log.error("enqueue_tick failed: %s", e)
            try:
                self.post_tick()
            except Exception as e:
                log.error("post_tick failed: %s", e)
            self._stop.wait(TICK_SECONDS)
        log.info("PostLoop stopped")

    def stop(self):
        self._stop.set()

    # -- enqueue --

    def _write_dynamic_batch(self, statements):
        if not statements:
            return
        own_writer = self._dynamic_writer is None
        writer = self._dynamic_writer or Writer(self.db_path, name="moltbook_poster")
        try:
            writer.write_many(statements)
        finally:
            if own_writer:
                writer.close()

    def enqueue_tick(self):
        """Queue ONLY her quality thoughts, preserving the belief-id high-water mark."""
        # high-water mark: init to current-max on first run (post going
        # forward, not replay history), then advance monotonically.
        hw_row = self._dynamic_reader.read_one(
            "SELECT value FROM daemon_kv WHERE key=?", (_HWM_KEY,)
        )
        if hw_row is None:
            max_row = self._beliefs_reader.read_one(
                "SELECT COALESCE(MAX(id),0) FROM beliefs WHERE source='fountain_insight'"
            )
            hw = int(max_row[0]) if max_row else 0
            self._write_dynamic_batch([(
                "INSERT OR REPLACE INTO daemon_kv (key,value,updated_at) VALUES (?,?,?)",
                (_HWM_KEY, str(hw), time.time()),
            )])
            log.info("enqueue_tick: initialised belief high-water=%d "
                     "(posts new thoughts from here on)", hw)
            return   # nothing to backfill on first run

        hw = int(hw_row["value"])
        cutoff = time.time() - ENQUEUE_LOOKBACK_SECONDS
        cands = self._beliefs_reader.read(
            "SELECT id, content, created_at FROM beliefs "
            "WHERE source='fountain_insight' AND id > ? AND created_at > ? "
            "ORDER BY id ASC",
            (hw, cutoff),
        )
        if not cands:
            return
        # recent theme fingerprints for dedup (queued or posted lately)
        recent = self._dynamic_reader.read(
            "SELECT content FROM moltbook_post_queue "
            "WHERE status IN ('pending','posted') "
            "ORDER BY queued_at DESC LIMIT ?", (DEDUP_RECENT_N,)
        )
        recent_sets = [_content_tokens(r["content"]) for r in recent]

        inserted = 0
        max_id = hw
        statements = []
        for row in cands:
            max_id = max(max_id, int(row["id"]))
            content = row["content"]
            if not _is_quality(content):
                continue
            toks = _content_tokens(content)
            if _too_similar(toks, recent_sets):
                log.debug("skip near-duplicate belief=%s", row["id"])
                continue
            wc = len(content.split())
            statements.append((
                "INSERT OR IGNORE INTO moltbook_post_queue "
                "(thought_id, content, queued_at, status, word_count, droplet) "
                "VALUES (?, ?, ?, 'pending', ?, NULL)",
                (int(row["id"]), content, time.time(), wc),
            ))
            inserted += 1
            recent_sets.append(toks)   # dedup within this batch too
        # advance the high-water mark past everything we examined
        statements.append((
            "INSERT OR REPLACE INTO daemon_kv (key,value,updated_at) VALUES (?,?,?)",
            (_HWM_KEY, str(max_id), time.time()),
        ))
        self._write_dynamic_batch(statements)
        if inserted:
            log.info("enqueue_tick: queued %d quality thoughts (hw->%d)",
                     inserted, max_id)

    def post_tick(self):
        """If 30 min since last successful post, pick best & post."""
        row = self._dynamic_reader.read_one(
            "SELECT COALESCE(MAX(ts), 0) FROM moltbook_posts WHERE status='posted'"
        )
        last_post_ts = (row[0] if row else 0.0) or 0.0
        now = time.time()
        since = now - last_post_ts
        if since < POST_INTERVAL_SECONDS:
            log.debug("post_tick: %.0fs since last post, waiting %ds",
                      since, POST_INTERVAL_SECONDS - since)
            return

        window_start = now - QUEUE_WINDOW_SECONDS
        candidates = self._dynamic_reader.read(
            "SELECT id, thought_id, content, queued_at, word_count, droplet "
            "FROM moltbook_post_queue "
            "WHERE status='pending' AND queued_at >= ? "
            "ORDER BY queued_at DESC",
            (window_start,),
        )
        if not candidates:
            # Expire any old pending rows outside window
            self._write_dynamic_batch([(
                "UPDATE moltbook_post_queue SET status='expired' "
                "WHERE status='pending' AND queued_at < ?",
                (window_start,),
            )])
            log.debug("post_tick: nothing in window")
            return

        best = self._pick_best(candidates)
        self._refresh_submolts(force=False)
        submolt = pick_submolt(best["content"], self._available_submolts) or FALLBACK

        title = _derive_title(best["content"])
        content = best["content"][:CONTENT_MAX_CHARS]

        log.info("posting fid=%s submolt=%s title=%r",
                 best["thought_id"], submolt, title[:60])
        try:
            result = self.client.create_post(submolt, title, content)
            post_id = (
                (result or {}).get("post", {}).get("id")
                or (result or {}).get("id")
                or ""
            )
            self._write_dynamic_batch([
                (
                    "INSERT INTO moltbook_posts "
                    "(post_id, thought_id, ts, submolt, status, error) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (str(post_id), best["thought_id"], now, submolt, "posted", None),
                ),
                (
                    "UPDATE moltbook_post_queue SET status='posted' WHERE id=?",
                    (best["id"],),
                ),
                (
                    "UPDATE moltbook_post_queue SET status='skipped' "
                    "WHERE status='pending' AND queued_at >= ? AND id != ?",
                    (window_start, best["id"]),
                ),
            ])
            log.info("posted ok: post_id=%s submolt=%s", post_id, submolt)
        except RateLimited as e:
            log.warning("rate limited, will retry: retry_after=%s", e.retry_after)
            # leave candidate as pending; will try again next tick
        except ApiError as e:
            self._write_dynamic_batch([
                (
                    "INSERT INTO moltbook_posts "
                    "(post_id, thought_id, ts, submolt, status, error) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (None, best["thought_id"], now, submolt, "failed",
                     f"http {e.status}: {e.body[:300]}"),
                ),
                (
                    "UPDATE moltbook_post_queue SET status='failed' WHERE id=?",
                    (best["id"],),
                ),
            ])
            log.error("post failed: http %d body=%r", e.status, e.body[:200])
        except MoltbookError as e:
            log.error("post network/client error: %s", e)
            # leave pending — try next tick

    # -- helpers --

    def _pick_best(self, candidates: list[Row]) -> Row:
        """Among pending in-window, pick the best.

        Heuristic order:
          1. Highest word_count (more substance)
          2. Among ties, newest queued_at
        """
        ranked = sorted(
            candidates,
            key=lambda r: (r["queued_at"], (r["word_count"] or 0)),
            reverse=True
        )
        return ranked[0]

    def _refresh_submolts(self, force: bool):
        """Reload submolt list every ~30 min, or on force."""
        if not force and (time.time() - self._submolts_loaded_at) < 1800:
            return
        try:
            self._available_submolts = load_available_submolts(self.client)
            self._submolts_loaded_at = time.time()
            log.debug("submolts loaded: %d", len(self._available_submolts))
        except Exception as e:
            log.warning("submolts refresh failed: %s", e)
