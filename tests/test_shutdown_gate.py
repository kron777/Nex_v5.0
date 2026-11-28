"""Flask request admission and bounded drain tests."""
from __future__ import annotations

import threading
import time

from flask import Flask

from gui.shutdown_gate import ShutdownGate, install_shutdown_gate


def test_gate_timeout_reports_active_requests_and_closes_admission():
    gate = ShutdownGate()
    assert gate.enter()
    report = gate.begin_shutdown(time.monotonic() + 0.01)
    assert report == {
        "success": False,
        "active_requests": 1,
        "deadline_exceeded": True,
    }
    assert gate.is_closing
    assert gate.active_requests == 1
    assert not gate.enter()

    gate.leave()
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
        release.wait(timeout=2.0)
        return "finished"

    request_result = []
    request_thread = threading.Thread(
        target=lambda: request_result.append(
            app.test_client().get("/block").status_code
        ),
        name="in-flight-http-request",
    )
    request_thread.start()
    assert started.wait(timeout=1.0)

    shutdown_result = {}
    shutdown_thread = threading.Thread(
        target=lambda: shutdown_result.update(
            gate.begin_shutdown(time.monotonic() + 1.0)
        ),
        name="shutdown-request-drain",
    )
    shutdown_thread.start()

    deadline = time.monotonic() + 1.0
    while not gate.is_closing and time.monotonic() < deadline:
        time.sleep(0.001)
    assert gate.is_closing
    assert gate.active_requests == 1

    rejected = app.test_client().get("/block")
    assert rejected.status_code == 503
    assert rejected.get_json() == {"error": "server shutting down"}
    assert calls == ["entered"]

    release.set()
    request_thread.join(timeout=1.0)
    shutdown_thread.join(timeout=1.0)

    assert not request_thread.is_alive()
    assert not shutdown_thread.is_alive()
    assert request_result == [200]
    assert shutdown_result == {
        "success": True,
        "active_requests": 0,
        "deadline_exceeded": False,
    }
    assert gate.active_requests == 0
