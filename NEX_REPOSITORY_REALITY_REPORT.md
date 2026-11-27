# NEX v5.0 — Repository Reality Report

**Evidence date:** 27 November 2026  
**Repository:** https://github.com/kron777/Nex_v5.0  
**Source snapshot:** `main` at `612022e81f749a99de665372704d7acc0645de67`  
**Scope:** remote source and CI evidence only; this is not a host/runtime certification.

## 1. Repository identity and snapshot boundary

The source snapshot used for this report is the merged `main` commit above. The report was prepared from GitHub repository contents and commit metadata. No local checkout/worktree was available for this collection, so no clean/dirty working-tree claim is made.

Do not conflate this remote source snapshot with the host checkout described in older 25 November artefacts. Those documents describe a distinct branch/commit and a particular host collection at that time. Their branch, SHA and observations are historical evidence, not proof of the current deployed checkout.

## 2. Host, runtime and model evidence

The following current-host facts remain **UNKNOWN** in this collection:

- Whether a NEX process is running now, and which checkout/commit it uses.
- Current OS/kernel, CPU/RAM/GPU/VRAM measurements.
- Exact Python and SQLite versions on the active host.
- Ollama service/version and loaded model state.
- Exact Qwen model digest.
- Idle/load RAM and VRAM; prefill/decode throughput.
- Current user-service definitions, process ownership and service health.
- SHA-256 hashes, sizes and WAL state of the live substrate databases and runtime snapshots.

No live NEX process was started, stopped or restarted. No host database or private log was read, copied, hashed or modified. Absence of a host measurement is not evidence that a service or process is absent.

## 3. Automated test baseline

The exact M0.5 PR head `6d371fe385fc02a2c238247b39aff82681888745` passed GitHub Actions run #1392 (`45938552986`) in the repository's disposable offline test container:

- **2,491 passed**
- **7 skipped**
- **40 subtests passed**
- **0 intentional tests deselected**
- `scripts/check_test_baseline.py`: **OK**, no failures outside the known-intentional set.

The sandbox image build and sandbox probe passed. The mind-map verifier also completed without hard errors, but emitted 62 warnings (see §4). The push-triggered run on the resulting merge commit `612022e81f749a99de665372704d7acc0645de67` was still in progress when this report was drafted; its final conclusion must be appended after verification. Do not call the PR-head test result the final post-merge push result.

## 4. Mind-map verification warnings

The CI invocation `python mind_map/mind_map.py --check --verify` completed with warnings only. It reported:

- Two missing doctrine-file references: `VIRTUE_SLATE.md` and `mental_factors_inventory_alobha_spec.txt`.
- Stale `last_verified` evidence for a number of map nodes because referenced source files changed after the recorded verification dates.
- A past-due `UNBLOCK 2026-11-21` marker on `p13_finitude`.

These warnings are not test failures, and must not be hidden by deleting map entries, advancing dates without review, or weakening the verifier. They are current Phase 0 evidence gaps.

The current `mind_map/MIND_MAP.yaml` contains 39 entries under `nodes:` and 5 entries under `arms:`. The bootstrap comment and older planning references still say “30 nodes”. The 39/30 counting convention is unresolved; preserve all entries until the map owner reconciles substantive nodes, structural entries and placeholders.

The CI mind-map check includes a static AST guard. It enforces the descriptive-only metadata and rejects declared forbidden authority fields; it also scans configured runtime roots for direct imports of `mind_map` or direct `MIND_MAP.yaml` references. This is stronger than checking metadata alone, but it is still a static source guard over selected roots—not a proof against every dynamic, indirect or external authority path.

## 5. Phase 0 status

| Deliverable | Current evidence state |
|---|---|
| M0.1 repository identity | Remote repository and exact source SHA recorded; host checkout identity/cleanliness unknown |
| M0.1 host/runtime inventory | Partial/unknown; no current host collection or database hashes |
| M0.2 test baseline | PR-head full sandbox suite passed as stated above; post-merge push run pending at report cut |
| M0.3–M0.4 architecture crosswalk | Partial; documented static boot and key producer/consumer paths, not a complete faculty-by-faculty DAG |
| Roadmap v3.0 M0.5 causal trace | Implemented and merged; L3 fixture evidence; no live L4 capture |
| Gate 0 | **PENDING founder review** of the Reality Report, Crosswalk and verified defect/evidence-gap backlog |

## 6. Safety and activation boundary

The M0.5 overlay is default-OFF. `NEX5_TRACE_OVERLAY` unset or `0` means no trace is created. The CI and fixture runs do not enable it in a live process. No dark flags, behavioural experiments, prompt policies, confidence rules, Gate policy, substrate schema or deployment services were activated or changed as part of this report.

The trace sidecar performs synchronous local JSONL writes when explicitly enabled, so it can add I/O latency. The paired tests establish semantic equivalence of observed outputs and state, not identical wall-clock timing.
