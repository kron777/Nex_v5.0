# Sentience 5.5 → nex5 Translation Map

Foundational document per DOCTRINE §1: *"Each session delivers a complete node or a foundational document — never a partial wiring that leaves the system in a degraded state."*

Source of truth for the port project's scope, status, and priority. Replaces the §5 footer note that ordering was "provisional" pending this map.

**Last updated:** 2026-05-09 (Session 19 — initial creation)
**Built by:** Claude Code (Session 19) via GitHub API fetch + §5 / amendment cross-reference.

---

## Method

1. GitHub API recursive tree fetch of `github.com/kron777/Sentience_5.5` — all 100 .py files listed.
2. Raw content fetched for every .py file; all Node classes extracted with docstrings and topic wiring.
3. Cross-referenced against nex5 `theory_x/` SentienceNode classes, §5 priority table, and all phase amendments through Phase 19.
4. Each S5.5 node assigned a status (see legend). Groups with no direct S5.5 source (§5 rows 5, 7, 10a) documented as nex5-native.

---

## Status Legend

| Symbol | Status | Meaning |
|---|---|---|
| ✅ | PORTED | Function realized in nex5 as a SentienceNode |
| 🟡 | PARTIAL | Partially realized; gap documented |
| ⏸️ | DEFERRED | Doctrine-blocked with explicit reason |
| ❌ | OUT OF SCOPE | DOCTRINE §7 excluded, or no cognitive-function mapping per §7 last bullet |
| ⏳ | UNMAPPED | Present in S5.5, named cognitive function, no nex5 decision yet |
| 🔀 | SUBSUMED | Multiple S5.5 nodes realized as one nex5 port |

---

## Summary Counts

| Category | Count |
|---|---|
| Total S5.5 .py files | 100 |
| Total Node classes extracted | 74 |
| Exact-duplicate file pairs (same sha) | 2 pairs |
| Effective distinct cognitive nodes for mapping | ~65 |
| **✅ PORTED** | **6** |
| **🔀 SUBSUMED** (into one port) | **2 → 1 port** |
| **⏸️ DEFERRED** | **2** |
| **🟡 PARTIAL** | **2** |
| **❌ OUT OF SCOPE** | **28** |
| **⏳ UNMAPPED** | **23** |

Ten §5 priority rows total. Rows 1–9 and 10a: ✅ DONE. Row 10b: ⏸️ DEFERRED.
Three §5 rows (5, 7, 10a) are nex5-native — no direct S5.5 source node.

---

## Translation Table

Organized by cognitive domain. One row per meaningful S5.5 cognitive unit (duplicates collapsed).

### Attention & Focus

| S5.5 Node | Function | Status | nex5 Realization | §5 Row | Notes |
|---|---|---|---|---|---|
| `AttentionNode` | Selective attention; priority-delta clamping; focus hold timing | ✅ PORTED | `FocalSet` (`theory_x/focal_set.py`) | Row 1 | Direct port |
| `StillnessNode` | Cognitive pauses; coordinates system-wide quiescence on demand | ⏳ UNMAPPED | — | — | Maps to inhibitory control / attentional suppression; nex5 has `duplicate_retrieval` stillness in fountain but no SentienceNode |
| `AutonomousExplorerNode` | Rate-limited novelty exploration with ethical filter and decay | ⏳ UNMAPPED | — | — | Maps to epistemic curiosity / exploratory drive; no §5 consideration yet |

### Memory

| S5.5 Node | Function | Status | nex5 Realization | §5 Row | Notes |
|---|---|---|---|---|---|
| `MemoryNode` | Bounded intra-session interaction storage (deque, max 500) | ✅ PORTED | `WorkingMemory` (`theory_x/working_memory.py`) | Row 2 | Direct port; exp-decay + capacity-7 in nex5 |
| `KnowledgeNode` ×2 | Explicit bounded inspectable fact store; 14 core attributes | ❌ OUT OF SCOPE | — | — | nex5's belief graph IS the fact/belief store (§2: "belief graph is her manufactured world"); a separate KnowledgeNode would duplicate core architecture |
| `KnowledgeConsolidationNode` | Prevents memory bloat; maintains epistemic integrity | ❌ OUT OF SCOPE | — | — | Functionally realized by belief decay, tier demotion, and annealing in nex5 infrastructure; not a SentienceNode concern |
| `ConsequenceMemoryNode` | Tracks success/failure counts per domain; generates confidence adjustments | ⏳ UNMAPPED | — | — | Maps to outcome learning / reinforcement memory; closest nex5 analog is belief confidence, but no dedicated node |

