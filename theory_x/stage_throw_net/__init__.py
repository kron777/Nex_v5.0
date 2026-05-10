"""Theory X Stage Throw-Net — refinement engine.

Per net.txt v11 (committed 948475a).
Ports nex_core throw-net engine onto nex5 substrate.

Phase 25a TN-0+TN-1 scope: schema migration + TriggerDetector.
TN-2 through TN-5 are subsequent sessions.
"""
from theory_x.stage_throw_net.trigger_detector import TriggerDetector

THEORY_X_STAGE = "throw_net"

__all__ = ["TriggerDetector"]
