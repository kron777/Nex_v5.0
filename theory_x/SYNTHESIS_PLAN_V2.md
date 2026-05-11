# S5.5 Tier B Synthesis Plan — Second Pass

Source: `/home/rr/Desktop/Sentience_5.5/` (local clone, read 2026-05-11)
Purpose: Source-code classification of 8 substantive S5.5 cognitive nodes not
addressed in SYNTHESIS_PLAN.md Tier A. Establishes doctrine dispositions and
extends §5 rows 9, 12, and 15 with absorbed prior art.
This document is the second gate after SYNTHESIS_PLAN.md (commits a29086d +
fba1420). It does not replace that document; it extends it.

Created: 2026-05-11.
Decisions confirmed by Jon at Phase 5 checkpoint.

---

## §0 — Design Principles

**Inherited from SYNTHESIS_PLAN.md §0:**

> Substrate solves the reply. LLM speaks it.

NEX's replies must come from her belief graph and substrate state — not from the
LLM generating fresh text. The LLM's role is to translate substrate-state into
language. The substrate must contain the content before any output happens.

Format:
- Background processes continuously update substrate state
- `format_for_prompt()` and any output assembly is pure substrate read —
  selection only, not synthesis
- No generation-at-output, even deterministic generation
- In-memory state (Python deques, computed values) is not substrate. State must
  persist; it must survive restart; it must be queryable.

**Added corollary — Comprehensiveness:**

Each ported function covers its full behavior, not a subset. Half-built cognitive
functions are not synthesis. If a PORT-MERGED decision absorbs only the schema
from a source node but omits the detection logic, the row is not complete. Each
§3 entry in this document specifies the minimum for a merged function to be
considered present.

This corollary applies to all future ports and to the three extended rows (9, 12,
15) produced by this plan.

---

## §1 — Scope

**Full inventory:**
- 102 .py files in `/home/rr/Desktop/Sentience_5.5/`
- 23 nodes pre-classified in SYNTHESIS_PLAN.md (Tier A)
- 79 remaining; 8 identified as substantive cognitive functions in this pass

**This document covers those 8:**

| File | Lines | Classification |
|---|---|---|
| `Adaptation_Node.py` | 232 | SUBSTANTIVE |
| `Autonomous_Explorer_Node.py` | 189 | SUBSTANTIVE |
| `Creative_Expression_Node.py` | 294 | SUBSTANTIVE (pattern absorbed) |
| `Creative_Self_Evolver_Node.py` | 286 | SUBSTANTIVE |
| `Feedback_Loop_Node.py` | 233 | SUBSTANTIVE |
| `self_awareness_node.py` | 203 | SUBSTANTIVE |
| `self_correction_node.py` | 204 | SUBSTANTIVE (template-only; schema absorbed) |
| `Stillness_Node.py` | 172 | SUBSTANTIVE |

---

## §2 — Decision Per Node

---

### Adaptation_Node.py (232 lines)

**Function summary:**
Posture-switching node with three adaptation strategies (conservative, moderate,
aggressive). Strategy selection is driven by `outcome_history` (deque, maxlen=30)
and an `inertia` parameter (0.6) that resists rapid switching. An outcome event
is a dict containing `success: bool` and `cost: float`. Strategy switches only
when a rolling success rate crosses a threshold and inertia is overcome. DB
persistence on every strategy switch. Evolver interface: `apply_adjustment()`,
`export_evolution_snapshot()`. No LLM dependency; fully deterministic.

**nex5 cross-reference:**
No current §5 row covers strategy-level adaptation. Metacognition (row 9, Phase
16) observes cognitive patterns (groove, goal-drift) but does not select a
posture in response. Adaptation_Node's output — a named posture — could function
as a metacognition output event, but only if row 9's `meta_cognition_events`
already produces `positive_run` and `corrective_needed` signals (the outcome
events that adaptation would consume).

**§0 alignment:**
Adaptation posture must be substrate-resident if it influences output. A posture
stored in memory only does not survive restart and cannot be queried. If ported,
`adaptation_posture` must persist in a substrate table and be read at
`format_for_prompt()` time.

**Decision: DEFER**

