# R79 — PRE-REGISTRATION: L4_stakes, the bounded self-referent cost (`NEX5_STAKES`)

## 0. Status — Step-0 feasibility is MEASURED, and it GATES the round

This is **not yet a runnable effect-round.** As built, the stakes cost is **inert on the live
instrument**: the signal it reads never approaches the threshold that would make the cost
non-zero. Measured 2026-10-11 against the live data dir (§2). So the first thing this document
does is freeze that feasibility baseline and pre-register the **fork** that must be resolved
before `NEX5_STAKES` is ever armed — then (§4–§8) the full effect-round protocol for the case
where the mechanism *can* fire, locked now so no choice is improvised against a result.

Pre-registration order: this is sequenced **after r77 (chat arbiter) and r78 (`self_present`)** —
one variable at a time. `NEX5_STAKES` is held OFF during r77/r78 (it joins their confound set).

## 1. The change under test

**`NEX5_STAKES` (default OFF).** When armed, `readiness.score` subtracts
`readiness_penalty(appraise()["cost"])`, where `cost = clamp(ratio − 0.55)` bounded to ≤ 0.20,
and `ratio` = the fraction of the last `_SAMPLE_N=8` substantive fires that
`stakes_monitor._is_template` flags. Code: `theory_x/stage_tom/stakes_appraisal.py`,
`theory_x/stage6_fountain/readiness.py:104`. OFF ⇒ readiness byte-identical. ANALOGUE — no claim
of a felt cost. Welfare envelope (`SENTIENCE_PROGRAM.md §5a`): bounded, non-compounding,
disable-able, logged, never narrated as suffering.

## 2. Step 0 — FEASIBILITY (measured, frozen)

**Frozen baseline — the drift signal the cost reads, live instrument, 14 days to 2026-10-11:**

| Quantity | Value |
|---|---|
| day-by-day drift ratio (substantive fires) | mean **0.095**, median **0.077**, stdev 0.079 |
| max daily ratio | 0.155 (the 0.333 day had 3 fires — noise) |
| 8-fire `appraise()` reading, now | **0.0** (`cost` 0.0, `stakes_active` False, n=5) |
| lag-1 autocorrelation (daily) | +0.045 (drift does **not** persist day-to-day) |
| substantive fires sampled | 2556 across 13 active days |

**The gate.** `cost > 0` requires `ratio ≥ 0.55`, i.e. **≥ 5 of the last 8** substantive fires
flagged template. At the observed base rate (~0.10), P(≥5/8) ≈ **0.0004 per window**. The cost is
therefore **≈ 0 essentially always**; arming `NEX5_STAKES` at threshold 0.55 **changes nothing**.
→ **Feasibility FAILS at 0.55.** Running an effect-round now would pre-register a guaranteed null
(the "supply is not eligibility" error — predicting an effect from a mechanism the data shows is
inert).

**Diagnostic cross-check — the grooving is real, the cost is just blind to it.** The *other*
template detector, `theory_x/diversity/groove.py` (`_detect_template_repetition`, live via
`diversity/loop.py:53`), fired **696× in the same 14 days (~49.7/day)** at severity **mean 0.991
/ median 1.000** into `beliefs.db:groove_alerts`. So the fire-stream grooves often and hard;
`stakes_monitor`'s "≥55% of the last 8 fires" definition simply does not register it. (This is the
live-data reason the §7 "disconnected groove detector" finding matters here — not the problem-
promotion reason Beam gave.)

## 3. The pre-registered FORK — resolve BEFORE any arming (one of A/B/C, chosen openly, not post-hoc)

- **A — re-source the cost from `groove_alerts`.** Drive `appraise().cost` from the live-calibrated
  groove detector instead of `stakes_monitor`'s 8-fire ratio. **Caveat locked now:** template
  severity is pinned at ~0.99 nearly always, so a cost proportional to raw severity would be a
  *perpetual brake* (constant readiness depression = global slowdown, not a targeted signal), which
  **fails the §5 over-suppression guardrail by construction**. Path A is therefore specifically: the
  cost responds to the **rate or onset/delta** of `template_repetition` alerts (e.g. a rise above
  the per-hour baseline), never to the ever-present severity level. Requires a small rebuild +
  a re-frozen baseline on the new signal, then the §4–§8 round.
- **B — recalibrate `stakes_monitor`'s threshold** to a value the 8-fire ratio actually reaches.
  Weak: the 8-fire ratio sits near 0 even when grooving (§2), so lowering 0.55 barely helps and
  risks tripping on 1-of-8 noise. A dominates B unless there is a reason to keep the ratio source.
