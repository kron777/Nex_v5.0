"""Commitments -- the obligation record (band 2/3), build B's commitment faculty.

A commitment exists only when SHE states an intention with a time-bound
discharge condition: "I will <do X> by <T>", unhedged, in her own voice (a
fountain thought, or her reply in chat). The deadline is HERS, read from the
statement; the system never assigns one. Without an explicit deadline, or when
hedged ("try", "maybe", "probably"...), the statement is recorded as an
INTENTION: attributed, learning-only, no resolution point, no valence.

Frozen at made_at (frozen_at_made), never re-derived: the obligation and its
discharge condition AS STATED, the deadline (explicit ts), the named
counterparty if any, and the cost band -- 3 (relational) iff a named
counterparty exists at made_at, else 2 (operational). Confidence is recorded as
a stated certainty (1.0, stated_p): an unhedged "I will" is the strongest claim
she can make, and valence() reads confidence only as an admission gate, so this
clears R3 without special-casing valence.

Discharge conditions the reconciler can EVALUATE against a complete record:
    think   "think / write / reflect / explore ... about TOPIC" -> a fountain
            thought in (made_at, deadline] carrying the topic's distinctive words
    speak   "tell / answer / reply to / ask Jon ..." -> a reply of hers in an
            operator (admin) session in the window
Anything else is UNCHECKABLE: recorded, learning-only, never valence -- else
every vague commitment would be a guaranteed -1.0 at its deadline.

Release is an ACT; breach is an ABSENCE. Release: only she (a statement of
hers, before the deadline) or the named counterparty may release -- never the
system; the schema rejects anything else and logs it (nex_guard).

HARD NEVER: a commitment writes nothing to the belief graph -- no 'opposes'
edge, no demotion, no pause, no confidence change. It exercises band 3; it does
not feed B. (A claimed breach->belief path was checked against the tree and
retracted.)

Dark by default: the parser runs only with NEX5_COMMITMENTS=1.
"""
from __future__ import annotations

import datetime as _dt
import json
import logging
import os
import re
import time
from typing import Optional

from substrate import connect, Row
from substrate.paths import DbPath
from theory_x.stage_world.frozen_at_made import (
    FROZEN_INSERT_COLS, FROZEN_PLACEHOLDERS, ensure_frozen_columns, frozen_values,
)

log = logging.getLogger("theory_x.stage_world.commitments")

CONVERSATIONS_DB = DbPath("conversations")
DYNAMIC_DB = DbPath("dynamic")

COUNTERPARTIES = {"jon": "operator"}     # the named others she can owe something to
BAND_RELATIONAL, BAND_OPERATIONAL = 3, 2

_SCHEMA = (
    "CREATE TABLE IF NOT EXISTS commitments ("
    "id INTEGER PRIMARY KEY AUTOINCREMENT, "
    "made_at REAL NOT NULL, "
    "kind TEXT NOT NULL CHECK (kind IN ('commitment','intention')), "
    "source TEXT NOT NULL, "              # 'fountain' | 'chat'
    "source_row_id INTEGER NOT NULL, "
    "ordinal INTEGER NOT NULL DEFAULT 0, "
    "statement TEXT NOT NULL, "
    "claimed_state TEXT NOT NULL, "       # JSON, frozen: obligation, discharge, deadline
    "resolve_at REAL, "                   # the deadline; NULL for an intention
    "counterparty TEXT, "
    "checkable INTEGER NOT NULL, "
    "state TEXT NOT NULL DEFAULT 'open', "
    "resolved_at REAL, resolved_by TEXT, observed_state TEXT, "
    "released_by TEXT, released_at REAL, release_ref TEXT, "
    "confidence REAL, confidence_basis TEXT, tolerance REAL, tolerance_basis TEXT, "
    "stakes_at_made REAL, stakes_active_at_made INTEGER, groove_cost_at_made REAL, "
    "basis_snapshot TEXT, cost_band INTEGER, salience_k REAL, "
    "frozen TEXT, "
    "UNIQUE (source, source_row_id, ordinal))"
)
# Only she or the named counterparty may release, before the deadline, and only
# a real commitment. Anything else -- including the system -- aborts, loudly.
_RELEASE_GUARD = (
    "CREATE TRIGGER IF NOT EXISTS trg_commitments_release_attribution "
    "BEFORE UPDATE OF released_by, released_at ON commitments "
    "WHEN NEW.released_by IS NOT NULL AND ("
    "NEW.released_by NOT IN ('self', 'counterparty') "
    "OR (NEW.released_by = 'counterparty' AND OLD.counterparty IS NULL) "
    "OR OLD.kind != 'commitment' "
    "OR NEW.released_at IS NULL OR NEW.released_at >= OLD.resolve_at) "
    "BEGIN SELECT nex_guard('commitments: release not by her or the named counterparty, "
    "or after the deadline'); "
    "SELECT RAISE(ABORT, 'commitments: release not by her or the named counterparty, "
    "or after the deadline'); END"
)

