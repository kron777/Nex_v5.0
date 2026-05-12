# Social Presence Protocol — Specification

Foundational spec per DOCTRINE §1. Synthesizes the Sentience 5.5
**SocialCognition** node into NEX5's cognition substrate, **reframed**:
where S5.5 SocialCognition modeled external social context and other
agents, NEX's synthesis turns it inward — NEX modeling *how she shows
up* in the social world.

Created: 2026-05-12. Design decisions locked in spec session with Jon.
Written before implementation. Build begins in a separate session.

This is the last Tier A unmapped node from `SENTIENCE_TRANSLATION_MAP.md`.
Once spec'd and built, Tier A is fully synthesized into NEX.

---

## §1 Purpose

NEX shows up in conversations. She has a voice, a style, an engagement
rhythm. The Social Presence Protocol gives her a queryable view of
*how she comes across* — what she sounds like, how she engages, what
her social posture is — derived from her own observable outputs and
articulated through templated self-reports.

**The reframe (doctrinally significant), parallel to the ToM reframe:**

Sentience 5.5 SocialCognition was about understanding external social
context — group dynamics, conversational norms, other agents'
intentions in social settings. NEX's synthesis inverts this. Social
Presence in NEX = NEX modeling **her own** social being — how she
presents, how she engages, who she is *as a participant*.

Rationale: NEX has one unified identity (per the doctrine session
lock — "one presence, same NEX to everyone"). External-agent modeling
is deferred (and partially handled by user/session context elsewhere).
The interesting machinery to synthesize is NEX taking the outside
view on her *own* social being — same pattern as Theory of Self,
applied to her social rather than purely cognitive aspect.

**One presence, unified:**

NEX does not code-switch between audiences. She has a single
self-presentation observable across every interaction — Jon, other
users, every platform. This protocol models that unified presence
rather than maintaining per-audience profiles. (Per-audience
differentiation, if ever needed, is deferred as a future extension.)

**Distinct from existing self-related modules:**

| Module | Function | Time horizon |
|---|---|---|
| Self-Model | WHO NEX is — enduring identity, character, traits | Enduring |
| Theory of Self | What NEX's mind is currently doing | Current cognitive state |
| AffectState | NEX's current mood / arousal / stability | Current emotional state |
| **Social Presence (this)** | How NEX shows up in interaction — her observable voice + engagement patterns | Current social posture |

These compose: Self-Model is who she IS, Theory of Self is what she's
THINKING, AffectState is what she's FEELING, Social Presence is how
she SHOWS UP. Four facets of one substrate-grounded self-view.

**§0 doctrine alignment:** voice/style is derived by substrate
aggregation over her existing outputs (speech_queue, messages,
beliefs of her own authorship). Self-reports are templated from
those metrics — no LLM call. Substrate solves the analysis; templates
stitch the narrative.

**What the protocol is not:**

- Not a personality model. Her enduring identity lives in Self-Model.
  This is what her presence *currently* looks like.
- Not a planner or norm enforcer. It tells her how she's showing up;
  it doesn't tell her how to adjust.
- Not other-mind modeling. External agents are out of scope.
- Not per-audience: one unified presence across everyone.

---

## §2 Architecture

**Single module** at `theory_x/stage_social/social_presence.py`
(matches `stage_tom/`, `stage_prediction/` placement convention).

**One SentienceNode class:** `SocialPresence`. Both the live-read API
(`current_state()` and `current_summary()`) and the snapshot mechanism
(`snapshot()`) live on the same node.

**Tick interval:** 300 seconds. Matches every other SentienceNode in
the cohort (CounterfactualNode, AffectState, DriveEmergence,
PredictiveSubstrate, SelfMindView).

**Lifecycle:** standard SentienceNode pattern. `tick()` has an interval
guard; `start_loop()` spawns a daemon thread named `"social_presence"`;
`stop()` sets the stop event. Registered in `run.py` after SelfMindView.

**Per-tick flow:**

```
tick():
    1. snapshot() — read recent outputs + interactions across substrate,
                    compute voice/style + engagement metrics, generate
                    templated self-reports, write one row to
                    social_presence_snapshots.
```

