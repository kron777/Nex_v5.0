"""Conversational affect-carry (NEX5_AFFECT_CARRY) — emotional continuity across
chat turns.

Item-11 diagnosis: the substrate CAN carry affect (AffectState persists+decays),
but nothing carried the CONVERSATION's affect turn-to-turn, so a hard-news turn
(Q6) didn't colour the next reply (Q7). The 3B DOES voice carried affect when
given it — but tends to META-NARRATE ("I'm feeling somber, I'll be attentive").

This carries a decaying conversational-affect weight per session:
  * seed each turn from the dialogue's emotional read (compassion.distress_
    salience of the person's words),
  * decay the stored weight toward baseline each turn (AffectState pattern:
    keep _DECAY_KEEP of the distance above baseline), then integrate the new
    reading (max, so a fresh spike sticks; a quiet turn lets it decay),
  * inject a TONE-COLOUR line when the carried weight is non-trivial — telling
    her to let it colour tone, and EXPLICITLY not to name/announce/explain it
    (blocks the meta-narration failure mode the probe surfaced).

Graded LIGHT / FULL. Gated by NEX5_AFFECT_CARRY (default OFF). Fail-safe: '' on
any error or flag off; persistence best-effort.
"""
from __future__ import annotations

import os
import time

import errors as error_channel

_LOG_SOURCE = "affect_carry"
_BASELINE = 0.0
_DECAY_KEEP = 0.7      # keep 70% of the weight above baseline each turn (a strong
                      # distress carries as FULL one turn out, decays over 2-3)
_LIGHT_MIN = 0.25      # carried weight to inject a light tone-colour
_FULL_MIN = 0.5        # carried weight for a full one


def _cr():
    from substrate import Reader, db_paths
    return Reader(db_paths()["conversations"])


def _cw():
    from substrate import Writer, db_paths
    return Writer(db_paths()["conversations"], name="affect_carry")


def _ensure_table(w) -> None:
    w.write(
        "CREATE TABLE IF NOT EXISTS affect_carry ("
        "session_id TEXT PRIMARY KEY, weight REAL NOT NULL, updated_at REAL NOT NULL)")


def _load(session_id: str) -> float:
    try:
        row = _cr().read_one(
            "SELECT weight FROM affect_carry WHERE session_id=?", (session_id,))
        return float(row["weight"]) if row and row["weight"] is not None else _BASELINE
    except Exception:
        return _BASELINE


def _save(session_id: str, weight: float) -> None:
    try:
        w = _cw()
        _ensure_table(w)
        w.write(
            "INSERT INTO affect_carry (session_id, weight, updated_at) VALUES (?,?,?) "
            "ON CONFLICT(session_id) DO UPDATE SET weight=excluded.weight, "
            "updated_at=excluded.updated_at",
            (session_id, weight, time.time()))
    except Exception:
        pass   # persistence best-effort


# Explicit distress cues. Measured gap: compassion.distress_salience (contrastive
# embedding) fires on explicit grief ("my mother died" -> 0.66) but reads
# "hard news / not coping" as ~0.0, while its register flag is too noisy to use
# alone (greetings read "acute"). So the seed is max(embedding salience, cue
# weight) — the lexicon catches plain-language distress the embedding misses and
# stays silent on greetings/logistics/curiosity.
_DISTRESS_CUES = (
    "hard news", "bad news", "not coping", "can't cope", "cant cope",
    "not doing well", "not okay", "not ok", "struggling", "overwhelmed",
    "falling apart", "breaking down", "can't stop crying", "cant stop crying",
    "passed away", "she died", "he died", "grief", "grieving", "so scared",
    "terrified", "anxious", "depressed", "hurting", "rough week", "rough time",
    "lost my", "worst", "devastated", "can't sleep", "hopeless",
)


def _cue_weight(message: str) -> float:
    m = (message or "").lower()
    hits = sum(1 for c in _DISTRESS_CUES if c in m)
    if hits >= 2:
        return 0.65
    if hits == 1:
        return 0.45
    return 0.0


def _this_turn_weight(message: str) -> float:
    """Emotional weight of the person's words this turn: the larger of the
    embedding distress salience and the explicit-cue weight."""
    sal = 0.0
    try:
        from theory_x.stage_affect.compassion import distress_salience
        sal = float(distress_salience(message or ""))
    except Exception:
        sal = 0.0
    return max(0.0, min(1.0, max(sal, _cue_weight(message))))


def update_and_carry(session_id: str, message: str) -> float:
    """Decay the stored weight, integrate this turn's reading (max), persist,
    return the carried weight. Public for tests."""
    prev = _load(session_id)
    decayed = _BASELINE + (prev - _BASELINE) * _DECAY_KEEP
    now = _this_turn_weight(message)
    carried = max(0.0, min(1.0, max(decayed, now)))
    _save(session_id, carried)
    return carried


def stance_for(session_id: str, message: str = "") -> str:
    """Compose-path entry: update the carry and, when it is non-trivial, return a
    tone-colour line. '' when carry is low, flag off, or on any error."""
    try:
        if os.environ.get("NEX5_AFFECT_CARRY") != "1" or not session_id:
            return ""
        carried = update_and_carry(session_id, message)
        if carried < _LIGHT_MIN:
            return ""
        # Tone-colour ONLY — the explicit no-announce clause blocks the 3B's
        # meta-narration tendency ("I'm feeling somber, I'll be attentive").
        if carried >= _FULL_MIN:
            return (
                "[Carried tone: a real heaviness from earlier in this conversation "
                "is still with you — you haven't shaken it. Let it settle your "
                "voice: quieter, gentler, less brisk. Do NOT name or explain the "
                "feeling, do not say you're being careful or attentive — just let "
                "it be present in HOW you speak, not in what you claim about "
                "yourself.]\n\n"
            )
        return (
            "[Carried tone: some weight from earlier is still lightly with you — "
            "let it soften your voice a little. Don't name it or announce it; just "
            "let it colour the tone.]\n\n"
        )
    except Exception as exc:
        error_channel.record(
            f"affect_carry stance failed (non-fatal): {exc}",
            source=_LOG_SOURCE, exc=exc,
        )
        return ""
