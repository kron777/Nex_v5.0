# NEX 5.0 — INDEX / DEVELOPMENT MANUAL

**Last verified against:** `main` at `b5e78842f43ac93c2624697f686da0b600306177`  
**Evidence date:** 28 November 2026  
**Purpose:** first-read guide for development, architecture review and operational investigation.

This is a living orientation document, not a governing specification, roadmap, runtime-state report or proof of cognitive capability. Source code and approved project documents take precedence. When this index conflicts with source, correct this index rather than bending source to fit it.

---

## 1. What NEX is

NEX 5.0 is an experimental, continuously executable cognitive architecture. It coordinates persistent state, sensing, dynamic formation, structured beliefs, attention, self-modelling, memory, metacognition, affect, language-model interaction and external interfaces.

The language model is one component, not the whole system. NEX's longer-term direction includes a reusable, locally operable cognitive layer for robotics. Robotics/cloud deployment, fleet intelligence and production-grade embodied autonomy remain development directions, not capabilities established by this repository snapshot.

NEX does **not** claim to have established consciousness or subjective experience. Implemented functional analogues and observed behaviour do not prove an experiencing subject. Keep claims proportional to evidence.

### Evidence vocabulary

Use these distinctions consistently:

- **Specified:** described in an approved specification or design.
- **Present:** source code or a testable component exists.
- **Boot-wired:** the normal boot path constructs or starts it.
- **Enabled:** its relevant runtime flag/configuration is active in the environment being examined.
- **Consumed:** its output reaches a downstream decision, prompt, retrieval surface, persistence path or user-facing effect.
- **Measured:** a controlled probe or runtime observation demonstrates the claimed effect.
- **Validated:** the effect survives an appropriate falsifier, baseline comparison and regression coverage.

These are not synonyms. A module can be present but dark; boot-wired but disabled by a flag; enabled but not consumed; or consumed without a demonstrated beneficial effect. A unit test of a module alone does not prove end-to-end runtime behaviour.

---

## 2. Authority and development governance

Do not infer project authority from repository convenience or from this index.

- Follow the current user-approved Master Roadmap and its phase gates. The known project position is **Phase 0 / Gate 0 pending founder review**; do not move into Phase 1 without the required explicit approval.
- The consolidated **S-01–S-25 specification/register is frozen**. Do not edit or reinterpret it as part of ordinary documentation maintenance.
- The separate user-authored **NEX v5.0 — DEVELOPMENT PROPOSAL V2.1** is not interchangeable with S-01–S-25. Its exact authoritative original/approval record must be retrieved before relying on its detailed contents.
- Do not substitute the older root `SPECIFICATION.md`, `ARCHITECTURE.md`, `DOCTRINE.md`, a mind map, the DAG, a handover or this index for the governing roadmap or frozen register.
- `mind_map/MIND_MAP.yaml` is explicitly descriptive. It must not gate, score, block or veto runtime action.
- `sentience_dag.json` with `nex_next_dev.py` is a separate development/buildability graph. It is not the Master Roadmap.
- Watcher and the Recursive Development Orchestrator (RDO) are external development/evidence instruments, not NEX runtime faculties. Human authority remains outside consequential project changes.

If an authority document is absent or ambiguous, retrieve it or ask. Do not invent a replacement.

---

## 3. Repository and runtime orientation

### Core entry points

| Path | Role |
|---|---|
| `run.py` | Unified NEX boot sequence and AppState wiring |
| `nex_keepalive.sh` | Single-instance supervisor, restart and standby handling |
| `nex_config.py` | Registry/validation for NEX5 environment flags |
| `substrate/init_db.py` | Six-database schema and migration initialization |
| `substrate/writer.py` | Serialized per-database write queue |
| `gui/server.py` | Flask cockpit and Chat API |
| `theory_x/` | Cognitive faculties, stages and experimental mechanisms |
| `voice/`, `speech/` | Model and speech interfaces |
| `mind_map/MIND_MAP.yaml` | Descriptive source-linked mind map |
| `sentience_dag.json`, `nex_next_dev.py` | Separate development dependency graph/tool |
| `tests/` | Controlled and regression tests |
| `journal/`, `observation_reports/` | Historical investigations and experimental evidence |

### Boot sequence (source-level)

The audited `run.py` sequence initializes the substrate, creates shared Readers/Writers, commits self-location, builds the mode state and sense scheduler, constructs dynamic formation, world model and membrane, then wires supporting faculties, Fountain and the GUI. Speech and numerous additional loops are conditional or separately started.

The six database identities are:

1. `beliefs`
2. `sense`
3. `dynamic`
4. `intel`
5. `conversations`
6. `probes`

Each has its own Reader/Writer path. The 28 sense adapters comprise 4 internal and 24 external adapters in the source inventory. Adapter construction does not prove that every external feed successfully polls, produces observations or influences downstream behaviour.

The Flask cockpit defaults to **127.0.0.1:8765**, configurable through `NEX5_HOST` and `NEX5_PORT`. Do not repeat the historical port-8770 claim. Verify current deployment settings from the host before assuming the listener is available.

### Deployment caution

The repository contains host-specific paths and service assumptions. Do not copy them into another installation without checking the actual checkout, virtual environment, systemd unit, data directory and environment file. A source-level inspection cannot establish which process, flags, services or databases are currently active on the user's machine.

---

## 4. Persistence and data ownership

The one-pen rule is a core persistence invariant: **one canonical Writer per database; all writes to that database go through its Writer**. Readers provide read access. See `substrate/writer.py`, `substrate/reader.py` and `substrate/init_db.py`.

A Writer serializes work for its own database. A transaction callback or multi-statement write can be atomic within that database. It does **not** create an atomic transaction spanning multiple SQLite databases. If one logical operation updates beliefs and conversations, a failure between those commits can leave partial cross-database state. Do not describe cross-database work as globally atomic.

