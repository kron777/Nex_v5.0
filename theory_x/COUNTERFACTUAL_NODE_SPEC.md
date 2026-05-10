# CounterfactualNode — Phase 25b Specification

Foundational spec per DOCTRINE §1. Defines CounterfactualNode
(DOCTRINE §5 row 10b, Option γ). Written before implementation.
Implementation begins Phase 25b-build (separate session).

Created: 2026-05-10. Design decisions locked in Phase 25b-spec
session with Jon. Six Q-new decisions from Phase 25b-prep
diagnose are the authoritative source for this document.

---

## §1 Purpose

CounterfactualNode is a proactive, problem-directed generative
SentienceNode. On a 5-minute clock, it reads NEX's open
problems, retrieves beliefs relevant to each problem, and
submits them as candidate answers through the Coherence Gate.
Accepted candidates enter the belief substrate tagged with the
originating problem's ID. When enough candidates accumulate for
a problem, the problem is marked for human review.

The psychological function being realized is generative
problem-directed thinking: the capacity to hold an open
question and continuously surface candidate answers from
one's accumulated knowledge, without being stuck or prompted.

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
between them — it does not generate new belief content. CounterfactualNode
retrieves existing beliefs as candidates and submits them to
the gate as potential new beliefs, tagged for a problem.

---

## §2 Inputs

CounterfactualNode reads three substrate sources. It holds no
references to other SentienceNodes — all reads go through
Reader objects per DOCTRINE §3.

**Open problems.** CounterfactualNode reads the open_problems
table in conversations.db. It processes only rows where
`state IN ('open', 'has_candidates')` — both active states.
Closed problems are skipped. The problem title is the primary
input to the retrieval step (§5).

**Active goals.** CounterfactualNode reads the goals table in
conversations.db (`state = 'open'`) for context. In Phase
25b-build, goals are not used directly in retrieval — they
are available for future weighting (e.g., prioritize problems
linked to active goals). This connection is deferred to a
post-build iteration.

**Beliefs.** CounterfactualNode reads beliefs.db for candidate
retrieval (§5). It uses the beliefs Reader only. It does not
write to beliefs directly — all belief writes go through the
CoherenceGate accept path.

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
    - `problem_id`: INTEGER — the open_problems.id of the
      problem this packet was generated for (Q-new-1)
    - `counterfactual_score`: the RefinementEngine score for
      this candidate (0–6)

Every ThoughtPacket is submitted to CoherenceGate.check().
The gate applies one of four outcomes: ACCEPT, REJECT, HOLD,
RESHAPE. CounterfactualNode does not inspect the outcome —
gate routing is the gate's responsibility per DOCTRINE §7.

When a ThoughtPacket is ACCEPTed, the gate's accept path
writes the belief to beliefs.db. The `problem_id` field from
the ThoughtPacket's metadata is written to the
`beliefs.problem_id` column (§6). This is the load-bearing
linkage between a generated candidate and its origin problem.

---

## §4 Tick Mechanics

**Interval**: 300 seconds (5 minutes). Same as ThrowNetMonitor
and HoldingZoneResolver. Consistent daemon-thread cadence
across the faculty model (Q-new-3 = a).

**Lifecycle**: CounterfactualNode follows the NovelAssociation
pattern. tick() contains an interval guard:

```
if elapsed since last run < _TICK_INTERVAL_S: return state()
```

Heavy work (retrieval + gate submission) runs only when the
interval has elapsed. tick() itself is always fast.

start_loop() spawns a daemon thread (name=
`"counterfactual_node"`). stop() sets the stop event.
Registration follows run.py step 9e pattern (same as
ThrowNetMonitor).

**Per-tick budget**: all candidates that survive the
RefinementEngine threshold are submitted to the gate. There is
no hard cap per problem per tick (Q-new-4 = c). In practice the
candidate pool per problem title is bounded by TimeFetch's
retrieval cap (40 raw candidates → top scored by RefinementEngine).
This is not unbounded in the pathological sense — it is
"unbounded by an arbitrary policy cap" while remaining bounded
by the retrieval pool size.

**Ordering**: problems are processed in `created_at ASC` order
(oldest open problem first). This is a consistent default;
goal-priority weighting is deferred.

---

## §5 Generation Strategy

**Retrieval** (Q-new-5 = a): extract content words from the
problem title using the same stopword strip established in
TriggerDetector (TN-1). Pass the resulting keyword string to
`TimeFetch.run(constraint)`. TimeFetch sweeps four substrate
sources (beliefs, novel_association_log, held_thoughts,
arc_notes) and returns up to 40 raw candidates.

