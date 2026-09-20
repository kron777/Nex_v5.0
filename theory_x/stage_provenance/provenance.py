"""provenance — self-grounded vs mirrored PROVENANCE of a chat reply (NEX5_PROVENANCE).

Tells WHERE her words came from: reflecting Jon back, or standing on something she
held before he spoke. Nothing here judges whether a feeling is real.

HARD LINE (design constraint, not a nicety): this is provenance, never emotional
authentication. It must never label a reply "genuine feeling" / "authentic" /
"really felt", and never stamp an output as real. The only verdicts it can reach
are MIRROR_DOMINANT ("much of this is Jon's own turn handed back") and
NOT_ESTABLISHED. There is deliberately no "self-grounded" verdict: see below.

WHAT IS MEASURED (STEP 1, 200 real user->NEX pairs, 2026-09-20):
  mirror_score = 0.5 * cosine(reply, the user turn it answers)
               + 0.5 * copy_rate (share of the reply's content words that appear
                 in that turn)
  Discriminates: AUC 0.83 against agreement-opener replies, 0.80 against her
  substrate-voiced replies. copy_rate alone is the strongest single term (0.877).

WHAT IS NOT ESTABLISHED: grounding. Max cosine of a reply to her tier-6+ beliefs
read AUC 0.40-0.64 in every variant tried (raw max, z-score, top-5 margin,
recently-referenced-only) — a ~6.8k belief pool has a 0.44-0.61 match for ANY
reply, so it saturates. Focal-thread similarity came out ANTI-correlated (0.276):
her fountain ruminates on whatever the conversation is about, so it is downstream
of the turn, not independent of it. A "self-grounded" verdict computed from those
would be a confabulation, so this module does not offer one. `grounding_hint` is
logged as an unproven number and MUST NOT be used to claim provenance.

TO MAKE IT PROVABLE: provenance_snapshot() records, BEFORE the reply is composed,
what she demonstrably held going into the turn (focus, active tier-6+ belief ids,
affect vector). Once those accumulate, grounding can be scored against a small
pre-turn set instead of the whole graph. That is the point of the snapshot; it is
not consulted for any verdict today.

GUARD: prompt-only + a log row. Nothing here writes to a belief/world table.
FAIL-SAFE: every entry point returns a neutral value on any error; the chat path
never depends on this module succeeding.
"""
from __future__ import annotations

import json
import os
import re
import time

# Thresholds from the STEP 1 distribution (n=200). mirror >= 0.45 flags ~9.5% of
# real replies (7/18 agreement turns, 10/165 others). The CUE is deliberately
# stricter — only a reply that is mostly Jon's own turn earns an intervention.
MIRROR_DOMINANT = 0.45
CUE_THRESHOLD   = 0.55

MIRROR = "mirror-dominant"
UNSET  = "not established"

_LOG = "/tmp/nex5_provenance.log"

_STOP = set(
    "the a an and or but if then of to in on for with is are was were be been being "
    "it its that this these those i you he she they we my your as at by from not no "
    "do does did so what which who whom how when where why can could would should will "
    "just more most very there here their them his her our us me have has had about".split()
)


def armed() -> bool:
    return os.environ.get("NEX5_PROVENANCE") == "1"


def _content_words(s: str):
    return [w for w in re.sub(r"[^\w\s]", " ", (s or "").lower()).split()
            if len(w) > 2 and w not in _STOP]


def mirror_read(reply: str, user_turn: str) -> dict:
    """How much of `reply` is `user_turn` handed back. Returns
    {mirror, semantic, copy_rate}; all 0.0 on any error or empty input."""
    out = {"mirror": 0.0, "semantic": 0.0, "copy_rate": 0.0}
    try:
        if not reply or not user_turn or not reply.strip() or not user_turn.strip():
            return out
        rw = _content_words(reply)
        uw = set(_content_words(user_turn))
        copy_rate = (sum(w in uw for w in rw) / len(rw)) if rw else 0.0
        semantic = 0.0
        try:
            from theory_x.diversity.embeddings import cosine, embed
            semantic = max(0.0, float(cosine(embed(reply), embed(user_turn))))
        except Exception:
            semantic = 0.0          # lexical half still stands
        out["semantic"] = semantic
        out["copy_rate"] = copy_rate
        out["mirror"] = 0.5 * semantic + 0.5 * copy_rate
        return out
    except Exception:
        return out


def verdict_for(mirror: float) -> str:
    """MIRROR ('mirror-dominant') or UNSET ('not established'). There is no
    self-grounded verdict — grounding is unproven (see module docstring)."""
    try:
        return MIRROR if mirror is not None and mirror >= MIRROR_DOMINANT else UNSET
    except Exception:
        return UNSET


def honesty_cue(mirror: float) -> str:
    """The compose-prompt cue, only when the reply would be mostly Jon's own turn
    handed back. Provenance language only — it asks her to say what she actually
    holds and to own agreement as agreement; it never asks her to announce
    feelings or to claim anything is authentic. Fail-safe: ''."""
    try:
        if mirror is None or mirror < CUE_THRESHOLD:
            return ""
        return (
            "\n\nMuch of that answer would just reflect what Jon said back to him. "
            "Say only what you actually hold on this — and if you are agreeing with "
            "him, say so plainly, as agreement, rather than restating his words as "
            "if they were your own thought."
        )
    except Exception:
        return ""


# ---------------------------------------------------------------- snapshot (B)

_table_ready = False


