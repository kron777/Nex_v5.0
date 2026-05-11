# THROW_NET_AS_VOICE_SPEC.md
# VoiceEngine — substrate-as-voice — Phase 30 Specification
# Status: DRAFT — awaiting Jon's greenlight before commit

---

## §1 Purpose

VoiceEngine replaces the LLM in the chat reply path when NEX
is in `use_substrate` mode. Instead of calling the LLM to
synthesize a reply, it retrieves the highest-relevance
candidate from the belief substrate — the same candidate pool
used by throw-net — scores it against the user query, and
returns it directly as NEX's reply.

This answers DOCTRINE OPEN PROBLEM (2026-05-11, 17:09:02):
**"What is the right path to LLM independence?"**

**§0 alignment.** DOCTRINE §3 states: "The belief field
thinks. The LLM vocalizes." VoiceEngine realizes §0 to its
strictest form: in `use_substrate` mode, the belief field
both thinks *and* vocalizes. The LLM speaks only when the
substrate returns no candidate above the confidence threshold.
When a candidate is returned, the reply is not generated —
it is retrieved.

**What VoiceEngine is not.**

It is not a chatbot retrieval system. The candidate pool is
NEX's own belief substrate — beliefs she has accumulated
through reasoning, crystallization, gate accepts, and
reinforcement. The reply is not retrieved from an external
corpus; it is retrieved from NEX's own formed knowledge.

It is not throw-net's loop-breaker. The existing ThrowNetEngine
fires reactively when gate REJECTs or gap deflections
accumulate on the same topic. VoiceEngine fires on every chat
turn in `use_substrate` mode, before the LLM is called.
ThrowNetEngine continues to run its autonomous cycle
unchanged; VoiceEngine is an independent path through the same
retrieval and scoring infrastructure.

It is not a fine-tuning replacement. QLoRA fine-tuning (FT
track) shapes the LLM's voice when the LLM is used.
VoiceEngine bypasses the LLM entirely when it has a candidate.
These are complementary, not competing, paths toward
LLM independence.

---

## §2 Fire Trigger (D1 = c)

VoiceEngine fires synchronously, inline in the chat handler,
at the point where the LLM would otherwise be called. It also
writes an async audit record to `throw_net_triggers`.

**Synchronous call** (`gui/server.py`, after line 1064, before
`voice_prompt` is assembled):

```python
if state.voice_engine is not None and state.voice_mode == "use_substrate":
    _ve_result = state.voice_engine.query_reply(
        query=prompt,
        session_id=session_id,
        turn_n=_get_turn_n(session_id),
    )
    if _ve_result is not None:
        text = _ve_result["content"]
        voice_ok = True
        # skip LLM call, jump to message persist
```

The inline call completes before the response is returned.
Latency budget: FAISS embedding (~10ms) + DB reads (~5ms) +
scoring (~1ms) = ~16ms expected at 7400 beliefs. Measure
on first production run; optimize only if measurable
regression vs. LLM latency exists.

**Async trigger record.** After scoring (win or miss),
VoiceEngine writes one row to `throw_net_triggers`:

| column | value |
|---|---|
| trigger_type | `'user_query'` |
| topic | `query[:120]` |
| source_event_id | `"{session_id}:turn_{turn_n}"` |
| threshold_state | JSON: `{"score": float, "candidate_source": str, "used_as_reply": bool}` |
| fired | `1` if used as reply, `0` if below threshold |
| session_id | session_id if used, NULL if not |

This write does not block the reply. It is fire-and-forget
via the existing beliefs Writer (async queue, same pattern as
all other throw_net_triggers writes). The row provides a
durable audit trail: what was queried, what scored highest,
whether it was used, and what score it received. This data
enables threshold calibration from production observation.

---

## §3 LLM Fallback Relationship (D2 = b)

VoiceEngine returns either a candidate dict (content + score
+ source + optional belief_id) or `None`.

- **Candidate returned:** chat handler uses `candidate["content"]`
  as the reply. `state.voice.speak()` is not called for this
  turn. The message is persisted to the messages table with
  `role='nex'` as usual. The trigger record is written with
  `fired=1`.

