"""Quality Synthesis — NEX's RSI loop.

Perplexity Brain for NEX: reviews genius scores per branch, writes a quality
signal JSON file. The attention._magnitude_for function reads this file and
applies a multiplier: high-genius branches get 1.20x amplification on incoming
sense events (accumulate focus_num faster), low-genius get 0.82x dampening.

The loop:
  1. Pull last N genius-tagged fires from conversations.db
  2. Join with fountain_events in dynamic.db to get hot_branch per fire
  3. Compute mean genius score per branch
  4. Write data/quality_signal.json
  5. attention.py reads it every 5 min and applies multipliers at magnitude calc

Runs every 30 min via background thread started in generator.__init__.
"""
from __future__ import annotations

import json
import logging
import sqlite3
import time
from pathlib import Path

log = logging.getLogger("theory_x.quality_synthesis")

_WINDOW_SECS  = 3 * 3600
_MIN_FIRES    = 8          # was 3 — 5-fire samples were triggering LOW verdicts
                            # that then suppressed the very branch that needed
                            # more fires to recover. Require real data before judging.
_HIGH_GENIUS  = 0.55
_LOW_GENIUS   = 0.25
_MAX_DAMPENED_BRANCHES = 2  # never dampen more than 2 branches at once —
                            # protects diversity when many thin branches
                            # simultaneously look bad on small samples
_SIGNAL_FILE  = Path("/home/rr/Desktop/nex5/data/quality_signal.json")


def _db(name: str) -> str:
    base = Path("/home/rr/Desktop/nex5/data")
    return str({"conversations": base / "conversations.db",
                "dynamic":       base / "dynamic.db"}[name])


def compute_branch_quality(window_secs: int = _WINDOW_SECS) -> dict:
    cutoff = time.time() - window_secs
    try:
        c_con = sqlite3.connect(_db("conversations"), timeout=5)
        c_con.row_factory = sqlite3.Row
        tags = c_con.execute(
            "SELECT fountain_event_id, score FROM genius_tags "
            "WHERE tagged_at > ? ORDER BY tagged_at DESC", (cutoff,)
        ).fetchall()
        c_con.close()
        if not tags:
            return {}

        d_con = sqlite3.connect(_db("dynamic"), timeout=5)
        d_con.row_factory = sqlite3.Row
        fids = [t["fountain_event_id"] for t in tags]
        placeholders = ",".join("?" * len(fids))
        events = d_con.execute(
            f"SELECT id, hot_branch FROM fountain_events WHERE id IN ({placeholders})",
            fids
        ).fetchall()
        d_con.close()

        branch_map = {e["id"]: e["hot_branch"] for e in events
                      if e["hot_branch"] and e["hot_branch"] != "quiescent"}

        branch_scores: dict[str, list[float]] = {}
        for tag in tags:
            branch = branch_map.get(tag["fountain_event_id"])
            if branch:
                branch_scores.setdefault(branch, []).append(tag["score"])

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
                "mean_score": round(mean, 3),
                "fire_count": len(scores),
                "high_frac":  round(high_frac, 3),
                "low_frac":   round(low_frac, 3),
                "verdict":    verdict,
            }
        return result
    except Exception as exc:
        log.warning("quality_synthesis.compute error: %s", exc)
        return {}


def apply_quality_signal(branch_quality: dict) -> dict:
    applied = 0
    # Cap how many branches can be dampened simultaneously — protects
    # diversity from a cascade where every thin branch looks LOW at once.
    low_candidates = [(b, i) for b, i in branch_quality.items()
                       if i["verdict"] == "low"]
    low_candidates.sort(key=lambda x: x[1]["mean_score"])
    dampened_branches = {b for b, _ in low_candidates[:_MAX_DAMPENED_BRANCHES]}

    for branch, info in branch_quality.items():
        verdict = info["verdict"]
        if verdict == "high":
            log.info("quality_synthesis: HIGH  %s mean=%.2f n=%d -> 1.20x attention",
                     branch, info["mean_score"], info["fire_count"])
            applied += 1
        elif verdict == "low":
            if branch in dampened_branches:
                log.info("quality_synthesis: LOW   %s mean=%.2f n=%d -> 0.82x attention",
                         branch, info["mean_score"], info["fire_count"])
                applied += 1
            else:
                log.info("quality_synthesis: LOW   %s mean=%.2f n=%d -> neutral "
                         "(dampen cap reached, protecting diversity)",
                         branch, info["mean_score"], info["fire_count"])
    return {"applied": applied}


def run_synthesis() -> dict:
    t0 = time.time()
    quality = compute_branch_quality()
    result  = apply_quality_signal(quality)
    try:
        _SIGNAL_FILE.write_text(json.dumps({
            "ts": t0, "branches": quality, "applied": result["applied"],
        }, indent=2))
    except Exception:
        pass
    elapsed = time.time() - t0
    log.info("quality_synthesis: pass done %.1fs — %d branches scored %d adjusted",
             elapsed, len(quality), result["applied"])
    return {"quality": quality, "applied": result["applied"], "elapsed_s": elapsed}


def start_loop(interval_secs: int = 1800) -> None:
    import threading
    def _run():
        time.sleep(300)
        while True:
            try:
                run_synthesis()
            except Exception as exc:
                log.error("quality_synthesis loop error: %s", exc)
            time.sleep(interval_secs)
    threading.Thread(target=_run, daemon=True, name="quality_synthesis").start()
    log.info("quality_synthesis loop started (interval=%ds)", interval_secs)


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    result = run_synthesis()
    print("\n=== QUALITY SYNTHESIS PASS ===")
    for branch, info in sorted(result["quality"].items(),
                                key=lambda x: -x[1]["mean_score"]):
        print(f"  [{info['verdict']:7s}] {branch:20s} mean={info['mean_score']:.3f} "
              f"n={info['fire_count']:3d} high={info['high_frac']:.0%} low={info['low_frac']:.0%}")
    print(f"\n  adjusted: {result['applied']} | elapsed: {result['elapsed_s']:.1f}s")