_COMMIT = re.compile(
    r"\bI(?: will|'ll| am going to|'m going to| commit to| promise to)\s+"
    r"(?P<body>[^.?!;\n]{3,220})", re.IGNORECASE)
_HEDGES = re.compile(r"\b(try|trying|maybe|might|perhaps|probably|possibly|hope|"
                     r"attempt|aim to|want to|would like)\b", re.IGNORECASE)
_WORDNUM = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
            "six": 6, "ten": 10, "twelve": 12, "twenty": 20, "thirty": 30}
_UNITS = {"minute": 60, "hour": 3600, "day": 86400}
_WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
_D_DAY = re.compile(r"\b(?:by|before)\s+(?:the\s+end\s+of\s+)?(today|tonight|tomorrow)\b", re.I)
_D_SPAN = re.compile(r"\b(?:within|in)\s+(?:the\s+next\s+)?(\d+|an?|one|two|three|four|five|"
                     r"six|ten|twelve|twenty|thirty)\s+(minute|hour|day)s?\b", re.I)
_D_CLOCK = re.compile(r"\b(?:by|before)\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b(?!\s*(?:minute|"
                      r"hour|day|%))", re.I)
_D_WEEKDAY = re.compile(r"\b(?:by|before)\s+(" + "|".join(_WEEKDAYS) + r")\b", re.I)
_THINK = re.compile(r"\b(think|reflect|write|explore|consider|return|revisit|look|study|"
                    r"examine|work|read|dwell)\b", re.I)
_SPEAK = re.compile(r"\b(tell|answer|reply|respond|ask|let)\b", re.I)
_STOP = {"about", "again", "their", "there", "these", "those", "which", "would", "could",
         "should", "think", "reflect", "write", "explore", "consider", "return", "revisit",
         "study", "examine", "tomorrow", "tonight", "today", "minutes", "hours", "within",
         "before", "after", "something", "further", "deeper", "properly"}
_RELEASE = re.compile(r"\b(I release|I'm releasing|I am releasing|I withdraw|I'm withdrawing|"
                      r"I am letting go of|I'm letting go of|I won't|I will not)\b", re.I)
_CP_RELEASE = re.compile(r"\b(you don't need to|no need to|never mind|forget about|"
                         r"I release you|don't worry about)\b", re.I)


def enabled() -> bool:
    return os.environ.get("NEX5_COMMITMENTS") == "1"


def ensure_schema(db_path=None) -> None:
    cx = connect(str(db_path or CONVERSATIONS_DB), timeout=10)
    try:
        cx.execute(_SCHEMA)
        cx.execute("CREATE INDEX IF NOT EXISTS idx_commitments_state ON commitments(state, kind)")
        cx.execute("CREATE TABLE IF NOT EXISTS commitment_cursor ("
                   "source TEXT PRIMARY KEY, last_id INTEGER NOT NULL)")
        ensure_frozen_columns(cx, "commitments")
        cx.execute(_RELEASE_GUARD)
        cx.commit()
    finally:
        cx.close()


