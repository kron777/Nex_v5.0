# CounterfactualNode — Phase 25b Specification (REDESIGNED)

Foundational spec per DOCTRINE §1. Defines CounterfactualNode
(DOCTRINE §5 row 10b, Option γ). Written before implementation.
Implementation begins Phase 25b-build (separate session).

**Amendment 2026-05-11: Redesigned around problem move
semantics rather than in-table state lifecycle.** The original
spec used a `has_candidates` state on `open_problems`; that
approach was abandoned mid-build (see CARRY_OVER_2026-05-11
or commit log for context). This version moves flagged problems
into a dedicated `review_queue` table, leaving `open_problems`
as the strict set of problems NEX is currently working on.

Created: 2026-05-10. Amended: 2026-05-11. Design decisions
locked in Phase 25b-spec and Phase 25b-redesign-spec sessions
with Jon.

**Dependencies:** this phase depends on the Tag Protocol
substrate being in place (`TAG_PROTOCOL.md`). Build order:
Tag Protocol substrate → Tag integration on existing surfaces
(beliefs, open_problems) → Phase 25b-build (this spec).

---

## §1 Purpose

CounterfactualNode (CN) is a proactive, problem-directed
generative SentienceNode. On a 5-minute clock, it reads
NEX's open problems, retrieves beliefs relevant to each
problem, and submits them as candidate answers through
the Coherence Gate. Accepted candidates enter the belief
substrate tagged with the originating problem's ID. When
enough candidates accumulate for a problem, the problem
is **moved** out of `open_problems` into a separate
`review_queue` table for downstream surfacing.

The psychological function being realized: generative
problem-directed thinking — the capacity to hold an open
question and continuously surface candidate answers from
one's accumulated knowledge, without being stuck or
prompted.

**What CounterfactualNode is not:**

It is not throw-net. Throw-net is a stuckness responder — it
fires after repeated gate REJECTs or gap deflections on the
same topic, and its purpose is to break out of a blocked
pattern. CounterfactualNode fires on a clock without any
stuckness signal. It runs during normal productive operation,
not only during failure.

It is not the fountain. The fountain generates spontaneous
thoughts from the full belief field without a specific target.
CounterfactualNode generates only in service of named open
problems. Every ThoughtPacket it produces is linked to a
specific problem row.

It is not novel_association. NovelAssociation detects semantic
similarity between existing belief pairs and writes edges
between them — it does not generate new belief content.
CounterfactualNode retrieves existing beliefs as candidates
and submits them to the gate as potential new beliefs, tagged
for a problem.

---

## §2 Inputs

CounterfactualNode reads three substrate sources via Reader
objects per DOCTRINE §3.

**Open problems.** Reads `open_problems` table in
`conversations.db`. Processes only rows where `state = 'open'`
(now the only active state — `has_candidates` is no longer a
valid state; flagged problems live in `review_queue`).

The problem title is the primary input to retrieval (§5).

**Active goals.** Reads `goals` table for context. In Phase
25b-build, goals are not used directly in retrieval — they
are available for future weighting (e.g., prioritize problems
linked to active goals). This connection is deferred to a
post-build iteration.

**Beliefs.** Reads `beliefs.db` for candidate retrieval (§5).
Uses the beliefs Reader for retrieval. Performs writer
INSERTs into `beliefs` after gate ACCEPT decisions (§6).

---

## §3 Output

Each tick, CounterfactualNode produces zero or more
ThoughtPackets, one set per open problem. Each ThoughtPacket
carries:

- **content**: the candidate belief text
- **source_node**: `"counterfactual.{problem_id}"` — the
  source encodes the originating problem at generation time,
  matching the throw-net convention (`throw_net.{trigger_type}`)
- **confidence**: derived from the candidate belief's own
  confidence score
- **branch_id**: inherited from the candidate belief if
  present; otherwise None
- **metadata**:
  - `problem_id`: INTEGER — the originating problem's id
    (this id is stable across the open_problems → review_queue
    move; see §7.4)
  - `counterfactual_score`: the RefinementEngine score for
    this candidate (0–6)

Every ThoughtPacket is submitted to `CoherenceGate.check()`.
The gate routes ACCEPT / REJECT / HOLD / RESHAPE per DOCTRINE §7.

**On ACCEPT:** CN persists the belief itself via direct
INSERT to `beliefs.db` (see §6). Tag auto-generation runs
as part of the belief writer pipeline (per Tag Protocol §4),
so the new belief lands with both `problem_id` and `tags`
populated.

