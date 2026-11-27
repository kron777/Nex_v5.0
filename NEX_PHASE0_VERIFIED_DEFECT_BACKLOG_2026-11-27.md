# NEX Phase 0 — Verified Defect and Evidence-Gap Backlog (Mainline)

**Snapshot:** `main` at `66a97964f0531c16d60637dc8291b42e0b73f00b`  
**Date:** 27 November 2026  
**Purpose:** Separate confirmed documentation/source discrepancies from unknown host/runtime evidence and incomplete audits. This backlog is not approval to change cognition or policy.

## A. Confirmed documentation discrepancies

### D-01 — Sense adapter count / startup overview (corrected)

- **Evidence:** The factory wires 28 adapters (4 internal, 24 external); the scheduler constructor calls `start_all()`. The scheduler overview and `ARCHITECTURE.md` were corrected in PR #148.
- **Additional drift found:** the `run.py` module overview still said five DBs and paused external feeds; `gui/server.py` still said 23 adapters.
- **Disposition:** all known scheduler overview discrepancies are corrected in PR #148 and PR #153. PR #153 merged as `66a97964f0531c16d60637dc8291b42e0b73f00b`; its exact-head full suite passed.

### D-02 — MIND_MAP node-count convention unresolved

- **Evidence:** Current `MIND_MAP.yaml` has 39 `nodes:` entries plus 5 arms; comments/roadmap references still refer to 30 nodes.
- **Impact:** audits can conflate the 30 substantive aspect nodes, structural/placeholder entries and full YAML entry count.
- **Disposition:** preserve the map as-is; request owner reconciliation of the counting convention. Do not delete or merge entries to force 30.

### D-03 — MIND_MAP doctrine references absent

- **Evidence:** CI verifier warns that `VIRTUE_SLATE.md` and `mental_factors_inventory_alobha_spec.txt` are missing.
- **Disposition:** identify the authoritative source copies and restore/repoint references through a traceable documentation change; do not fabricate substitutes.

## B. Verified policy / documentation boundary

### P-01 — Coherence Gate exception fallback is fail-open

- **Evidence:** `CoherenceGate.check()` catches evaluation exceptions, records them, and returns ACCEPT with `gate_error_fallback`.
- **Disposition:** current behavior is documented; no change to outcomes or policy in Phase 0. Any fail-closed or other policy change requires the governing specification and the applicable founder approval.

### P-02 — Coherence Gate outcome documentation had drifted

- **Evidence:** code persists HOLD through the Holding Zone and queues RESHAPE; old module docs described them as logged-only.
- **Disposition:** corrected in PR #149 (merged), doc-only.

### P-03 — DAG buildability description had drifted

- **Evidence:** executable `_SATISFIED` set is `built`, `live_unproven`, `terminal`, not `built` only.
- **Disposition:** corrected in PR #150 (merged), text-only; caveats retained.

## C. Evidence gaps / incomplete verification (not code defects)

### E-01 — Current host/runtime baseline absent

No current host collection establishes which checkout is deployed, whether a NEX process is running, whether user services are active, or the current OS/kernel/hardware/process state. The older 25-Nov report belongs to a different host/branch snapshot and must not be relabelled as current.

### E-02 — Live database integrity inventory absent

No current SHA-256/size/WAL inventory was collected for the six substrate databases or runtime snapshots. No private data was copied into Git.

### E-03 — Model/runtime performance baseline absent

Python/SQLite/Ollama exact versions on host, exact Qwen model digest, loaded-model state, idle/load RAM/VRAM and prefill/decode tokens/sec remain UNKNOWN.

### E-04 — Full faculty producer/consumer DAG incomplete

The boot graph and key Chat/Fountain paths have been mapped from source. A complete forward (declaration → boot → scheduler → emission → consumer) and backward (output/write → upstream producers) audit for every `theory_x/` faculty is not yet complete.

### E-05 — MIND_MAP freshness warnings

CI emitted stale-source verification warnings for numerous nodes, plus the past-due `p13_finitude` unblock marker. These need source review and evidence refresh, not timestamp-only edits.

### E-06 — L4/runtime causal trace not captured

