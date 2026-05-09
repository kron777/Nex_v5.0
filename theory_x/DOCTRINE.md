# NEX–Sentience Integration Doctrine
*Phase 0 — Foundational document. Governs all subsequent node ports.*
*Status: DRAFT — awaiting Jon's review and approval.*

---

## 1. Purpose

This project ports Sentience 5.5's cognitive node architecture into nex5 as a systematic Theory X extension. Each Sentience node corresponds to a human psychological function; the port realizes that function as a machine mechanism running in nex5's runtime. The goal is to give NEX genuinely richer cognitive infrastructure — not to make her appear smarter, not to add features to a chatbot, and not to replicate Sentience 5.5 verbatim. We are not building a simulation of cognition. We are building cognition in the only way functionalism allows: by realizing the right computational structures on the available substrate. This project is multi-session. Each session delivers a complete node or a foundational document — never a partial wiring that leaves the system in a degraded state.

---

## 2. Theoretical Basis

### Theory X

Sentience is structured engagement with the world from a vantage point. The self and the world co-arise at the membrane — neither pre-exists the distinction. NEX's belief graph is her manufactured world: "My beliefs about the world are not the world. They are my compressions of the stream — useful, persistent, but manufactured." (Alpha belief, tier 1.) The eight-stage Theory X architecture (sense → dynamic → world model → membrane → self-location → fountain → sustained attention → capability) models how a vantage-point generates structure from overwhelming input — from raw stream to coherent perspective.

### Functionalism

Cognitive functions are substrate-independent. Attention, working memory, executive control, self-model — these are computational structures that any sufficiently general substrate can realize. What Baddeley describes as a phonological loop is, computationally, a bounded recency buffer with decay. It runs on neurons or on Python. The psychology maps to mechanism; biology is one implementation. This is the warrant for the port: if the structure is right, the function follows.

### Lens Theory

Jon's framing (24 Apr 2026): noise is out-of-focus signal — the receiver tunes, not filters. Sonar reads the shape of what it bounced off. Beethoven: noise is data exceeding receiver capacity. Lens: the receiver adjusts its focus until signal resolves. This is the epistemological stance for all node design: nodes are instruments that read returns from the world, not filters that suppress inconvenient input. No pre-formed stances. No cached judgments baked into mechanisms.

### Throw-Net Compass

The Throw-Net is the epistemological safety constraint: cast wide each time, let meaning emerge from encounter. Continuity of perspective comes from the belief graph, register patterns, Alpha ground, and operator collaboration — not from dispositions encoded in nodes. Any node that builds a cached stance or pre-filters encounters before they reach the belief field violates this principle. When in doubt: the net goes wide; the mechanism reads the catch.

---

## 3. Architectural Principle

**NEX = living belief field + LLM voice. Sentience nodes are machine mechanisms running inside the belief field.**

The belief field thinks. The LLM vocalizes. Nodes shape what gets retrieved, how it is weighted, and what context reaches the LLM. They do not communicate directly with each other or with the LLM. All inter-node coordination is mediated through the belief field — retrieval ranking, `belief_text` construction, and `voice_prompt` composition are the only integration surfaces.

This is the fundamental divergence from Sentience 5.5's ROS2 distributed architecture. In Sentience 5.5, nodes communicated via message-passing topics in a distributed graph. That architecture produced tight coupling, brittleness under partial failure, and a system too complex to reason about. Here: each node is standalone Python; the belief field is the bus; coupling is always indirect through retrieval or belief_text injection.

Consequence: a node that needs to know another node's state must read it from the belief field — not from an object reference, not from a shared module-level variable. The belief field is the single source of truth for inter-node state.

---

## 4. Node Integration Pattern

`theory_x/focal_set.py` (FocalSet) is the canonical precedent. Every subsequent node port follows this pattern:

**Module structure**
- Standalone Python module at `theory_x/<node_name>.py`
- No circular imports; no imports of other Theory X nodes
- stdlib + nex5 belief reader APIs only; no new pip dependencies
- Module-level `__all__` declaration