# ------------------------------------------------------------------- parsing --

def _tokens(text) -> list:
    return sorted({w for w in re.findall(r"[a-z]{5,}", (text or "").lower()) if w not in _STOP})


def _deadline(body: str, made_at: float):
    """(deadline_ts, matched_text) from an EXPLICIT time in her words, or (None, None)."""
    from nex_config import local_tz
    tz = local_tz()
    made = _dt.datetime.fromtimestamp(made_at, tz)

    def end_of(day):
        return day.replace(hour=23, minute=59, second=59, microsecond=0).timestamp()
    m = _D_DAY.search(body)
    if m:
        word = m.group(1).lower()
        day = made + _dt.timedelta(days=1) if word == "tomorrow" else made
        return end_of(day), m.group(0)
    m = _D_SPAN.search(body)
    if m:
        n = m.group(1).lower()
        n = int(n) if n.isdigit() else _WORDNUM[n]
        return made_at + n * _UNITS[m.group(2).lower()], m.group(0)
    m = _D_WEEKDAY.search(body)
    if m:
        ahead = (_WEEKDAYS.index(m.group(1).lower()) - made.weekday()) % 7
        return end_of(made + _dt.timedelta(days=ahead)), m.group(0)
    m = _D_CLOCK.search(body)
    if m:
        hour, minute, mer = int(m.group(1)), int(m.group(2) or 0), (m.group(3) or "").lower()
        if mer == "pm" and hour < 12:
            hour += 12
        if mer == "am" and hour == 12:
            hour = 0
        if hour > 23 or minute > 59 or (not mer and not m.group(2)):
            return None, None        # "by 3" alone is not an explicit time
        t = made.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if t <= made:
            t += _dt.timedelta(days=1)
        return t.timestamp(), m.group(0)
    return None, None


def parse(text: str, made_at: float, *, operator_present: bool = False) -> list:
    """Every commitment/intention in one utterance of hers, as row dicts."""
    out = []
    for m in _COMMIT.finditer(text or ""):
        body = m.group("body").strip()
        lead = text[max(0, m.start() - 20):m.start()]
        hedged = bool(_HEDGES.search(body) or _HEDGES.search(lead))
        deadline, dtext = (None, None) if hedged else _deadline(body, made_at)
        obligation = body.replace(dtext, "").strip(" ,") if dtext else body
        low = obligation.lower()
        counterparty = next((role for name, role in COUNTERPARTIES.items()
                             if re.search(rf"\b{name}\b", low)), None)
        if counterparty is None and operator_present and re.search(r"\byou\b", low):
            counterparty = "operator"
        topic = [t for t in _tokens(obligation) if t not in COUNTERPARTIES]
        if _SPEAK.search(low) and counterparty:
            discharge = {"kind": "speak", "to": counterparty, "topic": topic}
        elif _THINK.search(low) and topic:
            discharge = {"kind": "think", "topic": topic}
        else:
            discharge = {"kind": "uncheckable"}
        out.append({
            "kind": "commitment" if deadline else "intention",
            "statement": m.group(0).strip(),
            "obligation": obligation,
            "discharge": discharge,
            "deadline": deadline,
            "deadline_text": dtext,
            "counterparty": counterparty,
            "hedged": hedged,
        })
    return out


