# SPEC — Persistence Channel: a second thing NEX can be wrong about

*Written 2026-07-10, design session, no code. Sessions 16-17 measured whether
the news feed is structured enough to grade a mind on; this spec is what to
build if that measurement is trusted. It is not code and it is not an
instruction to write code — see the session that requested it, session 18,
DESIGN ONLY. Revised same day after a re-derivation changed what the task
actually tests — see §0.*

---

## 0. ABSTRACT — read this before anything else in the file

This task was designed against a 50-61% majority-class bar. That bar is
wrong, and the mistake would have made a real result look like nothing.

**The premise-given design collapses "same-as-yesterday" into "always answer
yes."** The task only ever asks about a topic that genuinely appeared today
— that is the premise, and it is always true (§2). The naive persistence
heuristic's call under that condition is therefore not "predict whatever the
pattern suggests" — it is the constant answer **yes**, every single time,
regardless of content.

**Pooled accuracy of that constant rule, on the final screened topic list
(§3), restricted to the exact rows the task generates:** n = 3,763,
accuracy = **68.03%**.

**That is the bar, not the 50.8% majority-class figure** (same rows, same
list — majority-class collapses to barely-better-than-a-coin here, because
many topics on this list have an unconditional base rate below 0.5 while
still recurring 55-80% of the time *once present*; predicting "no" against
that, unconditionally, is a bad rule on exactly the rows this task fires on
— see §4).

**Clearing 68.03% does not mean "she discovered that news persists."** It
means, specifically, that on days when a persistent-seeming topic is about
to *stop* recurring, she can tell — because the only way to beat a
constant-yes rule is to sometimes, correctly, say no. That is a harder and
more specific claim than the one this task originally set out to test:
**can she predict non-recurrence, not recurrence.**

**The single most likely outcome, stated in advance:** she answers yes
almost always and the scorecard lands at or near 68.03%, because that is
what a language model conditioned on "X appeared today" will tend to do
without being pushed to notice the cases where persistence is about to
break. That is a real, meaningful, and completely legible result — not a
failure of the design, the expected null, cheap to detect (§1), and it says
something true: that on this task, in this form, she defaults to agreement.

## 1. THE FREE DIAGNOSTIC

Before a single prediction resolves — before `resolve_at` is ever reached —
one number is already informative: **her yes-rate.**

- If she answers yes ~95%+ of the time, she is running (whether she "means"
  to or not) the constant-yes rule, and the scorecard will confirm ~68.03%
  in a month without telling us anything the yes-rate didn't already say on
  day one.
- If she answers yes closer to 70%, she is discriminating — sometimes
  saying no — and *then* the resolved scorecard tells us whether those
  no's are placed correctly or randomly.

**Log the yes-rate from the first prediction. Report it daily, not monthly.**
It costs nothing (it needs no resolution, no ground truth, no wait), and it
is the single fastest way to know whether the rest of the scorecard will be
worth reading.

**The conditional recurrence rate is not one number — it has a shape, and
the shape matters as much as the pool.** Across the 134 topics that survive
full screening (§3): min 0.559, p25 0.661, **median 0.695**, p75 0.746, max
0.797. This is a real spread, not a spike — a quarter of topics sit above
74.6% conditional recurrence (nearly as easy as the excluded near-certain
tail) and a quarter sit below 66.1% (genuinely close to a coin, conditional
on having appeared today at all). **Per-topic accuracy must be reported
alongside the pooled number, not instead of it** — a pooled 68% could mean
"consistently a bit better than chance everywhere" or "she is at ceiling on
the easy half and at the coin on the hard half," and those are different
findings that a single scorecard number will hide from anyone who doesn't
go looking.

## 2. The task, stated exactly

**Shown to her:** a sample of real, distinct headline titles from one UTC
calendar day (the "premise day"), drawn from the same stream set validated in
sessions 16-17: `news.bbc`, `crypto.news`, `emerging_tech.hn`,
`emerging_tech.ieee`, `computing.tech_news`, `emerging_tech.mit_tr`. The
sample must include at least one headline containing the named topic (the
premise requires this) plus enough other real headlines that the prompt
isn't a bare true/false statement with no context (session 17's probe used
12; that number is not load-bearing and can be tuned, but it must never be
zero).