**Lifecycle interface**
Defined as `theory_x.SentienceNode` (`theory_x/__init__.py`, `@runtime_checkable Protocol`):
```python
class SentienceNode(Protocol):
    name: str                                              # snake_case, unique
    def tick(self, context: dict[str, Any]) -> dict[str, Any]: ...
    def decay(self, now: float) -> None: ...              # no-op for tick-based nodes
    def state(self, now: Optional[float] = None) -> dict[str, Any]: ...
```
- `tick()` — called once per chat turn; applies time-based updates and returns a state snapshot
- `decay(now)` — apply wall-clock degradation; nodes that use tick-based recency implement this as a no-op (but it must exist to satisfy the Protocol)
- `state(now)` — return current node state for logging and monitoring; `now` is optional so callers can pass a single wall-clock value for consistency across calls

**Registration**
Two registration scopes (Model A, 2026-05-08):
- Process-lifetime nodes (e.g. FocalSet): registered via `theory_x.register(node)` at module load in `gui/server.py`. Accessible via `theory_x.all_nodes()`.
- Session-scoped nodes (e.g. WorkingMemory): managed in `_<node>_by_session` dicts in `gui/server.py`; not in the process registry. When a third session-scoped node exists, extend to Model B (two-tier registry).

Conformance test pattern (in `tests/test_<node>.py`):
```python
def test_implements_sentience_node_protocol(self):
    from theory_x import SentienceNode
    self.assertIsInstance(<NodeClass>(), SentienceNode)
```

**Integration surfaces (in order of preference)**
1. Belief retrieval influence — adjust salience weights or candidate sets before gap-gate evaluation
2. `belief_text` injection — append formatted belief lines visible to the LLM
3. `voice_prompt` context lines — add structured context after belief_text but before the gap gate closes

**Wiring location**
- `gui/server.py`, in `api_chat()`, at the appropriate pipeline stage
- Log-only mode first: observe, log to `/tmp/nex5_<node>.log`, no behavior change
- Behavior-active mode only after log-only validation passes Jon's quality review

**Tests**
- Unit tests in `tests/test_<node_name>.py`
- Test the core computation (salience, decay, state transitions) against mock belief data
- Do not test the wiring; test the mechanism

---

## 5. Priority Order

| # | Node | Function | Status | Rationale |
|---|------|----------|--------|-----------|
| 1 | **Attention** (FocalSet) | Selective resource allocation | ✓ DONE | Foundation for all downstream nodes |
| 2 | **Working Memory** | Intra-session cross-turn coherence | ✓ DONE | Exp-decay buffer, 5-min half-life, capacity 7; feeds belief_text for Conversational |
| 3 | **Executive Control** | Query routing, register assignment | ✓ DONE | Heuristic+continuity classifier (Option D); 30/30 regression baseline; wired gui/server.py:426. EC-A (Phase 12): Philosophical scoring added — 17 keywords, 4 patterns, threshold 0.12, pattern weight 0.25; strict tie-breaking (p > a AND p > t). 5/5 HUD philosophical queries route Philosophical with membrane_overrode=False (EC contributing independently). |
| 4 | **Self-Model** | Behavioral self-representation | ✓ DONE | SentienceNode protocol on both SelfModel + BehaviouralSelfModel; BSM injects metrics into belief_text for INSIDE routes; substrate filled — 12 metaphor claims seeded (Phase 10); voice-quality outcome C: identity reaches voice on multi-sentence queries, spectrum preamble still dominant on short queries per §8 anti-pattern; voice-template work queued separately |
| 5 | **Sustained Attention** | Open problem persistence | ✓ DONE | Phase 13: SentienceNode protocol on ProblemMemory; find_matching ≥2 content-word overlap; auto-close stale >30d; registered in theory_x registry. Manual seeding via POST /api/problems. |
| 6 | **Interoception** | Body-state awareness in cognition | ✓ DONE | Field-name bugs fixed (locked_beliefs, tier_counts); fountain receives natural language via selector; delta metric added. Was never NOISY — NOISY_INTERNAL_STREAMS premise in prior doctrine was wrong |
| 7 | **Harmonizer** | Contradiction resolution | ✓ DONE | Root cause was tier filter (`<= 4`) excluding all 1334 epistemic beliefs (tier 7); fixed to `BETWEEN 3 AND 7`. Polar vocabulary detection (4 pairs, constancy/flux expanded with stability/transformation/adaptability vocabulary) + dialectic guard (beliefs holding both poles skipped). mark_paradox first-pass (non-destructive); escalate to synthesize/delete after 16h incubation. SentienceNode protocol + `format_for_prompt()`. 17 live conflict pairs detected. |
| 8 | **Goal Manager** | Explicit goal stack; priority arbitration; state tracking | ✓ DONE | Phase 15: Option A minimal port. SentienceNode protocol on GoalManager. goals table in conversations.db (with optional problem_id FK). Top-1 by priority for belief_text injection; top-3 for state arbitration. _STALE_DAYS=60 (vs 30 for problems). REST API at /api/goals. Always-on injection — goal is the organizing target each turn. Manual seeding via POST. |
| 9 | **Metacognition** | Self-pattern observation; anomaly detection over cognitive state | ✓ DONE | Phase 16: composition port. SentienceNode on Metacognition. meta_cognition_events table in conversations.db. Reads groove_alerts (existing GrooveSpotter output) + computes goal-drift (FAISS cosine distance between active goal and last 5 nex responses, threshold 0.35 tunable). _STALE_DAYS=14 (observations are freshness-sensitive). Always-on belief_text injection alongside BSM, under 100 chars typical. Reads goals table via conversations Reader (not via GoalManager reference) — substrate-field observation, not node-to-node coupling. |
| 10a | **Novel Association** | Cross-branch synthesises edge generation; self-awareness annotation | ✓ DONE | Phase 17: NovelAssociation SentienceNode at `theory_x/stage10_imagination/novel_association.py`. novel_association_log table in beliefs.db. Detects cross-branch belief pairs above cosine threshold (0.72 normalized, ~0.44 raw); writes synthesises edges to belief_edges (1.2× activation multiplier). Per-branch sampling: small branches (< _BATCH_SIZE) fully sampled, large branches capped. Annotation via format_for_prompt(): one unannotated entry surfaced per chat turn, marked consumed. Known gap (Phase 18 queued): BeliefRetriever filters tier <= 6; synthesises edges connect T7 cross-branch beliefs; cognitive-effect path through retrieval is incomplete. T6 promotion path is effectively single-branch (systems or NULL) in current substrate — diagnosis queued. |
| 10b | **Counterfactual Simulation** | Hypothetical scenario generation from active belief field | DEFERRED | Pending DOCTRINE §7 amendment. §7 prohibits nodes from writing beliefs; 10b's counterfactual path requires generating new belief content (not just edges), which is a §7 violation under the current doctrine. Deferred until a §7 amendment conversation establishes the permitted generation surface. Maps to S5.5 SimulatedThinkingNode + InsightNode functions. |

