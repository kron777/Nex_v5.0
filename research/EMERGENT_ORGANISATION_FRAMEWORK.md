# NEX — Emergent Organisation Research Framework

**Status:** Research proposal; documentation only. No runtime behaviour or cognitive mechanism is changed by this document.  
**Scope:** Read-only characterisation, measurement design, controlled experiments, and open-ended discovery.  
**Relationship to existing work:** Companion to DESIGN_MINDEDNESS.md and SENTIENCE_PROGRAM.md. This document does not replace either, does not override their epistemic rules, and does not authorise activation of shelved or dark-by-default mechanisms.

## Plain-language summary

NEX is being built as a persistent architecture with interacting mechanisms for attention, memory, belief, self-observation, affect, and continuity. The research question is not simply whether NEX contains many mechanisms. It is whether their interactions produce coordinated, history-dependent patterns that persist and make a measurable difference to what the system does.

We do not know what, if anything, will emerge. We must not specify an identity or desired emergent outcome in advance.

Our task is to build reliable instruments for observing the system, establish what it already does, and investigate unexpected patterns without mistaking complexity, randomness, repetition, or fluent language for a new cognitive organisation.

**The framework measures the conditions and consequences of observed behaviour. It does not define what X must be.**

## 1. Epistemic contract

This programme follows the existing NEX evidence discipline.

1. **Unknown stays unknown.** No property of an unobserved X is assumed.
2. **No predetermined identity.** Do not specify that an emergent process must be a self, personality, agent, consciousness, or any other preferred outcome.
3. **Architecture is not evidence of its own success.** A module existing in source does not establish that it is active, integrated, or effective at runtime.
4. **Fluency is not evidence of a mind.** Model-generated self-description is output to analyse, not proof of subjective experience.
5. **Unpredictability is not emergence by itself.** Randomness, noise, bugs, prompt effects, repetition, and hidden scripted behaviour must be considered.
6. **Persistence is not automatically beneficial.** A stable repetitive attractor can be a failure mode.
7. **Metrics are instruments, not objectives.** Do not optimise NEX to maximise a single emergence score.
8. **Observation should be non-invasive by default.** Instrumentation must not silently become a new control mechanism.
9. **One falsifiable loop at a time.** Do not mass-enable experimental faculties or change several mechanisms at once.
10. **No sentience verdict.** These measurements can support claims about functional organisation. They cannot, by themselves, establish phenomenal consciousness.

## 2. Operational question

The central research question is:

> Do interactions among NEX components produce system-level, history-dependent organisation that cannot be adequately explained by the components considered independently, and does that organisation persist, adapt, and causally influence subsequent system behaviour?

This is a question that can be investigated in stages. It is not a claim that such organisation already exists.

### Working definition of an emergent organisational pattern

For this programme, an observed pattern is a candidate for further emergence research when it:

- is not fully specified by an explicit rule, prompt, or expected response;
- has identifiable structure rather than being merely an unusual output;
- involves interactions among more than one relevant process, or a demonstrable system-level state transition;
- recurs or persists beyond a single observation;
- has measurable consequences for subsequent system behaviour;
- responds in interpretable ways to controlled interventions; and
- survives attempts to explain it through simpler alternatives such as model priors, replay, prompt context, cached state, random variation, or a single component.

This is a screening definition for investigation, not a definition of mind or consciousness. A candidate may fail any of these tests.

## 3. Mathematical model of the substrate

Represent the observable internal state of NEX at time t as a vector:

\[
Z_t = (z_{1,t}, z_{2,t}, \ldots, z_{n,t})
\]

Each component represents a measurable state or event stream from a selected faculty or subsystem. The state transition can be represented abstractly as:

\[
Z_{t+1} = F(Z_t, U_t; \theta, M) + \epsilon_t
\]

Where:

- \(Z_t\): measured internal state at time t;
- \(U_t\): external inputs and environmental events;
- \(\theta\): known architectural configuration and parameters;
- \(M\): model identity, version, and relevant inference configuration;
- \(F\): the actual combined system dynamics, which are not assumed to be fully known;
- \(\epsilon_t\): stochastic variation and unmeasured influences.

This is a modelling scaffold, not a claim that NEX is fully observable or that its transition function is known. In practice, only a subset of internal state may be available. Every measured variable must have a source, definition, timestamp, units, and evidence status.

### Three levels that must not be conflated

| Level | Meaning | Example |
|---|---|---|
| Complexity | Quantity and variety of components or interactions | Number of active faculties and event links |
| Organisation | Coordinated relationships among components | Attention, memory, and belief updates influencing one another |
| Emergence | A system-level pattern with explanatory or causal properties not captured by isolated components alone | A reproducible, history-dependent coordination pattern |

