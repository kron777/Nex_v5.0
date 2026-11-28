# run.py background-worker ownership census — 28 November 2026

**Source base:** `main` at `93f39f8eb12a24ce703e6cc76c4e4c1d4be71872`.  
**Files inspected:** `run.py` and `gui/server.py`.  
**Scope:** map the application boot path's explicitly started workers to the AppState shutdown registry. This is not a repository-wide thread census or a host observation.

## 1. Explicit run.py worker starts and shutdown owners

The following direct start sites were matched to the AppState field and `_quiesce_producers()` entry:

| run.py worker | AppState owner | Shutdown action |
|---|---|---|
| `_resolver.start_loop()` | `resolver` | `stop_loop()`, join `_thread` |
| `novel_association.start_loop()` | `novel_association` | `stop()`, join `_thread` |
| `_throw_net_monitor.start_loop()` (flag-gated) | `throw_net_monitor` | `stop()`, join `_thread` |
| `_substrate_harmonic.start_loop()` | `substrate_harmonic` | `stop_loop()`, join `_thread` |
| `_genius_tagger.start_loop()` | `genius_tagger` | `stop_loop()`, join `_thread` |
| `_counterfactual_node.start_loop()` | `counterfactual_node` | `stop()`, join `_thread` |
| `_drive_emergence.start_loop()` | `drive_emergence` | `stop()`, join `_thread` |
| `_warrant_recorder.start_loop()` (flag-gated) | `warrant_recorder` | `stop()`, join `_thread` |
| `_competing_drives.start_loop()` | `competing_drives` | `stop()`, join `_thread` |
| `_affect_state.start_loop()` | `affect_state` | `stop()`, join `_thread` |
| `_predictive_substrate.start_loop()` | `predictive_substrate` | `stop()`, join `_thread` |
| `_persona_responder.start_loop()` (flag-gated) | `persona_responder` | `stop()`, join `_thread` |
| `_self_mind_view.start_loop()` | `self_mind_view` | `stop()`, join `_thread` |
| `_world_pred_loop.start_loop()` (flag-gated) | `world_pred_loop` | `stop()`, join `_thread` |
| `_self_pred_loop.start_loop()` (flag-gated) | `self_pred_loop` | `stop()`, join `_thread` |
| `_self_maintain_shadow.start_loop()` (flag-gated) | `self_maintain_shadow` | `stop()`, join `_thread` |
| `speech_consumer.start()` | `speech_consumer` | `stop()`, join the Thread object |
| `diversity_loop.start()` | `diversity_loop` | `stop()`, join `_thread` |
| `edge_generator_loop.start()` | `edge_generator_loop` | `stop()`, join `_thread` |
| explicit `decoder_loop` Thread | `decoder_loop` (attached after AppState construction) | set stop Event, join `_thread` |

Flag-gated starts are only constructed when their corresponding environment switch is enabled. This table maps source-level ownership; it does not assert which optional workers are active on the deployed host.

## 2. Builder-owned workers

The inspected AppState registry also covers the principal builder-owned groups:

- `scheduler`: `shutdown()` signals adapters, followed by one remaining-time `join()`.
- `dynamic`, `world_model`, `membrane`: AppState sets each exposed `_stop` Event and joins its `_threads` collection.
- `fountain`, `strike_protocol`, `signal_loop`: explicit `stop()` plus their exposed thread handles.
- `resolver`: `stop_loop()` and `_thread`, as above.

The registry deduplicates thread objects, uses one monotonic join deadline, reports surviving thread names, and records stop/join exceptions. AppState's docstring correctly describes this as a bounded registry rather than a guarantee that every process thread is registered.

## 3. What this narrows — and what it does not

This source comparison did not identify an obvious direct `run.py` worker-start site omitted from the corresponding AppState managed list. That is a useful narrowing result, not a proof of total lifecycle coverage.

Still outside this check:

- Threads created internally by dependencies or by services not represented in `run.py`'s direct start statements.
- Detached tasks spawned dynamically after boot, thread pools, subprocesses, timers or work started by route-called services.
- Whether each service's `stop()` implementation prevents new work after an in-flight blocking call returns. The PersonaResponder, SenseScheduler and predictor-loop fixes address only specific observed paths; the PersonaResponder current-main replay remains under PR #393 at this snapshot.
- Whether direct SQLite writers or background workers use independent connections safely during shutdown.
- The actual process/thread inventory and service-manager behaviour on the user's host.

## 4. Next evidence-led increment

Continue the producer audit from each concrete worker's blocking operations to its first subsequent Writer/direct-SQLite side effect. Prioritize any enabled worker whose blocking call can exceed the five-second producer join allowance. Add stop checkpoints and deterministic tests only where a post-stop continuation is demonstrated. Do not increase shutdown budgets or change feature flags as a substitute for lifecycle evidence.

No runtime code, environment flags, timeouts, database schema, frozen S-01–S-25/M1.8 register, Master Roadmap, Gate 0 or Phase 1 authority changed.