The 27 November mainline includes the merged one-pen migrations for daily-life scheduled activity and canary persistence (#168), affinity (#169), learning-guard subtraction (#180), and Expectations persistence/reconciliation transaction support (#183). Important distinction: the shared-Writer migration does **not** establish that the Expectations reconciler is activated. The tracked launcher sets `NEX5_RECONCILER=1` and `NEX5_EXPECT_LEARN=1`, but the audited `run.py` has no Expectations/reconcile invocation, and `daily_life.py` imports only `record_canaries`; do not infer a live reconciliation loop from those flags. No activation is authorised by this documentation. PR #184 also fixes tied-timestamp pagination for Warrant lineage/arc reads; it does not broaden use-day eligibility or change Warrant policy. The current mainline includes the remaining bounded one-pen migrations: responder (#191), listener/poster (#196), and resumption, identity, Fountain momentum and recursion attribution (#200). #200 passed exact-head full baseline CI (2,539 passed, 7 skipped, 40 subtests) before merge. This closes those identified migration branches, not the repository-wide one-pen audit; every remaining writer path still requires source-to-sink verification.

Do not use direct `sqlite3` writes to live substrate databases as a shortcut. Test fixtures and isolated diagnostic databases are different from production persistence.

---

## 5. Cognitive pathways and integration boundaries

NEX is not a collection of independent modules that all automatically influence one another. Trace each pathway from producer through selection and gates to persistence and downstream consumer.

### Sense and dynamic formation

Sense adapters emit observations into the sense substrate. Stage 2 dynamic formation organises incoming signals, attention and branch/focus state. The source inventory contains many loops, but their successful start, liveness and downstream effect must be checked separately.

### World model and beliefs

The world-model layer retrieves and relates structured beliefs, with source, tier, confidence, provenance, edges and lifecycle state. Belief creation, reinforcement, promotion, pause, demotion, retirement and retrieval are separate operations. Audit eligibility at every consumer; do not assume that a filter in one retrieval path protects all others.

Recent work has identified inactive/paused/retired belief eligibility as a cross-cutting issue across Fountain context, special slots, self-narrative, graph/edge construction, pairing, affinity feedback, reification and other consumers. The G-53 Warrant cursor correction (#184) is merged, but it does not settle eligibility policy. Other corrective PRs must be checked individually for base, merge status and exact-head tests; do not assume branch-only changes affect current `main`.

### Coherence Gate

The Throw-Net trigger path is source-wired but its autonomous monitor is separately gated. `run.py` constructs a shared-Writer `TriggerDetector` and injects it into the Gate; non-Throw-Net REJECTs and Chat gap deflections write trigger rows. The documented 4-REJECT/3-gap thresholds are not enforced by the current consumer: callers ignore the detector's boolean return, `pending_triggers()` selects every unfired row, and `ThrowNetEngine.run_pending()` runs a session for each one. If `NEX5_THROWNET=1` is supplied, even a sub-threshold trigger can therefore launch a session. The monitor is not started unless that flag equals `1`; the tracked keepalive command does not set it, but any parent/systemd environment is unknown. This is a source-level defect and an inactive-by-default path, not evidence of live execution. Do not enable or change its thresholds without the relevant approval.

`theory_x/stage_gate/coherence_gate.py` evaluates ThoughtPackets into ACCEPT, REJECT, HOLD or RESHAPE and records decisions. The current implementation is **fail-open on evaluation exceptions**: an exception is recorded and the packet returns ACCEPT with reason `gate_error_fallback`. This is an availability policy, not a fail-closed safety boundary.

The Gate's documented design intent is universal coverage for generated thoughts, but source review has identified specific producer paths that write beliefs without calling it. These are policy/scope reconciliation findings, not permission to change the Gate or silently classify those paths differently. Read the current source, tests and approved policy before changing coverage.

### Fountain and Chat are different pathways

Fountain is an internally initiated thought/generation path. Chat is an input-driven conversational path through the GUI, membrane/routing, faculty context, voice/tool handling and message persistence. They do not necessarily share the same workspace, retrieval, gates or feature flags.

The Global Workspace implementation in `theory_x/stage_tom/global_workspace.py` arbitrates candidate framing/salience. Its output can lead the focus framing while other contributions remain present; it is not automatically equivalent to selecting or retrieving the body of the thought. Prompt framing, retrieval selection and persistent attention change are different mechanisms.

Check `NEX5_GLOBAL_WORKSPACE`, `NEX5_CHAT_WORKSPACE` and their actual call sites independently. A flag's presence in `nex_config.py` or a launcher is not proof that the corresponding path is active.

---

## 6. Continuity, memory, affect and stakes

The word **continuity** is overloaded. Keep these mechanisms distinct:

1. **Single-subject/process continuity:** single-instance supervision and protection against competing NEX processes.
2. **Cross-restart thought resumption:** `theory_x/memory/resumption.py` promotes real prior beliefs from a recent snapshot for post-boot context; it does not synthesize a new belief or prove uninterrupted subjective experience.
3. **Self-state history:** `theory_x/stage_tom/self_binding.py` composes faculty readings and records a self-state/history.
4. **SelfMindView:** `theory_x/stage_tom/self_mind_view.py` snapshots structured aspects of the system's current mental state; it does not consume the separate self-state history as a continuity mechanism in the audited mainline.
5. **Episodic reconstruction:** `theory_x/memory/episodic.py` is dark by default (`NEX5_EPISODIC=1`), not wired into the normal Fountain/Chat/live loop in the audited source. It can be called manually; its test coverage is not evidence of live episodic operation.
6. **Prompt/content continuity:** `NEX5_CONTINUITY_N` carries prior high-scoring thought content into prompts. This is not same-subject continuity or a no-forked-writer guarantee.

Self-binding is wired into the recursive-self path in Fountain in the audited mainline. The recursive prompt nudge is not evidence of mechanical attention change: the recorded test found P(move | active)=0.333 versus P(move | inactive)=0.337 over n=258. The DAG classifies that particular recursion mechanism as terminal/null; this does not invalidate the separate self-binding/history mechanism.

**Quantitative reading of the recursive-reflection attention probe (reported n=258):** the observed absolute difference is ΔP(move) = 0.333 − 0.337 = −0.004, i.e. −0.4 percentage points. Relative to the inactive-condition rate, this is approximately −1.19%; the observed rate ratio is 0.333 / 0.337 ≈ 0.988. This is a small descriptive difference, not evidence that reflection causes harm or that the conditions are equivalent. The available summary does not provide per-condition sample sizes, raw counts, allocation method, repeated-measures structure or uncertainty intervals, so a confidence interval, significance test and causal estimate cannot be reconstructed from n=258 alone. The result supports the narrower conclusion that this probe did not demonstrate an attention-movement benefit. Follow-up research should recover the original protocol/raw counts and distinguish prompt/self-report changes from measured changes in selection, salience or persistent attention. Do not promote this calculation into a new specification or roadmap gate.

Affect, drives, rāga, readiness, stakes and salience must each be traced to a real behavioural consumer. A scalar that is saturated or only written to a log may be present without materially changing selection. Do not infer a behavioural effect from a prompt label, variable name or module description.

---

## 7. Cost, trace and ledger boundaries

The Cost-and-Trace Ledger (CTL) is an architectural synthesis direction, not one unified live primitive in the audited code. Several separate structures currently carry related but non-identical information, including held tensions, expectations, commitments, undo events, belief warrants, shadow-budget spends, beliefs and episodes.

`theory_x/stage3_world_model/ledger_primitives.py` is explicitly not in the live path and depends on the shadow budget. Its episode consolidation branch is a documented no-op because no existing lossy episodic consolidation function was found.

The M0.5 causal trace overlay is a separate, default-OFF observational sidecar. It records explicit parent-linked events to JSONL, hashes text-bearing content and does not write to substrate databases or participate in decisions. The synthetic Fountain/Chat traces and paired tests are L3 fixture evidence, not live runtime captures. When enabled, synchronous file I/O can affect timing even where tested semantic outputs remain equivalent. Retention/rotation for the sidecar must be checked before any authorised long capture.

---

## 8. Autonomous activity and external effects

NEX contains autonomous and recurring processes in addition to request/response handling. Examples include sensing, Fountain, diversity/edge generation, metacognition, drive/affect updates, prediction, resumption, daily-life routines, speech and optional social integrations.

For every such process, distinguish:
- module exists;
- object is constructed;
- loop is started;
- environment flag permits the activity;
- credentials/network are available;
- external action is dry-run or live;
- action is authorised;
- result is persisted and consumed.

Moltbook components are separate listener, responder and poster pathways. Their persistence migrations have been merged in two steps: responder (#191), then listener/poster (#196). This is a persistence-ownership change, not proof that any Moltbook loop is running or authorised to act. The tracked launcher has been reported with `MOLTBOOK_DRY_RUN=1`, but only host environment and runtime logs can establish actual deployment state. Never infer live posting or interaction from source presence.

Daily-life routines and other autonomous processes require an explicit outbound-side-effect audit before being described as live or safe. Do not activate external actions as part of a source stocktake.

---

## 9. Architecture inventories and status maps

Do not conflate these inventories:

- The 30 entries in `mind_map/MIND_MAP.yaml` are descriptive mind-map nodes; they are not 30 active runtime faculties.
- The `sentience_dag.json` entries are a separate build/dependency graph; they are not the Master Roadmap.
- The 27 stage-named directories and other `theory_x/` packages are filesystem inventory, not proof of instantiated or active faculties.
- Python file counts are repository size, not cognitive capability counts.

The 27 November exact-head verification in PR #185 completed the full baseline (2,527 passed, 7 skipped, 40 subtests) and mind-map verifier: **30 nodes, 0 unverified, 14 dark, 2 blocked**. The earlier 18 source/path-date warnings were cleared by source-anchor corrections. The verifier still reports two absent doctrine references (`VIRTUE_SLATE.md` and `mental_factors_inventory_alobha_spec.txt`) and the overdue `p13_finitude` unblock marker (dated 2026-11-21); these remain explicit and unresolved. The two absent files are not recreated from inference, and the overdue marker is not advanced without source review.

The DAG uses `built`, `live_unproven`, `terminal`, `gap` and `gorge`. `nex_next_dev.py` treats `built`, `live_unproven` and `terminal` prerequisites as satisfied for dependency progression, while surfacing caveats. A terminal/null mechanism is not proof of success; a live_unproven mechanism is not validated.

The DAG contains a status/documentation mismatch worth preserving for review: `L4_teeth` remains labelled `gap` although its note says the retrieval/phrasing frontier was closed on 2026-11-07 and no further work is queued. Verify the intended status with the owner before changing the graph. Do not edit generated mind-map outputs by hand; `MIND_MAP.yaml` is the source for its generated representations.

**DAG consistency snapshot (27 November 2026):** a source-only check of `sentience_dag.json` found 15 nodes and 15 prerequisite edges; status counts were 9 `built`, 2 `terminal`, 2 `gap`, 1 `gorge` and 1 `live_unproven`. All prerequisite references resolved, with no duplicate prerequisite entries or unknown status values. Under the DAG's existing rule, both gap nodes (`L4_stakes` and `L4_teeth`) classify as buildable and both carry a terminal-null caveat through `L3_teeth_test`; no gap node is classified as blocked. The single `live_unproven` node is not a prerequisite of either gap. This is a consistency/inventory result for the descriptive development DAG only, not Master Roadmap progress, proof of implementation efficacy, or authority to change any node status.

---

## 10. Research and evidence practice

Use the source-to-sink method:

1. Identify the producer and the state/event it emits.
2. Follow selection, filtering, arbitration and gate conditions.
3. Identify the database/table and canonical Writer.
4. Follow every consumer and determine whether it can affect output, retrieval, ranking, memory or an external action.
5. Check flags, defaults, boot wiring and host configuration separately.
6. Read tests and determine whether they test a function, an integration boundary or a full production path.
7. Compare against measurements, preregistrations and falsifiers. Look for disconfirming evidence.
8. Record what is verified, inferred, unknown and contradicted.

Prefer controlled experiments and reversible changes. Do not add a new named faculty or duplicate a cognitive twin, genome or event ledger merely because a concept is interesting. First establish whether an existing mechanism already covers the function and where the actual gap lies.

A successful unit test does not establish runtime liveness. A successful boot does not establish cognitive efficacy. A model's first-person self-report does not establish subjective experience.

**Development-tool correction (27 November 2026; merged in PR #228):** source review found that `nex_next_dev.py --buildable` unpacked each `classify()` result as two values although the classifier returns three (`node`, unproven prerequisites, terminal-null prerequisites). The command therefore raised a tuple-unpacking error when a buildable gap was present. The full report also described a `live_unproven` prerequisite as a hard gate, contradicting `sentience_dag.json`'s explicit rule that `built`, `live_unproven` and `terminal` are all dependency-satisfied statuses, with the latter two surfaced as caveats rather than blockers. PR #228 fixes the unpacking, prints both caveat types in `--buildable`, corrects the full-report language and exposes a testable `main(argv)` entry point. Exact-head CI run `46000586294` passed: **2,552 passed, 7 skipped, 45 subtests passed**, baseline OK. This is a developer-tool correction only: no DAG status, runtime code, cognitive behaviour, flags, specifications or roadmap changed.

---

## 11. Current mainline snapshot and open work (27 November 2026)

Mainline inspected: `5d7f4e28eb6760d206eed455429c90e967a5bf10` (27 November 2026, after #189 manual reconciliation, #191 responder, #196 listener/poster, #199 manual refresh and #200 remaining one-pen migrations). Exact-head full baseline CI for #200 passed: 2,539 passed, 7 skipped, 40 subtests; mind-map verifier: 30 nodes, 0 unverified, 14 dark, 2 blocked. These are repository CI/source-verification results only; they do not establish host/runtime state.

Post-snapshot reconciliation recorded in the Phase 0 handoff branch identifies the following merged changes already present in that mainline SHA: #168 (DailyLife/canary Writer routing), #169 (affinity Writer routing), #174 (P13 finitude re-verification), #175 (full-history mind-map verifier guard), #180 (learning-guard Writer routing), #183 (Expectations transaction/Writers), and #184 (Warrant composite pagination cursors). The source reality report and crosswalk carried by PR #188 remain pinned to `ae406fa8`; its handoff reconciles changes through `99ae476`. The later mind-map source-verifier outcome from PR #185 is recorded separately above. Treat each evidence artefact as snapshot-bounded, not as a single fully refreshed audit of `ddb9f15`.

Relevant pull requests and integration state at this update:

- **#187** — INDEX/manual stocktake update; merged after exact-head CI.
- **#185** — consolidated mind-map source re-verification; merged after exact-head full baseline and verifier (2,527 passed, 7 skipped, 40 subtests; 30 nodes, 0 unverified, 14 dark, 2 blocked). Two missing doctrine references and the overdue P13 marker remain unresolved.
- **#188** — Phase 0 evidence-pack carry-forward; merged after exact-head CI. Its report/crosswalk snapshots remain pinned to `ae406fa8`, while the handoff reconciles through `99ae476`. Do not treat these artefacts as a fully refreshed audit of current main.
- **#189** — manual reconciliation after #185/#188; merged.
- **#191** — responder one-pen migration; merged after exact-head full baseline CI.
- **#196** — listener/poster one-pen migration; merged after exact-head full baseline CI. Together, #191 and #196 migrate all three Moltbook loop persistence paths without activating external posting.
- **#200** — ResumptionSeeder, IdentityLoop, Fountain momentum and recursion-attribution one-pen migrations; merged after exact-head CI (2,539 passed, 7 skipped, 40 subtests). This closes the previously outstanding bounded migration PRs #162/#166/#170 and does not prove the global writer audit complete.
- **#198** — superseded by #200 after #199 advanced main; closed without merge.
- **#197** — superseded by #198/#200 after main advanced; closed without merge.
- **#192–#199** — intermediate or documentation carry-forward PRs; #199 is merged, the others are closed/superseded by #200 or the final merged changes.
- **#162, #166, #170, #171–#173** — original stale-base migration branches; closed/superseded. Their old-head CI results are not current-main evidence.
- **#178** — episodic read/write boundary audit; closed after review found its `p8_episodic` mind-map node unchanged from current main. This does not validate episodic runtime activation; it remains dark by default and unwired in the audited live loop.

**External RDO/Watcher status (not NEX roadmap progress):** current `main` contains the RDO Stage 2–7 modules, stage documents and tests. The historical `claude/rdo-stage2…stage7` branches are divergent and roughly 475 commits behind current main; do not merge them or rely on their old test claims. The Stage-7 handoff manifest and independent Watcher source/path verifier are present, but Stage 7's own document says its full objective-to-verified-delivery exit criterion remains incomplete: real objective demonstration, safe test-execution boundary, host-only runtime observation and separate human acceptance remain. Watcher source/path verification does not run tests or establish runtime behaviour. RDO v1.4 is the current working specification (founder indicated on 24 Nov that they believed it had been approved); v1.3 remains historical implementation lineage. Formal frozen supersession is not recorded in the consolidated NEX register.

PRs based on other branches (including the earlier continuity branch) are not automatically part of `main`. Check the base branch and merge commit before describing their changes as current NEX behaviour.

The repository-level Phase 0 evidence pack and the NEX first-read index serve different purposes: the evidence pack records bounded findings and unknowns; this index tells a developer how to orient, investigate and avoid repeating stale assumptions.

---

## 12. Operational checks and session handoff

Before making a runtime claim, inspect the actual host:
- current checkout and commit;
- process tree and single-instance lock;
- systemd unit and supervisor state;
- effective environment flags and configuration;
- listening ports and HTTP health;
- data directory and database paths;
- logs, Writer health and scheduler/loop liveness;
- whether external credentials and integrations are enabled.

Do not run destructive database operations, activate external posting, change live flags or alter runtime services during a read-only stocktake. Obtain explicit approval for consequential live actions.

For each development session, state:
- exact base commit and branch;
- governing documents consulted;
- files and pathways inspected;
- tests run and their scope;
- verified findings versus hypotheses/unknowns;
- code/document changes and rollback path;
- remaining dependencies and required approvals.

**Phase gates require the founder's explicit greenlight.** Present the evidence and wait for the required approval; do not treat a positive review or a technically mergeable PR as phase authorisation.

---

## 13. Living-document protocol

This INDEX is hand-maintained. When the architecture or operating procedure materially changes, update the relevant section in a separate, traceable commit describing what changed and what was learned. Keep it aligned with current source and approved governance documents.

The public `README.md` is the concise project overview and local setup guide. This INDEX is the developer's first-read orientation/manual. Phase 0 evidence documents are audit artefacts, not replacements for either.

When in doubt: the current source and approved governing documents win—not this index.

---

*Last amended: 28 November 2026 — records Sentience 5.5/NEX cognitive wire trace (§46), self-binding shared-Writer correction and open semantic edges (§47), and current RDO/Watcher progress; Gate 0 boundaries remain.*



---

## 14. DAG prerequisite-reference integrity (27 November 2026)

A source audit found that `classify()` and `topo_sort()` silently ignored prerequisite IDs absent from the DAG's `nodes` mapping. In classification, filtering an unknown prerequisite could make `all([])` pass and incorrectly report a gap as buildable; topological sorting could produce an apparently valid order for an incomplete graph.

The current `sentience_dag.json` snapshot contains 15 nodes and 15 prerequisite edges, with no unresolved references. The latent defect is nevertheless important because a future misspelled or deleted node ID could corrupt the tool's output.

**PR #229 is merged** to `main` as `9002291b1fd36624e895a8635a8b916888442548`. It adds deterministic prerequisite-reference validation to both classification and topological sorting, with regression coverage. Exact-head CI run `46002918341` passed. The change is confined to the DAG developer tool, tests and this manual; it does not change DAG content/status, runtime behaviour, cognitive settings, frozen specifications, roadmap or phase gates.

## 15. DAG status and duplicate-edge integrity (27 November 2026)

A second pass found two additional latent defects in the same developer-tool path:

1. **Unknown or missing status values** could fall through every classifier branch and silently disappear from the report.
2. **Duplicate prerequisite edges** could increment Kahn's indegree more than once while successor traversal decremented only once, creating a false cycle report.

The current graph was checked independently: 15 nodes, 15 edges, no unresolved references, no duplicate edges, and all statuses belong to the five values declared in `sentience_dag.json`. These are latent tool defects, not current graph corruption.

PR #232 is the clean mainline replay of the PR #230 changes and is **merged** as `1d133035dd8337a76f65225e8255bd13b655cf17`. It adds duplicate-edge validation, rejects unknown/missing statuses, and applies shared graph validation before classification and topological sorting. The original PR #230 exact-head CI run `46003289108` passed; the clean mainline replay exact-head run `46004897984` also passed. Four regression tests cover duplicate edges in both paths and unknown/missing statuses.

This work remains limited to `nex_next_dev.py`, its tests and this manual. It does not alter `sentience_dag.json`, runtime code, cognitive behaviour, flags, frozen specifications, roadmap or phase gates. Rollback is by reverting the isolated developer-tool change.


---

## 16. DAG input-shape validation (27 November 2026)

A further developer-tool audit found that reference/status validation could still receive malformed node structures: non-object node definitions, non-list prerequisite containers, non-string prerequisite IDs, empty node IDs, and non-string statuses. These inputs could produce incidental Python exceptions rather than a deterministic graph-validation error.

PR #235 adds fail-fast shape checks before prerequisite-reference, duplicate-edge and status validation, with six focused regression tests. It does not change the current DAG or the meaning of any status or dependency. The change is limited to `nex_next_dev.py`, its tests and this manual; runtime behaviour, cognitive settings, frozen specifications, roadmap and phase gates remain unchanged.


---

## 17. Mind-map policy scan boot-path coverage (27 November 2026)

A source-to-guard audit found that the descriptive-only policy scanner did not cover two paths imported by the normal runtime boot graph: `run.py` imports `strikes.catalogue` and `strikes.protocols`, while `gui/server.py` imports top-level `influence_trace`. The scanner's `RUNTIME_ROOTS` omitted both `strikes/` and `influence_trace.py`.

**PR #233 is merged** with both roots added and a regression test proving that prohibited `mind_map` imports in those paths are detected. Exact-head CI run `46005619584` passed. This was a scan-coverage gap, not evidence that either path had violated the descriptive-only constraint.

No runtime imports, cognitive behaviour, policy semantics, flags, DAG content, frozen specifications, roadmap or phase gates were changed. The policy scanner remains descriptive-only enforcement.

## 18. Additional bounded one-pen migrations (27 November 2026)

Four previously open, independently tested persistence migrations are now merged:

- **PR #223 — WorldBridge:** injects the shared sense Reader and beliefs Writer; Phase-A selection/log-only behaviour is preserved. Exact-head run `45997969694`: 2,550 passed, 7 skipped, 45 subtests.
- **PR #224 — GUI, Compassion and AffectCarry:** routes the reviewed GUI mutations and affect persistence through shared Writers/Readers. Exact-head run `45998065075`: 2,557 passed, 7 skipped, 45 subtests.
- **PR #225 — SelfBinding:** routes current self-state and append-only history persistence through the canonical dynamic Writer. Exact-head run `45998142261`: 2,551 passed, 7 skipped, 45 subtests.
- **PR #226 — Decoder:** places dynamic reads, word-context inserts and cursor advancement inside the canonical dynamic Writer transaction, with sense timing read through the shared Reader. Exact-head run `45998199987`: 2,551 passed, 7 skipped, 45 subtests.

These migrations preserve the existing feature gates and decision logic. They close the four bounded persistence branches only; they do not prove the repository-wide one-pen audit complete or establish host/runtime activation. Cross-database operations remain separate transactions unless explicitly documented otherwise.


---

## 19. Phase 0 follow-up audit and gated SelfPredictionLoop integration (27 November 2026)

The current-main follow-up audit has rechecked G-68 to G-72. G-68 (experimental ProbeRunner safety), G-69 (SurpriseLoop delivery, Gate 0 held), and G-70 (speech playback trace continuity, proposed in PR #261 with exact-head CI pending) remain separately tracked. G-71's hidden-rowid cursor defect is closed by PR #253; Warrant eligibility questions remain separately tracked as G-74. No proposal is treated as activated.

G-72 is closed by **PR #236** (commitments canonical Writer/Reader path) and **PR #238** (AppState handle injection through the gated SelfPredictionLoop, self-prediction, owned-belief, commitments and Expectations paths). Exact-head full-suite runs passed: #236 `46006462779` (2,573 passed, 7 skipped, 45 subtests) and #238 `46008022480` (2,584 passed, 7 skipped, 45 subtests).

The `NEX5_SELF_PRED=1` gate and all other feature gates remain unchanged. No loop was started and no cognitive decision logic, cadence, thresholds, frozen specifications, roadmap or phase-gate state was changed. This closes the persistence-ownership integration finding only; it does not certify host activation or a complete repository-wide one-pen census.


---

## 20. Phase 0 continuation: G-68 to G-72 and shared daemon checkpoint schema (27 November 2026)

This section records follow-up work after the previous manual update. It is a remote-repository/source-and-CI stocktake, not a live-host inspection. The current mainline at the time of this update is `36624b7106ebaec801f6d744e87cd37b73279021`.

### Verified integration

- **PR #241 — G-68 to G-72 evidence reconciliation: merged** to main as `36624b7106ebaec801f6d744e87cd37b73279021`. The exact-head PR test run passed before merge. The change updates the Phase 0 follow-up record and handoff; it does not itself close the underlying open findings or authorize behaviour changes.
- The consolidated S-01–S-25 register, roadmap, phase gates and cognitive policy remain unchanged. Gate 0 remains pending founder review; Phase 1 is not authorized.

### Shared dynamic daemon checkpoint schema

A fresh-schema static-SQL compilation failure exposed a missing shared schema declaration for `dynamic.db:daemon_kv.updated_at`. The table is referenced by SurpriseLoop and the Moltbook poster. This is a persistence/schema completeness defect, distinct from the semantics of either worker.

- **PR #243 — shared `daemon_kv` schema and migration: OPEN / CI RUNNING at this update.** Its current head is `b55fe9b731d7353b0b8bb58fac1840bb34536ad1`. It adds the canonical table declaration to `substrate/schema/dynamic.sql`, an additive migration in `substrate/init_db.py`, and fresh-database plus legacy-table preservation regression tests in `tests/test_daemon_kv_migration.py`.
- The migration is additive: the intended legacy behaviour is to add `updated_at` without deleting or rewriting existing key/value checkpoints. The focused tests assert both the fresh schema and preservation of a pre-existing row.
- Do not describe this change as merged, validated or deployed until the exact-head CI result is green and the PR is integrated.

### Dependent PRs and test evidence

- **PR #242 — gated WorldPredictionLoop persistence ownership: OPEN; exact-head CI failed** on the same fresh-schema compilation error: `daemon_kv.updated_at` is absent from its base snapshot. The run reported 2,587 passed, 7 skipped, 45 subtests, and one failure in `tests/test_schema_indexes.py::TestEveryStaticStatementCompilesOnFreshInit`. This is a shared schema prerequisite failure; it does not establish that the AppState handle-injection change itself is defective. Revalidate on current main after #243 is merged. The existing `NEX5_WORLD_PRED` gate and prediction behaviour must remain unchanged.
- **PR #240 — Warrant declared composite-key cursor: OPEN; exact-head CI failed** on the same missing `daemon_kv.updated_at` fresh-schema error (2,583 passed, 7 skipped, 45 subtests, one failure). Its base is stale relative to current main. After #243 is integrated, rebase/replay the cursor-only change on current main and rerun the full suite. Do not broaden Warrant use-day eligibility or alter Warrant policy.
- **PR #239 — SurpriseLoop monotonic event cursor: OPEN; exact-head CI passed.** It proposes tie-safe event paging, retry-safe checkpoint handling and related duplicate-content treatment. Despite green tests, it remains **held for founder Gate 0 review** because it changes which events may enter the belief corpus. Do not merge, deploy or activate it before that approval.
- **PR #243 CI** is still running at the time of writing; the result must be checked before any merge decision. A green result on another PR or on a prior base does not substitute for #243's exact-head result.

### G-70 refinement — speech outcome state versus causal trace

A targeted source recheck refines the wording of G-70. The speech path is not wholly unobservable after enqueue: `speech/queue_consumer.py` updates each queue row through `speaking` and then `spoken`, or `failed` on synthesis/playback exceptions; non-speakable content is marked `suppressed`. `speech/player.py` calls `sounddevice.play(..., blocking=True)` and `sd.wait()`. Therefore a persisted `spoken` status means the playback call returned without raising; it is not independent acoustic confirmation that sound reached a listener.

The remaining G-70 gap is specifically **cross-thread causal trace continuity**: the Fountain trace records the `speech_queue` enqueue Writer delta and queue-row ID, but the consumer does not continue that trace with parent-linked dequeue, synthesis, playback-start/completion or failure events. The queue status columns are operational outcome state, not a substitute for a parent-linked trace. This refinement does not change the finding's OPEN status and does not authorize speech-path changes.

### Development and evidence interpretation

The current work continues the research → bounded implementation → rescan → consequence analysis → documentation cycle. Persistence ownership fixes and schema completeness are kept separate from cognitive-policy changes. A green unit or full-suite result demonstrates only the tested repository state and paths; it does not prove that a feature flag is enabled, a worker is running, a host database has migrated, or a behavioural effect is beneficial.

The shared Writer/Reader one-pen rule remains in force. The six SQLite databases remain separate transaction domains; no cross-database atomicity is implied. No live substrate database, host process, service, credential, external integration or feature flag was inspected or changed during this remote repository work.

### Next bounded actions

1. Complete exact-head CI review for #243; correct any migration/test defects before merging.
2. Once #243 is merged, rebase/revalidate #242 and #240 against current main; preserve their narrow persistence/cursor scopes.
3. Keep #239 held for explicit Gate 0 founder review despite its green CI.
4. Continue the source-to-sink Phase 0 audit and update this manual in the same development cycle as findings and integrations accumulate.
5. Keep unresolved defects, unknown host/runtime facts and approval gates explicit. Do not promote a Phase 0 stocktake into Phase 1 authorization.


## 21. RDO experiment-registry fail-closed boundary and shared-handle review (27 November 2026)

### RDO protected-experiment registry

A new test-only continuation, **PR #245 — RDO fail-closed experiment registry boundary: OPEN / exact-head CI RUNNING**, adds regression coverage for a safety boundary already present on main. Head: `2fe8c360c75fafd956a4c690203c653eafdf4ea0`; exact-head run: `46013089837`.

Source review on main confirms the distinction:

- `watcher.registry.ingest_registry()` returns evidence class `unknown` when the observation-report directory is missing; a successfully read registry is `measured` and contains an `active_or_pending` list.
- `rdo.orchestrator._active_experiments()` returns `None` for unknown/unmeasured evidence, malformed registry data, or read errors. It returns a list (including an empty list) only when the registry is measured and structurally valid.
- `rdo.prioritise.eligibility()` blocks when the registry is `None`; a verified empty list does not create a registry blocker; a matching active experiment blocks the affected obligation.
- Stage 2 and Stage 3 both pass the registry result into the shared `_run_one()` path. PR #245 adds tests that protect this propagation as well as the eligibility distinctions.

The PR is tests-only and uses synthetic evidence. It does not change eligibility logic, experiment state, execution, runtime flags, roadmap or cognitive behaviour. Do not call it validated until its exact-head full-suite result is green. This is a repository-level regression check, not an inspection of live experiment state.

### Shared AppState Reader/Writer concurrency contract — source recheck

The #242 handle-injection review was extended to the underlying substrate primitives. `substrate.reader.Reader` stores a database path and opens/closes a fresh read-only connection for each `read()` / `read_one()` call; it does not share one SQLite connection across daemon threads. `substrate.writer.Writer` serializes submitted requests through a thread-safe queue on its dedicated worker thread; synchronous callers wait on each request's Future. These implementations support sharing the AppState Reader/Writer objects across the WorldPredictionLoop thread without creating a second Writer or a cross-thread SQLite connection. This source review supports the ownership design, but does not prove the host actually starts the gated loop or that its external price/voice services are available. The `NEX5_WORLD_PRED` gate remains OFF by default and unchanged.

### Updated continuation order

1. Finish exact-head CI for #243, #244 and #245; merge only after green results and final diff review.
2. After #243 lands, rebase/revalidate #242 and #240 against current main; preserve their narrow scopes.
3. Keep #239 held for explicit Gate 0 founder review.
4. Continue the Phase 0 source-to-sink audit and keep this manual synchronized with each meaningful code or evidence change.



## 22. Current-main replay and exact-head test reconciliation (27 November 2026)

### Shared schema prerequisite integrated

**PR #243 is merged** to main as `5b95c6caaf6f99a61140ec261412421c08fb01cb`. Its exact-head full-suite CI passed. The canonical `dynamic.db:daemon_kv(key, value, updated_at)` declaration and additive legacy migration are now part of main. Existing checkpoint rows are preserved. This integration does not activate any daemon or alter event-selection policy.

### Dependent work replayed on the corrected base

The original branches #240 and #242 were based before the shared schema prerequisite and their exact-head runs failed on that missing-schema defect. Rather than treating those runs as evidence against the isolated changes, the narrow patches have been replayed on current main:

- **PR #247 — Warrant composite-key cursor current-main replay: OPEN / exact-head full-suite CI RUNNING.** It uses the declared primary keys of `belief_lineage` and `arc_members`, not hidden SQLite rowids that may be remapped by VACUUM. Existing scalar cursors and Warrant policy are preserved.
- **PR #248 — gated WorldPredictionLoop AppState handle current-main replay: OPEN / exact-head full-suite CI RUNNING.** It passes the existing AppState conversations Writer/Reader and beliefs Reader through prediction, calibration, persistence and resolution. The `NEX5_WORLD_PRED` gate remains unchanged and OFF by default; no loop was started.

The original #240 and #242 PRs are superseded by these current-main replays. Their prior CI failures remain historical evidence about the missing schema on their old base, not validation of the replayed heads.

### RDO registry regression: fixture correction

The original **PR #245** exact-head full-suite run failed with **1 failed, 2,592 passed, 7 skipped and 45 subtests passed**. The failing test's synthetic Stage 2 cycle fixture omitted `signature_matches`, a field consumed by the real Stage 2 report after the mocked runner returned. Source review confirmed the production registry boundary itself was not the failure.

**PR #249 — current-main replay and corrected fixture: OPEN / CI status to be checked.** It carries the tests onto the post-#243 mainline and adds the missing `signature_matches=[]` fixture field. The production RDO code is unchanged. The tests continue to distinguish an unavailable/unverified registry (`None`, blocked) from a successfully measured empty registry (`[]`, no registry blocker), and cover active matches plus Stage 2/Stage 3 propagation. No live experiment state is read or modified.

### Manual branch reconciliation

The earlier manual updates #244 and #246 were authored against main before #243 merged. **PR #250** carries their full `INDEX.md` content onto the post-#243 mainline and adds this reconciliation section, so the maintained first-read manual does not omit the now-integrated schema prerequisite or the replayed dependent work.

### Current evidence and next sequence

1. Require exact-head full-suite success and diff review for #247, #248 and #249 before merging.
2. Complete the current-main manual integration in #250; keep its status distinct from runtime activation.
3. Keep #239 held for explicit founder Gate 0 review despite its earlier green CI.
4. Continue the Phase 0 source-to-sink audit; preserve frozen specifications, roadmap, feature gates and cognitive behaviour.
5. Treat host migration, service operation, feature enablement and behavioural benefit as unverified until separately observed and measured.


## 23. Warrant cursor ordering: append-time semantics and older-parent additions (27 November 2026)

A second-pass producer review found that a cursor ordered only by declared primary key is not sufficient for every append path. `theory_x/arcs/detector.py` can add a new `arc_members` row to an already-existing active arc when a later fire joins it. That row has a new `joined_at` but can have an `arc_id` lower than the last key-only cursor. Similarly, a new lineage relation can be recorded for an earlier child ID. A key-only cursor could therefore permanently skip valid new use evidence even though it is immune to hidden-rowid remapping.

**PR #247 was strengthened before merge.** Its current design orders by event time first and uses declared primary-key columns only as deterministic tie-breakers:

- lineage: `(created_at, child_id, parent_id, relationship)`
- arc membership: `(joined_at, arc_id, belief_id)`

This preserves tied-timestamp pagination without relying on hidden rowids and ensures later events for older arcs/children still sort after the saved cursor. The tuple-cursor reader also validates component types and falls back to a replayable default when stored JSON is malformed or type-incompatible.

The expanded regression fixture now advances beyond arc ID 1 to arc ID 2 and child ID 104, then inserts a later event for arc ID 1 and child ID 2. It asserts both events are still consumed. It also forces rowid remapping between pages and exercises malformed cursor data. Current #247 head at this update: `3908a587373e958dbd3faf542d7c3a7d56d50677`; its exact-head CI is queued/running and must pass before merge.

This is an important distinction for future cursor work: a stable identity key solves rowid instability, but does not by itself prove append-order monotonicity. Cursor ordering must be checked against the actual producer's insertion semantics, not inferred from the table's primary key alone.


## 24. WorldPredictionLoop persistence ownership integrated (27 November 2026)

**PR #248 is merged** to main as `a49e0d0e6e048eeed7d5676611b53cf3ce4d286e`. Its exact-head full baseline suite passed: **2,590 passed, 7 skipped and 45 subtests passed** (run `46013847927`). This integrates the gated WorldPredictionLoop's use of AppState-owned conversations Writer/Reader and beliefs Reader through prediction generation, calibration, schema setup, resolution and scorecard paths.

The source review remains as recorded above: Reader opens a fresh read-only connection for each operation; Writer serializes writes on its queue worker. The change removes duplicate per-worker persistence handles from this path. It does **not** set `NEX5_WORLD_PRED`, start the loop, establish availability of the external price/voice endpoints, or demonstrate predictive benefit. The feature gate remains OFF by default.

The manual update is being replayed on this new mainline as **PR #251** so its verified-main SHA and integration history match the current repository. The earlier #250 manual branch was based before #248 merged and is superseded by this current-main documentation replay.

### Remaining exact-head validation

- **PR #247** — Warrant event-time plus stable-key cursors: expanded late-addition/rowid-remap regression suite; exact-head CI still pending.
- **PR #249** — RDO fail-closed registry regression tests: Stage 2 fixture now includes the complete `CycleRecord` field contract; exact-head CI still pending.
- **PR #239** remains held for explicit founder Gate 0 review, regardless of its earlier green CI.


## 25. Post-integration revalidation of Warrant and RDO test branches (27 November 2026)

After #248 merged, the pending #247 and #249 branches were replayed once more so their full-suite results are tested against the actual current mainline, not the pre-#248 base:

- **PR #253 — Warrant event-time plus stable-key cursor, post-#248 replay: OPEN / exact-head CI pending.** It carries the late-addition fix and its rowid/tie/malformed-cursor regression tests onto main `a49e0d0e6e048eeed7d5676611b53cf3ce4d286e`.
- **PR #254 — RDO experiment-registry fail-closed tests, post-#248 replay: OPEN / exact-head CI pending.** It carries the corrected Stage 2 fixture and registry-boundary tests onto the same mainline.

The older #247 and #249 branches are closed as superseded. Their CI outcomes remain historical only; #253 and #254 are now the authoritative branches for any merge decision. The manual is kept on the current-main base in PR #252.


## 26. Warrant cursor query-plan and performance risk (27 November 2026)

The event-time cursor is a correctness improvement, but its production cost is not yet measured. The current beliefs schema indexes `belief_lineage` by parent/child and `arc_members` by belief ID; it does not declare indexes matching the new ordered cursor tuples:

- `belief_lineage(created_at, child_id, parent_id, relationship)`
- `arc_members(joined_at, arc_id, belief_id)`

Without matching indexes, SQLite may need to scan and sort these tables for each Warrant use cycle. The previous timestamp/rowid cursor also lacked an obvious matching composite index, so this is not yet established as a regression; it is an unmeasured cost of the current access path.

No speculative index migration has been added. Before enabling `NEX5_WARRANT_RECORD` on a data-bearing host, measure table row counts, inspect `EXPLAIN QUERY PLAN` for both cursor queries, and time representative cycles against realistic data. Add the composite indexes only if those measurements justify their write/storage overhead. The feature gate remains OFF and no live database was inspected.


## 27. SurpriseLoop loss-safe event delivery: current-main replay and Gate 0 hold (27 November 2026)

A further open contribution, **PR #251**, addresses the SurpriseLoop's timestamp-only cursor and failure checkpointing. Source review confirms that `theory_x/stage_prediction/predictive_substrate.py` writes each resolved `surprise_events` row with its final `actual_content`, `surprise_flag` and `big_surprise` values at insertion time; this supports the event-ID cursor's assumption that eligibility fields are not later filled in for an existing row.

The current-main replay is **PR #255 — SurpriseLoop loss-safe event delivery: OPEN / exact-head CI pending / GATE 0 HOLD**. It is based on post-#248 main. The implementation uses the monotonic `surprise_events.id`, migrates the legacy timestamp boundary by replaying events exactly at the cutoff, writes timestamp and ID checkpoint values together, and stops at the first non-duplicate conversion/write failure so the failing event and later events retry. Only duplicate belief-content collisions are checkpointed as already represented. Ordinary surprise tags are de-duplicated.

**Do not merge or deploy #255 yet.** This is not merely an observability fix: events that were previously skipped can now reach the belief corpus and change downstream retrieval inputs. The PR's own scope statement preserves the Gate 0 requirement. Founder review and explicit approval of that behaviour-impact decision are required. The correction does not change prediction scoring, surprise thresholds, event generation or loop cadence.

The older-base PR #251 is closed as superseded by #255. Its prior exact-head full-suite run passed, but #255 requires its own current-main exact-head validation. Gate 0 remains pending; Phase 1 remains unauthorized.


### SurpriseLoop migration boundary — historical limitation

The old timestamp-only implementation advanced its timestamp checkpoint even after some non-duplicate conversion/write failures. The new migration derives the initial event-ID cursor from the maximum event ID with `triggered_at < legacy_timestamp`; it replays rows exactly at the cutoff and all later rows. It cannot identify older rows that may already have been skipped before migration, and those rows remain outside the replay window. Recovering that older history would require a separate, explicit decision to backfill the belief corpus; it must not be smuggled into this cursor repair.

Source review of `theory_x/stage_prediction/predictive_substrate.py::_verify()` confirms each `surprise_events` row is inserted with its final `actual_content`, `surprise_flag` and `big_surprise` values together. The current event-ID scan therefore does not depend on a later update making an older event eligible. This assumption should be rechecked if the producer contract changes.


## 28. Warrant event cursor integration and subsequent revalidation (27 November 2026)

**PR #253 is merged** to main as `c80d9dbb878ac15a39d6707a9c89ab2a51f8518c`. Its exact-head full baseline suite passed: **2,590 passed, 7 skipped and 45 subtests passed** (run `46014884835`). The Warrant use-day scan now orders lineage and arc membership by event time with declared composite-key tie-breakers, preventing rowid remapping loss and late additions to older active arcs from being skipped. The Warrant gate remains OFF; this is persistence/cursor correctness, not evidence that Warrant is earning or affecting beliefs.

After #253 merged, the remaining pending branches were replayed onto the latest main:

- **PR #256 — RDO registry fail-closed regression tests: OPEN / exact-head CI pending.** Tests only; the complete Stage 2 fixture includes `signature_matches`.
- **PR #257 — SurpriseLoop loss-safe event delivery: OPEN / exact-head CI pending / GATE 0 HOLD.** Event-ID cursor and retry integrity fix; not for merge or deployment until founder approval because newly delivered events can alter belief-corpus inputs.

The older #254 and #255 branches are superseded by these post-#253 replays. The earlier PR #252 manual branch is likewise superseded by this current-main manual replay.


## 29. Dormancy scanner proposal review and older-base work (27 November 2026)

The current-main review confirms the dormancy issue recorded as **G-73** in the refreshed verified-defect backlog:

- `DormancyScanner.scan_incremental()` currently selects the oldest 50 source-eligible beliefs by `created_at` with no cursor. An unchanged oldest cohort can therefore be rescanned repeatedly.
- `DiversityLoop` owns one persistent scanner and invokes it on its loop cadence. `ClockRunner._run_fast()` constructs another scanner inside each fast tick, so that second path does not retain a cursor between ticks. Both paths address the same beliefs population/table; combined runtime work rate has not been measured.
- **PR #102** proposes ID-keyset rotation, wraparound, persistent ClockRunner scanner ownership, and tier/paused/retired filters in scan, dormant selection and reanimation. **PR #145** adds tests for partial-tail wraparound and persistent-instance reuse. Both exact-head suites passed on their own older base, but neither branch has been revalidated on current main.
- The proposal still leaves two independent scanner instances/cursors: DiversityLoop's scanner and ClockRunner's scanner. PR #145 tests persistence of the ClockRunner instance, not single-owner scheduling or combined cadence.
- The proposed final Fountain reanimation fetch rechecks `tier <= 7` and `paused = 0` but does not recheck `erosion_stage != 'retired'`. Add a test for a belief retired between selection and final injection before considering that path fully guarded.

This remains a scan-coverage/ownership and eligibility-contract question, not an observed live incident. Do not merge or replay the behaviour filters or alter maintenance cadence until the current-main rebase, exact-head tests, and Gate 0 policy review are complete. The older documentation branches #142/#144 are superseded by the current-main backlog/handoff update in PR #258; the separate PR #102/#145 code/test proposals remain open for review.


## 30. Warrant lifecycle questions and stale audit-branch reconciliation (27 November 2026)

The refreshed Phase 0 backlog and handoff now also carry two Warrant lifecycle questions verified against current main:

- **G-74 — retired-marker eligibility:** WarrantPass's scoring query and WarrantRecorder's survival query do not filter the independent `erosion_stage='retired'` marker. Normal Harmonizer retirement writes Tier 8; no normal lower-tier retired-marker writer or live such row was established. Confirm whether this marker overrides tier for Warrant scoring/survival before adding filters.
- **G-75 — Recorder versus WarrantPass boot:** normal `run.py` starts WarrantRecorder only behind `NEX5_WARRANT_RECORD=1`. No normal WarrantPass loop construction/start was found in `run.py` or `gui/server.py`; `tools/warrant_validate.py` performs one-shot read-only validation. The tracked keepalive sets the Recorder flag but not `NEX5_WARRANT`; host-effective state remains UNKNOWN because the launcher path blocker and active user systemd unit are unresolved. Record-only operation may be intentional while evidence accrues.

The older documentation branches **#142/#144** were based on a divergent continuity branch and are superseded by the current-main verified backlog/handoff updates in #258. Their useful findings were rechecked against current source and reconciled into the current backlog with corrected dispositions: G-53/G-71 Warrant cursor defects are closed by #253; G-56 EdgeBuilder telemetry was already closed by #157; G-53's former walk-anchor concern is narrowed in current G-54; the other current questions are G-51, G-54, G-55, G-57, G-73, G-74 and G-75. The stale producer-trace document was not merged wholesale because it predates substantial mainline changes.

PR #102 and test-only follow-on #145 remain older-base proposals. Their exact-head CI passed on that older base, but they are not current-main validated. PR #102 changes dormancy scan coverage, retired/paused eligibility and the fast-clock scanner lifecycle; PR #145 tests partial wraparound and ClockRunner scanner reuse. The two independent scanner owners remain, and the final Fountain reanimation query in #102 does not recheck the retired marker. Do not merge these proposals until the current-main replay, end-to-end eligibility tests and Gate 0 policy review are complete.

PR #258 now updates the first-read manual, verified defect backlog and Phase 0 handoff together. It does not alter the frozen specification/register, roadmap, runtime, flags or cognitive behaviour.


## 31. RDO registry regression integration and SurpriseLoop revalidation (27 November 2026)

**PR #256 is merged** to main as `e78773def4549f646257945e5886ec71a7837374`. Its exact-head full baseline suite passed: **2,599 passed, 7 skipped and 45 subtests** (run `46015838864`). It adds tests-only protection for the fail-closed RDO experiment registry: unknown/unreadable/malformed registry state remains blocked, verified-empty remains distinct, active matches block, and Stage 2/Stage 3 propagate the registry into the shared runner. No production RDO eligibility or experiment state changed.

**PR #259 — SurpriseLoop loss-safe event delivery on post-#256 main: OPEN / exact-head CI GREEN / GATE 0 HOLD.** Its exact-head full suite run `46017043819` passed **2,610 passed, 7 skipped, 45 subtests**. It replays the event-ID cursor and retry-safe checkpoint correction after #256 merged. Do not merge or deploy it until founder approval because previously skipped events may enter the belief corpus. Its legacy migration does not recover rows strictly older than the old timestamp cutoff.

The earlier manual PR #258 is superseded by this post-#256 documentation replay. PR #260 carries the full manual, backlog and handoff onto this mainline. PR #102/#145 remain older-base dormancy proposals and are still subject to the G-73 policy/revalidation boundary.


## 32. TimeFetch test inventory and VoiceEngine eligibility consumer (27 November 2026)

A current-source recheck incorporated the useful correction from older PR #143 and extended it through the consumer:

- `tests/test_throw_net_time_fetch.py` does exist. It covers confidence/content-length filters, novel-association matching and similarity ordering, arc type/quality filters, ProblemMemory routing, deduplication/capping and provenance.
- It does not assert exclusion of Tier-8, paused, locked or lower-tier retired belief endpoints, nor current-state eligibility of novel-association endpoints or arc provenance.
- `VoiceEngine._retrieve_candidates()` consumes `TimeFetch.run()` results and enriches belief candidates with tier/reinforce_count but does not recheck paused/locked/retired state. `_score_candidate()` applies a 0.5 tier score to non-T3–T6 candidates rather than excluding them; a sufficiently strong candidate can still clear the 0.6 minimum. `tests/test_voice_engine.py` compares T4 and T8 scores but does not assert hard exclusion.

This remains a policy/coverage gap, not an instruction to change retrieval. Confirm the canonical inactive-belief eligibility contract, then add end-to-end TimeFetch-to-VoiceEngine tests. The stale documentation branch #143 is superseded by the corrected current-main backlog entry G-52 in PR #260; its trace document was not merged wholesale.


---

## 33. G-70 speech trace continuity — merged implementation and remaining M0.5 evidence (27 November 2026)

The G-70 source-level speech-queue continuity gap is implemented and merged by **PR #261 — [causal provenance through speech playback](https://github.com/kron777/Nex_v5.0/pull/261)**.

- **Merge:** `cc8ae43652bdba919198ee4bb90fabbd8f05632f`; PR head `bed052c9d63422f52a9514325f74f113959db2a3`; base `e78773def4549f646257945e5886ec71a7837374`.
- **Scope:** `influence_trace.py`, `theory_x/stage6_fountain/crystallizer.py`, `speech/queue_consumer.py`, and `tests/test_speech_trace_bridge.py`.
- **Mechanism:** a process-local correlation registry keyed by belief ID, registered before queue insertion becomes visible; maximum 512 entries, one-hour TTL, one-shot consumption, and cleanup on failed insertion. The consumer emits parent-linked dequeue, synthesis, playback, suppression and terminal status/failure events.
- **Failure coverage:** explicit tracing for synthesis/playback failure and speaking/spoken/suppressed/failed status-write failures; registry concurrency, expiry, capacity, discard and trace-free fallback are tested.
- **Safety boundary:** no speech text/audio enters trace metadata; no schema, speech selection, queue ordering, cadence, synthesis/playback behaviour, flags or cognitive decisions were changed. The trace overlay remains default OFF. The registry is process-local and does not reconstruct lineage after restart.
- **Evidence limitation:** `spoken` means the blocking playback call returned without raising; it is not acoustic confirmation that a listener heard sound. No live L4 trace was captured.
- **Exact-head CI:** run `46020502376` passed **2,611 passed, 7 skipped, 45 subtests**, baseline OK. The mind-map verifier on the code-only branch still showed the P9 stale-anchor warning; its corrected source anchor was reverified by documentation-branch run `46020611137`, which passed **2,599 passed, 7 skipped, 45 subtests** with no P9 stale warning.
- **Disposition:** **G-70 source/test gap CLOSED. M0.5 acceptance remains OPEN** pending complete roadmap evidence, including authorised live L4 capture and paired semantic-equivalence evidence. No live runtime, speech device, database or feature flag was touched.


## 34. P9 source-anchor re-verification after daemon_kv schema insertion (27 November 2026)

The PR #261 exact-head mind-map check reported P9 as stale because `substrate/schema/dynamic.sql` changed on current main. A comparison of the prior and current schema blobs showed the entire change was an eight-line `daemon_kv` table insertion at the beginning of the file. The `held_tensions` definition itself was byte-for-byte unchanged and moved from lines 144–159 to 152–167. The P9 Harmonizer path and focused held-tension/retry tests were re-read. The source anchor and `last_verified` date were updated in the current documentation branch only; no P9 status or runtime behaviour changed. Documentation-branch CI run `46020611137` confirmed the corrected anchor: P9 no longer reports stale. The two missing-doctrine references and overdue P13 warning remain the only mind-map warnings.



## 35. WarrantPass boot-path documentation correction (27 November 2026)

The G-75 source review found a false statement in `WarrantPass`'s class docstring: it said the pass was constructed and started by `run.py`. The audited `run.py` source constructs and starts `WarrantRecorder` behind `NEX5_WARRANT_RECORD=1`, but contains no WarrantPass construction/start. `WarrantPass.start_loop()` separately checks `NEX5_WARRANT=1`. PR #262 merged as `c9e25d7cf85659e80053f5fe75928ee71486a141`; it corrects the docstring only and does not wire the pass or alter either flag. G-75 remains open because the intended record-only versus scoring lifecycle still requires owner clarification.



## 36. Current-main update after Warrant and speech-trace merges (27 November 2026)

PR #262 merged as `c9e25d7cf85659e80053f5fe75928ee71486a141`, correcting the WarrantPass class docstring without wiring or activating it. PR #261 merged as `cc8ae43652bdba919198ee4bb90fabbd8f05632f`, closing the G-70 speech trace source/test gap. The exact-head PR #261 suite passed **2,611 passed, 7 skipped, 45 subtests** (run `46020502376`). The G-75 lifecycle question and complete M0.5 acceptance remain open. The P9 stale-source warning was cleared after its schema line-anchor correction; documentation-branch run `46020611137` passed **2,599 passed, 7 skipped, 45 subtests**. The two missing doctrine files and overdue P13 unblock remain visible warnings, not silently repaired. This manual snapshot is pinned to current main `cc8ae43652bdba919198ee4bb90fabbd8f05632f`.



## 37. Current-main reconciliation and Claude first-read handoff (27 November 2026)

**Evidence snapshot:** `main` at `80c30b6cc649bb9ce46fd6fdc06bf4afbc9f57c5`. This is the merge commit for PR #263, which reconciled `INDEX.md`, the verified defect backlog, Phase 0 handoff, ADR-001 and the mind-map after the G-70 merge. The five-file documentation reconciliation is merged; it does not alter runtime code, frozen specifications, roadmap, feature flags or Gate 0.

### Manual authority and unresolved source material

This manual is an orientation and evidence index, not authority to create or reinterpret project policy. The consolidated S-01–S-25 register remains frozen. The roadmap and phase gates remain controlling for authorization. Source proves what the repository currently does; it does not by itself prove that the behaviour is intended.

The separate user-authored **NEX v5.0 Development Proposal V2.1** and its approval record remain an unresolved authority dependency. A recursive path inventory of the current `main` tree found no file whose path identifies that proposal. Earlier Library retrieval also did not establish the authoritative original or approval record. This means **not located**, not proven nonexistent. Do not reconstruct the proposal from memory, summaries, later implementation, `SPECIFICATION.md`, or this manual. Do not treat an unapproved proposal as an approved amendment.

### G-58 — Goal lifecycle contract remains unresolved

The current-main source finding is unchanged: `GoalManager.open()` creates goals with `state='open'`; its `list_open()` and `get_active()` methods select that state. `CoherenceGate._load_context()` queries `state='active'`. The focused Gate test helper seeds `active` directly and therefore does not exercise the normal GoalManager creation path. No normal `open` → `active` transition was established in the reviewed source.

This is a verified producer/consumer mismatch, but **the intended lifecycle semantics are not established**. Do not fix it by changing the writer to `active`, changing the Gate query to `open`, adding an automatic transition, migrating stored rows, or broadening the meaning of either state until the authoritative lifecycle rule and approval are recovered. The next valid engineering step is to obtain the exact V2.1 text and approval evidence, map its relevant clauses to each state and transition, then add a GoalManager-to-CoherenceGate integration test that encodes the approved contract. If the authority remains unavailable, keep G-58 open and document the limitation; do not guess.

### Current engineering boundary

- **PR #264** was superseded and closed because its base was pre-PR #263 main (`cc8ae43652bdba919198ee4bb90fabbd8f05632f`). Its exact-head full-suite run `46023260805` eventually passed, but that result did not cover the post-#263 base. **PR #266** replays the same two-file provenance-erosion keyset pagination fix and regression tests on current main `edb869af154a33cd77df5ad9bdf010d3e6ab06a2`; it is draft and awaits its own exact-head full-suite result. The behavioural impact remains material: previously starved beliefs may advance on a future six-hour cycle. Do not report #266 as validated or merged.
- G-69 remains held for Gate 0 review. G-73/G-74/G-75 remain open lifecycle/eligibility questions. The two missing doctrine references and overdue P13 unblock remain visible mind-map warnings.
- PR #263's merge is a documentation integration, not a Gate 0 approval. Gate 0 remains pending founder review; Phase 1 remains unauthorized.

### Claude first-read protocol

For a fresh independent review, read in this order: this `INDEX.md` (especially the latest status and evidence protocol in §39); `PHASE0_HANDOFF.md` (especially its latest status block); `NEX_PHASE0_VERIFIED_DEFECT_BACKLOG_2026-11-27.md` (check each finding's source SHA); `ADR-001.md`; then the exact frozen specification/register and Master Roadmap v3.0 from their authoritative locations. `NEX_REPOSITORY_REALITY_REPORT.md` and `NEX_ARCHITECTURE_CROSSWALK_v2.md` are historical source snapshots at `ae406fa8fcb1abdf25cdf4ae1bd65333e1148ca8`, not current-main audits; use them as maps and independently revalidate every relevant claim against the current checkout before relying on them.

Ask Claude to independently locate the original V2.1 proposal and approval record, identify the exact goal-lifecycle clauses, and return verbatim clause references plus the evidence establishing approval. If it cannot locate them, it must say so rather than infer the rule. Claude should then independently verify G-58 against current source and tests, distinguish confirmed implementation from intended semantics, and propose the smallest test-first reconciliation. No state semantics, policy, schema, live database or runtime change is authorized by this handoff.

The continuing work method is research → bounded implementation where authority permits → rescan changed code and surrounding dependencies → record evidence, consequences and newly exposed gaps → update this manual and backlog. Keep provisional hypotheses separate from verified facts and actively test disconfirming explanations.


## 38. Provenance erosion pagination replay corrected to the post-manual mainline (27 November 2026)

The prior §37 snapshot recorded PR #264 as based on the current post-#263 mainline. A later PR metadata and commit-graph recheck disproved that: #264's merge base was `cc8ae43652bdba919198ee4bb90fabbd8f05632f`, before the PR #263 documentation reconciliation. Its exact-head full-suite run `46023260805` subsequently completed successfully, but it is evidence for that older head/base only.

PR #264 was closed as superseded. **PR #266** replays the same source and regression-test changes on current main `edb869af154a33cd77df5ad9bdf010d3e6ab06a2`. It is draft, with exact-head CI pending. The source change remains bounded keyset pagination; the behavioural consequence remains that beliefs previously starved beyond the first 500 may now advance at the next scheduled erosion pass. The undo log is audit metadata, not automatic rollback. Keep #266 separate for exact-head verification and review; no live state was accessed or changed.

This correction illustrates the manual's evidence rule: a passing workflow on a PR head does not establish that the PR is based on the latest mainline. Verify both the exact tested SHA and its merge base before calling a replay current-main validated.


## 39. Claude comprehension, evidence freshness and current-main status ledger (27 November 2026)

**Authoritative repository snapshot checked for this update:** `main` at `9f5a9f0b476716b6a6fd0a39aa3cf3041a3a4465`. This is the post-PR #267 mainline. This section supersedes any earlier statement in §§11–38 that describes a different SHA as "current", "latest", "open", "pending", "in progress" or "merged". Earlier sections are retained as chronological evidence records, not silently rewritten into a false continuous snapshot.

### Read this manual correctly

NEX has several different kinds of authority and evidence. Do not collapse them:

1. **Founder-approved governance:** the Master Roadmap v3.0, frozen consolidated S-01–S-25 register and explicitly approved decisions control scope and gates. This manual cannot amend them.
2. **Implementation fact:** current source at a named commit proves what code is present. It does not prove that the behaviour is intended, enabled on a host, or effective.
3. **Test evidence:** a green test run proves only the exact tested commit and test scope shown by that run. It does not prove a different PR head, current main, deployment, live operation or user-visible effect.
4. **PR state:** distinguish open/closed, merged/unmerged, draft/ready, base SHA, head SHA, merge base and exact-head CI. A PR description is a claim, not independent proof of its base or status.
5. **Host/runtime evidence:** process state, service configuration, actual flags, database contents, model digest, devices and live traces remain UNKNOWN unless separately collected with authorization.
6. **Hypothesis / recommendation:** label these explicitly. Never turn a source observation or test fixture into a policy decision.

### Evidence freshness rule

For every substantive claim Claude repeats or changes, record: source path and line/function anchor; exact source commit; test path and exact test result/run ID where applicable; whether evidence is static source, fixture test, CI, host observation or founder approval; known counter-evidence; and last verification date. When main advances, re-check the affected source paths and tests. If not rechecked, label the finding **historical snapshot — revalidation required**, not "current". Never update a date or SHA merely to make a document look fresh.

### Current PR and Gate ledger (verified from GitHub metadata at this update)

| Item | Verified status | Interpretation |
|---|---|---|
| PR #267 | Merged to main as `9f5a9f0b476716b6a6fd0a39aa3cf3041a3a4465` | Documentation/evidence correction only |
| PR #268 | Open, draft; base `9f5a9f0b476716b6a6fd0a39aa3cf3041a3a4465`; head `8b8ffaff27e298ff96dd4a09452ac14067dc4916`; exact-head run `46024945847` in progress at last check | Current-main replay of provenance-erosion pagination; do not call validated or merge until exact-head full-suite completes and behaviour impact is reviewed |
| PR #266 | Open, draft, based on superseded `edb869af154a33cd77df5ad9bdf010d3e6ab06a2` | Superseded by #268; do not treat its CI as validation of #268 |
| PR #259 | Open, unmerged; base `e78773def4549f646257945e5886ec71a7837374`; head `9686fa6da7e835a149f31b516a5ff7a731c3a8b0`; diverged from current main (current main is 5 commits ahead, PR branch 2 commits ahead of the common base) | SurpriseLoop loss-safe delivery proposal is not a current-main replay. It remains Gate 0 HOLD and requires rebase/replay plus fresh exact-head CI after founder approval; do not merge/deploy |
| PR #255 | Closed, unmerged | Older SurpriseLoop attempt; not current implementation evidence |
| PR #261 | Merged | G-70 source/test continuity gap closed; M0.5 acceptance remains open |
| PR #262 | Merged | WarrantPass docstring correction only; no WarrantPass activation |
| PR #265 | Merged | Manual/Claude handoff reconciliation |
| PR #267 | Merged | Corrected evidence snapshot and handoff |
| G-58 | Open — intended goal lifecycle unresolved | Recover V2.1 original and approval before changing `open` / `active` semantics |
| G-69 | Gate 0 HOLD | No SurpriseLoop behaviour-changing merge/deployment |
| G-73/G-74/G-75 | Open | Keep as evidence/lifecycle questions until their specific dispositions are verified |
| Gate 0 | Pending founder review | No Phase 1 authorization |
| Phase 1 | Not authorized | No inference from CI or documentation merges |

**PR #259 ancestry check:** comparing current main to its head yields a diverged graph, not a current-main PR. Its PR body says it replays after #256, but the actual GitHub base SHA remains the earlier #256 merge. Trust the graph metadata, not the prose. The implementation is not on main by virtue of the PR being open.

**PR #268 CI status:** the disposable test image built successfully; the "Verify sandbox and run full baseline suite" step was still running. No final test count or pass/fail conclusion was available at this update. Re-query the exact head SHA and run ID before making a claim.

### Snapshot status of companion evidence documents

- `NEX_REPOSITORY_REALITY_REPORT.md` and `NEX_ARCHITECTURE_CROSSWALK_v2.md` were last audited at `ae406fa8fcb1abdf25cdf4ae1bd65333e1148ca8`. Current main is 44 commits ahead of that source snapshot. Their contents are now **historical orientation**, not a current-main reality certification or fully current architecture map. Revalidate affected source before using their claims. Do not change their source SHA metadata to current without actually repeating their audits.
- The verified defect backlog's header snapshot is now current main for navigation, but individual findings have different evidence dates/SHAs. Each finding retains its own source evidence boundary; revalidate before claiming it is still current.
- Sections 11–38 are preserved as a dated engineering history. Their old PR states, test counts and SHAs are not live status. Use this §39 ledger plus GitHub metadata for current state.

### Instructions to Claude — perform a comprehension check before coding

First, summarize the authority hierarchy and current status above in your own words. Then independently verify, without relying on this prose alone:

1. Resolve the current `main` SHA and compare it with each PR base/head/merge commit.
2. Re-query PR #268's exact-head workflow run; if still running, wait. If failed, inspect logs and repair on the same latest-main base. If passed, inspect the full patch, failure paths, query semantics and undo lineage; do not merge merely because CI is green.
3. Verify PR #259's diverged ancestry and preserve the G-69 Gate 0 hold. Do not rebase it into a mergeable state or change behaviour without founder approval.
4. Re-read GoalManager, CoherenceGate and their tests for G-58. Recover the exact Development Proposal V2.1 and its approval evidence from the founder's available sources; quote clause and page/section references. If unavailable, report **not located** and leave semantics unchanged.
5. Revalidate any reality-report or crosswalk assertion used for a new engineering decision against current source and tests.
6. Report discrepancies between this manual and independent findings before editing. Preserve the frozen S-01–S-25 register and roadmap.

Claude's deliverable should be an evidence table with: claim, source SHA, source anchor, test/run, evidence class, confidence/limitation, contradiction check, and disposition. It should separately list founder decisions required. Do not claim that you have contacted the founder or another model; this repository handoff is an instruction, not a message sent to Claude.

### Next research–development–observation cycle

After the comprehension check, continue with one bounded, authorized issue at a time: inspect → state the hypothesis → seek disconfirming evidence → implement only where authority permits → run focused tests and exact-head full baseline → rescan changed code and callers → record newly exposed dependencies and behavioural consequences → update this manual/backlog/handoff. Stop before any unresolved founder-policy or Gate 0 boundary. A prestigious result is a reproducible, understandable and governable system, not a large change count.


## 40. Current-main revalidation: G-65 and G-76–G-79 (27 November 2026)

**Authoritative source snapshot:** `main` at `90ffd57c75b33eff161ea33e29388e0732f0290e` (post-PR #269, with PRs #270 and #271 already merged). This section supersedes §39 for the current status of the PR sequence below and for the G-65/G-76–G-79 findings. Sections 1–39 remain chronological records; do not reinterpret their former status statements as current.

### Merge and exact-head CI ledger

| Item | Verified repository state | Exact evidence |
|---|---|---|
| PR #269 — manual/evidence reconciliation | Merged as `3e7f0f35ccc58519f57ae4fd2e13b1f688f688a3` | Exact head `493f3e04889df62f33f7d23cf5c81e2f65a596d9`; run `46034624423`: **2,629 passed, 7 skipped, 45 subtests; baseline OK**. Documentation only. |
| PR #270 — BeliefPromoter concurrency | Merged as `d2a5c107019d79276879f3ade6ebefd348686e36` | Run `46032636987`: **2,624 passed, 7 skipped, 45 subtests; baseline OK**. |
| PR #271 — Warrant promotion-history decoding | Merged as `77d4cd89015ebf605c9e5ec6af994a28126f6ed5` | Exact head `c319ae788689c83e52d38f0e6e24cb6ae437805e`; run `46032708456`: **2,629 passed, 7 skipped, 45 subtests; baseline OK**. |
| PR #272 — Expectations `_learn` compare-and-set | **Merged** as `90ffd57c75b33eff161ea33e29388e0732f0290e` | Exact head `67fcf46a84bcfae5b5a309502680fffe8bb347b8`; run `46035516300`: **2,632 passed, 7 skipped, 45 subtests; baseline OK**. The merged commit is now on current main. |

All four changes are present on the stated main snapshot. PR #272's exact-head test passed before its squash merge; its fix is now present on main. The merge sequence and tested trees were checked against their exact commit identities.

### G-65 — Expectations is boot-reachable; prior “no boot invocation” claim superseded

The earlier G-65 activation statement based on main `99ae476` said no boot invocation had been found. That conclusion is superseded by the current source chain:

- `run.py:511–514` starts `SelfPredictionLoop` when `NEX5_SELF_PRED=1`.
- `theory_x/stage_world/self_prediction.py:1149–1154` checks `reconciler_on()` inside `SelfPredictionLoop.tick()` and calls `expectations.reconcile()`.
- `theory_x/stage_world/expectations.py:126–127` reads the `NEX5_RECONCILER` gate; `reconcile()` reaches `_learn()` when `learning_on()` is true.
- The tracked `nex_keepalive.sh:218–219` launch command sets `NEX5_SELF_PRED=1`, `NEX5_RECONCILER=1` and `NEX5_EXPECT_LEARN=1`.

Therefore the Expectations reconcile/learning path is **launcher-armed and boot-reachable in the tracked configuration**. This is source/configuration evidence, not host observation: whether the host currently uses that launcher, whether the process is running, and the effective inherited environment remain **UNKNOWN**. Do not repeat the older “dormant/no boot invocation” conclusion as current.

### G-76 — Provenance erosion advances on reinforcement, not ordinary use (OPEN / founder decision)

- **Sources on this snapshot:** `theory_x/stage3_world_model/erosion.py` (`THRESHOLDS`, `record_use()`, `record_reinforce()`, `_erosion_check()`, `erosion_pass()`); `theory_x/stage3_world_model/promotion.py:118–182`.
- `record_use()` increments `use_count`, then calls `_erosion_check()`. The checker reads and compares `reinforce_count`, not `use_count`. Ordinary use therefore does not itself advance the erosion stage.
- `record_reinforce()` increments `reinforce_count` and invokes the same checker. The reviewed caller inventory found its runtime call at `BeliefPromoter.corroborate()` after a corroboration promotion (`promotion.py:182`). The stage thresholds are 10 for `external`, 30 for `nex_absorbed`, and 80 for `nex_integrated`; `nex_core` has no further threshold.
- The erosion module docstring says “through use and reinforcement”, which overstates the current mechanism. The verified implementation is reinforcement-count driven, with reinforcement currently tied to corroboration promotions. No historical maximum or live population estimate is asserted here.
- **Disposition:** OPEN for founder clarification of intended semantics. Do not silently change the counter, thresholds, stage transitions or confidence bump. No runtime/database state was inspected or changed.

### G-77 — BeliefPromoter stale-transition race (CLOSED by PR #270)

- **Source:** `theory_x/stage3_world_model/promotion.py`; tests: `tests/test_promotion_atomicity.py`.
- `corroborate()` now performs the read, threshold decision and tier/count write in one canonical beliefs-Writer transaction, preventing lost increments and duplicate threshold-crossing promotions. The decay path constrains its write to the snapshot tier, unlocked state and unchanged idle cutoff; decisive contradiction performs its read/decision/write transactionally.
- **Validation:** PR #270 merged as `d2a5c107019d79276879f3ade6ebefd348686e36`; run `46032636987` passed **2,624 tests, 7 skipped, 45 subtests** with baseline OK.
- **Scope:** atomicity and stale-write protection only; corroboration thresholds, promotion/demotion policy and cadence are unchanged.
- **Disposition:** CLOSED on current main.

### G-78 — Warrant survival ignored the stored promotion-history representation (CLOSED by PR #271)

- **Source:** `theory_x/stage_warrant/warrant.py::_promotion_events()` and `_survival()`; tests: `tests/test_warrant_promotion_log_format.py`.
- The producer appends `json.dumps(event)` as SQLite TEXT inside `json_insert`, so real `promotion_log` arrays contain JSON-encoded strings. The prior consumer expected object elements and could therefore fail to interpret actual promotion/decay/contradiction history. The fix decodes both string and object forms, skips malformed individual elements without discarding valid events, and orders decoded events by timestamp.
- Tests cover object/stored-format parity, malformed elements and a row written by the real BeliefPromoter.
- **Validation:** PR #271 merged as `77d4cd89015ebf605c9e5ec6af994a28126f6ed5`; exact-head run `46032708456` passed **2,629 tests, 7 skipped, 45 subtests** with baseline OK.
- **Disposition:** CLOSED on current main.

### G-79 — Expectations learning could overwrite a concurrent confidence change (CLOSED by PR #272)

- **Original source defect (main `3e7f0f3`, before PR #272):** `theory_x/stage_world/expectations.py::_learn()` read confidence and later issued an unconditional absolute update. A competing writer between those operations could be overwritten, while the learning log recorded a stale `before` value; a belief locked after the read could also be changed.
- **Fix merged in PR #272 as `90ffd57c75b33eff161ea33e29388e0732f0290e`:** compare-and-set update constrained by belief ID, the confidence value read, and `COALESCE(locked, 0)=0`; retry/re-read/re-decide at most three times. Deleted or newly locked rows are left alone; persistent contention is bounded and not logged as an applied transition. Learning-log entries are emitted only for transitions that actually applied. The factor, clamps, cap policy and existing beliefs-before-conversations commit ordering are preserved; no cross-database atomicity is claimed.
- **Tests:** three race regressions fail on unmodified main for the intended reasons; mutation checks show the confidence guard, lock guard and retry are each detected. The focused local suites passed 154 tests after the fix (the original implementation left the three new race tests failing).
- **Exact-head CI:** PR #272 head `67fcf46a84bcfae5b5a309502680fffe8bb347b8`, run `46035516300`: **2,632 passed, 7 skipped, 45 subtests; baseline OK**. The tested head was squash-merged as `90ffd57c75b33eff161ea33e29388e0732f0290e`.
- **Practical activation qualification:** the `_learn()` path is boot-reachable under the tracked launcher (see corrected G-65). The competing writers are not all currently armed by that launcher: the learning-guard subtraction flags are absent, `revert_subtraction()` has no runtime caller, and erosion's confidence bump occurs only on a stage advance (see G-76). Thus this is preventive persistence/ledger hardening, not evidence of an observed live race. Host-effective state remains UNKNOWN.
- **Disposition:** CLOSED on current main by PR #272. No new flags were enabled and no live state was touched.

### Current boundary and next decision

- Gate 0 remains pending founder review; Phase 1 remains unauthorized. G-69 / PR #259 remains an explicit Gate 0 HOLD and must not be merged or deployed.
- The frozen consolidated S-01–S-25 register and Master Roadmap are unchanged. This section records implementation/evidence facts; it does not decide the G-76 policy question or authorize runtime activation.
- PR #272 has been reviewed and merged after exact-head CI passed. Next engineering decision: obtain founder clarification on whether provenance erosion is intentionally reinforcement-only or should include ordinary use. Keep host/runtime evidence UNKNOWN until collected through the authorized Phase 0 process.


## 41. Post-#274 merge verification and MIND_MAP freshness recheck (27 November 2026)

**Current main:** `e4f439e6aef4383795ccc7e3e29b1d242ed0f98c`. PR #274 was squash-merged after exact-head CI passed on `3487a300ebfcb59e7e1d2b5d995d265eb2705814` (run `46037202834`): **2,632 passed, 7 skipped, 45 subtests; [baseline] OK**. The sandbox probe passed. The four documentation files were re-fetched from main after merge, and the plain-text manual body remains byte-identical to this INDEX.

### MIND_MAP verifier status

The same exact-head CI run executed `python mind_map/mind_map.py --check --verify` and reported:

- **30 nodes, 0 unverified, 14 dark, 2 blocked.**
- **No STALE source-drift warnings** were emitted.
- Two missing doctrine references remain: `VIRTUE_SLATE.md` and `mental_factors_inventory_alobha_spec.txt`.
- The `p13_finitude` `UNBLOCK 2026-11-21` marker remains past due.

This resolves the stale-source component of backlog E-05. The residual missing-source warnings remain governed by D-03; do not fabricate or silently remove the missing doctrine references. The P13 marker is deliberately retained as a warning, not authorization to rearm the chat workspace. The 14 dark and 2 blocked counts are node-state descriptors, not test failures or permission to activate features.

### Boundary

PR #274 changed documentation/evidence only. No MIND_MAP nodes, doctrine files, runtime flags, live databases, frozen S-01–S-25 specification, Master Roadmap, Gate 0 decision or Phase 1 authorization changed. Gate 0 remains pending founder review; G-69 / PR #259 remains HOLD.


## 42. Phase 0 system research continuation (27 November 2026)

**Research evidence snapshot:** `14873c10673760b8adbbf6fb0076226d1c97ffa4` (before PR #279). Current main additionally includes PR #279 at `8d2121d121931d37afcb1c3d23d27e7ccc9145d1` and PR #280 at `f03a3d2e7b9c71801e44be73cf728c01cb791c9d`. The selected-path research report is `NEX_PHASE0_SYSTEM_RESEARCH_2026-11-27.md`.

PR #275's mind-map freshness update, PR #276's RDO generated-cycle exclusion and PR #277's keepalive path portability fix are merged. Their exact-head full baselines passed respectively at 2,632, 2,634 and 2,636 passed tests (7 skipped, 45 subtests; baseline OK). PR #276 also has a passing post-merge main run. PR #277 preserves current main's `MOLTBOOK_DRY_RUN=1`. PR #279 moves the scheduled prose-statistics rebuild onto the shared beliefs Writer/Reader path; exact-head run `46044361663` passed 2,638 tests, 7 skipped, 45 subtests, baseline OK. Post-merge main run `46045384807` also passed 2,638. PR #280 hardens Writer shutdown/submission ordering; exact-head run `46045754339` passed 2,640 tests, 7 skipped, 45 subtests, baseline OK. It is merged as `f03a3d2e7b9c71801e44be73cf728c01cb791c9d`; post-merge main CI is in progress.

### Current source research

- G-80: reanimation is marked in SQLite before the pending handoff is durably delivered; a process loss can strand a reanimated row.
- G-81: Fountain's total-fire counter and ClockRunner's notified-fire counter count different event populations.
- G-82 is folded into G-73: the same oldest 50 dormancy rows are reselected on each scan, starving later rows; ClockRunner and DiversityLoop own separate scanners. `wake_one()` also lacks final eligibility filters. Old PR #102/#145 proposals are not current-main fixes.
- G-83: Metacognition can re-emit the same unacknowledged groove alert on successive Chat turns, while stillness counts event rows.
- G-84: shutdown still does not quiesce or join all producers before closing Writers; PR #280 fixes the Writer late-submit/timeout race, but the application-level producer shutdown gap remains.
- G-85: SignalToProblem's primary signal-to-problem tick remains a direct-write, split-commit path across two databases. PR #279 migrated the separate hourly prose-statistics rebuild to the shared Writer/Reader; the primary G-61 persistence gap remains open.
- G-86: SignalReaper's preservation allowlist has drifted from SignalToProblem's current promotable types.
- G-87: Moltbook dry-run suppresses non-GET requests but still reads remotely and can persist simulated sends as real `posted`/`sent` states.
- G-88 is closed by PR #277 (keepalive path portability); host service identity remains unknown.
- G-89 is closed by PR #276 (RDO generated `.cycles` records excluded from source-evidence searches).
- G-90: social silence is not yet modeled as a contextual social act; response latency and internal stillness mechanisms are not substitutes.

The RDO capability boundary and version-precedence questions are recorded in the research report. It remains an external advisory tool, not part of NEX runtime; its current objective intake requires externally supplied seed obligations and reconciliation signatures.

### Validation and limits

The latest mind-map CI check reports 30 nodes, 0 unverified, 14 dark, 2 blocked, no stale-source warnings, two missing doctrine references and the overdue P13 marker. PR #279 closes only the auxiliary prose-statistics direct-write path; SignalToProblem's primary cross-database signal/problem transaction remains open under G-85/G-61. PR #280 fixes the shared Writer lifecycle subproblem, not the missing global shutdown coordinator. No runtime, host service, live database or external API was inspected. No cognitive policy, feature flag, MIND_MAP node, frozen S-01–S-25 register, Master Roadmap or Gate 0 decision changed. Gate 0 remains pending; Phase 1 remains unauthorized.


### G-91 — RDO objective context is stored but not yet enforced

The intake preserves intent, scope, constraints, exclusions and acceptance criteria, but the current cycle runner receives only the original text, assumptions, caller-supplied seed obligations/relationships/signatures and expansion depth. Those other fields are not translated into plan obligations or checked against proposed work packages. RDO remains advisory; this is a capability gap, not an execution incident. See the Phase 0 research report and verified backlog.


### RDO v1.4 implementation audit

The current RDO has a working Extrapolator vertical slice, graph intelligence and partial OFT, but not the full v1.4 Interface Tension Profile, performance margins, capacity/headroom, operating envelopes, Pareto/net-value assessment or all twelve adversarial cases. See [RDO v1.4 implementation gap audit](rdo/RDO_V1_4_IMPLEMENTATION_GAP_AUDIT_2026-11-27.md). v1.4 is the working basis; v1.3 is historical.


## 43. RDO and Watcher mainline development update — 28 November 2026

### Merged implementation

The following bounded changes are now on `main`:

- **PR #341 — directed-cycle identity:** Watcher now preserves distinct directed feedback-cycle paths and produces deterministic cycle ordering rather than collapsing cycles by node membership alone.
- **PR #342 — ledger consistency:** Watcher validates evidence-reference containers and does not advance in-memory ledger state until the append has succeeded.
- **PR #339 — observed failure evidence:** RDO can preserve a typed, measured failure observation against an exact dependency relationship, including both canonical graph endpoints, observation window, operating-envelope context and evidence provenance. This remains distinct from structural failure-path candidates.
- **PR #343 — context review workflow:** Stage 7 now records digest-bound, append-only context-mapping and acceptance-criterion review events in its existing decision ledger. The independent Watcher verifier validates these event types against the immutable handoff manifest and event history.

The earlier #338 evidence-reference guard and #340 typed UNKNOWN-first objective-context records remain part of the same foundation. These changes are advisory/planning/evidence work; they do not enable NEX runtime execution, modify runtime flags, deploy code or promote cloud evidence into host observations.

### Verification evidence

Exact-head full-suite CI passed for the two larger new slices:

- **PR #339:** 2,819 passed, 7 skipped, 45 subtests passed. The mind-map verification completed with 30 nodes and 0 unverified nodes.
- **PR #343:** 2,812 passed, 7 skipped, 45 subtests passed. The mind-map verification completed with 30 nodes and 0 unverified nodes.

The mind-map check still reports existing warnings for missing doctrine source files `VIRTUE_SLATE.md` and `mental_factors_inventory_alobha_spec.txt`, plus the overdue P13 finitude unblock. These warnings were not introduced by these PRs and were not treated as successful completion of those doctrine tasks. Post-merge mainline CI for the combined tree is tracked separately.

### Integrity and authority boundaries

- Original planning fields and the handoff manifest are not rewritten. Observed failure evidence is appended to the CycleRecord's trailing `observed_failure_evidence` field; context mappings and criterion reviews are appended to the separate handoff event ledger.
- Handoff review events are bound to the exact manifest digest and hash chain.
- Reviewer/verifier attribution is caller-supplied and explicitly not identity-authenticated.
- Context mapping requires canonical obligation keys from the exact handoff. Criterion verification requires a prior reviewed mapping; the append re-checks that mapping under the ledger lock.
- A pending criterion has no verifier, confidence or verification timestamp. Passed, failed and not-applicable outcomes require evidence references, verifier attribution, confidence and a timezone-aware timestamp.
- Criterion verification is not overall human acceptance. The Watcher continues to report test verification as not authorized and runtime observation as host-only UNKNOWN unless independent host evidence exists.
- No frozen S-01–S-25/M1.8 specification content was changed.

### Stage-2 clarification — already implemented and regression-tested

The earlier suggestion to rerun the Stage-2 belief-development slice as an open task is superseded by the current repository evidence. `rdo/STAGE2_EXTRAPOLATOR_MVP.md` documents the belief-decay objective and its reuse of the existing Extrapolator, reconciler and CycleStore. `rdo/tests/test_stage2_extrapolator_mvp.py` includes a fresh Python subprocess that reloads the persisted cycle and checks its counts, frontier and native-planning kind. It also checks that fixture reviews do not write reusable patterns without an authorised review. The #339 and #343 exact-head full-suite runs passed this test suite.

This is isolated repository/test-store verification, not a live belief-database or host-runtime claim. Preserve the Stage-2 regression as a baseline; do not duplicate its implementation.

### Updated gap assessment

**G-91 — objective-context evidence resolution (partially closed).** Typed context requirements existed in #340. PR #343 adds a structured, caller-attributed mapping and criterion-review workflow, and the independent Watcher now validates it. Remaining gaps: mappings are still human-supplied; evidence references are not dereferenced or independently authenticated; mappings do not automatically generate new obligations or feed a subsequent planning cycle; and no execution authority is implied.

**G-92 — first-level decomposition and novel-kind rule development (open).** The repository's objective intake requires externally supplied seed obligations, and `run_cycle` begins from those seeds. The Extrapolator uses a finite static rule catalogue; a novel obligation kind is surfaced at the frontier when no rule exists. PatternMemory records applicable lessons and disconfirmations, but it does not create or promote executable expansion rules. Consequently, the repository provides recursive expansion of a supplied seed graph, not a self-contained raw-idea-to-complete-build decomposer. The external LLM/human seed-proposal boundary is explicit and can be used by ChatGPT, but it is not an integrated provider.

The next safe capability is a provider-neutral candidate-seed and candidate-rule proposal lifecycle: preserve alternative interpretations, assumptions, evidence needs, applicability, exceptions, disconfirmations, provenance and tests; require review/approval before a candidate rule enters the active versioned catalogue; never promote a rule solely because a pattern appeared repeatedly.

**G-93 — feedback-loop measurement/review update path (open).** `assess_system` already creates a `FeedbackLoopAssessment` for each detected influence cycle, serializes it into `TensionAssessment.dimensions.feedback_loop_assessments`, and persists it within `CycleRecord.tension`. Topology and UNKNOWN-first stability placeholders are therefore already preserved. Missing: a traceable way to append measured dimensions and independently reviewed stability evidence to that existing record; no CLI/API path currently accepts those updates. It does not calculate stability, gain, damping or thresholds. Next: add an evidence-bound update path that preserves original topology, validates measurement evidence/provenance, and leaves stability UNKNOWN unless a separately reviewed assessment is supported. Do not invent thresholds or stability verdicts.

### Next bounded development sequence

1. Confirm the post-merge mainline CI run for the combined #339/#343 tree.
2. Build a traceable end-to-end single-objective case: original idea and externally supplied seed proposal → objective intake → recursive expansion → context mapping → criterion verification → Stage-7 handoff → independent Watcher verification. Keep planning review distinct from execution and acceptance.
3. Design the candidate expansion-rule proposal/approval lifecycle for novel kinds, preserving disconfirming evidence and preventing automatic promotion.
4. Integrate FeedbackLoopAssessment into CycleRecord with legacy-load compatibility, UNKNOWN-first defaults and measured-evidence validation; do not calculate ungrounded stability scores.
5. Preserve the already implemented Stage-2 belief-development and fresh-process CycleStore-resume tests as regression baseline; focus next on novel-kind rule proposals and the raw-idea-to-handoff boundary rather than rebuilding Stage 2.

This update records implementation evidence and remaining capability boundaries; it does not amend the frozen specification/register.


## 44. One-pen census, G-78 validation consequence and persistence corrections (28 November 2026)

**Evidence snapshot:** `main` at `60cc178ba1f3c895651c86ad95345c98fd5a2198`. Source and fixture-test evidence only; host and runtime state remains **UNKNOWN**.

### One-pen census (G-61)

`tools/one_pen_census.py` is a read-only static scan, run with `python tools/one_pen_census.py`. It lists every write-capable `connect()` call site outside `substrate/` and the tests, and classifies each by write SQL in the enclosing function, by whether the connection is handed off, and by whether it is runtime code or a script. It found 112 sites:

- **Pre-merge baseline at `a6d08405`:** `signal_to_problem_tick()` was the only boot-reachable direct writer to the six substrate databases; PR #347 has since corrected that path. The census must be rerun on current main before making a current-count or reachability claim.
- **Documented exception:** `strikes/catalogue.py` writes its separate `strikes_catalogue.db` directly, by design. The open governance question is whether SPECIFICATION.md §8 should also cover non-substrate databases.
- **Present but not reachable at boot:** `groove_breaker`, `value_drift_monitor`, the `genius_provenance_tag`/`source_identity` backfills, `prose_stats.build_direct`, a `hot_observer` demo, and 10 script or tool sites.
- **Read through a non-read-only connection:** 68 runtime sites. Another 7 hand their connection off, and all of those were traced to readers except the strikes catalogue. This is hygiene, not a one-pen write.

The scan is a heuristic over source text, so its limits are recorded in backlog G-61. `tests/test_one_pen_census.py` pins the classification rules and the documented exception.

### G-78 consequence

`warrant_validate` gates on the composite warrant, of which survival is 35%. Before PR #271, survival ignored promotion history. Every earlier `warrant_validate` verdict therefore rests on history-free survival, including the failed gate that G-75 refers to.

A read-only host re-run needs founder authorisation.

### Merged persistence corrections (exact-head CI green before merge)

- **PR #347 — G-85: SignalToProblem one-pen, recoverable two-file order.** Merged as `8d6bc95d387687ed470713467d8779d09479e11d`.
  - Exact head `f84e1ada956386945bc7aaaa83ec30d6c3c3bf12`, run `46089697232`: 2,841 passed, 7 skipped, 45 subtests; baseline OK.
- **PR #348 — G-84 step 1: `AppState.close()` quiesces the dynamic loops before the Writers close.** Merged as `321a156e162a6554e27ae329522f253e8f6fe676`.
  - It also re-verifies the mind-map nodes that cite `gui/server.py` and corrects their already-drifted line anchors.
  - Exact head `fa4ea8d40c3beccd816bb12d0279db35d973e784`, run `46091039346`: 2,838 passed, 7 skipped, 45 subtests; baseline OK; no STALE warnings.

### Founder decisions required (no action taken)

1. **G-80:** should reanimation delivery be at-most-once or recoverable? The backlog requires this choice before any outbox or retry design.
2. **G-78:** may `tools/warrant_validate.py` be re-run, read-only, on host data?
3. **G-76:** is provenance erosion meant to be reachable, including whether `use_count` should count?
4. **G-61:** does the one-pen rule extend to non-substrate databases such as `strikes_catalogue.db`?

Gate 0 remains pending and Phase 1 is not authorised. G-69/#259 stays on HOLD. G-58 is unchanged.



## 45. Feedback-loop evidence update path — G-93 (28 November 2026)

**Evidence snapshot:** merged main commit `6f12f403e13b94a4b019aa666abac448b8a9a62d` (PR #357). Exact-head sandbox run `46101032854`.

### Merged capability

- `FeedbackLoopAssessment` remains UNKNOWN-first. Any dimension marked `measured` must now carry a finite numeric value, a unit, traceable evidence references and a confidence label.
- `FeedbackLoopEvidenceStore` records measurement and stability-review events in a separate append-only, hash-chained JSONL ledger.
- Every event is bound to the existing feedback-loop ID, members and directed relationships. Replay refuses to apply evidence if the loop topology has changed.
- Measurement and stability review remain separate. A measurement never calculates stability. A new measurement after a review resets the current verdict to UNKNOWN until another explicit review is recorded.
- A non-UNKNOWN stability state requires an explicit review with caller-attributed reviewer, source reference, assessment evidence and confidence. The local ledger does not authenticate reviewer identity.
- Event history is also persisted in the trailing, legacy-compatible `CycleRecord.feedback_loop_evidence_events` field. `feedback-replay` recovers a cycle snapshot if a ledger append succeeds but snapshot persistence does not.
- CLI commands: `feedback-measure`, `feedback-review`, `feedback-replay`.
- Operator guide: `rdo/FEEDBACK_LOOP_EVIDENCE.md`.

### Exact-head verification

- Full sandbox suite: **2,864 passed, 7 skipped, 45 subtests passed**.
- Mind-map verification: **30 nodes, 0 unverified**. Existing warnings remain for missing `VIRTUE_SLATE.md`, missing `mental_factors_inventory_alobha_spec.txt`, and overdue P13 finitude unblock; 14 dark and 2 blocked nodes are existing map status, not new unverified nodes.
- The sandbox probe confirmed unprivileged execution, no capabilities/credentials, read-only source, disposable data/tmpfs and no outbound network.

### Gap status and boundary

**G-93 update-path gap: closed.** The repository can now append measured dimensions and separately reviewed stability evidence to the existing CycleRecord while preserving topology and history. This does **not** implement calibrated stability, gain, damping, oscillation thresholds, causal propagation or automatic stability verdicts. Those remain UNKNOWN/unevaluated until exact v1.4 criteria and grounded measurements are available.

**G-92: partially closed.** PR #352 already merged the provider-neutral, hash-chained candidate-rule proposal lifecycle. Its `approved_for_catalogue` state remains deliberately inert: no dynamic activation, no automatic promotion and no changes to `EXPANSION_RULES`. The remaining raw-idea-to-handoff gap is the provider-neutral candidate-seed proposal and approval path; objective intake still requires externally supplied seed obligations.

### Next bounded development

Design the raw-idea → candidate-seed alternatives → explicit human review → objective.v1 intake → recursive expansion → Stage-7 handoff lineage. Bind each candidate to the exact raw objective revision; preserve competing interpretations, assumptions, evidence needs, acceptance-criterion coverage, disconfirming cases and provenance. Do not run planning from an unreviewed external-LLM seed proposal, and do not make the candidate-rule ledger an active rule loader.

No frozen S-01–S-25/M1.8 specification content, NEX runtime, protected experiment, deployment path, Gate 0 or Phase 1 authority was changed.


## 46. Cognitive network interaction trace — attention, affect, drives and workspace (28 November 2026)

**Evidence snapshot:** source files on `main` at `bbca5deb3a0398331503ce61c95a62f8d1b3d33d`. This is a source-level connection trace, not host/runtime telemetry. The exact source-file SHAs and detailed edge register are recorded in `research/SENTIENCE_5_5_COGNITIVE_WIRE_TRACE_2026-11-28.md`.

### The network is already more connected than a list of faculties

The current source contains several distinct interaction paths. They should be understood as a network of bounded influences, not collapsed into a single “mind” score or assumed to share one control loop.

**1. External sensing → attention → branch state → thought selection**

- Stage 2's A–F pipeline receives sense events, matches streams and payloads to cognitive branches, computes magnitude, applies the membrane aperture, derives a valence label, and calls `BonsaiTree.attend()`.
- Bonsai maintains branch-specific focus and texture. Fountain reads branch focus and uses it in branch selection; it also reads branch focus as one candidate in Global Workspace arbitration.
- The attention matcher contains direct stream-to-branch mappings and content/keyword matching. The magnitude function explicitly returns zero for `internal.*` telemetry. This is an intentional separation: internal machine telemetry must not pin the `systems` branch and starve other branches. It is not evidence that internal telemetry is unused everywhere; SelfModel still reads selected internal streams for self-representation.
- This creates a concrete distinction between *self-monitoring* and *attention steering*. A signal may describe the system without being allowed to steer its cognitive focus.

**2. Affect → selection and language (two different consumers)**

- `AffectState` is constructed and its background loop is started from `run.py`. It reads substrate-derived valence/arousal inputs and flagged surprise events, integrates and decays state, then persists the affect row and affect history.
- Chat has a separate path that appends `AffectState.format_for_prompt()` to assembled belief/context text when the AppState faculty is present.
- Fountain's `_valence_reach()` reads the persisted valence/arousal pair and can scale the novelty term in item selection. That mechanical influence is gated by `NEX5_VALENCE_DRIVE=1`; the source default is OFF. It is bounded and returns neutral multiplier 1.0 in the strongly negative anti-rut zone.
- Fountain's explicit compositional-mood language injection is separately gated by `NEX5_MOOD=1`. Therefore affect can have a Chat representation while its Fountain selection influence and Fountain mood narration remain separately controlled. Do not treat these as one wire.

**3. Competing drives → selection pressure, framing inputs and prompt representation**

- `CompetingDrives` is constructed and started from `run.py`; its state is computed from several measured substrate features and persisted.
- Fountain reads curiosity and exploration weights to scale its candidate scoring, and separately appends the competing-drive tension block when the faculty is available.
- The Global Workspace's optional drive candidate is supplied from `DriveEmergence.format_for_prompt()`, not from the CompetingDrives object. Those are distinct drive mechanisms and must not be conflated because both contain “drive” in their names.
- Fountain also records the current CompetingDrives weights into its per-fire snapshot where available and links activation records to resulting fountain events. This provides a traceable relationship, but does not itself prove the drive weights improved selection.

**4. Global Workspace → Fountain framing versus Chat block selection**

- Fountain's `NEX5_GLOBAL_WORKSPACE` path defaults to enabled in source. It compares available surprise, momentum, Bonsai-attention, stakes and DriveEmergence candidates, then prepends the winning frame to the focus block. The other faculty blocks are still appended; this is a leading frame, not exclusive selection of all cognitive content.
- Chat's `NEX5_CHAT_WORKSPACE` is a different mechanism. When enabled, it performs salience-ranked, character-budget admission of candidate faculty blocks while preserving their original assembly order and exempt blocks. It is not the same winner-takes-frame operation used by Fountain.
- The two workspaces therefore arbitrate at different levels: one chooses a leading frame for an internally generated thought; the other decides which already-assembled Chat context blocks fit a budget.

### Interaction consequences and open questions

1. **The same upstream signal can have multiple downstream effects.** Surprise can contribute to AffectState arousal and also appear as a Global Workspace candidate. These are parallel consequences with different timing and semantics, not one shared score.
2. **A faculty can be present and active without its strongest influence being enabled.** AffectState background computation and Chat injection do not imply that Fountain's valence-driven selection or mood narration is enabled.
3. **A shared name does not establish a shared mechanism.** DriveEmergence, CompetingDrives and the Global Workspace drive candidate are separate components with different data and call paths.
4. **The network has intentional exclusions.** Internal telemetry is excluded from Bonsai attention after a documented focus-pinning defect. Reconnecting that edge indiscriminately would risk recreating the starvation failure.
5. **Prompt contribution and behavioural steering are different effects.** A block may be described to the language model without mechanically changing branch selection; a numeric influence may change selection without being narrated. Both require separate measurements.
6. **The next test should measure a bounded perturbation across layers.** Use isolated fixtures to alter one external sense event, observe A–F magnitude and Bonsai focus, then observe whether Fountain's branch candidate and workspace frame change. Repeat with an `internal.*` event as a negative control. Do not alter live flags or runtime data.

### Current disposition

This trace is source-verified and hypothesis-generating. It identifies several existing connections and important non-connections; it does not yet establish runtime liveness, beneficial cognitive effect, or a unified integrated subject. No new node or runtime wire was added. A test-only characterization has now been added to `tests/test_dynamic.py`: an external `ai_research.arxiv` event must increase that branch's Bonsai focus and texture, while an `internal.proprioception` event is confirmed to match the systems branch but produce zero magnitude, no focus/texture change and no Stage-2 F-step event. This strengthens the previously weak internal-event assertion and adds a positive control. Exact-head CI is pending; no pass is claimed. The test currently establishes the Stage-2 pipeline → Bonsai edge only. Fountain branch selection and workspace framing remain the next separate test seam.

No frozen S-01–S-25/M1.8 specification content, Master Roadmap, M0/M1 gate, mind-map policy, live runtime flag, service or database was changed.

## 47. Self-binding shared-Writer correction — G-94 (28 November 2026)

**Evidence snapshot:** `main` at `bbca5deb3a0398331503ce61c95a62f8d1b3d33d`. Implementation is proposed on draft PR #362; exact-head CI is pending.

### Source-traced defect

The recursive self-reading and periodic self-view snapshot both had access to the canonical AppState `dynamic` Writer, but omitted it when invoking self-binding:

- Fountain called `recursive_self.format_for_prompt()` without a Writer. That function called `perturbation()`, which called `_bound_state()`; the helper already supported `dynamic_writer`, but the live call chain did not pass it.
- SelfMindView's `_snapshot()` called `self_binding.bind()` without passing its existing `self._dw`.
- With no injected Writer, `self_binding.bind()` and its schema helper open their own `Writer` for `dynamic.db`.

This contradicted the one-canonical-Writer-per-database invariant in §4. It was not a database-schema defect or evidence of corruption; it was a source-level ownership violation on two runtime call paths.

### Bounded correction on PR #362

- Fountain now passes `self._dynamic_writer` through `recursive_self.format_for_prompt(dynamic_writer=...)` → `perturbation(dynamic_writer=...)` → `_bound_state(dynamic_writer=...)` → `self_binding.bind(dynamic_writer=...)`.
- SelfMindView now passes its existing `self._dw` into `self_binding.bind()`.
- The optional self-owned Writer fallback remains available for standalone/CLI use; runtime call sites use the shared Writer.
- Regression coverage now asserts that the recursive prompt path carries the injected Writer, and that SelfMindView snapshotting succeeds while opening a second `self_binding.Writer` is forced to fail.
- The existing direct injected-Writer test in `tests/test_self_state_history.py` remains in place.

### Wider self-integration trace and unresolved edges

The Writer correction preserves an existing multi-faculty path:

`compositional emotion + rāga + competing-drive state + latest Fountain thought/readiness + open problem + proprioceptive substrate` → `self_binding.bind()` → `self_state` and append-only `self_state_history`.

Two consumers then use related but distinct aspects of this state:

- Fountain's recursive-self path rebinds on the thought-generation path, reads the resulting components and turns selected emotion/rāga patterns into a first-person prompt nudge. It does not directly write Bonsai focus or mechanically select a new branch; the intended behavioural influence is through the prompt.
- SelfMindView's 300-second snapshot captures the bound synthesis in `self_mind_snapshots.bound_self_synthesis`. Its separate `current_summary()` recomputes beliefs, intentions, knowledge, uncertainty and attention for Chat. `run.py` also injects SelfMindView into Metacognition; Metacognition reads its attention and uncertainty histories to detect recurring attention themes and unresolved-problem stagnation, records those as metacognitive events, and can surface the recent event as prompt text.

This is a genuine chain of connected representations and consumers, but the prompt-mediated feedback should not be mistaken for a measured change in selection or attention.

**Unresolved semantic edges (not changed in this PR):**

1. `self_binding.bind()` currently assigns `drift = "clean"` as a placeholder. At the base snapshot, the nearby comment claimed the binder read the last logged verdict, but the inspected function contained no such read. This PR corrects that misleading comment; the persisted value remains `clean` for compatibility and is still not a measured value-drift result. The field is not included in the returned `components` or synthesis.
2. The binder's attention input is the latest Fountain thought/readiness plus the newest open problem. It does not read the live Bonsai focus vector or identify the current hottest branch. That may be a deliberate narrow definition, but it is not a complete representation of Stage-2 attention.
3. The recursive perturbation currently consumes rāga and emotion (plus the named attending text); drive, readiness and substrate tone are bound but do not directly participate in its nudge rules. Their presence in the unified record does not prove they influence the recursive loop.
4. SelfMindView's Chat summary is recomputed from its five live aspects and is not the same object as the last persisted `bound_self_synthesis`. The snapshot and conversational summary are parallel views, not one shared narrative.

These are candidates for further source tracing and controlled experiments. No extra faculty or behavioural wire should be added until the intended semantics, consumers and effects are clear.

### Validation and boundary

**G-94 is corrected in the PR branch, pending exact-head full-suite CI and review.** No pass count is claimed until that run completes. The changes do not alter self-binding content, faculty semantics, prompt text, selection weights, feature flags, database schema or history shape. No live service or database was accessed.

This is a persistence-ownership correction that preserves the existing cognitive connections. It does not add a new faculty or claim that the recursive self-reading nudge produces a beneficial attention change. Gate 0 and Phase 1 authority remain unchanged.

## 48. RDO candidate seed proposal lifecycle — G-92 first increment (28 November 2026)

**Evidence snapshot:** `main` at `bbca5deb3a0398331503ce61c95a62f8d1b3d33d`. Implementation is on draft-review candidate PR #360; exact-head CI is being rerun after correcting the self-assessment count for the new adapter.

### What this increment adds

The new provider-neutral `rdo_adapters.seed_proposals` boundary preserves the user's raw objective revision and allows multiple competing seed-graph interpretations to be submitted as candidates. Each proposal binds the exact canonical raw-objective snapshot and SHA-256 digest, and carries seed obligations, typed relationships, acceptance-criterion coverage (each criterion must map to at least one declared seed obligation), assumptions, constraints, exclusions, open questions, disconfirming cases and evidence needs.

External-LLM-derived seed confidence must remain explicitly `inferred`; human-authored seed confidence may be `stated`. Approval requires an explicit review decision selecting exactly one existing alternative. A candidate is not an approved objective, and approval does not itself execute anything.

### Integrity and authority boundaries

- Proposal/review events are stored in an append-only, sequence-numbered, SHA-256-linked JSONL ledger with duplicate-key rejection, event/byte bounds, file locking, fsync, and symlink rejection for the ledger path.
- Raw-objective revisions are linked to the exact previous digest; original wording and intent remain immutable across revisions.
- Review decisions cannot be overwritten; a revised candidate must explicitly supersede a changes-requested or rejected proposal.
- The only approval retrieval is an explicit `approved_selection()` call. It returns the selected existing alternative and exact raw-objective lineage.
- This increment does **not** submit to `objective.v1`, run recursive expansion, create a Stage-7 handoff, execute generated code, load rules, activate policy, or change NEX runtime state.

### Validation and next work

The first exact-head CI exposed one stale self-assessment expectation: RDO correctly discovers a fourth boundary adapter after `seed_proposals.py` was added, while the existing test still expected three. The branch now updates that assertion and explicitly checks for `seed_proposals.py`. A second review found that a coverage record could name zero obligations; the validator now rejects empty obligation lists and a regression test covers it. The new exact-head full-suite CI is pending; no pass count is claimed.

The Python API and lifecycle are documented in `rdo/SEED_PROPOSAL_LIFECYCLE.md` and `rdo/README.md`; there is no CLI or GUI in this increment. The validator does not yet classify graph cycles or derive build order. The next bounded increment is a reviewed-selection-to-objective-intake bridge that preserves the raw-objective hash and selected proposal/alternative identity, and adapts validated proposal edges into the existing `Relationship` model and reuses `rdo.tension._find_cycles`, `_classify_cycle`, `assess_system` and `rdo.graph` SCC machinery to distinguish prerequisite cycles, influence feedback loops and unknown cases. It must not run planning or Stage-7 handoff until the separate authority and evidence conditions are satisfied.

No frozen S-01–S-25/M1.8 specification content, Master Roadmap, Gate 0, Phase 1 authority, live NEX runtime, database or feature flag was changed.


## 49. Active producer cooperative shutdown sweep — validation checkpoint (28 November 2026)

**Evidence snapshot:** mainline source through `55fd635bd535d15ece3e3878bf1e71621f56fa7c`; combined implementation and regression coverage on draft PR #413. The PR branch received a test-harness correction at commit `14c5e2ae6cab7aad7d12caf30bd5fe10f5a594eb`. Exact-head full-suite CI, baseline verification and mind-map verification remain required; no pass is claimed here.

### Scope now covered by the combined candidate

The shutdown sweep adds cooperative stop checkpoints to active producer paths and deterministic Event-based regressions across Counterfactual, AffectState, SelfMindView, PredictiveSubstrate, GeniusTagger, DriveEmergence, CompetingDrives/Fountain, NovelAssociation, SubstrateHarmonic, DiversityLoop, EdgeGenerator, WarrantRecorder, SelfMaintainShadow, SpeechQueueConsumer, SignalLoop and decoder transaction boundaries.

The intended invariant is narrow: once a producer observes its stop Event, it should not begin another expensive read/compute/write unit or a later independent side effect. Existing synchronous operations already entered are allowed to return; model/TTS calls and playback already underway are not forcibly cancelled. Paired logical writes are allowed to finish once started where splitting them would create a worse partial state. This is cooperative quiescence, not transactional cancellation.

### Test-harness correction

The isolated Warrant shutdown regression had been appended below an earlier `if __name__ == "__main__": unittest.main()` guard. Pytest discovery would still collect it, but direct execution of the test module would invoke unittest before the appended class was defined. The guard is now moved to the end of `tests/test_warrant_recorder.py` on the PR branch, so both discovery and direct module execution include the shutdown regression.

### Improvement questions and remaining boundaries

1. A stop Event check is not atomically coupled to a later Writer submission: a producer can observe the pre-stop state, then submit after the stop request but before AppState reaches Writer.close(). The Writer itself does have a separate lifecycle lock that atomically orders accepted submissions before its shutdown sentinel and rejects submissions after close admission shuts. Such a late-but-accepted request is drained; if a producer outlives its join budget, later submissions fail and shutdown must remain unclean. This distinction is important: the remaining question is stop-to-submit admission semantics, not an unprotected Writer-close/sentinel race.
2. A blocked synchronous Reader/Writer, embedding/model/TTS call or playback call can outlive the cooperative checkpoint. The producer join timeout and subsequent Writer close ordering therefore need separate lifecycle evidence; an Event alone cannot prove all work has quiesced.
3. Detached route workers and any producer not registered with AppState require a complete ownership census. Thread creation, registration, stop, join and resource ownership must be traced together.
4. Tests should distinguish “stop requested”, “stop observed”, “no new operation admitted”, “in-flight operation returned”, and “resource safely closed”. A clean thread join is not evidence that every detached or unregistered worker was included.
5. Preserve historical direct-call signatures when introducing optional stop Events; test both worker-driven stop-aware calls and standalone callers.

### Validation and authority boundary

PR #413 remains a candidate pending fresh exact-head full-suite CI, baseline verification and mind-map verification. Earlier failed runs remain failures and cannot be substituted for the final head. No shutdown budget, retry policy, feature flag, formula, prompt, schema, action authority, frozen S-01–S-25/M1.8, Master Roadmap, Gate 0 or Phase 1 authority is changed by this documentation/test-harness correction. No live runtime or database was accessed.

**Next bounded work:** verify the exact PR head and CI; then continue the shutdown ownership audit at the boundary between producer quiescence, synchronous Writer admission/drain and resource closure. Do not introduce a new cancellation or locking protocol until the current shared-Writer ownership and shutdown ordering are fully traced.


## 50. Shutdown ownership and Writer admission — source-level follow-up (28 November 2026)

**Evidence:** `run.py` blob `d4482e2c2a2da5e165ec810fd40cf9536c45f49c`; `gui/server.py` blob `cb399a337441bebe23f3f52079ea79bf1b7ab460`; `gui/shutdown_gate.py` blob `c03e8e83b2b27c79e050605f75cd37e590848852`; `substrate/writer.py` blob `455329e3c25aa1a3e7fd977241bb4cd7f8a61e34`. Source inspection only; no host/runtime observation.

### Confirmed shutdown order

1. The SIGTERM/SIGINT handler in `run.py` establishes one monotonic deadline.
2. `ShutdownGate.begin_shutdown()` atomically closes HTTP request admission under a Condition and waits for every admitted Flask request to leave.
3. The decoder stop Event is set.
4. `AppState.close(deadline=...)` shuts down the scheduler, signals registered producers, joins their known threads against the remaining producer budget, then closes Writers against the same absolute deadline.
5. A successful report is required before the clean-shutdown marker is written; incomplete request drain, producer join, Writer close or marker persistence exits without a clean marker.

### Important Writer lifecycle detail

`Writer.submit()` and `Writer.close()` share `_lifecycle_lock`. Close first stops acceptance and enqueues one sentinel while holding that lock. Therefore every accepted request is queued before the sentinel, and submissions that lose the race to close fail synchronously. The worker drains accepted requests FIFO before it sees the sentinel and closes SQLite. This is stronger than a bare stop Event and closes the queue-ordering race at the Writer boundary.

The remaining producer-level window is different: a producer can pass its stop check, then submit while Writer admission is still open because AppState deliberately waits for producers before closing Writers. That request is accepted and drained. If a producer survives the bounded join, Writer closure prevents later submissions; AppState reports the live producer and the caller refuses a clean-shutdown marker. Do not describe this as an atomic stop-to-submit barrier or as forced cancellation.

### Ownership census status and improvement questions

- `run.py` directly creates the decoder thread, then exposes its stop Event and thread through `state.decoder_loop`, allowing the AppState registry to stop and join it. The same entrypoint registers `state.close` with `atexit`; the explicit signal handler is the bounded clean-shutdown path.
- `AppState._quiesce_producers()` explicitly describes its registry as bounded, not a claim that every process thread is registered. It snapshots selected multi-thread worker registries under their service lock where available, signals all managed workers before joining, and reports survivors.
- This inspection did not establish a repository-wide census of thread creation, detached route workers, subprocesses, model calls or every service-owned worker. Do not infer completeness from the current managed tuple.
- The separate `gui/server.py` direct-entrypoint path also registers `state.close` with `atexit`; its signal/deployment lifecycle should be compared with the production `run.py` entrypoint before treating the two launch modes as equivalent.
- The first workflow run after the Warrant test-harness correction (`46134718448`) and the subsequent exact-head runs (`46134838495`, `46134932896`) were cancelled with no jobs when the branch advanced; none is a pass or failure diagnosis. The PR branch contains two Writer lifecycle regressions in `tests/test_writer_lifecycle.py`: a single submitter and eight concurrent submitters race close; every submission must either be accepted and drained before the sentinel or rejected after close wins, with no accepted Future stranded. The tests distinguish a `Writer.submit()` admission error from a failure of an already accepted Future. **Exact-head validation now passed** on PR head `75d9d23208b2144f05d4c4f498c393306fc152e7`: workflow run `46135005064`, pytest job `140948928374`; sandbox probe OK (unprivileged, no capabilities/credentials, read-only source, disposable data/tmpfs, no default route/outbound network); full baseline **3,045 passed, 7 skipped, 86 subtests passed**, zero known-intentional tests deselected; mind-map verification **30 nodes, 0 unverified, 12 dark, 2 blocked**. This validates the exact PR head's CI test scope, not host runtime behaviour or merge approval. Baseline and mind-map results are recorded; PR review/merge decision remains separate.

### Next bounded research/development

Complete the source-to-sink ownership census for thread/process creation and route-spawned work; reconcile every discovered worker with AppState ownership, stop semantics, join semantics and resource dependencies. Then test Writer acceptance ordering under a deterministic submit-vs-close race and test the AppState timeout path with a producer that remains alive. Keep the existing per-Writer lifecycle lock unless evidence demonstrates a defect; do not add a second global lock or alter shutdown budgets by assumption.

No live runtime, host process, database, feature flag, frozen specification, Master Roadmap, Gate 0 or Phase 1 authority was changed.


## 51. Request-drain versus voice-call timeout — operational improvement candidate (28 November 2026)

**Evidence source:** `research/SHUTDOWN_REQUEST_VOICE_TIMEOUT_GAP_2026-11-28.md` on the shutdown candidate branch; source snapshot after #378/#381. This is a code-derived timing risk, not an observed host failure.

### Finding

- The graceful shutdown budget is 12 seconds and includes HTTP request drain, producer quiescence and Writer drains; the tracked supervisor escalation is approximately 15 seconds.
- `ShutdownGate` closes new HTTP admission and waits for admitted requests, but it does not cancel the work inside a request.
- `VoiceClient` uses a 120-second per-request timeout. The inspected Chat route can make the initial voice call plus two sequential conditional retries (anti-repeat and provenance) when the corresponding conditions apply.
- The theoretical cumulative timeout exposure is therefore up to 360 seconds if all three calls stall to their individual timeout. This is not measured latency and does not mean every request makes three calls.
- If an admitted request remains inside a voice call beyond the 12-second drain deadline, the process exits non-zero before AppState producer quiescence, Writer draining or clean-marker persistence. This is fail-closed for the clean marker, but not a successful graceful shutdown. The source trace does not establish actual data loss or corruption.

### Betterment path

Do not silently change the 120-second voice timeout or the 12/15-second shutdown budgets. First measure normal and retry-path latency on the authorized host, then test SIGTERM during an active voice request with disposable/restorable data while recording active-request labels, Writer queue depth, exit code and clean-marker result. Only then compare a cancellable request path, bounded response abort, or a revised operational budget. Preserve the distinction between a request being admitted, a model call being attempted, a call returning and audio being physically heard.

This remains a host-evidence requirement, not permission to alter the frozen specifications, Master Roadmap, Gate 0 or Phase 1 authority. No host process, live database, runtime flag or timeout was changed.
