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

**Historical coordination.** The original implementation was isolated on
`claude/rdo-stage6-learning-loop`, based on the Stage-5 head `25e186a`. The integrated
Stage 2–7 capability set is now carried in PR #124 on the hardened mainline. No live NEX writes,
injections, flag/config changes, restarts or experiment modifications are performed.
`python -m rdo stage6`.

## What was added (reuse-first, in `memory.py`)

- `prediction_accuracy(cycle)` — UNKNOWN (`None`) until an actual is recorded; otherwise
  `correct / (correct + missed + unnecessary + inappropriate_reuse)` where
  `correct = predicted_net_new − unnecessary`. **Over-generation can only lower it.**
- `learning_provenance(cycle)` — `reviewer_attributed:planning_review` · `controlled_fixture_review` · `executed_verified_outcome` ·
  `independent_watcher_verified` · `automated_self_assessment` · `unknown_no_outcome`. A reviewer string is attribution, not authenticated identity. A planning review is **never** read as an
  execution outcome.
- `reopening_candidates(cycle, new_evidence)` — reopens a reviewed reuse or source-matched review branch
  now observed missing, or a deferred branch whose blocker is reported cleared; **UNKNOWN/insufficient evidence does not reopen**.
- `learning_loop(cycles, new_evidence, reopen_cycle)` — assembles per-cycle accuracy + provenance +
  contradictory-evidence flags, aggregates accuracy **only** over recorded outcomes, and keeps the
  rest UNKNOWN.

## Integrated demonstration provenance (`rdo stage6`)

The integrated runner ingests the RDO catalogue's recorded development-cycle outcomes and adds
one `controlled_fixture_review` solely to exercise the provenance and reopening paths. That
fixture is **not** an authenticated human review and is excluded from aggregate prediction accuracy.
Caller-supplied reviewer labels are reported as `reviewer_attributed`; the system does not claim
to authenticate the reviewer identity.

The runner also exercises a concrete contradiction: the prior `belief_staleness_input`
source-match branch is reported missing and reopens its semantic-review path, while the
`belief_decay_policy` UNKNOWN observation does not reopen. These are controlled evidence
fixtures, not observations of the live NEX runtime. The catalogue comparability group remains
limited to genuinely comparable migration-guard cycles.

## Requirements → evidence (tests)

`rdo/tests/test_stage6_learning_loop.py` contains focused tests for the following behaviours;
the full integrated suite is verified by the current exact-head PR #124 CI, not by the historical
stage-only count:

- predicted vs actual obligations / reuse / effort → `test_predicted_vs_actual_reuse_and_effort_tracked`, `test_missed_obligations_lower_accuracy`
- **anti-gaming** (over-generation never raises accuracy) → `test_over_generation_never_raises_accuracy`
- UNKNOWN for no/insufficient actual → `test_no_actual_is_unknown_not_fabricated`
- contradictory evidence flagged, not silenced → `test_contradictory_evidence_is_flagged`
- reviewer-attributed vs controlled-fixture vs automated vs executed provenance → `test_reviewed_vs_automated_vs_executed_provenance`, `test_controlled_fixture_does_not_influence_accuracy_aggregate`
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

The Stage-7 Watcher execution-verification capability is integrated alongside Stage 6 in PR #124.
The remaining live-runtime confirmation is host-only and UNKNOWN from cloud execution. The
**v1.3/v1.4 precedence** remains open; no version reconciliation is assumed.


## Integration evidence correction (26 Nov 2026)

The Stage-2 belief-recency finding is a source signature match, not an independently reviewed
semantic-reuse decision. Stage-6 reopening therefore covers both (a) a previously reviewed reuse
that is later contradicted and (b) a source-matched review branch whose source anchor is later
reported missing. It preserves the distinction in the emitted reason. Missing, empty or UNKNOWN
observations do not reopen anything.

The integrated learning loop also treats omitted discrepancy categories as UNKNOWN. It does not
silently substitute zero for missing missed/unnecessary/inappropriate-reuse reports; a prediction
accuracy value is emitted only when the required discrepancy categories have been explicitly
reported. Earlier example averages in the pre-integration Stage-6 report predate this stricter rule
and are not carried forward as verified results.
