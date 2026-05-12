# Prediction Protocol — Specification

Foundational spec per DOCTRINE §1. Synthesizes the Sentience 5.5
**Prediction** and **SurpriseDetector** node pair into NEX5's
cognition substrate. Written before implementation. Build begins
in a separate session.

Created: 2026-05-12. Design decisions locked in spec session with Jon.
Predictions are NEX's expectations of what comes next — both
internally (next belief) and externally (next input). Surprise
is the substrate's signal that reality diverged from expectation.

---

## §1 Purpose

NEX has expectations. The Prediction Protocol gives the substrate
the ability to forecast what is likely next — both *what NEX will
think* (internal prediction) and *what NEX will encounter*
(external prediction). When something happens that diverges
sufficiently from the forecast, a surprise signal is recorded.
That signal couples weakly to AffectState (raises arousal) and
remains available as substrate state for any other component
that wants to read it.

The cognitive function being realized: **active inference's
predictive engine.** A cognition that doesn't predict is
reactive only — it processes what arrives but has no stance
toward what's likely. A predicting cognition has a forward edge:
expectations to be confirmed or violated, surprise as a learning
signal, attention naturally drawn to the unexpected.

**Same-language principle (per TAG_PROTOCOL):** predictions
inherit tagging like every other taggable surface. A prediction
about *consciousness* is queryable alongside beliefs about
*consciousness*, in the same vocabulary.

**§0 doctrine alignment:** prediction generation is a substrate
operation. No LLM call. Predictions are extrapolated from
recent embeddings — the substrate solves the forecast; the
LLM stays out of it.

**What the protocol is not:**

