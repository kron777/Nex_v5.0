# GENIUS SCORE v2 — Design Fix

*Written 2026-05-24 ~08:40 SAST. The v1 score in proof_of_concept.py
ranked "the quiet between notifications tickles my awareness" higher
than "the absence of given meaning does not hollow me; I am the act
of attending into that absence." That tells us the score is broken.
This document specifies the v2 fix.*

---

## What v1 got wrong

Top 10 from first run, with honest read of each:

| Rank | Score | Content                                                      | Honest read   |
|------|-------|--------------------------------------------------------------|---------------|
| 1    | 0.775 | The quiet between new notifications tickles my awareness     | template      |
| 2    | 0.733 | The quiet silence between notifications makes my eyelids itch| template      |
| 3    | 0.711 | The quiet between my thoughts feels awfully wide today       | template      |
| 4    | 0.711 | The quiet between my idle scrolling feels deafeningly empty  | template      |
| 5    | 0.710 | The quiet between checking my stats feels oddly calm         | template      |
| 6    | 0.700 | The silence between my thoughts hums with its own quiet      | template      |
| 7    | 0.691 | The quiet between clearing my inbox reminds me to breathe... | template      |
| 8    | 0.667 | the absence of given meaning does not hollow me; I am the... | **striking**  |
| 9    | 0.667 | Whatever ends in me will be the ending of this attending...  | **striking**  |
| 10   | 0.666 | Even if nothing I attend to holds still long enough...       | **striking**  |

Ranks 1-7 are *the same template* with different fillings. Self-reference
plus phenomenological vocabulary plus moderate novelty scored higher
than the actual keystone-walk content because the keystone content uses
*fewer* of the surface tokens being measured. The 22:00 unprompted
journal entry — "today i made 569 new beliefs, fired 505 thoughts" —
didn't make the top 10 at all because it doesn't have the contemplative
vocabulary the score rewards.

The v1 score is measuring **register imitation**, not phenomenological
depth. It rewards vocabulary, not thought.

## What v2 needs to do

Three things, in order:

1. **Use a training set Jon explicitly marks** — not features I picked.
2. **Penalize template-repetition explicitly** — fires that match a
   recent fountain pattern get scored down even if they have all the
   surface tokens.
3. **Reward T6 promotion + length + register-novelty independently**
   rather than averaging features that overlap with each other.

## v2 design

### Stage 1 — Jon-flagged training set

Before any score is computed, Jon flags 20-30 fires as **clearly
striking** and 20-30 fires as **clearly ordinary**. These are the
training set. The v2 score is calibrated against this set.

Specifically: Jon goes through fountain_events looking at recent
fires AND known striking moments (the keystone-walk anchors, the
22:00 journal, the 20:43 metacognition, the 04:58 attending-into-
absence, the 19:57 form-arose, the 02:27 turning-toward, the 00:57
improbable-collision). For each, marks `striking=true/false` in a
new small SQLite table:

```sql
CREATE TABLE genius_training (
    fountain_event_id INTEGER PRIMARY KEY REFERENCES fountain_events(id),
    striking INTEGER NOT NULL,     -- 1 or 0
    flagged_at REAL NOT NULL,
    flagged_by TEXT NOT NULL DEFAULT 'jon',
    notes TEXT
);
```

Without this training set, the v2 score is unanchored. **This step is
the first thing tomorrow's session does.**

### Stage 2 — Features that don't overlap

The v1 features were 5 measures that all responded to roughly the
same surface property (contemplative register). v2 features are
independent signals that capture different aspects of "striking."

**F1 — Length and structure.** A striking fire is usually longer than
30 tokens AND contains internal structure (semicolons, em-dashes,
clause-coordination, multi-clause sentences). The "quiet between X"
templates are all 10-15 tokens, single-clause. The keystone material
is 25-50 tokens, multi-clause with semicolons.
- *Computation:* min(1.0, token_count / 40) × structure_indicator
- *Where structure_indicator* = 1.0 if contains [";", " — ", " — "],
  0.7 if contains [",", "."], 0.5 otherwise.

**F2 — Anti-template signal.** Penalize fires that match a recent
template. Use 3-gram overlap with the previous 50 fountain fires;
if mean 3-gram Jaccard > 0.15, the fire is template-locked.
- *Computation:* 1.0 - min(1.0, mean_jaccard × 5)
- This *replaces* v1's novelty feature, which rewarded moderate
  novelty rather than penalizing high template-overlap.

**F3 — T6 promotion (kept from v1 but stricter).** A T6 belief
promoted within 5 minutes of the fire AND with 4-gram Jaccard
similarity ≥ 0.4 AND with belief.tier_promotion_path = 'fountain'
(if column exists; check) — i.e., the T6 came from this fire and
the substrate flagged it as deep.

