# Executive Control — Design Proposal
*Phase 4.1 — Decision document. Jon reviews and picks approach before any code is written.*
*Status: DRAFT — awaiting Jon's direction.*

---

## 1. Current State

**`classify()` stub** (`voice/registers.py:classify()`):
```python
def classify(_text: str) -> Register:
    """Phase 1 stub — always Conversational."""
    return CONVERSATIONAL
```
Called at `gui/server.py:399`:
```python
register = (by_name(register_name) if register_name else classify(prompt)) or default_register()
```

**Membrane override** (`gui/server.py:512-515`):
```python
# Apply register override from router (INSIDE → philosophical) only if
# the user hasn't explicitly specified a register.
if register_override and not register_name:
    register = by_name(register_override) or register
```
This fires when `MembraneClassifier.classify_query()` detects self-inquiry keywords and `router._inside_route()` sets `register_hint = "philosophical"`. Membrane is authoritative for Philosophical routing and must remain so.

**Pipeline position of classify():**
```
classify(prompt) → initial register
membrane.route() → belief_text + register_override
register_override applied if no explicit register_name from user
WM injection
gap gate check
LLM call
```
Executive Control replaces step 1 only. Steps 2–end are unchanged.

---

## 2. What Each Register Actually Does

| Register | Trigger intent | LLM behaviour shaping |
|---|---|---|
| Analytical | Market/finance/data, cross-domain pattern, quantitative question | "Direct, numerate, confidence-calibrated. Offer your take with honest uncertainty." |
| Conversational | General discussion, opinions, most things | "Talk like a knowledgeable person, not an assistant. Curious, honest, willing to push back." |
| Philosophical | Self-inquiry only (nature, identity, consciousness, feelings) | "For inward questions only. Speak from stillness, not performance." |
| Technical | Code, mechanism explanations, deep-dives, step-by-step reasoning | "Precise; go long when warranted. Show reasoning steps. Cite sources when relevant." |

Philosophical is already handled by the membrane. Executive Control only needs to distinguish between **Analytical**, **Conversational**, and **Technical**.

---

## 3. Approach Options

### Option A — Pure Heuristic

Regex/keyword scoring against the three target registers. Score each register independently; take the highest; Conversational is the floor (wins on tie or insufficient signal).

**Latency:** ~0ms (in-process, no I/O)

**Accuracy:** Rough (~70-80%). Strong for Analytical (financial terms, numbers are distinctive). Reasonable for Technical (explanation verbs, technology nouns). Weakest for the Analytical/Technical boundary ("explain the market mechanism" could be either).

**Dependencies:** None. No Ollama call, no belief lookup.

**Failure modes:**
- Ambiguous cross-register queries ("explain how Bitcoin's correlation with tech stocks works" → Analytical or Technical?)
- Domain transfer ("what's the code complexity of human consciousness?" → Technical or Philosophical?)
- Short queries with no lexical signal ("why?" after a Technical conversation → falls to Conversational, losing session continuity)

**Implementation surface:** ~40 lines in `theory_x/executive_control.py`. Replaces `voice/registers.classify()` entirely.

---

### Option B — LLM-based (Ollama roundtrip)

Send `prompt` + register descriptions to Qwen2.5:3b (already running for voice) for a one-token classification.

**Latency:** 500–2000ms per chat turn (measured from Phase 2 multi-turn test: ~22s for a full voice response, so this adds ~10% overhead at best, 100% at worst if model is cold).

**Accuracy:** ~90%+. LLM handles the cross-register ambiguity and domain transfer cases that trip up the heuristic.

**Dependencies:** Ollama must be running. But: this is a SECOND request to the same endpoint that will service the voice call 100ms later. Two concurrent requests to Ollama at qwen2.5:3b on single-GPU hardware will queue; the voice call latency increases.

**Failure modes:**
- Ollama unavailable → classification call fails → must fall back to Conversational stub (net result: same as today)
- GPU contention with voice call → one or both calls queue, adding 2-10s latency
- Model hallucinates register name not in {Analytical, Conversational, Technical} → needs validation + fallback

**DOCTRINE constraint:** DOCTRINE §3 — "nodes do not communicate directly with the LLM." This is a borderline case; classify-via-LLM is a cognition step, not a voice step. But the practical GPU contention issue is the real blocker.

---

### Option C — Hybrid (heuristic first; LLM on ambiguous cases only)

Pure heuristic for high-confidence cases (Analytical threshold exceeded clearly, or Technical threshold exceeded clearly). LLM for medium-confidence cases where heuristic score difference is small.

**Latency:** ~0ms for clear cases (~60-70% of traffic), 500-2000ms for ambiguous cases (~30-40%).

**Accuracy:** Better than pure heuristic on ambiguous cases; same as heuristic on clear cases.

**Failure modes:** The ambiguity threshold is arbitrary. If set too low, LLM is called on most traffic. If set too high, it's effectively Option A. GPU contention applies to the ambiguous-case path.

---

### Option D — Heuristic with WorkingMemory session-continuity bias (recommended)

Pure heuristic for lexical signal, PLUS last-register persistence from session state. If heuristic is weak (low-confidence), fall back to the most recent register from this session. If session is new, use Conversational.

**Latency:** ~0ms

**Accuracy:** Better than naive Option A for session-continuous queries. The dominant accuracy gap in Option A was short queries with no lexical signal; those are precisely where the previous register is a good prior.

**Dependencies:** WM (already ported). ExecutiveControl holds last-register per-call via the `wm` or a simple `_last_register` dict keyed by `session_id`.

