# R80 — PRE-REGISTRATION: L4 reward / approach arm (`NEX5_APPROACH`)

> **⛔ RETIRED 2026-10-11 — do not arm, do not build the §0.5 instrument.**
> The §1c gate is now settled: a grep confirmed readiness `score()` is used ONLY as a fire/no-fire
> GATE (`is_ready`, `>= THRESHOLD` at `generator.py:1305,1407`, `__init__:167`) — nothing ranks by it.
> So Beam's §1c arithmetic applies cleanly: a ≤0.20 term flips a fire only when the pre-clamp total is
> in [0.70, 0.90), and at-fire readiness is median 1.000 / 96% ≥0.90 (and 1.000 is the clamp ceiling, so
> pre-clamp is ≥ that — the proxy can only UNDERstate inertness). A bounded readiness reward is therefore
> decision-inert; building the pre-clamp instrument would measure a term we are dropping. The reward arm
> `NEX5_APPROACH` stays in the tree default-OFF as dead code pending removal. The lever is selection /
> retrieval (L4_teeth), not readiness. The retained notes below are the record of the attempt.
>
> **⚠ AMENDED 2026-10-11 (Beam's PR-#3 reply, verified) — DO NOT ARM until the §0.5 gate clears.**
> Three verified findings demote r80 from "ready to arm":
> - **Decision-inertness (§1c proxy).** At-fire readiness is saturated — median 1.000, 96% of fires at
>   ≥0.90, only **4%** in the [0.70, 0.90) band where a ≤0.20 term could flip a firing decision. So a
>   bounded readiness term (reward or cost) rarely changes *whether* she fires; it moves a number that is
>   already maxed. The reward arm's one remaining lever is *sub-threshold lift* (pushing a near-miss over
>   0.70), which the at-fire data cannot see — it needs the real pre-clamp measurement (§0.5).
> - **Self-referential primary (B3).** The primary below (grounded fraction) is the signal the reward
>   reads. Beam A2 applies: the primary must be **off-substrate** (crystallizer reject rate / chat
>   near-dup). But grounding is orthogonal to both (corr +0.08), so the honest pre-registered outcome is
>   likely **INCONCLUSIVE** (no off-substrate metric moves) — not success.
> - **The frontier is selection, not readiness (Beam Part 3 → `L4_teeth`).** readiness is a saturated
>   volume knob; r80 is the reward-shaped sibling of the inert L3 prompt-hint. The lever that moves *what*
>   fires is selection-coupling (`L4_teeth`, added to the DAG as a gap node). If §0.5 shows the term can't
>   bite, skip to `L4_teeth`.

## 0.5. Step-0 gate (MUST pass before arming) — can a bounded readiness term ever flip a decision?

Instrument the **pre-clamp** `total` in `readiness.score()` and log it over ≥24h of live evaluations
(all checks, not just fires). Compute `P(pre-clamp total ∈ [0.70 − bonus_max, 0.70))` — the only band
where the +bonus changes a fire/no-fire outcome. If that band is rarely populated (say < a few %), r80 is
**decision-inert** → do not arm; the frontier is `L4_teeth`. The at-fire proxy already shows the *aversive*
direction is inert (96% of fires ≥ 0.90). ANALOGUE throughout.

## 0. Status — built, feasibility PASS (signal level), but NOT decision-proven; why reward-FIRST