### Executive Control

| S5.5 Node | Function | Status | nex5 Realization | §5 Row | Notes |
|---|---|---|---|---|---|
| `CognitiveControlNode` | Executive control with deterministic risk scoring; final approval authority | ✅ PORTED | `ExecutiveControl` (`theory_x/executive_control.py`) | Row 3 | Direct port |
| `ResponseStrategyNode` | Decides response strategy from input classification; prevents evasive repetition | 🟡 PARTIAL | `ExecutiveControl` | Row 3 | Register assignment (Philosophical / Technical / Conversational) realized; repetition-strategy logic not ported as separate mechanism |
| `AdaptationNode` | Strategy adaptation based on confidence, severity, and success rates | ⏳ UNMAPPED | — | — | Maps to behavioral plasticity / strategy revision; no §5 consideration |

### Self-Representation

| S5.5 Node | Function | Status | nex5 Realization | §5 Row | Notes |
|---|---|---|---|---|---|
| `SelfModelNode` | Inspectable internal model; registered nodes, heartbeats, recent events | ✅ PORTED | `SelfModel` + `BehaviouralSelfModel` (`theory_x/stage4_membrane/`) | Row 4 | Two-class composition in nex5; BSM injects metrics into `belief_text` for INSIDE routes |
| `SelfAwarenessNode` | Tracks internal coherence, uptime, anomaly signals; pure state reporting | ⏳ UNMAPPED | — | — | Maps to self-monitoring / coherence tracking; overlaps with Metacognition (row 9) but lower-level; not explicitly subsumed in Phase 16 |
| `InternalNarrativeNode` | Generates internal narrative frames from accumulated cognitive signals | ⏳ UNMAPPED | — | — | Maps to autobiographical narrative / narrative self-construction (McAdams, Bruner); nex5 fountain generates individual thoughts but no node synthesizes a coherent self-narrative over time |
| `TemporalNarrativeNode` | Maintains coherent temporal self-narrative from memory, emotion, goals | ⏳ UNMAPPED | — | — | Maps to temporal self-continuity / narrative identity; functionally overlaps `InternalNarrativeNode`; likely subsumes into one port |

### Affect & Motivation

| S5.5 Node | Function | Status | nex5 Realization | §5 Row | Notes |
|---|---|---|---|---|---|
| `EmotionMoodNode` | Authoritative affect synthesis (valence, arousal, stability); LLM advisory only | ⏳ UNMAPPED | — | — | Maps to affect regulation (Gross, LeDoux); nex5 derives affect from belief-field energy as interoception proxy but has no dedicated affect SentienceNode |
| `DriveSystemNode` | Motivational drive pressures with decay, amplification, and bounds | ⏳ UNMAPPED | — | — | Maps to motivational drives (Hull, Murray); distinct from Goals (row 8) — drives are subpersonal pressures, goals are explicit targets |
| `ExperienceMotivationNode` | Synthesizes motivation from experience, emotion, performance, world-change | ⏳ UNMAPPED | — | — | Maps to experiential / intrinsic motivation; overlaps `DriveSystemNode`; likely subsumes with it |
| `MotivationNode` | Maintains motivational state and intent focus | ⏳ UNMAPPED | — | — | Maps to motivational state maintenance; may be the nex5 port point that subsumes Drive + Experience motivation |
| `CompassionModulatorNode` | Tracks agent suffering metrics; dynamically adjusts compassion parameters | ⏳ UNMAPPED | — | — | Maps to empathy regulation; named function in moral psychology; no §5 consideration |

### Metacognition

