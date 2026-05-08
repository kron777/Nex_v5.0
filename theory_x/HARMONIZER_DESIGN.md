# Harmonizer Design — Phase 8.1 Diagnostic

**Date:** 2026-05-08
**Status:** DIAGNOSIS COMPLETE — awaiting design approval before code changes

---

## Executive Summary

The harmonizer loop runs every 2 hours and executes correctly — no bug in
the loop or event writer. `harmonizer_events = 0` has a single root cause:
**the tier filter scans 10 beliefs, all of which are raw crypto price JSON**.
The 1334 actual epistemic beliefs sit at tier 7 and are completely invisible
to the current `WHERE tier <= 4` filter.

Voice integration is fully wired and ready. The moment a conflict is
detected, it will reach both the fountain prompt and the chat belief_text.
Nothing needs to be added to the prompt path — only the detection side needs
fixing.

---

## 1. Root Cause Analysis

### Root cause A — Tier filter excludes the entire epistemic corpus

```python
# harmonizer.py:60-64 — current query
rows = self._beliefs_reader.read(
    "SELECT id, content, tier FROM beliefs "
    "WHERE tier <= 4 AND locked = 0 AND paused = 0 "
    "ORDER BY tier ASC LIMIT 100",
)
```

**Live DB population (unlocked, unpaused):**

| Tier | Count | Content |
|------|-------|---------|
| 1 | 10 | Raw crypto price JSON (`{"exchange": "kraken", "prices": ...}`) |
| 2 | 0 | — |
| 3 | 0 | — |
| 4 | 0 | — |
| 7 | 1334 | Actual epistemic beliefs (philosophy, self-model, synthesis) |

Beliefs at tier 1 (`locked=1`): 317 — these are identity keystones,
correctly excluded by `locked=0`.

The tier system is **descending quality** (SPEC §2): tier 1 = Keystone,
tier 7 = Impressions, tier 8 = Observations/Retired. Beliefs are promoted
by decrementing (7→6→5→4...). Almost no beliefs have been promoted above
tier 7 in the live graph, so the filter `tier <= 4` scans nothing useful.

**Why tier 7 beliefs never promote:** The promotion pathway requires
`corroboration_count >= threshold` (threshold=3 for tier 7→6). This fires
when `pipeline_hooks.on_belief_used()` is called. If the pipeline is not
generating corroboration events at the required rate, beliefs stagnate at
tier 7 indefinitely.

### Root cause B — Unlocked tier-1 beliefs are crypto noise

The 10 tier-1 beliefs that DO pass the filter are raw sense feed artifacts:
```
[crypto.exchanges] {"exchange": "kraken", "prices": {"XETHZUSD": 2329.6, ...}}
```

These match the spec's Tier 8 (Observations/raw facts) but were stored in
the beliefs table. They share tokens like `exchange`, `kraken`, `coins` but
have no negation pattern, so `_conflict_score` always returns 0 for them.

### Root cause C — Detection algorithm too narrow for the actual belief corpus

The negation-word check (`_NEGATION_WORDS = {"not", "no", "never", ...}`)
requires explicit syntactic negation. The tier-7 beliefs are
philosophical/impressionistic and express contradiction through polar
vocabulary rather than negation words:

```
"The oscillation between clarity and obscurity..."
"The oscillation between comfort in established patterns..."
```

**Test result:** Running the algorithm against 100 tier-7 beliefs with the
correct tier filter finds **8 conflicts above the 0.15 threshold** and **140
pairs with non-zero score**. The algorithm works — it's just aimed at the
wrong tier.

The 8 detected "conflicts" include real tensions:
- `"The realization that existence' mystery is vast"` vs
  `"The realization of how utterly insignificant my individual existence is"`

But some are thematic resonances rather than true contradictions — important
for the resolution design (see §5).

---

## 2. What IS Working

