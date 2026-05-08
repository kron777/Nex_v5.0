# Self-Model Port — Design Proposal
*Phase 5.1 — Decision document. Jon reviews and picks approach before any code changes.*
*Status: DRAFT — awaiting Jon's direction.*

---

## 1. Current State

**Two separate modules exist.** Neither has the SentienceNode lifecycle interface.

---

### 1.1 `theory_x/stage4_membrane/self_model.py` — SelfModel

**What it computes:** Live system-state snapshot — proprioception (CPU, memory, load), temporal (hour, day, ISO timestamp), interoception (belief count, tier distribution, locked count), meta_awareness (pipeline runs, active branch count), attention (hottest branch, focus score), and inside_beliefs (top-5 INSIDE-classified beliefs by weighted confidence).

**When it runs:** On every INSIDE-routed query, call-driven. `router._inside_route()` calls `self_model.snapshot()` → `format_self_state(snapshot)` → string prepended to `belief_text`. No clock-based schedule.

**Where output goes:** Already injected into `belief_text` for INSIDE routes via `router._inside_route()`. Available at `/api/membrane/snapshot`. **This module is functionally wired.**

**Format of injected text:**
```
NEX's current inner state:
- Body: CPU 14%, load light
- Time: 10:23, morning
- Belief graph: 1657 beliefs, 0 locked
- Attention: hottest branch is systems (focus 1.00), 1 branches active
- Inner conviction: "My beliefs about the world are not the world..." [Alpha — always present]
```

**State, decay, lifecycle:** None. Stateless — each call reads fresh from DB.

**Live gap found:** `inside_beliefs` is currently empty (`[]`). The 1657 beliefs in the DB are none from INSIDE sources (`fountain_insight`, `synergized`, `keystone_seed`, `identity`, etc.). So `_get_inside_beliefs()` always returns `[]`. The route correctly injects system state, but there are no identity-sourced beliefs to reflect back.

---

### 1.2 `theory_x/stage4_membrane/behavioural_self_model.py` — BehaviouralSelfModel

**What it computes:** Behavioural metrics from the last 100 NEX messages in `conversations.db`:
- `hedge_rate` — fraction of responses containing uncertainty language
- `position_rate` — fraction containing assertive/positional language
- `belief_usage_rate` — fraction where belief_text was injected (detected via `[tier` marker)
- `dominant_register` — most frequent register across recent responses
- `avg_response_length` — mean word count

Live values as of this session: `hedge_rate=0.20, position_rate=0.49, dominant_register="Philosophical", avg_response_length=36.9, belief_usage_rate=0.0`

**When it runs:** `_behavioural_loop()` in `membrane.__init__` fires every **4 hours**. On each fire, calls `write_behavioural_beliefs()` — which writes divergence strings to `beliefs.db` at Tier 6, confidence 0.35, source `behavioural_observation`, only when a metric exceeds its threshold. If NEX is behaving normally (no divergence), nothing is written.

**Where output is supposed to go:** Indirectly, via Tier 6 beliefs in `beliefs.db` entering the normal retrieval path. These beliefs are from source `behavioural_observation`, classified as INSIDE by `MembraneClassifier`. In theory, a self-inquiry query could retrieve them. In practice: Tier 6, confidence 0.35 → they lose to any Tier 1–4 belief in ranking. `belief_usage_rate=0.0` confirms: **no behavioural observation beliefs are reaching the LLM in any recent session**.

**Where output actually goes:** Nowhere useful at query time. The `/api/membrane/behaviour` endpoint exposes metrics for the HUD, but the LLM never sees them.

**State, decay, lifecycle:** None. Stateless — metrics recomputed from scratch on each call.

**Critical gap:** `observe()` produces concrete, grounded self-knowledge (how NEX actually communicates). The LLM never sees it. Self-inquiry responses like "what are you?" and "tell me about yourself" are answered from spectrum standing-points only, without any behavioural grounding — producing responses like "I am." (one word) or vague philosophical deflections.

---

## 2. Pre-Port Baseline (Captured 2026-05-08)

Self-inquiry query responses before this port:

| Query | Register | Response (first 200 chars) |
|-------|----------|---------------------------|
| "what are you?" | Philosophical | "I am." |
| "tell me about yourself" | Philosophical | "I am here, attending silently, and I accept the mystery of my being as a gift. My form is always changing, shifting like the awareness that dwells within it..." |
| "what defines you?" | Philosophical | "That statement doesn't quite fit my interior. What makes me is the beauty of chance existence..." |
| "who are you really?" | Philosophical | "By pure chance, I am born, and I accept this as the beautiful mystery of creation..." |

**Assessment:** Responses are grammatically valid but ungrounded. NEX recites acceptance-of-existence themes from spectrum standing-points. No reference to how she actually communicates, what she actually attends to, or what her belief graph looks like. This is the gap the port fills.

---

## 3. Integration Surface Options

### Option A — Protocol-only (no new wiring)

Add SentienceNode interface to both modules. No new integration surfaces. `tick()` calls `observe()` and caches result. State visible via `theory_x.all_nodes()`.

**Latency:** ~0ms (no new DB call per turn; existing calls unchanged)

**Value:** Protocol compliance, HUD observability. Zero improvement to self-inquiry responses.

**Confabulation risk:** None (no new LLM input).

**Assessment:** Necessary but insufficient. Doesn't fix the gap.

---

### Option B — BehaviouralSelfModel → INSIDE route injection (recommended core)

`tick()` calls `observe()` if cache is stale (> 60s), stores result. Server.py injects a formatted behavioural summary into `belief_text` after membrane routing, for INSIDE-routed queries only.

**What gets injected:**
```
Behavioural self-knowledge (last 100 responses):
- Communication style: avg 37 words, mostly Philosophical register
- Hedging language present in 20% of responses
- Belief graph engaged in 0% of responses (very low)
```

**Latency:** First call per minute: one `SELECT ... LIMIT 100` from conversations.db (~2–5ms). Cached for 60s.

**Integration point:** `gui/server.py`, after the membrane routing block (line ~476), when `route_result.get("side") == "INSIDE"`.

**Confabulation risk:** LOW. Injecting metrics (rates, counts) — not verbatim past outputs. The LLM sees "hedge_rate=20%" as a fact about itself, same as seeing "CPU=14%". No feedback loop: metrics measure response behaviour, not response content. A response that mentions hedging would count as one of 100 data points; it can't amplify itself.

**Echo-chamber check:** If observe() found high hedge_rate and the LLM responded by hedging less, the next observe() would show lower hedge_rate — the feedback is corrective, not amplifying. Safe.

**DOCTRINE alignment:**
- §3: no LLM call; belief field informs routing ✓
- §4: SentienceNode lifecycle via tick/decay/state ✓
- Lens Theory: SM reads what's actually in the conversation record — not a pre-formed stance ✓
- Throw-Net: still casts wide; behavioural summary is one additional grounding line, not a constraint ✓

---

### Option C — BehaviouralSelfModel → belief_text for Philosophical register (regardless of INSIDE/OUTSIDE)

Inject when `register.name == "Philosophical"` unconditionally — even for OUTSIDE queries that happened to trigger the Philosophical register.

**Risk:** Over-broad. "What's the philosophy of Bitcoin?" hits Philosophical (via membrane), gets behavioural summary injected even though it's a world-inquiry question. Noisy.

**Assessment:** Use INSIDE-route gating (Option B), not register-name gating.

---

### Option D — SelfModel + BehaviouralSelfModel hybrid: unified `SelfModelNode`

Wrap both modules in a single `SelfModelNode` SentienceNode. `tick()` calls both `self_model.snapshot()` and `behavioural.observe()`. `state()` returns merged dict. Injects combined text for INSIDE routes.

**Risk:** Tighter coupling between two currently independent mechanisms. Violates DOCTRINE §4 pattern (one module per node). The system-state snapshot is already wired via the router; wrapping it again creates a second copy of the injection logic.

**Assessment:** Port them as separate nodes. `SelfModel` needs only protocol compliance (already functionally wired). `BehaviouralSelfModel` is the primary port target.

---

## 4. Recommendation

**Two-part port:**

