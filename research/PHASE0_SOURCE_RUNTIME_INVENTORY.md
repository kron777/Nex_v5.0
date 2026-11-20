# NEX Phase 0 — Source-to-Runtime Inventory (Static Pass)

**Status:** Static repository audit, 2026-11-20. Not a live-machine or runtime verification.
**Branch:** `research/emergent-organisation-framework`
**Purpose:** identify what the current source says is constructed, connected, gated, or explicitly not wired, before proposing instrumentation or changing behaviour.

## Plain-language conclusion

NEX has substantial cognitive machinery and several real connections between subsystems. However, the repository does not justify treating all of that machinery as one continuously integrated process. Some components are active in particular paths; others are optional, dark by default, manually callable, or only visible through read-only GUI endpoints.

The biggest research gap is therefore not simply “build more faculties.” It is to establish, with a reproducible runtime trace, which existing state changes actually reach later processing and influence subsequent behaviour.

This pass is static. It cannot establish which flags are set on the user's machine, which processes are currently running, whether local databases contain rows, or whether a deployed copy matches GitHub.

## Evidence rules

- **Source-confirmed:** the inspected source contains the implementation or call path described.
- **Document-reported:** a project document reports a test or runtime result; the result was not rerun in this audit.
- **Not established:** source inspection alone cannot establish live operation, frequency, or behavioural effect.
- **Explicitly unconnected/dark:** the source or project documentation says the mechanism is not wired into the live loop or is disabled by default.

## Inventory

| Area | What source establishes | What remains unknown |
|---|---|---|
| Boot and orchestration | `run.py` initialises the databases and constructs sensing, dynamic formation, world model, membrane, fountain, metacognition and related services. | Which services are healthy in the current local deployment; whether every constructed service is actually consumed downstream. |
| Working memory | `theory_x/working_memory.py` describes a seven-item buffer with exponential decay and a five-minute half-life, integrated through the GUI chat path. | Current live contents, refresh/eviction rates, and whether those contents reliably alter later decisions. The module's own documentation describes it as short-term, not restart-persistent. |
| Self-binding | `theory_x/stage_tom/self_binding.py` reads several subsystem signals, composes a single synthesis, writes the current `self_state` row and attempts to append `self_state_history`. | Whether the local runtime invokes `bind()` at the expected cadence; history-write failures are caught and ignored in this source, so successful history accumulation must be verified from data/tests. The synthesis is a functional summary, not evidence of a felt self. |
| Global workspace | `global_workspace.py` contains a competitive arbitration path and a separate budgeted selector for multiple candidate blocks. The project documents the fire path as using arbitration. | Exact current call coverage across fire and chat paths, live candidate distributions, and whether the selected framing changes downstream outcomes. A helper existing does not establish that every path calls it. |
| Episodic memory | `theory_x/memory/episodic.py` defines event-to-episode recording and reconstructive retrieval. Its module documentation says it is not wired into the live loop and is dark unless `NEX5_EPISODIC=1`; recording is callable by hand or a future scheduler. | Whether any local manual runs occurred, whether the feature flag is set locally, and whether episodes exist in the deployed database. |
| Episodic GUI visibility | `gui/server.py` exposes a GET endpoint for listing episodes. The code comments describe this as read-only HUD visibility. | Whether the endpoint is used and whether it reflects current runtime data. A read endpoint is not a memory-production pathway. |
| Held tensions | The GUI exposes a read-only endpoint for held tensions; source comments describe the mechanism as flag-gated. | Whether the mechanism has been armed in a controlled test and whether held tensions affect later retrieval or decisions. |
| Metacognition | `run.py` constructs a metacognition service; the project documents event production and a proposed digest stage. | Whether observations are consolidated into a durable second-order state and whether that state influences later processing. |
| Chat-path integration | `SENTIENCE_PROGRAM.md` describes the chat path as concatenating many context blocks and proposes a bounded arbiter as Phase A. | The exact current block inventory and actual production call graph need a dedicated trace/test before any arbitration change. |
| Experimental controls | `DESIGN_MINDEDNESS.md` records prior cases where enabling mechanisms caused repetition or meta-narration, and requires one falsifiable loop at a time. | The latest local runtime flag values and whether current deployment matches the audited source revision. |

## Important discrepancy in the development plan

The repository's `SENTIENCE_PROGRAM.md` says Phase A — a bounded chat-path attention arbiter — is the next implementation phase. The new Emergent Organisation Framework instead says the first step is a reviewed source-to-runtime inventory, followed by read-only baseline instrumentation.

These are not necessarily incompatible, but they are different immediate priorities. The inventory should be completed first so the project does not implement a new control pathway before it knows which existing pathways are live and measurable.

**Recommendation:** treat Phase 0 as the immediate gate. Do not implement the chat arbiter, activate dark faculties, or add a new logger until the inventory is reconciled with current runtime evidence and the user approves the next change.

## What can be measured without changing NEX

Start with existing artefacts, not new instrumentation:

1. Read-only snapshots of process identity, code revision, environment flag names/values (redacting secrets), and database file locations.
2. Existing logs and event tables, including timestamps and counts by source.
3. Existing test reports, clearly labelled as test results rather than live-runtime evidence.
4. Existing read-only GUI/API endpoints, where available.
5. Offline analysis scripts that read copies or read-only database connections and write reports outside NEX's cognitive databases.

Do not assume every proposed signal is available. Mark missing signals as missing instead of adding a new write path to manufacture them.

## Minimum runtime verification needed to close Phase 0

On the actual NEX machine, collect a timestamped, read-only snapshot containing:

- Git commit and working-tree status for the deployed directory.
- Running NEX process and parent/supervisor relationship.
- Effective NEX5 flag names and values, with credentials and secret values removed.
- Resolved database paths and file metadata; no schema migrations or writes.
- Counts and timestamp ranges for existing history/event tables.
- A small trace showing whether key producers are invoked and whether their outputs are consumed downstream.

The trace should cover, at minimum, self-binding/history, working memory, workspace arbitration, metacognition events, and episodic recording. If the live machine cannot provide a call trace without code changes, document that gap and request a separately reviewed passive instrumentation plan.

## Exit decision

**Phase 0 is not yet complete.** The source audit identifies the likely pathways and several known disconnections, but local runtime state has not been inspected in this pass.

The next defensible action is to compare this inventory with a read-only snapshot from the user's running installation. Only after that should NEX receive a new measurement component or a behavioural change.

## Bottom line

NEX is more than a collection of isolated ideas: it has persistent databases, recurring processes, self-state binding, attention mechanisms, memory systems and model interfaces. But the evidence currently available here does not establish that these form one fully integrated, continuously self-organising cognitive loop.

That is not a failure. It tells us exactly what the next experiment must answer: **what is actually connected in the running system, and what consequences do those connections have over time?**
