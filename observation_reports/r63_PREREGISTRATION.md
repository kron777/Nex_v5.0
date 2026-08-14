# R63 — PRE-REGISTRATION: is the register drift a trend or punctuated?

**Committed BEFORE any drift statistic was computed.** Separate commit, no results.
Fifth in the series after `78d6a25`, `2fc6eb2`, `3b6825a`, `985b250`.

**Written:** 2026-08-14 · **Report-only. No code, no refit, no file edits.**

---

## The question, and why the answer changes the fix

R62 measured a drift gap: time-ordered splits 24–27/40 against random splits at matched
n of ~29–31. Random splits measure sampling noise; time-ordered measure noise **plus**
drift. Two mechanisms produce that gap and they need different fixes:

| | mechanism | fix |
|---|---|---|
| **TREND** | vocabulary turns over steadily; every day the register is slightly different | **decaying-weight fit** — recent documents weighted higher |
| **PUNCTUATED** | long stable stretches separated by a few discrete shifts | **shorter window + refit cadence** — fit inside a stretch, refit when one ends |

The wrong fix is worse than no fix: a decaying-weight fit applied to punctuated drift
smears across boundaries; a short-window cadence applied to trend drift refits
constantly and never stabilises.

## The discriminator — fixed now

For disjoint windows `Wi`, `Wj` of **equal, fixed size**:

    R(i,j)  = |top40(Wi) ∩ top40(Wj)|          (retention)
    Δt(i,j) = gap between window midpoints      (lag, in days)

**Window size must be held constant across all comparisons.** Retention rises with
window size mechanically, so mixing sizes would confound lag with n. All pairs must be
**disjoint** — the R62 lesson; overlapping windows self-score.

**Model A — TREND** predicts R declines smoothly and monotonically with Δt. Signature:
strong negative rank correlation between R and Δt, with unstructured residuals.

**Model B — PUNCTUATED** predicts R depends on *whether a boundary falls between* the
windows, not on how far apart they are. Signature: R is bimodal; within-stretch pairs
score high even at large lag; a change-point partition explains variance that lag alone
does not.

### Primary statistics

1. **Spearman ρ(R, Δt)** with p-value — the trend signature.
2. **ΔR² = R²(best single change-point model) − R²(linear-in-lag model)** — the
   punctuation signature, i.e. how much a discrete boundary buys over a smooth decay.

### DECISION RULE — fixed now

| | condition |
|---|---|
| **TREND** | \|ρ\| ≥ 0.5 with p < 0.05, **and** ΔR² < 0.15 |
| **PUNCTUATED** | ΔR² ≥ 0.15, **and** (\|ρ\| < 0.5 **or** the change-point model dominates on adjusted R²) |
| **MIXED** | both sets of conditions fire |
| **NOISE-DOMINATED** | \|ρ\| < 0.3 **and** ΔR² < 0.15 — the gap is not systematically structured, and R62's drift reading is mostly small-sample noise |

**NOISE-DOMINATED is a real possible outcome and I am naming it in advance**, because it
would mean R62 over-read its own finding. It must not be reported as "inconclusive"
if it fires — it is a substantive result.

## POWER FLOOR — fixed now

The clean corpus is 5.9 days. **If there are fewer than 15 disjoint pairs at the chosen
window size, or fewer than 3 distinct lag values, the verdict is INDETERMINATE BY POWER**
regardless of the statistics, and the round reports what corpus length would resolve it.
R58's primary was underpowered and unchecked; that does not repeat.

## Boundary validation — a secondary check with known answers

Three regime boundaries are documented and dated: **R29 (2026-08-03)**, **contamination
end (2026-08-08)**, **R57 (2026-08-12)**. On an extended history that spans them, a
punctuated process should show retention dips **at these specific dates**. This runs on
contamination-affected data and is therefore **secondary and clearly labelled** — it can
corroborate a punctuation verdict but cannot establish one, since contamination is
itself a convergence event that would manufacture a boundary.

## The reading that says "try plain n=1,000 first" — fixed now

Retention rises with window size. The question is whether it rises **enough**, by
W = 500 (each half of a 1,000-document corpus), to clear 33/40 with margin.

Measure `R(W)` at W = 60, 80, 100, 120, 160, 200 over disjoint pairs at matched lag, fit
an asymptotic curve, project to W = 500, and report the **drift penalty** = (random-split
retention − time-ordered retention) at matched W.

| verdict | condition | meaning |
|---|---|---|
| **GREEN — try n=1,000 first** | projected R(500) **≥ 35/40** *and* drift penalty **< 3 points** | count is the binding constraint after all; Aug 21 is worth attempting before any method change |
| **AMBER — borderline** | projected 33–35, *or* penalty 3–5 | R62's coin-flip stands; attempt it but pre-commit to the gate |
| **RED — n will not fix it** | projected **< 33**, *or* penalty **≥ 5** with the curve plateauing | method change needed before any refit; Aug 21 is not a date |

**The 35/40 bar for GREEN is deliberately 2 points above the 33/40 ship bar**, because a
projection that lands exactly on the bar is a coin-flip, which is the thing R62 already
identified and which this round exists to resolve.

## Scope

Report only. No code, no refit. `register_exclusion.json`,
`GENIUS_FIDELITY_BASELINE.md` and `corpus_convergence.py` untouched. This round
recommends a method; it does not implement one.
