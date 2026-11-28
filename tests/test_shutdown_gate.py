"""Flask request admission and bounded drain tests."""
from __future__ import annotations

import threading
import time

from flask import Flask

from gui.shutdown_gate import ShutdownGate, install_shutdown_gate


def test_gate_timeout_reports_active_requests_and_closes_admission():
    gate = ShutdownGate()
    token = gate.enter("GET /manual")
    assert token is not None
    report = gate.begin_shutdown(time.monotonic() + 0.01)
    assert report["success"] is False
    assert report["active_requests"] == 1
    assert report["deadline_exceeded"] is True
    assert len(report["active"]) == 1
    assert report["active"][0]["label"] == "GET /manual"
    assert report["active"][0]["thread"] == threading.current_thread().name
    assert report["active"][0]["elapsed_s"] >= 0
    assert gate.is_closing
    assert gate.active_requests == 1
    assert not gate.enter()

    gate.leave(token)
    assert gate.active_requests == 0


def test_flask_gate_rejects_new_requests_and_waits_for_admitted_request():
    app = Flask(__name__)
    gate = ShutdownGate()
    install_shutdown_gate(app, gate)
    started = threading.Event()
    release = threading.Event()
    calls = []

    @app.get("/block")
    def block():
        calls.append("entered")
        started.set()
        release.wait(timeout=5.0)
        return "finished"

    request_result = []
    request_thread = threading.Thread(
        target=lambda: request_result.append(
            app.test_client().get("/block").status_code
        ),
        name="in-flight-http-request",
    )
    request_thread.start()
    assert started.wait(timeout=2.0)

    shutdown_result = {}
    shutdown_thread = threading.Thread(
        target=lambda: shutdown_result.update(
            gate.begin_shutdown(time.monotonic() + 3.0)
        ),
        name="shutdown-request-drain",
    )
    shutdown_thread.start()

    deadline = time.monotonic() + 3.0
    while not gate.is_closing and time.monotonic() < deadline:
        time.sleep(0.001)
    assert gate.is_closing
    assert gate.active_requests == 1

    rejected = app.test_client().get("/block")
    assert rejected.status_code == 503
    assert rejected.get_json() == {"error": "server shutting down"}
    assert calls == ["entered"]

    release.set()
    request_thread.join(timeout=2.0)
    shutdown_thread.join(timeout=2.0)

    assert not request_thread.is_alive()
    assert not shutdown_thread.is_alive()
    assert request_result == [200]
    assert shutdown_result == {
        "success": True,
        "active_requests": 0,
        "active": [],
        "deadline_exceeded": False,
    }
    assert gate.active_requests == 0
