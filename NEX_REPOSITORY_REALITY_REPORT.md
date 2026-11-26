# NEX Repository Reality Report
## Phase 0 baseline — 27 November 2026

**Scope:** GitHub/cloud source inspection of the repository snapshot identified below. This report is not a host collection and does not claim that a deployed NEX process was observed.

## 1. Repository identity and provenance

- Repository: https://github.com/kron777/Nex_v5.0
- Default branch: main
- Snapshot commit: 49b1d6c0b247b5694259e1225d077fc60e5c3706
- Snapshot meaning: latest main commit verified during this audit; it includes the SenseScheduler documentation correction merged in PR #148.
- Repository access: the connected GitHub integration reported write permission.
- Local checkout path, local branch, detached/attached state, local HEAD and dirty working-tree status: UNKNOWN. GitHub's remote branch view does not reveal the state of the founder's workstation.
- No local NEX source checkout or host shell was available to this audit. A remote cloud file read is not a substitute for local Git status.

## 2. Repository size and source inventory

- The recursive Git tree was complete (not truncated).
- Python files beneath theory_x/: 273.
- Root entries at the time of inspection: 78.
- mind_map/MIND_MAP.yaml: 30 descriptive nodes across five arms.
- sentience_dag.json: 15 dependency/build-order nodes.
- The mind map, DAG and Python package inventory are different inventories and must not be treated as interchangeable.
- Many theory_x subpackages have empty __init__.py files. Their presence is not proof that they are independent faculties or booted services. Capability claims require source, boot and consumer evidence.

## 3. Test and CI baseline

The mainline disposable-container CI run associated with PR #148 completed successfully. The verified test summary was:

- 2,453 passed
- 7 skipped
- Mind-map verification completed
- No non-allowlisted baseline failure was reported

The repository's tests/known_failures.txt was empty at the inspected main snapshot. scripts/check_test_baseline.py was present and the CI workflow ran it before the mind-map verification.

The test environment is a GitHub Actions-built disposable container. The verified isolation probe reported: unprivileged execution, no capabilities, no credentials, read-only source, disposable data/tmpfs, no default route and no outbound network. This is evidence about the CI container, not the founder's host.

A separate candidate implementation for M0.5 causal tracing is being validated in PR #151. Its intermediate test runs are not part of the mainline baseline and must not be silently merged into this report's mainline result. An earlier completed intermediate run found five test-fixture mistakes (undefined _sink references and missing TraceContext producer arguments); those were corrected on the candidate branch. The candidate now includes paired full OFF/ON Fountain and Chat fixture cycles and explicitly distinguishes direct SQLite commits from Writer deltas. Its exact current head remains unmerged while disposable CI completes; this does not change the verified mainline baseline above.

## 4. Host, process, model and deployment facts

The following are UNKNOWN in this cloud-only audit:

- Host OS release/kernel, hardware inventory, GPU driver/runtime, memory and storage health.
- Python and SQLite versions on the founder's NEX host.
- Local repository path, local HEAD, dirty state and uncommitted changes.
- Active service-manager units, actual process tree, process command lines and environment.
- Which NEX services are running, stopped, retired or failing on the host at the time of observation.
- Ollama/llama-server version, model files actually installed, model loaded in memory, effective quantisation and actual request success.
- Current runtime flags and whether any experimental path is enabled on the host.
- Live state of the six substrate databases, their schema/version, sizes and hashes.
- Whether current model, configuration and data paths match the checked-in source.

The source contains historical deployment comments and launch scripts, but these are not observations of the current machine. They must not be promoted to runtime evidence.

## 5. Substrate and persistence

The source defines six principal substrate databases and a one-pen Writer abstraction. The Writer performs explicit transactions and is intended to own writes to its database. This audit did not inspect, hash, open or copy any live host database.

A source-level exception was found in the Fountain path: recursion_attrib uses a direct substrate.connect() write transaction rather than the Writer abstraction. The momentum helper also opens a direct SQLite connection for its upsert. These are source-level persistence facts; they do not establish whether the corresponding paths ran on the current host.

## 6. Architecture snapshot

The checked-in run.py constructs a broader set of capabilities than the older high-level architecture prose suggests. It wires the sense scheduler, dynamic formation, world model, membrane, gate/resolver, problem memory, goal manager, metacognition, drive systems, affect, prediction, Fountain, speech, signal detection, diversity, edge generation, tool use and other optional or diagnostic components.

Construction, loop start calls, emitted events, downstream consumption and live host operation are separate evidence states. This report records source wiring only. No claim is made that every started daemon completed useful work or that every external feed connected successfully.

## 7. Watcher and RDO relationship

Watcher and RDO are external engineering/observation packages, not NEX cognitive faculties:

- Watcher PR #46 and its chained host-evidence/service-integrity work are merged into main. The Watcher README says its cloud collectors establish static/GitHub evidence; live host evidence requires the local host-collect command and explicit ingestion. The README says the runtime graph remains STANDBY until host evidence exists.
- No host_results.json or equivalent host-origin collection was established by this audit. Current host/runtime evidence therefore remains UNKNOWN.
- RDO Stages 2–7 are present in the repository, but the RDO Stage 7 handoff explicitly does not claim end-to-end completion. A fixture is not a real objective-to-delivery run, and host runtime remains UNKNOWN.
- RDO remains advisory and external; it must not mutate NEX runtime or authorise protected work.

## 8. Gate and phase boundary

The Master Roadmap v3.0 places the Phase 0 deliverables behind Gate 0. The roadmap's exit condition requires founder review and approval of the Reality Report, Architecture Crosswalk and verified defect backlog before Phase 1 behavioural changes.

This report does not constitute founder approval, does not close Gate 0 and does not authorise Phase 1. No live experiment, behavioural flag, database state or deployment was changed during this audit.

## 9. Evidence summary

| Claim | Evidence class | Basis |
|---|---|---|
| Main snapshot commit and tracked source | L2 STATIC | GitHub tree/file/commit metadata |
| 273 theory_x Python files | L2 STATIC | Complete recursive Git tree |
| 30 mind-map nodes / five arms | L2 STATIC | MIND_MAP.yaml |
| 15 DAG nodes | L2 STATIC | sentience_dag.json |
| Mainline test suite 2,453 passed / 7 skipped | L3 OBSERVED | Completed disposable CI run associated with PR #148 |
| CI sandbox isolation probe passed | L3 OBSERVED | CI sandbox probe output |
| NEX host OS/hardware/process/model/database state | L0 UNKNOWN | No host-origin collection |
| Current live runtime behaviour | L0 UNKNOWN | No authorised host runtime capture |
| Current local working-tree cleanliness | L0 UNKNOWN | No local checkout status |

## 10. Source anchors

- mind_map/MIND_MAP.yaml
- mind_map/mind_map.py
- sentience_dag.json
- nex_next_dev.py
- ARCHITECTURE.md
- SENTIENCE_PROGRAM.md
- run.py
- substrate/writer.py
- substrate/db.py
- theory_x/stage1_sense/__init__.py
- theory_x/stage1_sense/scheduler.py
- theory_x/stage2_dynamic/__init__.py
- theory_x/stage3_world_model/__init__.py
- theory_x/stage4_membrane/__init__.py
- theory_x/stage6_fountain/__init__.py
- theory_x/stage6_fountain/generator.py
- theory_x/stage6_fountain/crystallizer.py
- theory_x/stage_tom/momentum.py
- watcher/README.md
- rdo/README.md
- rdo/STAGE7_HANDOFF.md
