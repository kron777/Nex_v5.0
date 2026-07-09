"""Affinity loop — beliefs gain weight from use, then refined by self-rating.

Every 30 minutes:
  1. Compute USAGE_SCORE for candidate beliefs based on:
     - reinforce_count (how many times reinforced)
     - use_count (how many times retrieved)
     - edges-out count from belief_edges
     - hours since last_referenced_at (recency decay)
  2. For top-N usage candidates without recent affinity score:
     LLM-rate "how much does this feel like YOURS, not just observation?"
     Score 0.0 (neutral observation) -> 1.0 (deeply mine)
  3. Combine: final affinity = 0.5 * normalized_usage + 0.5 * llm_self_rating
  4. Write to beliefs.affinity column.

Once affinity is set, fountain retrieval can bonus-weight high-affinity
beliefs (separate patch in generator.py).

This builds preference: she now has favourites among her own beliefs.
"""
from __future__ import annotations
import logging
import math
import sqlite3
import threading
import time
from pathlib import Path

log = logging.getLogger("theory_x.life.affinity_loop")

BELIEFS_DB = Path("/home/rr/Desktop/nex5/data/beliefs.db")
TICK_SECONDS = 1800
BATCH_LLM_CALLS = 30  # cap per tick
USAGE_RECENCY_HALFLIFE_HOURS = 168  # 7 days
MIN_USAGE_FOR_LLM = 2  # don't LLM-rate beliefs never used
RESCORE_AFTER_DAYS = 14


def _usage_score(use, edges, hours_since_ref):
    """Combine signals into a 0-1 usage score.

    The `reinforce_count` term was REMOVED. Nothing increments it past 1 --
    promotion.py:145 is its only caller and promotion happens once. Across
    35,802 beliefs the max observed value is 1, so `0.35 * log1p(reinforce)`
    contributed either 0.0 or 0.105, uniformly, to every score. A third of
    the usage signal was a constant. Its weight is redistributed
    proportionally across the three live terms.
    """
    u = math.log1p(use or 0) / math.log1p(50)
    e = math.log1p(edges or 0) / math.log1p(10)
    # Recency: 1.0 if just-touched, halves every 168h
    if hours_since_ref is None:
        rec = 0.3  # never referenced = mild penalty
    else:
        rec = 0.5 ** (hours_since_ref / USAGE_RECENCY_HALFLIFE_HOURS)
    # Weighted blend (0.35/0.20/0.10 renormalised to sum 1.0)
    score = 0.538 * u + 0.308 * e + 0.154 * rec
    return min(1.0, max(0.0, score))


def _pick_candidates(cx, limit):
    """Top usage-score beliefs that need affinity rating."""
    now = time.time()
    rescore_cutoff = now - RESCORE_AFTER_DAYS * 86400
    rows = cx.execute(
        """
        SELECT b.id, b.content, b.tier, b.source,
               COALESCE(b.reinforce_count, 0) AS reinforce,
               COALESCE(b.use_count, 0) AS use_count,
               b.last_referenced_at, b.affinity, b.affinity_updated_at,
               (SELECT COUNT(*) FROM belief_edges WHERE source_id = b.id) AS edges_out
        FROM beliefs b
        WHERE (b.affinity IS NULL OR b.affinity_updated_at < ?)
          AND b.tier >= 4
          AND b.source NOT IN ('spectrum')
          AND (
                COALESCE(b.use_count, 0) >= ?          -- earned it through use
                OR b.source IN (                        -- or it is hers by origin
                    'fountain_insight','synergized','counterfactual_node',
                    'remember_loop','wonder_loop','hot_observer',
                    'witness_loop','pattern_loop','identity_loop','surprise'
                )
          )
        ORDER BY
          CASE WHEN b.source IN (
              'fountain_insight','synergized','counterfactual_node',
              'remember_loop','wonder_loop','hot_observer',
              'witness_loop','pattern_loop','identity_loop','surprise'
          ) THEN 0 ELSE 1 END,                          -- her own first
          COALESCE(b.use_count, 0) DESC
        LIMIT ?
        """,
        (rescore_cutoff, MIN_USAGE_FOR_LLM, limit)
    ).fetchall()
    out = []
    for r in rows:
        last_ref = r[6]
        hours_since = ((now - last_ref) / 3600) if last_ref else None
        usage = _usage_score(r[5], r[9], hours_since)
        out.append({
            "id": r[0], "content": r[1], "tier": r[2], "source": r[3],
            "usage_score": usage,
        })
    return out