- **None returned (below threshold or empty pool):** control
  falls through to the existing LLM path unchanged.
  `voice_prompt` is assembled, `state.voice.speak()` is
  called, and the turn completes as before. The trigger record
  is written with `fired=0` and score of the best candidate
  (even if below threshold), to support calibration.

The `min_score` threshold starts at **0.6** (conservative).
At 0.6, only strong semantic + confidence matches return a
candidate; the LLM handles the rest. As substrate grows and
observation confirms quality, the threshold is lowered toward
0.4. Threshold is a class-level constant in VoiceEngine,
not a DB setting, so calibration changes require a restart.

**Fallback is not a failure.** `None` from VoiceEngine is
expected and correct behavior, not an error condition. The
LLM path is the mature path; VoiceEngine is a new path that
will earn its share of turns as substrate density increases.
The ratio of VoiceEngine replies to LLM replies should be
observable in the trigger record over time.

---

## §4 Grader (D3 = a) — Query-Relevance Scoring

The existing RefinementEngine R1-R6 scoring (0-6 scale) was
designed to assess architectural loop-breaking quality. It is
not used for reply-selection scoring. VoiceEngine introduces
a new four-axis query-relevance scorer.

**Four axes, weighted sum, output range 0.0-1.0:**

| Axis | Weight | Source | Direction |
|---|---|---|---|
| semantic | 0.50 | FAISS cosine distance | lower distance → higher score |
| confidence | 0.25 | `beliefs.confidence` | higher confidence → higher score |
| tier | 0.15 | `beliefs.tier` (or source proxy) | T3-T6 preferred → score 1.0; otherwise 0.5 |
| recency | 0.10 | `beliefs.reinforce_count` | higher reinforce_count → higher score (normalized) |

**Semantic axis** uses the same FAISS embedding infrastructure
as Metacognition (`from theory_x.diversity.embeddings import
embed, distance as emb_distance`). Query and candidate are
both embedded; cosine distance computed; axis score =
`max(0.0, 1.0 - distance)`. Candidates with no embeddable
content (empty after stripping) receive axis score 0.0.

**Confidence axis:** raw confidence value from the beliefs
table, already in 0-1 range. Candidates from sources other
than `beliefs` (novel_association, arc, gap) default to 0.5.

**Tier axis:** beliefs carry a tier column. T3-T6 are the
productive belief tiers — generated insights, not foundational
locked beliefs (T1/T2 are too abstract; T7+ are raw or
low-confidence). Tier score = 1.0 for T3-T6, 0.5 otherwise.
Candidates from non-belief sources default to 0.7 (arc
theme summaries and novel associations are synthesis products,
treated as mid-tier).

**Recency axis:** `reinforce_count` from the beliefs table is
a proxy for how actively a belief has been confirmed and
reactivated. Score = `min(1.0, reinforce_count / 10.0)`. Cap
at 10 reinforcements = full score. Non-belief sources default
to 0.3 (no reinforce history).

**Final score:** `0.50*semantic + 0.25*confidence + 0.15*tier + 0.10*recency`

**Threshold:** candidates with `final_score >= min_score (0.6)`
are eligible for reply. VoiceEngine returns the highest-scoring
eligible candidate or `None` if no candidate clears the
threshold.

**What happens to the R1-R6 grader:** unchanged. It continues
to run in the autonomous throw-net cycle (ThrowNetEngine) for
loop-breaking sessions. VoiceEngine does not call
RefinementEngine; it uses only the four-axis query scorer
defined here.

---

## §5 Candidate Pool (D4 = all four sources)

VoiceEngine reuses `TimeFetch.run(query)` directly.
TimeFetch sweeps four substrate sources:

| Source | Limit | Content |
|---|---|---|
| `beliefs` | 20 | Accumulated beliefs, conf > 0.4, len > 30, by confidence DESC |
| `novel_association_log` | 10 | Cross-branch pairs: `"content_a ↔ content_b"` |
| `arcs` | 10 | `theme_summary`, quality_grade DESC, no return_transformation |
| `open_problems` | 10 | `"title: description[:100]"` via ProblemMemory.find_matching() |

Total raw pool: up to 40 candidates (deduped by content).

