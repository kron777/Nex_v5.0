# NEX 5.0 — INDEX / DEVELOPMENT MANUAL

**Last verified against:** `main` at `18c8f06171e1de35c3210831a49b63d0e2487af0` (28 November 2026); exact-head CI status for this latest commit was not surfaced by the combined-status check
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

This trace is source-verified and hypothesis-generating. It identifies several existing connections and important non-connections; it does not yet establish runtime liveness, beneficial cognitive effect, or a unified integrated subject. No new node or runtime wire was added. A test-only characterization has now been added to `tests/test_dynamic.py`: an external `ai_research.arxiv` event must increase that branch's Bonsai focus and texture, while an `internal.proprioception` event is confirmed to match the systems branch but produce zero magnitude, no focus/texture change and no Stage-2 F-step event. This strengthens the previously weak internal-event assertion and adds a positive control. Implementation/test head `611ad5f6aff4c1aea44574fb9defae8a80309def` passed exact-head workflows `46149016907` and `46149041938`, each reporting **3,076 tests passed, 7 skipped, 86 subtests**; baseline check OK and isolated sandbox probe passed. The subsequent documentation-only synchronization is on the current PR branch and is receiving its own exact-head CI run before merge. The test currently establishes the Stage-2 pipeline → Bonsai edge only. Fountain branch selection and workspace framing remain the next separate test seam.

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



## 49. Development practice refinement — evidence, influence and learning (28 November 2026)

**Research snapshot:** current `main` at `55fd635bd535d15ece3e3878bf1e71621f56fa7c`. This entry records an engineering-method refinement from the existing INDEX, RDO design and development records, the G-92/G-93 lifecycle work, the cognitive interaction trace and the design-mindedness investigation. It is a development aid, not a governing specification, roadmap amendment or runtime finding.

### The central correction: diagnose the kind of gap before proposing a fix

Classify each finding before choosing an implementation:

1. **Absent capability:** no suitable mechanism exists in the current architecture.
2. **Disconnected capability:** the mechanism exists, but a required producer-to-consumer path is missing or incorrectly wired.
3. **Unconsumed or ineffective output:** a producer runs, but its output is not consumed, is neutralised, is stale, or has no demonstrated effect.
4. **Deliberate exclusion:** a path is disabled or filtered because prior evidence showed distortion, starvation, amplification, unsafe side effects or experimental confounding. Preserve it unless new evidence and authority justify reconsideration.
5. **Measurement gap:** the mechanism/path exists, but its actual influence, operating envelope or runtime status is unknown.
6. **Semantic/authority gap:** source behaviour exists but intended meaning, lifecycle contract, policy or approval is unresolved. Do not guess implementation semantics from convenient code.
7. **Regression or ownership defect:** a previously established invariant has been violated by a change, concurrency path, alternate consumer or lifecycle boundary.

These classes can overlap. Record the primary gap and any secondary gaps. Do not automatically translate every finding into a new feature.

### Trace influence as a relationship, not a component count

For each material signal or state, trace:

- origin and producer;
- representation, units, confidence, provenance and freshness;
- transformations, filters, defaults, thresholds and selection rules;
- persistence and ownership;
- every direct and indirect consumer;
- whether the effect is descriptive, prompt-mediated, selection-changing, state-changing or externally consequential;
- flags, deployment conditions, capability checks and approval authority;
- failure, retry, restart, concurrency and stale-data behaviour.

Assess influence per relationship: direct/indirect, read/behavioural, conditional/unconditional, bounded/unbounded, reversible/irreversible, measured/unmeasured. A count of consumers or files is not an authority or impact score. A prompt contribution is not proof of mechanical selection influence; a log entry is not proof of consumption; boot construction is not proof of liveness.

Record intentional negative edges explicitly. Use positive and negative controls where practical. A signal useful for self-description may be harmful when used for attention steering; a bounded scan may starve items unless it rotates; a safety filter in one path does not protect alternate consumers.

### Use a stronger evidence ladder

Keep these states separate in every report:

- specified;
- present in source;
- boot-wired;
- enabled in the examined environment;
- consumed by a real downstream path;
- measured under a controlled probe or authorised runtime observation;
- validated against a relevant falsifier, baseline and regression set.

For each claim preserve the exact source commit and path/line or symbol, test path and exact workflow/run/job, evidence class, counter-evidence, verification date and remaining unknowns. Source anchors establish where to inspect, not semantic satisfaction. A fixture establishes only its fixture scope. CI validates only the exact tested commit and test scope. Host behaviour remains UNKNOWN without authorised host evidence.

For PR work, independently check open/closed, draft/ready, base, head, merge base, changed files and exact-head CI. A green workflow on a stale base is not validation of a replay onto current main. Documentation commits after a code test do not change the tested code, but the new exact head should still be recorded accurately.

### Improve experiment design before increasing implementation scope

For a proposed connection or behaviour change:

1. State the causal claim in one sentence.
2. Identify the smallest observable intermediate variables.
3. Capture a baseline and source/fixture conditions.
4. Perturb one independent input at a time.
5. Include a positive control and a negative/intentional-exclusion control where appropriate.
6. Trace the effect through the intended consumer, not merely the producer.
7. Test counterfactual subtraction or disablement where feasible.
8. Inspect unintended consumers, feedback amplification, starvation and side effects.
9. Compare predicted and observed outcomes; preserve null, adverse and ambiguous results.
10. Only then decide whether the next integration level is justified.

Separate three levels of evidence: one connection works; the subsystem behaves coherently; the whole system delivers a beneficial, stable outcome. Passing the first does not imply the second or third. Prompt wording, self-report and component labels must not substitute for measured changes in attention, retrieval, selection or external behaviour.

### Make boundedness fair and lifecycle-safe

Whenever code uses limits, windows, top-K selection, pagination, sampling, retries or periodic scans, ask whether the bound creates starvation, permanent ordering bias, missed updates or restart gaps. Inspect cursor semantics, rotation, idempotency and recovery. When state is shared, identify the canonical owner and writer; inspect submit/close races, concurrent mutation, atomic persistence, replay and failure between ledger and snapshot writes.

Reuse existing infrastructure when its responsibility fits. Do not mechanically split modules based on LOC heuristics or create a parallel ledger, queue, workspace, node or authority layer merely to make a gap look addressed. Conversely, do not overload an existing component when ownership and lifecycle become incoherent. Choose the smallest change that closes the invariant, not necessarily the smallest textual diff.

### Treat NEX and RDO as systems that must also be examined critically

NEX's disabled mechanisms can encode experimental learning, not unfinished work. Recover the reason for an OFF state before proposing activation. Preserve welfare constraints, boundedness, reversibility and neutral alternatives where a mechanism can create aversive or self-reinforcing states. Do not describe functional analogues as proof of subjective experience.

RDO remains advisory and separate from NEX runtime cognition. Its source-signature reconciliation is not semantic verification; its prioritisation mathematics is not calibrated merely because it produces numbers; repeated patterns do not automatically justify new rules. Compare efficiency only across comparable executed-and-verified cycles, with denominators and missing outcomes preserved. Planning-only and imported-retrospective cycles are not execution outcomes. Human approval, scope review, acceptance, independent verification and execution remain distinct decisions.

### Revised research–develop–observe loop

`Orient → classify the gap → trace the relationship network → form competing hypotheses → identify disconfirming evidence → check authority and existing mechanisms → design the smallest causal probe → implement one bounded increment → validate exact scope → rescan changed and adjacent paths → record outcomes and newly exposed obligations → reassess.`

The loop is iterative, not a rigid waterfall. Research and implementation may proceed together where the evidence and authority permit. Stop expanding when the next obligation is actionable, an existing mechanism should be reused, a required authority/runtime fact is unavailable, or expected information gain has materially diminished. Record the unresolved boundary and continue elsewhere rather than inventing certainty.

**No NEX runtime code, feature flags, databases, frozen S-01–S-25/M1.8 content, Master Roadmap, mind-map authority, Gate 0 or Phase 1 status was changed by this method study.** This entry is a refinement of engineering practice only.


## 50. Boot-time worker ownership and partial-construction boundary (28 November 2026)

**Source snapshot:** `main` at `b680b13006a767cf0567c952697659fb92a831f7`. This is a source/test-coverage finding from the boot orchestrator, AppState shutdown registry, SenseScheduler, SignalLoop, DiversityLoop, EdgeGeneratorLoop and `tests/test_sense.py`. It is not a claim that a production boot failure or leaked thread has been observed.

### Verified construction and ownership paths

- `run.py` constructs the SenseScheduler at boot. Its constructor creates one `_AdapterThread` per adapter, and each `_AdapterThread` starts its daemon thread immediately. The scheduler then auto-starts external feeds.
- `build_signal_loop()` constructs and starts SignalLoop internally before returning it.
- `build_diversity_loop()` constructs only; `run.py` calls `.start()` separately.
- `run.py` starts SpeechQueueConsumer, DiversityLoop and EdgeGeneratorLoop before constructing AppState. SignalLoop and SenseScheduler are also already running by then.
- AppState's `_quiesce_producers()` has explicit stop/join handling for the registered services, and `close()` correctly refuses a clean result when registered producers remain alive or report errors. This registry is bounded to the services passed into AppState; it is not a process-wide thread census.
- The decoder thread is started after AppState construction and is then attached to state for shutdown handling.

### The uncovered lifecycle boundary

The normal post-construction shutdown path is substantially covered, but the inspected `tests/test_sense.py` scheduler tests do not exercise constructor rollback when adapter construction fails partway through `SenseScheduler.__init__`. Since each worker starts inside `_AdapterThread.__init__`, an exception while constructing a later adapter can leave earlier workers running without a successfully returned scheduler object to own and stop them. Duplicate adapter IDs are another untested ownership edge: the current dictionary assignment can replace a prior worker reference after its thread has already started.

The broader boot sequence has the same class of risk: if boot raises after one or more services start but before AppState is constructed, the normal AppState registry is not yet available to clean them up. The inspected source establishes the ordering and the missing owner during that interval; it does not establish that any particular exception path has occurred in a live host.

### Refinement direction — bounded, test-first

1. Make SenseScheduler construction transactional: validate adapter IDs before starting threads; if any worker construction/start fails, signal and join every worker already created before re-raising the original failure.
2. Add deterministic tests for duplicate IDs, failure after at least one successful worker start, and bounded cleanup when an earlier worker is blocked. Assert no worker is silently orphaned and preserve the original exception.
3. Separately design a boot-scope owner/rollback boundary that is established before the first background worker starts, or defer all starts until a complete state owner exists. Do not add a second competing shutdown registry; reuse the existing stop/join contracts and absolute deadline.
4. Keep builder semantics explicit. A builder that starts a worker must advertise that side effect and return an object with a defined stop/join lifecycle. Avoid silently mixing auto-start and caller-start conventions.
5. Re-run exact-head tests and rescan every boot-created producer against the AppState registry before claiming process-wide lifecycle completeness.

This finding does not justify changing graceful-shutdown timeouts, forcibly cancelling threads, altering scheduler feed policy, changing frozen specifications, or asserting a host leak. The next implementation should begin with the narrow SenseScheduler constructor invariant; the cross-boot rollback design is a separate increment because it spans many subsystems and must preserve their ownership contracts.

**Evidence boundary:** source ordering and normal-path tests inspected; no live host boot fault was injected. Partial-construction failure, duplicate-ID orphaning and boot-time leaked threads remain unobserved hypotheses requiring deterministic tests. No runtime code, feature flags, databases, frozen S-01–S-25/M1.8 content, Master Roadmap, mind-map authority, Gate 0 or Phase 1 status changed in this study.



## 51. Development approach upgrade — lifecycle contracts, adversarial probes and evidence debt (28 November 2026)

**Research snapshot:** `main` at `169217c2b9e9641abe98551c89a6cf0570d4fc4c`. This entry upgrades the working method in §49 using the boot-ownership investigation in §50 and the current SenseScheduler implementation branch. It is an engineering-process refinement, not a change to NEX's governing specifications, roadmap or runtime authority.

### 1. Model ownership as a lifecycle contract, not a shutdown callback

For every background service, explicitly map the lifecycle:

`unconstructed → constructed → prepared → started → active/paused → stop-requested → quiescent → joined → resources-released`

Not every service needs every state, but transitions and owners must be explicit. Distinguish:
- object construction from worker creation;
- thread creation from successful thread start;
- successful start from permission to perform work;
- stop request from actual quiescence;
- join completion from resource release;
- normal shutdown from rollback after failed construction.

A returned object is not automatically an owner of workers started before it was returned. A builder with side effects must either return a complete owner or roll back every side effect before propagating failure. At a higher level, boot must have an owner before the first service starts, or defer starts until that owner exists. Reuse the existing stop/join contracts; do not create a competing registry without evidence that the current owner cannot express the lifecycle.

### 2. Use a fault-injection matrix, not one happy-path test

For each owner/builder boundary, consider deterministic failure points:
- before any worker is prepared;
- after one or more workers are prepared but none started;
- after the first successful start;
- after a later start fails;
- immediately before the activation/release gate opens;
- during the first work unit;
- while work is blocked in I/O;
- while stop races with submit/write;
- during join timeout;
- during resource close after workers stop.

For each case assert the invariant, not just an expected log: no unowned live worker, no work before activation commits, no post-stop submission where prohibited, no false clean-shutdown marker, bounded waiting, and preservation of the original exception. Use events/barriers and injected failures rather than sleeps wherever possible. A test that only asserts `is_alive() == False` should also establish that the worker actually entered the intended path or never passed its activation gate.

### 3. Separate the three concurrency questions

Do not collapse these into a generic “thread-safe” claim:
1. **Ownership:** who retains the reference and is responsible for stop/join?
2. **Admission:** what prevents new work from beginning while shutdown/rollback proceeds?
3. **Completion:** what proves in-flight work has stopped before shared resources close?

For each shared resource, identify its canonical owner and the exact admission/close ordering. Check the time-of-check/time-of-use gap between a producer's stop check and a Writer submission; a cooperative stop flag alone cannot close that gap. Conversely, do not introduce locks or cancellation where the existing queue/close contract already guarantees the required ordering.

### 4. Expand the evidence record into an explicit claim ledger

Every material finding should have a compact record:
- claim and scope;
- source revision plus path/symbol;
- evidence class (source, test, CI, authorised host observation);
- exact test/workflow/job and revision;
- observed result;
- counter-evidence and falsifier;
- unresolved assumptions;
- next probe and stop condition.

Use precise status language: **observed**, **reproduced**, **source-derived**, **test-covered**, **CI-validated at exact head**, **host-observed**, or **unknown**. Do not promote one status into another. Preserve stale CI and base divergence as evidence debt, not as footnotes.

### 5. Add a deliberate adversarial review before widening scope

For every proposed fix, ask:
- What if the exception happens one instruction earlier or later?
- What if the callback runs twice or concurrently?
- What if the worker starts but the caller sees an exception?
- What if a resource is already closing?
- What if the process restarts between persistence steps?
- What if an alternate consumer bypasses the intended guard?
- What prior OFF-state or exclusion might this change accidentally undo?
- What evidence would show the fix is unnecessary or harmful?

Prefer the smallest causal change that closes the invariant. Then inspect adjacent owners and alternate paths for the same defect class; do not mass-refactor them from pattern resemblance alone. A repeated pattern creates a research obligation, not automatic permission to copy a fix.

### 6. Prioritise by risk, information gain and reversibility

A practical order is:
1. irreversible or externally consequential authority/side-effect boundary;
2. data integrity, persistence ownership and false-clean-shutdown risks;
3. orphaned workers, races, unbounded waits and recovery gaps;
4. silent loss, starvation, stale state and misleading observability;
5. semantic/interpretive quality and measured downstream effect;
6. usability and efficiency.

Within a tier, prefer a probe that distinguishes competing explanations and reduces uncertainty. Record expected information gain before expensive or broad work. If the evidence cannot distinguish hypotheses, keep the result unknown and move to a better probe rather than increasing code volume.

### 7. Research–develop–observe now includes a lifecycle and counterfactual pass

`Orient → classify the gap → map ownership and influence → state competing causal hypotheses → identify falsifiers → check existing contracts and authority → design fault/counterfactual probes → implement one bounded invariant → validate exact revision and scope → adversarially inspect adjacent paths → record evidence debt and consequences → reassess priority.`

Continue research and implementation concurrently when a bounded, reversible increment is justified. Do not let CI waiting become idle time: inspect adjacent contracts, test blind spots, source ownership and alternative explanations. Equally, do not infer a pass while CI is pending. Every new implementation should trigger a rescan of the changed code, its callers, its consumers and the owner that closes its resources.

### Current application: SenseScheduler startup transaction

PR #414 (`fix/sense-scheduler-transactional-startup-2026-11-28`, head `ab8a1908be1ee17026a80ab934c6318b87847a9e`) implements the first bounded application:
- validate adapter IDs before constructing workers;
- prepare all workers before starting any;
- hold workers behind a shared start gate until every thread has started;
- on partial start failure, stop and join all prepared workers before re-raising;
- treat never-started threads as already quiescent;
- add deterministic duplicate-ID and injected second-start-failure regressions.

The exact-head CI run 2526 was still running its full baseline suite when this entry was prepared; no pass is claimed here. The current regression proves the injected partial-start rollback and no-poll-before-commit case, but does not yet inject a worker blocked in its first operation during rollback. That is a specific remaining test question, not evidence of a leak.

The same internal-start pattern appears in Dynamic, World Model, Membrane and Fountain builders. This is a cross-subsystem research queue only. Inspect each builder's own cleanup contract, constructor dependencies and tests before changing it. The boot-level owner-before-first-start boundary remains separate from builder-level rollback.

**Unchanged boundaries:** no frozen S-01–S-25/M1.8 content, Master Roadmap, Gate 0/Phase 1 authority, Tibetan mind-map role, cognitive interpretation/action-authority separation, NEX runtime flags, databases or live host state changed by this method entry.



## 52. Dynamic builder startup rollback — first cross-builder application (28 November 2026)

**Implementation branch / PR:** `fix/dynamic-builder-transactional-startup-2026-11-28`, [PR #415](https://github.com/kron777/Nex_v5.0/pull/415), exact head `8889eba914cbffe1767efb200f70626e71f9c945`. Base at PR creation: `58a3cb13d4b15c65421e595830d78d233e663ffb`.

### Source-derived gap

`build_dynamic()` creates a DynamicState, prepares a list of loop functions, then starts each thread sequentially. Before this increment, it assigned `state._stop` and `state._threads` only after every `Thread.start()` succeeded. If a later start raised, earlier threads could already be running, but the builder would not return the state or expose its ownership handles to the caller. The normal `stop_dynamic()` contract could therefore not be used by the caller for that failed construction.

This is a source-derived partial-construction risk, not a report of an observed production failure or host leak.

### Bounded implementation

- Publish `state._stop` and the live `state._threads` list before starting any worker.
- Prepare workers behind a shared activation gate; loop bodies cannot begin until every thread start succeeds.
- If a start fails, set the stop event, release the gate so started wrappers can exit without entering their loop body, and join started threads against one shared one-second rollback budget.
- Preserve and re-raise the original startup exception. Log any worker that unexpectedly survives the bounded rollback.
- Add a deterministic regression injecting failure on the second thread start; it asserts that the first thread is joined, the second was never started, and the patched first loop body was never entered.

### Validation boundary and next work

PR #415 was opened against current `main`; exact-head CI had not yet been reported when this entry was written. No test pass is claimed. The regression exercises the second-start failure and gate/rollback ordering, but does not inject a failure after a worker has passed the gate, because the gate is deliberately withheld until all starts succeed.

This change does not alter the successful Dynamic loop cadence or processing semantics. It does not solve boot-level ownership before AppState. World Model, Membrane and Fountain have similar internal-start patterns, but their cleanup contracts differ and remain separate investigations. No shared thread utility or bulk refactor is justified yet.

**Unchanged boundaries:** no frozen S-01–S-25/M1.8 content, Master Roadmap, Gate 0/Phase 1 authority, mind-map role, cognitive/action authority separation, NEX runtime flags, databases or live host state changed by this increment.



## 53. SenseScheduler startup transaction — merged and exact-head validated (28 November 2026)

**Merged PR:** [#414](https://github.com/kron777/Nex_v5.0/pull/414), merge commit `c54a82f7add75553ad256c31d0f5e9ca04066d07`. The tested PR head was `ab8a1908be1ee17026a80ab934c6318b87847a9e`; its code was unchanged by the intervening documentation-only commits on `main).

**Exact-head CI:** workflow run `46137289839` (run 2526), job `140955316633`, completed successfully. Full baseline result: **3,001 passed, 7 skipped, 86 subtests passed**, 0 failures. Sandbox probe passed. Mind-map verification: 30 nodes, 0 unverified, 12 dark, 2 blocked. Existing warnings remain: two cited doctrine files missing and p13_finitude unblock past due. CI validates the exact PR head and its test environment, not live host operation.

The merged change validates adapter IDs before worker creation, prepares all workers before starting them, holds them behind a shared start gate until all starts succeed, and rolls back a partial start by stopping and joining the prepared workers before re-raising. Regression tests cover duplicate IDs and an injected second-start failure with no polling before startup commit.

**Integration boundary:** PR #414 is merged. This does not resolve the wider boot-before-AppState ownership gap, nor does it prove all other builders roll back partial startup. PR #415 separately addresses Dynamic builder rollback and remains under exact-head CI at the time of this entry.



## 54. Active producer cooperative shutdown sweep — validation checkpoint (28 November 2026)

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


## 55. Shutdown ownership and Writer admission — source-level follow-up (28 November 2026)

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


## 56. Request-drain versus voice-call timeout — operational improvement candidate (28 November 2026)

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

## 57. Dynamic builder startup transaction — merged and exact-head validated (28 November 2026)

**Merged PR:** [#415](https://github.com/kron777/Nex_v5.0/pull/415), merge commit `93bc7a820565e577ddae155004b69dc0bcd50207`. Tested PR head: `8889eba914cbffe1767efb200f70626e71f9c945`.

**Exact-head CI:** workflow run `46137634653` (run 2528), pytest job `140956406918`, completed successfully. Full baseline result: **3,000 passed, 7 skipped, 86 subtests passed**, 0 failures. Sandbox probe passed. Mind-map verification: 30 nodes, 0 unverified, 12 dark, 2 blocked. CI validates the tested PR head, not live host operation.

The merged builder publishes the DynamicState stop event and worker list before starting loops, gates loop-body entry until every thread has started, and on partial failure requests stop, releases the gate for wrappers to exit without running, joins started workers against one bounded rollback budget, logs any survivor, and re-raises the original exception. A deterministic second-start failure test verifies that no loop body is entered and the first worker is joined.

**Integration boundary:** PR #415 is merged. This closes the Dynamic builder's partial-thread-start ownership gap in the tested path. It does not establish process-wide boot ownership before AppState, nor does it prove the analogous World Model, Membrane, Fountain or other builders are transactional. Those remain separate, evidence-led increments.


## 58. The NEX Development Method — Cartographer, Scientist, Engineer and Gardener (28 November 2026)

**Purpose:** establish a repeatable method for learning about NEX, improving it without losing architectural coherence, and distinguishing genuine progress from activity. This chapter is a development method, not a governing specification, authority grant, runtime policy or roadmap amendment. It does not supersede frozen S-01–S-25/M1.8, the Master Roadmap, Phase 0/Gate 0, or any approved boundary.

### The central idea: develop understanding, not just code

NEX development is not a race to add faculties, nodes, loops, agents, scores or connections. It is the disciplined reduction of important uncertainty while preserving the system's integrity.

A code change is only one possible result of a successful development cycle. Other valid outcomes include:
- discovering that a capability already exists and reconnecting or correctly consuming it;
- proving that an apparent gap is actually an intentional exclusion;
- discovering that a feature is present but dark, unconsumed, ineffective or misrepresented;
- identifying a measurement gap and designing a discriminating experiment;
- finding that a proposed mechanism duplicates an existing one;
- deciding that the evidence is insufficient and recording the unknown;
- removing or declining a mechanism because it creates more distortion than value.

The objective is not maximum code volume. It is a better-founded system and a more accurate understanding of what the system actually does.

### 1. Four complementary engineering roles

Every substantial investigation should move deliberately between four perspectives.

**The Cartographer — understand the territory.**
- Map components, owners, inputs, outputs, persistence, consumers, configuration, lifecycle and dependencies.
- Trace real paths, not just class names or architecture diagrams.
- Record both connections and non-connections.
- Map the boundary between cognitive interpretation, typed operations, capability validation, approval authority, execution and post-execution verification.
- Treat the mind map as descriptive. Its placement of a Mind Aspect grants no action authority.

**The Scientist — challenge the explanation.**
- Maintain multiple plausible hypotheses until evidence distinguishes them.
- State what each hypothesis predicts and what observation would disconfirm it.
- Use baselines, positive controls, negative controls, counterfactuals and repeatable probes.
- Separate correlation, contribution, causal influence and beneficial effect.
- Ask what would change the current conclusion.

**The Engineer — change one meaningful thing.**
- Prefer the smallest reversible change that closes a demonstrated invariant or tests a valuable hypothesis.
- Reuse existing mechanisms before creating new ones.
- Define ownership, contracts, failure behaviour, observability and rollback before widening scope.
- Integrate one connection at a time and validate its effect on neighbouring paths.
- Keep the implementation proportional to the evidence and the risk.

**The Gardener — preserve conditions for healthy growth.**
- Protect deliberate exclusions, dark-by-default mechanisms and lessons from previous failures.
- Prune duplication, dead paths, misleading claims and unconsumed outputs.
- Avoid forcing every subsystem to participate in every decision.
- Recognise that restraint, delay, silence and non-action can be meaningful outcomes rather than defects.
- Stop experiments when they become uninformative, unsafe, redundant or disproportionately costly.

No single role is sufficient. Cartography without experiments becomes static documentation; experiments without architecture can measure the wrong thing; engineering without causal understanding creates feature accumulation; gardening without evidence can become arbitrary conservatism.

### 2. Build four maps before choosing a fix

For a consequential question, maintain four small, linked maps. They can be notes, tables, tests or diagrams; they do not require a new runtime subsystem.

1. **Structure map:** what exists, where it lives, who constructs it, who owns it, and how it starts and stops.
2. **Influence map:** where data originates, how it is represented and transformed, which selectors or consumers read it, and what observable effect follows.
3. **Authority map:** which component may interpret, propose, validate, approve, execute or verify an operation. Never infer authority from cognitive importance, mind-map position, salience or a numerical score.
4. **Evidence map:** what is specified, source-present, boot-wired, enabled, consumed, measured and validated—and which of those stages remain unknown.

The maps should expose both positive and negative space:
- a connection that exists;
- a connection that is absent;
- a connection that is intentionally excluded;
- an output nobody consumes;
- a consumer that bypasses the expected path;
- a capability that exists but is disabled;
- a state transition that has no reliable owner;
- an apparent absence that may actually be deliberate silence or restraint.

Do not treat all missing edges as defects. First discover whether the missing edge is accidental, intentional, obsolete, unsafe or simply unmeasured.

### 3. Classify the gap before designing the solution

Use the following gap classes as a first diagnosis:

1. **Capability absence:** the required mechanism does not exist.
2. **Disconnected capability:** it exists but is not connected to the intended pathway.
3. **Unconsumed or ineffective output:** a producer emits data, but no meaningful consumer uses it or its effect is negligible.
4. **Deliberate exclusion:** the path is intentionally dark, blocked, filtered or omitted, often because of a previous failure or policy.
5. **Measurement gap:** the mechanism may work, but the available evidence cannot establish whether it does.
6. **Semantic or authority gap:** data, meaning, responsibility or permission is unclear or conflated.
7. **Regression or ownership defect:** a previously established contract is broken by lifecycle, persistence, concurrency, integration or compatibility behaviour.

A single symptom can contain several gap classes. For example, a loop may be present and started, but not registered with the shutdown owner; its output may be persisted but never consumed; and the only available test may prove that the thread exists rather than that it produces useful work. Split the problem into independently testable claims instead of applying one broad label.

### 4. Maintain a hypothesis slate, not a premature conclusion

For every non-trivial investigation, write down at least two plausible explanations before selecting an implementation. Include the possibility that the current design is correct and the observed problem is caused elsewhere.

For each hypothesis record:
- the causal claim;
- the source paths and symbols that should contain evidence;
- the expected intermediate states;
- the predicted downstream effect;
- a disconfirming observation;
- the cheapest reliable probe;
- the risks of acting if the hypothesis is wrong.

Use counterfactual subtraction: if this component, connection, flag or data source were removed, what would observably change? Conversely, if it were introduced, what new consumers, feedback paths or failure modes would appear?

A source comment, class name, diagram or model-generated explanation is a lead, not proof. Trace the implementation and the consumer. If competing explanations remain indistinguishable, preserve the uncertainty and design a better probe.

### 5. Choose the smallest probe that can distinguish the hypotheses

Use an evidence ladder. Move upward only when the lower level cannot answer the question.

- **Static source trace:** establish what the code can do and what paths are wired.
- **Contract inspection:** identify inputs, outputs, invariants, owners, failure modes and compatibility requirements.
- **Focused unit or component test:** isolate one behaviour with deterministic fixtures.
- **Integration test:** verify the actual connection between neighbouring components.
- **Controlled subsystem experiment:** compare a baseline with one deliberate perturbation and appropriate controls.
- **Authorised host observation:** establish what a real deployment actually does under its observed configuration.
- **Operational validation:** repeat under representative workload, restart, failure, concurrency and recovery conditions.

A test result must name the exact revision, command, environment assumptions, test selection and result. A CI pass validates only the revision and test environment that ran. It does not prove that the user's host is running that revision, that a feature flag is enabled there, or that the behaviour is beneficial in production.

Prefer deterministic events, barriers, injected failures and isolated databases over timing sleeps and live-state manipulation. Never use a live substrate database as a convenient test fixture.

### 6. Design changes around invariants and contracts

Before editing code, write the invariant in plain language. Examples:

- every started worker has a reachable owner responsible for stopping and joining it;
- no worker performs useful work until subsystem startup has committed;
- accepted writes complete before the canonical Writer closes;
- a failed startup cannot leave an unowned live worker;
- an operation cannot cross an approval boundary merely because a cognitive component recommends it;
- a belief marked inactive cannot re-enter through an unexamined alternate consumer;
- a deliberate exclusion remains effective after adjacent code changes.

Then define:
- **preconditions:** what must already be true;
- **postconditions:** what the operation guarantees;
- **ownership:** who retains responsibility for resources and state;
- **admission:** what prevents new work from entering during stop or rollback;
- **completion:** what proves in-flight work is finished;
- **failure semantics:** what is returned, raised, recorded or retried;
- **observability:** what evidence distinguishes success from partial failure;
- **rollback:** how the change can be reversed without corrupting state.

Do not use the word *thread-safe*, *atomic*, *transactional*, *verified* or *safe* without identifying the exact guarantee and its scope.

### 7. Integrate by connections, not by architectural ambition

Use three integration levels:

**Level A — individual connection.** Connect one producer to one intended consumer, or one owner to one lifecycle. Test the edge in isolation. Confirm that unrelated consumers do not change.

**Level B — subsystem integration.** Test the connected components together under normal, boundary, failure, restart and concurrency conditions. Establish a new baseline.

**Level C — whole-system integration.** Only after subsystem contracts are stable, examine boot ordering, global resource ownership, cross-subsystem effects, operational observability and recovery.

Do not jump from a successful unit test directly to a whole-system claim. Each newly connected edge can create feedback, duplicate work, resource contention, authority confusion or a new failure route. A previously validated component can behave differently when placed in a new network.

For lifecycle work, explicitly distinguish construction, preparation, start, activation, stop request, quiescence, join and resource release. Builder-level rollback and boot-level ownership are separate obligations. Normal shutdown success does not prove that partial startup is safe.

### 8. Measure effects at the destination, not merely activity at the source

For each claimed improvement, identify the final effect that matters. Depending on the question, this may be:
- a downstream selection or decision;
- a persisted state transition;
- a verified operation;
- a measurable reduction in latency, failure or rework;
- improved continuity or retrieval;
- a human-observable interaction outcome.

Count neither emitted events nor connected consumers as proof of impact. Trace the effect through each transform and selector to the destination.

Use a baseline and, where useful, positive and negative controls. Record magnitude, timing, frequency, false positives, false negatives, starvation, unintended consumers and regressions. Separate:
- **mechanism activity** — it ran;
- **pathway influence** — its output changed a downstream state;
- **functional effect** — the change improved the intended outcome;
- **system value** — the improvement survives realistic conditions and comparison with a simpler alternative.

If the measurement is only a proxy, label it as a proxy. Do not promote a proxy into a claim about understanding, agency, emotion, consciousness or beneficial behaviour.

### 9. Keep an evidence and learning ledger

Every material development increment should leave a compact, durable record:

- question and scope;
- source revision and relevant paths/symbols;
- gap classification;
- competing hypotheses and falsifiers;
- invariant and intended effect;
- exact change and why existing mechanisms were insufficient;
- test command, revision, environment and results;
- CI workflow/job and exact tested head;
- adjacent paths rescanned;
- regressions, counter-evidence and unintended effects;
- remaining unknowns and next discriminating probe;
- rollback or recovery route.

Use evidence labels consistently: **specified**, **source-derived**, **test-covered**, **CI-validated at exact head**, **host-observed**, **reproduced**, **measured**, **validated**, or **unknown**. A historical pass remains historical. When a branch is rebased, reconstructed or changed after CI, its new head needs its own validation.

Record failures as information, not embarrassment. A failed hypothesis, rejected implementation or experiment that shows no effect can be a valuable result if its scope and conditions are clear.

### 10. Use a disciplined stopping rule

Research should not become endless browsing, and development should not become endless refactoring. Stop or redirect when one of these conditions is reached:

- a demonstrated defect has a bounded fix and its exact-scope validation is complete;
- the next action is clear and safely actionable;
- the remaining uncertainty requires host access, founder approval or unavailable evidence;
- competing hypotheses cannot yet be distinguished and a better probe is needed;
- the proposed work duplicates an existing mechanism;
- the expected information gain is lower than the cost or risk;
- the change would cross a frozen specification, roadmap gate or authority boundary;
- the result is stable enough to establish a new baseline and move to the next independent question.

Do not hide unresolved work. Convert it into an explicit obligation with an owner, evidence requirement and stop condition. Do not keep expanding a task merely because more code can be written.

### 11. Use AI systems as instruments, not authorities

Multiple AI systems can provide useful independent readings, adversarial critiques, test ideas and alternative hypotheses. Treat them as different analytical instruments with different blind spots—not as votes, oracles or substitutes for repository evidence.

For important decisions:
- ask systems to identify disconfirming evidence, not only support a preferred design;
- compare the assumptions behind their recommendations;
- verify claims against source, tests and approved documents;
- retain disagreements when evidence does not resolve them;
- keep human/founder authority at the correct approval boundary.

RDO, Watcher, extrapolation and prioritisation mechanisms can help identify obligations, compare evidence and organise work. They do not acquire project authority. An extrapolated obligation is a candidate for investigation, not an instruction to implement. Scores such as (V=R\times C\times I\times Q) are prioritisation aids, not calibrated truth or permission.

### 12. The operating loop

Use this sequence as the default for continuing NEX development:

1. **Orient:** verify the active branch, current main, governing documents, exact source revision and current CI state.
2. **Observe:** inspect the actual implementation and its callers, consumers, owners, flags and tests.
3. **Map:** update the structure, influence, authority and evidence maps for the question.
4. **Classify:** distinguish absent, disconnected, ineffective, deliberately excluded, unmeasured, semantic/authority and regression gaps.
5. **Hypothesise:** retain competing explanations and state what would falsify each.
6. **Probe:** choose the smallest deterministic experiment that can discriminate between them.
7. **Decide:** reuse, connect, measure, repair, defer or deliberately leave unchanged.
8. **Implement:** change one bounded invariant or connection with clear ownership and rollback.
9. **Validate:** test the exact revision, then inspect the changed code and adjacent paths for side effects.
10. **Integrate:** move from connection to subsystem to whole-system evidence without skipping levels.
11. **Learn:** record predictions, outcomes, surprises, regressions and remaining unknowns.
12. **Reorient:** choose the next task by consequence, information gain, reversibility and evidence—not by novelty or code volume.

The loop is iterative, not ceremonial. Research and implementation may proceed concurrently when a bounded change is justified. CI waiting is an opportunity to investigate adjacent contracts, but never a reason to claim success before the result arrives.

### 13. Current application and status corrections

This method is already being applied to background-worker lifecycle work:

- **SenseScheduler:** PR #414 merged as `c54a82f7add75553ad256c31d0f5e9ca04066d07`; exact-head CI validated 3,001 passed, 7 skipped and 86 subtests.
- **Dynamic builder:** PR #415 merged as `93bc7a820565e577ddae155004b69dc0bcd50207`; exact-head CI validated 3,000 passed, 7 skipped and 86 subtests.
- Earlier sections 52 and 53 are point-in-time notes written before those integrations completed. Section 57 records the later Dynamic merge; this section records the SenseScheduler merge status as well.
- **World Model builder startup rollback:** PR #417 merged as `f10879963fee55a1c4ee38c6d0c717f7ee6a4230`; its exact-head workflow passed. This validates the six-worker builder's tested partial-start rollback, not process-wide boot ownership.
- **Fountain builder startup rollback:** PR #419 merged as `2bc9c9bb0120895ccf12a9729bb3f74f5872b314`; its exact-head workflow passed 3,004 tests, 7 skipped and 86 subtests. The resulting mainline push also passed the same baseline.
- **Membrane builder startup rollback:** PR #418 merged as `405ca607265c13eedcb7bf57f4a35f2da1e1846c`; its reconciled exact-head workflow passed 3,005 tests, 7 skipped and 86 subtests.
- **Producer cooperative shutdown:** PR #416 merged as `149c7d1ff7dd8b1c2c7789ed74c0ac64fb39ffe5`. Its reconciled exact-head workflow run `46140753232` passed 3,051 tests, 7 skipped and 86 subtests. The merge preserves the newer Fountain startup gate while adding cooperative stop-aware generation and deterministic producer-shutdown regressions. This is repository CI evidence, not host-level SIGTERM validation or a process-wide thread census.

The next architectural questions remain separate: inspect SignalLoop's internal-start failure rollback; then address boot-level ownership before AppState. Producer cooperative shutdown and the World Model, Membrane and Fountain builder rollback increments are now individually merged and exact-head validated. Do not turn the repeated pattern into a bulk refactor without subsystem-specific evidence.

**Unchanged boundaries:** this chapter does not modify frozen S-01–S-25/M1.8, the Master Roadmap, Phase 0/Gate 0 authority, mind-map semantics, runtime flags, databases, live host state or cognitive/action authority separation.

---


## 59. Adaptive Study — Knowing When to Stop Building and Re-examine the System (28 November 2026)

**Purpose:** make the transition between study, development and observation an explicit adaptive capability of the NEX development process. This is a method for human-led repository work; it is not a runtime agent, autonomous authority, new NEX mechanism or roadmap amendment.

### The principle: study is triggered by evidence, not by the calendar

A development process that only follows a task queue will keep implementing even after its understanding has become stale. A process that studies continuously without a decision rule can become paralysed by analysis. NEX development needs a responsive transition between modes.

The question at every meaningful checkpoint is:

**"Is our current understanding still strong enough to justify the next change, or has something happened that makes renewed study more valuable?"**

Do not wait for a user to say "study again" when the repository evidence already shows that the next implementation would rest on a weak or outdated model. Equally, do not interrupt a well-understood, bounded change merely to repeat research that cannot change the decision.

### 1. Three operating modes, one continuous process

**STUDY — reduce consequential uncertainty.**
Enter Study when the system, evidence or causal explanation is not understood well enough to justify the next action. Trace source, ownership, data flow, authority, lifecycle, consumers, tests and deployment assumptions. Compare competing explanations and seek disconfirming evidence. Study can end in a code change, a test, a design correction, a deliberate non-change or a recorded unknown.

**DEVELOP — change a demonstrated invariant or test a valuable hypothesis.**
Enter Develop when the relevant contract is sufficiently understood, the change is bounded, the authority boundary is clear, and validation can discriminate success from failure. Implement one coherent increment with explicit ownership and rollback.

**OBSERVE — let evidence accumulate and check the consequences.**
Enter Observe after a change, integration, configuration change or surprising test result. Inspect exact-head CI, test behaviour, adjacent paths, downstream effects, regressions and operational evidence. Observation is not passive waiting: it checks whether reality matches the prediction.

These are not sequential project phases. They are operating modes that can recur within one task. A change may move STUDY → DEVELOP → OBSERVE → STUDY → DEVELOP more than once.

### 2. Study-trigger signals

At every completed increment, CI result, integration boundary and material surprise, evaluate these signals. A strong signal can trigger Study immediately; several weaker signals together can also justify it.

**A. Prediction failure**
- The implementation behaves differently from the stated hypothesis.
- A test passes, but the reason it passes is unclear.
- A failure occurs outside the changed path.
- The observed downstream effect differs from the predicted effect.
- A regression appears after an apparently unrelated integration.

**B. Model staleness**
- New source paths, consumers, owners, flags or lifecycle stages are discovered.
- The architecture map no longer describes the real call graph or boot order.
- A builder's contract differs from the pattern assumed from another builder.
- A previously documented fact is contradicted by current source or CI.
- The active branch, main revision, manual or governing evidence has moved.

**C. Uncertainty outruns consequence**
- A proposed change has broad, irreversible or cross-subsystem effects but weak evidence.
- Authority, ownership, persistence or failure recovery is unclear.
- The same data has multiple possible meanings or competing consumers.
- A cognitive interpretation is being mistaken for an operation, permission or execution decision.
- Host configuration, feature activation or runtime behaviour is unknown and materially affects the decision.

**D. Repeated friction**
- Similar defects recur in different subsystems.
- Fixes repeatedly require exceptions to the same assumed pattern.
- Tests are increasingly brittle, timing-dependent or disconnected from real contracts.
- Workarounds accumulate around an unexplained root cause.
- A task keeps expanding because each local fix exposes another unexamined dependency.

**E. Weak learning yield**
- Several changes add activity without demonstrating downstream value.
- A mechanism is present but its output is unconsumed or unmeasured.
- The same investigation is being repeated without new evidence.
- More implementation would add complexity before resolving the question that determines whether it is needed.
- A simpler existing mechanism may already solve the problem.

**F. Boundary and governance signals**
- A proposed action may affect frozen S-01–S-25/M1.8, the Master Roadmap, Phase 0/Gate 0 or another approval boundary.
- A change could alter the distinction between cognition, typed operation, capability, approval, execution and verification.
- A Mind Aspect is being treated as an action gate because of its descriptive map position.
- An extrapolated obligation, score, AI recommendation or test result is being treated as authority.

A governance or authority ambiguity is a hard Study trigger: do not implement across it until the boundary is resolved by the appropriate authority.

### 3. A practical decision rule: the Study Gate

Before the next non-trivial implementation, ask five questions:

1. **Do we know what is actually happening?** Have we traced the real source path, caller, consumer, owner and lifecycle?
2. **Can we explain why it is happening?** Are plausible alternatives and at least one disconfirming observation identified?
3. **Do we know what must remain true?** Is the invariant and authority boundary explicit?
4. **Can we recognise success and failure?** Is there a baseline, a discriminating test or a clearly stated evidence limitation?
5. **Would another hour of study plausibly change the implementation decision?** If yes, study first; if no, proceed with the smallest justified change or record the remaining uncertainty.

Decision:
- If questions 1–4 cannot be answered for a consequential change, enter STUDY.
- If a governance boundary is uncertain, pause implementation and seek the correct authority.
- If the first four are sufficiently answered and the fifth is no, enter DEVELOP.
- If a change has just landed or evidence is arriving, enter OBSERVE before selecting the next task.
- If the next step depends on unavailable host evidence, stop speculative implementation and define the exact observation required.

This is a judgement protocol, not a numeric score. Do not invent a confidence percentage or use an arbitrary timer to disguise uncertainty.

### 4. Study intensity should scale with risk and surprise

Use the smallest study intervention that resolves the uncertainty:

- **Light refresh:** reread the changed function, its callers and direct tests. Appropriate when the change is isolated and predictions held.
- **Neighbourhood study:** trace adjacent producers, consumers, ownership and lifecycle. Appropriate when a connection or subsystem boundary changed.
- **Subsystem study:** reconstruct the relevant call graph, state transitions, failure and recovery paths, and test coverage. Appropriate after repeated friction or unexpected integration behaviour.
- **System study:** revisit boot order, cross-subsystem ownership, authority boundaries, persistence, global configuration and operational assumptions. Appropriate when the local explanation repeatedly fails or the proposed change has system-wide consequences.

Do not automatically expand a local surprise into a full-system audit. Escalate the scope only when evidence points beyond the current boundary.

### 5. Prevent mode oscillation and analysis paralysis

A study trigger should change the next action, not restart the entire project.

- Name the exact uncertainty that triggered Study.
- Define what evidence would resolve it.
- Bound the study to the smallest relevant neighbourhood first.
- Keep implementation tasks that remain independently justified separate.
- Return to Develop when the decision-relevant uncertainty is resolved, not when every unknown in NEX has disappeared.
- If evidence is unavailable, record the unknown and its consequence; do not endlessly investigate around the missing evidence.
- If study produces no new evidence and cannot change the decision, stop and proceed cautiously or defer.

One surprise can justify a pause; it does not automatically justify a redesign. Conversely, repeated surprises in supposedly independent components are evidence that the shared mental model may be wrong.

### 6. The learning pulse after every increment

After each material code change, test result or integration, write a short pulse:

- **Expected:** what we predicted would happen.
- **Observed:** what source, tests, CI or host evidence actually showed.
- **Delta:** what differed, including the absence of an expected effect.
- **Confidence:** what is now better established and what remains uncertain, using words rather than false precision.
- **Scope:** which architecture maps or assumptions became stale.
- **Next mode:** STUDY, DEVELOP or OBSERVE, with one sentence explaining why.

This makes the development process responsive to its own evidence. It also prevents a successful test from silently becoming proof of a broader claim than it supports.

### 7. The adaptive loop

`ORIENT → STUDY (when triggered) → FORM HYPOTHESES → PROBE → DEVELOP (when justified) → OBSERVE → LEARNING PULSE → REASSESS MODE`

The loop may move directly from Study to Observe when the correct result is no code change. It may return from Observe to Study when a prediction fails. It may remain in Develop for a small sequence of tightly coupled edits only while the invariant and causal model remain stable.

**Do not use the number of commits, elapsed time, code volume or an empty task queue as the primary reason to change modes.** Use prediction accuracy, evidence quality, model staleness, consequence, reversibility and information gain.

### 8. What this means for the NEX development assistant

The assistant must not merely execute the next item in a backlog. It must continually assess whether its understanding remains adequate for the proposed next action.

At each checkpoint it should:
- compare current source and CI against the previous evidence snapshot;
- notice when a new discovery invalidates an earlier architectural assumption;
- distinguish a local implementation gap from a deeper model gap;
- proactively recommend Study when a trigger is present, even if the user asked to continue development;
- continue independent, well-understood work where safe rather than freezing everything;
- state what it knows, what it inferred, what it does not know and what evidence would resolve the uncertainty;
- never claim host observation from repository or CI evidence alone;
- ask the founder only when a genuine authority, priority or unavailable-context decision requires it.

The assistant should be willing to say: "The next code change is not yet justified. We have discovered that our model of this subsystem is incomplete; here is the smallest study that will resolve it." It should also be willing to say: "The study gate is satisfied. Further research is unlikely to change this bounded fix; I am proceeding."

This is adaptive judgement, not autonomous project authority. The founder's governance and approval boundaries remain intact.

**Unchanged boundaries:** this chapter adds no runtime mechanism, scheduler, score, database, feature flag, cognitive authority or permission. It does not modify frozen S-01–S-25/M1.8, the Master Roadmap, Phase 0/Gate 0 or the action-authority separation.

---

## 60. Boot-Time Ownership — AppState Before Producers (28 November 2026)

### Why the study boundary moved

The recent transactional-startup fixes for the World Model, Membrane and Fountain were separate, justified increments. Their repetition exposed a wider question: even if each builder can roll back its own partial start, who owns workers that have already started when a later boot step fails before the application has constructed its shutdown registry?

This is a deliberate return to study, not scope drift. The evidence changed from several local builder defects to a common boot-orchestration boundary in `run.py`.

### Source observations

- Writers start worker threads during construction, before the original `AppState` was created.
- The original `AppState`, its `atexit` cleanup registration and the normal graceful signal handler were established late, after multiple producer startup paths.
- The direct `run.py` starts already corresponded to fields understood by `AppState`. The defect was that ownership was published too late, not that a second process-wide supervisor was missing.
- Internally-started builders still need their own transactional rollback because the caller cannot publish an object it has not yet received.
- SignalLoop was the remaining internal-start boundary after the Scheduler, Dynamic, World Model, Membrane and Fountain rollback increments.
- The decoder thread was the only direct `Thread.start()` call left in `run.py`; it is now represented as an AppState-owned worker and started through `_own_and_start`.

### Candidate ownership sequence

1. Construct Writers and Readers, with bounded cleanup for Writers already constructed if setup fails.
2. Construct `AppState` immediately and register its close callback before starting producers.
3. Publish each directly-started worker into its AppState field before calling its start method.
4. On explicit start failure, request stop and perform a bounded join; keep the reference in AppState for final cleanup if the first rollback cannot finish.
5. For internally-started builders, keep rollback inside the builder. Publish the returned owner immediately, then check for a latched boot-shutdown request.
6. Preserve one absolute shutdown deadline from the original signal through producer quiescence and Writer draining.
7. Install normal clean-shutdown semantics only after the application object is constructed. A boot abort deliberately does not write the clean marker.

### Signal handling during boot

A boot-time SIGINT/SIGTERM handler latches a request rather than closing Writers underneath a builder that may still be starting. The current synchronous startup operation is allowed to return; the next safe checkpoint unwinds startup. Builder/helper rollback runs first, then `atexit` invokes the early-registered AppState cleanup. This avoids concurrent cleanup of a builder's partially-started resources.

This means a signal can be delayed until the current builder returns. That trade-off is explicit and remains subject to host timing validation.

### Regression evidence in the candidate

- AST checks require the single AppState construction and `atexit` registration to precede producer startup paths.
- Failure injection verifies ownership is published before a direct worker start and that a thread which starts before raising is stopped and joined.
- A boot-shutdown request injected during a start call must unwind through the helper and quiesce the worker.
- AppState must honor the absolute deadline latched at the boot signal.
- SignalLoop uses a start gate so a failed `Thread.start()` cannot enter the detector loop body; its regression injects a failure after the OS thread has been created.
- The decoder uses the same owner-before-start helper; its regression injects a failure after thread creation and verifies the stop Event is set and the worker is joined.

### Boundaries and unresolved evidence

- This is repository source/test work, not a live host or robot shutdown rehearsal. Real SIGTERM delivery, service-manager timeouts, SQLite contention and hardware startup timing remain unknown.
- A synchronous builder can delay the response to a boot-shutdown request until its next checkpoint.
- Partial Writer cleanup covers constructors that returned and were published in the local registry. A failure inside a Writer constructor after an OS thread exists but before the constructor returns is handled by merged PR #424 (§62), with exact-head full-suite validation.
- SIGKILL, power loss and process abort cannot be handled by Python cleanup.
- No process-wide thread census, new runtime flag, database, cognitive mechanism, Mind Aspect action authority or frozen-spec change is introduced.

### Current status

**Merged:** PR #420, merge commit `bf5dbbed66fc0d4884471420998823f658aedc7b`. Exact-head workflow run `46144422152` passed **3,058 tests, 7 skipped, 86 subtests**; baseline check OK and the isolated sandbox probe passed. The initial run on `fa2116ecd9404011072a536a74c200c42b872777` had one stale AST assertion failure; the corrected test now recognises decoder ownership through `_own_and_start`. The merged implementation is the boot ownership baseline. It has not been validated by a live host/robot SIGTERM rehearsal; real signal delivery, service-manager timeouts, SQLite contention and hardware startup timing remain unknown.


## 61. G-92 reviewed seed bridge and CLI — implementation status correction (28 November 2026)

**Source snapshot:** `main` at `dd0f2c32bb5669d85a9b01bdf4cdc5636cc3f96f`. The RDO bridge, CLI, tests and README files listed below are blob-identical to the reconciled PR #416 exact-head source at `e6d19453e0ec63447d0f0b7fca85ffcd3eef1d1a`. Exact-head CI run `46140753232` passed **3,051 tests, 7 skipped, 86 subtests**; baseline check OK. This correction supersedes the older §43/§48 statements that the bridge/CLI did not yet exist. Section 48 remains the historical first proposal-lifecycle increment.

### Implemented surface

The current `rdo/__main__.py` exposes six provider-neutral seed lifecycle commands:

- `seed-propose`: append candidate seed alternatives against an exact raw-objective snapshot.
- `seed-review`: append an explicit decision selecting an existing alternative.
- `seed-history`: inspect raw-objective revisions and append-only review events.
- `seed-selection`: retrieve an alternative only after explicit approval.
- `seed-prepare`: read-only mapping of the approved selection into a validated `objective.v1` candidate with graph diagnostics and lineage.
- `seed-intake`: explicitly persist the approved objective and proposal lineage, then run advisory RDO planning.

The source is `rdo_adapters/reviewed_seed_bridge.py`; the CLI is documented in `rdo/README.md` and `rdo/REVIEWED_SEED_BRIDGE.md`. Regression coverage includes `rdo/tests/test_seed_proposal_cli.py` and `rdo/tests/test_reviewed_seed_bridge.py`. The cross-layer lineage regression also verifies Stage-7 handoff provenance and non-execution authority.

### Integrity and authority boundaries

- Preparation validates the exact approval event, raw-objective digest, selected alternative identity and proposal lineage. It writes neither ledger and starts no planning.
- Intake appends the validated objective and its lineage together in one objective revision record. A retry reuses the same proposal lineage and CycleStore identity rather than creating another objective revision.
- Structural diagnostics reuse Tarjan SCC and the existing cycle/tension machinery. If a cyclic component exceeds 7 nodes or 18 internal cycle edges, detailed classification remains UNKNOWN rather than attempting unbounded simple-cycle enumeration.
- Intake runs the existing advisory `run_cycle` with no authorised gates. It does not create a Stage-7 handoff, execute generated code, activate runtime policy, or write to live NEX runtime state.
- Candidate seed interpretations still originate from an external human/provider submission. The lifecycle does not itself supply an integrated provider or an autonomous raw-idea-to-seed compiler.
- The separate candidate expansion-rule lifecycle is already implemented by merged PR #352 (rdo_adapters/rule_proposals.py and rdo/tests/test_rule_proposals.py; merge commit 60cc178ba1f3c895651c86ad95345c98fd5a2198). It binds proposals to a fingerprint of the active rule/terminal catalogue, preserves applicability, assumptions, exceptions, anti-requirements, alternatives, evidence, disconfirmations and positive/negative test plans, and records append-only review decisions. Even approved_for_catalogue remains inert: no activation API or dynamic loading exists, and EXPANSION_RULES changes only through a separate reviewed code change and tests.

### Updated G-92 disposition

**G-92 is partially closed, not complete.** Both candidate lifecycle layers now exist: seed alternatives can be proposed/reviewed and explicitly bridged into objective.v1 intake; novel-kind rule proposals can be recorded/reviewed without activation. The explicit approved-seed → objective.v1 → persisted cycle → resume → Stage-7 handoff lineage path is already covered by rdo/tests/test_reviewed_seed_bridge.py::test_approved_seed_lineage_survives_objective_cycle_resume_and_stage7. The handoff is a separate explicit operation, not an automatic side effect of intake. The remaining gap is upstream raw-idea-to-seed formulation: seed alternatives still require an external human/provider; there is no integrated provider or autonomous raw-idea compiler. Planning remains advisory, and objective-context mapping and criterion verification retain their separate evidence/review path. A rule approved for catalogue consideration still requires a separate ordinary source change, tests and CI before it can enter the active catalogue. No provider is inferred, no rule is automatically promoted, and no execution authority is created.

This update corrects the development status only. It does not create a new rule, activate a candidate, create a Stage-7 handoff, authorize execution, or change frozen S-01–S-25/M1.8, the Master Roadmap, Phase 0/Gate 0 or Phase 1 authority.

## 62. Writer constructor rollback after partial thread creation — merged PR #424 (28 November 2026)

**Source snapshot:** current main after merged PR #420 (`bf5dbbed66fc0d4884471420998823f658aedc7b`), #422 (`870d16359084db56de6e117aa90a8212abcb6350`), #423 (`c374185338070aeb2653227c04c487ef11fd5e6c`) and #424 (`b604ddfe4949b504196e005399c602677af157bd`). The final Writer rollback change was squash-merged from the rebased PR #424 branch.

### Source-derived gap and correction

`Writer.__init__()` calls `start()`. If `Thread.start()` raises after the OS thread has actually been created, construction raises before returning the Writer instance while its daemon worker may remain alive. The bounded correction catches startup failure, closes admission, queues the existing shutdown sentinel, and joins for at most 10 seconds while preserving the original exception. A worker that outlives rollback remains referenced and admission remains closed; a later retry cannot create a second concurrent writer. Once the worker exits, the stale sentinel is discarded and a fresh queue is used. Failure before OS thread creation leaves the object restartable.

### Regression coverage

Four deterministic cases cover: post-OS-start exception and worker rollback; pre-thread-creation failure and retry; worker database-open failure during caller-side start failure; and bounded rollback timeout, retained worker reference, and later retry without a stale sentinel. The timeout regression also asserts the rollback flag, sentinel flag and queue are clean before retry.

### Integration boundary

This is complementary to merged PR #420: #424 owns the individual partially started Writer, while #420 owns already-created producers during boot before AppState takes over. **Merged:** PR #424, merge commit `b604ddfe4949b504196e005399c602677af157bd`. Exact-head workflow run `46145202367` passed **3,064 tests, 7 skipped, 86 subtests**; baseline check OK and isolated sandbox probe passed. The mind-map check reports `p1_continuity` source drift because `substrate/writer.py` changed after its 2026-11-27 verification; this is an evidence-refresh item, not a failed test. No live dual-writer or host/robot runtime rehearsal is claimed.

**Unchanged boundaries:** no Writer transaction semantics, schema, runtime configuration, frozen S-01–S-25/M1.8, Master Roadmap, Phase 0/Gate 0, Phase 1 authority, descriptive Mind Aspect role, or cognitive/action authority separation is changed.

---

## 63. Rule-proposal ledger append durability and replay validation — merged PR #423 (28 November 2026)

**Merged:** `c374185338070aeb2653227c04c487ef11fd5e6c`. Candidate branch head `df33ed8140b08fa10f28988268fe018222a2a2bf`; exact-head workflow run `46144136825` passed **3,054 tests, 7 skipped, 86 subtests**; baseline check OK and the isolated sandbox probe passed.

### Source-derived corrections

- Validate the prospective event against the complete replay snapshot while holding the exclusive ledger lock, before writing bytes.
- Apply the configured byte limit to the encoded append, not merely the pre-existing ledger size.
- After first creating the ledger, fsync the file and then its parent directory so the directory entry is included in the durability boundary.
- Regression coverage verifies parent-directory fsync and that a malformed prospective event appends no bytes (the empty ledger file may exist).

This is a narrow integrity/durability correction to the existing append-only rule-proposal ledger. It does not change event schemas, review decisions, catalogue activation, execution authority or live runtime behavior.

**Unchanged boundaries:** no frozen S-01–S-25/M1.8, Master Roadmap, Phase 0/Gate 0, Phase 1 authority, cognitive/action authority or runtime feature-flag design is changed.

---

## 64. Provider-neutral CLI for inert expansion-rule proposals — merged PR #432 (28 November 2026)

**Merged:** [PR #432](https://github.com/kron777/Nex_v5.0/pull/432), merge commit `e29c6d8e2a8a486a54272445baab58ff5b1c5610`. This exposes the already-implemented `RuleProposalStore` lifecycle through three commands: `rule-propose` submits an exact-schema request/candidate envelope; `rule-review` appends an explicit review decision; and `rule-history` inspects proposals/events with an optional proposal filter. The default ledger remains `rdo/.cycles/rule_proposals.jsonl`.

The commands reuse the existing store and its catalogue fingerprint, schema validation, append-only hash chain, exclusive locking, prospective-event replay validation and fsync behavior. No second ledger or rule engine is introduced. The JSON envelope rejects unknown fields and duplicate JSON properties before store access. Proposer/reviewer labels remain caller-attributed, not identity-authenticated. The request is sourced from the RDO novel-kind frontier; the candidate remains human/external-provider supplied. The CLI persists and reviews proposals but does not invoke a model or implement an autonomous raw-idea-to-rule generator.

**Authority boundary:** `approved_for_catalogue` remains inert. No activation, dynamic loading, generated-code execution, catalogue mutation, runtime action or authority grant is exposed. The only route into `EXPANSION_RULES` remains a separate reviewed source change with tests and CI.

**Validation:** new `rdo/tests/test_rule_proposal_cli.py` covers command routing, review fields, filtered history, exact input-field and duplicate-key rejection before store access, and a real-ledger end-to-end check that approval leaves `EXPANSION_RULES` unchanged. Exact-head workflow run `46146066321` passed **3,068 tests, 7 skipped, 86 subtests**; baseline check OK and isolated sandbox probe passed. The mind-map warning for stale `p1_continuity` anchors is addressed by merged PR #437.

**Unchanged boundaries:** no frozen S-01–S-25/M1.8, Master Roadmap, Phase 0/Gate 0, Phase 1 authority, or cognitive/action authority is changed.

---

## 65. P1 continuity evidence refresh after Writer rollback — merged PR #437 (28 November 2026)

**Merged:** `af52387c3a0d3bc6f041b6d4d9413c74944adc68`. The `p1_continuity` node's source anchors now cite `substrate/writer.py:58-213` and `:214-375`, with `last_verified: 2026-11-28`. The note records the merged PR #424 partial-start rollback and its exact-head tests while preserving the existing preventive-vs-detective distinction and FAIL falsifier: rollback protection does not detect two writers claiming the same subject.

Exact-head workflow run `46146816088` passed **3,068 tests, 7 skipped, 86 subtests**; baseline check OK and isolated sandbox probe passed. Mind-map verification reports 30 nodes, 0 unverified, 12 dark and 2 blocked. The stale `p1_continuity` warning is cleared. Remaining warnings are two missing doctrine reference files (`VIRTUE_SLATE.md`, `mental_factors_inventory_alobha_spec.txt`) and the overdue `p13_finitude` unblock dated 2026-11-21; they remain visible and unmodified.

No live dual-writer or host/robot rehearsal is claimed. The mind map remains descriptive and has no action-control authority.

---

## 66. Objective intake first-revision directory durability — merged PR #438 (28 November 2026)

**Merged:** PR #438, merge commit `6de891fe128e144bc4428eb6a78b4f45c09decf7`. `ObjectiveInputStore.append()` now fsyncs the containing directory after the first `<objective_id>.jsonl` entry is created. A file fsync protects file contents; the additional directory fsync includes the new directory entry in the durability boundary.

**Bounded correction:** while holding the per-objective exclusive lock, detect first creation; append and fsync the revision file; then fsync the containing directory. Later revisions retain the existing file-only fsync behavior. The immutable revision schema, SHA-256 chain, lineage checks, locking and replay semantics are unchanged.

**Regression coverage:** `rdo/tests/test_objective_intake_durability.py` verifies first creation fsyncs the file then the parent directory, while a later revision fsyncs only the existing file. README records the durability boundary. Exact-head workflow run `46147315394` passed **3,070 tests, 7 skipped, 86 subtests**; baseline check OK and isolated sandbox probe passed. That branch's mind-map check still emitted the stale p1 warning because its base preceded merged PR #437; the current mainline has the refreshed evidence recorded in §65.

**Boundaries:** no objective schema, approval, planning, Stage-7, execution, runtime state, frozen S-01–S-25/M1.8, Master Roadmap, Phase 0/Gate 0 or cognitive/action authority is changed. No live database or host process was accessed.

---

## 67. Objective intake symlink and special-file path rejection — merged PR #439 (28 November 2026)

**Source-derived gap:** unlike the seed and rule-proposal stores, `ObjectiveInputStore` previously opened objective revision and lock paths without rejecting symlinks. A dangling ledger symlink could be treated as an empty history, and an existing symlink could redirect reads/appends outside the configured store directory. FIFO/device paths could also block or behave unlike regular ledger files.

**Bounded correction:** centralize safe opens for objective ledger and lock files. Reject symlinks before open and use `O_NOFOLLOW` where supported to close the check/open race; use non-blocking opens and require regular files so FIFOs and other special files are rejected. Preserve the existing per-objective flock, append-only revision chain, file/directory fsync, lineage validation and replay behavior.

**Merged:** PR #439, merge commit `51509a93aa204fe6fb34b75a88d0b3edec455e70`. Exact-head workflow run `46148127739` passed **3,074 tests, 7 skipped, 86 subtests**; baseline check OK and isolated sandbox probe passed. Mind-map verification reports 30 nodes, 0 unverified, 12 dark and 2 blocked; the `p1_continuity` warning remains cleared. Remaining warnings are the two missing doctrine references and overdue `p13_finitude` unblock, unchanged.

**Boundaries:** no objective schema, revision hash-chain, approval, planning, Stage-7, execution, runtime state, frozen S-01–S-25/M1.8, Master Roadmap, Phase 0/Gate 0 or cognitive/action authority is changed. No live database or host process was accessed.

---

## 68. Consistent seed and rule proposal history snapshots — candidate PR #441 (28 November 2026)

**Source-derived race:** the `rule-history` and `seed-history` CLIs previously called `proposals()` and `events()` separately. Each call acquired a valid shared ledger read, but a concurrent review append between those reads could produce a response whose proposal status and event list described different ledger revisions.

**Bounded correction:** `RuleProposalStore.history()` and `SeedProposalStore.history()` each read and validate their append-only ledger once, derive proposal state and filtered event rows from that same snapshot, and return both together. Both CLIs now use these APIs. Optional proposal-ID validation and unknown-ID errors remain explicit.

**Regression coverage:** `rdo/tests/test_rule_proposals.py` and `rdo/tests/test_seed_proposals.py` assert each history operation reads its ledger once and returns a review status consistent with the event sequence. Both CLI routing tests exercise the snapshot-based methods. Original implementation/test head `611ad5f6aff4c1aea44574fb9defae8a80309def` passed exact-head workflows `46149016907` and `46149041938`, each with 3,076 passed, 7 skipped and 86 subtests. The rebased integration branch includes the later #442 duplicate-key guard and requires its own exact-head run; no pass is claimed for that combined head.

**Boundaries:** read-only reporting only. No proposal schema, review semantics, rule-catalogue activation, action authority, runtime state, frozen S-01–S-25/M1.8, Master Roadmap or Gate 0 boundary changes.

---

---

## 69. Reject duplicate JSON keys in seed proposal CLI input — merged PR #442 (28 November 2026)

**Source-derived gap:** `seed-propose` used the default `json.load()`, which silently accepts duplicate object keys and retains the last value. The parallel `rule-propose` path already rejected duplicates, including nested objects.

**Bounded correction:** route seed proposal input through the shared recursive duplicate-key hook. The hook raises `ValueError`, which both CLI paths report as a concise input error with exit code 2. Duplicate keys are rejected before the proposal store is opened.

**Regression coverage:** `rdo/tests/test_seed_proposal_cli.py` covers duplicate top-level and nested properties and asserts the store is never accessed. Existing rule-proposal duplicate-key coverage remains in place. **Merged:** PR #442, merge commit `4ede2994e5177ad6b56211ddc0f91c274222caaa`. Exact-head workflow run `46151854310` passed **3,075 tests, 7 skipped, 86 subtests**; baseline check OK and isolated sandbox probe passed.

**Boundaries:** no seed schema, proposal/review semantics, provenance, approval, intake, planning, Stage-7, execution authority or runtime behavior changed.

---

## 70. Single-snapshot seed and rule proposal history — merged mainline commit `18c8f06171e1de35c3210831a49b63d0e2487af0` (PR #443; 28 November 2026)

**Finding addressed:** the `rule-history` and `seed-history` command paths previously assembled proposal state and event history through separate ledger reads. A review append between those reads could make the two parts of one response represent different ledger revisions.

**Implementation now present on main:** `RuleProposalStore.history()` and `SeedProposalStore.history()` each call the ledger reader once, derive the proposal snapshot from that returned event sequence, and select the matching event rows from the same sequence. Both history CLI handlers delegate to this store-level operation. This narrows the consistency boundary to one ledger snapshot; it does not claim a transaction across separate stores or a global snapshot of NEX.

**Evidence:** commit `18c8f06171e1de35c3210831a49b63d0e2487af0` is the latest commit returned by the repository-scoped commit search. The diff includes store-level history methods, CLI delegation and tests asserting one ledger read and agreement between the resulting review status and event sequence. The combined-status lookup returned no status rows for this commit; therefore this manual makes **no exact-head CI-pass claim** for #443. Earlier implementation/test-head workflow results recorded under §68 are not substitutes for the rebased/integrated #443 head.

**Study interpretation:** this is a useful example of a general NEX integrity rule: when a response combines a derived state view with its event history, derive both from the same immutable-in-memory read snapshot. The lock/read mechanism remains the store's responsibility; this change does not establish cross-process behaviour beyond what the underlying reader and its tests demonstrate.

**Next research seam — concurrency falsification:** add or inspect a deterministic interleaving test in which a review append is attempted while `history()` is reading. Establish whether the lock provides the intended consistent read on the actual supported filesystem/process model, and whether the reader returns either the pre-append or post-append state without mixing them. Prefer a barrier-controlled test over timing sleeps. Include a second-process test only if the store's supported deployment model requires cross-process access. Do not call this a discovered defect until the test or source establishes one.

**Unchanged boundaries:** no proposal schema, approval meaning, catalogue activation, generated-code execution, runtime action authority, frozen S-01–S-25/M1.8, Master Roadmap, Phase 0/Gate 0, Phase 1 authority or cognitive/action authority separation is changed. Proposal approval remains inert and does not activate a rule.

---

## 71. Stage-2 attention propagation and downstream selection — source/test seam study (28 November 2026)

**Question studied:** does an external perception merely update a local attention value, or can that value reach the later Fountain branch choice and Global Workspace framing? The negative control is equally important: internal telemetry is recognized for self-monitoring but must not monopolise cognitive attention.

### Source-traced chain

1. `theory_x/stage2_dynamic/attention.py` maps streams to branches and computes magnitude. The source explicitly returns zero for every `internal.*` stream, preserving the separation between internal self-monitoring and attention steering.
2. `theory_x/stage2_dynamic/pipeline.py` runs A–F: unpack event, match branches, calculate magnitude, apply membrane aperture, assign valence, then call `BonsaiTree.attend()` and log an F event when magnitude is at least 0.001.
3. `theory_x/stage2_dynamic/bonsai.py` updates branch focus and texture from the admitted magnitude. This is the stateful attention representation.
4. Fountain's production caller sorts the status branch vector by focus and passes the hottest branch through `_weighted_branch_pick()`. With `NEX5_BRANCH_TEMP` unset/zero, the hottest branch is preserved; with a positive temperature, a softmax roulette can select a lower-focus branch.
5. Global Workspace's production `arbitrate()` obtains a Bonsai candidate through `_bonsai_candidate(status)` and competes it against other candidates. The candidate is omitted when the hottest branch has focus at or below 0.1. The separate `arbitrate_candidates()` helper selects the highest-salience frame.

### Existing characterization and what it proves

The current `tests/test_dynamic.py` contains three useful tests:

- An `internal.proprioception` event is matched to `systems` but has zero magnitude, produces no Stage-2 F hit, leaves focus/texture unchanged and yields no Bonsai workspace candidate.
- An external `ai_research.arxiv` event increases the `ai_research` branch's focus and texture through the real A–F pipeline.
- Forty external events produce an `ai_research` focus above 0.1; the test checks the hottest branch, the zero-temperature Fountain helper, the positive-temperature roulette's forced final bucket, and the Bonsai candidate/frame helpers.

This is materially stronger than checking module existence: it exercises the real Stage-2 pipeline and several downstream selection functions with isolated objects. It is still **layered characterization**, not a complete live-path demonstration. The Fountain assertion calls `_weighted_branch_pick()` directly rather than executing the full Fountain fire orchestration. The workspace assertion manually builds a status dictionary and calls `_bonsai_candidate()` plus `arbitrate_candidates()`; it does not call production `arbitrate()` with its database-backed surprise/momentum candidates. No production flag, live database or host process was changed or exercised.

### Research conclusion

The source supports a real functional path from external sense input to branch attention, and shows two downstream consumers of that representation. The test evidence establishes selected edges and helper semantics, not that a live NEX process is running these paths, that every relevant flag is enabled, or that the resulting cognition is beneficial. Internal telemetry's exclusion is a deliberate anti-starvation boundary; reconnecting it indiscriminately would risk the historical systems-branch pinning failure documented in the source.

### Next falsification study

Build a deterministic, isolated integration test that crosses the remaining seams without touching live runtime state:

- Use a temporary substrate/database and controlled branch status to invoke the production Global Workspace `arbitrate()` path. Provide competing momentum/surprise candidates and assert both the Bonsai-win and non-Bonsai-win cases; record the exact salience margin and tie behaviour.
- Exercise the actual Fountain caller around branch sorting and `_weighted_branch_pick()`, or extract a narrow pure selection function only if that reduces test coupling without changing semantics. Compare temperature zero with a controlled positive-temperature draw.
- Add a paired negative-control case for `internal.*` and a positive external event case. Keep event count, initial focus, decay and aperture fixed; avoid relying on unbounded sleeps or stochastic sampling.
- Separate causal claims: pipeline-to-focus, focus-to-Fountain pick, and focus-to-workspace frame are three independently falsifiable edges. A pass at one edge must not be reported as proof of the others.

Do not change `NEX5_BRANCH_TEMP`, workspace flags, attention magnitude policy or runtime wiring as part of this study. First establish what the existing tests and production call sites actually guarantee.

**Source anchors inspected:** `tests/test_dynamic.py` blob `7e7493a5d79dda73f0ff374728a3da9eb34a558c`; `theory_x/stage2_dynamic/pipeline.py` blob `fbac28e96ffc34dbf59c60242d3ac635835e6e06`; `theory_x/stage2_dynamic/attention.py` blob `d2765c7618e8421bb3e60c8898f749f2370f0344`; `theory_x/stage2_dynamic/bonsai.py` blob `d0389d6036deecf27dcf636771ef817c685b1e7c`; `theory_x/stage6_fountain/generator.py` blob `26061914b1dd80858c3568217cd1ef0c49ce2c51`; `theory_x/stage_tom/global_workspace.py` blob `39d833d4a88ed3ad371daf7b62e7295d0dda6637`.

**Unchanged boundaries:** no runtime code, live flag, attention policy, schema, frozen S-01–S-25/M1.8, Master Roadmap, Phase 0/Gate 0, Phase 1 authority, descriptive Mind Aspect policy or cognitive/action authority separation is changed.

---

## 72. Theory X registry lifecycle and AppState ownership — continuation study (28 November 2026)

**Question studied:** does the process-level SentienceNode registry actually have process-lifetime ownership, or does it also retain objects whose database handles and workers belong to an individual AppState?

### Registry contract found in source

At current main snapshot 18c8f06171e1de35c3210831a49b63d0e2487af0, theory_x/__init__.py defines a module-global _registered_nodes list. register(node) checks isinstance(node, SentienceNode) using a runtime_checkable Protocol, then appends the object. all_nodes() returns a new list containing the same object references.

The implementation has no visible duplicate-name/identity check, removal/unregister operation, registry lock, or owner token. The runtime-checkable Protocol check establishes attribute presence, not method signatures or semantic lifecycle correctness. These are source observations, not proof that a current production consumer is malfunctioning.

### Registration paths traced

- **Module import (gui/server.py):** constructs and registers one process-level FocalSet and one ExecutiveControl. These are module globals and are naturally aligned with process scope.
- **GUI build_state() path:** when with_tools is enabled and the relevant handles exist, constructs ProblemMemory, GoalManager and Metacognition using that build's Readers/Writers, then registers those objects. The function also constructs Writers and starts/builds several services before returning its AppState; it is not a pure data-only factory.
- **GUI create_app(state) path:** registers the supplied membrane's self_model and behavioural nodes when the Flask app is created. Repeated app construction can therefore repeat registration for the same or a different state.
- **Unified run.py boot path:** constructs its own AppState rather than calling build_state(). It registers SelfNarrative, the HoldingZoneResolver, GoalManager, Metacognition, NovelAssociation, SubstrateHarmonic, GeniusTagger, DriveEmergence and AffectState at their respective construction sites. create_app(state) subsequently registers the membrane-owned nodes. Several registration calls are wrapped in broad exception handling or silently ignored, so a construction log is not itself a registry-membership proof.

### Consumer inventory and lifecycle risk

The inspected run.py and gui/server.py contain registration calls but no call to all_nodes(). The registry's own docstring describes process-level monitoring and future cross-node orchestration. A complete repository-wide consumer inventory remains **incomplete**; do not claim that the registry is unused everywhere.

A concrete ownership mismatch is possible on repeated GUI factory/app construction: build_state() creates faculties bound to that invocation's Readers/Writers, while the module-global registry retains those object references beyond the lifetime of the returned state. AppState.close() quiesces its owned producers and closes its Writers, but no registry removal is visible in the reviewed lifecycle. Repeated build_state() or create_app() calls can therefore accumulate duplicate/stale entries. This is a **lifecycle risk derived from source**, not yet a demonstrated production failure; its impact depends on whether any consumer iterates the registry and invokes those objects after their owning state closes.

The normal run.py path constructs one AppState and one Flask app, so the repeated-factory scenario must not be presented as evidence of a current live failure. The process registry also contains objects that are not necessarily owned by AppState in the same way (for example, module-level FocalSet and ExecutiveControl). The ownership contract needs to distinguish these cases rather than simply clearing the registry on every close.

### Required next study — do not patch yet

1. Complete the repository-wide registration and consumption inventory: every register() call, every all_nodes() read, any alias/import of either, and all tests that depend on registry state.
2. Trace the full lifecycle of both construction routes: run.py → AppState → create_app and gui/server.py main → build_state → create_app. Include test fixtures and repeated app creation.
3. In isolated tests with separate temporary databases, build two states sequentially, register their nodes, close the first, and determine whether registry entries from the first remain reachable and whether any consumer calls them. Check identity, names, Reader/Writer ownership and worker shutdown; do not access live databases.
4. Decide the ownership model only after the inventory: process-singleton registry for true process-lifetime nodes; an AppState-scoped registry for state-bound nodes; or an explicit owner-aware registration/removal contract. Any future design must define duplicate handling, thread safety, close ordering and behavior when registration fails.
5. Add a deterministic regression test for the selected contract before changing implementation. Preserve the frozen doctrine/specification and do not create a cross-node orchestrator merely because the registry's docstring mentions one.

**Source anchors inspected:** theory_x/__init__.py blob 661dc737f54c88f763588606867ae1b9cd7e6654; gui/server.py blob ecaa6982544e883a50dbf85c5de1e10f74180c67; run.py blob 8ebe33c251e874b16107428eb4e92cf6301a4621. All are source snapshots at main commit 18c8f06171e1de35c3210831a49b63d0e2487af0.

**Unchanged boundaries:** no registry code, protocol, AppState lifecycle, runtime configuration, database, frozen S-01–S-25/M1.8, Master Roadmap, Phase 0/Gate 0, Phase 1 authority or cognitive/action authority separation is changed.

---

## 73. Separate cognitive-node registry from AppState shutdown ownership — lifecycle study (28 November 2026)

**Question studied:** does the existing shutdown machinery already provide an owner-scoped lifecycle model, and is it distinct from the process-level SentienceNode registry?

### Important distinction established

There are two different registries in this architecture and they must not be conflated:

1. **SentienceNode registry** — `theory_x/__init__.py` keeps a module-global list intended for process-lifetime cognitive nodes, with `register()` and `all_nodes()`. Doctrine §4 (Model A) explicitly distinguishes process-lifetime nodes from session-scoped WorkingMemory.
2. **AppState producer ownership** — `gui/server.py`'s `AppState._quiesce_producers()` keeps a bounded list of state-owned producers/workers. It signals stop methods/events, gathers joinable threads, joins against a shared deadline, and reports survivors/errors before `AppState.close()` closes Writers. Its own docstring explicitly says it is not a claim that every process thread is registered.

The second mechanism is an owner-scoped shutdown inventory, not a consumer of the SentienceNode registry. The source and tests show it is deliberately populated through AppState fields and run.py's `_own_and_start()` boot path.

### What existing tests establish

- `tests/test_appstate_close_runpy_producers.py` pins the four run.py-only producer handles and checks in-flight writes finish before Writer closure; it also source-checks the boot wiring and early AppState ownership.
- `tests/test_appstate_close_held_loops.py` covers membrane behavioural, NovelAssociation, AffectState, DriveEmergence and SocialPresence shutdown handling.
- `tests/test_appstate_close_joins_producers.py`, `test_appstate_close_quiesces_dynamic.py` and `test_appstate_close_runpy_writers.py` add other producer, dynamic-loop and writer shutdown coverage.
- `tests/test_focal_set.py` and `tests/test_executive_control.py` verify those two nodes satisfy the SentienceNode Protocol. These are conformance tests, not tests of registry membership, uniqueness, removal or owner lifecycle.

This is meaningful lifecycle protection for AppState-owned workers. It does **not** prove that the SentienceNode registry is owner-aware or that its contents are drained/removed on AppState close.

### Doctrine-to-implementation tension

Doctrine §4 says registered nodes are process-lifetime (FocalSet is the canonical example) and session-scoped WorkingMemory is kept outside the process registry. The Protocol documentation says node names are unique across all nodes, but `register()` currently only performs a runtime Protocol attribute check and appends. It does not enforce uniqueness. The registry also has no visible removal, owner association or lock.

Production boot code registers additional faculties that are constructed in the same process as an AppState and, in several cases, retain that state's database Readers/Writers or services: `SelfNarrative`, `HoldingZoneResolver`, `GoalManager`, `Metacognition`, `NovelAssociation`, `SubstrateHarmonic`, `GeniusTagger`, `DriveEmergence`, and the GUI membrane's `self_model` and `behavioural` nodes. The GUI `build_state()` route also registers ProblemMemory, GoalManager and Metacognition. The normal unified `run.py` boot constructs one AppState and one app per process, so this can be consistent with a process-lifetime contract in the intended deployment. It becomes a lifecycle concern if multiple AppStates/apps are built sequentially in one process or if a future registry consumer outlives the state that owns a faculty.

The registration calls in `build_state()` and several run.py paths suppress exceptions; other run.py paths log warnings. Therefore a boot path's construction of a faculty does not prove that registration succeeded. No reviewed source or test currently establishes an operational consumer that iterates `all_nodes()`; the inspected `gui/server.py` and `run.py` do not call it. Repository-wide consumer inventory remains open because the available code-search result was incomplete; do not state that the registry is unused.

### Updated design judgment — no patch yet

Do not simply clear the process registry in `AppState.close()`: module-level process-lifetime nodes such as FocalSet and ExecutiveControl must survive an AppState teardown if they are genuinely process-owned. Do not automatically move every registered node into AppState either: that would change the Doctrine's Model A scope and may conflate observability with worker shutdown.

Before choosing a design, finish the consumer inventory and establish whether the intended contract is:
- process-singleton cognitive nodes only, with state-bound faculties excluded;
- process registry plus explicit owner metadata and unregister/close semantics; or
- separate process and AppState registries with narrowly defined responsibilities.

Any design must specify unique-name enforcement, duplicate object handling, thread safety, registration failure reporting, owner-close ordering and behaviour during repeated app construction. A registry is metadata/observability, not an action authority or a new cross-node orchestrator.

### Next falsification work

1. Find every `register()` call and every direct/aliased `all_nodes()` consumer across the complete repository, tests, scripts and alternate entry points. Treat current GitHub code-search results as incomplete.
2. Determine whether `gui/server.py`'s `main()` invokes `build_state()` and `create_app()` exactly once in the intended process; distinguish this supported lifecycle from test/reload/multi-app usage.
3. Use isolated temporary databases to construct two AppStates sequentially, create apps, close the first, and inspect registry identity/name membership. Do not call methods on stale nodes until the source/test establishes whether a consumer does so.
4. Add tests only after selecting the contract: duplicate names, same-object re-registration, different-object same-name registration, repeated app creation, failed registration reporting, and process singleton preservation across AppState close.
5. Keep AppState producer shutdown tests separate; they prove worker quiescence and Writer ordering, not cognitive-node registry ownership.

**Source anchors inspected at main `18c8f06171e1de35c3210831a49b63d0e2487af0`:** `theory_x/__init__.py` blob `661dc737f54c88f763588606867ae1b9cd7e6654`; `theory_x/DOCTRINE.md` blob `6506276979364dc62da120d4b7c8966328fb2e6d`; `gui/server.py` blob `ecaa6982544e883a50dbf85c5de1e10f74180c67`; `run.py` blob `8ebe33c251e874b16107428eb4e92cf6301a4621`; `tests/test_appstate_close_runpy_producers.py` blob `6c9ec4ac0e88e56853963d378383789263d68e24`; `tests/test_appstate_close_held_loops.py` blob `a759bd71b4dbca1d82c04bd4eeb7a41b00c9ebe6`; `tests/test_focal_set.py` blob `083b8053ff09ef0975f8aab35a120904b2f55423`; `tests/test_executive_control.py` blob `d0ffe94a36e60cb30536759090affc09cfc1c3b1`.

**Unchanged boundaries:** no registry code, AppState lifecycle, Protocol, doctrine, database, runtime flag, frozen S-01–S-25/M1.8, Master Roadmap, Phase 0/Gate 0, Phase 1 authority or cognitive/action authority separation is changed.

---

## 74. Bonsai influence ceiling in the production Global Workspace — salience study (28 November 2026)

**Question studied:** does a Stage-2 attention increase merely reach Global Workspace, or can it actually win the competition that frames a Fountain fire?

### Production path confirmed

The source path is now traced beyond isolated helpers:

1. Stage-2 `run_pipeline()` updates the Bonsai tree's branch focus from admitted sense-event magnitude.
2. `DynamicState.status()` returns `tree.snapshot()["branches"]` as the branch vector, including each branch's `focus_num`.
3. Fountain's production `_generate()` obtains `dynamic_state.status()` and passes it to `_build_prompt()`.
4. With `NEX5_GLOBAL_WORKSPACE` unset or equal to `1`, Fountain's production prompt builder calls `global_workspace.arbitrate(dynamic_status, stakes_active=..., drive_line=...)`.
5. `_bonsai_candidate()` selects the highest-focus branch only when its focus exceeds 0.1 and offers salience `focus_num * _W_BONSAI`. The winner is prepended as a framing line to the Fountain focus block. Other module blocks still append later; this is framing competition, not exclusive control over all prompt content.

Therefore the attention-to-workspace path is present in the production call chain. The existing Stage-2 propagation test does not execute the entire `FountainGenerator._generate() → _build_prompt() → arbitrate()` chain; it tests the real Stage-2 pipeline, then directly tests the Fountain selection helper and workspace candidate/helper functions.

### Effective influence ceiling

The current source constants are:
- surprise: 1.00 × surprise score (admitted above its gate);
- stakes: flat 0.90;
- momentum: flat 0.55 by default;
- Bonsai: 0.50 × highest branch focus;
- drive: flat 0.45.

Bonsai focus is clamped to a maximum of 1.0 in `BonsaiTree.attend()`. Thus under the default, undemoted momentum weight, Bonsai's maximum salience is 0.50 and it cannot beat an active momentum candidate at 0.55. It can beat drive only when focus is strictly above 0.90, and it can lead when stronger candidates are absent. Surprise and stakes have higher ceilings.

**Configuration qualification:** `_teeth_momentum_factor()` returns 1.0 unless `NEX5_L4_TEETH=1`; when enabled it applies a factor of 0.6, reducing momentum from 0.55 to 0.33. Bonsai can then beat momentum above focus 0.66, provided no stronger surprise/stakes candidate wins. The deployment's actual flag state was not inspected. Do not report either branch of this conditional as live host behaviour without runtime evidence.

### What the existing analysis tool does — and does not — establish

`tools/check_arbiter_competition.py` is a read-only analyser for `NEX5_GW_LOG` decision records. Its own design explicitly separates:
- correctness of the logged effective argmax;
- departure from the nominal flat-weight ladder; and
- the genuinely variable/data-dependent region.

It also detects demoted momentum salience as a signal that L4 teeth may have been armed. Its docstring warns that the arbiter chooses a framing line over a fetch whose content was already fixed; it is an expression/framing instrument, not a content-quality measure. `tests/test_arbiter_competition.py` checks the Bonsai-versus-drive veto region, detection of L4 demotion and other readout cases. These tests validate the analyser's calculations with synthetic records; they are not evidence of live decision frequencies.

### Research conclusion

The earlier claim that attention "influences the workspace" is true but incomplete. Its influence is sharply bounded by the salience ladder and by the presence of stronger candidates. Without L4 demotion, the default momentum line is structurally unbeatable by Bonsai. With L4 demotion, Bonsai has a larger competitive region, but only if its focus is high enough and surprise/stakes do not outrank it.

The important architectural question is therefore not simply whether faculties are connected. It is whether the measured competition gives a faculty a meaningful opportunity to alter the frame, and whether that alteration improves the resulting output. The current source/tests establish the competition mechanics, not the quality benefit.

### Next falsification study

1. Add a deterministic integration test using an isolated temporary dynamic database and controlled Bonsai state. Exercise `DynamicState.status()`, the actual Fountain prompt-building caller and `global_workspace.arbitrate()` without touching production databases or external voice services.
2. Cover the default momentum-present case, momentum-absent case, L4-demoted case, drive-only case, and surprise/stakes blockers. Assert exact candidate vectors, winner and inserted framing line.
3. Keep `NEX5_GLOBAL_WORKSPACE`, `NEX5_L4_TEETH` and all production flags unchanged. Inject/patch only within the test.
4. If measuring whether the frame improves output, preregister a separate content-quality evaluation. Do not infer benefit from a higher Bonsai win rate or a successful framing insertion.

**Source anchors inspected at main `18c8f06171e1de35c3210831a49b63d0e2487af0`:** `theory_x/stage2_dynamic/__init__.py` blob `b1740d7957953ca06b54133f67af821bdc76200e`; `theory_x/stage2_dynamic/bonsai.py` blob `d0389d6036deecf27dcf636771ef817c685b1e7c`; `theory_x/stage6_fountain/generator.py` blob `26061914b1dd80858c3568217cd1ef0c49ce2c51`; `theory_x/stage_tom/global_workspace.py` blob `39d833d4a88ed3ad371daf7b62e7295d0dda6637`; `tools/check_arbiter_competition.py` blob `e7881f8246e474fad67c2639e69faefac2a3e1eb`; `tests/test_dynamic.py` blob `7e7493a5d79dda73f0ff374728a3da9eb34a558c`; `tests/test_arbiter_competition.py` blob `d744e47021164acae15490d722a2b030ce8b663e`.

**Unchanged boundaries:** no attention magnitude, Bonsai focus, salience weights, L4 teeth, runtime flag, Global Workspace policy, prompt generation, frozen S-01–S-25/M1.8, Master Roadmap, Phase 0/Gate 0 or cognitive/action authority is changed.

---

## 75. Supported boot-path cardinality for Theory X registry ownership — entrypoint study (28 November 2026)

**Question studied:** does the normal application startup create multiple AppStates/apps in one process, or is repeated construction only a factory/test/future deployment concern?

### GUI entrypoint

At main snapshot `18c8f06171e1de35c3210831a49b63d0e2487af0`, `gui/server.py` defines `main()` with one direct `state = build_state()`, one `atexit.register(state.close)`, and one `app = create_app(state)`, followed by `app.run(..., use_reloader=False)`. The source has no second call to either factory in this main path. Disabling the Flask reloader avoids the usual development-server parent/child re-import path for this entrypoint.

### Unified run.py entrypoint

`run.py` imports `AppState` and `create_app` from `gui.server`, then constructs its own `AppState` directly during `main()` startup. It does not call `gui.server.build_state()`. It registers `state.close` early, constructs/wires the faculties and producers, then calls `create_app(state, shutdown_gate=...)` once before `app.run(..., use_reloader=False, threaded=True)`. The existing `tests/test_appstate_close_runpy_producers.py` includes a source-level assertion that `run.py` contains one `AppState(` construction and that ownership registration precedes producer-start paths.

### Revised risk assessment

The normal supported startup paths are single-AppState/single-app per process. This supports the current Model A process-lifetime registry assumption for the intended deployment; it does not establish that repeated construction is a production failure. The remaining lifecycle question is narrower: if the GUI factory is reused, tests create multiple app states, or a future embedded/multi-app host builds multiple instances in one process, state-bound registered faculties can remain in the module-global list after their owning AppState closes. There is still no reviewed `all_nodes()` consumer establishing that such stale references are actively invoked. Treat this as a reuse/extension hazard, not an incident.

**Design consequence:** preserve the current single-instance production model while testing the registry contract explicitly. Do not add an owner-aware registry or change Doctrine Model A solely to accommodate unsupported multi-instance use. If multi-instance operation becomes a supported requirement, it must be designed and tested as a deliberate architecture change.

**Source anchors inspected at main `18c8f06171e1de35c3210831a49b63d0e2487af0`:** `gui/server.py` blob `ecaa6982544e883a50dbf85c5de1e10f74180c67`; `run.py` blob `8ebe33c251e874b16107428eb4e92cf6301a4621`; `tests/test_appstate_close_runpy_producers.py` blob `6c9ec4ac0e88e56853963d378383789263d68e24`.

**Unchanged boundaries:** no boot path, app factory, registry, AppState lifecycle, runtime configuration, doctrine, frozen specification, roadmap or cognitive/action authority is changed.

---

## 76. Attention-selected branch attribution and next-fire continuity — causal seam study (28 November 2026)

**Question studied:** after Fountain generates a thought, does the attention-selected branch affect only logging, or does it also enter continuity mechanisms that can influence later turns?

### Production path traced

The Fountain generator obtains the current Stage-2 status before prompt construction. After a thought is generated, it independently sorts the status branch vector by `focus_num` and selects `hot_branch` through `_weighted_branch_pick()`. With `NEX5_BRANCH_TEMP` unset/zero, the hottest branch is retained; a positive temperature enables a focus-weighted roulette selection.

The selected branch is:
- recorded in `recursion_attrib` and the later `fountain_events` record;
- used as `_carry_branch`, unless the optional `NEX5_RETRIEVAL_TEETH=1` fixation diversion selects another branch for carry;
- passed to `capture_momentum()` when `NEX5_MOMENTUM` is unset or `1` (the default), which stores branch plus the generated thought fragment in the single-row `momentum` table;
- passed to the optional Hot Observer when `NEX5_HOT_OBSERVER=1`.

The attention-selected branch is therefore more than an ephemeral score: it is persisted as attribution and as momentum metadata. However, timing matters: this `hot_branch` selection occurs **after** the thought has been generated. It cannot be claimed as the cause of that same thought's content.

### What can influence the next fire?

Two consumers must be distinguished:

1. **Global Workspace momentum candidate:** `global_workspace._momentum_candidate()` reads the momentum row's timestamp and `thought_fragment` and offers a flat-weight continuation framing candidate. It does not use the stored branch field in the candidate text or salience. Thus the prior thought fragment can influence the next Fountain frame, but the branch label itself is not what makes that candidate win.
2. **SelfNarrative branch carry:** `stage_tom.self_narrative.build_narrative()` calls `read_momentum()`; that renderer includes the stored branch in a line such as `(I was on <branch>)`. Fountain appends this narrative to a later prompt only when `NEX5_SELF_NARRATIVE=1`. That flag is explicitly checked and its default is off. Therefore branch-labelled carry into the next prompt is conditional, not a default-on claim.

Momentum itself has anti-rut controls: the row goes stale after 30 minutes, and `read_momentum()` goes silent after more than three consecutive similar carries. The similarity check requires at least three shared distinctive words. These controls constrain continuity rather than allowing an indefinitely self-reinforcing loop.

### Existing tests and evidence boundary

- `tests/test_branch_selection.py` covers the focus-weighted selection helper, including default top-pick and temperature behavior.
- `tests/test_momentum_writer.py` verifies injected Reader/Writer persistence, branch storage, carry count, surprise metadata, resolution and readback on temporary databases.
- The existing Stage-2 propagation test separately exercises the real A–F pipeline, then calls branch/workspace helpers.
- The inspected tests do not yet execute one integrated sequence from Stage-2 focus → production Fountain branch selection → `capture_momentum()` → `read_momentum()` → optional SelfNarrative prompt insertion. In particular, no reviewed test verifies the branch label's conditional next-fire prompt effect under `NEX5_SELF_NARRATIVE`.

### Research conclusion

There are two different forms of downstream influence:
- **Current-fire framing:** Bonsai focus enters Global Workspace before thought generation, but its ability to win is bounded by the salience ladder and runtime configuration (see §74).
- **Post-fire attribution/continuity:** the focus-ranked branch is selected after generation and stored with the generated thought. Its branch identity reaches the next prompt only through the optional SelfNarrative path; the default Global Workspace momentum candidate uses the thought fragment, not the branch field.

This is a more precise causal model than saying "attention controls the next thought." Attention contributes to framing and branch attribution, while other mechanisms and feature flags determine whether the branch label is carried forward.

### Next falsification test

Build an isolated, deterministic test that:
1. feeds controlled external events through the real Stage-2 pipeline and obtains `DynamicState.status()`;
2. invokes the production Fountain branch-selection/carry path with controlled `NEX5_BRANCH_TEMP` and `NEX5_RETRIEVAL_TEETH` settings;
3. verifies `hot_branch` attribution remains distinct from a diverted `_carry_branch`;
4. verifies the exact branch and thought fragment written to the temporary momentum row;
5. verifies `read_momentum()` returns the branch-labelled line, and that SelfNarrative prompt insertion occurs only with `NEX5_SELF_NARRATIVE=1`;
6. verifies the default Global Workspace momentum candidate depends on the thought fragment and not the branch field.

Use temporary databases and patched flags only inside the test. Do not change any live flag, momentum policy, branch selection or prompt wiring as part of the study.

**Source anchors inspected at main `18c8f06171e1de35c3210831a49b63d0e2487af0`:** `theory_x/stage6_fountain/generator.py` blob `26061914b1dd80858c3568217cd1ef0c49ce2c51`; `theory_x/stage_tom/momentum.py` blob `45d0249fe445871ebb2bfbcdb2da6e131a229e18`; `theory_x/stage_tom/global_workspace.py` blob `39d833d4a88ed3ad371daf7b62e7295d0dda6637`; `theory_x/stage_tom/self_narrative.py` blob `5fbc617fadc177ade59b45acf118b77c43ef2e84`; `tests/test_branch_selection.py` blob `01b94766a9344b6c3287947a610302345ae1bd97`; `tests/test_momentum_writer.py` blob `fdbab169457a9ebe8c3c451c69b635e200127bd6`; `tests/test_dynamic.py` blob `7e7493a5d79dda73f0ff374728a3da9eb34a558c`.

**Unchanged boundaries:** no branch-selection algorithm, momentum policy, carry limit, self-narrative flag, hot-observer flag, retrieval teeth, Global Workspace salience or prompt behavior is changed. No live database or host process is accessed.

---

## 77. SentienceNode registration census and structural conformance — source audit (28 November 2026)

**Question studied:** are the state-bound faculties merely attempted registrations that silently fail Protocol validation, or do their source classes expose the required lifecycle surface?

### Registration call-site census

At the inspected main snapshot:

- `gui/server.py` contains seven potential object additions across its registration sites: module-level FocalSet and ExecutiveControl; build_state's ProblemMemory, GoalManager and Metacognition; and create_app's membrane SelfModel and BehaviouralSelfModel.
- `run.py` contains nine state-faculty registration sites: SelfNarrative, HoldingZoneResolver, GoalManager, Metacognition, NovelAssociation, SubstrateHarmonic, GeniusTagger, DriveEmergence and AffectState. The unified entrypoint imports gui.server (which registers its two module-level nodes) and calls create_app once (which attempts to register the two membrane nodes). This is up to thirteen registration attempts in that boot route if all optional constructions succeed; it is not a claim that all attempts always succeed.
- The two entrypoints are alternatives in normal use; do not add their counts together as one process boot.

### Structural conformance spot-check

The source classes inspected for ProblemMemory, GoalManager, Metacognition, SelfNarrative, HoldingZoneResolver, NovelAssociation, SubstrateHarmonic, GeniusTagger, DriveEmergence, AffectState, SelfModel and BehaviouralSelfModel each expose a `name` attribute and `tick()`, `decay()`, and `state()` methods. FocalSet and ExecutiveControl additionally have explicit Protocol conformance tests. This makes silent registration failure from a missing required member less likely for these inspected classes, but source inspection is not a substitute for an actual runtime membership test.

### What remains unproven

- `register()` checks the runtime-checkable Protocol and appends; it does not enforce unique names despite the Protocol documentation's uniqueness requirement.
- No reviewed test directly asserts registry membership, duplicate handling, removal, thread safety or repeated `create_app()` behavior.
- The GUI membrane registration catches and logs errors; several other registration sites suppress exceptions, so the caller does not always expose a failed registration.
- The complete repository-wide `all_nodes()` consumer inventory remains incomplete; the available code-search interface returned incomplete/empty results. The inspected `gui/server.py` and `run.py` do not consume `all_nodes()`.

### Next bounded test

Before changing implementation, add a focused registry test suite that exercises a conforming fake node, a nonconforming object, same-object re-registration, two distinct objects with the same name, and repeated create_app registration. The expected duplicate policy must first be chosen from Doctrine §4's process-singleton contract; do not silently invent a policy in tests. Keep a separate lifecycle test for AppState-owned faculty objects only if multi-instance AppState use is accepted as supported.

**Source anchors inspected at main `18c8f06171e1de35c3210831a49b63d0e2487af0`:** `theory_x/__init__.py` blob `661dc737f54c88f763588606867ae1b9cd7e6654`; `gui/server.py` blob `ecaa6982544e883a50dbf85c5de1e10f74180c67`; `run.py` blob `8ebe33c251e874b16107428eb4e92cf6301a4621`; `theory_x/stage7_sustained/problem_memory.py` blob `720ff939062ffbe52ff36da926f7aff71eb701ec`; `theory_x/stage8_goal_manager/goal_manager.py` blob `0b879a903fa499fb88153edbcb7f5c8e69bd6dfa`; `theory_x/stage9_metacognition/metacognition.py` blob `de853bd93a11dcfe39ee8afa30a84e5c7b1f8b08`; `theory_x/stage_self_narrative/self_narrative.py` blob `15d8c1dd1de8332b3d12e06a096aac2c0b2b2cb3`; `theory_x/stage_gate/resolver.py` blob `7fa47df888b2f17ef8457ddc9ec024ccaf96298d`; `theory_x/stage10_imagination/novel_association.py` blob `064e1a605f0f22e2484df2e05713cc8b7973513b`; `theory_x/harmonic/substrate_harmonic.py` blob `d3e32c3ccd7301542f60d67bac8e5a14546dd6b1`; `theory_x/genius/tagger.py` blob `ef9f290845f74e498044307dee60ee25437419b0`; `theory_x/stage_drives/drive_emergence.py` blob `3db144383c489ea4055697a1629563cfa94a4552`; `theory_x/stage_affect/affect_state.py` blob `fca8a47fe347a880d72fa1a41dc2c1796e76d1b8`; `theory_x/stage4_membrane/self_model.py` blob `c3646242ee244d7434228fcabf0550ebd0d37947`; `theory_x/stage4_membrane/behavioural_self_model.py` blob `cd6ce4179e95b8435c33602f116f0a33f89ced12`.

**Unchanged boundaries:** no registry behavior, Protocol, doctrine, startup wiring, AppState lifecycle, runtime flag, frozen specification, roadmap, Phase 0/Gate 0 or cognitive/action authority is changed.

---

## 78. RDO Stage-7 execution verification versus bounded handoff verification — authority/evidence seam study (28 November 2026)

**Question studied:** does NEX have one continuous execution verifier, or are there distinct mechanisms with different authority and evidence guarantees? In particular, what does an exact-path test allowlist actually authorize, and what does the newer independent Watcher process do?

### Two mechanisms, deliberately not conflated

The source exposes two separate paths:

1. **Legacy/in-process execution integration — `rdo/execution.py::verify()`.** It reads the after-state using the RDO's read-only `_grep`, optionally invokes pytest, records per-obligation lifecycle in `watcher.ledger.ConnectionLedger`, and produces source/test/runtime evidence dimensions. Test execution requires the caller to pass the exact repository-relative path in `approved_test_files`; the evidence requirement's `test_file` field alone is not permission. The helper rejects absolute paths, parent traversal and paths resolving outside the repository. The tests show that an unapproved test is not run and that an escaping symlink is refused.
2. **Newer independent handoff verifier — `watcher.handoff_verify`.** The Stage-7 handoff adapter launches the fixed Watcher verification process for source/path scope. Its own module contract explicitly says it does not execute tests, project scripts, agents, services or NEX runtime operations. The manifest is required to declare `execution_authority=none`, `tests_execution_authorized=false`, `runtime_operations_authorized=false`, `test_verified=not_authorized`, `runtime_observed=unknown_host_only`, and `human_acceptance=not_recorded`. It validates the immutable manifest, approval/event chain, planning revision, exact path scope and repository evidence. This is a read-only verification boundary, not an execution launcher.

The second mechanism does not silently replace or upgrade the first. The Stage-7 handoff documentation explicitly preserves this distinction.

### Important correction: exact-path allowlist is not a sandbox

The legacy verifier's allowlist is a path-authorization check, not containment of arbitrary code effects. Once a test is allowlisted, `_run_test()` invokes `python -m pytest <path> -q` in the repository process environment. That test can execute Python, pytest configuration, `conftest.py` and plugins. The Stage-7 documentation explicitly says this is not an OS sandbox and arbitrary test execution remains unapproved until a disposable environment with no secrets, no live NEX data mounts and restricted network access is independently designed and verified.

Therefore the safe interpretation is narrow:
- Exact-path allowlisting prevents a declared test path from being treated as permission by default.
- Repository containment prevents the selected path from escaping the repository root.
- Neither property proves that the test's transitive code or side effects are contained.
- A passed test in this legacy path is evidence about the controlled execution that occurred; it is not host/runtime observation of the live NEX organism.

### Evidence semantics and a subtle ledger distinction

The legacy verifier computes an obligation verdict from independent source evidence plus the optional test result:
- source absent → `claim_unverified`, even if a completion claim or unrelated test exists;
- source present, no test requested/authorized → `partial`;
- source present and test failed → `failed`;
- source present and test passed → `verified`.

The runtime dimension is still a host-origin placeholder with `data=None`, evidence class `unknown`. Cloud source/test verification cannot promote it to runtime-observed.

The generic `ConnectionLedger.seed_from_graph()` path is a different evidence operation: it can record `TEST_WRITTEN` and `TEST_PASSED` from a curated graph's `test_verified` assertion, while its own docstring says the ledger does not execute the cited test. Do not read that ledger state as an independently executed test result. By contrast, the legacy `rdo.execution.verify()` records its TEST state after its own pytest invocation returns. Provenance and the producer of the state matter; the state label alone is insufficient context.

### Human decisions remain separate from technical evidence

The bounded handoff manifest starts with test evidence not authorized, runtime unknown, and human acceptance not recorded. Scope review can authorize only the documented bounded preparation/edit actions; it does not authorize pytest, arbitrary commands, live NEX writes, database changes, experiment changes, service restarts or deployment. Reviewer/source fields are caller-attributed, not identity-authenticated.

Criterion-level verification, overall human acceptance, source implementation, test verification and runtime observation are separate records/dimensions. A human acceptance event does not rewrite the immutable manifest's creation-time evidence statuses, and a passed criterion does not itself grant execution authority.

### Research conclusion

NEX currently has a layered progression rather than a single all-powerful execution path:
- cognition/planning can form and refine work packages;
- the handoff manifest binds a proposed task to an exact repository snapshot and bounded file scope;
- human scope review records a limited preparation decision;
- the independent Watcher verifies source/path facts without executing tests;
- test execution remains a separate authority boundary;
- live runtime observation remains host-only UNKNOWN;
- human acceptance remains a distinct judgement.

This separation is consistent with the governing architecture principle: interpretive cognition is not operation authority. A Mind Aspect, salience score, proposal, plan or completion claim must not become an implicit capability grant.

### Next falsification / development work

1. Keep the legacy test runner and new handoff verifier explicitly labelled as separate APIs in all documentation and reports.
2. Add or retain regression coverage that the new handoff subprocess never launches pytest, project scripts, agents or runtime operations, and that its manifest rejects any attempt to claim those permissions.
3. Design the disposable test-execution environment as a separate security project. Threat-model pytest startup hooks, `conftest.py`, plugins, environment variables, filesystem mounts, credentials, network access, subprocesses, time/resource exhaustion and artifact egress before enabling arbitrary test execution.
4. Make evidence reports show the producer and method for each evidence state, not merely the label `TEST_PASSED`.
5. Do not broaden handoff approval actions or infer Stage-7 completion. The real objective-to-verified-delivery demonstration, safe test boundary, host/runtime evidence and separate human acceptance remain outstanding.

**Source anchors inspected at main `18c8f06171e1de35c3210831a49b63d0e2487af0`:** `rdo/execution.py` blob `c4c3bb9b8c0dab5c16091c0ca3146921cf569c15`; `rdo/tests/test_stage7_execution_watcher.py` blob `832b6290a45c793274e0890037618a7fb5eeea36`; `watcher/handoff_verify.py` blob `fae4a9c6475f9d52d16a786e71d42b907d094407`; `watcher/ledger.py` blob `698ae962fe1dfad2d252b39a41066cd8cc0e4310`; `watcher/evidence.py` blob `0d235f79a562ae6fad14325915b0be8c34d4f382`; `rdo/STAGE7_HANDOFF.md` blob `1585d1f4ffe28608614ade6679429584126a0987`.

**Unchanged boundaries:** no test execution, agent launch, RDO execution, handoff creation/review, approval action, sandbox, host operation, runtime flag, database, evidence policy, frozen S-01–S-25/M1.8, Master Roadmap, Phase 0/Gate 0 or cognitive/action authority is changed. This was a source-and-test review only.
## 79. Stage-B capability wire and autonomous-fire boundary — current-main reconciliation (28 November 2026)

**Question studied:** where can the existing tools actually be invoked, what operation representation crosses that boundary, and has the capability layer been connected to NEX's autonomous Fountain/fire loop?

### Current chat-path wire

At main snapshot `18c8f06171e1de35c3210831a49b63d0e2487af0`, `gui/server.py` constructs `ToolRegistry` and `ToolCaller` only when `with_tools` is enabled and the required conversation storage is available. The chat handler then performs this sequence:

```text
chat prompt
  → ToolCaller.should_use_tool(prompt)
  → ToolCaller.build_tool_kwargs(prompt, tool_name)
  → ToolRegistry.execute(tool_name, **kwargs)
  → ToolResult
  → successful result wrapped by build_tool_prompt()
  → appended to belief_text / response context
```

The route records tool-execution and tool-prompt-injection trace events when tracing is available. Exceptions are reported to the error channel. The current source calls `should_use_tool(prompt)` with one argument; an older research note describing `should_use_tool(prompt, [])` is not an accurate description of this snapshot.

### What the current Stage-B operation actually is

The caller selects from three registered tools:
- `web_fetch`: fetch an explicit URL or supported cryptocurrency-price target; the registry restricts HTTP(S) destinations to its fixed hostname allowlist, rejects URL credentials and disables automatic redirects.
- `python_exec`: the caller extracts a narrowly bounded numeric expression from a recognised sentence prefix, then passes explicit `code=print(expression)`. The registry parses and interprets a small numeric AST allowlist in-process; it does not use Python `exec`, `eval`, `compile` or a subprocess. It bounds expression length, AST size, integer magnitude, float magnitude and exponent size.
- `beliefs_query`: read-only retrieval through the configured beliefs reader.

This is a meaningful hardening of the old sentence-to-code boundary. Natural-language sentences are not silently substituted as Python source. Unsupported or ambiguous calculation wording produces no tool selection. The tool result is a `ToolResult` data object, then formatted as prompt context.

However, this is **not yet the general typed operation representation** envisioned by the broader NEX architecture. The caller still selects by keyword patterns and passes tool-specific keyword arguments; the registry directly dispatches by tool name. There is no general operation envelope here that carries a canonical operation ID, typed arguments, provenance, preconditions, requested side-effect class, expiry, approval requirement, or postcondition contract. Do not describe this narrow Stage-B route as the completed Sentence Code → Recursive Extrapolator → executable-interface pathway.

### Important authority observation

On the inspected chat path, once a supported tool is selected, `gui/server.py` directly calls `ToolRegistry.execute()`; no separate human approval step is visible between this heuristic selection and the bounded tool invocation. That observation must be interpreted in proportion to the actual capability surface: the current tools are limited to allowlisted HTTP GET, bounded arithmetic interpretation and read-only belief retrieval. It does not establish that arbitrary shell, filesystem, robot, deployment or other consequential operations are available.

The architectural lesson is not to put a Mind Aspect in front of this call as a veto. Preserve the user's rule: Mind Aspects provide interpretation, not action authority. If NEX expands the capability surface, the next design should add an explicit typed operation/authority boundary independent of the mind-map position of any cognitive faculty. Capability validation, any required human approval, execution and post-execution verification must remain separate stages.

### Autonomous-fire reachability: not present in the inspected Fountain source

A direct scan of `theory_x/stage6_fountain/generator.py` at this snapshot found no references to `ToolCaller`, `ToolRegistry`, `tool_caller`, `tool_registry`, `python_exec`, `web_fetch` or `beliefs_query`. The reviewed `gui/server.py` chat handler is therefore evidence of chat-triggered capability use, not autonomous-fire tool use. No fire-loop tool call, trigger rate, or autonomous execution frequency should be inferred from the chat path.

This matters to the wider neural-network/exponential-propagation idea: adding a new caller from internal thought state would change *who or what can trigger a capability*, even if the tool implementation itself remained unchanged. That would be a separate architecture and authority decision, not a harmless reuse of the chat helper.

### Reconciliation of older research notes

Two repository notes require snapshot-aware reading:
- `research/SENTENCE_TO_TOOL_WIRE_TRACE_2026-11-28.md` describes an earlier main snapshot `5ba30077` and a bounded correction as still candidate PR #369. The inspected current-main source at `18c8f061...` already contains the bounded AST interpreter and explicit expression extraction described there. Treat the note's implementation-status paragraph and old chat-call signature as historical, not current status.
- `observation_reports/fire_path_tools_SCOPE.md` describes `python_exec` as subprocess-based and refers to import blocklisting/sandboxing. That does not match the current `tools.py` implementation inspected here. Its broader governance warning remains useful: a new autonomous caller changes trigger source, volume and observability, even when the capability itself is bounded. Its old implementation description must not be repeated as current fact.

The current source snapshot, not a stale note, is the implementation authority for this study. The source trace itself remains a snapshot observation; it does not establish live host configuration or whether `with_tools` is enabled in a running deployment.

### Next bounded development sequence

1. Keep the current three-tool chat route bounded; do not connect it to Fountain as an incidental refactor.
2. Specify a minimal typed operation envelope for future capability growth, but first inventory existing execution interfaces and governance contracts. It should carry operation identity, typed inputs, provenance, requested capability, preconditions and expected postconditions; it must not itself grant authority.
3. Separate deterministic capability validation from approval policy. A cognition result or Mind Aspect may supply context and rationale, but must not silently approve or veto the operation.
4. Add explicit post-execution verification and preserve a provenance trail from originating request/intent through operation, result and verification.
5. Before any autonomous-fire caller is considered, measure candidate trigger base rates read-only, define per-capability limits and observability, and obtain a separate explicit design decision. Do not arm or prototype autonomous tool calls as part of this documentation study.

**Source anchors inspected at main `18c8f06171e1de35c3210831a49b63d0e2487af0`:** `gui/server.py` blob `ecaa6982544e883a50dbf85c5de1e10f74180c67`; `theory_x/stage_capability/tool_caller.py` blob `07ef6c7f044b0c26c3e8ba78f51e5cf285890402`; `theory_x/stage_capability/tools.py` blob `b00052d6286d23b58599bfc463ebf051b0c08668`; `theory_x/stage6_fountain/generator.py` blob `26061914b1dd80858c3568217cd1ef0c49ce2c51`; `tests/test_tools.py` blob `6afdbf3bd88c5b5463443947e02d4a5ef3fdf6ee`; `research/SENTENCE_TO_TOOL_WIRE_TRACE_2026-11-28.md` blob `a4481c09219e3c85c41df886f79449599c5929bc`; `observation_reports/fire_path_tools_SCOPE.md` blob `9b83406fbb00fc9e62908fec2a1e840a70473ccc`.

**Unchanged boundaries:** no tool call was made against a live NEX instance; no tool was invoked, no Fountain integration, autonomous caller, typed-operation implementation, approval gate, feature flag, runtime setting, database, frozen S-01–S-25/M1.8, Master Roadmap, Phase 0/Gate 0 or cognitive/action authority was changed.
## 80. Typed operation-contract inventory — reuse existing RDO records without mistaking planning records for executable authority (28 November 2026)

**Question studied:** does NEX already have a typed operation representation, or does it have typed planning/evidence records that stop before an executable operation contract?

### Existing typed structures found

The current RDO has substantial typed building blocks:
- `Obligation`: canonical key, kind, classification, parent/depth, rationale, provenance, assumptions, reconciliation status/evidence, confidence, impact and evidence needs.
- `Relationship`: source/destination, typed relationship kind, an authority descriptor (`none|bounded|strong`), reversibility and optional interface/operating-envelope/performance-margin evidence.
- `WorkPackage`: obligation keys, advisory eligibility, blockers, priority dimensions, anti-requirements and reversibility.
- `ContextRequirement` and `AcceptanceVerificationRecord`: source-linked context/criterion records with explicit mapping and verification evidence fields.
- `CycleRecord`: durable planning, graph, frontier, evidence, learning and lineage snapshot.
- Stage-7 handoff manifest: immutable binding to objective revision/digest, cycle, repository revision, work package, exact file scope, obligations, relationships, deliverables, constraints, exclusions, evidence requirements and separate decision records.

These are real typed structures, but their meanings are not interchangeable. An Obligation describes work to be considered; a Relationship describes a graph relation; a WorkPackage groups advisory work; a CycleRecord records planning; a handoff manifest binds a reviewed proposal to a repository snapshot and bounded path scope. None is by itself a canonical executable operation request.

### The current explicit lifecycle is already usefully staged

The reviewed proposal bridge makes the separation concrete:

1. `prepare_reviewed_selection()` requires an explicit approved proposal, verifies proposal/alternative identity and the raw-objective digest, recovers the exact approval event, validates objective.v1 and returns graph diagnostics plus a dual-chain lineage envelope. It writes neither ledger, starts no planning and creates no handoff.
2. `submit_reviewed_selection()` is a separate explicit call. It persists the validated objective and lineage together in the objective ledger and runs advisory RDO planning. It does not create a Stage-7 handoff or authorize execution.
3. `create_handoff()` binds a selected eligible work package to the exact clean repository snapshot and objective input digest. It preserves blockers and begins test evidence as not authorized, runtime as host-only unknown and human acceptance as not recorded.
4. Human scope review permits only the enumerated preparation/edit/review-branch actions. It does not authorize tests, arbitrary commands, live NEX writes, database/experiment changes, runtime flags, service restarts or deployment.
5. The independent Watcher verifies the source/path boundary without executing tests or project operations. Test verification, host runtime observation and human acceptance remain separate.

### Authority metadata is not authority enforcement

The `Relationship.authority` field and the typed `authority_boundary` evidence dimension are useful descriptive inputs to interface analysis. Their presence does not establish a capability validator, approval decision or execution gate. Similarly, a proposal's recorded `approved` state means the selected interpretation may be prepared for intake; it is not an approval to execute the work. A Stage-7 scope approval is a bounded preparation permission, not a general execution grant.

This is exactly where the architecture principle must hold: Mind Aspects may interpret intent, estimate relevance, expose uncertainty and contribute rationale. They must not turn their cognitive state, map position, score or preference into capability permission or an action veto.

### Gap: the missing typed operation envelope

No single general-purpose operation record was found in the inspected RDO/capability path that unifies the following fields and lifecycle:
- stable operation identity and schema version;
- originating request/intent and provenance chain;
- operation kind and typed, validated arguments;
- target/resource and requested capability;
- declared side-effect class and scope;
- preconditions and expiry/staleness binding;
- required capability checks and separately recorded approval requirements;
- idempotency/replay identity where relevant;
- execution attempt/result reference;
- postconditions and independent verification evidence.

The chat ToolCaller still selects a named tool and builds tool-specific kwargs. The RDO records a proposed work package and handoff, not a canonical operation envelope. Do not fill this gap by treating WorkPackage, Relationship.authority, a natural-language plan or a Mind Aspect output as an executable request.

### Recommended reuse-first design sequence

1. Map existing fields to a candidate envelope and identify what must remain separate. Reuse objective, lineage, obligation, work-package, handoff and evidence references; do not duplicate their full payloads.
2. Define a small versioned operation schema as a proposal only. It should carry references to immutable source records rather than copy mutable prose into a second authority store.
3. Define deterministic capability validation against the requested operation and target. Validation answers “is this capability technically available and within its declared boundary?”, not “should the system want to do it?”
4. Keep human/owner approval as a separate authority event where required. An approved proposal, an eligible work package and a valid capability are three different facts.
5. Execute only through a separately authorized adapter; record attempt/result without rewriting the originating plan.
6. Verify postconditions independently and retain UNKNOWN when required evidence is absent. Human acceptance remains a further distinct judgement.

**Source anchors inspected at main `18c8f06171e1de35c3210831a49b63d0e2487af0`:** `rdo/model.py` blob `11bb372469145d828d8163905b50afa63effc3ec`; `rdo/orchestrator.py` blob `e9dad9a11e8e09444b4ee2e7d77f60d580f7b104`; `rdo_adapters/reviewed_seed_bridge.py` blob `5b8580b0dabfa1f533301c18d86bf222ceb67114`; `rdo_adapters/handoff.py` blob `c0fe2afc90d3e5fe948c7555bde1cf1675d7c0be`; `rdo/REVIEWED_SEED_BRIDGE.md` blob `680791eb82ea29c43e54d875f4e522b624e351f6`; `rdo/OBJECTIVE_INTAKE.md` blob `4067c075e85f797a6555d06ce6e0d37cc7c8ae46`.

**Unchanged boundaries:** no operation schema, capability validator, approval policy, runtime adapter, tool integration, database, flag, execution permission, frozen S-01–S-25/M1.8, Master Roadmap, Phase 0/Gate 0 or cognitive/action authority is changed. This is a source inventory and design study only.
## 81. Recursive expansion growth and graph-analysis bounds — taming combinatorial propagation (28 November 2026)

**Question studied:** what currently contains the growth of NEX's recursive development network, and is depth alone a sufficient resource bound?

### Existing containment mechanisms

The RDO Extrapolator uses breadth-first expansion and has several meaningful controls:
- Objective v1 accepts 1–200 initial seed obligations, at most 1,000 relationships, and `max_depth` from 0 through 4.
- The generic expansion catalogue has a finite number of child rules per kind; the largest inspected fan-out is six children for `persistence`. Many generated kinds are terminal.
- A canonical-key map converges repeated discoveries. Compatible same-kind obligations merge provenance/evidence needs and preserve the stronger classification. A kind collision or build/anti-requirement contradiction raises `MergeConflict`; it is not silently collapsed.
- Anti-requirements stop development; terminal kinds stop decomposition; depth budget stops further expansion; valid independently reviewed reuse can stop expansion.
- Every stopping point is preserved in the frontier with its reason. A source-signature match alone does not prove semantic satisfaction, so the obligation continues conservatively.
- The expansion catalogue digest helps identify stale rule-proposal requests; novel kinds produce candidate-only rule proposals and do not activate new rules automatically.

The graph layer is also careful about expensive cyclic analysis. Tarjan SCC discovery is used to identify components. The reviewed-seed bridge limits detailed cycle enumeration to cyclic SCCs no larger than 7 nodes and 18 internal cycle edges. If any cyclic SCC exceeds either bound, detailed classification/system assessment is skipped and the graph remains `bounded_unknown`. A test with an 8-node cycle asserts that no cycles are enumerated and no system verdict is fabricated.

### The important remaining gap: no total expansion budget observed

The inspected `expand()` loop enforces depth and stopping rules but does not expose a separate maximum for total unique obligations, total generated relationships, total queue work or elapsed planning budget. The objective schema bounds initial input size and depth, but those are not the same as a hard cap on the expanded graph.

A deliberately loose theoretical illustration shows why this matters: with up to 200 seeds, a maximum six-child rule at each of four expansion levels gives a naive tree upper bound of 1 + 6 + 36 + 216 + 1,296 = 1,555 nodes per seed before accounting for actual rule-kind restrictions, terminal kinds and canonical convergence. That is not a prediction of actual RDO output; it is a warning that a depth cap alone is not a strict total-work budget. Actual expansion rules and convergence reduce the result, but no explicit total-node/edge ceiling was found in the inspected function.

### Design implication

The right response is not to suppress recursion or flatten the network. It is to bound the *resources spent exploring it* while preserving the unresolved network honestly.

A future, separately reviewed increment should consider:
1. A deterministic per-cycle unique-obligation budget and relationship budget, with explicit configuration/version provenance.
2. A frontier stop reason such as `node_budget_exhausted` or `edge_budget_exhausted`, preserving the unexpanded parent and remaining candidate rule outputs for later continuation.
3. A deterministic breadth-first ordering and stable canonical keys so the same snapshot/budget produces reproducible partial graphs.
4. No partial result may be described as complete merely because the budget was reached. Completeness must expose budget exhaustion separately from terminal, anti-requirement, semantic reuse and novel-kind stops.
5. Tests for adversarial fan-out, convergence-heavy graphs, incompatible key collisions, deterministic replay, budget-boundary off-by-one behaviour and persistence/resume of deferred frontier.
6. Separate limits for graph cycle enumeration and expansion generation; one must not be mistaken for the other.

This would tame combinatorial growth without denying the network's capacity to reveal relationships. The system retains the frontier instead of pretending to have completed the exploration.

### Research conclusion

NEX already has depth, fan-out-by-rule, terminal, reuse, convergence and SCC-enumeration controls. It does not yet demonstrate a strict total expansion-work budget in the inspected path. A deterministic total-node/edge budget is therefore a credible next RDO improvement candidate, but it must be designed against the frozen roadmap/specification boundaries and tested as an additive control. No budget value is invented here.

**Source anchors inspected at main `18c8f06171e1de35c3210831a49b63d0e2487af0`:** `rdo/extrapolator.py` blob `330e1aaec7504fdc1315b1b88b9c304942318c17`; `rdo/schemas/objective.v1.schema.json` blob `118ff013bfdb1193c4630ab5a3d07b2c05d0dc5b`; `rdo_adapters/seed_proposals.py` blob `4bebbba632cedef1bd74127dd0a152dfb45badb5`; `rdo/graph.py` blob `65d5443c2fa874e4408c563bccc8e5b88793699d`; `rdo/tests/test_stage2_extrapolator_mvp.py` blob `4f3642d7f90485ff3ab22d05e9f09c22a0989465`; `rdo/tests/test_reviewed_seed_bridge.py` blob `fef4fe2363f29cef3d8fc7a700e099095584ace5`.

**Unchanged boundaries:** no expansion rules, max depth, graph algorithms, proposal limits, runtime data, flags, database, frozen S-01–S-25/M1.8, Master Roadmap, Phase 0/Gate 0 or action authority is changed. No tests were executed; existing test source was inspected only.

## 82. Durable frontier persistence versus true planning continuation — reload is not resume (28 November 2026)

**Question studied:** when RDO documentation and tests say a cycle can be resumed, does loading a saved cycle actually continue its unfinished recursive expansion?

### What persistence demonstrably does

The CycleStore in **rdo/memory.py** writes a complete CycleRecord.to_dict() payload to a per-cycle JSON file. Its write path uses a temporary file, flush + fsync, atomic os.replace, and a directory fsync. load(cycle_id) reconstructs a CycleRecord from that JSON. The record retains obligations, relationships, counts and the full frontier, including stop reasons.

The Stage-2 tests establish useful durability properties:
- a saved cycle reloads with an equal to_dict() representation;
- a fresh interpreter can load the persisted record;
- unresolved and max-depth frontier entries survive save/reload unchanged;
- counts and frontier classifications survive persistence.

These are real persistence and recovery-of-record guarantees. They should not be discounted.

### What the current code does not demonstrate

The word *resume* is broader than the implementation evidence. In the inspected source:
- CycleStore exposes save(), load() and list_ids(); it does not expose a continuation method.
- load() deserializes a record. It does not reconstruct the Extrapolator's BFS queue, a queue cursor, pending rule outputs, or a partially completed expansion transaction.
- run_cycle() accepts a new set of seed Obligation objects and calls expand(seeds, reconciler, max_depth=...). It does not accept a prior CycleRecord as a resumable execution state.
- expand() creates fresh local obligations, relationships, frontier and queue collections on each call. Its returned frontier is a record of where that run stopped, not a persisted continuation cursor.
- A frontier entry generally identifies a key and a reason; it does not by itself preserve all scheduler state required to restart at the exact point of interruption.

Therefore, the source and tests prove **durable cycle reload**, not **automatic continuation of an interrupted recursive planning run**. A caller could potentially reconstruct selected obligations from a loaded record and submit a new planning cycle with new parameters, but that is a new/reconstructed run and would need explicit handling of prior relationships, reconciliation evidence, rule-catalogue version, repository snapshot and duplicate accounting. It must not be described as exact resume without tests proving those semantics.

### Why this distinction matters

A saved frontier can be complete as an *audit record* while still being insufficient as an *execution cursor*. Confusing the two can create false confidence that no work is lost after a process interruption. It can also cause duplicated expansion, stale reconciliation, changed rule interpretation or loss of deterministic ordering if a future continuation mechanism is improvised.

The correct status vocabulary should distinguish at least:
- **record_reloaded**: the durable cycle and its frontier were reconstructed;
- **continuation_prepared**: a validated continuation state was assembled from a prior cycle and pinned inputs;
- **continuation_executed**: additional expansion actually ran from that state;
- **continuation_verified**: resulting obligations/edges were reconciled against the prior record without silent loss or duplication.

These are proposed descriptive states, not existing NEX enums or flags.

### Reuse-first design for a future continuation capability

Before adding a new scheduler or persistence subsystem:
1. Define whether continuation means *retry unresolved frontier*, *increase depth*, or *resume an interrupted in-flight expansion*. These are different operations.
2. Reuse the immutable prior cycle as the parent evidence record. Give the continuation its own cycle/run identity and explicit parent-cycle reference rather than silently overwriting history.
3. Persist a versioned continuation descriptor: source cycle ID and digest, repository/source snapshot, expansion-catalogue digest, max-depth and resource-budget settings, deterministic queue order/cursor, pending obligation identities and relationship state.
4. Revalidate reconciliation against the current source snapshot. Do not carry forward a prior REUSE_EXISTING assertion as authority; the current Extrapolator already invalidates caller-supplied reuse claims and requires fresh semantic review.
5. Make replay idempotent and convergence explicit. Detect key-kind and build/anti-requirement conflicts exactly as the existing _merge() does.
6. Preserve the original frontier and record which entries were continued, superseded, intentionally closed or remain unresolved. Never convert an unknown frontier into completion by omission.
7. Test process termination at queue boundaries, duplicate replay, repository drift, catalogue drift, reconciliation changes, depth extension, budget exhaustion and fresh-process continuation.

This continuation study also sharpens the previous section's proposed total-work budget: a deterministic node/edge budget is only useful if the frontier carries enough versioned state to continue safely, or if the system explicitly declares that a later run is a fresh reconstruction rather than a resume.

### Research conclusion

NEX has robust cycle-record persistence and tests for reload across process boundaries. The inspected implementation does not yet show a first-class resumable BFS execution state or a continuation API. Treat "resume" in current documentation as **reload/recover the recorded cycle**, unless a separate, tested continuation path is identified. This is a precise capability boundary, not a criticism of the existing atomic persistence mechanism.

**Source anchors inspected at main 18c8f06171e1de35c3210831a49b63d0e2487af0:** rdo/memory.py blob ff0abb6d6ebdd91c4567362e238363d41ddb57e1; rdo/model.py blob 11bb372469145d828d8163905b50afa63effc3ec; rdo/orchestrator.py blob e9dad9a11e8e09444b4ee2e7d77f60d580f7b104; rdo/extrapolator.py blob 330e1aaec7504fdc1315b1b88b9c304942318c17; rdo/tests/test_stage2_extrapolator_mvp.py blob 4f3642d7f90485ff3ab22d05e9f09c22a0989465.

**Unchanged boundaries:** no CycleStore format, continuation API, queue algorithm, expansion rule, budget, runtime data, database, flag, frozen S-01–S-25/M1.8, Master Roadmap, Phase 0/Gate 0 or action authority is changed. This is a source-and-test study only; no tests were executed in this turn.

## 83. Mind-map policy enforcement and the cognitive/capability boundary (28 November 2026)

**Question studied:** how is the descriptive-only mind-map doctrine protected in code, and does that protection itself establish the full separation between cognitive interpretation and action authority?

### What is explicitly enforced

The mind-map source states that it is a descriptive index, not a runtime decision authority. The YAML doctrine is explicit: no node may gate, score, block or veto an action. Its node schema also distinguishes evidence/status modifiers such as dark and blocked from permission semantics.

The Python policy checker in mind_map/mind_map.py implements several concrete protections:
- It requires the descriptive-only/no-action-authority doctrine to remain in the map metadata.
- It rejects node fields whose names imply action authority, including gate, veto, authority, permission, priority, score, action_gate and execution_authority.
- It deliberately permits the blocked field because it describes evidence/status, not permission to block an action.
- It scans a declared set of runtime roots (including run.py, gui, theory_x, substrate, speech, voice, admin and strikes) and parses Python source with the AST.
- It rejects direct imports of mind_map and non-docstring string constants containing MIND_MAP.yaml in those scanned runtime files.
- It allows RDO/Watcher and developer tooling outside the runtime roots to read the map as evidence.

The policy tests characterize these rules: current map passes; action-authority fields and missing doctrine fail; runtime import and YAML loading fail; an external RDO reader is allowed; and selected boot-imported roots are included in the scan.

This is stronger than a comment-only doctrine. It is a source-level CI guard against the most direct route by which the map could become a runtime dependency.

### What this guard does not prove

The checker is a bounded static policy check, not a universal proof about every possible execution path:
- Its coverage depends on the declared RUNTIME_ROOTS. A new runtime root must be added deliberately.
- It looks for direct AST imports and literal string constants. Indirect loading, dynamically assembled paths, generated code or other non-Python mechanisms are not established as covered by these checks.
- It does not by itself prove that every other cognitive faculty is unable to influence action selection through a separate runtime pathway.
- It does not validate the semantics of every capability validator, approval event, executor or postcondition verifier.

Therefore the correct conclusion is narrow: **the mind-map artefact is guarded against direct runtime consumption through the currently scanned source roots**. Do not inflate this into a claim that all NEX action authority is already completely formalized.

### Cross-check against the current bounded capability route

The current Stage-B ToolCaller selects among three named capabilities: web_fetch, python_exec and beliefs_query. It constructs tool-specific arguments; ToolRegistry dispatches only names in its fixed registry. The arithmetic path interprets a deliberately small AST language rather than arbitrary Python source. This is a bounded capability surface, but the ToolCaller/Registry route is not a general approval system.

The inspected ToolCaller and ToolRegistry contain no mind_map import and do not consult the mind-map YAML. This is consistent with the policy. It does not mean a cognitive preference is an approval, nor does the presence of a registered tool mean every possible caller has permission to execute it.

The architecture must continue to keep these concepts separate:
1. **Cognitive interpretation:** Mind Aspects contribute perception, relevance, appraisal, uncertainty, memory and rationale.
2. **Operation representation:** a typed request names the intended operation, target and declared side effects.
3. **Capability validation:** deterministic checks establish whether that operation is technically available and within scope.
4. **Approval authority:** the required owner/human/system authority is recorded independently of cognitive preference.
5. **Execution:** a separately authorized adapter performs the operation.
6. **Verification:** independent evidence establishes what actually happened; human acceptance remains distinct where required.

A Mind Aspect may inform the first layer and provide evidence to later reviewers. It must not silently become any of layers 3–5, or veto an operation merely because of its map position or score.

### Design and maintenance implications

- Treat mind_map/mind_map.py and tests/test_mind_map_policy.py as an architectural invariant, not cosmetic diagram tooling.
- When runtime roots are added or renamed, update the policy scan and add a regression test for the new path.
- Consider adversarial tests for indirect/dynamic map loading if future runtime code introduces plugin discovery, generated modules or dynamic imports. Do not add brittle source heuristics without a concrete bypass case.
- Keep mind-map evidence/status terms distinct from executable permission vocabulary. In particular, blocked remains descriptive status, never an action switch.
- Keep separate tests for cognitive influence, capability validation, approval provenance, execution scope and post-execution verification. A passing mind-map policy test cannot substitute for those tests.

### Research conclusion

The repository has an explicit, tested descriptive-only doctrine and a static AST policy checker that prevents direct mind-map imports or literal YAML loads in its declared runtime roots. The Stage-B capability route is separately bounded and does not read the mind map. This supports the intended cognitive/action separation, while leaving the broader operation-envelope and approval formalization as separate work. No runtime policy or capability behavior was changed in this study.

**Source anchors inspected at main 18c8f06171e1de35c3210831a49b63d0e2487af0:** mind_map/MIND_MAP.yaml blob d569d6e50e5541f1845581b052ffdb9db8e2857f; mind_map/mind_map.py blob 6eda2aa414802374e18db242d8ccbc26c9ee06ad; tests/test_mind_map_policy.py blob de6a30f6d4ce92b28b70e9b5ef1d318c3844ed6c; theory_x/stage_capability/tool_caller.py blob 07ef6c7f044b0c26c3e8ba78f51e5cf285890402; theory_x/stage_capability/tools.py blob b00052d6286d23b58599bfc463ebf051b0c08668.

**Unchanged boundaries:** no Mind Aspect policy, mind-map schema, capability registry, approval rule, runtime code, tool behavior, database, flag, frozen S-01–S-25/M1.8, Master Roadmap, Phase 0/Gate 0 or action authority is changed. This is a source-and-test study only; no tests were executed in this turn.

## 84. Approval provenance: tamper-evident history is not authenticated identity (28 November 2026)

**Question studied:** what does a Stage-7 scope-review event actually prove, and what trust does the Watcher place in it?

### What the handoff boundary enforces

The immutable handoff manifest is canonicalized and SHA-256 digested. It records execution_authority=none, tests_execution_authorized=false, runtime_operations_authorized=false and the other explicit non-execution boundaries. Its creation binds the planning cycle, objective revision/digest, repository snapshot, work package and exact path scope.

Scope-review events are appended to a manifest-digest-bound JSONL ledger. The append path:
- validates the decision and restricts approved actions to a fixed allowlist of non-executing preparation actions;
- refuses unknown and forbidden actions such as run_tests, execute_code, deploy, live database writes and runtime-flag changes;
- requires an explicit permitted-action list for approval;
- records sequence, previous-event digest, timestamp and event digest;
- uses a file lock, append, flush and fsync;
- verifies the sequence and hash chain when history is read.

The Watcher independently rechecks the manifest digest, decision-event chain, current approved scope review, Git ancestry, changed paths and exact-file/symlink boundaries before recording source/path evidence. This is a meaningful integrity and scope-control design. It is not merely a human-readable approval note.

### The identity boundary is intentionally weaker

The code explicitly labels reviewer identity as caller-attributed, not authenticated. The API accepts reviewer and source_reference strings supplied by its caller. The event hash is an unkeyed SHA-256 digest over canonical event content; the chain detects accidental edits and ordinary tampering when the attacker cannot rewrite the chain, but it does not establish who supplied the event or provide a cryptographic signature from that person.

Consequently:
- a valid hash chain proves internal consistency of the recorded event sequence, not the real-world identity of the reviewer;
- a reviewer label is an attribution claim, not an authenticated principal;
- a source_reference preserves a pointer/claim about an approval source, not proof that the referenced source was checked or controlled by that reviewer;
- the Watcher can independently validate that the ledger contains a structurally valid, digest-bound, current approval event, but it cannot turn caller-attributed data into authenticated identity merely by validating the hashes.

This is not a defect hidden by the implementation: the limitation is explicitly documented in the adapter and Stage-7 manual. The important engineering requirement is to preserve it in every downstream status and UI. Never label this event “cryptographically signed approval” or “identity verified”.

### What the current approval actually authorizes

A successful scope review authorizes only the explicitly named non-executing preparation actions and only within the exact manifest path scope. It does not launch an agent. It does not authorize tests, arbitrary commands, runtime operations or deployment. The separate human-acceptance event is recorded only after scope approval and remains a distinct judgement; source/test/runtime evidence dimensions remain separate.

This fits the core architecture: planning eligibility is not permission; scope approval is not execution approval; evidence verification is not human acceptance. Mind Aspects remain interpretive and cannot manufacture or substitute for any of these authority records.

### Reuse-first path to stronger provenance, if ever required

Do not retrofit a home-grown identity system into this adapter. First define the actual threat model and operational principal:
1. Is the concern accidental misattribution, another local process writing the ledger, a compromised user account, or a remote reviewer?
2. Identify the trusted identity provider and the exact signed assertion format it can issue.
3. Bind the signed assertion to the handoff ID, manifest digest, decision, permitted actions, reviewer principal, expiry/nonce and policy version so it cannot be replayed against another handoff or scope.
4. Verify signatures in the trusted Watcher boundary using pinned trust roots; record both the original assertion reference and verification result.
5. Preserve a compatibility distinction between legacy caller-attributed events and newly authenticated events. Never silently upgrade historical records.
6. Test expired assertions, wrong-manifest replay, altered actions, wrong principal, key rotation/revocation, duplicate nonce, missing trust roots and clock uncertainty.

If the deployment has only a single trusted local operator and the explicit limitation is acceptable, retaining caller-attributed append-only events may be the simpler and more honest choice. Authentication is a threat-model decision, not a decorative feature.

### Research conclusion

Stage-7 provides strong manifest binding, bounded non-executing scope review, append-only hash-chained decision history and independent Watcher validation of that history. It deliberately does **not** authenticate reviewer identity. The system proves that a consistent attributed decision was recorded, not that a particular human cryptographically made it. Preserve that boundary; any stronger identity assurance requires a separately designed trust root and signed, replay-resistant approval assertion.

**Source anchors inspected at main 18c8f06171e1de35c3210831a49b63d0e2487af0:** rdo_adapters/handoff.py blob c0fe2afc90d3e5fe948c7555bde1cf1675d7c0be; rdo/tests/test_handoff.py blob [test file inspected]; rdo/execution.py blob c4c3bb9b8c0dab5c16091c0ca3146921cf569c15; rdo/tests/test_stage7_execution_watcher.py blob 832b6290a45c793274e0890037618a7fb5eeea36; rdo/STAGE7_HANDOFF.md and rdo/STAGE7_EXECUTION_WATCHER.md.

**Unchanged boundaries:** no identity provider, signing key, authentication mechanism, approval rule, event schema, execution capability, Watcher behavior, database, flag, frozen S-01–S-25/M1.8, Master Roadmap, Phase 0/Gate 0 or runtime authority is changed. This is a source-and-test study only; no tests were executed in this turn.

## 85. Cognitive feedback loops: attention, quality attribution and stale reinforcement signals (28 November 2026)

**Question studied:** which NEX cognitive pathways feed their own future prominence, and what prevents a useful adaptive loop from becoming a self-reinforcing attention bias?

### 1. The demonstrated Bonsai feedback path

The external-event A–F pipeline matches events to branches, calculates magnitude, applies the membrane aperture, derives valence and calls BonsaiTree.attend(). Bonsai focus is then consumed independently by:
- Fountain hot-branch selection, normally the highest-focus branch; optional positive-temperature selection can choose a lower-focus branch.
- Global Workspace framing, where the hottest branch becomes a candidate when focus exceeds 0.1 and receives salience focus × 0.50.
- Other downstream attention/carry attribution paths described in the existing Bonsai/Fountain trace.

This is a real shared-state coupling, not evidence of an uncontrolled infinite loop. Bonsai focus is bounded to [0,1], receives weighted increments, and has decay, recency penalties, cadence-aware decay and a starvation bonus. The current test characterization proves the shared state reaches both Fountain branch selection and Workspace framing, but it does not prove better reasoning or output quality.

### 2. Quality Synthesis creates a second-order reinforcement loop

When NEX5_QUALITY_SYNTH=1, Fountain startup launches Quality Synthesis. Every 30 minutes, it:
1. Reads recent genius_tags from the previous three hours.
2. Joins each tagged fire to fountain_events.hot_branch.
3. Computes per-branch score fractions.
4. Classifies branches as high, low or neutral.
5. Writes data/quality_signal.json.

Attention reloads that file every five minutes. A high branch receives a 1.20 multiplier on external-event magnitude; a low branch receives 0.82. That changes future Bonsai focus increments, which influence later branch selection and framing, which changes which branch receives the next fire's genius attribution.

The loop is therefore endogenous in part: branch prominence influences which outputs are attributed to the branch, and those attributed scores can then influence future branch prominence. This does not invalidate the signal, but it means the score is not a fully independent measure of branch quality. Exposure, selection and evaluator judgement are coupled.

### 3. Existing safeguards are meaningful but incomplete

The implementation already includes several protections:
- Minimum sample size is eight tagged fires per branch.
- Quality window is three hours.
- High requires at least 45% of scores >= 0.55; low requires at least 55% <= 0.25.
- No more than two low branches are dampened in one pass.
- Multipliers are bounded and modest (1.20 and 0.82).
- Internal telemetry streams are explicitly prevented from steering Bonsai attention, avoiding the previously observed systems-focus saturation.
- Bonsai focus is capped and decays; recent hot branches receive extra decay and starved branches receive a limited bonus.

These reduce runaway behavior and starvation. They do not remove the attribution feedback or establish that the score signal is calibrated, independent or causally beneficial.

### 4. A concrete lifecycle edge: the consumer is not gated by the producer flag

The producer loop is started only when NEX5_QUALITY_SYNTH=1. However, attention._quality_multiplier() reads quality_signal.json without checking that flag. The JSON file lives in the data directory and is not cleared by the inspected startup path. Thus, if a prior run wrote a signal and a later run disables the producer, the consumer can still apply the previously written high/low verdicts.

There is a related cache behavior: when file loading fails, the exception is swallowed and the old in-memory cache is retained. The cache reload timestamp is not advanced on failure, so the consumer retries on subsequent calls, but the last successfully loaded verdicts can continue to apply until a successful read replaces them. A deleted or malformed file therefore does not immediately mean neutral influence.

This is a source-level lifecycle finding, not proof that a particular host currently has a stale file or that the feature flag is enabled. Host/runtime state remains UNKNOWN.

### 5. SelfNarrative is another feedback path, but not the same kind

The current SelfNarrative implementation writes event-triggered entries and reads up to five recent entries into prompt context. Its rut mirror reads genius-tag striking-rate and, when a sustained trough is observed, writes a first-person observation at most once every two hours. That note is a prompt-visible reflection, not a command or a direct attention multiplier.

The distinction matters: SelfNarrative can influence future interpretation through language context, while Quality Synthesis directly changes a numeric attention multiplier. Both can create feedback, but they require different measurements and safeguards. The separate stage_self_narrative implementation and its older draft specification must not be conflated with the Stage-TOM implementation instantiated by Fountain.

### 6. Recommended study and design direction — no runtime change yet

Before changing weights, measure the loop as a causal system:
1. Record per-fire branch candidates, selected branch, score provenance, sample age/count and effective quality multiplier.
2. Compare branch quality under matched exposure, not only raw score averages. At minimum report fires per branch, score distribution, evaluator version and time window.
3. Run offline counterfactual replay with quality multiplier neutralized, then with current multipliers, keeping input events and evaluator tags fixed.
4. Measure winner-kind share, branch entropy/Gini, cold-branch exposure, repeated-branch streaks and output-quality outcomes separately.
5. Test the stale-signal lifecycle: producer flag off with an old file, file deleted, malformed JSON, old timestamp, partial write and a fresh valid file.

A conservative future consumer contract would require an explicit enable condition, a versioned signal schema, a bounded max-age check and neutral behavior for missing/invalid/stale signals. On load failure, stale cached values should not silently remain active beyond their declared validity. Any such change needs focused tests and exact-head CI before implementation is treated as complete.

Do not simply remove feedback. Adaptive cognition needs feedback. The objective is to make the feedback observable, bounded, freshness-aware and resistant to exposure bias—so useful signals can shape attention without becoming self-validating.

### Research conclusion

NEX already contains bounded attention dynamics and a real quality-to-attention feedback loop. Its safeguards limit magnitude and protect some diversity, but branch attribution makes the quality signal partly endogenous. The most actionable source-level issue is that the quality-signal producer is feature-flagged while its consumer is not, and the consumer retains its last cache after read failure. The next responsible step is characterization and measurement, not speculative weight tuning. No runtime code, feature flag, database, schema, frozen S-01–S-25/M1.8, Master Roadmap, Phase 0/Gate 0 or action authority was changed. No tests were run in this study.

**Source anchors inspected at main:** `theory_x/stage2_dynamic/pipeline.py` blob `fbac28e96ffc34dbf59c60242d3ac635835e6e06`; `theory_x/stage2_dynamic/attention.py` blob `d2765c7618e8421bb3e60c8898f749f2370f0344`; `theory_x/stage2_dynamic/bonsai.py` blob `d0389d6036deecf27dcf636771ef817c685b1e7c`; `theory_x/stage_tom/quality_synthesis.py` blob `284d37ef654eb2e43783e3cb6200e3f995229d75`; `theory_x/stage_tom/global_workspace.py` blob `39d833d4a88ed3ad371daf7b62e7295d0dda6637`; `theory_x/stage6_fountain/generator.py` blob `26061914b1dd80858c3568217cd1ef0c49ce2c51`; `theory_x/stage_self_narrative/self_narrative.py` blob `15d8c1dd1de8332b3d12e06a096aac2c0b2b2cb3`; `research/NEX_BONSAI_FOUNTAIN_WORKSPACE_TRACE_2026-11-28.md` blob `2e0b856b3cadd1c2c3e2152a5be865492f9447cb`.

**Host/runtime unknowns:** actual NEX5_QUALITY_SYNTH, NEX5_SELF_NARRATIVE and NEX5_BRANCH_TEMP settings; whether data/quality_signal.json exists on any deployment; current contents/timestamp; live per-branch sample distributions and actual runtime outcomes.

## 86. Prompt-level self-reinforcement: the active Fountain SelfNarrative path (28 November 2026)

**Question studied:** what does the SelfNarrative feature actually feed back into the next Fountain generation, and which implementation is active on the generator path?

### Correct implementation identity

The Fountain generator imports `SelfNarrative` from `theory_x.stage_tom.self_narrative` when `NEX5_SELF_NARRATIVE=1`. Before each relevant generation prompt is sent, it calls `get_narrative()` and appends the returned living narrative to prompt parts. This is the implementation that matters for the Fountain path.

It is not the same class as `theory_x.stage_self_narrative.self_narrative.SelfNarrative`, which is an event-log reader/writer with a five-row prompt formatter and a separate rut-notice tick. Do not use tests for one class as evidence that the other is tested.

### What the Fountain narrative composes

The Stage-TOM `build_narrative()` reads:
- recent real Fountain fires, excluding short, bracket-prefixed and near-duplicate items;
- the three most recent promoted T6 beliefs, filtered to avoid self-referential template residue;
- the three currently active branches over a two-hour window;
- the most recent HOT self-observation below the tombstone tier;
- an aggregate self-model summary;
- the current carried momentum thread, prepended as the leading line when present.

It then assembles a prompt block describing what NEX has actually been attending to. It is generated from existing records and statistics, not from a separate LLM call at prompt assembly time.

### The feedback path

The cycle is:

1. Fountain selects attention and context, then generates a thought.
2. The resulting fire is recorded with its hot branch and related evidence.
3. Later narrative assembly reads recent fires, active branches, beliefs, self-model statistics and momentum.
4. The composed narrative is injected into a later Fountain prompt when the feature flag is enabled.
5. That next thought can influence future branch attribution, memory, beliefs and momentum.

This is a prompt-level feedback loop. It can improve continuity by reminding NEX of recent activity and carried intent. It can also create self-confirmation: a branch is attended, appears in the narrative because it was attended, and is then presented as evidence of what NEX is currently about. Momentum can reinforce this effect by leading the narrative.

The implementation contains some useful anti-contamination choices: near-duplicate filtering for recent fires, filtering of known self-referential template residue, tier filtering for HOT observations, and a separation between aggregate pattern summary and specific recent events. These reduce some noise; they do not establish causal independence or prevent all repeated-theme amplification.

### Test and rollout boundary

The generator constructor and prompt insertion both check `NEX5_SELF_NARRATIVE=1`. The host's actual flag value is unknown. The inspected `tests/test_self_narrative.py` targets the separate `theory_x.stage_self_narrative` class, not the Stage-TOM `build_narrative()` implementation used by Fountain. Therefore it must not be cited as direct coverage of the Fountain prompt-injection path.

A focused test suite for the actual path should cover:
- feature flag off: no instance and no narrative prompt block;
- feature flag on with no fires: no block and no generation failure;
- branch diversity and stale records: narrative reflects the intended bounded time windows;
- repeated identical fires: near-duplicate filtering is deterministic;
- momentum present/absent: carry appears only when valid and does not dominate all other evidence;
- self-referential template filtering: both positive and negative examples;
- adversarially long narrative inputs: bounded prompt contribution;
- prompt provenance: record which source rows contributed, so the narrative can be audited after a fire.

### Reuse-first design recommendation

Do not remove continuity. Instead, make the narrative an evidence-balanced summary rather than a mirror of whichever branch happened to win most recently:
- preserve source diversity and explicit timestamps/ages;
- cap contribution per source category, not only total recent-fire count;
- distinguish observed history from current hypotheses and carried intentions;
- expose branch exposure counts alongside branch names, so frequency is not mistaken for merit;
- prevent a momentum item from silently becoming a persistent identity claim;
- retain provenance from each prompt fragment back to its source records.

These are proposed measurement and design improvements, not current behavior or new policy authority. The narrative remains interpretive context. It cannot approve, block or execute operations.

### Research conclusion

The active Fountain SelfNarrative path is a bounded-by-source, prompt-injected composition of recent fires, active branches, T6 beliefs, HOT observations, aggregate self-model and momentum. It creates a meaningful continuity loop, but also risks reflecting prior attention back as evidence for future attention. The correct next step is direct tests and provenance/exposure measurement for the Stage-TOM implementation—not assumptions based on the similarly named event-log class. No runtime code, feature flag, database, schema, frozen S-01–S-25/M1.8, Master Roadmap, Phase 0/Gate 0 or action authority changed. No tests were run in this study.

**Source anchors inspected at main:** `theory_x/stage6_fountain/generator.py` blob `26061914b1dd80858c3568217cd1ef0c49ce2c51`; `theory_x/stage_tom/self_narrative.py` blob `5fbc617fadc177ade59b45acf118b77c43ef2e84`; `theory_x/stage_self_narrative/self_narrative.py` blob `15d8c1dd1de8332b3d12e06a096aac2c0b2b2cb3`; `tests/test_self_narrative.py` blob `a293b97d46a7db14fb9302e2c3206b4516eefdb1`.

**Host/runtime unknowns:** actual `NEX5_SELF_NARRATIVE` setting, current Fountain prompt composition, recent-fire distribution, branch exposure skew, actual momentum quality and production effects.

## 87. Momentum lifecycle correctness: resolution belongs to a thread, not to the singleton row (28 November 2026)

**Question studied:** when one carried thought ends and a genuinely new thought begins, does momentum persistence reset all state that belongs to the old thread?

### 1. Confirmed persistence behavior

The momentum table is a singleton row (`id=1`). `capture_momentum()` reads the prior fragment and carry count, uses distinctive-word overlap to decide whether the new thought is the same thread, and sets:
- same thread: prior carry count + 1;
- different thread: carry count = 1.

It then upserts updated time, branch, fragment, surprise score/note and carry count. The conflict-update list does **not** include the `resolved` column.

`stamp_resolution()` writes `resolved` on that singleton row. `read_momentum()` reads the value later and, when `NEX5_CARRYOVER=1`, renders a clause saying the prior cycle settled into a belief or stalled.

### 2. Lifecycle defect: new thread inherits old resolution

A concrete sequence follows from the code:
1. Thread A is captured.
2. Thread A is stamped `resolved=1` (or `resolved=0`).
3. A genuinely different Thread B is captured. Its carry count resets to one, but the upsert leaves `resolved` untouched.
4. A subsequent read of Thread B can report Thread A's resolution outcome.

At the function boundary, this is stale provenance: the outcome is stored on the singleton row, but the row's identity has moved to a new fragment. Important call-site qualification: the inspected Fountain generator captures momentum around line 2812 and, when NEX5_CARRYOVER=1, stamps the current fire's outcome later around line 3150. In a normal successful full fire with that flag enabled, the later stamp should overwrite the inherited value before the next fire reads it. The inheritance remains observable for direct callers that do not stamp, when the feature is off and later enabled against an existing row, when capture succeeds but the later stamp is skipped/fails, or when capture rejects a short thought but the later stamp still applies to the previous row. The existing unit test verifies resolution rendering for one thread and a legacy schema migration; it does not test thread transitions or the full generator ordering.

### 3. Rendering inconsistency

The base prompt line always says: `this thread isn't finished.` If `NEX5_CARRYOVER=1` and `resolved` is non-NULL, the renderer appends either `last cycle it settled into a belief` or `last cycle it stalled; nothing settled.`

For a resolved thread, the prompt can therefore say both that it is unfinished and that it settled into a belief. For a stalled thread, "isn't finished" may be semantically compatible, but it still conflates a thread's current state with the generic carry wording. Resolution is currently an optional annotation, not a state transition that changes the base sentence.

### 4. Important nuance: the resolution flag is not used as a read gate

The inspected `read_momentum()` rejects stale rows older than 30 minutes, empty fragments and carry counts above three. It does not suppress a resolved thread. That may be intentional: a resolved topic can remain useful context briefly. Therefore the appropriate correction is not automatically "hide every resolved thread". It is to make the resolution status accurate, thread-bound and coherently phrased.

### 5. Reuse-first correction proposal — not implemented

Keep the singleton storage design unless a broader event-history requirement justifies a schema change. At minimum:
- When a new thread is detected, explicitly reset `resolved` to NULL in the same upsert that replaces the fragment and resets carry count.
- Keep same-thread captures' resolution behavior explicit: decide whether a new materially changed continuation clears a previous resolution or whether a resolved thread is considered closed and should not be recaptured. Encode that policy in tests.
- Render the base line according to resolution: unresolved/unknown, resolved, or stalled; do not state "unfinished" unconditionally.
- Treat resolution as evidence about the exact fragment/version that was evaluated. If the fragment changes, the old result must not silently follow it.
- Consider a stable thread fingerprint or monotonically increasing thread generation only if needed for audit/replay; do not introduce schema complexity without evidence.

### 6. Required regression tests

1. Capture A, stamp resolved true, capture dissimilar B; assert B has carry_count 1 and resolved NULL.
2. Repeat with A stamped false; assert B does not inherit false.
3. Capture same-thread continuation after resolution and assert the chosen policy explicitly.
4. With carryover enabled, assert resolved text never also says "this thread isn't finished".
5. With carryover disabled, verify the legacy prompt contract is intentionally specified.
6. Verify old/stale rows remain silent after 30 minutes and exhausted rows remain silent after the carry limit.
7. Verify all state transitions through injected Reader/Writer handles, preserving the one-pen persistence model.

### Research conclusion

The anti-rut design has a good core: similarity-based carry counting, a three-carry limit and a 30-minute expiry directly address a previously observed self-reinforcing loop. But the singleton row combines current-thread content with a resolution field whose value is not reset when the thread changes. This creates a specific stale-outcome inheritance bug and a contradictory prompt clause. Fixing the lifecycle is safer than changing carry thresholds or removing continuity. No runtime code, database schema, feature flag, frozen S-01–S-25/M1.8, Master Roadmap, Phase 0/Gate 0 or action authority changed. No tests were run in this study.

**Source anchors inspected at main:** `theory_x/stage_tom/momentum.py` blob `45d0249fe445871ebb2bfbcdb2da6e131a229e18`; `theory_x/stage6_fountain/generator.py` blob `26061914b1dd80858c3568217cd1ef0c49ce2c51`; `tests/test_momentum_writer.py` blob `fdbab169457a9ebe8c3c451c69b635e200127bd6`.

**Host/runtime unknowns:** whether `NEX5_CARRYOVER` is enabled on any deployment; actual momentum row contents; frequency of distinct-thread transitions after a resolution stamp; live database state.

## 88. Momentum call-site sequencing: capture, persistence and outcome stamping (28 November 2026)

**Question studied:** does the momentum lifecycle finding survive inspection of the full Fountain call sequence, or is it corrected by a later stage?

### Actual ordering in Fountain

The inspected `generator.py` path performs these operations in this order:
1. Optional HOT observation is written.
2. If `NEX5_MOMENTUM` is enabled (default "1"), `capture_momentum()` stores the generated thought and selected carry branch.
3. The Fountain event pair and downstream attribution/crystallization work proceed.
4. If `NEX5_CARRYOVER=1` and the generator is not stopping, `stamp_resolution(bool(crystallized_id))` stamps the outcome onto the current momentum row.

The narrative prompt assembly reads momentum earlier in the generation path, so it consumes the prior fire's state. The end-of-fire capture and optional outcome stamp prepare the state for a later fire.

### Revised interpretation of section 87

The stale-resolution issue is real at the `capture_momentum()` function boundary, because the upsert replaces the thread but omits `resolved`. However, a successful ordinary Fountain cycle with `NEX5_CARRYOVER=1` will normally call `stamp_resolution()` later in that same fire and overwrite the inherited result before the next fire reads it.

Therefore it would be inaccurate to claim that every normal feature-enabled full cycle necessarily exposes stale resolution to the next prompt. The edge cases that still merit direct testing are:
- direct use of `capture_momentum()` without a subsequent stamp;
- a prior resolved row surviving while carryover is disabled, then the flag being enabled later;
- capture succeeds but the later stamp is skipped by shutdown or fails;
- capture rejects the new thought (for example, fewer than six words), but the later stamp still runs and may stamp the prior row with the current fire's outcome;
- exception and writer-failure paths where capture/stamp do not complete as a pair.

The short-thought case is especially important: `capture_momentum()` returns false before replacing the old row, while the generator does not inspect that return value before the later `stamp_resolution()` call. Thus the outcome stamp can refer to the old momentum thread rather than the current thought.

### Revised recommendation

Do not treat the function-level finding as proof of a routine production failure. Test the whole transaction boundary. A robust design would make the thread identity explicit and ensure that outcome stamping is conditional on a successful capture of the same thread identity in the current fire. At minimum, reset `resolved` when a distinct thread is stored and make the generator check capture success before stamping. If adding a thread identifier is too invasive, a local success boolean plus a stable fragment/version check may be sufficient; choose only after examining the writer contract and concurrency assumptions.

Tests should exercise the generator ordering, not just isolated helpers: successful capture + stamp; failed/short capture + attempted stamp; shutdown between capture and stamp; stamp exception; feature flag off/on transition; and next-fire read. Assert that an outcome is never attached to a different fragment.

### Research conclusion

The right lesson is not "momentum is broken". The design already separates capture from later outcome evaluation, and the normal enabled path attempts to pair them. The weakness is that the pair is not explicitly bound by a thread identity or capture-success token. This is a lifecycle-integrity and edge-case problem, best solved with transaction-aware tests and explicit association—not by removing continuity or changing its thresholds. No runtime code, database schema, feature flag, frozen S-01–S-25/M1.8, Master Roadmap, Phase 0/Gate 0 or action authority changed. No tests were run in this study.

**Source anchors inspected at main:** `theory_x/stage6_fountain/generator.py` blob `26061914b1dd80858c3568217cd1ef0c49ce2c51`; `theory_x/stage_tom/momentum.py` blob `45d0249fe445871ebb2bfbcdb2da6e131a229e18`; `tests/test_momentum_writer.py` blob `fdbab169457a9ebe8c3c451c69b635e200127bd6`.

**Host/runtime unknowns:** actual `NEX5_MOMENTUM` and `NEX5_CARRYOVER` settings; stop timing and writer failure rates; actual short-thought rate; current deployed momentum row.

## 89. Self-model aggregation: bounded time window, unbounded row scan (28 November 2026)

**Question studied:** is the prompt-injected self-model computationally bounded in both time and work, or only by a lookback window?

### Source behavior

The active Stage-TOM SelfNarrative calls `aggregate_self_model(beliefs_db)` during narrative construction. The aggregator:
- uses a default 24-hour lookback;
- queries all `beliefs` rows where `source='hot_observer'` and `created_at > cutoff`;
- orders newest first but has no SQL `LIMIT`;
- fetches the entire result set into memory;
- returns no summary until at least five rows exist;
- scans every fetched row to count template/grounded observations and per-branch rates.

The HOT observer currently attempts one write every third eligible call, using process-local counter state. This reduces write volume but is not a hard work bound: restart behavior resets the counter, and the actual eligible fire rate is host/runtime-dependent.

### What is bounded and what is not

The 24-hour predicate is a semantic time window, not a strict maximum row count. If NEX runs at higher fire rates, or multiple producers write HOT observations, the aggregator's query and Python loop grow with the number of rows in that window. The prompt output itself is short (a few summary sentences), but the work required to produce it is proportional to the full row count.

No evidence was found in the inspected aggregator source of a row cap, pagination, incremental roll-up or cached aggregate. The database index coverage for the exact `source + created_at` predicate was not established by this inspection and remains unknown.

This is a potential scaling/latency concern, not proof of a current performance failure. At the documented design rate of one observation per three eligible calls, the expected daily row count may be modest; actual host rate is unknown.

### Reuse-first design direction

Before introducing a cache or summary table:
1. Measure actual HOT rows per 24 hours, query latency, returned row count and aggregation time.
2. Inspect the beliefs schema/indexes for the exact predicate.
3. Add a deterministic row-count/latency benchmark at realistic and adversarial volumes.
4. If a hard cap is needed, define the statistical semantics first. A simple newest-N limit changes the denominator and can bias branch comparisons; use explicit windowed sampling or incremental sufficient statistics only if they preserve the intended interpretation.
5. Keep the natural-language summary bounded and provenance-aware: observation count, lookback, cutoff and any sampling method should be visible or auditable.
6. Preserve the minimum-five-observations rule and ensure branch rates still require at least three classified observations.

A possible first implementation may be a bounded read with an explicit sample/aggregation contract, but it should not be chosen until measurement shows whether the current 24-hour scan is actually costly.

### Test coverage boundary

The inspected tests include broad self-model and behavioural-propagation tests, but the repository tree did not expose a dedicated test module named for `self_model_aggregator`. This is not proof that no indirect coverage exists. Add direct tests for empty/under-five samples, exact 24-hour cutoff, high-volume windows, unknown/unclassified observation text, branch minimum counts, deterministic ordering and output provenance.

### Research conclusion

The self-model aggregator has a bounded temporal horizon and a bounded textual output, but no explicit row/work budget. The next responsible step is to measure row volume and query cost, then preserve statistical meaning if a cap is introduced. Do not mistake a time filter for a computational bound. No runtime code, schema, indexes, feature flags, frozen S-01–S-25/M1.8, Master Roadmap, Phase 0/Gate 0 or action authority changed. No tests were run in this study.

**Source anchors inspected at main:** `theory_x/stage_tom/self_model_aggregator.py` blob `f05a03e8450c05bc92975bb668feb4baa7220488`; `theory_x/stage_tom/self_narrative.py` blob `5fbc617fadc177ade59b45acf118b77c43ef2e84`; `theory_x/stage_tom/hot_observer.py` blob `67ca7e3662ec15a05072544500761822471d43fb`; `tests/test_behavioural_self_model_propagation.py` blob `991f1766d003d94d21fcc8bdf73214a1e8d2de15`; `tests/test_self_model.py` blob `70817f1ba5aa371ee7f008967b45c16f27d6380d`.

**Host/runtime unknowns:** actual HOT observer write rate, 24-hour row volume, query plan/index use, aggregation latency, and whether multiple processes write HOT observations to the same beliefs database.


## 90. Belief formation, promotion, revision and prompt selection: separate the signals (28 November 2026)

**Question studied:** does NEX distinguish a belief's origin, confidence, corroboration, promotion, repeated use, contradiction and prompt exposure—or collapse them into one undifferentiated notion of "knowing"?

### 90.1 The belief record carries several different dimensions

The canonical beliefs schema stores content, tier, confidence, created_at, promotion/demotion timestamps and promotion_log, source, source_stream, source_kind, branch_id, locked, paused, corroboration_count, last_referenced_at, reinforce_count, use_count and erosion_stage. It also defines typed belief_edges: supports, opposes, synthesises, cross_domain and refines.

These fields are not interchangeable:
- **Origin/provenance** answers who or what produced the row, and what kind of source it came from.
- **Confidence** is a numeric signal used directly by retrieval.
- **Tier** is an ordinal lifecycle/strength category used by promotion, decay and retrieval eligibility.
- **Corroboration count** is a counter used by a tier-promotion rule.
- **Use/reinforcement** record different kinds of interaction.
- **Edges** represent typed relationships between belief rows.
- **Paused/locked** alter eligibility or mutability.

The schema therefore supports a richer lifecycle than a single scalar "belief strength." Any future unification must preserve these distinctions rather than flatten them.

### 90.2 Confidence controls retrieval, while tier promotion follows a different path

BeliefRetriever.retrieve() currently admits rows with tier <= 6, paused = 0, and (locked = 1 OR confidence >= 0.15). Keyword relevance is multiplied by confidence. The isolated Stage-5 pathway audit built a throwaway database from the real schema and exercised the real retriever: an unlocked 0.10-confidence matching belief was excluded, the same belief at 0.50 was admitted, and equally matching 0.90/0.30 beliefs ranked in that order. This is isolated mechanism evidence, not confirmation of the live population or deployment.

BeliefPromoter.corroborate() is a separate mechanism. It increments corroboration_count transactionally and promotes a tier when the configured threshold for that tier is reached. It stamps last_promoted_at and appends an event to promotion_log; the promotion itself does not directly increase confidence. survive_challenge() also has a tier-promotion path, while decisive_contradiction() demotes by two tiers and records the demotion. decay_pass() demotes idle unlocked Tier 5–7 beliefs based on COALESCE(last_referenced_at, created_at) and the configured idle window.

Therefore, **tier promotion is not proof that confidence was independently recalibrated**, and confidence changes are not the same thing as promotion. Keep both event histories explicit.

### 90.3 Repeated reinforcement can change confidence—but through provenance erosion

ProvenanceErosion advances an unprotected, unlocked belief through external → nex_absorbed → nex_integrated → nex_core when its reinforce_count reaches 10, 30 and 80 respectively. Each stage transition resets the reinforcement counter and adds 0.02 to confidence, capped at 1.0. record_use() increments use_count; it does not itself apply the confidence increment. In the inspected corroborate() path, a successful tier promotion calls record_reinforce() after the promotion transaction commits.

This is a meaningful distinction: confidence can rise through an assimilation/reinforcement lifecycle, not only through new external evidence. The code's name "erosion" describes provenance becoming internalised; it must not be interpreted as a truth-verification score. A belief becoming more "NEX-owned" is not, by itself, evidence that its proposition is more accurate.

### 90.4 Contradiction handling is multi-stage, not immediate truth adjudication

The Harmonizer's first paradox pass writes an opposes edge and records a paradox event without immediately pausing or retiring either belief. Escalated resolution after an incubation interval pauses both beliefs, then follows the configured resolution path: held tension when its feature flag is enabled, otherwise synthesis/retirement logic. The promoter's decisive-contradiction path demotes a belief by two tiers; the decay path separately demotes on inactivity.

These mechanisms show that NEX has machinery for preserving conflict and changing belief status. They do not establish that every contradiction is detected, that every opposes edge is semantically correct, or that the system has a universal evidence-adjudication procedure. The live feature flags and actual conflict-resolution outcomes remain host/runtime unknowns.

### 90.5 A prompt-selection label is stronger than the actual query

theory_x/stage_tom/self_narrative.py::_recent_t6() is documented as returning the "most recently promoted T6 deep beliefs." The actual query selects rows where tier=6, orders by created_at DESC, and considers up to n * 4 candidates before returning at most three. It does not order by last_promoted_at or consult promotion_log.

Consequently, the selection is most-recently-created among current Tier-6 candidates, not most-recently-promoted. A belief promoted to Tier 6 long after creation can be missed in favour of a newer-created belief that has been Tier 6 all along. This is a concrete semantic mismatch between the docstring and query. It is not proof that the current prompt is harmful, but it means prompt continuity can be based on the wrong temporal notion.

**Reuse-first correction direction:** decide whether the narrative wants "recently created", "recently promoted", or "recently changed"; then make the query and tests express that exact concept. If promotion recency is intended, order by last_promoted_at with an explicit NULL policy and stable tie-breaker, and test promotion-after-creation, null timestamps, demotion/re-promotion, paused/tombstoned candidates, and the bounded candidate scan. Do not change the query until that semantic choice is explicit.

### 90.6 The missing distinction: evidence quality versus reinforcement history

The inspected schema and pathways provide provenance, typed relations, confidence, tier transitions, reinforcement and contradiction handling. They do not, in the inspected pathway, amount to a single calibrated evidence ledger that records for each proposition:
- the exact supporting or opposing observations and their source identities;
- whether sources are independent or merely repeated copies;
- observation time versus ingestion time;
- the prediction or condition that would falsify the proposition;
- how much each observation changed confidence, and why;
- whether a later observation is genuinely new evidence or merely reuse/retrieval of an existing belief.

The typed edge graph can express supports and opposes, and source-kind stamping can classify origin, but these are not by themselves a proof of independent corroboration or calibrated probability. The Stage-4 audit also records provenance completeness as host-only unknown. Avoid describing NEX as having fully evidence-grounded belief revision until that gap is measured and tested.

### 90.7 Development direction: preserve a traceable belief state machine

Before adding another belief engine or schema:
1. Map every producer and updater to the existing fields and event log; distinguish creation, source stamping, corroboration, challenge survival, decay, contradiction, pause, synthesis, retirement and provenance erosion.
2. Define a proposition-level evidence event as a candidate design, not a new authority: stable belief identity, observation identity, source/provenance, support/opposition relation, independence group, event time, ingestion time, and rationale.
3. Keep confidence calibration separate from tier promotion and provenance assimilation. Any confidence update should state which evidence event caused it and whether the event is independent.
4. Make prompt selection semantics explicit: created, promoted, revised, referenced, or recently supported are different questions.
5. Test counter-evidence and revision symmetrically with reinforcement; include repeated identical sources, copied content, delayed observations, conflicting evidence, and replay/idempotency.
6. Measure actual source-kind completeness and live promotion/revision distributions only through the authorised host-side read-only gate. Do not infer live operation from source presence or isolated fixtures.

### Research conclusion

NEX already has distinct mechanisms for provenance, retrieval confidence, tier promotion/demotion, reinforcement-based assimilation, contradiction edges and prompt-level belief selection. The important design risk is not that these mechanisms are absent; it is that their meanings can be conflated. The clearest source-level mismatch found in this pass is _recent_t6() calling its result "most recently promoted" while ordering by creation time. The deeper architectural opportunity is a traceable, proposition-centred evidence history that separates independent evidence from repeated reinforcement and separates truth confidence from internal ownership.

No runtime code, database schema, indexes, feature flags, tests, frozen S-01–S-25/M1.8, Master Roadmap, Phase 0/Gate 0 or action authority changed. This was source research and manual documentation only; no tests were run in this study.

**Source anchors inspected at main:** substrate/schema/beliefs.sql blob 44a3f95dbf4c522d84dd030c9c825afffe760b6b; substrate/source_kind.py blob 11b052d529defefecd16caafae5b95a3b251c0f0; theory_x/stage3_world_model/retrieval.py blob aa3eeb15c9a4a19a24a6d328bc370cd0a4438cf3; theory_x/stage3_world_model/promotion.py blob 035f89c34d0bd9391bc531107f7689f14a529042; theory_x/stage3_world_model/erosion.py blob 93a80b9105d7510c58f793e40cecbb1364832d5b; theory_x/stage3_world_model/harmonizer.py blob e72008ec21ad91e20cbdcfc73bacf14263e34382; theory_x/stage_tom/self_narrative.py blob 5fbc617fadc177ade59b45acf118b77c43ef2e84; tests/test_belief_confidence_retrieval_pathway.py blob b2505f2494db8fcd2453f7f5ee28184906e83daa; tests/test_promotion_atomicity.py blob 503cfb9f130391245a2b99746080cf3ae3c5cfd7; tests/test_erosion.py blob 530191ab3252a632ec077eaed8988ae5a4819357; tests/test_source_kind.py blob d54ea4cb30b8d8315b1e3f34903f6088198c5374.

**Host/runtime unknowns:** live source-kind completeness; active confidence/tier distributions; which producers and promotion/contradiction loops are firing; feature flags governing semantic retrieval, tier climb, held tension and related pathways; whether the live prompt is using this Stage-TOM narrative; and whether the source-level selection mismatch is currently exercised.


## 91. Corroboration provenance: similarity is not source independence (28 November 2026)

**Question studied:** what exactly increments a belief's corroboration count, and does the mechanism distinguish independent evidence from repeated, related or self-generated signals?

### 91.1 Two observed routes call the same corroboration counter

The Stage-3 PipelineHooks route is registered as the DynamicState pipeline hook and is called after step F. It ignores events below magnitude 0.6, forms query tokens from sensation_source and branch_id, scans a bounded set of recent eligible beliefs, and calls BeliefPromoter.corroborate() when token overlap reaches 0.7. The default candidate scan is the 50 newest unlocked, unpaused beliefs through Tier 7. With NEX5_TIER_CLIMB=1, it additionally considers up to 500 Tier-6 rows.

The WorldConsolidator route is separate and dark unless NEX5_WORLD_CONSOLIDATE=1 (dry/report modes do not arm writes). It samples a bounded recent Tier-7 window, filters apparent world beliefs, embeds and clusters them by cosine similarity, then calls corroborate() on eligible cluster members, subject to a maximum of three promotions per run. The inspected code does not attach a distinct observation/source identity to each corroboration call.

Both routes therefore feed the same corroboration_count and tier-promotion mechanism, but their triggering evidence is not equivalent:
- PipelineHooks uses a high-magnitude event plus lexical overlap with a stored belief.
- WorldConsolidator uses similarity among stored beliefs in a cluster.
- Neither call signature passes an explicit independent-source group, observation identity or evidence-event record into corroborate().

This does not prove that the current system double-counts a particular event or that these routes are both enabled. It establishes that the shared counter itself does not enforce source independence.

### 91.2 Why this matters

A threshold such as three, five or eight corroborations is only meaningful as an evidence threshold if the counted events have a defined relationship to independent observations. If several events derive from one upstream feed, or several clustered beliefs are paraphrases/copies of one source, the counter can rise without the same number of independent confirmations.

The opposite risk also exists: overly strict deduplication could discard genuinely independent observations that happen to share content. Independence therefore cannot be inferred from text similarity alone. It needs source lineage and event identity.

The source_kind trigger classifies each belief's broad origin (authored, self, seeded, world, other_mind or received), and source_stream can preserve a sense-stream identity. Those fields are valuable foundations, but a broad kind such as world does not identify a particular feed, publisher, upstream event or copied source chain. Nor does source_kind by itself prove that two records are independent.

### 91.3 The current promotion threshold is tier-dependent, not evidence-calibrated

The current corroboration thresholds are Tier 7→6: 3; Tier 6→5: 5; Tier 5→4: 8; Tier 4→3: 12; Tier 3→2: 20. Tier 2→1 is reserved for reseed ceremony. The atomicity tests verify that concurrent calls do not lose increments and that threshold crossing promotes exactly once. That is a concurrency guarantee, not a guarantee that the increments represent independent evidence.

The promotion transaction itself increments the counter and records the tier event. After a promotion commits, the code writes a supports edge to a high-overlap peer and may record provenance reinforcement. The edge is a useful relationship record, but it is not a substitute for the source evidence that justified the count.

### 91.4 A safer evidence contract

Reuse the existing source_kind, source_stream, belief_edges and promotion_log before proposing a new subsystem. The next evidence-quality layer should make each corroboration attributable to a stable event:
- observation/event ID and upstream source identity;
- source lineage or copy/derivation group;
- source_kind and source_stream where available;
- time observed and time ingested;
- target belief ID and support/opposition rationale;
- whether this event has already contributed to this belief's count;
- whether it is independent of prior contributing events.

A deduplication key should be deterministic and scoped to the target belief plus evidence event, so replay does not increment twice. Independence groups should be explicit and conservative: unknown lineage remains unknown, not silently independent. Keep the existing tier thresholds unchanged until a measurement study demonstrates what their counts currently mean.

### 91.5 Test and measurement plan

- Unit-test same event replay, distinct events from the same upstream source, independent sources with similar text, copied/paraphrased source material, missing provenance, and source-stream inheritance.
- Test PipelineHooks with repeated events from one source and distinct source events; assert exactly which events can increment the count.
- Test WorldConsolidator clusters containing paraphrases from one source versus independently sourced observations; verify cluster membership alone is not labelled independent evidence.
- Preserve the existing concurrent atomicity tests; add provenance/idempotency tests rather than replacing them.
- Report raw corroboration count separately from independent-source count and unknown-lineage count. Do not silently reinterpret historical counts as independent evidence.
- Confirm actual feature flags and producers only through the authorised host-side read-only gate.

### Research conclusion

The existing code has two concrete corroboration feeders and a transactionally safe counter. The counter's concurrency correctness is established by tests, but independence of the counted evidence is not enforced at the shared API boundary. The next meaningful improvement is not a more elaborate promotion formula: it is provenance-aware, replay-safe evidence accounting that makes "five corroborations" mean something inspectable.

No runtime code, database schema, indexes, feature flags, tests, frozen S-01–S-25/M1.8, Master Roadmap, Phase 0/Gate 0 or action authority changed. This was source research and manual documentation only; no tests were run in this study.

**Source anchors inspected at main:** theory_x/stage3_world_model/pipeline_hooks.py blob 6750bb427ed493a3310d9ea69d0e82207d0d38f1; theory_x/stage3_world_model/world_consolidation.py blob 192550c20c7b8e776dfa55f4f82d80fd4cc7ce69; theory_x/stage3_world_model/promotion.py blob 035f89c34d0bd9391bc531107f7689f14a529042; substrate/source_kind.py blob 11b052d529defefecd16caafae5b95a3b251c0f0; tests/test_promotion_atomicity.py blob 503cfb9f130391245a2b99746080cf3ae3c5cfd7; tests/test_source_kind.py blob d54ea4cb30b8d8315b1e3f34903f6088198c5374.

**Host/runtime unknowns:** NEX5_TIER_CLIMB, NEX5_WORLD_CONSOLIDATE and related flags; actual PipelineHooks event/source mix; whether WorldConsolidator is armed; upstream lineage quality; number of distinct independent sources represented by historical corroboration counts; and live promotion rates by source kind.


## 92. SelfNarrative belief injection: a second path can bypass retrieval eligibility (28 November 2026)

**Question studied:** does the prompt's "What has consolidated deeply" section obey the same eligibility rules as ordinary belief retrieval?

### Source behavior

The ordinary BeliefRetriever explicitly filters for tier <= 6, paused = 0, and (locked = 1 OR confidence >= 0.15). Its docstring states those filters, and the SQL enforces them before scoring.

The Stage-TOM SelfNarrative has a separate direct query in _recent_t6(). It selects content from beliefs where tier=6, orders by created_at DESC, and considers a bounded candidate set (n * 4) before returning at most n results. It does not filter paused, confidence, locked, or erosion_stage. build_narrative() then inserts up to two of those results under "What has consolidated deeply" whenever the narrative is built.

This is a distinct prompt-injection path; it does not call BeliefRetriever and does not inherit its eligibility contract.

### Consequence

A Tier-6 belief that is paused by the Harmonizer can still be selected by _recent_t6() and inserted into SelfNarrative. Likewise, an unlocked Tier-6 belief below the ordinary retrieval confidence floor can be included. The direct query therefore has a wider eligibility set than ordinary retrieval.

This is a source-level possibility, not evidence that a specific paused or low-confidence belief has actually appeared in a live prompt. The path is also conditional on SelfNarrative being enabled and on at least one substantive fire existing, because build_narrative() returns None when there are no fires.

The mismatch matters because pausing is a deliberate state change in the contradiction-resolution lifecycle. If a belief is paused to prevent ordinary retrieval while a conflict is being resolved, a separate prompt path should not silently reintroduce it as a settled deep belief.

### Reuse-first direction

Do not duplicate a second definition of belief eligibility. Prefer one shared read-only eligibility predicate/query contract used by ordinary retrieval and narrative selection, with explicit exceptions documented where they are genuinely intended. Before changing the query, decide whether SelfNarrative is intended to include:
- only beliefs eligible for ordinary retrieval;
- paused beliefs as explicit unresolved tensions, labelled as such;
- low-confidence candidates as hypotheses, clearly distinguished from established beliefs.

If unresolved tensions should remain visible, they should be rendered in a separate, explicitly qualified section—not silently placed under "What has consolidated deeply."

### Tests required

Add direct tests for the active Stage-TOM module, not just the older separate Stage-SelfNarrative implementation:
- paused Tier-6 belief is excluded from the "deeply consolidated" section, or appears only in a dedicated unresolved-tension section;
- unlocked confidence 0.149 versus 0.150 boundary;
- locked low-confidence behavior if ordinary retrieval eligibility is the intended shared contract;
- Tier-6 creation-time ordering and the separate promotion-time semantic question from §90;
- no substantive fires returns None and performs no prompt injection;
- stable ordering and bounded candidate selection;
- prompt provenance identifies whether each line came from ordinary retrieval, recent creation, promotion, or unresolved tension.

The repository tree contains tests/test_self_narrative.py for the older Stage-SelfNarrative path, while the active Stage-TOM implementation is theory_x/stage_tom/self_narrative.py. Do not treat the older test module as coverage of this direct Stage-TOM query. This inspection did not establish a dedicated direct test module for the active path; indirect coverage may still exist.

### Research conclusion

NEX has two belief-to-prompt routes with different eligibility contracts. The ordinary retriever excludes paused beliefs and applies a confidence floor; Stage-TOM SelfNarrative's direct Tier-6 query does neither. The safest next step is to define a shared eligibility contract and explicitly model unresolved tensions, then test the active prompt path. No runtime code, database schema, indexes, feature flags, tests, frozen S-01–S-25/M1.8, Master Roadmap, Phase 0/Gate 0 or action authority changed. This was source research and manual documentation only; no tests were run in this study.

**Source anchors inspected at main:** theory_x/stage3_world_model/retrieval.py blob aa3eeb15c9a4a19a24a6d328bc370cd0a4438cf3; theory_x/stage_tom/self_narrative.py blob 5fbc617fadc177ade59b45acf118b77c43ef2e84; theory_x/stage3_world_model/harmonizer.py blob e72008ec21ad91e20cbdcfc73bacf14263e34382; tests/test_self_narrative.py (older Stage-SelfNarrative test path; blob SHA to be resolved if exact test evidence is later needed).

**Host/runtime unknowns:** NEX5_SELF_NARRATIVE setting; whether this Stage-TOM narrative is used in the live generator; live Tier-6 paused/low-confidence population; whether any such rows have entered prompts; and actual Harmonizer resolution flags/outcomes.


## 93. Reification retrieval override: current-main eligibility and test gap (28 November 2026)

**Question studied:** does the special `reification_recognition` inclusion path preserve the ordinary belief-eligibility and membrane boundaries, and is the word “always” in its comment an accurate description of the resulting retrieval?

**Evidence snapshot:** current `main` at `18c8f06171e1de35c3210831a49b63d0e2487af0`. This is a static source/test/PR comparison. No host, live database, feature flag or runtime was inspected.

### Current source path

In `theory_x/stage3_world_model/retrieval.py`, the ordinary candidate query applies:

- `tier <= 6`;
- `paused = 0`;
- `locked = 1 OR confidence >= 0.15`.

It does **not** currently include `erosion_stage != 'retired'` in the mainline query.

When `side_filter == "INSIDE"`, the normal candidate rows are first passed through the membrane classifier. After that filtering, the code performs a separate lookup for `source = 'reification_recognition'` and appends the row if its ID is not already present. That second lookup currently has no tier, paused, confidence, retirement or membrane-classification predicate. It can therefore reintroduce a row that the ordinary query would exclude, and it is appended after the membrane side filter has already run.

This is a source-level eligibility bypass, not evidence that a particular inactive row is present in a live prompt. It is also important not to overstate the comment “Always include”: after the row is appended, it still enters the ordinary scoring/selection path. With query tokens, zero-overlap candidates are dropped unless the optional semantic fallback admits them; with an empty-token query, the appended row is still subject to the final `rows[:limit]` slice. The special path is an extra candidate opportunity, not a guaranteed final result.

### Independent test coverage

- `tests/test_belief_confidence_retrieval_pathway.py` builds an isolated database from the real schema and tests the ordinary retriever's confidence floor, locked exception, paused exclusion and tier ceiling. It does not exercise `side_filter="INSIDE"` or the reification override.
- The mainline `tests/test_retrieval.py` exercises FountainGenerator's own-content/seed context path; it does not currently contain the reification-override regression tests.
- PR **#117 — Apply eligibility to reification retrieval override** contains the targeted tests and a proposed source correction. Its head `1dd1985f797bb218dd2aa10d077c092589ac6e63` passed workflow `45803079139` (1,611 passed, 5 skipped, 30 subtests), but the PR remains **open and draft**, based on the older `claude/nex-continuity-wire` commit `de93134f34adac07a3a41c2a05b33720510a2bfc`, not current main `18c8f06171e1de35c3210831a49b63d0e2487af0`. The commit graph is diverged: the #117 branch is 7 commits ahead and 1,016 behind current main, with merge base `fb87e247a116221cc7d814e2ee5ff2e1300f5a87`. Its green run is not current-main validation and its changes are not present on current main.

PR #117 proposes to add `tier < 8`, `paused = 0` and `erosion_stage != 'retired'` to the special lookup, and to exclude retired-marker rows from the ordinary pool. It does not add the ordinary confidence-floor condition to the special lookup. That remaining difference must be an explicit policy decision: should reification recognition be a deliberate confidence-floor exception, or should the same eligibility contract apply? Do not silently assume either.

### Consequence and bounded disposition

There are two separate issues to keep distinct:

1. **Eligibility integrity:** the special candidate lookup currently bypasses ordinary active-state checks and the membrane classifier; the main pool also lacks the independent retired-marker predicate.
2. **Selection semantics:** the comment promises “always include,” but scoring, zero-overlap handling and the result limit can still omit the candidate.

The safest next step is a current-main replay of #117's targeted tests and narrowly scoped filters, but only after the owner confirms the intended treatment of reification beliefs and whether the confidence floor is an exception. Add tests for paused, Tier-8, lower-tier retired, low-confidence, membrane-side mismatch, zero-overlap, empty-query and limit-boundary cases. Keep “eligible candidate” distinct from “selected result” in test names and documentation.

**Disposition:** verified current-main source gap; proposed correction remains unmerged and stale-base. No code, test, schema, index, flag, retrieval policy, mind-map authority, frozen S-01–S-25/M1.8, Master Roadmap, Phase 0/Gate 0 or runtime state was changed in this study. No tests were run for this documentation pass.

**Source anchors inspected:** `theory_x/stage3_world_model/retrieval.py` blob `aa3eeb15c9a4a19a24a6d328bc370cd0a4438cf3`; `tests/test_belief_confidence_retrieval_pathway.py` blob `b2505f2494db8fcd2453f7f5ee28184906e83daa`; current-main `tests/test_retrieval.py` blob `efd27b50c3cdc5ef64769fefcbb5529cc44ea90e`; PR #117 diff and metadata; exact-head workflow `45803079139`.

**Host/runtime unknowns:** effective `NEX5_SELF_NARRATIVE` and retrieval flags; whether INSIDE self-inquiry calls occur in the deployed process; live reification row tier/pause/confidence/retirement state; actual membrane classification of that row; whether it has been selected into any prompt; and whether the draft #117 fix is intentionally superseded or simply awaiting a current-main replay.


## 94. Held-tension prompt injection depends on a separate paradox counter (28 November 2026)

**Question studied:** when the optional held-tension path preserves contradictory beliefs, does the INSIDE chat route reliably surface the explicit tension description, independently of the historical paradox counter?

**Evidence snapshot:** current `main` at `18c8f06171e1de35c3210831a49b63d0e2487af0`. Static source and fixture-test review only; no host/runtime flags or live databases were inspected.

### Lifecycle observed in source

- `mark_paradox()` writes an `opposes` edge and a `harmonizer_events` row with resolution `paradox`. It explicitly does not pause or retire either belief.
- After the incubation interval, `resolve()` transiently sets both beliefs to `paused=1`.
- With `NEX5_HELD_TENSION` unset (the source default), the ordinary resolution path either synthesizes or retires both originals. The retirement updates set `tier=8` and `paused=0`.
- With `NEX5_HELD_TENSION=1`, `_hold_as_tension()` instead unpauses both beliefs, preserves their original content and tier, and writes an unresolved `held_tensions` row. Thus both can again qualify for ordinary retrieval if their tier/confidence otherwise qualifies. The separate `Harmonizer.format_for_prompt()` can render a content-specific “I notice I hold both…” line.

### Caller-level reachability mismatch

The GUI's INSIDE route in `gui/server.py` calls `harmonizer.tick()`, reads `active_paradox`, and only calls `format_for_prompt()` when `active_paradox > 0`.

But `format_for_prompt()` itself checks the open held-tension row first, before consulting the cached paradox count. Its content-specific line therefore does not intrinsically require an active paradox pair; the GUI caller imposes that extra precondition.

The count's meaning depends on `NEX5_HARMONIZER_TENSION_COUNT_FIX`:

- **Flag OFF (source default):** `tick()` counts all historical `resolution='paradox'` events. This can leave `active_paradox > 0` after a pair has been resolved as a held tension, allowing the GUI to reach the content-specific line for the wrong reason. The counter is historical, not a count of currently open paradox pairs.
- **Flag ON:** `tick()` uses the latest event per pair. Once the latest event is `held_tension`, that pair is no longer an open paradox pair. If no other open paradox pair exists, `active_paradox == 0` and the GUI skips `format_for_prompt()` entirely—even though an unresolved held-tension row exists and the formatter would have returned its content-specific line.

This is a caller/formatter contract mismatch. It means the explicit held-tension narration is not independently reachable from the GUI based on the existence of an open held tension; it is accidentally coupled to a separate paradox-count value.

### Test coverage and disposition

`tests/test_held_tension.py` verifies that the two beliefs survive unpaused, the held-tension row is written, and a direct call to `format_for_prompt()` returns the content-specific line. It does not exercise the GUI caller's `active_paradox > 0` guard. The source-level gap is therefore at the integration boundary, not in the formatter's isolated test.

**Disposition:** verified conditional integration gap; no runtime correction made. A bounded follow-up should add a GUI-level or extracted caller-contract test with (a) an open held tension and zero open paradox pairs, and (b) an open held tension plus unrelated historical paradox events. The eventual caller should gate tension formatting on the existence of a relevant tension signal, not on an unrelated count, while preserving the separate generic paradox summary semantics. Do not alter flag defaults or resolution policy as part of that test.

**Source anchors inspected:** `theory_x/stage3_world_model/harmonizer.py` blob `e72008ec21ad91e20cbdcfc73bacf14263e34382` (mark/resolve/hold, counter and formatter); `gui/server.py` blob `ecaa6982544e883a50dbf85c5de1e10f74180c67` (INSIDE caller guard); `tests/test_held_tension.py` blob `7acc6e6d0d98c2f8c252dd74d0a9eda42ec5179a` (direct formatter tests).

**Host/runtime unknowns:** effective `NEX5_HELD_TENSION` and `NEX5_HARMONIZER_TENSION_COUNT_FIX`; whether any unresolved held tensions exist in the deployed database; whether any INSIDE route has attempted to surface them; and the actual prompt-injection frequency. No tests were run in this documentation pass.

No runtime code, test, schema, flag, mind-map authority, frozen S-01–S-25/M1.8, Master Roadmap, Phase 0/Gate 0 or action authority was changed.


## 95. Per-stream provenance: stamping, ranking and identity-floor audit are separate mechanisms (28 November 2026)

**Question studied:** once NEX stamps each belief with `source_stream` and `source_kind`, where does that provenance actually affect retrieval, prompt composition and identity-claim review?

**Evidence snapshot:** current `main` at `18c8f06171e1de35c3210831a49b63d0e2487af0`. Static source and fixture-test review only. No host database or runtime state was accessed.

### Three separate mechanisms

**1. Write-time provenance stamping**

`substrate/source_kind.py` defines six origin kinds (`authored`, `self`, `seeded`, `world`, `other_mind`, `received`) and the stream/source mapping. SQLite insert triggers stamp `source_stream` and `source_kind` at the belief write boundary. A verbatim copy can inherit the earliest existing source stream for identical content; absent a stream, the producer name supplies the kind. This makes provenance available even to producers that do not explicitly pass a kind.

The trigger runs only when `NEW.source_kind IS NULL`; an explicitly supplied kind is therefore trusted at insertion. The separate audit can detect some stream/kind disagreements where source-stream evidence exists. The trigger is a metadata-stamping mechanism, not a policy gate.

**2. Downstream ranking and retrieval**

The ordinary `BeliefRetriever.retrieve()` query selects `id, content, tier, confidence, branch_id, source, locked`; it does not select `source_kind` or `source_stream`. Its relevance score is keyword overlap multiplied by confidence, with branch and optional boilerplate adjustments, then optional spreading-activation blending. The provenance kind is not part of this ordinary retriever's eligibility or score.

`NEX5_SOURCE_KIND` is consumed separately by `theory_x/life/affinity_loop.py` to choose provenance bands for affinity scoring. That is a distinct consumer and a separate flag. Do not infer that because source_kind is stamped, every retrieval or prompt pathway uses it.

**3. Identity-floor audit**

`theory_x/stage_tom/source_kind_audit.py::identity_floor()` scans identity-claim fires in `fountain_events`, joins their recorded `fountain_retrieval_log` belief IDs, and checks whether identity-claim beliefs among those retrieved supports are `authored` or `seeded`. It reports violations and sample IDs; `run_and_record()` writes the audit result to `source_kind_audit_log`. The daily-life schedule assigns this housekeeping audit to 03:00 local time.

This is retrospective measurement, not a pre-generation filter: it runs after a fire and records whether the observed retrieved-belief support met the floor. The tests prove that the audit catches a headline carrying an identity claim; they do not show that the audit blocks the prompt or prevents the fire.

### Prompt-source coverage limitation

The Fountain generator has additional identity-related prompt paths:

- `NEX5_IDENTITY_BLOCK` is explicitly default OFF. When enabled, `identity_block.append()` adds a standing floor selected from identity/self-location sources plus optional affinity extras.
- Separately, the generator reads the latest `identity_log` statement and appends it to the prompt (subject to the identity-ablation arm). This is not a belief row and is not represented as a belief ID in `fountain_retrieval_log`.

Consequently, the identity-floor audit's recorded population is specifically **identity-claim beliefs among logged retrieved belief IDs**. It is not a complete inventory of every identity-bearing prompt component, nor an enforcement boundary over all prompt text. This is a scope limitation, not evidence that the separate identity-log statement is incorrectly sourced; the identity-loop producer and its actual statement provenance need their own source-to-prompt check if a broader claim is desired.

### Research conclusion and next step

NEX now has useful provenance metadata at the write boundary, an optional provenance-aware affinity consumer, and a daily output audit. These are complementary but non-equivalent:

- stamping answers “where did this row come from?”;
- affinity answers “how does this origin band affect affinity?”;
- the audit answers “did logged retrieved identity-claim beliefs supporting an identity-claim fire meet the authored/seeded floor?”;
- none of these, as inspected, establishes a universal provenance gate over every prompt source.

A future design review should first decide whether the identity floor is intended as an observational quality metric or a hard prompt-admission rule. If it is meant to be a hard rule, define its coverage over all relevant prompt sources and place the check before generation, with explicit treatment of identity-log and identity-block material. Do not convert the current nightly audit into an enforcement mechanism by assumption, and do not silently alter the ordinary retriever's ranking.

**Source anchors inspected:** `substrate/source_kind.py` blob `11b052d529defefecd16caafae5b95a3b251c0f0`; `theory_x/stage3_world_model/retrieval.py` blob `aa3eeb15c9a4a19a24a6d328bc370cd0a4438cf3`; `theory_x/stage_tom/source_kind_audit.py` blob `ac98a6562d9b8247d3ecbcd9610438463340f702`; `theory_x/life/affinity_loop.py` blob `f6567537658be1d7e56ac29c951285f6e70c6b11`; `theory_x/stage6_fountain/generator.py` blob `26061914b1dd80858c3568217cd1ef0c49ce2c51`; `theory_x/stage6_fountain/identity_block.py` blob `d1f710d26f8eeb451ba71ce3b0a5a2dc683697f5`; `theory_x/life/daily_life.py` blob `3325a62b76aeaa50148c92706a0548e8f67448bf`; `tests/test_source_kind.py` blob `d54ea4cb30b8d8315b1e3f34903f6088198c5374`.

**Host/runtime unknowns:** effective `NEX5_SOURCE_KIND` and `NEX5_IDENTITY_BLOCK`; whether daily_life's 03:00 audit runs on the deployed host; live audit results; current identity-log content and producer path; and whether the intended identity floor is observational or a hard prompt-admission requirement. No tests were run in this documentation pass.

No runtime code, tests, schema, indexes, feature flags, identity policy, mind-map authority, frozen S-01–S-25/M1.8, Master Roadmap, Phase 0/Gate 0 or action authority was changed.


## 96. Fountain own-thought feedback: retrieved candidate, activation touch and rendered prompt are not the same event (28 November 2026)

**Question studied:** when NEX has already crystallized its own thoughts, do those thoughts actually return as words to the next Fountain generation, or are they only selected and touched as activation metadata?

**Evidence snapshot:** current `main` at `18c8f06171e1de35c3210831a49b63d0e2487af0`. Static source and isolated fixture-test review. No live Fountain process, production database or environment flags were inspected.

### Observed source path

`FountainGenerator._retrieve_context_beliefs()` builds a context candidate set. Its own-content pool includes sources such as `fountain_insight` and `synergized`, selects recent non-retired rows (`tier < 8`), applies per-source/per-branch caps and can optionally use associative recall or edge-weighted re-ranking. Seed material is selected separately.

`_build_prompt()` then:

1. Splits candidates into own content, own sense and seed groups.
2. Calls `bump_activation()` for every selected context belief when a beliefs Writer is available.
3. Renders own-sense rows into the prompt as “Things you've been reading about lately”.
4. Renders seed rows into the prompt as “Things you've read that sometimes come to mind”.
5. Renders distilled own-content beliefs as words only when `NEX5_OWN_CONTENT_RENDER=1`.

The generator's own comment explicitly records the historical correction: since the removal of raw fountain-event exemplars (commit `ea6fe74`), distilled own thoughts can remain in the retrieved context and activation path without being rendered into prompt text. The opt-in own-content block excludes `hot_observer` and applies first-sentence deduplication before rendering.

### What the activation touch means

`theory_x/substrate/activation.py::bump_activation()` upserts `belief_activation`, adding 1.0 after lazy exponential decay with a 30-minute half-life (and a cap of 10). This is a record that a belief was retrieved into a Fountain context. It is not, by itself, proof that its words were presented to the language model, nor proof that it changed the resulting thought.

This distinction matters because the current path can select a distilled belief, touch its activation record, and still omit its text from the prompt when the render flag is unset. Conversely, own-sense and seed entries have explicit text-rendering paths. The retrieval manifest records prompt slots; do not treat every candidate or every activation touch as a rendered prompt item.

### Independent test evidence

`tests/test_retrieval.py` contains three relevant characterizations:

- `test_build_prompt_includes_own_content_section`: with `NEX5_OWN_CONTENT_RENDER=1`, the section and the inserted belief's text appear.
- `test_build_prompt_default_off_skips_own_content`: with the flag unset, an available `fountain_insight` belief does not produce the “Some of what you've been thinking recently” section.
- `test_own_content_dominates_retrieval`: own-content beliefs can dominate the selected candidate set over seed material.

This is not an accidental inference from an absent block: the default-off behaviour is explicitly pinned by a test. The feature remains opt-in. The prior Bonsai-to-Fountain/Global Workspace characterization demonstrates a separate attention-state route into branch choice and workspace framing; it does not establish that distilled own-thought words are rendered by default.

### Causal interpretation and bounded next experiment

The current source supports three different claims, which must not be collapsed:

- **Candidate continuity:** the generator can select its previously crystallized thoughts.
- **Activation continuity:** selected beliefs can receive a decaying activation touch.
- **Verbal continuity:** those thoughts become text in the next generation prompt only under the explicit render flag (or through some other separately evidenced prompt source).

Therefore, “the thought was retrieved” is not enough to claim “the thought was fed back into the next thought”. The default configuration preserves a gap between candidate/activation continuity and direct verbal self-feedback.

The next safe experiment is a controlled, isolated A/B replay, not a production flag change: hold candidate IDs, ordering, model request settings, branch/workspace state and all other prompt blocks constant; compare default-off against the own-content render path; record exact prompt inclusion, retrieval-manifest slots, output similarity/relevance, repeated-phrase rate, and whether the generated result later crystallizes and is retrieved again. Include a no-own-content negative control and a deliberately unrelated own-belief control. Use multiple paired seeds/fires, preregister outcome measures and stop criteria, and inspect for self-reinforcing repetition or groove amplification. The source's own deduplication is a guard, not evidence that the feedback is beneficial.

Do not enable `NEX5_OWN_CONTENT_RENDER` in production on the strength of this source review. First establish the paired effect and ensure the test isolates textual feedback from activation, candidate selection, Bonsai branch choice and Global Workspace arbitration.

**Source anchors inspected:** `theory_x/stage6_fountain/generator.py` blob `26061914b1dd80858c3568217cd1ef0c49ce2c51` (candidate retrieval, activation touch, own-sense/seed rendering and opt-in own-content rendering); `theory_x/substrate/activation.py` blob `16a8e4265b9280a04cbfe038b8e58d1c36698b25` (30-minute activation record); `tests/test_retrieval.py` blob `efd27b50c3cdc5ef64769fefcbb5529cc44ea90e` (default-off and opt-in fixture tests); `theory_x/stage3_world_model/retrieval.py` blob `aa3eeb15c9a4a19a24a6d328bc370cd0a4438cf3` (separate query retriever and spreading activation path); `research/NEX_BONSAI_FOUNTAIN_WORKSPACE_TRACE_2026-11-28.md` blob `2e0b856b3cadd1c2c3e2152a5be865492f9447cb` (Bonsai attention consumers and fixture limits).

**Host/runtime unknowns:** effective `NEX5_OWN_CONTENT_RENDER`, `NEX5_ASSOC_RECALL`, `NEX5_EDGE_WEIGHTED_FOUNTAIN`, `NEX5_GLOBAL_WORKSPACE` and other relevant prompt flags; which own-content sources are selected in actual fires; whether their text is rendered by any other independent prompt block; current activation distribution; and whether a paired replay has a positive, neutral or harmful behavioural effect. No tests were run in this documentation pass.

No runtime code, tests, schema, feature flags, prompt policy, cognitive authority, frozen S-01–S-25/M1.8, Master Roadmap, Phase 0/Gate 0 or execution authority was changed.



## 97. Substrate retrieval activation: attention record, sidecar rendering and opt-in emission are distinct (28 November 2026)

**Question studied:** does the activation touch written when Fountain retrieves its own thoughts feed back into ordinary retrieval or subsequent generation, or do they only create an auxiliary attention record?

**Evidence snapshot:** current `main` at `18c8f06171e1de35c3210831a49b63d0e2487af0`. Static source review and test-file inspection only. No live process, production database, host environment or feature flags were inspected.

### First distinction: two mechanisms both called activation

The ordinary world-model retriever uses `theory_x/stage3_world_model/activation.py::ActivationEngine`. It spreads scores from the current query's top keyword seeds through `belief_edges`, computes an epistemic-temperature summary and supplies normalized scores to `BeliefRetriever.retrieve()`. When scores exist, the retrieval blend is `keyword * 0.4 + spreading_activation * 0.6`; otherwise it falls back to keyword scoring. This is query-local graph spreading, not the persistent `belief_activation` table.

The Fountain context builder separately calls `theory_x/substrate/activation.py::bump_activation()` for each selected context belief. That function writes/upserts `belief_activation`, adding 1.0 after lazy exponential decay (30-minute half-life, cap 10). Its module docstring defines this as how recently/frequently a belief was retrieved into a Fountain prompt. This is a persistent retrieval-history/recency signal; it is not the same calculation as query-local spreading activation.

### Where the persistent activation is consumed

The inspected production call sites in `theory_x/stage6_fountain/generator.py` show two distinct downstream paths:

1. **Optional hot-belief emission:** when `NEX5_SUBSTRATE_EMIT=1`, the generator calls `get_top_activated(..., n=4)`, formats the four highest effective-activation belief contents into a `[substrate emit]` thought, marks the candidate as `fresh_model_generation: False`, and sets it as the thought output. This is a real output-selection route, but it is explicitly environment-gated and the source comment labels it default OFF. It is not evidence that the beliefs were inserted into a language-model prompt or that a new model-generated thought causally incorporated them.

2. **Periodic parallel substrate fire:** on the main path, every fifth-fire schedule condition (`_total_fires % 5 == 1`) runs when the beliefs Writer exists. It calls `render_substrate_fire()`, reads the top activated belief, and persists the rendered output plus the top belief ID/activation value to the dynamic database's `substrate_fires` table. This is a separate sidecar/parallel output path. It is not guarded by `NEX5_SUBSTRATE_EMIT`; it is also not shown by the inspected call site to be inserted into the next Fountain prompt.

`theory_x/substrate/renderer.py` confirms that the sidecar is template-rendered without an LLM: it reports the most activated belief, up to three connected beliefs, and the latest recent synergy result. The old open-arcs prompt block remains commented out with an explicit historical note about a repetition regression. Thus the renderer's output is a graph-native observation, not a fresh language-model synthesis.

### What this does—and does not—establish

The current source supports the following distinctions:

- **Persistent activation write:** records that a belief was selected into Fountain context.
- **Ordinary retrieval influence:** the separately named world-model spreading-activation engine contributes to query-local retrieval scoring; the inspected implementation does not read the persistent `belief_activation` table for that blend.
- **Substrate sidecar:** the periodic renderer reads persistent activation and stores a graph-native parallel-fire output.
- **Optional direct emission:** the explicit `NEX5_SUBSTRATE_EMIT=1` route can choose hot beliefs as Fountain output without a fresh model generation.
- **Verbal prompt feedback:** none of the inspected persistent-activation consumers proves that the sidecar output is fed into a later Fountain prompt. Nor does an activation touch alone prove that a belief's text was rendered to the model.

This sharpens §96: own-thought continuity has at least four separable channels—candidate selection, persistent activation history, optional substrate output, and direct prompt-text rendering. The system has real activation consumers; describing the table as a passive, write-only counter would be inaccurate. But describing it as ordinary retrieval control or default verbal self-feedback would also overstate the evidence.

### Evidence limits and next bounded trace

GitHub code search for the exact table and reader names returned no results and marked its API response incomplete; therefore this pass does **not** claim an exhaustive repository-wide consumer census. The source-verified call sites above are positive evidence, not proof that no additional readers exist. The downstream read path from `substrate_fires` into GUI/observability or any later prompt path remains to be checked against the complete consumer set.

The next safe step is a repository-wide static consumer census using the complete tree/blob set or a local checkout, then a caller-to-prompt trace for any `substrate_fires` reader. If the user later authorizes a behavioural experiment, isolate default periodic sidecar output from `NEX5_SUBSTRATE_EMIT` and `NEX5_OWN_CONTENT_RENDER`; record exact prompt slots, output provenance, repeated-phrase/groove measures and downstream crystallization. Do not enable either opt-in flag in production on this source review.

**Source anchors inspected:** `theory_x/substrate/activation.py` blob `16a8e4265b9280a04cbfe038b8e58d1c36698b25` (persistent activation write/read/ranking); `theory_x/stage3_world_model/activation.py` blob `509a021671c7f698fb740086dfffa170d2543b84` (query-local spreading activation); `theory_x/stage3_world_model/retrieval.py` blob `aa3eeb15c9a4a19a24a6d328bc370cd0a4438cf3` (0.4 keyword / 0.6 spreading-activation blend); `theory_x/stage6_fountain/generator.py` blob `26061914b1dd80858c3568217cd1ef0c49ce2c51` (activation touch, optional hot-belief emission and periodic parallel fire); `theory_x/substrate/renderer.py` blob `fce3bce13e48c4ac989b58db7b8241ca0f304fc1` (template sidecar); `tests/test_retrieval.py` blob `efd27b50c3cdc5ef64769fefcbb5529cc44ea90e` (no direct `belief_activation` or substrate-emission coverage found in this file).

**Host/runtime unknowns:** effective `NEX5_SUBSTRATE_EMIT`; whether the periodic parallel-fire path is active in the deployed process; actual activation distribution and decay; whether `substrate_fires` is consumed elsewhere; whether any consumer inserts sidecar output into a later prompt; and the behavioural effect of optional direct emission. No tests were run in this documentation pass.

No runtime code, tests, schema, indexes, feature flags, prompt policy, cognitive authority, frozen S-01–S-25/M1.8, Master Roadmap, Phase 0/Gate 0 or execution authority was changed.



## 98. World-model spreading activation: it reranks the candidate pool; it does not independently widen recall (28 November 2026)

**Question studied:** does the graph activation engine actually bring connected beliefs into retrieval, or does it only change the order of beliefs that already passed the retriever's candidate-building stage?

**Evidence snapshot:** current `main` at `18c8f06171e1de35c3210831a49b63d0e2487af0`. Static source and fixture-test review only. No runtime or production database was accessed.

### The candidate boundary comes before graph activation

`BeliefRetriever.retrieve()` first builds `row_map` and `keyword_scores` from eligible rows. A row enters this candidate map when it has literal token overlap with the query, or—when `NEX5_SEMANTIC_RETRIEVAL=1`—when the separate semantic fallback gives a zero-overlap candidate a qualifying score. Only after this candidate map exists does the retriever take the top five keyword-score IDs as graph activation seeds.

The graph engine can return connected belief IDs that were not in that candidate map. But when the retriever merges the activation scores, it looks each ID up in `row_map` and skips it if no candidate row exists. Therefore, **graph connectivity alone cannot introduce a previously ineligible or zero-overlap belief into the returned retrieval set**. It can affect the ranking of a connected belief only when that belief has independently entered the candidate map through keyword overlap or semantic fallback.

This is a meaningful constraint on the architecture: the graph is currently a relevance re-ranker over an independently constructed candidate pool, not a graph-based recall expansion mechanism.

### How graph influence is calculated

`ActivationEngine.activate()` starts each seed at 1.0 and traverses outgoing `belief_edges` for up to three hops by default, with hop decay 0.55. Edge multipliers are:

- `supports` and `refines`: 1.0;
- `cross_domain`: 0.8;
- `synthesises`: 1.2;
- `opposes`: a negative delta equal to half the source score × edge weight × hop decay.

Only positive next-frontier values continue to the following hop. A negative opposing target remains in the returned score map but is not propagated as a new frontier. When an edges Writer is supplied, actually traversed edges receive a best-effort `last_traversed_at` stamp; that stamp is observational metadata, not the score itself.

The retriever normalizes activation values by the maximum absolute activation and blends them with normalized keyword relevance at 60% activation / 40% keyword whenever graph activation is available. It attaches typed-role metadata and a shared epistemic-temperature value to returned candidate records. The final result is sorted and limited; the inspected code does not convert a `TENSION` role into a veto or action-control decision.

### What tests prove—and what remains unproved

`tests/test_edges.py` characterizes direct support propagation, hop decay, a negative score from an `opposes` edge, typed-role categorization (including `tension`), keyword-only fallback when no edges exist, and presence of activation metadata when edges do exist.

Those tests do not establish that a connected but zero-overlap belief can enter `BeliefRetriever.retrieve()` through graph activation. The retriever's `row_map` guard shows the opposite for the inspected implementation. The existing integration test verifies metadata presence, not graph-only recall expansion or ranking changes under a controlled competing-candidate fixture. The direct opposing-edge test is one hop; no inspected test characterizes whether an inhibitory target should or should not propagate onward (the source currently stops negative values at the next-frontier boundary).

### Architectural interpretation and bounded next step

The current mechanism is a bounded influence channel, not an unconstrained spreading network:

- graph edges influence scores only after the query has produced seeds;
- candidate admission remains controlled by the retriever's independent eligibility and keyword/semantic candidate construction;
- activation affects relative ranking, but does not itself authorize, veto or execute anything;
- negative/tension semantics are represented as scores and role metadata, not as a separate approval authority.

This is compatible with keeping cognitive interpretation distinct from typed operation representation, capability validation, approval, execution and verification. A Tibetan mind-map or Mind Aspect label must not be substituted for any of those authorities.

Before broadening graph recall, decide whether connected zero-overlap nodes are intended to become candidates at all. If yes, design a bounded expansion policy with explicit hop, candidate-count, confidence/paused/tier eligibility, deduplication and provenance rules, then test it against a no-graph control and query-relevant/irrelevant connected nodes. If not, document that the graph is intentionally a re-ranker. Do not silently widen recall or change edge semantics during Phase 0.

**Source anchors inspected:** `theory_x/stage3_world_model/activation.py` blob `509a021671c7f698fb740086dfffa170d2543b84` (edge propagation, inhibitory frontier and role classification); `theory_x/stage3_world_model/retrieval.py` blob `aa3eeb15c9a4a19a24a6d328bc370cd0a4438cf3` (candidate construction, row_map guard, 0.4/0.6 score blend and result limit); `tests/test_edges.py` blob `24dd0f065d649faf80ebbeb26626a64393892f53` (direct edge and retriever fixture tests); `tests/test_semantic_retrieval.py` blob `b746afa3a3cb7d16b4529175bd1db5eaa54d1eda` (separate opt-in semantic candidate path).

**Host/runtime unknowns:** effective `NEX5_SEMANTIC_RETRIEVAL`; actual edge-type distribution and weights; how often graph-activated IDs are absent from the lexical/semantic candidate map; live ranking changes; and whether graph-only recall expansion is a desired product behaviour. No tests were run in this documentation pass.

No runtime code, tests, schema, indexes, feature flags, retrieval policy, cognitive authority, frozen S-01–S-25/M1.8, Master Roadmap, Phase 0/Gate 0 or execution authority was changed.



## 99. Fountain stillness duplicate guard appears disconnected from the retrieval manifest (28 November 2026)

**Question studied:** does Fountain's low-readiness duplicate-retrieval stillness guard receive the own-belief IDs it expects, given the actual slot labels emitted by prompt construction?

**Evidence snapshot:** current `main` at `18c8f06171e1de35c3210831a49b63d0e2487af0`. Static source and related test-file inspection only. This is a candidate defect, not a runtime-observed failure.

### The consumer's expected slot

In `FountainGenerator.fire()`, after `_build_prompt()` returns the prompt and retrieval manifest, the stillness detector builds `_own_belief_ids` using:

```python
_own_belief_ids = frozenset(
    bel_id for bel_id, slot, *_ in retrieval_manifest
    if bel_id and slot == "own"
)
```

The Jaccard duplicate check and stillness counter are reached only when this set is non-empty (and readiness is below `_STILLNESS_READINESS_CAP`). If the set is empty, this entire own-retrieval duplicate guard is skipped.

### The producer's actual slot vocabulary

A full scan of every `retrieval_manifest.append(...)` occurrence in the inspected `generator.py` shows these emitted slot labels:

- `spectrum` for standing-point rows;
- `own_sense` for `precipitated_from_sense` beliefs, which are explicitly rendered into the prompt;
- `seed` for seed/reference rows;
- `disturbance_a` and `disturbance_b` for the two sides of an unresolved tension;
- `own_render` for distilled own-content rows when `NEX5_OWN_CONTENT_RENDER=1`.

There is no `retrieval_manifest.append(..., "own", ...)` in the inspected file. The stillness consumer expects `own`, while the producer labels the rendered own-sense and opt-in distilled own-content slots `own_sense` and `own_render`. Consequently, on the inspected implementation, `_own_belief_ids` is empty for manifests built by this function and the guard appears unreachable through this path.

This is a producer/consumer contract mismatch, not merely a question of whether own-content text is enabled. Even with `NEX5_OWN_CONTENT_RENDER=1`, the distilled rows use `own_render`, not `own`.

### Why it matters

The nearby comments describe the stillness check as a mechanism to suppress repeated own-slot retrieval when readiness is low. The current slot mismatch means the intended Jaccard comparison may never receive the relevant own-belief set. That could leave repeated retrieval patterns unfiltered by this particular guard. It does **not** prove that Fountain necessarily repeats, that the stillness counter never changes through another path, or that another independent suppression mechanism is absent.

Relatedly, the stillness detector's intended comparison population needs an explicit decision: should it include all retrieved own-content candidates, only items actually rendered as text, or both `own_sense` and optional `own_render` but not seed/spectrum/disturbance? Candidate selection, prompt inclusion and activation touch must not be treated as interchangeable evidence.

### Test coverage and confidence

The inspected `tests/test_fountain.py`, `tests/test_fountain_arc_awareness.py`, and `tests/test_fountain_shutdown.py` contain no references to the stillness guard, its Jaccard helper, or the `own` slot contract. `tests/test_retrieval.py` does test the default-off and opt-in rendering of distilled own content, but it does not exercise the stillness consumer against the returned manifest. `tests/test_fountain_crystallizer.py` tests crystallizer near-duplicate rejection, which is a different mechanism and does not cover retrieval-set stillness.

The source mismatch is high-confidence for the inspected producer and consumer, but the behavioural consequence is unverified because no test or live process was run.

### Safe next step

Before any fix, add a focused caller-contract test that builds representative manifests through `_build_prompt()` in both default-off and `NEX5_OWN_CONTENT_RENDER=1` modes, then verifies the intended own-slot IDs reach the stillness comparison. Decide and document the exact population semantics first. The test should also prove that seed, spectrum and disturbance entries do not accidentally count as own-content continuity. A separate regression should demonstrate the Jaccard guard's below-cap and at/above-threshold behaviour.

If confirmed, the smallest likely correction is to align the consumer with the producer's explicit slot vocabulary (or centralize slot classification in one helper); do not rename slots casually because they also feed retrieval provenance and write-back logic. Re-scan every slot reader and the prompt-block manifest before changing labels. This remains a Phase 0 defect candidate pending caller-contract verification; no production fix is made here.

**Source anchors inspected:** `theory_x/stage6_fountain/generator.py` blob `26061914b1dd80858c3568217cd1ef0c49ce2c51` (all manifest append sites, `_build_prompt`, and stillness consumer); `tests/test_fountain.py` blob `4ea682443e4997e7cbbf02f795df8d2c43605299`; `tests/test_fountain_arc_awareness.py` blob `fc52380998f707a5f8cf61a544c3cc100725ef78`; `tests/test_fountain_shutdown.py` blob `83b9323802678db3f2fc219366dca4fc1a57b48f`; `tests/test_retrieval.py` blob `efd27b50c3cdc5ef64769fefcbb5529cc44ea90e`; `tests/test_fountain_crystallizer.py` blob `aa8b666f4bfe1afa0338a6993b14cf8d2d4a4d50`.

**Host/runtime unknowns:** actual readiness distribution; whether the stillness branch is reached in deployment; actual repeated-retrieval Jaccard values; whether any external wrapper transforms manifest slots (none was found in the inspected call path); and behavioural impact of a corrected slot classifier. No tests were run in this documentation pass.

No runtime code, tests, schema, indexes, feature flags, prompt policy, cognitive authority, frozen S-01–S-25/M1.8, Master Roadmap, Phase 0/Gate 0 or execution authority was changed.


## 100. Fountain retrieval slot contract disables both stillness and historical duplicate comparison (28 November 2026)

**Question studied:** does the §99 producer/consumer mismatch stop at the in-memory stillness guard, or does the persisted retrieval-log comparison share the same incompatible slot assumption?

**Evidence snapshot:** current `main` at `18c8f06171e1de35c3210831a49b63d0e2487af0`. Static source and test-file inspection only. This strengthens §99 from a single-consumer mismatch to a shared slot-contract defect candidate; no runtime exercise or tests were run.

### Second consumer: persisted previous-fire comparison

`FountainGenerator._check_retrieval_duplicate(current_ids)` selects the last three real fires from `fountain_retrieval_log`, then reads each fire's belief IDs using the literal SQL predicate `slot = 'own'`. It calculates Jaccard against the current ID set only when a prior set is non-empty.

The caller in `FountainGenerator._generate()` constructs that current set from the returned `retrieval_manifest` using the same literal `slot == "own"` predicate. Therefore the current and historical sides share the same expected label. The manifest writer later persists each tuple's slot verbatim to `fountain_retrieval_log`; it does not normalize or translate slot names. A manifest containing only the inspected producer labels cannot populate either side of this comparison.

This is more consequential than a skipped in-memory guard alone: even if a caller supplied a non-empty current ID set by some other means, the persisted comparison would still find no prior IDs for fires whose logged slots are `own_sense`, `own_render`, or another label.

### Complete producer/reader vocabulary found in the inspected path

The scan includes the helper passed the manifest, not only direct `retrieval_manifest.append()` calls in `generator.py`:

- `own_sense`: prompt-rendered sense-derived beliefs.
- `own_render`: optional distilled own-content lines, emitted only when `NEX5_OWN_CONTENT_RENDER=1`.
- `identity_block`: authored/self-location identity rows appended by `theory_x/stage6_fountain/identity_block.py` when `NEX5_IDENTITY_BLOCK=1`.
- `seed`, `spectrum`, `disturbance_a`, `disturbance_b`: other explicit context classes.

No inspected producer emits the literal `own` label. The separate `identity_block.append()` helper confirms that the manifest has another own-related class which §99's direct-generator scan did not enumerate. That does not mean identity rows should automatically count as retrieval continuity: their semantics differ from retrieved own-content candidates and the intended comparison population must be decided explicitly.

The other inspected readers are deliberately more specific: crystallization retains the top-ranked `own_sense` entry; trace metadata records the slot vocabulary; the retrieval-log writer stores the raw slot; and the stillness/current-ID and historical-ID comparison both require `own`. These readers should not be collapsed into one vague “own” category without deciding what each mechanism is measuring.

### Tests and confidence

The inspected `tests/test_fountain.py`, `tests/test_fountain_arc_awareness.py`, `tests/test_fountain_shutdown.py`, and `tests/test_retrieval_teeth.py` contain no Fountain retrieval-stillness or retrieval-duplicate contract tests. `tests/test_retrieval.py` covers ordinary own-content retrieval and the default-off/opt-in distilled rendering path, but does not exercise the stillness caller, the persisted log slot query, or a manifest-to-log-to-next-fire comparison. `tests/test_identity_block.py` verifies the optional identity block's prompt presence and `identity_block` manifest slot, but does not test its interaction with either duplicate guard. `tests/test_stillness.py` does cover stillness by name, but it tests the separate Stage-9 Metacognition `stillness_log` and the crystallizer's active-stillness response; it does not cover Fountain's retrieval-manifest/Jaccard guard. The crystallizer's near-duplicate tests are likewise a separate output-content mechanism.

**Confidence:** high that the inspected current producer labels and both literal-`own` consumers are incompatible; high that the writer persists labels without normalization; behavioural impact remains source-inferred because no tests or live database were run. Existing persisted rows from older implementations, if any, do not establish current-path correctness. Runtime startup/migration behaviour and effective host flags were not inspected in this pass.

### Safe next step: specify the measurement population before repairing the contract

Add a focused integration test around the actual producer → manifest → persisted log → next-fire reader path. It should prove both current and previous ID sets are populated for the intended class, and prove seed/spectrum/disturbance are excluded. Exercise `own_sense`, optional `own_render`, and optional `identity_block` separately so the policy is explicit rather than accidentally inherited from a broad label.

Then centralize slot classification or give each consumer a purpose-specific set. A single shared helper is appropriate only if the stillness detector and historical comparison are meant to compare the same population. Keep the crystallizer's `own_sense` selection and trace/provenance slot labels stable unless their separate contracts are deliberately reviewed. Add boundary tests for below-cap readiness, high readiness, Jaccard below/at threshold, empty previous history, and the three-consecutive-stillness force-fire escape.

This remains a Phase 0 defect candidate. No production slot renaming, behavioural fix, schema change, flag change, or test change is made in this documentation study.

**Source anchors inspected:** `theory_x/stage6_fountain/generator.py` blob `26061914b1dd80858c3568217cd1ef0c49ce2c51` (stillness caller, literal-`own` historical reader, raw manifest persistence, crystallizer's separate `own_sense` reader, and all direct manifest producers); `theory_x/stage6_fountain/identity_block.py` blob `d1f710d26f8eeb451ba71ce3b0a5a2dc683697f5` (additional `identity_block` producer); `tests/test_fountain.py` blob `4ea682443e4997e7cbbf02f795df8d2c43605299`; `tests/test_fountain_arc_awareness.py` blob `fc52380998f707a5f8cf61a544c3cc100725ef78`; `tests/test_fountain_shutdown.py` blob `83b9323802678db3f2fc219366dca4fc1a57b48f`; `tests/test_retrieval.py` blob `efd27b50c3cdc5ef64769fefcbb5529cc44ea90e`; `tests/test_identity_block.py` blob `405ae22f8491b1952fd361ade14d16d05019248a`; `tests/test_stillness.py` blob `9a855ee570dcc2e1f0b7b1da6c61cfd072de8ea7` (separate Stage-9 stillness mechanism); `tests/test_retrieval_teeth.py` blob `b917244ef6f467ab2b4a7085977c1c2209b02cd0`; `tests/test_fountain_crystallizer.py` blob `aa8b666f4bfe1afa0338a6993b14cf8d2d4a4d50`.

**Host/runtime unknowns:** effective `NEX5_OWN_CONTENT_RENDER` and `NEX5_IDENTITY_BLOCK`; actual slot distribution in live manifests/log rows; whether old persisted rows contain legacy `own` labels; actual Jaccard distributions; readiness distribution; and whether the two guards would change firing behaviour if correctly wired. No tests were run in this documentation pass.

No runtime code, tests, schema, indexes, feature flags, prompt policy, cognitive authority, frozen S-01–S-25/M1.8, Master Roadmap, Phase 0/Gate 0 or execution authority was changed.


## 101. Fountain stillness slot mismatch — historical origin narrowed (28 November 2026)

**Question studied:** was the literal `own` expectation always wrong, or was it a valid contract that later drifted away from the manifest producer?

**Evidence snapshot:** current source `main` at `18c8f06171e1de35c3210831a49b63d0e2487af0`, plus Git commit history and patches for the original manifest and stillness work. Static archaeology only; no runtime or tests run.

### Historical sequence

1. **30 April 2026 — manifest and first stillness detector.** Commit `41b3516b8d2f2fe87a82a4444dcfcb6d5c25183b` introduced `fountain_retrieval_log` and the `retrieval_manifest`. Its documented slot vocabulary was `own/seed/spectrum/disturbance_a/disturbance_b`; the own-belief producer appended slot `own`. Commit `ac6e4032e2b115f34ca86fbff8778a5cc51d14ca` added the first stillness detector and compared all manifest IDs with the prior fire's log.
2. **1 May 2026 — own-only Jaccard became intentional.** Commit `251cd797579aa08b8b848a5e95cd58c4c3e22b72` explicitly narrowed both current and historical sets to slot `own`, because random seed/spectrum draws diluted the overlap signal. It set the threshold to 0.7 and made the reader return a Jaccard value. At this point, the producer and both readers agreed: this was not an accidental string in the first implementation.
3. **15–16 May 2026 — the old `own` producer was explicitly disabled.** Commit `60732402f92c10819591072cd7c13d1688a21351` changes the `own_thoughts` prompt block from `if own_thoughts:` to `if False and own_thoughts:` (the comment dates the disable to 15 May). At that exact commit snapshot, the only `retrieval_manifest.append(..., "own", ...)` producer is inside that disabled block. The separate active `own_sense` loop appends `"own_sense"`, but source inspection shows it represents `precipitated_from_sense` items — things NEX has been reading from the sense feed — not her distilled own thoughts. The stillness caller and historical SQL reader still require `own`. This locates the producer-side change: disabling the old own-thoughts prompt/manifest path left the readers without their intended class. It does **not** establish that `own_sense` should replace it.
4. **10 October 2026 — distilled own-content rendering was restored behind a default-OFF flag.** Commit `7c90e1a0bf6aaa5f030bef606e90a483ccd4f5b8` adds a bounded render of own distilled beliefs, excluding `precipitated_from_sense` and `hot_observer`, under `NEX5_OWN_CONTENT_RENDER=1`. Its manifest slot is `own_render`, not `own`. The current stillness caller does not count this slot either. The flag's default-off status means it does not establish an always-present own-content prompt population.
5. **26 October 2026 — a new own-related class was added separately.** Commit `a90a76cd1783a1f725dcb0c73cd8ffce1ba0a5eb` adds the optional guaranteed identity block with its explicit `identity_block` manifest slot and dedicated tests. This is a distinct semantic class, not evidence that it belongs in the retrieval-duplication set.
6. **15 November 2026 — smṛti uses `own_sense` for a different purpose.** Commit `231059a12439b0c10e0d92dcea79b6567c03d621` selects the top-ranked `own_sense` entry for observational retention-through-crystallization. That consumer's choice does not make sense-feed items equivalent to distilled own thoughts for stillness comparison.

### Revised diagnosis

This is best described as **a legacy stillness detector whose original input producer was disabled during an echo-loop intervention**. The original own-only comparison was deliberate; the May 15–16 change removed the prompt block that emitted that class because it was feeding contemplative beliefs back into the speaking layer. `own_sense` is not a safe alias: it represents sense-feed material. Later, `own_render` restored a separate, bounded own-distilled-content block behind a default-OFF flag, but the stillness detector does not consume that slot. The source mismatch is certain; whether this is a defect or an intentionally retired detector is unresolved. No behavioural fix should be selected until that design intent is recovered or explicitly decided.

This distinction matters: a repair should preserve the original intent (compare the intended own-content retrieval population, not random seeds/spectrum) while deciding whether `own_render`, `identity_block`, and any other future classes are in or out. It should not simply broaden to all manifest IDs, nor rename every producer slot to `own`.

### Next bounded archaeology/test task

Inspect the May 15–16 echo-loop decision and the October own-content-render restoration to determine whether the stillness detector was intentionally retired, or whether it should compare the optional `own_render` population when that flag is enabled. Do not substitute `own_sense` merely because it is currently active. Then write the integration-test contract before proposing a patch:

- the current-fire set and prior-fire set must use the same explicitly defined retrieval population;
- `own_sense` is sense-feed material (`precipitated_from_sense`), not automatically the own-thought population;
- `own_render` is the bounded distilled own-content block, emitted only when `NEX5_OWN_CONTENT_RENDER=1`; decide explicitly whether stillness should observe it when enabled;
- `identity_block` is an explicit identity injection, not automatically the same retrieval population;
- `seed`, `spectrum`, and disturbance classes remain excluded from the own-retrieval Jaccard;
- old persisted `own` rows need an explicit compatibility decision (read both labels, migration, or time-bounded handling), informed by actual database distribution rather than guesswork.

Only after that contract is evidenced should a minimal source fix be considered. No code/test/schema/flag change is authorised or made by this research note.

**Source anchors:** `41b3516b8d2f2fe87a82a4444dcfcb6d5c25183b` (original manifest producer and slot vocabulary); `ac6e4032e2b115f34ca86fbff8778a5cc51d14ca` (first stillness detector and all-ID comparison); `251cd797579aa08b8b848a5e95cd58c4c3e22b72` (own-only current/historical Jaccard); `60732402f92c10819591072cd7c13d1688a21351` (15–16 May: disables the sole `own` manifest producer while active sense-feed producer remains); `7c90e1a0bf6aaa5f030bef606e90a483ccd4f5b8` (10 Oct: restores bounded distilled own-content rendering under default-OFF `own_render`); `33476505eff8ec740d31ece7af78eeb95b7df865` (R37 documentation of `own_sense` vocabulary); `a90a76cd1783a1f725dcb0c73cd8ffce1ba0a5eb` (identity block slot); `231059a12439b0c10e0d92dcea79b6567c03d621` (smṛti consumes top-ranked `own_sense`).

**Evidence level:** source/history-observed for the original and current contracts; exact producer-rename commit UNKNOWN; live database slot distribution and behavioural impact UNKNOWN; no test verification or runtime observation.


## 102. Fountain echo-loop intervention — what was removed, and what later returned (28 November 2026)

**Question studied:** did the May echo-loop work establish a blanket rule against feeding NEX's own prior content into the speaking prompt, or did it distinguish dangerous raw exemplars from bounded distilled content?

**Evidence snapshot:** commit history and source diffs for ea6fe744fdd247f9d6ee3f183c2f6f2ee7f73008 (12 May, Mechanism A), 60732402f92c10819591072cd7c13d1688a21351 (15–16 May prompt cleanup), 7e71935c015d4e14005fb05589455e5da7141bc2 (26 July dead-block removal), and 7c90e1a0bf6aaa5f030bef606e90a483ccd4f5b8 (10 October bounded restoration). Static source/history study; no live runtime or tests run in this pass.

### What the intervention actually targeted

1. **12 May — raw recent-event exemplars were identified as a repetition amplifier.** Commit ea6fe744 describes the Fountain prompt injecting the last N fountain_events as “Your recent thoughts” exemplars before asking for another thought. The recorded diagnosis was that the model was being few-shot-prompted with five copies of an already-dominant cicada/hum motif. A separate sense-grounding intervention had not broken the pattern: the commit reports 3/3 post-restart fires still on the same surface pattern. Mechanism A removed that raw recent-thoughts block rather than reordering prompt calls. Its stated design principle was: substrate provides; speaking layer composes freely.
2. **15–16 May — the intervention widened to four inward-feedback blocks.** Commit 60732402 records disabling own_thoughts, ongoing_threads, recent-closed arc context, and the thread-extension prompt. Its commit message records a 15-fire repetition of “clock ticks, and my mind drifts to the hum of the servers nearby”. The own_thoughts block was changed to if False and own_thoughts; this was not a mere slot rename. The later 26 July cleanup commit 7e71935 confirms the block was dead since 15 May, removes its unreachable body and orphaned local computation, and preserves a recovery pointer. It also confirms the other dead prompt blocks were removed as dead code, not silently restored.
3. **The May decision was specifically anti-loop, not a general ban on every self-derived input.** The contemporaneous mechanism description distinguishes raw fountain_events exemplars from distilled belief sources. The later code history shows that distinction was revisited rather than treated as permanently closed.

### October restoration: a different input contract

Commit 7c90e1a0 explicitly corrects a stale comment: own distilled beliefs (synergized, fountain_insight, and related sources) continued to enter _retrieve_context_beliefs(), but after Mechanism A and the session-49 cleanup they were not rendered into prompt text by default. They could affect activation/residue without being spoken-layer words.

The October change restored a deliberately narrower path:

- controlled by NEX5_OWN_CONTENT_RENDER=1, default OFF;
- selects distilled own-content candidates while excluding precipitated_from_sense and hot_observer;
- caps rendered lines at three;
- deduplicates first-sentence 5-grams at Jaccard threshold 0.5;
- writes the explicit manifest slot own_render, not the legacy own;
- leaves the live prompt unchanged when the flag is unset;
- records a live-measurement requirement before making the flag default-ON: re-measure groove-token probability against the R76 hot-slot baseline (13.2%).

The same change keeps own_sense in its separate “Things you've been reading about lately” block. That population is sense-feed material, not the distilled own-content population. The commit also excludes hot_observer because earlier R75/R76 work had traced a live repetition groove to that source. The design is therefore selective: it rejects raw/repetitive feedback, but permits a bounded, deduplicated, distilled channel behind an explicit default-OFF flag.

### What this changes in the stillness diagnosis

This history strengthens the §101 interpretation but does not resolve the detector's intended future contract:

- The old stillness own population was disabled as part of an anti-echo intervention.
- The October restoration deliberately uses own_render; it does not revive the old own contract or automatically reconnect the detector.
- The detector should not be repaired by relabelling own_sense as own, nor by indiscriminately including all manifest slots.
- If stillness is intended to measure repetition in the actual distilled words reintroduced to the prompt, own_render is the only currently evidenced candidate population. That is a design hypothesis, not an approved change. If the detector was intentionally retired, the correct outcome may instead be to document it as dormant.
- Any experiment must preserve the October safeguards and separately measure whether the detector itself changes firing/selection behaviour. Prompt inclusion, retrieval activation, and duplicate detection are different effects.

### Research conclusion and next falsifier

**Conclusion:** the historical rule is not “never feed own content back”. It is closer to: do not replay raw event exemplars or unbounded self-referential context as few-shot material; if distilled own content is allowed into the speaking layer, bound it, deduplicate it, exclude known groove-amplifying sources, and keep it opt-in until measured. This is source/history-observed, not a claim that the October path is safe in live operation.

Next bounded work is to inspect the exact _build_prompt() producer and both stillness readers at one consistent source snapshot, then specify a paired-fire integration contract for own_render under flag OFF and ON. The contract must show that current-fire and prior-fire sets use the same population, preserve historical own rows deliberately, exclude own_sense/seed/spectrum/disturbance/identity classes unless explicitly justified, and demonstrate that the guard cannot count material that was not actually rendered. Live groove-token rates and historical slot distributions remain runtime unknowns.

**Source anchors:** ea6fe744fdd247f9d6ee3f183c2f6f2ee7f73008 (Mechanism A: raw recent-event exemplars removed after 3/3 repeated-pattern fires); 60732402f92c10819591072cd7c13d1688a21351 (four inward-feedback blocks disabled; 15-fire hum-lock recorded); 7e71935c015d4e14005fb05589455e5da7141bc2 (dead blocks removed, recovery pointer retained); 7c90e1a0bf6aaa5f030bef606e90a483ccd4f5b8 (bounded distilled own-content restoration, default OFF, slot own_render, live-check requirement).

**Evidence level:** source/history-observed for the intervention and restoration design; test-verified only for the October unit tests described in that commit (not rerun here); live behavioural safety and actual flag/slot distribution UNKNOWN. No runtime code, tests, schema, indexes, feature flags, prompt policy, or execution authority changed.

## 103. Fountain own-content restoration — producer-to-manifest test gap (28 November 2026)

**Question studied:** do the October tests prove the whole path from opt-in distilled-content selection through manifest recording, persistence, and the stillness reader, or only prove prompt text rendering?

**Source snapshot:** main at the §102 source snapshot. Static inspection of tests/test_retrieval.py and theory_x/stage6_fountain/generator.py; no tests executed.

### Verified coverage boundary

- tests/test_retrieval.py::test_build_prompt_includes_own_content_section sets NEX5_OWN_CONTENT_RENDER=1, calls _build_prompt(), and asserts that the own-content heading and a sample belief string appear in prompt text.
- test_build_prompt_no_own_content_skips_section verifies that enabling the flag with no eligible own-content belief does not add the section.
- test_build_prompt_default_off_skips_own_content inserts an eligible distilled belief with the flag unset and verifies that the section is absent.
- The inspected test file contains no assertion about retrieval_manifest contents, no assertion that the rendered belief is recorded under own_render, and no invocation of the stillness/Jaccard caller using that manifest.
- Current generator source confirms the renderer appends (belief_id, own_render, rank, None) only for retained rendered lines. The stillness caller separately filters its current manifest for slot == own; _check_retrieval_duplicate() separately queries prior rows with SQL slot = 'own'.
- The tests therefore verify prompt text inclusion/default-off behaviour, not the full producer → manifest → persistence → next-fire consumer contract. The gap is a test-coverage finding, not evidence that the code should be changed.

### Proposed contract tests (design only)

1. With NEX5_OWN_CONTENT_RENDER unset, an eligible distilled belief does not appear in the prompt and does not produce an own_render manifest entry.
2. With the flag set, a retained eligible belief appears in the prompt and exactly the same belief ID is represented in the manifest as own_render; excluded hot_observer and precipitated_from_sense rows do not enter that rendered population.
3. The renderer's cap and deduplication are reflected consistently in both prompt text and manifest; skipped candidates must not appear in the manifest.
4. The test must explicitly encode the stillness policy decision: either own_render is intentionally outside the stillness detector and that detector is documented dormant/legacy, or both current and historical stillness sets consume a clearly defined matching population. Do not make this choice implicitly through a string rename.
5. If own_render is included, exercise the persisted prior-fire reader with historical own rows present and verify the compatibility rule (dual-read, migration, or bounded legacy handling) rather than silently dropping historical comparisons.

**Disposition:** retain as a Phase 0 evidence/test-contract gap. No production code, tests, schema, slot labels, flags, or runtime behaviour changed. The October tests remain useful and intentional for their narrower text-rendering contract; they simply do not establish downstream manifest or stillness integration.

**Source anchors:** tests/test_retrieval.py blob efd27b50c3cdc5ef64769fefcbb5529cc44ea90e (three opt-in/default-off prompt-render tests); theory_x/stage6_fountain/generator.py blob 26061914b1dd80858c3568217cd1ef0c49ce2c51 (own_render manifest producer, own-only current-set filter, and own-only historical SQL reader).

**Evidence level:** source-observed test coverage and source-observed producer/consumer mismatch; test execution not performed in this pass; persisted live slot distribution and intended stillness policy UNKNOWN.

## 104. Stillness detector — historical operation versus current source reachability (28 November 2026)

**Question studied:** was the stillness/Jaccard mechanism merely abandoned code, or is there evidence that it operated before the own-slot producer was disabled?

**Evidence:** historical commit messages for ac6e4032e2b115f34ca86fbff8778a5cc51d14ca, 251cd797579aa08b8b848a5e95cd58c4c3e22b72, and f18e859f11820326cb7698fa30003410d728835f; current main source snapshot already documented in §§101–103. Historical measurements are reported by the repository's own commit records, not independently recomputed here.

### Evidence that the detector once operated

- The original stillness implementation (ac6e4032) created the duplicate-retrieval skip path, with a retrieval-manifest Jaccard comparison against the last three real fires, readiness below 0.85, and a force-fire escape after three consecutive stillness events.
- The first all-slot comparison did not trigger reliably: commit 251cd797 records observed Jaccard around 0.2 because random spectrum and seed draws diluted repeated own content. The implementation was then deliberately narrowed to the own slot on both current and historical sides, and thresholded at 0.7.
- A later self-prediction audit (f18e859) reports 4,965 duplicate_retrieval cycles in the persistent fountain event history. It explicitly distinguishes these empty-thought stillness cycles from real speech, and reports that all 1,526 force_fires were included in the readiness analysis. This is strong historical evidence that duplicate-retrieval stillness was not merely a never-used stub during that measured period.
- This does not establish the date on which the detector stopped operating, nor the exact live distribution of manifest slots today. It does establish that the mechanism had meaningful historical operational use before the later source state now inspected.

### Current source reachability

At the inspected current source snapshot, the stillness caller's current set includes only manifest entries whose slot equals own. The historical reader likewise selects only rows with slot = 'own'. The complete manifest-producer census recorded in §§99–103 found no active producer emitting own: own_sense is sense-feed material; own_render is the optional bounded distilled-content render; identity_block, seed, spectrum and disturbance slots are separate classes.

Therefore, on the inspected source:
- with NEX5_OWN_CONTENT_RENDER unset (the default), the bounded own-content render is absent and no active producer supplies own; the stillness current set is empty and its Jaccard check is skipped;
- with NEX5_OWN_CONTENT_RENDER=1, the producer emits own_render, but the stillness caller still filters for own; the current set remains empty;
- even if historical rows contain own, the guard is not reached unless the current set is non-empty.

This is a source-level reachability conclusion, not a live runtime observation. It is stronger than saying the two readers are mismatched: the current producer inventory plus exact filters imply the detector's duplicate-retrieval branch cannot be entered through the inspected manifest path. The original force-fire escape does not change that because it is nested inside the duplicate-detection branch.

### Revised classification

Record this as a **high-confidence source-level dormant path / historical operational regression candidate**, not yet a confirmed behavioural defect. The historical evidence argues against assuming the detector was always intentionally retired. The May echo-loop intervention disabled the original own-content producer for a clear safety reason; October restored a different, bounded own-content population behind a default-OFF flag. No evidence located so far states that the stillness detector itself was deliberately retired, or authorises reconnecting it to own_render.

### Next evidence needed before any repair

1. Establish the chronology between the last measured duplicate_retrieval activity and the May producer disable; identify whether the historical 4,965 count predates or postdates that change using source/commit chronology and retained logs if available.
2. Inspect any explicit decision record for retiring or retaining the stillness mechanism. Absence of a note is not proof of intent.
3. If a controlled runtime dataset is available, count retrieval_manifest slot values and stillness_reason values over the same bounded period; distinguish no producer, no duplicate candidates, and guard-not-reached.
4. Only then decide whether stillness remains retired, is reactivated against own_render when that flag is on, or receives a separate opt-in measurement-only path. Preserve the historical own rows and compare current/prior populations symmetrically.
5. If a future contract includes own_render, test the full paired-fire lifecycle, including rendered-only membership, historical compatibility, threshold boundaries, readiness cap, empty history, and force-fire escape. A detector measurement must not be conflated with prompt selection or a new cognitive authority.

**Disposition:** no code/test/schema/flag changes. Phase 0 evidence work only. No Gate 0 claim.

**Source anchors:** ac6e4032e2b115f34ca86fbff8778a5cc51d14ca (initial stillness path); 251cd797579aa08b8b848a5e95cd58c4c3e22b72 (own-only Jaccard narrowing because all-slot overlap was too low); f18e859f11820326cb7698fa30003410d728835f (historical 4,965 duplicate_retrieval cycles and 1,526 force_fires); theory_x/stage6_fountain/generator.py blob 26061914b1dd80858c3568217cd1ef0c49ce2c51 (current source filters); tests/test_retrieval.py blob efd27b50c3cdc5ef64769fefcbb5529cc44ea90e (prompt-render-only coverage).

**Evidence level:** historical operational counts as reported in repository commit evidence; current source-level reachability; no current live database/runtime verification and no tests run in this pass. Intended retirement policy UNKNOWN.

## 105. Stillness records — two distinct mechanisms and the missing chronology (28 November 2026)

**Question studied:** do the historical duplicate-retrieval counts date the stillness detector's operation after the May anti-echo change, and are all repository records named `stillness_log` describing the same mechanism?

### Chronology now established

- **30 April 2026 22:22 UTC —** commit `ac6e4032e2b115f34ca86fbff8778a5cc51d14ca` introduced the Fountain duplicate-retrieval stillness path. It compared retrieval-manifest belief IDs against the last three real fires, required readiness below 0.85, and included a force-fire escape after three consecutive stillness skips.
- **1 May 2026 05:11 UTC —** commit `251cd797579aa08b8b848a5e95cd58c4c3e22b72` changed the detector to compare only slot `own`, because random spectrum/seed draws diluted all-slot Jaccard to roughly 0.2. Both the current set and prior-fire SQL reader were narrowed to the same slot.
- **16 May 2026 15:21 UTC —** commit `60732402f92c10819591072cd7c13d1688a21351` disabled the `own_thoughts` prompt/manifest producer as part of the anti-echo intervention. This is the producer-side break described in §§101–104.
- **9 July 2026 13:58 UTC —** commit `f18e859f11820326cb7698fa30003410d728835f` reported 4,965 `duplicate_retrieval` rows among 26,299 fountain cycles, and 1,526 `force_fires`. The same commit distinguishes empty-thought stillness cycles from actual speech and uses the historical counts in its self-prediction audit.

The July commit date is the date the aggregate was reported, **not the event-window boundary**. The commit does not supply timestamps or an ID/time range for those 4,965 rows. Therefore it cannot establish whether the counted duplicate-retrieval events occurred before or after the 16 May producer disable. The apparent chronology gap remains unresolved; do not infer post-May operation from the July report date.

### A second, separate stillness mechanism

The repository also has a different stillness mechanism with a table of the same name in a different database:

- Commit `c4b005f32e931047711ef6cdbe03e84a00183885` (11 May 2026) introduced **Row 9 Stillness**. Metacognition writes a time-bounded stillness row to **`conversations.db`** after at least three groove events in a 1,800-second window; the FountainCrystallizer reads the active row and suppresses crystallization for 60 seconds. Its tests are `tests/test_stillness.py` and concern Metacognition/Crystallizer behaviour.
- The duplicate-retrieval detector's `stillness_log` and `fountain_events.stillness_reason` belong to the **dynamic fountain retrieval/stillness path**, not the conversations.db Row 9 path.
- A 23 May journal commit (`a20968e6c7517b0fd491e8676ed9d2aa549a7761`) records a 90-minute fountain pause and says the relevant stillness log was empty in that window. Its narrative concerns the substrate/Row 9 mechanism and does not date the duplicate-retrieval event population.

This name collision matters: a search for `stillness_log`, or a statement that “stillness was active”, is not enough to identify which database, producer, consumer, or suppression effect was involved. Treat these as separate mechanisms unless a concrete cross-database caller proves otherwise.

### Revised conclusion

1. The duplicate-retrieval detector was introduced and deliberately refined to own-only comparison in late April/early May.
2. Its original `own` producer was disabled on 16 May as part of a documented anti-echo intervention.
3. A July audit reports substantial historical duplicate-retrieval/force-fire counts, but does not date those events. The source-level dormant-path finding in §104 remains valid for the inspected current source; whether the detector became dormant immediately on 16 May, later, or after a runtime-only transition remains UNKNOWN.
4. Row 9 Stillness is a distinct conversations.db mechanism. Its existence or tests do not validate the Fountain duplicate-retrieval detector, and vice versa.

### Next evidence step

The decisive artifact would be a retained, time-indexed `dynamic.db` snapshot or exported rows for `fountain_events`, `fountain_retrieval_log`, and the dynamic `stillness_log`, sufficient to align event timestamps/IDs with the May 16 change and identify the last `duplicate_retrieval` and `force_fire` events. If unavailable, retain the chronology as UNKNOWN; do not fabricate a date range from aggregate totals. Continue the repository-wide caller census separately for both stillness mechanisms.

**Disposition:** documentation/evidence refinement only. No runtime code, tests, schema, flags, or cognitive authority changed. No tests run. No Gate 0 claim.

**Source anchors:** `ac6e4032e2b115f34ca86fbff8778a5cc51d14ca` (initial duplicate-retrieval detector); `251cd797579aa08b8b848a5e95cd58c4c3e22b72` (own-only Jaccard); `60732402f92c10819591072cd7c13d1688a21351` (May anti-echo producer disable); `f18e859f11820326cb7698fa30003410d728835f` (July aggregate counts); `c4b005f32e931047711ef6cdbe03e84a00183885` (separate conversations.db Row 9 stillness); `a20968e6c7517b0fd491e8676ed9d2aa549a7761` (23 May journal observation).

**Evidence level:** commit-dated source/history evidence for code changes; July aggregate operational counts as reported by commit message; event-level chronology and current runtime state UNKNOWN.


## 106. Metacognition groove alerts — repeat-on-turn and false sustained-groove candidate (28 November 2026)

**Question studied:** does Stage 9 convert one persistent unacknowledged GrooveSpotter alert into multiple metacognition events across chat turns, and can those repeated rows satisfy Row 9's “sustained groove” threshold without three distinct groove episodes?

### Source path and cadence

- `theory_x/__init__.py` defines the SentienceNode contract as `tick()` called once per chat turn.
- `gui/server.py` calls `state.metacognition.tick()` inside the INSIDE chat request path, before calling `format_for_prompt()`. This is a per-chat-turn call, not a dedicated periodic daemon.
- `Metacognition._detect_groove(now)` reads up to three rows from `beliefs.db.groove_alerts` where `detected_at > now - 600s` and `acknowledged_at IS NULL`. It does not record a last-seen alert ID or update `acknowledged_at` in the inspected method.
- `tick()` writes every returned alert through `_write_event()`. The inspected `_write_event()` inserts a new `meta_cognition_events` row each time; it does not persist the source `groove_id` or acknowledge the source alert. The instance field `_last_groove_at` is initialized but has no read/write use in the inspected module snapshot.
- When any groove rows are returned, `tick()` calls `_maybe_engage_stillness(now)`. That method counts `event_type='groove'` rows in the preceding 1,800 seconds and writes a 60-second Row 9 stillness window when the count reaches three.

### Why this may matter

If the same source alert remains unacknowledged and within the 600-second lookback across multiple INSIDE chat turns, the same alert can be converted repeatedly into separate `meta_cognition_events` rows. Three chat turns could therefore create three “groove” rows from one source alert and satisfy the Row 9 threshold, even though the intended phrase is “three groove events in a 30-minute window”. The code currently does not prove those are three distinct episodes.

This is a **source-level repeat-on-turn candidate**, not yet a confirmed runtime defect. A separate actor may acknowledge alerts outside the inspected producer/consumer files; a complete repository-wide writer census for `groove_alerts.acknowledged_at` is still required. The July 22 GrooveSpotter fingerprint fix (commit `543e4ce957f2e3ad8e3ebf9fb25cd1bf977fed1a`) prevents the same detector fingerprint from being re-inserted every 60-second GrooveSpotter tick, but it does not, by itself, show that an already persisted alert is consumed only once by Metacognition on successive chat turns.

### Existing tests and gap

- `tests/test_metacognition.py` covers one unacknowledged alert becoming an event, prompt formatting, acknowledged alerts being ignored, and alerts outside the 600-second lookback being ignored.
- `tests/test_stillness.py` tests Row 9 threshold/window behaviour using a mocked groove-event count, and tests the crystallizer's read of the conversations.db stillness window.
- The inspected tests do not call `Metacognition.tick()` repeatedly against the same still-unacknowledged source alert and assert that only one durable event is created. They also do not prove that three distinct source episodes, rather than repeated reads of one alert, are required to engage Row 9 stillness.
- The July 22 GrooveSpotter fix was verified in an isolated controlled test for repeated detector ticks, but that is a different boundary: GrooveSpotter insertion deduplication does not test Metacognition's source-alert consumption semantics.

### Bounded next evidence

1. Complete the repository-wide census for writers/updates to `groove_alerts.acknowledged_at`, and determine whether any separate acknowledgement path exists.
2. Inspect `DiversityLoop` construction/lifetime and GrooveSpotter scheduling to confirm the fingerprint state lifetime relative to the per-chat Metacognition instance lifetime.
3. Add a test proposal only: seed one unacknowledged alert, call `tick()` repeatedly at distinct times within the lookback, and assert the chosen once-only or repeat semantics explicitly. Add a separate test with three genuinely distinct alert IDs/episodes to establish the Row 9 threshold contract.
4. Before any fix, decide whether the event should be once per source alert, once per distinct fingerprint/episode, or intentionally repeated per chat turn. Do not silently redefine Row 9's meaning or mutate source acknowledgement state without an authority review.

**Disposition:** Phase 0 source/test-contract finding only. No code, tests, schema, flags, or runtime behaviour changed. No tests run. No Gate 0 claim. Confidence: plausible source-level repeat path; live frequency and any external acknowledgement path UNKNOWN.

**Source anchors:** `theory_x/stage9_metacognition/metacognition.py` (current main blob `de853bd93a11dcfe39ee8afa30a84e5c7b1f8b08`); `theory_x/diversity/groove.py` (current main blob from this pass); `gui/server.py` and `theory_x/__init__.py` (per-chat tick contract); `tests/test_metacognition.py` blob `e2604f7baf113999b89e8c66c8bdf4fae22f5a8d`; `tests/test_stillness.py` blob `9a855ee570dcc2e1f0b7b1da6c61cfd072de8ea7`; `543e4ce957f2e3ad8e3ebf9fb25cd1bf977fed1a` (GrooveSpotter fingerprint dedup).

**Evidence level:** source-observed caller cadence and read/write path; test-coverage inspection; no runtime measurement and no test execution in this pass. Repository-wide acknowledgement writer census incomplete.


## 107. Groove alert re-consumption can manufacture the sustained-groove count (28 November 2026)

**Question studied:** does the current Metacognition path consume a GrooveSpotter alert once, or can repeated chat turns convert the same still-unacknowledged source row into multiple durable events and thereby satisfy Row 9's threshold?

### Source trace

- DiversityLoop._run() calls GrooveSpotter.detect_all() on its background loop, then waits 60 seconds. GrooveSpotter inserts a groove_alerts row when a new detector fingerprint appears. Its in-memory fingerprints suppress unchanged detector output within that process; they are not an acknowledgement or consumption record for Metacognition.
- Metacognition.tick() is called on the INSIDE chat path once per chat turn. Each tick calls _detect_groove(now).
- _detect_groove() selects up to three rows newer than 600 seconds with acknowledged_at IS NULL. It returns their IDs but does not update acknowledged_at, persist a last-consumed ID, or deduplicate against prior meta_cognition_events.
- For every returned row, tick() calls _write_event(). _write_event() inserts a new meta_cognition_events row and does not persist the source groove_id; the source ID is used only in the optional narrative call.
- If any groove rows are returned, tick() calls _maybe_engage_stillness(). That method counts all event_type='groove' rows in the preceding 1,800 seconds. It counts derived event rows, not distinct source alert IDs or detector episodes.

### Consequence and confidence

The same source alert can therefore be re-read and re-written on successive chat turns while it remains within the 600-second lookback and unacknowledged. Three such turns can create three groove event rows from one source alert; the Row 9 threshold can then be reached without three distinct alerts. This is a deterministic source-level pathway under those conditions, not merely a hypothetical race.

This does not establish that the pathway has occurred in the live runtime, how often it occurs, or whether another uninspected component acknowledges alerts. The 14 November investigation reported 0 acknowledged rows among 1,198 sampled groove_alerts and said the column appeared unwritten, but its repository-wide writer census was not demonstrated. The current source inspection confirms the known producer and consumer paths; the complete tracked-repository acknowledgement writer census remains open.

### Existing coverage and bounded next evidence

- Existing tests prove one unacknowledged alert creates a groove event and an acknowledged alert is ignored. They do not call tick() repeatedly against the same alert ID.
- Existing Row 9 tests exercise the count threshold with mocked groove-event counts; they do not establish that three distinct source alert IDs are required.
- Add test proposals only at this stage: (1) repeated ticks against one unchanged alert ID; (2) three distinct alert IDs; (3) a source alert becoming acknowledged between ticks; and (4) multiple alert rows returned in one tick. Assert source IDs and derived event counts separately.
- Before a fix, resolve the intended semantic unit: one event per source alert, per distinct detector episode/fingerprint, or per chat-turn observation. If once-only consumption is intended, choose an explicit durable/idempotent mechanism and review its cross-database implications; do not casually add a beliefs/conversations cross-database transaction or mutate source acknowledgement state without authority review.
- Complete the tracked-source writer census for groove_alerts.acknowledged_at, then inspect historical database evidence if an appropriately retained snapshot is available. Do not access or alter the live database as part of this source study.

**Disposition:** Phase 0 source/test-contract finding. Documentation only; no runtime code, tests, schema, flags, or behaviour changed. No tests run. No Gate 0 claim. No live host, database, process, or service accessed.

**Source anchors:** theory_x/diversity/loop.py (60-second detector cadence); theory_x/diversity/groove.py (in-memory detector fingerprints and alert inserts); theory_x/stage9_metacognition/metacognition.py (tick(), _detect_groove(), _write_event(), _maybe_engage_stillness()); gui/server.py (INSIDE chat call site); tests/test_metacognition.py; tests/test_stillness.py; journal/INVESTIGATION_2026-11-14_groove_facts.txt (historical 0/1,198 acknowledgement observation).

**Evidence level:** source-observed caller cadence and write/read/count path; test-coverage inspection; historical database aggregate reported in a journal; live event chronology and complete acknowledgement writer census UNKNOWN.


## §108 — Groove alert identity, producer semantics, and idempotency boundary (2026-11-28)

### Additional source inspection

This follow-on inspection uses the current `main` snapshot `18c8f06171e1de35c3210831a49b63d0e2487af0`. It narrows the producer/consumer contract but does not close the repository-wide acknowledgement-writer census.

- `DiversityLoop._run()` invokes `GrooveSpotter.detect_all()`, then the other diversity stages, then waits 60 seconds. This is a detector cadence, not proof that each alert is consumed once by Metacognition.
- The inspected GrooveSpotter detectors insert rows into `groove_alerts` for n-gram repetition, exact repetition, template repetition, and centroid tightening. Their duplicate suppression is held in per-instance fields such as `_last_ngram_pattern`, `_last_exact_content`, `_last_template_ids`, and `_last_centroid_ids`. These are process-memory comparisons, not durable acknowledgement of a database row. A process restart therefore resets those in-memory comparisons; whether this produces a repeated alert depends on the next detector window and remains a separate runtime question.
- `Metacognition._detect_groove()` selects the three newest unacknowledged source rows within its 600-second lookback. It returns the source row ID as transient `groove_id`, but the inspected `_write_event()` persists only event type, description, severity, source, and timestamp into `meta_cognition_events`; the source row ID is not stored in that derived event.
- `_maybe_engage_stillness()` counts derived `event_type='groove'` rows, not distinct source alert IDs. The threshold is three derived events in 1,800 seconds. Consequently, the same eligible source row being returned on multiple Metacognition ticks can increment this count repeatedly. This is a source-level causal pathway; no live occurrence is asserted.
- `substrate.Writer` documents and implements one writer worker per SQLite database. The observed source alert producer writes through the beliefs writer, while Metacognition writes derived events through the conversations writer. A future once-only design must therefore make its cross-database failure semantics explicit rather than assume an atomic transaction spans both stores.

### What the evidence does and does not establish

**Established from inspected source:** detector inserts; in-memory fingerprint suppression; 60-second detector loop; unacknowledged-row selection; transient source ID; derived-event insertion without persisted source ID; stillness count over derived rows; separate per-database Writer instances.

**Not established:** every tracked or dynamically loaded writer of `groove_alerts.acknowledged_at`; whether another maintenance path acknowledges rows; the exact production cadence of chat-triggered `tick()`; whether a live database has repeated derived rows from one source alert; whether restart has caused duplicate alert production; and the intended semantic unit of a groove event.

The GitHub code-search endpoint returned no matches for the acknowledgement field in this pass, so that result is not treated as a negative writer census. Targeted inspection of the core substrate, detector, metacognition, GUI, and tests also did not prove the absence of writers elsewhere. Census remains OPEN.

### Research refinement — identity must survive the boundary

The central design question is not simply “where should we set acknowledged_at?” It is “what identity is the system promising to preserve as a signal crosses components?” Keep these identities separate:

1. **Detector observation** — one detector evaluated one evidence window.
2. **Alert row** — one persisted GrooveSpotter output with a stable database ID.
3. **Episode/fingerprint** — a semantic pattern that may span multiple observations or rows.
4. **Metacognitive observation** — one act of Metacognition noticing an alert.
5. **Stillness evidence** — the distinct observations that satisfy the Row 9 threshold.

A future implementation must explicitly choose which of these is counted, deduplicated, acknowledged, and retained. Do not collapse them into a single “event” label. A stable provenance key on the derived event (or a separately justified consumption ledger) may be necessary if the intended unit is once per alert, but this remains a design candidate, not an approved change. The correct solution must define crash windows, retries, replay, retention, and cross-database partial failure before code is touched.

### Bounded next actions

1. Continue a tracked-source census for all SQL and wrapper-based writes that could target `groove_alerts` or `acknowledged_at`; record exact files and line ranges, including indirect SQL builders.
2. Inspect the table's authoritative creation/migration path and all consumers of `groove_id` before proposing a schema or transaction change.
3. Extend the proposed regression matrix to distinguish repeated observation of one alert from three distinct alert IDs and from repeated detector episodes with different row IDs.
4. Only after the census and semantic contract are complete, decide whether a bounded test-only probe is authorised. No production fix is justified yet.

**Disposition:** Phase 0 source-level refinement; documentation only. No runtime code, tests, schema, flags, or behaviour changed. No tests run. No live host, database, process, or service accessed. Gate 0 remains unestablished.

**Source anchors:** `theory_x/diversity/loop.py`; `theory_x/diversity/groove.py`; `theory_x/stage9_metacognition/metacognition.py`; `substrate/writer.py`; `gui/server.py`; `tests/test_metacognition.py`; `tests/test_stillness.py`. Snapshot: `18c8f06171e1de35c3210831a49b63d0e2487af0`.

**Evidence level:** source-observed producer and consumer path; source-observed database boundary; test-coverage inspection. Complete writer census, runtime chronology, and semantic event identity remain UNKNOWN.


## §109 — Groove source identity survives through the narrative side-path (2026-11-28)

### Correction and qualification to §§107–108

The earlier statement that the groove source ID was not persisted applies specifically to the `meta_cognition_events` row written by `Metacognition._write_event()`. It must not be read as saying that no downstream record retains the source identity. A second, separately persisted path exists and is wired at runtime:

- `run.py` constructs `SelfNarrative(writers["conversations"], readers["conversations"])` and passes it as `narrative=self_narrative` to `Metacognition`.
- `Metacognition.tick()` passes `ev.get("groove_id")` to `write_narrative()` for each groove event returned by `_detect_groove()`.
- `SelfNarrative.write_narrative()` inserts `content, trigger, source_id, created_at` into `narrative_log`; the source ID is the originating `groove_alerts.id`.
- The canonical `narrative_log` DDL is in `substrate/init_db.py`'s conversations migrations. It contains a nullable integer `source_id` and an index on `created_at`; no uniqueness constraint on `(trigger, source_id)` or `source_id` is present in the inspected schema.
- `theory_x/SELF_NARRATIVE_SPEC.md` explicitly defines a groove narrative's `source_id` as the source `groove_alerts.id`, and describes a write for each row returned by `_detect_groove()`.

Therefore, when the optional narrative writer is constructed and its write succeeds, the same source alert can be correlated across repeated observations by querying `narrative_log`. This is useful forensic provenance. It is not idempotency: the write is a plain `INSERT`, and neither the table schema nor the inspected writer enforces one narrative row per source alert. A repeated Metacognition tick can add another narrative row with the same `source_id`.

### The two derived streams must remain distinct

| Stream | Destination | Source ID retained? | Duplicate prevention shown? |
|---|---|---|---|
| Metacognitive event | `meta_cognition_events` in conversations.db | No; `_write_event()` persists no `groove_id` column | No source-ID idempotency shown |
| Self-narrative record | `narrative_log` in conversations.db | Yes, via `source_id` when narrative is wired and write succeeds | No; plain insert, no source-ID uniqueness |

Both streams are downstream of the same `groove_events` list in `tick()`. Stillness counts only the first stream's `event_type='groove'` rows. The narrative stream can aid source-level auditing, but it does not currently constrain or correct the count used by Row 9.

### Schema and migration finding

The source table's canonical DDL is `substrate/schema/beliefs.sql`:

```sql
CREATE TABLE IF NOT EXISTS groove_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    detected_at REAL NOT NULL,
    alert_type TEXT NOT NULL,
    severity REAL NOT NULL,
    pattern TEXT,
    sample_belief_ids TEXT,
    window_size INTEGER NOT NULL,
    acknowledged_at REAL
);
```

`substrate/init_db.py` maps the beliefs database to `beliefs.sql`; `init_all()` applies that schema before additive migrations. Thus a fresh database receives the current table definition. The current `_MIGRATIONS["beliefs"]` inspection did not locate an `ALTER TABLE groove_alerts ADD COLUMN acknowledged_at` migration. Since `CREATE TABLE IF NOT EXISTS` does not add a column to an already-existing older table, an installation whose pre-existing `groove_alerts` table predates this column would need separate migration evidence. The 2026-11-14 live-database journal records the column present in its sampled database (0/1,198 rows acknowledged); that historical observation does not prove every extant copy has the same schema.

### Test coverage and limits

- `tests/test_self_narrative.py` verifies that `source_id` is written and that independent calls produce independent rows. It does not test repeated ticks against one unchanged groove alert ID.
- `tests/test_metacognition.py` builds Metacognition without a narrative dependency in its shared helper; its one-alert test verifies a derived event but not the live paired narrative write.
- The static schema guards in `tests/test_schema_indexes.py` scan static SQL references/compilability against a fresh initialized store. They establish useful table/column coverage, not once-only consumption semantics or distinct-source counting.
- No tests were run in this source-only pass. No live database was queried.

### Revised next evidence

1. Add a read-only forensic query to a retained snapshot (not the live DB) that groups `narrative_log` by `trigger, source_id` and compares distinct source IDs with repeated row counts; separately group `meta_cognition_events` by time/source description where attribution is possible. Preserve limitations: event rows lack source IDs, so descriptions are not a robust join key.
2. Characterize repeated `tick()` calls with one alert and a wired `SelfNarrative`: assert counts and IDs in both destination tables. Then compare with three distinct source alert IDs.
3. Complete the full tracked-code census for writes to `groove_alerts.acknowledged_at`; this targeted pass still does not establish that no indirect or dynamically assembled writer exists.
4. Decide the semantic unit before any code change: detector observation, alert row, detector episode/fingerprint, metacognitive observation, or distinct evidence for stillness. Then specify retry/crash/retention behaviour separately for event and narrative streams.

**Disposition:** Phase 0 source-level correction and provenance refinement; documentation only. No runtime code, tests, schema, flags, or behaviour changed. No tests run. No live host, database, process, or service accessed. Gate 0 remains unestablished.

**Source anchors and main snapshot:** `run.py` (SelfNarrative construction/injection); `theory_x/stage9_metacognition/metacognition.py` (tick and source ID pass-through); `theory_x/stage_self_narrative/self_narrative.py` (narrative insert); `theory_x/SELF_NARRATIVE_SPEC.md`; `substrate/schema/beliefs.sql`; `substrate/init_db.py` (schema map, apply path, conversations migration); `substrate/schema/conversations.sql`; `tests/test_self_narrative.py`; `tests/test_metacognition.py`; `tests/test_schema_indexes.py`; `journal/INVESTIGATION_2026-11-14_groove_facts.txt`; snapshot `18c8f06171e1de35c3210831a49b63d0e2487af0`.

**Evidence level:** source-observed initialization, runtime dependency injection, source ID pass-through, and narrative persistence; test-coverage inspection; historical DB observation from journal. Full acknowledgement-writer census, present runtime chronology, and installed-schema distribution remain UNKNOWN.


## §110 — Active versus dormant readers; GrooveBreaker is not a live wire (2026-11-28)

### Reader inventory correction

A broader source search found `theory_x/auto_probe/groove_breaker.py`, which reads `groove_alerts`. It is a real code-level reader, but it is **not an active runtime consumer on the current main snapshot**:

- The module sets `ENABLED = False` and returns immediately from `check_and_maybe_log()` while disabled.
- The module docstring records that its live construction/call wiring was removed on 2026-07-26.
- `run.py` records that GrooveBreaker instantiation was removed.
- `theory_x/stage6_fountain/__init__.py` records removal of the `check_and_maybe_log()` call.
- `theory_x/stage6_fountain/generator.py` records removal of probe injection because `self._groove_breaker` was never non-None and the class was disabled.

If reactivated, `GrooveBreaker._fetch_active_alert()` currently selects the newest alert above a severity threshold within a freshness window; it does not filter `acknowledged_at`. Its `GrooveContext` retains `alert_id`, and its observation logger writes that ID into `auto_probe_log.groove_alert_id`. Those are dormant source-level behaviours, not current live effects. Do not add GrooveBreaker to the active causal path unless its enable flag and construction/call/injection chain are restored and verified.

### Schema introduction history narrows the migration concern

The schema-history check refined §109's conditional legacy concern:

- Commit `a396dda08e8861e22029ceef813c69211671a37e` (2026-04-26 12:51:58 UTC) added `theory_x/diversity/groove.py` and added the `groove_alerts` DDL to `substrate/schema/beliefs.sql`; the DDL included nullable `acknowledged_at` from its first observed tracked introduction.
- Its parent `db41da3faa03ea7cf96c999495190c5d4b463824` has no `groove_alerts` table in `beliefs.sql`, no `groove_alerts` reference in `init_db.py`, and no `theory_x/diversity/groove.py` file.
- This makes an official earlier tracked schema containing `groove_alerts` without `acknowledged_at` unlikely: the feature table and column entered together. The remaining uncertainty is limited to manually altered, partially upgraded, or otherwise non-standard installed databases; no current host database was inspected.

### Test evidence — detector suppression remains uncharacterized

`tests/test_diversity.py::TestGrooveSpotter` covers n-gram alert generation, no alert for diverse content, and cooldown-fragment filtering. It does not cover the later per-instance stale-rescan fingerprints (`_last_ngram_pattern`, `_last_exact_content`, `_last_template_ids`, `_last_centroid_ids`), repeated `detect_all()` calls on the same unchanged window, or restart/replay behaviour. The source comments document the intended suppression and historical incident, but the current tests do not independently prove those properties.

This is separate from the Metacognition repeat-read gap. There are therefore two unverified idempotency boundaries:

1. Detector -> `groove_alerts`: in-memory suppression of unchanged detector observations, reset on process restart.
2. `groove_alerts` -> derived metacognition/narrative rows: repeated reads of an unacknowledged alert, with source ID retained only on the narrative side-path and without source-ID uniqueness.

Neither boundary should be changed until the intended semantic identity is specified. The alert-row ID is durable within the database; the detector fingerprint is process-local; a detector episode can span multiple alert rows; a metacognitive observation may occur on each chat tick. These are not interchangeable units.

### Research–develop–observe refinement: prove reachability, not just existence

Add a required step to the NEX development scan:

**Source existence → construction → enablement → call site → data path → observable effect.**

For every apparent reader/writer, classify it as active, conditionally active, disabled, removed from runtime wiring, test-only, or unknown. A class that imports successfully or contains SQL is not evidence that the running process calls it. A flag set false plus removed construction/call sites is positive evidence of a dormant path. Conversely, a class may be active through dependency injection even without a direct call in its own module, so trace its object owner and caller before disposition.

This avoids two opposite errors: treating dead code as a live influence, and overlooking a live wire merely because its call is indirect. It is the next practical layer of the “3D scan of a dark artifact”: map not only the physical wire but also whether current is actually flowing through it.

**Disposition:** Phase 0 source-level classification and test-gap finding; documentation only. No runtime code, tests, schema, flags, or behaviour changed. No tests run. No live host, database, process, or service accessed. Gate 0 remains unestablished.

**Source anchors:** `theory_x/auto_probe/groove_breaker.py`; `run.py`; `theory_x/stage6_fountain/__init__.py`; `theory_x/stage6_fountain/generator.py`; `tests/test_diversity.py`; commit `a396dda08e8861e22029ceef813c69211671a37e` and parent `db41da3faa03ea7cf96c999495190c5d4b463824`; current snapshot `18c8f06171e1de35c3210831a49b63d0e2487af0`.

**Evidence level:** source-observed dormant flag and removed live wiring; source-observed historical introduction of table/column; targeted detector-test inspection. Complete repository-wide acknowledgement-writer census, all installed database schemas, and live runtime chronology remain UNKNOWN.


## §111 — GrooveBreaker reachability and detector regression boundary (2026-11-28)

### Reachability result

The earlier reader inventory is now closed for the known GrooveBreaker path. It is not a live consumer on current main:

- `theory_x/auto_probe/groove_breaker.py` has `ENABLED = False`; `check_and_maybe_log()` returns before reading the alert when disabled.
- `run.py` explicitly records its instantiation removed on 2026-07-26.
- `theory_x/stage6_fountain/__init__.py` explicitly records removal of the fountain-tick call.
- `theory_x/stage6_fountain/generator.py` explicitly records removal of the probe injection path and notes that `self._groove_breaker` was never non-None.
- `gui/server.py` has no GrooveBreaker call site in the inspected current source.

If reactivated, its existing alert query does not consult `acknowledged_at`; its context and observation log preserve `alert_id/groove_alert_id`. This should be treated as a reactivation review item, not a present runtime defect. The current active metacognition path is separate and remains wired through `run.py` and the chat handler.

### Detector test boundary

`tests/test_diversity.py::TestGrooveSpotter` contains tests for n-gram firing, diverse-content non-firing, and signal-cooldown fragment quality. It does not exercise `detect_all()` repeatedly against the same unchanged detector window. The current code's four in-memory fingerprint guards are therefore source-observed but not regression-test-verified by this class. The test inventory contains no separate GrooveBreaker test file in the current tree; the module is disabled and uninstantiated, consistent with the runtime classification above.

### Historical table/schema result

The schema's tracked introduction can be bounded to the April 26, 2026 change `a396dda08e8861e22029ceef813c69211671a37e` (12:51:58 UTC): the commit added `theory_x/diversity/groove.py` and added `groove_alerts` to `substrate/schema/beliefs.sql`, including `acknowledged_at` in the initial table DDL. The commit's parent `db41da3faa03ea7cf96c999495190c5d4b463824` has neither the table in the schema nor the GrooveSpotter module. Therefore, there is no evidence of a prior official tracked `groove_alerts` schema lacking the acknowledgement column. The earlier §109 concern is narrowed to manually modified/non-standard databases, not the ordinary tracked upgrade path.

### Development-practice rule added

For every apparent component, trace six gates: **source exists → object constructed → enabled → call site reachable → data actually passed → effect persisted/observed**. Mark each gate with evidence. Do not classify a component as an active influence because its source file contains a SELECT, nor as absent because a direct call is not in the file itself. Constructor injection, feature flags, removed runtime wiring, and process-local state all affect reachability.

This is now a reusable scan rule, not just a GrooveBreaker finding. It prevents dormant code from inflating the active architecture and helps expose live indirect wires.

**Disposition:** Phase 0 source-level refinement; documentation only. No runtime code, tests, schema, flags, or behaviour changed. No tests run. No live host, database, process, or service accessed. Gate 0 remains unestablished.

**Source anchors:** `theory_x/auto_probe/groove_breaker.py`; `run.py`; `theory_x/stage6_fountain/__init__.py`; `theory_x/stage6_fountain/generator.py`; `gui/server.py`; `tests/test_diversity.py`; commit `a396dda08e8861e22029ceef813c69211671a37e` and parent `db41da3faa03ea7cf96c999495190c5d4b463824`; snapshot `18c8f06171e1de35c3210831a49b63d0e2487af0`.

**Evidence level:** source-observed flag, deleted runtime wiring, and feature-table introduction; targeted unit-test inspection. Repository-wide acknowledgement-writer census and installed runtime chronology remain UNKNOWN.


## §112 — Active groove readers and the raw-row / episode distinction (2026-11-28)

### Current reader inventory (main snapshot 18c8f06171e1de35c3210831a49b63d0e2487af0)

The inspected active and dormant paths are now separated:

| Component | Reachability | Query/output | Writes acknowledgement? |
|---|---|---|---|
| `Metacognition._detect_groove()` | Active through `run.py` dependency injection and the chat handler's `tick()` call | Up to 3 newest rows in 600 seconds where `acknowledged_at IS NULL` | No writer found in this component |
| `DiversityLoop` → `ClockRunner._run_medium()` | Active: `run.py` constructs and starts the loop; medium clock runs at 200-fountain-fire intervals | Counts unacknowledged rows detected in the previous 7,200 seconds; stores the number under `consolidations.findings.active_groove_alerts` | No; read plus aggregate observation write only |
| `GET /api/diversity/overview` → `panel.overview()` | Request-activated endpoint in `gui/server.py` | Returns the latest 5 rows with `acknowledged_at IS NULL` | No; read-only panel data |
| `GrooveBreaker` | Dormant: disabled and runtime construction/call/injection removed (see §111) | Would select a recent high-severity row if reactivated | No acknowledgement write found; not active |
| `scripts/trajectory.py` | Standalone offline/read-only analysis | Reads historical rows and collapses consecutive matches into episodes | No; analytical read only |

This targeted inventory found several independent readers of the same alert table. They do not share one consumption cursor. The medium clock and panel count/show raw alert rows; Metacognition derives events and narratives; the trajectory script derives analytical episodes. These are different uses of the same source data, not evidence that one reader owns or consumes the row for all others.

### A current analytical episode definition already exists — but only in an instrument

`scripts/trajectory.py::_groove_episodes()` collapses consecutive rows with the same `(alert_type, sample_belief_ids)` signature into one episode, retaining the first row's timestamp and severity. The script explicitly treats raw rows as re-scans rather than independent events and uses deduplicated episodes for its groove-health calculation.

This gives NEX an existing, source-bounded analytical candidate for an episode signature. It does **not** establish that this signature is the product-level or cognitive semantic identity that Metacognition or Row 9 must use. Its algorithm is read-only, order-dependent, and does not share the in-memory detector fingerprint object. Keep it as an empirical measurement lens until its equivalence to current detector behaviour is validated.

### Why raw counts can diverge across the active system

The same set of source rows can produce at least four different measurements:

1. **Raw alert rows:** number of persisted `groove_alerts` records.
2. **Recent unacknowledged rows:** clock and panel filters over raw records.
3. **Metacognitive observations:** number of times an eligible source row is read and written as a derived `groove` event; repeated ticks can create repeat observations.
4. **Deduplicated episodes:** offline trajectory metric using consecutive `(alert_type, sample_belief_ids)` matches.

Do not compare these counts as though they measure the same thing. In particular, the current Row 9 stillness rule counts derived metacognition events, while the medium clock and panel expose source alert rows, and the offline instrument counts deduplicated episodes.

### Writer census status and search-index limitation

The targeted source inspection of the producer, schema/init path, Metacognition, SelfNarrative, diversity clock, diversity panel, GrooveBreaker, offline trajectory instrument, core substrate files, relevant tests, and maintenance/tool candidates found no active write to `groove_alerts.acknowledged_at`. GrooveSpotter writes new alert rows; the other located paths read them. This is not a repository-wide proof.

The GitHub repository metadata currently reports `is_code_search_indexed=false`. Exact code-search requests returned no matches with `incomplete_results=true`; they cannot establish absence. A direct repository clone could not be completed in the current environment because the host could not resolve `github.com`. Therefore the all-source acknowledgement-writer census remains OPEN. Do not convert the targeted no-match result into “no writer exists.”

### Updated causal map

```text
beliefs → GrooveSpotter → groove_alerts
                            ├─ Metacognition chat tick
                            │    ├─ meta_cognition_events (no groove_id stored)
                            │    └─ narrative_log (source_id stored; no uniqueness)
                            ├─ ClockRunner medium observation (raw row count)
                            ├─ Diversity overview endpoint (latest raw rows)
                            ├─ GrooveBreaker (dormant; not current runtime)
                            └─ trajectory.py (offline episode aggregation)
```

**Disposition:** Phase 0 source-level reader inventory and measurement-semantics refinement; documentation only. No runtime code, tests, schema, flags, or behaviour changed. No tests run. No live host, database, process, or service accessed. Gate 0 remains unestablished.

**Source anchors:** `run.py` (active DiversityLoop startup and Metacognition injection); `theory_x/diversity/loop.py`; `theory_x/diversity/consolidation.py`; `theory_x/diversity/panel.py`; `gui/server.py` (`/api/diversity/overview`); `theory_x/stage9_metacognition/metacognition.py`; `theory_x/stage_self_narrative/self_narrative.py`; `theory_x/auto_probe/groove_breaker.py`; `scripts/trajectory.py`; snapshot `18c8f06171e1de35c3210831a49b63d0e2487af0`.

**Evidence level:** source-observed active startup/call paths and read queries; source-observed derived write paths; offline episode heuristic; targeted code-path scan. Repository-wide acknowledgement writer census, production database chronology, and actual event-to-episode cardinality remain UNKNOWN.


## §113 — Row-9 threshold contract and bounded-read behaviour (2026-11-28)

### Direct source consequence

The combined source path now exposes a second-order threshold ambiguity:

1. `Metacognition._detect_groove()` selects at most the 3 newest unacknowledged alert rows inside a 600-second lookback.
2. `Metacognition.tick()` writes one `meta_cognition_events(event_type='groove')` row for every item returned.
3. After processing the returned list, `tick()` invokes `_maybe_engage_stillness()` once if the list is non-empty.
4. `_maybe_engage_stillness()` counts every `meta_cognition_events` row with `event_type='groove'` created within the previous 1,800 seconds. The threshold is 3.

Consequences derived from those source statements:

- A single tick returning 3 eligible source rows writes 3 derived groove rows and can meet the stillness threshold immediately, even though no repeated chat observation was needed.
- If only 1 source alert remains eligible, 3 separate chat-triggered ticks can write 3 derived rows from that same source alert and meet the threshold.
- If more than 3 unacknowledged source rows exist in the 600-second lookback, the query returns only the newest 3. Older rows wait behind them; because the query has no consumption cursor and no acknowledgement update in this path, sufficiently high arrival volume can cause some older rows to age out before selection. This is a source-level bounded-read/starvation possibility, not a confirmed live incident.
- The non-reentrant stillness check prevents overlapping active stillness rows; it does not deduplicate the evidence used to cross the threshold.

### Test-contract gap

`tests/test_stillness.py` tests that mocked groove counts at/above 3 write a stillness row, below-threshold counts do not, and expiry math is correct. The helper supplies the count as a mock result; it does not seed source alert IDs or prove that the counted derived events correspond to distinct alerts or episodes.

`tests/test_metacognition.py` verifies one seeded unacknowledged alert can create one derived event and that an acknowledged alert is ignored. Its shared Metacognition helper does not pass a SelfNarrative object, and the groove tests do not invoke repeated ticks against one source row.

The current tests therefore establish the numeric threshold and a single-read happy path, but not the threshold's intended semantic unit.

### Required distinction before implementation

The name `sustained_groove` and the constant `_STILLNESS_THRESHOLD = 3` do not specify whether three means:

- three alert rows;
- three distinct detector fingerprints/episodes;
- three distinct source alert IDs;
- three independent metacognitive observations; or
- three observations of the same continuing pattern over time.

Each interpretation has different producer and consumer requirements. The 600-second source lookback, 1,800-second derived-event count window, maximum of three returned rows per tick, and 60-second stillness duration are separate time/volume controls; none of them alone defines what counts as independent evidence.

### Phase 0 characterization matrix (proposal only)

| Scenario | Source setup | What to record |
|---|---|---|
| Repeat one alert | One alert ID, call `tick()` three times with controlled clock | Source ID read count; metacognition row count; narrative rows per source ID; stillness trigger time |
| Three alerts in one tick | Three distinct source IDs inside lookback | Whether one tick writes three events and triggers stillness |
| More than three alerts | Four or more eligible rows | Which three are returned; whether older rows enter or expire under controlled arrival times |
| Episode versus row | Multiple rows with same alert type/sample IDs, then a changed signature | Compare detector fingerprints, source row IDs, trajectory episode count, and Row 9 input count |
| Acknowledgement transition | Mark one source row acknowledged between controlled ticks in an isolated test DB | Confirm it leaves the selection set; do not modify any live database |

This is a characterization plan, not a permission to alter production semantics. Do not add a deduplication rule until the intended unit is explicitly justified against the frozen specification and Founder authority.

**Disposition:** Phase 0 causal/test-contract finding; documentation only. No runtime code, tests, schema, flags, or behaviour changed. No tests run. No live host, database, process, or service accessed. Gate 0 remains unestablished.

**Source anchors:** `theory_x/stage9_metacognition/metacognition.py` (`_detect_groove`, `tick`, `_maybe_engage_stillness`); `tests/test_metacognition.py`; `tests/test_stillness.py`; `substrate/schema/conversations.sql`; snapshot `18c8f06171e1de35c3210831a49b63d0e2487af0`.

**Evidence level:** source-observed query limit, per-row event write, stillness count/threshold, and mocked test contract. Distinct-episode semantics and runtime event chronology remain UNKNOWN.


## §114 — Row 9 stillness scope, duplicate table names, and output-path boundary (2026-11-28)

### The historical Row 9 design intent versus current source

The older `theory_x/SYNTHESIS_PLAN_V2.md` §3 describes stillness as a response when groove alerts reach at least three within 30 minutes **on the same topic**. It says the activation should be substrate-resident and non-reentrant, and that Fountain should suppress re-serving beliefs whose topic matches the grooved topic until expiry. The plan is useful design provenance because the current crystallizer labels its guard “Row 9 extension”; it is not, by itself, authority to reinterpret or amend the frozen S-01–S-25/M1.8 register or Founder sign-off.

Current main source differs in scope:

- `Metacognition._maybe_engage_stillness()` counts all `meta_cognition_events` rows with `event_type='groove'` inside the 1,800-second window. It does not group by topic, source alert ID, or detector episode.
- The Row 9 `conversations.stillness_log` schema has `started_at, duration_s, expires_at, trigger, groove_count`; it has no topic or source identity field.
- `FountainCrystallizer.crystallize()` checks whether **any** unexpired row exists in the conversations database. It does not compare the incoming thought, focal item, belief, or topic with the triggering groove. An active row therefore holds all crystallization through this path, not only crystallization related to the grooved topic.
- The stillness guard returns before the belief insert, the `fountain_crystallizations` link insert, and the speech queue enqueue code that follows a successful belief write.
- In contrast, `FountainGenerator.generate()` has already generated and recorded the fire in the dynamic stream before it calls the crystallizer. It does not return early when `crystallize()` returns `None`; it logs “Fountain fired” and returns the thought. The stage-6 loop receives and logs that returned thought. Therefore the Row 9 guard is not a generation pause: it blocks belief crystallization and the normal TTS queue path while the generated fire remains in the dynamic record.

### Two unrelated tables share the name `stillness_log`

This name collision must stay explicit in every trace:

| Database | Schema | Producer / consumer | Meaning |
|---|---|---|---|
| `conversations.db` | `started_at, duration_s, expires_at, trigger, groove_count` | Metacognition writes it; FountainCrystallizer reads it; GUI status endpoint reports it | Row 9 timed global crystallization hold |
| `dynamic.db` | `ts, reason, retrieval_signature, consecutive_stillness_count, jaccard` | FountainGenerator writes it during duplicate-retrieval stillness/force-fire instrumentation | Fountain retrieval-duplication observation and cadence recovery |

They are separate tables in separate SQLite databases with different schemas and different semantics. A generic search for `stillness_log` without database context is not a valid causal trace.

### What the existing tests establish

- `tests/test_stillness.py` verifies that an active conversations stillness row makes `FountainCrystallizer.crystallize()` return `None` and prevents belief writing; absent/expired rows allow the crystallizer to proceed.
- Those tests do not establish topic matching, because the current row has no topic field and the guard query has no topic predicate.
- They do not verify the full Generator consequence: the fire is already recorded, `generate()` returns the thought, and the normal speech queue is not populated because queue insertion sits later in the crystallizer after belief creation.
- The tests for the dynamic stillness table cover a different mechanism and must not be cited as Row 9 coverage.

### Existing finding linkage and authority boundary

This evidence refines existing backlog item **G-83 (OPEN)**; it is not a newly invented defect ID. G-83 already covers repeated reads of unacknowledged alerts and event-row counting. Its expanded evidence now includes (a) no distinct-source/topic evidence for the threshold, (b) a per-topic design description in an older plan versus a global implementation, (c) a global crystallizer hold, and (d) the fact that generation/dynamic event capture continues while belief/TTS persistence is held.

Before any behavioural change, compare this discrepancy with the actual Founder Sign-Off and frozen specification text. The older `SYNTHESIS_PLAN_V2.md` is historical provenance, not a new authorization. Preserve the known status of the frozen register and Master Roadmap; where the controlling Row 9 requirement or approval cannot be located, say UNKNOWN rather than filling the gap from this plan.

### Updated source-to-effect chain

```text
FountainGenerator
  ├─ generates thought; records dynamic fountain fire
  └─ calls FountainCrystallizer
       ├─ active conversations.stillness_log row?
       │    └─ YES: return None (no belief / crystallization-link / speech-queue write)
       └─ NO: quality checks → belief write → crystallization link → speech governor → TTS queue

Metacognition
  └─ global count of derived groove rows → conversations.stillness_log

Separate dynamic.stillness_log
  └─ records Fountain duplicate-retrieval stillness/force-fire observations
```

**Disposition:** Phase 0 source-to-effect and design-provenance refinement under G-83. Documentation only; no runtime code, tests, schema, flags, or behaviour changed. No tests run. No live host, database, process, or service accessed. Gate 0 remains unestablished; Phase 1 remains unauthorized.

**Source anchors:** `theory_x/SYNTHESIS_PLAN_V2.md` §3; `theory_x/stage9_metacognition/metacognition.py`; `theory_x/stage6_fountain/crystallizer.py`; `theory_x/stage6_fountain/generator.py`; `theory_x/stage6_fountain/__init__.py`; `substrate/init_db.py` (separate dynamic and conversations migrations); `gui/server.py` stillness status endpoint; `tests/test_stillness.py`; snapshot `18c8f06171e1de35c3210831a49b63d0e2487af0`.

**Evidence level:** source-observed end-to-end generation/crystallization/queue order and two database-specific schemas; historical design-plan text; targeted test inspection. Founder Sign-Off correspondence and frozen requirement's Row 9 semantic definition remain UNKNOWN.


## §115 — Row 9 implementation-history comparison (2026-11-28)

### What the tracked history shows

Two commits on 11 May 2026 bracket the original implementation:

- `36e7ed40661db58d83214b40aebde7a33fdb2519` at 11:29:57 UTC added `theory_x/SYNTHESIS_PLAN_V2.md` and updated `theory_x/DOCTRINE.md`. The detailed plan's §3 Row 9 says that stillness should follow at least three groove alerts **on the same topic** in 30 minutes and that Fountain should suppress re-serving beliefs matching that topic.
- `c4b005f32e931047711ef6cdbe03e84a00183885` at 13:21:14 UTC implemented Row 9. Its commit message describes a count of at least three groove events in 1,800 seconds. Its patch counts all `meta_cognition_events.event_type='groove'` rows, writes a topic-free `stillness_log` row, and adds a crystallizer query for any unexpired row. The added tests mock a scalar count; they contain no topic or source-ID fixture.

The Row 9 summary in the updated `theory_x/DOCTRINE.md` describes timed suppression on sustained groove and a non-reentrant substrate-resident timestamp for Fountain, but does not repeat the detailed plan's same-topic wording. The implementation commit message/patch does not explain whether the same-topic clause was deliberately deferred, simplified, or accidentally omitted. No separate decision record was located in this pass.

### Inference boundary

This history establishes that the more specific same-topic design text preceded the global-count/global-hold implementation by less than two hours on the same day. It establishes a **design-to-implementation scope divergence in the tracked artifacts**. It does not establish which document had controlling authority, whether Founder sign-off approved the simplification, or whether another decision record exists outside the inspected files. The current implementation's global behaviour is Runtime Truth; intended authority remains unresolved until the actual Founder Sign-Off/frozen requirement is located.

The finding stays under G-83. Do not create a new defect ID and do not “restore” same-topic semantics from the older plan without authority review. The next useful Phase 0 evidence is to locate the approval/decision record or explicitly retain UNKNOWN, then characterize source identity and topic semantics with isolated tests once such work is authorized.

**Disposition:** Phase 0 historical provenance refinement under G-83; documentation only. No runtime code, tests, schema, flags, or behaviour changed. No tests run. No live host, database, process, or service accessed. Gate 0 remains unestablished; Phase 1 remains unauthorized.

**Source anchors:** `theory_x/SYNTHESIS_PLAN_V2.md` §3; `theory_x/DOCTRINE.md` Row 9 table; design commit `36e7ed40661db58d83214b40aebde7a33fdb2519`; implementation commit `c4b005f32e931047711ef6cdbe03e84a00183885`; `theory_x/stage9_metacognition/metacognition.py`; `theory_x/stage6_fountain/crystallizer.py`; `tests/test_stillness.py`.

**Evidence level:** commit-dated design and implementation patches; current-source match to implementation; no documented rationale found in the inspected commit message/patch. Founder authorization and frozen Row 9 semantic definition remain UNKNOWN.

 
## §116 — Metacognition tick is chat-driven, not part of the 60-second diversity loop (2026-11-28)

### Caller and registry trace

The current boot/caller path separates background alert production from metacognitive consumption:

- run.py constructs the production Metacognition instance, injects SelfNarrative, assigns it to state.metacognition, and separately constructs/starts the DiversityLoop.
- DiversityLoop._run() calls GrooveSpotter, DormancyScanner, and ClockRunner every 60 seconds. It does not call Metacognition.tick().
- The production chat handler in gui/server.py calls state.metacognition.tick() while assembling chat context, then calls format_for_prompt().
- theory_x/__init__.py defines the SentienceNode protocol and a process-lifetime registry. Its protocol docstring explicitly describes tick() as being called once per chat turn. register() only appends a node; all_nodes() only returns the registered nodes. No periodic tick dispatcher is implemented in this registry.
- The alternate gui.server.build_state() path can construct a Metacognition instance when with_tools=True; that instance likewise uses the same chat handler tick path. It is not evidence of a background metacognition scheduler.

### Cadence consequence

GrooveSpotter may create alerts on its 60-second background cycle while Metacognition does not consume them until the next chat turn. At that turn it reads at most the three newest unacknowledged rows from the preceding 600 seconds. This produces a burst/recency consumer, not a paired detector-observation loop:

- if more than three alerts accumulate, the query returns only the newest three;
- if chat turns recur while the same rows remain unacknowledged, the same source rows can be re-read and re-written as derived events;
- if there is no chat turn, the current source path does not call _maybe_engage_stillness(), even if the background detector has produced alerts.

The Row 9 stillness mechanism therefore depends on chat-triggered observation frequency. The 60-second diversity cadence, 600-second detector lookback, 1,800-second event count window, and 60-second stillness duration are four separate controls, not one continuous observation cadence.

### What this does not establish

This does not prove that chat-driven ticking is wrong. The interface contract itself says tick is per chat turn. It does establish that the DiversityLoop is not a second periodic metacognition caller, and that a background GrooveSpotter alert does not automatically cause a Row 9 evaluation while the user is absent. Any expectation of background stillness response would need a distinct, authorized scheduler/caller contract; do not introduce one based on inference.

**Disposition:** Phase 0 caller/cadence refinement under G-83; documentation only. No runtime code, tests, schema, flags, or behaviour changed. No tests run. No live host, database, process, or service accessed. Gate 0 remains unestablished; Phase 1 remains unauthorized.

**Source anchors:** run.py (construction, injection, DiversityLoop startup); gui/server.py (chat handler tick and alternate build_state construction); theory_x/__init__.py (SentienceNode tick contract and passive registry); theory_x/diversity/loop.py; theory_x/stage9_metacognition/metacognition.py; snapshot 18c8f06171e1de35c3210831a49b63d0e2487af0.

**Evidence level:** source-observed boot construction, chat caller, background loop calls, and passive registry implementation. Exact user chat cadence and live alert accumulation remain UNKNOWN.


## §117 — Re-consumed groove rows can renew the Row 9 hold (2026-11-28)

### Derived source-level timeline

The combination of G-83's repeat-read path and the Row 9 non-reentrant window implies a repeatable renewal sequence. Let A be one still-unacknowledged groove alert, or A/B/C three such alerts, all still inside the 600-second source lookback:

1. At chat tick T0, _detect_groove() returns the eligible row(s). tick() writes one derived groove event per returned source row. If three events are now present in the rolling 1,800-second count, _maybe_engage_stillness() inserts a stillness row expiring at T0 + 60 seconds.
2. At later chat ticks before expiry, the same source row(s) may be returned again and more derived groove events written. The active-row check prevents another stillness insert, but it occurs after these event writes.
3. At a chat tick after the stillness row expires, if the same source alert(s) are still inside the 600-second lookback, _detect_groove() returns them again. The new derived groove event(s) are written before the stillness count. The count still includes at least three recent derived events, so a new 60-second stillness row can be inserted without a new detector episode.
4. The sequence can repeat while a source alert remains eligible and chat turns continue. New alerts can extend the eligibility period. Once no eligible groove alerts are returned, tick() does not call _maybe_engage_stillness(), so this particular renewal path stops creating new holds.

The threshold window is 1,800 seconds, longer than the 600-second alert lookback and the 60-second stillness duration. Re-consuming an unchanged source row replenishes the derived-event count before the next hold check. This means the repeated derived writes can both cross the threshold initially and keep it crossed when a prior stillness row expires.

### Separate starvation effect

The source query orders by detected_at DESC and LIMIT 3, with no cursor or acknowledgement in this consumer. If three or more unacknowledged rows remain eligible, the same newest three can be returned repeatedly. Older eligible rows remain behind them and, absent another removal path, can age out of the 600-second lookback without ever being selected. This is a deterministic query-order consequence under a static set of more than three eligible rows; no live accumulation has been asserted.

### Evidence boundary and test proposal

This is a source-derived renewal possibility, not a runtime incident. It depends on the chat caller being invoked while the same alert remains in the lookback. Exact chat cadence and live source-row chronology remain UNKNOWN.

Add a focused characterization scenario to the G-83 matrix: one alert ID (then three IDs), repeated chat ticks at controlled times inside and outside 60-second expiry boundaries, and no new detector writes. Record the source IDs selected, derived event row count, stillness activation timestamps, and the first tick at which the hold cannot renew. Also test four eligible alerts to expose LIMIT 3 starvation. Use an isolated test database and controlled clock; do not touch live state. Assertions must distinguish repeated observation from new alert/episode identity.

**Disposition:** Phase 0 causal consequence and regression-proposal refinement under G-83; documentation only. No runtime code, tests, schema, flags, or behaviour changed. No tests run. No live host, database, process, or service accessed. Gate 0 remains unestablished; Phase 1 remains unauthorized.

**Source anchors:** theory_x/stage9_metacognition/metacognition.py (_detect_groove, tick, _maybe_engage_stillness); gui/server.py (chat tick caller); tests/test_metacognition.py; tests/test_stillness.py; snapshot 18c8f06171e1de35c3210831a49b63d0e2487af0.

**Evidence level:** source-derived temporal sequence from inspected query ordering, write ordering, thresholds, and caller cadence; not test-verified and not runtime-observed.


## §118 — Sentience 5.5 StillnessNode prior art versus NEX Row 9 (2026-11-28)

### Original prior-art behaviour

The referenced file exists in the user's separate repository: kron777/Sentience_5.5, main snapshot 1767acf1fdb321d046261eb3c3059084c85fc0c8, Stillness_Node.py blob f290b17451974614d74881ea7e491b2ec4e9a252.

Its relevant design is deliberately simple:

- one process-wide is_still boolean and one stillness_until timestamp;
- enter_stillness(duration, trigger) returns immediately if already still, otherwise marks the global node still, awaits the duration, clears the state and writes a stillness_events row;
- the persisted row contains start_time, end_time, duration and trigger only;
- neither the live state nor the persisted event carries a topic, groove-alert ID, episode fingerprint or belief identity;
- it is trigger-driven through an HTTP handler; the module itself does not decide that a particular topic has become repetitive.

The file's role text says deterministic cognitive pauses/system-wide quiescence and no emotion, bias or interpretation. Its actual implementation exposes a global timed state/status and an event log; it does not itself contain a topic-aware suppression algorithm.

### Three layers of semantics must not be collapsed

1. **Sentience 5.5 prior art:** a global non-reentrant timed pause state, triggered externally, without topic or alert identity.
2. **NEX synthesis-plan extension:** at least three groove alerts on the same topic in 30 minutes; a substrate-resident non-reentrant activation; Fountain suppresses beliefs matching that topic.
3. **Current NEX implementation:** globally counts derived groove event rows, creates a topic-free conversations stillness row, and globally blocks crystallization while any such row is active. Fountain still generates/records the fire; the crystallizer returns before belief/link/TTS-queue persistence.

The current implementation is structurally closer to the prior art's global non-reentrant state than to the plan's same-topic refinement. However, it is not a full system-wide pause: the observed gate is at the crystallizer boundary, not at thought generation or all system activity.

### What can and cannot be concluded

The prior-art file helps explain the source shape and why a global state was an available starting point. It does not prove why the same-topic NEX plan was not carried into implementation. The implementation commit cites the Row 9 extension and StillnessNode prior art; its patch does not record an explicit decision to defer the topic refinement. The exact intended NEX semantics remain authority-sensitive and must be checked against Founder Sign-Off/frozen specifications before any behavioural change.

This research also yields a reusable porting lesson: when adapting prior art, write down the inherited behaviour, the NEX-specific semantic delta, and the tests that prove the delta. A copied non-reentrant state machine is not equivalent to a later topic-aware design just because both are called “stillness”.

**Disposition:** Phase 0 comparative design-provenance refinement under G-83; documentation only. No changes were made to Sentience_5.5 or NEX runtime. No tests run. No live host/database/process/service accessed. Gate 0 remains unestablished; Phase 1 remains unauthorized.

**Source anchors:** Sentience_5.5/Stillness_Node.py at 1767acf1fdb321d046261eb3c3059084c85fc0c8; NEX theory_x/SYNTHESIS_PLAN_V2.md §3; theory_x/DOCTRINE.md Row 9; NEX implementation commit c4b005f32e931047711ef6cdbe03e84a00183885; current NEX snapshot 18c8f06171e1de35c3210831a49b63d0e2487af0.

**Evidence level:** directly inspected original prior-art source; compared with the NEX design-plan text, doctrine summary, implementation patch and current runtime source. Reason for omitting the topic-specific refinement and controlling Founder authority remain UNKNOWN.


## §119 — Row 9 does not pause the existing speech queue (2026-11-28)

### Speech producer/consumer boundary

The earlier conclusion that the Row 9 guard prevents the current fire's normal speech enqueue is correct, but it must not be generalized into “stillness pauses speech”:

- A new Fountain thought reaches the speech enqueue code only after successful crystallization and belief creation. When the Row 9 guard returns None at the start of crystallization, that fire does not create the corresponding belief or speech_queue row.
- The SpeechQueueConsumer is a separate daemon thread. run.py constructs it with only the beliefs Writer/Reader (plus voice configuration/state/backend). It does not receive a conversations Reader.
- The consumer polls beliefs.db for speech_queue rows with status='pending', orders by queued_at, and speaks them when not paused and outside configured quiet hours.
- Its inspected polling and _speak_one() paths have no read of conversations.stillness_log and no Row 9 gate. The consumer can therefore continue consuming entries that were already pending when a Row 9 stillness row became active.
- The consumer's own pause/quiet-hours controls are independent. They are not set by Metacognition._maybe_engage_stillness().

### Effective Row 9 boundary

Current source behaviour is therefore:

| Output stage | Effect of active Row 9 conversations stillness row |
|---|---|
| Thought generation | Continues; Generator returns the thought |
| Dynamic fountain fire record | Already written before crystallizer call; remains |
| Belief crystallization | Blocked at Crystallizer precondition |
| New speech_queue item for that fire | Not created, because enqueue follows belief creation |
| Existing pending speech_queue items | Not held by the Row 9 code; consumer can continue speaking them |
| Other non-Fountain producers of speech_queue rows | Not shown to consult Row 9 in this source pass; their behaviour remains outside this specific path |

This is another reason not to call the current mechanism a global speech pause. It is a crystallization precondition whose side effect is to prevent new speech entries from that Fountain fire; it does not quiesce the already-running speech consumer or drain/hold its backlog.

### Test coverage and next characterization

tests/test_speech.py exercises queue creation, duplicate enqueue prevention, the consumer pause flag, and shutdown during synthesis. It does not activate a Row 9 conversations stillness row while a pending speech_queue item exists. tests/test_stillness.py verifies the crystallizer guard but does not start a consumer with pre-existing queued audio.

A bounded isolated characterization should seed a pending speech row, activate a conversations stillness row, and verify the consumer's current behavior separately from the new-enqueue path. This is a descriptive test of the existing boundary; it is not an authorization to make Row 9 control the consumer. Any new consumer gate would affect voice output policy and requires authority review.

**Disposition:** Phase 0 output-path refinement under G-83; documentation only. No runtime code, tests, schema, flags, or behaviour changed. No tests run. No live host, database, process, audio device, or service accessed. Gate 0 remains unestablished; Phase 1 remains unauthorized.

**Source anchors:** run.py (SpeechQueueConsumer construction and beliefs-only dependencies); speech/queue_consumer.py (pending poll, pause/quiet-hours checks, synthesis/playback); theory_x/stage6_fountain/crystallizer.py (belief and speech enqueue ordering); theory_x/stage6_fountain/generator.py (post-crystallizer return); tests/test_speech.py; tests/test_stillness.py; snapshot 18c8f06171e1de35c3210831a49b63d0e2487af0.

**Evidence level:** source-observed independent consumer, its dependencies, poll/write path and absence of Row 9 query in inspected consumer code; targeted test inventory. Runtime queue state/audio chronology remains UNKNOWN.


## §120 — Groove reader census: active prompt wires, conditional readers, and observation-only paths (2026-11-28)

### Direct alert-table producer and acknowledgement-writer result

The direct producer remains GrooveSpotter in theory_x/diversity/groove.py. Its four detector branches INSERT rows into beliefs.db.groove_alerts. The schema defines acknowledged_at as a nullable REAL field. In the tracked-source inspection, no direct UPDATE/assignment to acknowledged_at, trigger, or acknowledgement-owning service was located. All direct references located to that column are SELECT filters (Metacognition, ClockRunner, panel, Probe ContextSnapshot). The search service still reports this repository as not code-indexed, so empty code-search results are not evidence; this classification is from file-by-file source reads.

**Census disposition:** no tracked direct acknowledgement writer was found in the inspected Python, SQL, UI and launch/config source paths. This narrows the open question from “where is the writer?” to “is the column intentionally read-only, or is an external/untracked/dynamically assembled writer expected?” No live DB, host, or running process was inspected. Do not mark the field unwritten in all deployments as a runtime fact; no such runtime fact has been measured.

### Active prompt and drive influence

Two additional consumers are real runtime wires, rather than just references in files:

1. **CompetingDrives — active, indirect drive/prompt influence.**
   - run.py constructs and starts CompetingDrives on its 600-second loop.
   - FountainGenerator also calls compute_now() on the per-fire path.
   - _compute_weights() reads MAX(groove_alerts.severity) across the trailing 24 hours, without an acknowledged_at filter.
   - That value contributes 0.30 × groove to the raw coherence-drive weight. The active opposing pairs include coherence↔exploration and curiosity↔coherence.
   - format_for_prompt() emits a tension block when the opposing-pair set changes and qualifying weights exceed the threshold; FountainGenerator appends that block to the prompt.
   - This is an indirect, conditional influence on prompt framing through a drive measurement. It is not an action-authority gate, and it does not consume or acknowledge the source alert.

2. **Recent STRIKING feedback — default-on conditional prompt filter.**
   - FountainGenerator._build_recent_striking_block() retrieves recent STRIKING-tagged fire candidates, removes near-duplicates, then reads the newest groove_alerts.pattern with severity ≥0.5 from the preceding hour.
   - It splits that pattern into terms and removes sampled candidate fires containing those terms before building the “Recent voice of yours that landed as itself” prompt block.
   - The prompt builder invokes this block when conversations/dynamic readers exist and NEX5_GENIUS_PROMPT_OFF != 1. The tracked keepalive launch line does not set that disable flag; the default source path is therefore enabled, subject to inherited environment and the presence of eligible STRIKING rows.
   - This is an active/conditional prompt-selection influence, not an acknowledgement or action veto. It does not change previously stored alerts or beliefs.

### Conditional and dormant readers

| Path | Source condition / reachability | Effect and classification |
|---|---|---|
| Substrate-as-Voice in FountainGenerator | Reads max severity over 24h; caller only invokes it when NEX5_RECONCILE != 1. The tracked keepalive launch line sets NEX5_RECONCILE=1. | Dormant under the documented launch profile; if re-enabled, severe groove can shorten cooldown and select a stored anchor instead of normal generation. Do not include it in the current active path. |
| Stakes readiness appraisal | NEX5_STAKES=1 is required; module documents default OFF and shelving pending a dominance-out gate. The tracked keepalive line does not set NEX5_STAKES; inherited environment is not host-verified. | Conditional readiness penalty based on the rate of template_repetition alert rows in the trailing hour. Not part of the stated default launch profile; runtime environment remains UNKNOWN. |
| Topic Gate Shadow | NEX5_TOPIC_GATE_SHADOW=1 required; source documents default OFF and telemetry-only. | Dormant telemetry path; reads groove severity for topic_gate_shadow_log and does not block or replace prompt content. |
| GrooveBreaker | ENABLED=False; run.py construction, stage-6 tick call and prompt-injection wiring removed. | Dormant; its recent-alert reader is not a current runtime wire (see §111). |
| Raga detector | Standalone diagnostic CLI; its detect() can read one recent groove alert. FountainGenerator imports only its recent-thought/repetition helpers for another path; no booted Raga detector or current runtime call to its groove reader was located. | Manual diagnostic/measurement only in the inspected boot graph. |
| ContextSnapshot / ProbeRunner | ProbeRunner is constructed at boot; /api/probes/run calls it on request. ContextSnapshot reads the newest 10 unacknowledged rows before the requested probe and stores them in probe_context. | User/request-triggered research capture; no source acknowledgement and no autonomous action path. |
| SubstrateHarmonic | Active 300-second worker reads max groove severity over 24h and writes substrate_coherence. Module explicitly defines this phase as LOG-ONLY and says future consumers do not yet exist. | Active measurement only; no current behavioral consumer identified. |
| StateSnapshotWriter | ENABLED=True; run.py constructs/passes it to Fountain; the stage-6 loop calls write_snapshot(). The JSON snapshot includes the newest five groove alert rows. Its module states Phase A has no read-back. | Active forensic snapshot only; no current NEX read-back path. |
| Diversity overview / UI | GUI endpoint calls panel.overview(), which reads the latest five unacknowledged rows; app.js displays at most two. | Request/UI presentation only; no mutation. |
| trajectory.py | Standalone read-only monitor; collapses consecutive matching (alert_type, sample_belief_ids) rows into offline episodes. | Offline analysis only; not the live Row 9 identity contract. |

A small placeholder in coincidence/context_capture.py stores a groove_alerts field as None with a comment that it is not yet captured from the DB; it is not a direct alert-table read or acknowledgement writer.

### Revised causal inventory

The current alert table therefore has several distinct downstream semantics:

- **Detection:** GrooveSpotter emits alert rows.
- **Chat reflection:** Metacognition turns eligible source rows into derived groove events and can repeat them (G-83).
- **Timed crystallization hold:** Row 9 counts derived events globally and blocks new belief crystallization, with the generation/speech boundaries described in §§114–119.
- **Drive/prompt shaping:** CompetingDrives consumes severity as a coherence input; recent STRIKING feedback uses the alert pattern to filter prompt candidates.
- **Observation:** harmonic score, state snapshot, GUI, probe snapshot, trajectory analysis.
- **Dormant/conditional:** GrooveBreaker, substrate voice in the current launcher, topic shadow, and stakes penalty unless their relevant gates are active.

These routes do not share one acknowledgement cursor or one episode identity. They must not be added together as though they are one causal consumer. In particular, a prompt filter or drive weighting may read the same alert while Metacognition later re-reads it; neither reader's read is a global consume.

### Development-method refinement: trace the signal to all effect classes

Extend the “one wire is never local” scan from producer→reader to:

**producer → direct readers → transformed measures → runtime reachability → prompt/drive effects → observation-only sinks → independent consumers → authority boundary.**

For every read, record whether it (a) gates, (b) selects/reorders, (c) alters a prompt, (d) changes a drive/score, (e) records telemetry, or (f) only displays. Then trace the exact owner/caller and relevant flag. The same SQL SELECT can be observational in one module and behavior-shaping in another; the effect classification depends on the sink and reachability, not the query alone.

**Disposition:** Phase 0 reader-census and influence-classification refinement under G-83; documentation only. No runtime code, tests, schema, flags, or behaviour changed. No tests run. No live host, database, process, API request, audio device, or service accessed. Gate 0 remains unestablished; Phase 1 remains unauthorized.

**Source anchors:** theory_x/diversity/groove.py; theory_x/stage9_metacognition/metacognition.py; theory_x/diversity/consolidation.py; theory_x/diversity/panel.py; theory_x/stage_drives/competing_drives.py; run.py; theory_x/stage6_fountain/generator.py; theory_x/stage6_fountain/readiness.py; theory_x/harmonic/substrate_harmonic.py; theory_x/memory/snapshot_writer.py; theory_x/probes/context_snapshot.py; theory_x/probes/probe_runner.py; gui/server.py; gui/static/app.js; theory_x/stage_tom/raga_detector.py; theory_x/stage_tom/stakes_appraisal.py; scripts/trajectory.py; nex_keepalive.sh; substrate/schema/beliefs.sql; snapshot 18c8f06171e1de35c3210831a49b63d0e2487af0.

**Evidence level:** source-observed boot construction, loop/caller paths, feature-flag conditions, SQL reads/writes and sink behaviour; exact host environment, live event chronology, external DB clients, and dynamically assembled/untracked SQL remain UNKNOWN.


## §121 — GrooveSpotter's detector identity is process-local and type-specific (2026-11-28)

### Four detector fingerprints, four different meanings of “same”

The current GrooveSpotter implementation has four independent in-memory fingerprints:

| Detector | Fingerprint stored in the GrooveSpotter instance | What unchanged means |
|---|---|---|
| Exact repetition | Exact repeated sentence content | The top repeated sentence is unchanged |
| N-gram repetition | Top repeated trigram text | The most-common trigram remains the same |
| Template repetition | frozenset of all participating templated belief IDs | The participating belief-ID set is unchanged |
| Centroid tightening | Ordered tuple of all current-window belief IDs | The complete current-window order is unchanged |

Each detector clears its fingerprint when its own condition falls below its threshold (or, for the centroid detector, when the required previous window/spread is unavailable). A still-present unchanged fingerprint skips insertion on the next 60-second scan. This addresses the historical stale-rescan flood recorded in the module comments.

The fingerprints are **not durable**. They live on the GrooveSpotter instance created by DiversityLoop. The instance is recreated on process restart, so all four fingerprints start as None. The module comment explicitly allows one fresh emission after restart if the same condition is still present. Therefore:
- repeated scans in one process can be suppressed;
- a restart can create a new alert row for a still-present detector condition;
- a new alert row after restart is not necessarily a new underlying groove episode;
- the in-memory fingerprint is not available to Metacognition, the GUI, the probe snapshot, or the offline trajectory tool.

### Stored alert fields do not preserve every detector fingerprint

The four alert writers populate the common columns, but their sample_belief_ids fields are not a uniform identity contract:

- N-gram alerts store the first five rows of the current 20-belief window, while the in-memory fingerprint is the top trigram string.
- Exact-repetition alerts store IDs of the rows with the repeated exact content.
- Template-repetition alerts store the participating templated IDs; this broadly corresponds to its frozenset fingerprint.
- Centroid alerts store the first five current-window IDs, while the in-memory fingerprint includes the complete ordered current window.

The common table does not store a dedicated detector fingerprint, detector process/boot ID, episode ID, or durable “already emitted” record. Thus the original detector-level identity cannot always be reconstructed exactly from a persisted row.

### Offline trajectory grouping is a different equivalence relation

scripts/trajectory.py groups consecutive rows by (alert_type, sample_belief_ids) and treats the first row of each run as an episode. This is useful for historical analysis, but it is not identical to the detector's internal identity:

- For n-gram alerts, two different top trigram patterns can share the same alert_type and the same first-five sample IDs, causing the offline grouping to merge them.
- For centroid alerts, the current-window fingerprint can change outside the first five IDs while the persisted sample_belief_ids stays the same, so the offline grouping can merge detector states that the producer treated as different.
- A process restart can re-emit the same detector condition as a new row; the offline grouping may merge or separate it depending on adjacency and sample IDs, not on restart or process identity.

The trajectory episode count therefore remains an analytical estimate, not the canonical detector episode count. It should not be used as a drop-in replacement for alert-row IDs or source fingerprints in Row 9.

### Test boundary

tests/test_diversity.py::TestGrooveSpotter tests individual detector conditions and cooldown-fragment filtering. It does not currently characterize repeated detect_all() calls against the same unchanged window for all four detector types, fingerprint clearing when each condition stops holding, or new-instance/restart replay. The current tests therefore do not prove the in-memory stale-rescan suppression contract or its restart boundary.

### Bounded characterization matrix

| Case | Expected property to characterize |
|---|---|
| Same unchanged window, same instance | First qualifying scan emits; subsequent identical scans do not reinsert for each detector type |
| Condition clears, then returns | The detector resets its fingerprint and emits a new alert on the later recurrence |
| New GrooveSpotter instance, same unchanged window | The new instance may emit once again; this is restart replay, not necessarily a new episode |
| Same n-gram window, different top pattern | Producer fingerprint changes even if sample-belief window IDs remain the same |
| Same centroid first-five IDs, changed remaining window | Producer fingerprint changes even if the persisted sample-belief summary does not |
| Four or more eligible alerts downstream | Metacognition's independent LIMIT 3 selection remains separately characterized; detector dedup does not fix consumer replay |

These are characterization expectations from the inspected implementation, not executed test results. No source code or tests were changed in this pass.

**Disposition:** Phase 0 producer-identity refinement under G-83; documentation only. No runtime code, tests, schema, flags, or behaviour changed. No tests run. No live host, database, process, or service accessed. Gate 0 remains unestablished; Phase 1 remains unauthorized.

**Source anchors:** theory_x/diversity/groove.py (GrooveSpotter.__init__, detect_all, four detector methods); theory_x/diversity/loop.py (one per-loop instance and 60-second scan); run.py (loop startup); tests/test_diversity.py::TestGrooveSpotter; scripts/trajectory.py::_groove_episodes; theory_x/stage9_metacognition/metacognition.py; snapshot 18c8f06171e1de35c3210831a49b63d0e2487af0.

**Evidence level:** source-observed in-memory fingerprint rules and persistence fields; targeted test inventory; offline metric comparison. Restart chronology and actual production alert cardinality remain UNKNOWN.


## §122 — Test-only GrooveSpotter fingerprint characterization candidate (2026-11-28)

### Separate PR #448

A separate, test-only branch has been opened as draft PR #448:
https://github.com/kron777/Nex_v5.0/pull/448

Head commit: f4447ad5b243b97c91c28fc00abbef88fe7c51f9. Base: current main 18c8f06171e1de35c3210831a49b63d0e2487af0. One file added: tests/test_groove_spotter_fingerprints.py (177 lines, no deletions).

The tests exercise the four existing GrooveSpotter detector fingerprints independently:
- n-gram top-pattern string;
- exact repeated sentence content;
- template participating-belief-ID set;
- centroid ordered current-window ID tuple.

For each detector, the characterization checks: first qualifying observation emits, unchanged repeat in the same instance is suppressed, loss of the qualifying condition clears the fingerprint, the same condition can emit again after clearing, and a new GrooveSpotter instance can emit once again because fingerprints are process-local.

### Scope and validation boundary

This is characterization of existing source behaviour only. It does not change GrooveSpotter, thresholds, detection logic, alert schema, acknowledgement semantics, Metacognition, Row 9, feature flags, or NEX cognitive behaviour. It does not choose a canonical groove episode identity and does not claim that restart replay is a new semantic episode.

The repository's GitHub Actions workflow for this exact head was created as run 46173749707, event pull_request, status queued at the time of this snapshot. Commit status reports pending with zero completed status contexts. No test result is available yet. No local tests were run. Keep PR #448 draft until exact-head CI, review and evidence interpretation are complete.

### Next evidence after CI

If the workflow passes, record only that the characterization tests pass on this exact head; do not upgrade it to live runtime observation. If it fails, inspect the precise failure and correct the test fixture without touching runtime detector semantics. Then consider separate characterization of detect_all() call ordering and integration with the background loop, again without changing behaviour.

**Disposition:** Phase 0 test-characterization candidate under G-83. One test file only; no runtime source or behaviour change. G-83 remains OPEN. Gate 0 remains unestablished; Phase 1 remains unauthorized.

**Evidence anchors:** PR #448; commit f4447ad5b243b97c91c28fc00abbef88fe7c51f9; tests/test_groove_spotter_fingerprints.py; theory_x/diversity/groove.py; tests/test_diversity.py; workflow run 46173749707; main snapshot 18c8f06171e1de35c3210831a49b63d0e2487af0.

**Evidence level:** test source committed; exact-head CI queued, not yet test-verified; no runtime observation.


## §123 — Historical runtime anchor: November 14 groove alert population and episodes (2026-11-28)

### What the contemporaneous investigation recorded

The tracked journal journal/INVESTIGATION_2026-11-14_groove_facts.txt contains a direct, read-only observation of the then-live beliefs.db:

- COUNT(*) was 1,198 on the first check and 1,199 about 20 minutes later; the underlying NEX process was not stopped or touched during the investigation.
- Earliest recorded alert: 2026-10-26 22:29:46.
- Type distribution in the 1,198-row sample: template_repetition 1,136 (94.8%); ngram_repetition 62 (5.2%); exact_repetition 0; centroid_tightening 0.
- acknowledged_at IS NOT NULL was 0 of 1,198 at that historical observation time.

This is historical runtime-observed evidence preserved in the repository journal. It is not a measurement of the current host or current database. The journal also notes that its “never written” conclusion was based on what that investigation found; the current tracked-source census likewise has not located a direct writer, but neither source proves that no external, untracked, or dynamically constructed writer has ever existed.

### The historical 30-minute episode calculation

The journal grouped all 1,199 alert rows by a 30-minute gap between consecutive rows (chosen because other code uses a 1,800-second freshness window). That analysis produced:
- 55 gap-clustered groups;
- alerts per group: minimum 1, median 14, p90 54, maximum 102;
- group span: median approximately 106.7 minutes, p90 approximately 376.7 minutes, maximum approximately 837.3 minutes.

For the November 10 “Aligned Model” incident, the two specifically matched source alerts were IDs 751 and 752, both template_repetition at severity 1.0. The same historical gap analysis put that incident's alert group at 8 rows over 56.4 minutes. The journal also records that GrooveSpotter pushed a signal_cooldown entry and a later crystallization reject matched “aligned model”. These are source-journaled database observations, not a current replay.

### How this relates to today's identity analysis

Keep four identities distinct:

1. **Persisted alert row:** one row in groove_alerts, with its database ID and common alert columns.
2. **GrooveSpotter in-memory detector fingerprint:** one of four type-specific per-instance fingerprints (§121); not durable across restart.
3. **Historical 30-minute gap cluster:** an offline grouping of consecutive rows by time gap, across alert types. It is an analytical estimate, not the producer's fingerprint.
4. **Row 9 derived event:** a meta_cognition_events row created each time Metacognition reads an eligible source alert; repeats of the same source row can create multiple derived events.

The November 14 report's phrase “one alert” refers to a fresh detector emission after stale-rescan suppression, not to a universally defined episode. Its gap-clustering distribution is useful operational history, but cannot supply the missing canonical identity needed by G-83 or Row 9. In particular, the 55 historical gap groups must not be compared directly with current derived event counts or detector fingerprints.

### What this historical anchor supports — and what it cannot

It supports that:
- the historical source table was growing during the investigation;
- none of the sampled historical rows had acknowledged_at set;
- template_repetition overwhelmingly dominated that sample;
- long-lived repetition patterns were observed in the historical gap-cluster analysis;
- at least one specific live incident generated maximum-severity template alerts and a real cooldown effect.

It does not establish current alert frequency, present acknowledgement state, restart replay frequency, current host status, or whether all historical alert rows were distinct semantic episodes. The original journal itself flags that raw-fire topic dwell beyond crystallized beliefs was not computed; no estimate of raw-fire repetition duration should be inferred from this table.

**Disposition:** Phase 0 historical runtime evidence reconciliation under G-83; documentation only. No runtime code, tests, schema, flags, or behaviour changed. No live host/database/process/service accessed in this pass. Gate 0 remains unestablished; Phase 1 remains unauthorized.

**Source anchor:** journal/INVESTIGATION_2026-11-14_groove_facts.txt, especially its Q2 alert count/type/acknowledgement breakdown, 30-minute gap-clustering distribution, Q3 incident rows/cooldown evidence, and final evidence limitations. Current implementation comparison: theory_x/diversity/groove.py, theory_x/diversity/loop.py, theory_x/stage9_metacognition/metacognition.py; manual §§112–123.

**Evidence level:** historical runtime-observed counts and event rows as reported by the contemporaneous read-only journal; source-observed current identity model; retrospective 30-minute grouping method. Current live database state and cross-restart episode identity remain UNKNOWN.


## §124 — Dual G-83 characterization candidates: producer and consumer (2026-11-28)

### Producer-side characterization: PR #448

Draft PR #448, head f4447ad5b243b97c91c28fc00abbef88fe7c51f9, adds tests/test_groove_spotter_fingerprints.py. It characterizes all four producer fingerprints (ngram, exact, template, centroid) for same-instance unchanged suppression, clearing/re-emission after the condition disappears, and fresh-instance replay. Exact-head full test workflow run 46173749707 is IN_PROGRESS; no result yet.

### Consumer-side characterization: PR #449

Draft PR #449, head 50c2e083de1dab3e40301b37dc14b614a0d08f23, adds one controlled-clock test to tests/test_metacognition.py. It seeds exactly one unacknowledged source alert and calls Metacognition.tick() five times. The assertions characterize the current path:
- one source alert remains singular and unacknowledged;
- five derived groove events are written from that same source alert;
- the third event starts a 60-second Row 9 stillness window;
- the fourth event is written while the hold is active but does not stack a hold;
- after expiry, the fifth event causes a second stillness activation without a new source alert.

Exact-head full test workflow run 46174148899 is IN_PROGRESS; no result yet.

### Combined scope and interpretation

Both are test-only Phase 0 characterization candidates. Neither changes runtime code, thresholds, schemas, feature flags, detector or Metacognition behaviour, the frozen specifications, or the roadmap. Together they test the two separate replay boundaries documented in §121 and G-83: detector instance identity and downstream consumer re-observation. They do not settle what should count as a semantic episode or whether the Row 9 threshold should be global/topic-specific/source-based. G-83 remains OPEN.

No test has been run locally and no CI pass is claimed. Keep both PRs in draft until each exact-head workflow completes and the test results are reviewed. A failure must be diagnosed before updating the evidence status; do not treat queued/in-progress as validation.

**Disposition:** Phase 0 test-characterization evidence candidates only. No live host, database, process, API, or service accessed. Gate 0 remains unestablished; Phase 1 remains unauthorized.

**Evidence anchors:** PR #448 / run 46173749707 / commit f4447ad5b243b97c91c28fc00abbef88fe7c51f9; PR #449 / run 46174148899 / commit 50c2e083de1dab3e40301b37dc14b614a0d08f23; main snapshot 18c8f06171e1de35c3210831a49b63d0e2487af0.


## §125 — Producer fingerprint tests pass exact-head CI (2026-11-28)

### PR #448 result

Producer-side characterization PR #448 was tested at exact head f4447ad5b243b97c91c28fc00abbef88fe7c51f9 against base main 18c8f06171e1de35c3210831a49b63d0e2487af0.

GitHub Actions run 46173749707 completed successfully on 2026-11-28:
- 3,081 passed;
- 7 skipped;
- 86 subtests passed;
- 0 known-intentional deselections;
- baseline gate: OK;
- mind-map verification: 30 nodes, 0 unverified, 12 dark, 2 blocked.

The workflow also completed the disposable test-image build and sandbox probe successfully. The mind-map verifier retained existing warnings: missing VIRTUE_SLATE.md and mental_factors_inventory_alobha_spec.txt doctrine references, and the overdue p13_finitude UNBLOCK marker dated 2026-11-21. These are recorded as verifier warnings, not new test failures or authorization to rearm any node.

### What this validates

It validates that the four new tests pass against the current GrooveSpotter implementation on this exact commit:
- unchanged per-instance n-gram, exact, template and centroid observations are suppressed;
- the tested fingerprint clears when that detector condition is absent;
- a fresh GrooveSpotter instance can emit again because its process-local fingerprint begins empty.

It does not prove live restart frequency, canonical semantic episode identity, persistence across processes, or correct downstream interpretation by Metacognition/Row 9. The test PR remains draft pending review; passing CI is not approval to merge or change runtime behaviour.

### Consumer test still pending

Separate draft PR #449 (head 50c2e083de1dab3e40301b37dc14b614a0d08f23) is testing the controlled-clock Metacognition replay/Row 9 renewal characterization. Run 46174148899 was still in progress at this snapshot, in the disposable image-build step; no result is claimed.

**Disposition:** producer-side test characterization is now test-verified on the exact PR #448 head; G-83 itself remains OPEN. No runtime code, schema, flags or cognitive behaviour changed. Gate 0 remains unestablished; Phase 1 remains unauthorized.

**Evidence anchors:** PR #448; exact head f4447ad5b243b97c91c28fc00abbef88fe7c51f9; run 46173749707; job 141067710930; full log; tests/test_groove_spotter_fingerprints.py; main base 18c8f06171e1de35c3210831a49b63d0e2487af0. Pending separate PR #449/run 46174148899.

**Evidence level:** exact-head full-suite CI test-verified; no production runtime observation.


## §126 — G-83 consumer replay verified; trace the repeated observation into chat prompt paths (28 November 2026)

**Question studied:** after one unacknowledged GrooveSpotter alert is repeatedly re-read, what actually reaches the chat prompt, what is persisted separately, and which downstream effects count the repeats?

**Evidence snapshot:** current code main at `18c8f06171e1de35c3210831a49b63d0e2487af0`; test-only PR #449 exact head `50c2e083de1dab3e40301b37dc14b614a0d08f23`. Static source trace plus exact-head isolated CI. No live host, process, database or feature-flag state was inspected.

### Exact-head consumer characterization result

PR #449 adds one controlled-clock test to `tests/test_metacognition.py`. Exact-head workflow **46174148899** completed successfully:

- 3,078 passed;
- 7 skipped;
- 86 subtests passed;
- baseline gate OK;
- disposable test sandbox probe OK;
- mind-map verifier: 30 nodes, 0 unverified, 12 dark, 2 blocked.

The test seeds one unacknowledged source alert, invokes `Metacognition.tick()` five times at controlled timestamps, and observes five derived groove events plus two 60-second stillness activations (at 1020 and 1081) from that same source row. This is test-verified current behaviour, not approval of its semantics and not a live-host frequency measurement. PR #449 remains a test-only characterization candidate; exact-head CI is not a merge or runtime-authority decision.

### Source-to-prompt trace

The repeated source row has more than one downstream path:

1. **Boot wiring:** `run.py` constructs Stage-SelfNarrative using the conversations Writer/Reader and passes that instance to `Metacognition(..., narrative=self_narrative)`.
2. **Chat-turn caller:** `gui/server.py` calls `state.metacognition.tick()` on the chat path, immediately calls `format_for_prompt()`, and appends any returned text to `belief_text`. This is request-driven, not evidence of an independent 60-second Metacognition worker.
3. **Repeated source read:** `Metacognition._detect_groove()` selects up to three rows with `acknowledged_at IS NULL` and `detected_at > now - 600`, newest first. It does not mark the source row acknowledged.
4. **Derived event write:** each selected row becomes a new `meta_cognition_events` row. `_write_event()` invalidates the recent-event cache; `tick()` refreshes it before returning.
5. **Generic prompt observation:** `format_for_prompt()` reads only the newest cached event. For event type `groove`, it returns the fixed sentence “Self-observation: I notice repeated patterns in my recent thinking.” It does not include the specific alert pattern.
6. **Pattern-specific narrative side path:** for each repeated event, `tick()` also calls `self_narrative.write_narrative()` with “I noticed I am repeatedly returning to {pattern}”, storing the source alert ID. Later in the same GUI route, the separate Stage-SelfNarrative formatter receives `current_topic=prompt[:100]` and performs a substring `LIKE` filter over narrative content. The alert-derived narrative is therefore conditionally eligible; its presence in `narrative_log` does not prove it is injected into every chat prompt.

This separates three things that must not be collapsed: repeated source observation, generic Metacognition prompt text, and topic-filtered pattern-specific narrative.

### Downstream effect classification

- **Row 9 stillness:** counts all `meta_cognition_events` rows of type `groove` in the preceding 1,800 seconds. Three events trigger a 60-second `stillness_log` hold. If the hold expires while repeated source reads continue, a later chat tick can renew it. PR #449 verifies this in an isolated fixture.
- **Fountain crystallization:** the FountainCrystallizer reads the active stillness window and returns a HOLD before writing a belief. This is a crystallization hold, not proof that thought generation, the speech queue, or all other output paths are paused (see §§114–119).
- **CompetingDrives and Recent STRIKING:** these inspected consumers read the original `groove_alerts` table directly (severity and pattern respectively), not the derived repeated `meta_cognition_events` count. Do not multiply their effects by the number of Metacognition re-reads. Their distinct prompt/drive effects remain as classified in §120.
- **Recent self-observation slots:** the default recent-event query selects the three newest unresolved rows. Repeated groove events can therefore occupy multiple recent slots when they are the newest events; the formatter still emits one generic line based on the top row.

### Interpretation and next bounded trace

The feedback is **chat-turn-triggered repetition**, not an established autonomous exponential loop. One unchanged source row can be counted again on successive chat requests while it remains unacknowledged and inside the ten-minute lookback. Those repeats can renew Row 9 and populate recent self-observation history. The exact host request cadence, alert population, and prompt exposure remain UNKNOWN.

The next safe characterization is a separate fixture-level test of the complete prompt boundary: pass the real Stage-SelfNarrative instance into Metacognition; assert repeated pattern-specific narrative rows; compare matching and non-matching `current_topic` filters; assert the generic Metacognition line independently; and verify whether repeated groove rows displace an older independent event from the three-row recent window. Do not change acknowledgement semantics, episode identity, Row 9 threshold/duration, prompt policy or feature flags in that test.

**Disposition:** G-83 consumer replay is now exact-head test-verified. The prompt/narrative consequences above are source-observed; the additional combined formatter/caller test remains a candidate. G-83 remains OPEN pending an explicit semantic decision about source-alert acknowledgement and the unit counted as one groove episode. Documentation and test characterization only; no runtime source, schema, flags, cognitive behaviour, frozen S-01–S-25/M1.8, Master Roadmap, Phase 0/Gate 0 or action authority changed. No live host, database, process or service accessed.

**Source anchors:** `run.py` blob `8ebe33c251e874b16107428eb4e92cf6301a4621`; `gui/server.py` blob `ecaa6982544e883a50dbf85c5de1e10f74180c67`; `theory_x/stage9_metacognition/metacognition.py` blob `de853bd93a11dcfe39ee8afa30a84e5c7b1f8b08`; `theory_x/stage_self_narrative/self_narrative.py` blob `15d8c1dd1de8332b3d12e06a096aac2c0b2b2cb3`; `theory_x/stage6_fountain/crystallizer.py` blob `c0a5cf1388825e7fc9438cf1188aedd8e2ed8959`; PR #449 exact head `50c2e083de1dab3e40301b37dc14b614a0d08f23`; workflow 46174148899, job 141068939254.

**Evidence level:** source-observed caller/reader/writer/prompt paths; exact-head full-suite CI test-verified for repeated source-row re-consumption and Row 9 renewal; combined narrative/prompt exposure remains untested; production runtime observation remains absent.


## §127 — G-83 prompt assembly and LLM-entry boundary (28 November 2026)

**Question studied:** after Metacognition and Stage-SelfNarrative format a repeated groove observation, does that text necessarily reach the language model, or can the chat route return before prompt assembly?

**Evidence snapshot:** source files on main snapshot `18c8f06171e1de35c3210831a49b63d0e2487af0`; test candidate PR #449 head `8132db2a338727e580e3269ad148277db727b0d4`. Static caller/branch trace. Exact-head CI for the new combined fixture is in progress at workflow `46174972385`; do not claim a test result until the run completes.

### The actual prompt route

The inspected `gui/server.py` chat handler establishes this order:

1. Metacognition is ticked. Its generic `format_for_prompt()` text, when non-empty, is appended to `belief_text`.
2. Stage-SelfNarrative receives `SimpleNamespace(current_topic=prompt[:100])`. Its topic-filtered result, when non-empty, is also appended to `belief_text`.
3. Other faculty, tool, workspace and context blocks are assembled later.
4. The route computes `belief_count = belief_text.count("- [Tier")`. This counts tier-tagged belief lines, not arbitrary reflective text.
5. Unless the request is a probe, social query, or uses a register in `_ALLOW_THIN_REGISTERS`, a count below `CHAT_GAP_MIN_BELIEFS` causes a persisted gap-refusal response and an immediate return. No voice prompt is assembled and `state.voice.speak()` is not called on that path.
6. On the surviving path, the reflective text remains part of `belief_text`; the route later embeds the complete belief text under `Your interior right now:` in `voice_prompt`, records a `chat_prompt_ready` trace when tracing is enabled, then calls `state.voice.speak(VoiceRequest(prompt=voice_prompt, register=register), ...)`.

### Consequence

A reflective observation being appended to `belief_text` is **not sufficient evidence that the LLM receives it**. It is eligible for prompt inclusion only on requests that pass the separate thin-belief gap gate. Since the Metacognition and narrative strings do not themselves contain the `- [Tier` marker, they do not increase the measured `belief_count`. They cannot, by themselves, rescue a request that otherwise falls below the gate.

The gate is a chat-reply availability rule, not a cognitive authority or action veto. Do not conflate it with the Tibetan mind map or Mind Aspects; this trace concerns only the existing chat route's thin-belief response branch. No proposal is made to bypass, weaken or modify the gate.

### Next bounded question

The next test should characterize the route-level distinction without changing policy: under a fixture with insufficient tiered beliefs, prove the generic/narrative strings can be computed but the route returns the gap response before voice invocation; under a permitted thin-belief case (e.g. a register explicitly in `_ALLOW_THIN_REGISTERS`), prove the same strings appear in the exact `VoiceRequest.prompt`. Use mocks and isolated databases; no live host, model, flag or service. This is a candidate for a dedicated GUI route test, not a reason to widen the existing Metacognition unit test.

**Disposition:** source-observed prompt assembly and early-return boundary. The combined formatter fixture is awaiting exact-head CI. Route-level inclusion/exclusion remains untested. Production prompt-log observation remains UNKNOWN. G-83 remains OPEN; no source-alert acknowledgement, episode identity, Row 9 threshold/duration, prompt policy, flags, runtime code, schema, frozen S-01–S-25/M1.8, Master Roadmap, Gate 0 or action authority changed.

**Source anchors:** `gui/server.py` blob `ecaa6982544e883a50dbf85c5de1e10f74180c67`; `theory_x/stage9_metacognition/metacognition.py` blob `de853bd93a11dcfe39ee8afa30a84e5c7b1f8b08`; `theory_x/stage_self_narrative/self_narrative.py` blob `15d8c1dd1de8332b3d12e06a096aac2c0b2b2cb3`; PR #449 candidate head `8132db2a338727e580e3269ad148277db727b0d4`; workflow `46174972385`.

**Evidence level:** source-observed branch/caller/prompt composition; combined unit-level formatter test pending CI; GUI route behaviour statically traced but not route-test-verified; no runtime observation.


### Voice transport boundary refinement

The final source edge is now inspected too. `VoiceClient.speak()` calls `build_system_prompt()`, then constructs the request payload with two messages: the generated system prompt and a user message whose `content` is exactly `req.prompt`. It passes that payload to `_request_fn(self.url, payload)`. Therefore, on a route that reaches `state.voice.speak()`, the assembled `voice_prompt` is handed to the model transport as the user-message content without an additional rewrite in `VoiceClient.speak()`. The separate `belief_count` argument is recorded in response deflection metadata; it does not add or remove prompt text in this method.

This closes the static source chain from `belief_text` → `voice_prompt` → `VoiceRequest.prompt` → transport payload. It still does not prove the remote/local model server accepted the request, that a particular backend was active, or that the generated reply semantically used the reflective material. Those require runtime/request-level evidence. Source anchor: `voice/llm.py` blob `a41e04db8569393dc2ae2ebe622cf1e67ae3de66`.


### Route-level G-83 characterization candidate

A separate draft test PR #450 now exercises the real `/api/chat` route with isolated SQLite and a mocked VoiceClient transport. It seeds one groove alert and installs the real Metacognition and Stage-SelfNarrative instances. The test uses Technical with a deterministically raised threshold to assert the gap-refusal early return occurs before voice transport, then Philosophical to assert both the generic self-observation and topic-matched pattern narrative appear in the exact transport user-message content. Exact head: `b33022cfaf47cc34dc8eec316cd583c15e6d880e`; workflow `46175227754` is pending/in progress. This would test route-to-transport string delivery, not real model-provider acceptance or semantic use. PR #450 is test-only and remains draft; no runtime or policy change.


## §128 — G-83 upstream provenance: Fountain output → GrooveSpotter → two distinct feedback controls (28 November 2026)

**Question studied:** what information creates the source alert that Metacognition later re-reads, and does the producer itself suppress unchanged alerts?

**Evidence snapshot:** source files on main at `18c8f06171e1de35c3210831a49b63d0e2487af0`. Static trace through Fountain generator, crystallizer, DiversityLoop, GrooveSpotter and crystallizer cooldown reader. No live host, DB or runtime observation.

### Upstream source provenance

- `FountainGenerator` calls `FountainCrystallizer.crystallize(thought=..., ...)` for a generated thought when the crystallizer is present and the fire is not burst-suppressed.
- `FountainCrystallizer` writes surviving thoughts into `beliefs` as Tier 6 rows. The source/category is the active mode's `crystallization_category`, defaulting to `fountain_insight`.
- `DiversityLoop` constructs `GrooveSpotter` over the beliefs Writer/Reader, invokes `detect_all()`, then runs dormancy and clock work, and waits 60 seconds before the next pass.
- `GrooveSpotter.detect_all()` reads only the latest `WINDOW_SIZE * 2` beliefs whose source is `fountain_insight` or `synergized`; it takes the newest `WINDOW_SIZE=20` as the active detection window. It does not query the chat `messages` table or direct user prompt.
- N-gram repetition uses `NGRAM_REPEAT_THRESHOLD=3`: the top trigram must occur at least three times across the window. An unchanged top pattern matching the in-memory `_last_ngram_pattern` is not emitted again. If the condition drops below threshold or the window has no trigrams, that fingerprint is cleared. The in-memory fingerprint resets on process restart, so one re-emission after restart is possible by design.
- The emitted alert stores its pattern and sampled belief IDs in `groove_alerts`. This is an alert derived from NEX's own Fountain/Synergized substrate records, not a direct re-read of the user's last sentence.

### Two different downstream feedback controls

**Producer-side targeted cooldown:** for an n-gram alert with severity at least 0.5, GrooveSpotter calls `_push_cooldown()`. With the current n-gram severity floor of 0.5, this normally writes a meaningful pattern fragment into `signal_cooldown` with a two-hour expiry. The FountainCrystallizer later reads unexpired cooldown rows and rejects a candidate thought if a normalized stored fragment occurs within that thought. This is a content-specific future-crystallization filter.

**Consumer-side Row 9 stillness:** separately, Metacognition reads the unacknowledged `groove_alerts` row on chat ticks and re-emits derived `groove` events. Those derived events can accumulate into Row 9's 60-second stillness hold, which is global to crystallization while active. The consumer replay does not require GrooveSpotter to emit a new alert each time.

These controls must not be collapsed. One is a producer-side, pattern-specific two-hour cooldown; the other is a consumer-side, event-count-driven global crystallization hold. Both may originate from the same GrooveSpotter alert, but their data, timing, scope and triggering paths differ.

### Architectural interpretation

This is a real recurrent substrate feedback path at source level:

`Fountain thought → crystallized belief → GrooveSpotter pattern detection → groove alert → targeted cooldown + Metacognition observation → (when the chat route passes its gate) reflective prompt context → next language-model generation`.

It is not an established autonomous exponential loop. GrooveSpotter's producer scan is 60-second periodic; Metacognition's consumer read is chat-turn-triggered. The alert producer has an in-memory unchanged-pattern fingerprint, while the consumer does not acknowledge the source row in the inspected path. Runtime rates and the actual effect of prompt text on subsequent model output remain UNKNOWN.

### Next bounded investigation

Trace the other GrooveSpotter alert types (exact repetition, template repetition and centroid tightening) through their fingerprints, cooldown writes and consumer formatting; verify which have a pattern string that can actually be topic-matched into Stage-SelfNarrative. Then compare the alert's `sample_belief_ids` with the beliefs actually selected by the subsequent Fountain fire. Do not alter alert acknowledgement, thresholds, fingerprints, cooldown duration, stillness semantics or prompt policy before the controlling authority and full consumer effects are established.

**Disposition:** source-observed producer/consumer loop; upstream source set and producer-side fingerprint are source-verified; targeted cooldown and global Row 9 hold are separate source-verified effects. Exact-head tests for consumer replay and prompt boundary are pending CI in PRs #449 and #450. No live runtime observation. G-83 remains OPEN; no runtime source, schema, flags, frozen S-01–S-25/M1.8, Master Roadmap, Phase 0/Gate 0 or action authority changed.

**Source anchors:** `theory_x/stage6_fountain/generator.py` blob `26061914b1dd80858c3568217cd1ef0c49ce2c51`; `theory_x/stage6_fountain/crystallizer.py` blob `c0a5cf1388825e7fc9438cf1188aedd8e2ed8959`; `theory_x/diversity/loop.py` blob `186a1979283394a53154b609855b80f1fcfe0247`; `theory_x/diversity/groove.py` blob `1174b9001c7ffc876cec78ae677cb664481ad04e`; Metacognition source in §126; GUI/voice boundary in §127.

**Evidence level:** source-observed generator/crystallizer/producer/consumer paths; exact-head CI pending for the consumer and route tests; no production runtime observation or semantic model-effect evidence.


### §128 audit note — exact-repetition threshold remains ambiguous

One small producer detail is not yet closed: `groove.py` defines `EXACT_REPEAT_MIN = 2`, and `_detect_exact_repetition()` uses that constant, but the method docstring says the same sentence must appear at least three times. The current PR #448 fingerprint test uses three repeated rows, so it proves fingerprint behaviour but does not discriminate between a threshold of two and three. The inspected `tests/test_diversity.py` contains no explicit exact-repeat threshold assertion. Treat the implemented threshold as two for source-trace purposes, but leave the intended threshold UNKNOWN; do not change it or encode it as a normative requirement without locating the decision/history. This is a documentation/test-coverage discrepancy, not yet a new verified defect ID.
