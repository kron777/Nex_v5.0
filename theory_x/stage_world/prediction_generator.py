"""prediction_generator.py  —  Stage B of "more than a prompt processor".

Stage A (world_predictions.py) proved a plain function can read the live price
and score a falsifiable claim NEX cannot fake. Stage A claims were hand-inserted.

Stage B lets NEX make the claim ITSELF — and does it in the most honest, most
informative way: the VOICE (the same qwen model NEX runs) decides the direction.
That turns the scorecard into a real test of the project's whole thesis. We have
always said the voice is FLUENT but not PREDICTIVE — that it produces plausible
language, not knowledge. Until now that was asserted. Now reality scores it.

To make the test fair, every voice prediction is paired with a RANDOM control at
the same baseline and horizon. Over many samples:
  - if voice hit-rate ~= random hit-rate  -> the voice's directional calls carry
    no information. The fluent reasoning is decoration. (The expected result —
    and a TRUE finding, measured against the world instead of asserted.)
  - if voice hit-rate > random, consistently -> the voice's calls carry real
    signal. (Surprising; would be a genuine, falsifiable discovery.)

Either way, for the first time NEX's own output is being judged by something it
does not control. That is the line between a prompt processor and an agent with a
toehold in reality.

Standalone. Layers on Stage A. Does NOT touch generator.py or the pipeline.
Stdlib only. Calls the same local voice endpoint NEX already uses.
"""
from __future__ import annotations

import json
import logging
import os
import random
import sys
import time
import urllib.request
import urllib.error
import urllib.parse
from typing import Optional

# Stage A primitive (confirmed working on real data).
# Robust import: works whether this file is run directly as a script (sibling
# import) or imported as part of the package (Stage C integration).
try:
    from theory_x.stage_world import world_predictions as wp
except ModuleNotFoundError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import world_predictions as wp


# --- fetch the real recent trajectory to give the voice something to read ----
# v2 fix: the bare "up or down?" question gave the model NOTHING to reason from,
# so it defaulted to a constant ("DOWN" x32 in the first soak) — uninterpretable
# as a skill test. This hands it the actual recent price series (the same data
# NEX ingests) so its call is a genuine read of reality, not a reflex. If it
# STILL can't vary or beat chance with the data in front of it, that is the
# strong, clean finding.
_CHART_URL = "https://api.coingecko.com/api/v3/coins/{id}/market_chart"


def _recent_context(asset: str, timeout: float = 10.0) -> Optional[str]:
    """Return a compact summary of `asset`'s last ~hour of price movement, or
    None on failure (the caller degrades to a context-free question)."""
    url = (
        _CHART_URL.format(id=urllib.parse.quote(asset))
        + "?vs_currency=usd&days=1"
    )
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "nex5-world-pred/2"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        prices = [float(p[1]) for p in data.get("prices", []) if len(p) == 2]
    except (urllib.error.URLError, ValueError, KeyError, TypeError):
        return None
    if len(prices) < 6:
        return None
    # days=1 is ~5-minute granularity; last 12 points ~= last hour
    recent = prices[-12:]
    chg_1h = (recent[-1] - recent[0]) / recent[0] * 100.0
    series = ", ".join(f"{int(x)}" for x in recent)
    return (
        f"Recent {asset} USD price, 5-min steps, oldest first: {series}. "
        f"Net change over this last hour: {chg_1h:+.2f}%."
    )


# --- ask the voice for a directional call ------------------------------------
def _ask_voice_direction(
    asset: str, baseline: float, horizon_seconds: int
) -> Optional[str]:
    """Ask the SAME local model NEX runs for an up/down call, GIVEN the real
    recent trajectory. Returns 'up', 'down', or None if unparseable.

    Uses the OpenAI-compatible endpoint NEX already uses (NEX5_VOICE_URL).
    """
    url = os.environ.get(
        "NEX5_VOICE_URL", "http://localhost:11434/v1/chat/completions"
    )
    model = os.environ.get("NEX5_VOICE_MODEL", "qwen2.5:3b")
    ctx = _recent_context(asset)
    question = (
        (f"{ctx}\n\n" if ctx else "")
        + f"{asset} is currently ${baseline:.0f}. "
        + ("Based on the recent movement above, will " if ctx else "Will ")
        + f"the price be higher or lower in {horizon_seconds} seconds? "
        f"Answer with one word: UP or DOWN."
    )
    body = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You output exactly one word: UP or DOWN. Nothing else.",
            },
            {
                "role": "user",
                "content": question,
            },
        ],
        "max_tokens": 4,
        "temperature": 0.7,
    }
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            out = json.loads(resp.read().decode("utf-8"))
        txt = (out["choices"][0]["message"]["content"] or "").strip().lower()
    except (urllib.error.URLError, KeyError, IndexError, ValueError, TypeError):
        return None
    # parse — be strict but tolerant of trailing punctuation/words
    if "up" in txt and "down" not in txt:
        return "up"
    if "down" in txt and "up" not in txt:
        return "down"
    return None


