#!/home/rr/Desktop/nex5/.venv/bin/python3
"""NEX 5.0 — unified boot.

Starts the full stack in order:
  1. init_db (all 5 DBs, WAL mode, schema, keystone seeds, migrations)
  2. self-location commitment (Tier 1 locked belief)
  3. sense scheduler (external feeds PAUSED — flip GUI switch to start)
  4. dynamic formation (A-F pipeline, bonsai, crystallization)
  5. world model (belief retrieval, promotion, harmonizer)
  6. membrane (inside/outside classifier, self-model, router)
  7. fountain ignition (spontaneous thought loop)
  8. GUI server (Flask cockpit on port 8765)

All subsystems are wired into AppState before the GUI starts.
"""
from __future__ import annotations

import atexit
import logging
import os

import errors as error_channel
from alpha import ALPHA
from substrate import Reader, Writer, db_paths
from substrate.init_db import init_all

from theory_x.stage5_self_location.commitment import SelfLocationCommitment
from theory_x.stage1_sense import build_scheduler
from theory_x.stage2_dynamic import build_dynamic
from theory_x.stage3_world_model import build_world_model
from theory_x.stage4_membrane import build_membrane
from theory_x.stage6_fountain import build_fountain
from theory_x.auto_probe.groove_breaker import GrooveBreaker
from theory_x.stage6_fountain.readiness import FOUNTAIN_CHECK_INTERVAL_SECONDS
from theory_x.modes import build_mode_state
from speech.voices import build_voice_state
from gui.server import AppState, create_app
from voice.llm import VoiceClient


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    error_channel.install_handler()
    log = logging.getLogger("nex5.boot")

    log.info("NEX 5.0 booting")
    log.info("Alpha: %s", ALPHA.lines[0])

    # 1. Init databases
    log.info("Initialising databases...")
    init_all()

    # 2. Build writers/readers
    paths = db_paths()
    writers = {name: Writer(p, name=name) for name, p in paths.items()}
    readers = {name: Reader(p) for name, p in paths.items()}

    # 3. Self-location commitment
    log.info("Committing self-location...")
    commitment = SelfLocationCommitment()
    belief_id = commitment.commit(writers["beliefs"], readers["beliefs"])
    log.info("Self-location committed (belief id=%d)", belief_id)

    # 4. Pre-load Kokoro on main thread BEFORE any worker threads spawn.
    #    Loading inside a background thread races against other torch-importing
    #    threads and causes Python's _ModuleLock to deadlock every boot.
    from speech.config import SpeechConfig as _SpeechCfg
    from speech.kokoro_backend import KokoroBackend as _KokoroBackend
    _speech_cfg_pre = _SpeechCfg.from_env()
    _kokoro_backend: "_KokoroBackend | None" = None
    if _speech_cfg_pre.enabled:
        log.info("Pre-loading Kokoro on main thread...")
        try:
            _kokoro_backend = _KokoroBackend(
                voice=_speech_cfg_pre.voice,
                speed=_speech_cfg_pre.speed,
            )
            _kokoro_backend.load()
            log.info("Kokoro pre-loaded successfully")
        except Exception as _ke:
            log.error("Kokoro pre-load failed (speech will be disabled): %s", _ke)
            _kokoro_backend = None
    else:
        log.info("Speech disabled — skipping Kokoro pre-load")

    # 5. Mode state (must be before scheduler + fountain)
    log.info("Initialising mode state...")
    mode_state = build_mode_state(writers, readers)
    log.info("Mode state ready — current mode: %s", mode_state.current_name())

    voice_state = build_voice_state(writers, readers)
    log.info("Voice state ready — current voice: %s", voice_state.current_name())

    # 5. Sense scheduler (external feeds PAUSED)
    log.info("Starting sense scheduler (external feeds paused)...")
    scheduler = build_scheduler(writers, readers, mode_state=mode_state)
    log.info("Sense scheduler started — 23 adapters wired")

    # 5. Dynamic formation
    log.info("Starting dynamic formation...")
    dynamic = build_dynamic(writers, readers)
    log.info("Dynamic started — bonsai tree active")

    # 6. Voice client (shared by world model, fountain, strikes)
    voice = VoiceClient(
        url=os.environ.get("NEX5_VOICE_URL", "http://localhost:11434/v1/chat/completions"),
        model=os.environ.get("NEX5_VOICE_MODEL", "qwen2.5:3b"),
    )

    # Voice health check
    if voice.health_check():
        log.info("Voice endpoint reachable: %s", voice.url)
    else:
        log.warning("Voice endpoint NOT reachable at %s — chat will return fallback message", voice.url)

    # 7. World model
    log.info("Starting world model...")
    world_model = build_world_model(writers, readers, dynamic_state=dynamic, voice_client=voice)
    log.info("World model started")

    # 8. Membrane
    log.info("Drawing membrane...")
    membrane = build_membrane(
        writers, readers,
        dynamic_state=dynamic,
        world_model_state=world_model,
    )
    log.info("Membrane drawn — inside/outside boundary active")

    # 9. Problem memory (needed by fountain for task-bearing override)
    from theory_x.stage7_sustained.problem_memory import ProblemMemory
    problem_memory = ProblemMemory(writers["conversations"], readers["conversations"])

    # 10. Fountain ignition
    log.info("Igniting fountain...")
    log.info(
        "Speech governor: min_gap=%ss, base_prob=%.2f",
        os.environ.get("NEX5_SPEECH_MIN_GAP", "180"),
        float(os.environ.get("NEX5_SPEECH_PROB", "1.0")),
    )
    # Phase A: groove observer (Design v0.3)
    groove_breaker = GrooveBreaker(
        beliefs_db_path=str(paths["beliefs"]),
        dynamic_db_path=str(paths["dynamic"]),
    )
    fountain = build_fountain(writers, readers, voice, dynamic_state=dynamic,
                              problem_memory=problem_memory, mode_state=mode_state,
                              groove_breaker=groove_breaker)
    log.info("Fountain lit — loop running at %ds interval", FOUNTAIN_CHECK_INTERVAL_SECONDS)

    # 11. Strike protocols
    log.info("Arming strike protocols...")
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
        sense_reader=readers["sense"],
    )
    log.info("Strike protocols armed — 5 strikes available")

    # 12. Tool use
    log.info("Wiring tool use...")
    from theory_x.stage_capability.tools import ToolRegistry
    from theory_x.stage_capability.tool_caller import ToolCaller
    tool_registry = ToolRegistry(beliefs_reader=readers["beliefs"])
    tool_caller = ToolCaller(tool_registry)
    log.info("Problem memory + tools ready (Stage B)")

    # 12. Speech consumer
    speech_consumer = None
    try:
        from speech.queue_consumer import SpeechQueueConsumer
        from speech.config import SpeechConfig
        speech_cfg = SpeechConfig.from_env()
        if speech_cfg.enabled:
            speech_consumer = SpeechQueueConsumer(
                writer=writers["beliefs"],
                reader=readers["beliefs"],
                config=speech_cfg,
                voice_state=voice_state,
                backend=_kokoro_backend,
            )
            speech_consumer.start()
            log.info("Speech consumer started (voice=%s)", speech_cfg.voice)
        else:
            log.info("Speech disabled via NEX5_SPEECH_ENABLED=false")
    except Exception as e:
        import traceback
        log.error("Speech consumer failed to start: %s\n%s",
                  e, traceback.format_exc())

    # 13. Signal detection layer (LLM-free)
    log.info("Starting signal detection loop...")
    from theory_x.signals import build_signal_loop
    signal_loop = build_signal_loop(writers, readers)
    log.info("Signal loop ready — detectors running every 60s")

    # 14. Diversity ecology (LLM-free, sentence-transformers)
    log.info("Starting diversity ecology loop...")
    from theory_x.diversity import build_diversity_loop
    diversity_loop = build_diversity_loop(writers, readers)
    diversity_loop.start()
    log.info("Diversity loop ready")

    # 15. Arc reader (LLM-free, retrospective arc detection)
    log.info("Starting arc reader loop...")
    from theory_x.arcs.loop import build_arc_loop
    arc_loop = build_arc_loop(writers, readers)
    arc_loop.start()
    log.info("Arc loop ready — scanning every 5 min")

    # 16. Belief edge generator (Tropic Gradient Phase 1)
    log.info("Starting edge generator loop...")
    from theory_x.stage3_world_model.edge_generator import build_edge_generator_loop
    edge_generator_loop = build_edge_generator_loop(writers, readers)
    edge_generator_loop.start()
    log.info("EdgeGeneratorLoop started (tick=30min)")

    # 17. Probe archaeology (Lens Theory)
    probe_runner = None
    probes_reader = readers.get("probes")
    try:
        from theory_x.probes.probe_runner import ProbeRunner
        probe_runner = ProbeRunner(
            probes_writer=writers["probes"],
            beliefs_reader=readers["beliefs"],
            dynamic_reader=readers["dynamic"],
            sense_reader=readers["sense"],
        )
        log.info("Probe runner ready — Lens Theory archaeology online")
    except Exception as _probe_err:
        log.warning("Probe runner failed to start (non-fatal): %s", _probe_err)

    # 18. Wire AppState and start GUI
    state = AppState(
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
        tool_registry=tool_registry,
        tool_caller=tool_caller,
        speech_consumer=speech_consumer,
        mode_state=mode_state,
        voice_state=voice_state,
        signal_loop=signal_loop,
        diversity_loop=diversity_loop,
        arc_loop=arc_loop,
        probe_runner=probe_runner,
        probes_reader=probes_reader,
    )
    atexit.register(state.close)

    app = create_app(state)

    host = os.environ.get("NEX5_HOST", "127.0.0.1")
    port = int(os.environ.get("NEX5_PORT", "8765"))
    log.info("NEX 5.0 ready — GUI at http://%s:%d", host, port)
    log.info("External feeds PAUSED — flip the GUI switch to start")

    app.run(host=host, port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