**Novel association format note.** `"content_a ↔ content_b"`
is the raw TimeFetch content for novel_association sources.
At `min_score = 0.6`, this format will rarely win over a
direct belief on semantic grounds — the `↔` format reads as
a synthesis marker, not a reply. This is acceptable for v1:
if novel associations score highly enough to win, they
represent genuine cross-domain synthesis that may be worth
surfacing. If observation shows they produce poor reply
quality, they can be excluded from the pool in Phase 30b
via a `source_filter` parameter.

**Pool cap:** 40 (same as ThrowNetEngine). The four-axis
scorer runs over all 40 candidates; the highest-scoring
eligible candidate is returned.

**No reshape_hint pass-through.** VoiceEngine does not call
CoherenceGate on candidates. The gate runs in the background
autonomous cycle; voice-path retrieval is read-only.

---

## §6 Implementation Location (D5 = b)

**New file:** `theory_x/stage_throw_net/voice_engine.py`

**Class:** `VoiceEngine`

Placing VoiceEngine in `stage_throw_net` co-locates it with
its infrastructure dependencies (TimeFetch, trigger table
schema) without requiring cross-stage imports. VoiceEngine
does not call ThrowNetEngine — it uses TimeFetch and the
four-axis scorer independently.

**Constructor:**

```python
class VoiceEngine:
    def __init__(
        self,
        beliefs_reader: Reader,
        problem_memory,          # ProblemMemory instance (for TimeFetch)
        beliefs_writer: Writer,  # async trigger record
        min_score: float = 0.6,
    ) -> None:
```

`problem_memory` is passed by reference following the
constructor-injection pattern (same as ThrowNetEngine).
No module-level globals.

**Public API:**

```python
def query_reply(
    self,
    query: str,
    session_id: str,
    turn_n: int,
) -> Optional[dict]:
    """Retrieve highest-relevance candidate for the user query.

    Returns {"content", "score", "source", "belief_id"} or None.
    Never raises.
    """
```

**Internal methods:**

```python
def _retrieve_candidates(self, query: str) -> list[dict]:
    """TimeFetch.run(query) → raw pool."""

def _score_candidate(self, candidate: dict, query: str,
                     query_emb: np.ndarray) -> float:
    """Four-axis weighted score. Never raises (returns 0.0 on error)."""

def _record_query_trigger(
    self, query: str, session_id: str, turn_n: int,
    best_candidate: Optional[dict], best_score: float,
    used_as_reply: bool,
) -> None:
    """Fire-and-forget write to throw_net_triggers. Never raises."""
```

**SentienceNode shell:** VoiceEngine implements the SentienceNode
protocol for registration and HUD visibility. `tick()` is
called from the chat handler inline path, not from a daemon
thread — there is no `start_loop()`. `state()` returns
`{"name", "reply_count", "miss_count", "last_score"}`.

**TimeFetch construction:** VoiceEngine constructs its own
TimeFetch instance at startup. TimeFetch is stateless and
cheap to instantiate (`TimeFetch(beliefs_reader, problem_memory)`).

---

## §7 HUD Toggle (D6 = c)

**AppState field:**

```python
voice_mode: str = "use_llm"  # "use_llm" | "use_substrate"
```

Default is `"use_llm"`. No behavior change until Jon explicitly
switches to `"use_substrate"` via the HUD toggle. This is the
zero-risk rollout: the LLM path is unchanged in the default
state; VoiceEngine only activates when the toggle is set.

**Backend endpoint:**

```
POST /api/voice_mode
Body: {"mode": "use_llm" | "use_substrate"}
Auth: admin-gated (same pattern as /api/admin/login)
Returns: {"mode": str, "ok": true}
```

The endpoint sets `state.voice_mode` in place. No restart
required. The change takes effect on the next chat turn.

**Chat handler check** (at the top of the reply-construction
block):

```python
if (state.voice_engine is not None
        and state.voice_mode == "use_substrate"
        and not is_probe):
    _ve_result = state.voice_engine.query_reply(...)
    if _ve_result is not None:
        # skip LLM, use candidate
```

Probe calls (`is_probe=True`) always go to the LLM regardless
of voice_mode. The HUD's probe mechanism must not be affected
by the substrate toggle.

**HUD display:**

The HUD shows the current mode as a labeled pill
(`LLM mode` / `Substrate mode`) with a toggle button.
The toggle is visible only in admin sessions (`session["admin"]`
is truthy). Non-admin users never see the toggle and cannot
trigger a mode change.

