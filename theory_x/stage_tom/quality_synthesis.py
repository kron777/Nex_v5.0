"""Quality Synthesis — NEX's RSI loop.

Perplexity Brain for NEX: reviews what she actually fired, measures quality
(genius score), identifies which branches produce high-quality vs template
fires, and feeds that signal back into bonsai attention weights.

The loop:
  1. Pull last N genius-tagged fires from conversations.db
  2. Join with fountain_events in dynamic.db to get hot_branch per fire
  3. Compute mean genius score per branch (high = grounded, low = template)
  4. Write quality bonuses/penalties directly to bonsai_branches.focus_num
     in dynamic.db — same mechanism as _STARVE_BONUS in bonsai.py

This is genuine RSI: quality of output feeds back into what gets attended.
Not weight modification. Not code rewriting. But real: what she did well
shapes what she does next.

Run every 30 min via background thread or keepalive cron.
"""
from __future__ import annotations

import json
import logging
import sqlite3
import time
from pathlib import Path

log = logging.getLogger("theory_x.quality_synthesis")

# ── Config ────────────────────────────────────────────────────────────────────
_WINDOW_SECS   = 3 * 3600   # look back 3 hours of fires
_MIN_FIRES     = 3           # need at least this many fires per branch to trust signal
_HIGH_GENIUS   = 0.55        # score >= this = genuinely grounded fire
_LOW_GENIUS    = 0.25        # score <= this = template/drift fire
_SIGNAL_FILE   = Path("/home/rr/Desktop/nex5/data/quality_signal.json")


def _db(name: str) -> str:
    base = Path("/home/rr/Desktop/nex5/data")
    paths = {"conversations": base / "conversations.db",
             "dynamic":       base / "dynamic.db"}
    return str(paths[name])


def compute_branch_quality(window_secs: int = _WINDOW_SECS) -> dict[str, dict]:
    """
    Returns {branch_id: {mean_score, fire_count, verdict}}
    verdict: 'high' | 'low' | 'neutral'
    """
    cutoff = time.time() - window_secs
    try:
        # Pull genius scores with fountain_event_id from conversations.db
        c_con = sqlite3.connect(_db("conversations"), timeout=5)
        c_con.row_factory = sqlite3.Row
        tags = c_con.execute(
            "SELECT fountain_event_id, score FROM genius_tags "
            "WHERE tagged_at > ? ORDER BY tagged_at DESC",
            (cutoff,)
        ).fetchall()
        c_con.close()

        if not tags:
            return {}

        # Join with fountain_events in dynamic.db to get hot_branch
        d_con = sqlite3.connect(_db("dynamic"), timeout=5)
        d_con.row_factory = sqlite3.Row
        fids = [t["fountain_event_id"] for t in tags]
        placeholders = ",".join("?" * len(fids))
        events = d_con.execute(
            f"SELECT id, hot_branch FROM fountain_events WHERE id IN ({placeholders})",
            fids
        ).fetchall()
        d_con.close()

        # Build lookup: event_id -> branch
        branch_map = {e["id"]: e["hot_branch"] for e in events
                      if e["hot_branch"] and e["hot_branch"] != "quiescent"}

        # Aggregate scores per branch
        branch_scores: dict[str, list[float]] = {}
        for tag in tags:
            fid = tag["fountain_event_id"]
            branch = branch_map.get(fid)
            if branch:
                branch_scores.setdefault(branch, []).append(tag["score"])

        # Compute verdict per branch
        result = {}
        for branch, scores in branch_scores.items():
            if len(scores) < _MIN_FIRES:
                continue
            mean = sum(scores) / len(scores)
            high_frac = sum(1 for s in scores if s >= _HIGH_GENIUS) / len(scores)
            low_frac  = sum(1 for s in scores if s <= _LOW_GENIUS)  / len(scores)
            if high_frac >= 0.45:
                verdict = "high"
            elif low_frac >= 0.55:
                verdict = "low"
            else:
                verdict = "neutral"
            result[branch] = {
                "mean_score":  round(mean, 3),
                "fire_count":  len(scores),
                "high_frac":   round(high_frac, 3),
                "low_frac":    round(low_frac, 3),
                "verdict":     verdict,
            }
        return result

    except Exception as exc:
        log.warning("quality_synthesis.compute error: %s", exc)
        return {}


def apply_quality_signal(branch_quality: dict[str, dict]) -> dict:
    """Write quality bonuses/penalties to bonsai_branches in dynamic.db."""
    if not branch_quality:
        return {"applied": 0}

    applied = 0
    try:
        for branch, info in branch_quality.items():
            verdict = info["verdict"]
            if verdict == "high":
                        log.info("quality_synthesis: HIGH  %s (mean=%.2f, %d fires) -> 1.20x attention",
                         branch, info["mean_score"], info["fire_count"])
                applied += 1
            elif verdict == "low":
                log.info("quality_synthesis: LOW   %s (mean=%.2f, %d fires) -> 0.82x attention",
                         branch, info["mean_score"], info["fire_count"])
                applied += 1
    except Exception as exc:
        log.warning("quality_synthesis.apply error: %s", exc)

    return {"applied": applied}


def run_synthesis() -> dict:
    """One full synthesis pass. Call periodically."""
    t0 = time.time()
    quality = compute_branch_quality()
    result  = apply_quality_signal(quality)

    # Write signal file for inspection / HUD
    try:
        _SIGNAL_FILE.write_text(json.dumps({
            "ts": t0,
            "branches": quality,
            "applied": result["applied"],
        }, indent=2))
    except Exception:
        pass

    elapsed = time.time() - t0
    log.info("quality_synthesis: pass done in %.1fs — %d branches scored, %d adjusted",
             elapsed, len(quality), result["applied"])
    return {"quality": quality, "applied": result["applied"], "elapsed_s": elapsed}


def start_loop(interval_secs: int = 1800) -> None:
    """Start background synthesis loop — call once at startup."""
    import threading

    def _run():
        # First pass after 5 min (let her fire a few times first)
        time.sleep(300)
        while True:
            try:
                run_synthesis()
            except Exception as exc:
                log.error("quality_synthesis loop error: %s", exc)
            time.sleep(interval_secs)

    t = threading.Thread(target=_run, daemon=True, name="quality_synthesis")
    t.start()
    log.info("quality_synthesis loop started (interval=%ds)", interval_secs)


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    result = run_synthesis()
    print("\n=== QUALITY SYNTHESIS PASS ===")
    for branch, info in sorted(result["quality"].items(),
                                key=lambda x: -x[1]["mean_score"]):
        v = info["verdict"].upper()
        print(f"  [{v:7s}] {branch:20s} mean={info['mean_score']:.3f} "
              f"n={info['fire_count']:3d} "
              f"high={info['high_frac']:.0%} low={info['low_frac']:.0%}")
    print(f"\n  adjusted: {result['applied']} branches | "
          f"elapsed: {result['elapsed_s']:.1f}s")
