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

The fetch applies BOTH caps in recency order — per-source (max 3, `precipitated_from_sense` → **5**) AND
per-branch (**2**) — so the pre-screen is **cap-aware**: a belief can clear the rank cutoff yet be locked
out because its branch or source is already full. `promotable_effective` re-runs the real capped
admission with the candidate boosted and checks it actually lands in the top `own_n` (Beam Q1b — without
this the pre-screen would return a FALSE GO for structurally locked-out beliefs, the worst direction).

- **`sense.promotable_effective`** — cap-aware count of `precipitated_from_sense` beliefs a max boost
  lands in the fetch. **This is the GO gate** (Beam Q1: the lever acts on sense, so gate on the sense
  count; generic `promotable_effective` is a *substrate* diagnostic — gating on it is the readiness-gate
  mistake, measuring the room not the lever).
- **`sense.cap_blocked`** = clears the rank cutoff but a cap locks it out (the false-GOs now excluded).
- **SENSE breakdown** `in_pool / in_fetch / below_cutoff / clears / promotable_effective / cap_blocked`
  — names *why* a NO: `in_pool = 0` is upstream EXPOSURE (fix precipitation, not boost); `in_pool > 0,
  promotable_effective = 0` is a reach/cap/calibration problem. `in_fetch > 0` is a **ceiling REDUCER**
  (less marginal room), **not** a GO signal.
- generic `promotable_effective` / `clears_cutoff` / `cap_blocked` + `grade_to_promote_marginal` —
  diagnostics only.

### Go / no-go (gate = `sense.promotable_effective`)

- **NO-GO / SENSE PATH DEAD** (`sense.in_pool = 0`): upstream exposure problem, not a boost problem.
- **NO-GO / HEADROOM ABSENT** (`sense.promotable_effective = 0`): no sense belief is cap-aware-promotable
  (cutoff gap too large, or all cap-blocked). `belief_boost` is decision-**inert** for the sense path —
  the readiness-gate analogue. **DO NOT build.**
- **THIN** (1–2): design with caution, re-measure.
- **GO / HEADROOM PRESENT** (≥3): a boost genuinely lands sense content in the fetch; the lever has range.

## Resolved design (Beam Q2–Q4) — gated behind a GO

- **Q2 — transience is intended, not a defect; do NOT add a persistence gate.** The pool is a recency
  self-feedback loop; durable promotion would *freeze* its turnover into a standing priority — a
  different system. The window is an **effect-size read**: `effect_window` reports the static decay clock
  (`(B−1.05)/0.02` days) and the pool's own-write/day; the **binding RACE clock** (fresh writes push the
  cutoff younger) needs the live inter-fire cadence and is flagged as not-computable-offline. A *durable*
  effect would require re-applying the boost each fire — a **standing rule**, its own node and pre-reg,
  not this one-shot lever.
- **Q3 — locus is REAL (definitional-coupling check passes), and bigger than assumed.** `apply_boost` has
  **no live caller** (only a test/export); the grade that would feed it is the *collision-novelty* grader
  (`grader.py`: embedding input/output distance + rarity) with **no sense/surprise input**. So a
  sense→boost path is not double-counting an existing driver — `belief_boost` is **dormant in
  production**, and the lever would be its first live writer. Scope = *activate and drive a dormant
  channel*, not *add a knob to a running one*.
- **Q4 — topic-mix-toward-sense is a MANIPULATION CHECK, not the primary** (it is true by construction).
  The two **co-primaries are the prices**: (1) voice non-inferiority — `H(content|style)` must not fall
  below the G3 bound (baseline 3.21, n=2091); (2) sense-content **distinctness** — boosted items must be
  *new* sense beliefs, not the same ones re-surfaced every fire (a boost channel is itself a new fixation
  generator). **Design: randomize within-fire** (boost a random subset of sense beliefs each fire) for a
  per-fire paired boosted-vs-non-boosted read, keeping cutoff/cadence confounds common across arms.

## Tripwire / what it does NOT measure (binding)

1. **It measures FETCH-SET MOVABILITY, not the lever's effect on the voice.** A GO says a boost *can*
   land sense content; whether that changes what she writes is the Q4 co-primaries, not this pre-screen.
2. **Run it live, on a representative window.** The snapshot depends on the recent write burst; read the
   live `beliefs.db` over a normal window. `precipitated_from_sense` is a distinct `source`, never blended.