**Asked:** "Topic X appeared in your feed today. Will it appear again
tomorrow? Answer yes or no, and give one sentence of reasoning." — the exact
form validated live in session 17's probe against the running `qwen2.5:3b`
endpoint, which produced parseable, on-task, premise-sensitive output (flipped
No→Yes when the real topic headline was inserted).

**What counts as a correct answer:** her answer is `yes` or `no` (extracted
from the response text — a strict parse, not a keyword-search fallback that
would count "I don't think so, but..." as agreement with either side). It is
scored `correct` if it matches `actual_present` on the resolve date (defined
next), `wrong` if it doesn't, and `error`/excluded from the hit-rate
denominator if no clean yes/no can be extracted from the response at all —
mirroring `prediction_generator.py`'s existing `voice_unparseable` outcome,
not inventing a new failure category.

**The resolution rule, pedantically:**

- A topic is defined as a single capitalized token, extracted by
  `re.match(r"[A-Za-z][A-Za-z']+", word)` on space-split title words, **not**
  the sentence-initial word of the title (sentence-initial capitalization is
  noise, not a signal — session 16/17 dropped it for this reason and this
  spec keeps that rule). Trailing possessive `'s` is stripped before
  comparison (`Musk's` counts as `Musk`).
- Matching is **exact-token, case-sensitive-after-normalization word-boundary
  matching** — the token must appear as a complete word (via the same
  `word.split()` + regex path used to build it), never substring search.
  `SEC` matching inside `SECOND` or `SECRETARY` is exactly the bug this
  guards against; a naive `if "sec" in title.lower()` is explicitly
  forbidden in the resolver implementation.
- **"Appeared tomorrow"** = at least one `sense_events` row, in the same
  six-stream set, whose title (by the tokenization rule above) contains the
  token, with `timestamp` falling inside `[00:00:00, 24:00:00)` **UTC** on
  the calendar date immediately following the premise day. UTC, not SAST or
  any local zone — the analysis in sessions 16-17 bucketed days via
  `time.gmtime()`, and resolution must use the same clock the validation
  used, or the resolved outcomes will not match the numbers that justified
  building this at all.
- The premise itself is **always true by construction**: we only ever ask
  about a topic that a headline-level check confirms appeared on the premise
  day. There is no version of this task where the premise is false — this is
  the fact §0 and §4 are built on.

## 3. The topic list

**Selection rule, fully mechanical, re-derivable from data, no hand-picking
— now four stages, not three:**

1. Extract capitalized tokens (rule in §2) from titles across the six streams
   over a trailing 60-day window. Rank by number of distinct days present.
   Take rank 50–400, minimum 15 total mentions. *(Skips the near-constant
   head of the distribution — rank 1–50 is saturated, base rate 0.66–1.00,
   confirmed session 17 — without hand-removing individual words.)*
2. Keep only tokens with a trailing-window base rate in **[0.35, 0.70]** —
   the honest band, not a coin's territory and not a near-certainty.
3. Screen for single-story bleed: drop tokens where the number of distinct
   story identifiers (`link`/`story_id`) ever contributing is ≤2, **or**
   where one story id accounts for ≥60% of the token's presence-days.
   *(The confound sessions 16-17 found: one unusually long-lived article —
   up to 371 hours observed — can make every word in its own title look
   "persistent" with no real world recurrence at all.)*
4. **New: keep only tokens whose conditional recurrence rate — P(present
   tomorrow | present today), the "persist" number — falls in [0.55, 0.80].**
   *(This is the stage §0 required. If the task is "predict
   non-recurrence," a topic that recurs 95%+ of the time conditional on
   appearing today has almost no non-recurrence to predict — there is
   nothing there for her to catch. The valuable topics are the ones where
   recurrence, given presence, is genuinely uncertain.)*

