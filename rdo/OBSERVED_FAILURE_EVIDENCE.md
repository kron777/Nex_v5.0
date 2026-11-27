# RDO observed-failure evidence record

## Purpose

Structural failure-path candidates and observed failure outcomes are different
things. The graph can identify that consumer A depends on prerequisite B; that
alone does not show that a failure of B propagated to A.

This increment adds a traceable record for observations associated with one
canonical `depends_on` edge in the current repository model. It is an additive
extension to `CycleRecord` and does not change the existing structural candidate
analysis.

**Historical vocabulary note:** RDO v1.3 used `requires` for hard prerequisites;
the current repository model uses `depends_on`. The current working basis is RDO
v1.4, with v1.3 retained as historical implementation lineage. This record follows
the repository's existing `depends_on` orientation and does not rename or migrate
edge kinds. The raw 47,172-byte v1.4 source is not mounted for fresh byte-level
comparison, so this change makes no claim about exact v1.4 wording.

## Record semantics

- `failed_key` is the prerequisite (`relationship.dst`).
- `affected_key` is the consumer (`relationship.src`).
- `relationship_kind` must be `depends_on`.
- `failed_evidence` and `affected_evidence` are separate Watcher Evidence
  records whose subjects must match the corresponding canonical obligation keys.
- The failed endpoint must have measured event evidence with retained raw data.
  The affected endpoint may remain unobserved while association state is UNKNOWN.
- Static, implemented or inferred source evidence cannot be recorded as an observed
  failure event. Co-observation, temporal association and causal attribution require
  separate measured evidence for both endpoints.
- Measured cloud/CI evidence remains cloud evidence, not host runtime evidence.
- Each endpoint collection timestamp that is present must be timezone-aware and
  fall inside the explicitly bounded observation window.
- The operating envelope reuses the typed `OperatingEnvelopeAssessment` model;
  declared and assessed states remain separate, and assessed states still require
  their own evidence, provenance and confidence. No envelope is calculated.
- Watcher origin, evidence class, source reference, collection time, raw data
  and interpretation remain attached to each endpoint independently.
- The default association state is `unknown`.

## Association states

| State | Meaning |
|---|---|
| `unknown` | No assessed association is recorded. The affected endpoint may be unobserved. |
| `co_observed` | Both endpoints have independent evidence in the same bounded observation window; causality is not implied. |
| `temporal_association` | Both endpoints have independent timestamps and evidence; temporal association is recorded, not causality. |
| `causally_attributed` | An assessor recorded causal attribution with separate assessment evidence, provenance and confidence. |

Association state is an observer/reviewer-supplied assessment label. Validation checks
that the required measured endpoint evidence exists and falls inside the declared
window; it does not infer co-observation, temporal direction or causality from the
timestamps. The record does not calculate propagation, severity, probability,
stability, headroom, or an OFT verdict. Cloud-origin evidence remains cloud evidence;
it is never promoted to host runtime observation by this record.

## Persistence and compatibility

`CycleRecord.observed_failure_evidence` is appended as a trailing field with
an empty-list default. Existing cycle JSON files without the field continue to
load. The recording helper appends observations, treats identical observation-ID
replays as idempotent, and rejects ID reuse with different content. Recording
requires the exact relationship to exist in the cycle snapshot. Cycle JSON remains
ordinary mutable storage, not a tamper-evident or immutable evidence ledger.

This is an evidence container only. Any later analysis must separately define
how observations are aggregated across a path and must preserve UNKNOWN when
coverage, temporal alignment, operating-envelope comparability or causal
evidence is incomplete.