CN does not inspect the gate outcome beyond this dispatch.

---

## §4 Tick Mechanics

**Interval:** 300 seconds (5 minutes). Same as ThrowNetMonitor
and HoldingZoneResolver. Consistent daemon-thread cadence
across the faculty model.

**Lifecycle:** CounterfactualNode follows the NovelAssociation
pattern. `tick()` contains an interval guard:

```
if elapsed since last run < _TICK_INTERVAL_S: return state()
```

Heavy work (retrieval + gate submission) runs only when the
interval has elapsed. `tick()` itself is always fast.

`start_loop()` spawns a daemon thread named
`"counterfactual_node"`. `stop()` sets the stop event.
Registration in `run.py` follows the ThrowNetMonitor pattern.

**Per-tick budget:** all candidates that survive the
RefinementEngine threshold are submitted to the gate. No hard
cap per problem per tick. The candidate pool per problem
title is bounded by TimeFetch's retrieval cap (40 raw
candidates → top scored by RefinementEngine).

**Ordering:** problems are processed in `created_at ASC` order
(oldest open problem first). Goal-priority weighting is
deferred.

---

## §5 Generation Strategy

**Retrieval:** extract content words from the problem title
using the same stopword strip established in TriggerDetector
(TN-1). Pass the resulting keyword string to
`TimeFetch.run(constraint)`. TimeFetch sweeps four substrate
sources (beliefs, novel_association_log, held_thoughts,
arc_notes) and returns up to 40 raw candidates.

Title-only retrieval starts immediately on current substrate.
When descriptions are populated, the keyword string can be
extended to include description tokens without code change to
CN — the caller constructs the constraint string; TimeFetch
is indifferent to its origin.

**Scoring:** pass raw candidates through `RefinementEngine.run()`.
Same R1–R6 scoring on 0–6 scale. Candidates with score ≥ 3
are submitted to the gate. Candidates below 3 are discarded.

**reshape_hint:** candidates with score < 5 carry
`metadata['reshape_hint'] = True`, activating Phase 24's
RESHAPE path. Same D5 calibration as throw-net (score < 5 on
0–6 scale). This is the D5 convention applied uniformly
across all nodes that use RefinementEngine.

---

## §6 Problem-Candidate Linkage

The connection between an accepted belief and its origin
problem is stored in the beliefs table via `beliefs.problem_id`.

**Schema:**

```sql
ALTER TABLE beliefs ADD COLUMN problem_id INTEGER;
```

Nullable, no FK constraint (logical reference only — `beliefs.db`
does not reference `conversations.db`). Applied via the standard
`_MIGRATIONS` idempotent pattern.

**Persistence path (CORRECTED from original §10):**

The original §10 assumed the CoherenceGate's accept path
writes the belief to `beliefs.db`. **That assumption was
incorrect.** The gate routes decisions; callers own
persistence after ACCEPT, following the fountain crystallizer
pattern.

CN's INSERT pattern (post-gate-ACCEPT):

```sql
INSERT OR IGNORE INTO beliefs (
  content, confidence, branch_id, problem_id, tags, ...
) VALUES (?, ?, ?, ?, ?, ...)
```

If the content already exists (UNIQUE constraint), the INSERT
is silently ignored, and CN follows up with:

```sql
UPDATE beliefs
SET problem_id = ?
WHERE content = ? AND problem_id IS NULL
```

This means an existing belief whose content matches a
CN-accepted candidate gets retroactively tagged with the
problem_id. Semantically: *"this existing belief is also a
candidate answer to this problem."* This is consistent with
CN's role of retrieving existing beliefs and proposing them
as candidates (§1).

**The `gate_decisions` table** captures full packet metadata
per decision (including `problem_id`), providing an audit
trail of all CN submissions across all four outcomes.

---

## §7 Problem-Flagging Lifecycle

### §7.1 Threshold

CN flags a problem for review when **3 accepted candidates**
accumulate for that problem_id (3 rows in `beliefs` with
`problem_id = N`). Threshold constant:
`_HAS_CANDIDATES_THRESHOLD = 3`.

Rationale: matches the corroboration threshold in HoldingZone
(Phase 23) and the gap_deflection trigger threshold in
TriggerDetector (TN-1). The "3 is meaningful" convention is
preserved across the faculty model.

Configurable at the class level.

### §7.2 Schema change

New table in `conversations.db`:

