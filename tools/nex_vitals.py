#!/usr/bin/env python3
"""nex_vitals.py — READ-ONLY longitudinal "vitals" instrument for NEX v5.0.

READ-ONLY. This tool NEVER writes to any NEX database. It opens
data/{dynamic,beliefs,conversations}.db with ``file:...?mode=ro`` (uri=True),
closes every handle, and prints a human-readable vitals report to stdout. The
ONLY side effect it can ever have is appending exactly ONE JSON line to a
vitals log, and that happens solely behind an explicit ``--log [PATH]`` flag
(default ``logs/vitals_log.jsonl``). With no flag, no file is written.

It is a SIBLING to scripts/trajectory.py (which it does not duplicate): it
reuses trajectory's append-only JSONL discipline and its 2-sigma band rule
(flag a metric only when it breaks NEX's OWN variance, |z| >= 2), and reads
trajectory's latest log line for QUALITY/APERTURE/LIVENESS/GROOVE rather than
recomputing them. It ADDS the kleshas/register battery, per-mode decomposition,
topic-mix, the held-out register detector, within-window controls, and the
arm-ledger overlay — see nex_vitals_monitor_spec.txt (constraints C1-C8).

C2 (FROZEN + VERSIONED, BY COPY): the measurement primitives are PINNED COPIES
inside this module — the fidelity tokenizer + furniture list (frozen copy of
crystallizer.py:66-82), the DF-over-window primitive (frozen copy of
generator.py:122-141), the structural attending-template opener regex (frozen
copy of the attribution_marker.py / generator _FRAME_GATE_OPENER_RX family),
and the held-out register phrase set. They are NOT imported from live code, so
if that code drifts these historical numbers do NOT silently move. Every change
to a primitive is a logged discontinuity via INSTRUMENT_VERSION, never a silent
refit. For maxDF* this tool MAY call corpus_convergence.max_df_star (so the
alarm has one definition) but it records register_exclusion.json's version and
content hash alongside, so a refit of that list shows as a visible
discontinuity.

Usage:
  python3 tools/nex_vitals.py                       # tonight's read, stdout only
  python3 tools/nex_vitals.py --window 300          # last 300 fires
  python3 tools/nex_vitals.py --since 1700000000    # only fires after this epoch
  python3 tools/nex_vitals.py --trip-log SOAK_LOG --trip-tag "frame_gate:"  # within-window control
  python3 tools/nex_vitals.py --log                 # ALSO append one line to logs/vitals_log.jsonl
  python3 tools/nex_vitals.py --log /path/file.jsonl
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import math
import os
import re
import sqlite3
import statistics
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Optional

# ── instrument identity (C2: every emitted row carries this) ────────────────
# Bump this on ANY change to a frozen primitive below, so historical numbers do
# not silently move — a detector change is a logged discontinuity, not a re-fit.
INSTRUMENT_VERSION = "nex_vitals/1.0.0+2026-10-09"

# ── root-relative paths (warrant_validate.py house style; mode=ro at use) ───
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REGISTER_EXCLUSION = os.path.join(
    ROOT, "theory_x", "stage6_fountain", "register_exclusion.json")
_KEEPALIVE = os.path.join(ROOT, "nex_keepalive.sh")
_TRAJECTORY_LOG = os.path.join(ROOT, "logs", "trajectory_log.jsonl")
DEFAULT_LOG = os.path.join(ROOT, "logs", "vitals_log.jsonl")

Z_THRESHOLD = 2.0          # sigma; |z| >= this breaks band (trajectory.py rule)
WINDOW = 200               # default recent-fire window (matches subject_fidelity)
TOPN = 15                  # topic-mix size
TRIP_TOL_S = 2.0           # within-window: a fire is "touched" if a trip marker
                           # falls within this many seconds of its ts
_HIST_MIN = 3              # min history points before a 2-sigma flag is possible


def _data_dir() -> str:
    """Data dir, honouring NEX5_DATA_DIR (substrate.paths convention) else the
    ROOT-relative <repo>/data. Resolved at use time, never bound at import."""
    return os.environ.get("NEX5_DATA_DIR") or os.path.join(ROOT, "data")


def _db(name: str) -> str:
    return os.path.join(_data_dir(), f"{name}.db")


def _ro(path: str) -> sqlite3.Connection:
    """Open a DB strictly read-only. mode=ro makes any write raise."""
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def _fmt_ts(ts: float) -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(ts))


def _rg(row, key):
    """Column access that works for sqlite3.Row and dict; None if absent."""
    try:
        return row[key]
    except Exception:
        return None


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║ FROZEN PRIMITIVES — pinned copies (C2). Do NOT import from live code.      ║
# ╚══════════════════════════════════════════════════════════════════════════╝

# Frozen copy of crystallizer.py:66-82 (_FIDELITY_FURNITURE + _fidelity_tokens),
# GENIUS_FIDELITY_BASELINE.md section 1. Pinned so a live edit cannot move the
# content-grasp / topic-mix / TTR numbers retroactively.
_FROZEN_FURNITURE = frozenset("""
a an the and or but of to in on at for from by with as is are was were be been it its this that
these those into over under after before amid about up down out off than then new not no has have
had will can could would should may might says say said how why what who when where which more most
less first last you your i we our they their he she his her them uk us update live exclusive report
reports reveals warns here just also one two get gets make makes take takes back still now via amp
per cent""".split())
_FROZEN_POSS = re.compile(r"(?:'s|s'|’s|s’)\b")
_FROZEN_TOK = re.compile(r"[a-z0-9]+")


def _frozen_fidelity_tokens(text: Optional[str]) -> list:
    """FROZEN copy of crystallizer._fidelity_tokens: lowercase, strip
    possessives, drop sub-3-char tokens and furniture. Pure; [] on falsy."""
    stripped = _FROZEN_POSS.sub("", (text or "").lower())
    return [t for t in _FROZEN_TOK.findall(stripped)
            if len(t) >= 3 and t not in _FROZEN_FURNITURE]


# Frozen copy of generator.py:122-141 (_dominant_topic_terms / DF-over-window).
_FROZEN_CARRY_TOPIC_DF = 0.40
_FROZEN_CARRY_TOPIC_MIN_FIRES = 10


def _frozen_dominant_topic_terms(thoughts, df_frac: float = _FROZEN_CARRY_TOPIC_DF) -> list:
    """FROZEN copy of generator._dominant_topic_terms: content tokens whose
    document-frequency across `thoughts` is >= df_frac. Pure; [] on empty or
    sub-_FROZEN_CARRY_TOPIC_MIN_FIRES input; fail-safe []."""
    try:
        docs = [set(_frozen_fidelity_tokens(t)) for t in (thoughts or []) if (t or "").strip()]
        n = len(docs)
        if n < _FROZEN_CARRY_TOPIC_MIN_FIRES:
            return []
        df = Counter()
        for d in docs:
            df.update(d)
        thresh = df_frac * n
        return [tok for tok, c in df.items() if c >= thresh]
    except Exception:
        return []


# FROZEN held-out register phrase set — v1 seed (C1: intervention-DISJOINT; shares
# NO vocabulary with the live NEX5_FRAME_DEDUP / NEX5_FRAME_GATE ban list
# _FRAME_STOCK_PHRASES — "this item is about", "the curious dance", ... — so a
# "register fell" read is never circular with the intervention's own phrases).
_FROZEN_HELD_OUT = (
    "this item talks about",
    "makes me wonder",
    "resonates with my",
    "ground stance",
    "feels surreal",
)

# FROZEN structural attending-template opener (anchored), the family of
# attribution_marker.py:25 and generator._FRAME_GATE_OPENER_RX. Anchored to the
# start (^\W* tolerates leading quotes/space) so mid-clause uses do NOT trip.
_FROZEN_OPENER_RX = re.compile(
    r"^\W*(?:this item (?:is about|talks about|states|discusses|describes|reports|claims|introduces|notes)"
    r"|the feed (?:is about|discusses|reports|states|notes|describes))",
    re.IGNORECASE,
)


def held_out_hit(text: Optional[str]) -> bool:
    """True iff `text` contains any FROZEN held-out register phrase (case-
    insensitive substring). Pure; never raises."""
    if not text:
        return False
    low = text.lower()
    return any(p in low for p in _FROZEN_HELD_OUT)


def opener_hit(text: Optional[str]) -> bool:
    """True iff `text` opens with the FROZEN structural attending template
    (anchored). Pure; never raises."""
    if not text:
        return False
    return _FROZEN_OPENER_RX.match(text) is not None


# ── distribution helper ─────────────────────────────────────────────────────

def _pct(sorted_xs: list, q: float) -> Optional[float]:
    """Linear-interpolation percentile over an already-sorted list; None if
    empty. Deterministic."""
    if not sorted_xs:
        return None
    if len(sorted_xs) == 1:
        return float(sorted_xs[0])
    pos = (len(sorted_xs) - 1) * (q / 100.0)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return float(sorted_xs[lo])
    frac = pos - lo
    return float(sorted_xs[lo]) * (1 - frac) + float(sorted_xs[hi]) * frac


def _dist(values: list) -> dict:
    """p10/p50/p90/mean/min/max over `values` (non-None); all None if empty."""
    xs = sorted(float(v) for v in values if v is not None)
    if not xs:
        return {"n": 0, "min": None, "max": None, "mean": None,
                "p10": None, "p50": None, "p90": None}
    return {
        "n": len(xs),
        "min": xs[0],
        "max": xs[-1],
        "mean": sum(xs) / len(xs),
        "p10": _pct(xs, 10),
        "p50": _pct(xs, 50),
        "p90": _pct(xs, 90),
    }


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║ FIRE BATTERY — pure, over a supplied list of fire rows                     ║
# ╚══════════════════════════════════════════════════════════════════════════╝

def _norm_mode(m) -> str:
    """Normalise a fountain mode to one of DRIFT/ARGUE/EXPLAIN/null."""
    if m is None:
        return "null"
    s = str(m).strip()
    return s if s else "null"


def compute_fire_metrics(fires) -> dict:
    """The per-window fire battery over `fires` (row-likes with keys ts,
    thought, mode, word_count). PURE. Exposes raw hit COUNTS so an aggregate
    equals the exact mode-weighted recombination of its parts (C6/V2).

      held_out_hits/rate      — FROZEN held-out register detector (C1)
      opener_hits/rate        — FROZEN structural attending-template opener
      words{...}              — word_count p10/p50/p90/mean/min/max
      words_split_mismatch    — #fires where word_count != len(thought.split())
      ttr                     — type-token ratio (aliveness, C4)
      distinct_opener_rate    — distinct 5-word openers / n (aliveness, C4)
    """
    n = 0
    held = 0
    opens = 0
    wcs = []
    mismatch = 0
    all_tokens = []
    openers = []
    for r in fires:
        n += 1
        thought = _rg(r, "thought")
        if held_out_hit(thought):
            held += 1
        if opener_hit(thought):
            opens += 1
        wc = _rg(r, "word_count")
        if wc is not None:
            wcs.append(wc)
        if thought is not None:
            words = str(thought).split()
            if wc is not None and wc != len(words):
                mismatch += 1
            all_tokens.extend(_frozen_fidelity_tokens(thought))
            openers.append(" ".join(str(thought).lower().split()[:5]))

    ttr = (len(set(all_tokens)) / len(all_tokens)) if all_tokens else None
    distinct_opener_rate = (len(set(openers)) / len(openers)) if openers else None

    return {
        "n": n,
        "held_out_hits": held,
        "held_out_rate": (held / n) if n else None,
        "opener_hits": opens,
        "opener_rate": (opens / n) if n else None,
        "words": _dist(wcs),
        "words_split_mismatch": mismatch,
        "ttr": ttr,
        "distinct_opener_rate": distinct_opener_rate,
    }


def per_mode_metrics(fires) -> dict:
    """compute_fire_metrics split by fountain mode (C6: MANDATORY, never
    aggregate-only). Always returns the four canonical modes as keys (n=0 if
    absent) plus any other mode strings present."""
    buckets: dict = {"DRIFT": [], "ARGUE": [], "EXPLAIN": [], "null": []}
    for r in fires:
        buckets.setdefault(_norm_mode(_rg(r, "mode")), []).append(r)
    return {m: compute_fire_metrics(rows) for m, rows in buckets.items()}


def content_grasp(fires) -> dict:
    """Top content-token document-frequency + dominant share over the window,
    FROZEN tokens, NO exclusion (the raga/grasping read)."""
    docs = [set(_frozen_fidelity_tokens(_rg(r, "thought"))) for r in fires]
    docs = [d for d in docs if d]
    n = len(docs)
    if n == 0:
        return {"n": 0, "dominant_token": None, "dominant_share": None, "top": []}
    df = Counter()
    for d in docs:
        df.update(d)
    top = [(tok, c, c / n) for tok, c in df.most_common(5)]
    return {
        "n": n,
        "dominant_token": top[0][0],
        "dominant_share": top[0][2],
        "top": top,
    }


def topic_mix(fires, exclusion: Optional[set], topn: int = TOPN) -> dict:
    """Top-N content tokens by document-frequency, furniture (via tokenizer) +
    register excluded (C7). Separates a register/length change (attributable to
    an intervention) from topic drift."""
    excl = exclusion or set()
    docs = [set(_frozen_fidelity_tokens(_rg(r, "thought"))) - excl for r in fires]
    docs = [d for d in docs if d]
    n = len(docs)
    if n == 0:
        return {"n": 0, "top": []}
    df = Counter()
    for d in docs:
        df.update(d)
    top = [{"token": tok, "df_count": c, "df_share": c / n}
           for tok, c in df.most_common(topn)]
    return {"n": n, "top": top}


# ── within-window control (C8) ──────────────────────────────────────────────

def partition_touched(fires, markers, tol: float = TRIP_TOL_S):
    """Split `fires` into (touched, untouched) by a trip-marker timestamp list.
    A fire is TOUCHED iff some marker falls within `tol` seconds of its ts. The
    untouched remainder is the concurrent natural baseline. Exact given markers
    (V3). Pure."""
    touched, untouched = [], []
    ms = list(markers or [])
    for r in fires:
        t = _rg(r, "ts")
        hit = t is not None and any(abs(float(t) - float(m)) <= tol for m in ms)
        (touched if hit else untouched).append(r)
    return touched, untouched


def within_window_split(fires, markers, tol: float = TRIP_TOL_S) -> dict:
    """Every fire metric computed twice: on the touched fires vs the untouched
    concurrent baseline (C8)."""
    touched, untouched = partition_touched(fires, markers, tol)
    return {
        "tol_s": tol,
        "n_touched": len(touched),
        "n_untouched": len(untouched),
        "touched": compute_fire_metrics(touched),
        "untouched": compute_fire_metrics(untouched),
    }


def parse_trip_markers(path: str, tag: str) -> list:
    """Best-effort: timestamps of lines in a SOAK_LOG containing `tag` (e.g.
    "frame_gate:"). Parses a leading 'YYYY-MM-DD HH:MM:SS' (UTC) or a leading
    epoch float. Tolerates a missing/garbled file (returns [])."""
    out: list = []
    try:
        with open(path, "r", errors="replace") as fh:
            for line in fh:
                if tag not in line:
                    continue
                ts = _line_ts(line)
                if ts is not None:
                    out.append(ts)
    except Exception:
        return []
    return out


def _line_ts(line: str) -> Optional[float]:
    m = re.match(r"\s*(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2})", line)
    if m:
        try:
            dt = datetime.datetime.strptime(m.group(1).replace("T", " "),
                                            "%Y-%m-%d %H:%M:%S")
            return dt.replace(tzinfo=datetime.timezone.utc).timestamp()
        except Exception:
            pass
    m = re.match(r"\s*(\d{9,10}(?:\.\d+)?)\b", line)
    if m:
        try:
            return float(m.group(1))
        except Exception:
            pass
    return None


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║ DB READERS — all read-only, all best-effort                                ║
# ╚══════════════════════════════════════════════════════════════════════════╝

def load_fires(db_path: Optional[str] = None, window: int = WINDOW,
               since: Optional[float] = None, until: Optional[float] = None) -> list:
    """The fires, oldest first. With `since`/`until` returns all fires in
    (since, until]; otherwise the most-recent `window` fires. Read-only; [] if the
    table or DB is absent. The time bounds enable RETROSPECTIVE per-day reads over
    the existing history — the frozen detectors stay identical across windows, so
    a historical day is directly comparable to tonight."""
    path = db_path or _db("dynamic")
    if not os.path.exists(path):
        return []
    conn = _ro(path)
    try:
        if since is not None or until is not None:
            clauses, params = [], []
            if since is not None:
                clauses.append("ts > ?")
                params.append(since)
            if until is not None:
                clauses.append("ts <= ?")
                params.append(until)
            rows = conn.execute(
                "SELECT id, ts, thought, word_count, mode, focal_item "
                "FROM fountain_events WHERE " + " AND ".join(clauses) +
                " ORDER BY ts", params
            ).fetchall()
            return list(rows)
        rows = conn.execute(
            "SELECT id, ts, thought, word_count, mode, focal_item "
            "FROM fountain_events ORDER BY ts DESC LIMIT ?", (window,)
        ).fetchall()
        return list(reversed(rows))
    except Exception:
        return []
    finally:
        conn.close()


def register_info() -> dict:
    """register_exclusion.json's version + content hash + terms (C2: a refit
    shows as a visible discontinuity, not a silent shift). Best-effort."""
    try:
        with open(_REGISTER_EXCLUSION, "rb") as fh:
            raw = fh.read()
        data = json.loads(raw.decode("utf-8"))
        return {
            "available": True,
            "version": data.get("version"),
            "fitted_on": data.get("fitted_on"),
            "n_terms": data.get("n_terms", len(data.get("terms", []))),
            "sha256": hashlib.sha256(raw).hexdigest()[:16],
            "terms": set(data.get("terms", [])),
        }
    except Exception:
        return {"available": False, "version": None, "sha256": None, "terms": set()}


def maxdf_reading(beliefs_db: Optional[str] = None, window: int = 50) -> dict:
    """maxDF* corpus-convergence over crystallized beliefs (beliefs.db,
    source='fountain_insight'). Calls the LIVE corpus_convergence.max_df_star so
    the alarm keeps one definition (C2), but only if beliefs.db exists; the
    register hash is recorded separately by the caller. Best-effort — degrades
    to 'unavailable' with a reason."""
    path = beliefs_db or _db("beliefs")
    if not os.path.exists(path):
        return {"available": False, "reason": "no beliefs.db"}
    try:
        if ROOT not in sys.path:
            sys.path.insert(0, ROOT)
        from theory_x.stage6_fountain import corpus_convergence as cc  # lazy
        r = cc.max_df_star(db_path=path, window=window)
        return {
            "available": True,
            "max_df_star": r.get("max_df_star"),
            "token": r.get("token"),
            "doc_count": r.get("doc_count"),
            "n": r.get("n"),
            "threshold": r.get("threshold"),
            "breach": r.get("breach"),
            "top": r.get("top"),
        }
    except Exception as e:
        return {"available": False, "reason": f"{type(e).__name__}: {e}"}


def surprise_reading(db_path: Optional[str] = None,
                     since: Optional[float] = None, n_fires: int = 0) -> dict:
    """surprise_events rate + mean (dynamic.db). Best-effort; tolerates a
    missing table/column. 'rate' = surprises per fire over the window when a
    fire count is known."""
    path = db_path or _db("dynamic")
    if not os.path.exists(path):
        return {"available": False, "reason": "no dynamic.db"}
    conn = _ro(path)
    try:
        cols = {c["name"] for c in conn.execute(
            "PRAGMA table_info(surprise_events)").fetchall()}
        if "surprise_score" not in cols:
            return {"available": False, "reason": "no surprise_events.surprise_score"}
        # surprise_events' time column is triggered_at (not ts); accept either.
        tcol = "ts" if "ts" in cols else ("triggered_at" if "triggered_at" in cols else None)
        if since is not None and tcol:
            rows = conn.execute(
                f"SELECT surprise_score FROM surprise_events WHERE {tcol} > ?",
                (since,)).fetchall()
        else:
            rows = conn.execute("SELECT surprise_score FROM surprise_events").fetchall()
        scores = [r[0] for r in rows if r[0] is not None]
        if not scores:
            return {"available": True, "n": 0, "mean": None, "rate": None}
        return {
            "available": True,
            "n": len(scores),
            "mean": sum(scores) / len(scores),
            "rate": (len(scores) / n_fires) if n_fires else None,
        }
    except Exception as e:
        return {"available": False, "reason": f"{type(e).__name__}: {e}"}
    finally:
        conn.close()


def mood_reading(db_path: Optional[str] = None) -> dict:
    """Latest mood/valence from affect_state (conversations.db). Best-effort;
    tolerates a missing table/column."""
    path = db_path or _db("conversations")
    if not os.path.exists(path):
        return {"available": False, "reason": "no conversations.db"}
    conn = _ro(path)
    try:
        cols = [c["name"] for c in conn.execute(
            "PRAGMA table_info(affect_state)").fetchall()]
        if not cols:
            return {"available": False, "reason": "no affect_state"}
        pick = next((c for c in ("mood", "valence", "affect", "mood_valence")
                     if c in cols), None)
        if pick is None:
            return {"available": False, "reason": "no mood/valence column"}
        order = "ts" if "ts" in cols else ("rowid")
        row = conn.execute(
            f"SELECT {pick} FROM affect_state ORDER BY {order} DESC LIMIT 1").fetchone()
        return {"available": True, "column": pick,
                "latest": (row[0] if row else None)}
    except Exception as e:
        return {"available": False, "reason": f"{type(e).__name__}: {e}"}
    finally:
        conn.close()


def momentum_reading(db_path: Optional[str] = None) -> dict:
    """carry_count distribution + exhaustion (>3) from momentum (dynamic.db).
    Best-effort; tolerates a missing table/column."""
    path = db_path or _db("dynamic")
    if not os.path.exists(path):
        return {"available": False, "reason": "no dynamic.db"}
    conn = _ro(path)
    try:
        cols = {c["name"] for c in conn.execute(
            "PRAGMA table_info(momentum)").fetchall()}
        if "carry_count" not in cols:
            return {"available": False, "reason": "no momentum.carry_count"}
        rows = conn.execute("SELECT carry_count FROM momentum").fetchall()
        vals = [r[0] for r in rows if r[0] is not None]
        return {
            "available": True,
            "dist": _dist(vals),
            "n_exhausted": sum(1 for v in vals if v > 3),
        }
    except Exception as e:
        return {"available": False, "reason": f"{type(e).__name__}: {e}"}
    finally:
        conn.close()


# ── arm-ledger overlay (C8) ─────────────────────────────────────────────────

def _live_env() -> Optional[dict]:
    """The NEX5_* (and MOLTBOOK_DRY_RUN) env of the live process, from
    /proc/<pid>/environ (pid in ~/.nex/nex.pid). None if unreachable (a cloud
    checkout has no ~/.nex)."""
    try:
        with open(os.path.expanduser("~/.nex/nex.pid")) as fh:
            pid = fh.read().strip()
        with open(f"/proc/{pid}/environ", "rb") as fh:
            blob = fh.read()
        out = {}
        for tok in blob.split(b"\x00"):
            s = tok.decode(errors="replace")
            if "=" not in s:
                continue
            k, v = s.split("=", 1)
            if k.startswith("NEX5_") or k == "MOLTBOOK_DRY_RUN":
                out[k] = v
        return out
    except Exception:
        return None


def _declared_env() -> Optional[dict]:
    """The NEX5_* (and MOLTBOOK_DRY_RUN) env declared on nex_keepalive.sh's
    run.py launch line. None if unreadable. Reconstructs the backslash-continued
    command so it never picks up assignments mentioned in comments."""
    try:
        lines = open(_KEEPALIVE).read().splitlines()
    except Exception:
        return None
    idx = next((i for i, l in enumerate(lines)
                if "run.py" in l and ("${VENV}" in l or "run.py >>" in l)), None)
    if idx is None:
        return None
    start = idx
    while start - 1 >= 0 and lines[start - 1].rstrip().endswith("\\"):
        start -= 1
    cmd = " ".join(lines[start:idx + 1])
    toks = re.findall(r"\b(NEX5_[A-Z0-9_]+|MOLTBOOK_DRY_RUN)=(\S+)", cmd)
    return {k: v for k, v in toks} if toks else None


def _power_state() -> str:
    nex_dir = os.path.expanduser("~/.nex")
    if not os.path.isdir(nex_dir):
        return "unavailable"
    return "STANDBY" if os.path.exists(os.path.join(nex_dir, "STANDBY")) else "AWAKE"


def arm_ledger() -> dict:
    """live NEX5_* set, declared set, their DIFF, and power state (C8). Every
    piece best-effort; on a cloud checkout (no ~/.nex) live/diff are None and
    the overlay reports 'arm-ledger unavailable'."""
    live = _live_env()
    declared = _declared_env()
    power = _power_state()
    diff = None
    if live is not None and declared is not None:
        lk, dk = set(live), set(declared)
        diff = {
            "live_only": sorted(lk - dk),
            "declared_only": sorted(dk - lk),
            "value_mismatch": sorted(
                k for k in (lk & dk) if live[k] != declared[k]),
        }
    return {
        "available": not (live is None and declared is None),
        "live": live,
        "declared": declared,
        "diff": diff,
        "power": power,
    }


# ── trajectory ref (read the sibling's latest line; do not recompute) ───────

def trajectory_ref() -> Optional[dict]:
    """The latest line of scripts/trajectory.py's log (QUALITY/APERTURE/
    LIVENESS/GROOVE). Best-effort; None if absent."""
    try:
        if not os.path.exists(_TRAJECTORY_LOG):
            return None
        last = None
        with open(_TRAJECTORY_LOG, "r", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    last = line
        if not last:
            return None
        row = json.loads(last)
        return {
            "when_utc": row.get("when_utc"),
            "overall": row.get("overall"),
            "axes": {k: v.get("verdict") for k, v in (row.get("axes") or {}).items()},
        }
    except Exception:
        return None


# ── 2-sigma flags (trajectory.py band discipline, bootstrapped from own log) ─

def _probes(aggregate: dict) -> dict:
    """The scalar metrics eligible for a 2-sigma flag, flattened."""
    w = aggregate.get("words") or {}
    md = aggregate.get("maxdf") or {}
    su = aggregate.get("surprise") or {}
    return {
        "held_out_rate": aggregate.get("held_out_rate"),
        "opener_rate": aggregate.get("opener_rate"),
        "words_mean": w.get("mean"),
        "ttr": aggregate.get("ttr"),
        "distinct_opener_rate": aggregate.get("distinct_opener_rate"),
        "maxdf_star": md.get("max_df_star") if md.get("available") else None,
        "surprise_rate": su.get("rate") if su.get("available") else None,
        "surprise_mean": su.get("mean") if su.get("available") else None,
    }


# Pairing (C4, anti-Goodhart): a suppression metric falling is only "good" if
# its paired aliveness metric holds. Maps a suppression probe -> its aliveness
# partners; a DOWN-flag on the suppression metric whose partner also fell DOWN
# is annotated as NOT an improvement.
_PAIRED_ALIVENESS = {
    "held_out_rate": ("words_mean", "ttr", "distinct_opener_rate"),
    "opener_rate": ("words_mean", "ttr", "distinct_opener_rate"),
}


def _log_history(log_path: str) -> list:
    """Prior vitals rows, for bootstrapping bands. Read-only; [] if absent."""
    try:
        if not os.path.exists(log_path):
            return []
        rows = []
        with open(log_path, "r", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except Exception:
                    continue
        return rows
    except Exception:
        return []


def two_sigma_flags(aggregate: dict, history_rows: list) -> dict:
    """Flag each scalar whose current value breaks |z| >= 2 of its OWN history
    in the vitals log. Tolerates empty/short history (then no flags). Applies
    the C4 pairing caution."""
    cur = _probes(aggregate)
    series: dict = {k: [] for k in cur}
    for row in history_rows:
        hp = _probes(row.get("aggregate") or {})
        for k, v in hp.items():
            if v is not None:
                series[k].append(v)

    flags = []
    down = set()
    for k, v in cur.items():
        hist = series.get(k, [])
        if v is None or len(hist) < _HIST_MIN:
            continue
        mean = statistics.mean(hist)
        sd = statistics.stdev(hist) if len(hist) >= 2 else 0.0
        if sd <= 0:
            continue
        z = (v - mean) / sd
        if abs(z) >= Z_THRESHOLD:
            direction = "up" if z > 0 else "down"
            flags.append({"metric": k, "value": v, "mean": mean,
                          "stdev": sd, "z": z, "direction": direction})
            if direction == "down":
                down.add(k)

    cautions = []
    for supp, partners in _PAIRED_ALIVENESS.items():
        if supp in down:
            fell = [p for p in partners if p in down]
            if fell:
                cautions.append(
                    f"{supp} fell out of band but paired aliveness also fell "
                    f"({', '.join(fell)}) -> NOT an improvement (C4)")
    return {"insufficient_history": not history_rows, "flags": flags,
            "cautions": cautions}


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║ ORCHESTRATION                                                              ║
# ╚══════════════════════════════════════════════════════════════════════════╝

def build_result(dynamic_db: Optional[str] = None,
                 beliefs_db: Optional[str] = None,
                 conversations_db: Optional[str] = None,
                 window: int = WINDOW,
                 since: Optional[float] = None,
                 topn: int = TOPN,
                 trip_markers: Optional[list] = None,
                 trip_tol: float = TRIP_TOL_S,
                 now_ts: Optional[float] = None,
                 history_log: Optional[str] = None) -> dict:
    """Compute the full vitals result. PURE of side effects — no writes, reads
    only. Returns the dict that the report renders and (opt-in) the log row is
    drawn from."""
    now_ts = time.time() if now_ts is None else now_ts
    fires = load_fires(dynamic_db, window, since)
    reg = register_info()

    mode_counts = Counter(_norm_mode(_rg(r, "mode")) for r in fires)

    aggregate = compute_fire_metrics(fires)
    aggregate["content_grasp"] = content_grasp(fires)
    aggregate["maxdf"] = maxdf_reading(beliefs_db)
    aggregate["register_exclusion"] = {
        "available": reg["available"], "version": reg.get("version"),
        "fitted_on": reg.get("fitted_on"), "n_terms": reg.get("n_terms"),
        "sha256": reg.get("sha256"),
    }
    # Scope surprise to the SAME window as the fires. Without this, a "last N
    # fires" run (since=None) reads ALL surprise_events, so rate (= events /
    # window-fires) and mean are all-time, not window-scoped — not comparable
    # across snapshots. In window mode, derive the floor from the oldest fire.
    _fire_floor = min((_rg(r, "ts") for r in fires if _rg(r, "ts") is not None),
                      default=None)
    _surprise_since = since if since is not None else _fire_floor
    aggregate["surprise"] = surprise_reading(dynamic_db, _surprise_since, len(fires))
    aggregate["mood"] = mood_reading(conversations_db)
    aggregate["momentum"] = momentum_reading(dynamic_db)

    per_mode = per_mode_metrics(fires)
    mix = topic_mix(fires, reg.get("terms"), topn)

    within = None
    if trip_markers is not None:
        within = within_window_split(fires, trip_markers, trip_tol)

    traj = trajectory_ref()

    hist_path = history_log or DEFAULT_LOG
    flags = two_sigma_flags(aggregate, _log_history(hist_path))

    return {
        "ts": now_ts,
        "when_utc": _fmt_ts(now_ts),
        "instrument_version": INSTRUMENT_VERSION,
        "window": {
            "window_param": window,
            "since": since,
            "n_fires": len(fires),
            "mode_counts": dict(mode_counts),
        },
        "arm_ledger": arm_ledger(),
        "topic_mix": mix,
        "per_mode": per_mode,
        "aggregate": aggregate,
        "within_window": within,
        "trajectory_ref": traj,
        "flags": flags,
    }


# ── rendering ────────────────────────────────────────────────────────────────

_CANON_MODES = ("DRIFT", "ARGUE", "EXPLAIN", "null")


def _fmt_pct(x) -> str:
    return f"{x*100:5.1f}%" if x is not None else "    --"


def _fmt_num(x, w=6, p=1) -> str:
    return f"{x:>{w}.{p}f}" if x is not None else f"{'--':>{w}}"


def _mode_row(name: str, m: dict) -> str:
    w = m["words"]
    return (f"  {name:<8} n={m['n']:<5} "
            f"held-out {_fmt_pct(m['held_out_rate'])} ({m['held_out_hits']}) "
            f"opener {_fmt_pct(m['opener_rate'])} ({m['opener_hits']}) | "
            f"w/f p10/p50/p90 {_fmt_num(w['p10'],5,0)}/{_fmt_num(w['p50'],5,0)}/"
            f"{_fmt_num(w['p90'],5,0)} mean {_fmt_num(w['mean'],5,1)} "
            f"[{_fmt_num(w['min'],1,0)}-{_fmt_num(w['max'],1,0)}]")


def render_report(res: dict) -> str:
    out = []
    p = out.append
    p("=" * 80)
    p(f"NEX VITALS  --  {res['when_utc']}")
    p(f"instrument {res['instrument_version']}")
    win = res["window"]
    since = f" since {_fmt_ts(win['since'])}" if win["since"] else ""
    p(f"window: last {win['window_param']} fires{since}  |  total fires "
      f"{win['n_fires']}  |  modes " + ", ".join(
          f"{k}={v}" for k, v in sorted(win["mode_counts"].items())))
    p("=" * 80)

    # arm-ledger
    al = res["arm_ledger"]
    p("ARM-LEDGER (C8)")
    if not al["available"]:
        p(f"  arm-ledger unavailable (no live env / no keepalive)  power={al['power']}")
    else:
        live_n = len(al["live"]) if al["live"] is not None else None
        decl_n = len(al["declared"]) if al["declared"] is not None else None
        p(f"  power: {al['power']}  |  live NEX5_*: "
          f"{'n/a' if live_n is None else live_n}  "
          f"declared: {'n/a' if decl_n is None else decl_n}")
        if al["diff"] is not None:
            d = al["diff"]
            p(f"  live-only   : {d['live_only'] or '(none)'}")
            p(f"  declared-only: {d['declared_only'] or '(none)'}")
            p(f"  value-mismatch: {d['value_mismatch'] or '(none)'}")
        else:
            p("  diff: unavailable (need both live and declared)")
    p("-" * 80)

    # per-mode (C6)
    p("PER-MODE FIRE BATTERY (C6: mandatory, never aggregate-only)")
    pm = res["per_mode"]
    for name in _CANON_MODES:
        if name in pm:
            p(_mode_row(name, pm[name]))
    for name in sorted(k for k in pm if k not in _CANON_MODES):
        p(_mode_row(name, pm[name]))
    agg = res["aggregate"]
    p(_mode_row("AGG", agg))
    p("-" * 80)

    # grasping
    cg = agg["content_grasp"]
    p("CONTENT-GRASP (frozen tokens, NO exclusion)")
    if cg["n"]:
        p(f"  dominant '{cg['dominant_token']}' DF {_fmt_pct(cg['dominant_share'])}"
          f"  | runners-up: " + ", ".join(
              f"{t} {s*100:.0f}%" for t, _c, s in cg["top"][1:]))
    else:
        p("  (no fires)")

    md = agg["maxdf"]
    rx = agg["register_exclusion"]
    p("maxDF* CONVERGENCE (beliefs fountain_insight)")
    if md.get("available"):
        flag = "  ** OVER THRESHOLD **" if md.get("breach") else ""
        p(f"  {_fmt_pct(md['max_df_star'])} driven by '{md['token']}' "
          f"({md.get('doc_count')}/{md.get('n')}){flag}")
    else:
        p(f"  unavailable ({md.get('reason')})")
    if rx["available"]:
        p(f"  register_exclusion v{rx['version']} sha256={rx['sha256']} "
          f"({rx['n_terms']} terms, fitted {rx['fitted_on']})")
    else:
        p("  register_exclusion unavailable")
    p("-" * 80)

    # topic-mix (C7)
    mix = res["topic_mix"]
    p(f"TOPIC-MIX (C7; furniture+register excluded, top {TOPN})")
    if mix["n"]:
        p("  " + ", ".join(f"{t['token']} {t['df_share']*100:.0f}%"
                           for t in mix["top"]))
    else:
        p("  (no fires)")
    p("-" * 80)

    # aliveness (C4 counters)
    p("ALIVENESS (C4 counter-metrics — suppression down is only good if these hold)")
    p(f"  lexical diversity (TTR): {_fmt_num(agg['ttr'],6,3)}  |  "
      f"distinct-opener rate: {_fmt_pct(agg['distinct_opener_rate'])}")
    if agg["words_split_mismatch"]:
        p(f"  NOTE: word_count != len(thought.split()) on "
          f"{agg['words_split_mismatch']}/{agg['n']} fires")

    # affect / drive (best-effort)
    su, mo, mm = agg["surprise"], agg["mood"], agg["momentum"]
    sline = (f"rate {_fmt_num(su.get('rate'),5,2)} mean {_fmt_num(su.get('mean'),5,2)} "
             f"(n={su.get('n')})" if su.get("available") else f"unavailable ({su.get('reason')})")
    p(f"  surprise: {sline}")
    moline = (f"{mo.get('column')}={mo.get('latest')}" if mo.get("available")
              else f"unavailable ({mo.get('reason')})")
    p(f"  mood: {moline}")
    if mm.get("available"):
        d = mm["dist"]
        p(f"  momentum carry_count: p50 {_fmt_num(d['p50'],4,0)} max "
          f"{_fmt_num(d['max'],4,0)}  exhausted(>3)={mm['n_exhausted']}")
    else:
        p(f"  momentum: unavailable ({mm.get('reason')})")
    p("-" * 80)

    # within-window control (C8)
    ww = res["within_window"]
    if ww is None:
        p("WITHIN-WINDOW CONTROL (C8): skipped (no trip info given)")
    else:
        p(f"WITHIN-WINDOW CONTROL (C8): touched={ww['n_touched']} "
          f"untouched={ww['n_untouched']} (tol={ww['tol_s']}s)")
        for lbl, key in (("TOUCHED", "touched"), ("UNTOUCHED(baseline)", "untouched")):
            m = ww[key]
            p(f"  {lbl:<20} held-out {_fmt_pct(m['held_out_rate'])} "
              f"opener {_fmt_pct(m['opener_rate'])} "
              f"w/f mean {_fmt_num(m['words']['mean'],5,1)} "
              f"TTR {_fmt_num(m['ttr'],5,3)} "
              f"distinct-opener {_fmt_pct(m['distinct_opener_rate'])}")
    p("-" * 80)

    # trajectory ref
    tr = res["trajectory_ref"]
    if tr:
        p(f"TRAJECTORY REF (sibling): {tr.get('overall')}  [{tr.get('when_utc')}]")
        p("  " + "  ".join(f"{k}={v}" for k, v in (tr.get("axes") or {}).items()))
    else:
        p("TRAJECTORY REF: none (logs/trajectory_log.jsonl absent)")
    p("-" * 80)

    # 2-sigma flags
    fl = res["flags"]
    if fl["insufficient_history"]:
        p("2-SIGMA FLAGS: insufficient history (vitals log empty) — none")
    elif not fl["flags"]:
        p("2-SIGMA FLAGS: none (all metrics inside their own 2-sigma band)")
    else:
        p("2-SIGMA FLAGS:")
        for f in fl["flags"]:
            p(f"  {f['metric']} {f['direction'].upper()}  value={f['value']:.4f} "
              f"vs mean {f['mean']:.4f} stdev {f['stdev']:.4f}  z={f['z']:+.2f}")
    for c in fl["cautions"]:
        p(f"  CAUTION: {c}")
    p("=" * 80)
    return "\n".join(out)


# ── JSON log row (opt-in, the ONLY side effect) ─────────────────────────────

def _log_row(res: dict) -> dict:
    """Exactly the pre-registered JSON row shape (spec §4)."""
    return {
        "ts": res["ts"],
        "when_utc": res["when_utc"],
        "instrument_version": res["instrument_version"],
        "window": res["window"],
        "arm_ledger": res["arm_ledger"],
        "topic_mix": res["topic_mix"],
        "per_mode": res["per_mode"],
        "aggregate": res["aggregate"],
        "within_window": res["within_window"],
        "trajectory_ref": res["trajectory_ref"],
        "flags": res["flags"],
    }


def _jsonable(obj):
    if isinstance(obj, set):
        return sorted(obj)
    if isinstance(obj, tuple):
        return list(obj)
    raise TypeError(f"not JSON-serialisable: {type(obj)}")


def maybe_log(res: dict, log_path: Optional[str]) -> Optional[str]:
    """Append ONE JSON line to `log_path`, or do nothing when it is None. This
    is the tool's only possible write. Returns the path written, or None."""
    if log_path is None:
        return None
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a") as fh:
        fh.write(json.dumps(_log_row(res), default=_jsonable) + "\n")
    return log_path


