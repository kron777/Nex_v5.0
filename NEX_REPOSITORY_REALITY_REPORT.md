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

**Priority security finding — DRAFT-015:** the active public `/api/chat` route can select `python_exec` from a user prompt and passes the raw prompt to a subprocess. The import blacklist is bypassable through Python built-ins; this is not a sandbox. The route is explicitly exempted from the admin mutation gate. The default bind is loopback (`127.0.0.1`), but `NEX5_HOST` can expose it on another interface. If reachable by untrusted clients, this is a conditional unauthenticated arbitrary-code-execution path. No exploit was run. Do not expose the service beyond a trusted local boundary until this path is disabled or safely isolated and independently verified.

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


**FocalSet / WorkingMemory integration qualification (23 Nov 2026):** The current Chat handler does not stop at diagnostic FocalSet logging. A process-global `_focal_set` (K=4) is updated from each request's top-10 retrieved beliefs; the selected IDs are copied into a `WorkingMemory` instance keyed by that request's session. On a later turn, up to five active items from that session's WorkingMemory are appended to `belief_text` and enter the composition prompt, conditionally for Conversational register and at least two retrieved belief blocks. Since FocalSet's hold/last-shift state is shared across sessions, interleaved requests can influence focal selection in another session when candidate IDs overlap. The receiving session's own WorkingMemory is read; another session's WorkingMemory is not directly read. Isolated FocalSet/WorkingMemory tests exist, but no inspected two-session Flask integration test exercises this shared-state-to-session-buffer path. This is an unresolved session-isolation/attention-continuity contract, not a declared defect without the authoritative acceptance criteria. Source hashes: server `5ee8b167f386466c383090445c63a84810bbae52`; FocalSet `e12531f2858085778ebca75f73a7dee6ec8ce416`; WorkingMemory `4e9badadbb3ada939c05fcb4a82455723c0efa36`; tests `083b8053ff09ef0975f8aab35a120904b2f55423`, `446d90f4c79a515eba08aaac1b24c5c33f0797e3`, `b8123747372956ff38ab28838a8368429006b3f6`.


**Ordering clarification:** The handler updates FocalSet and adds current focal items to the session WorkingMemory before it reads and appends the `Recently attended (cross-turn)` block. On eligible turns, that prompt block can contain both current-turn selected items and retained prior-turn items; it is not exclusively historical context.


## Independent exact-head review reconciliation (23 Nov 2026)

Reviewed Maus's independent read-only assessment against PR #49 head `d046d5beadd640cca6df6631d9dbd3166d16fccf` and PR #65 head `3d5df48e6539818097b58b6e936059fae946ceca`. This addendum records evidence corrections; it does not authorise behavioural work.

### Authority boundary

The exact Founder Sign-Off/approval record and Frozen V2.1 specification are not present in the inspected PR #49 tree. This is a bounded absence, not proof that they do not exist in an external Library or another authoritative location. PR #49's own ADR says they remain unlocated and remains explicitly draft/not ratified; its crosswalk states that it is partial and not a Gate 0 submission. A statement that the Master Roadmap was reopened from the Library is not the canonical roadmap artifact or a substitute for its version, provenance and approval record. Gate 0 remains unestablished until the canonical authority materials are produced, hierarchy/criteria are reconciled, and the specified Founder review/approval is recorded.

### Exact-head CI correction

- PR #49 `d046d5beadd640cca6df6631d9dbd3166d16fccf`: pytest run `45255379806` completed successfully.
- PR #65 `3d5df48e6539818097b58b6e936059fae946ceca`: pytest run `45250499152` completed successfully.

These are separate PR heads and separate workflows. Green CI supersedes earlier pending/stale status statements for these exact revisions; it does not establish runtime behaviour, production trace completeness, host neutrality, Gate 0 approval, or test coverage outside the asserted fixtures. PR #49's historical CI table should be read as history, not as a live status source.

### Additional trace/control-flow findings

**VoiceEngine parent edge — source-supported trace concern:** In `gui/server.py`, the VoiceEngine input trace record includes both the Chat input record and general Chat retrieval record as parents (source lines 1901–1915). The actual `VoiceEngine.query_reply()` call receives the query, session ID and turn number, not the general Chat retrieval result; VoiceEngine performs its own TimeFetch retrieval. A shared query is a common upstream cause, but the inspected call does not establish general Chat retrieval as an immediate parent of the VoiceEngine retrieval. Preserve this as a parentage question; do not infer causality from chronology or shared context.

**Substrate miss comment/control-flow discrepancy:** The handler comment around lines 2261–2263 says a substrate miss suppresses LLM fallback in `use_substrate` mode. In the inspected handler, a miss leaves `text` unset and reaches `state.voice.speak()` (lines 2261–2282). The repository's `voice/llm.py::VoiceClient.speak()` builds a model request and invokes `_request_fn`; its default request function sends an HTTP request to the configured llama-server endpoint. The handler therefore does not itself implement the suppression described by the comment. A runtime-specific substitute or configuration could alter the downstream effect, so deployed model invocation remains unverified. Classification: source-confirmed comment/control-flow mismatch; runtime mode effect unresolved. No behavioural fix proposed.

**Speech queue overlap:** The consumer selects pending rows and later changes status; the inspected path has no atomic exclusive claim. Two overlapping consumers could select the same row before either update, but deployment topology and actual overlap are unknown. This is a conditional concurrency risk, not an observed duplicate-processing incident.

**Observer cost:** Trace appends perform synchronous JSONL serialization/write under a shared lock. Added latency and contention are possible by construction, but magnitude and host impact are unknown. The benchmark smoke test is diagnostic and non-gating; no latency threshold or production neutrality claim is established.

### Evidence classification guardrails

- The controlled commit-before-registration test establishes a reproducible ordering in which the consumer sees a committed pending row before the producer registers the trace link. It proves possibility, not deployed frequency.
- The process-local bounded registry can lose hand-off identity on restart or eviction; the consumer then remains explicitly unlinked. This is incomplete provenance, not a fabricated parent.
- Queue selection/processing-start is not an exclusive reservation; player-call return is not physical audibility; persisted `spoken` status is not proof of listener receipt.
- The Chat OFF/ON fixture is a minimal route fixture and does not establish trace completeness for optional faculties, VoiceEngine, tools, FocalSet/WorkingMemory or every branch.
- The two PR CI passes are not one integrated merged-tree run.

**Disposition:** No new runtime defect severity is assigned here. The VoiceEngine edge is a trace-integrity concern; the substrate miss is a comment/control-flow mismatch with unresolved runtime mode effect; consumer overlap and observer latency remain conditional. Gate 0 remains unestablished, and behavioural development remains unauthorised pending authority reconciliation and Founder approval.

Source blob hashes at PR #65 head: `gui/server.py` `d67df10f4449004c255e38b11b4a1888a4e4934c`; `voice/llm.py` `a41e04db8569393dc2ae2ebe622cf1e67ae3de66`; `substrate/trace_overlay.py` `fbccc3b63bc94dab8e9f01951a581ba3af3f087e`; `speech/queue_consumer.py` `cf97bf9cc8681de901c3d1b8c052b95df5c822b2`; `theory_x/stage6_fountain/crystallizer.py` `62cbb62cf55b8c39ab1301b9d89d36b37cc16bfc`; `substrate/writer.py` `b5b7bc98fcb39e75683188fbc59f33adf8868741`.


## Governing roadmap retrieval and internal reconciliation (23 Nov 2026)

The original full document **“NEX v5.0 — Master Technical, Research & Commercialization Roadmap (v3.0)”**, dated 20 November 2026, has now been located in the ChatGPT Library as `gemini.txt` (44,167 bytes; Library file reference `turn390file0`). This is the original full roadmap, not merely the technical-only derivative. It states the hierarchy Founder Sign-Off > Frozen V2.1 Spec > Runtime Truth > Roadmap. Its presence in the Library corrects any implication that the roadmap itself is unavailable; its absence from the reviewed PR #49 repository tree remains true. The exact Frozen V2.1 specification and Founder Sign-Off/approval record remain unlocated in the searched Library/repository material; do not infer global non-existence.

### Roadmap requirements mapped to current evidence

- **M0.1–M0.2:** The report exists and repository/CI evidence is being assembled. Exact host measurements (Python, SQLite, Ollama, Qwen2.5 3B model digest, idle/load RAM/VRAM, median tokens/sec), runtime DB/snapshot hashes, and an exact target-host clean/dirty inventory have not been observed in this workflow. CI passing on a GitHub runner is not a substitute for those target-host measurements.
- **M0.3–M0.4:** The Crosswalk and ADR exist as drafts, but the Crosswalk explicitly remains partial. The full forward Declaration → Boot → Scheduler → Emission → Consumer audit and backward Chat Output/Fountain Action/Belief Write → upstream audit for every `theory_x/` faculty is not established as complete. The 30-node mind map and named architecture documents require a complete, revision-bound reconciliation. The evidence ladder in Roadmap §1.2 defines L0–L5, while §6.2 says assign L0–L4; preserve this as an internal roadmap inconsistency for Founder clarification rather than silently choosing one.
- **M0.5:** The default-OFF trace implementation and isolated fixtures exist on the PR #65 branch, but the reviewed materials do not contain a complete production-host trace sample. The roadmap deliverable `NEX_CAUSAL_TRACE_SAMPLE.json` is not established as delivered. The tested OFF/ON fixtures do not by themselves prove a live Chat turn and full Fountain cycle on the target host.

### Roadmap sequencing conflict requiring authority clarification

The same v3.0 document contains a material sequencing tension:
- §5.1 says the read-only causal trace (Phase 0) runs first, the Chat Arbiter experiment (Phase 1.1) second, and CTL Shadow Trials (Phase 1.3) third.
- §6.3 defines Phase 0 Week 3 as the read-only causal trace and explicitly states Gate 0 requires Founder approval of the Reality Report, Crosswalk and verified defect backlog **before any behavioural edits**.
- §12.3's immediate 30-day checklist nevertheless places implementation and a frozen three-arm Chat Arbiter benchmark in Week 3, then places Gate 0 Founder sign-off in Week 4.

The Chat Arbiter treatment changes context selection and is separately classified as a Tier B Phase 1.1 experiment in §7.1; the checklist's Week 3 placement therefore conflicts with both §5.1 sequencing and §6.3's explicit Gate 0 condition. This report does not resolve whether §12.3 is stale, erroneous, or intended to describe a separately approved exception. Until the Founder resolves the conflict against the Frozen V2.1 authority, follow the explicit Gate 0 restriction and do not start the behavioural Chat Arbiter experiment.

**Current Phase 0 disposition:** M0.1–M0.5 are not yet demonstrated complete. Continue only read-only audit, documentation, approved isolated fixtures and non-behavioural trace-evidence work. Do not begin Phase 1 behavioural experiments/fixes. The original roadmap's retrieval is now verified; the higher-authority Frozen V2.1 and Founder Sign-Off remain unresolved.


## M0.3–M0.4 forward-audit continuation — Stage 2 life loops and sinks (23 Nov 2026)

A further source pass at PR #49 branch revision `07f6ebe42a1ac99a8038a73476782d1542704296` inspected the Stage 2 loop assembly and the principal life/sustained-attention/signal/edge/retention modules. This is static source evidence, not proof of host execution or actual emitted rows.

### Stage 2 loop assembly

`build_dynamic()` starts nine core daemon loops and appends further loop functions when their imports succeed: witness, pattern, identity, affinity, scorecard, surprise, remember, wonder, fetch, daily-life, sustained-focus, signal-to-problem, diversity edge-builder, gate retention, and the list returned by `get_moltbook_loops()`. It starts all assembled threads before returning DynamicState. This means those loop start attempts are source-defined, not merely module presence. Whether each thread completes ticks, writes rows, or affects downstream decisions remains unobserved.

### Source-to-sink inventory

| Loop / mechanism | Reads or trigger | Output / write | Downstream path established in inspected source |
|---|---|---|---|
| IdentityLoop | Belief/focus/surprise/Fountain/Moltbook and related substrate state | `identity_log` plus Tier-6 `identity_loop` belief | PatternLoop reads `identity_log`; Fountain has a separate identity-context read. |
| PatternLoop | Recent `identity_log` statements | `pattern_log` plus Tier-6 `pattern_loop` belief | WitnessLoop reads `pattern_log`; Tier-6 beliefs are eligible for general belief retrieval subject to retriever filters. |
| WitnessLoop | Recent `pattern_log` statements | `witness_log` plus Tier-6 `witness_loop` belief | Its own module describes retrieval feeding subsequent IdentityLoop composition; source confirms the belief write, but live retrieval/consumption is not observed. |
| RememberLoop | One old and one recent belief | LLM-generated Tier-6 `remember_loop` belief | General belief candidate pool, subject to retrieval filters. |
| WonderLoop | Recent `sense_events` / entities | LLM-generated Tier-6 `wonder_loop` question-belief | General belief candidate pool, subject to retrieval filters. |
| FetchLoop | Recent URL-bearing `sense_events`; bounded HTTP fetch | LLM-generated Tier-6 `fetch_loop` belief | General belief candidate pool, subject to retrieval filters. |
| SurpriseLoop | Unpromoted `surprise_events` | Tier-6 belief; special current-focus signal on qualifying large surprise | Belief retrieval; FocusLoop's current-focus path is a separate consumer to trace. |
| ScorecardLoop | Calls `ground_self_belief.refresh_self_belief()`, which reads the WorldPrediction scorecard | Updates/inserts a fixed-source Tier-1 locked market-prediction self-belief | Tier-1 locked belief is within the retriever's eligible tier/lock pool; actual prompt selection is query-dependent. |
| AffinityLoop | Belief graph and edge statistics | Updates `beliefs.affinity` / `affinity_updated_at` | The inspected BeliefRetriever scoring path and VoiceEngine scoring path do not read this affinity field. No downstream consumer was identified in this bounded pass; do not infer global absence. The module itself warns that its LLM self-rating is hollow. |
| FocusLoop | Open problems, belief overlap, recent Fountain thoughts and conversation activity | Upserts `current_focus`, updates `open_problems`, and may write a NEX chat message when stuck | IdentityLoop, DailyLife and Chat/Fountain context paths read related focus/problem state; exact per-turn influence is conditional and separately traced. |
| SignalToProblem | Unactioned `signals` rows and confidence/type/volume filters | Marks signals actioned and inserts `open_problems` | FocusLoop reads open problems and chooses a current focus. This is a source-defined signal → problem → sustained-focus chain. |
| Diversity EdgeBuilder | Belief candidates, existing edge counts and embedding similarity | Inserts `belief_edges` (`cross_domain`) | BeliefRetriever explicitly blends spreading activation when belief edges exist (60/40 in the inspected implementation). This is a source-defined retrieval influence path; actual edge creation and selected result remain runtime UNKNOWN. |
| Gate retention | Age-bounded `gate_decisions` and `throw_net_sessions` | Deletes rows beyond configured retention windows in bounded batches | Maintenance/retention path; not a prompt or action selector in this inspection. |
| DailyLife | Clock/calendar, beliefs, open problems, focus, Fountain and external interaction records | `daily_activities`; creates sessions/messages for scheduled entries/outreach/journal; may use sense/Moltbook context | Conversation rows may be visible to ordinary conversation readers; the precise user-facing/UI consumer and whether the resulting entries feed Chat context need separate source tracing. |

### Specific distinctions and limits

- Identity → Pattern → Witness is a source-defined recursive observation chain: PatternLoop reads IdentityLoop output; WitnessLoop reads PatternLoop output; the outputs are also written as beliefs. This is a constructed feedback design, not evidence of autonomous runtime execution or cognitive improvement.
- Tier-6 and Tier-1 belief writes are not automatically [L3]. They become candidates for retrieval subject to the retriever's eligibility, query overlap, branch/side filters and downstream context selection. A row existing is not proof it was selected or relied upon.
- EdgeBuilder is a stronger source-level downstream link than a log-only table: BeliefRetriever reads `belief_edges` and blends spreading activation. It remains [L1] source evidence until a trace links a particular persisted edge to a selected retrieval result and subsequent prompt/decision.
- Affinity updates should not be described as changing retrieval ranking on the basis of the inspected retriever/VoiceEngine paths: neither reads `beliefs.affinity` in the scoring code inspected. Other potential consumers remain unverified.
- ScorecardLoop's output is not a new market-prediction experiment; it refreshes the fixed-source self-belief using the scorecard module. The belief's eligibility does not establish that a particular Chat/Fountain prompt selected it.
- DailyLife and FocusLoop can write conversation messages. Their creation is not proof of delivery to a user or of a downstream response; recipient/session ownership and read paths require separate verification.
- Retention is a destructive data-maintenance operation by design. This audit records the source-defined bounded deletion path; no host run, deleted-row count or impact measurement was performed.

Source blob hashes:
- `theory_x/stage2_dynamic/__init__.py`: `7b35f304cf823b555a4c6ec78722a07d017de576`
- `theory_x/life/identity_loop.py`: `ada5eb0e310029ccaaeee5764fd6d39ebccac6c3`
- `theory_x/life/pattern_loop.py`: `08d62f4a36320880dcedcd728fc2effb880e6307`
- `theory_x/life/witness_loop.py`: `fffafc610293ab46cc6d8d72c598f16e2318507a`
- `theory_x/life/affinity_loop.py`: `403d39c2e41a5aebbb5ee196d072c33949ba41f0`
- `theory_x/life/scorecard_loop.py`: `2e14123418f9e98496fdc8de46dea081f8f5f9eb`
- `theory_x/life/surprise_loop.py`: `bb1869e3d5784ca668ca37e8c76cc25998d7a381`
- `theory_x/life/remember_loop.py`: `ffed94e8e237c8feb01d559512f094b827cf2ff8`
- `theory_x/life/wonder_loop.py`: `0f3f21f1a643955c2910f5b35398534e34b5a6af`
- `theory_x/life/fetch_loop.py`: `8bea7ef2a66df212fee7d6ce090277b2250e2ead`
- `theory_x/life/daily_life.py`: `15565b07db30e96b18665d27a64fba3be777e374`
- `theory_x/sustained/focus_loop.py`: `43e0dffdd88d8a6ccc1e2c86537764a6e74e7ad2`
- `theory_x/signals/signal_to_problem.py`: `87526c50ee07873a2a1ce6002487f0fdb5c91c8a`
- `theory_x/diversity/edge_builder.py`: `8bfb0c02aec8aea373c75c9954881fa748647c23`
- `theory_x/stage_gate/retention.py`: `5e6086caa8738f499861a9c7a8ffb24dc5da0ecc`
- `theory_x/stage3_world_model/retrieval.py`: `aa3eeb15c9a4a19a24a6d328bc370cd0a4438cf3`
- `theory_x/stage_throw_net/voice_engine.py`: `ea52711e13b7ea71531a3bec9a394d18e2574b40`
- `ground_self_belief.py`: `abb6f9e2f9d751097ad7cbaf375f7876d1cbca6c`

No source/runtime behaviour, schema, retention window, scheduler, feature flag, host state, experiment, merge or deployment was changed.


## M0.3–M0.4 forward-audit continuation — Stage 3 WorldModel feedback (23 Nov 2026)

At PR #49 source revision `07f6ebe42a1ac99a8038a73476782d1542704296`, `build_world_model()` starts six daemon loops. Their source-defined data paths are distinct:

| Loop / component | Trigger and source | Writes / state transition | Identified downstream relationship |
|---|---|---|---|
| Belief decay | Hourly loop calls `BeliefPromoter.decay_pass()` after an initial one-hour wait | Changes tier/demotion metadata for eligible beliefs | Retriever's tier ≤6 candidate filter makes tier changes relevant to future candidate eligibility. |
| Harmonizer | Every two hours calls `run_scan_and_resolve(world_model_state=state)` | Can pause/unpause contradictory beliefs, write harmonizer events/held tensions and belief edges, and resolve/retire pairs | Retriever excludes paused beliefs; activation reads belief edges; Chat/Fountain can read the Harmonizer's held-tension prompt summary through their separate integration paths. Exact influence depends on state and branch. |
| Cross-domain detection | Every six hours calls `Harmonizer.detect_cross_domain()` | Adds cross-domain belief edges | BeliefRetriever's ActivationEngine reads edges and blends activation into candidate scores. |
| Erosion | Every six hours calls `ProvenanceErosion.erosion_pass()` | Advances `erosion_stage` and resets reinforcement counters for qualifying beliefs; retrieval calls `record_use()` and increments use count | This is a usage/erosion feedback loop. The inspected base BeliefRetriever SQL does not filter on `erosion_stage`; do not claim erosion stage directly excludes a belief from retrieval without identifying another consumer. |
| Synergizer | Loop wakes every 60 seconds, with a 5-minute cooldown and a 25-minute timer trigger | `BeliefSynergizer.synthesize()` can insert a synthesized belief and records `synergizer_log`; it uses source data from beliefs, edges, Fountain fires, drives and cooldown state | Synthesized beliefs and edges can enter later retrieval subject to normal filters; live creation/selection remains unknown. |
| World consolidation | Thread starts, but exits without work when `NEX5_WORLD_CONSOLIDATE` is empty; `dry/report/test` runs report-only, `1/on/true/yes` arms promotion | When armed, clusters eligible Tier-7 world beliefs and calls promoter corroboration (bounded per run) | Tier changes can affect future retriever eligibility; runtime flag and host effect unknown. Do not describe this as unconditionally active. |

