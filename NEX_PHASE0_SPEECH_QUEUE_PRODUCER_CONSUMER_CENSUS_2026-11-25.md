# NEX Phase 0 — SpeechQueue Producer/Consumer Census (25 November 2026)

## Scope and evidence boundary

Static-source census against baseline commit `de93134f34adac07a3a41c2a05b33720510a2bfc` on the active host branch. All 350 Python source files in the repository tree (excluding tests) were fetched and scanned for `speech_queue`, `SpeechQueue`, enqueue helpers and SQL insert patterns. One literal `INSERT INTO speech_queue` callsite was found.

This is a source-level census, not a live database or service inspection. It does not establish queue depth, host environment values, worker liveness, playback success, or whether any row has ever been spoken. No runtime code, tests, flags, schema, service, experiment, baseline or deployment setting was changed.

## 1. Producer census

### Only located insert callsite: FountainCrystallizer

`theory_x/stage6_fountain/crystallizer.py` is the only Python source file with a literal `INSERT INTO speech_queue` callsite.

The queue insert is downstream of the Fountain belief-admission path:

1. Fountain quality checks pass.
2. CoherenceGate is called when the crystallizer has a Gate instance; normal `run.py` wiring supplies one.
3. The belief row is inserted.
4. A `fountain_crystallizations` row is inserted.
5. Speech eligibility is evaluated.

Speech eligibility requires all of the following:

- `category` is one of `fountain_insight`, `synergized`, `koan`, or `voice_fallback`. Spectrum source is explicitly excluded.
- `SpeechConfig.enabled` is true.
- Content length is between `SpeechConfig.min_chars` and `SpeechConfig.max_chars` inclusive (source defaults: 10–500).
- `SpeechGovernor.decide()` returns SPEAK.
- No existing `speech_queue` row has the same `belief_id`.

The insert stores `belief_id`, a content snapshot, configured voice and queued timestamp. Status defaults to `pending`. It does not wait for the consumer to confirm playback. Queue insertion failure is caught and logged; the belief and crystallization rows have already been written and are not rolled back.

### Other references are not producers

The 350-file scan found other references, but they are reads, state transitions, schema or maintenance:

- `speech/queue_consumer.py`: selects pending rows and updates their statuses; no insert.
- `run.py`: constructs and starts the consumer; no insert.
- `gui/server.py`: status, pause, resume, flush and immediate read-aloud endpoints; no insert.
- `speech/on_demand.py`: immediate read-aloud using the same backend/player; explicitly does not read or write the queue.
- `theory_x/stage6_fountain/generator.py`: reads MAX(spoken_at) during initialization; no insert.
- `theory_x/stage_social/social_presence.py`: reads recent queue speech for posture; normal `run.py` sets SocialPresence to None, so this is not populated in the inspected normal startup.
- `substrate/init_db.py`: creates the table/index and migrates pending legacy voice names; no insert of queue entries.
- `substrate/spectrumizer_process.py`: counts queue rows for diagnostics; no insert.
- `ground_self_belief.py`: includes speech_queue in a belief-deletion reference guard; it is maintenance, not a producer.

No additional literal queue producer was found in the scanned Python source.

## 2. Queue lifecycle and state transitions

The table is created in the beliefs database with columns for belief_id, content, voice, queued_at, spoken_at, status and error. It has a foreign key to beliefs(id), without an ON DELETE CASCADE clause, plus an index on (status, queued_at).

The consumer is a daemon thread. Its normal state transitions are:

- pending → speaking → spoken, with spoken_at set after playback completes;
- pending → failed, with error recorded if synthesis/playback raises;
- pending → suppressed, if the content is empty, raw JSON/source-prefixed JSON, or longer than 400 characters;
- pending → skipped, when the GUI flush endpoint is invoked.

Quiet-hours polling leaves pending rows pending; it does not mark them skipped or suppressed. Pause also leaves pending rows in place. There is no age-based expiry in the consumer's pending query.

### No belief-state recheck at playback

The consumer selects only queue-row fields (id, belief_id, content, voice). It does not join back to beliefs or recheck the referenced belief's tier, paused state, locked state or current content before speaking.

The queue stores a content snapshot at enqueue time. Consequently, if a belief is retired, paused or otherwise changed after enqueue but before playback, the consumer still speaks the queued snapshot if the queue row remains pending and the content passes the speakability check. This is a conditional source-level behaviour; no live queue row or state transition was inspected.

### No recovery for interrupted speaking rows

The consumer selects only status='pending'. It sets status='speaking' before synthesis/playback, then changes it to spoken or failed. No startup recovery path was found that resets status='speaking' after an abrupt process exit. A crash between those transitions can therefore leave a row outside the pending query indefinitely.

### Flush race

`flush()` first selects IDs currently pending, then updates each selected ID to skipped. The consumer separately selects a pending row and later updates its ID to speaking without a conditional `WHERE status='pending'` predicate. If flush and consumer overlap between those operations, the consumer can overwrite the skipped status and continue speaking. No transaction/claim operation was found to make the two paths atomic.

## 3. Producer/consumer policy mismatches and feedback

### Length mismatch

- Producer accepts 10–500 characters by default.
- Consumer suppresses content longer than 400 characters.

Therefore 401–500 character thoughts can be inserted as pending and later marked suppressed by the consumer. The current tests do not cover this boundary.

### Duplicate policy is status-independent

The producer checks for any existing queue row by belief_id, without a status predicate. A prior row in spoken, skipped, failed or suppressed state still blocks a second enqueue for the same belief. This implements once-per-belief deduplication across all statuses, not retry-on-failure semantics.