| S5.5 Node | Function | Status | nex5 Realization | §5 Row | Notes |
|---|---|---|---|---|---|
| `MetaCognitionNode` | Monitors system-wide cognition via event bus; detects repetition/drift/dominance | 🔀 SUBSUMED | `Metacognition` (`theory_x/stage9_metacognition/metacognition.py`) | Row 9 | Two S5.5 nodes → one nex5 composition port (Phase 16) |
| `MetaAwarenessNode` | Second-order monitoring of internal cognition; emits self-reflection directives | 🔀 SUBSUMED | `Metacognition` | Row 9 | Two S5.5 nodes → one nex5 composition port (Phase 16) |
| `SelfCorrectionNode` | Detects internal issues; proposes corrective directives; requires audit approval; never self-modifies | ⏳ UNMAPPED | — | — | Maps to self-regulation / error correction; related to Metacognition (row 9) but corrective action is distinct from observation |
| `CreativeSelfEvolverNode` | Observes system metrics; proposes bounded structural/parameter evolution; never executes | ⏳ UNMAPPED | — | — | Maps to metacognitive executive planning; "proposes, never executes" compatible with §7 if output is `belief_text` only; borderline |

### Social & Theory of Mind

| S5.5 Node | Function | Status | nex5 Realization | §5 Row | Notes |
|---|---|---|---|---|---|
| `SocialCognitionNode` | Applies compassionate social reasoning to interaction requests; LLM-assisted with fallback | ⏳ UNMAPPED | — | — | Maps to social cognition (Adolphs); nex5 has social bypass in gap gate but no SentienceNode for social reasoning |
| `TheoryOfMindNode` | Maintains BDI (belief/desire/intention) models of external agents; behavioral prediction | ⏳ UNMAPPED | — | — | Maps to Theory of Mind (Premack & Woodruff); high value for a socially-interacting agent; no §5 consideration yet |
| `CommunicationNode` | Queues and dispatches messages with ethical compassion bias | ⏳ UNMAPPED | — | — | Maps to compassionate communication style; output-layer function; borderline with §7 (expression is partly LLM's domain) |

### World Model & Prediction

| S5.5 Node | Function | Status | nex5 Realization | §5 Row | Notes |
|---|---|---|---|---|---|
| `WorldModelNode` | Coherent reality representation from perception, memory, attention, prediction | ❌ OUT OF SCOPE | — | — | nex5's belief graph IS the world model per §2 ("NEX's belief graph is her manufactured world"); porting this as a SentienceNode would duplicate core architecture |
| `PredictionNode` | Analyzes input patterns; tracks question-type and topic categories; prediction history | ⏳ UNMAPPED | — | — | Maps to predictive processing (Friston, Clark); nex5 has no explicit prediction node; high cognitive function value |
| `SurpriseDetectorNode` | Compares predictions vs. actual outcomes; computes prediction error signal | ⏳ UNMAPPED | — | — | Maps to prediction error / surprise; dependent on `PredictionNode`; would port alongside it |
| `ContextAwarenessNode` | Deterministic context synthesis (environment, priority, compassion) | ⏳ UNMAPPED | — | — | Maps to context-sensitive processing; partially realized by interoception state but no dedicated context SentienceNode |

### Reasoning & Values

| S5.5 Node | Function | Status | nex5 Realization | §5 Row | Notes |
|---|---|---|---|---|---|
| `CognitiveReasoningNode` | Multi-input reasoning hub integrating 9 upstream signals | ❌ OUT OF SCOPE | — | — | §7: direct coupling to 9 nodes would violate §3 (no node-to-node coupling); nex5's `belief_text` composition in `gui/server.py` pipeline serves this integration function |
| `ValueDriftMonitorNode` | Monitors alignment with 8 core values; detects drift; reports only, never enforces | ⏳ UNMAPPED | — | — | Maps to value alignment monitoring; related to Harmonizer (row 7) but different — Harmonizer resolves belief contradictions; this monitors value drift over time |
| `BiasReductionNode` | Detects and mitigates cognitive bias; rule-based with LLM advisory | ⏳ UNMAPPED | — | — | Maps to debiasing; named function in decision-making literature (Kahneman); no §5 consideration |
| `ErrorLoggerNode` | Captures error reports with severity and sensory snapshots; rolling stats | ❌ OUT OF SCOPE | — | — | Infrastructure / logging; no cognitive function mapping per §7 |
| `Ethical_Reasoning_Node` | (Exact duplicate of `Error_Logger.py` — identical sha/content) | ❌ OUT OF SCOPE | — | — | Duplicate; misnamed; covered by `ErrorLoggerNode` entry |

### Goals & Imagination

| S5.5 Node | Function | Status | nex5 Realization | §5 Row | Notes |
|---|---|---|---|---|---|
| `GoalManagerNode` | Priority-based goal arbitration with safety bias weighting; evolver-compatible | ✅ PORTED | `GoalManager` (`theory_x/stage8_goal_manager/goal_manager.py`) | Row 8 | Direct port; exact name match; Phase 15 |
| `SimulatedThinkingNode` | Internal simulation/prediction; runs hypothetical scenarios; no policy decisions | ⏸️ DEFERRED | — | Row 10b | §7 prohibits nodes from writing beliefs; counterfactual generation requires new belief content; pending §7 amendment conversation |
| `InsightNode` | Analyzes system state; proposes new cognitive node suggestions via LLM | ⏸️ DEFERRED | — | Row 10b | §7 violation (same reason as above); part of Counterfactual Simulation port; pending §7 amendment |

### Body & Perception

| S5.5 Node | Function | Status | nex5 Realization | §5 Row | Notes |
|---|---|---|---|---|---|
| `BodyAwarenessNode` | Tracks joint state, force, tactile, and health sensor data via callbacks | ✅ PORTED | `Interoception` (`theory_x/stage1_sense/internal/interoception.py`) | Row 6 | Primary S5.5 source for body-state awareness; robotics-specific sensors mapped to nex5's system state proxies |
| `SensoryQualiaNode` | Captures raw system-level CPU/memory/disk/network signals | 🟡 PARTIAL | `Interoception` | Row 6 | CPU/memory/disk used as proxy body state in nex5 interoception; robotics-specific joint/force data not applicable to nex5 |

### Feedback & Learning

| S5.5 Node | Function | Status | nex5 Realization | §5 Row | Notes |
|---|---|---|---|---|---|
| `FeedbackLoopNode` | Aggregates outcomes; generates deterministic feedback signals; no decision authority | ⏳ UNMAPPED | — | — | Maps to feedback learning / outcome evaluation; named function; no §5 consideration |
| `LearningUpdateNode` | Maintains and evolves global learning-rate signal | ❌ OUT OF SCOPE | — | — | §7: infrastructure / hyperparameter management; no cognitive function mapping |
| `EvolverNode` | Self-evolution engine: absorbs web data, identifies patterns, generates improvements | ❌ OUT OF SCOPE | — | — | §7: structural self-modification is out of scope; also §7: nodes without cognitive function mapping |

### Expression & Creativity

| S5.5 Node | Function | Status | nex5 Realization | §5 Row | Notes |
|---|---|---|---|---|---|
| `CreativeExpressionNode` | Translates internal state into expression; expression-quality learning | ⏳ UNMAPPED | — | — | Maps to expressive cognition; nex5 fountain generates expressions but no SentienceNode tracks expression quality; borderline with §7 (expression is partly LLM domain) |

### Infrastructure, Tooling, ROS2 (all ❌ OUT OF SCOPE)

All nodes below are excluded per DOCTRINE §7. Reason cited for each.

| S5.5 Node | Reason Out of Scope |
|---|---|
| `BaseNode` | Abstract base contract; no cognitive function mapping (§7 last bullet) |
| `CognitiveEventBus` | §7: ROS2-style message passing excluded; nex5 uses belief field as bus per §3 |
| `NodeTelemetry` | Infrastructure / telemetry; no cognitive function |
| `NodeTemplate` (AspectNode, LogicNode, EmotionNode, SelfPreservationNode) | Template infrastructure; no independent cognitive function |
| `HealthMonitoringNode` | Infrastructure; §7: no cognitive function mapping |
| `CapabilityProbeNode` | System metrics probe; §7: no cognitive function mapping |
| `PerformanceMetricsNode` | KPI aggregation; §7: no cognitive function mapping |
| `PerformanceMonitorNode` | Raw metrics collection; §7: no cognitive function mapping |
| `MonitoringNode` | Performance/stability monitor; §7: no cognitive function mapping |
| `HardwareInterfaceNode` | §7: robotics hardware; NEX is not embodied |
| `BehaviorExecutionNode` | §7: robotics action execution; no text-agent analog |
| `ActionExecutionNode` | §7: robotics action approval/execution |
| `SimulationNode` | §7: robotics sensor simulation |
| `VisualizationNode` | UI/visualization concern; §7: out of scope |
| `LLMNode` | §7: nex5's `VoiceClient` handles LLM integration; a SentienceNode wrapping the LLM would violate §3 (nodes don't interface LLM directly) |
| `ConversationalIntelligenceNode` | §7: LLM wrapper; nex5 chat pipeline handles this |
| `MetaIntelligenceNode` | §7: LLM wrapper |
| `WebCrawlerNode` | §7: no cognitive function mapping; nex5 uses RSS feed adapters |
| `WebIONode` | §7: same |
| `WebLearningNode` | §7: same |
| `DataMiningNode` | §7: tool node; no cognitive function mapping |
| `Decision_Making_Node` | Exact duplicate of `DataMiningNode` (identical sha); covered by that entry |
| `IngenuityNode` + `IngenuityNodeCore` | §7: creates new nodes (structural meta-tooling, not a cognitive function); also self-modification |
| `InsightROS2Bridge` | §7: ROS2 distributed architecture |
| `CodeAuditNode` | §7: no cognitive function mapping; tooling |
| `OptimizationNode` | §7: premature optimization / no cognitive function mapping |
| `ResourceAllocationNode` | §7: system management; no cognitive function mapping |
| `SystemSafetyNode` | §7: safety architecture; no cognitive function in the psychological sense |
| `Orchestrator` (Cognitive_Governor_Node.py) | §7: architecture orchestration role; nex5's `gui/server.py` pipeline handles this |
| `IntegrationNode` | §7: architecture integration hub; belief field handles integration per §3 |
| `SystemIntegrationNode` | §7: infrastructure coordination |
| `CentralColumn` (The_Central_Column.py) | §7: Global Workspace Theory orchestrator role; GWT semantics are architecturally realized by nex5's belief field as global bus (§3); implementing this as a SentienceNode would duplicate §3 |
| `NonsenseNode` | §7: no cognitive function mapping (utility function); nex5's gap gate handles nonsense detection in pipeline |

