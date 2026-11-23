# NEX v5.0 — Verified Defect and Risk Backlog

**Status:** Working Phase 0 evidence backlog — NOT founder-approved  
**Date:** 24 November 2026  
**Repository:** `kron777/Nex_v5.0`  
**Documentation branch:** `phase0/evidence-foundation-draft`  
**PR #49 head at creation:** `ae1b3c8227f11915803fa1a49ca42680748781c1`  
**Source branch used for the newest source audits:** PR #65 head `cffbbc94b5a494247d127abf2720886a08f7a567`  
**Authority:** Founder Sign-Off > Frozen V2.1 Spec > Runtime Truth > Master Roadmap v3.0

This backlog consolidates source-verified findings recorded in `NEX_REPOSITORY_REALITY_REPORT.md`. It is a triage aid for Gate 0 review, not approval to implement fixes. “Source-confirmed” means the described code path is visible in the inspected revision; it does not establish that the path has occurred on the target host. Conditional risks remain conditional. No live exploit, database mutation, flag change, external action or host experiment was performed.

## Evidence-level rules

The roadmap §1.2 defines:
- **L0 — Proposed:** design/hypothesis only; no code proof.
- **L1 — Constructed:** code, schema and unit tests exist; no proof of integrated runtime execution.
- **L2 — Runtime-active:** execution traces prove the code runs in live/simulated operation and emits records.
- **L3 — Operationally consumed:** an end-to-end ID-linked trace proves a downstream decision/context/actuator consumes and changes state based on the output.
- **L4 — Effectively validated:** controlled A/B or multi-arm testing against a frozen baseline demonstrates statistically significant improvement on predeclared metrics without guardrail violations.
- **L5 — Generalised:** independent validation across task families, backends or embodiments.

Roadmap §6.2 asks for L0–L4 labels, while §1.2 defines L0–L5. This internal range conflict is preserved for Founder clarification; this backlog uses no L5 claims. The majority of findings below are L1 source/test evidence only. No finding establishes L3 or L4 behavioural improvement. The fixture trace artifact is L2 simulated evidence for the trace overlay, not a live host trace.

## Priority triage — for Founder review only

Priority labels are proposed ordering by potential impact and exposure, not an approved project severity taxonomy.

### P0 — Security boundary

| ID | Finding | Evidence level | Status / exposure boundary |
|---|---|---:|---|
| DRAFT-015 | Public `/api/chat` can route raw prompt text to `python_exec`; regex import blocking is bypassable through Python built-ins, and the subprocess executes under the NEX process account. The route is exempt from the admin mutation gate. | L1 | Source-confirmed unsandboxed execution path. Default bind is loopback; unauthenticated arbitrary code execution is conditional on a caller being able to reach the service. No exploit was run. |
| DRAFT-016 | `web_fetch` uses `netloc.lstrip("www.")` rather than exact-prefix normalization and follows redirects without revalidating the final destination. | L1 | Source-confirmed allowlist/redirect weakness; SSRF is conditional on a controllable lookalike or permitted-origin redirect. No network request was made. |

**Containment recommendation:** do not expose the service beyond a trusted local boundary until the Python tool is disabled or safely isolated and the web-fetch destination policy is independently verified. This recommendation does not authorize a runtime change.

### P1 — Decision influence, authority and trigger integrity

| ID | Finding | Evidence level | Status / exposure boundary |
|---|---|---:|---|
| DRAFT-008 | WorldBridge documentation describes Phase A as selection/logging only, while the inspected runtime constructs the selector and appends selected event text to Fountain prompts; selector is source-enabled and does not consult the registered bridge flag. | L1 | Source-confirmed documentation/implementation mismatch. Approval intent and live selection frequency UNKNOWN. |
| DRAFT-011 | Empty prediction windows are deliberately stored with surprise score 1.0 and no actual content; the expectations ledger and SurpriseLoop reject them as evidence, but Fountain confidence weighting uses the score alone and can apply the maximum confidence boost. | L1 | Source-confirmed consumer semantic mismatch; weighting is source-default enabled. Host flag and occurrence UNKNOWN. |
| DRAFT-017 | Throw-Net threshold functions return threshold booleans, but CoherenceGate and Chat callers ignore them; the monitor processes every unfired trigger when enabled. | L1 | Source-confirmed threshold-wiring mismatch. Throw-Net monitor is default-OFF; live activation UNKNOWN. |
| DRAFT-020 | FocalSet is described as log-only but its selected beliefs are added to per-session WorkingMemory and injected into the same Chat turn's prompt on a conditional path. FocalSet state is process-global and unsynchronized. | L1 | Source-confirmed prompt influence and cross-session selection coupling; no arbitrary cross-session text leakage was demonstrated. |
| DRAFT-006 | Moltbook dry-run return values can be recorded as approved/posted/sent even when no external POST occurs; a supplied host log shows a loop instantiated in a potentially divergent checkout. | L2 for loop instantiation only | External action and current checkout identity UNKNOWN. Host log is historical; Manus must reconcile checkout identities before activation claims or code correction. |

