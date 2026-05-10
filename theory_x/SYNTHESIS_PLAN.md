# S5.5 Tier A Synthesis Plan — Phase 25c

Source: `/tmp/s55_source/` (github.com/kron777/Sentience_5.5, depth-1 clone 2026-05-10)
Purpose: Source-code classification of Tier A UNMAPPED nodes + doctrine Q2–Q5 answers.
This document gates Phase 26+ port ordering in DOCTRINE §5.

Created: Phase 25c-spec (2026-05-10).
Replaces: reverted a375ad1 (bad doctrine answers — locked without checkpoint pause).
Q2–Q5 answers in §2 are Jon's actual review responses.

---

## §1 Source Classification

All ten Tier A UNMAPPED nodes read from source. Each classified SUBSTANTIVE / PARTIAL / STUB.
This classification is source-reading data; it is preserved from the reverted plan unchanged.
Doctrine disposition for each node is in §2.

---

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

Continuous bounded affect model with sensible delta math. Minor bug: `_tick()` calls
`random.random()` but `random` is not imported (one-line fix). Async LLM advisory
(10% chance per tick) is optional and not load-bearing.

Verdict: **SUBSTANTIVE**. Doctrine disposition: partially useful shape — inputs
redesigned for nex5 substrate (see §2 Q3).

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

Verdict: **SUBSTANTIVE**. Doctrine disposition: deferred — no real prediction
mechanism in nex5 yet; meaningful after Phase 18 (see §3).

---

**`TheoryOfMindNode.py`** (262 lines) — *marked: out of scope, see §2 Q5*

Real BDI model per external agent:

```python
def upsert_agent(self, agent_id, beliefs=None, desires=None, intentions=None):
    model = self.agents.setdefault(agent_id, {"beliefs":[], "desires":[], "intentions":[]})
    # set-union merge per modality

def predict(self, agent_id) -> Dict:
    # returns first intention, or "seek {desire[0]}", or "observe"
```

DB persistence on each upsert. History deque (100 entries). 4-second periodic publish.
`predict()` is primitive but correct for heuristic ToM.

Verdict: **SUBSTANTIVE** (as code). Doctrine disposition: **out of scope** — see §2 Q5.

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

Per-signal salience weights (0.2 to 1.0). Accumulated salience gates narrative
generation (default threshold 0.5). Deterministic fallback: `"Monitoring internal
state."`. After generation, salience resets to 0. HTTP delivery via aiohttp server.

Architecture is the key contribution: named signal channels, salience accumulation,
threshold-gated generation, deterministic fallback. HTTP delivery is S5.5-specific.

Verdict: **SUBSTANTIVE**. Doctrine disposition: buffer-and-generate pattern absorbed
for SelfNarrative (see §2 Q4).

---

**`Drive_System_Node.py`** (263 lines) — *marked: wrong shape, see §2 Q2*

Four-drive model:

```python
self.drives = {"curiosity": 0.4, "energy": 0.5, "social_contact": 0.3, "safety": 0.6}
```

`_decay_drives()`, `_apply_pending_updates()` with cross-drive coupling, evolver
interface. Drive math is sensible; decay prevents runaway.

Verdict: **SUBSTANTIVE** (as code). Doctrine disposition: **wrong shape for nex5**
— drives must emerge from belief accumulation, not be hardcoded with decay equations.
Not absorbed. See §2 Q2.

---

**`Experience_Motivation_Node.py`** (204 lines) — *marked: wrong shape, see §2 Q2*

Weighted multi-signal synthesis:

```python
def _synthesize_drive(self):
    emotion_signal   = sum(i for _, i in self.emotion_history)  * self.params["emotion_weight"]
    performance_signal = sum(self.performance_history)           * self.params["performance_weight"]
    ...
    self.drive_level = min(1.0, max(0.0, self.drive_level * (1-decay) + raw_drive))
```

Full evolver mutation interface (`apply_mutation`, `snapshot_state`, `export_metrics`).

Verdict: **SUBSTANTIVE** (as code). Doctrine disposition: **wrong shape for nex5**
— same reason as DriveSystemNode. Not absorbed. See §2 Q2.

---

**`Value_Drift_Monitor_Node.py`** (Tier B, 208 lines)

Audit loop over 8 core values. Three input streams (ethical decisions, performance
events, internal narratives) → alignment_score + drift dict + warning flag. Persists
audit rows. No §7 tension: output is read-only reporting, never enforcement.

