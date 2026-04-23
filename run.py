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
from theory_x.stage6_fountain.readiness import FOUNTAIN_CHECK_INTERVAL_SECONDS
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

    # 4. Sense scheduler (external feeds PAUSED)
    log.info("Starting sense scheduler (external feeds paused)...")
    scheduler = build_scheduler(writers, readers)
    log.info("Sense scheduler started — 23 adapters wired")

    # 5. Dynamic formation
    log.info("Starting dynamic formation...")
    dynamic = build_dynamic(writers, readers)
    log.info("Dynamic started — bonsai tree active")

    # 6. World model
    log.info("Starting world model...")
    world_model = build_world_model(writers, readers, dynamic_state=dynamic)
    log.info("World model started")

    # 7. Membrane
    log.info("Drawing membrane...")
    membrane = build_membrane(
        writers, readers,
        dynamic_state=dynamic,
        world_model_state=world_model,
    )
    log.info("Membrane drawn — inside/outside boundary active")

    # 8. Fountain ignition
    voice = VoiceClient(
        url=os.environ.get("NEX5_VOICE_URL", "http://localhost:8080/v1/chat/completions"),
        model=os.environ.get("NEX5_VOICE_MODEL", "qwen2.5-3b"),
    )
    log.info("Igniting fountain...")
    fountain = build_fountain(writers, readers, voice, dynamic_state=dynamic)
    log.info("Fountain lit — loop running at %ds interval", FOUNTAIN_CHECK_INTERVAL_SECONDS)

    # 9. Strike protocols
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
    )
    log.info("Strike protocols armed — 5 strikes available")

    # 10. Problem memory + tool use
    log.info("Wiring problem memory and tool use...")
    from theory_x.stage7_sustained.problem_memory import ProblemMemory
    from theory_x.stage_capability.tools import ToolRegistry
    from theory_x.stage_capability.tool_caller import ToolCaller
    problem_memory = ProblemMemory(writers["conversations"], readers["conversations"])
    tool_registry = ToolRegistry(beliefs_reader=readers["beliefs"])
    tool_caller = ToolCaller(tool_registry)
    log.info("Problem memory + tools ready (Stage B)")

    # 11. Speech consumer
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
            )
            speech_consumer.start()
            log.info("Speech consumer started (voice=%s)", speech_cfg.voice)
        else:
            log.info("Speech disabled via NEX5_SPEECH_ENABLED=false")
    except Exception as e:
        log.warning("Speech consumer failed to start: %s", e)

    # 12. Wire AppState and start GUI
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
