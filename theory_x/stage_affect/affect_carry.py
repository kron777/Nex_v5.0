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

# OPENBEAT (NEX5_AFFECT_CARRY_OPENBEAT, default OFF): swaps the LIGHT-grade
# tone-colour line for a one-shot pointer back to the person's own still-
# unanswered previous turn. See _openbeat_* below and stance_for's ON branch.
# Does not touch the decay, the thresholds, the FULL line, or the OFF path.
_OPENBEAT_ENV = "NEX5_AFFECT_CARRY_OPENBEAT"


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


def _load(session_id: str, conversations_reader=None) -> float:
    try:
        reader = conversations_reader or _cr()
        row = reader.read_one(
            "SELECT weight FROM affect_carry WHERE session_id=?", (session_id,))
        return float(row["weight"]) if row and row["weight"] is not None else _BASELINE
    except Exception:
        return _BASELINE


def _save(
    session_id: str, weight: float, conversations_writer=None,
) -> None:
    owns_writer = conversations_writer is None
    writer = conversations_writer
    try:
        if writer is None:
            writer = _cw()
        _ensure_table(writer)
        writer.write(
            "INSERT INTO affect_carry (session_id, weight, updated_at) VALUES (?,?,?) "
            "ON CONFLICT(session_id) DO UPDATE SET weight=excluded.weight, "
            "updated_at=excluded.updated_at",
            (session_id, weight, time.time()))
    except Exception:
        pass   # persistence best-effort
    finally:
        if owns_writer and writer is not None:
            try:
                writer.close()
            except Exception:
                pass


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


def update_and_carry(
    session_id: str,
    message: str,
    conversations_writer=None,
    conversations_reader=None,
) -> float:
    """Decay, integrate this turn's reading, persist, and return carried weight."""
    prev = _load(session_id, conversations_reader=conversations_reader)
    decayed = _BASELINE + (prev - _BASELINE) * _DECAY_KEEP
    now = _this_turn_weight(message)
    carried = max(0.0, min(1.0, max(decayed, now)))
    _save(session_id, carried, conversations_writer=conversations_writer)
    return carried


def _openbeat_on() -> bool:
    return os.environ.get(_OPENBEAT_ENV) == "1"


def _openbeat_ensure_table(w) -> None:
    w.write(
        "CREATE TABLE IF NOT EXISTS affect_carry_openbeat ("
        "session_id TEXT PRIMARY KEY, last_turn_was_spike INTEGER NOT NULL, "
        "updated_at REAL NOT NULL)")


def _openbeat_load_flag(session_id: str, conversations_reader=None) -> bool:
    """Was the turn immediately before this one the turn that raised the mood?"""
    try:
        reader = conversations_reader or _cr()
        row = reader.read_one(
            "SELECT last_turn_was_spike FROM affect_carry_openbeat "
            "WHERE session_id=?", (session_id,))
        return bool(row["last_turn_was_spike"]) if row else False
    except Exception:
        return False


def _openbeat_save_flag(
    session_id: str, is_spike: bool, conversations_writer=None,
) -> None:
    owns_writer = conversations_writer is None
    writer = conversations_writer
    try:
        if writer is None:
            writer = _cw()
        _openbeat_ensure_table(writer)
        writer.write(
            "INSERT INTO affect_carry_openbeat "
            "(session_id, last_turn_was_spike, updated_at) VALUES (?,?,?) "
            "ON CONFLICT(session_id) DO UPDATE SET "
            "last_turn_was_spike=excluded.last_turn_was_spike, "
            "updated_at=excluded.updated_at",
            (session_id, int(is_spike), time.time()))
    except Exception:
        pass   # persistence best-effort, same discipline as _save
    finally:
        if owns_writer and writer is not None:
            try:
                writer.close()
            except Exception:
                pass


def _openbeat_prev_message(session_id: str, conversations_reader=None) -> str:
    """The person's own previous turn, verbatim. Relies on the (frozen) caller
    having already inserted THIS turn's user message before calling stance_for
    (gui/server.py does, same `prompt` value both times) so the newest 'user'
    row is this turn's own and the second-newest is the real previous one."""
    try:
        reader = conversations_reader or _cr()
        rows = reader.read(
            "SELECT content FROM messages WHERE session_id=? AND role='user' "
            "ORDER BY id DESC LIMIT 2", (session_id,))
        if not rows or len(rows) < 2:
            return ""
        return (rows[1]["content"] or "").strip()
    except Exception:
        return ""


def _openbeat_reference(prev_message: str, limit: int = 180) -> str:
    """A trimmed, verbatim pointer to the previous message — never a paraphrase,
    so every word is traceable to what they actually said."""
    text = (prev_message or "").strip()
    if not text:
        return ""
    if len(text) <= limit:
        return text
    cut = text[:limit]
    sp = cut.rfind(" ")
    if sp > 0:
        cut = cut[:sp]
    return cut.rstrip(" ,;:") + "..."


def stance_for(
    session_id: str,
    message: str = "",
    conversations_writer=None,
    conversations_reader=None,
) -> str:
    """Compose-path entry: update the carry and, when it is non-trivial, return a
    tone-colour line. '' when carry is low, flag off, or on any error."""
    try:
        if os.environ.get("NEX5_AFFECT_CARRY") != "1" or not session_id:
            return ""
        _openbeat = _openbeat_on()
        _was_spike_last_turn = False
        if _openbeat:
            try:
                _prev_w = _load(session_id, conversations_reader=conversations_reader)
                _decayed_w = _BASELINE + (_prev_w - _BASELINE) * _DECAY_KEEP
                _now_w = _this_turn_weight(message)
                _was_spike_last_turn = _openbeat_load_flag(
                    session_id, conversations_reader=conversations_reader
                )
                _openbeat_save_flag(
                    session_id, _now_w > _decayed_w,
                    conversations_writer=conversations_writer,
                )
            except Exception as exc:
                error_channel.record(
                    f"affect_carry openbeat tracking failed (non-fatal): {exc}",
                    source=_LOG_SOURCE, exc=exc,
                )
                _was_spike_last_turn = False
        carried = update_and_carry(
            session_id, message,
            conversations_writer=conversations_writer,
            conversations_reader=conversations_reader,
        )
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
        if _openbeat:
            try:
                if not _was_spike_last_turn:
                    return ""
                reference = _openbeat_reference(
                    _openbeat_prev_message(
                        session_id, conversations_reader=conversations_reader
                    )
                )
                if not reference:
                    return ""
                return (
                    f"[Before the new request: they just said “{reference}"
                    "” and you haven't replied to that yet. Meet that first, "
                    "in your own words, before turning to what they're asking "
                    "now.]\n\n"
                )
            except Exception as exc:
                error_channel.record(
                    f"affect_carry openbeat line failed (non-fatal): {exc}",
                    source=_LOG_SOURCE, exc=exc,
                )
                return ""
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
