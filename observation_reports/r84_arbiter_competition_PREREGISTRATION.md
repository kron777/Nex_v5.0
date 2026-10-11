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
  end-to-end tmp-dir run shows `line_on == line_off`). Record: `ts, n_candidates, kinds_present,
  winner_kind, winner_salience`.
- **`tools/check_arbiter_competition.py` (READ-ONLY, no flag)**: winner-kind distribution + entropy,
  override rate, candidate depth, per-kind eligibility (cadence). `--freeze`/`--baseline` for drift,
  like G3.

## PRIMARY (pre-registered)

**OVERRIDE-GIVEN-BONSAI-PRESENT** = among fires where `bonsai` was a candidate, the fraction where it
**lost**. This is the honest "the arbiter overrode an available baseline" number.

- **< 0.05 → RUBBER-STAMP.** The arbiter broadcasts the bonsai baseline ~always; its decision adds ~no
  variation to the lead frame. This would *confirm* the prompt-only-inert reading empirically and close
  the "does GWT do anything" question: keep it (fail-safe), stop investing, do not reorder.
- **≥ 0.25 → ACTIVE.** The arbiter frequently varies the lead frame. An **expression** lever may live
  there — but it folds into the **voice track** (does a different lead line measurably shift *style over
  fixed content*?), NOT a selection/reorder question.
- 0.05–0.25 → MOSTLY-BASELINE (occasional override).

## Tripwire / measurement-of-what guard (binding)

1. **The number measures FRAME variation, not content selection.** The fetch is fixed before the
   arbiter; override rate can never license a fetch reorder. State this on every citation.
2. **Override is confounded by cadence.** The weights fix `momentum (0.55) > bonsai ceiling
   (focus_num·0.50 ≤ 0.50)`, so momentum beats bonsai *whenever it is live*. A high override rate may be
   pure **momentum-liveness**, not a quality judgement — exactly the groove-alert "readiness is a volume
   knob" error ([[nex5-readiness-is-a-volume-knob]]). **Report override against `kinds_present_rate`;**
   if the override is ~entirely momentum-driven, the arbiter is a momentum-cadence relay, not a judge.
   If this question — "is override a judgement or a cadence term?" — cannot be answered from the logged
   fields, **STOP and ask**, do not substitute a weaker claim ([[nex5-round-protocol]]).
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
