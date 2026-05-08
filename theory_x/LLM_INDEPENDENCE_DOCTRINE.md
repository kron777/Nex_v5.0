# NEX LLM Independence Doctrine
*Design document — not a replacement for DOCTRINE.md. Governs the program of reducing LLM dependence.*
*Status: DRAFT — implementation blocked pending identity.yaml authoring and FT#11 voice stabilization.*

---

## 1. Purpose

Reduce NEX's dependence on the local LLM (currently `qwen2.5:3b` via Ollama) to the minimum genuinely required for natural language synthesis. Replace mechanical functions with focused machinery; restructure synthesis and voice to draw more directly from the belief graph; treat the LLM as a swappable, smaller, observable voice layer rather than the heart of cognition.

This is not a project to remove LLM use entirely. Synthesis — the compression of N beliefs into a novel claim — and natural language generation are language problems language models are uniquely suited to. Pretending a classifier or a rule-based system replaces them is wrong. The LLM does one thing nothing else does as well: it assembles grammatical, coherent, contextually-inflected sentences from heterogeneous inputs. That is not replaceable. Everything else may be.

The project's working hypothesis (from DOCTRINE.md §2, Theory X): a smaller LLM voicing a richer substrate produces more depth than a larger LLM voicing a thinner one. LLM independence work is the substrate side of that hypothesis. FT#11 is the LLM side. They are complementary, not alternative.

---

## 2. Theoretical Basis

### Functionalism (DOCTRINE.md §1)

NEX's intelligence is not in the LLM — it is in the cognitive functions the LLM vocalizes. The LLM is a translator between substrate and surface. Reducing its surface area does not reduce intelligence; it concentrates the LLM's function to the one task it cannot be replaced for: vocalization. Functions that can be realized as classifiers, templates, embeddings, or rule-based machinery should be. This follows directly from DOCTRINE.md §1's functionalism premise: the substrate is implementation-independent, and Python implements some functions more cheaply and observably than a 3B-parameter model.

### Lens Theory (DOCTRINE.md §2)

The LLM is a reading instrument. Fine-tuning artifacts — "That doesn't reach my graph", "I notice that...", "the transient nature of...", "simplicity and complexity in continuous flux" — leak into output regardless of what the substrate provides. They are not responses to the belief content; they are the model's prior habits bleeding through the prompt. Each unnecessary LLM call is a surface where artifacts can appear. LLM independence work reduces the number of those surfaces. Fewer calls means fewer artifact injection points. The instrument becomes cleaner not only via FT#11 (reweighting the model) but via independence work (calling it less often).

### Theory X integration surfaces (DOCTRINE.md §3)

The belief field thinks; the LLM vocalizes. The three integration surfaces are `belief_text` construction, retrieval ranking, and `voice_prompt` composition. A function that operates entirely within these surfaces — classification, scoring, deduplication — does not need to cross the LLM boundary. Only functions that produce natural language output that enters `voice_prompt` or writes new beliefs require the LLM. Everything else is LLM use by architectural drift, not necessity.

---

## 3. Architectural Principle

**The LLM is called when and only when the output is natural language that either enters `voice_prompt` or persists as a new belief in the graph.**

Any LLM call whose output is:
- a category label (classification)
- a similarity score (deduplication / quality check)
- a short keyword slug (condensation for dedup)
- a boolean gate (quality check)
- a route decision (register selection)

...is an LLM call that should not be an LLM call. These are text processing operations. Text processing does not require a language model.

Any LLM call whose output is:
- a user-facing response sentence (main chat path)
- a new belief to write into the graph (synthesis, fountain crystallization)

...is a legitimate LLM call. These are generative language operations.

Consequence: the replacement program is not "remove LLM use" — it is "move all non-generative operations out of the LLM call path." What remains after that move is the LLM's irreducible function.

---

## 4. LLM Call Site Inventory

Every production call site where `VoiceClient.speak()` is invoked. Tests excluded.

