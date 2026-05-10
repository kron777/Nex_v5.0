# SELF_NARRATIVE_SPEC.md
# Phase 26-spec — SelfNarrative
# Status: DRAFT — awaiting Phase 26-build

---

## §1 Purpose

SelfNarrative accumulates substrate-resident narrative entries when significant
cognitive events occur. It does **not** generate text at output time.

`format_for_prompt()` reads existing entries from the database and returns them
as-is. No synthesis. No LLM call. No inference at speak-time.

Aligned with DOCTRINE §0: **Substrate solves the reply. LLM speaks it.**

This is not autobiographical generation. It is autobiographical accumulation.
Background events write; the read path only returns what already exists. If no
relevant entries exist, `format_for_prompt()` returns an empty string.

SelfNarrative is DOCTRINE §5 row 11. It maps to S5.5's InternalNarrativeNode +
TemporalNarrativeNode by function (self-oriented narrative tracking) but not by
mechanism: S5.5's buffer-and-generate approach violates §0 and is not ported.

---

## §2 Substrate

**Table:** `narrative_log` in `conversations.db`

**Schema:**

```sql
CREATE TABLE IF NOT EXISTS narrative_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    content     TEXT NOT NULL,
    trigger     TEXT NOT NULL,
    source_id   INTEGER,
    created_at  REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_narrative_ts ON narrative_log(created_at DESC);
```

`trigger` values (v1): `'goal_complete'` | `'groove'`

`source_id` is the row id of the triggering record: `goals.id` for
`goal_complete`; `groove_alerts.id` for `groove`.

**Migration:** add to `substrate/init_db.py` `_MIGRATIONS["conversations"]`
dict as an idempotent `CREATE TABLE IF NOT EXISTS` entry. The schema already
uses this pattern (see `goals` migration at line 286).

**Boundedness:** No fade logic in v1. Growth rate is unknown before production
observation. A 90-day row age cutoff or size-based cap may be added in Phase
26b after observing actual write frequency. Until then the table is unbounded.

---

## §3 Write-triggers (v1 — two of five)

### Trigger 1: Goal completion

- **Fire point:** `stage8_goal_manager/goal_manager.py:111`
  (`UPDATE goals SET state='completed', completed_at=?`)
- **Threshold:** every completion writes — conservative for v1; no priority
  filter yet
- **Content shape:** `"I completed the goal: {goal.title}"`
- **`source_id`:** `goals.id` of the completed goal

### Trigger 2: Groove alert

- **Fire point:** `stage9_metacognition/metacognition.py:134`
  `_detect_groove()` — fires as `event_type = "groove"` during `tick()`
- **Threshold:** every detected groove writes — conservative for v1; a
  `severity` floor (e.g. ≥ 0.5) may be added in Phase 26b if noisy
- **Content shape:** `"I noticed I am repeatedly returning to {pattern}"`
  where `{pattern}` is `groove_alerts.pattern` from the triggering row
- **`source_id`:** `groove_alerts.id` of the triggering alert

### Wiring approach

`SelfNarrative` exposes a single public method:

```python
def write_narrative(self, content: str, trigger: str, source_id: int | None) -> None
```

This method writes one row to `narrative_log` and returns. No async, no daemon
thread, no side effects.

**GoalManager wiring:** `GoalManager.complete_goal()` calls
`self._narrative.write_narrative(...)` immediately after the `UPDATE` succeeds.

**Metacognition wiring:** `Metacognition.tick()` calls
`self._narrative.write_narrative(...)` for each new groove row returned by
`_detect_groove()`.

**Construction:** `SelfNarrative` is constructed once at startup in `run.py` (or
the equivalent top-level entry point). It is passed by reference to
`GoalManager` and `Metacognition` at their construction time, following the same
pattern as other shared services (e.g. `BeliefStore`). No module-level global;
constructor injection only.

---

## §4 Read path

**Method:** `SelfNarrative.format_for_prompt(context) -> str`

**Query:** reads the most recent `N` rows from `narrative_log` where the
`content` column matches the current topic.

**Default N:** 5

**Topic filter:** simple case-insensitive `LIKE` substring match between
`context.current_topic` and `narrative_log.content`. SQL:

```sql
SELECT content, created_at
FROM narrative_log
WHERE LOWER(content) LIKE LOWER('%' || ? || '%')
ORDER BY created_at DESC
LIMIT ?
```

