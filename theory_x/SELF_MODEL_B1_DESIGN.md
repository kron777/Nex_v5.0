# SelfModel B1 — Per-Request Injection Design

**Phase:** B1 (DOCTRINE §5 #4)  
**Status:** DESIGN — awaiting Jon's greenlight before B1.2 apply  
**Date:** 2026-05-08

---

## 0. Critical Finding — Injection Already Live

Before writing the wiring, read `theory_x/stage4_membrane/router.py` in full.

`QueryRouter._inside_route()` (lines 41–64) already does:

```python
snap = self_model.snapshot()          # live read, per INSIDE request
parts.append(format_self_state(snap)) # prepends formatted state to belief_text
```

The router calls `format_self_state()` and puts the result at the top of `belief_text` for every INSIDE-routed query. The content injection is already live. What is missing is **only the log write** — there is no write site for `/tmp/nex5_self_model.log`, so the audit's DOCTRINE §6 #5 check (log file fills) fails even though the node is functioning.

**B1 scope revision:** no content injection needed. B1.2 adds the log write only.

The `router._inside_route` call path also means:
- `snapshot()` is called once per INSIDE request (in the router)
- A second `snapshot()` call at the B1 log site would double the DB reads
- To avoid that, use `state.membrane.self_model.tick()` at the log site, which refreshes the 30s TTL cache. Since the router calls `snapshot()` directly (not `tick()`), the cache is empty after the router call — `tick()` will call `snapshot()` once more. A single additional snapshot per INSIDE request is the irreducible minimum for getting the log data including `locked_count`. The cost is acceptable.

---

## 1. Current State

### What SelfModel computes

`SelfModel.snapshot()` assembles five sections from live data sources:

| Section | Source | Live data (current run) |
|---------|--------|------------------------|
| proprioception | `sense.db` → `internal.proprioception` | cpu=4%, mem=None, load=None, thermal=None |
| temporal | `sense.db` → `internal.temporal` | hour=18, day=4, iso=2026-05-08T18:39:48 |
| interoception | `sense.db` → `internal.interoception` | belief_count=1671, **locked_count=317** |
| meta_awareness | `state.dynamic.status()` | pipeline_runs, active_branches (populated in live server) |
| attention | `state.dynamic.status()` | hottest_branch, hottest_focus (populated in live server) |
| inside_beliefs | `beliefs.db` INSIDE-filtered | **0 entries — data gap (see below)** |

### What `format_self_state(snapshot)` emits — verbatim live output

```
NEX's current inner state:
- Body: CPU 4%
- Time: 18:39, evening
- Belief graph: 1671 beliefs, 317 locked
- Inner conviction: "By pure chance, I am born, and I accept this as the beautiful mystery of creation." [Alpha — always present]
```

(Probe ran without `dynamic_state`; in live server, attention and meta_awareness lines will appear when `hottest_branch` / `pipeline_runs` are non-None.)

### The inside_beliefs data gap

`_get_inside_beliefs()` queries `beliefs WHERE paused=0 AND tier<=6 ORDER BY confidence DESC LIMIT 30`, then filters to INSIDE sources:

- The top-30 confidence pool is **100% spectrum** (200 spectrum beliefs at tier=1, conf=1.0 dominate)
- After INSIDE filter: **0 of 30**

INSIDE-source beliefs at tier≤6 exist, but are pushed out of the LIMIT 30 by spectrum:

| tier | source | count | in top-30? |
|------|--------|-------|-----------|
| 1 | keystone_seed | 7 | No — spectrum fills all 30 slots |
| 1 | self_location | 1 | No |
| 1 | reification_recognition | 1 | No |
| 2 | practice | 40 | No |
| 6 | synergized | 2 | No |
| 7 | synergized | 724 | Excluded (tier>6) |
| 7 | fountain_insight | 536 | Excluded (tier>6) |

**Critical:** `format_self_state()` does **not use `inside_beliefs`** — it reads only `proprioception`, `temporal`, `interoception`, `attention`, and `ALPHA.lines[0]`. The inside_beliefs data gap does not degrade the formatted output. The function produces useful signal regardless.

The inside_beliefs gap is a separate issue (same pool-monoculture root as C2); it is not a blocker for B1.

### What SelfModel does NOT have

- No `format_for_prompt()` method. The formatting function is module-level: `format_self_state(snapshot: dict) -> str` in `self_model.py`.
- `tick()` returns `state()` (a dict summary), not the snapshot. The cache (`_snapshot_cache`) is private.
- For per-request injection, call `snapshot()` directly — fresh read, not the 30s TTL cache. The TTL cache was designed for the background SentienceNode polling model, not per-request injection.

---

## 2. BSM Injection Precedent (gui/server.py lines 525–546)

```python
# BehaviouralSelfModel injection — INSIDE routes only
if (route_result is not None
        and route_result.get("side") == "INSIDE"
        and state.membrane is not None
        and state.membrane.behavioural is not None):
    try:
        state.membrane.behavioural.tick()
        _bsm_text = state.membrane.behavioural.format_for_prompt()
        if _bsm_text:
            belief_text = (belief_text or "") + "\n\n" + _bsm_text
            with open(_BSM_LOG, "a") as _bfh:
                _bfh.write(...)
    except Exception as _bsm_exc:
        error_channel.record(...)
```

B1 mirrors this exactly, with two differences:
1. Calls `snapshot()` (live read) rather than `tick()` (TTL cache)
2. Calls module-level `format_self_state(snap)` rather than a method

---

## 3. Content Comparison — BSM vs SelfModel (no redundancy)

| | BehaviouralSelfModel | SelfModel |
|---|---|---|
| Content | Behavioral patterns: avg response length, dominant register, hedge rate, belief usage rate | Physical/computational state: CPU, time, belief count, locked count, attention, Alpha |
| Describes | *How NEX habitually speaks* | *What NEX's body/graph state is right now* |
| Overlap | None | None |
| For self-inquiry | "I typically respond in ~41 words" | "My graph holds 1671 beliefs, 317 locked; it is evening" |

Both are useful on INSIDE routes. Together they give the LLM behavioral context + current state context.

---

## 4. Injection Point

**Location:** `gui/server.py`, after the BSM injection block (after line 546), before the disturbance tension block.

**Gate:** Same INSIDE-route condition as BSM.

**Ordering rationale:** BSM first (behavioral patterns → "how I usually speak"), SelfModel second (current state → "what my body/graph holds right now"). This layering matches a natural inside-out reading: behavior pattern → current state.

**Proposed code:**

```python
# SelfModel injection — INSIDE routes only (B1).
# Surfaces body state, belief count, locked count, attention, Alpha conviction.
if (route_result is not None
        and route_result.get("side") == "INSIDE"
        and state.membrane is not None
        and state.membrane.self_model is not None):
    try:
        from theory_x.stage4_membrane.self_model import format_self_state as _fmt_self_state
        _sm_snap = state.membrane.self_model.snapshot()
        _sm_text = _fmt_self_state(_sm_snap)
        if _sm_text:
            belief_text = (belief_text or "") + "\n\n" + _sm_text
            with open(_SM_LOG, "a") as _smf:
                _sm_intro = _sm_snap.get("interoception", {})
                _smf.write(
                    f"[{time.strftime('%H:%M:%S')}] INSIDE inject: "
                    f"beliefs={_sm_intro.get('belief_count', 0)} "
                    f"locked={_sm_intro.get('locked_count', 0)} "
                    f"inside_beliefs={len(_sm_snap.get('inside_beliefs', []))}\n"
                )
    except Exception as _sm_exc:
        error_channel.record(
            f"self-model injection failed: {_sm_exc}",
            source="gui.server", exc=_sm_exc,
        )
```

**Constants to add** (near `_BSM_LOG` at line 139):
```python
_SM_LOG  = "/tmp/nex5_self_model.log"
```

---

## 5. Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Prompt bloat on INSIDE routes | Low | 4–6 lines added; within acceptable range; INSIDE routes already carry belief_text + BSM |
| BSM content redundancy | None | Verified: distinct content domains |
| `snapshot()` per-request DB cost | Low | 4 × `SELECT ... LIMIT 1` on sense.db + 1 × `SELECT ... LIMIT 30` on beliefs.db; negligible at conversational pace |
| `state.membrane.self_model` absent | Handled | Guard condition mirrors BSM pattern |
| inside_beliefs always 0 in output | Not applicable | `format_self_state()` doesn't use `inside_beliefs`; the data gap is invisible to the LLM |
| `format_self_state` import at call site | Low | Inline `from ... import` inside try block; consistent with server.py patterns |

---

## 6. DOCTRINE §3-4 Alignment

**§3 (Belief field integration):** SelfModel draws from the interoception sense stream, which reflects the belief DB state (count, tier distribution, locked count). The injection makes the belief graph's own health visible to the LLM on self-inquiry queries — belief field informing the voice layer directly.

**§4 (Lifecycle protocol — SentienceNode):** SelfModel already implements the full protocol (`tick()`, `decay()`, `state()`). B1 adds the missing chat-path call site. The module is untouched; only the wiring in `gui/server.py` changes.

---

## 7. DOCTRINE §6 Six-Point Gate (B1.3 plan)

| Gate | Status | Verification |
|------|--------|-------------|
| #1 Module + tests | ✓ existing | `self_model.py` exists; no module changes needed |
| #2 Wired into chat pipeline | ✗ → B1.2 fix | After B1.2: call site in `api_chat()` on INSIDE routes |
| #3 Real-traffic validation | B1.3 | 5 self-inquiry queries: "what are you?", "tell me about yourself", "what defines you?", "how are you feeling?", "who are you really?" |
| #4 Five-query smoke | B1.3 | Standard set (no regression) |
| #5 Log fills | B1.3 | `/tmp/nex5_self_model.log` ≥5 entries with `locked=317` |
| #6 Jon quality call | PAUSE here | Jon reviews this doc + sample output before B1.2 |

---

## 8. Remaining Open Question

`snapshot()` without `dynamic_state` gives CPU + time + belief count + locked + Alpha. With `dynamic_state` (available in server via `state.membrane.self_model._dynamic`), it additionally gives pipeline_runs, active_branches, hottest_branch. The membrane was presumably constructed with `dynamic_state` — verify this in `build_state()` before B1.2.

If `state.membrane.self_model._dynamic` is None at runtime, the attention + meta_awareness lines will be absent from the output. This is graceful degradation, not a failure. The locked count and belief count will still surface.
