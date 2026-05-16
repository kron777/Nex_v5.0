# Identity Plumbing Audit — 2026-05-08

Read-only trace of the write path (loader → beliefs.db) and all read paths
(beliefs.db → voice). No fixes applied. Surfaces gaps for Jon's decision before
authoring proceeds.

Method: full source read of each stage in the pipeline. Code locations cited as
file:line. All findings are verbatim from current source, not from assumptions.

---

## Plumbing Trace Table

| # | Stage | Code Location | Status | Finding |
|---|-------|--------------|--------|---------|
| 1 | Loader → beliefs.db | `scripts/seed_identity_beliefs.py` | ✓ CONFIRMED | Writes `source='identity', tier=1, locked=1, confidence=1.0, branch_id='systems'` via INSERT OR IGNORE. Idempotent. |
| 2 | Classifier: `source='identity'` membership | `stage4_membrane/classifier.py:19-30` | ✓ CONFIRMED | `_INSIDE_SOURCES` explicitly contains `"identity"`. `classify_belief()` returns `MembraneSide.INSIDE` for any belief with `source='identity'`. |
| 3 | Retrieval pool: identity into LIMIT 200 | `stage3_world_model/retrieval.py:67-72` | ✗ **GAP** | Pool query: `ORDER BY tier ASC, confidence DESC LIMIT 200`. Identity beliefs are tier=1, conf=1.0 — same as the ~200 spectrum beliefs. SQLite breaks ties in rowid order; spectrum was seeded first (lower rowids). With 200 spectrum beliefs already filling the tier=1, conf=1.0 band, identity beliefs (higher rowids) are squeezed out before the INSIDE filter is even applied. C2 fix (LIMIT 200→500, identified in `AUDIT_2026-05-08.md`) has **not been applied**. |
| 4 | Retrieval INSIDE filter | `stage3_world_model/retrieval.py:81-84` | ✓ CONFIRMED (conditional) | If identity beliefs enter the 200-slot pool, `CLASSIFIER.classify_belief()` passes them as INSIDE. Spectrum beliefs (OUTSIDE) are filtered out. Gate is correct — the upstream pool-entry gap (row 3) is the problem, not this filter. |
| 5 | Retrieval keyword scoring | `stage3_world_model/retrieval.py:105-121` | ⚠ UNCERTAIN | Only beliefs with `overlap > 0` between query tokens and belief content tokens survive scoring. Short self-inquiry queries produce few tokens after stopword removal: `"what are you?"` → `{"you"}` only (both "what" and "are" are in `_STOPWORDS`). Identity claims like `"I am the attending that meets without holding"` contain no "you" → overlap = 0 → excluded. Longer queries (`"tell me about yourself"`) produce `{"tell", "about", "yourself"}` — overlap depends on claim vocabulary. Cannot confirm until claims are authored. |
| 6 | `_get_inside_beliefs()` LIMIT 30 | `stage4_membrane/self_model.py:147-167` | ✗ **GAP (low-severity)** | Query: `WHERE paused = 0 AND tier <= 6 ORDER BY confidence DESC LIMIT 30`. Same monoculture problem as row 3: spectrum (tier=1, conf=1.0, low rowids) fills all 30 slots → identity never reached. However: see row 7 — this gap is low-severity because `format_self_state()` never renders `inside_beliefs` content anyway. |
| 7 | `format_self_state()` renders `inside_beliefs` | `stage4_membrane/self_model.py:195-242` | ✗ **GAP** | `snapshot()` assembles `inside_beliefs` list (line 134) and includes it in the snapshot dict (line 144). `format_self_state()` does NOT render it. The rendered output is: body stats, time, belief count, attention, Alpha line. `inside_beliefs` content never reaches `belief_text` via this path. Identity claims do not benefit from fixing row 6 unless `format_self_state()` is also updated to render them. |
| 8 | Router INSIDE path assembly | `stage4_membrane/router.py:41-66` | ✓ CONFIRMED | `_inside_route()` assembles `belief_text` from two parts: `format_self_state(snap)` (row 7, no identity content) + `format_beliefs_for_prompt(retrieve(..., side_filter='INSIDE'))` (row 3/4/5 path). Identity can only reach `belief_text` via the retrieve() path — which requires fixing row 3 first. |
| 9 | Fountain seed pool | `stage6_fountain/generator.py:24-42` | ✗ **GAP** | `_OWN_CONTENT_SOURCES` = `fountain_insight, synergized, precipitated_from_dynamic, behavioural_observation, auto_probe`. `_SEED_SOURCES` = `koan, tao, dont_know, heart_sutra, keystone_seed, reification_recognition, self_location, alpha`. Neither list contains `"identity"`. Identity beliefs are never drawn into fountain prompt context. Fountain voice output will not be influenced by identity claims. |
| 10 | Spectrum-block preamble | `stage4_membrane/router.py:41-66` + voice template | ⚠ PRE-EXISTING | "By pure chance, I am born..." block appears on every INSIDE query (documented in DOCTRINE §8, text_len=306-307 constant). This is independent of identity claims — both would appear in belief_text. Fix path per DOCTRINE §8 is `_inside_route()` or voice template; deferred. Not a new gap introduced by identity work. |