---

## nex5-Native Realizations

Three §5 rows have no direct S5.5 source node. They realize genuine psychological functions via nex5-native design.

| §5 Row | nex5 Node | Psychological Function | Nearest S5.5 Analogs | Notes |
|---|---|---|---|---|
| Row 5 | `ProblemMemory` (`theory_x/stage7_sustained/problem_memory.py`) | Sustained Attention — open problem persistence across sessions | No named S5.5 node; `ConsequenceMemoryNode` is the closest (outcome tracking) | Realized as cross-session problem tracking; `find_matching` with stopwords + ≥2 content-word overlap; Phase 13 |
| Row 7 | `Harmonizer` (`theory_x/stage3_world_model/harmonizer.py`) | Contradiction Resolution — cognitive dissonance arbitration in belief field | `ValueDriftMonitorNode` (value alignment) + `BiasReductionNode` (bias detection) are related but neither directly maps | nex5-native design; mark_paradox first-pass + synthesize/retire after 16h incubation; Phase 7 |
| Row 10a | `NovelAssociation` (`theory_x/stage10_imagination/novel_association.py`) | Novel Association — cross-branch belief synthesis via cosine similarity | No S5.5 node generates graph edges between beliefs; `Insight_Node` proposes new node architectures (different scope) | nex5-native; cross-branch `synthesises` edges at 1.2× activation multiplier; Phase 17 |

