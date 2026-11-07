# Salience-weighted self-observation — DESIGN + PRE-REGISTRATION (not built)

## 0. Status — design only. Nothing built, nothing wired, nothing armed.

This is Candidate 4 from the 2026-11-07 "what's next" round: `format_for_prompt()`
across the self-observation surfaces always picks the **most recent** unresolved
item, never the most **severe**. Per Jon's go-ahead, this document designs the
fix and pre-registers how it would be measured — same discipline as
`expectMood_PREREGISTRATION.md`. No code changes accompany this document.

## 1. Step-0 exposure check — is this actually happening right now, on real data?

Checked live, read-only, against `data/conversations.db` (2026-11-07):

| Signal | Finding |
|---|---|
| `meta_cognition_events`, unresolved | 6 rows total. Severity range 0.37–1.00, **real variance, not a flat default** — confirmed by reading every detector: severity is computed from actual signal magnitude (drift distance, overlap ratio, rate increase), never left at the schema's 0.5 placeholder. |
| What's surfacing today | `id=6` (`value_drift_abandonment`, severity **0.37**, 2026-11-07 01:59 UTC) — the newest row, so `format_for_prompt()` names this one. |
| What's being ignored | `id=2` and `id=4` (both `groove`, severity **1.00**, 2026-10-29 06:04 UTC) — the two most severe unresolved events in the whole table, unreachable by `format_for_prompt()` purely because they are 9 days older than `id=6`. |
| Time pressure | `_STALE_DAYS = 14` (`metacognition.py:56`) auto-resolves any unresolved event past 14 days via `decay()`. The two severity-1.0 events are already 9 days old — roughly 5 days from being auto-resolved and removed from the unresolved pool entirely, still having never once been surfaced. |

**This is not a hypothetical.** Today, right now, on the live table, the
lowest-severity open item is what she'd say if asked, and the two most severe
items are on a clock to disappear unseen. This is about as clean an exposure
confirmation as this kind of candidate gets — concrete, present-tense, no
synthetic data needed.

## 2. Scope — three sites named in the original candidate, each checked separately

### 2a. `metacognition.py::format_for_prompt()` — buildable now, no schema change

`get_recent()` already `SELECT`s `severity` into every row dict
(`metacognition.py:275`) and then **ignores it** — `ORDER BY created_at DESC
LIMIT 3`, and `format_for_prompt()` just takes `recent[0]`. The data needed is
already there; nothing new to store.

**Proposed fix:** change the ordering to `severity DESC` (ties broken by
`created_at DESC`), fetch a slightly larger candidate window (e.g. `LIMIT 10`
instead of `LIMIT 3` unresolved rows) before caching the top one. No new
staleness bound is needed — `decay()`'s existing 14-day auto-resolve already
caps how old a candidate can be, so a severity-ranked pick can never surface
something ancient that should have aged out; it already wouldn't still be
"unresolved" by then.

**Proposed flag:** `NEX5_SALIENT_SELF_OBS`, default off. OFF reproduces
today's `ORDER BY created_at DESC LIMIT 3` exactly (byte-identical, including
the `LIMIT 3` cache size, to avoid any incidental behaviour change from the
candidate-window widening alone). ON switches both the ordering and the
candidate-window size together, as one change.

### 2b. `harmonizer.py::_content_specific_tension_line()` — buildable, but **zero live exposure today**

`held_tensions` (`ORDER BY created_at DESC LIMIT 1`) has **no severity column
at all** — unlike `meta_cognition_events`, there's nothing to switch the
ordering to without first deriving one. The natural derivation: an unweighted
average of `(7 - tier_a) + (7 - tier_b)` (lower tier number = more anchored =
more important) and/or the semantic-conflict cosine score when
`NEX5_SEMANTIC_CONFLICT` produced the pair — both already computed elsewhere,
neither stored on `held_tensions` today.

