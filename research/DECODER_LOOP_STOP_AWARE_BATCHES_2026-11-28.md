# Coincidence decoder row-boundary shutdown — 28 November 2026

**Base:** main at 55fd635bd535d15ece3e3878bf1e71621f56fa7c.  
**Scope:** cooperative stop checkpoints inside the decoder's canonical Writer transaction. No poll interval, tokenization, schema, word-context features or decoder semantics changed.

## 1. Source evidence

- decoder_loop is registered as an AppState-owned thread and polls fountain_events every 30 seconds.
- decoder_tick reads up to 200 unprocessed fires in one canonical dynamic Writer transaction.
- For each fire it tokenizes the thought, reads a tree snapshot, performs several state-count queries, reads the latest external sense-feed timestamp, derives local time fields, inserts one word_contexts row per unique token, and advances daemon_kv's decoder_last_fid cursor.
- Before this change, the stop Event was checked only by the outer loop. A stop during a tick could still process all 200 fires and their word rows before returning.
- Word inserts and cursor advancement already share one transaction, so the cursor can safely advance only for fully processed fire rows.

## 2. Bounded correction

- Add an optional keyword-only stop Event to decoder_tick and pass the loop's Event into it.
- Check stop before opening the transaction, after the cursor/read batch, and between the tree/state/sense/time preparation reads.
- Check before starting each fire row.
- Treat one fire row as the smallest commit unit: once word insertion begins, finish that row's complete token set and cursor update; check stop before the next fire.
- Return the actual count of completed rows rather than the original batch length when shutdown truncates a batch.
- Add deterministic tests for already-stopped entry, stop during the sense-feed read before writes, and stop after the first completed fire row.

## 3. Boundaries

- Individual SQLite/Reader operations are synchronous and not cancelled. A stop during a read is observed immediately after that read returns.
- If stop arrives during a fire row's word inserts, that row and its cursor update finish in the same transaction; later rows are skipped.
- The transaction commits completed rows and cursor state together. This preserves restart position and avoids reprocessing a partially inserted word set.
- This does not change the 30-second poll interval or prove host-level process shutdown.

## 4. Validation

Exact-head full-suite CI and baseline verification are required before merge. Tests use an in-memory SQLite connection and deterministic Events.