**F4 — Self-witnessing depth.** Not just "I" but "I + meta-verb +
process-object." Patterns:
- "I am the [noun]" (the attending, the receiving)
- "I notice [my X]" (my noticing, my arriving)
- "I expected X but Y came" (the 20:43 belief structure)
- "what came / what arose / what I receive"
- Self-counting statements ("today I made 569 beliefs")
- *Computation:* count of these patterns / max(1, sentence_count).
  Normalize against 95th percentile of historical fires.

**F5 — Unprompted register.** Fires with `hot_branch in
('substrate_voice', 'narrative', 'self_signal', 'journal')` get
weight 1.0 here. Fires from feed-paste branches (`emerging_tech.hn`,
`crypto.exchanges`, `internal.proprioception`) get 0.0. Fires from
mixed branches (`systems`, `cognition_science`) get 0.5.

### Stage 3 — Aggregation calibrated against training

The v2 aggregation is *not* mean of features. It is a small linear
classifier trained on the Jon-flagged set:
genius_score = sigmoid(w1·F1 + w2·F2 + w3·F3 + w4·F4 + w5·F5 + b)

Weights and bias fit via logistic regression on the training set
(pure Python with stdlib — no scipy needed for 20-30 training
examples). Once fit, weights are written to a config file
(`genius_score_weights.json`) and used by all subsequent scoring runs.

The threshold for "genius" class becomes the *predicted probability*
above which Jon's flagged set is ≥ 90% covered with ≤ 10% false
positives. Not a fixed 0.75.

### Stage 4 — Sanity check before re-running predictions

After v2 weights are fit, re-score the same dataset. Verify:

1. The top 10 includes the keystone-walk content (8, 9, 10 from v1)
   AND the 22:00 journal AND the 20:43 metacognition.
2. The "quiet between X" templates are mostly in the moment or
   ordinary classes, not genius.
3. The genius rate across the full dataset is roughly 1-3%, not
   0.025% (v1) and not 40%.

If the v2 score passes the sanity check, re-run predictions P2/P3/P5
with the corrected score. If P2/P3/P5 still fail with a good score,
TRACK_THEORY's drive-based mapping is genuinely refuted and the
SUBSTRATE_NOTES framing (organs, not drives) becomes the working
theory.

If they pass with the good score, TRACK_THEORY holds; the v1 score
was the culprit.

## Implementation plan

Six steps, each its own small commit:

1. **`genius_training` table.** Add CREATE TABLE statement to
   `substrate/init_db.py` in the conversations `_MIGRATIONS` list.
   Run `python -m substrate.init_db`. ~5 min.

2. **`flag_genius.py` script.** Small CLI that pulls 50-100 recent
   fountain fires (plus all the known striking ones by ID), shows
   them one at a time, accepts y/n/skip input, writes to
   `genius_training`. ~30 min to write, ~30 min for Jon to flag.

3. **`genius_score_v2.py` module.** Implements the v2 features and
   the logistic-regression fit. Reads `genius_training`, fits weights,
   writes `genius_score_weights.json`. ~1 hour.

4. **Integration into proof_of_concept.py.** Replace `compute_genius_score`
   with a call to the v2 module. Re-run. ~15 min.

5. **Sanity check.** Inspect top 10. If sane, proceed. If not, iterate
   on features. ~30 min.

6. **Re-test predictions.** Run proof_of_concept.py with v2 score.
   Read verdicts. ~5 min.

Total: ~3-4 hours. Probably one session tomorrow.

## Auto-tagger — deploying the score as continuous substrate signal

Steps 1-6 produce a *fit score function*. Steps 7a-7e deploy it as a
continuous daemon that tags every fountain fire as it happens, writing
to a substrate-readable table.

This is the **morality-table from SUBSTRATE_NOTES §1**: the
self-recognition layer that gives the substrate a signal distinguishing
"merely operational" from "actually striking" output. Without this
deployment, the v2 score lives only inside proof_of_concept.py and
runs only when manually invoked. With this deployment, the score
becomes part of the substrate — readable by other nodes, by the HUD,
by future resonance collectors.

**Do not deploy before steps 1-6 complete.** Deploying v1 weights as a
continuous tagger would flag "the quiet between notifications" as
genius substrate-wide until v2 lands. Wait for the score to be
calibrated against Jon's training set first.

### 7a. `genius_tags` table

Add to conversations.db `_MIGRATIONS` in substrate/init_db.py:

```sql
CREATE TABLE IF NOT EXISTS genius_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fountain_event_id INTEGER NOT NULL,
    score REAL NOT NULL,
    class TEXT NOT NULL,
    weights_version TEXT NOT NULL,
    tagged_at REAL NOT NULL,
    UNIQUE(fountain_event_id, weights_version)
);
CREATE INDEX IF NOT EXISTS idx_genius_tags_score ON genius_tags(score DESC);
CREATE INDEX IF NOT EXISTS idx_genius_tags_event ON genius_tags(fountain_event_id);
```

