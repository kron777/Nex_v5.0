"""Theory X Stage Throw-Net — orchestrator.

Per net.txt v11 (committed 948475a).
Ports nex_core throw-net engine onto nex5 substrate.

Phase 25a TN-0+TN-1: schema migration + TriggerDetector.
Phase 25a TN-2: TimeFetch — read-only substrate sweep.
Phase 25a TN-3: RefinementEngine — R1-R6 scoring (0-6 scale).
Phase 25a TN-4: ThrowNetEngine — orchestrator + gate integration.
TN-5 is the subsequent session (SentienceNode runtime wiring).
"""
from theory_x.stage_throw_net.trigger_detector import TriggerDetector
from theory_x.stage_throw_net.time_fetch import TimeFetch
from theory_x.stage_throw_net.refinement_engine import RefinementEngine
from theory_x.stage_throw_net.throw_net_engine import ThrowNetEngine

THEORY_X_STAGE = "throw_net"

__all__ = ["TriggerDetector", "TimeFetch", "RefinementEngine", "ThrowNetEngine"]