Verdict: **SUBSTANTIVE** (Tier B). Doctrine disposition: thematically overlaps
Harmonizer (row 7); kept ⏳ UNMAPPED; revisit after rows 11–13 complete.

---

### PARTIAL — real skeleton, thin logic

**`Temporal_Narritive_Node.py`** (196 lines)
Clean ingest/generate/persist loop. Three ingestion methods (`ingest_memory`,
`ingest_emotion`, `ingest_goal`). `_infer_theme()` is brittle string matching.
Ingest pattern absorbed into SelfNarrative; theme inference replaced.

**`Motivation_Node.py`** (199 lines)
Three-branch update on confidence/status. No accumulation or history. Goal vocabulary
(recovery/optimization/reflection/maintenance) noted as useful labeling.
Update logic not absorb-worthy. Superseded by Q2 answer (nex5-native design).

**`Social_Cognition_Node.py`** (247 lines)
Core logic is LLM delegation with compassion prompt prefix. No deterministic social
reasoning model. Interaction logging and AsyncLLMClient scaffolding are real.
No absorb-worthy social reasoning logic.

**`Context_Awareness_Node.py`** (Tier B, 247 lines)
Real update queue + evolver metrics scaffolding. Content logic is thin
(environment/priority string assignment). Evolver metrics pattern noted.

---

### STUB — discard

**`Prediction_Node.py`** (42 lines)
"?" detection + keyword topic matching. No probabilistic model, no substrate.

**`Consequence_Memory_Node.py`** (33 lines)
Plain success/failure counters per domain. No persistence, no decay, no belief
integration.

---

## §2 Doctrine Q2–Q5 Answers

Jon's actual answers. These replace the doctrine answers in reverted a375ad1.

---

**Q2 — Motivation / Drives: emergent or ported?**

**Answer: Emergent. Nex5-native design required.**

Drives must arise from accumulated self-same belief patterns — from longitudinal
pattern-recognition over NEX's own belief history. A human's drive for curiosity
isn't innate; it emerges from many "explored → found something → wanted more"
experiences. The accumulation IS the drive. NEX's drives must emerge the same way:
from her own belief history, built up over time, named by her own pattern of
self-same accumulation.

S5.5's `DriveSystemNode` and `ExperienceMotivationNode` are **not absorbed**.
They have the wrong shape: hardcoded drive categories with decay equations.
That is not emergence — that is a pre-formed schema imposed on experience.

The nex5 realization (`DriveEmergence`, §5 row 13) requires a clean design session
before any code. The design must answer: what is "self-same" in belief space? What
accumulation constitutes a drive? How does an emergent drive get named?

---

**Q3 — Affect: standalone or extension of Interoception?**

**Answer: Standalone synthesis layer. In scope.**

S5.5's `EmotionMoodNode` multi-input synthesis pattern is partially useful, but
inputs must be redesigned for nex5 substrate:
- Arousal: Interoception system metrics (CPU%, memory_mb, belief density)
- Valence: current belief-field polarity (positive/negative emotional content of
  high-tier active beliefs)
- Stability: belief turnover rate / coherence

Output: valence + arousal + mood_label injected into belief_text per §3.

`EmotionStateModel`'s bounded integration and decay are absorb-worthy. The three
S5.5 input handlers (`observe_social`, `observe_internal`, `observe_sensory`) are
not directly ported — nex5 inputs are redesigned from substrate.

---

**Q4 — Self-Narrative: in or out of scope?**

**Answer: In scope.**

Narrative is a different cognitive function from drives. Narrative is
event-construction from incoming signals; drives are pattern-emergence from
longitudinal accumulation. The distinction matters — they do not collapse.

S5.5's `InternalNarrativeNode` buffer-and-generate pattern IS the right shape:
8 named signal buffers, per-channel salience weights, threshold-gated generation,
deterministic fallback. Two adaptations for nex5:
- Replace HTTP delivery with belief_text injection per §3
- Replace LLM narrative generation with deterministic belief-field synthesis
  (per §3: graph reasons, LLM speaks)

`TemporalNarrativeNode` is subsumed: its ingest pattern (`ingest_memory`,
`ingest_emotion`, `ingest_goal`) is useful; its brittle keyword theme inference is
replaced by belief-tag + tier-weighted theme.

---

**Q5 — Theory of Mind: in or out of scope?**