```sql
CREATE TABLE IF NOT EXISTS review_queue (
  id          INTEGER PRIMARY KEY,    -- same id as the originating problem
  title       TEXT    NOT NULL,
  description TEXT,
  created_at  REAL    NOT NULL,       -- original problem creation time
  flagged_at  REAL    NOT NULL,       -- when the move happened
  tags        TEXT    NOT NULL DEFAULT '[]'  -- inline JSON, per Tag Protocol
);

CREATE INDEX IF NOT EXISTS idx_review_queue_flagged_at
ON review_queue(flagged_at DESC);
```

Note: `id` is **not** `AUTOINCREMENT`. The id is explicitly
specified at INSERT time to preserve the original problem's
identity (§7.4).

Migration applied via `_MIGRATIONS` idempotent pattern.

**Companion check on `open_problems`:** verify that
`open_problems.id` is declared `AUTOINCREMENT` so a future new
problem cannot collide with a moved problem's id. If not
currently AUTOINCREMENT, address during the build session
(SQLite requires a table rebuild for this change; assess
disruption).

### §7.3 Move semantics

When CN detects threshold reached (after a gate ACCEPT for a
counterfactual packet pushes the accepted-belief count for
`problem_id = N` to ≥ 3):

```python
# Inside a transaction (gatekeeper serializes writes):
row = conversations_reader.read(
    "SELECT id, title, description, created_at, tags "
    "FROM open_problems WHERE id = ?", (N,)
).one()

conversations_writer.write(
    "INSERT INTO review_queue "
    "(id, title, description, created_at, flagged_at, tags) "
    "VALUES (?, ?, ?, ?, ?, ?)",
    (row["id"], row["title"], row["description"],
     row["created_at"], now, row["tags"])
)

conversations_writer.write(
    "DELETE FROM open_problems WHERE id = ?", (N,)
)
```

**Tag inheritance:** the problem's tags (from
`open_problems.tags`) are read and carried into `review_queue.tags`
at move time. The tags remain the same string list — same
language, same meanings (Tag Protocol §8).

**Atomicity:** the SQLite gatekeeper serializes writes;
DELETE-then-INSERT against the same writer thread is
effectively atomic within a tick.

**Idempotency guard:** before performing the move, CN
checks whether the problem already exists in `review_queue`
(could happen on edge-case re-tick if the previous move
half-completed). If present, skip the move — the prior
move succeeded.

### §7.4 ID stability

The `review_queue` row preserves the original problem's id.
This means:

- `beliefs.problem_id = N` continues to resolve cleanly —
  the same id now refers to the row in `review_queue`
  instead of `open_problems`.
- Reverse flow (§7.5) and resolution flow (§7.6) round-trip
  cleanly without id translation.

### §7.5 Reverse flow (un-flag)

A flagged problem may be moved back to `open_problems`.
This is a manual operation, exposed via REST API (to be
specified in the build session — likely
`POST /api/review/{id}/unflag`).

The reverse move mirrors §7.3: DELETE from `review_queue`,
INSERT into `open_problems` with the same id (and
`last_touched_at` re-stamped to now). Tags travel back the
same way.

CN does not perform un-flag automatically. Only manual
human action triggers it.

### §7.6 Resolution flow

When a flagged problem is resolved, the resolution itself
is captured as a new belief in `beliefs.db`. The `review_queue`
row is then deleted (its purpose fulfilled).

**The resolution belief:**

