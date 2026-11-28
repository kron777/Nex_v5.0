# NEX chat faculty wire map — 2026-11-28

**Evidence snapshot:** NEX main at 3377197c4d216aedc7708a9d1ee758144bd0b09b (post-G-84 producer and StrikeProtocol shutdown integration)  
**Scope:** source trace of the existing chat-time cognitive/affective faculty blocks. No code, runtime state, feature flag, threshold, prompt policy or frozen specification changed.

## 1. What is connected to the central response path

The relevant path in gui/server.py is:

```text
human sentence
  -> chat route / membrane / belief and self-state context
  -> individual faculty reads
  -> ordered faculty blocks
  -> _assemble_chat_blocks(...)
  -> voice_prompt
  -> VoiceClient.speak(...)
  -> response
```

The faculty modules are called synchronously during chat prompt assembly. Their outputs are primarily short textual stances or cues. They are not all subscribers to one shared Cognitive_Event_Bus, and this path does not demonstrate unconstrained recursive propagation between nodes. The verified integration mechanism here is a call graph and a composed prompt.

The final ordered block list is:

1. operator
2. operator_anchor
3. compassion
4. compass
5. equanimity
6. apramada
7. virya
8. sraddha
9. prasrabdhi
10. affect_carry
11. convo
12. spectrum
13. tag

The assembled block string is inserted into the same voice prompt as the retrieved interior/belief context and the user's current sentence. That is the point where these faculties can subtly change the response's tone, attention, stance, confidence or continuity.

## 2. Faculty-by-faculty source trace

| Faculty | What it reads | What it contributes | Persistence / authority boundary |
|---|---|---|---|
| compassion (karuṇā) | The person's incoming sentence, using semantic distress-vs-neutral embedding anchors | A bounded, decaying care/non-harm stance when distress is sufficiently salient | A small compassion_state record is persisted in conversations.db; it does not write beliefs/world state. Prompt-only influence |
| compass (dharmic compass) | Compassion, amoha/clarity, affliction/distortion reads and semantic moral-weight salience | A provisional, situated, held-open moral lean | Reads other faculties without mutating compassion. Not a rule engine, verdict, fixed action map or action gate |
| equanimity (upekkhā) | NEX's internal rāga/fixation and dveṣa/aversion levels; the person's distress read | A graded hold-steady cue when internal pull is hot | Explicitly silent when compassion is live above its guard. Prompt-only |
| apramāda (conscientiousness) | Unresolved momentum threads, open problems and token overlap with the current sentence | A vigilance cue when a held commitment is at risk of being dropped | Does not nag when the thread is being attended or has exceeded its carry cap. Prompt-only |
| vīrya (joyous effort) | Current hard thread/open problem and recent Fountain outputs to estimate drift away from focus | A bounded lean-back-in cue when NEX is drifting from a difficult active thread | Yields when upekkhā reports a hot pull; prompt-only |
| śraddhā (warranted confidence) | Relevant beliefs and their tier, confidence, corroboration and graph connectivity | A graded signal that NEX can stand on genuinely well-supported material | Thin support stays silent; it does not manufacture confidence. Prompt-only |
| praśrabdhi (pliancy) | Rāga/circling plus whether recent work is on or off the current hard focus | A release/shift cue when circling is aimless and off-focus | Silent when sustained work is legitimate. Behavioural nudge, not a content cut or action gate |
| affect-carry | Current and previous conversational affect, including the compassion distress read | A decaying tone-colour carried across turns, without naming the feeling | Per-session state in conversations.db; prompt-only tone influence |
| operator model | The held operator/architect read from its private intake | A Jon-facing stance/tone colour | Admin-scoped and default-off; not imported into published paths |
| operator anchor | The fact of who is speaking in the current admin session | Keeps direct second-person addressee framing stable | Admin-scoped and default-off; it anchors addressee, not authority |
| conversation memory | Recent dialogue turns | Restores conversational continuity | Admin-scoped flag; prompt context only |
| spectrum | Existing beliefs with source='spectrum' | Standing-points from which the system frames a philosophical response | Read-only retrieval from beliefs.db |
| tag | Stored tagged thoughts and tags matching the current sentence | Relevant prior tagged thoughts | Retrieval helper is a no-op unless NEX_TAG_FEEDBACK_ON=1 |

## 3. Important cross-faculty influences

These are actual source-level dependencies, not inferred similarities from names:

- **Compassion → Compass:** Compass reads the situated compassion signal as one dimension of its moral-weight assessment. It composes that with clarity and affliction/distortion reads; it does not simply echo compassion.
- **Compassion → Equanimity:** Equanimity checks compassion distress and deliberately stays silent when care is live. This prevents “steadiness” from flattening a warranted compassionate response.
- **Compassion → Affect-carry:** Affect-carry uses the distress read to seed conversational affect continuity, then decays and integrates the current turn.
- **Equanimity → Vīrya:** Vīrya yields when upekkhā indicates a hot fixation/aversion pull; it does not intensify an already-hot state.
- **Vīrya ↔ Praśrabdhi (shared focus question):** Both inspect the current hard thread and recent Fountain drift. Vīrya sustains legitimate effort on the hard thread; praśrabdhi releases only aimless circling away from it. They are complementary, not interchangeable.
- **Apramāda → held commitments:** It reads momentum and open-problem records to detect a likely dropped thread; it does not infer a new goal from the sentence.
- **Śraddhā → belief substrate:** Its confidence cue depends on actual belief metrics and semantic relevance. It is not a general confidence score for every response.

## 4. Prompt assembly and competition

Each faculty is called only when its own environment flag is enabled and the admin-session condition is satisfied, except for the spectrum read and the tag helper's own internal flag handling. The source defaults for the named NEX5 faculty flags are OFF. The actual host environment values were not inspected, so live activation is UNKNOWN.

NEX5_CHAT_WORKSPACE is a separate prompt-assembly mechanism:

- OFF (default): concatenate the available blocks in their authored order.
- ON: select by configured salience within a character budget.
- compassion and compass are exempt from eviction in that workspace selector.

This is competition for limited prompt space, not a cognitive action score and not an authority to approve, block or veto machine operations. It can still change which aspects influence a particular reply, so its effects need separate characterization when armed.

Do not confuse this chat selector with the other Global Workspace path in the same module. Fountain-side arbitration uses candidates such as surprise, stakes, momentum, Bonsai focus and drive to frame one leading signal. Chat-side selection uses the thirteen faculty text blocks and keeps multiple blocks within a character budget. They reuse the global_workspace module but have different inputs, output semantics and downstream effects. Likewise, the Stage-2 Bonsai branch-focus vector is not the same thing as the per-faculty chat salience vector.

### Cross-turn carry: NEX5_SELF_PRESENT

When both NEX5_CHAT_WORKSPACE=1 and NEX5_SELF_PRESENT=1, _assemble_chat_blocks() passes the raw per-kind salience vector through theory_x.stage_tom.self_present.update() before selection.

- The previous per-session vector is loaded from conversations.db.
- Each carried kind is blended as 0.7 × previous salience + 0.3 × this turn's raw salience, clamped to [0, 1].
- New kinds begin at this turn's raw salience.
- The complete vector, current winner and turn count are persisted.
- The blended vector then feeds the chat block budget selector.

This is a real feedback edge: which faculty was prominent on a previous turn can influence which faculty gets prompt space on the next turn. The tests in tests/test_self_present.py demonstrate that a previously leading block can retain the lead for one changed turn, but a sustained new signal eventually takes over.

The carry is turn-based rather than wall-clock-decayed in the inspected implementation. Its live activation is UNKNOWN. This is structured salience continuity, not persistence of a rendered thought and not authority over an action.

## 5. Tests and evidence boundaries

The current test tree contains dedicated suites for compassion, compass, affect-carry and operator-model behaviour. Those suites cover useful isolated dynamics and some route-level injection/guard behaviour.

The path inventory does not show standalone test files named for upekkha, apramada, virya, sraddha or prasrabdhi. This does not prove there is no incidental coverage elsewhere; it means their direct source-to-prompt and pairwise interaction evidence should be checked explicitly before changing their wiring.

The inspected code establishes the source-level calls and their prompt assembly. It does not establish which flags are active on the live host, how much each block changes generated responses, or whether all simultaneous combinations remain stable.

## 6. Development implications

1. Do not add another copy of any of these faculties. They already exist as distinct modules.
2. Do not collapse their meanings into one generic “emotion” or “morality” score.
3. Preserve their asymmetries and silences: compassion is other-directed; equanimity must not suppress compassion; vīrya sustains legitimate effort; praśrabdhi releases aimless circling; śraddhā requires real evidence.
4. Keep their influence at the prompt/interpretation layer. The Tibetan Mind Aspects are not action-control gates.
5. Before changing a wire, test the individual source, its consumer, the pairwise interaction, the combined prompt, and the post-connection effect on the wider chat path.
6. Separate source availability from live activation and behavioural effect. A module existing in the repository is not proof it is active.

This map is a source-traced baseline for the next integration cycle. It is not a claim that the whole cognitive network is complete or that its emergent behaviour has been fully measured.