### Retrieval feedback closure

The inspected `BeliefRetriever.retrieve()` selects the eligible pool using `tier <= 6`, `paused = 0`, and `locked = 1 OR confidence >= 0.15`; it scores keyword overlap and optional semantic candidates, then seeds ActivationEngine from the top five keyword candidates. ActivationEngine reads `belief_edges`, returns activation/typed roles, and the retriever blends normalized keyword and activation scores at 0.4/0.6 when activation exists. After final results are selected, the retriever calls `ProvenanceErosion.record_use()` for each returned belief.

This yields a source-defined chain: edge producers (including cross-domain/harmonizer/novel-association/edge-builder paths) → ActivationEngine → retrieval ranking → selected beliefs → use-count update → later erosion processing. The chain is source-level; no single live trace here identifies a particular edge changing a particular Chat/Fountain selection and subsequent output. The same discipline applies to promotion/decay: tier changes alter eligibility only through later retrieval; they are not proof of model reliance.

### Important guardrail

The WorldConsolidation thread's existence is not equivalent to armed execution. The loop checks the environment before constructing the consolidator; an empty `NEX5_WORLD_CONSOLIDATE` returns immediately. Its own `tick()` distinguishes dry/report mode from armed promotion. The deployed value is unknown.

Source blob hashes:
- `theory_x/stage3_world_model/__init__.py`: `6cbde28b64315b869a260298ddec887d1b9bb0ae`
- `theory_x/stage3_world_model/harmonizer.py`: `e72008ec21ad91e20cbdcfc73bacf14263e34382`
- `theory_x/stage3_world_model/promotion.py`: `23def50b1ecfc7f2516f5562d60c791972a5d779`
- `theory_x/stage3_world_model/synergizer.py`: `2dd84ba796f06d95816e550d4ed4581903d82db4`
- `theory_x/stage3_world_model/world_consolidation.py`: `192550c20c7b8e776dfa55f4f82d80fd4cc7ce69`
- `theory_x/stage3_world_model/erosion.py`: `ad92f0c72e0682dfe42a9c5ce2c8e83e72f66b26`
- `theory_x/stage3_world_model/pipeline_hooks.py`: `6750bb427ed493a3310d9ea69d0e82207d0d38f1`
- `theory_x/stage3_world_model/activation.py`: `509a021671c7f698fb740086dfffa170d2543b84`
- `theory_x/stage3_world_model/retrieval.py`: `aa3eeb15c9a4a19a24a6d328bc370cd0a4438cf3`

No runtime behaviour, tier policy, edge policy, erosion threshold, schema, environment flag, host, experiment, merge or deployment was changed.


## M0.3–M0.4 forward/backward bridge — Stages 4–10 and actual Chat sinks (23 Nov 2026)

A further pass at source revision `07f6ebe42a1ac99a8038a73476782d1542704296` traced boot wiring for Stages 4–10 and checked the actual `gui/server.py::api_chat` consumers. This refines the broad faculty list in the earlier Crosswalk: construction, background loops, per-request methods, prompt injection and API-only surfaces are distinguished.

| Faculty | Boot/runtime construction path | Source-confirmed consumer / sink | Boundary |
|---|---|---|---|
| Stage 4 Membrane / SelfModel | `build_membrane()` constructs classifier, SelfModel, QueryRouter and BehaviouralSelfModel; starts the behavioural background thread when conversations Reader exists (normal boot supplies it). | Chat routes through Membrane when available; SelfModel snapshot and query-ranked INSIDE/OUTSIDE retrieval are distinct route contributions. BehaviouralSelfModel is called and formatted only for INSIDE route prompt injection. | Background loop waits four hours between write attempts; runtime writes unknown. Route fixture does not cover all integrations. |
| Stage 5 SelfLocationCommitment | `run.py` calls `commit()` once during boot. | Inserts-or-ignores fixed-source locked Tier-1 self-location belief, then reads back the ID. The belief is eligible for the general retriever under locked/tier filters. | Idempotent commit attempt, not evidence of a fresh row on every boot or of prompt selection. |
| Stage 7 ProblemMemory | Constructed in `run.py`, passed to Fountain and VoiceEngine and exposed to Chat. No autonomous ProblemMemory loop is started here. | Chat calls `find_matching(prompt)` and `format_for_prompt()`; VoiceEngine TimeFetch calls `find_matching()`; Fountain receives the object for task-bearing context. | Each consumer has separate conditions; matching/formatting does not prove selected content changed an answer. |
| Stage 8 GoalManager | Constructed and registered during boot; exposed through AppState and goal API endpoints. | Chat calls `get_active()` for a diagnostic log entry, but source comment explicitly says the goal text is no longer appended to the Chat prompt (SEAM 3). | Do not list GoalManager as a current Chat prompt contributor. API create/list/update/complete paths remain available in source. |
| Stage 9 Metacognition | Constructed and registered during boot; no autonomous daemon loop is started by `run.py`. | Each Chat request calls `tick()`, then `format_for_prompt()`; non-empty output is appended to the same request's `belief_text`. Separate Fountain prompt insertion has its own flag. | Request-driven Chat path, not continuous background observation. |
| Stage 10 NovelAssociation | Constructed, `start_loop()` called and registry registration attempted. | Chat calls `format_for_prompt()`; returned association text can be appended to `belief_text`. The method marks surfaced associations annotated. | Background generation and Chat surfacing are separate operations; actual association production and prompt selection unknown. |
| SelfNarrative | Constructed early and registered; passed as write-trigger target to CoherenceGate, ProblemMemory and NovelAssociation. | Chat calls topic-conditioned `format_for_prompt()` and appends non-empty autobiographical text to `belief_text`. | Source-defined prompt path; trigger production, row availability and selected text remain runtime unknown. |
| AffectState | Constructed and `start_loop()` called. | Chat calls `format_for_prompt()` and appends non-empty persisted affect-state text; separate status endpoint reads state. | DB-backed prompt summary, not evidence that model adopts it. |
| DriveEmergence | Constructed and `start_loop()` called. | Chat calls `format_for_prompt()`; VoiceEngine receives DriveEmergence and reads its drive-topic embedding for drive-alignment scoring. | Prompt summary and retrieval-score alignment are distinct consumer paths. |
| SelfMindView | Constructed and `start_loop()` called; passed into Metacognition and AppState. | Chat calls `current_summary()` and appends a non-empty cognitive-state summary. | Snapshot creation, summary availability and prompt use remain host/runtime dependent. |

### GoalManager correction

The broad earlier list of possible Chat prompt contributors should not be read as asserting GoalManager prompt injection. In the inspected handler, `get_active()` is called and the active goal is logged, but a source comment says goal text is no longer appended to the Chat prompt. GoalManager remains available through its API and internal state methods; the current Chat path does not use its goal text as context.

### Prompt-path causal closure update

The inspected Chat handler contains explicit source-level append paths for BehaviouralSelfModel (INSIDE only), ProblemMemory (matching query), Metacognition, NovelAssociation, SelfNarrative, AffectState, DriveEmergence and SelfMindView. These are distinct contributions to `belief_text`, later passed through Chat block assembly and model composition on applicable branches. The aggregate trace's `context_selection` record does not independently identify each selected row or prove that the model relied on a contribution. The direct VoiceEngine hit route can bypass model composition entirely.

Source hashes:
- `run.py`: `73a2c58a4f5f0348135a46eb83d6cdd61db874e7`
- `gui/server.py`: `5ee8b167f386466c383090445c63a84810bbae52`
- `theory_x/stage4_membrane/behavioural_self_model.py`: `cd6ce4179e95b8435c33602f116f0a33f89ced12`
- `theory_x/stage4_membrane/self_model.py`: `c3646242ee244d7434228fcabf0550ebd0d37947`
- `theory_x/stage4_membrane/router.py`: `74d82fe0f9fe210c75d86105e205dcb0c4151d79`
- `theory_x/stage5_self_location/commitment.py`: `fc26693efe9a371b9330a764a752743699a12917`
- `theory_x/stage7_sustained/problem_memory.py`: `4a9dcc839bf0be7bf28338168d8946309c7002f5`
- `theory_x/stage8_goal_manager/goal_manager.py`: `0b879a903fa499fb88153edbcb7f5c8e69bd6dfa`
- `theory_x/stage9_metacognition/metacognition.py`: `de853bd93a11dcfe39ee8afa30a84e5c7b1f8b08`
- `theory_x/stage10_imagination/novel_association.py`: `c9f25a0a1a5b13ef481abe05bb5b59cdaa560cbc`
- `theory_x/stage_self_narrative/self_narrative.py`: `15d8c1dd1de8332b3d12e06a096aac2c0b2b2cb3`

No runtime behaviour, prompt content, goal policy, schema, flags, host, experiment, merge or deployment was changed.


## M0.3–M0.4 correction and extension — Fountain prompt consumers and selection feedback (23 Nov 2026)

A deeper pass through `theory_x/stage6_fountain/generator.py` found additional downstream consumers and corrects one bounded conclusion in the Stage 2 audit.

### Affinity correction

The Stage 2 addendum correctly states that the inspected BeliefRetriever scoring and VoiceEngine scoring paths do not read `beliefs.affinity`. However, the Fountain prompt builder does read it: it selects up to ten beliefs with `affinity > 0.40`, randomly samples up to two, and appends their contents under "Beliefs you've come to feel as deeply yours". Therefore AffinityLoop output has a source-confirmed Fountain prompt consumer. This does not validate the self-rating signal: `affinity_loop.py` itself documents a prior test in which the model's ratings collapsed to the nearest prompt anchors. Record the relationship as **source-level prompt consumption of an unvalidated affinity field**, not as a validated preference or proof of influence on generated content.

### Fountain selection feedback paths

- **Momentum:** after a normal Fountain thought, `capture_momentum()` is called when `NEX5_MOMENTUM` is unset or `1` (source default ON). The next candidate-selection helper reads the persisted `momentum` row (`thought_fragment`, `carry_count`) and uses it as an unfinished-thread signal in the curiosity score. `NEX5_CARRYOVER=1` additionally stamps whether the prior fire crystallized. This is a source-defined cross-fire selection-feedback path, not just a prompt annotation. Actual flag state and effect on selected content remain host/runtime unknown.
- **Global Workspace:** `NEX5_GLOBAL_WORKSPACE` defaults to `1`; when a non-empty arbitration line is returned it is prepended to the DRIFT focus block. The winning workspace line is deliberately not carried into wide EXPLAIN/ARGUE fires unless the separate `NEX5_WIDE_FOCUS=1` path carries selected faculty lines. This distinction is source-defined.
- **RecursiveSelf:** `recursive_self.format_for_prompt()` is called without an environment gate and a non-empty line is appended to the focus block; its separate `perturbation()` result is sampled for `recursion_attrib`. The source does not establish that the attribution row itself changes the selection.
- **Conditional inner faculties:** Metacognition voice, mood/compositional emotion, Amoha, affliction cluster, L4 grounding/stakes, and wide-focus carry are individually gated by `NEX5_METACOG_VOICE`, `NEX5_MOOD`, `NEX5_AMOHA`, `NEX5_AFFLICTIONS`, `NEX5_L4_STAKES`, and `NEX5_WIDE_FOCUS`. Do not infer activation from the imported modules or source presence.
- **Affinity, identity, downtime and surprise:** the normal prompt builder reads recent `identity_log` statement, latest `self_downtime` belief, recent `surprise` belief (six-hour window), and random inward/outward `spectrum` standing-points. These are direct source reads into prompt construction. `NEX5_IDENTITY_BLOCK` is a separate optional identity-block mechanism; its flag being off does not remove the distinct latest-`identity_log` block.
- **HotObserver:** post-fire observer writing is gated by `NEX5_HOT_OBSERVER=1`; when enabled it writes a meta-belief about the completed fire and carry branch. Its beliefs can later be candidates for retrieval, but actual selection is unverified.
- **SubstrateVoice:** the potential anchor-verbatim path has a further `NEX5_RECONCILE != 1` guard plus groove/cooldown/anchor conditions. A source comment says the deployment has `NEX5_RECONCILE=1`, but the live host environment has not been inspected. Do not state whether the branch is active on the current host.
- **Quiescent path:** every fifth fire, by the counter condition in source, can record a bare external sense item (or tick fallback) and return before normal LLM composition/crystallization/speech. This is a distinct Fountain output branch.
- **Stillness path:** duplicate own-slot retrieval can write a blank Fountain event/stillness record and return without a generated thought; after three consecutive stillness events the next fire is forced with a quiet notice. This is distinct from the ordinary generated-thought route.
- **Substrate Emit / Reconcile Emit:** `NEX5_SUBSTRATE_EMIT=1` can render top activated substrate beliefs directly; `NEX5_RECONCILE=1` can construct a joint-progress prompt from open problems. These are separate source-defined generation alternatives; current host flag values remain unknown.
- **Post-fire observer records:** EmphasisEngine scores after thought generation and writes `emphasis_log`; `fountain_retrieval_log` and `fountain_prompt_blocks` are also written after the thought/event is already recorded. These are observer/persistence outputs, not upstream causes of that same fire. The retrieval log is dropped/recreated on startup except for the conditional legacy-FK migration branch; the prompt-block manifest is retained with 30-day pruning. No runtime reader for the prompt-block manifest was identified in this pass.
- **Parallel substrate fire:** every fifth main-path fire according to the counter condition can render a separate substrate output and persist it in `substrate_fires`; it does not replace the normal Fountain thought. This is another output path whose actual runtime occurrence is unknown.

### Evidence boundary

These observations expand the source-to-prompt and source-to-output map. They do not establish current host flag values, successful runtime execution, which prompt blocks were present on a live fire, whether a specific candidate was selected, or whether the model relied on it. The persistent prompt-block manifest is useful evidence infrastructure but is not itself a complete causal graph: its entries are hashes/lengths/prefixes, and the manifest has no identified runtime consumer in this inspection.

Source hash: `theory_x/stage6_fountain/generator.py` `43644876295ffdd649a240f52a7946c666a8579f`.

No runtime behaviour, flag, prompt, selection policy, schema, host, experiment, merge or deployment was changed.


## M0.3–M0.4 forward audit — predictive, counterfactual, provenance and optional families (23 Nov 2026)

This pass checked additional boot-managed faculties against their implementation and consumer paths at source revision `07f6ebe42a1ac99a8038a73476782d1542704296`.

| Faculty | Boot/activation condition | Source-defined output and consumer | Evidence boundary |
|---|---|---|---|
| PredictiveSubstrate | `run.py` constructs and calls `start_loop()` when initialization succeeds; 300-second cadence. | Generates internal-belief and external-input centroid predictions; later verifies due windows and writes `surprise_events`. Stage 2 SurpriseLoop reads unpromoted surprise events and can create Tier-6 beliefs; Fountain also reads a recent `source='surprise'` belief. | Source-defined feedback chain; no live tick/prediction/surprise row observed in this pass. |
| CounterfactualNode | Constructed and `start_loop()` called in boot when dependencies are available; 300-second cadence. | Processes one oldest-touched open problem; TimeFetch fetches candidates, RefinementEngine scores, CoherenceGate evaluates; ACCEPT candidates are inserted as Tier-3 `counterfactual_node` beliefs linked to the problem. | The later move to `review_queue` is disabled by immediate return in `_maybe_promote()`. The belief-insertion path remains present; whether any candidate is accepted in runtime is unknown. |
| Throw-Net | TriggerDetector/engine are constructed when their dependencies are available; monitor loop starts only when `NEX5_THROWNET=1`. | TriggerDetector records gate-reject and gap-deflection triggers; when enabled, ThrowNetMonitor calls `run_pending()`, which fetches/refines candidates and submits packets to CoherenceGate, writing session outcomes. | Source comments say the monitor is retired by default; triggers can still be logged. No deployed flag value or trigger volume observed. |
| Chat provenance | `NEX5_PROVENANCE=1` **and** admin session required. | Before model composition, captures the retrieved belief block (or recency fallback), current focus, latest Fountain thought and affect vector. After response, computes mirror/copy measures; only if mirror-dominant cue fires does it retry once, keeping the retry only if its mirror score is lower. | Conditional response-path behaviour, not merely a log-only observer. Grounding hint is explicitly unproven; there is no self-grounded verdict. Current flag/session state unknown. |
| WorldPredictionLoop | Starts only with `NEX5_WORLD_PRED=1`; default OFF in source. | Periodically resolves and makes external market predictions; writes prediction/scorecard records used by ScorecardLoop's self-belief refresh path. | Not an unconditional boot loop; host flag unknown. |
| SelfPredictionLoop | Starts only with `NEX5_SELF_PRED=1`; default OFF in source. | Resolves/makes self, authored-utterance and self-description predictions; includes a threshold monitor explicitly described as not wired to the live fire gate. Optional owned-belief/commitment/reconciler subpaths have their own flags. | Do not claim learned threshold controls live firing. No host flag/value or live result observed. |
| SelfMaintainShadow | Starts only with `NEX5_SELF_MAINTAIN_SHADOW=1`; default OFF. | Computes hypothetical active-set regulator metrics and writes `self_maintain_shadow`. Module says it changes no beliefs and has no table reader. | Shadow/telemetry only; no runtime activation or downstream reader observed. |
| WarrantRecorder | Starts only with `NEX5_WARRANT_RECORD=1`; default OFF. | Records survival/use evidence into side tables using retrieval log, Fountain anchor, Synergizer, lineage and arc sources. | Recording-only by module contract; it does not change what is thought/retrieved/said. It shares the conditional Fountain retrieval-log preservation path. |
| PersonaResponder | Starts only with `NEX5_PERSONA_RESPONDER=1` in the boot path. | Generates a response to recent Fountain thoughts and writes its own social/interlocutor state and external-other-mind sense events. Fountain's SOCIAL prompt layer has a separate gate. | Two-sided loop requires both responder activation and Fountain read gate; neither host flag is established here. |
| SocialPresence | Boot explicitly sets `_social_presence=None` and attaches None to Metacognition. | Module can write `social_presence_snapshots`, but its own source says there are no readers outside its module. | Not wired into this boot path; module presence is not activation. |
| Finitude BudgetShadow | Module source says it is not imported by `gui/server.py` or `selector.py`. | Shadow budget-spend ledger only. | Not in the inspected live path. |
| Stage Provenance | Conditional Chat path above; no independent background loop. | Pre-turn snapshot and post-response mirror read are admin-scoped. | Keep distinct from claims about emotional authenticity or groundedness. |

### Important causal distinctions

- PredictiveSubstrate's two streams are not the same target: internal predictions use recent beliefs/open problems/drive; external predictions use recent external sense events and user messages. Verification compares the target window against later beliefs or later sense/user-message content, respectively.
- An empty verification window is treated as surprise score 1.0 with no actual content; a surprise event can therefore be generated by absence of observed input, not only semantic mismatch. Downstream consumers must preserve this distinction.
- CounterfactualNode's automatic promotion to review_queue is disabled, but its upstream candidate generation, CoherenceGate submission and Tier-3 belief insertion remain in the inspected implementation. Do not describe the whole node as disabled.
- Trigger logging and Throw-Net processing are separate. TriggerDetector can record a threshold-crossing event while the periodic consumer remains stopped.
- Chat provenance is not purely observational when armed: it may cause one retry. It is admin-scoped and uses a mirror-dominant condition; its grounding score is expressly marked unproven.
- SocialPresence's implementation can write snapshots, but boot assigns None and Metacognition receives None. No external consumer was identified.

Source hashes:
- `theory_x/stage_prediction/predictive_substrate.py`: `24933b4d6217376a1341c351319cc48546543c80`
- `theory_x/stage_counterfactual/counterfactual_node.py`: `76f8146b803d6272721a349c86e3a5530af4df16`
- `theory_x/stage_throw_net/monitor.py`: `04f81a7a811f7a40da853e7b2a321e399590b3e5`
- `theory_x/stage_throw_net/throw_net_engine.py`: `6d420f9e3036a055bb9677664b5a44cc805edae4`
- `theory_x/stage_throw_net/trigger_detector.py`: `4d5b855cfb9debe70fdd84649b62273af9964bff`
- `theory_x/stage_provenance/provenance.py`: `92671a3e120a1935fab33f6d659ab806f1eb4cc6`
- `theory_x/stage_world/world_loop.py`: `d369250123c9cfa4f73d3ca5cc33708adf71899a`
- `theory_x/stage_world/self_prediction.py`: `a0474c459629e267e418e795419b4b1e1e2f6e48`
- `theory_x/stage_self_maintain/shadow.py`: `65da9373b112ea15fe255f81550b20b432c927db`
- `theory_x/stage_finitude/budget_shadow.py`: `a194f3d80c6da63078548bc1ab037986e1de7d00`
- `theory_x/stage_warrant/recorder.py`: `ade231c1fc7c8da7f90f8f7ab375d352837a7c79`
- `theory_x/stage_social/social_presence.py`: `80803ae0c8cdce8d08d78bfc416337559c188f17`
- `gui/server.py`: `5ee8b167f386466c383090445c63a84810bbae52`
- `run.py`: `73a2c58a4f5f0348135a46eb83d6cdd61db874e7`

