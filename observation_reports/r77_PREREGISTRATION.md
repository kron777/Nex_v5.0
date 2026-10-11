# R77 — PRE-REGISTRATION: the chat attention arbiter, locked before the treatment number exists

## 0. Status at time of writing — baselines OBSERVED, treatment UNOBSERVED

The OFF-condition baselines below are measured (frozen to `observation_reports/r77_baselines/`
by the three harnesses on the live corpus, 2026-10-10, NEX just resumed). The ON-condition
numbers do not exist yet — the arbiter has never run on the live instrument. This document fixes
the hypothesis, the window, the tripwires, and the full decision tree **before** any treatment
number exists, so no choice is improvised against the result.

## 1. The change under test

**`NEX5_CHAT_WORKSPACE` (default OFF)** — the chat turn's ~13 faculty blocks were concatenated
with no competition and no budget, while the fire path arbitrates. The arbiter keeps the
distress/moral-response blocks (`compassion`, `compass`) always and admits the rest by descending
salience until `NEX5_CHAT_WORKSPACE_BUDGET` chars (default 1400). Code: `gui/server.py`
`_assemble_chat_blocks`, `theory_x/stage_tom/global_workspace.select_within_budget`. **On branch
`claude/self-continuity`; NOT yet deployed to the main checkout** — r77 requires that deploy.

The salience weights and the budget are **provisional** (see §6). This round tests the
*mechanism*, not the numbers.

## 2. Hypothesis (primary)

Arming `NEX5_CHAT_WORKSPACE` **reduces chat self-repetition** — the within-session near-duplicate
fraction measured by `tools/check_session_consistency.py` — **without** regressing on-subject or
perturbing cadence. Mechanism: competition + budget stop the low-salience affliction/stance blocks
from piling on and crowding the block that answers the person.

## 3. Conditions and window

- **OFF** = the frozen baseline (current, un-armed main checkout).
- **ON** = `NEX5_CHAT_WORKSPACE=1`, deployed, in the launcher.
- **Window** = **≥ 200 chat turns OR ≥ 14 days**, whichever first. Chat turns, because the primary
  metric is chat-side. (The fire-path metrics are guardrails, not the test.)
- **One variable.** No other prompt/affect flag changes during r77. Held fixed:
  `NEX5_OWN_CONTENT_RENDER` (OFF), `NEX5_AFFECT_CARRY`, `NEX5_SELF_PRESENT` (OFF — it is r78).
  These are the confound set (shared prompt/affect surface).

## 4. Frozen baselines (OFF condition)

| Signal | Harness | Baseline (frozen) |
|---|---|---|
| **chat self-repetition (near-dup sessions)** — PRIMARY | `check_session_consistency` | **0.4889** (worst 1.0, mean 0.4923) |
| register largest-share (collapse guard) | `check_session_consistency` | 0.4178 (9 distinct) |
| surface template dup / cluster (guardrail) | `check_template_repetition --window 200` | 0.0 / 1.0% |
| active fires/day (guardrail) | `check_cadence --days 14` | 690.5 (median 2.09 min) |
| on-subject p_on_subject (guardrail) | `check_tripwires` | EXPLAIN 0.6427 / overall 0.529 |

## 5. Tripwires — revert immediately if ANY fires (checked during the window)

- **Cadence**: `check_cadence --baseline` active fires/day outside **±20%** of 690.5.
- **Template**: `check_template_repetition --baseline` dup rate or cluster fraction up **> +25%**.
- **On-subject**: `check_tripwires` `p_on_subject` reverts **< 0.65**, or maxDF* breach ≥ 25%.
- **Register collapse**: largest-share rises **> 0.70** (one register dominating).

A tripwire means STOP — disarm, record the breach, the arbiter does not ship this round.

## 6. THE DECISION TREE — fixed now

Primary metric = `check_session_consistency` near-dup-sessions fraction, baseline **0.4889**.

- **BRANCH A — drop of ≥ 25% relative (to ≤ 0.367) AND no tripwire.** The arbiter closed its loop.
  → it earns default-ON *consideration*; proceed to a salience/budget tuning pass (r77b, §7), not
  an immediate default-on.
- **BRANCH B — drop < 25% relative (incl. flat or up), no tripwire.** The mechanism did not
  measurably diversify chat attention at the provisional parameters.
  → **one** pre-registered tuning retry, r77b (§7). If r77b also fails Branch A, the arbiter is
  **falsified for its stated purpose** and is reverted. No further tuning (anti-fishing).
- **BRANCH C — any tripwire fires.** Revert regardless of the primary metric. The change perturbed
  something it must not. Record which tripwire and the reading.

## 7. r77b — the ONE pre-registered tuning retry (direction fixed now, to avoid post-hoc fishing)

If Branch B: the single tuning move is to **lower `NEX5_CHAT_WORKSPACE_BUDGET`** (from 1400 toward
900) so the competition bites harder, and nothing else. Rationale fixed now: at a budget that
rarely evicts, the arbiter ≈ concatenation, so a null result is consistent with "budget too loose"
and the honest next step is a tighter budget, once. If r77b (tighter budget) still fails Branch A,
the mechanism — not the parameters — is what failed, and it reverts.

## 8. Verdict and disarm

Verdict to `observation_reports/r77.md` + a row in `journal/DEPLOY_LEDGER.tsv` + `journal/CARRY_OVER.md`.
**The disarm commit's subject line carries the verdict and the disarm SHA** (repo convention —
`b941c79`, `6c203c3`, `99ab815`). Follow it or r77 is not comparable to the ledger.

## 9. The self_present follow-on is r78, NOT r77

`NEX5_SELF_PRESENT` (the structured carry, continuity of attention across turns) is tested
**separately**, after the arbiter round, one variable at a time. Its falsifier: the carried winner
must **change when the salience vector changes** and reach the composed prompt; `turn_count`
advancing while `winner_kind` is frozen = decorative. Pre-registered as r78 when r77 closes.

---

*No sentience claim. This round tests whether a functional loop (chat attention competition)
measurably changes behaviour; it is silent on whether anything is experienced.*
