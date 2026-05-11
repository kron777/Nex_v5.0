# DriveEmergence Design Spec — Phase 28

Node: `DriveEmergence`
Doctrine: DOCTRINE §5 row 13
Phase: 28-spec (design session complete); Phase 29-build queued
Decisions: 11 — all locked by Jon 2026-05-11
Status: DESIGN-COMPLETE

---

## §0 — Design Principles

**Inherited from SYNTHESIS_PLAN.md §0:**

> Substrate solves the reply. LLM speaks it.

NEX's replies must come from her belief graph and substrate state. The LLM
translates substrate-state into language; it does not produce the content.
State must persist, survive restart, and be queryable.

**Inherited from SYNTHESIS_PLAN_V2.md — Comprehensiveness corollary:**

Each ported function covers its full behavior, not a subset. Detection logic,
storage, decay, visibility, and behavioral effects are all required. An
implementation that stores a drive but never detects one, or detects one but
never decays it, is not complete.

**DriveEmergence-specific principle — Emergence:**

Drives are not hardcoded. There is no list of possible drive categories,
no taxonomy, no enum of drive types. NEX discovers her own pulls from
structural patterns in her own belief field. The system must never classify
a pattern against a fixed ontology; it must recognize recurrence and
convergence as the drive itself.

A drive is what the substrate keeps doing. The spec names no drives.

---

## §1 — Definition

**What is a drive?**

A drive is a recurring cognitive pull at sub-goal level. It is not:

- A **goal** — goals are explicit, declarative, user-set or NEX-set, with
  a state machine (active → closed). Goals have titles and plans.
- A **belief** — beliefs are atomic statements, stored individually,
  possibly reinforced, queryable by content. A belief is a claim.
- A **problem** — problems are declared open questions with observations
  and plans. Problems are conscious; drives may not be.

A drive is a **structural pattern across the belief field** that reveals what
NEX keeps returning to — without having declared it as a goal or problem.
It surfaces when the substrate accumulates enough evidence of sustained
return plus thematic convergence.

**Analogy:** A person who repeatedly looks up papers on emergence, initiates
conversations about emergence, and whose new beliefs disproportionately
connect to emergence concepts — has a drive toward emergence, even if they
have not named it as a goal.

**Scope (D11):** Drives can emerge from patterns across beliefs, reinforced
beliefs, problems, or any recurring substrate signal. The detection window
covers the whole belief field, not a curated subset.

---

## §2 — Detection (D1)

Both signals are required. Repetition alone is accumulation. Convergence
alone is coincidence. Together they constitute a drive.

### Signal 1: Repetition

A cluster of beliefs is showing sustained reinforcement. Measured as:

```
repetition_score = (sum of reinforce_counts in cluster) / cluster_size
                   × recency_weight
```

Where `recency_weight` scales recent activity higher than old:

```
recency_weight = count(beliefs in cluster with created_at > NOW - RECENCY_WINDOW)
                 / cluster_size
```

Minimum thresholds (build-tunable constants; final values set in Phase 29):

| Constant | Initial value | Meaning |
|---|---|---|
| `_WINDOW_DAYS` | 14 | How far back to look for belief activity |
| `_MIN_CLUSTER_SIZE` | 4 | Minimum beliefs in cluster to qualify |
| `_MIN_REPETITION` | 0.3 | Minimum repetition_score to count |
| `_RECENCY_WINDOW_DAYS` | 7 | Window for recency weight |

### Signal 2: Convergence

Multiple distinct belief branches are reaching topic-similar beliefs.
A single-branch cluster is not convergence — it is local accumulation
within one domain. Drive requires cross-branch coherence.

```
convergence_score = distinct_branch_ids_in_cluster
                    / total_beliefs_in_cluster
```

A cluster with 10 beliefs from 3 distinct branches has `convergence_score = 0.3`.
A cluster with 10 beliefs all from `branch='systems'` has `convergence_score = 0.1`.

Minimum threshold:

