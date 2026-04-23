#!/usr/bin/env python3
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
    log.info("Sense scheduler started — %d adapters wired", len(scheduler._adapters))

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

    # 9. Wire AppState and start GUI
    state = AppState(
        writers=writers,
        readers=readers,
        voice=voice,
        scheduler=scheduler,
        dynamic=dynamic,
        world_model=world_model,
        membrane=membrane,
        fountain=fountain,
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
