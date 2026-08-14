# R59 — PRE-REGISTRATION: groove cooldown ∩ register staleness

**Committed BEFORE any overlap number was computed.** This file exists as a separate
commit specifically so `git log` proves the threshold predates the measurement. R58's
fidelity tripwire failed because it was defined after the fact and could only return
"pass"; this is the corrective.

**Written:** 2026-08-14 · **Report-only round. No code changes, no fire-path change.**

---

## The claim under test

R58 §C3 observed that groove is writing cooldowns on `item aligns` / `item discusses`,
and that `aligns` (DF 0.1342) / `discusses` (DF 0.1613) are precisely the two tokens
`register_exclusion.json`'s own header names as its unfixed staleness defect. The
hypothesis: **groove's cooldown and the register staleness are one problem seen from
two ends — NEX generates formulaic scaffolding, groove blocks it, and maxDF\* is blind
to it.**

n=2 anecdote. This round asks whether it generalises.

## What has NOT been looked at

At the time of this commit I have read: `register_exclusion.json`'s term list and
provenance, `corpus_convergence.py`'s tokenizer and window, `groove.py`'s
`_push_cooldown` / `_is_meaningful_fragment`, and the schemas of `groove_alerts` /
`signal_cooldown`. **I have not computed any intersection, any DF over the live
corpus, or any count of distinct cooled fragments.**

## Definitions, fixed now

Tokenisation is `_fidelity_tokens()` **imported from `crystallizer.py`** for every set
below — same single definition maxDF\* uses (`GENIUS_FIDELITY_BASELINE.md` §1). No
re-declaration.

| set | definition |
|---|---|
| **G** | content tokens appearing in `signal_cooldown.content` rows with `created_at ≥ 2026-08-12 00:08:03 UTC`. **Primary source is `signal_cooldown`, not `groove_alerts`** — these are the fragments that actually blocked a crystallization, i.e. the ones that caused R58's absorption. `groove_alerts.pattern` over the same window is reported as a secondary/robustness set only. |
| **G_content** | G restricted to tokens that appear in the live corpus at all (a cooled token absent from the corpus cannot be a register miss) |
| **C** | live corpus = `beliefs` where `source='fountain_insight'` and `created_at ≥ R57` (2026-08-12 00:08:03 UTC) — matches the groove window exactly |
| **R** | the 38 terms in `register_exclusion.json` v2 |
| **S** | **staleness-miss set**: tokens that would enter a top-40-by-DF refit on **C** but are **not** in **R**. This is literally "what a refit would add", so it needs no arbitrary DF floor. |
| **V_hi** | all tokens in C at DF ≥ the DF of the weakest member of the top-40 refit (the same band S is drawn from) |

## PRIMARY METRIC

    overlap = |G_content ∩ S| / |G_content|

*"What share of what groove actually cooled down is register scaffolding the list
should have excluded but doesn't."*

## The confound this must survive

**Both sets are selected for high frequency.** groove cools repeated fragments; the
register list is top-DF. They will overlap somewhat *by construction*. A chance
baseline over the whole vocabulary would be anti-conservative and would manufacture a
positive.

So the primary is paired with a **frequency-matched enrichment**:

    enrichment = P(token ∈ S | token ∈ G_content) / P(token ∈ S | token ∈ V_hi \ G_content)

i.e. among tokens in the same high-DF band, are the ones groove cooled
*disproportionately* the ones the list misses? Significance by Fisher exact on the
2×2 (in G / not in G) × (in S / in R).

**Reverse direction**, reported alongside: `|G_content ∩ S| / |S|` — what share of the
refit's additions groove independently flagged.

## KILL CONDITION — fixed before measurement

| primary overlap | enrichment | Fisher p | **verdict** |
|---|---|---|---|
| **≥ 50%** | **≥ 2.0×** | **< 0.05** | **ONE problem.** Next dev targets the shared upstream cause — why the generator emits the scaffolding at all. Cooldown knob is NOT the target. |
| **< 30%** | — | — | **TWO problems.** R59 cooldown-tuning is back on the table. |
| 30–50%, **or** enrichment 1.0–2.0×, **or** p ≥ 0.05 | | | **INDETERMINATE.** No tuning in either direction. Report as underpowered and say what would resolve it. |

All three "ONE problem" conditions must hold jointly. Any single failure among them
drops the verdict to INDETERMINATE at best.

**Rationale for 50%:** if a majority of what groove blocks is register the list should
have caught, one upstream fix addresses both symptoms. **Rationale for 30%:** below
that, groove is predominantly doing its actual job — catching genuine topical
convergence, which is what maxDF\* is *supposed* to see as signal, not exclude —
and the two are separable. **Rationale for 2.0×:** both sets are high-frequency
selected, so the association must be at least twice what that shared selection alone
produces.

## POWER FLOOR — also fixed now

R58's primary was underpowered and nobody had checked before pre-registering it. So:

**If `|G_content| < 20` or `|S| < 10`, the verdict is INDETERMINATE BY POWER
regardless of what the ratios say**, and the round reports the n required rather than
a conclusion. A 2×2 with a single-digit cell cannot support a 2.0× enrichment claim.

## Independence check (the R58 lesson)

G is derived from `signal_cooldown` — written by `groove.py`, a template-repetition
detector over a 20-belief window. S is derived from document frequency over the
crystallized corpus against a list fitted in round 31. **Different code paths,
different inputs, different fitting procedures, neither derived from the other.** The
one shared component is the tokenizer, which is shared deliberately and cannot induce
overlap: it defines the vocabulary for both sets, it does not select within it.

## Scope

Report only. No code changes. No refit — the register refit remains blocked on its
own prerequisite (477/1,000 clean docs, ETA ~2026-08-21, per r58.md §C2); this round
*simulates* what a refit would add in order to define S, and writes nothing.
