"""GUI — Flask observability cockpit and chat column.

Endpoints:
    GET  /                    — dashboard page
    GET  /api/alpha           — Alpha lines (read-only display)
    GET  /api/db/stats        — row counts per table per DB
    GET  /api/writers/queues  — queue depth per Writer
    GET  /api/errors/recent   — recent entries from the central error channel
    GET  /api/admin/status    — {configured, authenticated}
    POST /api/admin/login     — {password} → {authenticated}
    POST /api/admin/logout    — clears admin session
    POST /api/chat            — {prompt, register?} → routes through voice/llm.py

The app is constructed from an AppState container so tests can drive
it with mock Writers/Readers and a mock VoiceClient.

See SPECIFICATION.md §8 — Full Observability.
"""
from __future__ import annotations

import atexit
import logging
import os
import secrets
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from flask import Flask, jsonify, render_template, request, session

import errors as error_channel
from admin.auth import is_configured as admin_is_configured
from admin.auth import verify_password
from alpha import ALPHA
from substrate import Reader, Writer, db_paths
from voice.llm import VoiceClient, VoiceRequest
from voice.registers import by_name, classify, default_register

THEORY_X_STAGE = None

logger = logging.getLogger("gui.server")

# Table lists per database — used for DB stats display.
TABLES_PER_DB: dict[str, tuple[str, ...]] = {
    "beliefs":       ("beliefs",),
    "sense":         ("sense_events",),
    "dynamic":       ("bonsai_branches", "pipeline_events", "accumulator"),
    "intel":         ("market_data", "news_events", "analysis_snapshots"),
    "conversations": ("sessions", "messages"),
}


@dataclass
class AppState:
    writers: dict[str, Writer]
    readers: dict[str, Reader]
    voice: VoiceClient
    # Optional hook a test can inject to short-circuit chat persistence.
    now_fn: Callable[[], int] = field(default_factory=lambda: (lambda: int(time.time())))

    def close(self) -> None:
        for w in self.writers.values():
            try:
                w.close()
            except Exception as e:
                error_channel.record(
                    f"Writer close failed: {e}", source="gui.server", exc=e
                )


def build_state(
    *,
    voice_url: Optional[str] = None,
    voice_model: str = "qwen2.5-3b",
) -> AppState:
    """Default state: real Writers/Readers against db_paths(), real VoiceClient."""
    paths = db_paths()
    writers = {name: Writer(p, name=name) for name, p in paths.items()}
    readers = {name: Reader(p) for name, p in paths.items()}
    voice = VoiceClient(
        url=voice_url or os.environ.get(
            "NEX5_VOICE_URL", "http://localhost:8080/v1/chat/completions"
        ),
        model=os.environ.get("NEX5_VOICE_MODEL", voice_model),
    )
    return AppState(writers=writers, readers=readers, voice=voice)


