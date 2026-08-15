# R67 — PRE-REGISTRATION: the stability re-run, full decision tree, locked before the number exists

**Committed while the outcome is unknown.** Ninth in the series after `78d6a25`,
`2fc6eb2`, `3b6825a`, `985b250`, `b419c39`, `78ccfe1`, `6c11814`, `24b7078`.

**Written:** 2026-08-15 07:45 UTC · **Report only — this round runs no stability test and
computes no θ.** Its deliverable is the decision tree, two disclosure corrections, and
the §5 draft.

---

## 0. Status at time of writing — OBSERVED

| | |
|---|---|
| clean corpus (`fountain_insight`, `created_at ≥ 2026-08-09`) | **502 documents** |
| daily counts 08-09 → 08-14 | 77 · 88 · 60 · 93 · 75 · 89 |
| **measured accrual, 6 full days** | **80.3/day** (range 60–93) |
| fountain | **alive** — 23 fires/h, last crystallization 08-15 07:13 UTC |
| fire path | **unchanged since R57** (`git log 2e7157e..HEAD` over crystallizer / generator / competing_drives / groove is empty) |

---

## 1. Precondition — a flagged deviation, resolved so neither choice improvises

**The brief specifies ≥700 clean documents. I want to register a problem with 700 and
then make both paths deterministic rather than argue the point.**

700 comes from 2 × (B + W + 100 windows) = 2 × 350. **At 100 windows per half the FPR
estimate moves in steps of 1/100 = 1%, which is exactly the calibration target.** Since
θ is "the smallest even % with FPR ≤ 1%", a **single window** flips θ at n=100. The test
would then be measuring quantisation noise and reporting it as threshold instability —
manufacturing the failure it exists to detect.

**≥150 windows per half ⇒ 2 × (200 + 50 + 150) = 800 documents.**

**Resolution, fixed now, so the outcome is pre-committed under either precondition:**

