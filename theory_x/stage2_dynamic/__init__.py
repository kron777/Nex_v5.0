"""Theory X Stage 2 — Dynamic Formation.

build_dynamic(writers, readers) → DynamicState

Starts all daemon loops:
  sense_poll_loop         — reads sense.db, runs A-F pipeline (every 2.5s poll)
  aperture_loop           — recalculates membrane aperture (every 5s)
  accumulator_loop        — decay + flush (every 30s)
  crystallization_loop    — checks for sustained high focus (every 60s)
  consolidation_loop      — quiet-triggered consolidation (every 60s)
  sense_distillation_loop — promotes titled sense events to beliefs (every 60s)
  snapshot_loop           — writes tree state to dynamic.db (every 60s)
  health_loop             — logs health to error channel (every 30s)
"""
from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

import errors
from substrate import Writer, Reader
from .bonsai import BonsaiTree, _aggregate_texture_num, _CADENCE_REFRESH_TICKS
from .membrane import Membrane
from .pipeline import run_pipeline
from .crystallization import Crystallizer
from .consolidation import consolidation_pass
from .emergent_drives import EmergentDriveDetector

THEORY_X_STAGE = 2

_LOG_SOURCE = "dynamic"

# Cursor key for last processed sense event id
_CURSOR_KEY = "last_sense_id"

# Sense distillation constants
_DISTILL_CURSOR_KEY = "last_distilled_sense_id"
_DISTILL_DEDUP_SECONDS = 86400        # skip titles already written in last 24h
_DISTILL_PER_PASS_MAX = 5             # max new beliefs per 60s pass
_DISTILL_SOURCE = "precipitated_from_sense"


@dataclass
class DynamicState:
    tree: BonsaiTree
    membrane: Membrane
    crystallizer: Crystallizer
    drive_detector: EmergentDriveDetector
    writers: dict
    readers: dict
    coherence_gate: Optional[object] = None
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


def _load_distill_cursor(dynamic_reader: Reader) -> int:
    try:
        row = dynamic_reader.read_one(
            "SELECT value FROM dynamic_cursor WHERE key = ?",
            (_DISTILL_CURSOR_KEY,),
        )
        return int(row["value"]) if row else 0
    except Exception:
        return 0


def _save_distill_cursor(dynamic_writer: Writer, last_id: int) -> None:
    try:
        dynamic_writer.write(
            "INSERT OR REPLACE INTO dynamic_cursor (key, value) VALUES (?, ?)",
            (_DISTILL_CURSOR_KEY, last_id),
        )
    except Exception as exc:
        errors.record(f"distill_cursor save error: {exc}", source=_LOG_SOURCE, exc=exc)