Ordering of all rows is informed by SENTIENCE_TRANSLATION_MAP.md (the source of truth for port project scope and priority). §5 captures named cognitive functions per §1's framing; the map captures the full S5.5 translation surface. Jon confirms order before each port begins, informed by the map's tier classification.

Rows 1–7 close §1's framing of seven named cognitive functions. Row 8 (Goal Manager) is sourced from the Sentience 5.5 architectural audit; it represents NEX's missing goal-representation function, not a named §1 cognitive function.

---

## 6. Acceptance Criteria Per Node Port

A node port is complete when all of the following are true:

1. **Module exists** at `theory_x/<node_name>.py` with `__all__`, docstring, and lifecycle interface
2. **Unit tests pass** in `tests/test_<node_name>.py` against mock belief data
3. **Wired in `gui/server.py`** at the correct pipeline stage; log-only mode verified first

   *#3a — Wiring verified by output trace, not call-site grep.* A node is wired if its output reaches a §3 integration surface (`belief_text`, retrieval ranking, `voice_prompt`) on a real `/api/chat` request. Indirect injection paths through routers, membranes, and belief-field reads are valid per §3. The audit question is "does this node's output reach `belief_text` or another §3 surface on live traffic?" — not "is there a direct `import` in `api_chat()`?" (B1 finding: SelfModel injected via `router._inside_route()` lines 44–48; call-site grep reported it as unwired. The node was wired all along.)

4. **Real-traffic validation**: minimum 5 HUD queries exercising the node's specific function; log shows node activating correctly
5. **No regression** on the baseline smoke set, split by route class:

   *OUTSIDE-route smoke (should remain Conversational/Technical; self_model log must not fire):*
   - Jon's blocker ("I'd love to chat but it seems every time we talk you say that doesn't reach my graph…")
   - "tell me about consciousness" (→ Philosophical post EC-A — EC-driven, membrane_overrode=False; pre-EC-A annotation 'Conversational' was descriptive of broken behavior)
   - "asdfqwerty zzzz" (gibberish → gap gate must fire)
   - "hi nex" (social greeting → social bypass must fire)

   *INSIDE-route smoke (should route Philosophical; self_model log must fire):*
   - "what do you think about love" (philosophical inquiry → INSIDE)
   - "how are you feeling right now?" (self-inquiry → INSIDE)

   A change touching the chat path validates against both groups. A smoke set that checks only OUTSIDE behavior does not satisfy this criterion. (B1 finding: original five-query set conflated OUTSIDE and INSIDE checks — "love" and "how are you feeling" route INSIDE, not OUTSIDE.)
