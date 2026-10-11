# R83 — PRE-REGISTRATION: the phrasing-layer groove (`NEX5_PHRASING_ROTATE`)

## 0. Status — the groove is phrasing-level (measured); lever = the generation prompt; NOT built pending Step-0

Every earlier L4 locus was the wrong layer: readiness (volume, r79/r80 — saturated gate), framing
(arbitrate, r81 — prompt-only), branch retrieval (r82 — branch switches 88%, no fixation). The
repetition that survives all of them is **phrasing**: a template opener frame applied across varied
content and branches. r83 targets it, and — learning from r80/r82 — **does not build the lever until a
Step-0 generation A/B confirms the lever actually moves the metric (§2b).**

## 1. The change under test (to build only if §2b passes)

**`NEX5_PHRASING_ROTATE` (default OFF).** The generation prompt frames content as "the item" 4+ times
across modes (`generator.py:355,380,391,400`, for grounding), which induces the opener template. The
lever **rotates the item-reference framing** across a small deterministic set per fire (e.g. "this
item" / "this" / "the material in front of me" / present the content without the "item" label), so
the opener frame cannot lock in — a *substitutive* prompt-STRUCTURE change, not an added instruction
(an instruction would be the inert L3-style hint). Not yet built.

## 2. Measured baseline (frozen) — `observation_reports/r83_baselines/phrasing.json`

Live, window 3000 (n=2116 substantive), 2026-10-11, via `tools/check_phrasing_repeat.py`:

| Signal | Baseline |
|---|---|
| **opener_repeat** (8-word opener shared by ≥1 other fire) — PRIMARY | **0.540** (1284 distinct, HHI 0.0028) |
| consec first-sentence 5-gram Jaccard ≥ 0.5 | 0.160 |
| `_is_template` per-fire rate | 0.103 |

Low HHI + high repeat = a STRUCTURAL frame over varied content — the groove's signature. Top openers:
"this item is about …", "this item brings up …", "this item discusses …", "the item discusses …".

## 2b. Step-0 FEASIBILITY (MUST pass before building §1 or arming) — the lesson from r80/r82

**Is the opener frame prompt-driven (so rotation moves it) or LLM-intrinsic (so rotation is inert)?**
Run an offline/scratch generation A/B: generate a sample of fires with the rotated framing vs the
fixed "the item" framing on the same retrieved items, and measure `opener_repeat` in each with the
harness. Gate:
- rotation cuts `opener_repeat` materially AND grounding (`p_on_subject`) holds ⇒ build §1, proceed.
- rotation does not move `opener_repeat` ⇒ the opener is model-intrinsic; the prompt lever is inert.
  Do NOT build it. Re-aim at generation parameters (frequency/presence penalty) or conclude the
  opener is a generation-model stylistic property, not a dark-flag-addressable mechanism — and record
  that as the honest terminus of the L4_teeth line.

This gate is non-negotiable: r79/r80/r82 were each built before their trigger's feasibility was
measured, and each turned out inert on the live instrument. r83 inverts the order.

## 3. Hypothesis and metrics (for the armed round, if §2b passes)

**Hypothesis.** Rotating the item-framing **reduces `opener_repeat`** (the template frame stops
locking in) **at constant cadence and without regressing grounding.** Mechanism: a varied prompt
structure gives the LLM no single frame to default to, so openers diversify.

**Primary (winner-blind, content-independent).** `opener_repeat`, baseline **0.540**. Effect sought:
a **≥ 20% relative drop** (to ≤ 0.43). **Secondary:** consec 5-gram Jaccard ≥ 0.5 (0.160).
MDE/power: at n ≥ 2000 fires/window the opener_repeat SE is small (< 0.015), so −0.11 absolute is
well powered; < MDE with CI excluding it ⇒ real null (→ §2b's inert branch), not inconclusive.

**Co-primary (Beam 1a).** Cadence within ±20% of 690.5/day.

**Guardrail.** `p_on_subject` (grounding) must NOT regress — the "use only what is in the item"
instruction is anti-hallucination; varying the referent must preserve grounding (`check_tripwires`
EXPLAIN ≥ 0.65).

## 4. Tripwires — revert if ANY fires
Cadence outside ±20%; `p_on_subject` EXPLAIN < 0.65; maxDF* breach ≥ 25%; register largest-share > 0.70.

## 5. Decision tree
- **A — opener_repeat down ≥ 20% at cadence in band, grounding held.** The phrasing lever works — the
  first L4 mechanism on the right layer. → default-ON consideration; one tuning pass (rotation-set
  size), then stop.
- **B — opener_repeat flat (< MDE), grounding held, cadence in band.** The opener is model-intrinsic,
  not prompt-structure-driven → the prompt lever is inert (consistent with §2b); record and re-aim at
  generation params, or accept the groove as a model stylistic property.
- **C — any tripwire (esp. grounding regression).** Revert; record which and the reading.

## 6. Sequencing
Its own flag; run alone (all other `NEX5_*` prompt/affect/teeth flags OFF). Re-freeze any earlier
round's baseline that this changes (the prompt surface is shared — Beam A4 staleness rule).

## 7. Verdict and disarm
Verdict to `observation_reports/r83.md` + `journal/DEPLOY_LEDGER.tsv` + `journal/CARRY_OVER.md`;
disarm commit subject carries the verdict and SHA.

---

*No sentience claim. r83 tests whether varying the generation prompt's framing measurably diversifies
the opener template at constant grounding — a prompt-structure lever on phrasing. It is silent on
whether anything is experienced.*
