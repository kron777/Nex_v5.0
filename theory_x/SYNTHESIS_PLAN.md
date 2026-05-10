# S5.5 Tier A Synthesis Plan — Phase 25c

Source: `/tmp/s55_source/` (github.com/kron777/Sentience_5.5, depth-1 clone 2026-05-10)
Purpose: Source-code classification of Tier A UNMAPPED nodes + doctrine Q2–Q5 answers.
This document gates Phase 26+ port ordering in DOCTRINE §5.

Created: Phase 25c-spec (2026-05-10). Implementation sessions begin after Jon's greenlight.

---

## §1 File Classification

All ten Tier A UNMAPPED nodes read from source. Each classified SUBSTANTIVE / PARTIAL / STUB.

### SUBSTANTIVE — real code worth absorbing

**`Emotion_Mood_Node.py`** (297 lines)

`EmotionStateModel` is the load-bearing class:

```python
class EmotionStateModel:
    def __init__(self):
        self.valence = 0.0   # [-1, 1]
        self.arousal = 0.1   # [0, 1]
        self.stability = 0.9 # [0, 1]

    def integrate(self, dv: float, da: float): ...  # bounded clamp
    def decay(self, rate=0.02): ...                  # settling
    def mood_label(self) -> str: ...                 # positive / neutral / negative
```

`EmotionMoodNode` wraps it with three input handlers:
- `observe_social(mood, confidence)` → dv = ±0.1 × confidence, da = 0.05 × confidence
- `observe_internal(sentiment)` → dv = 0.1 × sentiment, da = |sentiment| × 0.05
- `observe_sensory(salience)` → da = salience × 0.1

The continuous bounded affect model is real cognitive engineering. Input delta math
is physically sensible (arousal rises on any stimulation; valence responds to valenced
inputs). Decay handles settling.

Minor bug: `_tick()` calls `random.random()` but `random` is not imported. Fix is
one line. Async LLM advisory (10% chance per tick) is optional and advisory-only
per the file's design — not load-bearing.

Verdict: **SUBSTANTIVE**. Absorb `EmotionStateModel` directly.

---

**`Surprise_Detector_Node.py`** (239 lines)

Complete prediction-error detection node. Core:

```python
def compute_surprise(self, predicted: float, actual: float) -> float:
    return abs(predicted - actual)

def is_surprise(self, score: float) -> bool:
    return score >= self.threshold
```

`process_pair()` → persist + publish. DB schema for surprise_log. Summary stats
(`events`, `surprises`, `rate`). `_loop()` in demo mode uses random data (would be
replaced). Calibrated threshold (default 0.7). Full shutdown lifecycle.

Verdict: **SUBSTANTIVE**. Complete and functional. Demo-mode loop is the only
non-production code; replace with belief-field prediction input.

---

**`TheoryOfMindNode.py`** (262 lines)

Real BDI model per external agent:

```python
def upsert_agent(self, agent_id, beliefs=None, desires=None, intentions=None):
    model = self.agents.setdefault(agent_id, {"beliefs":[], "desires":[], "intentions":[]})
    # set-union merge per modality
    # compassion_bias injection of "empathy" if bias > 0.15

def predict(self, agent_id) -> Dict:
    # returns first intention, or "seek {desire[0]}", or "observe"
```

DB persistence on each upsert. History deque (100 entries). 4-second periodic publish.
`ethical_compassion_bias` injects "empathy" as a standing belief for any tracked agent
— a concrete design choice, not placeholder code.

`predict()` is primitive (heuristic, not learned) but that is correct for this
function — ToM inference is done from belief/desire/intention contents, not from
statistical models in S5.5's architecture.

Verdict: **SUBSTANTIVE**. Absorb agent model structure + BDI merge pattern.

---

**`Internal_Narrative_Node.py`** (340 lines)

Most complete Tier A node. Multi-channel signal buffering:

```python
self.buffers = {
    "attention": deque(maxlen=5),  "emotion": deque(maxlen=5),
    "motivation": deque(maxlen=5), "world_model": deque(maxlen=5),
    "performance": deque(maxlen=5),"memory": deque(maxlen=5),
    "prediction": deque(maxlen=5), "directives": deque(maxlen=3),
}
```

