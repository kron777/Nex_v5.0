# NEX Phase 0 — Open Problem and Goal Lifecycle Crosswalk (25 November 2026)

## Scope and evidence boundary

Static-source trace against active host source baseline `de93134f34adac07a3a41c2a05b33720510a2bfc`. This increment follows the prediction/surprise trace and maps the `open_problems` and `goals` records across their producers, state transitions, and inspected consumers.

No live rows, problem population, user-facing GUI state, or current process state was inspected. No problem/goal was created, updated, closed or re-opened. No runtime/code/test/flag/DB state was changed.

## 1. Two separate records with different semantics

The schema creates both tables in `conversations.db`:

- `open_problems`: working questions/unknowns, default state `open`, with description, plan, observations, timestamps and tags. Current code uses `open`, `stuck` and `closed`.
- `goals`: directional commitments, default state `open`, with priority, source, optional `problem_id`, timestamps and state. GoalManager transitions to `completed` or `cancelled`.

GoalManager's module documentation explicitly distinguishes a problem (“I don't know X”) from a goal (“I am working toward Y”). The tables are not interchangeable, and a `problem_id` link does not automatically synchronize their states.

## 2. open_problems producers and state transitions

### Producers

1. **ProblemMemory.open()** — GUI `POST /api/problems` uses the shared conversations Writer. It derives tags from title + description via Tag Protocol and inserts a new `open` row. It can also emit a SelfNarrative event.
2. **SignalToProblem** — normal Stage 2 loop reads eligible high-confidence `signals`, applies a daily cap, duplicate/quality filters and inserts directly into `open_problems`. It writes source-style tags `["auto", "signal:<type>"]`, not content-derived Tag Protocol tags (already recorded in G-29). It separately marks the source signal actioned.
3. **GUI review unflag** — `POST /api/review/<id>/unflag` reinserts a review_queue row into `open_problems` with its original ID and state `open`, then deletes the review_queue row. Automatic promotion into review_queue is intentionally disabled in CounterfactualNode; this is an operator/manual restoration route.
4. **Other paths** — no additional normal runtime `INSERT INTO open_problems` producer was found in the inspected source set. FocusLoop and ProblemMemory primarily update existing rows.

### State transitions

- ProblemMemory.close() sets `state='closed'`, stamps `resolved_at` and `last_touched_at`.
- ProblemMemory.decay() would close stale `open` rows after 30 days, but this method is not scheduled in the inspected normal startup path (see §6).
- FocusLoop._surface_to_chat() sets the selected problem to `stuck` after writing an internal NEX message asking for help. It does not close the problem.
- Optional Fountain RECONCILE write-back can append observations and, behind `NEX5_ABSTAIN_CLOSE=1` or `NEX5_COMMIT_CLOSE=1`, close the targeted problem once its observation count is at least ten and the relevant output predicate passes.
- Review unflag restores an existing review_queue item to `open`; the automatic CounterfactualNode promotion path returns immediately and is intentionally disabled.

## 3. Problem consumers differ by state filter

| Consumer | Selection | Consequence |
|---|---|---|
| Chat ProblemMemory match | `ProblemMemory.list_open()`, state exactly `open`, then ≥2 content-word overlap | Matching open problem text can be appended to Chat prompt |
| GUI `GET /api/problems` | `list_open()`, state exactly `open` | Stuck and closed problems are absent from the list response |
| GUI `GET /api/problems/<id>` | direct ID lookup, no state filter | A known stuck/closed ID can still be fetched |
| FocusLoop | state exactly `open` | Chooses the most belief-connected open problem; stuck/closed rows are not selected |
| CounterfactualNode | state exactly `open`, oldest touched first | Only open problems drive counterfactual refinement |
| DailyLife | counts and summarizes state exactly `open` | Stuck/closed rows are not included in its open-problem count |
| CoherenceGate | state exactly `open`, most recently touched | Up to five open problem titles enter the Gate context |
| PredictiveSubstrate | state exactly `open` | Open problem titles contribute to the internal prediction centroid |
| CompetingDrives | state exactly `open` | Open-problem count contributes to problem pressure |
| SelfMindView | state exactly `open` | Open-problem count and latest title enter the self snapshot |
| Fountain RECONCILE | states `open` and `stuck` | Up to eight older-touched problems can be paired for optional reconciliation |
| Fountain problem injection | all states, by design | `select_for_injection()` considers recent real questions regardless of state, including `stuck` and `closed`; it applies a 14-day lookback, per-problem eight-hour cooldown and minimum pool of three |

### Stuck-state boundary

FocusLoop's `_surface_to_chat()` changes a problem from `open` to `stuck`. That immediately removes it from the open-only consumers above: GUI list, Chat matching, FocusLoop, CounterfactualNode, DailyLife, CoherenceGate, PredictiveSubstrate, CompetingDrives and SelfMindView. It remains eligible for Fountain's explicit all-state problem-injection selection and the RECONCILE pool. The GUI has no dedicated stuck-problem list endpoint in the inspected routes, although a known ID can still be fetched.

This may be intentional: “stuck” can mean stop automatic work and surface the issue to the user. It is nevertheless a distinct visibility/consumer contract, not equivalent to “still open.” No live stuck-row inventory was read.

## 4. Goal lifecycle and consumer mismatch

### GoalManager writes `open`, not `active`

