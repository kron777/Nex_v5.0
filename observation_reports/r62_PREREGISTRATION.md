# R62 — PRE-REGISTRATION: ship/no-ship criterion for the register list alone

**Committed BEFORE any check was run.** Separate commit, no results. Fourth in the
series after `78d6a25` (R59), `2fc6eb2` (R60), `3b6825a` (R61).

**Written:** 2026-08-14 · **Report-only. No code, no refit. "Ship" here means a
RECOMMENDATION with the exact change specified — this round does not perform it.**

---

## The question

R61 found the ~1,000-doc floor gates the **quantiles**, not the **list**. Can the
register-list refit ship now on retention evidence, with quantile re-derivation
deferred to ~Aug 21?

## What I am deliberately NOT reusing

R50 §A.3 established that `corpus_convergence.py` is imported by nothing and
`register_exclusion.json` has exactly one reader. **That claim is four rounds old and
is a derived property of a codebase that has changed since** (R53's `retrieval.py`,
R57's `crystallizer.py`). Per R61's own finding, citing it unverified is the exact
failure mode this series just documented. **It gets re-run, not quoted.**

Likewise R61's own retention figure (34/40) was measured **fit-vs-full-corpus**, which
inflates because the resamples share documents with the reference. **This round
replaces it with a stricter test I am fixing now, before running it.**

## PRIMARY CRITERION — list stability, half-vs-half

Not fit-vs-full. **Two disjoint halves, each fitted independently, compared to each
other:**

    retention = |top40(A) ∩ top40(B)|   for disjoint A, B

evaluated under **three partition schemes**, all fixed now:

1. **time-ordered** — first half vs second half (tests temporal drift in the register)
2. **odd/even by document index** (removes time, keeps sample size)
3. **5 random disjoint partitions**, seed 62

**SHIP requires the MINIMUM retention across all 7 splits to be ≥ 33/40** — R31's own
stability bar, applied to a stricter test than R31 used.

This is deliberately harder than R61's 34/40. Each half is n≈240, so if halves at 240
agree, a fit at 481 versus one at 1,000 should agree at least as well — **REASONED,
and labelled as such in the report.**

## SECONDARY CRITERION — isolation (re-verified, not cited)

    grep -rn "corpus_convergence|register_exclusion|max_df_star" over all .py

**SHIP requires: zero executable readers outside `corpus_convergence.py` itself, and
zero importers of `corpus_convergence`.** Any live import, any fire-path reference, any
scheduled/cron caller ⇒ **NO SHIP**, because the change would then alter runtime
behaviour rather than what a CLI prints.

## TERTIARY CRITERION — no live reading moves

**SHIP requires that shipping the list changes no value consumed by any automated
path.** If the secondary criterion holds this is implied, but it is stated separately
because they can come apart — a JSON read at import time by something that *is*
imported would satisfy neither.

## QUATERNARY CRITERION — reversibility

**SHIP requires** the R31/R50 pattern be preservable: superseded file kept
byte-identical alongside, one-file revert, provenance fields (`fitted_on`, `corpus`,
`n_documents`, `method`) populated for the new fit.

## DECISION RULE — fixed now

| | |
|---|---|
| **SHIP** | all four criteria pass |
| **NO SHIP** | **any single** criterion fails |

No partial ship, no "ship with caveats" — a criterion that can be waived is not a
criterion. If the answer is SHIP, the recommendation must additionally carry the
interim guard below, or it converts to NO SHIP.

## THE INTERIM GUARD — a required component of any SHIP recommendation

Shipping the list while the quantiles stay stale creates one specific hazard: someone
reads "the refit landed" as "maxDF\* is trustworthy again" and compares a post-refit
reading against R31's 12 / 18 / 22 / 25 band.

**Any SHIP recommendation must therefore specify (a) that the do-not-consult order from
R59/R60 REMAINS IN FORCE, and (b) that the ship commit itself states the quantiles are
not yet refit.** I will quantify the size of the mis-location in the report rather than
assert it is small.

## What I will report regardless of the verdict

1. **Exactly what each deliverable needs** — list vs quantiles, separated.
2. **What breaks in the interim** — measured, not asserted.
3. **Whether any live reading moves** — the tertiary criterion, answered with evidence.
4. A caveat I already expect and am naming in advance so it cannot be presented as a
   discovery: **the clean corpus is short in TIME even when adequate in COUNT.** At the
   1,000-doc floor it will span ~12 days against R31's 45. Count adequacy and window
   adequacy are not the same thing, and the quantile deferral does not fix it.

## Scope

Report only. No code, no refit, no file edits. `register_exclusion.json`,
`GENIUS_FIDELITY_BASELINE.md` and `corpus_convergence.py` all untouched.
