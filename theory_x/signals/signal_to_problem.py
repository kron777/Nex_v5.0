"""Signal → Problem daemon.

Fills the documented gap: signals fire detecting belief-graph events,
but nothing converted them into open problems for sustained attention.
This daemon does. Strict filters so open_problems doesn't flood.

Per SUSTAINED_ATTENTION_DESIGN.md §2 — "No trigger from belief graph."
This is the trigger.
"""
from __future__ import annotations
import json
import logging
import re
import sqlite3
import threading
import os
import time
from pathlib import Path

log = logging.getLogger("theory_x.signals.signal_to_problem")

BELIEFS_DB = Path("/home/rr/Desktop/nex5/data/beliefs.db")
CONVERSATIONS_DB = Path("/home/rr/Desktop/nex5/data/conversations.db")
DYNAMIC_DB = Path("/home/rr/Desktop/nex5/data/dynamic.db")

TICK_SECONDS = 120              # check every 2 minutes
MIN_CONFIDENCE = 0.40  # lowered from 0.65 to admit t6_promotion_burst           # confidence floor
DAILY_PROBLEM_CAP = 5           # at most 5 new problems opened per 24h
LOOKBACK_SECONDS = 21600        # 6 hours — survive quiet periods (Saturday mornings, etc)
DEDUPE_WINDOW_DAYS = 7          # don't open same-entity problem twice within a week

# Signal types that map to genuine inquiry-worthy belief-graph events.
# Excludes noise: branch_silence_anomaly, ngram_repetition, template_repetition.
_PROMOTABLE_TYPES = {
    "2_branch",            # entity appearing across 2 branches (~650/day, conf 0.7)
    "3_branch",            # entity appearing across 3 branches (~24/day, conf 0.9)
    "t6_promotion_burst",  # tier-6 burst (conf ~0.4, threshold lowered below)
    "pattern_recognition_burst",
    "cross_branch_convergence",
    "novel_arc",
    "concept_emergence",
}


def _ensure_actioned_column(cx: sqlite3.Connection) -> None:
    """Add 'actioned' column to signals table if missing.
    Lets us mark signals we've converted, avoiding re-processing.
    """
    cols = [r[1] for r in cx.execute("PRAGMA table_info(signals)")]
    if "actioned_at" not in cols:
        cx.execute("ALTER TABLE signals ADD COLUMN actioned_at REAL")
        cx.commit()
        log.info("added signals.actioned_at column")


def _extract_entity(payload: dict) -> str | None:
    """Pull the most distinctive noun-phrase from a signal payload."""
    if not isinstance(payload, dict):
        return None
    # Common payload fields
    for key in ("entity", "term", "concept", "theme", "subject", "title"):
        v = payload.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    # Burst signals: branches list, use first
    if isinstance(payload.get("branches"), list) and payload["branches"]:
        return str(payload["branches"][0])
    return None


# ── Problem-quality gate ─────────────────────────────────────────────────────
# Bare common words that fire as "entities" in headlines but produce fake
# research programs when opened as investigation problems.
_VAGUE_ENTITY_WORDS = frozenset({
    "dynamic", "multilingual", "static", "advanced", "new", "latest", "big",
    "low", "high", "fast", "slow", "smart", "global", "local", "digital",
    "modern", "future", "source", "data", "system", "model", "process",
    "signal", "output", "input", "result", "impact", "change", "update",
    "report", "study", "research", "analysis", "are", "is", "was", "were",
    "enhancing", "improving", "increasing", "expanding", "growing", "building",
    "making", "showing", "using", "show", "the", "and", "for", "cup", "world", "your", "army", "liva", "crypto", "our", "their", "us", "uk", "war", "new", "old", "top", "key",
})

def _entity_has_substance(entity: str | None) -> bool:
    """True if entity is specific enough to warrant an investigation problem."""
    if not entity or len(entity.strip()) < 2:
        return False
    e = entity.strip()
    if " " in e:
        return True   # multi-word entities always substantive
    return e.lower() not in _VAGUE_ENTITY_WORDS

