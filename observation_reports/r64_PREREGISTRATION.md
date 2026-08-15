# R64 — PRE-REGISTRATION: persistence-filtered exclusion, designed end to end

**Committed BEFORE any of the three quantities was computed.** Separate commit, no
results. Sixth in the series after `78d6a25`, `2fc6eb2`, `3b6825a`, `985b250`, `b419c39`.

**Written:** 2026-08-14 · **Report-only. Recommendation with exact values; execution is
a later round. No code, no refit, no file edits.**

---

## Why one operation

List size, quantiles and threshold are coupled: a smaller exclusion set leaves more
tokens in contention, which raises every reading, which moves the quantiles, which moves
the threshold. Deriving them separately is how the current defect arose. **All three are
fixed together or none of them is.**

## Corpus — fixed now

Clean post-R29: `beliefs`, `source='fountain_insight'`, `created_at ≥ 2026-08-09`
(n≈482). **Lists are fitted on one half and every evaluation runs on the held-out
half.** No quantity is both fitted and scored on the same documents — the R62 lesson.

## The procedure under test

**Persistence filtering (R63):** the exclusion list is the set of tokens appearing in
the top-40 of **all k disjoint sub-windows** of the fitting half. k=3 gives ~18 terms,
k=4 gives ~13.

---

# 1. Selecting k — the criterion, fixed now

The two failure modes are not symmetric and must be measured separately.

## 1a. UNDER-EXCLUSION — the false-breach mode — PRIMARY

A list too small leaves standing register in contention, and it drives the reading.
**This is the live, observed defect**: maxDF\* reads 30.0% today driven by `item`,
which is register.

**Metric — under-exclusion rate:** over held-out rolling-50 windows, the fraction whose
maxDF\* **driver is itself a persistent token** (would qualify under persistence
filtering on an independent fit). A driver that is standing register means the list
failed at its one job.

Lower is better. Reported per k.

## 1b. OVER-EXCLUSION — the blindness mode — SECONDARY

A list that absorbs a genuinely topical token makes maxDF\* blind to a convergence on
it. **Structurally this should be near-zero for persistence filtering** — a convergence
is time-localized by definition, and the intersection across k disjoint sub-windows
selects against exactly that. **Verified, not assumed:**

**Metric — spike check:** for each listed term, `max sub-window DF / min sub-window DF`.
**A ratio ≥ 3 flags a term as spike-shaped and therefore possibly topical.** Count of
flagged terms reported per k.

**Sensitivity check:** confirm no candidate list contains `societal` — the one
documented real convergence driver (26–34% at 08-04). Any list containing it is
disqualified outright.

## 1c. DECISION RULE for k — fixed now

1. Pick the k with the **lower under-exclusion rate**.
2. **If the two are within 5 percentage points, pick k=3** (the larger, 18-term list).
   Justification fixed in advance: under-exclusion is the demonstrated live failure and
   over-exclusion has **no observed instance in the corpus's history**, so the
   asymmetric risk favours excluding more.
3. Any k whose list contains `societal`, or which has ≥3 spike-flagged terms, is
   disqualified regardless of its under-exclusion rate.

---

# 2. Quantiles and threshold — the rule, fixed now

## 2a. Quantiles

Rolling-50 maxDF\* over the **held-out** half using the chosen list. Report
**median / p90 / p99**, n windows, against R31's published 12 / 18 / 22.

## 2b. Threshold — derived from a principle, not from mimicry

R61 adopted R31's prose rule and **found it does not reconstruct R31's own choice** —
"smallest even % strictly above p99" gives 24% where R31 chose 25% from p99=22%. The
brief for this round says not to inherit unexamined constants, so the threshold is
derived from a **stated design target** instead:

> **PRIMARY RULE: the threshold is the smallest even percentage at which the
> clean-corpus false-breach rate is ≤ 1%.**

Even, because N=50 quantises to 2 pp. ≤1%, because that is the design target R31's
"just above p99" was evidently reaching for, stated directly instead of via a quantile.

**Both alternatives reported alongside:** R61's rule (smallest even > p99) and R31's
arithmetic (p99+3). **If the three disagree, the principled rule governs and the
disagreement is reported, not resolved silently.**

## 2c. Sensitivity floor — a threshold must still fire

**The chosen threshold must remain below 26%**, the low end of the documented
`societal` convergence (26–34%). A threshold that a real past convergence would not
have cleared is not an alarm. **If the ≤1% rule produces a threshold ≥26%, the design
fails on sensitivity** and that is reported as a failure, not patched.

---

# 3. The 33/40 bar — derivation method, fixed now

**33/40 was never a bar.** R31 *observed* that withholding 7 or 14 days retained 33/40
terms and the quantiles were unchanged. A later round promoted that observation to a
threshold. That is the same category error this series has now caught three times
(§5's quantiles, the "1–7 points" headroom, the 1,000-doc floor).

**Term retention was always a proxy. The thing that matters is whether two independent
fits of the same procedure produce the same reading.** So the bar is derived on that
directly:

> **BAR: a list-construction procedure is stable iff the median absolute difference
> between maxDF\*(list A) and maxDF\*(list B), computed over the same held-out windows,
> is ≤ 2 percentage points** — where A and B are independent fits of that procedure on
> disjoint halves.

**2 pp because that is one belief at N=50 — the metric's own resolution.** A
disagreement smaller than the quantisation cannot change any decision the metric feeds.

The round will then report **what term-retention level corresponds to that agreement
bar**, and compare it to 33/40. Three possible findings, all stated in advance as
legitimate:

- retention needed < 82.5% ⇒ **33/40 was too strict**, and the correct bar is the
  measured level;
- retention needed > 82.5% ⇒ **33/40 was too lenient**;
- no clean correspondence ⇒ **term retention is the wrong proxy entirely** and should be
  retired in favour of reading agreement.

---

# 4. HOW THIS ROUND FAILS — fixed now, before any computation

**Persistence filtering does NOT clear the bar if, at BOTH k=3 and k=4, any of:**

- **(a)** median |maxDF\*(A) − maxDF\*(B)| **> 2 pp** — reading agreement not achieved;
- **(b)** under-exclusion rate **≥ 50%** — most drivers are standing register, i.e. the
  list is not doing its job;
- **(c)** no threshold satisfies both the ≤1% false-breach target and the <26%
  sensitivity floor.

**If the design fails, the report says persistence filtering does not clear the bar and
the design question reopens. It does not propose a fourth mechanism in the same
breath.**

## The anti-tuning clause

**k=3 and k=4 were named by R63 before this round. I will test those two and no
others.** If both fail I will **not** test k=2, k=5, a different sub-window count, a
different top-N, or a hybrid in order to find something that passes. Searching over
hyperparameters until one clears is precisely the failure this pre-registration series
exists to prevent, and it would be undetectable in the final report.

Any later round that wants a wider search must pre-register it as a search, with the
multiplicity acknowledged.

---

## Scope

Report only. Recommendation with exact values. **No code, no refit, no file edits** —
`register_exclusion.json`, `GENIUS_FIDELITY_BASELINE.md` and `corpus_convergence.py`
stay untouched. Execution is a later round.
