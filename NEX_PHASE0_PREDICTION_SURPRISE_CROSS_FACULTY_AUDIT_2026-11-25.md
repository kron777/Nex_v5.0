# NEX Phase 0 — Prediction and Surprise Cross-Faculty Trace (25 November 2026)

## Scope and evidence boundary

Static-source trace against active host source baseline `de93134f34adac07a3a41c2a05b33720510a2bfc`. This increment follows the loop inventory and maps prediction/surprise records through their producers and consumers, distinguishing the three separate prediction mechanisms present in the source.

No live database rows, process state, model endpoint, market API, flags, or thread state were inspected. No prediction was generated, no external endpoint was contacted, and no runtime/code/test/flag/DB state was changed.

## 1. Three different prediction systems — do not conflate them

| System | Storage | Normal startup | What it predicts |
|---|---|---|---|
| Stage 35 PredictiveSubstrate | `predictions` and `surprise_events` in `dynamic.db` | Constructed and `start_loop()` called unconditionally in `run.py` | Embedding-centroid forecast of future internal belief content and future external input |
| Stage C WorldPredictionLoop | `world_predictions` in `conversations.db` | `NEX5_WORLD_PRED=1`; source default OFF | Voice and random-control Bitcoin direction claims scored against a later real CoinGecko price |
| SelfPredictionLoop | `self_predictions` in `conversations.db` | `NEX5_SELF_PRED=1`; source default OFF | Whether NEX will produce a Fountain fire in the named horizon, paired with a random control |

The existing `theory_x/stage_emphasis/prediction_tracker.py` is a fourth named prediction-related component, but the inspected normal `run.py` path does not construct or start it. It computes an expectation-error proxy from recent Fountain vocabulary when called; its source describes no persisted state.

These systems have different tables, clocks, targets, consumers and activation gates. A row in one is not evidence that another system is active.

## 2. Stage 35 PredictiveSubstrate — producer

### Startup and cadence

- `run.py` constructs `PredictiveSubstrate` with dynamic, beliefs, conversations and sense readers/writers plus DriveEmergence, then calls `start_loop()` without a dedicated environment flag.
- Default interval is 300 seconds. The loop waits one interval before its first tick; each tick verifies matured prior predictions, then creates new predictions.
- The source stores predictions and surprise events in `dynamic.db`. This is separate from the market and self-prediction tables in `conversations.db`.

### Internal prediction

- Reads the latest ten belief rows ordered by `created_at DESC`; there is no tier, paused or locked filter in this selection.
- Requires at least three beliefs.
- Embeds those beliefs, then adds weighted open-problem and current-drive embeddings where available; the resulting centroid is normalized.
- Selects representative content and inserts one `internal_belief` prediction.

### External-input prediction

- Reads up to ten recent sense rows with `stream NOT LIKE 'internal.%'`.
- Separately reads up to ten recent user messages.
- Concatenates the sense rows before the user-message rows, then slices the combined list to ten inputs.
- Requires at least three inputs, embeds the selected content and inserts one `external_input` prediction.

**Source discrepancy against PREDICTION_PROTOCOL.md §3.2/§4.2:** the protocol describes the last N sense events and chat messages “by recency.” The implementation does not merge-sort both sources by timestamp before choosing the ten-item set. If ten qualifying sense events are available, the later user-message rows are omitted from that tick's external centroid even if some user messages are more recent. This is a source-level ordering difference; its effect on prediction quality is unmeasured.

## 3. Verification and surprise-event production

For each due unverified prediction:

- `internal_belief` verification compares against beliefs created in the prediction window.
- `external_input` verification compares against sense events plus user messages in the window.
- If the comparison set is empty, surprise is set to 1.0 and actual content remains NULL.
- Otherwise the minimum embedding distance becomes the surprise score.
- The verifier writes a `surprise_events` row, then marks the prediction verified with score/flag fields.

**External-population mismatch:** the external prediction generator excludes `internal.%` sense streams, but its verifier query reads all `sense_events` in the time window without the same stream exclusion. Internal sense events can therefore participate in the “actual external input” comparison even though they were excluded from the forecast population. This can reduce the calculated minimum distance and change whether an external prediction is marked surprising. The mismatch is present in source; no live event distribution or score impact was measured.

The verifier uses one `now` value for all rows resolved in a tick. Multiple predictions due in the same tick can therefore produce `surprise_events` with the same `triggered_at` value.