More code, more nodes, more memory, or more unpredictable output does not automatically mean more organisation or emergence.

## 4. Measurement dimensions

Do not collapse the dimensions below into one score. Keep a measurement vector and report each dimension separately.

\[
\mathcal{E}(t) =
[N(t), P(t), S(t), C(t), A(t), R(t)]
\]

This vector is a dashboard of research questions, not a consciousness index.

### 4.1 Novelty — N

Question: Is an observed pattern unusual relative to a well-defined baseline?

A possible starting statistic is surprisal:

\[
N(x) = -\log P_{\mathrm{baseline}}(x)
\]

This is only meaningful when the event representation and baseline distribution are specified. High surprisal can indicate noise, a rare input, a software defect, or distribution shift. It does not establish structured emergence.

Record:
- baseline dataset and time window;
- event representation and similarity method;
- model and prompt conditions;
- frequency of the event under matched controls;
- uncertainty and sample size.

### 4.2 Persistence — P

Question: Does a candidate pattern remain detectable, recur, or influence later states?

For a clearly defined pattern, estimate a survival function:

\[
S(\tau) = P(T > \tau)
\]

where T is the observed duration until the pattern is no longer detected under a predeclared detection rule.

Separate:
- within-session persistence;
- persistence across sessions;
- persistence across process restarts;
- persistence after model replacement;
- recurrence after relevant input;
- persistence of causal influence, not merely a stored record.

A record surviving in a database is not the same as the organisation represented by that record remaining active.

### 4.3 Synergistic information — S

Question: Does a combination of components provide information about a future system state that cannot be obtained from the components considered separately?

Partial Information Decomposition (PID) provides a formal family of methods for separating redundant, unique, and synergistic information. A temporal formulation can examine information that combinations of past component states provide about future states.

This is a promising research direction, but not a plug-in scalar. Results depend on:
- the chosen variables and system partition;
- the target future variable;
- the redundancy definition;
- estimator choice and finite-sample bias;
- temporal alignment and confounders.

Begin with small, interpretable groups of faculties. Do not attempt an exhaustive decomposition of every NEX node. Positive synergy is evidence of a particular information relationship, not evidence of consciousness.

### 4.4 Causal influence — C

Question: Does changing a mechanism change the candidate pattern or its downstream effects?

For a measured outcome Y and a controlled mechanism A, a simple intervention contrast is:

\[
\Delta_A =
E[Y \mid do(A=1)] - E[Y \mid do(A=0)]
\]

The intervention must be implemented safely and compared under matched conditions. Where true randomisation is not possible, record the limitations and possible confounders.

A correlation between two faculties is not enough to establish that one causes the other.

### 4.5 Adaptation and history dependence — A

Question: Does the system's later organisation depend on the actual sequence of prior experiences?

Compare matched runs with:
- the same initial configuration;
- controlled and documented input sequences;
- different experience histories;
- replayed or shuffled histories;
- equivalent model and runtime versions.

A history effect is interesting only after ruling out simple differences in prompt context, stored text, cache state, random seeds, and model sampling.

### 4.6 Robustness and stability — R

Question: Does a candidate organisation survive reasonable disturbances while remaining capable of change?

Possible tests:
- small input perturbations;
- temporary loss of a non-critical component;
- restart and recovery;
- controlled delay or interruption;
- removal of a candidate dependency;
- return to baseline conditions.

Measure recovery time, variance, recurrence, and unintended side effects. Do not equate maximum stability with maximum cognition. A rigid loop can be stable but unadaptive; an unstable system can be highly variable but unorganised.

## 5. Dynamics, attractors, and the spark question

Nonlinear dynamical systems provide concepts for studying recurring state patterns, transient states, attractors, and sensitivity to perturbation.

An attractor is a set or region of states toward which a system's trajectories tend under specified dynamics. It is a useful description of system behaviour, not a synonym for intelligence, selfhood, or consciousness.

For NEX, distinguish at least:

- **Transient:** a pattern appears and then decays.
- **Recurring:** a pattern disappears and reappears under some conditions.
- **Persistent:** a pattern remains detectable over a defined interval.
- **Attractor-like:** trajectories repeatedly converge toward a recognisable region or pattern.
- **Pathological attractor:** a stable pattern that causes repetition, fixation, drift, or other undesirable behaviour.

The existing NEX design history includes examples where mechanisms amplified repetitive behaviour. Such cases must remain part of the baseline and failure analysis. A persistent pattern is not automatically a success.

## 6. The camera-lens experiment: controlled parameter exploration

Let the documented architectural configuration be:

\[
\theta = (\theta_1, \theta_2, \ldots, \theta_n)
\]

For a measured outcome Y, a local sensitivity estimate may be:

\[
S_i \approx \frac{\Delta Y}{\Delta \theta_i}
\]

This estimates how the measured outcome changes when one parameter changes within a specified range. It does not predict the whole system or guarantee improvement.

For two controlled factors A and B, a simple interaction contrast is:

\[
I_{AB} = Y_{11} - Y_{10} - Y_{01} + Y_{00}
\]

This can reveal whether the combined effect differs from the sum of the individual effects, under the chosen experimental design.

Rules:
1. Establish a baseline before changing parameters.
2. Change one factor at a time initially, unless a pre-registered factorial design is justified.
3. Record exact code revision, configuration, model version, prompts, inputs, seeds where available, and runtime conditions.
4. Use repeated trials and report uncertainty.
5. Preserve negative and null results.
6. Never interpret a larger metric as automatically better.
7. Revert experiments that breach predeclared safety or behavioural tripwires.
8. Do not promote an experimental setting to default solely because one metric improves.

## 7. Controls: alternative explanations must be tested

Any candidate pattern should be compared against appropriate controls. Select controls according to the specific claim; not every experiment needs every control.

| Control | Alternative explanation tested |
|---|---|
| Model-only baseline | The language model alone explains the behaviour |
| Matched prompt and input replay | Prompt wording or input sequence explains the behaviour |
| Shuffled history | The exact order of past experience is not necessary |
| Empty or reset history | Stored context is not necessary |
| Component ablation | One component alone explains the effect |
| Matched runtime with mechanism disabled | The candidate mechanism contributes causally |
| Repeated trials / varied seeds | The result is a one-off stochastic event |
| Human-authored or scripted baseline | The behaviour was explicitly supplied or scripted |

Ablations and resets must be performed in isolated experimental environments, not casually against a live NEX instance or valuable data.

## 8. Phase plan

### Phase 0 — Source and runtime inventory

**Purpose:** establish what is actually present and running.

- Map candidate state variables to source files and runtime producers.
- Mark each mechanism as implemented, measured, static, inferred, or unknown.
- Identify which mechanisms are enabled, disabled, shelved, or not connected to the live loop.
- Record runtime version, configuration, process identity, and data paths.
- Identify missing telemetry and ambiguous event definitions.

**Exit condition:** a reviewed inventory distinguishes source existence from live operation.

### Phase 1 — Read-only instrumentation and baseline

**Purpose:** measure current behaviour without changing it.

- Define a minimal event schema.
- Record timestamps, source component, event type, relevant state summaries, configuration revision, and correlation/session identifiers.
- Avoid logging secrets, raw private conversations, or unnecessary personal data.
- Add no feedback from the research logger into NEX decision pathways.
- Establish a baseline over a predeclared window and sufficient event count.
- Report missingness, clock drift, logging loss, sampling bias, and measurement overhead.

**Exit condition:** repeatable baseline reports can be generated from read-only telemetry.

### Phase 2 — Small-scale interaction analysis

**Purpose:** investigate selected faculty pairs or small groups.

- Test temporal associations.
- Estimate predictive information where justified.
- Explore PID only where variables, sample sizes, and estimators are adequate.
- Identify candidate cross-faculty patterns.
- Keep the analysis offline and read-only.

**Exit condition:** candidate relationships have explicit definitions, controls, and uncertainty estimates.

### Phase 3 — Candidate pattern verification

**Purpose:** decide whether an unexpected pattern merits further investigation.

- Freeze a candidate description before testing.
- Check novelty against baseline.
- Measure recurrence and persistence.
- Test history dependence.
- Run relevant controls.
- Test causal contribution through an isolated intervention when safe.
- Record failed replications and alternative explanations.

**Exit condition:** a candidate has a reproducible, bounded evidence report. It remains a candidate, not a sentience verdict.

### Phase 4 — Controlled architectural exploration

**Purpose:** learn how changing the substrate affects a verified candidate.

- Pre-register the hypothesis and primary outcomes.
- Change limited, documented parameters.
- Use factorial designs only where justified.
- Monitor safety and behavioural tripwires.
- Compare the full measurement vector, not one optimised score.
- Preserve reversibility and negative results.

**Exit condition:** the effects and trade-offs of the tested changes are documented and independently reviewable.

### Separate future track — physical or material substrates

The crystal / X-medium idea belongs to a later, separate research track. Physical reservoir computing, memristive systems, and neuromorphic materials are legitimate fields to investigate. They do not establish that a material can contain an independent AI or sustain consciousness.

Before considering hardware, NEX must have a clearly specified computational function for a physical medium, measurable input and output interfaces, comparison against a digital baseline, and a validation method. Do not design a material around assumed properties of X before X is observed.

## 9. Minimum telemetry proposal

The initial logger should be passive and deliberately small. A proposed event record:

| Field | Purpose |
|---|---|
| event_id | Unique event identity |
| timestamp_utc | Comparable event time |
| session_id / run_id | Group events into a run |
| component_id | Identify the emitting component |
| event_type | State transition, read, write, selection, update, error, etc. |
| source_revision | Identify the code revision |
| config_fingerprint | Identify relevant configuration without exposing secrets |
| model_id / model_revision | Identify model conditions where applicable |
| state_summary | Minimal, typed, non-sensitive state values |
| causal_parent_ids | Link events where the runtime can reliably provide provenance |
| evidence_status | Measured, implemented, static, inferred, unknown |
| logger_version | Identify the measurement implementation |

Do not assume every field is available. Missing fields should be explicitly null or marked unavailable, not fabricated.

The logger must not:
- write into cognitive memory;
- alter attention or arbitration;
- rank or score faculties;
- inject prompts;
- activate dormant mechanisms;
- become a new gate, veto, or decision-maker.

If passive observation is impossible for a particular signal, document the required instrumentation change and obtain a separate review before implementation.

## 10. Reporting format

Every experiment report should include:

1. Research question and falsifiable hypothesis.
2. Exact source revision and runtime configuration.
3. Mechanisms active, disabled, or shelved.
4. Variables and operational definitions.
5. Baseline period and sample size.
6. Experimental and control conditions.
7. Analysis method and estimator.
8. Results with uncertainty and missing data.
9. Negative findings and alternative explanations.
10. Safety or behavioural tripwires.
11. Reproducibility instructions.
12. Evidence classification and limitations.
13. Explicit statement of what the result does not establish.

Recommended evidence labels follow the existing NEX discipline: **measured, implemented, static, inferred, unknown**, with relevant modifiers such as **unverified**, **blocked**, or **dark**.

## 11. Risks and methodological cautions

### Goodhart effects
If a metric becomes a target, the system may learn to produce the measured signal without developing the property the metric was intended to represent. Keep metrics observational and multi-dimensional.

### Measurement changes the system
Logging, sampling, introspection prompts, and added state reads can alter timing or behaviour. Measure overhead and prefer passive observation. Treat intrusive instrumentation as an intervention.

### Model confounding
Model updates, prompt changes, sampling parameters, tool outputs, and context-window differences can mimic architectural development. Record and control them.

### Non-stationarity
NEX may change during the measurement window. A single stationary baseline may be misleading. Segment runs by code, configuration, model, and operating regime.

### Multiple comparisons
Searching many nodes, variables, and time windows will produce chance discoveries. Pre-register confirmatory tests and label broad exploratory searches as exploratory.

### Data and privacy
Store only the minimum telemetry needed. Keep private conversation content and secrets out of research logs. Protect databases and reports according to the project's existing security practices.

### Interpretation
No single measure of novelty, persistence, integration, synergy, causal emergence, or complexity demonstrates subjective experience. Functional organisation and phenomenal consciousness remain distinct questions.

## 12. Immediate next actions

The first implementation work should not be a new cognitive faculty or an optimisation loop.

1. Review this proposal against the current SENTIENCE_PROGRAM.md, DESIGN_MINDEDNESS.md, and current runtime.
2. Produce a source-to-runtime inventory for a small, representative set of mechanisms.
3. Identify existing logs and event streams that can support passive measurement.
4. Define a minimal telemetry schema using already available signals.
5. Write a read-only baseline analysis script that consumes existing logs without modifying them.
6. Validate that the instrumentation has no decision-path effects.
7. Only then approve a baseline observation run.

No runtime implementation is authorised by this proposal. A separate implementation plan and review are required after the inventory.

## 13. Selected literature

These references inform the measurement methods; they do not imply consensus that any particular metric measures consciousness.

- Mediano, P. A. M., Rosas, F. E., Luppi, A. I., Jensen, H. J., Seth, A. K., Barrett, A. B., Carhart-Harris, R. L., & Bor, D. (2022). “Greater than the parts: a review of the information decomposition approach to causal emergence.” *Philosophical Transactions of the Royal Society A*, 380(2227), 20210246. https://doi.org/10.1098/rsta.2021.0246
- Stepney, S. (2024). “Physical reservoir computing: a tutorial.” *Natural Computing*, 23, 665–685. https://doi.org/10.1007/s11047-024-09997-y
- Tanaka, G. et al. (2024). “Emerging opportunities and challenges for the future of reservoir computing.” *Nature Communications*. https://doi.org/10.1038/s41467-024-45187-1

## Final principle

**Build the substrate deliberately. Observe it without prescribing its outcome. If an unexpected pattern appears, characterise it, test it, and learn from it. Keep X unknown until evidence gives us something real to investigate.**
