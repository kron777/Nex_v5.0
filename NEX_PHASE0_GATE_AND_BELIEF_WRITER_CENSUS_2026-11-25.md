# NEX Phase 0 — CoherenceGate and Belief-Writer Census (25 November 2026)

## Scope and evidence boundary

This is a static-source continuation of the Phase 0 producer/consumer trace. The primary source baseline is the active host branch `claude/nex-continuity-wire` at `de93134f34adac07a3a41c2a05b33720510a2bfc`.

The audit follows the prescribed producer/consumer trace: map Gate callers and belief writes, separating external perception, internal generation, self-observation, bootstrap anchors, controlled promotion, maintenance and experimental utilities.

The source census was expanded to all 350 Python source files (tests excluded) using literal SQL and Gate-reference scans, then followed by targeted inspection of each hit and normal startup wiring. This is broader than the earlier bounded audit but is not a formal AST analysis: dynamically assembled SQL, non-Python code and runtime reflection may evade literal matching. It does not establish live thread execution, current environment flags, database contents, write frequency or behavioural effect. No live service or database was opened. No runtime code, tests, flags, schema, service, experiment, baseline, tripwire or deployment setting was changed.

## 1. Gate construction and wiring

### Main startup path

`run.py` constructs one `CoherenceGate` with the shared beliefs/conversations readers, beliefs writer, HoldingZone, HoldingZoneResolver, TriggerDetector and SelfNarrative (approximately lines 124–148). It then passes that instance into:

- `build_dynamic(..., coherence_gate=...)` — Stage 2 crystallizer and DynamicState (lines 150–153; stage2 factory around lines 459–500).
- `build_world_model(..., coherence_gate=...)` — World Model / Synergizer (lines 174–177).
- `build_membrane(..., coherence_gate=...)` (lines 179–187).
- Fountain construction (the Fountain wiring is later in `run.py`).
- CounterfactualNode and ThrowNetEngine (approximately lines 242–270 and 322–340).
- HoldingZoneResolver via `set_gate()`; the resolver re-submits reshaped packets through the gate.

The Stage 2 `_emergent_drives_loop` passes `state.coherence_gate` into `EmergentDriveDetector.apply_approved()` (stage2 `__init__.py` around lines 400–425). This is a real boot-wired path, not merely an optional unit-test construction.

### Alternate GUI state factory

`gui/server.py::build_state()` independently constructs its own Gate/HoldingZone/Resolver/TriggerDetector when it creates a standalone AppState, then passes the gate to Dynamic, World Model, Membrane, Fountain, ThrowNetEngine and CounterfactualNode. This is a second construction path in source, not evidence that two gates run simultaneously in the normal `run.py` process. The caller selecting the application state factory determines which construction path is used.

### Gate error policy

`CoherenceGate.check()` catches exceptions from `_evaluate()`, records the error and returns `GateOutcome.ACCEPT` with reason `gate_error_fallback`. The method then logs the decision and continues normal ACCEPT side effects. This is explicitly fail-open behavior; it is not a fail-closed gate. Caller-specific exception handling still matters for errors outside `check()`, but the inspected `check()` implementation itself is designed not to raise on evaluation failure.

## 2. Verified gate-consumer paths

| Path | Gate use | Belief effect / boundary |
|---|---|---|
| Stage 2 Dynamic Crystallizer | Builds a ThoughtPacket and calls `check()` before insertion | Inserts Tier 7 `precipitated_from_dynamic` only on ACCEPT |
| World Model Synergizer | Calls `check()` on the synthesized packet | Inserts Tier 6 `synergized` only on ACCEPT |
| FountainCrystallizer | Calls `check()` after quality checks and before insertion | Inserts the normal Fountain belief only on ACCEPT |
| Fountain drive probe | Submits a deterministic `drive_probe` ThoughtPacket | Probe is delivered to the gate; this method does not itself insert a belief |
| EmergentDriveDetector | `apply_approved()` calls `check()` for each approved proposal | Writes Tier 5 `emergent_drive` only on ACCEPT when a gate is supplied; the no-gate fallback writes without a gate |
| BehaviouralSelfModel | `write_behavioural_beliefs()` builds a ThoughtPacket and calls the supplied Gate before writing | Writes Tier 6 `behavioural_observation` only on ACCEPT in the normal path; an exception escaping `check()` is logged and falls through to the insert (conditional fail-open) |
| CounterfactualNode | Calls `check()` for each buildable candidate | Inserts the candidate belief only on ACCEPT |
| ThrowNetEngine | Calls `check()` for each refined candidate | Records per-candidate outcomes; the engine does not itself insert each candidate as a belief |
| HoldingZoneResolver reshape path | Transforms a held packet and re-submits the transformed packet through `check()` | The original held row is marked reshaped; the transformed packet's new gate outcome controls its subsequent handling |