The queue rows are not deleted by the inspected Python code. The belief-deletion guard in `ground_self_belief.py` treats speech_queue as a referencing table, so any historical queue row can also prevent deletion of its belief through that maintenance path. This may be intentional retention, but it means queue history is durable and can accumulate.

### Governor timing is enqueue timing, not confirmed playback timing

The active SpeechGovernor is owned by FountainCrystallizer. It initializes its last-speech timestamp from MAX(spoken_at) once at construction. When it decides SPEAK, it updates its in-memory last-speech timestamp before the queue insert and before playback.

The consumer writes spoken_at only after playback completes. It does not notify the governor of actual playback. SpeechGovernor has a `mark_spoken_externally()` method, but no callsite was found in the inspected generator, crystallizer, consumer, on-demand, GUI or run paths.

There is also a second SpeechGovernor object constructed in FountainGenerator, with its own MAX(spoken_at) initial timestamp; the field is not read again in the inspected generator source. The active enqueue decision is made by the separate governor in FountainCrystallizer.

Consequently, the active min-gap timer measures time since the enqueue decision during a running process, not confirmed audio completion. After restart, its initial timestamp is based on the last completed spoken_at row, not the newest pending/queued row.

### Two different quiet-hours controls

- SpeechGovernor always applies its probability damping from 22:00 to 07:00 local time (default damping 0.3), regardless of SpeechConfig.quiet_hours_enabled.
- SpeechQueueConsumer hard-pauses polling only when SpeechConfig.quiet_hours_enabled is true. Its default is false; when enabled, its configured window defaults to 23:00–07:00.

Thus source-default behaviour is probabilistic nighttime enqueue damping, not a hard consumer pause. The hard pause has a different start hour and is disabled by default.

### Voice selection

The queue stores the configured voice. At playback, the consumer first asks VoiceState for the current voice and uses that if available; the row voice is only a fallback. The status endpoint reports `consumer.config.voice`, not necessarily the effective VoiceState override.

## 4. Worker and on-demand speech boundaries

### Startup

`SpeechConfig.enabled` defaults to true. `run.py` constructs and starts SpeechQueueConsumer when that setting is true, and passes the shared VoiceState and backend. If backend loading fails inside the consumer thread, the thread logs an error and exits.

`run.py` logs “Speech consumer started” immediately after `.start()`; it does not wait for or verify the worker's successful backend load. The GUI status endpoint reports `enabled = not consumer.paused`, not `consumer.is_alive()` or backend readiness. If the thread exits during backend load failure, the status can still report enabled because the paused flag remains false.

### Immediate read-aloud is a separate path

`POST /api/speech/say` calls `speech.on_demand.speak_async()`. This uses the same backend and Player, but does not read or write speech_queue. It validates up to 2,000 characters, synthesizes on its own daemon thread and calls sounddevice.stop() before playback to preempt current audio.

The queue consumer does not check `on_demand.is_speaking()` and on-demand speech does not pause the queue consumer. Both paths share backend/player resources; concurrent queue and on-demand playback can therefore contend or preempt one another. No runtime overlap was tested.

The `/api/speech/status` field named `saying` reflects only `on_demand.is_speaking()`; it does not report the queue consumer's speaking row. The endpoint does not query status='speaking'. `POST /api/speech/stop` uses sounddevice.stop(), which cuts playback but does not itself update the queue row's status.

## 5. Tests and coverage

`tests/test_speech.py` covers:

- quiet-hours window behaviour;
- speech_queue table creation;
- Fountain crystallization enqueue;
- no duplicate queue row for the same belief_id;
- flush marking pending rows skipped;
- paused consumer not speaking.

`tests/test_fountain_crystallizer.py` covers quality checks, belief insertion and crystallization records, but does not add broader queue-consumer lifecycle coverage.

The inspected tests do not cover:

- the producer/consumer 401–500 character mismatch;
- suppression of JSON or overlength content;
- belief tier/paused/locked revalidation before playback;
- stale pending rows or startup recovery of speaking rows;
- flush/consumer race;
- duplicate suppression after failed/skipped/suppressed status;
- governor timing against actual playback;
- on-demand/queue concurrency;
- backend-load thread death versus API status;
- voice-state override versus reported configured voice.

No tests were run during this static audit.

## 6. Phase 0 disposition

### Confirmed source facts

- One literal Python insert callsite for speech_queue was found across 350 Python source files: FountainCrystallizer.
- The insert occurs after the belief has passed Fountain quality checks and, when wired, CoherenceGate.
- The consumer is a separate daemon and does not recheck belief status before speaking.
- Producer and consumer character limits differ.
- Queue deduplication is status-independent; queue rows are not pruned by the inspected Python paths.
- The active governor updates at enqueue decision time; the consumer records actual spoken_at later.
- On-demand speech bypasses the queue and shares playback resources.
- The API status endpoint does not verify queue worker liveness or queue speaking state.

### Unverified / authority-dependent

- Host-effective NEX5_SPEECH_ENABLED, NEX5_QUIET_HOURS, voice and governor settings.
- Actual queue depth, row ages, stuck speaking rows, failures, suppressions or playback.
- Whether historical queue rows are intentionally permanent references.
- Whether speech must be cancelled when the source belief is later paused/retired.
- Whether queue flush should be atomic with consumer claim.
- Whether on-demand speech should coordinate with queue playback.
- Whether governor min-gap is intended to measure enqueue or completed speech.

### Boundary

No remediation is proposed. Do not alter enqueue eligibility, status transitions, deduplication, retention, governor timing, quiet-hours policy, voice selection or playback concurrency until the governing authority and Gate 0 decision are recovered or explicitly re-established.