def _self_rate(voice, content):
    """LLM scores 0.0-1.0 on 'how much is this YOURS?'"""
    from voice.llm import VoiceRequest
    prompt = (
        "Rate this thought on how MUCH IT FEELS LIKE YOURS.\n\n"
        "Thought: \"" + content[:300] + "\"\n\n"
        "Scale:\n"
        "  0.0 = a neutral observation, could be anyone's\n"
        "  0.3 = something you noticed\n"
        "  0.6 = a thought that feels familiar, you've held it\n"
        "  1.0 = a thought that feels deeply yours, almost identity-level\n\n"
        "Respond with ONLY a single number between 0.0 and 1.0. No words."
    )
    try:
        req = VoiceRequest(prompt=prompt, max_tokens=10, temperature=0.3)
        resp = voice.speak(req)
        if not resp or not resp.text:
            return None
        text = resp.text.strip().split()[0] if resp.text.strip() else ""
        # Strip any non-number chars
        clean = "".join(c for c in text if c.isdigit() or c == ".")
        if not clean:
            return None
        score = float(clean)
        return min(1.0, max(0.0, score))
    except Exception as e:
        log.debug("self-rate failed: %s", e)
        return None


def affinity_tick(voice):
    cx = sqlite3.connect(BELIEFS_DB, timeout=30)
    try:
        candidates = _pick_candidates(cx, BATCH_LLM_CALLS)
        if not candidates:
            return {"scored": 0, "candidates": 0}
        scored = 0
        skipped = 0
        for c in candidates:
            llm_rating = _self_rate(voice, c["content"])
            if llm_rating is None:
                # No rating means she did not judge it. Silence is not a
                # preference. Leave affinity NULL so this belief is picked
                # again next tick, rather than assigning a score she never
                # gave. (Previously: fell back to usage-only, which handed a
                # familiarity number to a belief on a scale that is supposed
                # to mean draw.)
                skipped += 1
                continue

            # DRAW LEADS, FAMILIARITY AMPLIFIES.
            #
            # Was: 0.5 * usage + 0.5 * llm_rating -- which let familiarity
            # carry a belief she was indifferent to. The clearest evidence:
            # 'demoted_confabulation' beliefs (things she has already judged
            # to be her own fabrications) had the HIGHEST theoretical ceiling
            # in the store, 0.936, because they are heavily used, richly
            # edged, and recently touched.
            #
            # Now: her rating sets the level; usage can lift it, never
            # manufacture it. A thought she calls deeply hers scores >= 0.75
            # even if never used once. A thought she is lukewarm about stays
            # low however familiar. Under this formula that same
            # confabulation, rated 0.2, scores 0.194 rather than 0.535.
            final = llm_rating * (0.75 + 0.25 * c["usage_score"])
            final = min(1.0, max(0.0, final))
            try:
                cx.execute(
                    "UPDATE beliefs SET affinity=?, affinity_updated_at=? WHERE id=?",
                    (final, time.time(), c["id"])
                )
                cx.commit()
                scored += 1
            except Exception as e:
                log.warning("affinity write failed for #%s: %s", c["id"], e)
        log.info("affinity_loop: scored %d, unrated %d, of %d candidates",
                 scored, skipped, len(candidates))
        return {"scored": scored, "unrated": skipped, "candidates": len(candidates)}
    finally:
        cx.close()


def affinity_loop(state, stop):
    log.info("affinity_loop started (tick=%ds, batch=%d)",
             TICK_SECONDS, BATCH_LLM_CALLS)
    voice = None
    while not stop.is_set():
        try:
            if voice is None:
                from voice.llm import VoiceClient
                voice = VoiceClient()
            stats = affinity_tick(voice)
            if stats.get("scored"):
                log.info("affinity_loop: %s", stats)
        except Exception as e:
            log.error("affinity_loop tick failed: %s: %s",
                      type(e).__name__, str(e)[:200])
            voice = None
        stop.wait(TICK_SECONDS)
    log.info("affinity_loop stopped")