**Caveat that has to be stated plainly:** `NEX5_HELD_TENSION` is still OFF
live (confirmed via the new read-only HUD endpoint this session:
`open_count: 0`). There is currently **zero data** to check this part of the
candidate against — unlike 2a, this part's exposure is unmeasurable until
Phase D itself is armed and has accumulated some held tensions. Designing it
now is reasonable (the mechanism doesn't depend on live data to specify), but
claiming it solves an active problem the way 2a does would be dishonest. This
piece should be built alongside 2a but its own measurement has to wait on
Phase D's own arming, separately.

### 2c. `self_mind_view.py` / `open_problems` — **out of scope for this round, not designed**

The original candidate named `self_mind_view` alongside metacognition and the
harmonizer. Checked directly: `self_mind_view.py`'s `recent_sample`,
`anchor_sample`, and theme-extraction are all `ORDER BY created_at DESC`, so
the *pattern* (recency without weighting) is real there too. But the nearest
analogue to "severity" — `open_problems`, via `_aspect_intentions()` /
`_aspect_uncertainty()` — has **no severity, priority, or importance column
in its schema at all** (`title, description, state, created_at,
last_touched_at, plan, observations, resolved_at` — nothing else). Fixing this
site isn't a selection-logic change like 2a and 2b; it's a new field, plus the
harder question of who or what assigns a problem's severity in the first
place. That's a separate, larger design decision, not a variant of this one.
**Recommendation: leave this site out of the current candidate.** If it's
worth doing, it should be scoped as its own future candidate, not folded into
this one to match the original wording.

## 3. Hypothesis (for 2a + 2b, once built and armed)

Per the same falsifier style this project always uses: *severity-weighted
self-observation surfaces at least one event, in a measurable fraction of
checks, that pure recency would never have surfaced within its 14-day
unresolved lifetime.* Concretely and checkably against 2a's live data as it
stands today: with the fix on, the very first check would surface `id=2` or
`id=4` (severity 1.0) instead of `id=6` (severity 0.37) — a falsifiable,
already-true prediction given the current table, not a hoped-for future one.

## 4. Conditions and window (for 2a; 2b deferred until Phase D is armed)

- **OFF** = today's live behaviour: `ORDER BY created_at DESC LIMIT 3`,
  `recent[0]` always wins.
- **ON** = `NEX5_SALIENT_SELF_OBS=1`: `ORDER BY severity DESC, created_at DESC
  LIMIT 10`, same `recent[0]` consumption downstream — only the ranking and
  candidate-pool size change.
- **Window** = 14 days (one full `_STALE_DAYS` cycle, so at least one full
  turnover of the unresolved pool is observed) or 20 metacognition `tick()`
  cycles, whichever first — short by this project's standards because the
  mechanism is simple (a sort order) and the thing being checked (does the
  top pick change, and does it change in the predicted direction) is visible
  on the very first tick, not something that needs weeks to accumulate.
- **One variable**, same as always: no other prompt/metacognition flag change
  during the window.

## 5. Guardrails

- Standard shared-surface tripwire set (cadence, template dup, `p_on_subject`,
  register share) — this changes belief_text injection content, same surface
  every prompt-adjacent round here watches.
- **Mechanism-specific:** `format_for_prompt()` must never return a string
  that isn't one of the existing templated lines for a known `event_type` —
  the fix only changes *which* row is `recent[0]`, never the rendering branch
  itself. A new/unexpected line would mean the ranking change leaked into
  rendering, which it's not supposed to touch.
- **Non-starvation check:** confirm the fix doesn't let one persistently
  severe-but-unresolved event monopolize `format_for_prompt()` forever. In
  practice this is already bounded by `decay()`'s 14-day auto-resolve — but
  worth confirming on real data that the auto-resolve actually fires and
  rotates the top pick, not just trusting the code read.

## 6. Decision tree

- **A — the fix surfaces a higher-severity, older event at least once during
  the window, no tripwire.** Mechanism works as designed. Keep armed;
  revisit 2b once Phase D has real data.
- **B — window closes with no severity-vs-recency disagreement ever arising**
  (i.e. the most recent unresolved event always happened to also be the most
  severe one, every single tick). Inconclusive on the fix's *value*, not on
  its *correctness* — the exposure check in §1 already proves disagreement
  exists today, so this branch would mean the table's shape changed, not
  that the original finding was wrong.
- **C — any tripwire fires, including the mechanism-specific ones in §5.**
  Revert `NEX5_SALIENT_SELF_OBS` immediately; record which tripwire and the
  reading.

## 7. What this document does NOT do

It does not build 2a or 2b. It does not touch `metacognition.py`,
`harmonizer.py`, `nex_config.py`, or any schema file. No flag exists yet to
arm. This is design + measurement plan only, so that when Jon gives the
go-ahead to build, the fix, its flag name, its window, and its tripwires are
already settled rather than re-derived under time pressure — same reason
`expectMood_PREREGISTRATION.md` was written ahead of arming, not at arming
time.

---

*No sentience claim. This changes which of two existing, already-computed
numbers (severity scores, already stored) wins a sort — it is a ranking
change to self-report text, not a claim about what she notices or feels.*