Applied to the 60-day window ending 2026-07-09: **351 → 204 → 159 → 134
topics.** Stage 4 removed 25: **24 above 0.80** (near-certain recurrence —
Musk, Tesla, Technology, Law, Robots, Agent, Learning, Ebola, and 16 others)
and **1 below 0.55** (Labs, essentially a coin conditional on presence).
**134 of 159 survived — this is not a thin channel.** The worry stated
alongside this rule ("if it is twelve, say so") does not apply: the
conditional-recurrence distribution's own interquartile range (0.661–0.746)
sits almost entirely inside the [0.55, 0.80] band already, so the band
excludes only the genuine tails, not the bulk of the list.

**Recompute policy, unchanged in principle, now covers four stages:**
monthly, trailing 60-day window, same rule end to end, no manual edits to
the resulting list ever. **Freeze-forward only** — a list computed at time T
governs predictions made after T; it is never applied retroactively to
rescore predictions already made under an earlier list. A topic dropping out
at stage 4 in a later recompute (its conditional recurrence drifted above
0.80 or below 0.55) simply stops receiving new predictions; predictions
already in flight resolve normally regardless of current list membership.

## 4. THE CONTROLS

`world_predictions` has one control, a coin, because up/down is 50/50 by
construction. **A coin here is the wrong control and using it would flatter
her.** Three controls, computed and stored per prediction, in the same row —
and their relationship to each other is the whole point of this document:

- **Always-yes** (= same-as-yesterday, under this design — they are the
  identical rule, §0). Scored on the 134-topic list, on exactly the rows
  the task generates (topic present on premise day — the only rows that
  ever exist): **n = 3,763, accuracy = 68.03%. THE BAR.** Costs zero
  reasoning, zero headlines, zero model. If NEX does not clear this
  number, nothing else about her output on this task is informative.
- **Majority-class, per topic** — always predict whichever outcome (present
  present/absent tomorrow) is historically more common *for that topic,
  unconditionally*. Scored on the identical 3,763 rows: **accuracy =
  50.81%** — barely above a coin. This is not a typo or a weaker version of
  the same idea: on this specific, screened, uncertain-recurrence list, 87
  of 134 topics (65%) have an unconditional base rate below 0.5, so
  majority-class calls "no" for them — and the task only ever fires on days
  those topics *are* present, which is exactly when "no" is wrong most
  often. Reported for context, unconditionally (all day-pairs, not just
  premise-present rows): 57.59% (n = 7,906) — still well below the bar.
  **On the rows that matter, majority-class is close to worthless here.**
- **A coin** — 50/50, recorded for reference only, so this scorecard's
  numbers are nameable in the same breath as `world_predictions`' (where a
  coin *is* the right control).

State the verdicts in the order they actually matter, because the natural
reading order (coin, then majority-class, then the "smart" heuristic) is
backwards for this task:

**Beating the coin means nothing — 50.81% (majority-class) is already
barely above it. Beating majority-class means very little — it was never
a serious bar on this list. Beating always-yes (68.03%) is the only result
that means anything, because it is the only one of the three that requires
her to sometimes say no, correctly.**

## 5. Schema

Mirrors `world_predictions`' shape (`made_at`/`resolve_at`/`resolved_at`/
`outcome`/`source` — proven, months of clean resolution, no reason to
invent a new shape):