No runtime behaviour, schema, flag, host, experiment, merge or deployment was changed.



## M0.3–M0.4 forward/backward audit — cross-path feedback, annotation and analytical consumers (23 Nov 2026)

This pass follows several mechanisms that sit across the numbered stages and were not fully represented in the preceding Stage 1–10 map. Evidence is source-level at the exact PR #49 revision listed below.

### Fountain workspace and drive composition

- FountainGenerator calls global_workspace.arbitrate() on the normal prompt-composition path when NEX5_GLOBAL_WORKSPACE is unset or 1. The arbiter scores available surprise, momentum, bonsai, stakes and drive candidates and returns one leading frame, which is prepended to focus_block. This is a Fountain prompt-framing operation; the module's broader “broadcast to all” description should not be read as evidence that the winning frame is delivered to every faculty.
- DriveEmergence.format_for_prompt() supplies the drive candidate to the arbiter, and the generator separately appends the same drive line later in the focus block. Therefore workspace framing does not gate the direct drive contribution; depending on the winner, the drive may be represented both in the framing line and in its own appended block. This is a source-path observation, not a demonstrated quality defect.
- Chat has a distinct NEX5_CHAT_WORKSPACE budgeted block selector, source-commented default OFF. It is not the same operation as Fountain's single-winner arbiter. Its exempt blocks are retained regardless of budget, so the character budget is not an absolute ceiling when exempt content alone exceeds it.

### Human annotation → substrate feedback

- /api/coincidence/tag writes an operator-supplied coin, maybe or non label onto a Fountain event, propagates it to that event's existing word_contexts rows, captures a bounded substrate-context snapshot in coincidence_context, and attempts hypothesis auto-scoring.
- When NEX_TAG_FEEDBACK_ON=1, the label has multiple downstream paths: Chat's voice-composition route can inject a global tag summary and up to four keyword-matched tagged thoughts; Fountain samples the tag block with a 25% per-fire chance; and identity_loop adds recent tag counts to its next self-description. The tag retrieval functions are no-ops when the flag is unset or 0. The identity metric is independently guarded by the same flag.
- These retrieval queries are over the shared Fountain corpus and take no session identifier. The code therefore implements a system-level annotation-feedback path, not a session-private memory path. Whether this global feedback boundary is intended is unresolved pending the authoritative acceptance criteria; no cross-user privacy conclusion is made from this source inspection.

### Coincidence decoder and UI sink

- run.py starts coincidence.decoder_loop after AppState construction. The loop waits 15 seconds, then polls every 30 seconds; each tick reads up to 200 unprocessed Fountain events, tokenizes nonempty thoughts into unique sorted words (minimum token length three, stopwords removed), and writes per-word context rows to word_contexts. It also reads the nearest preceding tree snapshot, recent surprise and daemon counts, recent Fountain-fire count, and time since the latest external sense event. Its cursor advances over rows with no usable tokens as well.
- gui/server.py consumes word_contexts for the recent-fire ticker, top-word counts, word fingerprints and tag aggregates. The inspected sinks are GUI/analytical surfaces; no cognitive prompt or selector read of word_contexts was identified in this pass. The separately captured coincidence_context is read by rich tag retrieval to annotate tagged thoughts with aperture, branch and fire-count context.
- The decoder is therefore an active boot-managed analytical pipeline, not an inert library module. Its output is visible in the GUI, but visibility does not prove that it changes NEX's cognition.

### Affect, drive and gate cross-coupling

- AffectState starts a 300-second background loop at boot when construction succeeds. It integrates a lexical polarity signal from high-tier beliefs, a belief-creation-rate arousal signal, surprise-event arousal, and stability input; it persists the current row and appends affect_history. Chat reads the current affect row for prompt composition. CompetingDrives reads the history series to calculate affect variance, then contributes a separate tension block to Fountain. The current mood output is thus consumed through more than one route.
- NEX5_EXPECT_MOOD is a separate optional coupling: when enabled and eligible, AffectState reads reconciled event_valence rows as a capped valence nudge. The expectation ledger contains the reconciler implementation, but no direct call to expectations.reconcile() or commitments.scan() was found in the inspected run.py boot wiring or gui/server.py request path. This is a bounded wiring question, not proof that no external/manual caller exists. Accordingly, do not assume the event-valence-to-mood loop is operational merely because both modules exist.
- AffectCarry is distinct from AffectState: it is an on-demand, admin-scoped Chat compose path behind NEX5_AFFECT_CARRY=1, with per-session carry weights in conversations.db. It reads the current message's distress salience/cues, decays and persists the session's carry, and returns tone-colouring text. The optional openbeat subpath also reads the prior user message from that same session. It is not a boot daemon and should not be conflated with the substrate-wide affect state.
- CoherenceGate.check() catches internal evaluation exceptions and returns ACCEPT with reason gate_error_fallback, then logs the decision. This is a source-confirmed fail-open exception path. Its practical frequency and acceptability are unknown; do not describe the gate as fail-closed under internal error without changing or qualifying that claim.

### Evidence boundary and source hashes

- run.py: 73a2c58a4f5f0348135a46eb83d6cdd61db874e7
- gui/server.py: 5ee8b167f386466c383090445c63a84810bbae52
- theory_x/stage6_fountain/generator.py: 43644876295ffdd649a240f52a7946c666a8579f
- theory_x/stage_tom/global_workspace.py: 54ddab05112702eef34faaa4f24d45139350b349
- theory_x/coincidence/decoder_loop.py: b60a900d9dd3b7b1f1058bb0efc2baa6330e9bfd
- theory_x/coincidence/context_capture.py: a586d19c1a90293f410d876408585d9834e557bd
- theory_x/coincidence/tag_retrieval.py: 1277af630945b5b165f930e900a91095df6b5d04
- theory_x/life/identity_loop.py: ada5eb0e310029ccaaeee5764fd6d39ebccac6c3
- theory_x/stage_affect/affect_state.py: e6d1fd62d6a356929015f0d71586b6f7d80e9be1
- theory_x/stage_affect/affect_carry.py: e34848d18898608cab28826f26ad9480d4901d93
- theory_x/stage_drives/drive_emergence.py: 9f3c0a15f6e6bf67e45e25969e599873d35dd6f7
- theory_x/stage_drives/competing_drives.py: d24685fec6ac806fdd245c01b8f8c71df8e9cc7a
- theory_x/stage_gate/coherence_gate.py: 39f73108cb36e886cfc8dafe045646acba15549e
- theory_x/stage_world/expectations.py: 994b552e03ef12c6b76fe5161095731665fc167c
- theory_x/stage_world/commitments.py: fd11771f2a14c4abf5572e9f9327fcb78bb5f5ef

This remains a bounded source audit. The active environment, API access controls outside the route body, actual flag values, row volumes, model reliance and runtime frequencies have not been observed. No runtime or test behaviour, schema, flag, host state, experiment, merge or deployment was changed.



## M0.3–M0.4 forward/backward audit — active Diversity ecology and retention reconciliation (23 Nov 2026)

### Active DiversityLoop and its real consumers

- run.py constructs and starts DiversityLoop during normal boot. Its daemon thread polls every 60 seconds and calls GrooveSpotter.detect_all(), DormancyScanner.scan_incremental(), and ClockRunner.tick(current_fire_count()). FountainGenerator calls notify_fire() after each completed Fountain output, incrementing the process-local fire counter.
- GrooveSpotter writes groove_alerts and signal_cooldown records from recent own-content repetition/phrase/centroid patterns. Fountain reads active signal_cooldown content while scoring curiosity candidates and reads recent groove_alerts for multiple selection/feedback checks. The curiosity selector re-ranks the existing candidate set; its source comment explicitly says it does not drop candidates. These are genuine source-to-selection edges, not merely GUI telemetry.
- DormancyScanner updates dormant_beliefs. ClockRunner's fast pass calls wake_one(), which marks the highest-scored eligible dormant belief reanimated and sets the module-level pending item. Fountain later calls pop_reanimated() and can add that belief to its context candidate list at its reanimation cadence. Source comments describe a normal 20-fire cadence and an accelerated 5-fire cadence during a sustained low-striking-rate trough. The 60-second poll means these are threshold-driven nominal cadences, not a guarantee of one execution for every exact 20-fire interval under bursts.
- The trough path can also write a Tier-6 self_rut_notice belief, throttled to once per two hours. This is a state-writing self-observation triggered by the measured striking-rate condition; it is not just a log line.
- ClockRunner's fast/medium/slow clocks are thresholded at 20/200/2000 fire-count increments. The fast path decays belief_boost, runs another dormancy scan and attempts reanimation; the medium path records active groove-alert and collision-grade summaries; the slow path invokes GraderEvolver. These clock operations are triggered by the loop's observed fire count and 60-second poll, not by a dedicated timer per threshold.

### Diversity mechanisms whose production edges remain incomplete

- DiversityLoop constructs a CrossbreedGrader instance, but its active _run() method never calls the instance's grade() method. The grader's grade() method is the inspected writer of collision_grades; ClockRunner's medium/slow paths and the diversity panel read collision_grades, while GraderEvolver skips when fewer than ten rows exist. The active boot-managed producer for those grades is therefore not established by this loop. Other production callers have not been globally excluded.
- Fountain's own-belief candidate query LEFT JOINs belief_boost and converts boost_value into a bounded recency/time bonus. ClockRunner decays existing boost rows, but the inspected active DiversityLoop does not call apply_boost(). The current producer of new boost rows remains unresolved; do not infer that the grader automatically creates boosts.
- ClockRunner also stores a per-instance _reanimated_belief and exposes get_reanimated_belief(), while wake_one() separately stores the module-level pending item consumed by Fountain's pop_reanimated(). The inspected live hand-off uses the module-level item; the per-instance getter has no identified consumer in this path. This is redundant state, not evidence that reanimation is disconnected.
- ArcLoop remains disabled in run.py. Its tables can still be read by evaluation/recorder code, but the inspected normal boot path does not produce new arc memberships through ArcLoop. Do not infer active arc formation from table/schema presence.

### Retention documentation correction: residue

- theory_x/diversity/residue.py's module docstring says unconsumed residue is not in nex_db_reaper TARGETS and therefore never ages out. That statement is stale against the inspected repository revision: nex_db_reaper.py explicitly includes beliefs.db.residue with a two-day retention window. The reaper's target is timestamp-based on created_at, so the repository defines cleanup for old unconsumed as well as consumed residue rows.
- residue.py's own inline reaper only deletes consumed rows older than seven days; the separate DB reaper is the mechanism that supplies the shorter two-day TTL. The systemd service/timer definitions describe a nightly run around 04:00, but their installation/enabled state on the deployed host is UNKNOWN. Therefore the code-level retention target is verified; actual host execution and present row counts are not.
- No retention policy or data was changed. The stale residue module docstring should be corrected only through an approved source change, not by silently altering the reaper or deleting data in this Phase 0 pass.

### Source hashes

- run.py: 73a2c58a4f5f0348135a46eb83d6cdd61db874e7
- theory_x/diversity/loop.py: 0032eed6df58965161413825d89261bafa86d398
- theory_x/diversity/groove.py: 9d52c1b07ea54ad072b48245f6c44615e49967bf
- theory_x/diversity/dormancy.py: e75b793da32ad3909bc4c31d682459d53ebdc07f
- theory_x/diversity/consolidation.py: 6d9432af3287ad875571c74459995aaf2f742fb5
- theory_x/diversity/reanimate.py: 092fa76f8e8dadf7e65f5be1b648afe98a8e4593
- theory_x/diversity/residue.py: 4a6abc80cbe6177e4069f3d350a987e531332d9f
- theory_x/diversity/grader.py: 57fd77caa258cab6cea2fd6d870224b619a6549a
- theory_x/diversity/boost.py: 1c263965ef2fcc8b429d440300ef47da988b1325
- theory_x/diversity/evolver.py: 34ed3a6577d581a855b4372da923d72a5ec481fc
- theory_x/stage6_fountain/generator.py: 43644876295ffdd649a240f52a7946c666a8579f
- nex_db_reaper.py: 5cfb609a8ad8a5f9bd0ab83729d8b42220700658

This is a bounded source-level reconciliation. It does not establish runtime flag values, reaper installation, database row counts, frequency of the nominal fire-count thresholds, or whether the identified incomplete grader/boost producers have other external/manual callers. No runtime or test behaviour, schema, retention policy, data, flags, host state, experiment, merge or deployment was changed.



## M0.3–M0.4 forward/backward audit — optional Chat affect and operator prompt faculties (23 Nov 2026)

### Shared activation boundary

The inspected Chat handler invokes these blocks only on the voice-composition path (the branch where a model-composed reply is required). Each block is additionally gated by its own environment flag and admin session. Source comments describe them as prompt-only; no routing or belief-selection change is performed by these blocks. Their flags' deployed values are UNKNOWN. The separate NEX5_CHAT_WORKSPACE selector is source-commented default OFF; if enabled, it budget-selects among the assembled blocks, but exempt blocks are retained even when they exceed the nominal character budget.

### Individual input and state paths

- OperatorModel reads only the configured operator-intake text file (default path in its module) and formats answer lines; a missing/unreadable file yields no block. Its caller requires NEX5_OPERATOR_MODEL=1 and an admin session. The separate NEX5_OPERATOR_ANCHOR block is a constant second-person addressee instruction, also admin-scoped; it does not read or recite operator details.
- Compassion computes semantic distress salience/register from the current message using embedding anchors, then advances and persists compassion_state. This state is a single id=1 row in conversations.db, not keyed by session. NEX5_COMPASSION_V2 optionally changes the distress-anchor handling. The prompt block therefore has a persistent cross-turn substrate state, but the current code path is global across admin sessions rather than per-session. Actual multi-admin use is unknown.
- Compass is a prompt-only moral-weighting composition. It reads current-message distress without mutating Compassion's level, reads Amoha state, and calls self_binding._cluster_reads() to identify high affliction/distortion signals. It returns a held-open weighing, not a rule verdict. It is not evidence that the SelfBinding background process is running.
- Equanimity reads Raga and Dvesa detector outputs and suppresses its stance when Compassion distress is live. It is a prompt-only hold-steady cue.
- Apramada reads the global momentum carry and up to three open ProblemMemory items, then checks whether the current message attends those threads. It emits a vigilance cue for a held thread at risk of being dropped.
- Virya reads current_focus/open-problem content and recent Fountain thoughts to estimate drift from the hard thread. It yields when Equanimity is FULL. It is a prompt-only re-engagement cue.
- Sraddha searches live, unpaused Tier-6/7 beliefs for current-message token overlap, then evaluates confidence, corroboration and belief-edge degree before emitting a support cue. It does not read belief_warrant; this remains a separate support calculation.
- Prasrabdhi reads Raga and the Virya hard-thread/drift calculation; it emits only when circling is off-focus rather than legitimate sustained attention.

### Scope distinction

The eight named affect/operator prompt faculties above are present in the Chat voice-composition path. A source scan of the inspected FountainGenerator found no imports or flag references for these specific Chat faculties. Do not infer that these Chat blocks also participate in Fountain. Fountain has its own distinct optional faculty branches already mapped elsewhere in the Crosswalk.

### Source hashes

- gui/server.py: 5ee8b167f386466c383090445c63a84810bbae52
- theory_x/stage_tom/operator_model.py: b6e45b58cf811ab68bfa92103f5bf3bea48ba1da
- theory_x/stage_affect/compassion.py: eeed5387a828c8e16f7b946474dd5fafc91d04b0
- theory_x/stage_affect/compass.py: 64ecfbed96c8ecb350efa2b4c0f28975af625a71
- theory_x/stage_affect/upekkha.py: d3080e469204a7f53eadab1ad36a73c391d8dad6
- theory_x/stage_affect/apramada.py: a64ad433d78da0d2f1221dc472d925316fb4b216
- theory_x/stage_affect/virya.py: 02b66b8a355b25685f97de3f41601bf622dc1e5b
- theory_x/stage_affect/sraddha.py: 74d009c10182310d4f84ffb41adfdfc9a0ee6738
- theory_x/stage_affect/prasrabdhi.py: cec8b3e8e2ad1d312d26ff7a2c16dd93d0638047
- theory_x/stage_tom/self_binding.py: acbbe02e00723ebc6c5fd13236251f4877259ce5
- theory_x/stage_tom/amoha_detector.py: 8012d5d34d502e3a14fa7f61e2c525dc779c4206

This remains source-level evidence. No flag values, file presence on host, number of concurrent admin sessions, actual prompt composition, model reliance or behavioural effect has been observed. No runtime/test behaviour, schema, state, flag, host configuration, experiment, merge or deployment was changed.



## M0.3–M0.4 forward/backward audit — reshape outcome semantics and warrant activation (23 Nov 2026)

### Holding-zone reshape: transformation is not gate acceptance

- HoldingZoneResolver._process_reshape_pending() fetches up to ten pending rows, transforms each, and calls CoherenceGate.check(new_packet).
- The returned GateDecision is discarded. If the call raises, the exception is logged, but the original held row is still marked with terminal action "reshaped", the transformed preview is stored, and _reshape_count is incremented.
- Therefore the terminal status currently means at most "transformer returned a packet and the resolver attempted gate resubmission"; it does not establish that the gate accepted the new packet. In the exception branch it records "reshaped" despite the resubmission having raised.
- A non-exceptional REJECT, HOLD or another non-ACCEPT result is likewise not distinguished in the original row's resolution record. The gate may create its own new held/rejected state, but that outcome is not linked into the original held_resolutions row by this code.
- The accurate source-level classification is an outcome-accounting/observability gap, not proof that the transformed content bypasses the gate. The gate call is present. Whether "reshaped" was intentionally defined as "transformed and resubmitted" rather than "accepted" must be reconciled with the authoritative spec before any change.

### Warrant: evidence recorder is wired; score pass startup is not established

- run.py conditionally constructs and starts WarrantRecorder only when NEX5_WARRANT_RECORD=1. The recorder appends belief_survival checks and accumulates belief_use_day / belief_use_days from retrieval, Fountain anchors, synthesis, lineage and arc membership evidence.
- stage_warrant/warrant.py separately defines WarrantPass. Its run_once() calls compute_all() and persist(), creating/updating the derived belief_warrant side table. Its docstring says it is started only when NEX5_WARRANT=1 (run.py).
- The inspected run.py startup path contains the WarrantRecorder block but no import, construction or start of WarrantPass. The inspected gui/server.py startup path likewise has no WarrantPass construction. The Stage 2 dynamic factory has a retention loop but no WarrantPass registration in the inspected section. Thus the module's "run.py" startup claim is not supported by the inspected boot wiring.
- Recorder activation and warrant-score calculation are distinct: enabling NEX5_WARRANT_RECORD can collect raw evidence without calculating belief_warrant through WarrantPass. No claim is made about manual/CLI invocation or other external callers; those were not exhaustively excluded. The actual host flag values remain unknown.
- A second bounded completeness risk exists in WarrantRecorder.use_cycle(): the Fountain retrieval/event and synergizer cursors use monotonic IDs, but the belief_lineage and arc_members cursors use created_at/joined_at timestamps with a strict greater-than predicate. If a capped batch ends partway through multiple rows sharing the same timestamp, the cursor advances to that timestamp and remaining rows at the same timestamp are skipped on the next cycle. This is conditional on timestamp ties at a batch boundary; no incidence is established. It merits a fixture-level test before any repair.

### Source hashes

- run.py: 73a2c58a4f5f0348135a46eb83d6cdd61db874e7
- gui/server.py: 5ee8b167f386466c383090445c63a84810bbae52
- theory_x/stage_gate/resolver.py: c89fa5dcea4ffb5c14c1b528f16982efe19a0d4d
- theory_x/stage_gate/holding_zone.py: b3fc5713deee86a848782c671468ae4af9d7f53e
- theory_x/stage_gate/coherence_gate.py: 39f73108cb36e886cfc8dafe045646acba15549e
- theory_x/stage_warrant/recorder.py: ade231c1fc7c8da7f90f8f7ab375d352837a7c79
- theory_x/stage_warrant/warrant.py: a15bc9d012fffac319adf1634f52eb1fde0e35b6
- theory_x/stage2_dynamic/__init__.py: 7b35f304cf823b555a4c6ec78722a07d017de576

No runtime/test behaviour, schema, data, flags, host state, experiment, merge or deployment was changed. These findings are evidence and test-design candidates only; any behavioural repair requires the canonical specification and founder approval.



### Existing test coverage checked for the reshape and warrant findings

The repository's current tests were inspected to determine whether these source findings are already exercised:

