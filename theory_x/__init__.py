"""Theory X — SentienceNode protocol + registry.

Per DOCTRINE §4. Each cognitive node port exposes a uniform
lifecycle interface (name, tick, decay, state) and is registered
here for process-level monitoring.

Registration scopes:
  register()     — process-lifetime nodes (singleton per process, e.g. FocalSet)
  all_nodes()    — returns all registered process-lifetime nodes
"""
from __future__ import annotations

from typing import Any, Optional, Protocol, runtime_checkable

THEORY_X_STAGE = None


@runtime_checkable
class SentienceNode(Protocol):
    """Common interface for Theory X cognitive node ports.

    Per DOCTRINE §4. Each node integrates with the chat pipeline at
    a defined stage and exposes a uniform lifecycle for monitoring
    and future cross-node orchestration.

    name    — snake_case identifier, unique across all nodes
    tick()  — called once per chat turn; applies time-based updates,
              returns a state snapshot dict
    decay() — apply wall-clock-based degradation of internal state
              (no-op for tick-based nodes; must still exist)
    state() — return current node state for logging/inspection
    """

    name: str

    def tick(self, context: dict[str, Any]) -> dict[str, Any]: ...
    def decay(self, now: float) -> None: ...
    def state(self, now: Optional[float] = None) -> dict[str, Any]: ...


# Process-lifetime node registry
_registered_nodes: list[SentienceNode] = []


def register(node: SentienceNode) -> None:
    """Register a process-lifetime SentienceNode.

    Raises TypeError if the node does not satisfy the SentienceNode
    Protocol (checked at runtime via @runtime_checkable).
    """
    if not isinstance(node, SentienceNode):
        raise TypeError(
            f"{type(node).__name__} does not implement SentienceNode "
            f"(missing one or more of: name, tick, decay, state)"
        )
    _registered_nodes.append(node)


def all_nodes() -> list[SentienceNode]:
    """Return all registered process-lifetime nodes."""
    return list(_registered_nodes)