Title-only retrieval starts immediately on current substrate.
All five production open problems have empty descriptions and
observations. When descriptions are populated in the future,
the keyword string can be extended to include description
tokens without any code change to CounterfactualNode — the
caller constructs the constraint string; TimeFetch is
indifferent to its origin.

**Scoring**: pass raw candidates through `RefinementEngine.run()`.
RefinementEngine is already built (Phase 25a TN-3) and importable
without throw-net dependencies. The same R1–R6 scoring on
0–6 scale applies. Candidates with score ≥ 3 (buildable
threshold) are submitted to the gate. Candidates below 3 are
discarded.

**reshape_hint**: candidates with score < 5 carry
`metadata['reshape_hint'] = True`, activating Phase 24's
RESHAPE path. Same D5 calibration as throw-net (score < 5 on
0–6 scale). This is not a CounterfactualNode-specific rule —
it is the D5 convention applied uniformly across all nodes
that use RefinementEngine.

---

## §6 Problem-Candidate Linkage

The connection between an accepted belief and its origin
problem is stored in the beliefs table (Q-new-6 = b).

**Schema change required:**

```sql
ALTER TABLE beliefs ADD COLUMN problem_id INTEGER;
```

Nullable. No FK constraint (beliefs.db does not reference
conversations.db; the link is a logical reference only).
Applied via the standard `_MIGRATIONS` idempotent pattern
in `substrate/init_db.py`.

**Flow:**

1. CounterfactualNode puts `problem_id` in ThoughtPacket.metadata.
2. ThoughtPacket passes through CoherenceGate.
3. On ACCEPT: the gate's accept path extracts `problem_id`
   from the packet's metadata and writes it to
   `beliefs.problem_id` on INSERT.
4. On REJECT/HOLD/RESHAPE: `problem_id` is not persisted to
   beliefs (the belief does not enter the substrate).

The `gate_decisions` table already captures full packet
metadata per decision — `problem_id` will appear there for
all four outcomes as part of the existing metadata column.
This provides an audit trail of all counterfactual submissions
(accepted or not) keyed by problem.

---

## §7 Problem State Lifecycle

**States** (open_problems.state):

| State | Meaning |
|---|---|
| `open` | Problem is active; no accepted candidates yet, or manually reset |
| `has_candidates` | One or more accepted candidates exist; flagged for human review |
| `closed` | Problem resolved; only manual transition |

`has_candidates` is a new state, not present in the current
schema. The build session adds it to the application layer;
no schema change is required (state is a TEXT column with no
CHECK constraint).

**Trigger threshold** (not answered by Q-new questions —
proposed here):

CounterfactualNode marks a problem `has_candidates` when
**3 accepted candidates** accumulate for that problem_id
(i.e., 3 rows in beliefs with `problem_id = N`). Threshold
constant: `_HAS_CANDIDATES_THRESHOLD = 3`.

Rationale: 3 matches the corroboration threshold in
HoldingZone (Phase 23) and the gap_deflection trigger
threshold in TriggerDetector (TN-1). Using a consistent
"3 is meaningful" convention across the faculty model avoids
arbitrary per-node magic numbers.

The threshold is configurable at the class level. If
production observation shows 3 fires too quickly (or too
slowly) for useful review, it is a one-line change.

**Transition into has_candidates:**

After each gate ACCEPT for a counterfactual packet,
CounterfactualNode counts accepted beliefs for the
originating problem:

```sql
SELECT COUNT(*) FROM beliefs WHERE problem_id = ?
```

If count >= _HAS_CANDIDATES_THRESHOLD and problem.state
= 'open', CounterfactualNode writes:

```sql
UPDATE open_problems SET state='has_candidates',
  last_touched_at=? WHERE id=?
```

CounterfactualNode does not transition problems already in
`has_candidates` — the state is sticky until manually changed.

**HUD visibility**: the problems panel on the HUD currently
displays problem state. `has_candidates` will appear as a
distinct visual state (implementation detail for the build
session — exact label and styling are UI decisions).

**Reverse transition** (has_candidates → open):

Manual only. Via the existing REST API for problems
(`POST /api/problems/{id}` with `state='open'`). No automatic
revert. Rationale: `has_candidates` is a signal to Jon that
something worth reviewing exists — auto-reverting would erase
that signal without human acknowledgment. If candidates fade
from the belief graph (e.g., via tier decay or deletion),
the state does not auto-revert. The state records that
candidates were generated, not that they still persist.

**Forward transition** (has_candidates or open → closed):

