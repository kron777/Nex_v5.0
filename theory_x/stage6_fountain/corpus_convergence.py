"""maxDF* -- corpus-convergence metric for crystallized beliefs. READ-ONLY.

WHAT IT MEASURES
    The failure mode this catches is not "a bad belief" but "the belief corpus
    collapsing onto one story". Round 27 documented the loop: a single feed item
    scores STRIKING, occupies the exemplar pool, gets copied into the next
    prompt, scores STRIKING again. Nothing in the existing instrumentation can
    see that, because every individual fire looks fine -- the fidelity predicate
    passes, the scorer is happy, the gate lets it through. What has gone wrong is
    a property of the CORPUS, not of any one row in it.

    maxDF* is that property, in one number:

        over the rolling N most recent crystallized beliefs, the largest
        document-frequency share reached by any single content token, after
        excluding NEX5's own standing register.

    "Document frequency" = the fraction of those N beliefs the token appears in
    at all (not how often -- once per belief, counted once). The register
    exclusion is what makes the number mean something: without it the answer is
    always "quiet" or "hum", which is her voice, not a convergence.

WHAT IT IS NOT
    This module is instrumentation. It is not imported by the fire path, it
    gates nothing, it writes nothing, and it opens the database read-only. If it
    raises, nothing downstream notices, because nothing downstream calls it.

    It is also NOT a fidelity metric. Fidelity (GENIUS_FIDELITY_BASELINE.md
    section 1) asks "did this fire stay on its assigned subject". maxDF* asks
    "is the corpus as a whole still about more than one thing". A run can be
    100% subject-faithful and still be converging, because the subjects
    themselves are what collapsed.

BASELINE (45-day backtest, see GENIUS_FIDELITY_BASELINE.md section 5)
    median 12%   p90 18%   p99 22%   threshold 25%

    The threshold is set just above the observed p99 and is deliberately not
    tight: at N=50 one belief is 2 percentage points, so anything finer is
    quantisation noise. Crossing 25% means one token is in more than half of one
    in four recent beliefs, which in every case inspected so far has meant a
    single external story had taken the corpus over.

USAGE
    python3 -m theory_x.stage6_fountain.corpus_convergence
    python3 -m theory_x.stage6_fountain.corpus_convergence --history 40
"""
from __future__ import annotations

import json
import os
import sqlite3
from collections import Counter
from typing import Optional

# The tokenizer and furniture list are deliberately imported rather than
# re-declared. GENIUS_FIDELITY_BASELINE.md requires the predicate to have one
# definition; a second copy here is exactly the drift that round 25 could not
# untangle. This import is read-only use of two module-level helpers -- it does
# not construct a crystallizer and has no side effects.
from theory_x.stage6_fountain.crystallizer import _fidelity_tokens

_HERE = os.path.dirname(os.path.abspath(__file__))
_REGISTER_PATH = os.path.join(_HERE, "register_exclusion.json")
_DEFAULT_DB = "/home/rr/Desktop/Desktop/nex5/data/beliefs.db"

WINDOW = 50
THRESHOLD = 0.25

# Backtest quantiles, 45 days to 2026-08-04. Recorded here so a caller can
# report the reading against its baseline without a second lookup.
BACKTEST = {"median": 0.12, "p90": 0.18, "p99": 0.22}


def load_register_exclusion(path: str = _REGISTER_PATH) -> dict:
    """The frozen register list plus its provenance. Fitted data -- the
    'fitted_on' date is the point of the file; see the header comment inside."""
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def recent_crystallized(db_path: str = _DEFAULT_DB, window: int = WINDOW) -> list:
    """The `window` most recent crystallized beliefs, oldest first.

    source='fountain_insight' is the crystallizer's own category (its default
    `crystallization_category`), i.e. exactly the beliefs this pipeline minted.
    Opened read-only: this must never be able to touch live state.
    """
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=10)
    try:
        rows = conn.execute(
            "SELECT id, created_at, content FROM beliefs "
            "WHERE source='fountain_insight' AND content IS NOT NULL "
            "ORDER BY created_at DESC LIMIT ?",
            (window,),
        ).fetchall()
    finally:
        conn.close()
    return list(reversed(rows))


