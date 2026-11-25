# NEX Phase 0 — Chat Composition Route Trace (25 November 2026)

**Scope:** bounded static-source continuation of the active host branch `claude/nex-continuity-wire` at `de93134f34adac07a3a41c2a05b33720510a2bfc`. This note traces the GUI Chat composition blocks and their final inclusion boundary. It does not establish host flags, live route frequency, model consumption, or causal influence.

**Evidence class:** L2 / static source only. No runtime, database, service, flag, or behavioural state was changed.

## 1. Route boundary

The normal `POST /api/chat` route first persists the incoming user message, then attempts Membrane routing when both Membrane and World Model are available. Otherwise it uses the direct World Model retrieval fallback. The resulting `belief_text` is then augmented by route-dependent self-model and other context injections before faculty blocks are assembled.

The two Membrane routes are distinct:

- **INSIDE:** QueryRouter snapshots SelfModel, formats the self-state, and retrieves up to five INSIDE-filtered beliefs. The GUI then ticks BehaviouralSelfModel and appends its formatted metrics. The GUI also appends active Harmonizer tension when present.
- **OUTSIDE:** QueryRouter retrieves up to eight ordinary relevant beliefs using active Dynamic branches as hints. The INSIDE-only BehaviouralSelfModel and Harmonizer additions are not applied by those explicit route guards.

If Membrane routing raises, the route records the error; the source does not establish a guaranteed fallback to a fresh direct retrieval in that same exception branch. If Membrane is absent but World Model exists, the direct retrieval fallback uses up to three beliefs, a two-content-token overlap filter, and an approximately 800-character cap.

Sources: `gui/server.py:1145–1310`; `theory_x/stage4_membrane/router.py:28–95`.

## 2. Thirteen assembled Chat context blocks

The GUI builds thirteen named blocks and passes them in a fixed order to `_assemble_chat_blocks()` at `gui/server.py:1985–2004`.

| Order | Block | Source inclusion condition |
|---:|---|---|
| 1 | `operator` | `NEX5_OPERATOR_MODEL=1` and admin session |
| 2 | `operator_anchor` | `NEX5_OPERATOR_ANCHOR=1` and admin session |
| 3 | `compassion` | `NEX5_COMPASSION=1` and admin session |
| 4 | `compass` | `NEX5_COMPASS=1` and admin session |
| 5 | `equanimity` | `NEX5_EQUANIMITY=1` and admin session |
| 6 | `apramada` | `NEX5_APRAMADA=1` and admin session |
| 7 | `virya` | `NEX5_VIRYA=1` and admin session |
| 8 | `sraddha` | `NEX5_SRADDHA=1` and admin session |
| 9 | `prasrabdhi` | `NEX5_PRASRABDHI=1` and admin session |
| 10 | `affect_carry` | `NEX5_AFFECT_CARRY=1` and admin session |
| 11 | `convo` | `NEX5_CHAT_MEMORY=1` and admin session |
| 12 | `spectrum` | Best-effort sample of up to six `source='spectrum'` beliefs; no separate flag in this block builder |
| 13 | `tag` | Best-effort tag summary and up to four prompt-keyword matches; underlying `tag_retrieval` functions return empty when `NEX_TAG_FEEDBACK_ON` is not `1` |

The optional admin-scoped blocks fail safe to empty strings on errors. The conversation block uses `_recent_dialogue(...)` only when admin-scoped chat memory is active. The spectrum block attempts a random six-row sample on every composition path; it is empty if no matching rows are returned or the read fails. The tag helper enforces its own feature flag in `feedback_enabled()`, despite the GUI always calling the helper functions.

Sources: `gui/server.py:1670–1684, 1784–2004`; `theory_x/coincidence/tag_retrieval.py:1–31, 120–175`.

## 3. Assembly and workspace selection

`_assemble_chat_blocks()` has two materially different source-level modes:

- With `NEX5_CHAT_WORKSPACE` unset or not equal to `1`, it returns the concatenation of all thirteen block strings in their listed order. This is the default path.
- With `NEX5_CHAT_WORKSPACE=1`, it calls `select_within_budget()` using a default 1,400-character budget, overridable through `NEX5_CHAT_WORKSPACE_BUDGET`. The salience map is provisional and block-specific. `compassion` and `compass` are marked exempt from eviction. If `NEX5_SELF_PRESENT=1` as well, salience may be updated from cross-turn state; failure falls back to this-turn salience. Any outer workspace exception falls back to full concatenation.

The workspace is therefore a context-selection mechanism, not proof that every generated block reaches the model. The default-OFF path concatenates all block strings, including empty strings. When enabled, some non-exempt blocks may be omitted to meet the budget.

Sources: `gui/server.py:150–197`.

## 4. Final prompt composition

After assembly:

- If `belief_text` is truthy, the prompt is the concatenated faculty blocks, followed by the `Your interior right now:` section containing `belief_text`, followed by the user prompt and response instructions.
- If `belief_text` is empty, the prompt is the concatenated blocks immediately followed by the user prompt; if both are empty, the raw user prompt is used.

This is the normal LLM-composition prompt boundary. It is not the only Chat reply route: the separate VoiceEngine substrate-first hit path can set `text` before this composition block and return a stored candidate without consuming these assembled faculty blocks. A VoiceEngine miss falls through to LLM composition. See the existing producer/consumer tranche §§48–50.

Sources: `gui/server.py:1735–1768, 1985–2020`.

## 5. Evidence gaps and limits

1. The source map proves construction and prompt inclusion conditions, not the effective host environment values or which flags were active during any historical turn.
2. The source map does not prove that the language model attended to, followed, or was causally influenced by any particular block.
3. The workspace selection path is not verified live; no selection trace or block-level causal attribution is available here.
4. The spectrum query filters only by `source='spectrum'` in this call. Whether spectrum rows have any status/lifecycle semantics requiring further filtering is not decided by this trace.
5. This note does not adjudicate whether all Chat outputs, only autonomous belief candidates, or some narrower class fall under the governing CoherenceGate requirement. That remains blocked on the canonical Frozen V2.1 specification and founder authority clarification.
6. This is a GUI Chat path trace, not a complete crosswalk of all Chat, VoiceEngine, tools, probes, retries, and external publication paths.

## 6. Next bounded increment

Continue the source-only audit by tracing the complete construction and use of the `belief_text` context: each append site, the exact provenance snapshot boundary, and the prompt variants for normal LLM, operator HYBRID, substrate-hit, and retry/regeneration routes. Keep runtime and behavioural state untouched until the governing authority and Gate 0 requirements are resolved.