# ── retrospective daily series (read the EXISTING history; frozen detectors) ─

def daily_series(dynamic_db: Optional[str] = None, days: int = 14,
                 now_ts: Optional[float] = None) -> list:
    """Per-day battery over the last `days` UTC day-buckets, computed from the
    EXISTING fire history — a backward-looking series so climate-vs-weather can be
    read NOW, not after N future nights. Same FROZEN detectors as the live read,
    so days are comparable. Read-only. One dict per day (n=0 when no fires)."""
    now_ts = time.time() if now_ts is None else now_ts
    excl = register_info().get("terms")
    today = datetime.datetime.fromtimestamp(now_ts, datetime.timezone.utc).date()
    out = []
    for i in range(days - 1, -1, -1):
        d = today - datetime.timedelta(days=i)
        start = datetime.datetime(d.year, d.month, d.day,
                                  tzinfo=datetime.timezone.utc).timestamp()
        fires = load_fires(dynamic_db, since=start, until=start + 86400.0)
        if not fires:
            out.append({"date": d.isoformat(), "n": 0})
            continue
        pm = per_mode_metrics(fires)
        agg = compute_fire_metrics(fires)
        mix = topic_mix(fires, excl, topn=3)
        out.append({
            "date": d.isoformat(),
            "n": agg["n"],
            "agg_held": agg["held_out_rate"],
            "argue_held": pm["ARGUE"]["held_out_rate"],
            "argue_n": pm["ARGUE"]["n"],
            "drift_held": pm["DRIFT"]["held_out_rate"],
            "explain_held": pm["EXPLAIN"]["held_out_rate"],
            "drift_wf": pm["DRIFT"]["words"]["mean"],
            "top_topics": [t["token"] for t in mix["top"]],
        })
    return out