If `context.current_topic` is absent or empty, the query runs without the
`WHERE` clause (returns most recent N regardless of topic).

**Return format:** each row as a bullet line:

```
- {content} ({age})
```

Where `{age}` is human-readable: `"Xm ago"`, `"Xh ago"`, `"yesterday"`,
`"X days ago"`. Computed from `created_at` relative to `now`.

**No rows:** returns empty string `""`. No fallback message, no synthesis, no
placeholder. Callers must handle the empty case.

---

## §5 SentienceNode shell

**Class:** `SelfNarrative(SentienceNode)`

Located at: `theory_x/stage_self_narrative/self_narrative.py` (new directory)

| Method | Behavior |
|--------|----------|
| `tick(context=None)` | no-op — writes happen via direct trigger calls, not tick |
| `decay(now)` | no-op for v1 — fade logic deferred to Phase 26b |
| `state(now=None)` | returns `{"narrative_count": int, "last_write_ts": float \| None}` |
| `format_for_prompt(context)` | reads narrative_log, returns bullet string or `""` |
| `write_narrative(content, trigger, source_id)` | inserts one row; called by GoalManager and Metacognition |

No `start_loop()`. No daemon thread. No `asyncio`. SelfNarrative holds one
SQLite connection to `conversations.db` (write-safe; follows the
`isolation_level=None` pattern per project SQLite discipline).

---

## §6 Distinctness

| Node | What it does | What SelfNarrative does NOT do |
|------|-------------|-------------------------------|
| ThrowNet | Reactive stuckness detection | Does not write narrative |
| Fountain | Spontaneous belief crystallization | Does not write to narrative_log |
| Metacognition | Detects cognitive patterns (grooves) | SelfNarrative records that the detection *happened* |
| GoalManager | Manages goal lifecycle | SelfNarrative records that a goal *was completed* |

SelfNarrative is pure: **write-on-event** + **read-at-prompt-time**. Nothing else.

---

## §7 Test plan

### Unit tests (`tests/test_self_narrative.py`)

- `write_narrative` inserts a row with correct `trigger`, `content`,
  `source_id`, and `created_at` within 1s of now
- `format_for_prompt` returns the most recent N rows that match the topic
- `format_for_prompt` returns `""` when no rows match topic
- `format_for_prompt` returns `""` when `narrative_log` is empty
- `tick(context)` is a no-op (no rows written, no exception)
- `decay(now)` is a no-op (no rows deleted, no exception)
- `state()` returns correct `narrative_count` after N writes
- `state()` returns `last_write_ts = None` when table is empty

### Manual sanity (Phase 26-build verification)

1. Complete a real goal via the API → inspect `narrative_log` for one new row
   with `trigger='goal_complete'` and `source_id = goals.id`
2. Wait for or trigger a groove alert → inspect `narrative_log` for one new
   row with `trigger='groove'` and `source_id = groove_alerts.id`
3. Run a chat turn on a topic matching a narrative entry → observe
   `format_for_prompt` output injected into `belief_text` in the prompt
4. Run a chat turn on a non-matching topic → confirm `format_for_prompt`
   returns `""` and no narrative bullets appear

### Smoke regression

Existing test suite (`pytest tests/`) passes unmodified after wiring.

---

## §8 Open items — deferred to Phase 26-build

| Item | Decision deferred to |
|------|---------------------|
| Topic filter: simple LIKE substring vs. embedding similarity | Phase 26-build — start simple, observe |
| Trigger 3: problem close (`problem_memory.py:145`) | Phase 26b — after v1 production observation |
| Trigger 4: gate ACCEPT on problem-relevant topic | Phase 26b — blocked on Phase 25b CounterfactualNode |
| Trigger 5: novel association (high-threshold variant) | Phase 26b — threshold tuning needed |
| `narrative_log` fade strategy (90-day row age? size cap?) | Phase 26b — after observing growth rate |
| HUD surface for recent narrative entries | Phase 26b — deferred |
| `source_id` typed FK enforcement | Phase 26-build — fine as nullable INTEGER for now |

---

*Authored: 2026-05-10 — Phase 26-spec*
*Implements: DOCTRINE §5 row 11*
*Depends on: SYNTHESIS_PLAN.md §0, §3 row 11, §4 Option β*
*Next: Phase 26-build (separate session)*