- tests/test_reshape.py covers successful transform/re-submit, transformer returning None, the ten-row bound, and an error while inserting reshape_pending. It does not exercise an exception thrown by CoherenceGate.check() during resolver resubmission, nor assert how a returned REJECT/HOLD/RESHAPE outcome should be represented in the original held_resolutions record. The existing "gate_unaffected_by_reshape_path_error" test concerns put_reshape_pending failure at initial gate time, not resolver resubmission.
- tests/test_warrant_recorder.py covers rotating survival windows, distinct use days, idempotence, identity-block exclusion and disabled-loop inertness. It does not cover timestamp ties spanning the lineage/arc cursor batch boundary.
- tests/test_warrant.py covers score arithmetic and that WarrantPass.start_loop() is inert when NEX5_WARRANT is unset. It does not verify that run.py actually constructs/starts WarrantPass when the flag is set.
- These are test-coverage observations from the inspected files, not test execution results. No tests were run or modified in this pass.

Test source hashes:
- tests/test_reshape.py: de58caba4855ef05a9415bc3f4bc57a703f2a136
- tests/test_warrant_recorder.py: b16fa6185340f26a57c9e22c8c525a161e6e61db
- tests/test_warrant.py: 99e639bcf3bd8c1f6e5ab1acbf5b61f20e438b51



## M0.3–M0.4 forward/backward audit — recursive self-binding and quality-signal reach (23 Nov 2026)

### Recursive self-reading: active per-fire path and duplicated bind writes

- FountainGenerator calls recursive_self.format_for_prompt() during normal fire prompt composition. recursive_self.perturbation() refreshes its bound state by calling self_binding.bind(), which writes/replaces dynamic.db.self_state and appends a self_state_history row.
- Later in the same Fountain fire, generator calls recursive_self.perturbation() again to set _pending_nudge_active for the completion-time recursion_attrib row. That second call again invokes self_binding.bind(). Thus the inspected normal path performs two fresh self-binding writes/history appends per Fountain fire: one while composing the prompt line, and one while capturing the nudge flag. The two history rows are separate timestamps, not a single shared observation.
- This is a source-confirmed duplicated recomputation/write path. Whether the history is intended to represent each bind invocation or each fire is unresolved; it may inflate the apparent number of self-state observations. No runtime row-rate measurement was made.
- Generator itself writes recursion_attrib at fire completion using the captured _pending_nudge_active, current hot_branch and prior branch. The recursion_attribution.py docstring's standalone watcher/sample instructions are not the only path; the generator has its own inline sampler. Its helper _fixation_teeth() reads the latest recursion_attrib branch as an input to optional NEX5_RETRIEVAL_TEETH branch-carry diversion.

### Value-drift is not currently reflected in the bound self-state

- self_binding.bind() contains a comment that it reads the last logged value-drift verdict, but the implementation assigns drift = "clean" unconditionally. It does not query value_drift_log.
- value_drift_monitor.check() is a separate explicit check that makes model calls and appends value_drift_log. No automatic invocation was found in run.py, gui/server.py or FountainGenerator in the inspected revision.
- Consequently, the self_state.drift column is not a live reflection of value_drift_monitor results in this source path; it is always written as "clean". The self-binding synthesis/components returned to recursive_self do not currently include drift, so the direct behavioural impact of this placeholder is not established. This is a source/comment mismatch, not a claim that the value-drift monitor never runs manually.

### Quality synthesis: signal reaches attention, but only for a narrow payload type

- NEX5_QUALITY_SYNTH=1 in FountainGenerator.__init__ starts quality_synthesis.start_loop(). The loop scores recent genius_tags by fountain_event.hot_branch and writes quality_signal.json. This is a real background producer.
- Stage 2 attention._quality_multiplier() reads that JSON and maps high/low branch verdicts to 1.20/0.82 multipliers. Therefore the quality signal does have a downstream reader; it is not merely a log-only metric.
- However, _magnitude_for() returns early for string payloads and numeric payloads before calling _quality_multiplier(). The multiplier is applied only in the final fallback branch for values that are neither strings nor numbers. Thus the documented multiplier does not affect the ordinary string or numeric event paths through this function. This is a source-confirmed scope limitation; the distribution of actual adapter payload types and resulting live impact are unknown.
- Quality signal file absence/read failure leaves the cache/neutral result in place; actual flag values and whether the loop is running are unknown.

### Source hashes

- theory_x/stage6_fountain/generator.py: 43644876295ffdd649a240f52a7946c666a8579f
- theory_x/stage_tom/recursive_self.py: ada4aeb260a8deb70418c03dc9180f71cddec714
- theory_x/stage_tom/self_binding.py: acbbe02e00723ebc6c5fd13236251f4877259ce5
- theory_x/stage_tom/value_drift_monitor.py: e08a9649bd94e9094b49aeae59aa9f8feeacbff5
- theory_x/stage_tom/quality_synthesis.py: 284d37ef654eb2e43783e3cb6200e3f995229d75
- theory_x/stage2_dynamic/attention.py: d2765c7618e8421bb3e60c8898f749f2370f0344

No runtime/test behaviour, schema, data, flags, host state, experiment, merge or deployment was changed. These are source-level reach and accounting findings; any change requires the authoritative specification and founder approval.


## M0.3–M0.4 source-to-sink audit — Stage-TOM and Stage-Affect continuation (23 Nov 2026)

**Inspected implementation revision:** PR #65 integrated source head `3d5df48e6539818097b58b6e936059fae946ceca`. This is static source evidence. Optional flag values, deployed process wiring and live effects remain UNKNOWN.

### Structured present — a real optional Chat state write

- `gui/server.py::_assemble_chat_blocks()` computes salience for the Chat blocks. When `NEX5_CHAT_WORKSPACE=1`, it passes those candidates to `global_workspace.select_within_budget()`.
- If `NEX5_SELF_PRESENT=1` as well, the helper calls `stage_tom.self_present.update(session_id, salience, conversations_writer, conversations_reader)` before arbitration.
- `self_present.update()` reads the previous vector for that session, applies the bounded 0.7 carry / 0.3 current-turn blend, then writes the new vector, winner and turn count to the `self_present` table in conversations.db. It is therefore a stateful selection input, not merely a descriptive prompt line.
- The primary key is `session_id`; the implementation is session-keyed. `tests/test_self_present.py` covers the blend, persistence across turns, eventual yielding to sustained new salience, fail-safe behaviour and helper-level arbiter integration. It does not establish live Chat-route activation or multi-session isolation under concurrent requests.

### SelfNarrative, HOT observations and their actual consumer path

- FountainGenerator conditionally constructs SelfNarrative under `NEX5_SELF_NARRATIVE=1` and appends its returned narrative to the Fountain prompt when the same flag is enabled.
- `SelfNarrative.build_narrative()` reads recent Fountain fires, recent T6 beliefs, active branches and the latest non-retired `source='hot_observer'` belief. It also calls `self_model_aggregator.aggregate_self_model()`; the aggregator is therefore consumed by SelfNarrative, contrary to any reading of it as a standalone-only helper.
- The aggregator counts HOT observations in a 24-hour window, requires at least five, and derives overall and per-branch template/grounded proportions. The result is a summary string; it is not itself a new belief or an independently validated self-model.
- FountainGenerator conditionally calls `hot_observer.observe()` under `NEX5_HOT_OBSERVER=1`. The observer writes a Tier-3 belief every third eligible invocation (minimum 15 words) to beliefs.db. Fountain's retrieval prompt separately samples recent hot_observer beliefs from a 72-hour pool, with near-duplicate filtering, so this source has both a write path and a distinct retrieval path.
- The observer's every-third counter is process-local and resets on process restart. This is a source fact; no live rate or restart effect was measured.

### Source identity — operator backfill versus runtime stamping

- `stage_tom.source_identity.py` provides map, census and historical backfill commands. Backfill is dry-run by default; `--backfill --apply` performs UPDATEs to existing beliefs rows.
- No import/call was found in the inspected `run.py`, `gui/server.py` or FountainGenerator path. It should be classified as an operator/maintenance utility, not as proof that the live pipeline invokes the backfill.
- This is distinct from the separate `substrate/source_kind.py` write-time source-kind stamping path. Do not conflate the backfill utility with automatic provenance stamping.

### Stakes — three distinct mechanisms and one missing mutual-exclusion guard

- `ReadinessEvaluator.score()` conditionally adds the positive `appraise_approach()` bonus under `NEX5_APPROACH=1`, and separately subtracts the `appraise_groove()` cost under `NEX5_STAKES=1`.
- The source comment says these flags are mutually exclusive, but the implementation uses two independent `if` statements and contains no guard that rejects or suppresses the combination. If both flags are set, both terms are applied. This is a **conditional source-confirmed guard gap**; live flag values and actual incidence are UNKNOWN.
- `tests/test_stakes_appraisal.py` verifies the two arms separately, including their individual readiness wiring, but has no both-flags-enabled case.
- The older `NEX5_L4_STAKES` path in FountainGenerator is a third, distinct mechanism: every fifth fire it calls `stakes_monitor.check_world_contact()`, stores `_stakes_active`, and passes that state to the workspace arbiter / grounding-focus override. It is not the same as the `NEX5_STAKES` readiness penalty.
- The ratio-based `stakes_appraisal.appraise()` is retained as a measurement helper and is not the readiness consumer; readiness uses the groove-onset and approach appraisals under their separate flags.

### Stage-Affect wiring and budget treatment

- `run.py` constructs and starts the AffectState background loop. It restores the persisted row on startup and updates the substrate-resident valence/arousal/stability values on its 300-second tick.
- Chat reads `state.affect_state.format_for_prompt()` when the object is present. Fountain's `_valence_reach()` reads the persisted valence/arousal only under `NEX5_VALENCE_DRIVE=1`; the optional composed-emotion prompt line is gated by `NEX5_MOOD=1`. The AffectState tick also has a separate optional one-way `NEX5_EXPECT_MOOD` coupling to event-valence expectations.
- The Chat handler constructs optional admin-scoped blocks for Compassion, Compass, Equanimity, Apramada, Virya, Sraddha, Prasrabdhi and AffectCarry. Compassion and Compass are marked exempt from the Chat workspace budget; the other listed blocks compete with the remaining candidates. Their live flag states are not established by source inspection.
- `conviction.py` explicitly records that its former Chat regroup/order consumers were removed after measured-null results. No current call was found in the inspected Chat/Fountain/boot paths; treat the module as retained source, not a live prompt contribution.
- The composed-emotion helper reads the AffectState row and names a configuration; it does not establish felt emotion. No consciousness or subjective-experience claim follows from these functional signals.

### Test and source references

- `gui/server.py`: `d67df10f4449004c255e38b11b4a1888a4e4934c`
- `run.py`: `73a2c58a4f5f0348135a46eb83d6cdd61db874e7`
- `theory_x/stage6_fountain/generator.py`: `2be85084413f2cc9c4c512d3fa15b4f3d7483711`
- `theory_x/stage6_fountain/readiness.py`: `9132a0acd139ee817b4166dd51abe9ec8cec4108`
- `theory_x/stage_tom/self_present.py`: `501b7b6f17841840a13726852627aface1ab5aaa`
- `theory_x/stage_tom/self_narrative.py`: `5fbc617fadc177ade59b45acf118b77c43ef2e84`
- `theory_x/stage_tom/self_model_aggregator.py`: `f05a03e8450c05bc92975bb668feb4baa7220488`
- `theory_x/stage_tom/hot_observer.py`: `35d4e9774c0e5c7571faf7e1f577253d7d5c76de`
- `theory_x/stage_tom/source_identity.py`: `bfa24e3e63cbc502ebc678e190ac949858db3e4d`
- `theory_x/stage_tom/stakes_appraisal.py`: `6c07e833e991978e956ea4d0a479a1ded885af1f`
- `theory_x/stage_tom/stakes_monitor.py`: `871575360f185351b202efd2b67cc40f35ad3ec4`
- `theory_x/stage_affect/affect_state.py`: `e6d1fd62d6a356929015f0d71586b6f7d80e9be1`
- `theory_x/stage_affect/affect_carry.py`: `e34848d18898608cab28826f26ad9480d4901d93`
- `theory_x/stage_affect/compassion.py`: `eeed5387a828c8e16f7b946474dd5fafc91d04b0`
- `theory_x/stage_affect/compass.py`: `64ecfbed96c8ecb350efa2b4c0f28975af625a71`
- `theory_x/stage_affect/upekkha.py`: `d3080e469204a7f53eadab1ad36a73c391d8dad6`
- `theory_x/stage_affect/apramada.py`: `a64ad433d78da0d2f1221dc472d925316fb4b216`
- `theory_x/stage_affect/virya.py`: `02b66b8a355b25685f97de3f41601bf622dc1e5b`
- `theory_x/stage_affect/sraddha.py`: `74d009c10182310d4f84ffb41adfdfc9a0ee6738`
- `theory_x/stage_affect/prasrabdhi.py`: `cec8b3e8e2ad1d312d26ff7a2c16dd93d0638047`
- `theory_x/stage_affect/conviction.py`: `33c43bd6c7b1e2ec0a1df2056fe03ca447610e74`
- `theory_x/stage_affect/compositional_emotion.py`: `9e8b32559082530457489d0d1df28274774e98c2`
- Tests inspected: `tests/test_self_present.py` (`8d0aff76802adbe1661fe8b16f01c8a32d7d222f`), `tests/test_self_narrative.py` (`a293b97d46a7db14fb9302e2c3206b4516eefdb1`), `tests/test_stakes_appraisal.py` (`d735d5d57b36fbcd88ae9cce4b0898b1943649f2`), and `tests/test_affect_state.py` (`9c8ad303d6b4f6f80587e43e56041cde28089586`).

No tests were run or modified in this pass. No runtime behaviour, schema, database, flag, host, experiment, baseline, tripwire, merge or deployment was changed. These findings are source/test-coverage evidence only; any behavioural correction remains subject to the authority and Gate 0 requirements.


## M0.4 governance invariant — MIND_MAP is descriptive, not an action authority (23 Nov 2026)

The authoritative MIND_MAP metadata explicitly states: "Descriptive only. No node in this map may gate, score, block, or veto an action." The current MIND_MAP renderer is a developer-side YAML → Mermaid/DOT/Markdown generator. Its existing check validates node fields, source references, absent-source claims and stale verification dates. Before the policy guard, however, it did **not** validate the descriptive-only constraint, reject action-authority fields, or check that NEX runtime source does not import/load MIND_MAP.yaml. The existing CI workflow already runs mind_map/mind_map.py --check --verify, but that command did not enforce this invariant.

**DRAFT-005 — source-confirmed CI enforcement gap:** the map's descriptive-only rule was documented in YAML but not enforced by the CI check. This did not establish a live runtime violation: the inspected entrypoints do not import MIND_MAP, and the separate sentience_dag.json is a developer build-order DAG, not the mind map and not a NEX runtime faculty.

**Proposed enforcement:** PR #72 adds check_descriptive_only() to the existing checker. It requires the metadata constraint, rejects explicit action-authority keys on nodes (while deliberately allowing the existing blocked evidence/status modifier), and AST-scans NEX runtime roots for imports of mind_map or direct MIND_MAP.yaml reads. RDO, Watcher, tests and developer tooling are excluded because they may use the map as evidence without making it a runtime authority. Focused tests cover missing constraint, forbidden fields, runtime import/read, and allowed RDO use.

- PR #72: https://github.com/kron777/Nex_v5.0/pull/72
- Exact inspected PR head: 6aa226a80d623f223ef994ca9d2d49d29f7d1966
- CI run: 45272386599, in progress at time of this report update.
- This is a draft CI/governance correction, not a merged or yet CI-verified control. No NEX runtime behaviour changed.



## M0.3 external side-effect audit — optional Moltbook integration (23 Nov 2026)

**DRAFT-006 — conditional outbound-action / dry-run state-accounting gap.** The Stage-7 Moltbook package contains external write-capable operations:
- `DMListenLoop` auto-approves incoming DM requests that pass its claimed-account, karma and red-flag filters, then writes a local `moltbook_dms.approved=1` row.
- `PostLoop` can publish selected Fountain beliefs as external posts.
- `DMResponder` can call the local LLM and send replies to external DM conversations.
- `scripts_moltbook_seed.py` can send opening DMs to locally approved conversations.

The `MoltbookClient` defaults `MOLTBOOK_DRY_RUN` to `1`; non-GET requests return a dry-run result without HTTP POST. However, the consumers do not consistently distinguish that result from a successful external action:
- Listener records the conversation as locally approved after `dm_approve()` returns, including a dry-run stub.
- Poster records the post as `posted` and advances the queue after `create_post()` returns, including a dry-run stub.
- Responder marks a reply `sent` after `dm_send()` returns, including a dry-run stub.
- The one-shot seeder's `main(dry_run=False)` parameter is not passed into `MoltbookClient`; with the client's default dry-run enabled and no `--dry-run` flag, the script can log/count a message as sent although the client did not POST.

**Wiring boundary:** no startup construction of `DMListenLoop`, `PostLoop` or `DMResponder` was found in the inspected `run.py` or `gui/server.py`. The GUI `/api/moltbook/chats` route is read-only. The inspected `test_moltbook_optional.py` covers missing/installed table handling and HUD/daily-life reads, not loop startup, external writes or dry-run accounting. This is bounded source evidence, not proof that no operator or external launcher can start the loops.

**Classification:** source-confirmed conditional state-accounting defect in dry-run paths; actual activation, credentials, `MOLTBOOK_DRY_RUN` value and live external actions are UNKNOWN. No network request was made and no local database or flag was changed. No correction is applied pending Gate 0 and explicit approval of the external social-action policy.

Source hashes:
- `client.py` `0b60ce8ab9ec2e935c9abb55311235f07e43631e`
- `listener.py` `54c5a1d91aa54525c768d0b0c4914d6d830e6d83`
- `poster.py` `3acdf141685c28b60ea66102e93b01ead27f11be`
- `responder.py` `0e568897167e458b61701b29e3fcd2538ab22923`
- `scripts_moltbook_seed.py` `fa76ea6fce757d108060435f32a2955ca0f70854`
- `tests/test_moltbook_optional.py` `6bff5f1a331cd2133396853960e3cb3f9f39c3a6`
- Inspected boot/GUI hashes: `run.py` `73a2c58a4f5f0348135a46eb83d6cdd61db874e7`; `gui/server.py` `d67df10f4449004c255e38b11b4a1888a4e4934c`



### Host-log qualification — Moltbook activation and checkout identity (23 Nov 2026)

The supplied host log file `Pasted text(10).txt` records repeated `theory_x.stage7_moltbook` warnings on 16 Nov 2026 between 10:52 and 10:56: the integration was disabled because `/home/rr/.config/moltbook/credentials.json` was missing. At 10:57:13 the supervisor received SIGTERM; the scheduler and decoder stopped and NEX reported a clean STANDBY exit. This means a Moltbook loop was instantiated in the host runtime at that time, despite no loop startup being found in the inspected GitHub PR65 snapshot's `run.py` or `gui/server.py`.

The same log material identifies the runtime data path under `/home/rr/Desktop/Desktop/nex5`, while shell commands refer to the separate audit checkout `/home/rr/Desktop/NEX_AUDIT/Nex_v5.0-main`. It contains no `git status --short`, branch name or `git rev-parse HEAD` for both checkouts. Therefore the active host checkout and the GitHub snapshot used for this audit are **not proven identical**. The 16 Nov missing-credentials observation is historical, not a current credentials/status claim; no successful Moltbook post or DM is evidenced by that log excerpt. Current process/standby state remains UNKNOWN.

This qualifies DRAFT-006: the GitHub snapshot has no inspected startup wiring, but the host log confirms a locally instantiated loop in a potentially divergent checkout. Manus must compare both checkout identities and the current startup path before any activation claim or code correction.



## M0.3 belief-write instrumentation — TaggingBeliefWriter and IntakeResonance (23 Nov 2026)

The active boot path wraps the beliefs writer with `TaggingBeliefWriter` in both `run.py` and `gui/server.py`. For an eligible explicit-column `INSERT INTO beliefs` where the caller has not already supplied a `tags` column and the content parameter can be located, the wrapper:
1. runs `tag_ops.generate(content)` and rewrites the insert to include generated tags;
2. unless `NEX5_INTAKE_RESONANCE_OFF=1`, lazily constructs `IntakeResonance` and calls `compute(content)` before the underlying belief insert.

The resonance probe compares the incoming content against Tier 1–3 standing beliefs and a bounded Tier-6 pool. The T6 reserve logic is separately covered by `tests/test_intake_t6_reserve.py`; `tests/test_tag_protocol.py` covers tag generation/writer injection. No test in those files covers the default-on resonance logging, log retention, failed-insert association or cost.

`IntakeResonance.compute()` writes a row to `intake_resonance_log`, including a content excerpt (up to 500 characters), score, top-match belief ID and timestamp. The wrapper calls the probe before the actual belief insert, and the log has no incoming belief foreign key. `substrate/init_db.py` creates the table and indexes, but the inspected `nex_db_reaper.py` retention target list does not include `intake_resonance_log`. No retention limit or cleanup path was found in the inspected code.

