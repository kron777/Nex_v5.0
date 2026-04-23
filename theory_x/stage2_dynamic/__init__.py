"""Theory X Stage 2 — Dynamic Formation.

build_dynamic(writers, readers) → DynamicState

Starts all daemon loops:
  sense_poll_loop       — reads sense.db, runs A-F pipeline (every 2.5s poll)
  aperture_loop         — recalculates membrane aperture (every 5s)
  accumulator_loop      — decay + flush (every 30s)
  crystallization_loop  — checks for sustained high focus (every 60s)
  consolidation_loop    — quiet-triggered consolidation (every 60s)
  snapshot_loop         — writes tree state to dynamic.db (every 60s)
  health_loop           — logs health to error channel (every 30s)
"""
from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

import errors
from substrate import Writer, Reader
from .bonsai import BonsaiTree, _aggregate_texture_num
from .membrane import Membrane
from .pipeline import run_pipeline
from .crystallization import Crystallizer
from .consolidation import consolidation_pass

THEORY_X_STAGE = 2

_LOG_SOURCE = "dynamic"

# Cursor key for last processed sense event id
_CURSOR_KEY = "last_sense_id"


@dataclass
class DynamicState:
    tree: BonsaiTree
    membrane: Membrane
    crystallizer: Crystallizer
    writers: dict
    readers: dict
    _pipeline_runs: int = field(default=0, init=False)
    _consolidation_active: bool = field(default=False, init=False)
    _started_at: float = field(default_factory=time.time, init=False)

    def status(self) -> dict:
        snap = self.tree.snapshot()
        return {
            "branches": snap["branches"],
            "total_branches": snap["total_branches"],
            "active_branch_count": snap["active_branch_count"],
            "aggregate_focus": snap["aggregate_focus"],
            "aggregate_texture": snap["aggregate_texture"],
            "aperture": self.membrane.aperture,
            "consolidation_active": self._consolidation_active,
            "pipeline_runs": self._pipeline_runs,
            "uptime_seconds": int(time.time() - self._started_at),
        }


def _load_cursor(dynamic_reader: Reader) -> int:
    try:
        row = dynamic_reader.read_one(
            "SELECT value FROM dynamic_cursor WHERE key = ?",
            (_CURSOR_KEY,),
        )
        return int(row["value"]) if row else 0
    except Exception as exc:
        errors.record(f"cursor load error: {exc}", source=_LOG_SOURCE, exc=exc)
        return 0


def _save_cursor(dynamic_writer: Writer, last_id: int) -> None:
    try:
        dynamic_writer.write(
            "INSERT OR REPLACE INTO dynamic_cursor (key, value) VALUES (?, ?)",
            (_CURSOR_KEY, last_id),
        )
    except Exception as exc:
        errors.record(f"cursor save error: {exc}", source=_LOG_SOURCE, exc=exc)


def _sense_poll_loop(state: DynamicState, stop: threading.Event) -> None:
    sense_reader = state.readers["sense"]
    dynamic_writer = state.writers["dynamic"]
    dynamic_reader = state.readers["dynamic"]
    tree = state.tree
    membrane = state.membrane

    last_id = _load_cursor(dynamic_reader)
    reads_since_save = 0

    while not stop.is_set():
        try:
            rows = sense_reader.read(
                "SELECT id, stream, payload, provenance, timestamp "
                "FROM sense_events WHERE id > ? ORDER BY id ASC LIMIT 100",
                (last_id,),
            )
            for row in rows:
                run_pipeline(dict(row), tree, membrane, dynamic_writer)
                last_id = row["id"]
                state._pipeline_runs += 1
                reads_since_save += 1
                if reads_since_save >= 50:
                    _save_cursor(dynamic_writer, last_id)
                    reads_since_save = 0
        except Exception as exc:
            errors.record(f"sense_poll_loop error: {exc}", source=_LOG_SOURCE, exc=exc)
        stop.wait(2.5)
    # Save cursor on shutdown
    _save_cursor(dynamic_writer, last_id)