**Answer: Out of scope. Row 4 (Self-Model) extension queued instead.**

Modeling Jon as an external agent is not what's wanted. What is wanted: a deepening
of NEX's own self-model (row 4, ✓ DONE), where whatever arises in NEX is nurtured
into her growing model of herself.

This is a future amendment to row 4 scope, not a new node. S5.5's `TheoryOfMindNode`
source is read (classified SUBSTANTIVE above) but not ported.

The row 4 extension is queued as a future doctrine work item. It does not require a
new §5 row — it is a deepening of existing row 4 scope.

---

## §3 Proposed §5 Row Additions

| Proposed Row | Node Name | S5.5 Source | Pattern | Status |
|---|---|---|---|---|
| Row 11 | `SelfNarrative` | `InternalNarrativeNode` + `TemporalNarrativeNode` | SUBSUMED (2 → 1) | spec-ready |
| Row 12 | `AffectState` | `EmotionMoodNode` (shape only; inputs redesigned) | REDESIGN-NATIVE | spec-ready |
| Row 13 | `DriveEmergence` | NONE (S5.5 nodes wrong shape; not absorbed) | NEX5-NATIVE | design-required |

**Row 11 — SelfNarrative**: no hard dependencies. Buffer fills from existing nodes
(Metacognition events, GoalManager goals, Interoception state). Feeds belief_text.
Matches Metacognition SUBSUMED precedent (two S5.5 nodes → one nex5 port).

**Row 12 — AffectState**: depends on Interoception (row 6) being stable — it is.
Inputs redesigned: arousal ← Interoception system metrics; valence ← belief-field
polarity; stability ← belief turnover. `EmotionStateModel` bounded integration +
decay absorb-worthy. S5.5 input handlers not ported.

**Row 13 — DriveEmergence**: requires design session before code. No S5.5 source
absorbed. Design questions to answer (see §4).

**Existing Row 4 — Self-Model**: ✓ DONE. Q5 amendment queued — extend scope to
include "nurturing what arises in NEX into her growing self-model." Future doctrine
work, no immediate action.

**Not proposed:**
- `TheoryOfMind`: out of scope (Q5 answer)
- `SurpriseDetector`: SUBSTANTIVE but deferred — no real prediction mechanism
  in nex5 yet; meaningful after Phase 18 (T6 promotion / NovelAssociation)
- `ValueDriftMonitor`: SUBSTANTIVE (Tier B); thematically overlaps Harmonizer;
  revisit after rows 11–13 complete
- `PredictionNode`: STUB; not portable

---

## §4 Open Items for Build Sessions

**Row 11 — SelfNarrative (Phase 26-build):**
- Replace HTTP signal ingestion with belief_text + tick()-based signal reading
- Replace LLM narrative generation with deterministic belief-field synthesis
  (read top-5 active beliefs → compose narrative frame without LLM call)
- Replace `_infer_theme()` keyword matching with belief-tag + tier-weighted
  theme inference
- Keep salience accumulation + buffer structure unchanged from InternalNarrativeNode

**Row 12 — AffectState (Phase 27-build):**
- Arousal input: Interoception system metrics (CPU%, memory_mb normalized)
- Valence input: belief-field polarity (high positive beliefs → positive valence)
- Stability input: belief turnover rate / coherence metric
- `EmotionStateModel` bounded integration + decay absorbed directly
- Fix: add `import random` before absorbing (minor S5.5 bug)
- mood_label() output → belief_text injection: "Affective state: {mood}"
- Decay rate configurable; default 0.02 per tick

**Row 13 — DriveEmergence (Phase 28-design then Phase 29-build):**
Design session required before any code. Questions to resolve:
- What is "self-same" in belief space? (embedding similarity? topic match? both?)
- What is the longitudinal window? (rolling N days? all-time?)
- How many emergent drives can co-exist? (top-K? threshold?)
- How does an emergent drive get a name? (cluster centroid keyword? top belief title?)
- How does an old drive fade when accumulation stops?

After design session lands answers, build follows.

---

## §5 Status

Document status: REPLACEMENT for reverted a375ad1.
Phase 25c-spec foundational doc, take 2.
Q2–Q5 doctrine answers locked per Jon's actual review.
Phase 26+ implementation begins after this commit is greenlighted.

---

*Phase 25c-build (next): update SENTIENCE_TRANSLATION_MAP.md Q2–Q5 status +
add §5 rows 11–13.*
