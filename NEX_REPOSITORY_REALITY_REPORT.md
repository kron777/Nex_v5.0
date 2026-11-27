# NEX v5.0 — Repository Reality Report

**Evidence date:** 27 November 2026  
**Repository:** https://github.com/kron777/Nex_v5.0  
**Historical source snapshot:** `main` at `ae406fa8fcb1abdf25cdf4ae1bd65333e1148ca8`  
**Scope:** remote source and CI evidence only; this is not a host/runtime certification.

## 1. Repository identity and snapshot boundary

> **Historical evidence warning (27 November 2026):** this report was collected at `ae406fa8fcb1abdf25cdf4ae1bd65333e1148ca8`. Current main has since advanced 44 commits to `9f5a9f0b476716b6a6fd0a39aa3cf3041a3a4465`. This report is retained as a historical evidence record and orientation aid. It is not a current-main certification. Revalidate source paths, test results and CI before using any finding for a current engineering decision. Do not simply replace the SHA or date without repeating the audit.

The source snapshot used for this report is the current remote `main` commit above (27 November 2026, 06:27 UTC). The report was refreshed from GitHub repository contents, commit metadata and the exact mainline CI run. No local checkout/worktree was available for this collection, so no clean/dirty working-tree claim is made.

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

The exact M0.5 PR head `6d371fe385fc02a2c238247b39aff82681888745` passed GitHub Actions run #1392 (`45938552986`) in the repository's disposable offline test container (historical baseline):

- **2,491 passed**
- **7 skipped**
- **40 subtests passed**
- **0 intentional tests deselected**
- `scripts/check_test_baseline.py`: **OK**, no failures outside the known-intentional set.

The exact PR-head run #1392 (`45938552986`) passed: 2,491 passed, 7 skipped, 40 subtests, zero intentional tests deselected, baseline OK. A separate push run #1393 (`45939220368`) ran on parent commit `612022e81f749a99de665372704d7acc0645de67`, before PR #153 merged; it is not post-merge evidence for commit `66a9796` and must not be labelled as such. The latest current-main run below is the valid green baseline for this report.

The latest current-main run at `ae406fa8fcb1abdf25cdf4ae1bd65333e1148ca8` (GitHub Actions run `45951932639`) completed successfully: **2,508 passed, 7 skipped, 40 subtests passed**, baseline OK, in 182.51 seconds. The current mind-map verifier completed without hard errors and emitted 61 verifier warnings (see §4).

## 4. Mind-map verification warnings

The CI invocation `python mind_map/mind_map.py --check --verify` completed with warnings only. It reported:

- Two missing doctrine-file references: `VIRTUE_SLATE.md` and `mental_factors_inventory_alobha_spec.txt`.
- Stale `last_verified` evidence for a number of map nodes because referenced source files changed after the recorded verification dates.
- A past-due `UNBLOCK 2026-11-21` marker on `p13_finitude`.

The current-main run reports 58 stale-source warnings, 2 missing doctrine-file references and 1 past-due `p13_finitude` unblock marker (61 verifier warnings total). These warnings are not test failures, and must not be hidden by deleting map entries, advancing dates without review, or weakening the verifier. They are current Phase 0 evidence gaps.

The current `mind_map/MIND_MAP.yaml` contains exactly 30 entries under `nodes:` (18 arm, 9 ring, 2 boundary and 1 straddle), 5 entries under `arms:`, and 4 under `findings:`. The earlier “39 nodes” count incorrectly aggregated those three separate sections (30 + 5 + 4). The 30-node convention is correct; no map entries were changed.

The CI mind-map check includes a static AST guard. It enforces the descriptive-only metadata and rejects declared forbidden authority fields; it also scans configured runtime roots for direct imports of `mind_map` or direct `MIND_MAP.yaml` references. This is stronger than checking metadata alone, but it is still a static source guard over selected roots—not a proof against every dynamic, indirect or external authority path.

## 5. Phase 0 status

| Deliverable | Current evidence state |
|---|---|
| M0.1 repository identity | Remote repository and exact source SHA recorded; host checkout identity/cleanliness unknown |
| M0.1 host/runtime inventory | Partial/unknown; no current host collection or database hashes |
| M0.2 test baseline | Current main `ae406fa8`: 2,508 passed, 7 skipped, 40 subtests; baseline OK (run `45951932639`) |
| M0.3–M0.4 architecture crosswalk | Partial; documented static boot and key producer/consumer paths, not a complete faculty-by-faculty DAG |
| Roadmap v3.0 M0.5 causal trace | Implemented and merged; L3 fixture evidence; no live L4 capture |
| Gate 0 | **PENDING founder review** of the Reality Report, Crosswalk and verified defect/evidence-gap backlog |

## 6. Source documentation reconciliation

The remaining boot/API overview discrepancies were corrected in PR #153 and merged before this snapshot: `run.py` describes six DBs and the 28-adapter auto-start sequence; the GUI sense-status overview reports 28 adapters (4 internal, 24 external). Since the earlier `66a9796` snapshot, current main also merged one-pen Writer migrations for EdgeBuilder (#158), FocusLoop (#159), RememberLoop (#160), Fetch/Wonder (#163), Surprise (#165), and Pattern/Witness (#164). The remaining in-flight persistence migrations are tracked separately and are not represented as merged.

## 7. Safety and activation boundary

The M0.5 overlay is default-OFF. `NEX5_TRACE_OVERLAY` unset or `0` means no trace is created. The CI and fixture runs do not enable it in a live process. No dark flags, behavioural experiments, prompt policies, confidence rules, Gate policy, substrate schema or deployment services were activated or changed as part of this report.

The trace sidecar performs synchronous local JSONL writes when explicitly enabled, so it can add I/O latency. The paired tests establish semantic equivalence of observed outputs and state, not identical wall-clock timing.