The normal startup wiring supplies a Gate to the Stage 2 Dynamic factory and the normal Emergent Drives loop forwards that instance to `apply_approved()`. The optional no-gate branch remains in the method for standalone callers/tests. The Gate's own `gate_error_fallback` ACCEPT means that an internal evaluation exception can still result in an ACCEPT decision at this boundary.

HoldingZoneResolver's separate ACCEPT-corroboration mechanism is also confirmed: three corroborating ACCEPT events can invoke `HoldingZone.promote_to_belief()`. That is a controlled promotion path whose threshold is based on prior gate decisions, not an ordinary ungated producer.

## 3. Belief-writing paths and their distinct roles

### A. Runtime producers with an explicit Gate path

- Dynamic crystallization — `theory_x/stage2_dynamic/crystallization.py`.
- World Model synthesis — `theory_x/stage3_world_model/synergizer.py`.
- Normal Fountain crystallization — `theory_x/stage6_fountain/crystallizer.py`.
- Approved emergent drives — `theory_x/stage2_dynamic/emergent_drives.py`.
- BehaviouralSelfModel observations — `theory_x/stage4_membrane/behavioural_self_model.py`.
- Counterfactual candidates — `theory_x/stage_counterfactual/counterfactual_node.py`.

These are distinct from the drive-probe and ThrowNet paths, which submit packets to the Gate but do not directly insert a belief in the inspected function.

### B. Runtime belief producers without a Gate call in the inspected write path

1. **External sense distillation** — `theory_x/stage2_dynamic/__init__.py::_sense_distillation_loop` writes Tier 7 `precipitated_from_sense` beliefs through the beliefs Writer. Its docstring explicitly says it bypasses CoherenceGate because external perceptions are treated as substrate content, not internally generated thoughts. It excludes `internal.%` and `external.other_mind` streams. This is an explicit source rationale; whether it is an authorised exception to the governing contract remains unresolved.

2. **Fountain self-rut mirror** — `theory_x/stage6_fountain/generator.py` writes a Tier 6 `self_rut_notice` belief when its STRIKING-rate trough condition and two-hour throttle permit. The inspected insertion does not create a ThoughtPacket or call CoherenceGate. This is internally generated self-observation, not external perception.

3. **Seven Stage 2 life loops** — `theory_x/stage2_dynamic/__init__.py` imports and appends the following loops to its daemon-loop collection: IdentityLoop, PatternLoop, WitnessLoop, SurpriseLoop, RememberLoop, WonderLoop and FetchLoop. Their producer modules insert Tier 6 beliefs directly using `substrate.connect()`, rather than the shared beliefs Writer/CoherenceGate path:
   - `theory_x/life/identity_loop.py`
   - `theory_x/life/pattern_loop.py`
   - `theory_x/life/witness_loop.py`
   - `theory_x/life/surprise_loop.py`
   - `theory_x/life/remember_loop.py`
   - `theory_x/life/wonder_loop.py`
   - `theory_x/life/fetch_loop.py`

   These are normal-wired Stage 2 background loops in source, not just standalone scripts. They were introduced after the May 10 Phase 22 universal-gating record, as detailed in the prior trace §65. Whether each loop's output is a “thought” within the intended universal-gate scope is a governing-contract question, not something source inspection can decide.

4. **HotObserver** — `theory_x/stage_tom/hot_observer.py` contains a direct Tier 3 belief insertion through `substrate.connect()`. The import is dynamic: `FountainGenerator.generate()` imports and calls `hot_observer.observe()` on the normal Fountain path when `NEX5_HOT_OBSERVER=1` (around generator.py lines 2023–2025). Thus this is a conditional, Fountain-wired runtime producer, not an unreferenced module. The source default is OFF; the host-effective flag is UNKNOWN. The dedicated later retrieval query selects HotObserver rows into an intermediate candidate list, but the current prompt builder does not render them as normal Fountain prompt text (see the corrected producer/consumer trace §72).

