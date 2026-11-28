# Feedback-loop measurement and review updates

A graph cycle is not itself a stability verdict. The existing
`FeedbackLoopAssessment` remains UNKNOWN-first and records topology separately
from measurements and assessor conclusions. This update path adds append-only
evidence events without calculating stability or changing loop membership and
relationships.

## Record a measured dimension

Every measured dimension requires a finite numeric value, unit, evidence
references and a confidence label. Measurement provenance and the operating
envelope are also recorded on the event:

```bash
python -m rdo feedback-measure \
  --cycle-id <cycle-id> \
  --loop-id <loop-id> \
  --dimension gain \
  --value 0.72 \
  --unit ratio \
  --evidence-reference lab:gain-run-004 \
  --confidence medium \
  --provenance experiment:run-004 \
  --operating-envelope stress \
  --dir rdo/.cycles
```

Supported dimensions are gain, delay, damping, oscillation, overshoot,
recovery, and observation_window. The tool validates that the value is
finite and numeric; it does not impose engineering thresholds or interpret
whether the value is safe.

## Record an independently attributed stability review

A stability state is changed only by an explicit review with reviewer
attribution, source reference, assessment evidence and confidence:

```bash
python -m rdo feedback-review \
  --cycle-id <cycle-id> \
  --loop-id <loop-id> \
  --stability-state conditionally_stable \
  --reviewer "independent reviewer" \
  --source-reference review:stability-assessment-12 \
  --assessment-evidence test:closed-loop-response \
  --assessment-evidence trace:operating-envelope \
  --confidence medium \
  --note "Stable only inside the measured envelope." \
  --dir rdo/.cycles
```

Reviewer attribution is recorded, not authenticated by this local ledger.
The ledger does not calculate, infer or promote a stability state.

A new measurement recorded after a stability review invalidates the prior
verdict and returns the current state to UNKNOWN until a new review is
recorded. Earlier reviews and measurements remain in the event history.

## Persistence and replay

Events are written to the append-only, hash-chained
`feedback_loop_evidence.jsonl` ledger under the cycle store. The cycle
snapshot also stores the applied event history in
`CycleRecord.feedback_loop_evidence_events`. The existing loop ID, members
and relationships are hashed into each event; replay fails if that topology
has changed.

If a process stops after the ledger append but before the updated cycle
snapshot is saved, replay the durable events:

```bash
python -m rdo feedback-replay --cycle-id <cycle-id> --dir rdo/.cycles
```

Legacy CycleRecords load with an empty feedback evidence history. Initial
measurements remain UNKNOWN-first; a measurement is not a stability verdict.
No graph edges are added or removed, and no control-loop policy, runtime,
experiment, deployment, Gate 0 or Phase 1 authority is changed.