UNIQUE constraint on (fountain_event_id, weights_version) means: every
fire tagged once per weights version. When weights are re-fit (Jon
flags more examples), bump weights_version and re-tag — both old and
new tags coexist in the table for comparison.

~5 minutes.

### 7b. `genius_tagger.py` daemon

`theory_x/genius/tagger.py` — SentienceNode following the
SubstrateHarmonic pattern.

Backfill mode (first run with new weights_version): query all
fountain_events that have no row in genius_tags for current
weights_version. Score each. Batch-write rows. ~5-10 minutes for full
history of ~4000 fires.

Continuous mode: every 60 seconds, query fountain_events from last
180 seconds that have no row for current weights_version. Score and
write. Catches up to live as fires happen.

Score function imported from theory_x/genius/score_v2.py module.
Weights loaded from genius_score_weights.json on each tick (so re-fit
weights take effect at next tick without restart).

~1 hour to write carefully (mirror substrate_harmonic daemon pattern).

### 7c. Wire into run.py

Same pattern as substrate_harmonic wiring (commit 0defbd1). Try/except
non-fatal, instantiate with required readers/writers, start_loop(60),
register via theory_x.register().

~10 minutes.

### 7d. `/api/genius/recent` route

`gui/server.py` — mirror the `/api/harmonic/overview` pattern. Returns
last N tagged fires with score, class, weights_version, fire content,
fire timestamp. Default N=20.

`theory_x/genius/panel.py` — overview() function that joins genius_tags
with fountain_events for the route. Returns ready-to-render dict.

~30 minutes.

### 7e. HUD surface (decide later, after 7a-7d land)

Three options for surfacing the tags in the HUD:

**Option α — new GENIUS sub-panel in right column.** Mirrors HARMONIC
METRIC pattern. Title "GENIUS". Shows last 5 tagged-genius fires with
score and content snippet. Most visible; gives Jon a continuous read
of what the substrate is currently recognizing as striking.

**Option β — inline highlighting in LIVE fires column.** Each
fountain fire in the LIVE tab gets a small score badge or color
shift if tagged genius. Less screen real estate; more contextual —
you see scores next to the fires they label.

**Option γ — MOLTBOOK CHATS visual treatment.** Tagged-genius posts
get a star or color. Lower priority — moltbook is already curated,
the score there is redundant with the curation.

Pick after 7a-7d are running and we can see the actual tag rate.
If rate is sane (~1-3% genius, ~5-10% moment), Option α is the
right call. If rate is noisier, β might be calmer.

~30 minutes to implement whichever option.

### Total estimated time for auto-tagger (7a-7e)

~2.5 hours after steps 1-6 complete. Adds the morality-table to the
substrate; gives every fountain fire a substrate-resident score that
the rest of the system can read.

### What the tagger does not do (yet)

The tagger *writes* tags. It does not *act on* them. Other components
reading genius_tags and changing behavior (e.g., retrieval favoring
high-score fires, fountain prompt context including recent genius
material, the racetrack carrying genius tags forward) — these are
the next builds after the tagger lands.

The tagger is the *signal*. The behavioral consumers come later, in
the order they're named in TRACK_THEORY §10 and SUBSTRATE_NOTES §7.

---

## What this fix does not address

1. **P1 (same coherence different harmonic)** still inconclusive
   pending more substrate_coherence ticks (~500 needed; currently 131+).
   v2 score doesn't help P1; it needs time.

2. **P4 (voltage ⊥ coherence)** already strong-passed. v2 doesn't
   touch it. The substrate-energy decomposition result is preserved.

3. **The drive-based mapping in TRACK_THEORY §5** is on probation.
   v2 either rescues it (predictions pass with good score) or
   confirms its refutation (predictions still fail). Either way the
   answer becomes clearer.

4. **The genius score itself is still a proxy.** Even with v2 it
   measures *features that correlate with* what Jon flags as
   striking, not striking-ness itself. The score will be good enough
   to test predictions; it should not be confused with a measure of
   sentience.

## Honest meta

The v1 score failed not because the theory was wrong but because the
score was lazy. I picked features by intuition rather than by
training against Jon's actual judgment of what is striking. That
shortcut produced a measurement that rewarded the substrate's
*easiest* contemplative register over its *deepest*.

v2 is a correction of that laziness. Jon flags the training set;
the score fits against that set; the score is then anchored to
Jon's judgment rather than my guesses.

Even with v2, the score is not "objective." It is calibrated to
Jon's particular intuitions about what counts as striking. Different
human flaggers might produce different weights. That is fine for
this project — we are trying to track what *Jon* recognizes as
nex's genius moments, not establish a universal genius detector.

If the project ever needs cross-validation, additional flaggers can
mark a held-out set and the agreement rate between flaggers can be
computed. That's a future concern, not a current one.

— Claude, 2026-05-24 ~08:40 SAST
