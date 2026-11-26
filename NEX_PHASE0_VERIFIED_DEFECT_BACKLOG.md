# NEX Phase 0 Verified Defect and Reconciliation Backlog
## Evidence pinned to main 49b1d6c0b247b5694259e1225d077fc60e5c3706 — 27 November 2026

This backlog distinguishes confirmed source defects from documentation drift, missing evidence and unresolved governance. It is not a permission to alter protected experiments or live runtime state.

| ID | Classification | Finding | Evidence / impact | Disposition |
|---|---|---|---|---|
| D-01 | Confirmed source-contract discrepancy | Fountain writes recursion_attrib directly using substrate.connect(), and momentum.capture_momentum() also opens its own SQLite connection, despite substrate/writer.py defining Writer as the sole write path. | Source-level direct commits in the Fountain main path. This bypasses the one-pen Writer contract and complicates tracing, serialization and auditing. No host execution is claimed. | Preserve as a bounded defect. Map exact writer ownership and tests before proposing a code change. Do not alter live DBs. |
| D-02 | Documentation drift | Stage 2 Dynamic documentation understates the factory's current loop registrations. | Factory source registers nine unconditional core loops plus optional loop groups behind guarded imports/configuration. | Correct module documentation only after exact factory inventory and test/CI check. |
| D-03 | Documentation drift | Stage 3 World Model documentation describes two workers while its factory starts six. | Factory source and worker start calls. | Correct module documentation only; do not change loop membership or cadence. |
| D-04 | Missing repository references | mind_map/MIND_MAP.yaml metadata lists VIRTUE_SLATE.md and mental_factors_inventory_alobha_spec.txt, neither of which exists anywhere in the complete main Git tree. | Complete recursive Git tree search. SENTIENCE_SYNTHESIS.md is present. | Resolve references against the actual governing documents. Do not invent replacement doctrine or silently delete frozen doctrine links. |
| D-05 | Documentation / verification drift | Mind map was built 2026-11-09 and its node last_verified dates run through 2026-11-20; the map is not a 27-Nov re-verification of all 30 nodes. | MIND_MAP.yaml metadata. Its policy makes last_verified dates and source references meaningful. | Treat each node date as the last recorded verification; do not bulk-refresh dates without checking each node/source. |
| D-06 | Documentation drift | ARCHITECTURE.md and SENTIENCE_PROGRAM.md do not fully describe the present run.py construction/start order, optional flags and retired diagnostic components. | Current boot source vs high-level architecture docs. The scheduler-specific drift was corrected by PR #148. | Keep the current source crosswalk as the factual map; amend individual canonical docs only where the governing roadmap directs. |
| D-07 | Policy risk requiring founder decision, not an inferred defect fix | CoherenceGate.check() returns ACCEPT / gate_error_fallback when evaluation raises. | Verified exception path, documented by PR #149. This is fail-open, not fail-closed. | Do not change automatically. Capture the availability-vs-integrity trade-off for Gate 0 policy review. |
| E-01 | Missing host evidence (not a code defect) | No host-origin Watcher result was available in this cloud audit. | Watcher README requires local watcher host-collect and provenance-aware ingestion; host runtime remains STANDBY/UNKNOWN. | Keep runtime evidence L0. Obtain host evidence through the approved passive local collection procedure; do not fabricate a host report. |
| E-02 | Missing runtime evidence (not a code defect) | No active NEX process, service tree, current hardware/OS/model versions or live database hashes were observed. | GitHub/cloud inspection only. | Keep all host-specific claims UNKNOWN until host-origin results arrive. |
| E-03 | Unproven end-to-end validation (not a code defect) | RDO Stage 7 is not complete. | Stage 7 handoff reports a controlled fixture only; no full real objective-to-delivery cycle, no authorised test execution and no host runtime proof. | Do not promote Stage 7 or declare the RDO fully validated because its PRs merged. |

## Test baseline and current candidate

- Mainline last verified full disposable-suite baseline for the PR #148 mainline candidate: 2,453 passed, 7 skipped; sandbox probe and mind-map verification completed.
- tests/known_failures.txt is empty at the pinned snapshot.
- M0.5 trace PR #151 is a separate candidate and is not part of this pinned main baseline. One full run exposed five test-only issues in tests/test_influence_trace.py (three undefined _sink references and two TraceContext constructors missing producer). These were corrected on the PR branch; a new exact-head sandbox run is pending. Do not classify these transient branch test failures as main defects.

## Ordering constraints

1. Keep Phase 0 read-only evidence work separate from behavioural development.
2. Finish exact-head M0.5 tests and fixture traces; do not enable NEX5_TRACE_OVERLAY on live NEX.
3. Resolve the direct SQLite/Writer contract finding through a separate bounded design decision and tests; no live database mutation.
4. Obtain Watcher host evidence before assigning any L4 runtime evidence.
5. Gate 0 remains open until the founder reviews and approves the Reality Report, Crosswalk and this backlog.
6. Do not start Phase 1 or change experiment flags/specifications under this backlog.