### P2 — Reliability, measurement and recovery

| ID | Finding | Evidence level | Status / exposure boundary |
|---|---|---:|---|
| DRAFT-009 | Voice and random market predictions fetch separate baselines/timestamps; a failed leg can return a non-error wrapper result with a missing row ID. | L1 | Source-confirmed paired-experiment/accounting gap; live drift and partial-pair frequency UNKNOWN. |
| DRAFT-010 | Calibration consult can label unavailable scorecard data as “none”/unreliable rather than “unknown”; the level is stamped onto a prediction row. | L1 | Source-confirmed evidence-state misclassification; specific failure branch lacks a dedicated test. |
| DRAFT-012 | An accepted provenance retry is evaluated with logging disabled, so the provenance file records the discarded initial draft rather than the final delivered response. | L1 | Source-confirmed measurement gap; conditional on an armed feature and accepted retry. |
| DRAFT-013 | CounterfactualNode repeatedly selects the oldest open problem but does not update its `last_touched_at`; absent external touches/closure, newer problems can be starved. | L1 | Conditional scheduling starvation path; no live incidence. |
| DRAFT-014 | External-input prediction concatenates sense rows before chat messages and truncates to 10 without cross-source chronology; verification includes internal sense streams excluded from prediction. | L1 | Source-confirmed prediction/verification population mismatch; score impact UNKNOWN. |
| DRAFT-018 | An outer Throw-Net cycle failure persists a failed session but returns status complete and marks the trigger fired, preventing pending-query retry. | L1 | Source-confirmed result/retry accounting mismatch; intended consume-on-failure policy unresolved. |
| DRAFT-021 | run.py replaces SnapshotWriter's SIGTERM handler and calls `os._exit`, bypassing the writer's final snapshot and atexit callback. | L1 | Source-confirmed shutdown integration gap; periodic snapshots still occur. |
| DRAFT-022 | ResumptionSeeder consumes a valid snapshot even when promotion/reissue helpers swallow database errors and return zero/partial counts. | L1 | Source-confirmed recovery retry gap; no direct resumption failure test. |

### P3 — Conditional routing, governance and test coverage

| ID | Finding | Evidence level | Status / exposure boundary |
|---|---|---:|---|
| DRAFT-001 | Speech consumer fallback calls `row.get("voice")` on a `sqlite3.Row`, which has no `.get()`; only reached when normal VoiceState resolution is absent/fails. | L1 | Source-confirmed conditional fallback defect; normal startup supplies VoiceState. |
| DRAFT-002 | Natural-language calculation heuristics select `python_exec`, but the original prose query is passed as Python source and normally fails syntax parsing. | L1 | Source-confirmed integration defect; distinct from the unsandboxed-code security issue in DRAFT-015. |
| DRAFT-003 | Membrane classifier uses substring matching for “you”, so “YouTube” is classified as self-inquiry/INSIDE. | L1 | Source-confirmed conditional query-routing defect; runtime frequency UNKNOWN. |
| DRAFT-005 | MIND_MAP descriptive-only constraint was not enforced by the earlier CI check. PR #72 adds a static guard and focused tests; its exact head passed CI, but remains draft/unmerged. | L1 | Proposed governance correction in PR #72; do not mark resolved until merged and verified on the authoritative branch. |

## Top five documentation-versus-code discrepancies