The optional `NEX_TAG_FEEDBACK_ON` path is separate: it reads user tags from `fountain_events.tag` and can add tag context to Chat/Fountain prompts when enabled; it is default-off. Do not conflate that user-tag feedback with auto-generated `beliefs.tags` from TaggingBeliefWriter.

**Classification:** source-confirmed default-on write-path instrumentation and append-only content logging; not a demonstrated change to belief tier or selection. Data retention, log growth, embedding cost and failure association require a measured policy decision. No code or database changes made.

Source hashes:
- `writer_wrapper.py` `c267de05ebe279dc3992ae33d7108c0b77c3401b`
- `tag_ops.py` `d12b8d82767a22fae03b65484c34163fc99b48f7`
- `intake_resonance.py` `62c9b8bd200e49d3d7032f4815b267175d4c557f`
- `init_db.py` `575c95769939f85a776ab698d4c16f17cc1ba238`
- `nex_db_reaper.py` `5cfb609a8ad8a5f9bd0ab83729d8b42220700658`
- `tests/test_tag_protocol.py` `69ff8b38f3bf5930a90b8ed029de7fcee6ddb2e3`
- `tests/test_intake_t6_reserve.py` `1d892aa0de1649de10e93c92bfafa206f8e13819`

## M0.3 World Bridge — prompt injection vs Phase-A documentation (23 Nov 2026)

**DRAFT-008 — source-confirmed documentation/implementation mismatch; approval intent unresolved.** The `theory_x/world_bridge/selector.py` module and class docstrings describe Phase A as selection/logging only, with prompt injection deferred to Phase B. The inspected runtime path is further along:
- `run.py` constructs `WorldBridgeSelector` and passes it to `FountainGenerator` unconditionally.
- The selector module has `ENABLED = True`; the inspected path does not consult the registered `NEX5_BRIDGE` flag.
- Each Fountain generation calls `select_and_log(mark_injected=True)`; when fresh events are returned, the generator appends formatted stream/body text to the composition prompt.
- Selection is bounded to at most five events, 150 characters per event and a 1,500-character total injection budget. The selected event JSON and `injected` status are written to `world_bridge_log`.

The code therefore implements prompt injection when eligible sense events exist, despite the selector documentation describing Phase A only. The referenced World Bridge Design v0.2 and any approval record were not located in the inspected repository/Library material, so this is not yet classified as an unauthorized change; intent and phase approval remain unresolved.

`substrate/init_db.py` creates `world_bridge_log`; the inspected `nex_db_reaper.py` target list does not include it, and no cleanup path was found. The log stores selected-event JSON (including formatted body snippets), stream names and injection status. Live selection frequency, actual host flag/config and data volume are UNKNOWN.

Source hashes:
- `selector.py` `7b71b2b66e663b58a6f5eb71707153380cd882d0`
- `generator.py` `d57bde71eca5f5968964b2846b8a34cffa8964a2`
- `run.py` `73a2c58a4f5f0348135a46eb83d6cdd61db874e7`
- `init_db.py` `575c95769939f85a776ab698d4c16f17cc1ba238`
- `nex_db_reaper.py` `5cfb609a8ad8a5f9bd0ab83729d8b42220700658`

No prompt, runtime flag, database or host changes were made.



## M0.5 fixture trace sample — generated, verified and committed (23 Nov 2026)

The exact-head PR65 workflow passed at source revision `cffbbc94b5a494247d127abf2720886a08f7a567` (run `45273123963`). It uploaded artifact `NEX_CAUSAL_TRACE_SAMPLE` (artifact ID `14865998487`), and the verified JSON was committed in this Phase-0 evidence branch as `NEX_CAUSAL_TRACE_SAMPLE.json`.

- Fountain cycle: 14 records, from scheduler tick through prompt construction, model output, candidate generation, writer deltas, quality/coherence gates, crystallization and speech-gate HOLD to thought return. All non-root records have explicit earlier causal parents. The prompt-block-manifest writer record is now linked to the model-input and workspace-selection records.
- Chat turn: 11 records, from input arrival through message persistence, retrieval, context assembly, model input/output, sanitization and response persistence. All non-root records have explicit earlier causal parents. This fixture returned `no_belief_context`; it does not validate a populated retrieval/context path.
- The Fountain fixture's speech gate returned `hold`; the sample does not prove a queued/played/audible speech result.
- Both tests verified trace-overlay ON/OFF equivalence for the covered outputs, model requests, database rows and SQL read sequences. Raw prompts/responses and database rows are not included in the sample.

**Status:** the M0.5 sample and fixture-equivalence checks are complete at the isolated-test level. Live-host trace capture, production prompt-path coverage with non-empty retrieval, and speech-consumer/audibility evidence remain outstanding. This does not satisfy the host/runtime evidence requirements of Gate 0.



### Host-state timestamp qualification (19 Nov snapshot; current state unknown)

A separate `NEX_R77_diagnostics.txt` snapshot reports `NEX5 is currently OFF` (19 Nov 2026). The 16 Nov runtime log shows a clean SIGTERM/STANDBY transition, followed by keepalive/power-switch supervisor activity. These are historical observations only; they do not establish the process or standby-marker state on 23 Nov. The keepalive/power-switch may control relaunch, so Manus must inspect the current marker, process tree and supervisor before any host-side work.



## M0.3–M0.4 source audit — Stage World prediction and self-prediction (24 Nov 2026)

Inspected against PR #65 integrated source head `cffbbc94b5a494247d127abf2720886a08f7a567`. This pass follows the Stage World producers through loop startup, persistence, calibration consultation and the existing tests. It is static source/test evidence; deployed flag values and live incidence remain UNKNOWN.

### Startup and scope

- `run.py` starts `WorldPredictionLoop` only when `NEX5_WORLD_PRED=1`; the source default is OFF. The loop periodically resolves matured `world_predictions` and asks the local voice endpoint for a new directional prediction paired with a random control.
- `run.py` starts `SelfPredictionLoop` only when `NEX5_SELF_PRED=1`; the source default is OFF. Its tick is broader than the startup label suggests: it resolves and creates fire/no-fire predictions, runs the fire-threshold monitor, resolves/creates the `authored_30m` and `selfdesc_novel` targets, and conditionally invokes owned-belief production, commitment scanning and the single expectations reconciler under their separate flags.
- The expectations reconciler can write the expectations ledger and event-valence records; learning and mood remain separately gated. `expectations.reconcile()` also calls the learning-guard tick recorder. No host flag state or runtime activation is established here.

### DRAFT-009 — voice/random market predictions are not a strictly paired baseline

`prediction_generator.make_voice_prediction()` first fetches a baseline price and gives that value to the voice prompt. It then calls `world_predictions.make_prediction()` separately for the voice row and random row. Each call fetches the price again and takes its own `made_at` timestamp. Consequently, the prompt baseline, voice-row baseline and random-row baseline can differ; the voice and random rows are not guaranteed to share the same exact price/time observation despite the paired-comparison description.

There is also a partial-pair accounting path: `make_prediction()` returns `None` when its own price fetch fails, but `make_voice_prediction()` still returns its ordinary result dictionary without treating a missing voice or random row ID as an error. The loop logs a normal prediction result whenever the dictionary has no `error` key. A one-sided sample can therefore be recorded/treated as a successful cycle and later enter the separate source scorecards.

Test boundary: `tests/test_frozen_at_made.py::TestWorldPredictionProducer::test_voice_and_random` calls `make_prediction()` twice with a patched constant price. It verifies frozen columns but does not call `make_voice_prediction()`, assert shared baseline/timestamp identity, or exercise either leg failing independently. No dedicated `WorldPredictionLoop` or `make_voice_prediction` test file was found in the inspected PR #65 tree. This is a source-confirmed experimental-pairing and accounting gap; actual price drift, partial-pair frequency and score impact are UNKNOWN. No severity or repair is assigned.

### DRAFT-010 — calibration data failure is labelled as a negative result

`calibration_consult.consult_self_trust()` returns `level="unknown"` when the tested self-belief is absent. If that belief exists but the live scorecard read fails, the exception branch instead returns `level="none"` and a phrase saying the system has tested itself and was not reliable. The live numbers were unavailable, so that negative reliability conclusion is not supported by the evidence available to the function. `prediction_generator.make_voice_prediction()` stamps the returned level onto the voice prediction row, so the distinction persists as recorded metadata. The prediction itself is not changed by this consultation.

No dedicated calibration-consult test was found in the inspected test tree. The existing frozen-producer test checks that trust stamping does not alter frozen-at-made fields; it does not exercise the unavailable-scorecard branch. Source-confirmed evidence-state misclassification; host incidence and downstream use are UNKNOWN.

### Evidence and test coverage

- `run.py`: `73a2c58a4f5f0348135a46eb83d6cdd61db874e7`
- `theory_x/stage_world/world_loop.py`: `d369250123c9cfa4f73d3ca5cc33708adf71899a`
- `theory_x/stage_world/world_predictions.py`: `d79ace3fa5fc57dea4e34d66bdccfd244ca1b31`
- `theory_x/stage_world/prediction_generator.py`: `fa690c8db470da5a85e7d210a00aa3de75b2f0f3`
- `theory_x/stage_world/calibration_consult.py`: `f6ee331132fb915eb2785a2557ed5d59e6b63a3e`
- `theory_x/stage_world/self_prediction.py`: `a0474c459629e267e418e795419b4b1e1e2f6e48`
- `tests/test_frozen_at_made.py`: `88c4ed6cc757f1ce884b4afa4209a939f61b4763`
- `tests/test_selfpred_targets.py`: `528c26171e930123d18dc9486ec54b98859a613a`
- `tests/test_selfpred_cognitive.py`: `03fad84d60598f16b64a36856c21939c79f876a8`
- `tests/test_expectations.py`: `9d61df7d0cf0421e69e96681b89b8051f498ee61`

The self-prediction target and expectations tests provide meaningful fixture coverage for their individual producer/reconciler logic. They do not close the integrated voice/random market-pair path or the calibration read-failure branch. No tests were run or modified in this audit.

**Disposition:** These are Phase 0 evidence findings, not authorisation to alter the experiment or runtime. The relevant loops are source-gated OFF by default; deployed values remain UNKNOWN. No runtime code, test behaviour, schema, flags, database, host, experiment, merge or deployment was changed.


## M0.3–M0.4 source-to-sink finding — empty-window surprise reaches belief confidence (24 Nov 2026)

Inspected against PR #65 integrated source head `cffbbc94b5a494247d127abf2720886a08f7a567`.

### DRAFT-011 — empty prediction window is treated differently by separate surprise consumers

`PredictiveSubstrate._verify_one()` deliberately records an empty target window as `surprise_score=1.0` with `actual_content=None`; the same row receives `surprise_flag=1` and `big_surprise=1`. This is an explicit sentinel: the expectations reconciler's `_evidence_surprise()` recognises score 1.0 plus absent actual content as `empty_window` and returns no evidence. The normal Stage 2 `SurpriseLoop` also excludes rows with NULL/empty `actual_content` before promoting surprise events into beliefs.

A separate downstream consumer does not preserve that distinction. `FountainCrystallizer.crystallize()` calls `surprise_weighting.confidence_for_fire()` when `NEX5_SURPRISE_WEIGHT` is unset or `1` (the source default). That function selects the most recent `surprise_events` row within 60 seconds, reads `surprise_score`, and computes the confidence boost from the score alone. Although the query selects `surprise_flag` and `big_surprise`, neither flag nor `actual_content` is used to reject an empty-window sentinel. A recent empty window can therefore be interpreted as maximum novelty and raise the next crystallized belief's confidence from the 0.70 baseline to the 0.92 cap.

The PredictiveSubstrate loop is constructed and started unconditionally in the inspected `run.py` source; deployed operation is not established. The confidence consumer's source default is enabled, but the host environment value is UNKNOWN. This is a source-confirmed producer/consumer semantic mismatch and a conditional confidence-inflation path, not evidence that it has occurred on the target host.

### Test boundary

- `tests/test_predictive_substrate.py::test_verify_empty_window_scores_1` explicitly asserts the empty-window sentinel (score 1.0, no actual content).
- `tests/test_expectations.py::test_surprise_empty_window_is_unresolved_never_violated` checks that the ledger does not treat that sentinel as evidence.
- `theory_x/life/surprise_loop.py::surprise_tick()` excludes rows with absent actual content before belief promotion.
- No dedicated `tests/test_surprise_weighting.py` or inspected integration test covers the crystallizer confidence consumer's handling of the same sentinel.

No severity or repair is assigned pending the authoritative acceptance criteria and broader experiment review. No runtime or test behaviour was changed.

Source hashes:
- `theory_x/stage_prediction/predictive_substrate.py`: `24933b4d6217376a1341c351319cc48546543c80`
- `theory_x/stage_prediction/surprise_weighting.py`: `10db4a80a31c065b113290f21d89bd16743a89fb`
- `theory_x/stage6_fountain/crystallizer.py`: `62cbb62cf55b8c39ab1301b9d89d36b37cc16bfc`
- `theory_x/life/surprise_loop.py`: `bb1869e3d5784ca668ca37e8c76cc25998d7a381`
- `theory_x/stage_world/expectations.py`: `994b552e03ef12c6b76fe5161095731665fc167c`
- `run.py`: `73a2c58a4f5f0348135a46eb83d6cdd61db874e7`
- `tests/test_predictive_substrate.py`: `96f5b6dfa21729948499a3b2c483eb9cca050296`
- `tests/test_expectations.py`: `9d61df7d0cf0421e69e96681b89b8051f498ee61`


## M0.3–M0.4 source audit — Fountain EmphasisEngine and PredictionTracker (24 Nov 2026)

Inspected against PR #65 integrated source head `cffbbc94b5a494247d127abf2720886a08f7a567`.

The FountainGenerator constructs `PredictionTracker` and `EmphasisEngine` internally during generator initialization; they are not wired as separate run.py constructor arguments. At each completed thought, the generator scores the thought before inserting its own `fountain_events` row. This ordering is deliberate: the tracker reads the preceding 20 Fountain thoughts, so scoring after insertion would include the candidate itself and suppress its novelty signal. The result is then written to `dynamic.db.emphasis_log` with the corresponding `fountain_event_id`.

The current combiner averages three signals equally: open/stuck problem relevance, overlap with locked Tier-1 keystones, and entity novelty against the previous 20 Fountain thoughts. Drive resonance is still computed and logged, but is excluded from `combined` and `dominant_signal`; the source comment records a prior ground-truth test result of p=0.190 and says it was removed from the combiner. That historical experiment result was not independently re-verified in this pass.

The module and generator explicitly describe the mechanism as observation-only. The score is not fed back into candidate selection, generation, branch choice, crystallization or belief confidence in the inspected path. No downstream reader of `emphasis_log` was identified in the bounded source pass. This is [L1] constructed instrumentation, not evidence of operationally consumed emphasis or improved output quality.

Test boundary: the inspected test tree has Fountain and FountainCrystallizer tests but no dedicated `test_emphasis_engine.py` or `test_prediction_tracker.py`. No test was run or modified.

Source hashes:
- `theory_x/stage6_fountain/generator.py`: `d57bde71eca5f5968964b2846b8a34cffa8964a2`
- `theory_x/stage_emphasis/emphasis_engine.py`: `21d67aa1b86fe224d30dd17fed64cba987e71a6c`
- `theory_x/stage_emphasis/prediction_tracker.py`: `96c74a502616af1ee47d4204612158c8edea545d`
- `run.py`: `73a2c58a4f5f0348135a46eb83d6cdd61db874e7`

No runtime or test behaviour, schema, flags, database, experiment, host state, merge or deployment was changed.


## M0.3–M0.4 source audit — Chat provenance retry measurement (24 Nov 2026)

Inspected against PR #65 integrated source head `cffbbc94b5a494247d127abf2720886a08f7a567`.

### DRAFT-012 — accepted provenance retry is not written to the provenance log

When `NEX5_PROVENANCE=1` and the chat session is admin-scoped, `gui.server.api_chat` captures a pre-turn snapshot, generates a reply, and calls `read_provenance()` on that first reply. The default call logs the mirror/copy metrics and cue decision to `/tmp/nex5_provenance.log`. If the mirror score crosses the cue threshold, the route generates one retry and evaluates it using `read_provenance(..., log=False)`. If the retry is less mirrored, it replaces the first reply as the response returned to the user. No subsequent `read_provenance()` call with logging enabled records the accepted retry.

Therefore, when the retry is accepted, the provenance file records the discarded first draft, not the final response delivered to the user. The trace overlay can record the retry output and selection, but the provenance metrics file does not carry the final response's mirror score. Any analysis treating that file as a distribution of delivered replies would be biased toward pre-cue drafts. This is conditional on the feature being armed and a retry actually being accepted; host flag state and incidence are UNKNOWN.

The source's hard line remains explicit: provenance may identify mirror-dominance or say provenance is not established; it must not claim emotional authenticity or self-grounding. The grounding hint is explicitly unproven and is not used for the verdict.

Test boundary: `tests/test_provenance.py` covers mirror scoring, closed verdict vocabulary, cue thresholds, snapshot capture, and fail-safe behaviour. It does not exercise the `gui.server.api_chat` retry-selection path or assert which reply is written to the provenance log. No route-level provenance retry test was identified in the inspected test tree.

Source hashes:
- `gui/server.py`: `d67df10f4449004c255e38b11b4a1888a4e4934c`
- `theory_x/stage_provenance/provenance.py`: `92671a3e120a1935fab33f6d659ab806f1eb4cc6`
- `tests/test_provenance.py`: `fcefbeccb6bedc3e20798142814d7b96b4e6dca5`

No runtime or test behaviour, database, flags, host state, experiment, merge or deployment was changed.


## M0.3–M0.4 source audit — CounterfactualNode problem-selection rotation (24 Nov 2026)

Inspected against PR #65 integrated source head `cffbbc94b5a494247d127abf2720886a08f7a567`.

### DRAFT-013 — oldest open problem can be selected repeatedly without internal LRU rotation

`run.py` constructs and starts `CounterfactualNode` in an unconditional initialization block when its dependencies construct successfully; no environment gate is present in that block. Its loop waits 300 seconds between ticks. Each `_process_one()` selects exactly one `open_problems` row using `ORDER BY last_touched_at ASC LIMIT 1` (oldest first).

After selection, the node builds a constraint, calls `TimeFetch.fetch_from_beliefs()`, scores candidates, submits buildable candidates to CoherenceGate and inserts ACCEPT candidates as Tier-3 beliefs. The selected problem's `last_touched_at` is not updated in this path. `TimeFetch.fetch_from_beliefs()` is read-only and does not call ProblemMemory's mutation methods. `_maybe_promote()` returns immediately because automatic promotion is intentionally disabled. The schema has no trigger that automatically updates `last_touched_at` on a linked belief insert.

ProblemMemory exposes `touch(problem_id)` specifically to rotate the oldest-touched-first pool when an attempt produces no observation, but CounterfactualNode does not call it. Therefore, if the oldest open problem remains open and no other subsystem updates/touches it, subsequent ticks can repeatedly process that same problem while newer open problems remain unvisited. External updates or closure can change the order, so starvation is conditional rather than established live behaviour.

Test boundary: `tests/test_counterfactual_node.py` covers single-problem selection, candidate/gate handling, and promotion (with the promotion test explicitly skipped because promotion was intentionally disabled). No test seeds multiple open problems and verifies that successive ticks rotate the selected problem or advance `last_touched_at`.

This is a source-confirmed scheduling/coverage risk, not evidence of actual starvation on the host. No severity or repair is assigned.

Source hashes:
- `run.py`: `73a2c58a4f5f0348135a46eb83d6cdd61db874e7`
- `theory_x/stage_counterfactual/counterfactual_node.py`: `76f8146b803d6272721a349c86e3a5530af4df16`
- `theory_x/stage_throw_net/time_fetch.py`: `7a97a76a48eb54d621d1a436fc5c64d5f6ddfd7b`
- `theory_x/stage7_sustained/problem_memory.py`: `4a9dcc839bf0be7bf28338168d8946309c7002f5`
- `substrate/init_db.py`: `575c95769939f85a776ab698d4c16f17cc1ba238`
- `tests/test_counterfactual_node.py`: `1cd15a6a5c0bfe115791eec9a3aae4b4d088a3f8`

No runtime or test behaviour, database, flags, host state, experiment, merge or deployment was changed.


## M0.3–M0.4 source audit — PredictiveSubstrate external-input target population (24 Nov 2026)

Inspected against PR #65 integrated source head `cffbbc94b5a494247d127abf2720886a08f7a567`.

### DRAFT-014 — external-input prediction and verification use different populations

The `external_input` predictor constructs its sample from two separately limited queries: up to 10 non-`internal.*` sense events and up to 10 user messages. It concatenates the sense rows first, then the message rows, and slices the combined list to 10. It does not merge the two sources by timestamp. When 10 qualifying sense events exist, no user messages enter the prediction centroid; with fewer sense rows, the remaining slots go to messages only after the sense rows, regardless of their relative recency. This is not a true most-recent mixed stream sample.

