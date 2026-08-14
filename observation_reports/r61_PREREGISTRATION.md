# R61 — PRE-REGISTRATION: corrected maxDF\* baseline, and the citation-chain sweep

**Committed BEFORE any quantile or chain count was computed.** Separate commit, no
results. Third in the series after `78d6a25` (R59) and `2fc6eb2` (R60).

**Written:** 2026-08-14 · **Report-only. No code, no refit, no edit to `GENIUS_FIDELITY_BASELINE.md`.**

---

# Item 1 — corrected §5 backtest quantiles and threshold

## Why a pre-registration for a derivation

This is a derivation, not a hypothesis test, so it cannot "fail". But the **threshold
rule is a choice**, and choosing it after seeing the quantiles would let me tune the
alarm to a comfortable place. **R31's published rule is therefore adopted verbatim,
now, before the numbers exist:**

> *"The threshold sits just above the observed p99 and is deliberately coarse: at N=50
> one belief is 2 percentage points, so anything finer is quantisation noise."*
> — `GENIUS_FIDELITY_BASELINE.md` §5

**Operationalised, fixed now:** `threshold = smallest even percentage strictly greater
than the observed p99`. Even, because N=50 quantises to 2 pp. No other rule will be
substituted, and if the result looks uncomfortable it gets reported as-is.

## Corpus — fixed now

**Clean post-R29 only**: `beliefs` where `source='fountain_insight'` and
`created_at ≥ 2026-08-09`. This is R53's clean-window definition — contamination ran to
2026-08-08 for crystallized beliefs (R49 §A.1), and R29 landed 2026-08-03, so this is
the only window that is both post-R29 and uncontaminated.

**Known limitation, stated now:** this corpus is ~480 docs against R50's ~1,000-doc
bootstrap floor for a stable 40-term fit. **Every number produced here is PROVISIONAL
and must be recomputed at the refit.** The deliverable is a prepared replacement plus
its sensitivity, not a final answer.

## Method — fixed now

1. Fit a provisional register list: **top-40 by DF** on the clean corpus, per §5's
   stated method (same `_fidelity_tokens()`, imported not re-declared).
2. Replay maxDF\* over **rolling 50 most recent crystallized beliefs**, stepped one
   belief at a time across the clean corpus — the same construction as R31's 1,054
   windows.
3. Report **median / p90 / p99**, plus n windows, alongside R31's 12 / 18 / 22.
4. Apply the frozen threshold rule above.
5. **Stability check, mirroring R31:** withhold the last 7 and 14 days, refit, report
   term retention (R31's bar was 33/40) and whether the quantiles move.

## The regime check I am committing to run — R36's lesson

The clean corpus **spans R57** (2026-08-12), which raised `_TOO_LONG_ON_SUBJECT`
600→750 and admitted a band of longer documents. **maxDF\* counts document frequency,
and longer documents mechanically raise every token's DF** — this is precisely the
artefact R36 §C3 measured at R29 (30–55% of that step).

**So I will measure mean content tokens/doc either side of R57 within the clean window
before reporting any quantile.** If it has moved materially, the corpus spans two
length regimes and I will report the segments separately rather than pooling them.
Pooling across a length regime change is the exact error R36 caught R31–R32 making.

---

# Item 2 — is stale propagation a pattern?

## Definitions — fixed now

| | |
|---|---|
| **eligible figure** | a number measured from **live system state** (corpus properties, rates, DB counts, gate outcomes) whose true value **can drift**. |
| **excluded** | fixed facts — code constants, commit values, dates, thresholds-as-specified. Re-measuring `600` or "R29 landed 08-03" is meaningless, and counting them would inflate the result with non-risks. |
| **citation** | a later round restates the figure with attribution to an earlier round (`R50 found`, `per R31`, `R36 §C3`, `R53's`) rather than presenting a fresh measurement. |
| **chain length** | number of **distinct rounds** in which the figure appears — originating round + citers. |
| **re-measurement** | any round in the chain recomputes the figure and states a fresh value, **even if unchanged**. |

## Detection method — fixed now, so the sweep is auditable rather than cherry-picked

Systematic, not impressionistic: extract every line across the 24 reports that contains
**both** a numeric figure **and** an attribution marker (`R\d+`, `round \d+`, `§`),
group candidates by figure identity, then hand-verify chain length and re-measurement
status for each. **Candidates are enumerated before filtering, and the enumeration
count is reported** so the reader can see what was considered, not just what survived.

## STALE-PROPAGATION RISK — the per-chain criterion

A chain qualifies iff **all three** hold:

1. chain length **≥ 3 distinct rounds** (originator + ≥2 citers), **and**
2. **zero** re-measurement anywhere in the chain, **and**
3. the figure is **load-bearing** in at least one citing round — it supports a verdict,
   a gate, a schedule, or a ship/defer decision.

Chain length ≤2, or any chain containing a re-measurement, is **normal reference** and
is not a finding. Requiring (3) keeps recap and bookkeeping out of the count.

## VERDICT THRESHOLD — count of qualifying chains, EXCLUDING the known maxDF\* one

The maxDF\* headroom chain (R50 → R52 → R53, "1–7 points", re-measured at R60 as 14)
is the known instance and is **not** counted toward the total — the question is whether
it has company.

| additional qualifying chains | verdict |
|---|---|
| **≤ 1** | **ONE-INSTRUMENT PROBLEM.** Contained. Name it, no process change. |
| **2 – 3** | **EMERGING PATTERN.** Name each; recommend a targeted note, not a rule. |
| **≥ 4** | **SYSTEMIC.** A process rule is warranted — mandatory re-measurement of load-bearing cited figures, or explicit `unverified carry-over` marking. |

**Rationale.** One more instance is coincidence given 24 rounds and a shared author;
two or three is a habit worth naming; four or more means the corpus routinely argues
from unrefreshed numbers and the fix belongs in the protocol rather than in individual
rounds.

## COMPLETENESS FLOOR

The sweep must cover all 24 reports. **Any candidate chain whose re-measurement status
cannot be determined from the reports counts as QUALIFYING** (conservative direction —
it inflates toward "systemic"), and is reported as undetermined rather than dropped.

## Scope

Report only. No code changes. No refit. **`GENIUS_FIDELITY_BASELINE.md` is NOT edited**
— item 1 produces proposed values for the refit round to apply, per the brief.
