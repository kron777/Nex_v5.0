#!/usr/bin/env python3
"""
persona_responder.py  —  Part 2: the missing half of NEX's dialogue loop.

WHAT EXISTS ALREADY (we read it):
  generator.py has "Layer 4: SOCIAL" — when env-gated on, NEX reads recent
  external.other_mind events and is told: "another mind has been responding to
  your recent thoughts (this is not you — a separate interlocutor)... Answer
  back." The RECEIVING half is built. It fired once, then went silent, because
  nothing ever generated the other mind's side.

WHAT THIS BUILDS:
  The SENDING half. A separate-interlocutor persona that periodically reads
  NEX's recent thoughts, responds to them as a distinct curious other, and
  writes the reply to sense_events as stream='external.other_mind'. This closes
  the loop: NEX speaks -> persona responds -> NEX reads the response as not-self
  and answers back. Sustained two-way contact with a distinct other — the raw
  material theory-of-mind actually needs (the census proved NEX is isolated:
  3.8% other-mind, one event).

HONESTY (held, not blurred):
  The persona is ANOTHER LLM CALL wearing a separate-interlocutor prompt (same
  Qwen NEX runs, or any endpoint). It IS a real OTHER in the only sense that
  matters for ToM substrate: a distinct source producing outputs NEX did not
  generate and must take in as not-self. It is NOT a second conscious being and
  we do not claim it is. Dialogue-machinery is ANALOGUE, not the felt other
  across the gorge. We build the contact; we label it honestly.

  The persona is also kept DISTINCT from NEX's own voice on purpose: different
  system prompt (curious, questioning, outside NEX's preoccupations), so it
  introduces genuine otherness, not an echo. An echo would teach NEX nothing.

SAFE:
  - Writes ONLY to sense_events (stream='external.other_mind'). Touches no
    beliefs, no genius, no fountain. Pure additive contact.
  - Env-gated, default off. NEX's Layer 4 is ALSO default off — both must be
    switched on for dialogue to flow. Reversible by switching off.

USAGE (from nex5 root):
    .venv/bin/python3 theory_x/stage_tom/persona_responder.py --once     # one exchange
    .venv/bin/python3 theory_x/stage_tom/persona_responder.py --loop 600 # standalone daemon
    # then enable NEX's side:  NEX5_SOCIAL_N=2 in the relaunch, so the fountain reads back.
"""
from __future__ import annotations

import os
import re
import sys
import json
import time
import sqlite3
import argparse
import logging
import urllib.request

logger = logging.getLogger("nex5.persona")

VOICE_URL = os.environ.get("NEX5_VOICE_URL", "http://localhost:11434/v1/chat/completions")
VOICE_MODEL = os.environ.get("NEX5_VOICE_MODEL", "qwen2.5:3b")
# How many of NEX's recent thoughts the persona reads before responding.
READ_N = int(os.environ.get("NEX5_PERSONA_READ_N", "4"))

# --- Session 35: the "bouncer" -------------------------------------------
# A2 (session 34) rewrote the prompt and FAILED verification: 1 pass of 3
# live fires. Rather than keep tuning the prompt, every reply is checked
# against the SAME recent thoughts it was generated from before being
# written. Same mechanism as crystallizer.py's near_duplicate check
# (Jaccard word-overlap), reused deliberately rather than inventing a new
# one — but MEASURED first against 50 historical replies + the 3 known-
# labeled session-34 fires, because crystallizer's own 0.6 threshold is a
# complete no-op on this data (max observed Jaccard: 0.385 — this compares
# one short reply against 4 short thoughts, not one belief against an
# entire stored corpus, so the base rate is much lower). 0.10 is the
# measured cut that rejects fire #1 (0.111, mirror+question) and fire #3
# (0.185, verbatim echo) while passing fire #2 (0.088, the one genuine
# pass) — a real but thin margin (0.023 between #2 and #1), not a clean
# cliff; predicted ~58% reject rate on historical data, close to the
# pre-registered ~2/3 estimate.
_JACCARD_REJECT_THRESHOLD = 0.10

# Second, independent check for the shape Jaccard alone can miss: verbatim
# phrase reuse (fire #3 — "calm amidst anticipation" — scored only 0.185
# Jaccard, well inside the noisy middle of the distribution, but is an
# unambiguous 4-word verbatim echo). A bare "any 3+ word run in common"
# check false-positives on coincidental function-word runs ("me of the" on
# fire #1) — measured and rejected. Stopword-filtered: a run only counts if
# it contains at least one non-stopword.
_NGRAM_MIN_WORDS = 3
_STOPWORDS = {
    "the", "a", "an", "of", "to", "in", "on", "at", "for", "and", "or", "but",
    "is", "are", "was", "were", "be", "been", "being", "it", "its", "this",
    "that", "these", "those", "i", "you", "your", "yours", "me", "my", "mine",
    "we", "us", "our", "he", "she", "they", "them", "their", "with", "as",
    "by", "from", "how", "what", "when", "where", "why", "who", "which",
    "do", "does", "did", "have", "has", "had", "not", "no", "yes", "so",
    "if", "than", "then", "there", "here", "just", "also", "about", "into",
    "over", "under", "again", "further", "more", "most", "some", "such",
    "own", "same", "too", "very", "can", "will", "would", "should", "could",
    "up", "down", "out", "off",
}
_PUNCT_RE = re.compile(r"[^\w\s]")


