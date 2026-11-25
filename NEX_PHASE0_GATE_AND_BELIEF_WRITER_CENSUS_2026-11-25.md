# NEX Phase 0 — CoherenceGate and Belief-Writer Census (25 November 2026)

## Scope and evidence boundary

This is a bounded static-source continuation of the Phase 0 producer/consumer trace. The primary source baseline is the active host branch `claude/nex-continuity-wire` at `de93134f34adac07a3a41c2a05b33720510a2bfc`.

The audit follows the prescribed next increment in `NEX_PHASE0_PRODUCER_CONSUMER_TRACE_TRANCHE_2026-11-25.md` §8: map gate callers and belief writes, separating external perception, internal generation, self-observation, bootstrap anchors and controlled promotion.

This is a source-level census of the high-priority runtime paths and adjacent producer modules listed below. It is not a formal AST-backed exhaustive scan of every Python file, and it does not establish live thread execution, current environment flags, database contents, write frequency or behavioural effect. No live service or database was opened. No runtime code, tests, flags, schema, service, experiment, baseline, tripwire or deployment setting was changed.

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

4. **HotObserver** — `theory_x/stage_tom/hot_observer.py` contains a direct Tier 3 belief insertion through `substrate.connect()`. However, the inspected `run.py`, `gui/server.py` and `theory_x/stage_tom/__init__.py` do not show a normal boot import/wiring path for HotObserver. It is therefore recorded as a module-level writer whose normal runtime activation is unverified, not counted as a confirmed boot-wired producer.

### C. Self-knowledge and bootstrap writes — not ordinary generated-thought producers

- **SelfLocationCommitment** — `theory_x/stage5_self_location/commitment.py` idempotently inserts a locked Tier 1 `self_location` anchor during boot. This is a bootstrap commitment, not an ordinary generated thought.
- **Grounded scorecard self-belief** — `ground_self_belief.py` inserts the locked Tier 1 `grounded_scorecard:market_direction_v1` belief if absent, otherwise updates its content/confidence/timestamp in place. `theory_x/life/scorecard_loop.py` is appended to the Stage 2 loop list; it runs once immediately and then hourly. This is a measured self-knowledge refresh, not a new thought on every tick.
- **Keystone and koan seeds** — `keystone.py` and `substrate/koan_seeds.py` contain boot-seed inserts. The prior trace §60 records that these run during substrate initialisation before the runtime TaggingBeliefWriter wrapper is installed. Their bootstrap status should remain distinct from runtime cognition producers.
- **Spectrum seed paths** — `substrate/seed/load_spectrum.py` and `substrate/spectrumizer_process.py` contain spectrum-belief inserts. These are seed/import paths, not normal live generative loops.
- **Identity seed utility** — `scripts/seed_identity_beliefs.py` contains an insert, but is an explicit script path rather than a normal boot loop.

### D. Controlled promotion and maintenance

- `HoldingZone.promote_to_belief()` inserts a held candidate after the resolver's three-ACCEPT corroboration threshold. Keep this separate from raw producer bypasses.
- `BeliefPromoter`, `Harmonizer`, `Erosion`, `AffinityLoop`, `Fountain` refresh paths and `ground_self_belief` also update existing belief rows. These updates affect tier, affinity, erosion, timestamps or content; they are not automatically new thought admissions and should not be conflated with INSERT producer counts.
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

These are coverage observations, not a recommendation to add tests before the governing contract is recovered.

## 5. Phase 0 disposition

### Confirmed source facts

- The main startup path constructs and distributes one Gate instance to the listed components.
- The GUI `build_state()` function is a separate AppState construction path with its own Gate.
- CoherenceGate is fail-open on internal evaluation exceptions (`gate_error_fallback` returns ACCEPT).
- The eight consumer/re-submission paths in §2 are present in source.
- The seven Stage 2 life-loop belief writers are appended to the normal Dynamic loop list and insert beliefs directly.
- Sense distillation and Fountain's self-rut mirror are additional direct belief producers with no Gate call in their inspected insertion paths.
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
