"""Affinity loop — beliefs gain weight from use, then refined by self-rating.

=======================================================================
2026-07-09 FINDING: THE SELF-RATING IS HOLLOW. Read before trusting any
affinity number in this system.
=======================================================================

_self_rate() asks the 3B voice model "how much does this feel like YOURS?"
against a four-point scale (0.0/0.3/0.6/1.0). Tested at temperature=0.0
on six beliefs, five repetitions each, it emits ONLY 0.3 or 0.6 -- it
copies the nearest anchor label from the prompt rather than scoring the
content.

  headline   "Mount Etna eruption creates trail of lava"   -> 0.3
  her ground "My market calls are no better than chance,
              and I know this because it was checked"       -> 0.3
  noise      "The doorbell rings but I ignore it for now"   -> 0.3
  her axiom  "I attend to unfamiliar things..."             -> 0.3 / 0.6 (unstable)

Removing the anchors and asking for 0-100 gives 45/45/45/35/35/50 -- it
rates the volcano headline ABOVE her founding axiom. Forced binary
(MINE/OBSERVED) returns MINE for the volcano and the doorbell, and
OBSERVED for her own synthesis. Exactly backwards.

This is NOT general instruction-following failure. The same model, same
wrapper, same temperature, classifies the same sentences correctly:
  headline vs reflection : 4/4
  external vs internal   : 4/4
It cannot count words (34 for a 10-word sentence), and it cannot judge
ownership -- because judging ownership requires a persistent self to
compare against, and each call is a stateless completion wearing a
persona. There is no 'there' for the question to point at.

CONSEQUENCE: every affinity value in the store is
    (0.3 or 0.6) * usage_term
i.e. FAMILIARITY, relabelled as preference. The 12,564 scored beliefs,
the 0.2-0.3 histogram cluster, the 'favourites' list read by
generator.py:2393 -- all of it is retrieval-count arithmetic.

The formula below (draw leads, familiarity amplifies) is structurally
correct and semantically empty. It is retained because the shape is right
and awaits a real signal.

WHERE THE REAL SIGNAL LIVES: ownership need not be asked. It is already
recorded -- beliefs.source. wonder_loop is something she wondered;
synergized is something she built from two things she held;
precipitated_from_sense is a headline she read. And DRAW is not a rating
but a behaviour: what she returns to, builds on, speaks from. All logged.
The only belief in this system formed by genuine contact with something
she does not control is the market scorecard (grounded_scorecard,
tier 1, conf 0.99) -- and it is the only one that was checked rather
than asserted.

=======================================================================


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
from substrate import connect
import threading
import time
from pathlib import Path

log = logging.getLogger("theory_x.life.affinity_loop")

from substrate.paths import DbPath  # resolves NEX5_DATA_DIR at use time (test hygiene)
BELIEFS_DB = DbPath("beliefs")
TICK_SECONDS = 1800
BATCH_LLM_CALLS = 30  # cap per tick
USAGE_RECENCY_HALFLIFE_HOURS = 168  # 7 days
MIN_USAGE_FOR_LLM = 2  # don't LLM-rate beliefs never used
RESCORE_AFTER_DAYS = 14


# ---------------------------------------------------------------------------
# Provenance-based affinity (D-A). The LLM self-rating above is documented as
# hollow (see the file header): it emits only 0.3/0.6 and rates a volcano
# headline above her founding axiom. Ownership is already recorded in
# beliefs.source, so derive the base from there instead of asking the model.
#
# Gated by NEX5_AFFINITY_PROVENANCE:
#   off     (default) -- old llm_rating path, unchanged; a true rollback.
#   shadow            -- old path still drives the WRITES; also compute the
#                        provenance score and log the (prov - llm) delta once
#                        per tick, so the shift can be measured before trusting.
#   on                -- provenance drives the writes; no LLM call at all.
#
# The output envelope is preserved exactly. The old score was
# llm_rating*(0.75+0.25*usage) with llm_rating in {0.3,0.6}; the bases below
# feed the SAME multiplier, so the range is unchanged (0.225-0.60) and only the
# ordering changes -- her own synthesis now outranks a passing observation.
_AUTHORED = 0.60   # generated by her own loop from her own material
_WITNESSED = 0.45  # derived from external observation; ownership partial
_RECEIVED = 0.30   # seeded/imported, not generated (also the default)

PROVENANCE_BASE: dict[str, float] = {
    "fountain_insight": _AUTHORED,
    "synergized": _AUTHORED,
    "counterfactual_node": _AUTHORED,
    "remember_loop": _AUTHORED,
    "wonder_loop": _AUTHORED,
    "hot_observer": _AUTHORED,
    "surprise": _AUTHORED,       # owner's call: a surprise is hers, not observed
    "witness_loop": _WITNESSED,
    "pattern_loop": _WITNESSED,
    "identity_loop": _WITNESSED,   # seeded, so cannot outrank what she authored, but
                                   # must not rank below things she merely read (received)
    # --- D-A go-live: the 11 eligible sources that were falling through to the
    # _RECEIVED default. Classified explicitly (owner-approved) so none is scored
    # by accident -- an unmapped eligible source is a hard STOP in the backfill's
    # GO/STOP rule, precisely because a silent default is not a decision.
    # authored (0.60) -- self-originated
    "fountain": _AUTHORED,
    "emergent_drive": _AUTHORED,
    # witnessed (0.45) -- self-observation / from her own internal state
    "behavioural_observation": _WITNESSED,
    "precipitated_from_dynamic": _WITNESSED,
    "self_rut_notice": _WITNESSED,
    # received (0.30) -- external input / suspect / experimental; deny authored credit.
    # precipitated_from_sense is the author's own framing (header, line 47:
    # "precipitated_from_sense is a headline she read") -- external, not hers. It is
    # 27 sense streams flattened into one bucket; per-kind tiering via source_kind
    # (source_identity.py) is a tracked follow-up, not part of this go-live.
    "precipitated_from_sense": _RECEIVED,
    "fetch_loop": _RECEIVED,                    # reads external URLs
    "fountain_insight_quarantined": _RECEIVED,  # quarantined/suspect fountain insight
    "drive_probe": _RECEIVED,                   # experimental probe injection
    "auto_probe": _RECEIVED,                    # experimental probe injection
    "throw_net.gate_reject": _RECEIVED,         # rejected content
}

# Unknown sources are counted once per process (not per row) so a new source
# value shows up in the log without spamming it.
_unknown_sources: set = set()


def _provenance_affinity(source, usage_score):
    """Provenance base lifted by usage, same multiplier as the old formula."""
    base = PROVENANCE_BASE.get(source)
    if base is None:
        base = _RECEIVED
        if source not in _unknown_sources:
            _unknown_sources.add(source)
            log.info("affinity_loop: unknown source %r -> received base", source)
    final = base * (0.75 + 0.25 * (usage_score or 0.0))
    return min(1.0, max(0.0, final))


def _log_shadow_delta(deltas):
    """One line per tick: how far provenance moves scores off the llm values."""
    if not deltas:
        return
    n = len(deltas)
    mean = sum(deltas) / n
    buckets = {"<=-.25": 0, "-.25..0": 0, "0..+.25": 0, ">=+.25": 0}
    for d in deltas:
        if d <= -0.25:
            buckets["<=-.25"] += 1
        elif d < 0:
            buckets["-.25..0"] += 1
        elif d < 0.25:
            buckets["0..+.25"] += 1
        else:
            buckets[">=+.25"] += 1
    log.info("affinity_loop shadow: n=%d mean_delta=%+.3f dist=%s",
             n, mean, buckets)


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
    """Top usage-score beliefs that need affinity rating.

    2026-07-26: 'demoted_confabulation' excluded from eligibility entirely.
    It was already correctly absent from the "hers by origin" whitelist
    below, but the usage-based branch (use_count >= MIN_USAGE_FOR_LLM) has
    no source filter, so an already-self-acknowledged fabrication with high
    legacy use_count (accumulated before it was demoted) stayed eligible
    for LLM self-rating anyway. Confirmed live: belief 12310 ("I am nex,
    the intelligence", use_count=487) scored affinity=0.973 -- the highest
    in the entire store -- under the current llm_rating*(0.75+0.25*usage)
    formula, because the rater judged it maximally "hers." This is the same
    class of gap the whitelist already exists to prevent; the whitelist
    just didn't cover the OR'd usage branch. Whether the LLM rating itself
    should be trusted at all is a separate, unresolved question (see the
    SELF-RATING IS HOLLOW finding at the top of this file) -- not touched
    here.
    """
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
          AND b.source NOT IN ('spectrum', 'demoted_confabulation')
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


def _affinity_mode():
    """off | shadow | on, from NEX5_AFFINITY_PROVENANCE (default off)."""
    try:
        import nex_config
        mode = nex_config.get_str("NEX5_AFFINITY_PROVENANCE", "off")
    except Exception:
        mode = "off"
    mode = (mode or "off").strip().lower()
    return mode if mode in ("off", "shadow", "on") else "off"


def affinity_tick(voice):
    cx = connect(BELIEFS_DB, timeout=30)
    mode = _affinity_mode()
    try:
        candidates = _pick_candidates(cx, BATCH_LLM_CALLS)
        if not candidates:
            return {"scored": 0, "candidates": 0}
        scored = 0
        skipped = 0
        shadow_deltas = []
        for c in candidates:
            if mode == "on":
                # Provenance drives the write; no LLM call. beliefs.source
                # already records ownership, so there is nothing to ask.
                final = _provenance_affinity(c["source"], c["usage_score"])
            else:
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
                if mode == "shadow":
                    # Old score still written; record how far provenance would
                    # move it, to be reviewed before trusting (prov - llm).
                    shadow_deltas.append(
                        _provenance_affinity(c["source"], c["usage_score"]) - final
                    )
            try:
                cx.execute(
                    "UPDATE beliefs SET affinity=?, affinity_updated_at=? WHERE id=?",
                    (final, time.time(), c["id"])
                )
                scored += 1
            except Exception as e:
                log.warning("affinity write failed for #%s: %s", c["id"], e)
        cx.commit()  # one commit for the whole batch (was one fsync per row)
        if mode == "shadow":
            _log_shadow_delta(shadow_deltas)
        log.info("affinity_loop: scored %d, unrated %d, of %d candidates (mode=%s)",
                 scored, skipped, len(candidates), mode)
        return {"scored": scored, "unrated": skipped,
                "candidates": len(candidates), "mode": mode}
    finally:
        cx.close()


def affinity_loop(state, stop):
    log.info("affinity_loop started (tick=%ds, batch=%d)",
             TICK_SECONDS, BATCH_LLM_CALLS)
    voice = None
    while not stop.is_set():
        try:
            if voice is None:
                from voice.llm import VoiceClient, voice_model
                voice = VoiceClient(model=voice_model())
            stats = affinity_tick(voice)
            if stats.get("scored"):
                log.info("affinity_loop: %s", stats)
        except Exception as e:
            log.error("affinity_loop tick failed: %s: %s",
                      type(e).__name__, str(e)[:200])
            voice = None
        stop.wait(TICK_SECONDS)
    log.info("affinity_loop stopped")