def create_app(state: AppState) -> Flask:
    app = Flask(
        __name__,
        template_folder=str(Path(__file__).parent / "templates"),
        static_folder=str(Path(__file__).parent / "static"),
    )
    # Session secret — persisted in a gitignored file so admin logins survive
    # server restarts during development without requiring re-auth every process.
    app.secret_key = _ensure_secret()

    # -- pages ---------------------------------------------------------------

    @app.get("/")
    def index():
        return render_template("index.html", alpha_lines=ALPHA.lines)

    # -- read endpoints ------------------------------------------------------

    @app.get("/api/alpha")
    def api_alpha():
        return jsonify({"lines": list(ALPHA.lines)})

    @app.get("/api/db/stats")
    def api_db_stats():
        out: dict[str, dict] = {}
        for name, tables in TABLES_PER_DB.items():
            reader = state.readers.get(name)
            db_info: dict = {"tables": {}, "path": reader.db_path if reader else None}
            if reader is None:
                db_info["error"] = "no reader"
                out[name] = db_info
                continue
            try:
                for t in tables:
                    db_info["tables"][t] = reader.count(t)
            except Exception as e:
                db_info["error"] = str(e)
                error_channel.record(
                    f"DB stats failed for {name}: {e}",
                    source="gui.server", exc=e,
                )
            out[name] = db_info
        return jsonify(out)

    @app.get("/api/writers/queues")
    def api_writer_queues():
        return jsonify(
            {name: w.queue_depth() for name, w in state.writers.items()}
        )

    @app.get("/api/errors/recent")
    def api_errors_recent():
        try:
            limit = int(request.args.get("limit", "50"))
        except ValueError:
            limit = 50
        events = error_channel.recent(limit=max(1, min(limit, 500)))
        return jsonify({"events": [e.to_dict() for e in events]})

    # -- admin ---------------------------------------------------------------

    @app.get("/api/admin/status")
    def api_admin_status():
        return jsonify({
            "configured": admin_is_configured(),
            "authenticated": bool(session.get("admin")),
        })

    @app.post("/api/admin/login")
    def api_admin_login():
        payload = request.get_json(silent=True) or {}
        password = payload.get("password", "")
        if not isinstance(password, str) or not password:
            return jsonify({"authenticated": False, "reason": "empty"}), 400
        if verify_password(password):
            session["admin"] = True
            session["admin_since"] = int(time.time())
            return jsonify({"authenticated": True})
        error_channel.record(
            "Failed admin login attempt", source="gui.server", level="WARNING"
        )
        return jsonify({"authenticated": False, "reason": "mismatch"}), 401

    @app.post("/api/admin/logout")
    def api_admin_logout():
        session.pop("admin", None)
        session.pop("admin_since", None)
        return jsonify({"authenticated": False})

    # -- chat ----------------------------------------------------------------

    @app.post("/api/chat")
    def api_chat():
        payload = request.get_json(silent=True) or {}
        prompt = (payload.get("prompt") or "").strip()
        if not prompt:
            return jsonify({"error": "empty prompt"}), 400

        register_name = payload.get("register")
        register = (
            by_name(register_name) if register_name else classify(prompt)
        ) or default_register()

        # Ensure a session row exists in conversations.db.
        session_id = session.get("chat_session_id")
        writer = state.writers.get("conversations")
        if writer is not None:
            if session_id is None:
                session_id = uuid.uuid4().hex
                session["chat_session_id"] = session_id
                try:
                    writer.write(
                        "INSERT INTO sessions (id, started_at, admin) VALUES (?, ?, ?)",
                        (session_id, state.now_fn(), int(bool(session.get("admin")))),
                    )
                except Exception as e:
                    error_channel.record(
                        f"conversations: session insert failed: {e}",
                        source="gui.server", exc=e,
                    )

            try:
                writer.write(
                    "INSERT INTO messages (session_id, role, content, register, timestamp) "
                    "VALUES (?, 'user', ?, ?, ?)",
                    (session_id, prompt, register.name, state.now_fn()),
                )
            except Exception as e:
                error_channel.record(
                    f"conversations: user message insert failed: {e}",
                    source="gui.server", exc=e,
                )

        # Route through voice.
        try:
            resp = state.voice.speak(VoiceRequest(prompt=prompt, register=register))
            text = resp.text
            voice_ok = True
        except Exception as e:
            error_channel.record(
                f"voice.speak failed: {e}", source="gui.server", exc=e,
            )
            text = (
                "Voice layer unreachable — the llama-server is not responding. "
                "Phase 1 runs without it; the cockpit is still live."
            )
            voice_ok = False

        if writer is not None and session_id is not None:
            try:
                writer.write(
                    "INSERT INTO messages (session_id, role, content, register, timestamp) "
                    "VALUES (?, 'nex', ?, ?, ?)",
                    (session_id, text, register.name, state.now_fn()),
                )
            except Exception as e:
                error_channel.record(
                    f"conversations: nex message insert failed: {e}",
                    source="gui.server", exc=e,
                )

        return jsonify({
            "text": text,
            "register": register.name,
            "voice_ok": voice_ok,
            "session_id": session_id,
        })

    return app


def _ensure_secret() -> bytes:
    """Persist a Flask session secret in a gitignored file."""
    path = Path(__file__).resolve().parent.parent / ".flask_secret"
    if path.exists():
        return path.read_bytes()
    secret = secrets.token_bytes(32)
    path.write_bytes(secret)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return secret


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    error_channel.install_handler()

    state = build_state()
    atexit.register(state.close)

    app = create_app(state)
    host = os.environ.get("NEX5_GUI_HOST", "127.0.0.1")
    port = int(os.environ.get("NEX5_GUI_PORT", "8765"))
    logger.info("Starting NEX 5.0 cockpit on http://%s:%d", host, port)
    app.run(host=host, port=port, debug=False, use_reloader=False)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
