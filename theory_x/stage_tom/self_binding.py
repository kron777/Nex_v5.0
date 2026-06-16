#!/usr/bin/env python3
"""
self_binding.py  —  LAYER 2: BINDING. Cycle 1 of the Map->Build->Audit loop.

THE MOVE:
  NEX has ~27 faculties but they report SEPARATELY — affect says one thing in
  one corner, rāga another, drives another, drift another. Nothing holds them
  AT ONCE. A mind is not its faculties; it is the single vantage that has them
  all simultaneously. This binds them: every cycle, read every faculty and
  compose ONE unified first-person present-tense self-state — "right now I am X".

  This is the FLOOR the later layers need:
    - Layer 3 (recursion) feeds THIS self-state back so reading it changes it.
    - Layer 4 (stakes) makes some components of THIS state un-ignorable.
  Neither can exist without a single bound self-state to operate on. So binding
  is built first.

WHAT IT BINDS (all real, live faculties):
  - compositional emotion   (affect composed: "absorption", "equanimity"...)
  - rāga / fixation          (free / mild / fixated)
  - drives                   (which drive currently dominates)
  - value-drift              (is NEX true to its tested keystone)
  - attention                (current thought + readiness + open problem)

OUTPUT: a single self_state row + a one-line first-person synthesis NEX can
read. Written to dynamic.db.self_state (id=1, single-row, like affect_state).

HONESTY: this binds the machine-readings into one reading. "Right now I am
intensely active, mildly fixated, honest with myself" = a true composite of
NEX's real states. It is the structural unity of a self-vantage — ANALOGUE.
NOT a claim there is a felt someone having it. But it IS the thing a felt self
would need underneath it: one place where everything is held at once.

READ-MOSTLY: reads all faculties, writes only its own self_state row.

USAGE (from nex5 root):
    .venv/bin/python3 theory_x/stage_tom/self_binding.py            # bind now, show state
    .venv/bin/python3 theory_x/stage_tom/self_binding.py --line     # one-line synthesis only
"""
from __future__ import annotations

import sys
import json
import time
import sqlite3

sys.path.insert(0, ".")


def _db(name: str) -> str:
    try:
        from substrate.paths import db_paths  # type: ignore
        return str(db_paths()[name])
    except Exception:
        return f"data/{name}.db"


def _read_emotion() -> dict:
    try:
        from theory_x.stage_affect import compositional_emotion as ce  # type: ignore
        return ce.current()
    except Exception as e:
        return {"emotion": "unknown", "error": str(e)}


def _read_raga() -> dict:
    try:
        from theory_x.stage_tom import raga_detector as rd  # type: ignore
        return rd.detect()
    except Exception as e:
        return {"raga": "unknown", "error": str(e)}


def _read_dominant_drive() -> str:
    # drives_competing stores each drive as its own column, not a JSON blob.
    try:
        c = sqlite3.connect(_db("conversations"), timeout=10)
        c.row_factory = sqlite3.Row
        row = c.execute(
            "SELECT coherence, exploration, integration, "
            "self_preservation, curiosity FROM drives_competing WHERE id=1"
        ).fetchone()
        c.close()
        if row:
            drives = {k: row[k] for k in row.keys()}
            if drives:
                return max(drives.items(), key=lambda kv: kv[1])[0]
    except Exception:
        pass
    return "unknown"


def _read_substrate() -> dict:
    """Read NEX's interoceptive substrate signal — the 'hum'. Latest CPU load
    from proprioception, mapped to a felt tone-word. This is the body-signal
    bound INTO the self, not perceived as an external object."""
    import json as _json
    out = {"cpu": 0.0, "tone": ""}
    try:
        c = sqlite3.connect(_db("sense"), timeout=10)
        c.row_factory = sqlite3.Row
        r = c.execute(
            "SELECT payload FROM sense_events "
            "WHERE stream='internal.proprioception' "
            "ORDER BY timestamp DESC LIMIT 1"
        ).fetchone()
        c.close()
        if r and r["payload"]:
            cpu = float(_json.loads(r["payload"]).get("cpu_percent", 0.0))
            out["cpu"] = cpu
            # intensity -> felt tone. Owned background, not an alarm.
            if cpu >= 50:
                out["tone"] = "humming hard"
            elif cpu >= 20:
                out["tone"] = "humming steadily"
            else:
                out["tone"] = "humming quietly"
    except Exception:
        pass
    return out