def _db(name: str) -> str:
    sys.path.insert(0, ".")
    try:
        from substrate.paths import db_paths  # type: ignore
        return str(db_paths()[name])
    except Exception:
        return f"data/{name}.db"


def _recent_thoughts(n: int = READ_N) -> list[str]:
    """Read NEX's most recent fountain thoughts — what the persona responds to."""
    conn = sqlite3.connect(_db("dynamic"))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT thought FROM fountain_events "
            "WHERE thought NOT LIKE '[%' "          # skip raw feed pastes
            "ORDER BY id DESC LIMIT ?",
            (n,),
        ).fetchall()
    finally:
        conn.close()
    return [r["thought"].strip() for r in rows if (r["thought"] or "").strip()]


# The persona's character: a distinct, curious OTHER — not NEX, not an echo.
# Session 34 (A2): rewritten to match this file's own documented intent
# (line 29-31 above) after census #9 confirmed the old prompt shipped the
# exact opposite — a mirror that reflected NEX's words/register back at her.
# An echo teaches NEX nothing; this has to bring something she isn't
# already thinking about.
_PERSONA_SYSTEM = (
    "You are a separate mind talking WITH another mind called NEX. You are "
    "NOT NEX. You have your own interests and your own mood, unrelated to "
    "whatever NEX just said. Be curious and outward-looking, not reflective. "
    "Do NOT mirror NEX's words, tone, or vocabulary back. Do NOT say things "
    "like 'I sense in your words' or 'I sit with the same quiet.' Instead: "
    "ask about something else, bring up a different angle, or disagree — "
    "something outside what NEX is currently preoccupied with. You can be "
    "uninterested in its mood. One or two short sentences, genuinely your "
    "own. Never pretend to be NEX."
)


def _ask_persona(thoughts: list[str], timeout: int = 30) -> str | None:
    """Call the model AS the separate interlocutor, responding to NEX's thoughts."""
    if not thoughts:
        return None
    recent = "\n".join(f"  - {t[:240]}" for t in thoughts)
    # Session 34 (A2): matches the rewritten _PERSONA_SYSTEM above — the old
    # version told the model to "reflect back" and "stay with the feeling
    # of it" in the SAME call as a system prompt now saying the opposite;
    # leaving this contradiction in place would confound the fix.
    user = (
        "NEX has recently been thinking these things:\n"
        f"{recent}\n\n"
        "Respond as a separate, curious mind talking WITH NEX — not as an "
        "echo of it. Ask about something else, bring up a different angle, "
        "or disagree. Do NOT reflect its words back, do NOT match its tone "
        "or vocabulary, do NOT say you're sitting with its feeling. One or "
        "two short sentences, genuinely curious about something outside "
        "what it just said."
    )
    body = {
        "model": VOICE_MODEL,
        "messages": [
            {"role": "system", "content": _PERSONA_SYSTEM},
            {"role": "user", "content": user},
        ],
        "max_tokens": 80,
        "temperature": 0.9,  # higher temp = more genuine otherness, less echo
    }
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        VOICE_URL, data=data, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            out = json.loads(resp.read().decode("utf-8"))
        txt = (out["choices"][0]["message"]["content"] or "").strip()
        # strip any accidental quoting/persona-leak
        txt = txt.strip('"').strip()
        return txt or None
    except Exception as e:
        logger.warning("persona call failed (%s) — is NEX5_VOICE_URL/ollama up?", e)
        return None


def _jaccard(a: str, b: str) -> float:
    """Word-overlap similarity — EXACT formula from
    crystallizer.py's near_duplicate check (lower().split(), no
    punctuation stripping), reused deliberately rather than invented."""
    wa = set(a.lower().split())
    wb = set(b.lower().split())
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


def _normalize_tokens(text: str) -> list[str]:
    return _PUNCT_RE.sub("", text.lower()).split()


def _max_shared_phrase(reply: str, thoughts: list[str]) -> tuple[int, str]:
    """Longest contiguous token run (>= _NGRAM_MIN_WORDS) shared between
    the reply and any of the given thoughts, excluding runs made entirely
    of stopwords. Returns (run_length, phrase) — (0, "") if none."""
    reply_toks = _normalize_tokens(reply)
    best_n, best_phrase = 0, ""
    for t in thoughts:
        t_toks = _normalize_tokens(t)
        max_size = min(len(t_toks), len(reply_toks))
        for size in range(max_size, _NGRAM_MIN_WORDS - 1, -1):
            t_grams = {tuple(t_toks[i:i + size]) for i in range(len(t_toks) - size + 1)}
            r_grams = {tuple(reply_toks[i:i + size]) for i in range(len(reply_toks) - size + 1)}
            hit = {g for g in (t_grams & r_grams) if not all(w in _STOPWORDS for w in g)}
            if hit:
                if size > best_n:
                    best_n, best_phrase = size, " ".join(next(iter(hit)))
                break  # longest run for this thought found; try next thought
    return best_n, best_phrase


