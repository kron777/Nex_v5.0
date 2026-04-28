"""Belief activation tracking with lazy exponential decay.

activation represents how recently and frequently a belief has been
retrieved into a fountain prompt. Decay is continuous — effective
activation is computed on-read rather than stored decayed.

Writer-safe: bump_activation and get_top_activated accept a substrate.Writer
(not a raw sqlite3.Connection) so writes queue through the single worker
thread and never race with the WAL write lock.
"""
import math
import time

HALFLIFE_SECONDS = 1800  # 30 minutes


def bump_activation(writer, belief_id: int) -> None:
    """Record a retrieval hit for belief_id, decaying the existing value first.

    writer: substrate.Writer instance for beliefs.db
    """
    now = time.time()
    writer.write(
        """
        INSERT INTO belief_activation (belief_id, activation, last_touched_at)
        VALUES (?, 1.0, ?)
        ON CONFLICT(belief_id) DO UPDATE SET
            activation = MIN(10.0,
                activation * EXP(-(? - last_touched_at) / ?) + 1.0),
            last_touched_at = ?
        """,
        (belief_id, now, now, HALFLIFE_SECONDS, now),
    )


def get_activation(reader, belief_id: int) -> float:
    """Return the current effective activation for belief_id.

    reader: substrate.Reader instance for beliefs.db
    Returns 0.0 if belief has never been activated.
    """
    now = time.time()
    row = reader.read_one(
        "SELECT activation, last_touched_at FROM belief_activation WHERE belief_id = ?",
        (belief_id,),
    )
    if not row:
        return 0.0
    activation, last_touched = row[0], row[1]
    return activation * math.exp(-(now - last_touched) / HALFLIFE_SECONDS)


def get_top_activated(reader, n: int = 10) -> list[dict]:
    """Return up to n beliefs sorted by current effective activation (desc).

    reader: substrate.Reader instance for beliefs.db
    Each dict has keys: belief_id, eff_activation, last_touched_at,
                        content, tier, source.
    """
    now = time.time()
    rows = reader.read(
        """
        SELECT ba.belief_id,
               ba.activation * EXP(-(? - ba.last_touched_at) / ?) AS eff_activation,
               ba.last_touched_at,
               b.content, b.tier, b.source
        FROM belief_activation ba
        JOIN beliefs b ON ba.belief_id = b.id
        WHERE ba.activation * EXP(-(? - ba.last_touched_at) / ?) > 0.01
        ORDER BY eff_activation DESC
        LIMIT ?
        """,
        (now, HALFLIFE_SECONDS, now, HALFLIFE_SECONDS, n),
    )
    return [dict(r) for r in rows]
