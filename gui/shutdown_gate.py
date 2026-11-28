"""Request admission and in-flight drain for bounded graceful shutdown."""
from __future__ import annotations

import threading
import time
from typing import Any

from flask import g, jsonify, request


class ShutdownGate:
    """Atomically stop new HTTP work and wait for admitted requests to leave."""

    def __init__(self) -> None:
        self._condition = threading.Condition()
        self._closing = False
        self._active_requests: dict[int, dict[str, Any]] = {}
        self._next_token = 0

    @property
    def is_closing(self) -> bool:
        with self._condition:
            return self._closing

    @property
    def active_requests(self) -> int:
        with self._condition:
            return len(self._active_requests)

    def enter(self, label: str | None = None) -> int | None:
        """Admit one request and return its token, or reject during shutdown."""
        with self._condition:
            if self._closing:
                return None
            self._next_token += 1
            token = self._next_token
            self._active_requests[token] = {
                "label": label or "request",
                "thread": threading.current_thread().name,
                "started_at": time.monotonic(),
            }
            return token

    def leave(self, token: int) -> None:
        """Release the exact request admitted by the matching Flask context."""
        with self._condition:
            if token not in self._active_requests:
                raise RuntimeError("ShutdownGate request token is unknown or already released")
            del self._active_requests[token]
            if not self._active_requests:
                self._condition.notify_all()

    def _active_snapshot(self) -> list[dict[str, Any]]:
        now = time.monotonic()
        return [
            {
                "label": item["label"],
                "thread": item["thread"],
                "elapsed_s": round(max(0.0, now - item["started_at"]), 3),
            }
            for item in self._active_requests.values()
        ]

    def begin_shutdown(self, deadline: float) -> dict[str, Any]:
        """Close admission and wait for active requests until a monotonic deadline."""
        with self._condition:
            self._closing = True
            while self._active_requests:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return {
                        "success": False,
                        "active_requests": len(self._active_requests),
                        "active": self._active_snapshot(),
                        "deadline_exceeded": True,
                    }
                self._condition.wait(timeout=remaining)
            return {
                "success": True,
                "active_requests": 0,
                "active": [],
                "deadline_exceeded": False,
            }


def install_shutdown_gate(app, gate: ShutdownGate) -> None:
    """Count every Flask request and reject work after shutdown admission closes.

    Register this before authentication and route-specific before_request hooks:
    even public GET/POST routes must be covered by the shutdown boundary.
    """

    @app.before_request
    def _nex_shutdown_gate():
        token = gate.enter(f"{request.method} {request.path}")
        if token is None:
            return jsonify({"error": "server shutting down"}), 503
        g._nex_shutdown_gate_token = token
        return None

    @app.teardown_request
    def _nex_shutdown_gate_leave(_exc):
        token = getattr(g, "_nex_shutdown_gate_token", None)
        if token is not None:
            g._nex_shutdown_gate_token = None
            gate.leave(token)

    app.extensions["nex_shutdown_gate"] = gate
