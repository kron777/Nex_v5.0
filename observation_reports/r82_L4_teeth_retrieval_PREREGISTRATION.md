# R82 — PRE-REGISTRATION: L4_teeth (retrieval), the mechanical fixation shift (`NEX5_RETRIEVAL_TEETH`)

## 0. Status — built, the TRUE teeth (retrieval, not frame)

r81's `NEX5_L4_TEETH` was confirmed frame-only (it demotes a prompt framing line; the body is
fetched independently — grep, Beam C2). This is the mechanical version the L3 note named:
**"retrieval weight shift on fixation, not a prompt hint."** When the fire's seed branch repeats
the previous fire's (fixation), the **credit+carry loop** — the documented groove mechanism that
seeds subsequent fires (`generator.py:177-178`: momentum "I was on X" + hot_observer "branch: X")
— is diverted to a different branch, so different content seeds the next fires. Built behind
`NEX5_RETRIEVAL_TEETH` (default OFF). Arming is the maintainer's step.

## 1. The change under test

**`NEX5_RETRIEVAL_TEETH` (default OFF).** At the branch credit (`generator.py`, after
`_weighted_branch_pick`), `_fixation_teeth(sorted_branches, hot_branch)` reads the previous fire's
recorded seed branch from `recursion_attrib`; if `hot_branch` repeats it (fixation), it diverts to
the next branch with positive `focus_num`. The diverted branch (`_carry_branch`) is passed to
`capture_momentum` and `hot_observer.observe` (the carry), **not** to the recorded `hot_branch`
(`recursion_attrib` / `fountain_events` keep the true branch — so the fixation signal stays honest,
the teeth re-fires while fixation persists, and the L3 teeth-test's `recursion_attrib` is NOT
contaminated). Bounded (one step, real alternative only, on a detected repeat), fail-safe to the
true pick. OFF ⇒ byte-identical.

## 2. Feasibility — WIRED, and this time at RETRIEVAL

- The carry loop is live (`NEX5_MOMENTUM` default-on; `NEX5_HOT_OBSERVER`) and is what "seeds
  subsequent fires" (`:177-178`). So diverting it changes *what content leads later fires*, not a
  framing line — the locus Beam C2/C3 identified.
- Fixation is observable: `recursion_attrib` records each fire's seed branch; `_fixation_teeth`
  reads the last one. The existing teeth-test v2 uses the same table, so the signal is proven live.
- Determinism: on a detected repeat with a positive-focus alternative, the divert fires by
  construction. (How often depends on the live fixation rate — a pre-arm read of consecutive equal
  branches in `recursion_attrib` should confirm it is non-trivial before arming; note here, measure there.)

## 3. Hypothesis and metrics

**Hypothesis.** Breaking branch-fixation in the carry loop **reduces output self-repetition** at
constant cadence. Mechanism: the carry stops re-pulling the fixated branch, so subsequent fires
draw from more varied content, and the output is less template-repetitive.

**Primary (winner-blind, non-definitional — Beam C1).** `template_repetition` alerts **per fire**
(`groove_alerts` / fires, de-cadenced), baseline **~0.187/fire** (14d live). This measures the
OUTPUT's cross-fire bigram repetition — independent of the branch label the teeth forces, so it is
not a definitional function of the manipulation (unlike branch/focal-item coverage). Effect sought:
a **≥ 15% relative drop** at matched cadence.

**Mechanism-fired (confirms the lever engaged, not the primary).** Carried-branch concentration
(HHI over `momentum.branch`, or the divert-rate) falls vs OFF — the teeth actually diversified the
carry. This WILL move by construction; it is the "did it fire", not the "did it help".

**Co-primary (Beam 1a).** Cadence within **±20%** of 690.5/day.

## 4. The falsifier — and the honest alternative it would reveal

If output grooming does **not** drop even though the carry demonstrably diversified (mechanism
fired, cadence in band), then **grooming is phrasing-level, not branch-level** — consistent with the
earlier finding that grounding ⊥ grooming (r80 §3). That falsifies the carry-branch teeth *for
reducing grooming* and points the lever at the phrasing/template layer instead (the crystallizer /
generation prompt), not branch retrieval. Record it; it is a real result, not a null to hide.

## 5. Tripwires — revert if ANY fires
- Cadence outside ±20% of 690.5/day.
- `check_tripwires` `p_on_subject` EXPLAIN reverts < 0.65 (diversifying the carry must not pull her
  off-subject); maxDF* breach ≥ 25%; register largest-share > 0.70.

## 6. Decision tree
- **BRANCH A — groove/fire down ≥ 15% at cadence in band, no tripwire.** The retrieval teeth works —
  the mechanical lever the readiness/frame arms were not. → default-ON consideration; one tuning
  pass (r82b: divert to a focus-weighted roulette pick rather than the single next branch), then stop.
  Promotes L4_teeth toward `built`; green-lights `L4b_persistent_stake` at the same (fetch) locus.
- **BRANCH B — groove/fire flat (< MDE, CI excludes −15%), mechanism fired, cadence in band.**
  Grooming is not branch-driven (§4). → the lever is the phrasing layer, not retrieval; record and
  re-aim.
- **BRANCH C — any tripwire.** Revert; record which and the reading.

## 7. Sequencing
Its own flag; run alone (all other `NEX5_*` prompt/affect/stake/teeth flags OFF, including r81's
`NEX5_L4_TEETH`). `NEX5_MOMENTUM`/`NEX5_HOT_OBSERVER` must stay ON (default) — the teeth is a no-op
if the carry loop is disabled.

## 8. Verdict and disarm
Verdict to `observation_reports/r82.md` + `journal/DEPLOY_LEDGER.tsv` + `journal/CARRY_OVER.md`;
disarm commit subject carries the verdict and SHA.

---

*No sentience claim. r82 tests whether a bounded, mechanical shift in which content the carry loop
seeds on fixation measurably reduces output self-repetition — retrieval, not framing, not
excitability. It is silent on whether anything is experienced.*