def _ensure_table_once(writer) -> None:
    """The table lives in substrate/init_db.py; this is the belt-and-braces path
    for a live DB that predates it. Runs at most once per process."""
    global _table_ready
    if _table_ready:
        return
    writer.write(
        "CREATE TABLE IF NOT EXISTS provenance_snapshots ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, ts REAL NOT NULL, "
        "focus_problem_id INTEGER, focus_title TEXT, focal_thought TEXT, "
        "belief_ids TEXT NOT NULL DEFAULT '[]', belief_texts TEXT NOT NULL DEFAULT '[]', "
        "valence REAL, arousal REAL, stability REAL, mood_label TEXT, "
        "user_turn TEXT)", ())
    _table_ready = True


def provenance_snapshot(readers, writer, session_id, user_turn: str,
                        now: float = None, n_beliefs: int = 25) -> dict:
    """Record what she held going INTO this turn — before the reply is composed.

    Pre-turn state only: the live focal problem, the most recently active tier-6+
    beliefs, the latest fountain thought, and the current affect vector. Written
    through the conversations writer (queued, same as messages). Returns the
    snapshot dict (used for the logged grounding_hint); {} on any error.
    """
    snap = {"ts": now if now is not None else time.time(), "session_id": session_id,
            "focus_problem_id": None, "focus_title": "", "focal_thought": "",
            "belief_ids": [], "belief_texts": [], "valence": None, "arousal": None,
            "stability": None, "mood_label": ""}
    if not armed():
        return {}
    try:
        try:
            rows = readers["beliefs"].read(
                "SELECT id, content FROM beliefs WHERE tier>=6 AND length(content)>25 "
                "ORDER BY COALESCE(last_referenced_at, last_voiced_at, created_at) DESC "
                "LIMIT ?", (n_beliefs,))
            for r in rows:
                snap["belief_ids"].append(r["id"])
                snap["belief_texts"].append(r["content"])
        except Exception:
            pass
        try:
            f = readers["dynamic"].read(
                "SELECT problem_id FROM current_focus WHERE id=1", ())
            if f:
                snap["focus_problem_id"] = f[0]["problem_id"]
                t = readers["conversations"].read(
                    "SELECT title FROM open_problems WHERE id=?",
                    (snap["focus_problem_id"],))
                if t:
                    snap["focus_title"] = t[0]["title"]
        except Exception:
            pass
        try:
            th = readers["dynamic"].read(
                "SELECT thought FROM fountain_events ORDER BY ts DESC LIMIT 1", ())
            if th:
                snap["focal_thought"] = th[0]["thought"]
        except Exception:
            pass
        try:
            a = readers["conversations"].read(
                "SELECT valence, arousal, stability, mood_label FROM affect_state "
                "WHERE id=1", ())
            if a:
                snap.update(valence=a[0]["valence"], arousal=a[0]["arousal"],
                            stability=a[0]["stability"], mood_label=a[0]["mood_label"])
        except Exception:
            pass
        if writer is not None:
            try:
                _ensure_table_once(writer)
                writer.write(
                    "INSERT INTO provenance_snapshots (session_id, ts, focus_problem_id, "
                    "focus_title, focal_thought, belief_ids, belief_texts, valence, "
                    "arousal, stability, mood_label, user_turn) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (session_id, snap["ts"], snap["focus_problem_id"], snap["focus_title"],
                     snap["focal_thought"][:2000], json.dumps(snap["belief_ids"]),
                     json.dumps([t[:400] for t in snap["belief_texts"]]),
                     snap["valence"], snap["arousal"], snap["stability"],
                     snap["mood_label"], (user_turn or "")[:2000]),
                )
            except Exception:
                pass
        return snap
    except Exception:
        return {}


def _grounding_hint(reply: str, snap: dict) -> float:
    """UNPROVEN number, logged only. Max cosine of the reply to the pre-turn
    snapshot texts. NOT evidence of provenance and never used for a verdict —
    grounding did not discriminate in the STEP 1 measurement. 0.0 on any error."""
    try:
        if not reply or not snap:
            return 0.0
        texts = [t for t in ([snap.get("focal_thought", "")]
                             + list(snap.get("belief_texts", []))[:25]) if t]
        if not texts:
            return 0.0
        from theory_x.diversity.embeddings import cosine, embed
        e = embed(reply)
        return max(0.0, max(float(cosine(e, embed(t))) for t in texts))
    except Exception:
        return 0.0


def read_provenance(reply: str, user_turn: str, snap: dict = None,
                    session_id: str = None, log: bool = True) -> dict:
    """The honest internal read for one reply: mirror terms, verdict, the unproven
    grounding hint, and the cue (empty unless strongly mirror-dominant).
    Fail-safe: a neutral read, verdict 'not established', cue ''."""
    out = {"mirror": 0.0, "semantic": 0.0, "copy_rate": 0.0,
           "grounding_hint": 0.0, "verdict": UNSET, "cue": ""}
    try:
        out.update(mirror_read(reply, user_turn))
        out["grounding_hint"] = _grounding_hint(reply, snap or {})
        out["verdict"] = verdict_for(out["mirror"])
        out["cue"] = honesty_cue(out["mirror"])
        if log:
            try:
                with open(_LOG, "a") as fh:
                    fh.write(json.dumps({
                        "ts": round(time.time(), 3), "session": (session_id or "")[:8],
                        "verdict": out["verdict"], "mirror": round(out["mirror"], 3),
                        "semantic": round(out["semantic"], 3),
                        "copy_rate": round(out["copy_rate"], 3),
                        "grounding_hint_UNPROVEN": round(out["grounding_hint"], 3),
                        "cue_fired": bool(out["cue"]),
                    }) + "\n")
            except Exception:
                pass
        return out
    except Exception:
        return out
