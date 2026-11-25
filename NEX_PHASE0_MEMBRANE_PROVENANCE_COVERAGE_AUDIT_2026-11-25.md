# NEX Phase 0 — Membrane route and provenance coverage audit
Date: 2026-11-25

## Scope

Static inspection at commit `9397ab1da304862b7a09c1fcafc4de326993904b`.
Inspected the membrane router, self-model formatter, shared belief formatter,
tool registry/caller, provenance parser and snapshot, relevant tests, and the
Chat prompt assembly in `gui/server.py`.

This is source evidence only. It does not establish live flags, live database
contents, actual tool invocation frequency, model attention, or runtime impact.

## 1. Membrane route construction

`QueryRouter.route()` selects one of two paths:

- INSIDE: `_inside_route()` calls `self_model.snapshot()`, formats it with
  `format_self_state()`, then retrieves up to five beliefs using
  `branch_hints=["systems"]` and `side_filter="INSIDE"`. The returned
  `belief_text` joins the self-state prose and formatted belief block.
  It sets `register_hint="philosophical"` and includes the snapshot for
  observability.
- OUTSIDE: `_outside_route()` derives active branch hints from dynamic state,
  retrieves up to eight beliefs, and returns the shared formatted belief
  block with no register override.

The fallback route in `gui/server.py` is distinct: it retrieves up to three
beliefs, applies the Chat-only two-token overlap filter, formats them, and
caps that rendered block at 800 characters. The membrane route does not pass
through that fallback filter/cap in the inspected code.

## 2. INSIDE self-state contains additional belief-derived text

`format_self_state()` includes up to three `inside_beliefs` as plain
`- Standing-points:` / `  - {content}` lines. These are sourced from the
self-model snapshot's separate `_get_inside_beliefs()` query, which selects
unpaused beliefs with tier <= 6 and then applies the membrane classifier.

This is distinct from the router's subsequent INSIDE-filtered retrieval.
The self-state standing-points are supplied to the model as context, but they
do not carry the shared formatter's Tier-line structure. The provenance
parser therefore does not normally include them in its parsed `belief_texts`.
The two sets may overlap, but the source does not guarantee identity.

This establishes a provenance coverage boundary: the snapshot can record the
formatted route belief lines while omitting belief-derived standing-points
also present in the same INSIDE prompt. It is not established whether the
intended provenance contract is meant to include those standing-points.

## 3. Tool-result path can add another formatted belief block before the gap gate

For explicit belief questions, `ToolCaller.should_use_tool()` can select
`beliefs_query`. The registry's `_beliefs_query()` retrieves up to five
beliefs and formats them with the same `format_beliefs_for_prompt()`.
On successful tool execution, `gui/server.py` appends the resulting tool
prompt to `belief_text` before calculating `belief_count`.

Therefore, when this branch succeeds, the composite buffer can contain
Tier-marked belief lines from both the initial route retrieval and the
tool-result retrieval. The count may represent repeated presentation of
beliefs rather than distinct belief records. The tool query's retrieval is
separate and is not deduplicated against the route retrieval in the inspected
path. Whether this occurs on a particular turn depends on query classification,
tool success, and actual retrieval results.

The web-fetch and Python tool outputs are also appended as free text on
successful execution; their output is not structurally typed as a belief block.

## 4. Provenance parser and embedded newlines

`parse_belief_block()` accepts lines matching an anchored Tier-line regular
expression and extracts the remainder of each matching line. The existing
tests cover ordinary Tier lines, a question-mark tier, short content and
unrelated prose. They do not cover embedded newlines inside belief content.

The shared formatter interpolates belief content verbatim. The self-state
formatter also interpolates inside-belief content verbatim. If either content
value contains a newline followed by text matching the Tier-line grammar, the
rendered prompt and provenance parser can treat that embedded line as a
separate belief line. This is a structural injection/attribution risk, not
evidence that any stored record currently contains such content.

## 5. Final prompt and snapshot coverage

The final composed LLM prompt can include:
- the route/fallback `belief_text` plus pre-gap-gate augmentations;
- later Philosophical spectrum standing-points;
- Working Memory lines for eligible Conversational turns;
- optional VoiceEngine RAG grounding on the admin/HYBRID path;
- the separately assembled operator, compassion, compass, equanimity,
  conscientiousness, effort, confidence, pliancy, affect-carry, conversation,
  spectrum-sample and tag blocks.

The provenance snapshot is created from `_retrieved_belief_text`, captured
immediately after initial route/fallback retrieval and before the later
augmentations. The parser extracts only Tier-shaped lines from that value.
Thus it is not a transcript of the full final prompt, nor a complete inventory
of all contextual influences on the reply. This may be appropriate for a
narrow belief-retrieval provenance measure; it must not be described as
complete prompt provenance.

The VoiceEngine substrate-hit path can return a stored answer directly and
skip the ordinary LLM composition/snapshot block. On a substrate miss, the
ordinary composition path continues. This route distinction remains relevant
when interpreting provenance coverage.

## 6. Test coverage observations

- `tests/test_membrane.py` verifies route selection, register hint and the
  presence of inner-state text; it does not assert the full set or provenance
  of all belief-derived content in the INSIDE route.
- `tests/test_provenance.py` verifies standard Tier-line parsing and snapshot
  persistence; it does not test newline-injected Tier markers, distinction
  between route beliefs and self-state standing-points, or duplicated
  tool-retrieval blocks.
- `tests/test_tools.py` verifies that tool prompt construction is non-empty;
  it does not assert how a successful beliefs_query affects the Chat gate's
  marker count.

These are coverage observations, not a recommendation to add tests before
the governing specification is confirmed.

## 7. Phase 0 disposition

Confirmed source facts:
- INSIDE prompt text includes self-state plus a separate formatted belief
  retrieval; OUTSIDE includes the formatted retrieval.
- INSIDE self-state includes up to three additional plain-text belief-derived
  standing-points.
- A successful `beliefs_query` tool result can append another formatted
  Tier-marked block before `belief_count` is calculated.
- Provenance parses Tier-shaped lines from the initial route/fallback string,
  not the complete final prompt.
- Existing tests do not cover the identified distinctions and edge cases.

Unverified:
- whether self-state and router retrieval sets overlap in practice;
- whether the same beliefs are counted twice on real tool-assisted turns;
- whether stored content contains embedded Tier-shaped lines;
- whether Frozen V2.1 defines provenance as retrieved-belief provenance or
  broader full-prompt provenance;
- runtime frequency and behavioural impact.

No remediation is proposed. Frozen V2.1 authority and founder Gate 0 review
remain unresolved. No runtime code, tests, flags, databases, services,
experiments, baselines, or deployment settings were changed.
