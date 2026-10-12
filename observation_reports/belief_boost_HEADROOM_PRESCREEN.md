# E4 HEADROOM PRE-SCREEN: the `belief_boost` content lever

> **STATUS 2026-10-12 — READ-ONLY PRE-SCREEN. No lever built. No flag, no fire-path change.** This is
> the go/no-go measurement that must pass BEFORE any `belief_boost`-based content lever is designed —
> the belief-pool analogue of the arbiter's `NEX5_GW_LOG` exposure and of READ A's `self_state_history`
> headroom. Unlike those, the belief pool is **populated now**, so this runs today (operator runs it on
> the live `beliefs.db`; the worktree has none and the tool reports "is beliefs.db populated?").

## Why this is the only reorder-free content path

The fountain fetch (`generator._retrieve_context_beliefs`) is **recency-ordered**, not focus-gated: it
takes the top `own_n` (modes.py default **12**) own-content beliefs by **effective recency**

    eff = created_at + (boost_value − 1.0) · BOOST_TIME_BONUS_SECONDS   (3.5 days)

with a per-branch cap of 2. `sense` already enters this pool as `precipitated_from_sense` beliefs
competing on recency. So the one way a sense/surprise-derived signal could change the *fetched content*
**without reordering the fire path** is to raise a belief's effective recency — i.e. `belief_boost`
(`theory_x/diversity/boost.py`). A boost **replaces** (ON CONFLICT UPDATE), it does not stack, and
**decays** 0.02/day (removed at `boost_value ≤ 1.05`). Empirical grade ~0.42 ⇒ a boost buys **~1.47
days** of effective recency.

## The binding predicate — HEADROOM

Can a within-range boost actually change *which* beliefs are fetched? A below-cutoff belief is
promotable iff `created_at + max_grade·3.5d > eff[cutoff]` (boost replaces, so its max reachable recency
is `created_at + max lift`). The pre-screen (`tools/check_belief_headroom.py`) reports:

- **`promotable_count`** — below-cutoff own-content beliefs a max boost could lift into the top `own_n`.
- **`grade_to_promote_marginal`** — the grade the single most-recent below-cutoff belief would need
  (vs `max_grade`).
- **`swap_zone_count`** — density of beliefs whose `created_at` is within one max-lift of the cutoff.
- **SENSE read** — the same restricted to `precipitated_from_sense` (`in_pool / in_fetch / below_cutoff
  / promotable`): the lever's *purpose* is sense→content, so sense material must be present and
  promotable, not just generic content.

### Go / no-go

- **HEADROOM ABSENT** (`promotable_count = 0`, or `grade_to_promote_marginal > max_grade`): the cutoff
  gap exceeds any feasible boost — a boost **cannot** change the fetched set. `belief_boost` is
  decision-**inert** here, the direct analogue of the readiness gate saturated at fire. **DO NOT build
  the lever.**
- **HEADROOM THIN** (1–2 promotable): design with caution, re-measure before arming.
- **HEADROOM PRESENT** (≥3 promotable): a boost genuinely re-orders the fetch; the lever has range.
- **SENSE PATH DEAD / INERT** overrides: even with generic headroom, if no `precipitated_from_sense`
  belief is in the pool (DEAD) or none is in-fetch-or-promotable (INERT), the sense→content path itself
  is inert — the lever would only re-weight own-fire content, not route sense.

## Tripwire / what it does NOT measure (binding)

1. **It measures FETCH-SET MOVABILITY, not the lever's effect on the voice.** A passing headroom says a
   boost *can* swap content in; whether doing so changes what she writes (the outcome) is a separate,
   voice-track question ([[nex5-lever-prescreen-and-voice]]), not this pre-screen.
2. **Decay is not yet in the predicate.** Headroom is a snapshot; a boost decays 0.02/day and is removed
   at ≤1.05, so a one-shot boost's promotion is transient (~days). If headroom passes, the next question
   (open, for Beam) is whether a one-shot boost persists long enough to matter or must be re-applied.
3. **Run it live, on ≥ a representative pool.** The snapshot depends on the recent write burst; read it
   on the live `beliefs.db` over a normal window, not a quiet one. `precipitated_from_sense` is a
   distinct `source`, so the sense read is never blended with own-fire content.
