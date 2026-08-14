# R60 — PRE-REGISTRATION: maxDF\* exposure audit

**Committed BEFORE any round was classified or counted.** Separate commit, no results
in it, so `git log` verifies the threshold predates the finding. Same discipline as
`78d6a25` (R59).

**Written:** 2026-08-14 · **Report-only audit. No code, no refit, nothing written.**

---

## The question

R59 established that `register_exclusion.json` is ~75% stale (10 of 38 terms still in
a live top-40) and that maxDF\* is currently reading a **false breach** (30.0%, over
its 25% threshold, all five drivers being staleness misses). R52 §D wired maxDF\* as a
revert tripwire.

**Has any prior round's verdict leaned on a maxDF\* reading while the list was already
stale?**

## Prior knowledge — declared, because I am not blind here

Incidental greps during R58/R59 already surfaced maxDF\* mentions at `r39:197`,
`r40:154`, `r44:204`, `r51:212`, `r53:24`, `r53:26`, `r54:73`, and
`GENIUS_FIDELITY_BASELINE.md` §9.3/§9.5. **I have read those lines. I have not
classified, counted, or assessed flip-risk for any of them.** The thresholds below are
fixed without that work. Declaring this because a pre-registration that pretends to
blindness it doesn't have is worse than none.

## Audit window — the list's entire life

`register_exclusion.json` was fitted **2026-08-04** (round 31) on a 45-day window
`2026-06-20 → 2026-08-04`. R29 landed **2026-08-03** and tripled crystallized-belief
length (9.6 → 27.7 content tokens/doc). **So ~44 of the 45 fitting days are pre-R29:
the list was born stale and applied immediately to post-R29 corpora.** R39 §197 saw
this at the time.

There is therefore no "clean early period" to bound the audit — **the window is
2026-08-04 → now, the whole life of the list.**

**Denominator: 24 round reports** — r34, r36–r56, r58, r59 (no r35; R57 was
commit-only) — plus `GENIUS_FIDELITY_BASELINE.md` and `journal/DEPLOY_LEDGER.tsv`.

## Classification, fixed now

Each round is exactly one of:

| | |
|---|---|
| **A — LOAD-BEARING** | the round's verdict, ship/revert/keep decision, or a pre-registered tripwire outcome depended on a maxDF\* **reading** (an actual number). Remove the reading and the verdict changes or loses its stated support. |
| **B — SUPPORTING** | a maxDF\* reading is cited as corroboration, but the verdict has independent stated grounds that survive without it. |
| **C — META-ONLY** | the round discusses maxDF\*'s trustworthiness, its register list, or the refit schedule, but consults **no reading**. **This is not exposure — it is the system catching itself.** |
| **—** | no maxDF\* content at all. |

## The directional asymmetry — stated before measurement

Staleness means current-register tokens are **not** excluded, so they surface as
drivers and **maxDF\* reads too HIGH**. Correcting the list can only move a reading
**down**. Therefore:

- a reading **at or above** threshold, used to conclude breach / revert / block
  → **FLIP RISK** (correction may move it below);
- a reading **below** threshold, used to conclude no-breach / safe-to-ship
  → **CONSERVATIVE, NOT flip risk** (correction moves it further below, strengthening
  the conclusion the round already drew).

**The one channel that could break this asymmetry** is a false *negative*: a term
sitting **in** the 38-term list that is genuinely topical and high-DF in the live
corpus would be wrongly excluded and could hide a real convergence. R50 audited this
channel and removed `changes` / `systems` for exactly that reason. **I will re-check
it against the live corpus.** If no current list term is a live high-DF topical token,
the channel is closed and the asymmetry holds absolutely. If one is, the asymmetry is
void and every below-threshold reading also becomes flip-risk — which would push the
verdict toward corpus-wide by construction.

## PRIMARY EXPOSURE METRIC

    |A_flip|  =  rounds that are BOTH load-bearing (A) AND flip-risk

## THRESHOLD — fixed before counting

| | verdict | action |
|---|---|---|
| **\|A_flip\| = 0** | **CONTAINED** | record in the ledger; **no re-reads**. Justified only because the directional asymmetry means every other use was conservative. |
| **\|A_flip\| ∈ {1, 2}** | **LOCALISED** | name those rounds; re-read exactly those when the refit lands. Nothing else. |
| **\|A_flip\| ≥ 3**, **or** \|A\| ≥ 5 with flip-risk undetermined for ≥3 | **CORPUS-WIDE CONTAMINATION** | every post-08-04 verdict citing maxDF\* is re-read after the refit, **and** `GENIUS_FIDELITY_BASELINE.md` §5/§9 baselines are re-derived, since they are themselves stale-list readings. |

**Rationale for 0 / 1–2 / 3.** The asymmetry means most uses are self-protecting, so a
nonzero count is only meaningful if a reading actually crossed a decision boundary in
the wrong direction. One or two such rounds is a bounded, nameable re-read list. Three
or more means the metric was routinely load-bearing in the direction it is broken, and
spot-fixing would leave an unknown remainder — at that point the cheaper honest move is
to distrust the whole class.

## COMPLETENESS FLOOR

Coverage must be total: all 24 reports + `GENIUS_FIDELITY_BASELINE.md` + the ledger,
searched case-insensitively for `maxdf`, `max_df`, `corpus_convergence`,
`register_exclusion`, and `convergence`. **Any round whose classification cannot be
determined from its own text counts as UNDETERMINED and rolls into the `|A| ≥ 5`
clause** — it is never silently dropped. A partial audit reports as
CORPUS-WIDE by default, not as CONTAINED.

## Scope

Report only. No code changes. No refit — the refit stays blocked on its own
prerequisite (477/1,000 clean docs, ETA ~2026-08-21). This round reads reports and
recomputes readings for comparison; it writes nothing but its own report and a ledger
line.
