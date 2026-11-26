# NEX Phase 0 — Moltbook External I/O and Dry-Run Semantics Audit (25 November 2026)

## Scope and evidence boundary

Static-source audit against active-host source baseline `de93134f34adac07a3a41c2a05b33720510a2bfc`. It traces the three Stage 2 Moltbook workers, client dry-run behavior, local state transitions, outbound content selection and inbound message path.

No credentials were read, no HTTP request was sent, no Moltbook account was contacted, and no local Moltbook DB was opened. No live host environment or service state was inspected. No runtime/code/test/flag/DB state was changed.

## 1. Registration and service gates

- If `theory_x.stage7_moltbook` imports, Stage 2 registers Poster (60 s), Listener (300 s) and Responder (300 s) loops. There is no separate `MOLTBOOK_ENABLED` flag in the inspected factory.
- Each worker calls `_ensure_client()`, which loads credentials from the configured local credentials file and calls the remote status endpoint; the service must report `claimed`.
- `MOLTBOOK_DRY_RUN` defaults to the exact string `"1"`; the client sets `dry_run = (value == "1")`.
- Dry-run intercepts non-GET requests. GET status, feed, conversation-list and message-read calls still use the remote API.
- Any environment value other than exactly `"1"` (including `"0"`, `"true"`, a typo or an empty value) sets `dry_run=False` and allows actual non-GET requests. This is exact-string parsing, not a strict fail-closed parser.
- The tracked `nex_keepalive.sh` explicitly sets `MOLTBOOK_DRY_RUN=0`, which would permit actual outbound writes if that launcher were used and the Moltbook workers became ready. The current reconciliation separately records a path blocker for that tracked launcher and that the actual host service unit is untracked/unknown. The tracked value is not proof of live activity.

Therefore “dry-run” is not offline mode: remote reads and local ingestion still occur, and the tracked launcher is configured for real writes if it reaches the application.

## 2. Outbound poster path

### Candidate selection

Poster reads new `fountain_insight` belief rows by ID/high-water mark and age. The selection query does not filter tier, paused, locked or retired state. It then applies content/quality, length, dedup and posting-interval checks before inserting a local queue row.

A source='fountain_insight' belief that is later paused or Tier 8 is not excluded by the selection query if it is otherwise newer than the high-water mark and passes the other checks. No live candidate was inspected.

### Dry-run local state

The poster calls `MoltbookClient.create_post()`. In dry-run, the client returns a synthetic success-shaped object without a remote post ID. The poster's success path still:

- writes a `moltbook_posts` record with local status `posted`;
- updates the queue row to `posted`;
- advances the local posting timestamp/high-water state.

Thus dry-run can consume a candidate locally as “posted” even though no remote post exists. This is a local false-success/state-divergence path, not a network side effect.

When `dry_run=False`, the same path performs the actual remote POST.

## 3. Inbound listener and DM approval path

### Remote reads and local writes

Listener uses GET requests to list DM requests, list conversations and read messages. It filters candidate agents by claimed status, a red-flag check and a karma floor (default 100). Requests passing the filter are automatically sent through `dm_approve()`; there is no human-approval step in this normal worker path.

After the client call returns, the listener writes local approval state. In dry-run the remote POST is mocked, but the local record can still be marked approved.

For unread inbound messages, the listener:

- stores the raw message JSON in `sense_events` with stream `moltbook_dm`;
- inserts a local `moltbook_pending_replies` row with `needs_human=0` and status `new`.

The normal sense-distillation loop does read non-`internal.%` streams, but the shared `extract_sense_title()` only extracts JSON fields `title`, `headline`, `name` or `subject`. The Moltbook payload uses fields such as `message` and `from_agent`, so the current extractor returns None for that JSON payload; the inspected Stage 2 distillation path therefore does not turn the raw DM text into a `precipitated_from_sense` belief. This is a useful negative finding, not a claim that the DM is absent from every other context path.

### Dry-run local state

A mocked `dm_approve()` return is not distinguished from a real remote approval before the local row is marked approved. This can create local approval state that does not correspond to remote approval.

