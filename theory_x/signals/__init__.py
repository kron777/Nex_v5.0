"""Signal detection layer — LLM-free pattern detection in the belief graph."""
from theory_x.signals.detectors import (
    CoOccurrenceDetector,
    SilenceDetector,
    BurstDetector,
)
from theory_x.signals.templates import PatternTemplateLibrary
from theory_x.signals.loop import SignalLoop, build_signal_loop

__all__ = [
    "CoOccurrenceDetector", "SilenceDetector", "BurstDetector",
    "PatternTemplateLibrary",
    "SignalLoop", "build_signal_loop",
]
