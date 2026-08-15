# R65 — PRE-REGISTRATION: should maxDF\* exist at all?

**Committed BEFORE any consumer trace, replay, or feasibility probe.** Separate commit,
no results. Seventh in the series after `78d6a25`, `2fc6eb2`, `3b6825a`, `985b250`,
`b419c39`, `78ccfe1`.

**Written:** 2026-08-14 · **Report-only. Design recommendation; execution is a later
round. No code, no refit, no file edits.**

---

## The question

R64 established the exclusion-list mechanism has no bottom: no list fitted on past
documents can cover a register drifting at 1.75 terms/day, at any size or construction
method. **So the question is no longer how to build the list. It is whether maxDF\*
should exist in this form at all.**

**"Kill it" is an allowed outcome and is specified below on equal terms with
"replace it".** This round must be able to conclude that the correct action is deletion.

---

# Item 1 — what is maxDF\* for?

## What it was built for — the stated purpose

`GENIUS_FIDELITY_BASELINE.md` §5: every per-fire check scores one row at a time; the
round-27 failure mode is a property of the **corpus**, not of any row — a single story
saturates the exemplar pool, is copied into the next prompt, and scores well again.
maxDF\* exists to detect that.

**So the decision it is supposed to inform is: "has the corpus collapsed onto one
subject, such that intervention is needed?"** Everything below tests whether it does
that, and whether anything still needs it.

## The three measurements — fixed now

### (a) UTILITY — how many decisions has it changed?

Not "how many rounds cited it" (R60 already answered that: |A| = 3 load-bearing) but
**how many decisions came out differently than they would have without the reading.**

Counting rule, fixed now. A reading changed a decision iff removing it would have
changed the round's action — a ship, a revert, a deferral, a gate. **Explicitly
excluded and counted separately:**

- readings that **corroborated** a verdict reached independently on other evidence
- readings used to **explain** an observation without changing an action
- readings that prompted **maintenance of maxDF\* itself** — a metric whose only output
  is its own upkeep has produced nothing

### (b) DETECTION — did it catch the one documented real convergence?

The Gatwick exemplar-pool contamination (fires 2026-07-26→08-07, crystallized beliefs
07-28→08-08) is the only confirmed corpus-level convergence on record, and it is exactly
the failure mode §5 describes.

**Replay maxDF\* daily across that window and ask: did it breach, and was the driver the
contaminant?** `GENIUS_FIDELITY_BASELINE.md` §9.5 asserts *"maxDF\* never saw the
mono-culture"* — **that assertion is four rounds old and gets re-run, not quoted**, per
the standing lesson of this series.

- **Detected** = breached its threshold during the window **with the contaminant as
  driver**.
- **Missed** = no breach, or a breach driven by something else.

### (c) REDUNDANCY — does an existing instrument already cover it?

Candidate incumbents, all already on the fire path with automated consumers:
`groove_alerts` (template/ngram/exact repetition over a rolling belief window),
`crystallization_rejects` reasons `near_duplicate` / `droplet_repetition` /
`semantic_repetition`.

**Covered** = an existing instrument shows a clear signal during the Gatwick window that
its own consumer acted on. R58 already established groove is powerful enough to regulate
crystallization volume, so it is not a toy.

---

# Item 2 — if a convergence signal is still wanted, must it be exclusion-list-based?

The failure is specifically that **a frozen standing register cannot track drift**. Three
candidate families that do not assume stationarity. **Scoping only — no design.**

| candidate | assumption it rests on | how it fails |
|---|---|---|
| **self-referencing baseline** — compare the current window's vocabulary to a trailing window of NEX's own recent output | the trailing window is itself convergence-free | a slow convergence is absorbed into the moving baseline and becomes invisible — the same "refit only on a corpus with no active convergence" trap, now continuous and unfixable |
| **drift-native** — measure the *rate of change* of the vocabulary distribution (e.g. divergence between consecutive windows); convergence shows as anomalously **low** churn | normal operation has a characteristic, stable churn rate | a quiet news period looks identical to a convergence; a fast news cycle masks one |
| **subject-level** — measure concentration over `focal_item`s rather than tokens | focal items are populated and meaningfully distinct | blind to a convergence that expresses in *vocabulary* while subjects stay diverse — which is exactly R59's scaffolding finding |

## Feasibility criterion — fixed now

**A candidate is WORTH A DESIGN ROUND iff all three hold:**

1. it does **not** require a convergence-free reference period (the assumption that
   killed the exclusion list);
2. a cheap probe shows it **would have flagged the Gatwick window**;
3. it has a **plausible automated consumer, or a named human decision it informs** — if
   nothing acts on it, a better instrument is still worthless.

**A candidate is NOT worth a design round if it fails (2), or if its failure mode is the
same class as the one that killed the exclusion list.**

---

# The retirement condition — fixed now, on equal terms

| outcome | condition |
|---|---|
| **RETIRE, NO SUCCESSOR** | (a) it has changed **zero** decisions, **and** (b) it **missed** the Gatwick convergence, **and** (c) an existing instrument **covers** the failure mode. Recommend deleting `corpus_convergence.py`, `register_exclusion.json`, `register_exclusion_v1_contaminated.json`, and §5 of the baseline doc. |
| **DEMOTE TO DIAGNOSTIC** | (a) and (b) hold but (c) fails — the failure mode is real and uncovered, yet no candidate clears the feasibility criterion. Keep the CLI, **delete the threshold and the breach language**, read with judgment, never gate on it. |
| **REPLACE** | the failure mode is live and uncovered **and** ≥1 candidate clears all three feasibility conditions. Name it; design is a later round. |

**If (a) and (b) both hold, "keep maxDF\* as it is" is not an available outcome** — a
metric that has changed no decisions and missed the one event it was built for cannot be
retained unchanged on the grounds that it might help later.

## What would make me wrong about retirement

Stated in advance so it is not rationalised afterwards: **if the replay shows maxDF\*
DID breach on the contaminant during the Gatwick window, item (b) flips, the metric is
vindicated as a detector, and the correct action is to fix its list problem rather than
retire it** — which would send this back to R64's dead end and mean the honest answer is
"we need an instrument we do not know how to build."

## Scope

Report only. **No deletions performed** — this round recommends, a later round executes.
`register_exclusion.json`, `GENIUS_FIDELITY_BASELINE.md`, `corpus_convergence.py`
untouched.