def _compose_title(signal_type: str, entity: str | None, payload: dict) -> str:
    """Frame the signal as an actionable inquiry title."""
    if signal_type == "triple_cooccurrence" and entity:
        return f"What is '{entity}' doing across these domains?"
    if signal_type == "t6_promotion_burst":
        branches = payload.get("branches") or []
        branch = branches[0] if branches else "substrate"
        return f"Why is {branch} producing strong beliefs right now?"
    if signal_type == "pattern_recognition_burst":
        branches = payload.get("branches") or []
        branch = branches[0] if branches else "substrate"
        return f"What pattern is emerging in {branch}?"
    if signal_type == "cross_branch_convergence" and entity:
        return f"How does '{entity}' bridge these branches?"
    if signal_type == "novel_arc" and entity:
        return f"What does this new arc around '{entity}' mean?"
    if signal_type == "concept_emergence" and entity:
        return f"What is '{entity}'?"
    # Fallback
    if entity:
        return f"Signal: investigate '{entity}'"
    return f"Signal: {signal_type}"


def _compose_description(signal_type: str, payload: dict, sig_id: int) -> str:
    """Body of the problem — pretty-print the signal evidence."""
    pretty = json.dumps(payload, indent=2)[:800]
    return (
        f"Auto-opened from signal #{sig_id} (type: {signal_type}).\n\n"
        f"Evidence:\n{pretty}\n\n"
        f"This problem will accumulate observations as more sense events arrive."
    )


def _has_recent_dupe(cv_cx: sqlite3.Connection, entity: str, window_days: int) -> bool:
    """Only block re-open if a non-closed problem already covers this entity.
    2026-05-16: previously matched closed problems too, starving new opens
    after stale test problems accumulated."""
    if not entity:
        return False
    cutoff = time.time() - (window_days * 86400)
    row = cv_cx.execute(
        "SELECT id FROM open_problems "
        "WHERE state IN ('open','stuck') "
        "  AND last_touched_at > ? "
        "  AND (title LIKE ? OR description LIKE ?) "
        "LIMIT 1",
        (cutoff, f"%{entity}%", f"%{entity}%")
    ).fetchone()
    return row is not None


def _count_recent_opens(cv_cx: sqlite3.Connection, hours: int = 24) -> int:
    cutoff = time.time() - hours * 3600
    row = cv_cx.execute(
        "SELECT COUNT(*) FROM open_problems WHERE created_at > ?",
        (cutoff,)
    ).fetchone()
    return row[0] if row else 0