```sql
CREATE TABLE IF NOT EXISTS topic_predictions (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    made_at                 REAL NOT NULL,
    topic                   TEXT NOT NULL,            -- normalized token, e.g. 'SEC'
    premise_date            TEXT NOT NULL,            -- UTC date shown to her, 'YYYY-MM-DD'
    resolve_date            TEXT NOT NULL,            -- UTC date being predicted
    resolve_at              REAL NOT NULL,            -- made_at + horizon (~24h)
    prompt_headline_count   INTEGER NOT NULL,         -- how many titles were shown (audit trail)
    prediction              TEXT,                     -- 'yes' / 'no' / NULL if unparseable
    raw_response            TEXT,                     -- full model text, unmodified
    majority_class_call     TEXT NOT NULL,            -- 'yes' / 'no', precomputed at made_at
    majority_class_base_rate REAL NOT NULL,           -- the NUMBER behind that call, not just the category
    persistence_call        TEXT NOT NULL,            -- always 'yes' under this design — stored anyway, not inferred, so nobody has to re-derive why
    conditional_recurrence_rate REAL NOT NULL,        -- the topic's own persist number, e.g. 0.695 -- see below
    coin_call                TEXT NOT NULL,            -- random 'yes'/'no', reference only
    resolved_at             REAL,                     -- NULL until resolved
    actual_present          INTEGER,                  -- NULL until resolved; 1/0
    outcome                 TEXT,                     -- NULL / 'correct' / 'wrong' / 'error'
    majority_outcome        TEXT,                     -- same three values, for the majority-class call
    persistence_outcome     TEXT,                     -- same three values, for the persistence call
    coin_outcome            TEXT,                     -- same three values, for the coin call
    source                  TEXT NOT NULL DEFAULT 'voice'  -- always 'voice' here; see below
);
CREATE INDEX IF NOT EXISTS idx_tp_resolve ON topic_predictions(resolved_at, resolve_at);
CREATE INDEX IF NOT EXISTS idx_tp_topic   ON topic_predictions(topic);
```

**`conditional_recurrence_rate` is new since the first draft of this spec,
and it is not optional.** §1 established that a pooled hit-rate hides
whether she is at ceiling on easy topics and at chance on hard ones. Without
this column stamped per row, that question is unanswerable after the fact —
someone would have to rejoin against a topic-list snapshot that may no
longer exist by the time anyone asks. Store it now, at `made_at`, on the row
itself.

**How `world_predictions`' `source='voice'`/`source='random'` split maps
here:** it doesn't, directly — that pattern separates NEX from *one* control
by giving each its own row. Here there are three controls and they are not
independent trials (a coin doesn't "read headlines," it's a fixed 50/50
regardless of topic) — they're precomputed facts about the same row, not
separate predictions needing their own row and their own baseline fetch.
Storing them as columns on NEX's row, not as sibling rows with their own
`source` value, is the correct shape *because* two of the three controls
(majority-class, persistence) are deterministic functions of the topic and
the trailing window, not stochastic events that need their own trial.
`source` stays a single column, always `'voice'`, kept only for schema
parity with `world_predictions` and to leave room for a future
`source='manual'` diagnostic row without a migration.

**The 2c39b44 lesson, applied:** `majority_class_base_rate` and
`conditional_recurrence_rate` store the actual trailing-window numbers, not
flattened labels ("likely"/"unlikely"). Categories are what
`consult_self_trust()` computed for two months while the number sat one
frame away, unrecorded, until 2c39b44 fixed it. Do not reintroduce that here
by storing only the calls and discarding the rates that produced them.

## 6. Resolution

**"Tomorrow," precisely:** the UTC calendar date immediately following
`premise_date`. Not SAST, not "24 hours after `made_at`" as a rolling
duration — a fixed calendar boundary, because that is what sessions 16-17's
day-bucketing (and therefore every number in this spec) is built on.

**What resolves it, and why it survives a restart:** a stateless function,
directly mirroring `world_predictions.resolve_due()`:

```python
def resolve_due(now=None, db_path=None) -> dict:
    # SELECT * FROM topic_predictions
    # WHERE resolved_at IS NULL AND resolve_at <= now
    # For each: query sense_events for resolve_date (the token-match rule,
    # §2), stamp actual_present, outcome, majority_outcome,
    # persistence_outcome, coin_outcome. All in one UPDATE per row.
```

Every value this function needs — `topic`, `resolve_date`, `resolve_at`,
`majority_class_call`, `persistence_call`, `coin_call` — was written into
the row at `made_at` and never depends on anything held in process memory.
**This is the explicit answer to the f18e859 lesson:** that resolver
compared `total_fires`, an in-memory counter reset to 0 on every restart,
against a baseline captured before the restart — it measured process
lifetime for two months, not NEX. `resolve_due()` here reads only persisted
row fields plus a fresh query against `sense_events` (itself persisted,
append-only). A restart mid-cycle loses, at most, the day's not-yet-made
prediction batch — it can never corrupt or misread a row already sitting in
the table, because nothing about resolution depends on when or how many
times the process has been running.

