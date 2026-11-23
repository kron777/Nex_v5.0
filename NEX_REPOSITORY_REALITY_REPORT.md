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
| Confirmed code defect | One conditional source-confirmed fallback defect on draft PR #65; focused test added; PR #65 full pytest passed; host impact UNKNOWN |
| Stale test | UNKNOWN — no fresh suite output |
| Environment / missing dependency | UNKNOWN — no fresh host run |
| Collection error | UNKNOWN — no fresh host run |

The absence of active entries in `known_failures.txt` is not proof that there are no failures.

**Later Phase 0 branch finding (not part of the inspected `main` snapshot):** PR #65 source inspection found a conditional speech-consumer defect. `Reader.read()` returns `sqlite3.Row`, but `SpeechQueueConsumer._speak_one()` falls back to `row.get("voice")` when `voice_state.current_name()` returns an empty value or raises; `sqlite3.Row` has no `.get()` method. Normal `run.py` startup supplies `voice_state`, so this is a fallback-path defect, not evidence that the ordinary boot path fails. A focused test documents the row type; PR #65's combined full pytest run passed (run `45243112976`). No runtime failure has been observed.

### 5.1 Verified defect backlog — working, non-exhaustive

The following items are source-confirmed in the current Phase 0 draft stack. They are not live-host failure reports, and no repair is authorised or included here.

| Ref | Finding | Trigger / impact boundary | Evidence | Status |
|---|---|---|---|---|
| DRAFT-001 | Speech consumer's voice fallback calls `row.get("voice")`, but `Reader.read()` returns `sqlite3.Row`, which has no `.get()` method. | Reached only when `voice_state.current_name()` returns an empty value or raises. Normal `run.py` startup supplies `voice_state`; the ordinary boot path is not shown to hit this fallback. | Source inspection and a focused isolated test on PR #65; combined PR #65 pytest run `45243112976` passed. | Source-confirmed conditional defect; host frequency/impact UNKNOWN. |
| DRAFT-002 | ToolCaller routes natural-language calculation patterns to `python_exec`, but `build_tool_kwargs()` passes the original query with an empty `code`; ToolRegistry then substitutes the natural-language query as Python source. | Queries such as `calculate 15 * 37` match the math heuristic, but are passed to `python3 -c` as invalid Python syntax. The tool returns failure and Chat does not inject the result because it only appends successful tool results. | Source inspection of `tool_caller.py`, `tools.py`, and `gui/server.py`; existing `tests/test_tools.py` tests routing and direct Python code separately but not the integrated natural-language execution hand-off. | Source-confirmed conditional integration defect; live incidence/impact UNKNOWN. |
| DRAFT-003 | Membrane query classification uses substring membership for the token `"you"`, so the product name `YouTube` is treated as a self-inquiry marker. | A world query such as `how do I use YouTube` contains the substring `you`; `classify_query()` therefore returns INSIDE, routing Chat to the self-model/INSIDE retrieval branch rather than ordinary OUTSIDE retrieval. This is deterministic from the current classifier implementation. | Source inspection of `theory_x/stage4_membrane/classifier.py`; `tests/test_membrane.py` covers representative self-inquiry and world queries but has no YouTube/product-name boundary case. | Source-confirmed conditional routing defect; live incidence/impact UNKNOWN. |

No severity, priority or remediation is assigned pending the full runtime/call-path audit and the higher-authority Frozen V2.1 acceptance constraints. DRAFT-002 and DRAFT-003 are source-level conditional findings; their actual runtime frequency and user impact remain UNKNOWN. The list is not exhaustive: other defect classes remain UNKNOWN until the fresh test baseline and approved host capture are completed.

**Evidence-branch CI note (23 Nov 2026):** PR #49's current run `45243207500` failed. The focused authority-boundary test failure was reproduced as a false positive caused by two module docstrings containing map filenames; the test has been corrected to ignore docstrings while retaining executable literal-reference and import checks. The full CI log was unavailable, so it is not known whether this was the only failure. A new PR #49 run is required before the evidence branch can be described as green. This note does not change the report's inspected-main revision above.

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

**Evidence-branch CI update (23 Nov 2026):** PR #49's corrected head `bbbd86bce7d24e2583aa1c882910915fc1914448` passed the full pytest workflow and the `Mind map stays sourced (no stale status claims)` step in run `45249262986`. The preceding run `45243207500` failed; focused reproduction showed the authority-boundary scan incorrectly matched map filenames in module docstrings. The guard now excludes module/class/function docstrings while retaining executable literal-reference and direct-import checks. The complete failed-run log was unavailable, so it is not established that the docstring false positive was the only failure. PR #65's combined full pytest run `45243112976` also passed. These CI results do not establish host behaviour or Gate 0 readiness.