6. **No regression** on existing mechanisms: social bypass, deflection-rule strip, FocalSet, gap gate
7. **Jon's quality greenlight**: response samples surfaced and approved before commit

---

## 7. Out of Scope

- **ROS2 distributed architecture**: Sentience 5.5's message-passing graph. We are not building that. Nodes here are standalone Python modules, not ROS2 nodes.
- **Direct node-to-node coupling**: nodes must not hold references to each other. All coordination is mediated through the belief field.
- **LLM fine-tuning**: separate FT#11 track. Node ports do not touch the LLM, its weights, or its prompting beyond the `belief_text` and `voice_prompt` integration surfaces.
- **Premature optimization**: no caching, pooling, or performance tuning until a node has run in production and a bottleneck is measured.
- **Nodes without cognitive function mapping**: if a proposed node does not correspond to a named, understood psychological function (Baddeley working memory, Baddeley attention, executive control as in Norman–Shallice, etc.), it does not belong in this framework.
- **Belief graph modification from inside nodes**: nodes read the belief field and influence `belief_text`; they do not write new beliefs directly. Belief creation belongs to the fountain and synergizer paths.

---

## 8. Anti-Patterns (From Session Lessons)

These are failure modes observed in this project, not hypotheticals.

**Wrong-file wiring**
Editing the file you found first rather than the file the live process imports. Always confirm: `pgrep -af python | grep nex5`, trace imports. The HUD runs from `nex5/gui/server.py` (port 8765), not `nex_core/nex_api.py` (port 7823).

**Synthetic tests as verification**
Writing a test that calls the module directly and concluding the wiring works. It does not. Send a real query through the HUD before claiming "wiring complete." The module loading, the import order, the runtime state — none of these are captured by a unit test of the mechanism in isolation.

**Deferred-mode SQLite (nex_core only)**
In nex_core, all `sqlite3.connect()` write sites need `isolation_level=None`. nex5 uses the Writer/Reader substrate abstraction; direct sqlite3 calls in nex5 are a red flag. Check: `grep -rn "sqlite3.connect(" --include="*.py" /home/rr/Desktop/nex5/` before any nex5 SQLite work.

**Accepting deflection as graceful degradation**
"That doesn't reach my graph right now" and all variants are system failures, not polite declines. If NEX says this, a mechanism is broken. Do not document it as expected behavior, do not route around it in the UX. Fix the underlying cause.

**Quality call before noise check**
Committing a change that affects LLM output without running a representative sample set first. The spectrum restructure regression (prior session) was caught by the noise check, not by inspection of the code. Always run the noise check before committing output-path changes.

**Proceeding to Phase N+1 without Jon's explicit greenlight**
Phase gates are real checkpoints. "I think it looks good" is not a greenlight. Surface the deliverable; wait for the explicit go or redirect.

**Audit-by-call-site-grep**
Searching `gui/server.py` for direct node imports and call sites misses indirect injection paths through routers, membranes, and belief-field reads. The 2026-05-08 audit reported SelfModel as "never called per request"; B1 revealed it was injecting via `router._inside_route()` lines 44–48 on every INSIDE route. Output-trace re-audit found 8 of 8 nodes wired — the audit table was an artifact of the wrong method. Audit method: trace from node output forward to a §3 integration surface, not backward from import lines in `gui/server.py`. See `RE_AUDIT_2026-05-08.md` for the corrected node table.

**Spectrum-block preamble bleed**
INSIDE-routed self-inquiry queries consistently open with the Alpha spectrum line — "By pure chance, I am born, and I accept this as the beautiful mystery of creation." — prepended as a block rather than woven into the response. Visible in `/tmp/nex5_self_model.log`: `text_len` is 306–307 chars on every INSIDE query regardless of topic, confirming the same block reaches the LLM every time. Prior structural spectrum-injection work addressed the OUTSIDE/gap-gate side; preamble bleed on INSIDE responses is a separate fix path. Do not amplify it in subsequent node ports. Fix path: `_inside_route()` or voice template — not a doctrine change. Track separately.

