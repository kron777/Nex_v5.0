"""world_predictions.py  —  Stage A of "more than a prompt processor".

The point of this module
------------------------
Everything NEX does today happens inside language: the voice writes thoughts,
stores them as beliefs, reads its own beliefs back, writes more. Even its
existing `predictions` table only predicts NEX's OWN next thought and scores the
"surprise" against its own actual thought — still sealed inside itself.

This module introduces the first thing NEX cannot talk its way out of: a
FALSIFIABLE claim about the outside world, scored by a plain function that
independently fetches reality. NEX says "bitcoin will be higher in N seconds";
later, the resolver fetches the real price from the live API — NOT from NEX's
own stored data — and stamps the claim correct or wrong. The verdict is not
authored by the voice. Over time this accumulates into a hit-rate NEX earned
against the world, not one it asserted.

This is deliberately STANDALONE: it does not touch generator.py or any of the
working pipeline. It is testable in complete isolation (see __main__). Stage A
proves the load-bearing question — can a plain function read the live price and
score a claim — before any code that GENERATES predictions is wired in.

Stdlib only. No new dependencies.
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path
from typing import Optional


# --- DB path: matches the project convention (NEX5_DATA_DIR override) ---------
def _default_db_path() -> str:
    override = os.environ.get("NEX5_DATA_DIR")
    if override:
        return str(Path(override) / "conversations.db")
    # default: <cwd>/data/conversations.db  (run from the nex5 repo root)
    return str(Path("data") / "conversations.db")


# --- schema: a small purpose-built table for falsifiable world claims --------
# Deliberately NOT reusing the existing `predictions` table — that one is built
# around thought-embedding centroids for self-prediction. A price claim has no
# centroid; forcing it in would be a square peg. Separate concern, separate table.
_SCHEMA = (
    "CREATE TABLE IF NOT EXISTS world_predictions ("
    "id INTEGER PRIMARY KEY AUTOINCREMENT, "
    "made_at REAL NOT NULL, "
    "asset TEXT NOT NULL, "              # coingecko id, e.g. 'bitcoin'
    "baseline_price REAL NOT NULL, "    # price at the moment of the claim
    "direction TEXT NOT NULL, "         # 'up' or 'down'
    "horizon_seconds INTEGER NOT NULL, "
    "resolve_at REAL NOT NULL, "        # made_at + horizon
    "resolved_at REAL, "                # NULL until resolved
    "price_at_resolve REAL, "           # NULL until resolved
    "outcome TEXT, "                    # NULL / 'correct' / 'wrong' / 'error'
    "source TEXT NOT NULL DEFAULT 'manual')"  # who made it: 'manual'/'voice'
)
_IDX = (
    "CREATE INDEX IF NOT EXISTS idx_wp_resolve "
    "ON world_predictions(resolved_at, resolve_at)"
)


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=10.0, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=10000")
    return conn


def ensure_schema(db_path: Optional[str] = None) -> None:
    db_path = db_path or _default_db_path()
    conn = _connect(db_path)
    try:
        conn.execute(_SCHEMA)
        conn.execute(_IDX)
    finally:
        conn.close()


# --- the load-bearing piece: independently fetch reality ----------------------
# This hits the real CoinGecko API directly. It does NOT read NEX's stored
# snapshot. That independence is the whole point: the verdict comes from outside
# anything NEX controls.
_PRICE_URL = "https://api.coingecko.com/api/v3/simple/price"


def fetch_price(asset: str = "bitcoin", timeout: float = 10.0) -> Optional[float]:
    """Return the current USD price of `asset`, or None on any failure.

    Plain, dependency-free, independent of NEX's own feeds.
    """
    url = f"{_PRICE_URL}?ids={urllib.parse.quote(asset)}&vs_currencies=usd"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "nex5-world-pred/1"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        val = data.get(asset, {}).get("usd")
        return float(val) if val is not None else None
    except (urllib.error.URLError, ValueError, KeyError, TypeError):
        return None


# --- make a falsifiable claim -------------------------------------------------
def make_prediction(
    asset: str = "bitcoin",
    direction: str = "up",
    horizon_seconds: int = 3600,
    db_path: Optional[str] = None,
    source: str = "manual",
) -> Optional[int]:
    """Record a claim: `asset` will be `direction` (up/down) vs now, in
    `horizon_seconds`. Captures the real baseline price now. Returns row id,
    or None if the price couldn't be fetched (no claim without a baseline).
    """
    if direction not in ("up", "down"):
        raise ValueError("direction must be 'up' or 'down'")
    db_path = db_path or _default_db_path()
    ensure_schema(db_path)
    baseline = fetch_price(asset)
    if baseline is None:
        return None  # cannot make a falsifiable claim without a real baseline
    now = time.time()
    conn = _connect(db_path)
    try:
        cur = conn.execute(
            "INSERT INTO world_predictions "
            "(made_at, asset, baseline_price, direction, horizon_seconds, "
            "resolve_at, source) VALUES (?,?,?,?,?,?,?)",
            (now, asset, baseline, direction, int(horizon_seconds),
             now + horizon_seconds, source),
        )
        return int(cur.lastrowid)
    finally:
        conn.close()


# --- the resolver: a verdict NEX does not author -----------------------------
def resolve_due(now: Optional[float] = None, db_path: Optional[str] = None) -> dict:
    """Find claims past their resolve time that are still unresolved, fetch the
    real current price for each, and stamp correct/wrong. Returns a small summary.

    'correct' = price moved in the claimed direction (strictly). A flat price
    counts as 'wrong' — the claim said it would move, and it didn't.
    """
    now = now if now is not None else time.time()
    db_path = db_path or _default_db_path()
    ensure_schema(db_path)
    conn = _connect(db_path)
    resolved, correct = 0, 0
    try:
        due = conn.execute(
            "SELECT id, asset, baseline_price, direction FROM world_predictions "
            "WHERE resolved_at IS NULL AND resolve_at <= ?",
            (now,),
        ).fetchall()
        # fetch each asset's price once
        price_cache: dict[str, Optional[float]] = {}
        for row in due:
            asset = row["asset"]
            if asset not in price_cache:
                price_cache[asset] = fetch_price(asset)
            price_now = price_cache[asset]
            if price_now is None:
                # leave unresolved; try again next pass (mark nothing)
                continue
            base = float(row["baseline_price"])
            if row["direction"] == "up":
                outcome = "correct" if price_now > base else "wrong"
            else:
                outcome = "correct" if price_now < base else "wrong"
            conn.execute(
                "UPDATE world_predictions SET resolved_at=?, price_at_resolve=?, "
                "outcome=? WHERE id=?",
                (now, price_now, outcome, row["id"]),
            )
            resolved += 1
            if outcome == "correct":
                correct += 1
    finally:
        conn.close()
    return {"resolved": resolved, "correct": correct}


# --- the earned number: a scorecard the voice cannot touch -------------------
def scorecard(db_path: Optional[str] = None) -> dict:
    db_path = db_path or _default_db_path()
    ensure_schema(db_path)
    conn = _connect(db_path)
    try:
        row = conn.execute(
            "SELECT "
            "COUNT(*) FILTER (WHERE outcome IS NOT NULL) AS resolved, "
            "COUNT(*) FILTER (WHERE outcome='correct') AS correct, "
            "COUNT(*) FILTER (WHERE outcome IS NULL) AS pending "
            "FROM world_predictions"
        ).fetchone()
    finally:
        conn.close()
    resolved = row["resolved"] or 0
    correct = row["correct"] or 0
    pending = row["pending"] or 0
    hit_rate = (correct / resolved) if resolved else None
    return {
        "resolved": resolved,
        "correct": correct,
        "pending": pending,
        "hit_rate": hit_rate,
    }


# --- standalone self-test: proves the loop end-to-end, no NEX needed ----------
if __name__ == "__main__":
    import sys

    db = _default_db_path()
    print(f"[world_predictions self-test]  db={db}")

    print("1) fetching live price (independent of NEX)...")
    p = fetch_price("bitcoin")
    if p is None:
        print("   FAIL: could not fetch price. Check network / coingecko reachable.")
        sys.exit(1)
    print(f"   OK: bitcoin = ${p:,.2f}")

    horizon = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    print(f"2) making a claim: bitcoin UP within {horizon}s ...")
    pid = make_prediction("bitcoin", "up", horizon, db_path=db, source="selftest")
    print(f"   claim recorded id={pid}, baseline=${p:,.2f}")

    print(f"3) waiting {horizon}s for the window to close...")
    time.sleep(horizon + 2)

    print("4) resolving (resolver independently re-fetches the real price)...")
    res = resolve_due(db_path=db)
    print(f"   resolved={res['resolved']} correct={res['correct']}")

    print("5) scorecard (a number NEX did not author):")
    sc = scorecard(db_path=db)
    hr = "n/a" if sc["hit_rate"] is None else f"{sc['hit_rate']*100:.0f}%"
    print(f"   resolved={sc['resolved']} correct={sc['correct']} "
          f"pending={sc['pending']} hit_rate={hr}")
    print("done.")