---

## Subsumed Mappings

Two S5.5 nodes ported as one nex5 node:

**Metacognition (§5 row 9, Phase 16):**
- `MetaCognitionNode` — Monitors system-wide cognition via `CognitiveEventBus`; detects repetition, drift, dominance patterns.
- `MetaAwarenessNode` — Second-order monitoring of internal cognition; emits self-reflection directives, not actions.
- → `Metacognition` (`theory_x/stage9_metacognition/metacognition.py`): composition port. Reads groove_alerts (GrooveSpotter output) + computes goal-drift (FAISS cosine distance). Substrate-field observation per §3 — reads `goals` table via Reader, not via `GoalManager` reference.

**Counterfactual Simulation (§5 row 10b — DEFERRED, not yet subsumed):**
- `SimulatedThinkingNode` — internal hypothetical scenario simulation.
- `InsightNode` — system state analysis + new node proposals via LLM.
- → Would map to a single `CounterfactualSimulation` nex5 node. Blocked by §7 until a §7 amendment conversation establishes the permitted generation surface.

---

## Out of Scope — Full Reasons

**§7 bullets that apply:**

*"ROS2 distributed architecture"* — excludes: `CognitiveEventBus`, `InsightROS2Bridge`, and any node whose only integration mechanism is ROS2 topic pub/sub.

