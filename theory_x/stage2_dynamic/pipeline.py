"""A-F pipeline — six-step processing of sense events into branch attention.

Step A: Receive sense event
Step B: Match to branches (proximity)
Step C: Compute magnitude per branch
Step D: Apply aperture gate
Step E: Compute valence
Step F: Attend tree + log
"""
from __future__ import annotations

import json
import time
from typing import Any, Optional

import errors
from substrate import Writer, Reader
from .attention import _match_branches, _magnitude_for
from .bonsai import BonsaiTree, BonsaiNode
from .membrane import Membrane

THEORY_X_STAGE = 2

_LOG_SOURCE = "pipeline"


def _log_event(writer: Writer, step: str, sensation_source: str,
               branch_id: Optional[str], magnitude: Optional[float],
               valence: Optional[str], meta: Optional[dict]) -> None:
    writer.write(
        "INSERT INTO pipeline_events "
        "(ts, step, sensation_source, branch_id, magnitude, valence, meta) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            time.time(), step, sensation_source,
            branch_id, magnitude, valence,
            json.dumps(meta) if meta else None,
        ),
    )


def step_A(row: dict) -> tuple[str, Any, str]:
    """Unpack a sense_events row → (stream, value, provenance)."""
    stream = row["stream"]
    payload = row["payload"]
    provenance = row.get("provenance", "")
    return stream, payload, provenance


def step_B(stream: str, value: Any) -> list[tuple[str, float]]:
    """Match stream/value to branches → [(branch_id, proximity)]."""
    return _match_branches(stream, value)


def step_C(stream: str, value: Any, matches: list[tuple[str, float]]) -> list[tuple[str, float]]:
    """Compute magnitude per branch → [(branch_id, magnitude)]."""
    result = []
    for branch_id, proximity in matches:
        mag = _magnitude_for(stream, value, branch_id)
        combined = mag * proximity
        result.append((branch_id, combined))
    return result


def step_D(magnitudes: list[tuple[str, float]], aperture: float) -> list[tuple[str, float]]:
    """Gate magnitudes through membrane aperture."""
    return [(bid, mag * aperture) for bid, mag in magnitudes]


def step_E(tree: BonsaiTree, magnitudes: list[tuple[str, float]],
           value: Any) -> list[tuple[str, float, str]]:
    """Compute valence per branch → [(branch_id, magnitude, valence)].

    For text payloads: high magnitude + smooth texture → 'like';
                       high magnitude + rough texture → 'neutral' (overwhelm dampening).
    For numeric payloads: positive delta → 'like', negative → 'dislike'.
    """
    result = []
    is_text = isinstance(value, str)
    for branch_id, mag in magnitudes:
        node = tree.get(branch_id)
        if node is None:
            result.append((branch_id, mag, "neutral"))
            continue

        if is_text:
            # rough texture (texture_num > 0.6) → overwhelm → neutral
            if mag > 0.4 and node.texture_num <= 0.6:
                valence = "like"
            else:
                valence = "neutral"
        else:
            if isinstance(value, (int, float)):
                valence = "like" if float(value) >= 0 else "dislike"
            else:
                valence = "neutral"

        result.append((branch_id, mag, valence))
    return result


def step_F(tree: BonsaiTree, membrane: Membrane, writer: Writer,
           stream: str, provenance: str,
           valenced: list[tuple[str, float, str]]) -> int:
    """Attend tree, add to accumulator, log events. Returns count logged."""
    count = 0
    for branch_id, mag, valence in valenced:
        if mag < 0.001:
            continue
        tree.attend(branch_id, mag)
        membrane.add_to_accumulator(branch_id, provenance, mag)
        _log_event(writer, "F", provenance or stream, branch_id, mag, valence,
                   {"stream": stream})
        count += 1
    return count


def run_pipeline(row: dict, tree: BonsaiTree, membrane: Membrane,
                 writer: Writer, hook=None) -> int:
    """Full A-F pipeline for one sense_events row. Returns branch hits.

    hook: optional callable(event_dict) called after step F for each logged event.
    """
    try:
        stream, value, provenance = step_A(row)
        matches = step_B(stream, value)
        if not matches:
            return 0
        for branch_id, _ in matches:
            _log_event(writer, "B", stream, branch_id, 0.0, None, None)
        magnitudes = step_C(stream, value, matches)
        gated = step_D(magnitudes, membrane.aperture)
        for branch_id, mag in gated:
            _log_event(writer, "D", provenance or stream, branch_id, mag, None, None)
        valenced = step_E(tree, gated, value)
        for branch_id, mag, valence in valenced:
            _log_event(writer, "E", provenance or stream, branch_id, mag, valence, None)
        hits = step_F(tree, membrane, writer, stream, provenance, valenced)
        if hook is not None and hits > 0:
            for branch_id, mag, valence in valenced:
                if mag >= 0.001:
                    try:
                        hook({
                            "sensation_source": provenance or stream,
                            "branch_id": branch_id,
                            "magnitude": mag,
                            "valence": valence,
                        })
                    except Exception:
                        pass
        return hits
    except Exception as exc:
        errors.record(
            f"pipeline error on row id={row.get('id')}: {exc}",
            source=_LOG_SOURCE,
            exc=exc,
        )
        return 0