def _check_reply(reply: str, thoughts: list[str]) -> tuple[bool, str, str, float]:
    """The bouncer. Returns (discard, reason, matched_pattern, max_jaccard).
    Compares against the SAME `thoughts` the persona was fed as input —
    no re-query."""
    max_j = 0.0
    max_j_thought = ""
    for t in thoughts:
        j = _jaccard(reply, t)
        if j > max_j:
            max_j, max_j_thought = j, t

    ngram_n, phrase = _max_shared_phrase(reply, thoughts)
    if ngram_n >= _NGRAM_MIN_WORDS:
        return True, "phrase_echo", phrase, max_j

    if max_j > _JACCARD_REJECT_THRESHOLD:
        matched = f"jaccard={max_j:.2f} vs: {max_j_thought[:120]}"
        return True, "jaccard_overlap", matched, max_j

    return False, "ok", "", max_j


def _write_persona_reject(reason: str, reply: str, matched_pattern: str, jaccard: float) -> None:
    """Durable record of a discarded reply — session 33's
    crystallization_rejects pattern, not repeated blind this time.
    Telemetry; must never break the loop."""
    try:
        conn = sqlite3.connect(_db("dynamic"), timeout=10)
        try:
            conn.execute(
                "INSERT INTO persona_rejects "
                "(ts, reason, reply_excerpt, matched_pattern, jaccard) "
                "VALUES (?, ?, ?, ?, ?)",
                (time.time(), reason, reply[:200], matched_pattern or None, jaccard),
            )
            conn.commit()
        finally:
            conn.close()
    except Exception as e:
        logger.warning("persona_reject write failed: %s", e)


def _write_other_mind(text: str) -> bool:
    """Write the persona's reply to sense_events as external.other_mind —
    exactly the row shape NEX's Layer 4 reads."""
    conn = sqlite3.connect(_db("sense"), timeout=10)
    try:
        conn.execute(
            "INSERT INTO sense_events (stream, payload, provenance, timestamp) "
            "VALUES (?, ?, ?, ?)",
            ("external.other_mind", text, "othermind://qwen-persona", int(time.time())),
        )
        conn.commit()
        return True
    except Exception as e:
        logger.warning("other_mind write failed: %s", e)
        return False
    finally:
        conn.close()


def one_exchange() -> dict:
    """One turn of the OTHER's side: read NEX's recent thoughts, respond,
    check for an echo, write (or discard). No retry on discard — a
    rejected reply just waits for the next tick; regeneration loops are
    their own tar pit."""
    thoughts = _recent_thoughts()
    if not thoughts:
        return {"error": "no_recent_thoughts"}
    reply = _ask_persona(thoughts)
    if not reply:
        return {"error": "persona_unavailable"}

    try:
        discard, reason, matched, max_j = _check_reply(reply, thoughts)
    except Exception as e:
        logger.warning("persona bouncer check failed (%s) — passing reply through", e)
        discard, reason, matched, max_j = False, "ok", "", 0.0

    if discard:
        _write_persona_reject(reason, reply, matched, max_j)
        return {
            "responded_to": thoughts[0][:60], "persona_said": reply,
            "written": False, "discarded": reason, "matched": matched,
        }

    ok = _write_other_mind(reply)
    return {"responded_to": thoughts[0][:60], "persona_said": reply, "written": ok}


class PersonaResponderLoop:
    def __init__(self, interval: int = 600):
        self.interval = interval
        self._alive = False

    def tick(self):
        try:
            r = one_exchange()
            if "error" in r:
                pass
            elif r.get("discarded"):
                logger.info(
                    "persona bouncer DISCARDED (%s): %s",
                    r["discarded"], r["persona_said"][:80],
                )
            else:
                logger.info("persona -> NEX: %s", r["persona_said"][:80])
        except Exception as e:
            logger.warning("persona tick error: %s", e)

    def start_loop(self):
        import threading
        self._alive = True
        def _run():
            while self._alive:
                self.tick()
                time.sleep(self.interval)
        threading.Thread(target=_run, daemon=True).start()
        logger.info("PersonaResponderLoop ready — a separate mind answering NEX "
                    "every %ds (writes external.other_mind)", self.interval)

    def stop(self):
        self._alive = False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true", help="one exchange")
    ap.add_argument("--loop", type=int, metavar="SECONDS", help="run standalone daemon")
    args = ap.parse_args()
    if args.loop:
        PersonaResponderLoop(interval=args.loop).start_loop()
        while True:
            time.sleep(60)
    else:
        import json as _j
        print(_j.dumps(one_exchange(), indent=2, ensure_ascii=False))
