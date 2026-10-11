# R84 — PRE-REGISTRATION: does the global-workspace arbiter earn its keep? (`NEX5_GW_LOG`)

> **STATUS 2026-10-12 — OBSERVATIONAL EXPOSURE BUILD. No lever. Dark-by-default; arming+deploy is the
> operator's.** This round does not change a fire. It builds the missing EXPOSURE so the arbiter can be
> measured at all, then reads it. It is the arbiter sibling of the G3 voice instrument and of Phase-1 for
> `self_state_history`: you cannot pre-screen what isn't recorded.

## Why this round exists (the H-series conclusion, verified)

The L4 "break the groove" hunt established, by measurement, that the global-workspace arbiter
(`theory_x/stage_tom/global_workspace.arbitrate`) sits at a **prompt-only locus**: it surveys ~2–5
candidates (surprise / momentum / bonsai / stakes / drive), picks the max-salience one, and prepends a
single **framing line** to `focus_block` (`generator.py:3121`). Crucially the belief **fetch**
(`:3057`) completes and is **fixed before** the arbiter runs (`:3115`), so the winner changes the lead
*instruction*, never the retrieved material. Beam's proposed "decision-to-content coupling" is therefore
a fire-path **reorder**, ruled out a priori (it would make the arbiter a content filter and destroy the
G3 voice instrument by construction — predicate-4 definitional coupling).

What was **never measured** is whether the arbiter *earns its keep*: how often it overrides its routine
bonsai baseline instead of rubber-stamping it. It couldn't be measured — the decision is written
nowhere (`git grep` arbiter_decisions → 0). This round fixes that, and nothing else.

## What is built (this branch)

- **`NEX5_GW_LOG` (default OFF, fail-safe)** in `global_workspace.arbitrate`: appends one JSON line per
  fire to `arbiter_decisions.jsonl`, a **lock-free sibling of the dynamic DB** — deliberately NOT the
  one-pen substrate, so it never contends with the single writer or stalls a fire. OFF ⇒ no file is
  written and `arbitrate()` is **byte-identical** (verified: `tests/test_arbiter_competition.py`,
  end-to-end tmp-dir run shows `line_on == line_off`). Record: `ts` + the full candidate VECTOR
  `[{kind, salience}]` + `winner_kind`. The vector (not just the winner) is
  mandatory — it is the only way to recover each candidate's EFFECTIVE salience and so the ladder
  prediction (Beam Q-arb; same "log the vector, re-rank offline" rule as `self_present`).
- **`tools/check_arbiter_competition.py` (READ-ONLY, no flag)**: the ladder-residual readout below +
  winner distribution/entropy, candidate depth, per-kind eligibility (cadence). `--freeze`/`--baseline`
  for drift, like G3.

## PRIMARY (pre-registered) — LADDER RESIDUAL

The salience weights form a static ladder: `surprise 1.00 > stakes 0.90 > momentum 0.55 > bonsai 0.50 >
drive 0.45`. A naive "override rate" just reads out *which* candidates were live (cadence), not whether
the arbiter decided anything. The decision content is the **residual**:

> **residual rate** = fraction of fires where the observed winner ≠ the winner the **static weight
> ladder** predicts from that fire's live kinds, reported as a four-column readout stratified by
> liveness signature (signature → n → ladder-predicted → observed dist → residual).

- **≈ 0 → STRICT LADDER.** The arbiter picks the top-priority *available* line and decides nothing beyond
  priority order. "Earns its keep" = no; the question closes as cleanly as diversity_starvation did.
  Keep it (fail-safe), stop investing, do not reorder.
- **> 0 → RESIDUAL PRESENT.** Something re-ranks candidates. It can only be the two **variable**
  multipliers (momentum/stakes/drive are *constant* weights, so they never move the ladder): a weak
  surprise (`surprise_score·1.00`, score ∈ (0.3, 0.55)) falling **below** flat momentum 0.55, or a
  low-focus bonsai (`focus_num·0.50`) falling **below** flat drive 0.45. The residual therefore localizes
  to `surprise_score` and `focus_num` — and `focus_num` comes from `sense_events → bonsai`, closing the
  loop back to the sense_events selector. *That* localized residual is the answer.

## Tripwire / measurement-of-what guard (binding)

1. **The residual measures FRAME variation, not content selection.** The fetch is fixed before the
   arbiter; it can never license a fetch reorder. State this on every citation.
2. **Do not report the raw override/winner distribution as the primary** — it is a cadence readout
   (P(kind live)), exactly the groove-alert "readiness is a volume knob" error
   ([[nex5-readiness-is-a-volume-knob]]). The residual *subtracts* the ladder (the cadence) and is the
   only non-cadence number. If the residual cannot be computed from the logged vector (e.g. a schema
   regression drops saliences), **STOP and fix the schema**, do not substitute override rate
   ([[nex5-round-protocol]]).
3. **Exposure gate.** No claim until ≥ ~1 day of live fires are logged with `NEX5_GW_LOG=1` deployed.
   Until then the instrument prints "insufficient / is NEX5_GW_LOG armed?" by design.

## E4 pre-screen status (the five predicates)

- **Exposure:** currently **FAILS** (nothing logged). This build *creates* the exposure; the primary is
  deferred until data accrues, not failed.
- **Locus:** the arbiter is expression (frame), confirmed; so any lever found here is a voice/expression
  lever, never a selection one. **Design rule, not a measurement.**
- **Headroom, definitional-coupling, reproduce-from-live-input:** evaluated once the log has data.

## Not in scope (explicitly)

No reorder. No content lever. The only reorder-free content path identified (should one ever be wanted)
is the **belief pool / `belief_boost`** — sense already enters the fetch as `precipitated_from_sense`
beliefs on recency — and it would get its own headroom pre-screen. Not this round.