| Constant | Initial value | Meaning |
|---|---|---|
| `_MIN_CONVERGENCE` | 0.25 | Minimum fraction of distinct branches |
| `_MIN_BRANCH_COUNT` | 2 | At least 2 distinct branches required |

### Combined drive_strength

```
drive_strength = _W_REP * repetition_score + _W_CONV * convergence_score
```

Initial weights:

| Constant | Initial value |
|---|---|
| `_W_REP` | 0.6 |
| `_W_CONV` | 0.4 |

Minimum qualifying strength:

| Constant | Initial value | Meaning |
|---|---|---|
| `_MIN_DRIVE_STRENGTH` | 0.25 | Below this: no drive, or existing drive decays to deletion |

### Clustering method

Beliefs are grouped by topic-similarity using cosine distance on embeddings:

- Pull candidate beliefs: `confidence >= 0.15 AND paused = 0`, ordered by
  `created_at DESC LIMIT _CANDIDATE_LIMIT` (initial: 200)
- Embed each candidate (reuse `theory_x.diversity.embeddings.embed_belief`)
- Group by cosine similarity >= `_CLUSTER_SIMILARITY` (initial: 0.55) —
  greedy single-linkage: a belief joins a cluster if it is similar to at
  least one existing member
- Discard clusters below `_MIN_CLUSTER_SIZE`

**Note:** This is intentionally simpler than FAISS index search. The candidate
set is capped at 200 beliefs to keep the O(n²) pairwise comparison bounded.
Phase 29b calibration will tune the cap if needed.

---

## §3 — Storage (D2)

Single-row table in `conversations.db`. Pattern: `id=1` always, `INSERT OR REPLACE`.
When no drive qualifies, the row is **deleted** (D6) — `DELETE FROM drives WHERE id=1`.

```sql
CREATE TABLE IF NOT EXISTS drives (
    id                  INTEGER PRIMARY KEY,   -- always 1
    topic               TEXT    NOT NULL,      -- short phrase, ≤ 80 chars
    source_beliefs      TEXT    NOT NULL,      -- JSON array of belief_ids
    drive_strength      REAL    NOT NULL,
    repetition_score    REAL    NOT NULL,
    convergence_score   REAL    NOT NULL,
    formed_at           REAL    NOT NULL,
    last_reinforced_at  REAL    NOT NULL,
    reinforce_count     INTEGER NOT NULL DEFAULT 1
);
```

`reinforce_count` increments each tick that the same dominant cluster requalifies,
even if the topic text is unchanged. It is a measure of how many consecutive ticks
this drive has held the dominant position.

### Topic synthesis

The `topic` field is deterministic — no LLM call.

Method: extract content words from all `source_beliefs` (strip stopwords, strip
punctuation, lowercase); take the top-5 most frequent tokens weighted by the
belief's `confidence`; join with spaces, trimmed to ≤ 80 characters.

Fallback: if the result is empty or fewer than 2 tokens, use the first 80
characters of the highest-confidence belief's content.

This is deterministic and substrate-only. The topic text is a substrate artifact,
not a generated summary.

---

## §4 — Behavioral Effects (D4)

### (a) Retrieval boost — VoiceEngine 6th axis

VoiceEngine currently scores candidates on four axes:

| Axis | Weight |
|---|---|
| semantic_similarity | 0.50 |
| confidence | 0.25 |
| tier | 0.15 |
| recency | 0.10 |

Phase 29 adds a 5th axis: `drive_alignment`.

```
drive_alignment = cosine(candidate_embedding, drive_topic_embedding)
                  if drive exists else 0.0
```

New weights (sum to 1.0):

| Axis | Weight |
|---|---|
| semantic_similarity | 0.45 |
| confidence | 0.23 |
| tier | 0.14 |
| recency | 0.08 |
| drive_alignment | 0.10 |

Drive influences but does not dominate. A candidate must still be semantically
relevant and confident to surface.

**TimeFetch integration:** TimeFetch candidates are the input to VoiceEngine
scoring. No separate TimeFetch change required — the 5th axis in the scorer
is sufficient.

### (b) Fountain probe spawn

