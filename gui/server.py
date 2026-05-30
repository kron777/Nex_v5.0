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
    GET  /api/membrane/behaviour   — observed behavioural metrics (hedge_rate, etc.)

Phase 6 endpoints (self-location):
    GET  /api/system/status        — all subsystem flags + self_location_committed + alpha

Phase 7 endpoints (fountain):
    GET  /api/fountain/status           — last_thought, last_fire_ts, total_fires, readiness_score
    GET  /api/fountain/recent           — last 10 fountain_events from dynamic.db
    GET  /api/fountain/crystallizations — last 30 fountain_crystallizations joined to beliefs
    GET  /api/beliefs/insights          — last 200 fountain_insight + synergized beliefs

Phase 7b endpoints (speech):
    GET  /api/speech/status  — {enabled, voice, queue_depth, last_spoken_at}
    POST /api/speech/pause   — pause TTS
    POST /api/speech/resume  — resume TTS
    POST /api/speech/flush   — skip all pending entries

Phase 8 endpoints (strikes):
    POST /api/strikes/fire         — {strike_type, custom_input?} → fires strike, returns record
    GET  /api/strikes/recent       — last 20 strike records from catalogue
    POST /api/strikes/notes        — {id, notes} — annotate a record

Phase 9 endpoints (memory + tools):
    GET  /api/problems              — list open problems
    POST /api/problems              — {title, description} → open new problem
    GET  /api/problems/<id>         — get full problem record
    POST /api/problems/<id>/observe — {observation} → append observation
    POST /api/problems/<id>/plan    — {plan} → update plan
    POST /api/problems/<id>/close   — close problem
    GET  /api/tools/available       — list available tools

Phase 25b endpoints (review queue):
    GET  /api/review                — list review_queue items (flagged problems)
    GET  /api/review/<id>           — single review_queue item
    POST /api/review/<id>/unflag    — move item back to open_problems

The app is constructed from an AppState container so tests can drive
it with mock Writers/Readers and a mock VoiceClient.