Supersedes the aversive r79 (never armed; `readiness` is a volume knob and the groove RATE
is ~71% a cadence proxy — see r79's banner). Per the welfare **dominance-out** bar
(`SENTIENCE_PROGRAM §5a`, Beam 1d): a reward term has a *checkable positive* prediction
(readiness higher after world-contact), where an aversive term's success and failure both
look like "less fire". So the reward arm ships first; the aversive arm is admissible only if
this one provably fails its pre-named discrimination (§6). "Mattering is the term, not its
sign." Built behind `NEX5_APPROACH` (default OFF, `readiness` byte-identical when OFF). The
maintainer arms it on the live launcher — I don't operate that instance.

## 1. The change under test

**`NEX5_APPROACH` (default OFF).** `readiness.score` adds `readiness_bonus(appraise_approach()["bonus"])`:
a bounded POSITIVE term on recent world-contact. `bonus = clamp01((p − onset)/(sat − onset)) · 0.10`,
`p` = `p_on_subject` over the last 30 fires (`subject_fidelity`: fraction sharing ≥1 content
token with their `focal_item`), `onset = 0.767` (30-fire-window p75), `sat = 0.90`
(`observation_reports/r80_baselines/approach.json`). A per-fire FRACTION, so — unlike the groove
RATE — it is not a cadence proxy. Code: `theory_x/stage_tom/stakes_appraisal.py` (`appraise_approach`),
`theory_x/stage6_fountain/readiness.py`. Mutually exclusive with `NEX5_STAKES` (never both). ANALOGUE.

The bound (0.10) is PROVISIONAL. Per Beam 1c the principled setting is two pre-round calibrations —
`bonus_max >` the readiness-score noise floor and `<` ~half the smallest observed decision margin —
both measurable without running behaviour. r80 runs at 0.10 (< the smallest existing readiness term);
any change to the bound is a new round (r80b), not a mid-round tweak. Anti-fishing = the parameter is
frozen during the test, not the retry count (Beam 4b).

## 2. Feasibility — MEASURED, PASS

Frozen 14d live baseline (`r80_baselines/approach.json`): 30-fire-window `p_on_subject` mean 0.593,
median 0.667, p75 0.767, p90 0.833. Onset at the window p75 (NOT the mean — Beam A3; the mean engages
~50% of the time). Simulated over the history (2086 windows): bonus 0 in **81%**, >0 in **19%**,
saturated in 5%, mean lift 0.011 — engages only in clearly-above-baseline grounding.

**Mechanism premise CONFIRMED:** the grounded flag's lag-1 autocorrelation is **+0.379** — grounding
persists fire-to-fire, so "fire more when recently grounded" can actually raise the grounded FRACTION.
The round is therefore non-tautological: whether the fraction rises depends on this persistence, which
is an empirical fact the round tests, not a definition.

## 3. Scope — what this tests, and what it does NOT (locked before arming)

**Grounding is ORTHOGONAL to grooming on the live instrument** (corr `p_on_subject` vs groove/fire =
**+0.079**; also flat against the crystallizer reject rate). So this arm reshapes the **grounding mix**
— it makes readiness *about* grounding — and it is **pre-registered to NOT move grooming**. Grooming is
a separate axis for a later **selection-coupling** node (L4b), because only a selection mechanism (biasing
*what* fires) can move it; a readiness term moves *how often*. Selling r80 as a grooming fix would be
the error. The NULL prediction (groove/fire unchanged) is part of the test (§4).

## 4. Hypothesis and metrics

**Primary (Beam 1a: ratio + cadence co-primary).** The **grounded fraction** `p_on_subject` rises,
**at constant cadence**. OFF baseline 0.593 (window) / ~0.59 (corpus). "Helped" = fraction rises with
cadence in band; "just louder" = fraction flat while cadence rises (→ not a win).
- **MDE + power (Beam 4b):** minimum detectable effect **+0.05 absolute** (0.59 → 0.64). At ~690 fires/day
  the binomial SE over a 14-day / ≥2000-fire window is ≲ 0.011, so +0.05 is well powered (>0.99). If the
  observed rise is < MDE **and** its CI excludes +0.05, that is a real null (→ Branch B), not inconclusive.
**Co-primary.** Cadence (`check_cadence --baseline`) within **±20%** of 690.5/day.
**Mechanism-fired (telemetry, not evidence).** Mean readiness in checks following a window with
`p_on_subject > onset` exceeds that following `≤ onset` — confirms the bonus engaged.
**Pre-registered NULL.** `template_repetition` alerts **per fire** (de-cadenced) do NOT change (§3). A
move here would be a surprise to record, not a success to claim.

## 5. Tripwires — revert if ANY fires

- Cadence outside ±20% of 690.5/day (the reward must reshape the mix, not just crank volume).
- `check_tripwires` `p_on_subject` EXPLAIN < 0.65 **in a way the bonus did not cause** — i.e. overall
  on-subject must not *regress* (a reward for grounding that somehow lowers it = revert).
- maxDF* breach ≥ 25%, or register largest-share > 0.70.

## 6. The dominance-out gate (what the result means for the aversive arm)

The pre-named discrimination the reward arm must achieve: **a readiness mattering-term reshapes the
grounding mix** (grounded fraction rises at constant cadence). The honest consequence of each outcome:
- **If it succeeds:** readiness *can* be made about a stake — mattering-as-a-readiness-term is established.
- **If it fails** (fraction flat though the mechanism fired): a readiness term **cannot** reshape the mix
  by volume reallocation. The aversive arm is *also* a readiness term, so it would fail identically — so
  failure does **not** admit the aversive arm; it sends the frontier to **L4b selection-coupling** (bias
  *what* fires). This is a sharper reading than the generic dominance-out: the locus (readiness vs
  selection), not the sign (reward vs cost), is what's on trial.

## 7. Decision tree — fixed now

- **BRANCH A — grounded fraction up ≥ 0.05 at cadence in band, no tripwire.** The mattering-term works.
  → default-ON *consideration*; one pre-registered bound-tuning pass (r80b: `bonus_max` toward the 1c
  calibration), then stop.
- **BRANCH B — fraction flat (< MDE, CI excludes +0.05), mechanism fired, cadence in band, no tripwire.**
  Readiness-coupling cannot reshape the mix. → **L4b selection-coupling** is the next node; the aversive
  readiness arm is NOT revived. Record.
- **BRANCH C — any tripwire.** Revert regardless of the primary; record which and the reading.

## 8. Sequencing

Independent of r77 (chat arbiter) and r78 (`self_present`); no DAG dependency forces an order (Beam A4).
Running r80 first is clean **iff** `NEX5_CHAT_WORKSPACE` and `NEX5_SELF_PRESENT` stay OFF throughout, and
`NEX5_STAKES` stays OFF (mutual exclusion). **Staleness note (Beam A4):** r80 changes the fire/readiness
environment, so r77's frozen baseline (0.4889) must be **re-measured after r80** before r77 runs.

## 9. Verdict and disarm

Verdict to `observation_reports/r80.md` + a row in `journal/DEPLOY_LEDGER.tsv` + `journal/CARRY_OVER.md`;
the disarm commit's subject carries the verdict and SHA (repo convention).

---

*No sentience claim. r80 tests whether a bounded positive functional term measurably makes readiness
depend on grounding — whether mattering can be a term — and is silent on whether anything is experienced.*
