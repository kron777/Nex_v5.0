#!/usr/bin/env python3
"""check_voice_stability.py — READ-ONLY observational instrument for NEX's VOICE.

The one program that needs no flag and no intervention (Beam G3): it measures the
organism as-is and separates a stable VOICE from a pathological GROOVE, which the
groove detector cannot do (that one is content-blind and treats all repetition as
pathology). Voice = a stable STYLE whose CONTENT still responds to the situation;
groove = form AND content both frozen.

Two quantities over fire outputs (fountain_events.thought x hot_branch=topic):
  I(style; content)   — does HOW she opens depend on WHAT it's about? (>0 => responsive)
  H(content | style)  — within a fixed style, how varied is the content? (high => alive)

Verdict (Beam's table, with the H(C|S) disambiguation):
  I>0                         -> VOICE (style responds to content)
  I~=0, H(C|S) high           -> VOICE (stable signature, responsive content) [her opener]
  I~=0, H(C|S) low            -> GROOVE (frozen form and content)

DRIFT = a change in the profile {I, H(C|S), H(style)} between releases, not any single
value. --freeze stores the profile as a release snapshot; --baseline flags movement.

READ-ONLY: opens dynamic DB mode=ro; writes nothing (except --freeze -> a JSON profile).
Usage:
  python3 tools/check_voice_stability.py [--window N] [--days D]
  python3 tools/check_voice_stability.py --freeze observation_reports/voice/v1.json
  python3 tools/check_voice_stability.py --baseline observation_reports/voice/v1.json
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import re
import sqlite3
import sys
import time

sys.path.insert(0, __file__.rsplit("/tools/", 1)[0])

from substrate.paths import db_paths  # noqa: E402

_DRIFT_BAND = 0.15  # |delta| beyond this on I or H(C|S) flags drift


def _toks(t: str) -> list:
    return re.findall(r"[a-z']+", (t or "").lower())


def _style_class(thought: str) -> str:
    """Categorical STYLE of the opening — the FORM, independent of topic."""
    t = (thought or "").strip()
    low = t.lower()
    toks = _toks(t)
    if not toks:
        return "empty"
    if re.match(r"^(this|the)\s+item\b", low):
        return "item-frame"
    if toks[0] in ("i", "my", "me", "i'm", "i've", "you", "your"):
        return "self-ref"
    if re.match(r"^[^.!?]*\?", t):          # first sentence terminates in a question mark
        return "question-open"
    if toks[0] in ("the", "a", "an", "this", "that", "these", "those", "it", "there"):
        return "deictic-open"
    return "topic-direct"


def _entropy(counts) -> float:
    n = sum(counts.values())
    if not n:
        return 0.0
    return -sum((c / n) * math.log2(c / n) for c in counts.values() if c)


def _mutual_info(joint) -> float:
    n = sum(joint.values())
    if not n:
        return 0.0
    ps = collections.Counter()
    pc = collections.Counter()
    for (s, c), k in joint.items():
        ps[s] += k
        pc[c] += k
    I = 0.0
    for (s, c), k in joint.items():
        pxy = k / n
        I += pxy * math.log2(pxy / ((ps[s] / n) * (pc[c] / n)))
    return I


def measure(window: int = 3000, days: float | None = None) -> dict:
    db = str(db_paths()["dynamic"])
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=5)
    try:
        if days is not None:
            rows = con.execute(
                "SELECT thought, hot_branch FROM fountain_events WHERE ts > ? "
                "AND thought IS NOT NULL", (time.time() - days * 86400,)).fetchall()
        else:
            rows = con.execute(
                "SELECT thought, hot_branch FROM fountain_events WHERE thought IS NOT NULL "
                "ORDER BY ts DESC LIMIT ?", (window,)).fetchall()
    finally:
        con.close()
    subst = [(t, (b or "unknown")) for t, b in rows
             if t and len(t.split()) >= 15 and not t.startswith("[")]
    n = len(subst)
    if n < 30:
        return {"n": n, "error": "insufficient substantive fires"}

    joint = collections.Counter()
    style_c = collections.Counter()
    content_c = collections.Counter()
    per_style_content = collections.defaultdict(collections.Counter)
    for t, b in subst:
        s = _style_class(t)
        joint[(s, b)] += 1
        style_c[s] += 1
        content_c[b] += 1
        per_style_content[s][b] += 1

    H_style = _entropy(style_c)
    H_content = _entropy(content_c)
    I = _mutual_info(joint)
    H_content_given_style = H_content - I            # chain rule
    # content entropy within the dominant style bucket (her signature opener)
    dom_style, dom_n = style_c.most_common(1)[0]
    H_content_in_dom = _entropy(per_style_content[dom_style])

    # verdict (Beam's table + H(C|S) disambiguation)
    if I >= 0.15:
        verdict = "VOICE (style responds to content)"
    elif H_content_given_style >= 1.5:
        verdict = "VOICE (stable signature, responsive content)"
    else:
        verdict = "GROOVE (frozen form and content)"

    return {
        "n": n,
        "I_style_content": round(I, 4),
        "H_style": round(H_style, 4),
        "H_content": round(H_content, 4),
        "H_content_given_style": round(H_content_given_style, 4),
        "dominant_style": dom_style,
        "dominant_style_share": round(dom_n / n, 3),
        "H_content_in_dominant_style": round(H_content_in_dom, 4),
        "style_distribution": dict(style_c.most_common()),
        "verdict": verdict,
    }


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--window", type=int, default=3000)
    ap.add_argument("--days", type=float, default=None)
    ap.add_argument("--freeze", metavar="PATH")
    ap.add_argument("--baseline", metavar="PATH")
    args = ap.parse_args(argv[1:])

    m = measure(window=args.window, days=args.days)
    print("=" * 68)
    print(f"VOICE-STABILITY  {time.strftime('%Y-%m-%d %H:%M:%S')}  (n={m.get('n')})")
    print("=" * 68)
    if "error" in m:
        print("  " + m["error"])
        return 1
    print(f"  I(style; content)        : {m['I_style_content']:.3f} bits   (>0 => style responds)")
    print(f"  H(style)                 : {m['H_style']:.3f} bits")
    print(f"  H(content | style)       : {m['H_content_given_style']:.3f} bits   (high => content alive)")
    print(f"  dominant style           : {m['dominant_style']} ({m['dominant_style_share']:.0%}), "
          f"content-entropy within it {m['H_content_in_dominant_style']:.3f}")
    print(f"  style distribution       : {m['style_distribution']}")
    print(f"  VERDICT                  : {m['verdict']}")

    if args.freeze:
        import os
        os.makedirs(os.path.dirname(args.freeze) or ".", exist_ok=True)
        with open(args.freeze, "w") as f:
            json.dump({**m, "frozen_at": time.strftime("%Y-%m-%d")}, f, indent=2)
        print(f"\n  release profile frozen -> {args.freeze}")
    if args.baseline:
        with open(args.baseline) as f:
            base = json.load(f)
        # Beam G3 refinement: the voice->groove regression shows as FALLING H(content|style)
        # and RISING dominant-style share, NOT as changing I (I~=0 is stability, which alone is
        # ALSO consistent with a groove). So watch the content term directionally, not |delta| on I.
        print(f"\n  DRIFT vs {base.get('frozen_at','?')} — regression = content entropy FALLING / "
              f"style share RISING (not I changing):")
        hcs_b, hcs_c = base.get("H_content_given_style"), m.get("H_content_given_style")
        if hcs_b is not None:
            d = hcs_c - hcs_b
            flag = "  ** GROOVE DRIFT: content entropy collapsing **" if d < -_DRIFT_BAND else ""
            print(f"    H(content|style)     : {hcs_c:.3f}  (was {hcs_b:.3f}, {d:+.3f}){flag}  <- discriminator")
        ds_b, ds_c = base.get("dominant_style_share"), m.get("dominant_style_share")
        if ds_b is not None:
            d = ds_c - ds_b
            flag = "  ** CONCENTRATION DRIFT: one style dominating **" if d > _DRIFT_BAND else ""
            print(f"    dominant-style share : {ds_c:.3f}  (was {ds_b:.3f}, {d:+.3f}){flag}  <- leading indicator")
        i_b, i_c = base.get("I_style_content"), m.get("I_style_content")
        if i_b is not None:
            print(f"    I(style;content)     : {i_c:.3f}  (was {i_b:.3f})  [~0 = stability; NOT the drift signal]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