M0.5 currently has L3 synthetic fixtures and paired test evidence. No authorised live run has set `NEX5_TRACE_OVERLAY_CONTEXT=runtime`; L4 remains UNKNOWN.

### E-07 — V2.1 / doctrine authority boundary

Roadmap v3.0 M0.5 (technical causal trace) is distinct from V2.1 M0.5 (six doctrine questions). This backlog does not claim the six doctrine questions are answered, does not recreate a missing Frozen V2.1 source, and does not alter the frozen S-01–S-25 register.

## D. Test / CI evidence

- Exact M0.5 PR head `6d371fe385fc02a2c238247b39aff82681888745`: 2,491 passed, 7 skipped, 40 subtests, baseline OK, CI run #1392.
- Mind-map verification: completed with warnings only; no hard errors. Warnings include 2 missing doctrine references, stale verification dates and one past-due unblock marker.
- The post-merge push run `45939220368` on `66a97964f0531c16d60637dc8291b42e0b73f00b` was still pending/in progress at the time this backlog was drafted. Append its final result after completion.

## E. Additional bounded producer/consumer findings verified on current main

These are source-level conditions and test-coverage gaps recovered from older audit notes and re-checked against the current `main` snapshot. They are **not** findings about live rows, active processes or measured incidents.

### G-51 — CounterfactualNode can repeatedly select one unchanged oldest problem

- **Source:** `theory_x/stage_counterfactual/counterfactual_node.py`; `ProblemMemory.touch()` exists in `theory_x/stage7_sustained/problem_memory.py`.
- **Verified:** `_process_one()` selects one `state='open'` row using `ORDER BY last_touched_at ASC LIMIT 1`. It returns on empty TimeFetch, no buildable results, or after Gate processing without updating `last_touched_at` or calling `ProblemMemory.touch()`. The auto-promotion path is disabled.
- **Test gap:** `tests/test_counterfactual_node.py` tests a single open problem and individual packet/Gate behavior; it has no multi-open-problem progression/rotation test.
- **Risk/qualification:** if no other producer touches the selected row, subsequent ticks can select it again and delay newer problems. No live problem rows or tick history were inspected. Whether persistent focus is intended is unresolved.
- **Disposition:** design/evidence question; do not wire `touch()` or change selection until policy is established.

### G-52 — TimeFetch candidate eligibility is broader than its basic test inventory

- **Source:** `theory_x/stage_throw_net/time_fetch.py`.
- **Verified:** `fetch_from_beliefs()` filters confidence and minimum content length but does not constrain `tier`, `paused`, `locked` or `erosion_stage`. Novel-association retrieval joins the paired belief rows without those current-state filters; arc retrieval filters arc type/quality/summary but does not prove current-state eligibility of beliefs represented by an arc.
- **Tests:** `tests/test_throw_net_time_fetch.py` covers confidence/length, similarity and quality ordering, return-transformation exclusion, ProblemMemory routing, deduplication, cap and provenance. It does not test the above belief-status exclusions or post-creation eligibility of novel-association/arc endpoints.
- **Disposition:** policy/coverage gap only. Whether Tier 8, paused, locked or otherwise retired content should be excluded is a governing eligibility decision, not inferred here.

### G-53 — Warrant use-day timestamp cursors can skip tied rows at a page boundary

- **Source:** `theory_x/stage_warrant/recorder.py`; `_USE_BATCH = 20000`.
- **Verified:** `belief_lineage` and `arc_members` use strict-greater-than timestamp cursors (`created_at > ?`, `joined_at > ?`) ordered only by those timestamps. The last timestamp in each batch becomes the next cursor.
- **Conditional risk:** if equal-timestamp rows straddle a 20,000-row page boundary, the next query's strict `>` cursor skips remaining rows with that same timestamp. `record_synergy()` and arc-member writes can share a timestamp across related rows. The source establishes the keyset weakness; no live table population or actual skipped row was observed.
- **Test gap:** `tests/test_warrant_recorder.py` covers basic use-day counting, idempotence and ordinary cursor movement; it does not exercise a tied-timestamp group crossing the batch boundary.
- **Disposition:** candidate for a deterministic fixture with composite (timestamp, stable row ID) cursor semantics. No cursor/schema edit made.

