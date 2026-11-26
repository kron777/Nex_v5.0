# NEX Phase 0 — Chat belief-count and formatter boundary audit
Date: 2026-11-25

## Scope and evidence boundary

Static source audit against `claude/nex-continuity-wire` at base commit
`de93134f34adac07a3a41c2a05b33720510a2bfc`. This note describes source
construction only. It does not establish host-effective flags, live database
contents, runtime incidence, or model attention.

## 1. The formatter's marker is a presentation convention, not a typed record

`theory_x/stage3_world_model/retrieval.py:37-51` implements
`format_beliefs_for_prompt()`. It emits one line per input belief using
`- [Tier {tier} | {confidence} ...] {content}`. The belief's `content` is
interpolated verbatim after the marker; it is not escaped or structurally
separated from the rendered line.

Consequently, counting occurrences of the substring `- [Tier` in the final
composite text is not guaranteed to equal the number of belief rows. A belief
content string containing that same substring contributes an additional count.
This is a source-level possibility, not evidence that such a row exists in a
live database.

## 2. The Chat gap gate counts a composite string after several augmentations

In `gui/server.py`, Chat begins with either membrane-provided
`route_result["belief_text"]` or the fallback retrieval/formatter route.
The fallback formatter is followed by an 800-character cap. The initial
retrieved text is then snapshotted as `_retrieved_belief_text` for provenance.

Before the gap-gate count, the route can append:
- BehaviouralSelfModel text (INSIDE route);
- Harmonizer tension summary (INSIDE route);
- disturbance text interpolating `content_a` and `content_b`;
- ProblemMemory text, whose formatter includes stored title, description,
  plan and observations;
- Metacognition, NovelAssociation, SelfNarrative, AffectState,
  DriveEmergence, SelfMindView and SocialPresence output;
- successful tool-result prompt text.

At the gate, `belief_count = belief_text.count("- [Tier")` is used to decide
whether to return the thin-graph refusal and to record the gap-deflection
reason. The count is therefore a textual marker count over a composite buffer,
not a count of retrieved belief records.

The source establishes a possible false-positive path: pre-gate injected text
or interpolated stored content can contain the marker substring and increase
the count without representing an additional retrieved belief. In particular,
ProblemMemory inserts stored free text before the count; the inspected
formatter does not constrain that text to exclude the marker. This is a
structural risk, not a verified live-data defect or measured false positive.

## 3. Later standing-point additions do not explain the current gate count

The Philosophical standing-point block is appended after the gap-gate count.
Its generated lines use `- [Tier 1]`, but this later append cannot inflate the
count already computed for that turn. It can, however, make the final prompt
contain more tier markers than the gate's recorded count. The spectrum sample
block is separately built as plain bullet text.

## 4. Formatter spot-check

The following inspected prompt formatters do not themselves emit the literal
`- [Tier` marker in their static templates:
- BehaviouralSelfModel;
- Harmonizer;
- ProblemMemory's own labels (its stored free-text fields remain unconstrained);
- Metacognition;
- AffectState.

This is a bounded spot-check, not an exhaustive proof for every dynamic string,
tool output, route implementation, or future formatter. The marker can still
arrive through interpolated content.

## 5. Provenance boundary remains distinct from the gap-gate boundary

`_retrieved_belief_text` is captured before the listed augmentations. The
provenance snapshot receives that pre-augmentation value as
`prompt_beliefs`, while the Chat generation path later receives the augmented
`belief_text`. Thus the provenance field represents the initial retrieved
belief block, not a complete inventory of every contextual block supplied to
the model. This is a deliberate source distinction to preserve in any future
provenance interpretation; it is not proof that the snapshot is incorrect
under its intended contract.

## 6. Phase 0 disposition

- Confirmed: `belief_count` is derived by substring counting over a composite
  text buffer, not by counting structured belief rows.
- Confirmed: belief content is interpolated verbatim by the fallback formatter.
- Confirmed: ProblemMemory free-text fields are appended before the count.
- Possible but unverified: a live row or injected context contains the marker
  and causes a false-positive count.
- Not established: frequency, runtime impact, or whether the intended
  Frozen V2.1 contract requires a different counting boundary.
- No remediation is proposed here. The governing Frozen V2.1 source and
  founder Gate 0 approval remain unresolved; this note records evidence only.

No runtime code, flags, databases, services, experiments, baselines, or
deployment settings were changed.
