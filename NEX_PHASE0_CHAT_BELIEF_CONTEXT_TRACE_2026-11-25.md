# NEX Phase 0 — Chat Belief-Context Assembly Trace (25 November 2026)

**Branch/source:** `claude/nex-continuity-wire`, audited source snapshot `de93134f34adac07a3a41c2a05b33720510a2bfc`.
**Evidence:** L2 static-source tracing only. No runtime, database, environment, service, or behaviour was changed.

## 1. Initial retrieval and provenance boundary

In `gui/server.py:1204–1263`, `belief_text` starts empty and is populated from one of two paths:

1. If Membrane and World Model are both available, `state.membrane.route()` supplies `belief_text` and an optional register hint.
2. Otherwise, if World Model exists, the GUI retrieves up to three beliefs, filters them to at least two shared content tokens with the prompt, formats them, and truncates the rendered block to about 800 characters.

Immediately after this initial retrieval, the route assigns:

```python
_retrieved_belief_text = belief_text
```

This is the pre-augmentation snapshot. The source comment explicitly identifies it as the retrieved belief block before later self-model, harm, problem, affect, drive, and other injections. The provenance snapshot later receives this value as `prompt_beliefs` (`gui/server.py:2035–2041`), rather than the final fully assembled `belief_text`.

**Interpretation:** provenance's `prompt_beliefs` field represents the initial retrieval result, not the entire final interior context. It does not by itself attribute the additional prompt blocks listed below.

## 2. Ordered augmentation of `belief_text`

After the initial snapshot, the route appends context in this source order when each component returns content:

| Source order | Component / context | Condition and source location |
|---:|---|---|
| 1 | BehaviouralSelfModel metrics | INSIDE route only; calls `tick()`, then `format_for_prompt()`; `gui/server.py:1265–1288` |
| 2 | Harmonizer tension summary | INSIDE route only; ticks Harmonizer and appends formatted state when active paradox count is positive; `1320–1344` |
| 3 | Active disturbance pair | World Model present, disturbance exists, and register is Philosophical/AUTO/unspecified; appends the two tension contents and decrements remaining cycles; `1347–1362` |
| 4 | Matching open-problem context | ProblemMemory present and a prompt match exists; formats the first match; `1364–1385` |
| 5 | Metacognition summary | Component present; ticks and appends `format_for_prompt()`; `1415–1440` |
| 6 | NovelAssociation annotation | Component present and an unannotated association is returned; `1442–1466` |
| 7 | SelfNarrative entries | Component present; formats topic-matched autobiographical entries using the first 100 prompt characters; `1468–1480` |
| 8 | AffectState summary | Component present; appends current mood/valence format; `1482–1493` |
| 9 | DriveEmergence summary | Component present; appends current drive topic; `1495–1506` |
| 10 | SelfMindView summary | Component present; appends `current_summary()` as current cognitive state; `1508–1519` |
| 11 | SocialPresence summary | Component present; appends `current_summary()` as current social posture; `1521–1532` |
| 12 | Tool result prompt | Tool caller and registry present, a tool is selected, and execution succeeds; appends tool prompt; `1534–1549` |
| 13 | Philosophical standing-points | For an allowed thin register and low `belief_count`, samples up to four `source='spectrum'` rows and appends Tier-1 formatted entries; `1686–1703` |
| 14 | Working Memory | Session and WorkingMemory available, Conversational register, and `belief_count` meets the minimum; appends up to five active attended items; `1705–1714` |
| 15 | Operator HYBRID grounding | Admin + operator-composition path + VoiceEngine substrate hit; prepends the stored candidate to the existing interior; `1732–1783` |

The GoalManager is queried at `gui/server.py:1393–1413`, but the active goal is only written to an observability log. The source comment explicitly records that the old goal-text prompt injection was removed (SEAM 3). It is not a current Chat `belief_text` producer in this route.

A previous duplicate recent-conversation transcript block was also removed. The retained dialogue-history path is the separate `convo` faculty block in the 13-block assembly note; the old `[user]/[nex]` copy is not appended at the removed seam (`gui/server.py:1716–1721`).

## 3. Belief-count measurement boundary

At `gui/server.py:1632`, the route computes:

```python
belief_count = belief_text.count("- [Tier") if belief_text else 0
```

This is a count of rendered marker strings in the then-current composite `belief_text`. It is not a direct SQL count of retrieved belief rows. At this point it includes the initial retrieval and any earlier successful appends (BehaviouralSelfModel, Harmonizer, disturbance, ProblemMemory, Metacognition, NovelAssociation, SelfNarrative, AffectState, DriveEmergence, SelfMindView, SocialPresence, and successful tool injection). It occurs before the later Philosophical standing-point and Working Memory appends.

That value controls the thin-context refusal for non-probe, non-social queries in registers outside the allowed-thin set (`1631–1668`), and it also gates the later Philosophical standing-point and Working Memory conditions. Whether all earlier formatted blocks can contain the literal marker `- [Tier` has not been exhaustively tested in this tranche.

**Evidence gap / candidate measurement question:** the name `belief_count` can be read as a count of retrieved beliefs, but source semantics are a string-marker count over a mixed context buffer. Establishing whether any non-belief block contributes the marker, and whether that is intended, requires formatter-level tests. No behavior change is proposed.

## 4. Final route distinctions

- The ordinary LLM path assembles the 13 faculty blocks and then uses the fully augmented `belief_text` in the `Your interior right now` section when it is non-empty (`gui/server.py:1985–2020`).
- A VoiceEngine substrate hit can set `text` before the normal composition block. For a non-admin hit, the candidate is returned verbatim and the faculty blocks plus augmented `belief_text` are not consumed by that reply. In the admin HYBRID path, the candidate is prepended as grounding and the LLM composes from the resulting interior.
- A VoiceEngine miss continues to the LLM composition path.
- Repeat and provenance-cue regeneration reuse the assembled `voice_prompt`, with bounded additions to the prompt. They do not rebuild the initial retrieval snapshot.
- The final reply is sanitized and persisted to `conversations.messages`; the current source trace does not show a CoherenceGate decision on this user-facing reply path.

## 5. Evidence limits and next increment

This trace establishes source order and conditional inclusion, not actual host component presence, environment flags, tool execution frequency, model attention, or causal influence. It also does not settle whether Chat replies themselves fall within the governing universal-gate scope.

Next bounded source-only increment: inspect the formatters and data readers behind the appended blocks, particularly whether the string-based `belief_count` can be incremented by non-belief content and whether the provenance snapshot intentionally excludes the appended context. Compare formatter semantics and existing tests; do not alter behaviour pending the canonical Frozen V2.1 authority and Gate 0 review.