## 4. Surprise events have four distinct downstream consumers

### 4.1 SurpriseLoop → belief writer

The Stage 2 factory registers `life.surprise_loop`; it wakes every five minutes. It:

1. Reads flagged surprise events newer than a timestamp cursor, requiring non-empty predicted and actual content.
2. Limits each query to 20 rows.
3. Formats each row as a first-person Tier 6 `surprise` belief with confidence 0.75.
4. Inserts directly into `beliefs` through a SQLite connection, without a `ThoughtPacket` or `CoherenceGate.check()`.
5. Advances the cursor in `dynamic.db:daemon_kv`.

This is one of the seven direct life-loop belief paths already recorded in G-25. It is a distinct producer from PredictiveSubstrate: the substrate writes the surprise event; SurpriseLoop promotes selected events into belief content.

### 4.2 AffectState → arousal

Normal startup constructs AffectState with the dynamic reader and starts its background loop. On each 300-second tick it reads flagged surprise events newer than the prior `affect_state.updated_at`, averages their scores, and adds `average × 0.2` to arousal after baseline decay, capped at 1.0.

This is implemented in current source and covered by `tests/test_affect_state.py` (flagged surprise raises arousal; unflagged surprise does not). However, `PREDICTION_PROTOCOL.md` §6/§11 still describes this AffectState coupling as a future follow-on amendment and says the consumer reads through its conversations Reader. The current implementation uses the separately supplied dynamic Reader. The protocol text is stale relative to source.

### 4.3 Fountain curiosity re-ranking

`FountainGenerator`'s curiosity re-ranker reads up to 20 recent `surprise_events.actual_content` values from the last six hours where `surprise_score > 0.3`, tokenizes them, and uses those tokens as a candidate-scoring signal. It is a separate read from AffectState and does not require `surprise_flag=1`.

### 4.4 Surprise-weighted crystallization

FountainCrystallizer calls `surprise_weighting.confidence_for_fire()` when `NEX5_SURPRISE_WEIGHT` is not `0` (source default is `1`). The helper reads the latest event in the last 60 seconds and computes a confidence boost from its score.

The helper selects `surprise_score`, `surprise_flag` and `big_surprise`, but the score calculation uses only `surprise_score`; it does not require either flag. Consequently a recent event below the 0.5 surprise threshold can still increase crystallization confidence. The helper's module description emphasizes high-surprise events; the actual predicate is any recent event. Whether continuous low-score weighting is intended is a calibration/spec question, not a confirmed defect.

## 5. SurpriseLoop cursor has a bounded-batch loss condition

The consumer cursor is a timestamp (`surprise_loop_last_ts`), not an event ID or composite cursor. Its query is `triggered_at > since ORDER BY triggered_at ASC LIMIT 20`. After processing the returned batch it advances the cursor to the maximum timestamp encountered.

Two source-level conditions can skip rows:

1. **More than 20 rows share a timestamp.** PredictiveSubstrate can verify many overdue predictions in one tick and passes the same `now` to every `_verify_one()`; all resulting surprise rows receive the same `triggered_at`. If more than 20 eligible rows share that timestamp, SurpriseLoop reads 20, advances to that timestamp, and the remaining equal-timestamp rows no longer satisfy `triggered_at > since`.
2. **A write fails after the row is fetched.** The loop advances `max_ts` for the row even when the belief INSERT raises an exception; the cursor is then persisted past that event, so the failed row is not retried by this cursor.

An `IntegrityError` for duplicate belief content is also treated as a skipped row and the cursor advances; that may be an intentional dedup outcome. The first two cases are conditional loss/retry gaps. No live backlog, same-timestamp batch, or failed insert was inspected.

The existing `tests/test_predictive_substrate.py` verifies prediction generation, verification math, empty-window handling, flags, idempotency and schema. There is no dedicated `tests/test_surprise_loop.py` in the inspected tree, and the tests do not exercise timestamp-cursor pagination, equal-timestamp overflow or failed-write cursor advancement.

## 6. Separate Stage C market-prediction path and its scorecard consumer

### WorldPredictionLoop

