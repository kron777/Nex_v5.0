# NEX v5.0 — Repository Reality Report

**Current snapshot:** 25 November 2026
**Active host checkout:** /mnt/games/storage/Desktop/Desktop/nex5
**Branch:** claude/nex-continuity-wire
**HEAD:** de93134f34adac07a3a41c2a05b33720510a2bfc
**Worktree:** host collector reported clean at this SHA.

This is the current M0.1–M0.2 reality report for the active host checkout. The earlier fb87e24 snapshot is preserved in NEX_REPOSITORY_REALITY_REPORT_HISTORICAL_fb87e24.md. The full Phase 0 branch reconciliation, boot-wiring first pass, M0.3–M0.5 status and crosswalk gaps are in NEX_PHASE0_CURRENT_RECONCILIATION_2026-11-25.md. The founder-reviewable defect backlog is NEX_PHASE0_VERIFIED_DEFECT_BACKLOG_2026-11-25.md. The `p12_selfreport` provenance distinction is recorded in NEX_PHASE0_P12_SELFREPORT_PROVENANCE_RECONCILIATION_2026-11-26.md.

## 1. Repository identity and branch divergence

- Repository: https://github.com/kron777/Nex_v5.0
- Active checkout path: /mnt/games/storage/Desktop/Desktop/nex5
- Active branch: claude/nex-continuity-wire
- Active HEAD: de93134f34adac07a3a41c2a05b33720510a2bfc
- Host collector reported a clean worktree at this SHA.
- GitHub comparison against main: active branch is 4 commits ahead and 205 commits behind; merge base fb87e247a116221cc7d814e2ee5ff2e1300f5a87.
- The active branch has 757 tree entries and 42 top-level theory_x package directories. These counts are filesystem inventories, not faculty/node counts.
- mind_map/MIND_MAP.yaml is absent from the active branch but present on main. Vitals files are also present on main but absent from the active branch.

Do not merge/rebase main wholesale into the active checkout. Main contains later changes, including unrelated behavioural changes. Branch-specific source and runtime evidence must remain distinct.

## 2. Host baseline

Read-only host collector evidence on 25 November 2026 reported:

- OS: Zorin OS 18.1, Ubuntu Noble base.
- Kernel: 7.0.0-43.
- CPU: AMD Ryzen 7 5800X.
- RAM: 24 GB.
- GPU: Radeon RX 6600, 8 GB.
- Ollama: 0.40.11.
- qwen2.5:3b is installed. The captured ollama ps output was empty, so no loaded model was verified.
- Disk: /dev/sda1 mounted at /mnt/games; 21% used at collection time.
- Python and SQLite exact versions were not recorded in the evidence available for this report.

### Model and performance unknowns

The following remain UNKNOWN:

- Exact Qwen2.5 3B model digest.
- Idle/load RAM and VRAM.
- Median prefill/decode tokens per second.
- Exact Python and SQLite versions.
- Whether a NEX process was running at collection time. The collector reported no process candidates after its filter; that is not proof that no NEX process existed.

## 3. Runtime artifact and database integrity

The host collector's runtime_artifact_hashes request was explicitly skipped by the operator. Therefore no current SHA-256 inventory of runtime databases or snapshots is available from this collection. Database identity, sizes, WAL state and snapshot hashes remain UNKNOWN.

No live NEX database was read or written during this report refresh. No private logs, secrets or runtime database files were copied into Git.

## 4. Test baseline

The founder-provided host command was:

    PYTHONPATH=. .venv/bin/python scripts/check_test_baseline.py

Reported result on the active checkout:

- 1610 passed
- 5 skipped
- 30 subtests passed
- 0 unexpected failures
- 122.87 seconds

tests/known_failures.txt contains no active test-node allowlist entries. The older report's environment-limited result (1568 collected, 107 failed, 1406 passed, 5 skipped and 62 errors) is historical and must not be presented as the current baseline.

## 5. User-service path repair and operational status

The founder approved correcting four loaded user units to the actual checkout path /mnt/games/storage/Desktop/Desktop/nex5. The founder then applied the correction. Subsequent systemctl --user cat output confirmed all four loaded definitions used the actual checkout path, and systemd-analyze --user verify reported no unit syntax errors.

No services were started or restarted. Service operation and NEX application health remain untested.

Static source inspection found that the active branch's nex_keepalive.sh still hard-coded /home/rr/Desktop/Desktop/nex5 in its initial cd and in keepalive journal/git-revision paths. If the corrected unit starts this script, it would still attempt the old path and exit before launching run.py. Draft PR #97 replaces these paths with SCRIPT_DIR derived from BASH_SOURCE[0] and passed exact-head CI (1612 passed, 5 skipped, 30 subtests); it has not been merged or deployed.

The checked-in deploy/systemd/nex5-db-reaper.service reference also retains the old path. This is a stale reference template; it does not show that the founder-corrected active user unit reverted.

## 6. Vitals status

tools/nex_vitals.py, tools/nex-vitals.service, tools/nex-vitals.timer, tools/NEX_VITALS_CRON.md and tests/test_nex_vitals.py are present on main but absent from the active host branch. They entered main through merge 7f873d1, which also changed persona/focus/frame behaviour. Cherry-picking that merge to restore Vitals would import unrelated changes.

The Vitals timer is not merely a read-only diagnostic: scheduled --log mode appends persistent measurement history. Its live environment reader trusts the PID in ~/.nex/nex.pid and reads /proc/<pid>/environ without verifying process identity against the NEX checkout. The exact governing Vitals spec referenced by its introduction was not recovered. Do not restore, enable, start, disable or delete the timer by assumption.

## 7. M0.1–M0.2 assessment

| Item | Status | Evidence / limitation |
|---|---|---|
| Repository URL, branch, full SHA | Recorded | Exact active host checkout identity above |
| Worktree state | Reported clean | Host collector snapshot at de93134 |
| Main-branch divergence | Known | 4 ahead / 205 behind; no wholesale merge |
| Host hardware and OS | Partial | OS, kernel, CPU, RAM, GPU and disk reported |
| Ollama and model | Partial | Ollama version and installed model known; model digest/load unknown |
| Python / SQLite versions | UNKNOWN | Not recorded |
| Runtime DB/snapshot SHA-256 | UNKNOWN | Hash request skipped by operator |
| RAM/VRAM and token throughput | UNKNOWN | No idle/load benchmark captured |
| Test baseline | Current run reported clean | 1610 passed, 5 skipped, 30 subtests, 0 unexpected failures |
| Failure reconciliation | Partial | No current unexpected failures reported; older environment-limited result preserved as history; V2.1 `p12_selfreport` failure identity/classification unresolved |

**M0.1 and M0.2 remain partial.** The 1610-pass run is the reported current active-branch baseline, but it does not close M0.2 while the V2.1 `p12_selfreport` failure identity/classification remains unresolved. See the provenance reconciliation note.

## 8. Governance and next gate

Gate 0 remains PENDING. The founder must review the current Reality Report, current Crosswalk and verified defect backlog before Phase 1 behavioural experiments/fixes. A general instruction to continue development is not treated as Gate 0 sign-off.

Do not activate the default-OFF continuity feature from f9ac58d. Do not start/restart services, modify live DBs, alter protected experiments R79–R83, baselines or tripwires, or merge/deploy the prepared PRs without the relevant explicit approval.

See NEX_PHASE0_CURRENT_RECONCILIATION_2026-11-25.md for the full branch-specific Phase 0 status, boot-wiring inventory, M0.3–M0.5 gaps and RDO/Watcher cross-check.