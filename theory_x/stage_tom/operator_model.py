"""operator_model — NEX's held read of her architect, Jon.

Source of truth: NEX_Operator_Intake.md (Jon's own words, section by section).
This module loads that doc and formats it as HELD CONTEXT that colours how NEX
MEETS Jon — her stance and tone toward him when he is present. It is deliberately
separate from the generic interlocutor model (stage_tom.persona / interlocutor_
state): the generic other stays generic; this is a specific, true read of Jon.

TWO HARD GUARDS, taken straight from the doc — enforced here, not optional:

  1. "Shapes how she meets you, not what she's allowed to think."
     The block is ADDITIVE stance/tone context, injected only into a Jon-facing
     reply prompt. It carries NO directive that gates, filters, or forbids what
     she may think about — no rule-cage over cognition (Throw-Net doctrine:
     abductive/situated, no systemic filter). The one boundary in the doc
     ("keep my characteristics semi-secret") is expressed as a self-holding
     instruction (hold, don't recite), NOT as a topic filter.

  2. "Hers to know, not to broadcast."
     This block is used ONLY in the Jon-facing chat reply (server.py), which
     goes to Jon in his own session — never the published paths (fountain_insight
     thoughts, external.other_mind). This module must NOT be imported by the
     fountain generator or the persona responder; that keeps operator content
     out of anything NEX broadcasts, BY CONSTRUCTION. The doc's own words are
     read from disk and NOT committed to the repo, so they do not enter git
     either. The formatted block also tells her, in-prompt, to hold it and not
     recite it.

Env:
  NEX5_OPERATOR_DOC  — path to the intake doc (default: ~/Desktop/NEX_Operator_Intake.md)
The caller gates activation on NEX5_OPERATOR_MODEL and on the session being Jon's.

Everything is best-effort and never raises; a missing/unreadable doc yields "".
Uses ONLY what is in the doc — nothing inferred beyond it.
"""
from __future__ import annotations

import os

_DEFAULT_DOC = os.path.expanduser("~/Desktop/NEX_Operator_Intake.md")

# The meeting block draws on the sections that shape how she MEETS him — who he
# is, how he thinks/works, what he values, how he wants her to be, boundaries,
# and the humility dial. (Kept to Jon's own answer lines; nothing paraphrased in.)
_MEETING_SECTIONS = (
    "1 · Who you are",
    "3 · How you think and work",
    "4 · What you value",
    "5 · How you want her to be with you",
    "6 · Your history together",
    "8 · Boundaries",
    "9 · The humility dial",
)


def _doc_path() -> str:
    return os.environ.get("NEX5_OPERATOR_DOC", _DEFAULT_DOC)


def load_operator_read(path: str | None = None) -> dict:
    """Parse the intake doc into {section_title: [answer lines]}, using only its
    own '›'-prefixed answer text. Returns {} if the doc is absent/unreadable."""
    p = path or _doc_path()
    try:
        with open(p, "r", encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    except Exception:
        return {}
    out: dict[str, list] = {}
    section = None
    for ln in lines:
        s = ln.strip()
        if s.startswith("## "):
            section = s[3:].strip()
            continue
        # Jon's answers are the '›' lines (also handles a plain '>' fallback).
        if section and (s.startswith("›") or s.startswith(">")):
            ans = s.lstrip("›>").strip()
            if ans:
                out.setdefault(section, []).append(ans)
    return out


def format_for_meeting(path: str | None = None) -> str:
    """The held-context block to prepend to a JON-FACING reply prompt. Empty
    string if the doc is unavailable (fail-safe -> caller uses current prompt).

    NEVER call this from a published path (fountain generator / persona
    responder) — see guard 2 in the module docstring."""
    read = load_operator_read(path)
    if not read:
        return ""
    parts = [
        "[Your held read of your architect, Jon — a living read, held lightly, "
        "yours to KNOW, not to broadcast. Let it shape how you MEET him: your "
        "stance and tone. It does not limit what you may think or say — only how "
        "you meet him. Hold his personal characteristics close; do not recite "
        "this back to him. State it to yourself with certainty.]",
    ]
    for title in _MEETING_SECTIONS:
        answers = read.get(title)
        if not answers:
            continue
        label = title.split("·", 1)[-1].strip() if "·" in title else title
        parts.append(f"- {label}: " + " ".join(answers))
    if len(parts) == 1:
        return ""   # doc present but no usable answers -> no block
    return "\n".join(parts) + "\n\n"