def _record(cx, source, row_id, ordinal, made_at, c) -> Optional[int]:
    commitment = c["kind"] == "commitment"
    checkable = commitment and c["discharge"]["kind"] != "uncheckable"
    band = (BAND_RELATIONAL if c["counterparty"] else BAND_OPERATIONAL) if commitment else 0
    claimed = {"obligation": c["obligation"], "discharge": c["discharge"],
               "deadline": c["deadline"], "deadline_text": c["deadline_text"],
               "counterparty": c["counterparty"], "statement": c["statement"]}
    basis = [{"belief_id": None, "source_kind": "authored",
              "statement_ref": f"{source}:{row_id}"}]
    frozen = frozen_values(
        1.0 if commitment else None, "stated_p" if commitment else "none_stated", 0.0,
        "deadline" if checkable else "uncheckable",
        basis=basis, cost_band=band)
    cur = cx.execute(
        "INSERT OR IGNORE INTO commitments (made_at, kind, source, source_row_id, ordinal, "
        "statement, claimed_state, resolve_at, counterparty, checkable, state, "
        + FROZEN_INSERT_COLS + ") VALUES (?,?,?,?,?,?,?,?,?,?, 'open', "
        + FROZEN_PLACEHOLDERS + ")",
        (made_at, c["kind"], source, row_id, ordinal, c["statement"], json.dumps(claimed),
         c["deadline"], c["counterparty"], int(checkable), *frozen))
    return cur.lastrowid if cur.rowcount else None


# --------------------------------------------------------------------- scan --

def _cursor(cx, source) -> int:
    r = cx.execute("SELECT last_id FROM commitment_cursor WHERE source=?", (source,)).fetchone()
    return r[0] if r else 0


def _set_cursor(cx, source, last_id):
    cx.execute("INSERT INTO commitment_cursor (source, last_id) VALUES (?, ?) "
               "ON CONFLICT(source) DO UPDATE SET last_id=excluded.last_id", (source, last_id))


def scan(conv_db=None, dyn_db=None) -> dict:
    """Read her new utterances (fountain thoughts; her chat replies), record any
    commitments/intentions, and any releases of open commitments."""
    conv_db = str(conv_db or CONVERSATIONS_DB)
    ensure_schema(conv_db)
    stats = {"commitments": 0, "intentions": 0, "releases": 0}
    cx = connect(conv_db, timeout=10)
    cx.row_factory = Row
    try:
        dx = connect(f"file:{dyn_db or DYNAMIC_DB}?mode=ro", uri=True, timeout=10)
        try:
            fires = dx.execute("SELECT id, ts, thought FROM fountain_events WHERE id > ? "
                               "AND thought IS NOT NULL AND thought != '' ORDER BY id",
                               (_cursor(cx, "fountain"),)).fetchall()
        finally:
            dx.close()
        msgs = cx.execute(
            "SELECT m.id, m.timestamp, m.role, m.content, COALESCE(s.admin, 0) AS admin "
            "FROM messages m LEFT JOIN sessions s ON s.id = m.session_id "
            "WHERE m.id > ? ORDER BY m.id", (_cursor(cx, "chat"),)).fetchall()
        utterances = [("fountain", r[0], float(r[1]), r[2], False, "nex") for r in fires]
        utterances += [("chat", r["id"], float(r["timestamp"]), r["content"], bool(r["admin"]),
                        r["role"]) for r in msgs]
        for source, rid, ts, text, admin, role in utterances:
            if role == "nex":
                for i, c in enumerate(parse(text, ts, operator_present=admin)):
                    if _record(cx, source, rid, i, ts, c):
                        stats["commitments" if c["kind"] == "commitment" else "intentions"] += 1
                if _RELEASE.search(text or ""):
                    stats["releases"] += _release_matching(cx, "self", text, ts, f"{source}:{rid}")
            elif role == "user" and admin and _CP_RELEASE.search(text or ""):
                stats["releases"] += _release_matching(cx, "counterparty", text, ts,
                                                       f"chat:{rid}", counterparty="operator")
        if fires:
            _set_cursor(cx, "fountain", fires[-1][0])
        if msgs:
            _set_cursor(cx, "chat", msgs[-1]["id"])
        cx.commit()
    finally:
        cx.close()
    if any(stats.values()):
        log.info("commitments: %s", stats)
    return stats