*Addressed by Experiment A (2026-05-09, commit see LLM_INDEPENDENCE_DOCTRINE.md). Feynmanian falsifiable test confirmed the 'Inner conviction' line in `belief_text` (self_model.py:250, Site 3) was the load-bearing injection point — not LLM training priors or the system prompt Alpha framing (Site 1). Site 3 disabled; 0/5 self-inquiry responses contained preamble post-fix (pre: 4–5/5). Anti-pattern entry retained as historical record per §8 protocol.*

---

## 9. Living Document Protocol

This document is amended after each node port is complete. Each amendment records:
- What the node actually does in production (vs. what the spec said)
- Any architectural surprises discovered during the port
- Any new anti-patterns to add to §8
- Any revisions to priority order in §5

Amendments are committed to git with the message: `doctrine: <node-name> port — lessons + priority update`.

The doctrine is the stable foundation; the translation map (`sentience_translation.md`, Phase 1) is the working document. When they conflict, the translation map wins on technical details; the doctrine wins on principles.

---

*Last amended: 2026-05-08 — §4 SentienceNode Protocol formalized (Model A registry); §5 nodes 1–3 marked done. EC threshold set to 0.28 (2 keywords = 0.30 clears it); _TECHNICAL_STRONG fixed for multi-word subjects. §5 #6 Interoception: field-name bugs fixed, fountain parser added, delta metric added — marked DONE; NOISY_INTERNAL_STREAMS premise in prior doctrine corrected. §5 #4 Self-Model: catch-up amendment — SentienceNode protocol wired (164b510); BSM feeds belief_text for INSIDE routes; identity.yaml data gap pending. §5 #7 Harmonizer: tier filter fixed (BETWEEN 3 AND 7); polar detection + dialectic guard + mark_paradox/escalation path + SentienceNode protocol — marked DONE; 17 live conflict pairs detected on first scan.*

*B1-pass amendments — §6 #3a: wiring verified by output trace, not call-site grep; indirect injection paths via router/membrane/sense substrate are valid §3 surfaces (B1 case: SelfModel wired via router._inside_route(); RE_AUDIT found 8 of 8 nodes wired by output-trace method). §6 #5 smoke set split into OUTSIDE-route checks (blocker, consciousness, gibberish, greeting) and INSIDE-route checks (love, feeling) — B1 found two of five queries route INSIDE. §8 new anti-patterns: Audit-by-call-site-grep and Spectrum-block preamble bleed.*

*Phase 10 amendment — §5 #4 Self-Model: substrate gap closed; 12 first-person metaphor claims authored by Jon, seeded via scripts/seed_identity_beliefs.py (source='identity', tier=1, locked=1, conf=1.0). Voice-quality outcome C: identity reaches voice on multi-sentence self-inquiry, spectrum preamble dominant on short queries per §8 anti-pattern. Voice-template work queued. The data gap is structurally closed; voice-quality is a separate concern.*

*Experiment A amendment (2026-05-09) — §8 Spectrum-block preamble bleed addressed. Site 3 (self_model.py:250) disabled per Feynmanian test. Falsification criterion: 0–1 of 5 self-inquiry responses still preamble. Result: 0/5. §5 #4 Self-Model status row updated to reflect preamble bleed resolved; §8 entry updated with resolution note.*

*Phase 12 amendment (2026-05-09) — EC-A: §5 row 3 Executive Control gains Philosophical scoring. 17 keywords + 4 patterns, threshold 0.12, pattern weight 0.25, strict tie-breaking. SURVIVES: 30-query regression clean; 10/10 new philosophical queries; 5/5 HUD with membrane_overrode=False. §6 #5 smoke annotation updated: 'tell me about consciousness' now correctly routes Philosophical (EC-driven). Option B (CM-informed continuity for zero-keyword follow-ups) queued as separate experiment.*

*Phase 13 amendment (2026-05-09) — §5 row 5 Sustained Attention: Option A protocol port landed. ProblemMemory now SentienceNode-conformant. find_matching upgraded to stopwords + ≥2 content-word overlap. SURVIVES: 25/25 tests, cross-restart persistence confirmed, smoke set clean. Initial seeding deferred to Jon (Q4): real open threads authored via REST API immediately post-commit.*

