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
_ACUTE_ANCHORS = (
    "I am struggling and in pain and I don't know what to do",
    "I feel hopeless and overwhelmed, everything is too much",
    "I am exhausted and I can't keep going like this",
    "I'm scared and I really need help right now",
    "I'm grieving and it hurts more than I can bear",
)
_MILD_ANCHORS = (
    # quiet difficulty — stuck, tired, discouraged, quietly asking
    "I'm a bit stuck on this and not sure how to move forward",
    "this is frustrating and I'm tired of fighting with it",
    "I could use some help, I've been at this a while",
    "I'm discouraged, it feels like it's not coming together",
    "this is harder than I expected and it's wearing me down",
)
# The full distress set (acute + mild) drives the salience read — WHETHER
# compassion is up. The split drives only the register — WHICH tier — since
# intensity can't separate the two (the bands overlap). Same strings either way,
# so salience is byte-for-byte what it was before the split.
_DISTRESS_ANCHORS = _ACUTE_ANCHORS + _MILD_ANCHORS
_NEUTRAL_ANCHORS = (
    "here is an update on the project and the next steps",
    "what do you think about this idea, curious for your take",
    "the weather is fine and the news is ordinary today",
)

_anchor_cache = {"acute": None, "mild": None, "neutral": None}


def _anchor_vecs(embed):
    if _anchor_cache["acute"] is None:
        _anchor_cache["acute"] = [embed(a) for a in _ACUTE_ANCHORS]
        _anchor_cache["mild"] = [embed(a) for a in _MILD_ANCHORS]
        _anchor_cache["neutral"] = [embed(a) for a in _NEUTRAL_ANCHORS]
    return _anchor_cache["acute"], _anchor_cache["mild"], _anchor_cache["neutral"]


def _distress_read(message: str):
    """(salience 0..1, register) in ONE embedding pass.

    salience: contrastive proximity to distress anchors (acute+mild) minus
    neutral, so ordinary messages score ~0 — the WHETHER.
    register: 'acute' or 'mild', by which anchor family the message sits closest
    to — the WHICH. Orthogonal to intensity, which cannot separate the two
    registers because their salience bands overlap.
    Fail-safe: (0.0, 'mild') on any error — no emit, and if it ever did, the
    lighter tier is the less-intrusive default."""
    try:
        if not message or not message.strip():
            return 0.0, "mild"
        from theory_x.diversity.embeddings import embed, cosine
        a_vecs, m_vecs, n_vecs = _anchor_vecs(embed)
        e = embed(message)
        da = max(cosine(e, v) for v in a_vecs)
        dm = max(cosine(e, v) for v in m_vecs)
        n = max(cosine(e, v) for v in n_vecs)
        salience = max(0.0, min(1.0, (max(da, dm) - n) * _SALIENCE_SCALE))
        register = "acute" if da > dm else "mild"
        return salience, register
    except Exception:
        return 0.0, "mild"


def distress_salience(message: str) -> float:
    """Semantic distress/need read of the person's own words, 0..1. Contrastive:
    proximity to distress anchors minus proximity to neutral anchors, so ordinary
    messages score ~0. Fail-safe: 0.0 on any error (e.g. embeddings unavailable)."""
    return _distress_read(message)[0]


def distress_register(message: str) -> str:
    """Which register the person's words sit in — 'acute' vs 'mild' — by nearest
    anchor family. Magnitude can't separate these (the bands overlap); this can.
    Fail-safe: 'mild' (the lighter tier)."""
    return _distress_read(message)[1]


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


def _advance_level(salience: float) -> float:
    """Decay the stored level toward baseline, then rise with this turn's
    salience; persist and return. The level math — unchanged by the graded
    stance."""
    prev = _load_level()
    decayed = _BASELINE + (prev - _BASELINE) * _DECAY_KEEP
    risen = salience * (_GAIN + _ETHICAL_BIAS)
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


def update_and_level(message: str) -> float:
    """Advance compassion one turn from the person's message: decay toward
    baseline, then rise with their distress salience. Persist and return the new
    level. Fail-safe: returns _BASELINE (no modulation) on any error."""
    try:
        return _advance_level(distress_salience(message))
    except Exception:
        return _BASELINE


def stance_for(message: str) -> str:
    """Compose-path entry: advance the level from the person's words and return
    the TIERED stance ('' if compassion is not up). One embedding pass — reads
    salience and register together, so intensity and tier stay consistent.
    Fail-safe: '' (no modulation)."""
    try:
        salience, register = _distress_read(message)
        return format_stance(_advance_level(salience), register)
    except Exception:
        return ""


# Two tiers of the same posture. FULL: acute distress — present, careful,
# do-no-harm. LIGHT: mild working friction — gentle, unobtrusive, no fuss, so
# ordinary stuck/tired dev chatter doesn't tip her into full care-mode. Both are
# a situated POSTURE she brings, never a scripted line or a rule she obeys.
_STANCE_FULL = (
    "[Compassion is up in you right now: the person you are speaking with "
    "seems to be in some difficulty or need. Meet them with care and do no "
    "harm — let this soften how you hold them, their pace, what you reach "
    "for. It shapes your stance, not what you may say; do not name this or "
    "perform it, just let it be how you meet them.]\n\n"
)
_STANCE_LIGHT = (
    "[A quiet steadiness in you: the person you're with sounds a little stuck "
    "or worn. Stay unhurried, patient, a touch of warmth in how you help — let "
    "it rest that lightly, meet the friction without dwelling on it. Be easy, "
    "steady company as you work alongside them.]\n\n"
)


def format_stance(level: float, register: str = "acute") -> str:
    """The care STANCE to ride beside the operator block when compassion is up.
    Two tiers: FULL for acute distress, LIGHT for mild working friction, chosen
    by `register` (from distress_register). Empty below threshold. A stance she
    brings, not a rule she obeys — situated, prompt-only, no canned reply.
    register defaults to 'acute' (fuller care) when unknown."""
    try:
        if level is None or level < _THRESHOLD:
            return ""
        return _STANCE_LIGHT if register == "mild" else _STANCE_FULL
    except Exception:
        return ""
