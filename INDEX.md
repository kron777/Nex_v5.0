# NEX 5.0 — INDEX / DEVELOPMENT MANUAL

**Last verified against:** `main` at `99ae476e198ec438d3f2c065316ebcb6ff6ebac6`  
**Evidence date:** 27 November 2026  
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

The 27 November mainline includes the merged one-pen migrations for daily-life scheduled activity and canary persistence (#168), affinity (#169), learning-guard subtraction (#180), and Expectations persistence/reconciliation transaction support (#183). Important distinction: the shared-Writer migration does **not** establish that the Expectations reconciler is activated. The tracked launcher sets `NEX5_RECONCILER=1` and `NEX5_EXPECT_LEARN=1`, but the audited `run.py` has no Expectations/reconcile invocation, and `daily_life.py` imports only `record_canaries`; do not infer a live reconciliation loop from those flags. No activation is authorised by this documentation. PR #184 also fixes tied-timestamp pagination for Warrant lineage/arc reads; it does not broaden use-day eligibility or change Warrant policy. Several one-pen migrations remain open at this update: Fountain/momentum (#162), identity (#166), resumption (#170), and Moltbook responder/listener/poster (#171–#173). Check exact PR state and head CI before relying on further changes.

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

Moltbook components are separate listener, responder and poster pathways. Their one-pen migration PRs (#171–#173) remain open at this update. The tracked launcher has been reported with `MOLTBOOK_DRY_RUN=1`, but only host environment and runtime logs can establish actual deployment state. Never infer live posting or interaction from source presence.

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

---

## 11. Current mainline snapshot and open work (27 November 2026)

Mainline inspected: `c6bc4e411141497f9e25540178e771a08cbab79d` (27 November 2026, after the manual and mind-map source-verification merges). The earlier `99ae476e` mainline GitHub Actions pytest check completed successfully at 09:40:22 UTC; PR #185 subsequently passed the exact-head full baseline and verifier. These are repository CI/source-verification results only; they do not establish host/runtime state.

Post-snapshot reconciliation recorded in the Phase 0 handoff branch identifies the following merged changes already present in that mainline SHA: #168 (DailyLife/canary Writer routing), #169 (affinity Writer routing), #174 (P13 finitude re-verification), #175 (full-history mind-map verifier guard), #180 (learning-guard Writer routing), #183 (Expectations transaction/Writers), and #184 (Warrant composite pagination cursors). The source reality report and crosswalk in PR #186 are pinned to `ae406fa8`, not `99ae476`; use the handoff's post-snapshot follow-up for the intervening changes and do not present the older crosswalk as a fully refreshed `99ae476` audit.

Relevant open pull requests at the inspection point:

- **#187** — the INDEX/manual stocktake update; merged as `f6e51f8ff6eb191438372a0ae1e6fff52b7b33a3` after exact-head CI passed.
- **#185** — consolidated mind-map source re-verification after G64/G65 and valence review; merged as `c6bc4e411141497f9e25540178e771a08cbab79d` after exact-head CI passed (2,527 passed, 7 skipped, 40 subtests; verifier: 30 nodes, 0 unverified, 14 dark, 2 blocked). The two missing doctrine references and overdue P13 marker remain.
- **#188** — Phase 0 evidence-pack carry-forward onto current main, with five documentation artefacts. Its report/crosswalk remain pinned to `ae406fa8`; the handoff reconciles through `99ae476`. Exact-head CI is still running at this manual revision; it does not approve Gate 0.
- **#186** — older Phase 0 evidence-pack PR, superseded for current-main integration by #188; do not merge the stale branch.
- **#178** — episodic read/write boundary audit; retained as a narrower backup pending #185.
- **#171** — responder one-pen migration; corrected constructor injection and its exact-head full CI passed, but the branch is still based on `ae406fa8` and diverges from current main. Reconcile/rebase and re-test before merge.
- **#162, #166, #170, #172, #173** — remaining one-pen migrations for Fountain, identity, resumption and Moltbook listener/poster; earlier CI passes are on old heads and do not establish current-main compatibility.

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

*Last amended: 27 November 2026 — mainline stocktake and exact-head mind-map verifier reconciliation. Replaces stale May 2026 architecture, port, database-count, subsystem-status and operational claims with evidence-qualified current guidance.*