def signal_to_problem_tick() -> dict:
    """One pass. Convert eligible recent signals into open problems."""
    b_cx = sqlite3.connect(BELIEFS_DB, timeout=15)
    b_cx.row_factory = sqlite3.Row
    cv_cx = sqlite3.connect(CONVERSATIONS_DB, timeout=15)
    cv_cx.row_factory = sqlite3.Row

    try:
        _ensure_actioned_column(b_cx)

        # Check daily cap
        recent_opens = _count_recent_opens(cv_cx)
        if recent_opens >= DAILY_PROBLEM_CAP:
            log.debug("daily cap reached (%d), skipping tick", recent_opens)
            return {"considered": 0, "opened": 0, "skipped_cap": 1}

        cutoff = time.time() - LOOKBACK_SECONDS
        type_placeholders = ",".join("?" * len(_PROMOTABLE_TYPES))
        rows = b_cx.execute(
            f"SELECT id, detected_at, signal_type, payload, confidence "
            f"FROM signals "
            f"WHERE detected_at > ? "
            f"  AND signal_type IN ({type_placeholders}) "
            f"  AND confidence >= ? "
            f"  AND actioned_at IS NULL "
            f"ORDER BY confidence DESC, detected_at DESC "
            f"LIMIT 20",
            (cutoff, *_PROMOTABLE_TYPES, MIN_CONFIDENCE)
        ).fetchall()

        if not rows:
            return {"considered": 0, "opened": 0, "skipped_cap": 0}

        # JUNK-TOKEN SUPPRESSION (env-gated, default OFF): count how often each
        # entity recurs across this lookback window. One-off headline fragments
        # ('Papers','Nine','Netherlands') appear once; real recurring themes
        # ('Bitcoin') appear repeatedly. Used below to gate the fallback path.
        from collections import Counter as _Counter
        _entity_counts = _Counter()
        if os.environ.get("NEX5_SIG_QUALITY") == "1":
            for _s in rows:
                try:
                    _pl = json.loads(_s["payload"]) if _s["payload"] else {}
                except Exception:
                    _pl = {}
                _e = _extract_entity(_pl)
                if _e:
                    _entity_counts[_e.strip().lower()] += 1

        opened = 0
        skipped = 0
        remaining_cap = DAILY_PROBLEM_CAP - recent_opens

        for sig in rows:
            if remaining_cap <= 0:
                break
            try:
                payload = json.loads(sig["payload"]) if sig["payload"] else {}
            except Exception:
                payload = {}

            entity = _extract_entity(payload)

            if _has_recent_dupe(cv_cx, entity, DEDUPE_WINDOW_DAYS):
                # Mark actioned anyway so we don't keep re-checking
                b_cx.execute(
                    "UPDATE signals SET actioned_at=? WHERE id=?",
                    (time.time(), sig["id"])
                )
                skipped += 1
                continue

            title = _compose_title(sig["signal_type"], entity, payload)
            if (title.startswith("Signal: investigate '")
                    and not _entity_has_substance(entity)):
                # vague bare-word entity — blocks unconditionally before open
                b_cx.execute("UPDATE signals SET actioned_at=? WHERE id=?",
                             (time.time(), sig["id"]))
                log.debug("quality_gate: blocked vague entity %r", entity)
                skipped += 1
                continue
            if (os.environ.get("NEX5_SIG_QUALITY") == "1"
                    and title.startswith("Signal: investigate '")
                    and entity
                    and _entity_counts.get(entity.strip().lower(), 0) < 2):
                # one-off, uncorroborated headline fragment — don't open a
                # sustained problem for it; mark actioned so we stop re-checking.
                b_cx.execute(
                    "UPDATE signals SET actioned_at=? WHERE id=?",
                    (time.time(), sig["id"])
                )
                skipped += 1
                continue
            desc = _compose_description(sig["signal_type"], payload, sig["id"])
            now = time.time()

            try:
                cv_cx.execute(
                    "INSERT INTO open_problems "
                    "(title, description, state, created_at, last_touched_at, "
                    " plan, observations, tags) "
                    "VALUES (?, ?, 'open', ?, ?, '', '[]', ?)",
                    (title, desc, now, now,
                     json.dumps(["auto", f"signal:{sig['signal_type']}"]))
                )
                b_cx.execute(
                    "UPDATE signals SET actioned_at=? WHERE id=?",
                    (now, sig["id"])
                )
                opened += 1
                remaining_cap -= 1
                log.info(
                    "opened problem from signal %s (%s, conf=%.2f): %s",
                    sig["id"], sig["signal_type"], sig["confidence"], title[:80]
                )
            except sqlite3.Error as e:
                log.warning("INSERT open_problem failed for sig %s: %s",
                            sig["id"], e)
                skipped += 1

        b_cx.commit()
        cv_cx.commit()
        return {"considered": len(rows), "opened": opened, "skipped_dupe": skipped}
    finally:
        b_cx.close()
        cv_cx.close()


def signal_to_problem_loop(state, stop: threading.Event) -> None:
    """Daemon entry — matches stage2_dynamic's (state, stop) contract."""
    log.info(
        "signal_to_problem loop started "
        "(tick=%ds, conf>=%.2f, cap=%d/24h)",
        TICK_SECONDS, MIN_CONFIDENCE, DAILY_PROBLEM_CAP
    )
    while not stop.is_set():
        try:
            stats = signal_to_problem_tick()
            if stats.get("opened", 0) > 0:
                log.info("signal_to_problem: %s", stats)
        except Exception as e:
            log.error("signal_to_problem tick failed: %s: %s",
                      type(e).__name__, str(e)[:200])
        stop.wait(TICK_SECONDS)
    log.info("signal_to_problem loop stopped")
