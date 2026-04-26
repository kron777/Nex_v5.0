"""Mode system — runtime configuration presets for NEX's operation.

A Mode bundles the runtime parameters that shape how NEX operates
in a given register. The underlying architecture is unchanged —
modes just parameterize behavior across components.
"""
from theory_x.modes.modes import (
    Mode,
    ModeName,
    MODES,
    get_mode,
    DEFAULT_MODE,
    DISPLAY_ORDER,
)
from theory_x.modes.state import ModeState, build_mode_state

__all__ = [
    "Mode",
    "ModeName",
    "MODES",
    "get_mode",
    "DEFAULT_MODE",
    "DISPLAY_ORDER",
    "ModeState",
    "build_mode_state",
]