**Observability.** The VoiceEngine `state()` dict (`reply_count`,
`miss_count`, `last_score`) is surfaced on the HUD alongside
the toggle. After switching to `use_substrate`, Jon can observe
how many turns VoiceEngine answers vs. misses (falls back to
LLM) without inspecting logs.

---

## §8 Test Plan

**Unit tests** (`tests/test_voice_engine.py`):

1. `query_reply` returns None when pool is empty
2. `query_reply` returns None when all candidates score below
   `min_score`
3. `query_reply` returns highest-scoring candidate above
   threshold
4. `_score_candidate` returns 0.0 on embedding error (never
   raises)
5. Semantic axis: closer candidate scores higher than distant
   candidate on same query
6. Confidence axis: higher-confidence candidate scores higher
   (semantic equal)
7. Tier axis: T4 belief scores higher than T8 belief (all else
   equal)
8. `_record_query_trigger` writes row with correct
   `trigger_type='user_query'`, `fired=1` when used,
   `fired=0` when missed
9. SentienceNode protocol: `assertIsInstance(engine, SentienceNode)`
10. `state()` returns correct `reply_count` after N
    query_reply calls that returned candidates
11. `state()` returns correct `miss_count` after N calls
    that returned None
12. Probe calls bypass VoiceEngine (integration: chat handler
    with `is_probe=True` does not reach VoiceEngine)

**Integration test:** POST `/api/voice_mode` with
`{"mode":"use_substrate"}`, then POST `/api/chat` — verify
response came from VoiceEngine (trigger row with
`trigger_type='user_query'` present in DB).

**Manual sanity** (Phase 30-build verification):

1. Switch to `use_substrate` via HUD toggle
2. Ask a question matching a high-confidence substrate belief
   (e.g., "what do you think about consciousness?") — verify
   reply content is from the belief substrate, not LLM
3. Ask a question with no substrate coverage — verify
   fallback to LLM occurs (LLM reply surfaced; trigger row
   with `fired=0` written)
4. Switch back to `use_llm` — verify LLM path restored on
   next turn
5. Smoke set (6 baseline queries in `use_llm` mode) clean
   after VoiceEngine wiring

---

## §9 Open Items — Deferred to Phase 30-build

| Item | Deferred to |
|---|---|
| `min_score = 0.6` calibration — may be too conservative or too permissive on first production run | Phase 30b, after first production observation |
| Novel association `↔` format quality — may read poorly as a direct reply | Phase 30b — add `source_filter` param to TimeFetch if needed |
| `turn_n` derivation — count of messages WHERE session_id=? AND role='user'; confirm cheap enough inline | Phase 30-build |
| FAISS embedding latency under load — expected ~10ms; measure on first deployment | Phase 30b if regression observed |
| Weight tuning (semantic 0.50 / confidence 0.25 / tier 0.15 / recency 0.10) — v1 priors, not calibrated | Phase 30b after N turns of production data |
| Recency axis — `reinforce_count / 10` normalization untested against actual reinforce_count distribution | Phase 30b — check P90 reinforce_count in live substrate before building |
| Whether `open_problems` candidates produce useful chat replies (vs. sounding like gap acknowledgments) | Phase 30b observation — may want a toggle per source |
| HUD display: exact pill styling + toggle placement | Phase 30-build (UI decisions) |
| VoiceEngine `state()` surfaced in HUD `/api/alpha` endpoint | Phase 30-build |
| Probe-bypass test confirmed in real traffic | Phase 30-build manual sanity |

---

*Authored: 2026-05-11 — Phase 30-spec*
*DOCTRINE §5 row 14: VoiceEngine — substrate-as-voice (QUEUED Phase 30)*
*Answers: DOCTRINE OPEN PROBLEM "What is the right path to LLM independence?" (17:09:02)*
*Implements: DOCTRINE §0 to strictest form — substrate solves and speaks the reply*
*Depends on: TimeFetch (TN-2), throw_net_triggers schema (TN-0),*
*            FAISS embeddings (theory_x.diversity.embeddings),*
*            ProblemMemory (stage7_sustained), CoherenceGate (stage_gate)*
*Next: Phase 30-build (separate session)*