def _aperture_loop(state: DynamicState, stop: threading.Event) -> None:
    while not stop.is_set():
        try:
            nodes = state.tree.all_nodes()
            agg_texture = _aggregate_texture_num(nodes)
            state.membrane.recalc_aperture(agg_texture)
        except Exception as exc:
            errors.record(f"aperture_loop error: {exc}", source=_LOG_SOURCE, exc=exc)
        stop.wait(5.0)


def _accumulator_loop(state: DynamicState, stop: threading.Event) -> None:
    while not stop.is_set():
        try:
            state.membrane.decay_accumulator()
            flushed = state.membrane.flush_accumulator()
            if flushed:
                errors.record(
                    f"accumulator flushed {len(flushed)} entries",
                    source=_LOG_SOURCE,
                    level="INFO",
                )
        except Exception as exc:
            errors.record(f"accumulator_loop error: {exc}", source=_LOG_SOURCE, exc=exc)
        stop.wait(30.0)


def _crystallization_loop(state: DynamicState, stop: threading.Event) -> None:
    while not stop.is_set():
        try:
            crystallized = state.crystallizer.check_all()
            if crystallized:
                errors.record(
                    f"crystallized branches: {crystallized}",
                    source=_LOG_SOURCE,
                    level="INFO",
                )
        except Exception as exc:
            errors.record(f"crystallization_loop error: {exc}", source=_LOG_SOURCE, exc=exc)
        stop.wait(60.0)


def _consolidation_loop(state: DynamicState, stop: threading.Event) -> None:
    sense_reader = state.readers["sense"]
    while not stop.is_set():
        try:
            active = consolidation_pass(state.tree, sense_reader)
            state._consolidation_active = active
        except Exception as exc:
            errors.record(f"consolidation_loop error: {exc}", source=_LOG_SOURCE, exc=exc)
        stop.wait(60.0)


def _snapshot_loop(state: DynamicState, stop: threading.Event) -> None:
    dynamic_writer = state.writers["dynamic"]
    while not stop.is_set():
        try:
            snap = state.tree.snapshot()
            dynamic_writer.write(
                "INSERT INTO tree_snapshots "
                "(ts, tree_json, total_branches, active_branch_count, "
                "aggregate_texture, membrane_aperture) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    time.time(),
                    json.dumps(snap["branches"]),
                    snap["total_branches"],
                    snap["active_branch_count"],
                    snap["aggregate_texture"],
                    state.membrane.aperture,
                ),
            )
        except Exception as exc:
            errors.record(f"snapshot_loop error: {exc}", source=_LOG_SOURCE, exc=exc)
        stop.wait(60.0)


def _health_loop(state: DynamicState, stop: threading.Event) -> None:
    while not stop.is_set():
        try:
            status = state.status()
            errors.record(
                f"dynamic health: {status['active_branch_count']} active branches, "
                f"{status['pipeline_runs']} pipeline runs, "
                f"aperture={status['aperture']:.2f}",
                source=_LOG_SOURCE,
                level="INFO",
            )
        except Exception as exc:
            errors.record(f"health_loop error: {exc}", source=_LOG_SOURCE, exc=exc)
        stop.wait(30.0)


def build_dynamic(writers: dict, readers: dict) -> DynamicState:
    """Factory: initialise tree, wire everything, start daemon loops."""
    tree = BonsaiTree()
    tree.init_tree()

    membrane = Membrane()

    crystallizer = Crystallizer(
        tree=tree,
        beliefs_writer=writers["beliefs"],
        dynamic_writer=writers["dynamic"],
        dynamic_reader=readers["dynamic"],
    )

    state = DynamicState(
        tree=tree,
        membrane=membrane,
        crystallizer=crystallizer,
        writers=writers,
        readers=readers,
    )

    stop = threading.Event()

    loops = [
        (_sense_poll_loop,      "dynamic.sense_poll"),
        (_aperture_loop,        "dynamic.aperture"),
        (_accumulator_loop,     "dynamic.accumulator"),
        (_crystallization_loop, "dynamic.crystallization"),
        (_consolidation_loop,   "dynamic.consolidation"),
        (_snapshot_loop,        "dynamic.snapshot"),
        (_health_loop,          "dynamic.health"),
    ]

    for fn, name in loops:
        t = threading.Thread(target=fn, args=(state, stop), name=name, daemon=True)
        t.start()

    state._stop = stop  # type: ignore[attr-defined]
    return state
