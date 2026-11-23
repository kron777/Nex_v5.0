# NEX Repository Reality Report

**Status:** Working evidence draft — not a Gate 0 submission  
**Inspection date:** 2026-11-23  
**Inspected revision:** `6e6712bd4bde15ad2288f220cd4438b11622c93c`  
**Repository:** https://github.com/kron777/Nex_v5.0  
**Branch inspected:** `main`  
**Authority:** Founder Sign-Off > Frozen V2.1 Spec > Runtime Truth > Master Roadmap v3.0

> This report records what was verifiable from the public GitHub repository and the supplied governing documents. It does not represent a local checkout inspection or a live-host measurement. UNKNOWN means evidence was not available; it does not mean the capability or condition is absent.

## 1. Executive finding

The inspected public `main` branch was at the revision above. The repository exposes a substantial Python codebase, a CI test-baseline workflow, a sourced descriptive mind map, a separate dependency DAG, and multiple runtime pathways. The repository's current Phase 0 evidence package is incomplete.

The following are established from repository evidence:

- The default branch is `main`.
- `scripts/check_test_baseline.py` runs pytest and deselects only node IDs listed in `tests/known_failures.txt`.
- The current allowlist contains explanatory comments but no active pytest node IDs.
- The GitHub Actions workflow invokes the baseline script and the mind-map source/status check.
- The tests directory contains 182 files matching `test_*.py` at the inspected revision. This is a file inventory, not a count of collected test cases or a fresh test result.
- The boot path constructs the CoherenceGate and passes it into Fountain construction.
- The Chat route has its own context assembly and optional Chat Workspace selection path.
- The required Phase 0 reports and a genuine causal trace sample were not present on `main` at inspection.

## 2. Repository provenance

| Field | Finding | Evidence |
|---|---|---|
| Repository | `kron777/Nex_v5.0` | GitHub repository metadata |
| Default branch | `main` | GitHub repository metadata |
| Inspected branch | `main` | GitHub branch API |
| Full HEAD | `6e6712bd4bde15ad2288f220cd4438b11622c93c` | GitHub branch API |
| Local working tree | UNKNOWN | No local checkout/worktree access in this inspection |
| Local remotes / ignored files / untracked files | UNKNOWN | Not visible through the public repository API |
| Deployed runtime revision | UNKNOWN | No live host access |
| Runtime database hashes | NOT COLLECTED | Requires approved host-side read-only hashing |

A GitHub branch snapshot cannot establish whether a separate local or deployed checkout contains uncommitted work.

## 3. Source and test baseline

### 3.1 Baseline runner

Source: `scripts/check_test_baseline.py`  
Blob SHA: `748d80d0c1f09826af993429e843eeed09696639`

The script:

1. Reads `tests/known_failures.txt`.
2. Ignores blank lines and comments.
3. Runs the current Python interpreter with `-m pytest -q --tb=short`.
4. Adds one `--deselect` argument per active allowlist entry.
5. Sets `PYTHONPATH` to the repository root if not already set.
6. Returns non-zero if pytest fails or collection/environment fails.

The runner's docstring describes the allowlist as intentional failures, but the current file contains no active node IDs. The baseline therefore has no active test exclusions at this revision.

### 3.2 Known-failure inventory

Source: `tests/known_failures.txt`  
Blob SHA: `313fd886b4ede45b8b0222782aba30b6d4139649`

The file contains 18 lines, all comments. It states that the previous one-pen compliance-ratchet exclusions were retired on 2026-10-17. No active test failure is declared in this file.

This does not establish that the suite currently passes locally.

### 3.3 Test inventory and CI

- `tests/` contains 182 `test_*.py` files in the GitHub directory listing.
- The CI workflow is `.github/workflows/tests.yml`.
- The workflow invokes `python scripts/check_test_baseline.py`.
- The workflow also invokes `python mind_map/mind_map.py --check --verify`.
- The main-branch Actions run previously inspected for this revision completed successfully: https://github.com/kron777/Nex_v5.0/actions/runs/44771704123

**Fresh baseline:** NOT RUN in this session.  
**Collected pytest case count:** UNKNOWN.  
**Failure classification:** No fresh failure output exists to classify.

Do not translate a successful historical CI run into a claim that the current host environment has passed.

## 4. Host and model baseline

The roadmap's target host description is Zorin OS / Ryzen 7 5800X / Radeon 8 GB. This is a target description, not a measurement captured during this inspection.

