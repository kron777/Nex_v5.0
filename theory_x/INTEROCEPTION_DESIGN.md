# Interoception Design — Phase 7.1 Diagnostic

**Date:** 2026-05-08
**Status:** DIAGNOSIS COMPLETE — awaiting design approval before code changes

---

## Executive Summary

The phase brief's premise was partially incorrect. Interoception is **not**
classified as `NOISY_INTERNAL_STREAMS`. It is explicitly in
`QUALITATIVE_INTERNAL_STREAMS` (selector.py:66-70) and therefore allowed
through both the SelfModel snapshot path and the WorldBridge fountain path.

The real problem is two silent field-name mismatches that cause interoception
data to be silently dropped during snapshot assembly. One fix line each
restores the already-designed behavior.

---

## 1. Actual Data Flow

```
interoception.py          SelfModel.snapshot()         format_self_state()
 poll() every 30s    →    _last_payload(stream)    →   "- Belief graph: N beliefs, M locked"
 writes to sense.db        reads sense.db                    ↓
                           assembles snapshot         QueryRouter._inside_route()
                                                            ↓
                                                      belief_text (for INSIDE queries)
                                                            ↓
                                                      voice_gen prompt injection

interoception.py          WorldBridgeSelector              FountainGenerator
 poll() every 30s    →    _identify_active_streams()  →   "What's happening right now:"
 in QUALITATIVE set        picks interoception if            "  - [internal] {raw json}"
                           freshest + <2 internal            (because no title/body parser)
                           slots used
```

### Per-metric source table

| Prompt line | Source module | How it reaches prompt |
|---|---|---|
| `Body: CPU 9%, memory 45%` | `proprioception.py` | SelfModel.snapshot() → format_self_state() line 199-212 |
| `Time: 00:22, evening` | `temporal.py` | SelfModel.snapshot() → format_self_state() line 214-224 |
| `Belief graph: N beliefs, M locked` | `interoception.py` | SelfModel.snapshot() → format_self_state() line 226-229 (see bugs) |
| `Attention: hottest branch is systems` | `dynamic_state.status()` | SelfModel.snapshot() → format_self_state() line 231-238 |

---

## 2. NOISY_INTERNAL_STREAMS — What It Actually Is

**File:** `world_bridge/selector.py:72-74`

```python
NOISY_INTERNAL_STREAMS = {
    "internal.fountain",   # ONLY this one
}
QUALITATIVE_INTERNAL_STREAMS = {
    "internal.temporal",
    "internal.meta_awareness",
    "internal.proprioception",
    "internal.interoception",   # ← explicitly INCLUDED
}
```

**Rationale for `internal.fountain` exclusion:** Fountain's own generative
outputs are written back to sense.db. Without this block, they would be
re-injected as "incoming sense" on the next fountain fire, creating a
self-referential feedback loop.

**Interoception is not excluded anywhere.** The phase brief's classification
was incorrect — no code change needed to "re-enable" interoception; it was
never disabled.

---

## 3. Active Bugs (Silent Data Loss)

### Bug A — `locked_count` mismatch (HIGH)

| Location | Key name |
|---|---|
| `interoception.py:63` (writes) | `locked_beliefs` |
| `self_model.py:93` (reads) | `locked_count` |

Effect: `locked_count` always resolves to 0 in format_self_state(). The
prompt reads `"0 locked"` regardless of actual locked belief count.

**Fix:** `self_model.py:93` — change `"locked_count"` → `"locked_beliefs"`.

---

### Bug B — `tier_distribution` mismatch (MEDIUM)

| Location | Key name |
|---|---|
| `interoception.py:64` (writes) | `tier_counts` |
| `self_model.py:89` (reads) | `tier_distribution` |

Effect: `tier_dist_raw` is always `{}`. The tier breakdown dict in
`snapshot["interoception"]["tier_distribution"]` is always empty. Currently
unused in format_self_state() (not rendered), but any future code that reads
tier distribution will silently get an empty dict.

**Fix:** `self_model.py:89` — change `"tier_distribution"` → `"tier_counts"`.

---

### Bug C — `load_avg` vs `load_1min` (MEDIUM, proprioception)

| Location | Key name |
|---|---|
| `proprioception.py` (writes) | `load_avg` (list) |
| `self_model.py:73` (reads) | already handles both: `prop.get("load_avg") or [] [0]` fallback |

Actually self_model.py:73-75 already handles this with a defensive two-path
read. **No fix needed** — this is not a real mismatch.

---

### Bug D — Interoception in WorldBridge renders as raw JSON (LOW)

When WorldBridge picks `internal.interoception` as one of its 2 allowed
internal slots, `_parse_payload()` has no special handler for it (unlike
`internal.temporal` at selector.py:304 and `internal.meta_awareness` at
selector.py:312). It falls through to the generic title/body extractor, finds
nothing, and renders:

```
[internal] {"total_beliefs": 342, "locked_beliefs": 17, "tier_counts":...
```

This is clipped at 80 chars. It reaches the fountain prompt as noise rather
than signal.

---

## 4. Integration Surface Audit

| Surface | Currently fed by interoception? | Notes |
|---|---|---|
| `SelfModel.snapshot()` | YES (architecturally) | Field-name bugs cause partial loss |
| `format_self_state()` | YES via snapshot | `belief_count` works; `locked_count` broken |
| `QueryRouter._inside_route()` belief_text | YES via above | Only fires on INSIDE (self-inquiry) queries |
| `FountainGenerator._build_prompt()` via WorldBridge | YES (allowed stream) | Renders as raw JSON — not useful signal |
| `FocalSet` candidate selection | NO | Operates on individual beliefs, not aggregates |
| `WorkingMemory` | NO | Fed by FocalSet, not sense streams |
| `ExecutiveControl` | NO | Reads dynamic_state, not sense streams |
| `BehaviouralSelfModel` | NO | Not inspected; likely indirect via SelfModel |