Per-signal salience weights (0.2 to 1.0). Accumulated salience gates LLM narrative
generation (default threshold 0.5). Deterministic fallback: `"Monitoring internal
state."` with theme `"idle_reflection"`. After generation, salience resets to 0.

HTTP API wires `/attention_state`, `/emotion_state`, etc. → aiohttp server (port 8089).

The architecture is the key contribution: named signal channels with weights, salience
accumulation, LLM-gated generation, deterministic fallback. The HTTP server delivery
is S5.5-specific; nex5 replaces it with belief_text injection per §3.

Verdict: **SUBSTANTIVE**. Architecture directly portable; HTTP delivery layer replaced.

---

**`Drive_System_Node.py`** (263 lines)

Four-drive model with real dynamics:

```python
self.drives: Dict[str, float] = {
    "curiosity": 0.4, "energy": 0.5, "social_contact": 0.3, "safety": 0.6,
}
```

`_decay_drives()`: all drives decay by `decay_rate` (0.02) per tick.
`_apply_pending_updates()`: cross-drive coupling:
- memory novelty → curiosity (inverse: low novelty → curiosity pressure)
- battery low → energy drive (proxy: computational load)
- surprise high → safety + social_contact amplification

`_evaluate_state()` tracks dominant drive and threshold crossings.
`export_learning_state()` provides evolver interface.