5. **BehaviouralSelfModel** — `theory_x/stage4_membrane/behavioural_self_model.py` writes Tier 6 `behavioural_observation` beliefs through the shared beliefs Writer. The normal `build_membrane()` path constructs the component with the supplied CoherenceGate and starts `_behavioural_loop` as a daemon thread. The loop runs on a four-hour cadence. `write_behavioural_beliefs()` builds a ThoughtPacket and calls Gate before insertion; a non-ACCEPT returns without writing. However, an exception escaping `check()` is caught and logged, after which the function continues to the insert. The Gate's own `check()` method normally catches evaluation errors and returns `gate_error_fallback` ACCEPT, but the outer BSM catch is an additional fail-open boundary if `check()` itself raises. `tests/test_behavioural.py::test_write_behavioural_beliefs` constructs BSM without a Gate, so it does not test the normal Gate path or this exception boundary.

### C. Self-knowledge and bootstrap writes — not ordinary generated-thought producers

- **SelfLocationCommitment** — `theory_x/stage5_self_location/commitment.py` idempotently inserts a locked Tier 1 `self_location` anchor during boot. This is a bootstrap commitment, not an ordinary generated thought.
- **Grounded scorecard self-belief** — `ground_self_belief.py` inserts the locked Tier 1 `grounded_scorecard:market_direction_v1` belief if absent, otherwise updates its content/confidence/timestamp in place. `theory_x/life/scorecard_loop.py` is appended to the Stage 2 loop list; it runs once immediately and then hourly. This is a measured self-knowledge refresh, not a new thought on every tick.
- **Keystone and koan seeds** — `keystone.py` and `substrate/koan_seeds.py` contain boot-seed inserts. The prior trace §60 records that these run during substrate initialisation before the runtime TaggingBeliefWriter wrapper is installed. Their bootstrap status should remain distinct from runtime cognition producers.
- **Spectrum seed paths** — `substrate/seed/load_spectrum.py` and `substrate/spectrumizer_process.py` contain spectrum-belief inserts. These are seed/import paths, not normal live generative loops.
- **Identity seed utility** — `scripts/seed_identity_beliefs.py` contains an insert, but is an explicit script path rather than a normal boot loop.

### D. Controlled promotion and maintenance


### E. Manual, experimental and dry-run utilities

- **Decryption ProbeRunner** — `decryption/probe_runner.py` is explicitly invoked through `run_condition()` / `run_matrix()`; it is not imported by normal startup. With its default `dry_run=False`, it can directly insert synthetic `fountain_insight` rows into the configured beliefs.db using raw `substrate.connect()`, tagged by `parent_belief_id=-99`, then delete those IDs in its `finally` teardown. It also changes the live mode through `POST /api/mode/set` and waits for a genuine Fountain fire. It bypasses CoherenceGate and the shared TaggingBeliefWriter wrapper. Cleanup is normal-path only; abrupt termination can leave synthetic rows. This is an experimental live-system utility, not an automatic loop. It was not run.
- **Signal repetition cleanup** — `theory_x/diversity/signal_cleanup.py` deletes all but the newest `keep_n` exact-content copies of a fountain_insight belief. It is a one-time helper; no normal startup callsite was found in run.py or the Stage 2 builder. It does not call Gate.
- **Affinity backfill** — `nex_affinity_backfill.py` is a manual affinity update/backfill path, not a new-belief producer and not a Gate path.
- **Dry synergizer sample** — `tools/synth_dry_sample.py` constructs CoherenceGate with a RecordingWriter and enforces read-only SQLite connections; it is explicitly designed not to write to the live graph. It is not a live belief writer.
- **Warrant and recorder paths** — `WarrantPass` and `WarrantRecorder` use the shared beliefs Writer to maintain side tables such as `belief_warrant`, `belief_survival` and `belief_use_day`; they do not insert/update the `beliefs` table. Their background activation is separately environment-gated.
- **Other Writer parameters are not proof of belief writes** — voice state, mode state, signal loop, Warrant, and NovelAssociation modules accept a beliefs Writer or writer-like object but their inspected SQL targets their own state/log tables, not `beliefs`.