The verifier for `external_input` uses the same time window but queries all sense events without the producer's `stream NOT LIKE 'internal.%'` filter, then adds user messages. Internal sense events excluded from the predicted population can therefore participate in the actual comparison. The target population used to build the centroid and the population used to score it are not equivalent.

This affects the meaning of the resulting surprise score and, conditionally, downstream consumers including SurpriseLoop and the Fountain confidence-weighting path described in DRAFT-011. It is a source-confirmed population/verification mismatch; live event composition and measured score impact are UNKNOWN.

Test boundary: `tests/test_predictive_substrate.py::test_external_prediction_written` seeds sense events only. The external-input verification tests do not exercise a mixed chat/sense window or assert exclusion of internal streams. No test was found for chronological merging or parity between the external predictor's and verifier's stream filters.

Source hashes:
- `theory_x/stage_prediction/predictive_substrate.py`: `24933b4d6217376a1341c351319cc48546543c80`
- `tests/test_predictive_substrate.py`: `96f5b6dfa21729948499a3b2c483eb9cca050296`
- `theory_x/stage_prediction/surprise_weighting.py`: `10db4a80a31c065b113290f21d89bd16743a89fb`
- `theory_x/life/surprise_loop.py`: `bb1869e3d5784ca668ca37e8c76cc25998d7a381`

No runtime or test behaviour, schema, database, flags, host state, experiment, merge or deployment was changed.


## M0.3 security audit — public Chat to Python tool execution (24 Nov 2026)

### DRAFT-015 — unauthenticated Chat can invoke unsandboxed Python execution

**High-impact security risk — conditional network exposure.**

The inspected startup path constructs `ToolRegistry` and `ToolCaller` unconditionally and passes both into `AppState`. In `api_chat`, the raw user prompt is passed to `tool_caller.should_use_tool(prompt, [])`; when a heuristic matches, `build_tool_kwargs()` forwards the raw query as the Python code input and `ToolRegistry.execute()` runs it.

The `python_exec` implementation only searches for literal `import os` / `from os`-style statements using regular expressions. It then executes the supplied text via `subprocess.run(["python3", "-c", safe_code], ...)`. This does not constrain Python built-ins, indirect imports such as `__import__`, file access, dynamic evaluation, or other capabilities available to the application user. The declared `_SAFE_IMPORTS` set is not used as an AST allowlist or execution sandbox. A prompt can include a tool-triggering keyword such as “calculate” in valid Python comment text and still supply executable Python beneath it; no exploit was executed to establish this source-level path.

The route's authentication boundary is explicit: `api_chat` is included in `_PUBLIC_MUTATIONS`, so the central admin gate deliberately exempts it. Tool selection/execution in the chat route has no additional admin check. `run.py` binds to `127.0.0.1` by default, which limits ordinary remote exposure in the default configuration; however, `NEX5_HOST` is configurable. If the service is bound to a non-loopback interface or exposed through a reachable reverse proxy, an unauthenticated caller may be able to execute arbitrary Python with the NEX process account's permissions. Local callers are also within the reachable boundary.

The risk is therefore **conditional on network reachability**, not a claim that the default loopback deployment is publicly reachable. The consequence, if exposed, is high impact: access to files, environment values and processes available to the application account. This is not a claim of observed exploitation or host compromise.

### Test and verification boundary

- `tests/test_tools.py::test_python_exec_blocks_os_import` checks only a literal `import os` string; the corresponding sys test checks literal `import sys`.
- `tests/test_tools.py::test_build_tool_kwargs_python_exec` confirms the query is passed through as the code input.
- No test covers builtin/indirect-import bypass, filesystem/process capability, isolation, or the public route's authorization boundary.
- No exploit or security test was executed. No runtime setting or source code was changed.

Source hashes:
- `run.py`: `73a2c58a4f5f0348135a46eb83d6cdd61db874e7`
- `gui/server.py`: `d67df10f4449004c255e38b11b4a1888a4e4934c`
- `theory_x/stage_capability/tool_caller.py`: `31faba3cc49b60f21069679e920c73442249f919`
- `theory_x/stage_capability/tools.py`: `ff5f251b225c975c01f6bf3c3da9cbad1f77fbee`
- `tests/test_tools.py`: `85c7aa8236e2cdd1005f3ab4aa49c8c6da337d2d`

**Disposition:** security finding for Gate 0 defect backlog and independent review. No severity remediation is implemented here because the governing change-approval gate remains closed. The service should not be exposed to untrusted networks in this state.


### DRAFT-016 — web_fetch allowlist can be bypassed before and after the initial URL check

The same public tool path exposes `web_fetch`. Its allowlist check normalizes the hostname with `parsed.netloc.lstrip("www.")`. Python `lstrip` removes any leading characters belonging to the supplied character set, not the exact `www.` prefix. A lookalike hostname beginning with `w` can therefore be transformed into an allowlisted hostname for the comparison (for example, the string `wcoingecko.com` becomes `coingecko.com`). Whether any such lookalike domain is attacker-controlled is not established.

Separately, after validating the initial hostname, the code calls `urllib.request.urlopen()` with the default redirect handling and does not validate the final URL/host after redirects. A permitted origin that redirects to an internal/private destination can therefore bypass the initial destination check. This is a conditional server-side request forgery (SSRF) path; no redirect or network request was executed, and no reachable internal service is claimed.

The existing `tests/test_tools.py::test_web_fetch_rejects_unknown_domain` checks a straightforward `evil.com` URL. It does not test hostname normalization, lookalike prefixes, redirects, or private-address destinations.

Source hash: `theory_x/stage_capability/tools.py` `ff5f251b225c975c01f6bf3c3da9cbad1f77fbee`; test hash: `tests/test_tools.py` `85c7aa8236e2cdd1005f3ab4aa49c8c6da337d2d`.

**Disposition:** conditional SSRF/allowlist-bypass risk within the same unauthenticated public Chat tool boundary as DRAFT-015. No remediation or exploit testing was performed.


## M0.3–M0.4 source audit — Throw-Net threshold and failure accounting (24 Nov 2026)

Inspected against PR #65 integrated source head `cffbbc94b5a494247d127abf2720886a08f7a567`.

### DRAFT-017 — threshold return values do not gate pending Throw-Net sessions

`TriggerDetector.record_gate_reject()` writes an unfired `throw_net_triggers` row for each qualifying non-Throw-Net CoherenceGate REJECT, then returns whether the same-topic count reached four in 15 minutes. `CoherenceGate.check()` calls this method for every eligible REJECT but ignores its boolean return. Similarly, the Chat gap-deflection path calls `record_gap_deflection()` for each gap refusal and ignores its return value (which reports whether the same-topic count reached three in 30 minutes).

`TriggerDetector.pending_triggers()` selects every row where `fired=0`; it does not filter by threshold count/state. `ThrowNetEngine.run_pending()` runs a session for every returned row. Thus the threshold methods calculate and report threshold crossings, but the active producer → pending queue → monitor path does not use those results to gate session creation. If `NEX5_THROWNET=1`, every logged trigger can be processed, including a first single rejection/deflection, rather than only a threshold-qualified trigger.

The monitor is constructed when dependencies exist but its background loop is started only when `NEX5_THROWNET=1` (source default OFF). This is a source-confirmed threshold-wiring mismatch, not evidence of live session volume.

Test boundary: `tests/test_throw_net_trigger.py` checks the boolean thresholds and verifies that pending_triggers returns unfired rows; `tests/test_throw_net_engine.py` verifies run_pending processes all pending rows. No test verifies that sub-threshold rows remain ineligible or that only threshold-qualified rows reach run_session. The existing tests therefore cover each method independently but not the intended threshold contract across the chain.

### DRAFT-018 — failed Throw-Net cycle can be returned as complete and its trigger consumed

If the outer `run_session()` cycle raises (for example, `TimeFetch.run()` or refinement raises), the exception handler persists the session row with `status='failed'`. After the handler, the function still calls `_try_mark_fired()` and then returns a dictionary with `status='complete'` unconditionally. Because `pending_triggers()` selects only `fired=0`, that trigger is no longer eligible for a later retry. The persisted row and returned result can therefore disagree, and a failed cycle is consumed without an automatic retry path.

This is distinct from a per-candidate CoherenceGate exception: those are caught inside the candidate loop and counted in `outcomes['error']`, after which the overall session can legitimately complete. The existing `test_run_session_handles_gate_error_per_candidate` covers only that inner case. No test was identified for an outer cycle exception, the returned status, or the failed-trigger retry/consumption policy. Whether consume-on-failure is intended is unresolved; returning `complete` when the persisted row is `failed` is source-confirmed.

Source hashes:
- `theory_x/stage_gate/coherence_gate.py`: `39f73108cb36e886cfc8dafe045646acba15549e`
- `theory_x/stage_throw_net/trigger_detector.py`: `4d5b855cfb9debe70fdd84649b62273af9964bff`
- `theory_x/stage_throw_net/throw_net_engine.py`: `6d420f9e3036a055bb9677664b5a44cc805edae4`
- `theory_x/stage_throw_net/monitor.py`: `04f81a7a811f7a40da853e7b2a321e399590b3e5`
- `gui/server.py`: `d67df10f4449004c255e38b11b4a1888a4e4934c`
- `tests/test_throw_net_trigger.py`: `34648ab33397d7de53ca4d8f5fc4cf3fe53ab8e5`
- `tests/test_throw_net_engine.py`: `e5a354809f7ec0d7eec83fbea5d72b04f34a436c`

No runtime or test behaviour, flags, database, host state, experiment, merge or deployment was changed.


## M0.3–M0.4 source audit — FocalSet / WorkingMemory chat influence and session scope (24 Nov 2026)

Inspected against PR #65 integrated source head `cffbbc94b5a494247d127abf2720886a08f7a567`.

### DRAFT-020 — FocalSet is described as log-only but feeds same-turn prompt memory

`gui.server` constructs one module-level `FocalSet(K=4)` for the process. It is shared by all Chat sessions and its implementation has no lock around `update()`, its priority map or its focal-ID set. Each chat turn retrieves up to 10 beliefs for the current prompt, updates this shared FocalSet, and reads the resulting focal IDs.

The code comment calls this “log-only attention tracking (no behavior change)”. However, the same block adds the selected current-turn focal beliefs to a `WorkingMemory` object keyed by the current Flask session ID. Later in the same `api_chat` request, the WorkingMemory injection path reads those just-added items and appends them to `belief_text` when the register is Conversational and `belief_count >= 2`. This is a real prompt influence on that conditional path, not merely logging or cross-turn-only memory.

The FocalSet's priorities and current focal IDs are process-global, so one session's update can influence another session's selection when their retrieved candidate sets overlap. Concurrent chat requests can also interleave between `update()` and `get_focal_ids()`; the FocalSet itself has no synchronization. The later content filter uses the current request's own `_raw_beliefs`, so this pass found no path that directly copies another session's arbitrary belief text into the current session's WorkingMemory. The confirmed concern is shared selection state and potential inconsistent selection, not demonstrated private-text leakage.

The `_working_memory_by_session` dictionary is also process-global, has no registry lock and no cleanup/eviction path. Each WorkingMemory instance is bounded to seven items and has its own internal lock, but the number of session objects in the registry is unbounded over process lifetime. Concurrent first use of the same session can also race the dictionary's check/create sequence. The Flask session ID is generated server-side and stored in the signed session; this audit did not find a client-supplied arbitrary session ID in `api_chat`.

Test boundary: `tests/test_focal_set.py` tests the node's selection mechanics; `tests/test_working_memory.py` tests individual-buffer decay, capacity and concurrent adds; neither tests multi-session FocalSet isolation or the Chat prompt handoff. The WorkingMemory concurrency test does not cover the module-level session registry. `tests/test_conversation_memory.py` tests session-filtered SQL, but `gui.server` constructs a ConversationMemory object without a call to its `state()` method in the inspected module; the actual Chat history path uses `_recent_dialogue()` instead.

Source hashes:
- `gui/server.py`: `d67df10f4449004c255e38b11b4a1888a4e4934c`
- `theory_x/focal_set.py`: `e12531f2858085778ebca75f73a7dee6ec8ce416`
- `theory_x/working_memory.py`: `4e9badadbb3ada939c05fcb4a82455723c0efa36`
- `theory_x/conversation_memory.py`: `5d9be238428ed5559af5117c7ab57bdef34f121f`
- `tests/test_focal_set.py`: `083b8053ff09ef0975f8aab35a120904b2f55423`
- `tests/test_working_memory.py`: `446d90f4c79a515eba08aaac1b24c5c33f0797e3`
- `tests/test_conversation_memory.py`: `9632aa1d9bc0b617cef1b93d31e886174d560b68`

No runtime or test behaviour, prompt, session policy, database, flags, host state, experiment, merge or deployment was changed.


## M0.3–M0.4 source audit — shutdown snapshot and resumption durability (24 Nov 2026)

Inspected against PR #65 integrated source head `cffbbc94b5a494247d127abf2720886a08f7a567`.

### DRAFT-021 — graceful SIGTERM path overrides the snapshot writer's final-snapshot handler

`StateSnapshotWriter.__init__()` registers both an `atexit` callback and its own SIGTERM handler, with the latter intended to write a final snapshot. The normal `run.py` boot path constructs the writer and passes it into Fountain. Fountain calls `write_snapshot()` on every scheduler tick, so periodic snapshots are present in the source path.

Later in the same `run.py`, the application registers its own `_graceful_standby` SIGTERM handler, replacing the handler installed by `StateSnapshotWriter`. That standby handler marks a clean-shutdown timestamp, waits, stops the decoder, drains state via `state.close()`, then calls `os._exit(0)`. It does not call `snapshot_writer.write_snapshot()`; `os._exit` bypasses Python's `atexit` callbacks. Consequently, the writer's advertised final SIGTERM/atexit snapshot is not executed on the normal power-pill/keepalive SIGTERM path. The most recent periodic snapshot remains the recovery point, which may predate final state changes after the last Fountain tick.

This does not mean no snapshot exists: Fountain writes periodically. The finding is specifically that the final-shutdown snapshot hook is shadowed in the normal shutdown sequence. Host shutdown incidence and the amount of state that can change after the last tick are UNKNOWN.

### DRAFT-022 — resumption snapshot is consumed even when database recovery writes fail

`ResumptionSeeder.run()` reads a valid, non-stale snapshot, calls `_promote_beliefs()` and `_reissue_probes()`, then unconditionally calls `_consume_snapshot()` and sets `executed=True`. Both helper methods catch their own database exceptions and return `0` (or a partial count) rather than propagating failure. The caller therefore cannot distinguish “nothing to promote/reissue” from “database write failed”; it still renames the snapshot to `.consumed`. A transient database error can consequently discard the only recovery manifest before the next boot can retry those belief promotions or probe reissues.

The normal boot sequence deliberately calls `downtime.record_boot()` before the seeder because both read the same snapshot and the seeder consumes it; that ordering is correct and source-documented. The issue is the seeder's consume-on-partial-failure behaviour after that read.

Test boundary: the inspected test tree contains downtime, probe-context snapshot and episodic tests, but no dedicated `test_snapshot_writer.py` or `test_resumption.py` exercising SIGTERM handler ownership, final snapshot writing, partial promotion/reissue failure, or consume/retry policy. No shutdown or database-failure test was run.

Source hashes:
- `run.py`: `73a2c58a4f5f0348135a46eb83d6cdd61db874e7`
- `theory_x/stage6_fountain/__init__.py`: `28095c55d0d88bbf49288c7cf399b8c9f4c3ee19`
- `theory_x/memory/snapshot_writer.py`: `367defcc540bab11708ca2cb9aed5a09ee4377cd`
- `theory_x/memory/resumption.py`: `665b379cd6f09842462c469cfa64e4c437e57472`
- `theory_x/memory/downtime.py`: `c609c501a2470be6ef3494e2d918bd05271d1f6d`

No runtime, snapshot, database, test behaviour, host state, merge or deployment was changed.


## Phase 0 defect/risk backlog companion (24 Nov 2026)

A companion `NEX_VERIFIED_DEFECT_BACKLOG.md` has been added to this draft branch for Gate 0 review. It consolidates the DRAFT findings in this Reality Report, separates source-confirmed paths from conditional exposure and unknown host incidence, assigns provisional triage ordering, records the top five documentation/implementation discrepancies and states the evidence-level limits. It is not Founder-approved and does not authorize remediation. The exact-head CI status and M0.1–M0.5 completion limits are recorded in the backlog and ADR-001.


## M0.3 node-level reconciliation (24 Nov 2026)

The Crosswalk now contains an explicit row for each of the 30 declared MIND_MAP nodes, with source path, declared evidence/dark/blocked modifiers, separate L0–L4 assessment, and historical host-evidence caveats. The node-level assessment is not a conversion of MIND_MAP's own evidence vocabulary. Four nodes remain L0, sixteen L1, nine L2-reported (host checkout identity pending), one L3 only in the isolated Fountain fixture, and none L4. See the “Explicit 30-node MIND_MAP → source/runtime evidence crosswalk” section in NEX_ARCHITECTURE_CROSSWALK_v2.md.


### DRAFT-023 — ExecutiveControl is registered but bypassed by the active Chat register path

The GUI module constructs a process-global ExecutiveControl instance and registers it with the Theory X node registry. Its module docstring says it replaces the classify() stub in voice/registers.py. However, the active api_chat route does not call _executive.select(). The route explicitly chooses the user-supplied register when present, otherwise by_name("Philosophical"), with a comment dated 2026-05-29: “default chat to Philosophical”; the comment says to restore the ExecutiveControl branch later. The voice.registers.classify() function remains the Phase 1 stub returning Conversational, and default_register() also returns Conversational.

Therefore, the classifier's unit tests do not establish that it participates in the production Chat route. The current default Chat register is Philosophical, not the classifier's selected register and not voice.registers.default_register(). This may be a deliberate temporary product choice; whether it is approved and still intended is unresolved. The mismatch is between the module's replacement claim, the register module's stated default, and the actual route.

The ExecutiveControl instance is still registered and may be ticked for state monitoring, but that does not consume its classification output. The class also describes itself as thread-safe while its continuity-bias read of _session_registers occurs outside the lock, and its process-lifetime session map has no expiry/cleanup; those are secondary risks if select() is restored to the concurrent Chat path.

Test boundary: tests/test_executive_control.py covers classifier unit behavior and continuity bias, but no route-level test verifies that api_chat calls ExecutiveControl or validates the deliberate Philosophical default. No concurrency or session-expiry test was identified.

Source hashes:
- gui/server.py: d67df10f4449004c255e38b11b4a1888a4e4934c
- theory_x/executive_control.py: af98135e115d43ab01bdae08b2cde71b3f6eecc1
- voice/registers.py: e9d836ec1854572f6209e0f25435aec6653fe4df
- tests/test_executive_control.py: d0ffe94a36e60cb30536759090affc09cfc1c3b1

No register, prompt, runtime or test behaviour was changed.


### DRAFT-024 — Chat passes an empty belief set to ToolCaller even when local retrieval has run

The active api_chat route calls ToolCaller.should_use_tool(prompt, []) rather than passing the beliefs retrieved earlier in the same route. ToolCaller documents its factual web-fetch fallback as “No beliefs found + query looks factual”; with an unconditional empty list, that predicate is always eligible for factual-pattern prompts, even when the route has already assembled local belief context. The heuristic also selects web_fetch for current/latest/today and price/crypto patterns.

This may be an intentional preference for external freshness, but the actual caller does not implement the documented “only when no local beliefs were found” condition. It can cause unnecessary external fetches and increases the reachable surface of DRAFT-016. The precise route branch and intent should be confirmed before any correction.

Test boundary: ToolCaller unit tests include a non-empty-beliefs case that suppresses the factual fallback, but no api_chat integration test verifies that the route passes its actual retrieval result or intentionally forces the fallback.

Source hashes:
- gui/server.py: d67df10f4449004c255e38b11b4a1888a4e4934c
- theory_x/stage_capability/tool_caller.py: 31faba3cc49b60f21069679e920c73442249f919

No tool call, network request or runtime behaviour was changed.


### Manus advisory reconciliation — 24 Nov 2026

The following points are independent technical recommendations, not governing requirements or Founder decisions. The reviewed PR tree did not contain the canonical Master Roadmap or Frozen V2.1 specification; exact acceptance wording must be checked against those authoritative documents.

1. **Asynchronous parentage.** Require an explicit parent edge for an in-scope asynchronous handoff when the producer record exists and consumer identity can be joined to it. Do not infer parentage from timestamps or ordering. The controlled speech-queue commit-before-registration test demonstrates a real unlinked-trace race and a useful partial result, not complete producer-to-consumer lineage. Preserve missing-parent observations as explicit gaps. Additional isolated coverage is recommended for registration failure, trace-registry loss/restart and overlapping consumers. No race-frequency claim is made.