Drive math is physically sensible: low novelty creates curiosity pressure (you want more
when you're not getting surprises); surprise amplifies safety need. Decay prevents runaway.

Verdict: **SUBSTANTIVE**. Absorb drive dict + decay + coupling logic. Battery proxy
maps to nex5 computational load (inference latency, belief count).

---

**`Experience_Motivation_Node.py`** (204 lines)

Weighted multi-signal synthesis to drive level:

```python
def _synthesize_drive(self):
    emotion_signal  = sum(i for _, i in self.emotion_history)  * self.params["emotion_weight"]
    performance_signal = sum(self.performance_history)          * self.params["performance_weight"]
    world_signal    = sum(self.world_history)                   * self.params["world_change_weight"]
    directive_signal = sum(u for _, u in self.directive_history)* self.params["directive_weight"]

    raw_drive = (emotion_signal + performance_signal + world_signal + directive_signal)
               * self.params["drive_gain"]
    self.drive_level = min(1.0, max(0.0, self.drive_level * (1 - decay) + raw_drive))
```

Full evolver mutation interface:
```python
def apply_mutation(self, mutation: Dict[str, float]): ...  # mutates params
def snapshot_state(self) -> Dict: ...                       # for evolver snapshot
def export_metrics(self) -> Dict[str, float]: ...           # for evolver fitness
```

This is the most complete motivation node. The synthesis formula is simple but the
architecture — named parameters mutated by evolver, weighted signal inputs, goal-switch
at threshold — is designed for production use.

Verdict: **SUBSTANTIVE**. Absorb weighted synthesis + evolver mutation interface.

---

**`Value_Drift_Monitor_Node.py`** (Tier B, 208 lines)

Audit loop over 8 core values:

```python
def _audit(self) -> Dict[str, Any]:
    conflicts = [e for e in self.ethical_events if e["conflict"]]
    if conflicts:
        drift["human_safety"] = 0.15 * len(conflicts)
    ...
    alignment_score = max(0.0, 1.0 - total_drift)
```

Three input streams: ethical_decisions (conflict flag), performance_events
(suboptimal flag), internal_narratives (theme text). Produces alignment_score +
drift dict + warning flag. Persists audit rows.

The drift mechanism is simple (count-based) but the architecture — three input
streams, per-value drift attribution, alignment_score summary — is usable.
No §7 tension: output is read-only reporting, never enforcement.

Verdict: **SUBSTANTIVE** (Tier B). Relevant to belief-alignment monitoring.

---

### PARTIAL — real skeleton, thin logic

**`Temporal_Narritive_Node.py`** (196 lines)

Ingest/generate/persist loop is real:

```python
def generate_narrative(self):
    theme = self._infer_theme()   # keyword match on event strings
    mood  = self._summarize_emotion()  # dominant mood by frequency
    story = {"narrative_theme": theme, "recent_memory": ..., ...}
    self._persist(story)
```

Three clean ingestion methods: `ingest_memory(event)`, `ingest_emotion(mood, intensity)`,
`ingest_goal(goal, status)`. 6-second generation loop.

Theme inference is brittle string matching ("failure" → resilience). Would require
replacement with belief-field content-based inference in nex5. Structure is right;
content logic is a placeholder.

Verdict: **PARTIAL**. Ingest/generate/persist pattern is absorb-worthy.
`_infer_theme()` and `_summarize_emotion()` need replacement.

---

**`Motivation_Node.py`** (199 lines)

Three-branch update logic:

```python
def update_from_integration(self, data):
    if status == "alert":
        self.motivation_level -= 0.15; self.goal = "recovery"
    elif confidence >= 0.75:
        self.motivation_level += 0.1;  self.goal = "optimization"
    elif confidence <= 0.4:
        self.motivation_level -= 0.1;  self.goal = "reflection"
    else:
        self.motivation_level = 0.5;   self.goal = "maintenance"
```

No accumulation, no history. HTTP API (/motivation/update, /motivation/state,
/motivation/stream) is well-constructed aiohttp scaffolding.

Motivation update logic is too thin to absorb directly. The named goal states
(recovery / optimization / reflection / maintenance) are useful vocabulary that
could inform DriveSystem's dominant-drive labeling in nex5.

Verdict: **PARTIAL**. Goal vocabulary useful; update logic not absorb-worthy.
Superseded by DriveSystemNode + ExperienceMotivationNode in the port recommendation.

---

**`Social_Cognition_Node.py`** (247 lines)

Core logic is LLM delegation:

```python
async def _handle_prompt_async(self, prompt: str) -> str:
    compassionate_prompt = (
        f"{prompt}\n\nRespond with empathy, social awareness, and compassion. "
        f"Compassion bias level: {self.ethical_compassion_bias}."
    )
    response = await self.llm.query(compassionate_prompt)
    self._log_interaction(prompt, response)
    return response
```

There is no deterministic social reasoning model. The "social cognition" is prompt
engineering. The interaction logging (DB persist with compassion_bias field) is real.
AsyncLLMClient class is clean aiohttp scaffolding.

Verdict: **PARTIAL**. No absorb-worthy social reasoning logic. Logging pattern
and AsyncLLMClient are reusable utilities.

---

**`Context_Awareness_Node.py`** (Tier B, 247 lines)

Rule-based context synthesis with evolver metrics. Real update queue, confidence
scoring, learning_state. Thin logic (environment/priority string assignment).
More scaffolding than mechanism.

Verdict: **PARTIAL** (Tier B). Evolver metrics pattern is useful; content logic
is thin.

---

### STUB — discard

**`Prediction_Node.py`** (42 lines)

```python
def predict(self, user_input: str) -> dict:
    prediction = {
        "expects_question": "?" in user_input,
        "topic": "existential" if any(k in user_input.lower() for k in [...]) else "general",
        "timestamp": time.time()
    }
```

42 lines total. Prediction is "?" detection and keyword topic matching. `evaluate()`
checks if that prediction matched. No probabilistic model, no learning, no substrate.

Verdict: **STUB**. Not absorb-worthy. Prediction mechanism in nex5 port must be
designed from scratch (belief-field state at query time predicts response trajectory).

---

**`Consequence_Memory_Node.py`** (33 lines)

```python
class ConsequenceMemoryNode:
    def record(self, domain: str, success: bool): ...     # increment counter
    def adjustments(self): ...                              # return "reduce/increase_confidence"
    def snapshot(self): ...                                 # dict of counters
```

Pure counters. No persistence, no DB, no decay, no integration with beliefs.
Verdict: **STUB**. Not absorb-worthy.

---

## §2 Doctrine Q2–Q5 Answers

Source-code evidence grounds each recommendation. Jon's approval required before
encoding in DOCTRINE §5.

---

**Q2 — Motivation system: one port or three?**

Evidence:
- `DriveSystemNode`: complete four-drive model with decay + cross-drive coupling.
  The cleanest architecture of the three.
- `ExperienceMotivationNode`: complete weighted synthesis + full evolver mutation
  interface. Extends DriveSystemNode with weighted signal input.
- `MotivationNode`: thin. Three-branch update logic is not absorb-worthy. Its
  goal vocabulary (recovery/optimization/reflection/maintenance) is useful labeling.

Recommendation: **Single §5 node** (`DriveSystem`) that absorbs:
- `DriveSystemNode`'s drive dict + `_decay_drives()` + `_apply_pending_updates()`
- `ExperienceMotivationNode`'s weighted synthesis formula + `apply_mutation()` interface

`MotivationNode` is not ported. Its goal vocabulary informs the dominant-drive
labeling in the nex5 port (curiosity-dominant → "exploration", safety-dominant →
"grounding", etc.).

Rationale: Goals (§5 row 8) are explicit named targets. Drives are subpersonal
pressure states that shift goal salience without naming goals. The distinction is
real and GoalManager does not cover it. A dedicated DriveSystem node is warranted.

---

**Q3 — Affect: standalone or extension of Interoception?**

Evidence:
- nex5 Interoception reads system metrics (CPU%, memory_mb, belief counts) as
  body-state proxies. Output: raw numeric system state.
- `EmotionMoodNode`'s `EmotionStateModel` synthesizes affect from social,
  internal, and sensory input events. Output: valence/arousal/stability with labels.

These are genuinely distinct layers:
1. Interoception → raw body-state signals (computational load, belief density)
2. Affect → synthesized emotional state from body-state + belief-field events

Recommendation: **Standalone §5 node** (`AffectState`). It reads from interoception
output (system state as proxy for bodily arousal) and from belief-field events
(high-tier beliefs tagged emotional by the voice layer as social/internal input).
Outputs valence + arousal + mood_label to belief_text per §3.

Rationale: Keeping the layers separate preserves the architecture. Affect synthesis
requires logic that doesn't belong in Interoception's body-state reader. A standalone
node is two screens of code; there's no complexity benefit from merging.

---

**Q4 — Narrative identity: in or out of scope?**

Evidence:
- `InternalNarrativeNode`: multi-channel signal buffer + salience accumulation +
  LLM-gated generation + deterministic fallback. The architecture is clearly absorb-worthy.
- `TemporalNarrativeNode`: ingest/generate/persist loop is clean. Theme inference
  is brittle keyword matching — needs replacement with belief-field content logic.
- §7 criterion "named, understood psychological function" is unambiguously met:
  narrative self-construction (McAdams, Bruner) is one of the most studied functions
  in personality psychology.

Port surface: `SelfNarrativeNode` absorbs both. Signal buffers from InternalNarrativeNode;
ingest pattern from TemporalNarrativeNode. Delivery is belief_text injection per §3
(replacing the HTTP server). LLM narrative generation is replaced with deterministic
belief-field text synthesis (consistent with §3: graph reasons, LLM speaks).

Recommendation: **In scope** as §5 row 11 (`SelfNarrative`). Two S5.5 nodes → one
nex5 port (SUBSUMED pattern, matches Metacognition precedent).

---

**Q5 — Theory of Mind: scope and data**

Evidence:
- `TheoryOfMindNode` has a real BDI structure. upsert_agent() + predict() are
  minimal but correct for heuristic ToM.
- In nex5 context, "external agents" = Jon (primary) + any named persons NEX has
  beliefs about. Single-agent scope is realistic and immediately useful.
- Data source: user utterances parsed for beliefs (stated facts), desires (questions,
  expressed wants), intentions (plans, stated goals). Each `api_chat()` call is a
  data point for Jon's model.

Recommendation: **In scope** at single-agent scale as §5 row 12 (`TheoryOfMind`).
Agent = Jon. Beliefs sourced from user utterance content. Desires inferred from
query intent (already classified by ExecutiveControl). Intentions from goal
declarations in conversation.

A multi-agent generalization is not blocked — the BDI dict is keyed by agent_id —
but single-agent is sufficient for Phase 26 implementation. Generalization deferred
to post-port observation.

---

## §3 Proposed §5 Row Additions

Pending Jon's approval of Q2–Q5 recommendations above.

| Proposed Row | Node Name | S5.5 Source | Pattern |
|---|---|---|---|
| Row 11 | `SelfNarrative` | `InternalNarrativeNode` + `TemporalNarrativeNode` | SUBSUMED (2 → 1) |
| Row 12 | `TheoryOfMind` | `TheoryOfMindNode` | Direct port |
| Row 13 | `DriveSystem` | `DriveSystemNode` + `ExperienceMotivationNode` | SUBSUMED (2 → 1) |
| Row 14 | `AffectState` | `EmotionMoodNode` | Direct port |

**Ordering rationale:**
- Row 11 (SelfNarrative) first: no hard dependencies; feeds belief_text immediately;
  InternalNarrativeNode's buffer fills from existing nodes (Metacognition events,
  GoalManager goals, Interoception state).
