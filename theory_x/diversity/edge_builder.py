"""Edge builder daemon — grows the associative graph automatically.

Finds beliefs with fewer than N outgoing edges, computes embedding
similarity against a pool of recent beliefs, writes top-K matches as
'cross_domain' edges. Substrate intelligence amplifier: lets retrieval
walk associations instead of just sorting by recency.

Idempotent via UNIQUE(source_id, target_id, edge_type) in belief_edges.
"""
from __future__ import annotations
import logging
import re
import sqlite3
import threading
import time
from pathlib import Path

from theory_x.diversity.embeddings import embed_belief, cosine

log = logging.getLogger("theory_x.diversity.edge_builder")

BELIEFS_DB = Path("/home/rr/Desktop/Desktop/nex5/data/beliefs.db")

TICK_SECONDS    = 60     # wake up every minute
MIN_EDGES_PER_BELIEF = 3 # consider a belief "associated" when it has this many
BELIEFS_PER_TICK     = 30  # cap processing per tick (cost control)
POOL_SIZE            = 800 # how many recent beliefs to compare against
TOP_K_PER_BELIEF     = 3  # edges to write per under-edged belief
SIM_THRESHOLD        = 0.75  # cosine (rescaled 0-1); real topical similarity
MIN_CONTENT_LEN      = 20  # skip junk-short beliefs

# Don't try to embed obvious non-prose
_NON_PROSE_RE = re.compile(r'^\s*[\[\{"]')


def _should_skip(content: str | None) -> bool:
    if not content:
        return True
    if len(content.strip()) < MIN_CONTENT_LEN:
        return True
    if _NON_PROSE_RE.match(content):
        return True
    return False


def edge_builder_tick(db_path: Path = BELIEFS_DB) -> dict:
    """One pass. Returns stats dict for logging."""
    cx = sqlite3.connect(db_path, timeout=15)
    cx.row_factory = sqlite3.Row
    try:
        # Find beliefs with fewer than MIN_EDGES_PER_BELIEF outgoing edges.
        # Prefer newer beliefs (created_at DESC).
        candidates = cx.execute("""
            SELECT b.id, b.content
            FROM beliefs b
            LEFT JOIN (
                SELECT source_id, COUNT(*) AS n
                FROM belief_edges
                GROUP BY source_id
            ) e ON e.source_id = b.id
            WHERE COALESCE(e.n, 0) < ?
              AND b.paused = 0
              AND b.locked = 0
              AND length(b.content) >= ?
            ORDER BY b.created_at DESC
            LIMIT ?
        """, (MIN_EDGES_PER_BELIEF, MIN_CONTENT_LEN, BELIEFS_PER_TICK)).fetchall()

        if not candidates:
            return {"considered": 0, "wrote": 0, "skipped": 0}

        # Build the comparison pool — recent beliefs above a content threshold.
        pool = cx.execute("""
            SELECT id, content
            FROM beliefs
            WHERE length(content) >= ?
              AND paused = 0
            ORDER BY created_at DESC
            LIMIT ?
        """, (MIN_CONTENT_LEN, POOL_SIZE)).fetchall()
        pool = [(r["id"], r["content"]) for r in pool if not _should_skip(r["content"])]
        if not pool:
            return {"considered": len(candidates), "wrote": 0, "skipped": len(candidates)}

        wrote = 0
        skipped = 0
        for c in candidates:
            if _should_skip(c["content"]):
                skipped += 1
                continue

            try:
                src_vec = embed_belief(c["id"], c["content"])
            except Exception as e:
                log.warning("embed failed for belief %s: %s", c["id"], e)
                skipped += 1
                continue

            # Score every pool member; collect (target_id, sim) above threshold
            scores: list[tuple[int, float]] = []
            for pid, pcontent in pool:
                if pid == c["id"]:
                    continue
                try:
                    pvec = embed_belief(pid, pcontent)
                    sim = cosine(src_vec, pvec)
                except Exception:
                    continue
                if sim >= SIM_THRESHOLD:
                    scores.append((pid, sim))

            scores.sort(key=lambda x: x[1], reverse=True)
            top = scores[:TOP_K_PER_BELIEF]
            if not top:
                continue

            now = time.time()
            for target_id, sim in top:
                try:
                    cx.execute(
                        "INSERT OR IGNORE INTO belief_edges "
                        "(source_id, target_id, edge_type, weight, created_at) "
                        "VALUES (?, ?, 'cross_domain', ?, ?)",
                        (c["id"], target_id, float(sim), now)
                    )
                    if cx.total_changes > 0:
                        wrote += 1
                except sqlite3.IntegrityError:
                    pass

        cx.commit()
        return {"considered": len(candidates), "wrote": wrote, "skipped": skipped}
    finally:
        cx.close()


def edge_builder_loop(state, stop: threading.Event) -> None:
    """Daemon entrypoint matching stage2_dynamic's (state, stop) contract."""
    log.info("edge_builder loop started (tick=%ds, sim>=%.2f, top=%d)",
             TICK_SECONDS, SIM_THRESHOLD, TOP_K_PER_BELIEF)
    while not stop.is_set():
        try:
            stats = edge_builder_tick()
            if stats["wrote"] > 0:
                log.info(
                    "edge_builder: considered=%d wrote=%d skipped=%d",
                    stats["considered"], stats["wrote"], stats["skipped"]
                )
            else:
                log.debug("edge_builder: %s", stats)
        except Exception as e:
            log.error("edge_builder tick failed: %s: %s",
                      type(e).__name__, str(e)[:200])
        stop.wait(TICK_SECONDS)
    log.info("edge_builder loop stopped")
