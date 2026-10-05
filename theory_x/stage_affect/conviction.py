"""Conviction — śraddhā re-expressed machine-natively (NEX5_CONVICTION).

śraddhā (sraddha.py) computes a support gate and then hands the voice a canned
imperative ("you can stand on it plainly, no need to hedge into mush"). The
quality lives in the English, not in her state. This module moves it to the
substrate side of doctrine §0: each retrieved belief gets a SUPPORT score from
primitives the graph actually carries, and the retrieved belief block is
re-rendered into two groups — "Held:" and "Still unsettled:". No sentence is
added and nothing tells her how to speak; the grouping IS the state. The LLM
reads stance from structure.

SUPPORT (only primitives measured to carry signal, 2026-09-26):
  depth   = (8 - tier) / 7         tier is promotion depth: promotion is tier-1
                                   (promotion.py), T1 keystone .. T7 impression.
                                   śraddhā reads this INVERTED (tier >= 6 = strong,
                                   i.e. the two shallowest tiers) — corrected here.
  conf    = confidence
  cent    = log1p(deg) / log1p(DEG_REF), deg over synthesises + cross_domain
            edges (the dense types; 267k of ~268k edges)
  rec     = exp(-age_h / REC_TAU_H), age from the most recent last_traversed_at
            on those edges (spreading-activation stamp) or last_referenced_at
  support = weighted mean of the four, in [0, 1]
NOT used: corroboration_count (non-zero only at T7, which chat retrieval never
returns — tier <= 6 filter — and reset to 0 on every promotion) and opposes
edges (165 of ~268k: too sparse to read).

HELD iff support >= HELD_MIN. DEG_REF / REC_TAU_H / HELD_MIN are calibrated on
the chat-retrieval population, not guessed — see tools/conviction_harness.py.

HONESTY: this encapsulates the FUNCTIONAL ROLE of conviction — a computed
held/unsettled signature over her own graph. It does not certify that she
feels certain. No sentience verdict.

Read-only (beliefs.db opened mode=ro). FAIL-SAFE: any error, or any belief line
that cannot be resolved to a row, returns the block unchanged (the current flat
block).

RECORDED NULL — NOT WIRED (2026-09-26). Both chat-path uses were measured and
removed from gui/server.py:
  * regroup()          (NEX5_CONVICTION): C vs labels-swapped control, hedges/100w
                       3B +0.24 [-1.00,+1.10], 7B +0.16 [-0.19,+0.54] — the voice
                       does not read the labels.
  * order_by_support() (NEX5_CONVICTION_ORDER): what she draws on is driven by
                       relevance to the question (+0.138 [+0.051,+0.247]), not
                       position (+0.014) or support (-0.048); support correlates
                       -0.21 with relevance (centrality = generic, not earned).
Harnesses: tools/conviction_harness.py, tools/conviction_order_harness.py.
The support score itself is the weak part: it measures connectedness, not
warrant. Kept as the record; nothing imports this live.
"""
from __future__ import annotations

import math
import re
import time

__all__ = ["regroup", "order_by_support", "signatures", "support",
           "HELD_HEADER", "UNSETTLED_HEADER"]

_BELIEFS_DB = "/home/rr/Desktop/Desktop/nex5/data/beliefs.db"

# Calibrated 2026-09-26 on the chat-retrieval population — 98 non-test user turns
# re-retrieved read-only, 196 sets, 472 beliefs (tools/conviction_harness.py
# --calibrate): DEG_REF = p95 dense-edge degree, REC_TAU_H = median traversal age,
# HELD_MIN = the cut that maximises turns carrying BOTH groups.
DEG_REF = 125.0     # p95 dense-edge degree (pool median 11, max 368)
REC_TAU_H = 22.6    # median traversal age, hours
HELD_MIN = 0.46     # 87% of retrieved sets then carry both groups; 56% of pool Held
_W = {"depth": 0.25, "conf": 0.25, "cent": 0.25, "rec": 0.25}

HELD_HEADER = "Held:"
UNSETTLED_HEADER = "Still unsettled:"

# Same line shape format_beliefs_for_prompt writes: "- [Tier 6 | 0.70 | ROLE] text"
_LINE_RE = re.compile(r"^-\s*\[Tier\s*([0-9?]+)[^\]]*\]\s*(.+)$")
_DENSE = ("synthesises", "cross_domain")


def _db_path() -> str:
    try:
        from substrate.paths import db_paths
        return str(db_paths()["beliefs"])
    except Exception:
        return _BELIEFS_DB


def support(tier: int, confidence: float, deg: int, age_h,
            deg_ref: float = None, tau_h: float = None, w: dict = None) -> float:
    """Pure scorer, [0, 1]. age_h None (never traversed/referenced) -> rec 0."""
    deg_ref = DEG_REF if deg_ref is None else deg_ref
    tau_h = REC_TAU_H if tau_h is None else tau_h
    w = _W if w is None else w
    depth = max(0.0, min(1.0, (8 - int(tier)) / 7.0))
    conf = max(0.0, min(1.0, float(confidence or 0.0)))
    cent = min(1.0, math.log1p(max(0, deg or 0)) / math.log1p(deg_ref))
    rec = 0.0 if age_h is None else math.exp(-max(0.0, age_h) / tau_h)
    parts = {"depth": depth, "conf": conf, "cent": cent, "rec": rec}
    return sum(w[k] * parts[k] for k in w) / sum(w.values())


