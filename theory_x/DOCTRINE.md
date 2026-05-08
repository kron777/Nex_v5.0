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
| 3 | **Executive Control** | Query routing, register assignment | ✓ DONE | Heuristic+continuity classifier (Option D); 30/30 regression baseline; wired gui/server.py:426 |
| 4 | **Self-Model** | Behavioral self-representation | ✓ DONE | SentienceNode protocol on both SelfModel + BehaviouralSelfModel; BSM injects metrics into belief_text for INSIDE routes; data gap on inside_beliefs pending seeds/identity.yaml authoring (loader scaffold in 12f50e5) |
| 5 | **Sustained Attention** | Open problem persistence | ABSENT | `open_problems` table wired but always empty; `stage7_sustained/problem_memory.py` unused |
| 6 | **Interoception** | Body-state awareness in cognition | ✓ DONE | Field-name bugs fixed (locked_beliefs, tier_counts); fountain receives natural language via selector; delta metric added. Was never NOISY — NOISY_INTERNAL_STREAMS premise in prior doctrine was wrong |
| 7 | **Harmonizer** | Contradiction resolution | ✓ DONE | Root cause was tier filter (`<= 4`) excluding all 1334 epistemic beliefs (tier 7); fixed to `BETWEEN 3 AND 7`. Polar vocabulary detection (4 pairs, constancy/flux expanded with stability/transformation/adaptability vocabulary) + dialectic guard (beliefs holding both poles skipped). mark_paradox first-pass (non-destructive); escalate to synthesize/delete after 16h incubation. SentienceNode protocol + `format_for_prompt()`. 17 live conflict pairs detected. |

Ordering 3–7 is provisional. The full translation map (Phase 1 of the port project) determines final sequence. Jon confirms order before each port begins.

---

## 6. Acceptance Criteria Per Node Port

A node port is complete when all of the following are true:

1. **Module exists** at `theory_x/<node_name>.py` with `__all__`, docstring, and lifecycle interface
2. **Unit tests pass** in `tests/test_<node_name>.py` against mock belief data
3. **Wired in `gui/server.py`** at the correct pipeline stage; log-only mode verified first
4. **Real-traffic validation**: minimum 5 HUD queries exercising the node's specific function; log shows node activating correctly
5. **No regression** on the five-query baseline: social greeting, philosophical self-inquiry, casual question, self-state probe, world event question
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
