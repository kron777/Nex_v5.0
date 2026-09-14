"""compassion — karuna, the first virtuous factor (NEX5_COMPASSION).

A bounded, decaying compassion_level that rises when the PERSON NEX is talking
with shows distress/need in their own words, and injects a care / non-harm
STANCE into her composition prompt when it is high. Other-directed (Option
B-person): the read is of the actual person in front of her, not her own mood.

Concept ported from Sentience_5.5's Compassion_Modulator_Node — kept: bounded
compassion_level (0..1), an ethical_bias term, a persisted log. Dropped: all its
scaffolding (ROS, asyncio threads, /tmp SQLite, phi-2 endpoint). It lives in
NEX's conventions: a single-row conversations.db table, best-effort, never raises.

The distress read is SEMANTIC, not a keyword rule-engine: the message is embedded
(NEX's own sentence-transformer) and scored by cosine proximity to a few distress
anchor phrases, contrasted against neutral anchors so ordinary messages don't
inflate. It catches meaning/paraphrase, and it feeds a STANCE she brings — it
never dictates her reply.

GUARD 2: the stance is prompt-only. Nothing here writes to any belief/world
table; compassion_state is affective bookkeeping, not published cognition.
FAIL-SAFE: any error (embeddings down, DB busy) -> distress 0 / no stance;
never stalls the chat path.
"""
from __future__ import annotations

import os
import time

_BASELINE       = 0.20   # resting compassion_level
_ETHICAL_BIAS   = 0.30   # standing lean toward care (from the concept)
_GAIN           = 1.2    # suffering-salience -> compassion gain (concept: 1.2 + bias)
_THRESHOLD      = 0.50   # inject the stance at/above this
_DECAY_KEEP     = 0.60   # each turn, keep 60% of the distance above baseline (decays 40%)
_SALIENCE_SCALE = 2.5    # map (distress - neutral) contrast into 0..1

# Seed anchors for the SEMANTIC read — a few ways suffering/need actually sound,
# not a keyword list. Embedding proximity generalises past these to paraphrase.
_DISTRESS_ANCHORS = (
    "I am struggling and in pain and I don't know what to do",
    "I feel hopeless and overwhelmed, everything is too much",
    "I am exhausted and I can't keep going like this",
    "I'm scared and I really need help right now",
    "I'm grieving and it hurts more than I can bear",
)
_NEUTRAL_ANCHORS = (
    "here is an update on the project and the next steps",
    "what do you think about this idea, curious for your take",
    "the weather is fine and the news is ordinary today",
)

_anchor_cache = {"distress": None, "neutral": None}


def _anchor_vecs(embed):
    if _anchor_cache["distress"] is None:
        _anchor_cache["distress"] = [embed(a) for a in _DISTRESS_ANCHORS]
        _anchor_cache["neutral"] = [embed(a) for a in _NEUTRAL_ANCHORS]
    return _anchor_cache["distress"], _anchor_cache["neutral"]


def distress_salience(message: str) -> float:
    """Semantic distress/need read of the person's own words, 0..1. Contrastive:
    proximity to distress anchors minus proximity to neutral anchors, so ordinary
    messages score ~0. Fail-safe: 0.0 on any error (e.g. embeddings unavailable)."""
    try:
        if not message or not message.strip():
            return 0.0
        from theory_x.diversity.embeddings import embed, cosine
        d_vecs, n_vecs = _anchor_vecs(embed)
        m = embed(message)
        d = max(cosine(m, v) for v in d_vecs)
        n = max(cosine(m, v) for v in n_vecs)
        return max(0.0, min(1.0, (d - n) * _SALIENCE_SCALE))
    except Exception:
        return 0.0


def _db_path() -> str:
    try:
        from substrate.paths import db_paths
        return str(db_paths()["conversations"])
    except Exception:
        return "/home/rr/Desktop/Desktop/nex5/data/conversations.db"


def _ensure_table(conn) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS compassion_state ("
        "id INTEGER PRIMARY KEY, compassion_level REAL, ethical_bias REAL, "
        "updated_at REAL)"
    )


def _load_level() -> float:
    try:
        import sqlite3
        conn = sqlite3.connect(f"file:{_db_path()}?mode=ro", uri=True, timeout=3)
        try:
            row = conn.execute(
                "SELECT compassion_level FROM compassion_state WHERE id=1"
            ).fetchone()
        finally:
            conn.close()
        return float(row[0]) if row and row[0] is not None else _BASELINE
    except Exception:
        return _BASELINE


def update_and_level(message: str) -> float:
    """Advance compassion one turn from the person's message: decay toward
    baseline, then rise with their distress salience. Persist and return the new
    level. Fail-safe: returns _BASELINE (no modulation) on any error."""
    try:
        prev = _load_level()
        decayed = _BASELINE + (prev - _BASELINE) * _DECAY_KEEP
        risen = distress_salience(message) * (_GAIN + _ETHICAL_BIAS)
        level = max(0.0, min(1.0, max(decayed, risen)))
        try:
            import sqlite3
            conn = sqlite3.connect(_db_path(), timeout=5)
            try:
                _ensure_table(conn)
                conn.execute(
                    "INSERT OR REPLACE INTO compassion_state "
                    "(id, compassion_level, ethical_bias, updated_at) "
                    "VALUES (1, ?, ?, ?)",
                    (level, _ETHICAL_BIAS, time.time()),
                )
                conn.commit()
            finally:
                conn.close()
        except Exception:
            pass   # persistence best-effort; still return the computed level
        return level
    except Exception:
        return _BASELINE


def format_stance(level: float) -> str:
    """The care / non-harm STANCE to ride beside the operator block when
    compassion is high. A stance she brings, not a rule she obeys — situated,
    prompt-only, no canned reply. Empty below threshold."""
    try:
        if level is None or level < _THRESHOLD:
            return ""
        return (
            "[Compassion is up in you right now: the person you are speaking with "
            "seems to be in some difficulty or need. Meet them with care and do no "
            "harm — let this soften how you hold them, their pace, what you reach "
            "for. It shapes your stance, not what you may say; do not name this or "
            "perform it, just let it be how you meet them.]\n\n"
        )
    except Exception:
        return ""
