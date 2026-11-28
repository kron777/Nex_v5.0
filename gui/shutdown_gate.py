"""Request admission and in-flight drain for bounded graceful shutdown."""
from __future__ import annotations

import threading
import time
from typing import Any

from flask import g, jsonify


class ShutdownGate:
    """Atomically stop new HTTP work and wait for admitted requests to leave."""

    def __init__(self) -> None:
        self._condition = threading.Condition()
        self._closing = False
        self._active_requests = 0

    @property
    def is_closing(self) -> bool:
        with self._condition:
            return self._closing

    @property
    def active_requests(self) -> int:
        with self._condition:
            return self._active_requests

    def enter(self) -> bool:
        """Admit one request, or reject it once shutdown has begun."""
        with self._condition:
            if self._closing:
                return False
            self._active_requests += 1
            return True

    def leave(self) -> None:
        """Release one admitted request from its Flask teardown hook."""
        with self._condition:
            if self._active_requests <= 0:
                raise RuntimeError("ShutdownGate request count underflow")
            self._active_requests -= 1
            if self._active_requests == 0:
                self._condition.notify_all()

    def begin_shutdown(self, deadline: float) -> dict[str, Any]:
        """Close admission and wait for active requests until a monotonic deadline."""
        with self._condition:
            self._closing = True
            while self._active_requests:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return {
                        "success": False,
                        "active_requests": self._active_requests,
                        "deadline_exceeded": True,
                    }
                self._condition.wait(timeout=remaining)
            return {
                "success": True,
                "active_requests": 0,
                "deadline_exceeded": False,
            }


def install_shutdown_gate(app, gate: ShutdownGate) -> None:
    """Count every Flask request and reject work after shutdown admission closes.

    Register this before authentication and route-specific before_request hooks:
    even public GET/POST routes must be covered by the shutdown boundary.
    """

    @app.before_request
    def _nex_shutdown_gate():
        if not gate.enter():
            return jsonify({"error": "server shutting down"}), 503
        g._nex_shutdown_gate_entered = True
        return None

    @app.teardown_request
    def _nex_shutdown_gate_leave(_exc):
        if getattr(g, "_nex_shutdown_gate_entered", False):
            g._nex_shutdown_gate_entered = False
            gate.leave()

    app.extensions["nex_shutdown_gate"] = gate