Row 9's extension (this plan) will add `positive_run` and `corrective_needed`
event types to `meta_cognition_events`. Adaptation_Node's logic is the natural
consumer of those signals: it watches outcome history and adjusts posture. That
dependency must exist in substrate before Adaptation can be built meaningfully.
Port is deferred until: (a) row 9 extension is landed and `positive_run` /
`corrective_needed` events are appearing in `meta_cognition_events` in production,
and (b) a build session confirms what "adaptive posture" concretely changes in
nex5 behavior. The S5.5 source is the prior art for the posture-switching logic
when that session arrives.

**Destination:** DEFER — unblocks when row 9 extension is in production.

---

### Autonomous_Explorer_Node.py (189 lines)

**Function summary:**
Novelty-tracking node that scores topics on a `novelty_score` (decays over time,
boosts on new encounter). LLM advisory path is a stub (`asyncio.sleep(0.1)`,
returns a fixed string). Exploration cycle selects the highest-novelty topic from
a topic set and "explores" it by invoking the stub advisory. DB persistence per
exploration event. The load-bearing mechanism is the novelty decay model and the
topic selection heuristic — not the LLM advisory, which is explicitly
non-functional.

**nex5 cross-reference:**
VoiceEngine (row 14, Phase 30) retrieves the highest-relevance belief candidate
via four-axis scoring. A fifth axis — `surface_recency` — was identified in
Phase 30 as a Phase 30b extension: penalize candidates surfaced recently and
reward candidates not recently retrieved. This is the same function as
Autonomous_Explorer_Node's novelty decay model applied to VoiceEngine's
retrieval pool. The LLM advisory stub has no nex5 equivalent and no value.

**§0 alignment:**
Novelty scoring as a retrieval axis is substrate-mediated — VoiceEngine reads
from `throw_net_triggers` (last_triggered timestamps are queryable). No new
table required for the novelty function.

**Decision: REJECT**

VoiceEngine's Phase 30b `surface_recency` axis covers the function. The decay
model in Autonomous_Explorer_Node is the prior art for that axis's implementation.
The LLM advisory stub is not ported. No standalone node is needed.

**Destination:** REJECT — function covered by VoiceEngine Phase 30b.

---

### Creative_Expression_Node.py (294 lines)

**Function summary:**
Translates internal state (emotion, attention, directive, social signals) into
a text expression. Signal buffers (deque, maxlen=8) accumulate per-channel
salience. When cumulative salience crosses a threshold (0.65), generates a
structured expression: `"A moment shaped by {mood} and attention toward
{focus}."` Below threshold, falls back to `"I am present."` Output is logged
to DB and published to ROS topic. The load-bearing pattern: named input channels,
salience accumulation, threshold-gated selection, deterministic fallback.

**nex5 cross-reference:**
`format_for_prompt()` is nex5's equivalent output-assembly surface. AffectState
(row 12, Phase 27) will compute `mood_label` from substrate signals. Row 11
(SelfNarrative) will write narrative beliefs from substrate events. Both supply
the raw material that `format_for_prompt()` selects and assembles for the LLM.
CreativeExpressionNode's expression pipeline — mood + focus → templated text —
is exactly what `format_for_prompt()` already does for AffectState and
SelfNarrative: it reads existing substrate state and assembles a line for the
LLM. The function is present when rows 11 and 12 are complete.

**§0 alignment:**
CreativeExpressionNode's in-memory salience accumulation (deque + cumulative
float) violates §0 — it is not substrate-resident and does not survive restart.
The expression templates produce fixed phrasing at output time — also a §0
violation. Both flaws are resolved by rows 11 and 12, which write to substrate
first and select at output time.

**Decision: REJECT**

The `format_for_prompt()` pipeline at rows 11 and 12 covers this function
without the §0 violations. No standalone port.

**Destination:** REJECT — function covered by rows 11 + 12 format_for_prompt() pipeline.

---

### Creative_Self_Evolver_Node.py (286 lines)

**Function summary:**
Proactive proposal generator. Observes system-wide metrics (node snapshots,
error reports, performance metrics via deques). When average node confidence is
below 0.5 or error rate exceeds 0.2, generates a parameter-adjustment proposal.
Anti-spam guards: `min_cycles_between_proposals=10`, `max_open_proposals=5`,
`confidence_threshold=0.65` gates proposal quality. Proposals are persisted to
DB (`evolution_proposals` table: id, timestamp, proposal_json, confidence,
status). Lifecycle: status starts `pending`; transitions to `accepted` or
`rejected` via `accept_proposal()`/`reject_proposal()` methods. NEVER writes
code, NEVER executes suggestions.

