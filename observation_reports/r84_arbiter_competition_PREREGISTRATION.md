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

## PRIMARY — three channels, never conflated (Beam Q-arb round 2)

A single "ladder residual" against the **nominal flat-weight** ladder (`surprise 1.00 > stakes 0.90 >
momentum 0.55 > bonsai 0.50 > drive 0.45`) **false-fires**: the variable multipliers (`surprise_score`,
`focus_num`) re-order the intended priority *by construction*, so that residual is large whenever
`surprise_score < 0.90` or `focus_num < 0.9` — reading it as "the arbiter decided something" is the exact
measurement-of-what error this round guards against ([[nex5-measurement-of-what]]). Split it:

- **`R_correct` (CORRECTNESS TRIPWIRE, must be ≈ 0):** observed winner ≠ the **effective argmax** over
  the logged saliences. The code sets `winner = max-salience`, so any departure is a tie-path / log-
  integrity bug — inspect it, never read it as "keep". `R_correct > 0` ⇒ STOP and inspect.
- **`R_design` (DESIGN READOUT, expected LARGE, not a keep signal):** observed winner ≠ the nominal
  flat-weight prediction. This just measures how far the multiplier layer re-orders the intended
  priority. Report it; do **not** interpret it as decision content.
- **EARNS-ITS-KEEP (the real primary):** the arbiter's data-driven surface is provably tiny.
  `focus_num ≤ 1.0` and momentum is flat 0.55, so bonsai (`focus_num·0.50 ≤ 0.50`) can **never** beat
  momentum (needs `focus_num > 1.1`); `focus_num` has **veto power only** — it drops bonsai under flat
  drive (0.45) when `focus_num < 0.9`, never promotes it. So the question reduces to
  **`P(bonsai wins | momentum absent)` + the `focus_num` distribution there**, and the only genuinely
  data-driven region is `{momentum absent} ∩ {focus_num > 0.9}` (`data_driven_region_share`).
  - region share **< 0.02 → NEAR-DETERMINISTIC**: outcome ~fully fixed by flat weights + liveness;
    "earns its keep" = no; keep it (fail-safe), stop investing, do not reorder.
  - region share **≥ 0.02 → DATA-DRIVEN REGION PRESENT**: `focus_num` (from `sense_events → bonsai`)
    actually decides bonsai-vs-drive in that slice — the one place sense_events reaches the frame.
- **SURPRISE ENTRY RATE (exposure diagnostic):** surprise enters at `score > 0.3` but its salience *is*
  the score, so a surprise in `(0.3, 0.45)` enters yet loses to flat drive — a dead band that pads depth
  and never wins. `surprise_events` IS populated (`predictive_substrate.py:405`), so this measures live
  *clearance*: if the entry rate is ~0 or the dead-band share ~1, the nominal #1 is effectively a
  phantom and the arbiter is a 4-way with `focus_num` its only data term.

## Tripwire / measurement-of-what guard (binding)

1. **Everything here measures FRAME variation, not content selection.** The fetch is fixed before the
   arbiter; no number here can license a fetch reorder. State this on every citation.
2. **Never promote `R_design`, override rate, or winner distribution to the primary** — all are cadence
   readouts (P(kind live) + the multiplier layer obeying the code), the "readiness is a volume knob"
   error ([[nex5-readiness-is-a-volume-knob]]). Only the earns-its-keep region share and `R_correct` are
   decision/ correctness claims.
3. If a channel cannot be computed from the logged vector (e.g. a schema regression drops saliences),
   **STOP and fix the schema**, do not substitute a weaker number ([[nex5-round-protocol]]).
4. **Exposure gate.** No claim until ≥ ~1 day of live fires are logged with `NEX5_GW_LOG=1` deployed.
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
