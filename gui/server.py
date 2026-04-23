"""GUI — Flask observability cockpit and chat column.

Phase 1 endpoints:
    GET  /                    — dashboard page
    GET  /api/alpha           — Alpha lines (read-only display)
    GET  /api/db/stats        — row counts per table per DB
    GET  /api/writers/queues  — queue depth per Writer
    GET  /api/errors/recent   — recent entries from the central error channel
    GET  /api/admin/status    — {configured, authenticated}
    POST /api/admin/login     — {password} → {authenticated}
    POST /api/admin/logout    — clears admin session
    POST /api/chat            — {prompt, register?} → routes through voice/llm.py

Phase 2 endpoints (sense stream):
    GET  /api/sense/status              — scheduler status for all 23 adapters
    POST /api/sense/start               — start_all() external feeds
    POST /api/sense/stop                — stop_all() external feeds
    POST /api/sense/toggle/<adapter_id> — enable/disable individual feed
    GET  /api/sense/recent              — last 50 sense_events rows

Phase 3 endpoints (dynamic formation):
    GET  /api/dynamic/status      — tree summary: branches, aperture, pipeline runs
    GET  /api/dynamic/pipeline    — last 50 pipeline events from dynamic.db
    GET  /api/dynamic/crystallized — last 20 crystallization events
    GET  /api/beliefs/recent       — last 20 beliefs from beliefs.db

Phase 4 endpoints (world model):
    GET  /api/beliefs/stats        — tier distribution, total, recent additions

Phase 5 endpoints (membrane):
    GET  /api/membrane/snapshot    — NEX's live inner state (inside snapshot)
    GET  /api/membrane/classify    — classify a stream as INSIDE or OUTSIDE

Phase 6 endpoints (self-location):
    GET  /api/system/status        — all subsystem flags + self_location_committed + alpha

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
    "dynamic":       ("bonsai_branches", "pipeline_events", "tree_snapshots",
                      "crystallization_events", "accumulator"),
    "intel":         ("market_data", "news_events", "analysis_snapshots"),
    "conversations": ("sessions", "messages"),
}


@dataclass
class AppState:
    writers: dict[str, Writer]
    readers: dict[str, Reader]
    voice: VoiceClient
    scheduler: Optional["SenseScheduler"] = None   # type: ignore[type-arg]
    dynamic: Optional["DynamicState"] = None        # type: ignore[type-arg]
    world_model: Optional["WorldModelState"] = None # type: ignore[type-arg]
    membrane: Optional["MembraneState"] = None      # type: ignore[type-arg]
    # Optional hook a test can inject to short-circuit chat persistence.
    now_fn: Callable[[], int] = field(default_factory=lambda: (lambda: int(time.time())))

    def close(self) -> None:
        if self.scheduler is not None:
            try:
                self.scheduler.shutdown()
            except Exception as e:
                error_channel.record(
                    f"Scheduler shutdown failed: {e}", source="gui.server", exc=e
                )
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
    with_scheduler: bool = True,
    with_dynamic: bool = True,
    with_world_model: bool = True,
    with_membrane: bool = True,
) -> "AppState":
    """Default state: real Writers/Readers against db_paths(), real VoiceClient."""
    from theory_x.stage1_sense import build_scheduler

    paths = db_paths()
    writers = {name: Writer(p, name=name) for name, p in paths.items()}
    readers = {name: Reader(p) for name, p in paths.items()}
    voice = VoiceClient(
        url=voice_url or os.environ.get(
            "NEX5_VOICE_URL", "http://localhost:8080/v1/chat/completions"
        ),
        model=os.environ.get("NEX5_VOICE_MODEL", voice_model),
    )
    scheduler = build_scheduler(writers, readers) if with_scheduler else None

    dynamic = None
    if with_dynamic:
        from theory_x.stage2_dynamic import build_dynamic
        dynamic = build_dynamic(writers, readers)

    world_model = None
    if with_world_model and dynamic is not None:
        from theory_x.stage3_world_model import build_world_model
        world_model = build_world_model(writers, readers, dynamic_state=dynamic)

    membrane = None
    if with_membrane and dynamic is not None:
        from theory_x.stage4_membrane import build_membrane
        membrane = build_membrane(
            writers, readers,
            dynamic_state=dynamic,
            world_model_state=world_model,
        )

    return AppState(
        writers=writers,
        readers=readers,
        voice=voice,
        scheduler=scheduler,
        dynamic=dynamic,
        world_model=world_model,
        membrane=membrane,
    )


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

        # Route query through membrane (self-inquiry vs world-inquiry).
        belief_text = None
        register_override = None
        if state.membrane is not None and state.world_model is not None:
            try:
                route_result = state.membrane.route(
                    query=prompt,
                    belief_retriever=state.world_model.retriever,
                    dynamic_state=state.dynamic,
                )
                belief_text = route_result.get("belief_text")
                register_override = route_result.get("register_hint")
            except Exception as e:
                error_channel.record(
                    f"membrane routing failed: {e}", source="gui.server", exc=e,
                )
        elif state.world_model is not None:
            try:
                from theory_x.stage3_world_model.retrieval import format_beliefs_for_prompt
                active_branches: list[str] = []
                if state.dynamic is not None:
                    snap = state.dynamic.status()
                    active_branches = [
                        b["branch_id"] for b in snap.get("branches", [])
                        if b.get("focus_num", 0) > 0.1
                    ]
                beliefs = state.world_model.retriever.retrieve(
                    query=prompt, branch_hints=active_branches, limit=8
                )
                belief_text = format_beliefs_for_prompt(beliefs) if beliefs else None
            except Exception as e:
                error_channel.record(
                    f"belief retrieval failed: {e}", source="gui.server", exc=e,
                )

        # Apply register override from router (INSIDE → philosophical) only if
        # the user hasn't explicitly specified a register.
        if register_override and not register_name:
            register = by_name(register_override) or register

        # Route through voice.
        try:
            resp = state.voice.speak(
                VoiceRequest(prompt=prompt, register=register),
                beliefs=belief_text,
            )
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

    # -- sense stream (Phase 2) ----------------------------------------------

    @app.get("/api/sense/status")
    def api_sense_status():
        if state.scheduler is None:
            return jsonify({"error": "scheduler not initialised"}), 503
        return jsonify(state.scheduler.status())

    @app.post("/api/sense/start")
    def api_sense_start():
        if state.scheduler is None:
            return jsonify({"error": "scheduler not initialised"}), 503
        state.scheduler.start_all()
        return jsonify({"global_running": True})

    @app.post("/api/sense/stop")
    def api_sense_stop():
        if state.scheduler is None:
            return jsonify({"error": "scheduler not initialised"}), 503
        state.scheduler.stop_all()
        return jsonify({"global_running": False})

    @app.post("/api/sense/toggle/<adapter_id>")
    def api_sense_toggle(adapter_id: str):
        if state.scheduler is None:
            return jsonify({"error": "scheduler not initialised"}), 503
        try:
            status = state.scheduler.status()["adapters"].get(adapter_id)
            if status is None:
                return jsonify({"error": f"unknown adapter {adapter_id!r}"}), 404
            if status["is_internal"]:
                return jsonify({"error": "cannot toggle internal adapter"}), 400
            if status["enabled"]:
                state.scheduler.disable(adapter_id)
            else:
                state.scheduler.enable(adapter_id)
            new_state = state.scheduler.status()["adapters"][adapter_id]["enabled"]
            return jsonify({"adapter_id": adapter_id, "enabled": new_state})
        except (KeyError, ValueError) as e:
            return jsonify({"error": str(e)}), 400

    @app.get("/api/sense/recent")
    def api_sense_recent():
        reader = state.readers.get("sense")
        if reader is None:
            return jsonify({"events": []})
        try:
            limit = int(request.args.get("limit", "50"))
        except ValueError:
            limit = 50
        rows = reader.read(
            "SELECT id, stream, payload, provenance, timestamp "
            "FROM sense_events ORDER BY id DESC LIMIT ?",
            (max(1, min(limit, 200)),),
        )
        return jsonify({
            "events": [
                {
                    "id": row["id"],
                    "stream": row["stream"],
                    "payload": row["payload"],
                    "provenance": row["provenance"],
                    "timestamp": row["timestamp"],
                }
                for row in rows
            ]
        })

    # -- world model (Phase 4) -----------------------------------------------

    @app.get("/api/beliefs/stats")
    def api_beliefs_stats():
        reader = state.readers.get("beliefs")
        if reader is None:
            return jsonify({"error": "no beliefs reader"}), 503
        try:
            tier_rows = reader.read(
                "SELECT tier, COUNT(*) as cnt FROM beliefs GROUP BY tier ORDER BY tier"
            )
            total = sum(r["cnt"] for r in tier_rows)
            cutoff_24h = int(__import__("time").time()) - 86400
            recent_rows = reader.read(
                "SELECT COUNT(*) as cnt FROM beliefs WHERE created_at >= ?",
                (cutoff_24h,),
            )
            recent_count = recent_rows[0]["cnt"] if recent_rows else 0
            return jsonify({
                "tier_distribution": {str(r["tier"]): r["cnt"] for r in tier_rows},
                "total": total,
                "added_last_24h": recent_count,
            })
        except Exception as e:
            error_channel.record(f"beliefs stats failed: {e}", source="gui.server", exc=e)
            return jsonify({"error": str(e)}), 500

    # -- membrane (Phase 5) -------------------------------------------------

    @app.get("/api/membrane/snapshot")
    def api_membrane_snapshot():
        if state.membrane is None:
            return jsonify({"error": "membrane not initialised"}), 503
        try:
            return jsonify(state.membrane.snapshot())
        except Exception as e:
            error_channel.record(f"membrane snapshot failed: {e}", source="gui.server", exc=e)
            return jsonify({"error": str(e)}), 500

    @app.get("/api/membrane/classify")
    def api_membrane_classify():
        stream = request.args.get("stream", "")
        if not stream:
            return jsonify({"error": "stream parameter required"}), 400
        if state.membrane is not None:
            side = state.membrane.classify_stream(stream)
        else:
            from theory_x.stage4_membrane.classifier import CLASSIFIER
            side = CLASSIFIER.classify_stream(stream).value
        return jsonify({"stream": stream, "side": side})

    # -- system status (Phase 6) ---------------------------------------------

    @app.get("/api/system/status")
    def api_system_status():
        from theory_x.stage5_self_location.commitment import SelfLocationCommitment
        committed = False
        reader = state.readers.get("beliefs")
        if reader is not None:
            try:
                committed = SelfLocationCommitment().is_committed(reader)
            except Exception:
                pass
        return jsonify({
            "scheduler": state.scheduler is not None,
            "dynamic": state.dynamic is not None,
            "world_model": state.world_model is not None,
            "membrane": state.membrane is not None,
            "self_location_committed": committed,
            "alpha": ALPHA.lines[0],
        })

    # -- dynamic formation (Phase 3) ----------------------------------------

    @app.get("/api/dynamic/status")
    def api_dynamic_status():
        if state.dynamic is None:
            return jsonify({"error": "dynamic not initialised"}), 503
        return jsonify(state.dynamic.status())

    @app.get("/api/dynamic/pipeline")
    def api_dynamic_pipeline():
        reader = state.readers.get("dynamic")
        if reader is None:
            return jsonify({"events": []}), 503
        try:
            rows = reader.read(
                "SELECT id, ts, step, sensation_source, branch_id, magnitude, valence, meta "
                "FROM pipeline_events ORDER BY id DESC LIMIT 50",
            )
            return jsonify({
                "events": [
                    {
                        "id": r["id"],
                        "ts": r["ts"],
                        "step": r["step"],
                        "sensation_source": r["sensation_source"],
                        "branch_id": r["branch_id"],
                        "magnitude": r["magnitude"],
                        "valence": r["valence"],
                        "meta": r["meta"],
                    }
                    for r in rows
                ]
            })
        except Exception as e:
            error_channel.record(f"dynamic pipeline read failed: {e}", source="gui.server", exc=e)
            return jsonify({"error": str(e)}), 500

    @app.get("/api/dynamic/crystallized")
    def api_dynamic_crystallized():
        reader = state.readers.get("dynamic")
        if reader is None:
            return jsonify({"events": []}), 503
        try:
            rows = reader.read(
                "SELECT id, ts, branch_id, belief_id, content, magnitude "
                "FROM crystallization_events ORDER BY id DESC LIMIT 20",
            )
            return jsonify({
                "events": [
                    {
                        "id": r["id"],
                        "ts": r["ts"],
                        "branch_id": r["branch_id"],
                        "belief_id": r["belief_id"],
                        "content": r["content"],
                        "magnitude": r["magnitude"],
                    }
                    for r in rows
                ]
            })
        except Exception as e:
            error_channel.record(f"crystallized read failed: {e}", source="gui.server", exc=e)
            return jsonify({"error": str(e)}), 500

    @app.get("/api/beliefs/recent")
    def api_beliefs_recent():
        reader = state.readers.get("beliefs")
        if reader is None:
            return jsonify({"beliefs": []}), 503
        try:
            rows = reader.read(
                "SELECT id, content, tier, confidence, created_at, branch_id, source, locked "
                "FROM beliefs ORDER BY created_at DESC LIMIT 20",
            )
            return jsonify({
                "beliefs": [
                    {
                        "id": r["id"],
                        "content": r["content"],
                        "tier": r["tier"],
                        "confidence": r["confidence"],
                        "created_at": r["created_at"],
                        "branch_id": r["branch_id"],
                        "source": r["source"],
                        "locked": r["locked"],
                    }
                    for r in rows
                ]
            })
        except Exception as e:
            error_channel.record(f"beliefs recent read failed: {e}", source="gui.server", exc=e)
            return jsonify({"error": str(e)}), 500

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
