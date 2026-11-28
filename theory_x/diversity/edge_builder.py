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
from substrate import Reader, Writer
import threading
import time
from pathlib import Path

from theory_x.diversity.embeddings import embed_belief, cosine

log = logging.getLogger("theory_x.diversity.edge_builder")

from substrate.paths import DbPath  # resolves NEX5_DATA_DIR at use time (test hygiene)
BELIEFS_DB = DbPath("beliefs")

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


def edge_builder_tick(
    db_path: Path = BELIEFS_DB,
    *,
    beliefs_reader: Reader | None = None,
    beliefs_writer: Writer | None = None,
    stop_event=None,
) -> dict:
    """One pass through the canonical Reader/Writer pair.

    The standalone db_path form remains available for tests/tools; in normal
    Stage-2 operation the existing per-database Reader and Writer are injected.
    All candidate reads use Reader, and all edge inserts are committed atomically
    through the single beliefs Writer.
    """
    own_writer = beliefs_writer is None
    reader = beliefs_reader or Reader(db_path)
    writer = beliefs_writer or Writer(db_path, name="diversity.edge_builder")
    try:
        # Find beliefs with fewer than MIN_EDGES_PER_BELIEF outgoing edges.
        # Prefer newer beliefs (created_at DESC).
        if stop_event is not None and stop_event.is_set():
            return {"considered": 0, "wrote": 0, "skipped": 0}
        candidates = reader.read("""
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
        """, (MIN_EDGES_PER_BELIEF, MIN_CONTENT_LEN, BELIEFS_PER_TICK))

        if not candidates or (stop_event is not None and stop_event.is_set()):
            return {"considered": 0, "wrote": 0, "skipped": 0}

        # Build the comparison pool — recent beliefs above a content threshold.
        pool_rows = reader.read("""
            SELECT id, content
            FROM beliefs
            WHERE length(content) >= ?
              AND paused = 0
            ORDER BY created_at DESC
            LIMIT ?
        """, (MIN_CONTENT_LEN, POOL_SIZE))
        if stop_event is not None and stop_event.is_set():
            return {"considered": len(candidates), "wrote": 0, "skipped": 0}
        pool = []
        for r in pool_rows:
            if stop_event is not None and stop_event.is_set():
                return {"considered": len(candidates), "wrote": 0, "skipped": 0}
            if not _should_skip(r["content"]):
                pool.append((r["id"], r["content"]))
        if not pool:
            return {"considered": len(candidates), "wrote": 0, "skipped": len(candidates)}

        statements: list[tuple[str, tuple]] = []
        skipped = 0
        for candidate in candidates:
            if stop_event is not None and stop_event.is_set():
                break
            if _should_skip(candidate["content"]):
                skipped += 1
                continue

            try:
                source_vector = embed_belief(candidate["id"], candidate["content"])
            except Exception as exc:
                log.warning("embed failed for belief %s: %s", candidate["id"], exc)
                skipped += 1
                continue
            if stop_event is not None and stop_event.is_set():
                break

            # Score every pool member; collect (target_id, similarity) above threshold.
            scores: list[tuple[int, float]] = []
            for pool_id, pool_content in pool:
                if stop_event is not None and stop_event.is_set():
                    break
                if pool_id == candidate["id"]:
                    continue
                try:
                    pool_vector = embed_belief(pool_id, pool_content)
                    if stop_event is not None and stop_event.is_set():
                        break
                    similarity = cosine(source_vector, pool_vector)
                except Exception:
                    continue
                if similarity >= SIM_THRESHOLD:
                    scores.append((pool_id, similarity))

            if stop_event is not None and stop_event.is_set():
                break
            scores.sort(key=lambda item: item[1], reverse=True)
            top = scores[:TOP_K_PER_BELIEF]
            if not top:
                continue

            now = time.time()
            for target_id, similarity in top:
                statements.append((
                    "INSERT OR IGNORE INTO belief_edges "
                    "(source_id, target_id, edge_type, weight, created_at) "
                    "VALUES (?, ?, 'cross_domain', ?, ?)",
                    (candidate["id"], target_id, float(similarity), now),
                ))

        if stop_event is not None and stop_event.is_set():
            return {"considered": len(candidates), "wrote": 0, "skipped": skipped}

        # One BEGIN IMMEDIATE / COMMIT through the canonical per-DB Writer.
        # rowcount is captured per statement so ignored duplicates remain zero.
        results = (
            writer.write_many_with_counts(
                statements, continue_on_integrity_error=True
            ) if statements else []
        )
        wrote = sum(1 for _row_id, rowcount in results if rowcount > 0)
        return {"considered": len(candidates), "wrote": wrote, "skipped": skipped}
    finally:
        if own_writer:
            writer.close()


def edge_builder_loop(state, stop: threading.Event) -> None:
    """Daemon entrypoint matching stage2_dynamic's (state, stop) contract."""
    log.info("edge_builder loop started (tick=%ds, sim>=%.2f, top=%d)",
             TICK_SECONDS, SIM_THRESHOLD, TOP_K_PER_BELIEF)
    while not stop.is_set():
        try:
            stats = edge_builder_tick(
                beliefs_reader=state.readers["beliefs"],
                beliefs_writer=state.writers["beliefs"],
                stop_event=stop,
            )
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