# --- NEX makes its own claim, paired with a random control -------------------
def make_voice_prediction(
    asset: str = "bitcoin",
    horizon_seconds: int = 3600,
    db_path: Optional[str] = None,
) -> dict:
    """NEX (the voice) makes a directional claim about `asset`, recorded with
    source='voice'. A random control claim is recorded at the same time/horizon
    with source='random'. Returns the ids and the calls.

    Returns {'voice_id', 'voice_dir', 'random_id', 'random_dir', 'baseline'} or
    an 'error' key if the price or the voice call failed.
    """
    db_path = db_path or wp._default_db_path()
    baseline = wp.fetch_price(asset)
    if baseline is None:
        return {"error": "price_fetch_failed"}

    voice_dir = _ask_voice_direction(asset, baseline, horizon_seconds)
    if voice_dir is None:
        return {"error": "voice_unparseable", "baseline": baseline}

    # Calibration (Step 2): consult NEX's tested record before trusting this call.
    try:
        from theory_x.stage_world.calibration_consult import consult_self_trust
        trust = consult_self_trust()
    except Exception:
        trust = {"level": "unknown", "reason": "consult unavailable"}
    logging.getLogger("nex5.world_loop").info(
        "calibration: voice call trust=%s (%s)", trust["level"], trust["reason"]
    )
    random_dir = random.choice(["up", "down"])

    voice_id = wp.make_prediction(
        asset, voice_dir, horizon_seconds, db_path=db_path, source="voice"
    )
    random_id = wp.make_prediction(
        asset, random_dir, horizon_seconds, db_path=db_path, source="random"
    )
    return {
        "voice_id": voice_id,
        "voice_dir": voice_dir,
        "random_id": random_id,
        "random_dir": random_dir,
        "baseline": baseline,
        "trust": trust["level"],
    }


# --- scorecard split by source: voice vs random ------------------------------
def scorecard_by_source(db_path: Optional[str] = None) -> dict:
    db_path = db_path or wp._default_db_path()
    wp.ensure_schema(db_path)
    conn = wp._connect(db_path)
    try:
        rows = conn.execute(
            "SELECT source, "
            "COUNT(*) FILTER (WHERE outcome IS NOT NULL) AS resolved, "
            "COUNT(*) FILTER (WHERE outcome='correct') AS correct, "
            "COUNT(*) FILTER (WHERE outcome IS NULL) AS pending "
            "FROM world_predictions GROUP BY source"
        ).fetchall()
    finally:
        conn.close()
    out: dict = {}
    for r in rows:
        res = r["resolved"] or 0
        cor = r["correct"] or 0
        out[r["source"]] = {
            "resolved": res,
            "correct": cor,
            "pending": r["pending"] or 0,
            "hit_rate": (cor / res) if res else None,
        }
    return out


# --- standalone self-test ----------------------------------------------------
if __name__ == "__main__":
    db = wp._default_db_path()
    horizon = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    print(f"[prediction_generator self-test]  db={db}  horizon={horizon}s")

    print("1) NEX (voice) makes its own directional call, paired with random...")
    r = make_voice_prediction("bitcoin", horizon, db_path=db)
    if "error" in r:
        print(f"   FAIL: {r['error']}")
        if r.get("baseline"):
            print(f"   (price fetch worked: ${r['baseline']:,.2f} — the voice "
                  f"endpoint is the problem. Check NEX5_VOICE_URL / ollama up.)")
        sys.exit(1)
    print(f"   baseline=${r['baseline']:,.2f}")
    print(f"   VOICE call : bitcoin {r['voice_dir'].upper()}  (id={r['voice_id']})")
    print(f"   RANDOM ctrl: bitcoin {r['random_dir'].upper()}  (id={r['random_id']})")

    print(f"2) waiting {horizon}s for the window to close...")
    time.sleep(horizon + 2)

    print("3) resolving against the real price (Stage A resolver)...")
    res = wp.resolve_due(db_path=db)
    print(f"   resolved={res['resolved']} correct={res['correct']}")

    print("4) scorecard by source (voice vs random, judged by the market):")
    sc = scorecard_by_source(db_path=db)
    for src in ("voice", "random"):
        s = sc.get(src)
        if not s:
            continue
        hr = "n/a" if s["hit_rate"] is None else f"{s['hit_rate']*100:.0f}%"
        print(f"   {src:7s}: resolved={s['resolved']} correct={s['correct']} "
              f"pending={s['pending']} hit_rate={hr}")
    print("done.  (one sample proves plumbing; skill needs MANY samples.)")