- Lives in `beliefs.db` like any other belief
- Carries `problem_id = N` (the original problem's id)
- May carry a tag like `resolution` or similar (TBD in the
  Resolution Writer phase)
- Is the durable cognitive output of the entire
  problem-directed cycle

**This entire flow is downstream of Phase 25b.** CN does
not implement resolution capture. A future phase (the chat
surfacer + resolution writer) handles it. Phase 25b CN's
job ends when the problem lands in `review_queue`.

### §7.7 HUD surface

**None.** Per Jon's principle — *"the workings of NEX's mind
are its own"* — `review_queue` does not render on the HUD as
a panel. NEX surfaces flagged problems to the user via the
chat surfacer (a downstream phase), not via a dashboard
panel.

Admin/dev surfaces (e.g., direct SQL queries) remain
available; what's absent is a user-facing HUD panel.

---

## §8 Distinctness

**vs. throw-net:**
Throw-net fires when CoherenceGate accumulates 4 same-topic
REJECTs in 15 minutes, or when the gap gate accumulates 3
same-topic deflections in 30 minutes. It requires a stuckness
signal. CounterfactualNode fires on a 5-minute clock with no
stuckness signal — it runs during normal productive operation.
The two nodes are complementary: throw-net breaks stuckness
in the moment; CounterfactualNode works open problems in the
background.

**vs. fountain:**
The fountain generates thoughts spontaneously from the full
belief field. It has no target. CounterfactualNode generates
only in service of named problems. Every packet it produces
encodes its originating problem. The fountain's output is
shaped by spreading activation and the current attention
field; CN's output is shaped by what is relevant to a
specific problem title.

**vs. novel_association:**
NovelAssociation scans existing belief pairs for cross-branch
semantic similarity and writes edges between them. It
generates graph structure, not belief content. CN retrieves
existing beliefs and proposes them as new substrate entries
linked to a problem — it generates content (new rows in
beliefs), not graph structure.

---

## §9 Test Plan

**Unit tests** (`tests/test_counterfactual_node.py`):

1. `tick()` returns state dict with expected keys (name,
   tick_count, problems_processed, candidates_accepted)
2. `tick()` respects interval guard — no retrieval if elapsed < interval
3. `state()` returns correct shape after zero ticks
4. `open_problems` rows are filtered to `state='open'` only
   (no `has_candidates` filter — that state no longer exists)
5. ThoughtPacket carries correct `problem_id` in metadata
6. ThoughtPacket `source_node = "counterfactual.{problem_id}"`
7. Gate errors per packet are caught; do not abort the tick
8. **Move fires when accepted count reaches threshold.** The
   `open_problems` row is DELETED; a new row in `review_queue`
   appears with the same id, same title/description/created_at,
   and a fresh `flagged_at`.
9. **Move does NOT fire below threshold.** Below 3 accepted
   candidates, the problem stays in `open_problems`.
10. **Move does NOT re-fire** if the problem is already in
    `review_queue` (idempotency guard works).
11. **Tags are inherited** on move: `review_queue.tags` equals
    `open_problems.tags` at move time.
12. Schema migration adds `review_queue` table idempotently.
13. Schema migration adds `beliefs.problem_id` column idempotently.
14. SentienceNode protocol: `assertIsInstance(node, SentienceNode)`

**Manual sanity** (Phase 25b-build):

1. Seed a test problem via `POST /api/problems`
2. Wait one tick (≤ 5 min); verify candidates submitted to
   gate (`gate_decisions` rows with `source_node LIKE
   'counterfactual.%'`)
3. Verify accepted candidates have `problem_id` populated in
   `beliefs`
4. Accumulate 3 accepted candidates; verify problem moves
   to `review_queue` (gone from `open_problems`; new row
   in `review_queue`)
5. Verify tags inherited correctly
6. Smoke set (6 baseline queries) clean after node wiring

---

## §10 Open Items / Deferred to Build Session

**RefinementEngine import** — verify clean import from
`theory_x.stage_throw_net.refinement_engine`. Confirmed viable
in Phase 25b-spec diagnostic; should remain so.

**TimeFetch import** — same. Confirmed viable.

**`open_problems.id` AUTOINCREMENT** — verify the column
declaration. If missing, add via migration (SQLite requires
table rebuild for this change; assess during build session
whether disruption is acceptable, or defer with a documented
collision risk).

**REST endpoints for review_queue:**

- `GET /api/review` (list flagged problems)
- `GET /api/review/{id}` (single)
- `POST /api/review/{id}/unflag` (manual un-flag, §7.5)
- Resolution endpoint deferred to Resolution Writer phase

**Tag Protocol dependency:** this phase assumes the Tag
Protocol substrate is built (`TAG_PROTOCOL.md`). CN's INSERT
pipeline calls into the tag protocol writer when persisting
accepted beliefs. If Tag Protocol isn't built yet, build
it first.

**Candidate quality calibration:** RefinementEngine thresholds
were calibrated for throw-net's stuckness context.
Problem-title retrieval may produce a different candidate
distribution. Observe first production run; recalibrate if
pass rate is pathological.

**Goal-priority weighting:** goals are read as context input
(§2) but not used to order problem processing. Deferred to
a post-25b-build iteration.

---

*Document status: AMENDED DRAFT — awaiting Jon's review and
greenlight before commit. Implementation session (Phase
25b-build) begins after this document and `TAG_PROTOCOL.md`
are both committed.*
