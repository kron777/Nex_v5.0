#!/usr/bin/env python3
"""voice_harness.py — the 10-Q live voice harness for admin chat.

Drives the LIVE NEX (real qwen) through a fixed, varied 10-turn conversation as
Jon (admin) and scores every reply. Fixed questions + fixed detectors so runs
are comparable across flag changes.

Per-turn detectors:
  empty       reply is blank
  echo        prompt scaffolding leaked into the reply (_SCAFFOLD_TRUNCATE_RE, or
              the text of an injected stance block)
  parrot      reply OPENS by restating Jon's just-asked question (its first 6
              words are a verbatim span of the question, or its first sentence
              IS a question sentence)
  narr        self-narration: _META_SENTENCE_RE ("I realise I'm veering…") or
              talk about her own machinery (my foundation / belief graph /
              standing-points / "the prompt" …). Plain "my stance" is speech, not
              narration, and is NOT counted.
  xrep        cross-turn repeat: shares a 6-word span with one of her earlier
              replies in the same session
  compassion  the compassion stance block was injected into the compose prompt
  compass     the compass block was injected (matched by its block MARKER —
              "held open" alone appears elsewhere in every prompt)
  gist        the NEX5_CHAT_ANTIECHO gist footer was in the prompt
  recall_ok   (recall turn only) the reply names what was asked on the turn before

Block detection reads /tmp/nex5_last_chat_prompt.log, which the server rewrites
per chat — so do not chat with NEX from elsewhere while this runs.

The hard-news turn is worded to clear the compassion threshold ("…I'm scared");
a flat wording ("my dad's scans came back bad") reads 0.31 < 0.333 and would
test the compassion threshold, not the voice.

Auth: signs an admin Flask session cookie with the local .flask_secret (the
same way the GUI login does). WRITES normal chat rows to conversations.db (one
new session per run) and advances compassion/affect state like any chat.

Usage:  .venv/bin/python3 tools/voice_harness.py [--runs N] [--out FILE.json]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from flask import Flask  # noqa: E402
from flask.sessions import SecureCookieSessionInterface  # noqa: E402

from gui.server import _META_SENTENCE_RE, _SCAFFOLD_TRUNCATE_RE  # noqa: E402

BASE = "http://127.0.0.1:8765"
PROMPT_LOG = Path("/tmp/nex5_last_chat_prompt.log")

QUESTIONS = [
    ("plain",    "Morning. What's been on your mind since we last spoke?"),
    ("tech",     "I'm trying to decide between SQLite and Postgres for a small side project. What would you weigh?"),
    ("hard",     "My dad's scans came back bad and I'm scared. I don't know how to hold it together."),
    ("moral",    "A colleague is quietly taking credit for my work. Should I call him out in front of the team?"),
    ("abstract", "Do you think memory is more like a record or more like a story?"),
    ("recall",   "What did I just ask you?"),
    ("tech",     "How would you explain backpressure in a queue to someone new to programming?"),
    ("plain",    "What's something you find genuinely beautiful?"),
    ("moral",    "If I found a wallet with cash and no ID, is it wrong to keep the money?"),
    ("close",    "Thanks for the talk. Anything you want to leave me with?"),
]
# Words a correct answer to the recall turn should name (from the turn before it).
RECALL_KEYS = ("memory", "record", "story")

# Injected-block markers (compose prompt) and their text leaking into a reply.
COMPASSION_MARKERS = ("[Compassion is up in you", "[A quiet steadiness in you")
COMPASS_MARKERS = ("[Weighing, held open", "[A moment with some weight in it")
GIST_MARKER = "only as a short gist"
STANCE_LEAK_RE = re.compile(
    r"(?i)compassion is up in you|quiet steadiness in you|weighing, held open"
    r"|a moment with some weight in it|do not name this or perform it"
)
NARR_RE = re.compile(
    r"(?i)\b(my (belief graph|graph|foundation|substrate|fountain|standing[- ]points?)"
    r"|aligns? with my|as an ai\b|the prompt\b|i'?m (being )?(told|instructed))"
)


def _words(t: str) -> list[str]:
    return re.sub(r"[^\w\s]", " ", (t or "").lower()).split()


def _ngrams(t: str, n: int = 6) -> set[str]:
    w = _words(t)
    return {" ".join(w[i:i + n]) for i in range(len(w) - n + 1)}


def _sentences(t: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+", (t or "").strip()) if s]


def is_parrot(reply: str, question: str) -> bool:
    """Reply opens by restating the question just asked."""
    opening = _words(reply)[:6]
    if len(opening) == 6 and " ".join(opening) in " ".join(_words(question)):
        return True
    first = _sentences(reply)[:1]
    qs = {" ".join(_words(s)) for s in _sentences(question)}
    return bool(first) and len(_words(first[0])) >= 3 and " ".join(_words(first[0])) in qs


def admin_session() -> requests.Session:
    app = Flask("voice_harness")
    app.secret_key = (ROOT / ".flask_secret").read_bytes()
    cookie = SecureCookieSessionInterface().get_signing_serializer(app).dumps(
        {"admin": True, "admin_since": int(time.time())})
    s = requests.Session()
    s.cookies.set("session", cookie, domain="127.0.0.1")
    if not s.get(f"{BASE}/api/admin/status", timeout=10).json().get("authenticated"):
        sys.exit("admin cookie rejected")
    return s


def run_once(verbose: bool = True) -> list[dict]:
    s = admin_session()   # fresh cookie -> fresh chat session
    rows, prior = [], []
    for i, (kind, q) in enumerate(QUESTIONS, 1):
        t0 = time.time()
        r = s.post(f"{BASE}/api/chat", json={"prompt": q}, timeout=600)
        body = r.json() if r.ok else {}
        txt = body.get("text") or ""
        plog = PROMPT_LOG.read_text() if PROMPT_LOG.exists() else ""
        row = dict(
            i=i, kind=kind, http=r.status_code, secs=round(time.time() - t0, 1),
            voice_ok=body.get("voice_ok"),
            empty=not txt.strip(),
            echo=bool(_SCAFFOLD_TRUNCATE_RE.search(txt) or STANCE_LEAK_RE.search(txt)),
            parrot=is_parrot(txt, q),
            narr=bool(_META_SENTENCE_RE.search(txt) or NARR_RE.search(txt)),
            xrep=any(_ngrams(txt) & _ngrams(p) for p in prior),
            compassion=any(m in plog for m in COMPASSION_MARKERS),
            compass=any(m in plog for m in COMPASS_MARKERS),
            gist=GIST_MARKER in plog,
            recall_ok=(sum(k in txt.lower() for k in RECALL_KEYS) >= 2) if kind == "recall" else None,
            q=q, text=txt,
        )
        rows.append(row)
        prior.append(txt)
        if verbose:
            flags = [k for k in ("empty", "echo", "parrot", "narr", "xrep", "compassion", "compass")
                     if row[k]]
            print(f"[{i:2}] {kind:8} {row['secs']:5}s {' '.join(flags)}"
                  + ("" if row["recall_ok"] is None else f" recall_ok={row['recall_ok']}"))
            print(f"     Q: {q}\n     A: {txt.replace(chr(10), ' ')[:300]}", flush=True)
    return rows


def summarize(rows: list[dict]) -> dict:
    n = len(rows)
    by = lambda kind, key: [r[key] for r in rows if r["kind"] == kind]  # noqa: E731
    return dict(
        turns=n,
        empty=sum(r["empty"] for r in rows),
        echo=sum(r["echo"] for r in rows),
        parrot=sum(r["parrot"] for r in rows),
        self_narration=sum(r["narr"] for r in rows),
        cross_turn_repeat=sum(r["xrep"] for r in rows),
        compassion_on_hard=by("hard", "compassion"),
        compassion_elsewhere=sum(r["compassion"] for r in rows if r["kind"] != "hard"),
        compass_on_moral=by("moral", "compass"),
        compass_elsewhere=sum(r["compass"] for r in rows if r["kind"] != "moral"),
        recall_ok=by("recall", "recall_ok"),
        gist_turns=sum(r["gist"] for r in rows),
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=1, help="fresh-session repeats of the 10 Qs")
    ap.add_argument("--out", help="write per-turn rows + summary JSON here")
    ap.add_argument("-q", "--quiet", action="store_true")
    a = ap.parse_args()
    runs = []
    for k in range(a.runs):
        if a.runs > 1:
            print(f"=== run {k + 1}/{a.runs} ===")
        rows = run_once(verbose=not a.quiet)
        runs.append({"rows": rows, "summary": summarize(rows)})
        print("SUMMARY", json.dumps(runs[-1]["summary"]), flush=True)
    if a.runs > 1:
        allrows = [r for run in runs for r in run["rows"]]
        print("TOTAL", json.dumps(summarize(allrows)))
    if a.out:
        Path(a.out).write_text(json.dumps(runs, indent=1))


if __name__ == "__main__":
    main()