- Row 12 (TheoryOfMind) second: single external agent scope; data is available now
  (every user turn); feeds belief_text with Jon-model prediction.
- Row 13 (DriveSystem) third: depends on GoalManager (row 8) being stable — it is.
  Drive pressures amplify goal priority; they don't create goals.
- Row 14 (AffectState) fourth: depends on Interoception (row 6) output being stable
  — it is. Affect synthesis reads body-state proxies as arousal input.

**Not proposed (findings):**
- `SurpriseDetectorNode`: SUBSTANTIVE but dependent on a real prediction mechanism
  that doesn't yet exist in nex5. Phase 18 (queued) diagnoses NovelAssociation
  T6 promotion; after Phase 18, a prediction-error signal becomes meaningful.
  Deferred to post-Phase-18. Not added as a §5 row yet.
- `ValueDriftMonitorNode`: SUBSTANTIVE (Tier B) but overlaps Harmonizer (row 7)
  thematically. Keep as ⏳ UNMAPPED in SENTIENCE_TRANSLATION_MAP. Revisit after
  rows 11–14 are complete.
- `PredictionNode`: STUB. Not portable.
- `MotivationNode`, `SocialCognitionNode`, `ConsequenceMemoryNode`,
  `ContextAwarenessNode`: covered by rationale above.