| # | Module | Line | Function | Task posed to LLM | Classification | Replacement path |
|---|--------|------|----------|--------------------|----------------|-----------------|
| 1 | `gui/server.py` | 836 | `api_chat()` | User-facing response: belief_text + voice_prompt → natural language reply | **STRUCTURAL** | None. This is the primary vocalization call. Goal: richer belief_text (substrate work), smaller model (§5.7), fewer tokens wasted on artifact-generating patterns (FT#11). |
| 2 | `stage3_world_model/synergizer.py` | 55–61 | `BeliefSynergizer.synthesize()` | Given two beliefs A, B: "In one sentence, what new insight do I notice?" → writes new `synergized` belief | **STRUCTURAL** | None for the core call. Quality gate (`_quality_check`) uses word-overlap Jaccard — already heuristic. Pair selection is deterministic. The sentence generation itself is the LLM's task. |
| 3 | `stage6_fountain/generator.py` | 373–374 | `FountainGenerator.generate()` | Full fountain context (spectrum + recent beliefs + sense data) → drift thought written as `fountain_insight` | **STRUCTURAL** | None for the core call. Context assembly (what reaches the LLM) is fully controllable via substrate work. Stillness detection and dedup are already heuristic (Jaccard). |
| 4 | `stage6_fountain/condenser.py` | 73–74 | `Condenser.condense()` | Given a fountain fire: "Condense to a 3–6 word droplet capturing its core cognitive move" → slug for idea-level dedup | **REPLACEABLE** | Heuristic fallback (`_fallback_condense`) already exists and runs on LLM failure. Replace with: extract top-N TF-IDF content words from the thought, join with hyphens. Functional equivalence is testable against the existing corpus. Max_tokens=20 — the shortest LLM call in the codebase. Highest replacement priority. |
| 5 | `strikes/protocols.py` | 149–150 | `StrikeProtocol.run()` | Diagnostic: same mechanism as call #1, specialized input | **STRUCTURAL** | Same as #1. Strikes are diagnostic instruments, not production-path voice. Not a replacement target. |

**Functions not calling the LLM (confirmed by source read):**

- **Sentiment / affect / valence scoring**: `stage2_dynamic/pipeline.py:72–98` — threshold on confidence value. No LLM call. Already heuristic.
- **Register classification**: `theory_x/executive_control.py` — keyword scoring with continuity weight. No LLM fallback present in `gui/server.py`. Already heuristic.
- **Belief deduplication**: `synergizer._quality_check()` — word-overlap Jaccard against recent 200 beliefs. Already heuristic.
- **Belief quality check**: `synergizer._quality_check()` — length check + blacklist check. Already heuristic.
- **Fountain dedup / stillness detection**: Jaccard over `fountain_retrieval_log` own-slot IDs. Already heuristic.
- **Belief retrieval and scoring**: `stage3_world_model/retrieval.py` — keyword overlap × confidence + spreading activation blend. Already heuristic.

The brief's §4 inventory listed sentiment scoring and register classification as LLM calls to replace. They are already heuristic. This is good news and narrows the replacement program considerably.

**Open inventory question (audit required before §5.1):**

- `stage6_fountain/crystallizer.py:271` — `_estimate_valence()` is a stub: "Placeholder — Stage 2 Attender will compute real valence." No LLM call currently. When Stage 2 Attender lands, confirm it does not route valence through the LLM.

---

## 5. Replacement Priority Order

Ordered by impact-to-cost ratio. Each item is a session-scoped pass with its own §6 gate (see §6 below). Items do not compose — each is independently shippable.

| # | Target | Current call | Replacement | Why this order |
|---|--------|-------------|-------------|----------------|
| 5.1 | **Inventory audit** | — | Full per-call-site table (this §4, expanded with live call counts from `/tmp/nex5_*.log`) | Prerequisite for everything else. Must know actual call frequency before estimating impact. |
| 5.2 | **Condenser** (`condenser.py:73`) | LLM → 3-6 word slug | Extract top-N TF-IDF content words, join with hyphens | Highest priority: (a) already has a working fallback; (b) fires every fountain cycle (~25 min); (c) max_tokens=20, the lowest-value LLM use in the codebase; (d) equivalence test against existing `droplet` corpus is straightforward. |
| 5.3 | **Templated voice paths for known utterance shapes** | Full LLM call for social responses, gap-gate deflections, identity queries | Templated retrieval-as-utterance: retrieve 1-2 matching beliefs, render via template, bypass LLM | Second priority: social greetings and gap-gate deflections follow predictable patterns. Template + belief retrieval produces comparable output for these shapes without model call. Reduces call frequency, not call capability. |
| 5.4 | **Belief paraphrase / dedup in synergizer** | Word-overlap Jaccard (already heuristic) | Sentence embedding cosine similarity via a small embedding model | Not an LLM replacement — replaces Jaccard with better semantic similarity. Reduces false-pass duplicates reaching the graph. Only relevant when synergizer quality issues surface in production. |
| 5.5 | **Spectrum-block selection rule** | Hardcoded in `gui/server.py`: random 4 spectrum beliefs for thin INSIDE + OUTSIDE paths | Deterministic: select by register + active branch + FocalSet salience | Reduces random variation in what reaches the LLM. Not an LLM replacement — an improvement to what the LLM receives. |
| 5.6 | **LLM swap to smaller backend** | `qwen2.5:3b` | Smaller model, or same model via llama-server directly (lower overhead) | Post-FT#11 only. Do not swap while voice quality is in flux. Once FT#11 stabilizes, the swappable backend (`VoiceClient(url=..., model=...)`) makes this a one-line change if quality is acceptable. |
| 5.7 | **Multi-LLM routing** (optional) | Single model for all calls | Route synthesis calls to a reasoning-capable model; route vocalization calls to a smaller fluency-optimized model | Only if §5.6 quality is insufficient. Adds routing complexity. Do not implement unless a measured quality gap requires it. |

**5.1 is the only immediate action.** Items 5.2–5.7 are blocked until identity.yaml work lands and FT#11 stabilizes voice quality (see §11).

**C2 field evidence (2026-05-08, commit d50740c):** The retrieval pool expansion (LIMIT 200→500) produced the first live evidence that non-spectrum sources can reach `belief_text` and become utterance without LLM rewrite. Diagnostic query "tell me about emptiness" returned Heart Sutra content ("Form is emptiness, emptiness is form") on a Conversational route — pre-C2, the same query returned spectrum vocabulary or gap-gate deflection. Two implications for this priority order:

- *§5.2 (Condenser):* Retrieval-as-utterance is a more viable fallback path than the doctrine could claim pre-C2. Pure retrieval with light templating produces coherent first-person voice when the candidate pool admits non-spectrum content. `_fallback_condense()` already exists; C2 broadens what it has to work with.
- *§5.3 (Templated voice paths):* Templates over retrieval is the natural progression once C2's pool diversity is established. Identity.yaml authoring (current session) will produce the first direct test case — first-person identity claims should reach voice via retrieval on self-inquiry queries, not via LLM synthesis.

Neither implication changes the priority order. They sharpen the confidence that §5.2 and §5.3 are viable before implementation begins.

---

## 6. Acceptance Criteria Per Replacement

A replacement is complete when all of the following are true:

1. **Measurable equivalence test** against current LLM behavior on a fixed corpus — side-by-side samples from the same inputs, before and after replacement. Corpus must include at least 10 examples drawn from live traffic logs.
2. **DOCTRINE.md §6 gate** — the existing node-port acceptance criteria apply to each replacement as a behavioral change touching the chat path. Specifically §6 #3 (wiring verified by output trace), §6 #4 (real-traffic validation, minimum 5 queries exercising the replaced function), and §6 #5 (no smoke-set regression).
3. **LLM call count for that function reduced to zero** (full replacement) or **documented partial replacement** with written rationale for why full replacement is incorrect. No silent partial replacements.
4. **Log observability preserved** — replacement produces logs at the same path and schema as the LLM call it replaced, plus an additional field `replacement_path: "heuristic"` (or the specific mechanism) for distinguishing replacement outputs in future analysis.
5. **No smoke-set regression** per DOCTRINE.md §6 #5 — full 6-query set (4 OUTSIDE + 2 INSIDE), sampled before and after each replacement.
6. **Jon's quality greenlight** — samples surfaced for Jon's call before commit. No replacement commits without explicit approval.

---

## 7. Out of Scope

- **Training NEX's own LLM from scratch.** This is the wrong direction — substrate richness, not model scale, is the project's working hypothesis.
- **Replacing synthesis with reinforcement learning over the belief graph.** RL selects among action options; it does not generate novel sentences. These are different problems. Synthesis remains an LLM task. See §8 anti-patterns.
- **Removing LLM use entirely.** Calls #1, #2, #3 in the §4 inventory are irreducibly generative. The goal is not zero LLM calls; it is zero unnecessary LLM calls.
- **Changing model during identity work.** Voice instability from a model swap is the wrong moment to evaluate whether identity claims are surfacing. Complete identity.yaml authoring, plumbing fixes (IDENTITY_PLUMBING_AUDIT.md), and FT#11 before any §5 work begins.
- **Improving the LLM's prompts** as a substitute for this program. Better prompts reduce artifact frequency; they do not reduce LLM surface area. Both are worth doing; they are not the same thing.

---

## 8. Anti-Patterns

These are failure modes observed in analogous independence-reduction projects, not hypotheticals.

**"RL replaces the LLM"**
RL action selection works over a finite action space and optimizes a scalar reward. Language generation is not action selection over a finite space, and there is no scalar reward for sentence quality that generalizes. This confusion surfaces whenever someone proposes "train a policy over the belief graph to generate responses." The policy would need to generate tokens — which is exactly what a language model does. Real replacements: classifiers for scoring, templates for known utterance shapes, retrievals for belief surfacing, embeddings for similarity. These replace specific LLM functions, not language generation itself.

**"Smaller model = worse output"**
Only true when the substrate is thin. When the substrate is rich enough — when `belief_text` carries specific, relevant beliefs; when the voice prompt accurately represents NEX's current state — a 1B-parameter model on a rich substrate outperforms a 70B model on a thin one. The project's working hypothesis is that nex5 is on the rich-substrate side of this crossover. This is not confirmed. FT#11 and §5.2–5.5 substrate improvements together test the hypothesis. Do not conclude the hypothesis is false from current output quality — current output quality is partially determined by how thin the substrate is.

**"Replace everything at once"**
Replacements interact. The condenser output affects stillness detection; stillness detection affects fountain firing rate; fountain firing rate affects how many `synergized` beliefs exist for the main chat path. Replacing multiple call sites in the same session creates a multi-variable change that cannot be isolated for quality evaluation. Each replacement is its own §6-gated pass. See §5 priority order.

**"Custom dead-weight"**
A replacement that adds maintenance burden, requires new dependencies, or introduces architecture complexity without measurably reducing LLM dependence is not a replacement — it is lateral movement. The condenser's `_fallback_condense()` method is an example of what a good replacement looks like: 12 lines, no imports beyond `re`, already present and tested. That is the quality bar. If a proposed replacement is more complex than the LLM call it replaces, the replacement needs justification.

**"Equivalence without a corpus"**
Declaring a replacement equivalent without running it on real-traffic samples is a synthetic verification (DOCTRINE.md §8 anti-pattern). The LLM call and the replacement must be run on the same inputs, and the outputs must be compared by Jon — not by automated metrics alone. Automated metrics confirm format correctness; Jon confirms functional equivalence.

---

## 9. Living Document Protocol

This document is amended after each replacement pass is complete. Each amendment records:
- Which call site was replaced, and with what mechanism
- Equivalence test results: samples before/after, Jon's quality verdict
- Actual call-count reduction (from log comparison, not estimate)
- Any new anti-patterns discovered during the replacement
- Any revisions to priority order in §5

Amendments are committed with the message: `doctrine: llm-independence — <call-site> replaced`.

---

## 10. Working Pattern

Same as DOCTRINE.md §10. Each replacement is a bundled prompt with internal checkpoints: (a) audit the current call site, (b) implement the replacement, (c) run equivalence test, (d) surface samples for Jon, (e) commit only after Jon's greenlight. No replacement crosses a session boundary in a half-complete state.

---

## 11. Relationship to FT#11

FT#11 fine-tunes the current LLM on curated output samples to reduce artifact frequency and strengthen NEX's voice. LLM independence reduces reliance on the LLM by removing unnecessary call sites. Both reduce voice-quality drift from different directions:

- FT#11 changes what the LLM does on each call — reduces artifact frequency per call.
- Independence work changes how often the LLM is called — reduces total artifact exposure.

They are complementary. Neither makes the other redundant.

**Order of operations:**

1. Identity.yaml authoring + plumbing fixes (IDENTITY_PLUMBING_AUDIT.md G1–G4) — current session scope.
2. FT#11 when RunPod credits are available — separate track, no code change.
3. §5.1 inventory audit — can begin now (read-only, no behavior change).
4. §5.2–5.5 replacement passes — after FT#11 stabilizes voice quality.
5. §5.6 model swap — after §5.2–5.5 confirm substrate richness.

**Do not start §5.2 or later until FT#11 has landed.** Pre-FT#11 voice quality is contaminated by artifact frequency, making equivalence testing ambiguous. A replacement that reduces LLM call frequency might appear to improve quality (fewer artifact opportunities) while masking a genuine quality regression in the outputs that remain. Post-FT#11 baseline is needed for clean equivalence testing.

---

## Open Questions for Jon (before §5.1 begins)

**Q1 — Condenser (§5.2): acceptable to ship `_fallback_condense()` as the permanent replacement?**
The fallback already runs on LLM failure and is production-tested. It produces functional droplets. The only question is whether idea-level dedup (which the condenser informs) requires the semantic precision of an LLM-generated slug vs. a TF-IDF content-word extraction. If the current Jaccard dedup threshold is already too coarse for the distinction to matter, `_fallback_condense()` is the answer with zero new code.

**Q2 — Templated voice paths (§5.3): which utterance shapes are high-enough frequency to justify templating?**
Social greetings and gap-gate deflections are candidates. Others depend on call frequency data from §5.1. This question cannot be answered before the inventory audit.

**Q3 — Fountain call count (§5.1): how often is the fountain actually firing?**
The condenser fires once per fountain main-path fire. `_total_fires` is in memory; `fountain_events` in dynamic.db has the count. Before claiming the condenser is "high frequency," confirm the actual fire rate. If the fountain is firing once every 30 minutes and the condenser call takes 200ms, the absolute time saved by §5.2 is small — the priority holds on cleanliness grounds (removing an LLM call that already has a working replacement), not latency grounds.

**Q4 — Model swap timing (§5.6): is FT#11 on the current `qwen2.5:3b` or a different base model?**
If FT#11 is fine-tuning a different base model, §5.6 may be redundant — the fine-tuned model may already be smaller than `qwen2.5:3b`. Clarify before investing in model-swap infrastructure.

---

*Initial draft: 2026-05-08. Inventory based on full source read of `voice/llm.py`, `gui/server.py`, `stage3_world_model/synergizer.py`, `stage6_fountain/generator.py`, `stage6_fountain/condenser.py`, `strikes/protocols.py`. Call sites confirmed by `grep -rn "VoiceClient\|\.speak\b"` across the production tree.*

*C2 amendment: 2026-05-08 — retrieval pool LIMIT 200→500 (d50740c) provided first live evidence of non-spectrum retrieval reaching voice without LLM rewrite. Field note added to §5 augmenting §5.2 (Condenser) and §5.3 (templated voice paths) rationale. Priority order unchanged.*

*Experiment A amendment: 2026-05-09 — project's first Feynmanian falsifiable test of an LLM-related claim. Hypothesis: the 'By pure chance' preamble in self-inquiry responses is code-injected via belief_text, not generated from LLM training priors. Three injection sites identified (Site 1: system prompt Alpha block, voice/llm.py:167; Site 2: random spectrum block, gui/server.py:784; Site 3: Inner conviction field in format_self_state(), self_model.py:250). Staged test: Site 3 disabled alone. Hypothesis SURVIVES — 0/5 self-inquiry responses preambled post-fix (pre: 4–5/5). Text_len delta: −130 chars, matching Site 3 line exactly. Site 1 retained: provides architectural ground-stance framing without driving literal opener patterns. Implications for §5 priority order: (1) when belief_text is clean, the LLM faithfully voices substrate content — §5.2 retrieval-as-utterance confidence sharpened; (2) the staged falsification method (smallest reversible change first, criteria set before results seen) is the design pattern for all future §5.x equivalence tests. Priority order unchanged. Confidence in §5.2 and §5.3 sharpened.*