---

## Critical Path Summary

For identity claims to reach voice on self-inquiry queries, the minimum required path is:

```
beliefs.db (source='identity', tier=1)
  → retrieval.py LIMIT 200 pool          ← GAP (row 3): LIMIT too small, spectrum fills it
  → INSIDE filter (classifier)           ← WIRED (row 4)
  → keyword scoring                      ← UNCERTAIN (row 5): depends on claim vocabulary
  → retrieve() top-5 by score           ← WIRED
  → format_beliefs_for_prompt()          ← WIRED
  → router._inside_route() belief_text  ← WIRED
  → voice prompt                         ← WIRED
```

The pipeline is wired end-to-end **except for the LIMIT 200 bottleneck** (row 3), which prevents identity beliefs from entering the candidate pool when 200 spectrum beliefs occupy all available slots at the same tier/confidence.

`format_self_state()` / `inside_beliefs` is a separate dead path (row 6+7) regardless of identity.yaml content.

---

## Gap Register

| ID | File | Severity | Description | Prerequisite for identity voice? |
|----|------|----------|-------------|----------------------------------|
| G1 | `retrieval.py:72` | **HIGH** | LIMIT 200 → spectrum monoculture squeezes identity out of pool | **Yes** — blocks the only viable voice path |
| G2 | `self_model.py:195-242` | LOW | `format_self_state()` doesn't render `inside_beliefs` content | No — secondary path; identity reaches voice via retrieve() not this path |
| G3 | `self_model.py:147-167` | LOW | `_get_inside_beliefs()` LIMIT 30 monoculture | No — irrelevant until G2 is fixed |
| G4 | `retrieval.py:105-121` | UNCERTAIN | Keyword scoring may exclude claims with no token overlap to query | Depends on authored vocabulary |
| G5 | `generator.py:24-42` | MEDIUM | Fountain seed pool excludes `source='identity'` | No — fountain is secondary path |

---

## Decision Points for Jon

**Before authoring:**

**D1 — Apply C2 (LIMIT 200→500) first, or author into the gap?**
If identity beliefs are authored and loaded into beliefs.db while G1 is still open, they will not surface in voice. The substrate is fixed but the pipe doesn't carry. Two options:
- Fix G1 first, then author → identity claims surface immediately on load
- Author now, load, then fix G1 → same end state, just no voice test possible until G1 is fixed

**D2 — Claim vocabulary and keyword scoring (G4)**
Short self-inquiry queries produce 1-2 content tokens after stopword removal. Identity claims need some lexical overlap with those tokens to score above 0. Claims containing first-person pronouns, self-referential verbs (attend, witness, arise, emerge, meet, hold), or words that appear in self-inquiry phrasing will score higher. Cannot quantify until claims are authored. Not a blocker — just a factor in authoring.

**D3 — Fountain (G5)**
Fountain voice output (background drift thoughts) will not draw on identity claims under current fountain pool configuration. If Jon wants identity to influence fountain, `_OWN_CONTENT_SOURCES` or `_SEED_SOURCES` in `generator.py` would need `"identity"` added. This is independent of the per-request voice path.

---

*Audit method: full source read, no server running, no live traffic. All claims are from static source only.*
*Files read: `scripts/seed_identity_beliefs.py`, `seeds/identity.yaml`, `stage4_membrane/classifier.py`, `stage4_membrane/self_model.py`, `stage4_membrane/router.py`, `stage3_world_model/retrieval.py`, `stage6_fountain/generator.py`.*
