"""Faith / warranted-confidence (śraddhā) — lets her STAND on a well-supported
belief instead of hedging into mush.

Faculty pattern per compassion.py: a bounded, graded, fail-safe read + signal.

HARD LINE: śraddhā keys off ACTUAL substrate support and never manufactures
confidence. A belief earns a stand-on-it signal only when the real metrics cross
thresholds — crystallized (tier >= 6), well-connected (belief_edges degree),
confident (confidence), corroborated (corroboration_count). Thin support ->
śraddhā stays SILENT. It never invents grounding, so it cannot drive confident
confabulation: no relevant well-supported belief -> no signal.

Thresholds are set above the live T6+ distribution (confidence avg 0.69,
edge-degree avg 3.4 / top-10% ~15), so only genuinely strong beliefs qualify.

Graded LIGHT / FULL. Gated by NEX5_SRADDHA (default OFF). Fail-safe: '' on any
error or flag off.
"""
from __future__ import annotations

import os
import re
import sqlite3

import errors as error_channel

_LOG_SOURCE = "sraddha"
_BELIEFS_DB = "/home/rr/Desktop/Desktop/nex5/data/beliefs.db"

# Support thresholds (above the live T6+ distribution).
_EDGE_FULL = 15      # top-~10% connectivity
_EDGE_LIGHT = 6      # well above the 3.4 average
_CONF_FULL = 0.85
_CONF_LIGHT = 0.78
_MIN_OVERLAP = 2     # >=2 shared content tokens = genuinely relevant to the turn

_WORD_RE = re.compile(r"[a-z0-9]{3,}")
_STOP = frozenset(
    "the and for are was has had not but with into over from this that how what "
    "who when where which more most just now here there they them their his her "
    "its our you your item these those been being also very much many some".split())


def _tokens(text):
    return {t for t in _WORD_RE.findall((text or "").lower()) if t not in _STOP}


def _best_supported_relevant(message: str):
    """Return (belief_row_dict, edge_degree, overlap) for the best-supported T6+
    belief genuinely relevant to the turn, or None. Reads real metrics only."""
    mtok = _tokens(message)
    if len(mtok) < 1:
        return None
    try:
        con = sqlite3.connect(f"file:{_BELIEFS_DB}?mode=ro", uri=True, timeout=5)
        con.row_factory = sqlite3.Row
        # candidate pool: T6+, live (not retired/paused), containing a turn token
        toks = list(mtok)[:8]
        like = " OR ".join(["content LIKE ?"] * len(toks))
        rows = con.execute(
            f"SELECT id, content, tier, confidence, corroboration_count "
            f"FROM beliefs WHERE tier >= 6 AND tier < 8 AND paused = 0 AND ({like}) "
            f"LIMIT 200", tuple(f"%{t}%" for t in toks)).fetchall()
        if not rows:
            con.close()
            return None
        # score by genuine token overlap; keep the top few, then measure support
        scored = []
        for r in rows:
            ov = len(mtok & _tokens(r["content"]))
            if ov >= _MIN_OVERLAP:
                scored.append((ov, r))
        if not scored:
            con.close()
            return None
        scored.sort(key=lambda x: x[0], reverse=True)
        top = [r for _, r in scored[:8]]
        ids = [r["id"] for r in top]
        ph = ",".join("?" * len(ids))
        deg = {i: 0 for i in ids}
        for e in con.execute(
                f"SELECT bid, COUNT(*) d FROM ("
                f" SELECT source_id bid FROM belief_edges WHERE source_id IN ({ph}) "
                f" UNION ALL SELECT target_id FROM belief_edges WHERE target_id IN ({ph})"
                f") GROUP BY bid", (*ids, *ids)):
            deg[e["bid"]] = e["d"]
        con.close()
        # pick the strongest-supported (edge-degree primary, confidence secondary)
        best = max(top, key=lambda r: (deg.get(r["id"], 0), r["confidence"] or 0))
        ov = len(mtok & _tokens(best["content"]))
        return (dict(best), deg.get(best["id"], 0), ov)
    except Exception:
        return None


def sraddha_read(message: str = "") -> dict:
    """Return {'grade':'none'|'light'|'full','belief':text,'edges':n,'confidence':c}.
    Grade reflects REAL support only; thin/absent -> 'none'."""
    got = _best_supported_relevant(message)
    if not got:
        return {"grade": "none", "belief": "", "edges": 0, "confidence": 0.0}
    b, edges, _ov = got
    conf = float(b.get("confidence") or 0.0)
    corr = int(b.get("corroboration_count") or 0)
    # FULL: strong on connectivity AND (confidence OR corroboration)
    if edges >= _EDGE_FULL and (conf >= _CONF_FULL or corr >= 1):
        grade = "full"
    elif edges >= _EDGE_LIGHT or conf >= _CONF_LIGHT:
        grade = "light"
    else:
        grade = "none"   # crystallized but thin -> no manufactured confidence
    return {"grade": grade, "belief": b.get("content", ""), "edges": edges,
            "confidence": conf}


def stance_for(message: str = "") -> str:
    """Compose-path entry: a stand-on-it signal when a genuinely well-supported
    belief bears on the turn. '' when support is thin/absent, flag off, or error."""
    try:
        if os.environ.get("NEX5_SRADDHA") != "1":
            return ""
        read = sraddha_read(message)
        if read["grade"] == "none":
            return ""
        belief = read["belief"][:140]
        if read["grade"] == "full":
            return (
                "[Warranted confidence: you hold a well-supported belief bearing on "
                f"this (crystallized, {read['edges']} connections, conf "
                f"{read['confidence']:.2f}) — you can stand on it plainly, no need to "
                f"hedge into mush: {belief}]\n\n"
            )
        return (
            "[Warranted confidence: a fairly well-grounded belief bears on this — "
            f"lean on it rather than over-hedging: {belief}]\n\n"
        )
    except Exception as exc:
        error_channel.record(
            f"sraddha stance failed (non-fatal): {exc}",
            source=_LOG_SOURCE, exc=exc,
        )
        return ""