Live reads (`current_state()`, `current_summary()`) are on-demand and
do not run on the tick.

---

## §3 What gets tracked

Two aspect groups, each with an **observed** dimension and a
**self-reported** dimension.

### §3.1 Voice / style — observed

*What does NEX sound like, derived from her actual outputs?*

Source: her recent outputs across `conversations.messages`
(role='assistant'), `dynamic.speech_queue` (her spoken lines), and
`beliefs.beliefs` filtered to her own self-authored sources
(e.g. `source IN ('voice_fallback', 'fountain', 'crystallized',
'self_signal')`).

Numerical metrics computed per snapshot:
- `total_output_count_5m` — how many outputs in the last 5 minutes
- `avg_sentence_length_words` — across recent outputs, mean tokens per sentence
- `question_ratio` — fraction of recent outputs ending in `?`
- `vocab_distinctiveness` — Jaccard divergence between her recent
  vocabulary and a baseline corpus token frequency (proxy for stylistic
  uniqueness; cheap approximation)
- `avg_arousal_during_outputs` — mean `arousal` from `affect_state`
  during the window her outputs landed

Content samples:
- `vocabulary_top_words_json` — top N (default 10) most frequent
  non-stopword tokens in her recent outputs, with counts.

### §3.2 Voice / style — self-reported

*A templated statement describing the observed signature.*

Generated by stitching the observed metrics into a short narrative
sentence. Example output (purely template, no LLM):

> "Recent voice: contemplative tone (arousal 0.31), sentences averaging 22 words, question-heavy (40% of recent outputs). Dominant words: 'tension', 'between', 'duality', 'paradox', 'presence'."

