#!/usr/bin/env python3
"""DRY live-quality sample of the synergizer — the REAL synthesize() path
(pair selection, LLM strike, quality check, coherence gate) with NOTHING
written to NEX's graph.

Write-freedom is ENFORCED in-process, not assumed:
  * sqlite3.connect raises unless the target is a mode=ro URI (every live
    Reader opens mode=ro);
  * substrate.Writer cannot be constructed;
  * the synergizer's writer is a RecordingWriter (captures, returns fake ids);
  * the coherence gate gets a RecordingWriter and NO holding zone / resolver /
    trigger detector / self-narrative (those are post-decision side effects;
    the ACCEPT/REJECT decision reads only);
  * errors.record's disk sink is a no-op in this process.
The voice call is a plain HTTP request to ollama (same model NEX uses).

Two things the live loop would see are simulated from this run's own output,
since nothing is written: the synergizer_log "recently used" window (dry picks
prepended to the real log) and the quality check's recent-beliefs duplicate
list (dry texts prepended).

  .venv/bin/python3 tools/synth_dry_sample.py --n 20 --out RUN.jsonl
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# ── hard write guards (installed before anything opens a db) ────────────────
_real_connect = sqlite3.connect
REFUSED = []


def _ro_only_connect(database, *a, **k):
    db = str(database)
    if db == ":memory:" or (k.get("uri") and db.startswith("file:") and "mode=ro" in db):
        return _real_connect(database, *a, **k)
    REFUSED.append(("sqlite", db))
    raise RuntimeError(f"DRY GUARD: refused non-read-only sqlite connect to {db!r}")


sqlite3.connect = _ro_only_connect

import substrate  # noqa: E402
import substrate.writer as _sw  # noqa: E402


def _no_writer(*a, **k):
    REFUSED.append(("Writer", a[1] if len(a) > 1 else "?"))
    raise RuntimeError("DRY GUARD: substrate.Writer construction refused")


_sw.Writer.__init__ = _no_writer
import errors  # noqa: E402
errors._to_disk = lambda ev: None

from substrate import Reader, db_paths  # noqa: E402
from theory_x.diversity import embeddings as _emb  # noqa: E402
_emb._CACHE_MAX = 30000          # in-process only: avoid re-embedding 15k beliefs per pick
from theory_x.stage3_world_model.synergizer import BeliefSynergizer  # noqa: E402
from theory_x.stage_gate.coherence_gate import CoherenceGate  # noqa: E402
from voice.llm import VoiceClient  # noqa: E402

_DEGENERATE = re.compile(
    r"\b(everything is (?:inter)?connected|interconnectedness|all things are (?:connected|one)|"
    r"(?:the )?unity of (?:all|everything)|oneness|all is one|web of (?:life|existence)|"
    r"we are all (?:connected|one)|the universe itself)\b", re.I)
_NEWSY = re.compile(r"\b(the item|this item|the article|headline|announced|reported|"
                    r"stock|shares|price|bitcoin|according to|study (?:shows|finds))\b", re.I)


class RecordingWriter:
    def __init__(self):
        self.writes = []
        self._id = 900_000_000

    def write(self, sql, params=()):
        self.writes.append((sql.split()[0:4], params))
        self._id += 1
        return self._id

    def write_many(self, stmts):
        return [self.write(s, p) for s, p in stmts]


class Capture:
    def __init__(self):
        self.msgs = []

    def record(self, msg, source=None, level=None, exc=None, **k):
        self.msgs.append(str(msg))


class ProxyReader:
    """Live read-only Reader, plus this run's dry output where the live loop
    would see its own writes."""
    def __init__(self, path, state):
        self._r = Reader(path)
        self._s = state

    def read(self, sql, params=()):
        if "FROM synergizer_log" in sql and "ORDER BY ts DESC LIMIT 20" in sql:
            dry = [{"belief_id_a": a, "belief_id_b": b} for a, b in reversed(self._s["picks"])]
            return (dry + [dict(r) for r in self._r.read(sql, params)])[:20]
        if sql.strip().startswith("SELECT content FROM beliefs ORDER BY created_at DESC LIMIT 200"):
            dry = [{"content": t} for t in reversed(self._s["texts"])]
            return (dry + [dict(r) for r in self._r.read(sql, params)])[:200]
        return self._r.read(sql, params)

    def read_one(self, sql, params=()):
        return self._r.read_one(sql, params)

    def connection(self):
        return self._r.connection()


class SpyVoice:
    def __init__(self):
        self._v = VoiceClient()
        self.last = None

    def speak(self, req):
        self.last = None
        resp = self._v.speak(req)
        self.last = resp.text if resp else None
        return resp


def run_arm(name, env, n, out):
    for k in ("NEX5_SYNTH_FRESH", "NEX5_BRIDGE"):
        os.environ.pop(k, None)
    os.environ.update(env)
    paths = db_paths()
    state = {"picks": [], "texts": []}
    br = ProxyReader(paths["beliefs"], state)
    gw = RecordingWriter()
    gate = CoherenceGate(beliefs_reader=Reader(paths["beliefs"]), beliefs_writer=gw,
                         conversations_reader=Reader(paths["conversations"]))
    sw, cap, voice = RecordingWriter(), Capture(), SpyVoice()
    syn = BeliefSynergizer(sw, br, voice, errors_channel=cap, coherence_gate=gate)
    # capture the bridge context _select_pair computes (read-only), for reporting
    _real_ctx = syn._bridge_context
    _last_ctx = {}

    def _spy_ctx(*a, **k):
        _last_ctx["ctx"] = _real_ctx(*a, **k)
        return _last_ctx["ctx"]
    syn._bridge_context = _spy_ctx
    byid = {}
    for i in range(n):
        cap.msgs.clear()
        t0 = time.time()
        pair = syn._select_pair()
        if pair is None:
            print(f"  [{name}] {i}: no pair"); continue
        a, b = pair
        byid[a["id"]], byid[b["id"]] = a, b
        va, vb = _emb.embed_belief(a["id"], a["content"]), _emb.embed_belief(b["id"], b["content"])
        cos = float(va @ vb / ((va @ va) ** 0.5 * (vb @ vb) ** 0.5))
        ctx = _last_ctx.get("ctx")
        bridged = bool(ctx) and BeliefSynergizer.bridge_factor(ctx, a["id"], b["id"], cos=cos) > 1.0
        # the REAL path, with _select_pair pinned to the pair just chosen
        syn._select_pair = lambda _p=pair: _p
        try:
            res = syn.synthesize()
        finally:
            del syn._select_pair
        raw = voice.last or ""
        if res:
            outcome, text = "PASS", res["content"]
        else:
            gate_msg = next((m for m in cap.msgs if m.startswith("Synergizer gate")), None)
            text = raw
            if gate_msg:
                outcome = "GATE " + gate_msg.split("(")[0].replace("Synergizer gate", "").strip()
            elif not raw:
                outcome = "NO_TEXT"
            else:
                outcome = "QUALITY"   # length / blacklist / duplicate
        state["picks"].append((a["id"], b["id"]))
        if res:
            state["texts"].append(text)
        rec = {"arm": name, "i": i, "outcome": outcome, "text": text,
               "gate_reason": next((m for m in cap.msgs if "gate" in m.lower()), ""),
               "a": {k: a.get(k) for k in ("id", "source", "branch_id", "content")},
               "b": {k: b.get(k) for k in ("id", "source", "branch_id", "content", "created_at")},
               "b_age_d": round((time.time() - float(b["created_at"])) / 86400, 2),
               "cos": round(cos, 3), "bridged": bridged,
               "degenerate": bool(_DEGENERATE.search(text or "")),
               "koan_x_news": a["source"] in ("koan", "tao") and bool(_NEWSY.search(b.get("content") or "")),
               "secs": round(time.time() - t0, 1)}
        out.write(json.dumps(rec) + "\n"); out.flush()
        print(f"  [{name}] {i}: {outcome:14s} {rec['secs']:5.1f}s  a={a['source']}/{a['id']} "
              f"b={b['source']}/{b.get('branch_id')}/{rec['b_age_d']}d cos={cos:.3f}"
              f"{' BRIDGED' if bridged else ''}", flush=True)
    return gw, sw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--out", default="/tmp/synth_dry.jsonl")
    ap.add_argument("--arms", default="A,B,C")
    a = ap.parse_args()
    arms = {"A": ("A neither", {}),
            "B": ("B SYNTH_FRESH", {"NEX5_SYNTH_FRESH": "1"}),
            "C": ("C FRESH+BRIDGE", {"NEX5_SYNTH_FRESH": "1", "NEX5_BRIDGE": "1"})}
    with open(a.out, "w") as out:
        for k in a.arms.split(","):
            name, env = arms[k]
            print(f"== {name}", flush=True)
            gw, sw = run_arm(name, env, a.n, out)
            print(f"   recorded (NOT written): synergizer writer {len(sw.writes)} statements, "
                  f"gate writer {len(gw.writes)} statements; guard refusals so far: {len(REFUSED)} "
                  f"{REFUSED[:3]}", flush=True)


if __name__ == "__main__":
    main()
