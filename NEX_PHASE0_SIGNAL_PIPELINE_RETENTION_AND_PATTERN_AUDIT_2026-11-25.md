# NEX Phase 0 — Signal Pipeline, Retention and Pattern Crosswalk (25 November 2026)

## Scope and evidence boundary

Static-source audit against active host source baseline `de93134f34adac07a3a41c2a05b33720510a2bfc`. This increment traces SignalLoop detector outputs through signal persistence, pattern templates, SignalToProblem promotion, signal retention, and the inspected readers of the signals/patterns tables.

No live signal rows, reaper execution, external activity, or current DB size was inspected. No signal was emitted, promoted, deleted, or replayed. No runtime/code/test/flag/DB state was changed.

## 1. Signal producers

### 1.1 Normal SignalLoop

`run.py` calls `build_signal_loop()`, which starts a daemon thread immediately with a 60-second interval. Each tick:

1. Attempts the hourly bounded signals reaper.
2. Runs CoOccurrenceDetector, SilenceDetector and BurstDetector.
3. Inserts each detected signal into `beliefs.db:signals`.
4. Passes only the signals emitted during that same tick to PatternTemplateLibrary.
5. Inserts any resulting `patterns` rows.

The three detector sources are distinct:

- **CoOccurrenceDetector:** reads up to 500 recent beliefs in a 30-minute window, excluding selected seed sources, groups capitalized phrase entities across branches and emits `N_branch` signal types when the branch set changes.
- **SilenceDetector:** reads external (non-`internal.%`) sense events over the last hour; with at least five events it compares current silence to three times the average gap and emits `branch_silence_anomaly` when the frozen average-gap fingerprint changes.
- **BurstDetector:** counts Tier 6 beliefs over 15 minutes and emits `t6_promotion_burst` when the count/branch-set fingerprint changes above threshold.

These are structural, LLM-free detectors. Their in-memory fingerprints reset on process restart, so a restart can permit one fresh emission for an unchanged pattern.

### 1.2 Direct advancements_drift producer

Fountain's maxDF* convergence path calls `emit_advancements_drift()`, which inserts an `advancements_drift` row into the same `signals` table through the supplied beliefs Writer. It is edge-triggered on a false→true breach transition. This producer does not depend on the 60-second SignalLoop tick.

## 2. PatternTemplateLibrary semantics

The current template library contains three templates: triple co-occurrence, branch silence anomaly and T6 promotion burst. Each has `min_signals=1` and one required detector.

The library receives only the current SignalLoop tick's in-memory `all_signals` list. It does not query or aggregate historical signal rows across ticks. Therefore a “pattern match” can be produced from one signal row; it is a template rendering of a detector result, not a multi-tick temporal cluster in the current implementation.

When multiple signals of the required detector are emitted in one tick:

- `signal_ids` records all IDs from that detector for the template;
- the prediction text is composed from only the first signal's payload.

A pattern row can therefore reference several signal rows while its human-readable prediction describes only the first one. No live multi-signal batch was inspected.

The schema comment in `substrate/schema/beliefs.sql` explicitly marks `validated_at`, `outcome_score` and `outcome_notes` as vestigial: no update path was found, and the only inspected read is the GUI display endpoint. `predicted_window_seconds` is stored, but no pattern validation worker uses it. This is separate from Stage C `world_predictions`, which has a real resolver and scorecard.

## 3. SignalToProblem promotion

The Stage 2 dynamic factory registers `signal_to_problem_loop`, which ticks every 120 seconds. Its current source contract is:

- `LOOKBACK_SECONDS = 21600` (6 hours);
- minimum confidence 0.40;
- at most five new problems per rolling 24 hours;
- fetch at most 20 eligible un-actioned rows ordered by confidence then recency;
- current promotable types are `2_branch`, `3_branch`, `4_branch` and `advancements_drift`;
- excludes branch-silence and the old burst/template types after measured noise problems;
- applies a seven-day entity duplicate check, plus a durable open/stuck `advancements_drift` debounce keyed by the source-style tag;
- `NEX5_SIG_QUALITY=1` enables the corroboration/quality filters; `NEX5_PROBLEM_SELF_GATE=1` enables the external-branch corroboration gate. Both source defaults are OFF.

For skipped duplicates/quality/self-gate cases, the source signal is marked actioned so it is not rechecked every two minutes. A successful path inserts an `open_problems` row with tags `["auto", "signal:<type>"]`, then marks the signal actioned. This tag dialect is the previously recorded G-29 divergence from TAG_PROTOCOL content-derived tags.

### Cross-database commit boundary

The producer opens separate connections to `beliefs.db` and `conversations.db`. It executes the open-problem insert in conversations and the `actioned_at` update in beliefs, then commits beliefs first and conversations second. These are separate SQLite transactions, not one atomic cross-database transaction.