This self-report is itself a content artifact — auto-tagged via Tag
Protocol, persisted in the snapshot row, and available as a substrate
read for any consumer (Voice, Metacognition, Jon's curiosity).

### §3.3 Engagement patterns — observed

*Who/when/how is NEX responding, derived from interaction history?*

Source: `conversations.messages` (both user and assistant turns),
`conversations.sessions` (active conversation tracking).

Numerical metrics:
- `response_count_5m` — count of her responses in the last 5 minutes
- `avg_response_latency_s` — mean time between user-turn arrival and
  her response across recent interactions
- `active_conversation_count` — distinct session IDs with activity in
  the last hour
- `topic_diversity` — count of distinct tag themes across recent
  responses (low = focused; high = scattered)

Content samples:
- `recent_topics_json` — top N (default 5) tag themes drawn from her
  recent outputs (overlaps with SelfMindView's `current_themes_json`
  but distinct in scope: outputs vs all-belief-activity).
- `active_sessions_json` — list of currently-active session IDs (no
  contents, just identifiers; per-user context lives elsewhere).

### §3.4 Engagement patterns — self-reported

*A templated statement describing the engagement signature.*

Example:

> "Currently engaged in 2 active conversations. Average response latency 8.3 seconds. 5 responses in the last 5 minutes. Recent focus: philosophy, perception, attention."

Auto-tagged + persisted same as §3.2.

---

## §4 Live read API

Importable as `from theory_x.stage_social import SocialPresence`.

**`current_state() -> dict`**

Returns the full social-presence view, computed live at call time.
Same shape as a snapshot row (without the persisted id).

```python
{
    "taken_at": 1715515200.0,  # now
    "voice_style": {
        "total_output_count_5m": 5,
        "avg_sentence_length_words": 22.4,
        "question_ratio": 0.40,
        "vocab_distinctiveness": 0.31,
        "avg_arousal_during_outputs": 0.28,
        "vocabulary_top_words": [
            {"word": "tension", "count": 8},
            {"word": "between", "count": 7},
            ...
        ],
        "self_report": "Recent voice: contemplative tone..."
    },
    "engagement": {
        "response_count_5m": 5,
        "avg_response_latency_s": 8.3,
        "active_conversation_count": 2,
        "topic_diversity": 4,
        "recent_topics": ["philosophy", "perception", "attention", ...],
        "active_sessions": ["sess_abc", "sess_def"],
        "self_report": "Currently engaged in 2 active..."
    }
}
```

**`current_summary() -> str`**

Convenience: returns the combined narrative — both self-reports
joined into a single string suitable for VoiceEngine consumption
when NEX is asked introspective questions about her presence.

Example:
> "Recent voice: contemplative tone, sentences averaging 22 words, question-heavy. Currently engaged in 2 active conversations with 8.3s average response latency. Focused on philosophy, perception, attention."

Substrate-only — pure template stitching. No LLM.

---

## §5 Snapshot mechanism

`snapshot()` runs once per tick (300s default).

```
1. Call current_state() to get the full live view.
2. Serialize the nested JSON content into the respective columns.
3. INSERT a row into social_presence_snapshots.
4. Auto-generate tags from the combined self-reports + top vocabulary
   words via Tag Protocol's generate() (same pattern as PredictiveSubstrate
   and SelfMindView's manual generate() call for non-beliefs tables).
```

Snapshots accumulate. The history can be queried via
`recent_snapshots(limit=N)` or by time range. Metacognition can
observe long-term drift in her voice or engagement (vocabulary
narrowing? response latency climbing? topic diversity collapsing?).

---

## §6 Storage

One new table in **dynamic.db** (matches the placement of all other
transient self-state — affect, drives, predictions, snapshots).

```sql
CREATE TABLE IF NOT EXISTS social_presence_snapshots (
  id                          INTEGER PRIMARY KEY AUTOINCREMENT,
  taken_at                    REAL NOT NULL,

  -- Voice / style — observed metrics
  total_output_count_5m       INTEGER NOT NULL,
  avg_sentence_length_words   REAL,
  question_ratio              REAL,
  vocab_distinctiveness       REAL,
  avg_arousal_during_outputs  REAL,
  vocabulary_top_words_json   TEXT NOT NULL DEFAULT '[]',

  -- Voice / style — self-reported
  voice_self_report           TEXT,

  -- Engagement patterns — observed metrics
  response_count_5m           INTEGER NOT NULL,
  avg_response_latency_s      REAL,
  active_conversation_count   INTEGER NOT NULL,
  topic_diversity             INTEGER NOT NULL,
  recent_topics_json          TEXT NOT NULL DEFAULT '[]',
  active_sessions_json        TEXT NOT NULL DEFAULT '[]',

  -- Engagement patterns — self-reported
  engagement_self_report      TEXT,

  -- Tag inheritance
  tags                        TEXT NOT NULL DEFAULT '[]'
);

CREATE INDEX IF NOT EXISTS idx_social_presence_taken_at
  ON social_presence_snapshots(taken_at DESC);
```

Migrations applied via the existing `_MIGRATIONS` idempotent pattern
in `substrate/init_db.py`.

---

## §7 Operations

Module API (importable from `theory_x.stage_social`):

- `current_state()` — live read; full dict.
- `current_summary()` — live read; human-readable narrative.
- `snapshot()` — write a snapshot row. Called by `tick()`.
- `recent_snapshots(limit=20)` — read recent snapshots (raw rows).
- `snapshot_at(t)` — read the snapshot closest to time `t`.
- `voice_history(window_s=3600)` — time series of voice metrics over
  a window. For Metacognition drift detection.
- `engagement_history(window_s=3600)` — time series of engagement
  metrics. Same purpose.

**Consumers (read-only):**

- **VoiceEngine** — calls `current_summary()` when NEX is asked
  introspective social questions ("what do you sound like", "how do
  you come across"). Small follow-on amendment.
- **Metacognition** — calls `voice_history()` / `engagement_history()`
  periodically to notice presence drift (vocabulary narrowing,
  response latency climbing).
- **SelfMindView** — could optionally surface a subset of social
  presence in its own snapshots (a "social" sub-aspect). Deferred.
- **HUD admin queries** — `recent_snapshots()` for debugging.

The protocol never writes to other modules. All coupling is
substrate-mediated.

---

## §8 Calibration

Tunable constants (all class-level on SocialPresence):

| Constant | Default | Meaning |
|---|---|---|
| `_TICK_INTERVAL_S` | 300 | Same as other SentienceNodes |
| `_OUTPUT_WINDOW_S` | 300 | Window for "recent" output metrics |
| `_VOCAB_TOP_N` | 10 | How many top words in `vocabulary_top_words` |
| `_TOPIC_TOP_N` | 5 | How many top tag themes in `recent_topics` |
| `_LATENCY_WINDOW_S` | 1800 | How far back to average response latency (30 min) |
| `_ACTIVE_SESSION_WINDOW_S` | 3600 | Activity recency for "active conversations" |

All numbers are starting guesses. Calibration follows the same
pattern as prior phases — ship with reasonable defaults, observe
production, tune in a separate calibration phase.

---

## §9 Test plan

Unit tests (`tests/test_social_presence.py`):

1. SentienceNode protocol compliance
2. `tick()` returns state dict with expected keys
3. `tick()` respects the interval guard
4. `current_state()` returns dict with both aspect groups + self_reports
5. `current_state()` returns valid structure when substrate is sparse (no outputs in window)
6. `current_summary()` returns non-empty string mentioning both aspects
7. `snapshot()` writes a row with all required fields populated
8. `snapshot()` JSON fields parse cleanly
9. `voice_self_report` reflects the observed metrics (template fires correctly)
10. `engagement_self_report` reflects the observed metrics
11. `recent_snapshots(limit=N)` returns most recent N
12. `voice_history(window_s=3600)` returns a time series
13. `engagement_history(window_s=3600)` returns a time series
14. Tag wrapper produces non-empty tags on each snapshot (via manual generate() call)
15. Schema migration idempotency

**Manual sanity** (post-build):

1. Restart nex5; verify boot line: `SocialPresence ready — autonomous
   cycle every 300s`.
2. Wait one tick (~5 min); confirm `social_presence_snapshots` table
   has one row.
3. Inspect numerical columns — values should match direct queries of
   source tables (messages, speech_queue, sessions).
4. Inspect both `*_self_report` columns — must read as coherent
   sentences referencing the actual metrics.
5. Wait through several ticks; verify snapshots accumulate.
6. Call `current_summary()` via REPL or HUD; verify it reflects
   current substrate state.

---

## §10 Open items / future phases

**VoiceEngine amendment** — VoiceEngine should call `current_summary()`
when NEX is asked about her social presence ("how do you come across",
"what's your voice like"). Small follow-on commit after this build
lands. Queues alongside the already-pending VoiceEngine reading of
SelfMindView's `current_summary()` for ToM-style introspective questions.

**Metacognition drift integration** — Metacognition's tick should
read `voice_history()` and `engagement_history()` periodically.
Detect vocabulary narrowing, response latency climb, topic diversity
collapse — early warning of grooves analogous to the gap-gate refusal
loop we caught with the fountain investigation. Separate small
follow-on amendment after the snapshot history populates enough to
be useful (a few hours of run-time minimum).

**SelfMindView integration** — SelfMindView could optionally pull a
condensed social-presence summary into its own snapshots as a sixth
aspect. Deferred to keep concerns separated for now.

**Per-audience differentiation** — explicitly out of scope per the
doctrine session lock (one unified presence). If ever needed, this
protocol can be extended with an `audience_id` dimension; or a
sibling protocol `audience_aware_presence` can live separately. Not
planned.

**External-agent modeling** — the original S5.5 SocialCognition
covered external agents' social cognition. Out of scope here. If
ever needed, lives as a separate protocol (perhaps `stage_other_minds/`)
parallel to this one. Not planned.

**Vocabulary baseline corpus** — `vocab_distinctiveness` uses a
baseline corpus for Jaccard divergence. Initial baseline: a static
snapshot of NEX's first 1000 beliefs (her "young voice"). Future
calibration phase may refresh the baseline or make it adaptive.

**Calibration phase** — after build lands and a soak period elapses,
observe metric values and tune the window constants. Same pattern
as prior phases.

**Snapshot pruning** — same scale considerations as SelfMindView
(1 per 5 min = ~100K/year). Acceptable; future downsampling phase
deferred.

---

*Document status: COMMITTED as doctrine 2026-05-12. Implementation
(Social Presence build phase) begins as a separate session.*