- Startup is explicitly gated by `NEX5_WORLD_PRED=1`; source default is OFF.
- When armed, it waits the configured interval (default 900 seconds) before its first tick.
- Each tick resolves due claims by fetching a real current CoinGecko price, then asks the configured local Voice endpoint for an up/down call and records a random control at the same baseline/horizon.
- `world_predictions` is created in `conversations.db` by `ensure_schema()`; the table is separate from Stage 35's `predictions` in `dynamic.db`.
- The voice call consults `calibration_consult` after generating its direction and stamps the current trust level/gap/sample size on the voice prediction row. The consulted trust does not alter the already-produced guess.

### ScorecardLoop is not gated with WorldPredictionLoop

- `life.scorecard_loop` is registered in the normal Stage 2 loop list without the `NEX5_WORLD_PRED` gate.
- It calls `ground_self_belief.refresh_self_belief()` once immediately when its thread starts, then hourly.
- That helper reads the `world_predictions` scorecard and inserts or updates a locked Tier 1 `grounded_scorecard:market_direction_v1` belief through a standalone Writer.
- `scorecard_by_source()` calls `ensure_schema()`, so the scorecard table can be created by this consumer even when WorldPredictionLoop is not armed.
- With no resolved scorecard data, the sentence is conservative (“not enough resolved guesses”); if prior/manual rows exist, it reports those. Thus the belief refresh is normal-wired independently of new automatic market predictions.

This is not necessarily a defect: a scorecard consumer can legitimately maintain a statement from prior/manual data. The source does show that “WorldPredictionLoop default OFF” does not mean “the market scorecard/self-belief path is inactive.”

### SelfPredictionLoop

`NEX5_SELF_PRED=1` separately starts a self-firing prediction loop (default OFF). It stores paired `self` and `random` predictions in `self_predictions`, resolves them against actual non-empty Fountain thoughts in `fountain_events`, and exposes a separate scorecard. The inspected normal startup does not connect this scorecard to `ground_self_belief` or Stage 35 `surprise_events`.

## 7. Test coverage and source-document alignment

- `tests/test_predictive_substrate.py` covers state shape, interval guard, sparse-context skips, internal/external prediction creation, verification, surprise flags, idempotency, tags and schema.
- `tests/test_affect_state.py` covers flagged/unflagged surprise-to-arousal coupling.
- `tests/test_gw_surprise_nonempty.py` concerns a separate Global Workspace surprise-candidate rule; it is not a test of Stage 35 `surprise_events` promotion.
- No dedicated SurpriseLoop cursor/promotion test was found in the inspected test tree.
- No integration test was found that verifies the external-input sample is globally recency ordered, or that the external verification population matches the generation population.
- The protocol's deferred-AffectState text and reader description no longer match current implementation.

## 8. Phase 0 disposition

### Confirmed source facts

- Stage 35 PredictiveSubstrate is normal-wired and writes to `dynamic.db`; WorldPredictionLoop and SelfPredictionLoop are distinct, optional systems using `conversations.db`.
- External-input prediction generation and verification use different sense-stream populations, and generation does not merge sense/user inputs by global recency.
- SurpriseLoop is a normal-wired, direct Tier 6 belief producer with a timestamp-only cursor and a 20-row batch cap.
- The cursor can skip equal-timestamp overflow rows and does not retry rows whose belief write fails after fetch.
- Surprise events feed SurpriseLoop, AffectState arousal, Fountain curiosity scoring and Fountain crystallization confidence.
- AffectState surprise coupling is implemented and tested even though the protocol still labels it deferred.
- The market ScorecardLoop runs independently of the default-OFF WorldPredictionLoop and maintains a locked Tier 1 scorecard self-belief.

### Unverified / authority-dependent

- Host-effective flags, loop activation, database contents, actual external feed mix, and whether the scorecard has prior/manual rows.
- Whether the external-input verifier is intended to include internal sense events.
- Whether scorecard refresh should be coupled to the optional WorldPredictionLoop or may use historical/manual results.
- Whether SurpriseLoop should be lossless across timestamp ties and transient insert failures, and what dedup/retry policy is intended.
- Whether surprise-weighted crystallization should use continuous scores or require a flagged event.
- Whether the PREDICTION_PROTOCOL document has an approved amendment for the implemented AffectState coupling.

### Boundary

No code, tests, flags, data or runtime settings were changed. Do not change prediction populations, cursor semantics, scorecard activation, surprise weighting or AffectState coupling until the relevant governing contract and Gate 0 authority are resolved.
