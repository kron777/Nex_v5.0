"""Theory X — Harmonic subsystem.

CHORD §4 deliverable C — substrate_harmonic coherence metric.

Per CHORD.md: the substrate has a harmonic; the harmonic is the chord;
the chord carries her meaning. This subsystem measures cross-component
coherence as a numeric value 0-1 every 300s, log-only at phase 1.

Phase 1: SubstrateHarmonic SentienceNode + substrate_coherence table.
Phase 2 (later): HUD panel reads substrate_coherence and surfaces it
as the HARMONIC METRIC tab in the right column.
Phase 3 (later): consumers (chord-aware arc closure, mirror-character,
metacognition chord-logging) read substrate_coherence as substrate.
"""
from __future__ import annotations

from theory_x.harmonic.substrate_harmonic import SubstrateHarmonic

__all__ = ["SubstrateHarmonic"]