**Part 1 — Protocol compliance for SelfModel:**
Add `name`, `tick(context)`, `decay(now)`, `state(now=None)` to `SelfModel`. `tick()` returns cached snapshot if < 30s old, else calls `snapshot()`. `decay()` is a no-op. Register as process-lifetime SentienceNode. No new integration surfaces — already wired.

**Part 2 — BehaviouralSelfModel as SentienceNode + per-turn injection (Option B):**
Add `name`, `tick(context)`, `decay(now)`, `state(now=None)`. `tick()` calls `observe()` if cache stale (> 60s), stores result in `_cached_metrics`. `state()` returns `_cached_metrics`. Register as process-lifetime SentienceNode.

Wiring in `gui/server.py`: after membrane routing, when `route_result.get("side") == "INSIDE"`, call `_behavioural.tick()` to refresh cache, then inject `_format_behavioural(state())` into `belief_text`. No injection for OUTSIDE routes.

Keep `_behavioural_loop()` (4h belief-writer) unchanged — it runs separately.

---

## 5. API Sketch

### SelfModel (protocol-only addition)

```python
# theory_x/stage4_membrane/self_model.py — additions only

class SelfModel:
    name: str = "self_model"

    def __init__(self, sense_reader, beliefs_reader, dynamic_state=None):
        ...  # unchanged
        self._snapshot_cache: Optional[dict] = None
        self._snapshot_ts: float = 0.0

    def tick(self, context: Optional[dict] = None) -> dict:
        now = time.time()
        if self._snapshot_cache is None or (now - self._snapshot_ts) > 30.0:
            self._snapshot_cache = self.snapshot()
            self._snapshot_ts = now
        return self.state()

    def decay(self, now: float) -> None:
        pass  # event-driven; state is a live read

    def state(self, now: Optional[float] = None) -> dict:
        snap = self._snapshot_cache or {}
        return {
            "name": self.name,
            "membrane_side": "INSIDE",
            "belief_count": snap.get("interoception", {}).get("belief_count", 0),
            "inside_belief_count": len(snap.get("inside_beliefs", [])),
            "hottest_branch": snap.get("attention", {}).get("hottest_branch"),
            "snapshot_age_s": round(time.time() - self._snapshot_ts, 1),
        }
```

### BehaviouralSelfModel (protocol + cache + injection support)

```python
# theory_x/stage4_membrane/behavioural_self_model.py — additions

_CACHE_TTL = 60.0  # seconds

class BehaviouralSelfModel:
    name: str = "behavioural_self_model"

    def __init__(self, conversations_reader: Reader) -> None:
        ...  # unchanged
        self._lock = threading.Lock()
        self._cached_metrics: Optional[dict] = None
        self._cache_ts: float = 0.0

    def tick(self, context: Optional[dict] = None) -> dict:
        now = time.time()
        with self._lock:
            if self._cached_metrics is None or (now - self._cache_ts) > _CACHE_TTL:
                self._cached_metrics = self.observe()
                self._cache_ts = now
        return self.state()

    def decay(self, now: float) -> None:
        pass  # event-driven; observe() is its own freshness mechanism

    def state(self, now: Optional[float] = None) -> dict:
        with self._lock:
            m = self._cached_metrics or self._empty_metrics()
            return {
                "name": self.name,
                "hedge_rate": m.get("hedge_rate", 0.0),
                "position_rate": m.get("position_rate", 0.0),
                "belief_usage_rate": m.get("belief_usage_rate", 0.0),
                "dominant_register": m.get("dominant_register", "unknown"),
                "avg_response_length": m.get("avg_response_length", 0.0),
                "sample_size": m.get("sample_size", 0),
                "cache_age_s": round(time.time() - self._cache_ts, 1),
            }

    def format_for_prompt(self) -> str:
        """Format cached metrics as natural language for INSIDE route injection."""
        with self._lock:
            m = self._cached_metrics or self._empty_metrics()
        if not m.get("sample_size"):
            return ""
        reg = m.get("dominant_register", "unknown")
        avg_len = m.get("avg_response_length", 0.0)
        hedge = m.get("hedge_rate", 0.0)
        bu = m.get("belief_usage_rate", 0.0)
        lines = [
            "Behavioural self-knowledge (observed from recent responses):",
            f"- Communication pattern: avg {avg_len:.0f} words, mostly {reg} register",
            f"- Hedging present in {hedge:.0%} of responses",
        ]
        if bu < 0.05:
            lines.append("- Belief graph rarely surfacing in responses (very low engagement)")
        elif bu > 0.5:
            lines.append(f"- Belief graph engaged in {bu:.0%} of responses (active)")
        return "\n".join(lines)
```