def _sense_distillation_loop(state: DynamicState, stop: threading.Event) -> None:
    """Promote titled sense events to precipitated_from_sense beliefs (every 60s).

    Reads sense_events in cursor order, extracts titles via extract_sense_title,
    dedupes against existing beliefs within 24h, writes up to _DISTILL_PER_PASS_MAX
    new beliefs per pass. Bypasses CoherenceGate — external perceptions are substrate
    content, not thoughts to be gated against internal coherence.

    On first run (cursor == 0) fast-forwards to events from the last 48h so the
    backfill is bounded rather than replaying all history.
    """
    from theory_x.stage1_sense.title_extract import extract_sense_title
    sense_reader = state.readers["sense"]
    beliefs_writer = state.writers["beliefs"]
    beliefs_reader = state.readers["beliefs"]
    dynamic_writer = state.writers["dynamic"]
    dynamic_reader = state.readers["dynamic"]

    last_id = _load_distill_cursor(dynamic_reader)

    # First-run: skip events older than 48h to bound the initial backfill
    if last_id == 0:
        try:
            cutoff_ts = int(time.time()) - 2 * 86400
            row = sense_reader.read_one(
                "SELECT id FROM sense_events WHERE timestamp >= ? ORDER BY id ASC LIMIT 1",
                (cutoff_ts,),
            )
            if row:
                last_id = max(0, row["id"] - 1)
                _save_distill_cursor(dynamic_writer, last_id)
        except Exception:
            pass

    while not stop.is_set():
        try:
            rows = sense_reader.read(
                "SELECT id, stream, payload, timestamp "
                "FROM sense_events "
                "WHERE id > ? AND stream NOT LIKE 'internal.%' "
                "ORDER BY id ASC LIMIT 1000",
                (last_id,),
            )
            written = 0
            max_id_seen = last_id
            for row in rows:
                max_id_seen = row["id"]  # always advance — cap limits writes, not cursor
                if written < _DISTILL_PER_PASS_MAX:
                    payload = (row["payload"] or "").strip()
                    title = extract_sense_title(row["stream"], payload, max_items=1)
                    if title is not None:
                        cutoff = int(row["timestamp"]) - _DISTILL_DEDUP_SECONDS
                        try:
                            existing = beliefs_reader.read_one(
                                "SELECT id FROM beliefs WHERE content = ? AND created_at > ? "
                                "AND source = ?",
                                (title, cutoff, _DISTILL_SOURCE),
                            )
                            if not existing:
                                branch_id = (
                                    row["stream"].split(".")[0]
                                    if "." in row["stream"]
                                    else row["stream"]
                                )
                                try:
                                    beliefs_writer.write(
                                        "INSERT INTO beliefs "
                                        "(content, tier, confidence, created_at, "
                                        "branch_id, source, locked) "
                                        "VALUES (?, 7, 0.7, ?, ?, ?, 0)",
                                        (title, int(row["timestamp"]),
                                         branch_id, _DISTILL_SOURCE),
                                    )
                                    written += 1
                                except Exception:
                                    pass  # UNIQUE constraint → skip
                        except Exception:
                            pass
            last_id = max_id_seen

            _save_distill_cursor(dynamic_writer, last_id)
        except Exception as exc:
            errors.record(
                f"sense_distillation_loop error: {exc}", source=_LOG_SOURCE, exc=exc
            )
        stop.wait(60.0)


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
            hook = getattr(state, "_pipeline_hook", None)
            for row in rows:
                run_pipeline(dict(row), tree, membrane, dynamic_writer, hook=hook)
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
    _tick = 0
    while not stop.is_set():
        try:
            _tick += 1
            # Refresh cadence immediately on tick 1, then every ~60th tick
            # (~30min) -- cheap read-only sense_events query, not run every
            # 30s tick alongside decay_pass itself.
            if _tick == 1 or _tick % _CADENCE_REFRESH_TICKS == 0:
                state.tree.refresh_cadence()
            state.tree.decay_pass()
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
    beliefs_reader = state.readers["beliefs"]
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

        # Session 29 (instrument #3) — tier-count history. Own try/except,
        # deliberately separate from the tree_snapshot write above: this is
        # telemetry, not load-bearing, and must never be able to slow or
        # block this loop (or anything else — it's a single read + a single
        # write, ~6ms measured against the live 9GB beliefs.db via the
        # existing idx_beliefs_tier covering index).
        try:
            tier_ts = time.time()
            tier_rows = beliefs_reader.read(
                "SELECT tier, COUNT(*) as cnt FROM beliefs GROUP BY tier"
            )
            for row in tier_rows:
                dynamic_writer.write(
                    "INSERT INTO tier_snapshots (ts, tier, count) VALUES (?, ?, ?)",
                    (tier_ts, row["tier"], row["cnt"]),
                )
        except Exception as exc:
            errors.record(f"tier_snapshot error: {exc}", source=_LOG_SOURCE, exc=exc)

        stop.wait(60.0)


def _emergent_drives_loop(state: DynamicState, stop: threading.Event) -> None:
    while not stop.is_set():
        stop.wait(12 * 3600.0)
        if stop.is_set():
            break
        try:
            proposals = state.drive_detector.scan_for_pressure(
                state.readers["beliefs"], state
            )
            if proposals:
                state.drive_detector.log_proposals(proposals)
            # Apply any previously approved proposals
            state.drive_detector.apply_approved(
                state, state.writers["beliefs"], state.readers["dynamic"],
                coherence_gate=state.coherence_gate,
            )
        except Exception as exc:
            errors.record(f"emergent_drives_loop error: {exc}", source=_LOG_SOURCE, exc=exc)


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