| Measurement | Result | Required evidence |
|---|---|---|
| Host OS/version | UNKNOWN | `cat /etc/os-release` |
| CPU model | UNKNOWN on deployed host | `lscpu` |
| GPU model/driver | UNKNOWN on deployed host | `lspci -nnk`, `rocminfo` or approved vendor tool |
| Physical RAM | UNKNOWN | `free -h` |
| Python version | UNKNOWN | `python3 --version` in NEX environment |
| SQLite runtime version | UNKNOWN | `python3 -c 'import sqlite3; print(sqlite3.sqlite_version)' ` in NEX environment |
| Ollama version | UNKNOWN | `ollama --version` |
| Qwen model tag | Source default is `qwen2.5:3b` in `run.py`; deployed selection UNKNOWN | Redacted runtime configuration |
| Exact model digest | UNKNOWN | `ollama list` plus model metadata/digest |
| Idle RAM/VRAM | UNKNOWN | Approved idle sample |
| Loaded RAM/VRAM | UNKNOWN | Approved representative workload sample |
| Median generation throughput | UNKNOWN | Repeated, documented tokens/sec measurement |

No host command was executed and no runtime flag, process or database was touched.

## 5. Failure classification

| Class | Current result |
|---|---|
| Confirmed code defect | UNKNOWN — no fresh suite output |
| Stale test | UNKNOWN — no fresh suite output |
| Environment / missing dependency | UNKNOWN — no fresh host run |
| Collection error | UNKNOWN — no fresh host run |

The absence of active entries in `known_failures.txt` is not proof that there are no failures.

## 6. Required host-side capture

When the approved host is available, capture the following in one timestamped, read-only session:

1. `git -C <checkout> rev-parse HEAD`, `git status --short --branch`, `git remote -v`.
2. Record the actual deployed checkout separately from any development checkout.
3. Capture OS, CPU, GPU/driver, RAM, Python, SQLite and Ollama versions.
4. Capture the exact Qwen model digest without copying credentials or private prompts.
5. Record idle resource use over a defined interval.
6. Run one agreed representative load and record peak/median RAM, VRAM and generation throughput.
7. Run `PYTHONPATH=. python3 scripts/check_test_baseline.py` from the repository root and preserve complete stdout/stderr, exit code, duration, interpreter and environment.
8. Reconcile every non-allowlisted failure into confirmed defect, stale test, environment/missing dependency, or unresolved.
9. Hash only explicitly approved runtime DB/snapshot files in place; do not copy private logs or secrets into Git.

Do not run live probes, change flags, restart NEX or write to runtime databases as part of this capture.

## 7. Phase 0 deliverable status

| Deliverable | Status at inspected revision |
|---|---|
| Repository identity | REMOTE VERIFIED |
| Local worktree identity/dirty state | UNKNOWN |
| Host/model baseline | BLOCKED — host evidence unavailable |
| Fresh test baseline | NOT RUN |
| Known-failure reconciliation | PARTIAL — allowlist inspected; no fresh failures |
| Architecture crosswalk | PARTIAL — see `NEX_ARCHITECTURE_CROSSWALK_v2.md` |
| ADR-001 | DRAFT — see `ADR-001.md` |
| Causal trace sample | NOT COLLECTED — no live/approved capture |

## 8. Limitations and next evidence

This is a source-and-GitHub report, not a local checkout or runtime report. It does not establish the deployed code revision, process topology, runtime flags, current model digest, current resource profile, or current behavioural operation.

The report must be updated after host measurements and a fresh test run. Gate 0 must not be declared ready from this document alone.

## 9. Source manifest

Inspected at `6e6712bd4bde15ad2288f220cd4438b11622c93c`:

- `scripts/check_test_baseline.py` — `748d80d0c1f09826af993429e843eeed09696639`
- `tests/known_failures.txt` — `313fd886b4ede45b8b0222782aba30b6d4139649`
- `run.py` — `73a2c58a4f5f0348135a46eb83d6cdd61db874e7`
- `mind_map/MIND_MAP.yaml` — `cb7e54052b0c5c8bee8b257fd196630093dbe567`
- `sentience_dag.json` — `687cd854913714193622468bd64a6f872f5b7854`
- `ARCHITECTURE.md` — `e60f7b9c60081a3f8b24a32484ecd4a0adc0ca1a`
- `SENTIENCE_PROGRAM.md` — `3c5a82f1bed3d814c3b63b9557ae588cb8042016`
- `.github/workflows/tests.yml` — `c17858ca7fe83f85610937362d92ebe9bffd63b2`
- `theory_x/stage6_fountain/generator.py` — `43644876295ffdd649a240f52a7946c666a8579f`
- `theory_x/stage6_fountain/crystallizer.py` — `4b5c1633d91c9502347c9d9774e39dc74be7c5b4`
- `theory_x/stage_tom/global_workspace.py` — `54ddab05112702eef34faaa4f24d45139350b349`
- `theory_x/stage_gate/coherence_gate.py` — `39f73108cb36e886cfc8dafe045646acba15549e`
- `gui/server.py` — `5ee8b167f386466c383090445c63a84810bbae52`
- `substrate/writer.py` — `b5b7bc98fcb39e75683188fbc59f33adf8868741`

**Status rule:** All source claims above are revision-bound. Re-check the branch SHA before relying on this report after any new commit.