def _resolve(con, content: str):
    """Row for a rendered belief line. Exact content first; a line cut by the
    chat path's 800-char cap ends in ' …' — fall back to a prefix match."""
    r = con.execute(
        "SELECT id, tier, confidence, last_referenced_at FROM beliefs WHERE content=?",
        (content,)).fetchone()
    if r:
        return r
    stem = content.rstrip(" …").rstrip()
    if len(stem) >= 40:
        like = stem.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        return con.execute(
            "SELECT id, tier, confidence, last_referenced_at FROM beliefs "
            "WHERE content LIKE ? ESCAPE '\\' LIMIT 1", (like + "%",)).fetchone()
    return None


def _features(con, row, now: float) -> dict:
    bid, tier, conf, lref = row
    deg, trav = con.execute(
        "SELECT COUNT(*), MAX(last_traversed_at) FROM belief_edges "
        "WHERE (source_id=? OR target_id=?) AND edge_type IN (?, ?)",
        (bid, bid, *_DENSE)).fetchone()
    last = max([t for t in (trav, lref) if t] or [0]) or None
    age_h = (now - last) / 3600.0 if last else None
    return {"id": bid, "tier": tier, "confidence": conf, "deg": deg or 0,
            "age_h": age_h}


def signatures(contents: list, now: float = None, db_path: str = None) -> list:
    """Per-belief support signature for rendered belief contents. Returns a list
    aligned with `contents`; an entry is None when that belief did not resolve."""
    now = time.time() if now is None else now
    from substrate import Reader
    with Reader(db_path or _db_path()).connection() as con:   # mode=ro
        out = []
        for c in contents:
            row = _resolve(con, c)
            if row is None:
                out.append(None)
                continue
            f = _features(con, row, now)
            f["support"] = support(f["tier"], f["confidence"], f["deg"], f["age_h"])
            f["held"] = f["support"] >= HELD_MIN
            out.append(f)
        return out


def regroup(block: str, now: float = None, db_path: str = None,
            invert: bool = False) -> str:
    """Re-render a belief block into Held / Still unsettled groups, keeping every
    line byte-for-byte (the [Tier N | conf] markers stay). Non-belief lines (a
    header, a self-state preamble) keep their place; the belief lines are
    regrouped where the first one stood. `invert` swaps the groups — a harness
    control only, never used on the live path. FAIL-SAFE: returns `block`
    unchanged on any error, on any unresolvable belief line, or when there are
    no belief lines."""
    try:
        lines = (block or "").split("\n")
        idx = [i for i, ln in enumerate(lines) if _LINE_RE.match(ln.strip())]
        if not idx:
            return block
        contents = [_LINE_RE.match(lines[i].strip()).group(2).strip() for i in idx]
        sigs = signatures(contents, now=now, db_path=db_path)
        if any(s is None for s in sigs):
            return block
        held = [lines[i] for i, s in zip(idx, sigs) if s["held"] != invert]
        unsettled = [lines[i] for i, s in zip(idx, sigs) if s["held"] == invert]
        grouped = []
        if held:
            grouped += [HELD_HEADER] + held
        if unsettled:
            grouped += [UNSETTLED_HEADER] + unsettled
        keep = set(idx)
        out = []
        for i, ln in enumerate(lines):
            if i == idx[0]:
                out.extend(grouped)
            elif i not in keep:
                out.append(ln)
        return "\n".join(out)
    except Exception:
        return block


def order_by_support(block: str, now: float = None, db_path: str = None,
                     reverse: bool = False, supports: list = None) -> str:
    """Conviction as SELECTION, not labelling (measured null, see module doc): the belief
    lines are reordered by support, highest first. Nothing is added (no header,
    no sentence) and nothing is dropped (ordering, not filtering — recall is
    preserved); every line stays byte-for-byte, and non-belief lines keep their
    slots. The sort is stable, so ties keep retrieval order.

    `reverse` (lowest first) and `supports` (precomputed scores aligned to the
    belief lines, so a replay keeps the exact split) are harness-only.
    FAIL-SAFE: returns `block` unchanged on any error, on any unresolvable belief
    line, or when there are fewer than two belief lines."""
    try:
        lines = (block or "").split("\n")
        idx = [i for i, ln in enumerate(lines) if _LINE_RE.match(ln.strip())]
        if len(idx) < 2:
            return block
        if supports is None:
            contents = [_LINE_RE.match(lines[i].strip()).group(2).strip() for i in idx]
            sigs = signatures(contents, now=now, db_path=db_path)
            if any(x is None for x in sigs):
                return block
            supports = [x["support"] for x in sigs]
        if len(supports) != len(idx) or any(x is None for x in supports):
            return block
        order = sorted(range(len(idx)), key=lambda k: supports[k], reverse=not reverse)
        out = list(lines)
        for slot, k in zip(idx, order):
            out[slot] = lines[idx[k]]
        return "\n".join(out)
    except Exception:
        return block
