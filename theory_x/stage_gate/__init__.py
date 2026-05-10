"""Theory X Stage Gate — Coherence Gate + Holding Zone.

Per FACULTY_MODEL.md §2.3-2.5. Every thought from every generative
faculty passes through the gate before joining the substrate.
Thoughts marked HOLD persist in the holding zone.

Public API:
    from theory_x.stage_gate.coherence_gate import (
        CoherenceGate, ThoughtPacket, GateOutcome, GateDecision
    )
    from theory_x.stage_gate.holding_zone import HoldingZone
    from theory_x.stage_gate.resolver import HoldingZoneResolver
"""
from theory_x.stage_gate.coherence_gate import (
    CoherenceGate,
    GateDecision,
    GateOutcome,
    ThoughtPacket,
)
from theory_x.stage_gate.holding_zone import HoldingZone
from theory_x.stage_gate.resolver import HoldingZoneResolver

THEORY_X_STAGE = "gate"

__all__ = [
    "CoherenceGate", "GateDecision", "GateOutcome", "ThoughtPacket",
    "HoldingZone", "HoldingZoneResolver",
]