### G-54 — Warrant scorer and recorder consume different anchor sources

- **Source:** `theory_x/stage_warrant/warrant.py`, `theory_x/stage_warrant/recorder.py`, `theory_x/stage6_fountain/generator.py`, `nex_keepalive.sh`.
- **Verified:** the Warrant scorer includes `dynamic.substrate_snapshots.walk_anchor_id` as a use signal. The recorder's use-cycle reads Fountain retrievals, `fountain_events.anchor_belief_id`, synergizer parents, `belief_lineage` parents and `arc_members`; it does not read `substrate_snapshots`.
- **Conditional source interaction:** the only `_capture_fire_snapshot()` call found in Fountain is in the substrate-voice path, which is gated by `NEX5_RECONCILE != '1'`. The tracked `nex_keepalive.sh` recipe sets both `NEX5_RECONCILE=1` and `NEX5_WARRANT_RECORD=1`. This describes that launch script only; the effective live host environment remains UNKNOWN.
- **Disposition:** establish intended use-signal coverage and test it with isolated fixtures before changing the source set. No claim about actual host use-day undercount is made.

### G-55 — RememberLoop writes a temporal link without durable parent lineage

- **Source:** `theory_x/life/remember_loop.py`.
- **Verified:** `remember_tick()` selects an old and recent belief, composes a linking sentence, and inserts a Tier-6 `remember_loop` belief. It returns the two source IDs to its caller/log, but does not write them to `belief_lineage` or another durable parent table in the inspected implementation.
- **Boot/test boundary:** `run.py` has no direct `remember_loop` import/start call; the repository has `tests/test_associative_recall.py`, which tests Fountain's different `_associative_recall` method, not this Life module. No claim is made that RememberLoop is currently running.
- **Disposition:** lineage provenance gap if/when this producer is authorised and active; define the intended relationship type and parent contract before adding writes.

### G-56 — Diversity EdgeBuilder's write counter is cumulative, not per statement

- **Source:** `theory_x/diversity/edge_builder.py:edge_builder_tick()`.
- **Verified:** after each `INSERT OR IGNORE`, the code increments `wrote` when `cx.total_changes > 0`. SQLite `total_changes` is cumulative for the connection; after the first successful change, later ignored duplicates can still satisfy that condition.
- **Impact:** the returned/logged `wrote` statistic can overstate successful inserts. This is a metric defect; the insert/ignore result and persisted graph are not thereby changed.
- **Test gap:** the inspected `tests/test_diversity.py` covers the DiversityLoop clocks and other diversity components but does not contain an EdgeBuilder duplicate-write/counter fixture.
- **Disposition:** bounded metric-only correction candidate (cursor `rowcount` or per-statement change count) with a duplicate fixture; no runtime code altered here.

### G-57 — Generic Stage-2 edges can make beliefs ineligible for Stage-3 typed classification

- **Sources:** `theory_x/diversity/edge_builder.py`; `theory_x/stage3_world_model/edge_generator.py`; `theory_x/stage2_dynamic/__init__.py`; `run.py`.
- **Verified:** Stage-2 EdgeBuilder creates generic `cross_domain` edges from a recent comparison pool for under-connected beliefs. Stage-3 EdgeGenerator selects recent `fountain_insight`/`synergized` beliefs only when they have no edge in either direction. A generic edge can therefore remove a belief from the Stage-3 candidate set before typed `supports`, `refines` or `opposes` classification.
- **Qualification:** this may be intended early graph saturation; no live graph coverage or lost classification was measured. The Stage-2 loop is registered through the dynamic factory; Stage-3 EdgeGenerator is separately started in `run.py`.
- **Disposition:** graph-admission ordering/ownership question for the crosswalk. Do not change edge types, queue criteria or loop order without specification/approval.

## F. Gate boundary

This backlog is evidence input for Gate 0. It is not permission to enable Phase 1 experiments, change prompts, change confidence/belief revision, modify Coherence Gate policy, alter dark flags, start/restart services or touch live databases.