2. **Operation-stage evidence.** Distinguish a pre-call attempt marker, observed callee entry, successful return or exception, persisted outcome, and physical completion. A pre-call marker does not prove callee entry; a returned player call does not prove audio completed or was audible. A queue row marked spoken is software-state evidence only. Persistence claims should be tied to Writer success and, where material, independent read-back. Physical completion remains unobserved without a device/backend acknowledgement.

3. **Observer overhead.** Treat behavioural neutrality and latency neutrality as separate properties. Synchronous JSONL serialization, filesystem writes and shared-lock contention necessarily may add elapsed time. Do not assert zero added delay. Before an acceptance benchmark, agree the representative host/workload and a bounded latency budget; report repeated p50/p95/p99, including concurrency and lock contention. The existing benchmark remains diagnostic and non-gating until its workload and threshold are approved.

4. **L5 classification.** Provisionally treat L5 as a separate generalisation classification and keep the Phase 0 faculty audit at L0–L4 if that is what the canonical roadmap's Phase 0 text specifies. Record L5 separately as exploratory/out of scope unless the canonical roadmap explicitly requires it. The apparent global L0–L5 versus Phase 0 L0–L4 distinction still requires exact-document reconciliation.

These recommendations do not resolve the roadmap's acceptance criteria, approve a latency threshold, certify causal-trace completeness, or authorise runtime, schema, queue, flag, host, experiment, merge or deployment changes. Gate 0 remains unestablished.



### Speech operation-stage evidence addendum — 24 Nov 2026

PR #74 adds an isolated test that inspects the trace from inside the fake synthesis and player call bodies. It confirms that `synthesis_started` and `player_invocation_started` are emitted before the respective callee body begins, and that completion/return events are only present after the call returns. These event names therefore denote pre-call attempt markers in the current implementation, not independent proof of callee entry. No runtime instrumentation semantics were changed.

The existing real-Writer/Reader speech fixture independently reads back the final `spoken` row after the synchronous Writer call, confirming committed queue status in that isolated SQLite test. It does not prove physical playback completion or audibility. The new exact-head test commit is `ec551aac4c634aa21d9b827421dc89f24c0246f2`; CI is pending and no pass is claimed.



### Watcher host-evidence request CI update — 24 Nov 2026

PR #73 exact head `e917f3704647c3431d2f2a86b4abf8ab40818aef` completed workflow run `45283644024` successfully, including the full repository test/baseline gate and MIND_MAP sourcing check. This validates the Watcher request-template coverage and its isolated tests at that commit only. It does not mean any target-host probe was executed: OS/model/runtime measurements, artifact hashes, live checkout identity and performance remain uncollected. PR #73 remains open, draft and unmerged.



### MIND_MAP source-pointer integrity spot audit — 24 Nov 2026

A repository-tree check against the PR #49 evidence branch found 30 declared MIND_MAP nodes. The nine distinct file-typed source references currently present in `mind_map/MIND_MAP.yaml` all resolve to tracked repository files, and each stated line range is within the current file length. This is a pointer-integrity check only: it does not validate the semantic sufficiency of each cited source, re-run the probes, or establish live activation.

The same pass inspected all nine `sentience_dag.json` nodes carrying a `module` field. Seven values resolve as repository paths; two values — `bonsai.py decay_pass (recency penalty)` and `bonsai.py decay_pass (starvation bonus)` — are descriptive function labels, not literal paths. They are therefore not counted as missing source files, but remain less directly navigable than path-qualified module references. The DAG and MIND_MAP are distinct artifacts with different node sets/roles; this check does not assert they should be one-to-one.

The repository tree contains 311 Python files under `theory_x/`. This bounded check does not close the required faculty-by-faculty forward/backward dependency audit, dynamic imports, event/shared-state edges, SQL readers/writers, or downstream consumers. Those remain open for M0.3.



### Boot-orchestrator forward-path audit slice — 24 Nov 2026

Static inspection of `run.py` on this branch confirms a concrete boot construction path, distinct from mere module presence:

- Core factories imported and called from `main()`: `build_scheduler` (stage1), `build_dynamic` (stage2), `build_world_model` (stage3), `build_membrane` (stage4), and `build_fountain` (stage6); supporting construction includes self-location commitment, mode/voice state, drives, memory/resumption, and WorldBridge selection.
- Additional faculties are imported/constructed in the boot body rather than through those five factories: SelfNarrative; CoherenceGate/HoldingZone/Resolver/TriggerDetector; ProblemMemory; GoalManager; Metacognition; NovelAssociation; ThrowNet; SubstrateHarmonic; GeniusTagger; CounterfactualNode; DriveEmergence; CompetingDrives; VoiceEngine; and affect-related components.
- Activation is not uniform. Several constructors/loops are guarded by broad `try/except` blocks and can fail non-fatally. Throw-Net's monitor is constructed, but its autonomous loop is started only when `NEX5_THROWNET=1`; otherwise trigger telemetry remains. WarrantRecorder is only constructed/started when `NEX5_WARRANT_RECORD=1`. The code comments identify some subsystems as log-only.
- This is a source-level boot-path observation, not proof that the target host is running this checkout, that all optional constructors succeeded, or that every constructed component is registered, consumed, or behaviourally influential.

Source anchor: `run.py` at the PR #49 evidence branch (boot setup and faculty wiring, approximately lines 100–420). This slice strengthens the forward boot map but does not close backward-consumer, dynamic-import, shared-state, event, or SQL edge closure across the 311 Python files under `theory_x/`.


### Stage 1 internal self-observation audit slice — 24 Nov 2026

Static source inspection of `theory_x/stage1_sense/internal/interoception.py`, `meta_awareness.py` and `scheduler.py` adds a bounded qualification to the Stage 1 map:

- Interoception reads aggregate belief graph counts through the beliefs Reader and emits an `internal.interoception` SenseEvent to the Stage 1 Writer path. It separately appends a best-effort `/tmp/nex5_interoception.log` record; auxiliary log failure is swallowed. Its first in-process belief-count delta is null.
- MetaAwareness emits Writer queue depths, recent error-channel length and scheduler state. Its external-active count counts enabled flags; it does not measure recent poll success, source reachability or event production.
- The scheduler sets an adapter's enabled flag when enabling it, before a successful poll. Empty poll results are not treated as errors by the scheduler. Consequently enabled/active telemetry must not be interpreted as source health.
- The scheduler docstring says external feeds begin paused, but its constructor unconditionally invokes `start_all()`. This is a source-level documentation/implementation discrepancy, not proof of what is running on the target host.

The backward-consumer search for these two internal stream names remains open. No claim of global absence is made. No runtime/test behaviour, schema, flags, host state or experiment was changed.

### Stage 1 persistence and read-consistency audit slice — 24 Nov 2026

Further source inspection of the Stage 1 adapter base and SQLite substrate found an important qualification to the previously recorded scheduler-status semantics:

- Adapter persistence is one synchronous `Writer.write()` call per SenseEvent, each committed as its own transaction. `Adapter.submit()` catches individual insert failures, records them to the error channel and continues; it returns only the number of writes that returned successfully. A multi-event poll is therefore not an atomic batch and can be partially persisted.
- Because per-event persistence errors are swallowed inside `Adapter.submit()`, the scheduler can update `last_poll_at`, record a zero/partial event count and leave `last_error=None` even when one or more event inserts failed. Thus neither enabled state nor a clean scheduler iteration is a durable-persistence health signal.
- The current `sense_events` schema stores stream, payload, provenance and timestamp with stream/timestamp indexes; it has no dedicated trace or parent identity columns. This does not exclude correlation carried inside payloads or elsewhere.
- Each `Reader.read()` / `read_one()` call opens a fresh read-only connection. Interoception's four aggregate queries are therefore not enclosed in one explicit read snapshot; under concurrent writes their results could reflect different moments. No such inconsistency was observed or measured.

This remains a bounded source-level finding. No live sense.db, emitted event, target-host runtime or downstream consumer was inspected. No runtime, test, schema, flag or host changes were made.

### Stage 1 factory inventory and activation qualification — 24 Nov 2026

The Stage 1 package factory confirms 28 adapter instances are assembled against the shared sense Writer; Interoception receives the beliefs Reader and MetaAwareness receives the Writer map plus a late-bound scheduler reference. The four internal streams are Proprioception (system resource observations), Temporal (clock observations), Interoception (belief aggregates) and MetaAwareness (Writer/error/scheduler telemetry).

The package/factory documentation says external feeds start paused, but the constructed `SenseScheduler` unconditionally calls `start_all()` in its constructor. In this source path, external adapters are therefore enabled and the global run event is set during scheduler construction. This is a source comment/docstring versus implementation discrepancy; it is not evidence of the target host's current process state or successful external polling.

The factory's active list omits Reuters, APNews, PhilPapers and PapersWithCode, which are retained in the source tree but explicitly commented out of factory construction. This audit confirms construction wiring only, not poll success, durable row persistence, downstream use or live activation.

### Stage 1 backward-consumer evidence — 24 Nov 2026

A source-to-sink pass now identifies the following consumers of Stage 1 rows:

- Stage 4 SelfModel queries the latest row for all four internal streams. It maps Proprioception, Temporal and Interoception payload fields into its snapshot. It also fetches the latest MetaAwareness payload, but the inspected code does not use that payload in the returned meta-awareness fields; when DynamicState exists, those fields come from DynamicState instead. This is a fetch-versus-reliance distinction.
- Stage 6 FountainGenerator reads non-internal sense rows in its quiescent branch (latest row, every fifth fire under the inspected condition) and through _recent_sense_sample(), which samples a recent window, filters internal/noise streams, extracts summaries and returns up to a configured number of distinct streams for drift context.
- Fountain also writes an internal.fountain row. The inspected readers above explicitly exclude internal.%, so this producer write is not evidence of a self-consumer.
- tests/test_interoception_fixes.py and tests/test_sense_extract.py provide isolated fixture coverage for portions of the SelfModel and Fountain paths. They do not demonstrate target-host execution or causal impact on a final output.

This closes a bounded backward-consumer slice, not the full Stage 1 audit. Source presence and test coverage do not establish live row availability, call frequency, or row-level decision influence.


### Stage 1 → Stage 2 ingestion audit — 24 Nov 2026

Source inspection of the sense table schema, Stage 2 Dynamic loops and A–F pipeline establishes the following:

- The `sense_events` table is append-only in the inspected schema shape (autoincrement id, stream, payload, provenance, timestamp); it has no per-consumer processing status or retry marker.
- Stage 2's general `_sense_poll_loop()` reads all streams, including internal streams, in ascending id batches of 100. It invokes `run_pipeline()` and advances the cursor after the call without checking the returned hit count.
- `run_pipeline()` catches exceptions internally, writes an error-channel record and returns 0. The caller cannot distinguish this error return from a legitimate zero-branch-match result, so it advances the in-memory cursor and counts the row as a pipeline run. The cursor is saved every 50 rows and on shutdown. Depending on when failure occurs relative to cursor persistence/restart, a failed row may be retried or may be passed permanently; no deployed loss rate is known.
- The A–F pipeline is not atomic across its side effects. Each `pipeline_events` write is a separate synchronous Writer transaction; Stage F mutates tree and membrane state before its final event write. A later failure can therefore leave partial logs/state. No failure was injected and no live partial outcome is claimed.
- The distinct sense-distillation loop excludes internal streams and `external.other_mind`, caps new belief writes at five per pass, but still advances the cursor through the full fetched batch after the cap. Later candidate rows in that batch are not reconsidered by this loop. The code comment explicitly describes the cap as limiting writes rather than cursor movement; whether this deliberate throughput policy is approved remains unresolved.

The result is a materially different set of downstream semantics: general Stage 2 attention consumes all streams; belief distillation consumes a filtered subset with a write cap; Fountain's external context readers apply their own filtering. These are not interchangeable definitions of “Stage 1 data consumed.”

Evidence level: source-confirmed control flow at the PR #49 evidence branch. Exposure, actual row counts, runtime errors, cursor values, and live effects remain UNKNOWN. No runtime, test, schema, flag, host or experiment changes were made.


### Stage 2 internal-stream influence qualification — 24 Nov 2026

The Stage 2 attention mapper narrows the meaning of “consumes all streams.” Internal rows are read by the general sense poller and can match the `systems` branch at Step B, but `_magnitude_for()` returns 0.0 for every `internal.*` stream. The A–F pipeline may still write B/D/E diagnostic rows; Step F skips magnitudes below 0.001, so this inspected path does not update Bonsai attention or the membrane accumulator from internal telemetry. For non-internal text rows, branch matching uses stream and selected payload tokens, with direct stream mappings and keyword-overlap magnitude logic. No live row-level influence is claimed.


### Stage 1 feed failure semantics and complete Fountain input-lane qualification — 24 Nov 2026

The additional source inspection records a distinction between an adapter's successful return and completeness of its upstream sources:

- `parse_rss()` emits up to the configured entry cap and gives all entries in one poll the same poll-time timestamp. It does not perform cross-poll deduplication or add a separate source-item identifier. The current source therefore permits repeated feed items to be inserted on later polls; whether duplicates actually accumulate in the target database is UNKNOWN.
- `ExchangePrices.poll()` handles Binance, Coinbase and Kraken independently, swallowing each source's request/parse exception and returning whatever exchange groups succeeded. `CryptoNews.poll()` similarly swallows each RSS-source exception and returns whatever entries were collected. Scheduler `last_error` cannot expose those swallowed per-source failures; its event count is only the count of returned/persisted events. `ArxivAI.poll()`, in contrast, propagates fetch/parse exceptions to the scheduler. No live source outage or partial poll was observed.
- Fountain's ordinary recent-sense block reads up to six times the requested number of latest non-internal rows, filters configured noise streams, extracts a title/summary, and selects at most one row per stream. It does not impose an explicit age cutoff. Its optional OVERWHELM block reads the latest N external rows when `NEX5_SENSE_OVERWHELM_N > 0`; its optional SELF block reads the latest N internal rows when `NEX5_SELF_LAYER_N > 0`. Both environment-derived defaults are zero in the inspected constructor, but target-host values are UNKNOWN.
- Fountain also has a separate optional SOCIAL block reading `external.other_mind` rows when `NEX5_SOCIAL_N > 0`. That stream is not among the 28 Stage 1 factory adapters; its producer path remains outside this audit slice. The Fountain source comments describe SOCIAL as a separate interlocutor, but this inspection does not establish deployed activation or provenance.
- The quiescent/latest-row path and optional OVERWHELM/SELF/SOCIAL blocks are distinct prompt-construction paths. Their existence must not be collapsed into a claim that every sense row is always included in every Fountain prompt.

Test boundary: `tests/test_sense_extract.py` verifies extraction of title-like fields, JSON/no-title handling, noise-stream classification, and isolated distillation helpers. It does not exercise real adapter partial-source failures, repeated RSS poll ingestion, stale-row behaviour, or the live Fountain prompt under target-host flag settings. No tests were run in this pass.

Source anchors at inspected PR #49 evidence head `23e327e84b6b26b6e22eb27808514100c2802855`: `theory_x/stage1_sense/feeds/_helpers.py`, `feeds/exchange_prices.py`, `feeds/crypto_news.py`, `feeds/arxiv_ai.py`, `theory_x/stage6_fountain/generator.py` and `tests/test_sense_extract.py`. The later Stage 2 source audit already recorded in this report identifies separate all-stream attention and filtered/capped sense-distillation consumers; the Stage 1-to-Fountain paths documented here are additional, not an exhaustive inventory of all `sense_events` readers.

Evidence remains source-level. No target-host environment, external-feed health, sense.db contents, duplicate rate, prompt inclusion frequency or row-level causal effect was observed. No runtime, schema, test, flag, host, experiment, merge or deployment change was made.


### Stage 2 test review qualification — 24 Nov 2026

The bounded tests inspected (`tests/test_dynamic.py`, `tests/test_sense.py`) establish successful pipeline/cursor basics and successful adapter submission. They do not exercise swallowed `run_pipeline()` errors with subsequent cursor movement, replay boundaries, partial pipeline side effects, or the five-write distillation cap. The internal-stream test asserts only a non-negative hit count and does not verify absence of tree/membrane influence. The inspected adapter tests do not inject a Writer failure into the concrete Adapter.submit() path. This is a bounded test-coverage observation; it is not a repository-wide claim that no related tests exist.


### Cross-stage consequence of repeated Stage 1 feed rows — 24 Nov 2026

The RSS ingestion findings were traced one step further into Stage 2:

- The inspected RSS helper/adapter path does not deduplicate feed items across polls, and the sense table has no unique source-item key. Repeated feed entries can therefore be persisted as separate rows; this remains a source-level possibility, not a measured target-host duplicate rate.
- Stage 2's general `_sense_poll_loop` consumes every new row by database ID, including internal and repeated external rows, and invokes the A–F pipeline once per row. The inspected pipeline has no content-level idempotency check; if a repeated row matches branches, it can be processed again. Actual duplicate frequency and downstream state impact are UNKNOWN.
- Stage 2's separate sense-distillation loop does apply exact/near-duplicate belief checks and excludes internal and `external.other_mind` streams. That protects this belief-promotion path only; it does not deduplicate the general A–F pipeline.
- The A–F pipeline catches exceptions internally, records an error and returns zero. Its caller advances the in-memory row cursor after the call returns, so a caught pipeline failure is not distinguished from a no-match/zero-hit result by the caller. This is a source-level accounting boundary; no failure was injected and no row loss is claimed.

Source anchors at inspected PR #49 branch head `5dc5f8b13e18a716901a5b0296a50c7463156ebe`: `theory_x/stage1_sense/feeds/_helpers.py`, `feeds/arxiv_ai.py`, `substrate/schema/sense.sql`, `theory_x/stage2_dynamic/__init__.py` and `theory_x/stage2_dynamic/pipeline.py`. These findings supplement, rather than replace, the prior Stage 2 loop audit.

Evidence remains source-level. No duplicate count, live tree/membrane mutation, target-host cursor state, or failure/restart outcome was measured. No runtime, schema, test, flag, host, experiment, merge or deployment change was made.


### Stage 2 cadence, consolidation and crystallization readers — 24 Nov 2026

Further backward inspection identified additional source paths:

- `BonsaiTree.refresh_cadence()` reads non-internal sense rows from a 24-hour window, groups by stream, burst-clusters timestamps, derives median inter-burst gaps and maps recognised streams to branches. The minimum mapped interval is cached and later scales branch decay. This means stream frequency is a separate influence channel from an individual row's A–F magnitude/Step-F attention result.
- `consolidation._external_quiet()` expects `seconds_since_last_user_message` in the latest `internal.temporal` payload and runs an extra decay/prune pass only when the value exceeds 300 seconds. The built-in `Temporal.poll()` implementation inspected in the Stage 1 factory emits clock fields but not this key. The inspected consolidation tests manually seed the expected key instead of using the real adapter. Another writer could theoretically supply it; a complete repository-wide writer census was not established. Record this as a source-level producer/consumer contract discrepancy with live impact UNKNOWN, not as proof consolidation never runs.
- The Stage 2 Crystallizer reads `pipeline_events` (dynamic.db), selecting high-magnitude recent branch events and carrying stream provenance into a precipitated belief when the chosen metadata contains a sensed title. This is downstream of the A–F pipeline log rather than a direct sense.db read.

No live cadence cache, temporal payload, consolidation run, crystallized belief or target-host effect was inspected.


### RSS parser identity and malformed-feed qualification — 24 Nov 2026

A closer read of `feeds/_helpers.py::parse_rss()` adds two qualifications to the feed audit:

- The helper does not inspect Feedparser's `bozo` / parse-warning status before accepting `feed.entries`. A malformed or partially parsed response may still yield entries and be treated as an ordinary poll result; no malformed response was supplied or observed in this audit.
- The stored payload contains title, link, summary, published, authors and tags, but omits the RSS/Atom entry's stable `id`/`guid` field. The table therefore receives no dedicated item identity from this helper. Title/link may help downstream matching, but they are not guaranteed unique or stable identifiers.
- Together with the absence of cross-poll deduplication and a unique source-item key in the inspected schema, this means the current source path cannot itself distinguish a repeated item from a newly observed item with the same content. This is a structural limitation, not a measured duplicate-ingestion incident.

Source anchor: `theory_x/stage1_sense/feeds/_helpers.py` at PR #49 source revision `23e327e84b6b26b6e22eb27808514100c2802855`. No malformed-feed test or live feed response was run. No runtime or test behaviour changed.


### Stage 1 scheduler shutdown and Writer-close ordering — 24 Nov 2026

A bounded lifecycle trace from the Stage 1 adapter threads through application shutdown found a possible in-flight write race:

- `_AdapterThread` starts a daemon thread but does not retain the `threading.Thread` handle on the object. Its `stop()` method only sets a stop event; it does not join or otherwise wait for the worker to exit.
- If shutdown begins while an adapter is inside `poll()`, the worker continues through `submit(events)` and updates status before its next loop condition observes the stop event. The stop event shortens the subsequent wait but does not cancel or synchronously drain the in-flight poll/submit.
- `SenseScheduler.shutdown()` calls `stop()` for each adapter thread and returns without joining them.
- `AppState.close()` calls `scheduler.shutdown()` and then immediately calls `close()` on each Writer. `Writer.close()` enqueues its sentinel and joins its worker with a timeout. A Stage 1 adapter that reaches `Writer.write()` after the Writer sentinel has been enqueued could enqueue behind the sentinel, after the Writer worker has exited; its synchronous future wait may then remain unresolved. The exact interleaving depends on shutdown timing and Writer queue state.
- This is a source-confirmed race possibility, not an observed shutdown failure. No thread interleaving was induced, no shutdown test was run, and no target-host impact is claimed.

Source anchors at current PR #49 source head: `theory_x/stage1_sense/scheduler.py` (`_AdapterThread.__init__`, `_run`, `stop`, `SenseScheduler.shutdown`); `gui/server.py` (`AppState.close`); and `substrate/writer.py` (`Writer.close`, synchronous `write`, worker sentinel handling). This lifecycle edge belongs in the Stage 1 forward dependency/termination map and remains an open Phase 0 defect/risk candidate pending authoritative acceptance criteria. No remediation is authorised by this finding.

No runtime, test, schema, flag, host, experiment, merge or deployment change was made.


### Stage 2 → Stage 3 pipeline-hook influence path — 24 Nov 2026

The WorldModel factory constructs `PipelineHooks` and registers the live `DynamicState`, which injects `on_pipeline_event` as the optional callback used by Stage 2 `run_pipeline()`. The callback is reached only after Step F has at least one qualifying branch hit; Stage 2 invokes it for each valenced branch with magnitude at least 0.001. The hook itself ignores magnitudes below 0.6, then tokenises `sensation_source` (the provenance string when present, otherwise the stream name) together with the branch id. It reads up to the 50 newest beliefs with tier <= 7 that are unpaused and unlocked, and calls the promoter's corroboration path when overlap divided by the hook query-token count is at least 0.7. With `NEX5_TIER_CLIMB=1`, it additionally considers up to 500 T6 beliefs.

This means the inspected cross-stage feedback is not a direct semantic comparison between the full sensed payload and belief content: the hook's comparison input is provenance/stream plus branch identity. It is also conditional on a Step-F hit and a high enough magnitude. Internal streams do not reach Step F in the inspected mapper because their magnitude is forced to zero. The hook is a real source-level connection from Stage 2 attention to Stage 3 belief corroboration, but no live invocation or specific belief promotion is established.

The inspected `tests/test_world_model.py` covers the promoter's corroboration threshold and stage labels; the reviewed test slice does not exercise the full DynamicState → Step-F → PipelineHooks integration or verify which source tokens drive corroboration.


### Stage 2/3 startup ordering qualification — 24 Nov 2026

A source-level startup ordering window exists around the pipeline hook. `build_dynamic()` starts its daemon loops, including `_sense_poll_loop()`, before returning. In `run.py`, `build_dynamic()` is called before VoiceClient construction/health check and before `build_world_model()`. The WorldModel factory creates `PipelineHooks` and only then calls `hooks.register(dynamic_state)`, which sets `dynamic_state._pipeline_hook`. The Stage 2 poller uses `getattr(state, "_pipeline_hook", None)` each batch, so rows processed before registration have no Stage 3 corroboration callback. This is a possible startup race/window, not evidence that a qualifying external row was actually processed in that interval; internal rows are magnitude-zero in the inspected mapper. No synchronization or startup barrier was identified in these inspected paths.


### Stage 1 scheduler test-coverage reconciliation — 24 Nov 2026

The existing `tests/test_sense.py` suite explicitly asserts that external adapters are running/enabled immediately after scheduler construction (`test_starts_running_for_external`), matching the constructor's auto-start call and dated inline comment. This makes the paused-by-default package/scheduler docstrings a stale documentation discrepancy; the inspected test suite encodes the auto-start behaviour. The same test file's teardown calls `scheduler.shutdown()`, and its direct `_AdapterThread` test calls `stop()`, but neither asserts that worker threads have terminated before Writers are closed. Thus the shutdown/join risk remains untested by the inspected cases; this is not a claim that the auto-start behaviour itself is untested.


### Additional sense_events consumers: WorldBridge and probe/strike context snapshots — 24 Nov 2026

A wider backward search from the Stage 1 sense table identified two additional consumer families beyond the previously mapped Stage 2 loops, SelfModel and Fountain's direct sampling helpers:

- `run.py` constructs `WorldBridgeSelector` with the sense DB path and passes it into `build_fountain()`. The active Fountain prompt builder calls `select_and_log(mark_injected=True)`; when selections are returned, it appends their formatted text under “What's happening in the world right now”. This is an actual source-level prompt-injection path, not merely a selection log.
- The selector's own module/class docstrings still describe “Phase A: select + log only, no prompt modification” and “Phase B (future): inject”. That prose is stale relative to the inspected caller. The selector is enabled by a module constant, identifies streams with events inside cadence-scaled freshness windows, excludes crypto/market noise and selected internal noise, includes the four qualitative internal streams as eligible candidates, selects at most five streams (with at most two internal), takes the latest row per selected stream, formats within a character budget, applies process-local fingerprint deduplication, and logs the result. The generator passes `mark_injected=True` and then actually appends returned items to its prompt.
- This qualifies the earlier narrower observation that Fountain's quiescent and recent-sample readers exclude `internal.%`: those particular SQL paths do, but WorldBridge's distinct prompt path can include `internal.temporal`, `internal.meta_awareness`, `internal.proprioception` and `internal.interoception` when the selector's freshness/selection conditions admit them. The optional SELF layer is another distinct path.
- `theory_x/probes/context_snapshot.py` reads `sense_events` for a grouped `feed_activity` summary over a configurable time window (default 600 seconds), storing stream counts and latest timestamps. `ProbeRunner.run_probe()` captures this snapshot before sending a probe and persists the fields into `probe_context`. `StrikeProtocol._capture_snapshot()` uses the same function and stores the JSON snapshot in the strike record. These are measurement/context-capture consumers, not evidence that the snapshot itself is fed into the Chat or Fountain cognition prompt.
- The inspected `tests/test_strikes.py` verifies that a wired sense Reader produces the required `feed_activity` snapshot key and that failures can be represented. That test does not exercise WorldBridge's selector-to-Fountain-prompt integration. No claim is made that a dedicated WorldBridge integration test is absent globally; the test search was bounded to the paths inspected here.

Source anchors at PR #49 source revision `e0ab228728094eacc22e3e51f10d5174523c6e18`: `run.py`; `theory_x/world_bridge/selector.py` (active stream selection, cadence/freshness, qualitative internal eligibility and formatting); `theory_x/stage6_fountain/generator.py` (selector invocation and prompt append around lines 4085–4105); `theory_x/probes/context_snapshot.py`; `theory_x/probes/probe_runner.py`; `strikes/protocols.py`; and `tests/test_strikes.py`.

This closes another bounded consumer slice but does not establish target-host activation, which exact rows were selected, whether the resulting text changed a model response, or complete global reader closure. No runtime, test, schema, flag, host, experiment, merge or deployment change was made.


### WorldBridge internal-payload reliance qualification — 24 Nov 2026

The selector formatter confirms that eligible internal rows are not merely counted or logged before prompt assembly:

- `internal.temporal` is reduced to its local ISO timestamp.
- `internal.meta_awareness` is reduced to adapter count plus a running/idle label derived from `sense_adapter_count` and `sense_global_running`. Those source fields ultimately reflect scheduler/control-state telemetry, not verified feed health or successful persistence; WorldBridge can therefore present that narrower control-state signal in Fountain's prompt.
- `internal.interoception` is reduced to total/locked belief counts, dominant tier and non-zero delta.
- `internal.proprioception` has no dedicated formatter branch in the inspected selector. It falls through generic JSON handling; absent title/body/url fields, the payload's first 80 characters can be used as the prompt snippet.
- Consequently, the earlier Stage 4 SelfModel finding that its fetched MetaAwareness payload is not used in the returned SelfModel snapshot must not be generalized to “MetaAwareness is unused”: WorldBridge is a separate, conditional prompt consumer of that stream. Eligibility remains dependent on recent-row freshness, selection cap and formatting.

Source anchor: `theory_x/world_bridge/selector.py` at source revision `e0ab228728094eacc22e3e51f10d5174523c6e18`, `QUALITATIVE_INTERNAL_STREAMS`, `_pick_events()` and `_parse_payload()`. No target-host prompt or selected row was observed.


### Consolidated Stage 1 sense-table consumer index — 24 Nov 2026

The following index consolidates the source paths identified so far. It is a navigational synthesis of inspected paths, **not** a claim that every repository reader has been found.

| Consumer | Input scope | What the code does | Evidence boundary |
|---|---|---|---|
| Stage 2 sense poll loop → A–F pipeline | Every new row by id, including internal and external | Runs branch matching, magnitude/aperture, valence, tree attention, membrane accumulation and pipeline logging | Source path; row-level live effects and retry outcomes UNKNOWN |
| Stage 2 sense distillation loop | Non-internal rows except external.other_mind | Extracts titles; exact/near-duplicate checks; up to five new belief writes per pass; cursor advances across fetched batch | Separate belief-promotion path; does not make A–F processing idempotent |
| Stage 2 BonsaiTree cadence refresh | Previous 24 hours of non-internal rows | Derives per-stream burst/cadence measures that feed branch decay timing | Frequency influence can occur without a Step-F hit; target-host cadence values UNKNOWN |
| Stage 2 consolidation quiet check | Latest internal.temporal row | Looks for seconds_since_last_user_message to trigger extra quiet-period decay/pruning | Inspected Temporal factory producer does not emit that key; another writer/live payload not ruled out |
| Stage 4 SelfModel snapshot | Latest rows for four internal streams | Uses Proprioception, Temporal and Interoception fields; fetches but does not use MetaAwareness payload in that snapshot | Retrieval is not equivalent to reliance |
| Stage 6 Fountain direct sampling | Latest non-internal row, recent distinct-stream sample, optional OVERWHELM and SELF lanes, optional external.other_mind SOCIAL lane | Several separate prompt-context paths with different filters and default-off flags | Target-host flags and exact included rows UNKNOWN |
| WorldBridge selector called by Fountain | Fresh external plus eligible qualitative internal streams | Selects/formats up to five rows (at most two internal) and returned text is appended to the Fountain prompt | Actual source-level prompt contributor; host activation and model reliance UNKNOWN |
| ProbeRunner / StrikeProtocol context snapshot | Grouped feed_activity within configurable window | Captures stream counts/latest timestamps into probe/strike records | Observational record, not direct Chat/Fountain prompt input |

The index reconciles several apparent contradictions: “Fountain excludes internal streams” is true only for its specific non-internal SQL readers, not for WorldBridge or the optional SELF layer; “MetaAwareness is unused” is true only of the inspected SelfModel snapshot mapping, not of WorldBridge's conditional prompt formatting; and Stage 2 attention, belief distillation and cadence derivation are separate consumers with different inclusion and persistence rules.

Remaining closure work: verify the complete repository-wide reader/writer census (including dynamic imports, direct SQLite connections, helpers and non-obvious table aliases), reconcile every faculty edge against the governing architecture documents, and distinguish source presence from target-host activation and causal influence. The current map remains bounded and provisional.


### WorldBridge write-path / One-Pen Rule reconciliation — 24 Nov 2026

A further check against the repository's governing technical specification found a concrete storage-boundary discrepancy:

- SPECIFICATION.md §8 states that each database has exactly one writer thread, all writes submit to the single writer queue, and no code acquires a write lock directly. Its “non-negotiable” rules section further states that every write goes through the queue and direct DB writes are bugs.
- WorldBridgeSelector imports substrate.connect and uses a fresh ordinary connection to the beliefs database inside _log_selection(), executing an INSERT into world_bridge_log directly. It is not passed the beliefs Writer. This is not a read-only connection and does not route the insert through the Writer queue.
- The boot path constructs WorldBridgeSelector and passes it into Fountain; Fountain invokes select_and_log() in prompt construction. Therefore the direct-write method is reachable on the inspected source path, subject to the selector and Fountain path executing.
- The existing test_sense.py one-pen ratchet searches for the literal “import sqlite3” outside substrate. A module using “from substrate import connect” and issuing INSERT is outside the coverage of that specific grep assertion; this observation does not establish that no other guard or test covers it.
- This is source-confirmed divergence from the inspected SPECIFICATION.md contract. Whether there is a later approved exception or superseding authority has not been established. No contention event or live impact is claimed, and no remediation is authorised by this audit.

Source anchors at current PR #49 source revision: SPECIFICATION.md §8 and the non-negotiable rules; theory_x/world_bridge/selector.py (_log_selection); run.py (selector construction); theory_x/stage6_fountain/generator.py (selector call and prompt assembly); tests/test_sense.py (literal import scan). This should be reconciled with the Frozen V2.1 authority before any implementation change.


### Stage 3 retrieval and Harmonizer coverage audit — 24 Nov 2026

The inspected production chat path calls Stage 3 retrieval through Stage 4 QueryRouter when membrane and WorldModel are both present. INSIDE queries combine a self-model snapshot with up to five INSIDE-filtered beliefs; OUTSIDE queries retrieve up to eight using active Dynamic branch hints. The no-membrane fallback instead retrieves up to three and applies a chat-only two-token overlap filter and ~800-character cap. The retrieved belief block is used in prompt assembly.

The retrieval implementation's spreading activation does not add graph-only neighbours to the returned candidates: after activation scores are computed, result assembly drops any activated ID absent from the original keyword-scored `row_map`. Graph activation therefore adjusts/reranks the keyword-matched candidate set in this implementation, rather than expanding it with zero-overlap neighbours. Edge traversal stamps are best-effort. FocalSet/Working Memory is a separate attention-tracking path; the inspected code updates its buffer and logs it but does not append that buffer to the prompt at that point. A separate dashboard activation calculation is likewise not evidence of response influence.

The Harmonizer's initial conflict scan selects only 200 eligible beliefs ordered by ascending tier. Its own source comment reports a historically measured pool exceeding 3,700, with more than 600 Tier 3 beliefs and no Tiers 5–7 reached by that scan. The optional paradox-fix pass directly rechecks already-open paradox pairs to escalate them after incubation; it does not repair initial discovery coverage for beliefs excluded from the 200-row selection. Current target-host population and whether the flag is armed are UNKNOWN.

No live query, retrieved belief set, graph traversal, focal buffer, Harmonizer scan, or current beliefs.db population was observed. All findings above are source-level path semantics, with historical measurements identified as such.


### Stage 3 test-boundary review — 24 Nov 2026

The reviewed `tests/test_world_model.py` covers small-population keyword retrieval, basic activation-adjacent retrieval, promotion/decay and a two-belief Harmonizer conflict example. It does not test graph-connected zero-keyword-overlap beliefs being returned, the 200-row/tier-order starvation boundary, or the distinction between initial conflict discovery and the optional direct escalation pass. The chat injection test only asserts that a request does not crash and that the system prompt contains the generic NEX marker; it does not assert the exact routed belief set, INSIDE/OUTSIDE policy, or provenance of the injected belief block. These are bounded observations about the inspected test file, not repository-wide absence claims.


### WorldBridge test-tree spot check — 24 Nov 2026

The recursive tracked-tree inventory at PR #49 source head 90b4ee4cd4dbee06abfdb54fc8f8111264259831 contains no dedicated tests/test_world_bridge*.py module. The inspected tests/test_fountain.py does not reference WorldBridgeSelector, select_and_log or world_bridge_log. By contrast, tests/test_probe_snapshot.py explicitly tests feed_activity grouping by stream and snapshot-window behavior. This narrows the test evidence: the probe/strike snapshot consumer has direct fixture coverage, while the selector-to-Fountain prompt and direct beliefs.db logging paths were not covered by the specific test modules inspected. This is not a claim that no assertion about WorldBridge exists anywhere in the entire suite.


### Stage 4 SelfModel payload-use audit — 24 Nov 2026

The SelfModel reads the latest rows for four Stage 1 streams using four independent `SELECT ... ORDER BY id DESC LIMIT 1` operations. It does not use one shared read snapshot, so the assembled self-state can combine different event times. This is a source-level consistency limitation, not a measured stale-data incident.

The payload-use distinction is narrower than the snapshot field names suggest:

- Proprioception payload fields populate CPU, memory, load and a selected thermal value. The prompt formatter surfaces CPU, memory and load, but not thermal.
- Temporal contributes hour, weekday and local ISO time to the snapshot; the formatter surfaces local time/period, but not weekday.
- Interoception contributes total belief count, tier distribution and locked count; the formatter surfaces total and locked counts, but not the tier distribution.
- The latest `internal.meta_awareness` payload is fetched into `meta_p` but never read. The snapshot's `meta_awareness` fields are instead populated from `DynamicState.status()`. Those fields are returned in the snapshot object but `format_self_state()` does not render them into the INSIDE prompt block.
- The inside-belief query selects at most 30 candidates from an explicit source allowlist, then scores by confidence × tier weight and returns five; the prompt formatter renders at most the first three.

Thus “read”, “mapped into snapshot”, and “surfaced to the model” are separate stages. The inspected router calls `self_model.snapshot()` directly for each INSIDE route; the 30-second cache belongs to `tick()`/state reporting and is not used by that direct route call. No live snapshot contents or prompt payload were captured.


### Stage 4 BehaviouralSelfModel evidence qualification — 24 Nov 2026

The BehaviouralSelfModel's `belief_usage_rate` is calculated by scanning the last 100 stored role=`nex` message contents for `her current beliefs` or `[tier`. The GUI persists the sanitized generated assistant reply as role `nex`, while the retrieved belief block is assembled into the system prompt before generation and separately captured in `_retrieved_belief_text`. The metric therefore measures whether the reply text echoes prompt-marker strings, not whether beliefs were actually injected into that turn's prompt. It is an unreliable proxy for prompt-injection frequency; the direction and magnitude of any live measurement error are unknown.

That metric is compared against a seeded expectation and can generate a Tier 6 `behavioural_observation` belief via the membrane's four-hour loop. The resulting belief is a downstream artefact of the proxy metric. No live message sample, observed metric value, or resulting belief was inspected.


### Stage 4 test-coverage boundary — 24 Nov 2026

The inspected `tests/test_behavioural.py` seeds role=`nex` message text directly and checks hedge metrics / that belief-writing does not raise; it does not compare `belief_usage_rate` against the actual per-turn system prompt or `_retrieved_belief_text`. The reviewed `tests/test_self_model.py` and `tests/test_membrane.py` verify snapshot keys, caching, basic sensor payload mapping and route outputs, but do not assert which snapshot fields survive `format_self_state()` into the model prompt, nor that the fetched MetaAwareness payload is unused. These are bounded gaps in the inspected test files, not claims that no other test covers adjacent behaviour.


### Stage 5 → Stage 6 identity-continuity path — 24 Nov 2026

Stage 5 is a boot-time commitment write in the inspected runtime, not a continuously running self-location process. `run.py` calls `SelfLocationCommitment.commit()` after database initialisation and Writer/Reader construction, before Kokoro preload and before later worker/faculty startup. The method writes one locked Tier 1 belief (confidence 0.98, branch `systems`, source `self_location`) with the fixed “I am inside / vantage point” content. The beliefs schema's partial unique index on locked Tier 1 content makes the fixed-content `INSERT OR IGNORE` idempotent against concurrent identical inserts; the method then reads back the source-qualified row. The isolated self-location tests cover the write, repeated-call idempotency and resistance to decisive contradiction. This establishes the intended boot call in source and tests, not that the target host has executed it.

Stage 6's separate `NEX5_IDENTITY_BLOCK` is default-OFF. The generator checks the environment flag directly while building the Fountain prompt; the module's `enabled()` helper is not the call-site gate. When enabled, the block selects one floor claim on every eligible fire: a random authored `identity` claim if present, otherwise a `self_location` claim. It can append up to two further self-model claims with affinity >= 0.40 (configurable), and records each selected belief in the Fountain retrieval manifest. Thus the boot commitment supplies a fallback floor; it does not mean the standing identity block is active by default. The dedicated tests exercise flag-off absence, flag-on floor presence, affinity-controlled extras, self-location fallback and a normal/treatment-arm ablation case.

A treatment-isolation uncertainty remains: `identity_block._ablation_defers()` catches any import or condition-read exception and returns False, which permits the identity block rather than suppressing it. The reviewed tests cover a readable treatment configuration, not a missing/unreadable experiment module or condition lookup failure. Whether fail-open is acceptable must be resolved against the experiment protocol; no treatment state or host flag was inspected. This is recorded as a failure-mode/acceptance question, not a prescribed code change.

The Stage 6 readiness evaluator is a separate gate from identity continuity. The loop is started by `build_fountain()`; each check evaluates Dynamic branch focus/consolidation, total belief count and elapsed time, with optional genius-rate modulation when a conversations Reader is supplied. The generator independently checks readiness >= 0.7 before composing. Mode-level Fountain suppression is checked in the loop. Neither a committed Stage 5 belief nor an assembled identity prompt block alone establishes a Fountain fire or spoken output.