Manual only. Via `POST /api/problems/{id}/resolve` or
equivalent. CounterfactualNode stops generating for closed
problems (closed rows are filtered out of the problem list
at the start of each tick).

---

## §8 Distinctness

**vs. throw-net:**
Throw-net fires when CoherenceGate accumulates 4 same-topic
REJECTs in 15 minutes, or when the gap gate accumulates 3
same-topic deflections in 30 minutes. It requires a stuckness
signal. CounterfactualNode fires on a 5-minute clock with no
stuckness signal — it runs during normal productive operation.
Throw-net's topic is the rejected or deflected topic from
recent conversation. CounterfactualNode's topic is drawn from
durable named open problems, not from conversation state.
The two nodes are complementary: throw-net breaks stuckness
in the moment; CounterfactualNode works open problems in the
background.

**vs. fountain:**
The fountain generates thoughts spontaneously from the full
belief field. It has no target — a given fountain thought may
be about anything in the substrate. CounterfactualNode
generates only in service of named problems. Every packet it
produces encodes its originating problem. The fountain's
output is shaped by spreading activation and the current
attention field; CounterfactualNode's output is shaped by
what is relevant to a specific problem title.

**vs. novel_association:**
NovelAssociation scans existing belief pairs for cross-branch
semantic similarity and writes synthesises edges between them.
It generates graph structure (edges), not new belief content.
CounterfactualNode retrieves existing beliefs and proposes
them as new substrate entries linked to a problem — it
generates content (new rows in beliefs), not graph structure.

---

## §9 Test Plan

**Unit tests** (`tests/test_counterfactual_node.py`):

1. tick() returns state dict with expected keys (name,
   tick_count, problems_processed, candidates_accepted)
2. tick() respects interval guard — no retrieval if elapsed < interval
3. state() returns correct shape after zero ticks
4. Closed problems are skipped during tick
5. ThoughtPacket carries correct problem_id in metadata
6. ThoughtPacket source_node = `"counterfactual.{problem_id}"`
7. Gate errors per packet are caught; do not abort the tick
8. has_candidates transition fires when accepted count
   reaches threshold
9. has_candidates transition does NOT fire below threshold
10. has_candidates transition does NOT re-fire for a problem
    already in has_candidates state
11. Schema migration adds problem_id column idempotently
12. SentienceNode protocol: assertIsInstance(node, SentienceNode)

**Manual sanity** (Phase 25b-build):

1. Seed a test problem via POST /api/problems
2. Wait one tick (≤ 5 min) — verify candidates submitted to gate
   (gate_decisions rows with source_node LIKE 'counterfactual.%')
3. Verify accepted candidates have problem_id populated in beliefs
4. Accumulate 3 accepted candidates — verify problem.state = 'has_candidates'
5. Verify closed problems produce zero gate submissions per tick
6. Smoke set (6 baseline queries) clean after node wiring

---

## §10 Open Items Deferred to Build Session

**Gate accept path extension**: the CoherenceGate accept path
currently writes beliefs via a standard INSERT. It needs to
read `problem_id` from `ThoughtPacket.metadata` and include
it in the INSERT. This is the only code path change required
outside the CounterfactualNode module itself.

**RefinementEngine import**: verify `RefinementEngine` is
importable from `theory_x.stage_throw_net.refinement_engine`
without pulling in throw-net runtime dependencies. If
circular or heavyweight, a shared location for RefinementEngine
may be needed (e.g., `theory_x.stage_gate.refinement`).
Diagnose at build start.

**TimeFetch import**: same question as RefinementEngine.
TimeFetch lives in `theory_x.stage_throw_net.time_fetch`.
If the import is clean, reuse directly. If not, factor out
the retrieval logic.

**HUD state display**: `has_candidates` is a new problem state.
The problems panel in `gui/server.py` and the frontend need to
render it distinctly from `open`. UI label and styling are
build-session decisions.

**Goal-priority weighting**: goals are read as context input
(§2) but not yet used to order problem processing. Deferring
the weighting logic (e.g., process problems with linked active
goals first) to a post-25b-build iteration.

**Candidate quality calibration**: RefinementEngine thresholds
(R1 ≥ 5, R2 ≥ 3) were calibrated for throw-net's stuckness
context. Problem-title retrieval may produce a different
candidate distribution. Observe first production run and
recalibrate if the pass rate is pathological (all pass or
all fail).

---

*Document status: DRAFT — awaiting Jon's review and greenlight
before commit. Implementation session (Phase 25b-build) begins
after this document is committed.*