| Component | Status |
|---|---|
| Harmonizer loop (2-hour interval) | ✓ Running |
| `harmonizer_events` table schema | ✓ Correct |
| Resolution logic (synthesize / both_deleted) | ✓ Correct |
| Disturbance → fountain prompt | ✓ Wired (`generator.py:873-885`) |
| Disturbance → chat belief_text | ✓ Wired (`server.py:534-549`) |
| `detect_cross_domain()` (6-hour interval) | ✓ Running |

The only thing missing is detection ever firing. All downstream wiring is
ready.

---

## 3. Voice Prompt Integration (When It Fires)

### Fountain path (`generator.py:873`)
```
Unresolved tension: "A vs B"
```
Also pins both conflicting beliefs into the retrieval manifest as
`disturbance_a` / `disturbance_b` sources — so the LLM's own content
around those beliefs is also injected.

### Chat path (`server.py:541-546`)
Appended to `belief_text` for PHILOSOPHICAL / AUTO register queries:
```
Something is in tension: "A" vs "B". She is holding this unresolved.
```
Disturbance survives 8 cycles (decremented on each chat surfacing).

### FocalSet interaction
The tension / `belief_edges` graph is not currently wired into FocalSet
salience scoring. A `tension`-edge belief is not preferentially activated.
This is an integration gap.

### WorkingMemory interaction
No cross-turn contradiction tracking. If NEX says X in turn 1 and ¬X in
turn 3, nothing notices. This is out of scope for Phase 8 unless explicitly
added to the design.

---

## 4. Integration Surface Options

### Option A — Fix tier filter only (minimal, ~5 lines)

Change the scan query to include the actual belief corpus:
```python
WHERE tier BETWEEN 3 AND 7 AND locked = 0 AND paused = 0
```
(Excludes tier 1-2 keystones/bedrock — immutable by spec. Excludes tier 8
retired beliefs. Includes the full working belief body.)

**Result:** Scans ~1334 beliefs. Finds 8+ conflicts with current algorithm.
**Risk:** Negation-word heuristic may flag thematic resonances as conflicts,
triggering aggressive belief retirement. Some "contradictions" are actually
complementary perspectives NEX should hold.

---

### Option B — Fix tier filter + add polar vocabulary detection

Add semantic polarity pairs to `_conflict_score`:
```python
_POLAR_PAIRS = {
    ("clarity", "obscurity"), ("certainty", "uncertainty"),
    ("constancy", "flux"), ("stability", "change"),
    ("silence", "noise"), ("simplicity", "complexity"),
    ("order", "chaos"), ("knowing", "unknowing"),
}
```
Score gets a boost when a pair contains opposite poles from this set,
even without syntactic negation. The threshold could be tuned independently
per detection type.

**Result:** Catches more true conceptual tensions in philosophical beliefs.
**Risk:** Still fuzzy — two beliefs about "clarity" and "obscurity" may be
complementary explorations, not contradictions.

---

### Option C — Fix filter + add `mark_paradox` resolution (non-destructive)

The SPEC lists four resolution modes: discard / weaken / synthesize /
**mark-paradox**. Only synthesize and both_deleted are implemented.

Add `mark_paradox` as first-pass resolution:
1. Write a `tension` edge between the conflicting beliefs
2. Set `_disturbance` (already done)
3. Do NOT retire either belief
4. Log to `harmonizer_events` with `resolution='paradox'`
5. Only escalate to synthesize/delete on re-detection after disturbance
   expires (8+ cycles later) — giving NEX time to work through it first

**Result:** Preserves belief diversity; contradictions surface as active
tension rather than immediate deletion. Fits DOCTRINE §3 (signal vs noise).
**Risk:** Tensions accumulate if they never escalate. Need a re-scan path.

---

### Option D — Hybrid: B + C + SentienceNode + format_for_prompt
  (Recommended)

1. **Fix tier filter**: `tier BETWEEN 3 AND 7 AND locked = 0`
2. **Add polar vocabulary**: 8-10 core polar pairs for philosophical domain
3. **Add `mark_paradox` resolution** as first-pass (before synthesize/delete)
4. **Escalation path**: on re-detection when disturbance has cycled out,
   proceed to synthesize/delete