def render_daily(series: list) -> str:
    out = ["=" * 84,
           "NEX VITALS — RETROSPECTIVE DAILY SERIES (frozen instrument, READ-ONLY)",
           f"instrument {INSTRUMENT_VERSION}",
           "=" * 84,
           "date          n    AGG-held  ARGUE-held(n)  DRIFT-held  DRIFT w/f  top topics",
           "-" * 84]
    for r in series:
        if not r.get("n"):
            out.append(f"{r['date']}     0    (no fires)")
            continue
        out.append(
            f"{r['date']}  {r['n']:>4}   {_fmt_pct(r['agg_held'])}   "
            f"{_fmt_pct(r['argue_held'])}({r['argue_n']:>3})   "
            f"{_fmt_pct(r['drift_held'])}   {_fmt_num(r['drift_wf'],6,1)}   "
            f"{', '.join(r.get('top_topics') or [])}")
    out.append("-" * 84)
    out.append("READ: is ARGUE-held-out register STABLE across days (climate) or does it")
    out.append("track the top-topics (weather)? NB 2026-10-08/09 overlap the FRAME_DEDUP /")
    out.append("FRAME_GATE armed windows (perturbed); all other days are dark/natural.")
    out.append("=" * 84)
    return "\n".join(out)


# ── CLI ──────────────────────────────────────────────────────────────────────