- `GoalManager.open()` inserts goals with `state='open'`.
- `list_open()` and `get_active()` select `state='open'`, with `get_active()` returning the highest-priority open goal.
- `complete()` sets `completed`; `cancel()` and `decay()` set `cancelled`.
- The GUI `POST /api/goals` calls GoalManager.open(); it defaults priority to 0.5 and source to `user`.

### CoherenceGate reads a different state

`CoherenceGate._load_context()` queries:

`SELECT id, title FROM goals WHERE state='active' ORDER BY priority DESC LIMIT 5`

No `GoalManager` method in the inspected implementation creates or transitions a row to `active`; the schema default and normal API path use `open`. The Gate unit-test helper seeds a goal directly with `state='active'`, so the test fixtures exercise the Gate's expected state without proving that a normal GoalManager-created goal reaches that query.

Therefore a goal created through the normal GoalManager/API path is not selected by this Gate context query. This is a source-level producer/consumer state-vocabulary mismatch. No live goals were read, and no conclusion is made about whether legacy rows with state `active` exist.

### Other goal consumers

- Chat calls `GoalManager.get_active()` but only writes the selected ID/title to a diagnostic log. The prior Chat “Current goal / Working on” prompt block was explicitly removed (SEAM 3).
- The Fountain startup wiring receives ProblemMemory but not GoalManager; its task/problem injection path is based on open_problems.
- The inspected PredictiveSubstrate, SelfMindView and CompetingDrives paths read open_problems/drives, not goals.
- The normal startup path therefore constructs/registers GoalManager and exposes GUI CRUD, but the only inspected cognitive consumer is CoherenceGate—and its state predicate does not match GoalManager's normal writes.

The GoalManager module docstring and `get_active()` docstring still describe belief_text injection. Current Chat source explicitly removes that injection. Treat this as stale module documentation, not evidence that a goal is presently in the prompt.

## 5. Goal and problem SentienceNode lifecycle is not an autonomous scheduler

- `ProblemMemory` and `GoalManager` expose `tick()` and `decay()` methods. Their `tick()` methods only refresh an in-memory list cache; their `decay()` methods would close stale problems after 30 days and cancel stale goals after 60 days.
- Both are constructed in normal startup and registered in the process-lifetime Theory X registry (ProblemMemory in GUI AppState construction; GoalManager in run.py / AppState wiring).
- `theory_x/__init__.py` implements `register()` and `all_nodes()`; the registry is a list, with no tick/decay scheduler.
- The inspected `run.py` and `gui/server.py` paths do not iterate `all_nodes()`, call `ProblemMemory.tick/decay()`, or call `GoalManager.tick/decay()`. Other nodes (e.g. Metacognition and BehaviouralSelfModel) are called explicitly from Chat, but these two are not.
- Their CRUD and list methods are called by Chat/GUI and other consumers; the stale-close/cancel methods are only exercised directly in unit tests in the inspected source set.

Consequently the 30-day ProblemMemory auto-close and 60-day GoalManager auto-cancel behaviours are callable methods, not active scheduled lifecycle rules in the inspected normal boot path. This is a source-wiring finding; another entry point or operator invocation could still call them.

## 6. Tests and evidence boundaries

- `tests/test_problem_memory.py` covers CRUD, matching, manual `decay()` and list behavior; it does not test a boot scheduler invoking decay.
- `tests/test_goal_manager.py` covers CRUD, priority, manual `decay()` and list behavior; it does not test that normal API-created `open` goals are visible to CoherenceGate.
- `tests/test_coherence_gate.py` seeds a goal directly with state `active`; it does not use GoalManager.open() as an integration fixture.
- The reviewed routes do not expose a dedicated stuck-problem list endpoint or a GoalManager-to-CoherenceGate integration endpoint.
- No live data, status counts, or state transition frequency was inspected.

## 7. Phase 0 disposition

### Confirmed source facts

- Problem and goal records are separate; ProblemMemory/SignalToProblem/review-unflag create or restore problems through distinct paths.
- FocusLoop changes selected problems to `stuck`; most normal consumers select only `open`, while Fountain problem injection intentionally includes any state.
- GoalManager creates `open` goals, while CoherenceGate reads only `active` goals. The Gate test seeds `active` directly, so it does not cover the normal producer path.
- GoalManager is diagnostic-only in Chat after the prompt injection was removed; Fountain receives ProblemMemory, not GoalManager.
- ProblemMemory/GoalManager decay methods are not scheduled in the inspected normal boot path; the Theory X registry does not itself orchestrate tick/decay.

### Unverified / authority-dependent

- Whether `stuck` is intended as a hidden-from-open-lists state, a user-review state, or a separate first-class problem status.
- Whether Gate should consume `open` goals, whether `active` is a separate lifecycle state, or whether GoalManager's state vocabulary is stale.
- Whether stale close/cancel methods are intended to be manually invoked, called by an omitted orchestration layer, or should be scheduled.
- Whether the removal of Chat goal injection is intended to leave goals primarily as UI/diagnostic state.
- Live distribution of open/stuck/closed problems and open/completed/cancelled/active goals.

### Boundary

No state vocabulary, prompt injection, decay scheduling, review promotion, problem lifecycle, or Gate query was changed. Do not alter any of these until the governing Frozen V2.1 / roadmap authority and Gate 0 decision are recovered or explicitly re-established.