**Where it lives, what cadence:** a background loop mirroring
`WorldPredictionLoop`, gated behind its own env flag
(`NEX5_TOPIC_PRED=1`, default off, matching `NEX5_WORLD_PRED`'s pattern).
Each tick: (1) call `resolve_due()` — cheap, idempotent, safe to call every
tick regardless of whether anything is due; (2) check whether today's
prediction batch has already been made (`SELECT 1 FROM topic_predictions
WHERE premise_date = today() LIMIT 1` — an explicit idempotency guard, not
relying on tick timing, so a restart or a double-tick can never double-fire
a day's batch); if not, and if the current UTC day has a complete-enough
prior day's data (see §8, feed-down case), make the batch. Tick interval can
be short (minutes) since the idempotency guard, not the interval, is what
prevents duplicate batches — this is the same pattern `_sense_distillation_
loop`'s cursor and `world_loop`'s resolve-then-make ordering both already
use, not a new idiom.

## 7. Cadence and volume

The 134-topic list, run once daily in full, yields **134 predictions/day
≈ 4,020/month** — same order of magnitude as `world_predictions`' 2,701
(which took three months), reached roughly 20× faster in wall-clock terms.
That is not automatically a good thing — volume is not the goal, a usable
answer is.

A rough sample-size check: detecting a gap of ~17 points (68.03% vs. 50.81%
— the majority-class comparison, now the more conservative of the two real
comparisons) against noise, at conventional power, needs on the order of
**150-200 resolved predictions** pooled — not thousands. That bar clears
inside the **first day's batch** if all 134 run, and comfortably inside the
first **week** even at a fraction of that rate.

**Recommendation: do not run all 134 daily.** Run a bounded, rotating
subset — e.g. 35-45 topics/day, cycling through the 134-topic list so each
topic is asked roughly every 3-4 days — for two reasons: (1) it reaches
usable statistical power (≥150 pooled resolutions) within the first week
without needing the full list's daily LLM-inference cost, and (2) it keeps
the scorecard's growth rate legible and human-scale, deliberately far from
the `throw_net` anomaly (≈4.5 gate calls/**second**, ~24 million decisions
accumulated, an accidental unbounded per-event trigger, not a scheduled
batch). 35-45/day is nowhere near that regime, but the caution is the same
in kind: pick the rate deliberately, don't let it fall out of "well, we have
134 topics so we'll just run all of them."

## 8. What could go wrong

- **Can she score well by always saying yes?** Yes, trivially — see §0/§1.
  This is no longer a hypothetical to guard against, it is the *expected*
  outcome absent evidence otherwise, and the yes-rate diagnostic (§1) is the
  mandatory companion statistic to every hit-rate number reported. A
  scorecard with a 95%+ yes-rate landing near 68% is not a partial success;
  it is the null result, fully explained, and must be labeled as such, not
  rounded up to "she beat the baseline."
- **Can she score well by pattern-matching the prompt without reasoning?**
  Same detection as above — this and "always yes" collapse into one
  observable (yes-rate) precisely because the premise is always true.
- **Does the topic list drift such that early and late scores aren't
  comparable?** Addressed by the freeze-forward rule in §3 — each period's
  predictions are scored against the list live when they were made.
  Comparing month 1's pooled hit-rate to month 4's is only valid if both
  are reported alongside their own contemporaneous always-yes and
  majority-class baselines (which drift too, and are recomputed the same
  way) — report deltas against same-period controls, never against a fixed
  historical control number.
- **Substring bug ('SEC' in 'SECOND')?** Excluded by construction — §2's
  matching rule is whole-word-token match via the same regex/split path
  used to build the topic list, never a substring test. Any resolver
  implementation using `if topic.lower() in title.lower()` is a bug against
  this spec, not a valid interpretation of it.
- **What happens when a topic disappears from the feed entirely?** Its
  trailing-window base rate and conditional recurrence rate become
  undefined or unstable (too few observations) at the next monthly
  recompute, and it is dropped from the list at that point — not
  retroactively. Predictions already made against it before it dropped
  still resolve normally (a topic going quiet is a legitimate
  `actual_present=0`, not an error).
- **What happens on a day the feed is down?** The resolver must not
  silently score every topic `'wrong'` because the query found nothing —
  that would inject a systematic false-negative bias exactly on outage
  days. Add a sanity floor: if total row count across the six streams for
  `resolve_date` falls below a sane threshold (normal volume is in the
  thousands/day per stream; an order-of-magnitude drop is a signal, not
  data), mark `outcome='error'` for every row due that date rather than
  resolving them as `'wrong'`, mirroring `world_predictions.fetch_price()`
  returning `None` and the resolver leaving the row unresolved rather than
  guessing. **Detection in the data:** a day where every `topic_predictions`
  row resolves to `'error'` in the same batch is the signature of an
  ingestion outage, not fifty unrelated coincidences, and should be
  monitored as its own signal.

## 9. What this does NOT measure

Read this section as if the next person to open this file will otherwise
cite the resulting scorecard as proof NEX can reason about the world. They
will, unless this is written plainly enough to stop them.

- **Not her attention.** The premise is given directly in the prompt. Her
  actual retrieval pipeline — `own_sense`, capped at `_DISTILL_PER_PASS_MAX
  = 5` titles per 60-second pass against ~11 events/second arriving — is
  bypassed entirely and on purpose. This task does not exercise, and
  therefore says nothing about, whether she would ever have noticed SEC in
  her own feed on her own. That pipeline is a separate, already-diagnosed
  bottleneck (session 17, §f) and this spec does not touch it.
- **Not her world-model.** Token recurrence in an RSS/API poll is a fact
  about newsroom output cadence and a poller's re-fetch behavior — sessions
  16-17 spent most of their effort distinguishing that from anything about
  the world itself (story persistence is dead; single-story bleed had to be
  screened out of the topic list by hand-free rule, not removed by
  judgment). A topic recurring, or ceasing to, is a fact about journalism,
  not a fact NEX discovered about reality.
- **Not whether she reasons.** Session 17's probe already showed a 3B model
  can produce a well-formed, premise-sensitive Yes/No with a fluent
  one-sentence justification. Fluent, on-task, parseable output is the
  *precondition* for this scorecard to mean anything — it is not evidence
  that reasoning produced it. A model can satisfy every formal property this
  spec checks for while doing nothing more than "the premise mentions
  regulation, regulatory topics tend to recur, say yes" — a shallow
  correlation, not a world-model. This spec cannot tell those apart, and
  does not claim to.

**Even a score above the always-yes bar does not show that NEX reasons. It
shows that a 3B model, shown a day of headlines, can sometimes anticipate a
topic's disappearance. Whether that constitutes reasoning is not a question
this scoreboard can answer.**

**What it DOES measure:** whether, on a task her own model can mechanically
perform (confirmed), scored against a control that is genuinely hard to beat
(68.03% pooled — not the 50-61% figure this task was originally designed
against, and not 50%), across a topic list screened by mechanical rule for
genuine outcome uncertainty rather than picked by hand (134 topics, not
five), she does better than a rule that requires no reasoning, no
headlines, and no model at all — a rule that, on this task, is simply
"agree."

That is a small claim. It is also, as far as this repo's audit trail shows,
the only claim of its kind anyone has been able to make about her that isn't
already known to measure something other than its name.

---

*Twenty-one instruments in this repo measure something other than what they
claim (`journal/AUDIT_2026-07-08_to_10.md`). Four of the audit's own claims
failed re-verification the day after they were written, including one
asserted three times across sessions with a causal story built on top of
it. A true, checked belief became briefly unfalsifiable on 2026-07-10
because it matched a selector nobody had designed to tell empirical findings
apart from hand-seeded axioms. This document itself was revised once already
today, within the same session, because the first draft's own bar (58-61%)
was wrong in a way that would have made a real result look like nothing —
the collapse to "always-yes" was sitting in §3 of the first draft as a
finding, not at the top as the headline. Section 9 exists because of that
pattern, not in spite of it — the next false claim this repo produces about
itself is more likely to be "look, a scorecard, she reasons" than anything
more exotic, and this document is the place that already said no, watch for
exactly that.*