def main(argv: Optional[list] = None) -> int:
    ap = argparse.ArgumentParser(
        description="NEX vitals — READ-ONLY longitudinal pathology instrument.")
    ap.add_argument("--window", type=int, default=WINDOW,
                    help=f"recent-fire window (default {WINDOW})")
    ap.add_argument("--since", type=float, default=None,
                    help="only fires with ts > this epoch (overrides --window span)")
    ap.add_argument("--topn", type=int, default=TOPN,
                    help=f"topic-mix size (default {TOPN})")
    ap.add_argument("--data-dir", default=None,
                    help="override the data dir (else NEX5_DATA_DIR or <repo>/data)")
    ap.add_argument("--trip-log", default=None, metavar="SOAK_LOG",
                    help="within-window control: a SOAK_LOG to grep for trip markers")
    ap.add_argument("--trip-tag", default=None, metavar="TAG",
                    help="the trip marker tag to match (e.g. 'frame_gate:')")
    ap.add_argument("--trip-tol", type=float, default=TRIP_TOL_S,
                    help=f"touched-match tolerance seconds (default {TRIP_TOL_S})")
    ap.add_argument("--log", nargs="?", const=DEFAULT_LOG, default=None,
                    metavar="PATH",
                    help=f"append ONE JSON line to PATH (default {DEFAULT_LOG}). "
                         f"Opt-in only; with no flag nothing is written.")
    ap.add_argument("--daily", type=int, default=None, metavar="N",
                    help="RETROSPECTIVE: print a per-day battery over the last N "
                         "days from existing history (read-only; ignores --log).")
    args = ap.parse_args([] if argv is None else argv)

    if args.data_dir:
        os.environ["NEX5_DATA_DIR"] = args.data_dir

    if args.daily:
        print(render_daily(daily_series(days=args.daily)))
        return 0

    trip_markers = None
    if args.trip_log and args.trip_tag:
        trip_markers = parse_trip_markers(args.trip_log, args.trip_tag)

    res = build_result(window=args.window, since=args.since, topn=args.topn,
                       trip_markers=trip_markers, trip_tol=args.trip_tol,
                       history_log=args.log)
    print(render_report(res))

    written = maybe_log(res, args.log)
    if written:
        print(f"[logged -> {written}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