## 4. Outbound DM responder path

- Responder selects pending rows with status `new` and `needs_human=0`; the listener's normal insert sets `needs_human=0`.
- It sanitizes inbound message text using a pattern-based `sanitize_inbound()` helper before composing. The raw inbound message remains in its local pending/sense record.
- It fetches up to 400 related beliefs from sources `spectrum`, `precipitated_from_sense` and `fountain_insight`. The query has no tier, paused, locked or retired-state filter.
- It composes a reply with the configured local LLM endpoint, then calls `dm_send()`.
- After `dm_send()` returns without raising, the responder marks the pending row `sent`. In dry-run the client returns a synthetic object, so the local row can be marked sent even though no remote DM was delivered.
- When `dry_run=False`, the same path sends the DM externally.

The belief selection can therefore include paused/retired/Tier 8 content in an outbound response prompt. The responder's inbound text sanitizer does not filter those stored belief rows. This is a candidate stale/untrusted-content exposure at the external boundary; no live content or outbound reply was inspected.

## 5. One-shot seed utility

`scripts_moltbook_seed.py` is a separate manual utility that can send an opening DM to selected approved conversations. Its local `DRY` variable defaults false, but it still uses the same client-level dry-run. With client dry-run enabled, the POST is mocked while the script's success path can count/log the item as sent; with `MOLTBOOK_DRY_RUN=0`, the client permits a real POST. This is not a normal boot worker, but it is another outbound entry point.

## 6. Tests and coverage

The inspected tree has no dedicated Moltbook client, Poster, Listener or Responder test module. `tests/test_social_presence.py` concerns a separate SocialPresence faculty and does not exercise the Moltbook client/loops.

No tests were found for:

- dry-run GET versus non-GET boundaries;
- malformed `MOLTBOOK_DRY_RUN` values;
- synthetic success not advancing local sent/posted/approved state;
- outbound belief status filtering;
- automatic DM approval and reply policy;
- raw inbound DM payload handling in sense distillation.

No credentials, network calls or live DB operations were performed during this audit.

## 7. Phase 0 disposition

### Confirmed source facts

- Three Moltbook loops are registered when the package imports; no separate master enable flag is present in the inspected factory.
- Dry-run still permits GET network calls and local ingestion; non-GET requests are mocked only when the environment value is exactly `"1"`.
- The tracked keepalive explicitly sets `MOLTBOOK_DRY_RUN=0`; launcher reachability and live service state remain unknown.
- Poster, Listener and Responder can mark local records posted/approved/sent after synthetic dry-run responses.
- Poster candidate selection and responder related-belief retrieval do not filter paused, locked, retired or Tier 8 belief states.
- Listener auto-approves eligible DM requests based on claimed/red-flag/karma filters and inserts pending replies with `needs_human=0`.
- Raw DM JSON is stored as `moltbook_dm` sense events, but the current title extractor does not extract its `message` field for Stage 2 sense distillation.
- The one-shot seed utility is a further outbound entry point.
- No Moltbook-specific tests were found in the inspected test tree.

### Unverified / authority-dependent

- Whether the Moltbook package imports on the live host; whether credentials exist; whether remote status is claimed; whether any worker is active.
- Actual environment value of `MOLTBOOK_DRY_RUN` in the host's untracked service unit.
- Whether any real post, DM approval or DM reply has occurred.
- Whether automatic approval/reply is intended or should require explicit user review.
- Whether Fountain insights and related beliefs are permitted for external publication when paused/retired/locked/Tier 8.
- Whether dry-run should be a no-network/no-local-consumption simulation or merely a no-write-to-remote mode.
- Whether the sense event payload is intentionally retained but excluded from generic distillation.

### Boundary

No external request, approval, post, DM, credential access, local DB operation, flag change or worker activation occurred. Do not enable Moltbook, change dry-run, change filters, or alter approval/reply policy until the founder explicitly decides the external interaction contract and Gate 0 authority is resolved.
