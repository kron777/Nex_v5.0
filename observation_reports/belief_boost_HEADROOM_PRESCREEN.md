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
- **GO / REORDER HEADROOM PRESENT** (≥3 **and** `sense.cap_saturated`): the sense slot is full
  (`in_fetch = cap = 5`), so **net sense additions = 0** — each promotable belief enters only by
  **evicting an incumbent** sense belief. Honest label (Beam QC): this is *reorder* headroom, not *add*.

## LIVE RESULT (2026-10-13, `beliefs.db`, `--days 14`)

`n≈4236` own-content; sense **73% of the pool** and **5/12 of the fetch = its full source cap**.
`sense.promotable_effective ≈ 566`, `cap_blocked ≈ 603`. Verdict: **GO / REORDER HEADROOM PRESENT**.
So: presence is **already met** (sense is majority and cap-saturated); the lever's only honest target is
**selection** — *which* sense beliefs occupy the 5 slots. Recency is currently the sole selector into
them (modulo the branch cap); a boost adds a second selector. **Headroom ≠ deficiency:** the GO licenses
*building* and *testing* the lever, not arming it — see "driver divergence" below.

## Resolved design (Beam QC/QA/QB + Q2–Q4) — gated behind a GO

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
- **QC — DRIVER DIVERGENCE is the one read before arming (headroom ≠ deficiency).** The GO says a boost
  *can* change the output; it does **not** establish that recency is a *deficient* selector. The gate:
  overlap between the current top-5 sense (recency + branch cap, which is what the dormant fetch already
  picks) and the top-5 sense the boost **grade** would pick. Overlap ≈ full ⇒ the reorder is **cosmetic**
  (boost re-selects what recency already selects) ⇒ headroom-present-but-for-nothing. Divergence ⇒ the
  swap changes what she sees — that divergence *is* the effect being bought. This is measured by QA Stage
  A (below), not by this snapshot. And the outcome must score **both sides of the eviction**: did the
  entrant improve the set *relative to the incumbent it displaced*, under the driver's own criterion?
- **QA — existing grade FIRST, as a channel-liveness test, then the sense driver (two drivers, one dormant
  channel).** Stage A: drive `apply_boost` with the **existing collision-novelty grade** (zero new logic)
  and measure composition divergence + voice — this answers the *plumbing* question (is the channel live
  end-to-end: write→eff→admission→fetch) and the divergence question, cheaply. If divergence ≈ 0, the
  channel or the selection is inert and there is nothing to build on. Stage B: swap in the sense/surprise
  driver and measure the *targeted* divergence. Going straight to B confounds "channel works" with
  "sense driver good".
- **QB — durability stays a separate PRODUCTION node, but run one-shot AND re-boost as experimental ARMS.**
  Dormancy + the ~1.5-day one-shot window (Q2) is a power risk, so round one carries: **Arm A** one-shot;
  **Arm B** re-boost each fire, re-*selected* each fire (not the same set — else it entrenches and the
  distinctness co-primary flags it); **Control** no boost. Arm B is "the arm that keeps the window alive
  through the trial", not the production policy. If B wins, the durable form is pre-registered separately.
- **Q4 — the manipulation check is now COMPOSITION DIVERGENCE, not share-rise** (share is capped at 5 and
  cannot rise, so the old check is dead). Manipulation check = the fraction of the fetched top-5 sense
  that recency alone would not have selected. Co-primaries unchanged: (1) voice non-inferiority
  `H(content|style)` ≥ G3 bound (3.21, n=2091); (2) sense-content **distinctness** — and it matters *more*
  here, because a reorder loop that keeps re-selecting the same 5 entrants is template-repetition inside
  the sense block (the groove, relocated). Design: randomize within-fire for a per-fire paired read.

## Forward flag (separate node, do not fold in)

The live pool is **73% `precipitated_from_sense`** — the fountain is largely re-surfacing sense. Whether
that composition is healthy is its own question, upstream of this lever; it is noted, not addressed here.

## Tripwire / what it does NOT measure (binding)

1. **It measures FETCH-SET MOVABILITY, not DEFICIENCY, and not the voice effect.** A GO says a boost
   *can* reorder sense content; whether recency is a *bad* selector (driver divergence) and whether the
   swap helps (voice + distinctness) are the arming gates, not this pre-screen.
2. **When `cap_saturated`, the result is REORDER headroom — net additions 0.** Do not read it as raising
   sense presence; presence is set by the source cap (a different, non-recommended lever).
3. **Run it live, on a representative window.** The snapshot depends on the recent write burst; read the
   live `beliefs.db` over a normal window. `precipitated_from_sense` is a distinct `source`, never blended.