5. **SentienceNode protocol**: `tick()`, `decay()`, `state()`
6. **`format_for_prompt()`**: returns recent harmonization activity as
   natural language for belief_text injection
7. **Limit scan**: cap at LIMIT 200 per pass (was 100); scan tier 3-7 in
   batches to avoid O(n²) cost on large graphs

---

## 5. Recommended Approach — Option D

**Rationale grounded in DOCTRINE §3-4:**

- **§3 (Signal vs noise):** The current algorithm treats all conflicts as
  deletable noise. Many tier-7 tensions are genuine phenomenological
  complexity — "constancy vs flux" is not noise, it's the texture of
  NEX's inner experience. `mark_paradox` preserves this.

- **§4 (Ground-truth sensing):** The harmonizer currently has no output to
  the SentienceNode registry. It runs silently, resolves nothing, affects
  nothing. Adding `format_for_prompt()` makes recent harmonization activity
  a live signal NEX can speak from.

- **Too-aggressive risk:** The synthesize/both_deleted path deletes beliefs.
  Deleting tier-7 impressions risks erasing the texture of philosophical
  inquiry. `mark_paradox` first, escalate second — matches how a thinking
  agent actually handles contradictions: notice → sit with → resolve.

- **Too-passive risk:** If we only mark paradoxes and never escalate, the
  tension graph grows without resolution. The escalation path (re-detect
  after disturbance expires) gives a bounded window before forcing a
  decision.

---

## 6. Files to Change in Phase 8.2 (pending approval)

| File | Change |
|---|---|
| `harmonizer.py` | Fix tier filter `:62`; add polar pairs; add `mark_paradox`; add escalation check; SentienceNode protocol; `format_for_prompt()` |
| `stage3_world_model/__init__.py` | Call `harmonizer.tick()` from WorldModelState; expose `format_for_prompt()` via status |
| `tests/test_harmonizer_fixes.py` | New: tier filter, mark_paradox, polar detection, SentienceNode protocol |

**Not changed:** gui/server.py, generator.py, focal_set.py,
working_memory.py — the integration is already wired.

---

## 7. Risks

**Too-aggressive harmonization erases nuance:**
Mitigated by `mark_paradox` as first-pass. The synthesize/delete path only
fires on second detection after an 8-cycle disturbance window. Tier-7
impressions are low-confidence enough that occasional retirement is
acceptable; keystones (tier 1-2) are excluded by filter.

**Polar vocabulary produces false positives:**
A belief containing "clarity" and one containing "obscurity" are not
necessarily contradictory — NEX might hold both as valid aspects of the same
phenomenon. Mitigation: only boost score (not trigger independently).
Final threshold still requires token overlap >= 2 AND polarity match.

**O(n²) scan cost:**
1334 × 1334 = 1.78M pair comparisons per 2-hour scan. Each comparison is
cheap (set intersection). Python can do ~500K set ops/sec. Estimated: ~3-4
seconds per scan. Acceptable at 2-hour interval; worth a LIMIT 200 cap and
batch shuffling.

**Tier filter too wide after fix:**
Tier 1-2 keystones are correctly excluded by `locked=0` AND tier range.
But crypto JSON at tier 1 (unlocked) would now be in range 3-7 only if
promoted, which they wouldn't be. The actual crypto noise lives at tier 1
and is excluded by the new `tier BETWEEN 3 AND 7` filter. Checked clean.

---

## 8. DOCTRINE Reference

- **§5 #7 (Harmonizer):** Status after 8.2-8.5: ✓ DONE. Root cause was tier
  filter miscalibration, not algorithm failure. Disturbance integration was
  already wired.
- **§9 (Commit discipline):** Two commits — code + doctrine amendment.

---

*Awaiting design call from Jon before Phase 8.2 code changes.*