- **C — do not ship it.** Per `SENTIENCE_PROGRAM.md §5a`, an aversive signal must be *necessary, not
  gratuitous*. A cost that does **no work** (inert, §2) is by definition gratuitous, and the grooving
  it was meant to answer is already detected and consumed elsewhere (`groove_alerts` → 9+ consumers).
  If A's rebuild cannot clear the §6 mechanical falsifier, **C is the welfare-correct default**:
  revert `NEX5_STAKES`, keep the appraisal module as instrumentation only (no readiness coupling).

**This fork is a decision for the maintainer, not a silent substitution** (round protocol: when a
pre-registered predicate fails its own tripwire, ask — don't swap the threshold to manufacture an
effect). Nothing downstream of §4 runs until the fork is resolved and a baseline re-frozen.

## 4. Hypothesis + primary metric (for A or B, once the mechanism can fire)

**Hypothesis.** Arming the (re-sourced) cost **reduces grooving** — the near-duplicate / template
share of the subsequent fire stream — **without** a global cadence collapse and **without**
regressing on-subject. Mechanism: high grooving now → bounded readiness cost now → the fountain
fires less *during* the groove → the groove dissipates → lower grooving next window.

**Primary metric.** The `template_repetition` alert **rate** (alerts/day from `groove_alerts`),
baseline **~49.7/day**. Effect sought: a ≥ 25% relative drop, ON vs frozen OFF baseline.

## 5. Over-suppression guardrail (the thing that separates "helped" from "just slowed her down")

- **Cadence** (`check_cadence --baseline`): active fires/day must stay within **±20%** of 690.5.
  A cost that cuts grooving *only* by cutting total output is a global brake, not a targeted
  signal — it fails here even if the primary metric moves.
- **On-subject** (`check_tripwires`): `p_on_subject` must not revert < 0.65 (EXPLAIN) and maxDF*
  must not breach ≥ 25%. (The hardened `check_tripwires.py` now resolves its DBs via `DbPath`, so
  this reads the armed instance, not a stale literal — see commit.)

## 6. The mechanical falsifier (held to the L3 standard)

L3's lesson was `P(move|active)=0.333 ≈ P(move|absent)=0.337` → "the nudge does not mechanically
move attention." The L4 analogue, pre-registered now:

> **P(grooming-rate drops in window *t+1* | cost was active in window *t*)**
> vs **P(grooming-rate drops in window *t+1* | cost ≈ 0 in window *t*)**.

If these are within noise of each other, the cost is **not** what reduced grooving (something else
is, or it is chance) → **falsified**, regardless of the primary-metric movement. The reduction must
be **concentrated in the windows where the cost actually fired.**

## 7. Tripwires — revert immediately if ANY fires (checked during the window)

Reuse r77's: cadence outside ±20% of 690.5; template dup/cluster up > +25%; `p_on_subject`
EXPLAIN < 0.65 or maxDF* breach ≥ 25%; register largest-share > 0.70. Plus an L4-specific one:
**readiness floor** — if mean readiness drops such that fires/day falls > 20% (the §5 guardrail),
STOP: the bound (0.20) is too large for the live signal and the cost is braking, not steering.

## 8. Decision tree — fixed now

Primary = `template_repetition` rate, baseline ~49.7/day.
- **BRANCH A — ≥ 25% relative drop AND no tripwire AND the §6 mechanical test passes.** The cost
  steers grooving. → default-ON *consideration*; one pre-registered bound-tuning pass (r79b: adjust
  `_COST_CLAMP` toward the smallest value that still clears §6), then stop.
- **BRANCH B — drop < 25%, or §6 fails, no tripwire.** The mechanism did not mechanically reduce
  grooming at the provisional bound. → **one** retry (r79b, bound tuning only). If r79b also fails
  Branch A, L4_stakes-as-a-readiness-cost is **falsified for its stated purpose** → Fork path **C**.
- **BRANCH C — any tripwire fires.** Revert regardless of the primary metric; record which and the
  reading.

## 9. Verdict and disarm

Verdict to `observation_reports/r79.md` + a row in `journal/DEPLOY_LEDGER.tsv` + `journal/CARRY_OVER.md`.
The disarm commit's subject line carries the verdict and the disarm SHA (repo convention). If the
Fork (§3) resolves to **C** without ever arming, that is itself the verdict: record "inert at 0.55,
not shipped" — a pre-registration that stopped an aversive signal from shipping inert is a success,
not a non-result.

---

*No sentience claim. This round tests whether a bounded functional cost measurably and mechanically
reduces a measured behaviour (grooving); it is silent on whether anything is experienced. The
Step-0 finding is that the cost as built cannot fire on the live instrument, and the welfare clause
makes "do not ship an inert aversive signal" the default, not the fallback.*
