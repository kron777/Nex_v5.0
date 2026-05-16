# Phase 6 — Sustained Attention: Design Document

**Date:** 2026-05-08  
**Module:** `theory_x/stage7_sustained/problem_memory.py`  
**DOCTRINE §5 node:** #5 Sustained Attention  
**Status:** ABSENT (table wired, always empty)

---

## 1. Module Audit

### `ProblemMemory` (problem_memory.py, 144 lines)

Well-written CRUD class. No `name`, `tick`, `decay`, `state` — not yet a SentienceNode.

| Method | Description |
|--------|-------------|
| `open(title, description)` | INSERT new problem, returns rowid |
| `observe(problem_id, observation)` | Append observation to JSON array |
| `update_plan(problem_id, plan)` | Update plan field |
| `close(problem_id)` | Mark state='closed', set resolved_at |
| `resume(problem_id)` | Return full problem dict, parse observations |
| `list_open()` | All open problems by last_touched_at DESC |
| `find_matching(query)` | Naive word-overlap match across open problems |
| `format_for_prompt(problem_id)` | Format one problem as injection block |

**`find_matching` quality:** Bag-of-words word-overlap. High false positive rate for short/common words. No IDF weighting. No stopword removal. Queries like "what do you think" will spuriously match any problem containing common English words.

### Schema (`open_problems` in conversations.db)

```sql
id              INTEGER PRIMARY KEY AUTOINCREMENT
title           TEXT NOT NULL
description     TEXT NOT NULL
state           TEXT NOT NULL DEFAULT 'open'
created_at      REAL NOT NULL
last_touched_at REAL NOT NULL
plan            TEXT NOT NULL DEFAULT ''
observations    TEXT NOT NULL DEFAULT '[]'   -- JSON array of {text, ts}
resolved_at     REAL
```

**Live row count: 0.** Table exists, schema is sound, no data.

---

## 2. Root Cause: Why Always Empty

**Single write path:** Only the explicit REST API writes to `open_problems`:
- `POST /api/problems` — opens a problem (requires JSON body with title+description)
- `POST /api/problems/<id>/observe` — appends observation
- `POST /api/problems/<id>/plan` — updates plan
- `POST /api/problems/<id>/close` — closes

No automatic path exists. Neither conversation turns, belief events, nor internal state changes ever call `problem_memory.open()`. The user must explicitly invoke the API.

**No trigger from belief graph.** Belief tensions, unsatisfied focal-set themes, or stale-but-high-confidence beliefs never emit a problem. The crystallizer checks `list_open()` to gate a context flag (`open_problems: bool`) but only reads — never writes.

**No conversation extraction.** No heuristic scans NEX responses for unresolved-inquiry markers ("I haven't figured out", "I'm still uncertain about") that could auto-open.

---

## 3. Integration Audit

### Read path (what already works when data exists)

```
api_chat()
  ↓
state.problem_memory.find_matching(prompt)
  ↓ (returns matching problems)
state.problem_memory.format_for_prompt(matching[0]["id"])
  ↓
belief_text += problem_text     # injected before LLM call — all routes, not INSIDE-gated
```

**Important: problem injection is NOT gated by route_result.side.** Unlike BSM which is INSIDE-only, open problem context fires on any matching query from any register. This is correct — a technical query can match an open technical problem.

### Crystallizer read path

`FountainCrystallizer.ambient_context()` calls `list_open()` → sets `open_problems: bool` in the context dict passed to fountain generators. The fountain can use this to modulate spontaneous thought generation. Currently `open_problems` is always `False`.

### SentienceNode gap

ProblemMemory has no `tick()`, `decay()`, `state()`, or `name` attribute. It is **not registered** in the Theory X process-lifetime SentienceNode registry. The HUD cannot observe it. The sentinel loop cannot heartbeat it.

---

## 4. Options

### Option A — Protocol only (recommended baseline)

Add SentienceNode protocol conformance to `ProblemMemory`. Keep manual-API-only population. `tick()` reads the table, `state()` reports count/age. `decay()` optionally auto-closes problems stale >30 days.

**What changes:**
- Add `name = "problem_memory"`, `_lock`, `_cache`, `tick()`, `decay()`, `state()` to ProblemMemory
- Register in `create_app()` after `build_state()` (same pattern as SelfModel/BSM)
- `tick()` calls `list_open()`, caches result, returns count + oldest age
- `decay(now)` auto-closes problems where `last_touched_at < now - 30*86400` (configurable)
- `state()` reports `{name, open_count, oldest_age_days, last_touched_age_s}`

**Result:** Node is DOCTRINE-compliant and HUD-visible. Injection still requires manual API population. The node reports that it exists and functions. Population remains a workflow concern.

**Risk:** Node always reports `open_count=0` until Jon uses the API — superficially identical to before. But it CAN work, it's just empty.

---

### Option B — Heuristic conversation extraction

After each NEX response (or in `tick()`), scan the last 20 NEX messages for "open inquiry" markers: phrases like "I haven't resolved", "I'm still thinking about", "this remains uncertain", "I wonder whether". Auto-open a problem when a marker is found and no similar problem exists.

**Pros:** Self-populating. Makes the node live without user action.  
**Cons:** High false-positive risk. NEX hedges a lot (`hedge_rate` is high per BSM). Almost every response could trigger a spurious problem. Noise overwhelms signal.  
**DOCTRINE concern:** This requires pattern-matching against NEX's own outputs — borderline self-surveillance. Could be framed as introspection but risks creating a noisy loop.

