#!/usr/bin/env python3
"""snapshot.py - periodic substrate state snapshot, read-only.

Captures structured JSON of drive state, voice_profile, fountain activity
split by hot_branch and real-thought-vs-feed-paste, substrate_voice anchor
usage, gate decisions, throw-net activity. Idempotent.

Usage:
  python3 scripts/snapshot.py
  python3 scripts/snapshot.py --diff
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

REPO = Path("/home/rr/Desktop/Desktop/nex5")
CONV_DB = REPO / "data" / "conversations.db"
DYNAMIC_DB = REPO / "data" / "dynamic.db"
BELIEFS_DB = REPO / "data" / "beliefs.db"
SNAPDIR = REPO / "snapshots"


def is_real_thought(thought):
    if not thought:
        return False
    return not thought.lstrip().startswith("[")


def take_snapshot():
    now = time.time()
    snap = {
        "snapshot_at": now,
        "snapshot_at_str": datetime.fromtimestamp(now).strftime("%Y-%m-%d %H:%M:%S"),
        "drives": {},
        "voice_profile": [],
        "fountain": {},
        "substrate_voice_anchors": {},
        "recent_thoughts": [],
        "gate": {},
        "throw_net": {},
        "open_problems": [],
        "process": {},
    }

    conv = sqlite3.connect("file:" + str(CONV_DB) + "?mode=ro", uri=True)
    conv.row_factory = sqlite3.Row
    dyn = sqlite3.connect("file:" + str(DYNAMIC_DB) + "?mode=ro", uri=True)
    dyn.row_factory = sqlite3.Row
    bel = sqlite3.connect("file:" + str(BELIEFS_DB) + "?mode=ro", uri=True)
    bel.row_factory = sqlite3.Row

    drow = conv.execute("SELECT * FROM drives_competing WHERE id = 1").fetchone()
    if drow:
        snap["drives"] = {
            "coherence": drow["coherence"],
            "exploration": drow["exploration"],
            "integration": drow["integration"],
            "self_preservation": drow["self_preservation"],
            "curiosity": drow["curiosity"],
            "tension_pairs": json.loads(drow["tension_pairs"] or "[]"),
            "computed_at": drow["computed_at"],
        }

    for vrow in conv.execute("SELECT * FROM voice_profile ORDER BY frequency DESC").fetchall():
        sig = json.loads(vrow["signature_vocabulary"] or "[]")
        snap["voice_profile"].append({
            "drive_pair": vrow["drive_pair"],
            "frequency": vrow["frequency"],
            "updated_at": vrow["updated_at"],
            "top12": [{"word": e["word"], "count": e["count"], "ratio": e["ratio"]}
                      for e in sig[:12]],
        })

    fountain_rows = dyn.execute(
        "SELECT hot_branch, thought FROM fountain_events "
        "WHERE ts > ? AND thought IS NOT NULL",
        (now - 86400,),
    ).fetchall()

    by_branch_real = Counter()
    by_branch_feed = Counter()
    for r in fountain_rows:
        branch = r["hot_branch"] or "null"
        if is_real_thought(r["thought"]):
            by_branch_real[branch] += 1
        else:
            by_branch_feed[branch] += 1

    snap["fountain"] = {
        "total_24h": len(fountain_rows),
        "real_thought_count_24h": sum(by_branch_real.values()),
        "feed_paste_count_24h": sum(by_branch_feed.values()),
        "by_branch_real": dict(by_branch_real),
        "by_branch_feed": dict(by_branch_feed),
    }

    sv_rows = dyn.execute(
        "SELECT anchor_belief_id, COUNT(*) AS n FROM fountain_events "
        "WHERE hot_branch = 'substrate_voice' AND ts > ? "
        "  AND anchor_belief_id IS NOT NULL "
        "GROUP BY anchor_belief_id ORDER BY n DESC LIMIT 20",
        (now - 86400,),
    ).fetchall()
    anchor_ids = [r["anchor_belief_id"] for r in sv_rows]
    if anchor_ids:
        ph = ",".join("?" * len(anchor_ids))
        anchor_content = {}
        for r in bel.execute(
            "SELECT id, content FROM beliefs WHERE id IN (" + ph + ")",
            anchor_ids,
        ).fetchall():
            anchor_content[r["id"]] = r["content"][:120]
        snap["substrate_voice_anchors"] = {
            "total_24h": sum(r["n"] for r in sv_rows),
            "unique_anchors_24h": len(sv_rows),
            "top": [
                {"anchor_id": r["anchor_belief_id"], "count": r["n"],
                 "content": anchor_content.get(r["anchor_belief_id"], "?")}
                for r in sv_rows[:10]
            ],
        }
    else:
        snap["substrate_voice_anchors"] = {
            "total_24h": 0, "unique_anchors_24h": 0, "top": []
        }

    recent = dyn.execute(
        "SELECT id, ts, hot_branch, substr(thought, 1, 140) AS thought "
        "FROM fountain_events WHERE thought NOT LIKE '[%' "
        "ORDER BY id DESC LIMIT 10"
    ).fetchall()
    snap["recent_thoughts"] = [
        {"id": r["id"], "ts": r["ts"], "hot_branch": r["hot_branch"],
         "thought": r["thought"]}
        for r in recent
    ]

    try:
        gate_rows = bel.execute(
            "SELECT outcome, COUNT(*) AS n FROM gate_decisions "
            "WHERE ts > ? GROUP BY outcome",
            (now - 86400,),
        ).fetchall()
        snap["gate"] = {r["outcome"]: r["n"] for r in gate_rows}
    except Exception as e:
        snap["gate"] = {"error": str(e)[:80]}

    try:
        tn_rows = bel.execute(
            "SELECT trigger_type, COUNT(*) AS n, SUM(fired) AS fired_n "
            "FROM throw_net_triggers WHERE ts > ? GROUP BY trigger_type",
            (now - 86400,),
        ).fetchall()
        snap["throw_net"] = {}
        for r in tn_rows:
            snap["throw_net"][r["trigger_type"]] = {
                "total": r["n"], "fired": r["fired_n"] or 0,
            }
    except Exception as e:
        snap["throw_net"] = {"error": str(e)[:80]}

    try:
        pm_rows = dyn.execute(
            "SELECT id, title, status FROM problems "
            "WHERE status = 'open' ORDER BY id DESC LIMIT 10"
        ).fetchall()
        snap["open_problems"] = [
            {"id": r["id"], "title": r["title"], "status": r["status"]}
            for r in pm_rows
        ]
    except Exception:
        pass

    try:
        n_beliefs = bel.execute("SELECT COUNT(*) AS n FROM beliefs").fetchone()["n"]
        snap["process"] = {"belief_count": n_beliefs}
    except Exception:
        pass

    return snap


def write_snapshot(snap):
    SNAPDIR.mkdir(parents=True, exist_ok=True)
    fname = datetime.fromtimestamp(snap["snapshot_at"]).strftime("%Y-%m-%d_%H%M")
    path = SNAPDIR / (fname + ".json")
    path.write_text(json.dumps(snap, indent=2, default=str))
    return path


def show_summary(snap):
    sat = snap["snapshot_at_str"]
    print("=== Snapshot " + sat + " ===")
    print()
    d = snap["drives"]
    if d:
        keys = ["coherence", "exploration", "integration", "self_preservation", "curiosity"]
        pairs = [(k, d.get(k, 0)) for k in keys]
        pairs.sort(key=lambda x: -x[1])
        print("Drives (weighted):")
        for n, v in pairs:
            print("  " + n.ljust(20) + " " + format(v, ".3f"))
        if d.get("tension_pairs"):
            print("  tension: " + str(d["tension_pairs"]))
        print()

    for vp in snap["voice_profile"]:
        words = [e["word"] for e in vp["top12"][:6]]
        print("voice_profile[" + vp["drive_pair"] + "] freq=" + str(vp["frequency"]))
        print("  top-6: " + str(words))
    print()

    f = snap["fountain"]
    print("Fountain 24h: " + str(f["total_24h"]) + " events ("
          + str(f["real_thought_count_24h"]) + " real, "
          + str(f["feed_paste_count_24h"]) + " feed-paste)")
    pairs = sorted(f["by_branch_real"].items(), key=lambda x: -x[1])
    for branch, n in pairs:
        print("  " + branch.ljust(20) + " " + str(n).rjust(4))
    print()

    sv = snap["substrate_voice_anchors"]
    print("Substrate-voice 24h: " + str(sv["total_24h"]) + " fires, "
          + str(sv["unique_anchors_24h"]) + " unique anchors")
    for a in sv["top"][:5]:
        print("  [" + str(a["count"]).rjust(2) + "x] anchor_id="
              + str(a["anchor_id"]) + ": " + a["content"][:80])
    print()

    g = snap["gate"]
    if "error" not in g and g:
        total = sum(g.values()) or 1
        print("Gate 24h: " + str(total) + " decisions")
        for outcome, n in sorted(g.items(), key=lambda x: -x[1]):
            pct = 100 * n / total
            print("  " + outcome.ljust(10) + " " + str(n).rjust(6)
                  + " (" + format(pct, ".1f") + "%)")
        print()

    tn = snap["throw_net"]
    if "error" not in tn and tn:
        print("Throw-net 24h:")
        for tt, td in tn.items():
            print("  " + tt.ljust(18) + " " + str(td["total"]).rjust(6)
                  + " total, " + str(td["fired"]).rjust(4) + " fired")
        print()

    if snap["open_problems"]:
        print("Open problems:")
        for p in snap["open_problems"][:5]:
            print("  #" + str(p["id"]) + ": " + p["title"][:80])
        print()

    print("Recent fountain (non-feed, last 5):")
    for s in snap["recent_thoughts"][:5]:
        hb = s["hot_branch"] or "?"
        print("  #" + str(s["id"]).rjust(5) + " [" + hb.ljust(16) + "] "
              + s["thought"])


def latest_snapshot():
    paths = sorted(SNAPDIR.glob("*.json"))
    return paths[-2] if len(paths) >= 2 else None


def show_diff(current_path):
    prior = latest_snapshot()
    if not prior or prior == current_path:
        print("(no prior snapshot to diff against)")
        return
    prior_snap = json.loads(prior.read_text())
    cur_snap = json.loads(current_path.read_text())

    print()
    print("=== DIFF vs " + prior.stem + " ===")
    print()

    p_drives = prior_snap.get("drives", {})
    c_drives = cur_snap.get("drives", {})
    if p_drives and c_drives:
        print("Drive deltas:")
        for k in ("coherence", "exploration", "integration", "self_preservation", "curiosity"):
            delta = c_drives.get(k, 0) - p_drives.get(k, 0)
            if abs(delta) > 0.01:
                sign = "+" if delta > 0 else ""
                print("  " + k.ljust(20) + " " + sign + format(delta, ".3f"))
        print()

    p_vp = {v["drive_pair"]: v for v in prior_snap.get("voice_profile", [])}
    c_vp = {v["drive_pair"]: v for v in cur_snap.get("voice_profile", [])}
    for pair, c in c_vp.items():
        p = p_vp.get(pair)
        if p:
            df = c["frequency"] - p["frequency"]
            p_words = set(e["word"] for e in p["top12"])
            c_words = set(e["word"] for e in c["top12"])
            entered = c_words - p_words
            exited = p_words - c_words
            print("voice_profile[" + pair + "]: freq "
                  + str(p["frequency"]) + " -> " + str(c["frequency"])
                  + " (+" + str(df) + ")")
            if entered:
                print("  + entered top-12: " + str(sorted(entered)))
            if exited:
                print("  - exited top-12:  " + str(sorted(exited)))
            print()


def main():
    snap = take_snapshot()
    path = write_snapshot(snap)
    print("Snapshot saved: " + str(path))
    print()
    show_summary(snap)
    if "--diff" in sys.argv:
        show_diff(path)


if __name__ == "__main__":
    main()