**Failure modes:**
- Over-sticky: once in Technical/Analytical register, stays there until strong switch signal (manageable: Conversational is always the final fallback; membrane override is always authoritative)
- Still misclassifies some cross-register queries, but these are the hard cases for any non-LLM approach

**DOCTRINE alignment:**
- §3: no LLM call for cognition; belief field (WM) informs routing ✓
- §7: no premature optimization; ~40 lines, no new dependencies ✓
- Lens Theory: reads the pattern of prior turns from the belief field rather than pre-filtering the current turn ✓

---

## 4. Recommendation

**Option D — Heuristic with session-continuity bias.**

Rationale:
1. Philosophical is already classified correctly by the membrane; the remaining problem (Analytical vs Technical vs Conversational) has strong enough lexical signals that a good heuristic covers the dominant cases.
2. Option B's GPU contention is a real production risk. On the RX 6600 LE with Ollama at qwen2.5:3b, two concurrent requests will serialize; voice latency would increase on every chat turn.
3. DOCTRINE §3 keeps cognition in the belief field. Session continuity via last-register is the simplest form of this — the EC node reads its own recent state rather than asking the LLM.
4. This is upgradeable: the `classify()` method on `ExecutiveControl` can be swapped for the LLM path later without changing the integration point.

---

## 5. API Sketch

Per SentienceNode protocol (DOCTRINE §4):

```python
# theory_x/executive_control.py

class ExecutiveControl:
    """Register classifier — Executive Control node (Theory X port, DOCTRINE §5 #3).

    Heuristic-based with session-continuity bias. Replaces classify() stub in
    voice/registers.py. Membrane override for Philosophical remains authoritative.
    """
    name = "executive_control"

    def __init__(self) -> None:
        self._session_registers: dict[str, str] = {}  # session_id → last register name
        self._classify_calls: int = 0
        self._register_counts: dict[str, int] = {}

    def classify(
        self,
        prompt: str,
        session_id: Optional[str] = None,
        wm: Optional["WorkingMemory"] = None,
    ) -> Register:
        """Classify prompt to register. Thread-safe. Never raises."""
        ...

    # SentienceNode lifecycle
    def tick(self, context: dict) -> dict: ...
    def decay(self, now: float) -> None: ...      # no-op; state is event-driven
    def state(self, now: Optional[float] = None) -> dict: ...
```

Key internal methods:
```python
def _score_prompt(self, prompt: str) -> dict[str, float]:
    """Return {register_name: confidence} for Analytical, Technical, Conversational."""
    # Analytical signals: numbers/%, financial terms, "analyze/compare/correlate"
    # Technical signals: explanation verbs, tech nouns, "how does/implement/step by step"
    # Conversational: floor — starts at 0.3; wins on insufficient signal
    ...

def _apply_continuity_bias(
    self, scores: dict[str, float], session_id: Optional[str]
) -> dict[str, float]:
    """Boost previous session register's score by CONTINUITY_WEIGHT (0.15)."""
    ...
```

Tunable constants:
```python
_ANALYTICAL_THRESHOLD = 0.45     # score above this → Analytical
_TECHNICAL_THRESHOLD  = 0.45     # score above this → Technical
_CONTINUITY_WEIGHT    = 0.15     # boost for previous session register
```

---

## 6. Integration Plan

**Replace classify() in `gui/server.py`:**

Current (line 398-400):
```python
register = (
    by_name(register_name) if register_name else classify(prompt)
) or default_register()
```

After (single-line change):
```python
register = (
    by_name(register_name) if register_name
    else _exec_control.classify(prompt, session_id=session_id)
) or default_register()
```

Where `_exec_control` is a process-lifetime singleton at module level (analogous to `_focal_set`):
```python
try:
    from theory_x.executive_control import ExecutiveControl as _ExecControl
    _exec_control = _ExecControl()
except Exception:
    _exec_control = None
```

When `_exec_control is None`: fall through to `default_register()` (Conversational) — same behaviour as today.

**Membrane override remains authoritative (unchanged):**
```python
# Lines 512-515 — NOT TOUCHED
if register_override and not register_name:
    register = by_name(register_override) or register
```
Philosophical routing: membrane classifies INSIDE → sets `register_hint = "philosophical"` → overrides EC's output. This is correct: Philosophical is a self-model question, not a voice-register question. EC handles what to say; membrane handles whether to look inward.

**Session-continuity via `session_id` (not WM items):**
EC receives `session_id` from server.py and maintains `_session_registers` dict internally. WM is available for potential Phase 2 topical-context amplification but is not required for Phase 1.

**Fallback path:**
Any exception in `classify()` returns `CONVERSATIONAL` — identical to today's stub behaviour.

---

## 7. What this does NOT do

- Does not touch membrane routing (INSIDE/OUTSIDE classification unchanged)
- Does not modify register descriptions or LLM prompting
- Does not add a second LLM call
- Does not replace the membrane's Philosophical override
- Does not require WorkingMemory to function (uses it for bias only)
- Does not classify PHILOSOPHICAL — membrane is authoritative for that

---

## 8. Open questions for Jon

**Q1. Heuristic vocabulary:** The signal words for Analytical vs Technical need tuning against real traffic. The Phase 2 multi-turn test showed only Conversational and Philosophical queries. Should we run 20-30 representative queries through a dry-run first to tune thresholds before wiring?

**Q2. Continuity weight:** 0.15 is a guess. Too high → register gets sticky in long sessions. Too low → no benefit from continuity. Tunable post-deploy, but initial value matters.

**Q3. Option A vs D:** If you want to start without the continuity bias (pure heuristic, simpler first version) and add bias in a follow-up, that's cleanest. The integration point is identical.

---

*Last amended: 2026-05-08 — initial draft.*