**Not recommended** until hedge_rate and false-positive rates are better understood.

---

### Option C — Belief-graph-driven problem extraction

When two beliefs with tension-type edges exist, auto-open a problem. When a belief ages beyond N days without resolution or promotion, auto-open.

**Pros:** Belief-graph-grounded, fully consistent with DOCTRINE.  
**Cons:** Requires belief edge infrastructure. Nex5's belief graph does not yet have tension-type edges (that's nex_core's phase 1 roadmap). Premature in nex5.

**Not recommended** until belief edges exist.

---

### Option D — Conversation topic persistence (lightweight multi-session detection)

`tick()` scans last 50 messages for recurring noun phrases (via simple frequency). When the same noun phrase appears in 3+ messages across 2+ sessions and no open problem covers it, auto-open one.

**Pros:** Grounded in observable conversation data, no LLM needed.  
**Cons:** High engineering cost for uncertain benefit. Noun phrase extraction without NLP is unreliable. Session boundary detection needs conversation session_id tracking.

**Not recommended** — complexity:benefit ratio is poor.

---

## 5. Recommendation

**Option A: SentienceNode protocol only.**

The infrastructure is complete. The wiring is correct. The only gaps are:
1. No SentienceNode conformance (blocking HUD visibility and registry)
2. No automatic population (table stays empty)
3. `find_matching` is fragile (word overlap with no stopwords)

For 6.2-6.3, port Option A and improve `find_matching` to strip stopwords and require ≥2 content-word matches. Leave population as manual-API-with-decay.

**For the injection trigger in find_matching:** Add a minimum content-word overlap count (≥ 2 non-stopword words) to prevent spurious matches. Return at most one problem (already the case — uses `matching[0]`).

Population can become self-sustaining later when either:
- Jon seeds initial problems via API (immediate, manual)
- Belief edges arrive (Option C becomes viable)

---

## 6. Open Questions for Jon

**Q1: Decay policy.** Should `decay()` auto-close problems stale > N days, lower their `confidence` (doesn't exist in schema), or just report age? My proposal: auto-close stale > 30 days, configurable via constant.

**Q2: Injection gating.** Problem injection currently fires on ANY register match (not INSIDE-only). This seems correct — a technical question can surface a technical open problem. Confirm, or should it be INSIDE-only like BSM?

**Q3: find_matching quality.** Word-overlap with stopwords present is fragile. The fix (strip stopwords, require ≥2 content-word matches) is small but changes behavior. Approve or defer?

**Q4: Initial seeding.** The API exists at `POST /api/problems`. Jon authors 3-5 initial problems — topics NEX is genuinely holding across sessions (architecture decisions, open philosophical threads, etc.) — to make the injection path live immediately after port. Willing?

---

## 7. Proposed API (Phase 6.2)

```python
class ProblemMemory:
    name: str = "problem_memory"
    
    _STALE_DAYS = 30
    _CACHE_TTL  = 120.0  # seconds
    
    def __init__(self, conversations_writer, conversations_reader):
        # ... existing args ...
        self._lock = threading.Lock()
        self._cached_open: Optional[list] = None
        self._cache_ts: float = 0.0
    
    def tick(self, context=None) -> dict:
        """Refresh open-problem cache; return state."""
        now = time.time()
        with self._lock:
            if self._cached_open is None or (now - self._cache_ts) > self._CACHE_TTL:
                self._cached_open = self.list_open()
                self._cache_ts = now
        return self.state()
    
    def decay(self, now: float) -> None:
        """Auto-close problems stale > _STALE_DAYS."""
        cutoff = now - self._STALE_DAYS * 86400
        self._writer.write(
            "UPDATE open_problems SET state='closed', resolved_at=?, last_touched_at=? "
            "WHERE state='open' AND last_touched_at < ?",
            (now, now, cutoff),
        )
    
    def state(self, now=None) -> dict:
        now = now or time.time()
        with self._lock:
            problems = self._cached_open or []
            oldest_age = None
            if problems:
                oldest_ts = min(p["last_touched_at"] for p in problems)
                oldest_age = round((now - oldest_ts) / 86400, 1)
            return {
                "name": self.name,
                "open_count": len(problems),
                "oldest_age_days": oldest_age,
                "cache_age_s": round(now - self._cache_ts, 1),
            }
```

**find_matching improvement:**

```python
_STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been",
    "do", "does", "did", "have", "has", "had", "will", "would",
    "can", "could", "should", "may", "might", "shall",
    "i", "you", "he", "she", "it", "we", "they",
    "what", "how", "why", "when", "where", "which", "who",
    "this", "that", "these", "those", "and", "or", "but",
    "of", "in", "on", "at", "to", "for", "with", "about",
    "not", "no", "so", "if", "as",
}

def find_matching(self, query: str) -> list[dict]:
    open_problems = self.list_open()
    if not query or not open_problems:
        return []
    query_words = {w for w in query.lower().split() if w not in _STOPWORDS and len(w) > 2}
    if not query_words:
        return []
    matches = []
    for p in open_problems:
        candidate_words = {
            w for w in (p["title"] + " " + p["description"]).lower().split()
            if w not in _STOPWORDS and len(w) > 2
        }
        overlap = query_words & candidate_words
        if len(overlap) >= 2:
            matches.append(p)
    return matches
```

---

*Last amended: 2026-05-08 — initial Phase 6.1 diagnostic.*