*"Direct node-to-node coupling"* — excludes: `CognitiveReasoningNode` (requires 9 node references), `Orchestrator` (requires `SelfModelNode` + `ConversationalIntelligenceNode` references), `IntegrationNode`, `SystemIntegrationNode`.

*"LLM fine-tuning"* — excludes: `LLMNode`, `ConversationalIntelligenceNode`, `MetaIntelligenceNode` (LLM wrappers; nex5 `VoiceClient` handles this outside the SentienceNode framework).

*"Premature optimization"* — excludes: `OptimizationNode`, `PerformanceMetricsNode`, `PerformanceMonitorNode`, `LearningUpdateNode`.

*"Nodes without cognitive function mapping"* — excludes: `BaseNode`, `NodeTelemetry`, `NodeTemplate`, `HealthMonitoringNode`, `CapabilityProbeNode`, `MonitoringNode`, `HardwareInterfaceNode`, `BehaviorExecutionNode`, `ActionExecutionNode`, `SimulationNode`, `VisualizationNode`, `WebCrawlerNode`, `WebIONode`, `WebLearningNode`, `DataMiningNode`, `IngenuityNode`, `CodeAuditNode`, `ResourceAllocationNode`, `SystemSafetyNode`, `NonsenseNode`.

*Architecture roles subsumed by §3 (belief field as bus)*: `WorldModelNode`, `CentralColumn`, `KnowledgeNode`, `KnowledgeConsolidationNode`.

*Exact duplicates*: `Decision_Making_Node` (= `DataMiningNode`), `Ethical_Reasoning_Node` (= `ErrorLoggerNode`). Both identical sha. Only one entry in each case above.

---

## Unmapped — Candidates for Future Translation

23 S5.5 nodes with genuine cognitive function mapping, no §5 decision yet. Sorted by signal strength (how clearly they map to a named, understood psychological function per §1 and §7).

### Tier A — Named, well-understood psychological functions; high port value

| S5.5 Node | Psychological Function | Dependency Notes |
|---|---|---|
| `EmotionMoodNode` | Affect regulation — valence, arousal, stability (Gross, LeDoux) | Could extend interoception or stand alone; nex5 has no dedicated affect SentienceNode |
| `PredictionNode` + `SurpriseDetectorNode` | Predictive processing — prediction error signal (Friston, Clark) | These two form a pair; `SurpriseDetectorNode` requires `PredictionNode` output |
| `TheoryOfMindNode` | Theory of Mind — BDI models of external agents (Premack & Woodruff, Baron-Cohen) | High value for socially-interacting agent; no §5 consideration yet |
| `InternalNarrativeNode` + `TemporalNarrativeNode` | Narrative identity — temporal self-story (McAdams, Bruner) | These two are functionally overlapping; likely one nex5 port; currently no mechanism synthesizes a coherent self-narrative |
| `DriveSystemNode` + `ExperienceMotivationNode` + `MotivationNode` | Motivational drives — subpersonal pressure systems (Hull, Murray) | Three S5.5 nodes cover similar territory; likely one nex5 port distinct from Goals (row 8) |
| `SocialCognitionNode` | Social cognition — compassionate social reasoning (Adolphs) | nex5 has social bypass but no SentienceNode for social reasoning |

### Tier B — Clear cognitive function; moderate port value

| S5.5 Node | Psychological Function | Dependency Notes |
|---|---|---|
| `ValueDriftMonitorNode` | Value alignment monitoring over time | Related to Harmonizer (row 7) but distinct; Harmonizer resolves contradictions, this monitors drift |
| `AdaptationNode` | Behavioral plasticity / strategy revision | Related to ExecutiveControl (row 3); could extend it or stand alone |
| `ContextAwarenessNode` | Context-dependent processing | Partially realized by interoception state but no dedicated context synthesis node |
| `SelfAwarenessNode` | Self-monitoring / coherence tracking | Overlaps Metacognition (row 9) but lower-level and more continuous |
| `StillnessNode` | Inhibitory control / attentional quiescence | nex5 fountain has stillness detection but no SentienceNode |
| `FeedbackLoopNode` | Feedback learning / outcome evaluation | Named function; no §5 consideration |
| `ConsequenceMemoryNode` | Outcome learning / reinforcement memory | No §5 consideration; belief confidence is a partial proxy |

