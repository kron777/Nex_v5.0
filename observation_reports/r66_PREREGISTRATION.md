# R66 — PRE-REGISTRATION: self-referencing excess, designed end to end

**Committed BEFORE any baseline sweep, calibration, or injection test.** Separate commit,
no results. Eighth in the series after `78d6a25`, `2fc6eb2`, `3b6825a`, `985b250`,
`b419c39`, `78ccfe1`, `6c11814`.

**Written:** 2026-08-14 · **Report-only. Recommendation with exact values; execution is a
later round. No code, no refit, no file edits, no deletions.**

---

## The measure

    excess(t) = DF(t, current W) − DF(t, trailing B)
    score     = max over t of excess(t)

**W = 50 is held fixed** — it is maxDF\*'s defined window and the unit the backtest
quantiles and the 2 pp quantisation are expressed in. Varying W is out of scope; a
future round may revisit it, but changing three parameters at once is how the current
mess was made.

**B is the parameter this round derives.** R65 used B=200 as a feasibility probe and
explicitly declined to defend it.

---

# 1. Baseline length B

## The trade, stated as a mechanism

The trailing window defines "already normal". **Too short** and a building convergence
enters its own baseline and cancels itself — the blind spot R65 named. **Too long** and
the baseline reacts slowly and spans regime changes (R29, R57).

**Note the direction is not the naive one:** a *longer* baseline is *less* blind to slow
convergence, because the ramp has less time to contaminate it. The cost of length is
regime-spanning and staleness, not blindness. This round measures both sides.

## Method — fixed now

**(i) Gatwick must still fire.** Hard requirement at every candidate B. Measured on the
real event, per-belief resolution, as R65 established.

**(ii) Blind-spot boundary, by injection.** Synthetic convergence injected into the clean
post-R29 corpus (`created_at ≥ 2026-08-09`, which contains no convergence):

- a token absent from the corpus is injected into documents on a **linear ramp** to peak
  DF **p = 0.34**, matching Gatwick's observed peak;
- ramp duration **T ∈ {50, 100, 200, 400, 800, 1600} beliefs**;
- baseline **B ∈ {100, 200, 400, 800} beliefs**.

**T_max(B) = the longest ramp still detected at B.** Reported in beliefs and converted
to days at the measured accrual rate.

**(iii) Regime-spanning cost.** False-positive rate on the clean corpus at each B — a B
long enough to span R57 (2026-08-12) should show it here.

## SELECTION RULE for B — fixed now

**Choose the largest B whose clean-corpus false-positive rate is ≤ 1%**, subject to
Gatwick firing. Largest, because B buys sensitivity to slow convergence and the only
thing it costs is the FPR budget — so spend the budget.

**Tie-break, in order:** (1) higher T_max; (2) shorter B, as the cheaper and less
regime-spanning option.

**The recommendation must state the blind-spot cost explicitly**: "at the recommended B,
a convergence ramping slower than X days is invisible." Not a footnote — a headline
number.

---

# 2. Threshold calibration

## Method — fixed now

**Calibration corpus: clean post-R29 (`≥ 2026-08-09`), which contains no convergence.**
This is the false-positive reference. The Gatwick window is the *sensitivity* reference
and is never used to set the threshold — that would be fitting on the event.

For each candidate threshold θ (even percentages, since N=50 quantises to 2 pp), report
the clean-corpus FPR, and separately whether Gatwick still fires.

**PRIMARY RULE (same as R64): θ = the smallest even percentage at which the clean-corpus
false-positive rate is ≤ 1%.**

## Sensitivity margin — fixed now

**θ must be ≤ 0.8 × the observed Gatwick peak excess** at the chosen B. A threshold
sitting just under the one real event it must catch is a knife-edge, not a calibration.
**20% headroom is required, not preferred.**

## Rule-reconstruction check — required, per R61/R64

R61 found R31's stated rule does not reconstruct R31's own choice. **The same check runs
here:** does the ≤1% rule, applied to maxDF\*'s historical readings, reconstruct its 25%
threshold? **If it does not, that is reported as a limitation of the rule, not
explained away** — and it weakens the rule's authority for this design too.

## Threshold stability — fixed now

Calibrate independently on **two disjoint halves** of the clean corpus. **The two
calibrated thresholds must agree within 4 pp (two beliefs at N=50).** Wider disagreement
means the threshold is a property of the sample, not of the system.

---

# 3. Fate of the frozen list, and of maxDF\* itself

Determined, not assumed:

1. **Re-verify** (not cite — R62's finding is four rounds old) what reads
   `register_exclusion.json`, `corpus_convergence.py`, and `max_df_star`.
2. **State exactly what the replacement makes obsolete** — file by file, symbol by
   symbol.
3. **Parallel-run recommendation.** Since neither path has an automated consumer, "cut
   over" costs almost nothing and "keep both" costs almost nothing. The recommendation
   must nonetheless name a **concrete validation window and a concrete exit criterion**,
   not "run both for a while".

**Pre-registered default, to be overridden only on evidence:** keep the old path **inert
but present** for a **14-day validation window**, recording both readings; delete only
after the new measure has produced **zero unexplained fires** over that window. Deletion
is a later round regardless — **this round deletes nothing.**

---

# 4. HOW THIS ROUND FAILS — fixed now

**Self-referencing excess is NOT worth shipping if any of:**

- **(a)** no B in the pre-declared grid achieves clean FPR ≤ 1% while firing on Gatwick
  with the required 20% margin;
- **(b)** **T_max at the chosen B is less than 2× the measured Gatwick ramp duration** —
  meaning the measure only detects events at least as fast as the single one it was
  validated on. That is not a detector, it is a memory of one event;
- **(c)** the two disjoint-half thresholds disagree by more than 4 pp — threshold
  instability.

**If it fails, the report says self-referencing excess is not worth shipping and
maxDF\*'s replacement is unsolved.** It does not propose a fourth measure in the same
breath, and it does not fall back to "keep maxDF\* as is" — R65 already established
that a 10.8%-precision alarm is not retainable.

## Anti-tuning clause

**The grids above — B ∈ {100, 200, 400, 800}, T ∈ {50…1600}, θ even percentages — are
fixed now and will not be widened to find a pass.** In particular I will not try
B=300 or B=150 because 200 and 400 straddled a bar. If the grid brackets a boundary,
the report says so and a later round pre-registers the finer search as a search.

**Nor will I re-tune p.** p=0.34 is Gatwick's measured peak; injecting a larger p to
make detection easier would be tuning the test rather than the design.

## Scope

Report only. Recommendation with exact values. **No code, no refit, no file edits, no
deletions.** `register_exclusion.json`, `GENIUS_FIDELITY_BASELINE.md`,
`corpus_convergence.py` all untouched. Execution is a later round.
