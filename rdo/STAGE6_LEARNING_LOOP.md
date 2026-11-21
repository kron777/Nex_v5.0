# RDO Stage 6 — Learning Loop

**Governing scope:** RDO v1.3 §16 Stage 6. Establish the learning loop over the **actual** Stage 2–5
development evidence: compare predicted vs actual obligations and reuse, track missed / unnecessary /
inappropriate-reuse / deferred / unresolved, evaluate prediction accuracy and estimation quality with
traceable evidence, preserve reviewer provenance, reopen deferred/resolved branches on new evidence,
persist reproducibly, and report **UNKNOWN** rather than manufacture certainty.

**OFT:** no general-purpose ML subsystem. The loop reuses the existing `memory.py` primitives
(`compare`, `cycle_metrics`, `accuracy_series`, `comparability_assessment`, `_confidence`,
`PatternMemory.refute`) and adds only the genuinely-new pieces, in the same module (no 14th module;
module count stays 13).

**Coordination.** Branch `claude/rdo-stage6-learning-loop`, based on `25e186a` (Stage 5 head).
`rdo/`-only; earlier branches untouched. No live NEX writes, injections, flag/config changes,
restarts or experiment modifications. `python -m rdo stage6`.

## What was added (reuse-first, in `memory.py`)

- `prediction_accuracy(cycle)` — UNKNOWN (`None`) until an actual is recorded; otherwise
  `correct / (correct + missed + unnecessary + inappropriate_reuse)` where
  `correct = predicted_net_new − unnecessary`. **Over-generation can only lower it.**
- `learning_provenance(cycle)` — `human_reviewed:planning_review` · `executed_verified_outcome` ·
  `automated_self_assessment` · `unknown_no_outcome`. A planning review is **never** read as an
  execution outcome.
- `reopening_candidates(cycle, new_evidence)` — reopens a reused mechanism now observed missing, or a
  deferred branch whose blocker is reported cleared; **UNKNOWN/insufficient evidence does not reopen**.
- `learning_loop(cycles, new_evidence, reopen_cycle)` — assembles per-cycle accuracy + provenance +
  contradictory-evidence flags, aggregates accuracy **only** over recorded outcomes, and keeps the
  rest UNKNOWN.

## Results on real evidence (`rdo stage6`)

Ingested the real executed cycles (catalogue) + one reviewer-attributed planning cycle (10 cycles):

- **Provenance split:** 1 `human_reviewed` (planning review) · 5 executed/self-assessed · **4 UNKNOWN**.
- **Mean prediction accuracy:** ~0.84 over the recorded-outcome cycles; the 4 planning-only cycles are
  **UNKNOWN**, not averaged in. Per-cycle is traceable (e.g. `arc_closers` = 0.5: predicted 1, missed 1).
- **Reopening (controlled fixtures on a real cycle):** `belief_staleness_input` (reused → reported
  missing) **reopens**; `belief_decay_policy` (UNKNOWN observation) **does not**.
- **Comparability:** the honest largest comparable group is unchanged (migration guards); a planning
  review contributes **no** executed comparable cycle.

## Requirements → evidence (tests)

`rdo/tests/test_stage6_learning_loop.py` (9 tests), full RDO suite **98 passing**:

- predicted vs actual obligations / reuse / effort → `test_predicted_vs_actual_reuse_and_effort_tracked`, `test_missed_obligations_lower_accuracy`
- **anti-gaming** (over-generation never raises accuracy) → `test_over_generation_never_raises_accuracy`
- UNKNOWN for no/insufficient actual → `test_no_actual_is_unknown_not_fabricated`
- contradictory evidence flagged, not silenced → `test_contradictory_evidence_is_flagged`
- reviewed vs automated vs executed provenance → `test_reviewed_vs_automated_vs_executed_provenance`
- planning review ≠ execution outcome → `test_planning_review_is_not_counted_as_execution`
- reopening only on concrete contradicting evidence → `test_reopening_only_on_concrete_contradicting_evidence`
- real stage evidence + persistence + fresh-process resume → `test_real_stage_evidence_loop_persists_and_resumes`

## Limitations / remaining gaps

- **Small sample.** Accuracy is computed over a handful of recorded outcomes; `accuracy_series` keeps
  its no-acceleration guard. No trend/acceleration is claimed.
- **Planning reviews are not execution.** Their calibration informs *planning*, not verified
  implementation outcomes; the loop tags and segregates them.
- **Live verification is host-only.** The loop learns from recorded RDO development evidence; it does
  not and cannot, from the cloud, confirm live NEX runtime behaviour.
- **Calibration weights remain heuristic** (`_confidence`), explicitly uncalibrated.

## Next roadmap step

Per RDO v1.3 §16: **Stage 7 — execution integration verified through Watcher** (close the loop with
Watcher observation of executed work). The host-only live confirmations and the **v1.3/v1.4
precedence** remain open for your authority/ruling; no version reconciliation is assumed.