| run at | PASS (≤4 pp) | FAIL (>4 pp) |
|---|---|---|
| **≥800** *(recommended)* | conclusive → Branch A | conclusive → Branch B |
| **700–799** *(brief's figure)* | **conclusive** — passing despite added quantisation noise is a fortiori | **NOT conclusive** — must be re-run at ≥800 before Branch B is entered |

**This costs nothing to adopt**: at 80.3/day the difference between 700 and 800 is
~1.2 days.

| | |
|---|---|
| shortfall to 700 | 198 docs → **2.5 days** → ~2026-08-17 |
| shortfall to 800 | 298 docs → **3.7 days** → ~2026-08-18/19 |
| at the slow-day rate (60/day) | add ~1 day to each |

**Do not run below 700 under any circumstance.** If the corpus is short on the chosen
day, report "precondition not met" and reschedule — no partial run.

**Conditional on no fire-path change landing meanwhile.** Any change to
`crystallizer.py` / `generator.py` / `competing_drives.py` / `groove.py` resets the clean
window and the schedule slips; the corpus must be single-regime.

## 2. The test — fixed now

1. Split the clean corpus into **two disjoint, time-ordered halves**. No overlap, no
   resampling against a full-corpus reference (the R62 lesson).
2. On **each half independently**, compute the excess series at **B=200, W=50** and
   calibrate **θ = smallest even percentage at which that half's FPR ≤ 1%**.
3. **PASS BAR: |θ_A − θ_B| ≤ 4 percentage points** (two beliefs at N=50).
4. **Supporting, not the bar:** bootstrap θ within each half to report whether an
   observed difference sits inside sampling noise. **The 4 pp bar governs regardless.**

---

## 3. THE DECISION TREE — both branches fixed now

### BRANCH A — halves agree within 4 pp

**Not clear-to-implement. Four gates remain, all fixed now.**

| gate | test | on failure |
|---|---|---|
| **A1** | recompute θ on the **full** clean corpus at the run-day n | — |
| **A2** | recalibrated θ must be **within 4 pp of 22%** | θ drifting with corpus size *is* instability → **route to Branch B** |
| **A3** | Gatwick fires at the **new** θ with the 20% margin | blocked; report and stop |
| **A4** | T_max = p(W+B)/(2θ) ≥ **146 beliefs** at the **new** θ | blocked; report and stop |

**A3 and A4 exist because θ is an input to both.** R66 verified them at θ=22% only. A
*lower* θ raises T_max but shrinks the Gatwick margin; a *higher* θ does the reverse.
**Neither direction is automatically safe.**

**A3 uses the measured (contaminated-baseline) peak excess at the operative B**, not the
clean-baseline value from §4.2 — the measured figure is the smaller one, so it is the
conservative bar. The report must state both.

**If A1–A4 all pass → phase 1**: implement excess at the recalibrated B=200/θ alongside
maxDF\*, maxDF\* deprecated but callable, **both readings recorded for a 14-day parallel
window**. Deletion stays a separate later round.

### BRANCH B — halves disagree by more than 4 pp

**B=200 is dead; the R66 recommendation is withdrawn.**

**B1 — B=400 is NOT tested in the same round.** The brief asks whether it becomes
evaluable at ~700. **Arithmetic, decided now: its *full-corpus calibration* does become
adequate (≥700 − 450 = 250+ windows), but its *disjoint-half stability test* — the thing
that just failed — needs 2 × (400 + 50 + 150) = 1,200 documents.** Running it at 700–800
would repeat exactly the error §1 corrects. **So: calibration yes, stability no, and
stability is the question. It does not get tested in the same round.**

**B2 — record the direction.** R66 measured B=100 at **6 pp**. The mechanism predicts
monotone improvement with B. **If disagreement at B=200 is < 6 pp, the trend supports a
longer baseline and B3 proceeds. If it is ≥ 6 pp, the mechanism is falsified, longer
baselines are not indicated, and the round goes straight to B4.**

**B3 — only if B2 shows improvement:** schedule the B=400 stability test at **1,200
documents (≈ 2026-08-23 → 08-25)** as **its own pre-registered round**, same tree
instantiated at B=400.

**B4 — STOPPING RULE. B=400 is the last candidate.** B=800 needs
2 × (800 + 50 + 150) = **2,000 documents ≈ 25 days** of single-regime corpus. NEX has not
gone 25 days without a fire-path change, and R63 established the register drifts
continuously — a 25-day baseline is an average over regimes, not a baseline. **If B=400
fails, self-referencing excess is abandoned.**

**B5 — what abandonment means.** maxDF\* is **not** resurrected; R65 established a
10.8%-precision alarm is not retainable. The terminal statement would be: **the failure
mode is real, uncovered, and we have no instrument for it.** Written down now so it
cannot later soften into "needs more work".

### Anti-tuning, restated

**The B grid stays {100, 200, 400, 800}.** No other baseline length is evaluated on the
run day. No θ rule other than "smallest even % with FPR ≤ 1%". No adjustment of the
4 pp bar — **4.5 pp is Branch B, not "so close it counts".** If the run brackets a
boundary, a later round pre-registers the finer search **as** a search; it is not
widened in place.

---

## 4. TWO DISCLOSURE CORRECTIONS

### 4.1 The length/blind-spot mechanism was misattributed — CORRECTED

R66's pre-registration said a longer baseline is less blind to slow convergence
*"because the ramp has less time to contaminate it."* **That is the wrong mechanism.**

The derived relation is `T_max = p·(W + B) / (2θ)`. **T_max scales with (W + B): a longer
baseline reaches further back along the ramp, to a point where the token was rarer, so
the difference integrates over a longer span.** The baseline is *not* less contaminated —
§4.2 shows it is thoroughly contaminated — it is averaged over a longer reach that
includes lower values.

**The verdict is unchanged; the stated reason was wrong.** Recorded because
misattributing a mechanism while getting the number right is the exact failure this
series keeps cataloguing.

**And the correction carries a live consequence: W and B enter (W + B) symmetrically.**

| B | θ | T_max at W=50 | T_max at W=100 |
|---|---|---|---|
| 100 | 24% | 106 | 142 |
| 200 | 22% | **193** | 232 |
| 400 | 20% | 382 | 425 |

**Widening the current window buys exactly what widening the baseline buys.** W was held
fixed all series as "maxDF\*'s defined window" — the formula says that was a free
parameter nobody costed. **Not changed now** (anti-tuning; W is also the 2 pp
quantisation unit), but it belongs in the next design round's scope.

### 4.2 The Gatwick baseline was contaminated — MEASURED, margin is safer than reported

The brief asks whether the trailing-B lookback during the replay was clean. **It was
not, at any B:**

| B | peak excess | baseline span | **% of baseline inside contamination** | `societal` DF in baseline | in current window |
|---|---|---|---|---|---|
| 100 | 32.0% | 08-01 03:47 → 08-03 19:21 | **100%** | 2.0% | 34.0% |
| **200** | **30.5%** | 07-29 02:59 → 08-03 17:56 | **100%** | **3.5%** | 34.0% |
| 400 | 32.2% | 07-22 08:00 → 08-03 17:56 | **60%** | 1.8% | 34.0% |

**The baseline already contained the convergence, so every reported excess is
understated.** Against a genuinely clean baseline the excess is the full **34.0%**.

**This also explains the non-monotonic peak (32.0 / 30.5 / 32.2)** the brief flagged: it
is not a property of B, it is how much ramp each lookback happened to absorb. B=200's
baseline caught the most `societal` (3.5%) and therefore showed the lowest excess.

**Consequence for the 20% margin rule:** at B=200 the bar was θ ≤ 0.8 × 30.5% = 24.4%,
passed at 22%. Against the clean-baseline 34.0% the bar is 27.2% — **so the true margin
is wider, and the rule was indeed measuring headroom against a B-dependent transform of
the event.** The conservative (measured) figure is retained as the bar; **both are
disclosed** so the margin is never again mistaken for a clean-detection margin.

---

## 5. §5 BLIND-SPOT DISCLOSURE — drafted now

Locked here so it cannot quietly shrink once the measure ships and the limitation is
inconvenient.

> ### Blind spot — read this before trusting a quiet reading
>
> This measure compares the most recent 50 crystallized beliefs against the 200 that
> preceded them. **A convergence ramping to peak over more than ~2.4 days is invisible at
> B=200** — it builds slowly enough to be absorbed into its own baseline and never
> registers. One building over a week is invisible by a wide margin.
>
> **A quiet reading is evidence of no *fast* convergence. It is not evidence of no
> convergence. Do not cite it as an all-clear.**
>
> The Gatwick contamination of 2026-07/08 ramped in 1.28 days and is detected with
> roughly 1.9× margin — but it sits at the fast end of the detectable range, not the
> middle. Its measured excess (30.5%) understates true sensitivity, because the trailing
> baseline used in that replay was itself inside the contaminated period; against a clean
> baseline the excess is 34.0%.
>
> This blind spot is the deliberate price of removing the register-exclusion list. The
> old maxDF\* had no slow-convergence blind spot but ran at 10.8% precision — 348 of its
> 390 breaches were false, every one driven by NEX's own standing vocabulary. The trade
> is a known blind spot for a usable alarm, made on measurement (r63.md, r64.md, r66.md),
> not preference.

**If the recalibrated θ differs from 22%, recompute the figure as T_max/80.3 days and
update the sentence before pasting. The number is not decorative.**

---

## 6. Scope

Report only. **No stability test run, no θ computed.** No code, no refit, no file edits,
no deletions. `register_exclusion.json`, `GENIUS_FIDELITY_BASELINE.md`,
`corpus_convergence.py` untouched.