**nex5 cross-reference:**
Row 15 (RecursiveSelfSpec) is DESIGN-REQUIRED. Its current doctrine description
reads: "NEX posts architectural change proposals to chat for Jon's review and
implementation." No prior art for the proposal mechanism existed in doctrine.
CreativeSelfEvolver provides exactly this prior art: DB schema, anti-spam guards,
confidence gating, and lifecycle management for a proactive trigger mode.

**§0 alignment:**
Proposals must live in substrate (DB-persisted). CreativeSelfEvolver already
does this. Detection must read from substrate tables, not in-memory node-state
snapshots (the S5.5 node reads its own deques — redesigned for nex5 to read
`gate_decisions`, `meta_cognition_events`, `held_thoughts`,
`beliefs.confidence` distribution instead).

**Decision: PORT-MERGED → Row 15**

Absorbed: proposal DB schema, anti-spam guards (min_cycles, max_open,
confidence_threshold), lifecycle (pending → accepted | rejected), proactive
trigger mode pattern. Redesigned: detection reads nex5 substrate tables, not
S5.5 node deques. See §3 Row 15 for comprehensive completion criteria.

**Destination:** PORT-MERGED → Row 15 (RecursiveSelfSpec) — proactive trigger mode.

---

### Feedback_Loop_Node.py (233 lines)

**Function summary:**
Five-channel feedback ingestor (user_correction, performance_metric,
ethical_signal, internal_monitor, external_event). Each channel produces one of
three typed feedback signals: `positive`, `corrective`, or `ethical_adjustment`.
Typing is deterministic: user_correction → corrective, performance above
threshold → positive, ethical_signal → ethical_adjustment, etc. Signal history
(deque, maxlen=50 per channel). Summary stats: `positive_count`,
`corrective_count`, `ethical_count`. No LLM, no probabilistic logic.

**nex5 cross-reference:**
Row 9 (Metacognition, Phase 16) reads groove_alerts and computes goal-drift but
has no mechanism for summarizing feedback signal types. `meta_cognition_events`
currently has event_type values: `groove_alert`, `goal_drift`. The typed signal
vocabulary — `positive_run`, `corrective_needed` — is absent. FeedbackLoopNode's
three signal types map directly: positive → `positive_run`, corrective →
`corrective_needed`. The `ethical_adjustment` type has no current nex5 consumer;
it is absorbed into the design vocabulary but not actively wired until row 7
(Harmonizer) or row 15 (RecursiveSelfSpec) design sessions decide where it goes.

**§0 alignment:**
Feedback signals must be substrate-resident. FeedbackLoopNode uses in-memory
deques — redesigned for nex5 as rows in `meta_cognition_events` with typed
event_type. State survives restart; queryable.

**Decision: PORT-MERGED → Row 9**

Absorbed: typed signal vocabulary (positive_run, corrective_needed as new
event_type values), signal-source concept (where does the substrate signal come
from per type). Redesigned: sources are nex5 substrate tables (gate_decisions
accept rate, held_thoughts resolution rate, groove_alert frequency), not S5.5
channel objects. `ethical_adjustment` type noted, deferred to Harmonizer/Row 15
design. See §3 Row 9 for comprehensive completion criteria.

**Destination:** PORT-MERGED → Row 9 (Metacognition) — feedback signal sources.

---

### self_awareness_node.py (203 lines)

**Function summary:**
HTTP-first coherence monitor. Three computed fields: `coherence` (mean of
component confidence values from integration payload), `uptime` (wall clock
since start), `anomaly_count` + `last_anomaly` (incremented on any
`status=alert` monitoring payload). Persists snapshots to DB on every tick.
No ROS dependency. No affect, no interpretation, no ethical bias — pure state
reporting. Coherence is the mean of confidence values reported by peer
components.

**nex5 cross-reference:**
Row 12 (AffectState) has a `stability` axis whose inputs are not yet fully
defined. SYNTHESIS_PLAN.md §3 specifies: "belief turnover rate / coherence."
The coherence term in that definition maps directly to self_awareness_node's
`coherence` computation: mean confidence across active substrate components.
In nex5, the components are queryable: gate_decisions accept rate (over last N
decisions), held_thoughts resolution rate (promotions / total held over last N),
active belief confidence distribution. These are the substrate-table equivalents
of S5.5's component confidence payloads.