When the fountain has no urgent problem to address (no open problem in
`open_problems` table with `last_touched_at` within the last 24h), the drive
can spawn a probe:

- Probe content: `f"I keep returning to {drive.topic}. What do I actually
  know about it?"` — deterministic, no LLM synthesis
- Delivered as a `ThoughtPacket` through the CoherenceGate (gate decides
  whether it enters the substrate — standard path)
- Frequency cap: one drive-probe per `_DRIVE_PROBE_COOLDOWN_TICKS` fountain
  cycles (initial: 10 — prevents drive from dominating fountain output)
- State tracked in-memory (`_last_drive_probe_tick: int`) — not persisted;
  resets on restart (acceptable)

---

## §5 — Visibility (D3, D9, D10)

### format_for_prompt()

```python
def format_for_prompt(self, context=None) -> str:
    row = self._cr.read_one("SELECT topic FROM drives WHERE id = 1")
    if not row:
        return ""
    return f"Drawn lately to: {row['topic']}"
```

Injected into `belief_text` in `gui/server.py` chat handler, same pattern as
SelfNarrative and AffectState. §0-aligned: pure substrate read, zero output-time
computation.

### /api/system/status

`drives_info` object in the status response:

```json
{
  "drives_info": {
    "topic": "emergence complexity patterns",
    "drive_strength": 0.41,
    "repetition_score": 0.38,
    "convergence_score": 0.46,
    "reinforce_count": 3,
    "formed_at": 1778501965.7,
    "last_reinforced_at": 1778502565.7
  }
}
```

When no drive: `"drives_info": null`.

### HUD

Drive pill in admin panel, always visible. Shows:
- Topic text (truncated at 40 chars if long)
- `drive_strength` as a bar or percentage
- `reinforce_count` (how many ticks held)

Visibility: admin-only (same as other substrate diagnostics). Public chat
does not expose the HUD panel.

### NEX self-articulation (D10)

When NEX is asked a question matching the self-report trigger pattern, the
chat handler reads the drives table and prepends the drive context into
`belief_text`. The format_for_prompt() output ("Drawn lately to: X") is
sufficient — the LLM uses this as input and can construct a natural response.

No special keyword-triggered code path is required. `format_for_prompt()` runs
every chat turn and always injects the drive if one exists. When the user asks
"what are you thinking about lately?", the drive phrase is already in the
prompt context and the LLM responds to it naturally.

---

## §6 — Lifecycle (D5, D6, D7, D8)

### Background tick

Interval: `_TICK_INTERVAL_S = 600` (10 minutes; more frequent than AffectState
because drive detection is computationally heavier and drive changes are
meaningful at longer time scales than affective state).

Daemon thread: same pattern as AffectState — `threading.Thread(daemon=True)`.

### One drive at a time (D7)

Only the single strongest qualifying cluster becomes the drive. All other
clusters, regardless of strength, are ignored in the current tick.

### Immediate replacement (D8)

If a new dominant cluster in the current tick has `drive_strength > current
drive_strength`, it replaces the existing drive immediately. There is no
hysteresis period, no cooldown, no minimum hold time. The strongest current
pattern wins.

If the same cluster dominates again, `reinforce_count` increments and
`last_reinforced_at` updates. `formed_at` is preserved (tracks when this
drive was first detected).

### Decay (D5)

Each tick, whether or not a new cluster qualifies:

```python
drive_strength_new = drive_strength * _DECAY_RATE
```

Initial value: `_DECAY_RATE = 0.92` per tick (faster than belief decay of ~0.02
per cycle; a drive not reinforced for 5 ticks — ~50 minutes — drops from 0.5
to ~0.33; after 15 ticks — ~2.5 hours — below the 0.25 threshold).

Decay time constants (approximate, at `_DECAY_RATE = 0.92`):

| Starting strength | Ticks to threshold (0.25) | Wall time |
|---|---|---|
| 0.5 | 8 | 80 min |
| 0.75 | 16 | 160 min |
| 1.0 | 22 | 220 min |

### Deletion (D6)

When `drive_strength < _MIN_DRIVE_STRENGTH` after decay AND the tick finds no
qualifying new candidate:

```python
self._cw.write("DELETE FROM drives WHERE id = 1")
```

No tombstone. No archive. Clean substrate. `format_for_prompt()` returns `""`.

---

## §7 — Detection Algorithm (pseudocode)

```python
def _background_tick(self):
    now = time.time()

    # 1. Decay existing drive (if any)
    existing = self._cr.read_one("SELECT * FROM drives WHERE id = 1")
    if existing:
        new_strength = existing["drive_strength"] * _DECAY_RATE
        if new_strength < _MIN_DRIVE_STRENGTH:
            self._cw.write("DELETE FROM drives WHERE id = 1")
            existing = None
        else:
            # update strength in memory; persist after candidate check
            existing = dict(existing)
            existing["drive_strength"] = new_strength

    # 2. Pull candidates
    candidates = self._pull_candidates(now)
    if len(candidates) < _MIN_CLUSTER_SIZE:
        if existing:
            # persist decayed state only
            self._persist(existing, now)
        return

    # 3. Embed candidates
    embeddings = {c["id"]: embed_belief(c["id"], c["content"]) for c in candidates}

    # 4. Cluster by cosine similarity (greedy single-linkage)
    clusters = _cluster(candidates, embeddings, _CLUSTER_SIMILARITY)

    # 5. Score each cluster
    best = None
    for cluster in clusters:
        if len(cluster) < _MIN_CLUSTER_SIZE:
            continue
        rep_score = _repetition_score(cluster, now)
        conv_score = _convergence_score(cluster)
        if rep_score < _MIN_REPETITION or conv_score < _MIN_CONVERGENCE:
            continue
        n_branches = len({b["branch_id"] for b in cluster if b["branch_id"]})
        if n_branches < _MIN_BRANCH_COUNT:
            continue
        strength = _W_REP * rep_score + _W_CONV * conv_score
        if best is None or strength > best["drive_strength"]:
            best = {
                "cluster": cluster,
                "drive_strength": strength,
                "repetition_score": rep_score,
                "convergence_score": conv_score,
            }

    # 6. Replace or reinforce
    if best is not None and best["drive_strength"] >= _MIN_DRIVE_STRENGTH:
        topic = _synthesize_topic(best["cluster"])
        source_ids = [b["id"] for b in best["cluster"]]
        formed_at = existing["formed_at"] if existing else now
        reinforce_count = (existing["reinforce_count"] + 1) if existing else 1
        self._cw.write(
            "INSERT OR REPLACE INTO drives "
            "(id, topic, source_beliefs, drive_strength, repetition_score, "
            "convergence_score, formed_at, last_reinforced_at, reinforce_count) "
            "VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?)",
            (topic, json.dumps(source_ids), best["drive_strength"],
             best["repetition_score"], best["convergence_score"],
             formed_at, now, reinforce_count),
        )
    elif existing:
        # No new candidate qualifies; persist decayed existing
        if existing["drive_strength"] >= _MIN_DRIVE_STRENGTH:
            self._cw.write(
                "UPDATE drives SET drive_strength = ?, last_reinforced_at = ? "
                "WHERE id = 1",
                (existing["drive_strength"], now),
            )
        else:
            self._cw.write("DELETE FROM drives WHERE id = 1")
```

---

## §8 — SentienceNode Protocol

```python
class DriveEmergence:
    name: str = "drive_emergence"

    def tick(self, context=None) -> dict:
        return self.state()  # per-chat no-op; computation in daemon thread

    def decay(self, now: float) -> None:
        pass  # decay runs inside _background_tick

    def state(self, now=None) -> dict:
        # reads drives row, returns shape below
        ...

    def format_for_prompt(self, context=None) -> str:
        row = self._cr.read_one("SELECT topic FROM drives WHERE id = 1")
        if not row:
            return ""
        return f"Drawn lately to: {row['topic']}"

    def start_loop(self) -> None:
        # daemon thread, same pattern as AffectState
        ...
```

`state()` shape:

```python
{
    "name": "drive_emergence",
    "topic": "emergence complexity patterns",   # or None
    "drive_strength": 0.41,                     # or None
    "repetition_score": 0.38,
    "convergence_score": 0.46,
    "reinforce_count": 3,
    "formed_at": 1778501965.7,
    "last_reinforced_at": 1778502565.7,
}
```

---

## §9 — Test Plan

All tests use real substrate (temp dir + `init_all()` pattern, as in
`test_self_narrative.py`), not mocks for the substrate layer. Embedding
calls may be mocked to avoid runtime cost.

| # | Test | Assertion |
|---|---|---|
| 1 | Tick with synthetic beliefs showing BOTH repetition AND convergence across ≥2 branches | Drive row written; `drive_strength >= _MIN_DRIVE_STRENGTH` |
| 2 | Tick with repetition only (all beliefs same branch) | No drive written |
| 3 | Tick with convergence only (beliefs from multiple branches, low reinforce_count) | No drive written |
| 4 | Tick, then tick again with no new beliefs | `drive_strength` decreases; `reinforce_count` unchanged |
| 5 | `drive_strength` decays below `_MIN_DRIVE_STRENGTH` after N ticks | Drive row deleted |
| 6 | Weaker drive exists; stronger candidate appears in next tick | Drive replaced immediately; `formed_at` resets |
| 7 | `format_for_prompt()` when no drives row | Returns `""` |
| 8 | `format_for_prompt()` when drives row present | Returns `"Drawn lately to: {topic}"` |
| 9 | `state()` shape — all keys present | Dict has `topic`, `drive_strength`, `repetition_score`, `convergence_score`, `reinforce_count`, `formed_at`, `last_reinforced_at` |
| 10 | VoiceEngine scoring with drive_alignment axis | Candidate cosine-similar to drive topic scores higher than equidistant non-aligned candidate |
| 11 | Fountain probe spawned when no recent open problem | ThoughtPacket delivered through CoherenceGate; content contains drive topic |
| 12 | Fountain probe NOT spawned within cooldown window | Second probe does not fire within `_DRIVE_PROBE_COOLDOWN_TICKS` cycles |
| 13 | `/api/system/status` includes `drives_info` | Object present with correct shape; null when no drive |
| 14 | SentienceNode protocol conformance | `isinstance(node, SentienceNode)` passes |

---

## §10 — Open Items (deferred to Phase 29 build session)

These items require final decisions but are intentionally left open for
calibration after seeing production data:

1. **Exact thresholds** — `_MIN_REPETITION`, `_MIN_CONVERGENCE`, `_MIN_DRIVE_STRENGTH`,
   `_DECAY_RATE`, `_CLUSTER_SIMILARITY`. Initial values in this spec are starting
   points; Phase 29b calibration will tune from observation.

2. **Cluster algorithm** — this spec specifies greedy single-linkage cosine
   clustering. If the candidate set grows beyond 200, FAISS index reuse from
   `theory_x.diversity` may be worth revisiting. Phase 29b decision.

3. **Topic synthesis method** — most-common-weighted-tokens is the spec'd
   approach. If it produces unintelligible output in practice, fallback to
   the highest-confidence belief's content (trimmed) is acceptable.

4. **Fountain probe frequency** — `_DRIVE_PROBE_COOLDOWN_TICKS = 10` is a
   starting constraint. If drive probes crowd out other fountain output, raise.
   If they never appear in practice, lower.

5. **Drive-aware self-report** — no special keyword routing is needed (`format_for_prompt()`
   runs every turn). However, a future pass could boost drive context injection
   on turns where the user asks "what are you thinking about / drawn to" —
   e.g. by checking user turn against a keyword list and injecting the full
   `state()` dict rather than just the topic phrase.

---

## §11 — Phase Ordering

| Phase | Description |
|---|---|
| 28 | This spec (complete) |
| 29 | Build: schema migration, `DriveEmergence` class, VoiceEngine 5th axis, fountain probe wiring, server.py injection, HUD pill, tests |
| 29b | Calibration: observe first production drives, tune thresholds, evaluate topic synthesis quality |