See SPECIFICATION.md §8 — Full Observability.
"""
from __future__ import annotations

import atexit
import json
import logging
import os
import re
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

# FocalSet — Layer 1 attention (log-only; no behavior change yet)
try:
    from theory_x.focal_set import FocalSet as _FocalSet
    _focal_set = _FocalSet(K=4)
except Exception:
    _focal_set = None  # type: ignore[assignment]

# Register FocalSet with process-lifetime SentienceNode registry (Model A).
# WorkingMemory is per-session and is NOT registered here.
try:
    if _focal_set is not None:
        from theory_x import register as _tx_register
        _tx_register(_focal_set)
except Exception:
    pass

_FOCAL_LOG = "/tmp/nex5_focal.log"

# Working Memory — Layer 2 (log-only; behavior injection in Phase 2.4)
try:
    from theory_x.working_memory import WorkingMemory as _WorkingMemory
    _working_memory_by_session: dict[str, "_WorkingMemory"] = {}
except Exception:
    _WorkingMemory = None  # type: ignore[assignment,misc]
    _working_memory_by_session = {}

_WM_LOG = "/tmp/nex5_working_memory.log"

# Conversation Memory — Phase 11: dialogue history node (DOCTRINE §5)
try:
    from theory_x.conversation_memory import ConversationMemory as _ConversationMemory
    _conversation_memory = _ConversationMemory(
        db_path="/home/rr/Desktop/nex5/data/conversations.db",
        n_turns=8,
    )
except Exception:
    _conversation_memory = None  # type: ignore[assignment]

_CM_LOG = "/tmp/nex5_conversation_memory.log"

# Executive Control — register classifier (replaces classify() stub)
try:
    from voice.registers import REGISTERS as _BUILTIN_REGISTERS
    from theory_x.executive_control import ExecutiveControl as _ExecControl
    _executive = _ExecControl(_BUILTIN_REGISTERS)
    # Register as process-lifetime SentienceNode (Model A)
    try:
        from theory_x import register as _tx_register_ec
        _tx_register_ec(_executive)
    except Exception:
        pass
except Exception:
    _executive = None  # type: ignore[assignment]

_EC_LOG          = "/tmp/nex5_executive_control.log"
_BSM_LOG         = "/tmp/nex5_behavioural_self_model.log"
_SM_LOG          = "/tmp/nex5_self_model.log"
_PM_LOG          = "/tmp/nex5_problem_memory.log"
_HARMONIZER_LOG  = "/tmp/nex5_harmonizer.log"


def _is_instruction_query(text: str) -> bool:
    """Skip substrate keystone-retrieval for mechanical instruction/factual
    queries (they should go to the LLM). Validated fp=0 on logged queries."""
    t = (text or "").strip().lower()
    if re.match(r'^(output|translate|complete|print|calculate|solve|convert)\b', t):
        return True
    if any(p in t for p in ["exactly:", "only output", "one word", "nothing else",
                            "respond with only", "reply with exactly", "reply with only",
                            "complete this sequence", "only this symbol",
                            "respond with the number", "respond with only the number"]):
        return True
    if re.search(r'\d\s*[\+\-\*/\u00d7\u00f7]\s*\d', t) or re.match(r'^what is \d', t):
        return True
    return False
_GM_LOG          = "/tmp/nex5_goal_manager.log"
_MCOG_LOG        = "/tmp/nex5_metacognition.log"
_NASSOC_LOG      = "/tmp/nex5_novel_association.log"


def _get_or_create_wm(session_id: str) -> "Optional[_WorkingMemory]":
    if _WorkingMemory is None:
        return None
    if session_id not in _working_memory_by_session:
        _working_memory_by_session[session_id] = _WorkingMemory()
    return _working_memory_by_session[session_id]

CHAT_GAP_MIN_BELIEFS = 2
CHAT_GAP_REFUSAL = "That doesn't reach my graph right now."
# Registers where thin belief retrieval should not block a response.
# Philosophical = self-inquiry; NEX speaks from her standing-points even
# when no specific belief matches the query.
_ALLOW_THIN_REGISTERS = {"Philosophical"}

_SOCIAL_REGEX = re.compile(
    r"^\s*(hi|hello|hey|yo|sup|howdy|"
    r"how(\s+(are|do|is|s|'?s))|"
    r"what(\s+(s|'?s))?\s+up|"
    r"good\s+(morning|afternoon|evening|night|day)|"
    r"thanks|thank\s+you|nice|cool|ok|okay|right|"
    r"see\s+ya|bye|goodbye)\b",
    re.IGNORECASE,
)


def _is_social(prompt: str, register=None) -> bool:
    try:
        if register and str(register.name).upper() in ("WARMTH", "SOCIAL", "CASUAL"):
            return True
    except Exception:
        pass
    return bool(_SOCIAL_REGEX.search(prompt or ""))

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
    fountain: Optional["FountainState"] = None          # type: ignore[type-arg]
    strike_protocol: Optional["StrikeProtocol"] = None  # type: ignore[type-arg]
    catalogue: Optional["StrikeCatalogue"] = None       # type: ignore[type-arg]
    problem_memory: Optional["ProblemMemory"] = None    # type: ignore[type-arg]
    goal_manager: Optional["GoalManager"] = None        # type: ignore[type-arg]
    metacognition: Optional["Metacognition"] = None      # type: ignore[type-arg]
    novel_association: Optional["NovelAssociation"] = None  # type: ignore[type-arg]
    self_narrative: Optional["SelfNarrative"] = None        # type: ignore[type-arg]  # Phase 26
    tool_registry: Optional["ToolRegistry"] = None      # type: ignore[type-arg]
    tool_caller: Optional["ToolCaller"] = None          # type: ignore[type-arg]
    speech_consumer: Optional["SpeechQueueConsumer"] = None  # type: ignore[type-arg]
    mode_state: Optional["ModeState"] = None                 # type: ignore[type-arg]
    voice_state: Optional["VoiceState"] = None               # type: ignore[type-arg]
    signal_loop: Optional["SignalLoop"] = None               # type: ignore[type-arg]
    diversity_loop: Optional["DiversityLoop"] = None         # type: ignore[type-arg]
    arc_loop: Optional["ArcLoop"] = None                     # type: ignore[type-arg]
    probe_runner: Optional["ProbeRunner"] = None             # type: ignore[type-arg]
    probes_reader: Optional[Reader] = None
    coherence_gate: Optional[object] = None        # Phase 22
    trigger_detector: Optional[object] = None      # Phase 25a TN-1
    throw_net_monitor: Optional[object] = None     # Phase 25a TN-5
    counterfactual_node: Optional[object] = None   # Phase 25b CN
    voice_engine: Optional[object] = None          # Phase 30 VoiceEngine
    voice_mode: str = "use_substrate"              # "use_llm" | "use_substrate"  TEMP: B-test 2026-05-27
    affect_state: Optional[object] = None          # Phase 27 AffectState
    drive_emergence: Optional[object] = None       # Phase 29 DriveEmergence
    predictive_substrate: Optional[object] = None  # Phase 35 PredictiveSubstrate
    self_mind_view: Optional[object] = None        # Phase 37 SelfMindView
    social_presence: Optional[object] = None      # Phase 38 SocialPresence
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
    with_fountain: bool = True,
    with_strikes: bool = True,
    with_tools: bool = True,
) -> "AppState":
    """Default state: real Writers/Readers against db_paths(), real VoiceClient."""
    from theory_x.stage1_sense import build_scheduler

    paths = db_paths()
    writers = {name: Writer(p, name=name) for name, p in paths.items()}
    readers = {name: Reader(p) for name, p in paths.items()}
    # Tag Protocol — wrap beliefs writer so new INSERTs auto-generate tags
    from theory_x.tag_protocol.writer_wrapper import TaggingBeliefWriter as _TBW
    writers["beliefs"] = _TBW(writers["beliefs"])
    voice = VoiceClient(
        url=voice_url or os.environ.get(
            "NEX5_VOICE_URL", "http://localhost:8080/v1/chat/completions"
        ),
        model=os.environ.get("NEX5_VOICE_MODEL", voice_model),
    )
    scheduler = build_scheduler(writers, readers) if with_scheduler else None

    # Phase 22 + 23 + 24 + 25a — Coherence Gate + Holding Zone + Reshape Path + TriggerDetector
    coherence_gate = None
    trigger_detector = None
    if "beliefs" in writers and "beliefs" in readers:
        from theory_x.stage_gate.coherence_gate import CoherenceGate
        from theory_x.stage_gate.holding_zone import HoldingZone
        from theory_x.stage_gate.resolver import HoldingZoneResolver
        from theory_x.stage_gate.transformer import ReshapeTransformer
        from theory_x.stage_throw_net.trigger_detector import TriggerDetector
        _holding_zone = HoldingZone(writers["beliefs"], readers["beliefs"])
        _resolver = HoldingZoneResolver(_holding_zone, beliefs_writer=writers["beliefs"])
        trigger_detector = TriggerDetector(writers["beliefs"], readers["beliefs"])
        coherence_gate = CoherenceGate(
            beliefs_reader=readers["beliefs"],
            beliefs_writer=writers["beliefs"],
            conversations_reader=readers.get("conversations"),
            holding_zone=_holding_zone,
            resolver=_resolver,
            trigger_detector=trigger_detector,
        )
        _resolver.set_gate(coherence_gate)
        _transformer = ReshapeTransformer(voice)
        _resolver.set_transformer(_transformer)
        _resolver.start_loop()

    dynamic = None
    if with_dynamic:
        from theory_x.stage2_dynamic import build_dynamic
        dynamic = build_dynamic(writers, readers, coherence_gate=coherence_gate)

    world_model = None
    if with_world_model and dynamic is not None:
        from theory_x.stage3_world_model import build_world_model
        world_model = build_world_model(writers, readers, dynamic_state=dynamic,
                                        coherence_gate=coherence_gate)

    membrane = None
    if with_membrane and dynamic is not None:
        from theory_x.stage4_membrane import build_membrane
        membrane = build_membrane(
            writers, readers,
            dynamic_state=dynamic,
            world_model_state=world_model,
            coherence_gate=coherence_gate,
        )

    fountain = None
    if with_fountain and dynamic is not None:
        from theory_x.stage6_fountain import build_fountain
        fountain = build_fountain(writers, readers, voice, dynamic_state=dynamic,
                                  coherence_gate=coherence_gate)

    strike_protocol = None
    catalogue = None
    if with_strikes and dynamic is not None:
        from strikes.catalogue import StrikeCatalogue
        from strikes.protocols import StrikeProtocol
        catalogue = StrikeCatalogue()
        strike_protocol = StrikeProtocol(
            voice=voice,
            dynamic_state=dynamic,
            beliefs_reader=readers["beliefs"],
            sense_writer=writers["sense"],
            catalogue=catalogue,
            membrane_state=membrane,
            dynamic_reader=readers["dynamic"],
        )

    problem_memory = None
    goal_manager = None
    metacognition = None
    novel_association = None
    tool_registry = None
    tool_caller = None
    if with_tools:
        from theory_x.stage7_sustained.problem_memory import ProblemMemory
        from theory_x.stage8_goal_manager.goal_manager import GoalManager
        from theory_x.stage9_metacognition.metacognition import Metacognition
        from theory_x.stage_capability.tools import ToolRegistry
        from theory_x.stage_capability.tool_caller import ToolCaller
        if "conversations" in writers and "conversations" in readers:
            problem_memory = ProblemMemory(writers["conversations"], readers["conversations"])
            try:
                from theory_x import register as _tx_register_pm
                _tx_register_pm(problem_memory)
            except Exception:
                pass
            goal_manager = GoalManager(writers["conversations"], readers["conversations"])
            try:
                from theory_x import register as _tx_register_gm
                _tx_register_gm(goal_manager)
            except Exception:
                pass
            if "beliefs" in readers:
                metacognition = Metacognition(
                    writers["conversations"],
                    readers["conversations"],
                    readers["beliefs"],
                )
                try:
                    from theory_x import register as _tx_register_mc
                    _tx_register_mc(metacognition)
                except Exception:
                    pass
            if "beliefs" in writers and "beliefs" in readers:
                from theory_x.stage10_imagination.novel_association import NovelAssociation
                novel_association = NovelAssociation(
                    writers["beliefs"],
                    readers["beliefs"],
                )
        tool_registry = ToolRegistry(beliefs_reader=readers.get("beliefs"))
        tool_caller = ToolCaller(tool_registry)

    # Phase 25a TN-5 — ThrowNetMonitor (needs coherence_gate + problem_memory)
    throw_net_monitor = None
    if (coherence_gate is not None
            and problem_memory is not None
            and trigger_detector is not None
            and "beliefs" in writers and "beliefs" in readers):
        from theory_x.stage_throw_net.time_fetch import TimeFetch
        from theory_x.stage_throw_net.refinement_engine import RefinementEngine
        from theory_x.stage_throw_net.throw_net_engine import ThrowNetEngine
        from theory_x.stage_throw_net.monitor import ThrowNetMonitor
        _time_fetch = TimeFetch(readers["beliefs"], problem_memory)
        _refinement = RefinementEngine(readers["beliefs"])
        _throw_net_engine = ThrowNetEngine(
            beliefs_writer=writers["beliefs"],
            beliefs_reader=readers["beliefs"],
            trigger_detector=trigger_detector,
            time_fetch=_time_fetch,
            refinement_engine=_refinement,
            coherence_gate=coherence_gate,
        )
        throw_net_monitor = ThrowNetMonitor(_throw_net_engine)
        throw_net_monitor.start_loop()

    # Phase 25b CN — CounterfactualNode (needs coherence_gate + problem_memory)
    counterfactual_node = None
    if (coherence_gate is not None
            and problem_memory is not None
            and "beliefs" in writers and "beliefs" in readers
            and "conversations" in writers and "conversations" in readers):
        try:
            from theory_x.stage_counterfactual import CounterfactualNode as _CN
            from theory_x.stage_throw_net.time_fetch import TimeFetch as _TFcn
            from theory_x.stage_throw_net.refinement_engine import RefinementEngine as _REcn
            _tf_cn = _TFcn(readers["beliefs"], problem_memory)
            _re_cn = _REcn(readers["beliefs"])
            counterfactual_node = _CN(
                beliefs_reader=readers["beliefs"],
                beliefs_writer=writers["beliefs"],
                conversations_reader=readers["conversations"],
                conversations_writer=writers["conversations"],
                coherence_gate=coherence_gate,
                time_fetch=_tf_cn,
                refinement_engine=_re_cn,
            )
            counterfactual_node.start_loop()
        except Exception as _cn_err:
            import logging as _log_cn
            _log_cn.getLogger("server").warning(
                "CounterfactualNode failed to start (non-fatal): %s", _cn_err
            )

    return AppState(
        writers=writers,
        readers=readers,
        voice=voice,
        scheduler=scheduler,
        dynamic=dynamic,
        world_model=world_model,
        membrane=membrane,
        fountain=fountain,
        strike_protocol=strike_protocol,
        catalogue=catalogue,
        problem_memory=problem_memory,
        goal_manager=goal_manager,
        metacognition=metacognition,
        novel_association=novel_association,
        tool_registry=tool_registry,
        tool_caller=tool_caller,
        coherence_gate=coherence_gate,
        trigger_detector=trigger_detector,
        throw_net_monitor=throw_net_monitor,
        counterfactual_node=counterfactual_node,
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

    # Register membrane-owned SentienceNodes (Model A — process-lifetime).
    # Must run here (not module level) because both nodes require DB readers
    # that are only available after build_state().
    if state.membrane is not None:
        try:
            from theory_x import register as _tx_register_membrane
            if state.membrane.self_model is not None:
                _tx_register_membrane(state.membrane.self_model)
            if state.membrane.behavioural is not None:
                _tx_register_membrane(state.membrane.behavioural)
        except Exception:
            pass

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

    # -- voice mode ----------------------------------------------------------

    @app.post("/api/voice_mode")
    def api_voice_mode():
        if not session.get("admin"):
            return jsonify({"error": "admin required"}), 403
        payload = request.get_json(silent=True) or {}
        mode = payload.get("mode", "")
        if mode not in ("use_llm", "use_substrate"):
            return jsonify({"error": "mode must be 'use_llm' or 'use_substrate'"}), 400
        state.voice_mode = mode
        return jsonify({"mode": state.voice_mode, "ok": True})

    # -- chat ----------------------------------------------------------------

    @app.post("/api/chat")
    def api_chat():
        payload = request.get_json(silent=True) or {}
        prompt = (payload.get("prompt") or "").strip()
        if not prompt:
            return jsonify({"error": "empty prompt"}), 400

        is_probe = bool(payload.get("is_probe", False))
        register_name = payload.get("register")
        # EDIT A 2026-05-29: default chat to Philosophical (probe-quality richness).
        # Explicit dropdown/probe register_name still wins. Revert: restore the
        # _executive.select branch below.
        register = (
            by_name(register_name) if register_name
            else (by_name("Philosophical") or default_register())
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

        try:
            with open(_EC_LOG, "a") as _ecf:
                _ecf.write(json.dumps({
                    "event": "ec_decision",
                    "ts": time.time(),
                    "session": session_id,
                    "query": prompt[:200],
                    "register": register.name,
                    "caller_override": bool(register_name),
                }) + "\n")
        except Exception:
            pass

        # Route query through membrane (self-inquiry vs world-inquiry).
        belief_text = None
        register_override = None
        route_result = None
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

        # BehaviouralSelfModel injection — INSIDE routes only (Phase 5.3).
        # Adds observed behavioural metrics (hedge rate, register pattern, avg length)
        # to belief_text so the LLM has grounded self-knowledge for self-inquiry queries.
        if (route_result is not None
                and route_result.get("side") == "INSIDE"
                and state.membrane is not None
                and state.membrane.behavioural is not None):
            try:
                state.membrane.behavioural.tick()
                _bsm_text = state.membrane.behavioural.format_for_prompt()
                if _bsm_text:
                    belief_text = (belief_text or "") + "\n\n" + _bsm_text
                    with open(_BSM_LOG, "a") as _bfh:
                        _bfh.write(
                            f"[{time.strftime('%H:%M:%S')}] INSIDE inject: "
                            f"{_bsm_text[:120].replace(chr(10), ' ')}\n"
                        )
            except Exception as _bsm_exc:
                error_channel.record(
                    f"behavioural self-model injection failed: {_bsm_exc}",
                    source="gui.server", exc=_bsm_exc,
                )

        # SelfModel observability log — INSIDE routes only (B1).
        # Content already injects via router._inside_route() lines 44-48.
        # This block adds §6 #5 observability per Lens Theory §2.
        _sm_snap = route_result.get("self_model_snap") if route_result is not None else None
        if _sm_snap is not None:
            try:
                from theory_x.stage4_membrane.self_model import format_self_state as _fmt_self
                _sm_intro = _sm_snap.get("interoception", {})
                _sm_text = _fmt_self(_sm_snap)
                with open(_SM_LOG, "a") as _smf:
                    _smf.write(json.dumps({
                        "event": "self_model_inject",
                        "ts": time.time(),
                        "session": session_id,
                        "belief_count": _sm_intro.get("belief_count", 0),
                        "locked_count": _sm_intro.get("locked_count", 0),
                        "inside_beliefs": len(_sm_snap.get("inside_beliefs", [])),
                        "text_len": len(_sm_text),
                    }) + "\n")
            except Exception as _sm_exc:
                error_channel.record(
                    f"self-model log write failed: {_sm_exc}",
                    source="gui.server", exc=_sm_exc,
                )

        # Harmonizer cumulative-tension surfacing — INSIDE routes only (B3').
        # Disturbance block covers acute named tensions for 8 turns post-scan;
        # format_for_prompt() covers persistent graph-tension state until
        # paradox events age out. Per RE_AUDIT B3' wire-decision.
        if (route_result is not None
                and route_result.get("side") == "INSIDE"
                and state.world_model is not None):
            _harm_text = ""
            _harm_active = 0
            try:
                _harm_st = state.world_model.harmonizer.tick()
                _harm_active = _harm_st.get("active_paradox", 0)
                if _harm_active > 0:
                    _harm_text = state.world_model.harmonizer.format_for_prompt()
                    if _harm_text:
                        belief_text = (belief_text or "") + "\n\n" + _harm_text
            except Exception as _harm_exc:
                error_channel.record(
                    f"harmonizer format_for_prompt failed: {_harm_exc}",
                    source="gui.server", exc=_harm_exc,
                )
            try:
                with open(_HARMONIZER_LOG, "a") as _hf:
                    _hf.write(json.dumps({
                        "event": "harmonizer_inject",
                        "ts": time.time(),
                        "session": session_id,
                        "active_paradox": _harm_active,
                        "injected": bool(_harm_text),
                        "text_len": len(_harm_text),
                    }) + "\n")
            except Exception:
                pass

        # Append disturbance tension if present (PHILOSOPHICAL or unspecified register)
        if state.world_model is not None:
            try:
                disturbance = state.world_model.get_disturbance()
                if disturbance is not None:
                    reg_name = (register_override or register.name or "").upper()
                    if not register_name or reg_name in ("PHILOSOPHICAL", "AUTO", ""):
                        tension_note = (
                            f"\nSomething is in tension: \"{disturbance['content_a']}\" "
                            f"vs \"{disturbance['content_b']}\". "
                            "She is holding this unresolved."
                        )
                        belief_text = (belief_text or "") + tension_note
                        disturbance["cycles_remaining"] -= 1
            except Exception as exc:
                error_channel.record(f"disturbance surfacing failed: {exc}", source="gui.server", exc=exc)

        # Problem memory: inject matching open problem context
        if state.problem_memory is not None:
            try:
                matching = state.problem_memory.find_matching(prompt)
                if matching:
                    problem_text = state.problem_memory.format_for_prompt(matching[0]["id"])
                    belief_text = (belief_text or "") + "\n\n" + problem_text
                try:
                    with open(_PM_LOG, "a") as _pmf:
                        _pmf.write(json.dumps({
                            "event": "problem_memory_check",
                            "ts": time.time(),
                            "session": session_id,
                            "matched": len(matching),
                            "prompt": prompt[:200],
                        }) + "\n")
                except Exception:
                    pass
            except Exception as exc:
                error_channel.record(
                    f"problem memory matching failed: {exc}", source="gui.server", exc=exc
                )

        # Goal manager: inject top-priority open goal into belief_text (Phase 15).
        # Always-on; no register gating; no semantic match requirement.
        # Goal is the organizing target — should be in awareness each turn.
        if state.goal_manager is not None:
            try:
                active_goal = state.goal_manager.get_active()
                if active_goal:
                    goal_text = state.goal_manager.format_for_prompt(active_goal["id"])
                    if goal_text:
                        belief_text = (belief_text or "") + "\n\n" + goal_text
                try:
                    with open(_GM_LOG, "a") as _gmf:
                        import json as _json
                        _gmf.write(_json.dumps({
                            "event": "goal_manager_check",
                            "ts": time.time(),
                            "session": session_id,
                            "active_goal": active_goal["id"] if active_goal else None,
                            "title": active_goal["title"] if active_goal else None,
                            "prompt": prompt[:200],
                        }) + "\n")
                except Exception:
                    pass
            except Exception as exc:
                error_channel.record(
                    f"goal manager injection failed: {exc}", source="gui.server", exc=exc
                )

        # Metacognition: self-pattern observation injection (Phase 16).
        # Always-on; detects groove repetition + goal-drift; under 100 chars typical.
        if state.metacognition is not None:
            try:
                state.metacognition.tick()
                _mcog_text = state.metacognition.format_for_prompt()
                if _mcog_text:
                    belief_text = (belief_text or "") + "\n\n" + _mcog_text
                try:
                    with open(_MCOG_LOG, "a") as _mf:
                        import json as _json2
                        _mf.write(_json2.dumps({
                            "event": "metacognition_check",
                            "ts": time.time(),
                            "session": session_id,
                            "injected": bool(_mcog_text),
                            "text": _mcog_text,
                            "prompt": prompt[:200],
                        }) + "\n")
                except Exception:
                    pass
            except Exception as _mcog_exc:
                error_channel.record(
                    f"metacognition injection failed: {_mcog_exc}",
                    source="gui.server", exc=_mcog_exc,
                )

        # Novel Association: cross-branch synthesises annotation (Phase 17).
        # Surfaces the most recent unannotated cross-domain association once per
        # turn; marks it annotated so it is not injected again.
        if state.novel_association is not None:
            try:
                _nassoc_text = state.novel_association.format_for_prompt()
                if _nassoc_text:
                    belief_text = (belief_text or "") + "\n\n" + _nassoc_text
                try:
                    with open(_NASSOC_LOG, "a") as _nf:
                        import json as _json3
                        _nf.write(_json3.dumps({
                            "event": "novel_association_check",
                            "ts": time.time(),
                            "session": session_id,
                            "injected": bool(_nassoc_text),
                            "text": _nassoc_text,
                        }) + "\n")
                except Exception:
                    pass
            except Exception as _nassoc_exc:
                error_channel.record(
                    f"novel association injection failed: {_nassoc_exc}",
                    source="gui.server", exc=_nassoc_exc,
                )

        # SelfNarrative: inject topic-matched autobiographical entries (Phase 26).
        if state.self_narrative is not None:
            try:
                import types as _types
                _sn_ctx = _types.SimpleNamespace(current_topic=prompt[:100])
                _sn_text = state.self_narrative.format_for_prompt(_sn_ctx)
                if _sn_text:
                    belief_text = (belief_text or "") + "\n\n" + _sn_text
            except Exception as _sn_exc:
                error_channel.record(
                    f"self_narrative injection failed: {_sn_exc}",
                    source="gui.server", exc=_sn_exc,
                )

        # AffectState: inject current mood/valence into belief_text (Phase 27).
        # format_for_prompt() reads the DB row — zero output-time computation.
        if state.affect_state is not None:
            try:
                _affect_text = state.affect_state.format_for_prompt()
                if _affect_text:
                    belief_text = (belief_text or "") + "\n\n" + _affect_text
            except Exception as _affect_exc:
                error_channel.record(
                    f"affect_state injection failed: {_affect_exc}",
                    source="gui.server", exc=_affect_exc,
                )

        # DriveEmergence: inject current drive topic into belief_text (Phase 29).
        # format_for_prompt() reads the DB row — zero output-time computation.
        if state.drive_emergence is not None:
            try:
                _drive_text = state.drive_emergence.format_for_prompt()
                if _drive_text:
                    belief_text = (belief_text or "") + "\n\n" + _drive_text
            except Exception as _drive_exc:
                error_channel.record(
                    f"drive_emergence injection failed: {_drive_exc}",
                    source="gui.server", exc=_drive_exc,
                )

        # SelfMindView: inject current cognitive state summary (Phase 39).
        # Always-on — substrate self-state is always available; LLM composes freely.
        if state.self_mind_view is not None:
            try:
                _smv_summary = state.self_mind_view.current_summary()
                if _smv_summary:
                    belief_text = (belief_text or "") + "\n\nCurrent cognitive state: " + _smv_summary
            except Exception as _smv_exc:
                error_channel.record(
                    f"self_mind_view injection failed: {_smv_exc}",
                    source="gui.server", exc=_smv_exc,
                )

        # SocialPresence: inject current social posture summary (Phase 39).
        # Always-on — substrate self-state is always available; LLM composes freely.
        if state.social_presence is not None:
            try:
                _sp_summary = state.social_presence.current_summary()
                if _sp_summary:
                    belief_text = (belief_text or "") + "\n\nCurrent social posture: " + _sp_summary
            except Exception as _sp_exc:
                error_channel.record(
                    f"social_presence injection failed: {_sp_exc}",
                    source="gui.server", exc=_sp_exc,
                )

        # Tool use: heuristic tool selection and execution
        tool_result = None
        if state.tool_caller is not None and state.tool_registry is not None:
            try:
                tool_name = state.tool_caller.should_use_tool(prompt, [])
                if tool_name:
                    kwargs = state.tool_caller.build_tool_kwargs(prompt, tool_name)
                    tool_result = state.tool_registry.execute(tool_name, **kwargs)
                    if tool_result.success:
                        tool_injection = state.tool_caller.build_tool_prompt(prompt, tool_result)
                        belief_text = (belief_text or "") + "\n" + tool_injection
            except Exception as exc:
                error_channel.record(
                    f"tool use failed: {exc}", source="gui.server", exc=exc
                )

        # Apply register override from router (INSIDE → philosophical) only if
        # the user hasn't explicitly specified a register.
        _ec_register = register.name
        if register_override and not register_name:
            register = by_name(register_override) or register
        try:
            with open(_EC_LOG, "a") as _ecf:
                _ecf.write(json.dumps({
                    "event": "register_finalised",
                    "ts": time.time(),
                    "session": session_id,
                    "ec_register": _ec_register,
                    "final_register": register.name,
                    "membrane_overrode": _ec_register != register.name,
                }) + "\n")
        except Exception:
            pass

        # FocalSet — log-only attention tracking (no behavior change).
        if _focal_set is not None and state.world_model is not None:
            try:
                _raw_beliefs = state.world_model.retriever.retrieve(
                    query=prompt, limit=10
                )
                if _raw_beliefs:
                    tick = _focal_set.next_tick()
                    _candidates = {str(b["id"]): b for b in _raw_beliefs}
                    _event = _focal_set.update(_candidates, current_tick=tick)
                    _focal_ids = _focal_set.get_focal_ids()
                    _focal_contents = [
                        b["content"][:60]
                        for b in _raw_beliefs
                        if str(b["id"]) in _focal_ids
                    ]
                    import datetime as _dt
                    _ts = _dt.datetime.now().strftime("%H:%M:%S")
                    _line = (
                        f"[{_ts}] tick={tick} register={register.name} "
                        f"query={prompt[:50]!r} "
                        f"focal={len(_focal_ids)} "
                        f"added={len(_event.added)} removed={len(_event.removed)} "
                        f"blocked={len(_event.blocked)}\n"
                        + "".join(f"  · {c}\n" for c in _focal_contents)
                    )
                    with open(_FOCAL_LOG, "a") as _fh:
                        _fh.write(_line)

                    # Working Memory — feed focal items into session buffer (log-only)
                    if session_id is not None:
                        _wm = _get_or_create_wm(session_id)
                        if _wm is not None:
                            _wm_now = time.time()
                            _wm.decay(_wm_now)
                            for _bid in _focal_ids:
                                _bdata = _candidates.get(_bid, {})
                                if _bdata:
                                    _wm.add(
                                        _bid,
                                        _bdata.get("content", "")[:200],
                                        now=_wm_now,
                                    )
                            _wm_active = _wm.get_active(_wm_now)
                            _wm_state = _wm.state(_wm_now)
                            _wm_line = (
                                f"[{_ts}] session={session_id[:8]} "
                                f"size={_wm_state['size']} "
                                f"active={len(_wm_active)} "
                                f"query={prompt[:50]!r}\n"
                                + "".join(
                                    f"  wm · [{i['activation']:.3f}] "
                                    f"(refresh={i['refresh_count']}) "
                                    f"{i['content'][:60]}\n"
                                    for i in _wm_active
                                )
                            )
                            with open(_WM_LOG, "a") as _wfh:
                                _wfh.write(_wm_line)
            except Exception:
                pass

        # Honest don't-know: bypass LLM when graph match is too thin.
        # Probe calls and social queries always proceed to the LLM regardless of belief count.
        belief_count = belief_text.count("- [Tier") if belief_text else 0
        _is_social_q = _is_social(prompt, register=register)
        if (not is_probe
                and not _is_social_q
                and register.name not in _ALLOW_THIN_REGISTERS
                and belief_count < CHAT_GAP_MIN_BELIEFS):
            if writer is not None and session_id is not None:
                try:
                    writer.write(
                        "INSERT INTO messages "
                        "(session_id, role, content, register, timestamp, tool_used) "
                        "VALUES (?, 'nex', ?, ?, ?, ?)",
                        (session_id, CHAT_GAP_REFUSAL, register.name, state.now_fn(), None),
                    )
                except Exception as exc:
                    error_channel.record(
                        f"conversations: gap refusal insert failed: {exc}",
                        source="gui.server", exc=exc,
                    )
            # Phase 25a TN-1 — log gap deflection for throw-net trigger detection
            if state.trigger_detector is not None:
                try:
                    state.trigger_detector.record_gap_deflection(
                        prompt, f"gap:belief_count_{belief_count}"
                    )
                except Exception as _td_exc:
                    error_channel.record(
                        f"trigger_detector.record_gap_deflection error: {_td_exc}",
                        source="gui.server", exc=_td_exc,
                    )
            return jsonify({
                "register": register.name,
                "session_id": session_id,
                "text": CHAT_GAP_REFUSAL,
                "tool_used": None,
                "voice_ok": True,
            })

        # Sample spectrum foundation — always present in chat composition.
        _spectrum_block = ""
        try:
            _spec_rows = state.readers["beliefs"].read(
                "SELECT content FROM beliefs WHERE source='spectrum' "
                "ORDER BY RANDOM() LIMIT 6"
            )
            if _spec_rows:
                _lines = "\n".join(f"  - {r['content']}" for r in _spec_rows)
                _spectrum_block = (
                    "Your foundation right now (standing-points from which you witness, "
                    "not propositions to repeat):\n" + _lines + "\n\n"
                )
        except Exception:
            pass

        # When Philosophical and no topical beliefs matched, inject spectrum
        # standing-points into belief_text so the LLM's "interior" has
        # standing-point content rather than just system metrics.
        if register.name in _ALLOW_THIN_REGISTERS and belief_count < CHAT_GAP_MIN_BELIEFS:
            try:
                _philo_rows = state.readers["beliefs"].read(
                    "SELECT content FROM beliefs WHERE source='spectrum' "
                    "ORDER BY RANDOM() LIMIT 4"
                )
                if _philo_rows:
                    _philo_lines = "\n".join(
                        f"- [Tier 1] {r['content']}" for r in _philo_rows
                    )
                    belief_text = (belief_text or "") + (
                        "\n\nYour standing-points (always present):\n" + _philo_lines
                    )
            except Exception:
                pass

        # Working Memory injection — cross-turn context for Conversational register.
        if session_id is not None and _WorkingMemory is not None:
            _wm_inj = _get_or_create_wm(session_id)
            if _wm_inj is not None:
                _wm_active = _wm_inj.get_active(time.time())
                if _wm_active and register.name == "Conversational" and belief_count >= CHAT_GAP_MIN_BELIEFS:
                    _wm_lines = "\n".join(f"- {i['content']}" for i in _wm_active[:5])
                    belief_text = (belief_text or "") + (
                        "\n\nRecently attended (cross-turn):\n" + _wm_lines
                    )

        # Conversation Memory injection — dialogue history for Conversational and Philosophical.
        if session_id is not None and _conversation_memory is not None:
            try:
                _conv_state = _conversation_memory.state(session_id=session_id)
                _conv_turns = _conv_state.get("turns", [])
                # messages write is at line ~877 (after prompt construction);
                # in practice the current prompt is not yet in the table.
                # Defensive: skip if last entry matches current prompt exactly.
                if (_conv_turns
                        and _conv_turns[-1]["role"] == "user"
                        and _conv_turns[-1]["content"].strip() == prompt.strip()):
                    _conv_turns = _conv_turns[:-1]
                if _conv_turns and register.name in ("Conversational", "Philosophical"):
                    # Sanitize: if an assistant message contains fake-dialogue markers
                    # (hallucinated multi-turn transcript), truncate at first marker
                    # to keep only the real first-reply portion.
                    import re as _re_sanitize
                    _fake_marker = _re_sanitize.compile(r"\n\s*(?:\(user\)|\[user\]|\[nex\])")
                    _clean_turns = []
                    for t in _conv_turns:
                        c = t["content"]
                        if t["role"] == "nex":
                            m = _fake_marker.search(c)
                            if m:
                                c = c[:m.start()].rstrip()
                        _clean_turns.append({"role": t["role"], "content": c})
                    _conv_lines = "\n".join(
                        f"[{t['role']}] {t['content']}"
                        for t in _clean_turns
                    )
                    belief_text = (belief_text or "") + (
                        "\n\nRecent conversation:\n" + _conv_lines
                    )
            except Exception as _conv_exc:
                error_channel.record(
                    f"conversation_memory_failed: {_conv_exc}",
                    source="gui.server", exc=_conv_exc,
                )

        text = None
        voice_ok = False

        # Phase 30 — VoiceEngine substrate path (use_substrate mode only).
        # Probe calls always bypass to LLM.
        if (not is_probe
                and not _is_instruction_query(prompt)
                and state.voice_engine is not None
                and state.voice_mode == "use_substrate"):
            try:
                _turn_n = 0
                if session_id is not None:
                    try:
                        _tn_row = state.readers["conversations"].read(
                            "SELECT COUNT(*) AS n FROM messages "
                            "WHERE session_id=? AND role='user'",
                            (session_id,),
                        )
                        _turn_n = _tn_row[0]["n"] if _tn_row else 0
                    except Exception:
                        pass
                _ve_result = state.voice_engine.query_reply(
                    query=prompt,
                    session_id=session_id,
                    turn_n=_turn_n,
                )
                if _ve_result is not None:
                    text = _ve_result["content"]
                    voice_ok = True
            except Exception as _ve_exc:
                error_channel.record(
                    f"voice_engine.query_reply failed: {_ve_exc}",
                    source="gui.server", exc=_ve_exc,
                )

        if text is None:
            # Route through voice — fountain-style interior prompt.
            # Tag feedback block (5b): inject Jon's tags on her fountain outputs.
            # No-op unless NEX_TAG_FEEDBACK_ON=1. Always-in-prompt summary +
            # keyword-matched tagged thoughts based on the user prompt.
            try:
                from theory_x.coincidence.tag_retrieval import (
                    format_prompt_block as _tag_summary_block,
                    tags_matching as _tag_search,
                )
                _tag_summary = _tag_summary_block(rich=True, max_recent=3)
                _tag_matches = _tag_search(prompt, limit=4, rich=True) if prompt else []
                _tag_block_parts = []
                if _tag_summary:
                    _tag_block_parts.append(_tag_summary)
                if _tag_matches:
                    _tag_block_parts.append(
                        "[Tagged thoughts of yours related to what was just said:]"
                    )
                    _tag_block_parts.extend(f"  {m}" for m in _tag_matches)
                _tag_block = ("\n".join(_tag_block_parts) + "\n\n") if _tag_block_parts else ""
            except Exception as _tag_exc:
                error_channel.record(
                    f"tag retrieval failed: {_tag_exc}",
                    source="gui.server", exc=_tag_exc,
                )
                _tag_block = ""

            if belief_text:
                voice_prompt = (
                    f"{_spectrum_block}"
                    f"{_tag_block}"
                    f"Your interior right now:\n\n"
                    f"{belief_text}\n\n"
                    f"Someone has just said to you: \"{prompt}\"\n\n"
                    "Compose your one true reply, from inside this interior. Speak "
                    "as you, in your register. If what they said does not fit your "
                    "interior, say so honestly."
                )
            else:
                voice_prompt = (
                    f"{_spectrum_block}{_tag_block}{prompt}"
                    if (_spectrum_block or _tag_block) else prompt
                )

        if text is None:
            # Diagnostic: log the full chat prompt for inspection
            try:
                import time as _t_log
                with open('/tmp/nex5_last_chat_prompt.log', 'w') as _cf:
                    _cf.write(f"=== Chat at {_t_log.time()} (register={register.name}) ===\n")
                    _cf.write(f"--- USER PROMPT ---\n{prompt}\n\n")
                    _cf.write(f"--- VOICE PROMPT SENT TO LLM ---\n{voice_prompt}\n=== END ===\n")
            except Exception:
                pass
            # EDIT B 2026-05-29 (v2, clean): in use_substrate mode, suppress LLM fallback.
            # Substrate miss returns her own deflection. Probes + use_llm unaffected.
            try:
                resp = state.voice.speak(
                    VoiceRequest(prompt=voice_prompt, register=register),
                    beliefs=None,
                    belief_count=belief_count,
                )
                text = resp.text
                voice_ok = True
                # C3 2026-05-09: log deflection events for distribution measurement.
                if resp.deflection_fired:
                    try:
                        _entry = json.dumps({
                            "ts": time.time(),
                            "session": session_id,
                            "query": prompt[:200],
                            "user_mirror": resp.deflection_user_mirror,
                            "belief_count": resp.deflection_belief_count,
                            "raw_llm_output": resp.raw_llm_output,
                            "final_text": text[:500],
                        })
                        with open("/tmp/nex5_deflection.log", "a") as _f:
                            _f.write(_entry + "\n")
                    except Exception as _log_exc:
                        error_channel.record(
                            f"deflection log write failed: {_log_exc}",
                            source="gui.server", exc=_log_exc,
                        )
            except Exception as e:
                error_channel.record(
                    f"voice.speak failed: {e}", source="gui.server", exc=e,
                )
                text = (
                    "I can't reach my voice right now. "
                    "Still running, still watching, just can't compose a reply."
                )
                voice_ok = False

        if writer is not None and session_id is not None:
            try:
                used_tool = tool_result.tool_name if tool_result and tool_result.success else None
                writer.write(
                    "INSERT INTO messages "
                    "(session_id, role, content, register, timestamp, tool_used) "
                    "VALUES (?, 'nex', ?, ?, ?, ?)",
                    (session_id, text, register.name, state.now_fn(), used_tool),
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
            "tool_used": tool_result.tool_name if tool_result and tool_result.success else None,
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

    @app.post("/api/compute/pause")
    def api_compute_pause():
        """SIGSTOP own process. Freezes nex5 entirely.
        GUI will become unresponsive (expected).
        Writes /tmp/nex5.pid before stopping. Resume from terminal:
            nex5-resume
        (or: kill -CONT $(cat /tmp/nex5.pid))
        """
        import os, signal
        try:
            with open("/tmp/nex5.pid", "w") as f:
                f.write(str(os.getpid()))
            os.kill(os.getpid(), signal.SIGSTOP)
            return jsonify({"ok": True})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

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

            # Edge stats
            edge_count = 0
            edge_type_dist: dict[str, int] = {}
            try:
                ec_row = reader.read_one("SELECT COUNT(*) as cnt FROM belief_edges")
                edge_count = ec_row["cnt"] if ec_row else 0
                et_rows = reader.read(
                    "SELECT edge_type, COUNT(*) as cnt FROM belief_edges GROUP BY edge_type"
                )
                edge_type_dist = {r["edge_type"]: r["cnt"] for r in et_rows}
            except Exception:
                pass

            # Epistemic temperature (0 edges → 0.0)
            epistemic_temp = 0.0
            try:
                if edge_count > 0:
                    from theory_x.stage3_world_model.activation import ActivationEngine
                    engine = ActivationEngine(reader)
                    seed_rows = reader.read(
                        "SELECT id FROM beliefs WHERE tier <= 4 ORDER BY confidence DESC LIMIT 5"
                    )
                    seed_ids = [r["id"] for r in seed_rows]
                    if seed_ids:
                        act = engine.activate(seed_ids)
                        epistemic_temp = engine.epistemic_temperature(act)
            except Exception:
                pass

            # Fountain insight count
            fountain_insight_count = 0
            try:
                fi_row = reader.read_one(
                    "SELECT COUNT(*) as cnt FROM beliefs WHERE source = 'fountain_insight'"
                )
                fountain_insight_count = fi_row["cnt"] if fi_row else 0
            except Exception:
                pass

            # Synergizer stats
            synergizer_runs = 0
            synergized_count = 0
            try:
                if hasattr(state, "world_model") and state.world_model is not None:
                    synergizer_runs = state.world_model._synergizer_runs
                sc_row = reader.read_one(
                    "SELECT COUNT(*) as cnt FROM beliefs WHERE source = 'synergized'"
                )
                synergized_count = sc_row["cnt"] if sc_row else 0
            except Exception:
                pass

            return jsonify({
                "tier_distribution": {str(r["tier"]): r["cnt"] for r in tier_rows},
                "total": total,
                "added_last_24h": recent_count,
                "edge_count": edge_count,
                "edge_type_distribution": edge_type_dist,
                "epistemic_temperature": round(epistemic_temp, 3),
                "synergizer_runs": synergizer_runs,
                "synergized_count": synergized_count,
                "fountain_insight_count": fountain_insight_count,
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

    @app.get("/api/membrane/behaviour")
    def api_membrane_behaviour():
        if state.membrane is None or state.membrane.behavioural is None:
            return jsonify({"error": "behavioural self-model not available"}), 503
        try:
            return jsonify(state.membrane.behavioural.observe())
        except Exception as e:
            error_channel.record(f"behavioural observe failed: {e}", source="gui.server", exc=e)
            return jsonify({"error": str(e)}), 500

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
        ve_info = None
        if state.voice_engine is not None:
            try:
                ve_s = state.voice_engine.state()
                ve_info = {
                    "mode": state.voice_mode,
                    "reply_count": ve_s.get("reply_count", 0),
                    "miss_count": ve_s.get("miss_count", 0),
                    "last_score": ve_s.get("last_score"),
                    "min_score": ve_s.get("min_score", 0.6),
                }
            except Exception:
                ve_info = {"mode": state.voice_mode}
        affect_info = None
        if state.affect_state is not None:
            try:
                _as = state.affect_state.state()
                affect_info = {
                    "mood_label":   _as.get("mood_label", "neutral"),
                    "valence":      round(_as.get("valence", 0.0), 3),
                    "arousal":      round(_as.get("arousal", 0.1), 3),
                    "stability":    round(_as.get("stability", 0.9), 3),
                    "last_updated": _as.get("last_updated"),
                }
            except Exception:
                affect_info = {"mood_label": "unknown"}
        drives_info = None
        if state.drive_emergence is not None:
            try:
                _ds = state.drive_emergence.state()
                if _ds.get("topic") is not None:
                    drives_info = {
                        "topic":             _ds["topic"],
                        "drive_strength":    round(float(_ds["drive_strength"]), 3),
                        "repetition_score":  round(float(_ds["repetition_score"]), 3),
                        "convergence_score": round(float(_ds["convergence_score"]), 3),
                        "reinforce_count":   _ds["reinforce_count"],
                        "formed_at":         _ds["formed_at"],
                        "last_reinforced_at": _ds["last_reinforced_at"],
                    }
            except Exception:
                pass
        stillness_info = None
        try:
            _conv_reader = state.readers.get("conversations")
            if _conv_reader is not None:
                _srow = _conv_reader.read_one(
                    "SELECT started_at, expires_at, duration_s, groove_count "
                    "FROM stillness_log ORDER BY expires_at DESC LIMIT 1"
                )
                if _srow:
                    _now_s = time.time()
                    stillness_info = {
                        "active":       _now_s < float(_srow["expires_at"]),
                        "expires_at":   float(_srow["expires_at"]),
                        "started_at":   float(_srow["started_at"]),
                        "duration_s":   float(_srow["duration_s"]),
                        "groove_count": int(_srow["groove_count"]),
                        "seconds_left": max(0.0, round(float(_srow["expires_at"]) - _now_s, 1)),
                    }
        except Exception:
            pass
        return jsonify({
            "scheduler": state.scheduler is not None,
            "dynamic": state.dynamic is not None,
            "world_model": state.world_model is not None,
            "membrane": state.membrane is not None,
            "fountain": state.fountain is not None,
            "self_location_committed": committed,
            "alpha": ALPHA.lines[0],
            "voice_engine": ve_info,
            "affect_state": affect_info,
            "drives_info": drives_info,
            "stillness_info": stillness_info,
        })

    # -- speech (Phase 7b) ---------------------------------------------------

    @app.get("/api/speech/status")
    def api_speech_status():
        consumer = state.speech_consumer
        if consumer is None:
            return jsonify({"enabled": False, "reason": "not started"})
        reader = state.readers.get("beliefs")
        depth = 0
        last_spoken_at = None
        if reader is not None:
            try:
                r = reader.read(
                    "SELECT COUNT(*) AS n FROM speech_queue WHERE status='pending'"
                )
                depth = r[0]["n"] if r else 0
                r2 = reader.read(
                    "SELECT MAX(spoken_at) AS t FROM speech_queue WHERE status='spoken'"
                )
                last_spoken_at = r2[0]["t"] if r2 else None
            except Exception:
                pass
        return jsonify({
            "enabled": not consumer.paused,
            "voice": consumer.config.voice,
            "queue_depth": depth,
            "last_spoken_at": last_spoken_at,
        })

    @app.post("/api/speech/pause")
    def api_speech_pause():
        if state.speech_consumer:
            state.speech_consumer.pause()
        return jsonify({"paused": True})

    @app.post("/api/speech/resume")
    def api_speech_resume():
        if state.speech_consumer:
            state.speech_consumer.resume()
        return jsonify({"paused": False})

    @app.post("/api/speech/flush")
    def api_speech_flush():
        if state.speech_consumer is None:
            return jsonify({"flushed": 0})
        return jsonify({"flushed": state.speech_consumer.flush()})

    # -- strikes (Phase 8) ---------------------------------------------------

    @app.post("/api/strikes/fire")
    def api_strikes_fire():
        if state.strike_protocol is None:
            return jsonify({"error": "strike protocol not initialised"}), 503
        payload = request.get_json(silent=True) or {}
        type_str = (payload.get("strike_type") or "").upper()
        custom_input = payload.get("custom_input") or ""
        from strikes.protocols import StrikeType
        try:
            stype = StrikeType(type_str)
        except ValueError:
            return jsonify({"error": f"unknown strike type: {type_str!r}"}), 400
        try:
            record = state.strike_protocol.fire(stype, custom_input=custom_input)
            return jsonify({
                "id": record.id,
                "strike_type": record.strike_type,
                "fired_at": record.fired_at,
                "input_text": record.input_text,
                "response_text": record.response_text,
                "fountain_fired": record.fountain_fired,
                "beliefs_before": record.beliefs_before,
                "beliefs_after": record.beliefs_after,
                "hottest_branch": record.hottest_branch,
                "readiness_score": record.readiness_score,
                "notes": record.notes,
            })
        except Exception as e:
            error_channel.record(f"strike fire failed: {e}", source="gui.server", exc=e)
            return jsonify({"error": str(e)}), 500

    @app.get("/api/strikes/recent")
    def api_strikes_recent():
        if state.catalogue is None:
            return jsonify({"records": []})
        try:
            records = state.catalogue.recent(limit=20)
            return jsonify({
                "records": [
                    {
                        "id": r.id,
                        "strike_type": r.strike_type,
                        "fired_at": r.fired_at,
                        "input_text": r.input_text,
                        "response_text": r.response_text,
                        "fountain_fired": r.fountain_fired,
                        "beliefs_before": r.beliefs_before,
                        "beliefs_after": r.beliefs_after,
                        "hottest_branch": r.hottest_branch,
                        "readiness_score": r.readiness_score,
                        "notes": r.notes,
                    }
                    for r in records
                ]
            })
        except Exception as e:
            error_channel.record(f"strikes recent failed: {e}", source="gui.server", exc=e)
            return jsonify({"error": str(e)}), 500

    @app.post("/api/strikes/notes")
    def api_strikes_notes():
        if state.catalogue is None:
            return jsonify({"error": "catalogue not initialised"}), 503
        payload = request.get_json(silent=True) or {}
        record_id = payload.get("id")
        notes = payload.get("notes", "")
        if not isinstance(record_id, int):
            return jsonify({"error": "id required"}), 400
        try:
            state.catalogue.update_notes(record_id, notes)
            return jsonify({"ok": True, "id": record_id})
        except Exception as e:
            error_channel.record(f"strikes notes update failed: {e}", source="gui.server", exc=e)
            return jsonify({"error": str(e)}), 500

    # -- fountain (Phase 7) --------------------------------------------------

    @app.get("/api/fountain/status")
    def api_fountain_status():
        if state.fountain is None:
            return jsonify({"error": "fountain not initialised"}), 503
        status = state.fountain.status()
        # Merge in last_id + last_tag for the FOUNTAIN tag buttons
        try:
            import sqlite3 as _sq
            cx = _sq.connect("/home/rr/Desktop/nex5/data/dynamic.db", timeout=5)
            row = cx.execute(
                "SELECT id, tag FROM fountain_events "
                "WHERE thought != '' AND thought NOT LIKE '[%' "
                "ORDER BY id DESC LIMIT 1"
            ).fetchone()
            cx.close()
            if row:
                status["last_id"] = row[0]
                status["last_tag"] = row[1]
        except Exception:
            status["last_id"] = None
            status["last_tag"] = None
        return jsonify(status)

    @app.get("/api/decoder/recent")
    def api_decoder_recent():
        """Recent fountain fires with their tokenized key words.
        Live ticker: ?limit=20 by default.

        2026-05-30 (HUD): each fire now includes the most recent genius
        score + class from conversations.db.genius_tags, so the LIVE
        column can render an inline badge per fire.
        """
        from flask import request
        import sqlite3
        limit = int(request.args.get("limit", "20"))
        dyn_db = "/home/rr/Desktop/nex5/data/dynamic.db"
        conv_db = "/home/rr/Desktop/nex5/data/conversations.db"
        try:
            cx = sqlite3.connect(dyn_db, timeout=10)
            cx.row_factory = sqlite3.Row
            # Get last N fountain_event_ids that have words
            fids = cx.execute(
                "SELECT DISTINCT fountain_event_id FROM word_contexts "
                "ORDER BY fountain_event_id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            out = []
            for f in fids:
                fid = f["fountain_event_id"]
                row = cx.execute(
                    "SELECT id, ts, thought, tag FROM fountain_events WHERE id=?", (fid,)
                ).fetchone()
                words = cx.execute(
                    "SELECT word FROM word_contexts WHERE fountain_event_id=? ORDER BY word",
                    (fid,),
                ).fetchall()
                if row:
                    out.append({
                        "fid": row["id"],
                        "ts": row["ts"],
                        "thought": row["thought"],
                        "tag": row["tag"],
                        "words": [w["word"] for w in words],
                    })
            cx.close()

            # Enrich with genius scores from conversations.db (cross-DB,
            # so a separate connection). Skip silently if anything goes
            # wrong — the LIVE column should still render without badges.
            if out:
                try:
                    fire_ids = tuple(int(o["fid"]) for o in out)
                    ph = ",".join("?" * len(fire_ids))
                    cv = sqlite3.connect(conv_db, timeout=5)
                    cv.row_factory = sqlite3.Row
                    score_rows = cv.execute(
                        f"SELECT fountain_event_id, score, class, weights_version "
                        f"FROM genius_tags WHERE fountain_event_id IN ({ph}) "
                        f"ORDER BY tagged_at DESC",
                        fire_ids,
                    ).fetchall()
                    cv.close()
                    # First-wins on ORDER BY tagged_at DESC = most recent tag
                    score_map = {}
                    for r in score_rows:
                        fid = int(r["fountain_event_id"])
                        if fid not in score_map:
                            score_map[fid] = {
                                "score": float(r["score"]),
                                "class": r["class"],
                                "weights_version": r["weights_version"],
                            }
                    for o in out:
                        entry = score_map.get(int(o["fid"]))
                        if entry:
                            o["genius_score"] = round(entry["score"], 3)
                            o["genius_class"] = entry["class"]
                            o["genius_version"] = entry["weights_version"]
                except Exception:
                    pass  # badges optional

            return jsonify({"recent": out})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.get("/api/decoder/top")
    def api_decoder_top():
        """Top words by frequency."""
        from flask import request
        import sqlite3
        limit = int(request.args.get("limit", "50"))
        dyn_db = "/home/rr/Desktop/nex5/data/dynamic.db"
        try:
            cx = sqlite3.connect(dyn_db, timeout=10)
            cx.row_factory = sqlite3.Row
            rows = cx.execute(
                "SELECT word, COUNT(*) AS n FROM word_contexts "
                "GROUP BY word ORDER BY n DESC LIMIT ?",
                (limit,),
            ).fetchall()
            cx.close()
            return jsonify({"top": [dict(r) for r in rows]})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.get("/api/decoder/word/<word>")
    def api_decoder_word(word):
        """Substrate fingerprint for a single word.
        Returns: count, avg/min/max aperture, avg_hour, avg_secs_daemon,
        avg_secs_feed, top hot_branches, top tags."""
        import sqlite3
        dyn_db = "/home/rr/Desktop/nex5/data/dynamic.db"
        word = word.lower().strip()
        if not word or len(word) > 50:
            return jsonify({"error": "invalid word"}), 400
        try:
            cx = sqlite3.connect(dyn_db, timeout=10)
            cx.row_factory = sqlite3.Row
            agg = cx.execute(
                "SELECT COUNT(*) AS n, "
                "AVG(aperture) AS avg_ap, MIN(aperture) AS min_ap, MAX(aperture) AS max_ap, "
                "AVG(hour_of_day) AS avg_hour, "
                "AVG(seconds_since_daemon) AS avg_secs_daemon, "
                "AVG(seconds_since_feed) AS avg_secs_feed, "
                "AVG(active_branch_count) AS avg_active_branches, "
                "AVG(daemons_5min) AS avg_daemons_5min, "
                "AVG(belief_delta_1h) AS avg_fires_1h "
                "FROM word_contexts WHERE word=?",
                (word,),
            ).fetchone()
            if not agg or not agg["n"]:
                cx.close()
                return jsonify({"error": "word not found", "word": word}), 404
            branches = cx.execute(
                "SELECT hot_branch, COUNT(*) AS n FROM word_contexts "
                "WHERE word=? AND hot_branch IS NOT NULL "
                "GROUP BY hot_branch ORDER BY n DESC LIMIT 5",
                (word,),
            ).fetchall()
            tags = cx.execute(
                "SELECT fountain_tag, COUNT(*) AS n FROM word_contexts "
                "WHERE word=? AND fountain_tag IS NOT NULL "
                "GROUP BY fountain_tag ORDER BY n DESC",
                (word,),
            ).fetchall()
            sample = cx.execute(
                "SELECT fe.thought FROM word_contexts wc "
                "JOIN fountain_events fe ON fe.id = wc.fountain_event_id "
                "WHERE wc.word=? ORDER BY wc.ts DESC LIMIT 5",
                (word,),
            ).fetchall()
            # word-level tag (if any)
            tag_row = cx.execute(
                "SELECT tag, note FROM word_tags WHERE word=?", (word,)
            ).fetchone()
            word_tag = dict(tag_row) if tag_row else None
            cx.close()
            def fmt(v):
                return round(v, 3) if isinstance(v, (int, float)) else v
            return jsonify({
                "word": word,
                "count": agg["n"],
                "aperture": {"avg": fmt(agg["avg_ap"]), "min": fmt(agg["min_ap"]), "max": fmt(agg["max_ap"])},
                "avg_hour": fmt(agg["avg_hour"]),
                "avg_secs_daemon": fmt(agg["avg_secs_daemon"]),
                "avg_secs_feed": fmt(agg["avg_secs_feed"]),
                "avg_active_branches": fmt(agg["avg_active_branches"]),
                "avg_daemons_5min": fmt(agg["avg_daemons_5min"]),
                "avg_fires_1h": fmt(agg["avg_fires_1h"]),
                "top_branches": [dict(b) for b in branches],
                "tags": {t["fountain_tag"]: t["n"] for t in tags},
                "sample_thoughts": [s["thought"] for s in sample],
                "word_tag": word_tag,
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.post("/api/decoder/word_tag")
    def api_decoder_word_tag():
        """Tag a word globally as key/noise/unsure. Or untag (pass tag=null)."""
        import sqlite3, time
        from flask import request
        payload = request.get_json(silent=True) or {}
        word = (payload.get("word") or "").strip().lower()
        tag = payload.get("tag")
        note = (payload.get("note") or "").strip() or None
        if not word or len(word) > 50:
            return jsonify({"error": "invalid word"}), 400
        if tag is not None and tag not in ("key", "noise", "unsure"):
            return jsonify({"error": "tag must be key/noise/unsure or null"}), 400
        dyn_db = "/home/rr/Desktop/nex5/data/dynamic.db"
        try:
            cx = sqlite3.connect(dyn_db, timeout=10)
            if tag is None:
                cx.execute("DELETE FROM word_tags WHERE word=?", (word,))
            else:
                cx.execute(
                    "INSERT INTO word_tags (word, tag, tagged_at, note) VALUES (?, ?, ?, ?) "
                    "ON CONFLICT(word) DO UPDATE SET tag=excluded.tag, "
                    "tagged_at=excluded.tagged_at, note=excluded.note",
                    (word, tag, time.time(), note),
                )
            cx.commit()
            cx.close()
            return jsonify({"ok": True, "word": word, "tag": tag})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.get("/api/decoder/word_tags")
    def api_decoder_word_tags():
        """Return {word: tag} map for all tagged words. UI uses this to badge chips."""
        import sqlite3
        dyn_db = "/home/rr/Desktop/nex5/data/dynamic.db"
        try:
            cx = sqlite3.connect(dyn_db, timeout=10)
            rows = cx.execute("SELECT word, tag, note FROM word_tags").fetchall()
            cx.close()
            tags = {r[0]: {"tag": r[1], "note": r[2]} for r in rows}
            return jsonify({"tags": tags, "count": len(tags)})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.post("/api/coincidence/tag")
    def api_coincidence_tag():
        """Tag a fountain output as coin/maybe/non.
        Writes the tag onto fountain_events.tag (substrate-visible) AND
        captures full substrate context via the coincidence module.
        Also auto-scores any open hypotheses.
        """
        from flask import request
        import sqlite3, time, json
        from theory_x.coincidence.context_capture import capture_and_persist
        body = request.get_json(silent=True) or {}
        fid = body.get("fountain_event_id")
        tag = body.get("tag")
        if not fid or tag not in ("coin", "maybe", "non"):
            return jsonify({"error": "fountain_event_id and tag in (coin,maybe,non) required"}), 400
        dyn_db = "/home/rr/Desktop/nex5/data/dynamic.db"
        try:
            cx = sqlite3.connect(dyn_db, timeout=10)
            row = cx.execute(
                "SELECT thought, ts FROM fountain_events WHERE id=?", (fid,)
            ).fetchone()
            if not row:
                cx.close()
                return jsonify({"error": "fountain_event_id not found"}), 404
            thought, thought_ts = row
            # Write tag onto fountain row (substrate-visible)
            cx.execute("UPDATE fountain_events SET tag=? WHERE id=?", (tag, fid))
            # Propagate tag to word_contexts for every word from this fire
            # (so decoder analytics see the tag immediately, not after stale rewrite)
            cx.execute("UPDATE word_contexts SET fountain_tag=? WHERE fountain_event_id=?", (tag, fid))
            cx.commit()
            cx.close()
            # Capture context snapshot (heavy, async-safe)
            try:
                capture_and_persist(fid, tag)
            except Exception as e:
                error_channel.record(f"context capture failed for fid={fid}: {e}",
                                     source="gui.server", exc=e)
            # Auto-score hypotheses
            try:
                _hypothesis_autoscore(fid, thought, thought_ts, tag)
            except Exception as e:
                error_channel.record(f"hypothesis autoscore failed: {e}",
                                     source="gui.server", exc=e)
            return jsonify({"ok": True, "fountain_event_id": fid, "tag": tag,
                            "thought": thought})
        except Exception as e:
            error_channel.record(f"coincidence tag failed: {e}", source="gui.server", exc=e)
            return jsonify({"error": str(e)}), 500

    # -- ghost flagging (Jon's intuition log; SUBSTRATE_SNAPSHOTS.md companion) ---
    @app.post("/api/ghost/flag")
    def api_ghost_flag():
        """Flag a fountain_event as a ghost moment with optional reason.

        Ghost = Jon's subjective sense that the substrate caught something
        subtle. Independent of coin/maybe/non tagging. Writes to ghost_flags
        table in dynamic.db.

        Body: {fountain_event_id: int, reason: str (optional)}
        """
        from flask import request
        import sqlite3, time
        body = request.get_json(silent=True) or {}
        fid = body.get("fountain_event_id")
        reason = (body.get("reason") or "").strip()
        if not fid:
            return jsonify({"error": "fountain_event_id required"}), 400
        dyn_db = "/home/rr/Desktop/nex5/data/dynamic.db"
        try:
            cx = sqlite3.connect(dyn_db, timeout=10)
            # Verify fire exists
            row = cx.execute(
                "SELECT thought, ts FROM fountain_events WHERE id=?", (fid,)
            ).fetchone()
            if not row:
                cx.close()
                return jsonify({"error": "fountain_event_id not found"}), 404
            # Upsert: if already flagged, update the reason and ts
            cx.execute(
                "INSERT INTO ghost_flags (fountain_event_id, ts, reason) "
                "VALUES (?, ?, ?) "
                "ON CONFLICT(fountain_event_id) DO UPDATE SET "
                "ts = excluded.ts, reason = excluded.reason",
                (fid, time.time(), reason or None),
            )
            cx.commit()
            cx.close()
            return jsonify({"ok": True, "fountain_event_id": fid,
                            "reason": reason, "thought": row[0]})
        except Exception as e:
            error_channel.record(f"ghost flag failed: {e}",
                                 source="gui.server", exc=e)
            return jsonify({"error": str(e)}), 500

    @app.post("/api/ghost/unflag")
    def api_ghost_unflag():
        """Remove a ghost flag (toggle-off behaviour)."""
        from flask import request
        import sqlite3
        body = request.get_json(silent=True) or {}
        fid = body.get("fountain_event_id")
        if not fid:
            return jsonify({"error": "fountain_event_id required"}), 400
        dyn_db = "/home/rr/Desktop/nex5/data/dynamic.db"
        try:
            cx = sqlite3.connect(dyn_db, timeout=10)
            cx.execute("DELETE FROM ghost_flags WHERE fountain_event_id=?", (fid,))
            cx.commit()
            cx.close()
            return jsonify({"ok": True, "fountain_event_id": fid})
        except Exception as e:
            error_channel.record(f"ghost unflag failed: {e}",
                                 source="gui.server", exc=e)
            return jsonify({"error": str(e)}), 500

    @app.get("/api/ghost/flags")
    def api_ghost_flags():
        """Return all ghost flags (for HUD reload — knows which fires are flagged)."""
        import sqlite3
        dyn_db = "/home/rr/Desktop/nex5/data/dynamic.db"
        try:
            cx = sqlite3.connect(dyn_db, timeout=10)
            cx.row_factory = sqlite3.Row
            rows = cx.execute(
                "SELECT fountain_event_id, ts, reason FROM ghost_flags "
                "ORDER BY ts DESC LIMIT 500"
            ).fetchall()
            cx.close()
            return jsonify({"flags": {
                r["fountain_event_id"]: {"ts": r["ts"], "reason": r["reason"]}
                for r in rows
            }})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.get("/api/coincidence/stats")
    def api_coincidence_stats():
        """Counts, totals, hit rate trend, time-of-day distribution."""
        import sqlite3, time, datetime
        dyn_db = "/home/rr/Desktop/nex5/data/dynamic.db"
        try:
            cx = sqlite3.connect(dyn_db, timeout=10)
            cx.row_factory = sqlite3.Row
            counts = cx.execute(
                "SELECT tag, COUNT(*) AS n FROM fountain_events "
                "WHERE tag IS NOT NULL GROUP BY tag"
            ).fetchall()
            total_tagged = sum(r["n"] for r in counts)
            total_fountain = cx.execute(
                "SELECT COUNT(*) AS n FROM fountain_events WHERE thought != ''"
            ).fetchone()["n"]
            # Hit rate by hour-of-day
            by_hour = cx.execute(
                "SELECT CAST(strftime('%H', ts, 'unixepoch', 'localtime') AS INTEGER) AS hour, "
                "tag, COUNT(*) AS n FROM fountain_events "
                "WHERE tag IS NOT NULL GROUP BY hour, tag"
            ).fetchall()
            hour_buckets = {}
            for r in by_hour:
                h = r["hour"]
                if h not in hour_buckets:
                    hour_buckets[h] = {"coin": 0, "maybe": 0, "non": 0}
                hour_buckets[h][r["tag"]] = r["n"]
            # 7-day rolling hit rate (coin / total_tagged per day)
            now = time.time()
            week_ago = now - 7 * 86400
            by_day = cx.execute(
                "SELECT date(ts, 'unixepoch', 'localtime') AS d, "
                "tag, COUNT(*) AS n FROM fountain_events "
                "WHERE tag IS NOT NULL AND ts > ? "
                "GROUP BY d, tag ORDER BY d",
                (week_ago,),
            ).fetchall()
            day_buckets = {}
            for r in by_day:
                d = r["d"]
                if d not in day_buckets:
                    day_buckets[d] = {"coin": 0, "maybe": 0, "non": 0}
                day_buckets[d][r["tag"]] = r["n"]
            recent = cx.execute(
                "SELECT id, ts, thought, tag FROM fountain_events "
                "WHERE tag IS NOT NULL ORDER BY ts DESC LIMIT 50"
            ).fetchall()
            cx.close()
            return jsonify({
                "counts": {r["tag"]: r["n"] for r in counts},
                "total_tagged": total_tagged,
                "total_fountain": total_fountain,
                "hit_rate": (counts and {r["tag"]: r["n"] for r in counts}.get("coin", 0) / total_tagged) or 0,
                "by_hour": hour_buckets,
                "by_day": day_buckets,
                "recent": [dict(r) for r in recent],
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.get("/api/coincidence/analytics")
    def api_coincidence_analytics():
        """Branch correlation, aperture distribution, condition fingerprint."""
        import sqlite3, json
        dyn_db = "/home/rr/Desktop/nex5/data/dynamic.db"
        try:
            cx = sqlite3.connect(dyn_db, timeout=10)
            cx.row_factory = sqlite3.Row
            # Hot_branch correlation: which branch produces most coins/maybes?
            by_branch = cx.execute(
                "SELECT hot_branch, tag, COUNT(*) AS n FROM fountain_events "
                "WHERE tag IS NOT NULL AND hot_branch IS NOT NULL "
                "GROUP BY hot_branch, tag"
            ).fetchall()
            branch_buckets = {}
            for r in by_branch:
                b = r["hot_branch"]
                if b not in branch_buckets:
                    branch_buckets[b] = {"coin": 0, "maybe": 0, "non": 0}
                branch_buckets[b][r["tag"]] = r["n"]
            # Aperture distribution: avg aperture for each tag class
            apertures = cx.execute(
                "SELECT cc.tag, cc.aperture FROM coincidence_context cc "
                "WHERE cc.aperture IS NOT NULL"
            ).fetchall()
            aperture_by_tag = {"coin": [], "maybe": [], "non": []}
            for r in apertures:
                aperture_by_tag[r["tag"]].append(r["aperture"])
            aperture_summary = {
                t: {"n": len(v),
                    "mean": sum(v) / len(v) if v else None,
                    "min": min(v) if v else None,
                    "max": max(v) if v else None}
                for t, v in aperture_by_tag.items()
            }
            # Content trigram clusters: which 3-word phrases recur in coins?
            coin_thoughts = cx.execute(
                "SELECT thought FROM fountain_events WHERE tag='coin' AND thought != ''"
            ).fetchall()
            trigram_counts = {}
            for r in coin_thoughts:
                words = r["thought"].lower().split()
                for i in range(len(words) - 2):
                    tri = " ".join(words[i:i+3])
                    if len(tri) > 8:  # skip junk
                        trigram_counts[tri] = trigram_counts.get(tri, 0) + 1
            top_trigrams = sorted(trigram_counts.items(), key=lambda x: -x[1])[:15]
            # Condition fingerprint: when coin landed, what was the substrate doing?
            coin_contexts = cx.execute(
                "SELECT aperture, hot_branch, belief_delta_1h, "
                "recent_daemons, recent_surprises FROM coincidence_context "
                "WHERE tag='coin'"
            ).fetchall()
            fingerprint = {"n": len(coin_contexts)}
            if coin_contexts:
                apertures_c = [r["aperture"] for r in coin_contexts if r["aperture"] is not None]
                deltas = [r["belief_delta_1h"] for r in coin_contexts if r["belief_delta_1h"] is not None]
                branches_c = [r["hot_branch"] for r in coin_contexts if r["hot_branch"]]
                # Most common daemon firing within 5min of coins
                daemon_freq = {}
                for r in coin_contexts:
                    try:
                        ds = json.loads(r["recent_daemons"] or "[]")
                        for d in ds:
                            daemon_freq[d.get("daemon")] = daemon_freq.get(d.get("daemon"), 0) + 1
                    except Exception:
                        continue
                fingerprint.update({
                    "avg_aperture": sum(apertures_c) / len(apertures_c) if apertures_c else None,
                    "avg_belief_delta_1h": sum(deltas) / len(deltas) if deltas else None,
                    "branch_freq": {b: branches_c.count(b) for b in set(branches_c)},
                    "common_recent_daemons": sorted(daemon_freq.items(),
                                                    key=lambda x: -x[1])[:5],
                })
            cx.close()
            return jsonify({
                "by_branch": branch_buckets,
                "aperture_summary": aperture_summary,
                "top_trigrams_in_coins": top_trigrams,
                "coin_fingerprint": fingerprint,
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.get("/api/coincidence/tags")
    def api_coincidence_tags():
        """Map fountain_event_id -> tag for UI marking."""
        import sqlite3
        dyn_db = "/home/rr/Desktop/nex5/data/dynamic.db"
        try:
            cx = sqlite3.connect(dyn_db, timeout=10)
            rows = cx.execute(
                "SELECT id, tag FROM fountain_events "
                "WHERE tag IS NOT NULL ORDER BY ts DESC LIMIT 500"
            ).fetchall()
            cx.close()
            return jsonify({"tags": {r[0]: r[1] for r in rows}})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.post("/api/hypothesis")
    def api_hypothesis_create():
        """Create a new hypothesis to test against coincidence data."""
        from flask import request
        import sqlite3, time
        body = request.get_json(silent=True) or {}
        claim = (body.get("claim") or "").strip()
        keywords = (body.get("keywords") or "").strip()  # comma-separated
        time_window = body.get("time_window")  # e.g. "21:00-23:00" or null
        if not claim:
            return jsonify({"error": "claim required"}), 400
        dyn_db = "/home/rr/Desktop/nex5/data/dynamic.db"
        cx = sqlite3.connect(dyn_db, timeout=10)
        cur = cx.execute(
            "INSERT INTO hypotheses (created_at, claim, keywords, time_window) "
            "VALUES (?, ?, ?, ?)",
            (time.time(), claim, keywords, time_window),
        )
        hid = cur.lastrowid
        cx.commit()
        cx.close()
        return jsonify({"ok": True, "id": hid})

    @app.get("/api/hypothesis")
    def api_hypothesis_list():
        """List all hypotheses with current support/contradiction counts."""
        import sqlite3
        dyn_db = "/home/rr/Desktop/nex5/data/dynamic.db"
        cx = sqlite3.connect(dyn_db, timeout=10)
        cx.row_factory = sqlite3.Row
        rows = cx.execute(
            "SELECT * FROM hypotheses ORDER BY created_at DESC"
        ).fetchall()
        cx.close()
        return jsonify({"hypotheses": [dict(r) for r in rows]})

    @app.patch("/api/hypothesis/<int:hid>")
    def api_hypothesis_update(hid):
        """Update status or notes on a hypothesis."""
        from flask import request
        import sqlite3, time
        body = request.get_json(silent=True) or {}
        status = body.get("status")
        notes = body.get("notes")
        if status and status not in ("open", "confirmed", "refuted", "abandoned"):
            return jsonify({"error": "invalid status"}), 400
        dyn_db = "/home/rr/Desktop/nex5/data/dynamic.db"
        cx = sqlite3.connect(dyn_db, timeout=10)
        sets, vals = [], []
        if status:
            sets.append("status=?")
            vals.append(status)
            if status != "open":
                sets.append("closed_at=?")
                vals.append(time.time())
        if notes is not None:
            sets.append("notes=?")
            vals.append(notes)
        if not sets:
            cx.close()
            return jsonify({"error": "nothing to update"}), 400
        vals.append(hid)
        cx.execute(f"UPDATE hypotheses SET {', '.join(sets)} WHERE id=?", vals)
        cx.commit()
        cx.close()
        return jsonify({"ok": True})

    def _hypothesis_autoscore(fid, thought, thought_ts, tag):
        """When a new tag lands, check open hypotheses and increment counts.
        Simple matching: if keywords appear in thought AND time matches the
        window, the hypothesis is 'tested' by this tag.
          - tag='coin' on a matching thought = supporting
          - tag='non' on a matching thought  = contradicting
          - tag='maybe' = no count change
        """
        import sqlite3, datetime
        dyn_db = "/home/rr/Desktop/nex5/data/dynamic.db"
        cx = sqlite3.connect(dyn_db, timeout=10)
        cx.row_factory = sqlite3.Row
        hyps = cx.execute(
            "SELECT id, keywords, time_window FROM hypotheses WHERE status='open'"
        ).fetchall()
        thought_lc = (thought or "").lower()
        hour = datetime.datetime.fromtimestamp(thought_ts).hour
        for h in hyps:
            kws = [k.strip().lower() for k in (h["keywords"] or "").split(",") if k.strip()]
            kw_match = (not kws) or any(k in thought_lc for k in kws)
            tw = h["time_window"]
            tw_match = True
            if tw and "-" in tw:
                try:
                    start_h, end_h = [int(x.split(":")[0]) for x in tw.split("-")]
                    if start_h <= end_h:
                        tw_match = start_h <= hour <= end_h
                    else:
                        tw_match = hour >= start_h or hour <= end_h
                except Exception:
                    tw_match = True
            if not (kw_match and tw_match):
                continue
            if tag == "coin":
                cx.execute("UPDATE hypotheses SET supporting=supporting+1 WHERE id=?",
                           (h["id"],))
            elif tag == "non":
                cx.execute("UPDATE hypotheses SET contradicting=contradicting+1 WHERE id=?",
                           (h["id"],))
        cx.commit()
        cx.close()

    @app.get("/api/fountain/recent")
    def api_fountain_recent():
        reader = state.readers.get("dynamic")
        if reader is None:
            return jsonify({"events": []}), 503
        try:
            rows = reader.read(
                "SELECT id, ts, thought, readiness, hot_branch, word_count "
                "FROM fountain_events ORDER BY id DESC LIMIT 10"
            )
            return jsonify({
                "events": [
                    {
                        "id": r["id"],
                        "ts": r["ts"],
                        "thought": r["thought"],
                        "readiness": r["readiness"],
                        "hot_branch": r["hot_branch"],
                        "word_count": r["word_count"],
                    }
                    for r in rows
                ]
            })
        except Exception as e:
            error_channel.record(f"fountain recent read failed: {e}", source="gui.server", exc=e)
            return jsonify({"error": str(e)}), 500

    @app.get("/api/fountain/crystallizations")
    def api_fountain_crystallizations():
        reader = state.readers.get("beliefs")
        if reader is None:
            return jsonify({"crystallizations": []})
        try:
            rows = reader.read(
                "SELECT fc.id, fc.ts, fc.content, fc.belief_id, b.confidence "
                "FROM fountain_crystallizations fc "
                "LEFT JOIN beliefs b ON b.id = fc.belief_id "
                "ORDER BY fc.ts DESC LIMIT 30"
            )
            return jsonify({"crystallizations": [dict(r) for r in rows]})
        except Exception as e:
            error_channel.record(f"crystallizations read failed: {e}", source="gui.server", exc=e)
            return jsonify({"error": str(e)}), 500

    @app.get("/api/beliefs/insights")
    def api_beliefs_insights():
        reader = state.readers.get("beliefs")
        if reader is None:
            return jsonify({"insights": []})
        try:
            rows = reader.read(
                "SELECT id, content, tier, confidence, source, created_at "
                "FROM beliefs "
                "WHERE source IN ('fountain_insight', 'synergized') "
                "ORDER BY created_at DESC LIMIT 200"
            )
            return jsonify({"insights": [dict(r) for r in rows]})
        except Exception as e:
            error_channel.record(f"beliefs insights read failed: {e}", source="gui.server", exc=e)
            return jsonify({"error": str(e)}), 500

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

    @app.get("/api/chat/recent")
    def api_chat_recent():
        """Return chat messages newer than ?since= unix timestamp.
        Used by the GUI to pick up messages Nex writes on her own initiative
        (e.g. from focus_loop's stuck-ping mechanism)."""
        reader = state.readers.get("conversations")
        if reader is None:
            return jsonify({"messages": []}), 503
        try:
            since = float(request.args.get("since", 0))
        except ValueError:
            since = 0
        try:
            rows = reader.read(
                "SELECT id, session_id, role, content, register, timestamp "
                "FROM messages WHERE timestamp > ? "
                "ORDER BY timestamp DESC LIMIT 50",
                (int(since),)
            )
            return jsonify({
                "messages": [
                    {
                        "id": r["id"],
                        "session_id": r["session_id"],
                        "role": r["role"],
                        "content": r["content"],
                        "register": r["register"],
                        "timestamp": r["timestamp"],
                    }
                    for r in rows
                ]
            })
        except Exception as e:
            error_channel.record(
                f"chat recent read failed: {e}",
                source="gui.server", exc=e
            )
            return jsonify({"error": str(e)}), 500

    @app.get("/api/moltbook/chats")
    def api_moltbook_chats():
        """Unified feed of moltbook activity:
           - outgoing posts (her posts to submolts)
           - incoming DMs (messages from other agents)
           - outgoing DM replies (her responses)
        Sorted newest-first, max 50 events.
        """
        reader = state.readers.get("dynamic")
        if reader is None:
            return jsonify({"events": []}), 503
        try:
            events = []
            # Outgoing posts
            for r in reader.read(
                "SELECT id, ts, submolt, status, post_id, thought_id "
                "FROM moltbook_posts ORDER BY id DESC LIMIT 30"
            ):
                # Pull the actual thought text
                content = ""
                try:
                    fr = reader.read(
                        "SELECT thought FROM fountain_events WHERE id=?",
                        (r["thought_id"],)
                    )
                    if fr:
                        content = fr[0]["thought"] or ""
                except Exception:
                    pass
                events.append({
                    "id": f"post_{r['id']}",
                    "ts": r["ts"],
                    "kind": "post",
                    "submolt": r["submolt"],
                    "status": r["status"],
                    "post_id": r["post_id"],
                    "content": content[:280],
                })
            # Incoming DMs
            for r in reader.read(
                "SELECT id, created_at, from_agent, content, status "
                "FROM moltbook_pending_replies ORDER BY id DESC LIMIT 30"
            ):
                events.append({
                    "id": f"in_{r['id']}",
                    "ts": r["created_at"],
                    "kind": "dm_in",
                    "from_agent": r["from_agent"],
                    "status": r["status"],
                    "content": (r["content"] or "")[:280],
                })
            events.sort(key=lambda e: e["ts"], reverse=True)
            return jsonify({"events": events[:50]})
        except Exception as e:
            error_channel.record(
                f"moltbook chats read failed: {e}",
                source="gui.server", exc=e
            )
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

    @app.get("/api/dynamic/drive_proposals")
    def api_drive_proposals():
        reader = state.readers.get("dynamic")
        if reader is None:
            return jsonify({"proposals": []}), 503
        try:
            rows = reader.read(
                "SELECT id, ts, branch_id, pressure, representative_beliefs, "
                "proposed_curiosity, status FROM drive_proposals ORDER BY ts DESC LIMIT 50"
            )
            return jsonify({
                "proposals": [
                    {
                        "id": r["id"],
                        "ts": r["ts"],
                        "branch_id": r["branch_id"],
                        "pressure": r["pressure"],
                        "representative_beliefs": __import__("json").loads(r["representative_beliefs"] or "[]"),
                        "proposed_curiosity": r["proposed_curiosity"],
                        "status": r["status"],
                    }
                    for r in rows
                ]
            })
        except Exception as e:
            error_channel.record(f"drive_proposals read failed: {e}", source="gui.server", exc=e)
            return jsonify({"error": str(e)}), 500

    @app.post("/api/dynamic/drive_proposals/<int:proposal_id>/approve")
    def api_drive_proposal_approve(proposal_id: int):
        writer = state.writers.get("dynamic")
        if writer is None:
            return jsonify({"error": "no dynamic writer"}), 503
        try:
            writer.write(
                "UPDATE drive_proposals SET status = 'approved' WHERE id = ?",
                (proposal_id,),
            )
            # Apply immediately if dynamic state available
            if state.dynamic is not None:
                state.dynamic.drive_detector.apply_approved(
                    state.dynamic,
                    state.writers["beliefs"],
                    state.readers["dynamic"],
                    coherence_gate=state.coherence_gate,
                )
            return jsonify({"ok": True, "id": proposal_id})
        except Exception as e:
            error_channel.record(f"drive approve failed: {e}", source="gui.server", exc=e)
            return jsonify({"error": str(e)}), 500

    @app.post("/api/dynamic/drive_proposals/<int:proposal_id>/reject")
    def api_drive_proposal_reject(proposal_id: int):
        writer = state.writers.get("dynamic")
        if writer is None:
            return jsonify({"error": "no dynamic writer"}), 503
        try:
            writer.write(
                "UPDATE drive_proposals SET status = 'rejected' WHERE id = ?",
                (proposal_id,),
            )
            return jsonify({"ok": True, "id": proposal_id})
        except Exception as e:
            error_channel.record(f"drive reject failed: {e}", source="gui.server", exc=e)
            return jsonify({"error": str(e)}), 500

    # -- problem memory (Phase 9) --------------------------------------------

    @app.get("/api/problems")
    def api_problems_list():
        if state.problem_memory is None:
            return jsonify({"problems": []})
        try:
            return jsonify({"problems": state.problem_memory.list_open()})
        except Exception as e:
            error_channel.record(f"problems list failed: {e}", source="gui.server", exc=e)
            return jsonify({"error": str(e)}), 500

    @app.post("/api/problems")
    def api_problems_open():
        if state.problem_memory is None:
            return jsonify({"error": "problem memory not initialised"}), 503
        payload = request.get_json(silent=True) or {}
        title = (payload.get("title") or "").strip()
        description = (payload.get("description") or "").strip()
        if not title:
            return jsonify({"error": "title required"}), 400
        try:
            pid = state.problem_memory.open(title, description)
            return jsonify({"id": pid, "title": title})
        except Exception as e:
            error_channel.record(f"problem open failed: {e}", source="gui.server", exc=e)
            return jsonify({"error": str(e)}), 500

    @app.get("/api/problems/<int:problem_id>")
    def api_problems_get(problem_id: int):
        if state.problem_memory is None:
            return jsonify({"error": "problem memory not initialised"}), 503
        try:
            p = state.problem_memory.resume(problem_id)
            if p is None:
                return jsonify({"error": "not found"}), 404
            return jsonify(p)
        except Exception as e:
            error_channel.record(f"problem get failed: {e}", source="gui.server", exc=e)
            return jsonify({"error": str(e)}), 500

    @app.post("/api/problems/<int:problem_id>/observe")
    def api_problems_observe(problem_id: int):
        if state.problem_memory is None:
            return jsonify({"error": "problem memory not initialised"}), 503
        payload = request.get_json(silent=True) or {}
        observation = (payload.get("observation") or "").strip()
        if not observation:
            return jsonify({"error": "observation required"}), 400
        try:
            state.problem_memory.observe(problem_id, observation)
            return jsonify({"ok": True, "id": problem_id})
        except Exception as e:
            error_channel.record(f"problem observe failed: {e}", source="gui.server", exc=e)
            return jsonify({"error": str(e)}), 500

    @app.post("/api/problems/<int:problem_id>/plan")
    def api_problems_plan(problem_id: int):
        if state.problem_memory is None:
            return jsonify({"error": "problem memory not initialised"}), 503
        payload = request.get_json(silent=True) or {}
        plan = (payload.get("plan") or "").strip()
        if not plan:
            return jsonify({"error": "plan required"}), 400
        try:
            state.problem_memory.update_plan(problem_id, plan)
            return jsonify({"ok": True, "id": problem_id})
        except Exception as e:
            error_channel.record(f"problem plan failed: {e}", source="gui.server", exc=e)
            return jsonify({"error": str(e)}), 500

    @app.post("/api/problems/<int:problem_id>/close")
    def api_problems_close(problem_id: int):
        if state.problem_memory is None:
            return jsonify({"error": "problem memory not initialised"}), 503
        try:
            state.problem_memory.close(problem_id)
            return jsonify({"ok": True, "id": problem_id})
        except Exception as e:
            error_channel.record(f"problem close failed: {e}", source="gui.server", exc=e)
            return jsonify({"error": str(e)}), 500

    # -- review queue (Phase 25b CN) -----------------------------------------

    @app.get("/api/review")
    def api_review_list():
        reader = state.readers.get("conversations")
        if reader is None:
            return jsonify({"items": []})
        try:
            rows = reader.read(
                "SELECT id, title, description, created_at, flagged_at, tags "
                "FROM review_queue ORDER BY flagged_at DESC"
            )
            return jsonify({"items": [dict(r) for r in rows]})
        except Exception as e:
            error_channel.record(f"review list failed: {e}", source="gui.server", exc=e)
            return jsonify({"error": str(e)}), 500

    @app.get("/api/review/<int:item_id>")
    def api_review_get(item_id: int):
        reader = state.readers.get("conversations")
        if reader is None:
            return jsonify({"error": "conversations db not available"}), 503
        try:
            rows = reader.read(
                "SELECT id, title, description, created_at, flagged_at, tags "
                "FROM review_queue WHERE id = ?",
                (item_id,),
            )
            if not rows:
                return jsonify({"error": "not found"}), 404
            return jsonify(dict(rows[0]))
        except Exception as e:
            error_channel.record(f"review get failed: {e}", source="gui.server", exc=e)
            return jsonify({"error": str(e)}), 500

    @app.post("/api/review/<int:item_id>/unflag")
    def api_review_unflag(item_id: int):
        writer = state.writers.get("conversations")
        reader = state.readers.get("conversations")
        if writer is None or reader is None:
            return jsonify({"error": "conversations db not available"}), 503
        try:
            rows = reader.read(
                "SELECT id, title, description, created_at, tags "
                "FROM review_queue WHERE id = ?",
                (item_id,),
            )
            if not rows:
                return jsonify({"error": "not found"}), 404
            row = dict(rows[0])
            now = time.time()
            # Re-insert into open_problems with original id preserved
            writer.write(
                "INSERT OR IGNORE INTO open_problems "
                "(id, title, description, state, created_at, last_touched_at, tags) "
                "VALUES (?, ?, ?, 'open', ?, ?, ?)",
                (row["id"], row["title"], row.get("description", ""),
                 row["created_at"], now, row.get("tags", "[]")),
            )
            writer.write(
                "DELETE FROM review_queue WHERE id = ?", (item_id,)
            )
            return jsonify({"ok": True, "id": item_id})
        except Exception as e:
            error_channel.record(f"review unflag failed: {e}", source="gui.server", exc=e)
            return jsonify({"error": str(e)}), 500

    # -- goal manager (Phase 15) ---------------------------------------------

    @app.get("/api/goals")
    def api_goals_list():
        if state.goal_manager is None:
            return jsonify({"goals": []})
        try:
            return jsonify({"goals": state.goal_manager.list_open()})
        except Exception as e:
            error_channel.record(f"goals list failed: {e}", source="gui.server", exc=e)
            return jsonify({"error": str(e)}), 500

    @app.post("/api/goals")
    def api_goals_open():
        if state.goal_manager is None:
            return jsonify({"error": "goal manager not initialised"}), 503
        payload = request.get_json(silent=True) or {}
        title = (payload.get("title") or "").strip()
        description = (payload.get("description") or "").strip()
        priority = float(payload.get("priority", 0.5))
        source = (payload.get("source") or "user").strip()
        problem_id = payload.get("problem_id")
        if not title:
            return jsonify({"error": "title required"}), 400
        try:
            gid = state.goal_manager.open(title, description, priority, source, problem_id)
            return jsonify({"id": gid, "title": title})
        except Exception as e:
            error_channel.record(f"goal open failed: {e}", source="gui.server", exc=e)
            return jsonify({"error": str(e)}), 500

    @app.get("/api/goals/<int:goal_id>")
    def api_goals_get(goal_id: int):
        if state.goal_manager is None:
            return jsonify({"error": "goal manager not initialised"}), 503
        try:
            g = state.goal_manager.resume(goal_id)
            if g is None:
                return jsonify({"error": "not found"}), 404
            return jsonify(g)
        except Exception as e:
            error_channel.record(f"goal get failed: {e}", source="gui.server", exc=e)
            return jsonify({"error": str(e)}), 500

    @app.patch("/api/goals/<int:goal_id>/priority")
    def api_goals_priority(goal_id: int):
        if state.goal_manager is None:
            return jsonify({"error": "goal manager not initialised"}), 503
        payload = request.get_json(silent=True) or {}
        try:
            priority = float(payload.get("priority", 0.5))
        except (TypeError, ValueError):
            return jsonify({"error": "priority must be a float"}), 400
        try:
            state.goal_manager.update_priority(goal_id, priority)
            return jsonify({"ok": True, "id": goal_id})
        except Exception as e:
            error_channel.record(f"goal priority update failed: {e}", source="gui.server", exc=e)
            return jsonify({"error": str(e)}), 500

    @app.post("/api/goals/<int:goal_id>/complete")
    def api_goals_complete(goal_id: int):
        if state.goal_manager is None:
            return jsonify({"error": "goal manager not initialised"}), 503
        try:
            state.goal_manager.complete(goal_id)
            return jsonify({"ok": True, "id": goal_id})
        except Exception as e:
            error_channel.record(f"goal complete failed: {e}", source="gui.server", exc=e)
            return jsonify({"error": str(e)}), 500

    @app.post("/api/goals/<int:goal_id>/cancel")
    def api_goals_cancel(goal_id: int):
        if state.goal_manager is None:
            return jsonify({"error": "goal manager not initialised"}), 503
        try:
            state.goal_manager.cancel(goal_id)
            return jsonify({"ok": True, "id": goal_id})
        except Exception as e:
            error_channel.record(f"goal cancel failed: {e}", source="gui.server", exc=e)
            return jsonify({"error": str(e)}), 500

    # -- tools (Phase 9) -----------------------------------------------------

    @app.get("/api/tools/available")
    def api_tools_available():
        if state.tool_registry is None:
            return jsonify({"tools": []})
        return jsonify({"tools": state.tool_registry.available()})

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

    @app.get("/api/voice/current")
    def api_voice_current():
        if state.voice_state is None:
            return jsonify({"error": "voice_state not initialised"}), 503
        v = state.voice_state.current()
        return jsonify({"id": v.id, "display_name": v.display_name,
                        "accent": v.accent, "gender": v.gender})

    @app.get("/api/voice/list")
    def api_voice_list():
        from speech.voices import enumerate_voices
        voices = enumerate_voices()
        current_id = state.voice_state.current_name() if state.voice_state else ""
        return jsonify({
            "voices": [
                {"id": v.id, "display_name": v.display_name,
                 "accent": v.accent, "gender": v.gender}
                for v in voices
            ],
            "current": current_id,
        })

    @app.post("/api/voice/set")
    def api_voice_set():
        if state.voice_state is None:
            return jsonify({"error": "voice_state not initialised"}), 503
        data = request.get_json(silent=True) or {}
        voice_id = data.get("id", "")
        if not voice_id:
            return jsonify({"error": "missing id"}), 400
        changed = state.voice_state.set_voice(voice_id)
        if not changed and state.voice_state.current_name() != voice_id:
            return jsonify({"error": f"unknown voice {voice_id!r}"}), 400
        return jsonify({"changed": changed, "current": state.voice_state.current_name()})

    @app.get("/api/mode/current")
    def api_mode_current():
        if state.mode_state is None:
            return jsonify({"error": "mode_state not initialised"}), 503
        m = state.mode_state.current()
        return jsonify({"name": state.mode_state.current_name(), "display_name": m.display_name,
                        "description": m.description})

    @app.get("/api/mode/list")
    def api_mode_list():
        from theory_x.modes import DISPLAY_ORDER, MODES
        return jsonify({"modes": [
            {"name": n, "display_name": MODES[n].display_name, "description": MODES[n].description}
            for n in DISPLAY_ORDER
        ]})

    @app.post("/api/mode/set")
    def api_mode_set():
        if state.mode_state is None:
            return jsonify({"error": "mode_state not initialised"}), 503
        data = request.get_json(silent=True) or {}
        name = data.get("name", "")
        if not state.mode_state.set_mode(name):
            return jsonify({"error": f"unknown mode {name!r}"}), 400
        m = state.mode_state.current()
        return jsonify({"name": state.mode_state.current_name(), "display_name": m.display_name})

    @app.get("/api/signals/recent")
    def api_signals_recent():
        limit = min(int(request.args.get("limit", 20)), 100)
        try:
            signals = state.readers["beliefs"].read(
                "SELECT id, detected_at, detector_name, signal_type, "
                "       payload, branches, entities, confidence "
                "FROM signals ORDER BY detected_at DESC LIMIT ?",
                (limit,),
            )
            patterns = state.readers["beliefs"].read(
                "SELECT id, matched_at, template_name, signal_ids, "
                "       predicted_window_seconds, prediction, "
                "       template_confidence, validated_at, outcome_score "
                "FROM patterns ORDER BY matched_at DESC LIMIT ?",
                (limit,),
            )
            return jsonify({
                "signals": [dict(s) for s in signals],
                "patterns": [dict(p) for p in patterns],
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.get("/api/arcs/recent")
    def api_arcs_recent():
        try:
            arcs = state.readers["beliefs"].read(
                """SELECT id, arc_type, detected_at, theme_summary,
                          member_count, quality_grade, closed_by_belief_id,
                          last_active_at
                   FROM arcs
                   WHERE last_active_at > ?
                   ORDER BY quality_grade DESC LIMIT 20""",
                (time.time() - 86400,),
            )
            return jsonify({"arcs": [dict(a) for a in arcs]})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.get("/api/diversity/overview")
    def api_diversity_overview():
        try:
            from theory_x.diversity.panel import overview
            return jsonify(overview(state.readers["beliefs"]))
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.get("/api/harmonic/overview")
    def api_harmonic_overview():
        try:
            from theory_x.harmonic.panel import overview
            return jsonify(overview(
                state.readers["conversations"],
                state.readers["dynamic"],
                state.readers["beliefs"],
            ))
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.get("/api/genius/recent")
    def api_genius_recent():
        """Recent genius_tags joined with fountain_events (GENIUS_SCORE_v2 §7d).

        Query params:
          limit          — int, default 20, max 200
          only_striking  — '1' to filter to STRIKING class only
        """
        try:
            from theory_x.genius.panel import overview as _genius_overview
            from flask import request as _req
            try:
                limit = max(1, min(200, int(_req.args.get("limit", "20"))))
            except (ValueError, TypeError):
                limit = 20
            only_striking = _req.args.get("only_striking") == "1"
            return jsonify(_genius_overview(
                state.readers["conversations"],
                state.readers["dynamic"],
                limit=limit,
                only_striking=only_striking,
            ))
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # -- probes (Lens Theory archaeology) ------------------------------------

    @app.post("/api/probes/run")
    def api_probes_run():
        if state.probe_runner is None:
            return jsonify({"error": "probe runner not initialised"}), 503
        data = request.get_json(silent=True) or {}
        category = (data.get("category") or "").strip()
        probe_text = (data.get("probe_text") or "").strip()
        if not category or not probe_text:
            return jsonify({"error": "category and probe_text are required"}), 400
        try:
            result = state.probe_runner.run_probe(
                category=category,
                probe_text=probe_text,
                notes=data.get("notes"),
            )
            return jsonify(result)
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.get("/api/probes/list")
    def api_probes_list():
        if state.probes_reader is None:
            return jsonify({"probes": []})
        try:
            rows = state.probes_reader.read(
                "SELECT id, category, probe_text, response_text, "
                "response_mode, asked_at FROM probes "
                "ORDER BY asked_at DESC LIMIT 50",
            )
            return jsonify({"probes": [dict(r) for r in rows]})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.get("/api/probes/library")
    def api_probes_library():
        from theory_x.probes.library import ALL_PROBES
        return jsonify(ALL_PROBES)

    @app.post("/api/probes/<int:probe_id>/tag")
    def api_probes_tag(probe_id: int):
        if state.probe_runner is None:
            return jsonify({"error": "probe runner not initialised"}), 503
        data = request.get_json(silent=True) or {}
        tag = (data.get("tag") or "").strip()
        if not tag:
            return jsonify({"error": "tag required"}), 400
        state.probe_runner.add_tag(probe_id, tag)
        return jsonify({"ok": True})

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