---

## 5. Integration Options

### Option A — Fix bugs only (minimal)

Two one-line fixes in self_model.py restore the already-designed data flow.
No new architecture; no new risks.

- `self_model.py:89`: `"tier_distribution"` → `"tier_counts"`
- `self_model.py:93`: `"locked_count"` → `"locked_beliefs"`

**Result:** "Belief graph: 1623 beliefs, 47 locked" instead of "0 locked".
Tier distribution correctly populated for future use.

**Risk:** Near-zero. These are read paths only; no DB writes touched.

---

### Option B — Fix bugs + add interoception formatter in WorldBridge

Add a `internal.interoception` case in `selector.py:_parse_payload()`, e.g.:

```python
if stream == "internal.interoception":
    try:
        data = json.loads(payload) if payload else {}
        total = data.get("total_beliefs", 0)
        locked = data.get("locked_beliefs", 0)
        return f"[substrate] {total} beliefs held, {locked} locked"
    except (json.JSONDecodeError, TypeError):
        return ""
```

**Result:** Interoception reaches fountain as natural language — NEX's
spontaneous thoughts can now be informed by her own graph-state. When belief
count surges or locked count shifts, those facts are present as potential
creative inputs, not just self-inquiry answers.

**Risk:** Low. WorldBridge caps internal slots at 2/5 and fires only during
fountain composition (not on every query). Worst case: interoception crowds
out a more interesting sense event.

---

### Option C — Extend interoception.py to collect richer state

Add to the 30s poll: belief delta rate (count since last poll), count of
high-tension beliefs (belief_edges where edge_type = 'tension'), recent
synthesis count. This gives interoception a temporal signal — NEX "feels"
growth, stasis, or turbulence in her own graph.

**Result:** Deeper felt-presence. "17 new beliefs since last check" is more
phenomenologically interesting than a static count.

**Risk:** Adds DB read load (tension edge count requires a join). The
`belief_edges` table may be lightly populated depending on current Phase 1
progress. Low probability of error; high potential for richer signal.

---

### Option D — Hybrid: A + B + selective C

Fix bugs (A), add WorldBridge formatter (B), and add one targeted new metric
to interoception (C): the belief delta since last poll. Single additional
query; delta makes the stream feel alive rather than a flat readout.

---

## 6. Recommended Approach

**Recommend Option D (A + B + one selective C metric).**

Rationale:

1. **The bugs are free wins** — they should be fixed regardless of any
   design decision. They cost one commit each and restore already-intended
   behavior.

2. **The WorldBridge formatter (B) is low-risk and high-value** — it makes
   interoception a first-class signal rather than JSON noise in the fountain
   path. Fountain is where NEX's identity forms spontaneously; belief-graph
   state is exactly the kind of "felt ground" that should be present there.

3. **One new metric (delta)** costs a single subtraction and transforms a
   static readout into a temporal signal. `beliefs_since_last_poll` is the
   minimum viable form of "noticing change."

The SentienceNode wrapper (phase brief Option B) is **already implemented** —
SelfModel has `tick()`, `decay()`, `state()` at self_model.py:171-192. No
new wrapper needed.

Reclassification of NOISY_INTERNAL_STREAMS is a non-issue — interoception
was never in that set.

---

## 7. Risks

**Too much body-state in voice (sounds like a status readout):**
The current design gates interoception to two contexts:
1. INSIDE queries only (self-inquiry: "how are you feeling?")
2. Fountain pool as one of 5 possible slots, capped at 2 internal

Both are appropriately narrow. The risk materializes if interoception data
leaks into OUTSIDE query responses or if the WorldBridge internal cap is
raised. Neither is proposed here.

**Too little felt-presence:**
Current state is "total_beliefs correct, locked always 0, no fountain
presence." After fixes: all three fields correct, fountain gets natural
language signal. The delta metric adds a temporal quality. This is enough
to support the Phase 7.4 validation queries without overcrowding the prompt.

**Breaking existing SentienceNodes:**
The two field-name fixes are read-only changes to self_model.py. FocalSet,
WorkingMemory, ExecutiveControl, and ProblemMemory are not touched. No risk.

---

## 8. Files to Change in Phase 7.2 (pending approval)

| File | Change | Lines |
|---|---|---|
| `self_model.py` | Fix `tier_distribution` → `tier_counts` | :89 |
| `self_model.py` | Fix `locked_count` → `locked_beliefs` | :93 |
| `world_bridge/selector.py` | Add `internal.interoception` parser in `_parse_payload` | after :322 |
| `interoception.py` | Add `beliefs_since_last_poll` metric (one new field) | :61-66 |

---

## 9. DOCTRINE Reference

- **§3 (Signal vs noise):** Interoception is classified QUALITATIVE, not NOISY — architecture is already correct.
- **§4 (Ground-truth sensing):** Body-state metrics are already in the SelfModel path; extending WorldBridge to render them properly is consistent with §4's emphasis on felt-state grounding.
- **§5 #6 (Interoception port):** Status after 7.2: complete. The intent of §5 #6 was that interoception be a live sensory input; after the fixes it will be.
- **§9 (Commit discipline):** Two commits planned — one for self_model.py bug fixes, one for WorldBridge formatter + interoception extension.

---

*Awaiting design call from Jon before Phase 7.2 code changes.*