- `HoldingZone.promote_to_belief()` inserts a held candidate after the resolver's three-ACCEPT corroboration threshold. Keep this separate from raw producer bypasses.
- `BeliefPromoter`, `Harmonizer`, `Erosion`, `AffinityLoop`, `Fountain` refresh paths and `ground_self_belief` also update existing belief rows. These updates affect tier, affinity, erosion, timestamps or content; they are not automatically new thought admissions and should not be conflated with INSERT producer counts. AffinityLoop is appended to the normal Stage 2 loop list and updates affinity on its 30-minute cadence; it is not a new-belief producer.
- `ResumptionSeeder` is called once during normal `run.py` startup. It updates `created_at` for up to five IDs in the prior `state_snapshot.json`; it does not call Gate or revalidate tier/paused/locked status. The snapshot writer's source filter is by selected source family, not an explicit active-status predicate. This is a boot-time recency promotion, not a new belief insert.
- `signal_cleanup.py::purge_signal_repetitions()` is a one-time duplicate-deletion helper for repeated fountain_insight rows. No normal run.py or Stage 2 builder callsite was found in the inspected startup path.
- `nex_affinity_backfill.py` is a separate backfill/update utility, not a normal loop.
- `IntakeResonance` writes to `intake_resonance_log`, not `beliefs`.
- `ProblemMemory` and `SignalToProblem` write to `open_problems`, not `beliefs`.
- `NovelAssociation` accepts a beliefs Writer but no `INSERT INTO beliefs` path was found in the inspected implementation; its presence in the dependency graph is not evidence of belief production.

## 4. Test-coverage observations

Static inspection of the current tests found:

- `tests/test_coherence_gate.py` covers core Gate outcomes and explicitly tests the FountainCrystallizer, Synergizer and Stage 2 Crystallizer write boundaries.
- `tests/test_reshape.py` covers reshape enqueue, transformer/resolver processing and re-submission.
- `tests/test_counterfactual_node.py` checks Gate invocation and per-candidate exception handling.
- `tests/test_throw_net_engine.py` checks per-candidate Gate calls, outcomes and exception handling.
- `tests/test_emergent_drives.py::test_apply_approved_applies_branch` calls `apply_approved()` without passing a Gate. It exercises the no-gate branch that writes the belief; it does not test the normal boot-wired Gate branch, REJECT/HOLD behavior or the gate-error path.
- The inspected test inventory contains no dedicated tests for the seven life-loop belief writers. The inspected tests also do not establish Gate-boundary behavior for sense distillation or the Fountain self-rut mirror. `tests/test_membrane.py` does enumerate `precipitated_from_sense` as an INSIDE source, but that is a classification test, not a test of the distillation writer or its gate boundary.
- No test was found for HotObserver's activation/wiring status.
- `tests/test_behavioural.py::test_write_behavioural_beliefs` exercises BSM without supplying CoherenceGate; no test was found for Gate rejection/hold or the exception-falls-through insertion boundary.

These are coverage observations, not a recommendation to add tests before the governing contract is recovered.

## 5. Phase 0 disposition

### Confirmed source facts

- The main startup path constructs and distributes one Gate instance to the listed components.
- The GUI `build_state()` function is a separate AppState construction path with its own Gate.
- CoherenceGate is fail-open on internal evaluation exceptions (`gate_error_fallback` returns ACCEPT).
- The eight consumer/re-submission paths in §2 are present in source.
- The seven Stage 2 life-loop belief writers are appended to the normal Dynamic loop list and insert beliefs directly.
- Sense distillation and Fountain's self-rut mirror are additional direct belief producers with no Gate call in their inspected insertion paths.
- BehaviouralSelfModel is a further normal-wired Stage 4 background belief producer; its ordinary path calls Gate, but its outer exception handler can fall through to insertion.
- Scorecard and self-location paths maintain/seed locked Tier 1 self-knowledge rather than ordinary generated-thought rows.
- Controlled HoldingZone promotion follows prior Gate ACCEPT corroboration.

### Unverified / authority-dependent

- Whether Frozen V2.1 defines all seven life-loop outputs, self-rut notices or perception distillation as Gate-scoped thoughts.
- Whether the source-level direct-write paths have approved exceptions.
- Whether HotObserver is activated by an out-of-band caller not found in the inspected boot paths.
- Runtime incidence, current flags, actual DB row counts, live loop status and causal effects.
- Whether the separate GUI state factory is used in any current deployment process.

### Boundary

No remediation is proposed. Do not retrofit Gate calls, suppress direct producers, change bootstrap policy, migrate writer paths or alter existing rows until the exact Frozen V2.1 authority and founder Gate 0 decision are recovered or explicitly re-established. This increment is evidence documentation only.