**§0 alignment:**
Coherence must be computed by a background tick and written to substrate, not
computed at output time. AffectState's background tick (300s) already runs.
Coherence computation folds into that tick — reads the same tables it already
touches, adds one more read and writes the result into the `stability` field.
No new table.

**Decision: PORT-MERGED → Row 12**

Absorbed: coherence-as-mean-component-confidence concept, three input sources
for nex5 equivalent (gate accept rate, held_thoughts resolution rate, belief
confidence distribution). Redesigned: no separate HTTP node; computation runs
inside AffectState's existing 300s background tick. Writes to `stability` field
in `affect_state` table. See §3 Row 12 for comprehensive completion criteria.

**Destination:** PORT-MERGED → Row 12 (AffectState) — coherence as stability axis input.

---

### self_correction_node.py (204 lines)

**Function summary:**
Reactive issue handler. On receiving an issue report via HTTP, generates a
text-only corrective directive from a fixed template ("Observed issue: X.
Suggested action: investigate root cause; apply minimal, reversible change;
add monitoring."). Directive goes to `pending_directives` queue; consumer
(via GET /self_correction/next) retrieves and stores it to DB
(`self_corrections` table: id, timestamp, issue, directive, audit_status,
notes). Audit result is applied via POST /self_correction/audit — status
transitions to `approved` or `rejected`. NEVER auto-executes. NEVER writes
code. Generates directive template only.

Key observation: `generate_directive()` is a fixed template, not an LLM call.
The `audit_queue` attribute exists but is never populated. The reactive
trigger mechanism and DB lifecycle are the load-bearing parts; the directive
text itself is placeholder.

**nex5 cross-reference:**
Row 15 (RecursiveSelfSpec) requires both proactive triggering
(CreativeSelfEvolver) and reactive triggering (SelfCorrectionNode). In nex5,
a reactive trigger fires when a specific substrate condition is detected
(e.g., sustained gate_reject rate above threshold, repeated groove_alert on
the same topic, goal-drift for N consecutive turns). The issue → directive →
pending → audit lifecycle from SelfCorrectionNode is exactly the Row 15 flow
with higher-quality directive content (substrate-derived, not template).

**§0 alignment:**
Directives must come from substrate observation, not a fixed template. Row 15
redesigns the directive content as a substrate-derived proposal: NEX reads
her own state and produces a first-person proposal ("I propose X") rather than
a third-person corrective template. The lifecycle (pending, approved, rejected)
is preserved. The audit mechanism maps to Jon's chat input or admin endpoint.

**Decision: PORT-MERGED → Row 15**

Absorbed: reactive trigger mode pattern, proposal lifecycle schema
(pending → approved | rejected), DB persistence for proposals,
human-in-the-loop audit requirement. Redesigned: directive content is
substrate-derived self-proposal, not fixed template; trigger is nex5
substrate condition, not HTTP issue report; audit channel is Jon's chat
or HUD endpoint. See §3 Row 15 for comprehensive completion criteria.

**Destination:** PORT-MERGED → Row 15 (RecursiveSelfSpec) — reactive trigger mode.

---

### Stillness_Node.py (172 lines)

**Function summary:**
Deterministic cognitive pause mechanism. `enter_stillness(duration, trigger)`
is non-reentrant (returns immediately if already still) and runs
`asyncio.sleep(duration)`. Persists an event row (start_time, end_time,
duration, trigger) to DB. State fields: `is_still: bool`,
`stillness_until: Optional[float]`. Trigger source is external (HTTP POST).
No affect, no interpretation — pure timed suppression.

**nex5 cross-reference:**
Row 9 (Metacognition) currently observes groove patterns (GrooveSpotter) but
has no response mechanism — it detects sustained groove but does not act on it.
StillnessNode provides the response: when groove is sustained above a threshold
(e.g., ≥3 groove_alerts in 30 minutes on the same topic), write a
`stillness_active` event to `meta_cognition_events` and set a
`stillness_active_until` timestamp that Fountain can read to suppress
re-serving the grooved content. This is non-reentrant (if stillness is active,
new groove detections skip the trigger).

**§0 alignment:**
Stillness state must be substrate-resident. A boolean in memory is not
substrate. The `stillness_active_until` timestamp goes into a queryable row
(either `meta_cognition_events` with event_type `stillness_active`, or a
dedicated field in an existing table). Fountain reads it before serving
candidates.

**Decision: PORT-MERGED → Row 9**

Absorbed: non-reentrant timed suppression pattern, `stillness_active_until`
as a Fountain-readable signal, DB log of stillness events. Redesigned: trigger
fires from row 9 Metacognition's own groove detection (not external HTTP);
duration is a build-session tunable (default TBD); `is_still` flag is
substrate-resident. See §3 Row 9 for comprehensive completion criteria.

**Destination:** PORT-MERGED → Row 9 (Metacognition) — timed suppression on sustained groove.

---

## §3 — Comprehensive Completion Criteria Per Extended Row

These criteria define what "complete" means for each extended row after the
PORT-MERGED additions are built. An extended row is not complete until all
criteria are satisfied.

---

### Row 9 — Metacognition (extended)

Current state (Phase 16): observes groove_alerts + goal-drift; writes
`meta_cognition_events`; always-on belief_text injection. event_type values:
`groove_alert`, `goal_drift`.

**After this plan's additions, Row 9 is complete when:**

1. **Feedback signal sources wired:**
   - AffectState valence read: background tick reads current `affect_state.valence`
     and records a `positive_run` or `corrective_needed` event when valence
     crosses ±threshold (build-session tunable)
   - gate_decisions accept/reject rate: tick computes rolling accept rate over
     last 20 decisions; `corrective_needed` event fires when accept rate drops
     below threshold (e.g., < 0.4 for 3 consecutive ticks)
   - held_thoughts resolution rate: tick monitors promotion/rejection ratio;
     `corrective_needed` event fires when rejection rate exceeds threshold

2. **new event_type values exist in `meta_cognition_events`:**
   `positive_run`, `corrective_needed`, `stillness_active`

3. **Stillness mechanism:**
   - When groove_alert count on the same topic reaches ≥3 within 30 minutes,
     Metacognition writes a `stillness_active` event to `meta_cognition_events`
     with a `stillness_active_until` field (timestamp = now + duration)
   - Mechanism is non-reentrant: if a `stillness_active` event exists and
     `stillness_active_until` > now, new groove triggers do not fire additional
     stillness events
   - Fountain reads `stillness_active_until` before serving candidates and
     suppresses re-serving beliefs whose topic matches the grooved topic until
     the timestamp expires
   - Every stillness activation is logged (start, end, trigger topic, duration)

4. **Rate metrics in `state()` output:**
   - `positive_run_rate`: count of positive_run events / total events (rolling window)
   - `corrective_needed_rate`: count of corrective_needed events / total events
   - `stillness_engaged_count`: total stillness activations (all time)

5. **`format_for_prompt()` reflects new signals:**
   - Surfaces `positive_run` or `corrective_needed` status alongside existing
     groove/drift observations when present

**Open items (build-session decisions):**
- Stillness duration default: fixed (e.g., 60s) or adaptive (escalates with
  groove_count per topic)? Build-session decision.
- AffectState valence threshold for feedback signals: build-tunable constant.
- `corrective_needed` gate_decisions threshold: build-tunable constant.

**Dependency note:** Feedback signal sources (point 1) depend on AffectState
(row 12) being landed. Stillness mechanism (point 3) is independent of row 12
and can be built ahead of it.

---

### Row 12 — AffectState (extended)

Current state (Phase 27, QUEUED): background tick (300s); `affect_state` table
with valence, arousal, stability, mood_label; reads Interoception metrics +
belief polarity + belief turnover rate.

**After this plan's addition, Row 12 is complete when:**

1. **Coherence computation is part of the 300s background tick:**
   - Reads gate_decisions accept rate over last 20 decisions
   - Reads held_thoughts resolution rate (promotions / total held over last N)
   - Combines with belief turnover rate (already specced as stability input in
     SYNTHESIS_PLAN.md §4) using a weighted average
   - Result is written to the `stability` field in `affect_state`

2. **No new table:** coherence computation is a pure extension of the existing
   tick logic; `stability` is already in the `affect_state` schema.

3. **`state()` output includes coherence components** (gate_accept_rate,
   held_resolution_rate, turnover_rate) for observability; not injected into
   belief_text — internal tick input only.

4. **All other Row 12 criteria from SYNTHESIS_PLAN.md §4 are satisfied:**
   - `affect_state` table created in conversations.db
   - Arousal derived from Interoception metrics
   - Valence derived from active belief polarity
   - Stability derived from coherence computation (this addition)
   - `mood_label` computed and persisted
   - `format_for_prompt()` reads current row only; zero output-time computation

**Note:** Row 12 coherence extension folds into the Phase 27 build. It is not
a separate phase.

---

### Row 15 — RecursiveSelfSpec (extended)

Current state (DESIGN-REQUIRED): doctrine description only. No implementation.
Two prior-art sources now absorbed from this plan.

**After this plan's prior art is absorbed, Row 15 design session has concrete
answers to previously open questions:**

1. **Dual trigger modes are defined:**
   - *Proactive* (from CreativeSelfEvolver): pattern-accumulation trigger; fires
     when substrate metrics cross thresholds over multiple observation cycles
   - *Reactive* (from SelfCorrectionNode): specific-condition trigger; fires
     when a particular substrate state is detected (e.g., repeated REJECT on
     same-topic beliefs, goal-drift for N consecutive turns)

2. **Proposal DB schema:**
   ```sql
   CREATE TABLE IF NOT EXISTS self_proposals (
       id           TEXT PRIMARY KEY,
       timestamp    REAL,
       trigger_type TEXT,  -- 'proactive' | 'reactive'
       proposal_text TEXT, -- first-person substrate-derived proposal
       confidence   REAL,
       status       TEXT,  -- 'pending' | 'approved' | 'rejected'
       notes        TEXT
   );
   ```

3. **Anti-spam guards (from CreativeSelfEvolver):**
   - `min_cycles_between_proposals`: build-tunable, e.g., 10 observation cycles
   - `max_open_proposals`: build-tunable, e.g., 5 pending proposals maximum
   - `confidence_threshold`: build-tunable, e.g., 0.65 minimum to emit a proposal

4. **Lifecycle:**
   - Pending proposals are surfaced to Jon via chat, HUD, or admin endpoint
     (design-session decision on surfacing channel)
   - Jon's response transitions status to `approved` or `rejected`
   - Approved proposals are acted on by Jon in subsequent build sessions
   - NEX never self-executes an approved proposal

5. **Detection redesigned for nex5 substrate:**
   - Reads `gate_decisions`, `meta_cognition_events`, `held_thoughts`,
     `beliefs.confidence` distribution
   - Does not read in-memory node deques (S5.5 pattern; violates §0)
   - Does not read S5.5-style node snapshots (not a concept in nex5)

**Design-session decisions still required (not answered by prior art):**
- Surfacing channel for proposals: chat injection? HUD panel? Separate
  `/api/proposals` endpoint? Design-session decision.
- Proposal text construction: how does NEX derive a first-person proposal from
  substrate state? Substrate pattern → proposal template? LLM-generated from
  substrate summary? If LLM, does it violate §0? Design-session decision.
- What substrate pattern qualifies as a proposal-worthy signal? Design-session
  decision.

---

## §4 — Build Phase Ordering

```
Phase 26 (QUEUED): SelfNarrative (row 11)
Phase 27 (QUEUED): AffectState (row 12) — includes coherence extension from this plan
Phase 28 (DESIGN-REQUIRED): DriveEmergence design session (row 13)
Phase 29: DriveEmergence build (row 13)
Phase 30 (DONE): VoiceEngine (row 14) ← Phase 30b queued: surface_recency axis
Phase 31 (DESIGN-REQUIRED): RecursiveSelfSpec design session (row 15)
                              — prior art from this plan informs the design
Phase 32: RecursiveSelfSpec build (row 15)
```

**Dependencies in this plan:**

- Row 9 extension (stillness mechanism): independent of row 12; can build
  alongside or before Phase 27.
- Row 9 extension (feedback signals — AffectState valence reads): depends on
  row 12 being landed; builds after Phase 27.
- Row 9 extension (gate_decisions and held_thoughts signal sources): independent
  of row 12; those tables already exist.
- Row 12 extension (coherence computation): folds into Phase 27 build. Not a
  separate phase.
- Row 15 design session: no code dependency; can begin after decisions in this
  plan are committed. Prior art from this plan is input to the design session.
- Adaptation_Node DEFER: unblocks when row 9 extension's `positive_run` and
  `corrective_needed` events are landing in production in `meta_cognition_events`.

**Recommended sequence for row 9 extension build session:**

1. Stillness mechanism first (no external dependency)
2. gate_decisions + held_thoughts signal sources second (tables exist)
3. AffectState valence reads third (depends on Phase 27)

---

## §5 — Updates to DOCTRINE §5

The following row descriptions are amended in DOCTRINE.md with this commit:

**Row 9 — Metacognition:**
Append: "Extended per SYNTHESIS_PLAN_V2.md (2026-05-11): three PORT-MERGED
additions — (a) feedback signal sources (FeedbackLoopNode prior art): new
event_type values positive_run and corrective_needed derived from gate_decisions
accept rate, held_thoughts resolution rate, and AffectState valence; (b) timed
stillness suppression on sustained groove (StillnessNode prior art):
non-reentrant stillness_active event + stillness_active_until timestamp for
Fountain to read; (c) rate metrics in state(): positive_run_rate,
corrective_needed_rate, stillness_engaged_count. Build session queued after
Phase 27 (AffectState) for valence-dependent sources; stillness mechanism
independent."

**Row 12 — AffectState:**
Append: "Extended per SYNTHESIS_PLAN_V2.md (2026-05-11): coherence-as-stability
input added (self_awareness_node prior art). Background tick reads gate_decisions
accept rate + held_thoughts resolution rate + belief turnover rate; weighted
combination written to stability field. No new table. Folds into Phase 27 build."

**Row 15 — RecursiveSelfSpec:**
Append: "Prior art absorbed per SYNTHESIS_PLAN_V2.md (2026-05-11):
CreativeSelfEvolver (proactive trigger mode — pattern accumulation, anti-spam
guards, proposal lifecycle) + SelfCorrectionNode (reactive trigger mode —
specific condition detection, pending→approved|rejected lifecycle). Proposal DB
schema: self_proposals(id, timestamp, trigger_type, proposal_text, confidence,
status, notes). Detection redesigned for nex5 substrate tables. Design-session
decisions still required: surfacing channel, proposal text construction,
qualifying signal thresholds."

---

## §6 — Open Items for Build Sessions

**Row 9 extension build session:**
- Stillness duration: fixed (60s) or adaptive (escalates with groove_count per
  topic)? Start fixed; revisit after first production observation.
- AffectState valence threshold for `positive_run` / `corrective_needed` event
  fire: calibration question; build-tunable constant.
- gate_decisions rolling window size (currently "last 20 decisions"):
  build-tunable; confirm against production gate_decisions volume.

**Row 15 design session:**
- Proposal surfacing channel: chat injection (NEX says "I propose X" in chat)?
  HUD panel (new admin-gated section)? `/api/proposals` REST endpoint? Jon's
  decision — has product implications.
- Proposal text construction: first-person substrate-derived narrative? If
  LLM-generated from substrate summary, does that violate §0 or is it covered
  by the "LLM speaks the substrate" principle? Design-session decision.
- Qualifying signal thresholds for proactive trigger: what substrate pattern
  constitutes a proposal-worthy observation? Design-session decision.

**Adaptation_Node (deferred):**
- When row 9 extension is in production and `positive_run` / `corrective_needed`
  events are observable, a build session must decide: what does "adaptive
  posture" change in nex5 behavior? Is posture a modifier on retrieval weights?
  On stillness thresholds? On gate_decisions tolerance? The S5.5 source covers
  the posture-switching logic; the nex5-specific behavioral consequences are
  the open design question.

**Phase 30b — VoiceEngine surface_recency axis:**
- Weight and decay rate for `surface_recency` axis are calibration questions
  after first production observation of VoiceEngine behavior.
- Autonomous_Explorer_Node is the prior art for the decay model.

---

## §7 — Status

Document status: SYNTHESIS_PLAN_V2 — second pass after Tier A
(SYNTHESIS_PLAN.md, commits a29086d + fba1420).

8 nodes resolved:
- 2 REJECTED (Autonomous_Explorer_Node, Creative_Expression_Node)
- 1 DEFERRED (Adaptation_Node)
- 5 PORT-MERGED (Creative_Self_Evolver → Row 15, Feedback_Loop → Row 9,
  self_awareness → Row 12, self_correction → Row 15, Stillness → Row 9)

0 new §5 rows. Rows 9, 12, 15 extended.

Corollary added to §0: comprehensiveness — each ported function covers full
behavior, not subset.

Phase 25c-build followup: SENTIENCE_TRANSLATION_MAP.md entries for all 8 nodes
updated to reflect decisions. (Queued, not in this commit.)