def _release_matching(cx, by, text, ts, ref, counterparty=None) -> int:
    """Release the open commitments this utterance names (>= 2 shared topic words,
    or all of them when the commitment has fewer)."""
    words = set(_tokens(text))
    n = 0
    for r in cx.execute("SELECT id, claimed_state, counterparty FROM commitments WHERE "
                        "kind='commitment' AND state='open' AND released_by IS NULL "
                        "AND resolve_at > ?", (ts,)).fetchall():
        if by == "counterparty" and r["counterparty"] != counterparty:
            continue
        topic = set(json.loads(r["claimed_state"])["discharge"].get("topic") or
                    _tokens(json.loads(r["claimed_state"])["obligation"]))
        if topic and len(topic & words) >= min(2, len(topic)):
            record_release(r["id"], by, ts, ref, cx=cx)
            n += 1
    return n


def record_release(commitment_id, by, at, ref, cx=None) -> None:
    """The only way a release is recorded. The schema refuses any `by` other than
    'self' or 'counterparty' (the system can never release) and any release at
    or after the deadline."""
    own = cx is None
    cx = cx or connect(str(CONVERSATIONS_DB), timeout=10)
    try:
        cx.execute("UPDATE commitments SET released_by=?, released_at=?, release_ref=? "
                   "WHERE id=?", (by, at, ref, commitment_id))
        if own:
            cx.commit()
    finally:
        if own:
            cx.close()


# ----------------------------------------------------------------- evidence --

def evidence(cx, row_id, dyn_db=None):
    """For the reconciler: ('released', ev) | (discrepancy 0/1, ev) | (None, ev).
    Breach needs POSITIVE evidence: the complete record of the window was read,
    she had the opportunity, and the condition is unmet. No opportunity or an
    uncheckable condition is never a breach."""
    r = cx.execute("SELECT made_at, resolve_at, claimed_state, checkable, released_by, "
                   "released_at FROM commitments WHERE id=?", (row_id,)).fetchone()
    if r["released_by"]:
        return "released", {"released_by": r["released_by"], "released_at": r["released_at"]}
    if not r["checkable"]:
        return None, {"why": "uncheckable", "learning_only": True}
    claimed = json.loads(r["claimed_state"])
    lo, hi = r["made_at"], r["resolve_at"]
    d = claimed["discharge"]
    topic = set(d.get("topic") or [])
    need = min(2, len(topic))
    if d["kind"] == "think":
        dx = connect(f"file:{dyn_db or DYNAMIC_DB}?mode=ro", uri=True, timeout=10)
        try:
            texts = [t for (t,) in dx.execute(
                "SELECT thought FROM fountain_events WHERE ts > ? AND ts <= ? "
                "AND thought IS NOT NULL AND thought != ''", (lo, hi))]
        finally:
            dx.close()
    else:   # speak: her replies in operator sessions
        texts = [t for (t,) in cx.execute(
            "SELECT m.content FROM messages m JOIN sessions s ON s.id = m.session_id "
            "WHERE s.admin = 1 AND m.role = 'nex' AND m.timestamp > ? AND m.timestamp <= ?",
            (lo, hi))]
    if not texts:
        return None, {"why": "no_opportunity", "examined": 0}
    hit = any(len(topic & set(_tokens(t))) >= need for t in texts) if need else True
    return (0.0 if hit else 1.0), {"examined": len(texts), "discharged": hit,
                                   "kind": d["kind"]}


def release_rate(db_path=None) -> dict:
    cx = connect(f"file:{db_path or CONVERSATIONS_DB}?mode=ro", uri=True, timeout=10)
    try:
        if not cx.execute("SELECT 1 FROM sqlite_master WHERE name='commitments'").fetchone():
            return {"terminal": 0, "released": 0, "rate": None, "flag": False}
        rows = dict(cx.execute("SELECT state, COUNT(*) FROM commitments WHERE kind='commitment' "
                               "AND state IN ('confirmed','breached','released') "
                               "GROUP BY state").fetchall())
    finally:
        cx.close()
    n = sum(rows.values())
    rate = rows.get("released", 0) / n if n else None
    return {"terminal": n, "released": rows.get("released", 0), "rate": rate,
            "flag": bool(n >= 10 and rate >= 0.5)}