These five are the most material discrepancies identified in the current source pass; the list is a Phase 0 snapshot, not a final severity ranking.

1. **DRAFT-015 — Python tool safety claim vs actual execution:** the public chat path forwards raw prompt text to a Python subprocess; regex import blocking is not a sandbox.
2. **DRAFT-008 — WorldBridge Phase A description vs actual prompt injection:** documentation says selection/logging only, while the inspected generator appends selected event text to the prompt.
3. **DRAFT-020 — FocalSet “log-only” comment vs actual prompt influence:** same-turn FocalSet selections enter WorkingMemory and can be appended to the current prompt.
4. **DRAFT-017 — Throw-Net thresholds vs actual scheduling:** threshold return values are ignored; all unfired trigger rows are processed when the monitor is enabled.
5. **DRAFT-011 — empty-window sentinel vs downstream confidence semantics:** one consumer treats the sentinel as no evidence while another treats its maximum score as novelty.

DRAFT-016 is an additional security boundary weakness; DRAFT-006 is an external-action state-accounting risk; both remain high-priority review items.

## Current repository and CI state

| Workstream | Exact head | CI | PR state |
|---|---|---|---|
| PR #49 evidence foundation | `ae1b3c8227f11915803fa1a49ca42680748781c1` | Run `45280433678` in progress | Open, draft, unmerged |
| PR #65 trace/speech integration | `cffbbc94b5a494247d127abf2720886a08f7a567` | Run `45273123963` success | Open, draft, unmerged |
| PR #72 MIND_MAP CI guard | `6aa226a80d623f223ef994ca9d2d49d29f7d1966` | Run `45272386599` success | Open, draft, unmerged |

CI success validates only the tested repository suite at that exact head. It does not establish host runtime behaviour, Gate 0 readiness or live causal influence.

## Phase 0 completion status

| Roadmap item | Current evidence | Status |
|---|---|---|
| M0.1 repository baseline | GitHub repository/PR/source revisions inspected; exact host checkout and local working-tree status not captured. | Partial |
| M0.2 host and test baseline | Target Zorin/Python/SQLite/Ollama/Qwen digest, RAM/VRAM and tokens/sec not measured. Full target-host pytest baseline and `known_failures.txt` reconciliation not performed. | Incomplete |
| M0.3 forward/backward crosswalk | Broad source-to-sink coverage across core loops and optional faculties; remaining faculty-by-faculty closure and all backward consumers still need reconciliation against every governing source. | Partial |
| M0.4 evidence labels/top five | Top five listed above; strict evidence levels applied in the Crosswalk and this backlog, subject to the roadmap's L0–L4/L0–L5 wording conflict. | Partial |
| M0.5 causal trace | `NEX_CAUSAL_TRACE_SAMPLE.json` exists in PR #49 as an isolated fixture artifact with one Chat turn and one Fountain cycle. It is not a live host capture. OFF/ON fixture equivalence is tested; complete host capture and full causal closure remain unestablished. | Partial |

## Gate 0 blockers

1. Exact Frozen V2.1 specification and Founder Sign-Off/approval record remain unlocated in the searched Library/repository material.
2. Founder must reconcile the authority hierarchy and the roadmap's L0–L4 versus L0–L5 evidence-level wording.
3. The target runtime checkout identity and current host state must be established. The Moltbook host log references a potentially divergent checkout; Manus must compare both checkout identities and startup paths before any activation claim or code correction.
4. M0.1/M0.2 host measurements and full test-baseline reconciliation remain incomplete.
5. The forward/backward audit must be closed for every `theory_x/` faculty against `MIND_MAP.yaml`, `sentience_dag.json`, `ARCHITECTURE.md`, `SENTIENCE_PROGRAM.md` and `run.py`.
6. A live host Fountain trace and Chat trace have not been captured.
7. Founder review and approval of the Reality Report, Crosswalk and this verified defect/risk backlog are required before behavioural edits.

**No remediation is authorised by this backlog.** No runtime code, tests, database, flags, host, protected experiment, baseline, tripwire, external action, merge or deployment was changed in producing it. All items remain open for evidence review; some may be downgraded, reclassified or closed after higher-authority reconciliation and approved verification.