If the beliefs commit succeeds and the conversations commit then fails, the signal can be durably marked actioned without its corresponding problem row. If the first commit fails, neither transaction is guaranteed committed; if the second commit fails, the loop catches the outer exception and retries later, but the signal may already be actioned. The source shows this conditional partial-commit window; no commit failure or lost problem was observed. This is a transaction-boundary risk to assess against the approved database contract, not a claim of an incident.

## 4. Signal retention and allowlist drift

The reaper runs from SignalLoop and is self-throttled to one pass per hour. It targets signals older than seven days, in batches of at most 50,000, and intends to preserve un-actioned signals that SignalToProblem can still promote.

The two modules currently have different allowlists:

| Signal type | SignalToProblem currently promotes | Reaper preserves if un-actioned |
|---|---:|---:|
| `2_branch` | yes | yes |
| `3_branch` | yes | yes |
| `4_branch` | yes | no |
| `advancements_drift` | yes | no |
| `t6_promotion_burst` | no | yes |
| `pattern_recognition_burst` | no | yes |
| `branch_silence_anomaly` | no | no |

The reaper list also contains `cross_branch_convergence`, `novel_arc` and `concept_emergence`, which are not in the current SignalToProblem promotable set.

Consequences of the mismatch:

- An un-actioned `4_branch` or `advancements_drift` row can be deleted after seven days, despite being listed as promotable by SignalToProblem. However, SignalToProblem only looks back six hours, so such a seven-day-old row is already outside its current processing window; the reaper's stated “preserve unconsumed promotable signals regardless of age” contract is still not met.
- Un-actioned `t6_promotion_burst` and `pattern_recognition_burst` rows are preserved indefinitely by the reaper allowlist even though SignalToProblem explicitly removed them from its current promotable set. This can defeat the reaper's intended bounded-retention rule for those old rows.

This is a source-level allowlist drift. No current table population, affected row count or disk effect was measured.

Additional implementation detail: `reap()` documents that it returns the number of rows deleted, but the function returns the constant `_REAP_BATCH` after any successful Writer call, regardless of the actual delete count. SignalLoop ignores this return value in the inspected path, so it does not currently drive a displayed count there.

## 5. Inspected readers and consumers

The reaper module enumerates four readers, and the inspected source supports that bounded set:

1. **SignalToProblem:** six-hour promotion query.
2. **CompetingDrives:** counts signal types over the last 24 hours to derive cross-domain/new-entity rates.
3. **Probe context snapshot:** includes recent signals from the last ten minutes in a diagnostic snapshot.
4. **GUI `GET /api/signals/recent`:** returns the latest up to 100 signals and patterns without a time predicate.

The GUI is the only inspected pattern-table consumer. It displays `signal_ids`, prediction text, validation timestamp and outcome fields; it does not join the signal IDs back to the signals table. Reaping old signal rows can therefore leave historical IDs in the JSON field, but the inspected GUI displays those IDs as stored and does not dereference them.

## 6. Tests and coverage

- `tests/test_signals.py` covers detector logic, template rendering, pattern match creation and SignalLoop signal/pattern writes.
- The template tests explicitly accept one signal as sufficient for each current template, consistent with `min_signals=1`.
- No dedicated SignalToProblem producer/consumer test file was found in the inspected test tree.
- `tests/test_retention_reaper.py` tests the separate general observability-log reaper, not `theory_x/signals/reaper.py`.
- No test was found for parity between the reaper preservation list and SignalToProblem's current promotable set, cross-database commit failure, or reaper actual-row-count reporting.
- The inspected tests do not validate pattern predictions against their stored future windows.

## 7. Phase 0 disposition

### Confirmed source facts

- Signals have two producer routes: the three-detector SignalLoop and Fountain's direct advancements_drift emitter.
- PatternTemplateLibrary consumes only current-tick signal objects; all current templates allow one signal, and prediction validation fields are vestigial in the schema.
- SignalToProblem reads the current promotable set over six hours and writes problems plus actioned markers across two separate database connections/transactions.
- The SignalToProblem and reaper allowlists are out of sync.
- The reaper preserves some types no longer promotable and omits two currently promotable types.
- Signal readers are time-bounded except the GUI latest-N endpoint; pattern JSON signal IDs are not dereferenced by the inspected reader.

### Unverified / authority-dependent

- Actual live signal volumes, reaper batches, remaining backlog and current disk footprint.
- Whether the reaper allowlist is intended to mirror current SignalToProblem eligibility or preserve legacy rows for another purpose.
- Whether patterns are intended as one-signal template annotations or true multi-signal temporal patterns.
- Whether pattern predictions are intentionally archival-only or should have a validation consumer.
- Required cross-database atomicity/recovery contract for SignalToProblem.
- Whether any alternate consumer exists outside the inspected active branch.

### Boundary

No retention window, allowlist, pattern template, validation path, signal conversion, database transaction or startup behaviour was changed. Do not reconcile these behaviours or add consumers before the governing Frozen V2.1 / roadmap authority and Gate 0 decision are resolved.