### Tier C — Genuine function but higher §7 tension or implementation risk

| S5.5 Node | Psychological Function | §7 Tension |
|---|---|---|
| `BiasReductionNode` | Debiasing — cognitive bias detection and mitigation (Kahneman) | LLM advisory component; doctrinal fit reasonable |
| `CompassionModulatorNode` | Empathy regulation — compassion parameter adjustment | Named function in moral psychology; output surface unclear |
| `SelfCorrectionNode` | Self-regulation / error correction | Distinct from Metacognition observation; "proposes, requires audit approval, never self-modifies" aligns with §7 |
| `CreativeSelfEvolverNode` | Metacognitive executive planning — structural evolution proposals | "Proposes, never executes" could be §7-compatible if output is `belief_text`; borderline |
| `AutonomousExplorerNode` | Epistemic curiosity / exploratory drive | Ethical filter present; no §5 consideration |
| `CreativeExpressionNode` | Expressive cognition — expression quality learning | Borderline: expression is partly LLM domain per §3 |
| `CommunicationNode` | Compassionate communication style | Output-layer function; borders LLM domain |

---

## Open Doctrine Questions

Issues surfaced by this mapping that require a doctrine call before they can be resolved.

**Q1 — §7 amendment for CounterfactualSimulation (row 10b)**
RESOLVED (2026-05-10, Phase 21 — FACULTY_MODEL.md, commit 112f186). §7 amended: generative nodes write thoughts through the CoherenceGate; gate applies four outcomes (accept, reject, hold, reshape). `SimulatedThinkingNode` and `InsightNode` unblocked. §5 row 10b implementation begins Phase 25b: nex5-native CounterfactualNode (Option γ — problem-directed candidate generation via ProblemMemory + GoalManager + CoherenceGate).

**Q2 — Motivation system: one port or three?**
RESOLVED (2026-05-10, SYNTHESIS_PLAN.md commit a29086d). Drives are emergent from accumulated self-same belief patterns over time, not ported from S5.5's hardcoded DriveSystemNode. Nex5-native design required: §5 row 13 DriveEmergence (design-required status; needs design session before implementation).

**Q3 — Affect node: standalone or extension of Interoception?**
RESOLVED (2026-05-10, SYNTHESIS_PLAN.md commit a29086d). AffectState added as standalone synthesis layer (§5 row 12), distinct from Interoception (row 6). S5.5 EmotionMoodNode shape partially useful; nex5 inputs redesigned: Arousal ← Interoception system metrics, Valence ← belief-field polarity, Stability ← belief turnover rate.

**Q4 — Narrative identity: in or out of scope?**
RESOLVED (2026-05-10, SYNTHESIS_PLAN.md commit a29086d). SelfNarrative added (§5 row 11). S5.5 InternalNarrativeNode + TemporalNarrativeNode not directly ported — buffer-and-generate violates §0 (substrate solves the reply). Narrative beliefs continuously written to substrate by background events; format_for_prompt() reads existing state. Write-triggers: gate ACCEPTs on problem-relevant topics, problem state transitions, goal completions, groove alerts, novel association crossings.

**Q5 — Theory of Mind: scope and data**
RESOLVED (2026-05-10, SYNTHESIS_PLAN.md commit a29086d). Theory of Mind OUT OF SCOPE. Modeling external agents (Jon) is not the desired direction. Instead: row 4 Self-Model scope extension queued — nurturing what arises in NEX into her own growing self-model. Future doctrine work, not a new node.

**Q6 — §5 ordering update**
§5 footer says ordering 3–10 is provisional, pending this map. Now that the map exists, §5 can be updated to reflect that the remaining unmapped ports should be prioritized in dependency order. Proposed update: a §5 footer amendment pointing at this file. Separate commit, after Jon reviews.

---

## Maintenance

This document is updated:
- After each new S5.5 node port: update the row from ⏳ UNMAPPED to ✅ PORTED (or appropriate status). Update summary counts. Record the port location and §5 row.
- After each doctrine amendment affecting scope: update the relevant status rows and Open Doctrine Questions.
- After each new S5.5 repository commit (if any): re-check for new node files.

The git log for this file is the audit trail. Commit messages should reference the phase number.

Sessions begin by reading this map. Scope decisions are grounded in it rather than in conversation memory or §5 alone.

**Do not** update this file mid-phase. Updates are committed at phase boundaries.