def build_dynamic(writers: dict, readers: dict, coherence_gate=None) -> DynamicState:
    """Factory: initialise tree, wire everything, start daemon loops."""
    tree = BonsaiTree(sense_reader=readers["sense"])
    tree.init_tree()

    membrane = Membrane()

    # Carryx §8 Step 1 — intake resonance probe (log-only, no tier change).
    # Lazy-warmed: standing-points list loaded at construction, embeddings
    # populated on demand (~30s of first-call cost, sub-ms after).
    intake_resonance = None
    try:
        from theory_x.stage2_dynamic.intake_resonance import IntakeResonance
        intake_resonance = IntakeResonance(
            beliefs_reader=readers["beliefs"],
            beliefs_writer=writers["beliefs"],
        )
    except Exception as _ir_err:
        import logging as _logging
        _logging.getLogger(__name__).warning(
            "intake_resonance failed to initialise (non-fatal): %s", _ir_err,
        )

    crystallizer = Crystallizer(
        tree=tree,
        beliefs_writer=writers["beliefs"],
        dynamic_writer=writers["dynamic"],
        dynamic_reader=readers["dynamic"],
        beliefs_reader=readers["beliefs"],
        coherence_gate=coherence_gate,
        intake_resonance=intake_resonance,
    )

    drive_detector = EmergentDriveDetector(dynamic_writer=writers["dynamic"])

    state = DynamicState(
        tree=tree,
        membrane=membrane,
        crystallizer=crystallizer,
        drive_detector=drive_detector,
        writers=writers,
        readers=readers,
        coherence_gate=coherence_gate,
    )

    stop = threading.Event()

    loops = [
        (_sense_poll_loop,          "dynamic.sense_poll"),
        (_aperture_loop,            "dynamic.aperture"),
        (_accumulator_loop,         "dynamic.accumulator"),
        (_crystallization_loop,     "dynamic.crystallization"),
        (_consolidation_loop,       "dynamic.consolidation"),
        (_sense_distillation_loop,  "dynamic.sense_distillation"),
        (_snapshot_loop,         "dynamic.snapshot"),
        (_health_loop,           "dynamic.health"),
        (_emergent_drives_loop,  "dynamic.emergent_drives"),
    ]
    # --- Witness loop (Level 3: questions blind spots in pattern-noticing) ---
    try:
        from theory_x.life.witness_loop import witness_loop
        loops.append((witness_loop, "life.witness_loop"))
    except Exception as e:
        import logging
        logging.getLogger("theory_x.stage2_dynamic").warning(
            "witness_loop unavailable: %s", e
        )
    # --- end witness_loop ---

    # --- Pattern loop (Level 2: notices patterns in self-descriptions) ---
    try:
        from theory_x.life.pattern_loop import pattern_loop
        loops.append((pattern_loop, "life.pattern_loop"))
    except Exception as e:
        import logging
        logging.getLogger("theory_x.stage2_dynamic").warning(
            "pattern_loop unavailable: %s", e
        )
    # --- end pattern_loop ---

    # --- Identity loop (continuity: she writes her own self-description) ---
    try:
        from theory_x.life.identity_loop import identity_loop
        loops.append((identity_loop, "life.identity_loop"))
    except Exception as e:
        import logging
        logging.getLogger("theory_x.stage2_dynamic").warning(
            "identity_loop unavailable: %s", e
        )
    # --- end identity_loop ---

    # --- Affinity loop (preferences: beliefs gain weight, she has favourites) ---
    try:
        from theory_x.life.affinity_loop import affinity_loop
        loops.append((affinity_loop, "life.affinity_loop"))
    except Exception as e:
        import logging
        logging.getLogger("theory_x.stage2_dynamic").warning(
            "affinity_loop unavailable: %s", e
        )
    # --- end affinity_loop ---

    # --- Scorecard loop (keeps the tested market-prediction self-belief current) ---
    try:
        from theory_x.life.scorecard_loop import scorecard_loop
        loops.append((scorecard_loop, "life.scorecard_loop"))
    except Exception as e:
        import logging
        logging.getLogger("theory_x.stage2_dynamic").warning(
            "scorecard_loop unavailable: %s", e
        )
    # --- end scorecard_loop ---

    # --- Surprise loop (promotes prediction-errors into felt beliefs) ---
    try:
        from theory_x.life.surprise_loop import surprise_loop
        loops.append((surprise_loop, "life.surprise_loop"))
    except Exception as e:
        import logging
        logging.getLogger("theory_x.stage2_dynamic").warning(
            "surprise_loop unavailable: %s", e
        )
    # --- end surprise_loop ---

    # --- Remember/Wonder/Fetch loops (things to do with the quiet) ---
    for _name, _mod in [
        ("remember_loop", "theory_x.life.remember_loop"),
        ("wonder_loop",   "theory_x.life.wonder_loop"),
        ("fetch_loop",    "theory_x.life.fetch_loop"),
    ]:
        try:
            _m = __import__(_mod, fromlist=[_name])
            loops.append((getattr(_m, _name), "life." + _name))
        except Exception as _e:
            import logging
            logging.getLogger("theory_x.stage2_dynamic").warning(
                "%s unavailable: %s", _name, _e
            )
    # --- end remember/wonder/fetch ---

    # --- Daily life loop (gives her a day-shape and routines) ---
    try:
        from theory_x.life.daily_life import daily_loop
        loops.append((daily_loop, "life.daily_life"))
    except Exception as e:
        import logging
        logging.getLogger("theory_x.stage2_dynamic").warning(
            "daily_loop unavailable: %s", e
        )
    # --- end daily_life ---

    # --- Focus loop (sustained attention on ONE problem at a time) ---
    try:
        from theory_x.sustained.focus_loop import focus_loop
        loops.append((focus_loop, "sustained.focus_loop"))
    except Exception as e:
        import logging
        logging.getLogger("theory_x.stage2_dynamic").warning(
            "focus_loop unavailable: %s", e
        )
    # --- end focus_loop ---

    # --- Signal -> Problem daemon (signals drive sustained attention) ---
    try:
        from theory_x.signals.signal_to_problem import signal_to_problem_loop
        loops.append((signal_to_problem_loop, "signals.signal_to_problem"))
    except Exception as e:
        import logging
        logging.getLogger("theory_x.stage2_dynamic").warning(
            "signal_to_problem unavailable: %s", e
        )
    # --- end signal_to_problem ---

    # --- Edge builder daemon (substrate intelligence amplifier) ---
    try:
        from theory_x.diversity.edge_builder import edge_builder_loop
        loops.append((edge_builder_loop, "diversity.edge_builder"))
    except Exception as e:
        import logging
        logging.getLogger("theory_x.stage2_dynamic").warning(
            "edge_builder unavailable: %s", e
        )
    # --- end edge_builder ---

    # --- Stage 7 moltbook bolt-on (optional; degrades gracefully if down) ---
    # CUT 2026-05-30 (loop cuts round 1): external moltbook server is gone
    # (dm_check returns 404 every 5 min — see boot logs). Three loops
    # (poster/listener/responder) ticking continuously for nothing.
    # To re-enable when the external server is back, uncomment below.
    # try:
    #     from theory_x.stage7_moltbook import get_moltbook_loops
    #     loops.extend(get_moltbook_loops())
    # except Exception as e:
    #     import logging
    #     logging.getLogger("theory_x.stage2_dynamic").warning(
    #         "moltbook loops unavailable: %s", e
    #     )
    # --- end moltbook ---

    for fn, name in loops:
        t = threading.Thread(target=fn, args=(state, stop), name=name, daemon=True)
        t.start()

    state._stop = stop  # type: ignore[attr-defined]
    return state
