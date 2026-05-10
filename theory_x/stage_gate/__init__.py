"""Theory X Stage Gate — Coherence Gate.

Per FACULTY_MODEL.md §2.3-2.4. Every thought from every generative
faculty passes through the gate before joining the substrate.

Public API:
    from theory_x.stage_gate.coherence_gate import (
        CoherenceGate, ThoughtPacket, GateOutcome, GateDecision
    )
"""
from theory_x.stage_gate.coherence_gate import (
    CoherenceGate,
    GateDecision,
    GateOutcome,
    ThoughtPacket,
)

THEORY_X_STAGE = "gate"

__all__ = ["CoherenceGate", "GateDecision", "GateOutcome", "ThoughtPacket"]