**Additional source finding (23 Nov 2026, PR #65 integrated branch):** DRAFT-002 was identified by following the Chat tool path end to end. `ToolCaller.should_use_tool()` selects `python_exec` for natural-language calculation patterns; `build_tool_kwargs()` returns the query plus an empty code string; `ToolRegistry._python_exec()` then uses the query itself as code. A normal phrase such as `calculate 15 * 37` is not valid Python source, so the subprocess returns a syntax error and `api_chat` omits the unsuccessful result from the prompt. Existing tests cover the routing decision and valid direct Python code independently, but not this integrated contract. No runtime repair is included. Source blobs: `tool_caller.py` `31faba3cc49b60f21069679e920c73442249f919`; `tools.py` `ff5f251b225c975c01f6bf3c3da9cbad1f77fbee`; `gui/server.py` `d67df10f4449004c255e38b11b4a1888a4e4934c`; test `tests/test_tools.py` `85c7aa8236e2cdd1005f3ab4aa49c8c6da337d2d`. This is source evidence only, not a host failure report.

**Additional source finding (23 Nov 2026, PR #65 integrated branch):** DRAFT-003: `MembraneClassifier.classify_query()` checks whether each self-inquiry keyword is a substring of the lowercased query. Because `"you"` is one of those keywords, the product name `YouTube` matches it and is classified INSIDE. In `api_chat`, that selects the INSIDE membrane route (self-model snapshot plus INSIDE-filtered beliefs and a Philosophical register hint), rather than the OUTSIDE route. Existing membrane tests cover example self-inquiry and world queries but no product-name/token-boundary case. This is a source-confirmed conditional misclassification, not evidence of deployed incidence. Source blobs: classifier `84f68975083266ba1a3fecf5322664392711bf10`; tests `42c0347534b765ef4c24685e333c8fe4047fdce8`; router `74d82fe0f9fe210c75d86105e205dcb0c4151d79`. No runtime fix is included.


**Additional source-audit qualification (23 Nov 2026, PR #65 integrated branch):** VoiceEngine's TimeFetch candidate pipeline is a four-source ordered sweep (beliefs → novel associations → arcs → problem gaps), with source-specific limits 20/10/10/10, exact-content deduplication preserving the first source, then a cap of 40 before scoring. Belief candidates are enriched with tier/reinforcement and optionally Genius score through a two-database lookup. The Genius query selects `weights_version` but the inspected consumer neither filters by nor carries that field forward; score comparability across versions is unverified. The six-component score uses weights totaling 1.15 because the 0.15 Genius component is not renormalized; `min_score` is therefore implementation-specific, not a normalized probability. The module header and scoring docstring still say five-axis. Separately, `test_score_candidate_returns_zero_on_embed_error` passes a zero vector rather than simulating an embedding exception; the implementation zeroes the semantic component on local embedding failure and continues the other components. This is a documentation/test-coverage qualification, not a demonstrated runtime defect. Source hashes: TimeFetch `7a97a76a48eb54d621d1a436fc5c64d5f6ddfd7b`; VoiceEngine `ea52711e13b7ea71531a3bec9a394d18e2574b40`; test `a82f104fbd2bc3efd1b3fed9d6410b838f38fd6f`. No runtime changes are included.


**Additional VoiceEngine retrieval detail (23 Nov 2026):** The open-problem gap source calls `ProblemMemory.find_matching()`, which considers open problems ordered by most recently touched and includes a row when at least two cleaned content tokens overlap with the query/title+description. It does not rank those matches by overlap count or semantic similarity before TimeFetch adds them to the candidate pool. Source hash: `theory_x/stage7_sustained/problem_memory.py` `4a9dcc839bf0be7bf28338168d8946309c7002f5`. This is a retrieval-order fact, not a defect determination.


**Genius score version boundary (23 Nov 2026):** The design document specifies that old and new Genius tags coexist, uniquely keyed by fountain event and weights version, for comparison after re-fitting. VoiceEngine selects the latest tag by timestamp without filtering to a declared active weights version. Thus “latest tagged” is source-confirmed; “current approved score” is not established. This is an unresolved consumer/version contract, not a declared defect absent the authoritative acceptance rule. Design source hash: `GENIUS_SCORE_v2.md` `be73cb4f7b494c48eb37eeec8635aba89ea5751e`.