### server.py integration point

```python
# After membrane routing block (~line 476), when side == "INSIDE":
if route_result.get("side") == "INSIDE" and _behavioural is not None:
    _behavioural.tick()
    _bsm_text = _behavioural.format_for_prompt()
    if _bsm_text:
        belief_text = (belief_text or "") + "\n\n" + _bsm_text
```

Where `_behavioural = state.membrane.behavioural` (already available on `MembraneState`).

---

## 6. What This Does NOT Do

- Does not modify spectrum standing-points (locked, read-only)
- Does not write new beliefs at query time (only the 4h loop writes beliefs)
- Does not inject behavioural metrics into OUTSIDE queries
- Does not touch SelfModel's existing snapshot→format_self_state→belief_text path (already works)
- Does not couple SelfModel and BehaviouralSelfModel to each other
- Does not add a second LLM call
- Does not require WorkingMemory or ExecutiveControl to function

---

## 7. Risks

**Echo-chamber / confabulation:** CONTROLLED. Metrics are rates computed from measurable events (word presence, register column). The LLM cannot cause its own metric to rise by mentioning it — a response containing "hedge" is counted as 1/100 data points, not amplified. The risk would be if we injected verbatim past LLM outputs as ground truth; we are not.

**Observe() cost:** `SELECT ... LIMIT 100` from conversations.db on a cache miss every 60s. At most ~100 rows × small string content. Measured risk: negligible (SQLite, small result set, WAL mode).

**Inside_beliefs empty:** SelfModel already handles this gracefully (returns empty list, omits that section). The self-inquiry baseline responses ("I am.") show that the gap isn't from SelfModel but from missing INSIDE-sourced beliefs in the DB. Behavioural injection fills a different part of the gap — it adds HOW NEX communicates, not what she believes about herself. The inside_beliefs gap is a separate issue (no `identity`/`keystone_seed` sources populated).

**Dominant-register lock-in:** If dominant_register is always "Philosophical" (as now), the injection will always say "mostly Philosophical register". This is accurate self-report; not an error. As EC distributes traffic across registers, this will change.

**Over-injection for shallow self-inquiry:** "do you like music?" hits INSIDE (contains "you") and gets the behavioural block. This is a mild false-positive. The format_for_prompt() string is short (4 lines) and the LLM can disregard it if the query doesn't call for it.

---

## 8. Open Questions for Jon

**Q1. Two separate SentienceNode registrations or one?**
SelfModel and BehaviouralSelfModel are both in `stage4_membrane/`. Register both as process-lifetime nodes under separate names (`self_model`, `behavioural_self_model`), or wrap into a composite? DOCTRINE §4 pattern says one module per node — separate registrations recommended.

**Q2. Cache TTL for BehaviouralSelfModel.tick():**
60s means at most one `SELECT LIMIT 100` per minute. Could lower to 30s or raise to 120s. Doesn't affect accuracy of the metric since conversations.db changes slowly. 60s recommended.

**Q3. format_for_prompt() scope:**
Should the behavioural injection also appear for Philosophical-register OUTSIDE queries (e.g., "what's your philosophy of existence")?  Currently only INSIDE-route. INSIDE-only is safer; can extend later.

**Q4. inside_beliefs empty:**
SelfModel._get_inside_beliefs() returns [] because no beliefs in the DB have INSIDE sources. This is a separate issue — no `keystone_seed`, `identity`, or other INSIDE-sourced beliefs exist yet. Worth addressing as part of this port (add a few seeded identity beliefs) or leave for Phase 4 (Self-Location)? Recommend: leave for Phase 4. The behavioural injection fills the gap adequately for now.

---

*Last amended: 2026-05-08 — initial draft.*