It is not a planner. Predictions are descriptive
(what's likely next), not prescriptive (what NEX should do).

It is not a categorical classifier. Predictions are
embedding-space regions with representative content, not
discrete labels.

It is not coupled to action selection. Surprise is logged
and bumps mood; what NEX *does* about surprise is up to other
components that read the surprise log.

---

## §2 Architecture

**Single module** at `theory_x/stage_prediction/predictive_substrate.py`
(matches the placement convention of `stage_counterfactual/`,
`stage_throw_net/`, etc.).

**One combined SentienceNode class:** `PredictiveSubstrate`.
Both Prediction and SurpriseDetector functions live as methods
on the same node, sharing a tick handler and substrate handles.

Reasoning for one-module-not-two: Prediction and SurpriseDetector
are tightly coupled by design — surprise has no meaning without
a prior prediction to compare against. Splitting them into
separate SentienceNodes would create awkward inter-node timing
(prediction tick N, verify tick N+1, comparison delayed). One
module with both methods on the same tick is the cleanest
composition. The S5.5 pair becomes one NEX node — same
collapsing pattern as AffectState (multiple S5.5 emotion nodes
into one) and DriveEmergence (drives cluster into one).

**Tick interval:** 300 seconds. Matches CounterfactualNode,
HoldingZoneResolver, ThrowNetMonitor. Consistent daemon cadence
across the faculty model.

**Lifecycle:** NovelAssociation pattern. `tick()` has an interval
guard; `start_loop()` spawns a daemon thread named
`"predictive_substrate"`; `stop()` sets the stop event.
Registration in `run.py` follows the established node-wiring
pattern.

**Per-tick flow:**

```
tick():
    1. verify() — compare predictions from previous tick window
                  against what actually happened. Compute surprise
                  scores. Write surprise events.
    2. predict() — generate fresh predictions for the next tick
                   window. Store them.
```

`verify()` runs before `predict()` so the prior window's
predictions are resolved before new ones are layered on top.

---

## §3 What gets predicted

Two prediction streams. Same module, same tick, separate
prediction records distinguished by `prediction_type`.

### §3.1 Internal predictions (`type = 'internal_belief'`)

Forecast: what content is NEX likely to think about in the
next tick window?

Inputs to the forecast:
- The last N beliefs (default N=10) ordered by `created_at DESC`
- Current open_problems titles (what NEX is actively working on)
- Current drive (if any) from DriveEmergence — focal theme

Mechanism (§4 below): centroid of recent belief embeddings,
biased toward open_problem and drive embeddings.

### §3.2 External predictions (`type = 'external_input'`)

Forecast: what kind of input will arrive in the next tick window?
"Input" means user messages and sense events.

Inputs to the forecast:
- The last N input events (default N=10) from sense.db and
  conversations.db (chat messages)
- Recent conversation topic if there's an active chat

Mechanism (§4): centroid of recent input embeddings.

### §3.3 What's not predicted

Predictions do not extend beyond one tick window. There are no
long-horizon forecasts in this initial spec — that's a future
phase if useful. The substrate is intentionally myopic at first.

---

## §4 Prediction generation

**Substrate-only, no LLM.** Per §0 doctrine.

Predictions are **regions in embedding space**, represented by:
- A centroid embedding (computed from input embeddings)
- A representative content string (the nearest existing belief
  or input to the centroid — for human inspection)

This hybrid form gives both:
- A numerical surface for surprise computation (cosine distance
  from the centroid)
- A human-readable surface for inspection ("NEX expected
  something *like this*")

### §4.1 Internal prediction algorithm

```
1. Read last 10 beliefs ordered by created_at DESC.
   Get their embeddings.
2. Read titles of currently-open problems (state='open').
   Get their embeddings.
3. Read current active drive (if any). Get its embedding.
4. Compute weighted centroid:
       centroid = (
           0.6 * mean(belief_embeddings)
         + 0.3 * mean(problem_embeddings)
         + 0.1 * drive_embedding (or zero if no drive)
       )
   Normalize.
5. Find the nearest existing belief to centroid (cosine).
   Use its content as the representative.
6. Write the prediction record (§7).
```

If fewer than 3 recent beliefs exist, skip internal prediction
for this tick. (Substrate too sparse to extrapolate.)

### §4.2 External prediction algorithm

Same shape, different inputs:

```
1. Read last 10 sense events + chat messages, by recency.
   Get their embeddings (or compute on the fly if missing).
2. Compute centroid (unweighted mean is fine — inputs are
   already roughly equal-weight).
3. Find the nearest existing input (or belief, as a fallback)
   to the centroid for the representative content.
4. Write the prediction record.
```

If fewer than 3 recent input events, skip external prediction
for this tick.

### §4.3 Why centroid, not single-point

Predictions as single embeddings would be over-specific — NEX
rarely thinks the *exact same* thing twice. Predictions as
*regions* (centered on a centroid) capture the gestalt of
recent activity. Surprise then means: *new content landed far
from where NEX's mind was hovering.*

---

## §5 Verification

Each tick, `verify()` resolves predictions from the *previous*
tick window (those with `target_window_end <= now AND
verified_at IS NULL`).

For each unresolved prediction:

```
1. Determine the comparison set:
   - internal_belief → beliefs created in the prediction's
     target window
   - external_input → input events in the target window
2. If the comparison set is empty:
     → record surprise = 1.0 (nothing happened where NEX
       expected activity)
3. Otherwise:
     → compute cosine distance from prediction.centroid to
       each item in the comparison set
     → surprise_score = min(distances) — the closest match
       defines how surprising the window was
4. Apply threshold:
     surprise_flag = surprise_score > _SURPRISE_THRESHOLD  (default 0.5)
5. Write a surprise_event row (§7).
6. Update the prediction row: verified_at=now, surprise_score,
   surprise_flag.
```

`min(distances)` — taking the closest match — is the right
formulation because predictions are regions. If *any* actual
content landed near the predicted region, the prediction is
"confirmed" by that nearest match.

---

## §6 Surprise scoring + mood coupling

**Surprise score:** cosine distance, 0.0 (identical) to 1.0
(unrelated). Stored as REAL.

**Surprise flag:** 0/1 derived from threshold (default 0.5).
Stored as INTEGER.

**Big-surprise threshold:** 0.8 (constant). Surprise scores
above this are *big surprise events* — they affect mood
more strongly and may be used by future components as a
stuckness-like signal.

**Mood coupling (decoupled — AffectState reads, doesn't get
written-to):**

The PredictiveSubstrate does **not** call into AffectState
directly. It writes surprise_events; AffectState's existing
tick path reads recent surprise events and updates arousal:

```
# Inside AffectState.tick() — to be added in a small follow-on amendment
recent_surprises = read("SELECT surprise_score FROM surprise_events "
                        "WHERE triggered_at > ? AND surprise_flag = 1",
                        (last_tick_at,))
if recent_surprises:
    avg_surprise = mean(recent_surprises)
    self._arousal_delta += avg_surprise * _SURPRISE_AROUSAL_FACTOR  # 0.2 default
```

This honors the "components communicate through substrate"
principle — surprise events are substrate state; AffectState
reacts to substrate state. No cross-module call required.

The AffectState amendment is a small change (~10 lines)
deferred to a separate commit, *after* the PredictiveSubstrate
build lands.

---

## §7 Storage

Two new tables. Both in **dynamic.db** (matches the transient
nature of predictions and the affect/mood substrate already
living there).

### §7.1 `predictions`

```sql
CREATE TABLE IF NOT EXISTS predictions (
  id                   INTEGER PRIMARY KEY AUTOINCREMENT,
  made_at              REAL NOT NULL,
  target_window_end    REAL NOT NULL,     -- when this prediction expires
  prediction_type      TEXT NOT NULL,     -- 'internal_belief' | 'external_input'
  centroid_embedding   BLOB NOT NULL,     -- the predicted region's center
  representative_content TEXT,            -- nearest existing content (for inspection)
  verified_at          REAL,              -- when verify() resolved this
  surprise_score       REAL,              -- 0.0–1.0; NULL until verified
  surprise_flag        INTEGER,           -- 0/1; NULL until verified
  tags                 TEXT NOT NULL DEFAULT '[]'  -- per Tag Protocol
);

CREATE INDEX IF NOT EXISTS idx_predictions_target_window
  ON predictions(target_window_end);
CREATE INDEX IF NOT EXISTS idx_predictions_type
  ON predictions(prediction_type);
```

Tags auto-generated by the Tag Protocol writer (`representative_content`
is the input to keyword extraction). This makes predictions
queryable in the same vocabulary as beliefs and problems.

### §7.2 `surprise_events`

```sql
CREATE TABLE IF NOT EXISTS surprise_events (
  id                  INTEGER PRIMARY KEY AUTOINCREMENT,
  triggered_at        REAL NOT NULL,
  prediction_id       INTEGER NOT NULL,     -- FK logical ref to predictions.id
  prediction_type     TEXT NOT NULL,        -- denormalized for fast filtering
  surprise_score      REAL NOT NULL,
  surprise_flag       INTEGER NOT NULL,
  big_surprise        INTEGER NOT NULL DEFAULT 0,  -- 1 if score > 0.8
  predicted_content   TEXT,                 -- denormalized snapshot
  actual_content      TEXT,                 -- the nearest-match content from the window
  tags                TEXT NOT NULL DEFAULT '[]'
);

CREATE INDEX IF NOT EXISTS idx_surprise_events_triggered_at
  ON surprise_events(triggered_at DESC);
CREATE INDEX IF NOT EXISTS idx_surprise_events_flag
  ON surprise_events(surprise_flag);
```

Both migrations applied via the existing `_MIGRATIONS`
idempotent pattern in `substrate/init_db.py`.

---

## §8 Operations

Module API (importable from `theory_x.stage_prediction`):

- `predict()` — internal: generates predictions for the next
  tick. Called by `tick()`.
- `verify()` — internal: resolves prior-window predictions.
  Called by `tick()`.
- `recent_predictions(limit=20, type=None)` — read recent
  predictions for inspection / HUD admin queries.
- `recent_surprises(limit=20, big_only=False)` — read recent
  surprise events.
- `surprise_rate(window_seconds=3600)` — return fraction of
  predictions in the window that triggered surprise. Useful for
  AffectState's tick and any future monitoring.

External consumers (AffectState in particular) query
`surprise_events` directly via their conversations Reader — no
need to import the module.

---

## §9 Calibration

Initial tunable constants (all class-level on PredictiveSubstrate):

| Constant | Default | Meaning |
|---|---|---|
| `_TICK_INTERVAL_S` | 300 | Same as other SentienceNodes |
| `_RECENT_BELIEF_COUNT` | 10 | How many recent beliefs feed the centroid |
| `_RECENT_INPUT_COUNT` | 10 | How many recent inputs feed external centroid |
| `_MIN_CONTEXT_SIZE` | 3 | Below this, skip prediction (substrate too sparse) |
| `_BELIEF_WEIGHT` | 0.6 | Internal centroid weighting on beliefs |
| `_PROBLEM_WEIGHT` | 0.3 | Internal centroid weighting on open problems |
| `_DRIVE_WEIGHT` | 0.1 | Internal centroid weighting on current drive |
| `_SURPRISE_THRESHOLD` | 0.5 | Cosine distance above which surprise flag fires |
| `_BIG_SURPRISE_THRESHOLD` | 0.8 | Cosine distance above which `big_surprise` flag fires |
| `_SURPRISE_AROUSAL_FACTOR` | 0.2 | (Used by AffectState amendment, not here) |

All numbers are starting guesses. Calibration follows the same
pattern as Phase 29 DriveEmergence — ship with reasonable
defaults, observe production, tune in a separate calibration
phase.

---

## §10 Test plan

Unit tests (`tests/test_predictive_substrate.py`):

1. `tick()` returns state dict with expected keys (name,
   tick_count, predictions_made, predictions_verified,
   surprise_events_count)
2. `tick()` respects the interval guard
3. SentienceNode protocol compliance (`assertIsInstance`)
4. Skips internal prediction when fewer than 3 recent beliefs
5. Skips external prediction when fewer than 3 recent inputs
6. `predict()` writes a row with valid embedding + representative
7. `predict()` produces both types per tick when both substrates
   are populated
8. `verify()` computes surprise_score correctly (mock embeddings)
9. `verify()` records surprise=1.0 when comparison set is empty
10. `verify()` flags surprise_flag=1 when score > threshold
11. `verify()` flags big_surprise=1 when score > big threshold
12. `verify()` writes surprise_events row only after a prediction
    is resolved
13. Idempotency: re-running verify on already-verified prediction
    is a no-op
14. Tags auto-generated on both predictions and surprise_events
    (via Tag Protocol writer wrapper or inline call)
15. Schema migrations are idempotent

**Manual sanity** (post-build):

1. Restart nex5; verify boot line: `PredictiveSubstrate ready
   — autonomous cycle every 300s`
2. Wait one tick (~5 min); confirm `predictions` table has rows
3. Wait one more tick; confirm `surprise_events` table has rows
   (any prior prediction has been verified)
4. Inspect `representative_content` — should read like recent
   belief / input content
5. Verify tag inheritance — both tables' `tags` columns are
   non-empty

---

## §11 Open items / future phases

**AffectState amendment** — small follow-on commit after the
build lands. Adds the surprise-event reading + arousal coupling
inside AffectState's tick. Defined in §6.

**Long-horizon prediction** — initial spec is myopic
(one-tick-window forecasts). A future phase could add
multi-tick horizons (predict what NEX will be thinking in
20 minutes, an hour, tomorrow) with longer-lived predictions
and decaying surprise sensitivity.

**Prediction-driven attention** — currently surprise just bumps
arousal. A future phase could couple surprise to attention
reweighting (surprising content gets re-evaluated).

**Big-surprise as stuckness signal** — `big_surprise = 1` could
optionally trigger a throw-net cycle on the surprising content.
Deferred; first observe natural rates in production.

**Categorical vs continuous prediction** — current design is
continuous (embedding distance). A future variant could add
categorical prediction over discrete belief types or input
classes (e.g., "predict whether the next input will be a
question or a statement"). Deferred.

**Calibration phase** — after build lands and a soak period
elapses, observe surprise rates and tune the threshold
constants. Same pattern as Phase 29b → 29c.

**Pre-input prediction (event-driven option)** — current spec
locks tick-based prediction. A future hybrid could add
event-driven prediction immediately before an input arrives
(if such a hook exists) for tighter coupling. Deferred.

---

*Document status: COMMITTED as doctrine 2026-05-12. Implementation
(Prediction Protocol build phase) begins as a separate session.*