def max_df_star(
    docs: Optional[list] = None,
    exclusion: Optional[set] = None,
    db_path: str = _DEFAULT_DB,
    window: int = WINDOW,
) -> dict:
    """Compute maxDF* over `docs` (default: the live rolling window).

    `docs` may be a list of raw strings or of rows whose last element is the
    text, so a caller replaying history can pass DB rows straight through.

    Returns the reading, the token driving it, and the runners-up -- the token
    is the whole point, since "26%" alone tells you nothing about what to go
    look at.
    """
    if docs is None:
        docs = recent_crystallized(db_path, window)
    texts = [d if isinstance(d, str) else d[-1] for d in docs]
    if exclusion is None:
        exclusion = set(load_register_exclusion()["terms"])

    n = len(texts)
    if n == 0:
        return {"n": 0, "max_df_star": None, "token": None, "top": [],
                "threshold": THRESHOLD, "breach": False}

    df = Counter()
    for t in texts:
        df.update(set(_fidelity_tokens(t)) - exclusion)

    top = [(tok, cnt, cnt / n) for tok, cnt in df.most_common(5)]
    best = top[0] if top else (None, 0, 0.0)
    return {
        "n": n,
        "max_df_star": best[2],
        "token": best[0],
        "doc_count": best[1],
        "top": top,
        "threshold": THRESHOLD,
        "breach": best[2] > THRESHOLD,
    }


def _main(argv: list) -> int:
    import argparse
    import time

    ap = argparse.ArgumentParser(description="maxDF* corpus-convergence reading")
    ap.add_argument("--window", type=int, default=WINDOW)
    ap.add_argument("--db", default=_DEFAULT_DB)
    ap.add_argument("--history", type=int, default=0,
                    help="also print the last N rolling readings")
    args = ap.parse_args(argv)

    reg = load_register_exclusion()
    r = max_df_star(db_path=args.db, window=args.window)

    print(f"maxDF*  window={r['n']} most recent crystallized beliefs")
    print(f"register exclusion: {reg['n_terms']} terms, fitted {reg['fitted_on']} "
          f"on {reg['corpus']['n_documents']} docs")
    if r["max_df_star"] is None:
        print("  no data")
        return 0
    flag = "  ** OVER THRESHOLD **" if r["breach"] else ""
    print(f"  maxDF* = {r['max_df_star']*100:.1f}%  driven by '{r['token']}' "
          f"({r['doc_count']}/{r['n']} beliefs){flag}")
    print(f"  baseline: median {BACKTEST['median']*100:.0f}%  "
          f"p90 {BACKTEST['p90']*100:.0f}%  p99 {BACKTEST['p99']*100:.0f}%  "
          f"threshold {THRESHOLD*100:.0f}%")
    print("  runners-up: " + ", ".join(
        f"{t} {s*100:.0f}%" for t, _c, s in r["top"][1:]))

    if args.history > 0:
        conn = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True, timeout=10)
        try:
            rows = conn.execute(
                "SELECT created_at, content FROM beliefs "
                "WHERE source='fountain_insight' AND content IS NOT NULL "
                "ORDER BY created_at DESC LIMIT ?",
                (args.window + args.history,),
            ).fetchall()
        finally:
            conn.close()
        rows = list(reversed(rows))
        excl = set(reg["terms"])
        print(f"\nlast {args.history} rolling readings:")
        for i in range(args.window, len(rows) + 1):
            h = max_df_star(docs=rows[i - args.window:i], exclusion=excl)
            ts = time.strftime("%m-%d %H:%M", time.gmtime(rows[i - 1][0]))
            mark = " *" if h["breach"] else ""
            print(f"  {ts}  {h['max_df_star']*100:5.1f}%  {h['token']}{mark}")
    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(_main(sys.argv[1:]))