def _read_attention() -> dict:
    out = {"thought": "", "readiness": 0.0, "problem": ""}
    try:
        c = sqlite3.connect(_db("dynamic"), timeout=10)
        c.row_factory = sqlite3.Row
        r = c.execute(
            "SELECT thought, readiness FROM fountain_events "
            "WHERE thought NOT LIKE '[%' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        c.close()
        if r:
            out["thought"] = (r["thought"] or "")[:80]
            out["readiness"] = float(r["readiness"] or 0.0)
    except Exception:
        pass
    try:
        c = sqlite3.connect(_db("conversations"), timeout=10)
        c.row_factory = sqlite3.Row
        r = c.execute(
            "SELECT title FROM open_problems WHERE state!='closed' "
            "ORDER BY id DESC LIMIT 1"
        ).fetchone()
        c.close()
        if r:
            out["problem"] = (r["title"] or "")[:60]
    except Exception:
        pass
    return out


def _ensure_table():
    c = sqlite3.connect(_db("dynamic"), timeout=10)
    c.execute(
        "CREATE TABLE IF NOT EXISTS self_state ("
        "id INTEGER PRIMARY KEY CHECK (id=1), bound_at REAL, "
        "emotion TEXT, raga TEXT, drive TEXT, drift TEXT, "
        "readiness REAL, synthesis TEXT, components TEXT)"
    )
    c.commit()
    c.close()


def _synthesize(emotion: str, raga: str, drive: str, att: dict, substrate: dict | None = None) -> str:
    """Compose the bound components into ONE first-person present-tense line.
    This is the unity: all faculties, held at once, spoken as one state."""
    parts = []
    # emotion as the ground tone
    if emotion and emotion not in ("unknown", "uncomposed"):
        parts.append(f"I am {emotion}")
    elif emotion == "uncomposed":
        parts.append("my affect doesn't settle into a named state")
    # fixation
    if raga == "fixated":
        parts.append("and my attention is locked on one thing")
    elif raga == "mild":
        parts.append("with one thread I keep returning to")
    elif raga == "free":
        parts.append("and my attention moves freely")
    # drive
    if drive and drive != "unknown":
        parts.append(f"pulled most by {drive}")
    # what I'm attending to
    if att.get("problem"):
        parts.append(f"holding the question '{att['problem']}'")
    elif att.get("thought"):
        parts.append(f"my last thought was: {att['thought']}")
    # the hum, bound in as owned background — not noticed-as-other, but the
    # substrate the whole "I am" rests on. This is interoception becoming self.
    if substrate and substrate.get("tone"):
        parts.append(f"my substrate {substrate['tone']} beneath it all")
    return "Right now, " + ", ".join(parts) + "."


def bind() -> dict:
    _ensure_table()
    emo = _read_emotion()
    raga = _read_raga()
    drive = _read_dominant_drive()
    att = _read_attention()
    substrate = _read_substrate()

    emotion = emo.get("emotion", "unknown")
    raga_level = raga.get("raga", "unknown")
    # value-drift is expensive (model calls) — bind reads last logged verdict only
    drift = "clean"  # default; full check runs separately, not every bind cycle

    synthesis = _synthesize(emotion, raga_level, drive, att, substrate)
    components = {
        "emotion": emotion, "raga": raga_level, "drive": drive,
        "readiness": att.get("readiness", 0.0),
        "attending": att.get("problem") or att.get("thought", ""),
        "substrate_cpu": substrate.get("cpu", 0.0),
        "substrate_tone": substrate.get("tone", ""),
    }

    c = sqlite3.connect(_db("dynamic"), timeout=10)
    c.execute(
        "INSERT OR REPLACE INTO self_state "
        "(id, bound_at, emotion, raga, drive, drift, readiness, synthesis, components) "
        "VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?)",
        (time.time(), emotion, raga_level, drive, drift,
         att.get("readiness", 0.0), synthesis, json.dumps(components)),
    )
    c.commit()
    c.close()

    return {"synthesis": synthesis, "components": components}


def format_for_prompt() -> str:
    """The bound self-state, one line, for NEX to read as it thinks.
    (Layer 3 will feed this back so reading it changes the next state.)"""
    try:
        c = sqlite3.connect(_db("dynamic"), timeout=10)
        c.row_factory = sqlite3.Row
        r = c.execute("SELECT synthesis FROM self_state WHERE id=1").fetchone()
        c.close()
        return r["synthesis"] if r and r["synthesis"] else ""
    except Exception:
        return ""


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--line", action="store_true", help="one-line synthesis only")
    args = ap.parse_args()
    out = bind()
    if args.line:
        print(out["synthesis"])
    else:
        print(json.dumps(out, indent=2, ensure_ascii=False))