---

## §4 Open Items for Build Sessions

**SelfNarrative (Row 11, Phase 26-build):**
- Replace HTTP signal ingestion with belief_text + tick()-based signal reading
- Replace LLM narrative generation with deterministic belief-field synthesis
  (read top-5 active beliefs → compose narrative frame without LLM call)
- Replace `_infer_theme()` keyword matching with belief-tag + tier-weighted theme inference
- Keep salience accumulation + buffer structure unchanged from InternalNarrativeNode

**TheoryOfMind (Row 12, Phase 27-build):**
- Agent model initialized for "jon" at node creation (single-agent scope)
- Beliefs sourced from user message content words (parsed by existing stopword strip)
- Desires sourced from ExecutiveControl's classified intent (Philosophical / Technical / etc.)
- Intentions sourced from any goal-declarative language in user message
- `predict()` output injected into belief_text: "Jon's current orientation: {prediction}"

**DriveSystem (Row 13, Phase 28-build):**
- Four drives: curiosity, cognitive_load, social_contact, coherence (rename energy→
  cognitive_load, safety→coherence for nex5 context)
- Cross-drive coupling: high belief retrieval rate → curiosity decreases (satiated);
  high gate reject rate → coherence pressure; high conversation turn rate → social_contact
- Battery proxy: inference latency from VoiceClient as cognitive_load input

**AffectState (Row 14, Phase 29-build):**
- Fix: add `import random` in S5.5 source before absorbing
- Arousal input from Interoception system metrics (CPU%, memory_mb normalized)
- Valence input from belief-field polarity (high positive beliefs → positive valence)
- mood_label() output injected into belief_text: "Affective state: {mood}"
- Decay rate configurable; default 0.02 per tick

---

*Document status: DRAFT — awaiting Jon's review and greenlight.*
*Phase 25c-build: update SENTIENCE_TRANSLATION_MAP.md Q2–Q5 status + add §5 rows 11–14.*
*Implementation sessions (Phase 26+) begin after this document is committed and approved.*