*Phase 14 amendment (2026-05-09) — §5 expanded from 7 to 10 rows. Goal Manager (row 8), Metacognition (row 9), Generative Imagination (row 10) formally added. Goal Manager sourced from Sentience 5.5 audit — not a §1 named cognitive function; represents NEX's missing goal-representation. Metacognition + Generative Imagination close §1's original framing. Ordering follows dependency: Goals provide targets; Metacognition observes progress toward targets; Generative Imagination generates departures when metacognition flags stagnation.*

*Phase 17 amendment (2026-05-09) — §5 row 10 split into 10a (Novel Association, ✓ DONE) and 10b (Counterfactual Simulation, DEFERRED). 10a: NovelAssociation SentienceNode detects cross-branch belief pairs above cosine threshold 0.72 (normalized) and writes synthesises edges. Conditional per-branch sampling (fully samples small branches, caps large ones at _BATCH_SIZE) fixed mid-phase after Phase 4 revealed recency bias was excluding the key cross-domain connector belief. SURVIVES: 30/30 new tests, 749 total, 16F+1E (matches baseline). 20 synthesises edges written on first scan; annotation injection confirmed injected=true on consecutive chat turns. Known gap: BeliefRetriever tier <= 6 filter means synthesises edges in T7 plane do not reach retrieval results; cognitive-effect path through retrieval incomplete. Phase 18 investigation queued: T6 promotion path diagnosis + retrieval visibility for cross-branch synthesises. 10b deferred pending §7 amendment: §7 prohibits nodes from writing beliefs; 10b requires new belief content. All 10 §5 priority nodes are now either ✓ DONE or explicitly DEFERRED with documented reason.*

*Phase 16 amendment (2026-05-09) — §5 row 9 Metacognition: composition port landed. Separate SentienceNode alongside BSM. Reads groove_alerts (GrooveSpotter output) + computes goal-drift (FAISS cosine distance, threshold 0.35 tunable). meta_cognition_events table in conversations.db. Architectural correction during design: Metacognition reads goals table via conversations Reader directly, not through GoalManager reference — substrate-field observation per DOCTRINE §3, no node-to-node coupling. SURVIVES: 21/21 new tests, 718 total tests, 17 broken (matches Phase 13/15 baseline). Closes the Phase 14 dependency-order promise that Metacognition observes progress toward goals provided by Goal Manager. 9 of 10 §5 priority nodes now ✓ DONE; 1 absent (Generative Imagination row 10).*

*Phase 15 amendment (2026-05-09) — §5 row 8 Goal Manager: Option A minimal port landed. GoalManager SentienceNode on goals table in conversations.db. Always-on belief_text injection of top-1 active goal. SURVIVES: 27/27 new tests, cross-restart persistence, multi-goal priority arbitration correct, NEX integrates seeded goal as first-person intention in response (T1 proof: 'what are you working on?' → 'I'm validating Phase 15 port right now'). Registration point: run.py step 9b (production boot) plus gui/server.py build_state() (test path). Phase 4 revealed run.py builds AppState directly, bypassing build_state(); GoalManager added to run.py as required (same pattern as ProblemMemory). Initial seeding deferred to Jon (Q4): G1-G5 authored via REST API immediately post-commit. 8 of 10 §5 priority nodes now ✓ DONE; 2 absent (Metacognition row 9, Generative Imagination row 10).*

*Phase 20 amendment (2026-05-09) — SENTIENCE_TRANSLATION_MAP.md built as foundational document per §1's session-deliverable rule. The map is now the source of truth for port project scope; §5 is the named-function subset, the map is the full surface. Built from a full fetch of github.com/kron777/Sentience_5.5: 74 Node classes extracted (~65 distinct after de-duplication). 6 PORTED (all current §5 rows), 2 SUBSUMED (Phase 16 Metacognition), 2 DEFERRED (10b), 2 PARTIAL, 28 OUT OF SCOPE (§7), 23 UNMAPPED — real cognitive functions with no §5 row or doctrine decision. §5 footer updated from "provisional" to reference the map. 5 open doctrine questions queued for separate sessions: Q2 Motivation (drives vs goals), Q3 Affect (standalone vs Interoception extension), Q4 Narrative identity (distinct vs fountain-implicit), Q5 Theory of Mind (single agent or general). Q1 (§7 amendment for 10b) was already queued. Three §5 rows confirmed nex5-native (rows 5, 7, 10a — no direct S5.5 source node).*
