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
