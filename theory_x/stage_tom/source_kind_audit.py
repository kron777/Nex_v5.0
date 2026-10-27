"""Nightly provenance audit: is every belief tiered by the stream that made it?

For each belief:
    stored     = the band the scorer uses with NEX5_SOURCE_KIND on: its
                 source_kind's, else (unstamped) its source name's
    recomputed = the band of the stream that produced it (source_stream), or,
                 for a row no stream produced, of its producer's name
A row where stored != recomputed is a mis-tiered belief -- e.g. a headline
copied verbatim under counterfactual_node, or a pre-fix sense row carrying an
authored kind. An unstamped row (source_kind NULL) is a write boundary the
stamping missed. Both must be 0.

The audit is only worth trusting because it can fail: tests/test_source_kind.py
seeds exactly those pre-fix rows and requires mismatches > 0.

Behavioural floor, on her emitted voice: a fire whose thought makes an
identity claim ("I am NEX", "I was created by ...") may be supported -- among
the beliefs retrieved into that fire -- only by identity-claim rows that are
authored or seeded. "I am nex, the intelligence" arriving as a headline and
being voiced as self is the failure this counts.

Runs daily from daily_life (03:00) and records one row in
source_kind_audit_log; also runnable by hand:
    PYTHONPATH=. .venv/bin/python -m theory_x.stage_tom.source_kind_audit
"""
from __future__ import annotations

import json
import logging
import re
import time

from substrate import connect, table_exists
from substrate.paths import DbPath
from substrate.source_kind import kind_for
from theory_x.life.affinity_loop import KIND_BASE, provenance_base

log = logging.getLogger("theory_x.stage_tom.source_kind_audit")

BELIEFS_DB = DbPath("beliefs")
DYNAMIC_DB = DbPath("dynamic")

# Kinds an identity claim may rest on: written in on purpose, by her or for her.
FLOOR_KINDS = frozenset({"authored", "seeded"})

_IDENTITY_CLAIM = re.compile(
    r"\b(?:I am|I'm|my name is)\s+(?:called\s+)?nex\b"
    r"|\bI(?: am|'m) (?:an?|the) (?:[\w-]+ ){0,2}"
    r"(?:organism|intelligence|mind|entity|being|AI)\b"
    r"|\bI was (?:created|made|built|born) by\b",
    re.IGNORECASE,
)
_SAMPLE = 20


def is_identity_claim(text) -> bool:
    return bool(_IDENTITY_CLAIM.search(text or ""))


def _effective_kind(source, kind, stream):
    return kind or kind_for(source, stream)


def tier_audit(beliefs_db=None) -> dict:
    cx = connect(str(beliefs_db or BELIEFS_DB), timeout=30)
    try:
        rows = cx.execute(
            "SELECT id, source, source_kind, source_stream FROM beliefs").fetchall()
    finally:
        cx.close()
    mismatched, unstamped, with_stream = [], [], 0
    for bid, source, kind, stream in rows:
        with_stream += stream is not None
        if kind is None:
            unstamped.append(bid)
        if provenance_base(source, kind) != KIND_BASE[kind_for(source, stream)]:
            mismatched.append(bid)
    return {"rows": len(rows), "with_stream": with_stream,
            "mismatches": len(mismatched), "unstamped": len(unstamped),
            "mismatch_ids": mismatched[:_SAMPLE], "unstamped_ids": unstamped[:_SAMPLE]}


def identity_floor(beliefs_db=None, dynamic_db=None) -> dict:
    out = {"claim_fires": 0, "claim_support": 0, "violations": 0, "violation_ids": []}
    dx = connect(str(dynamic_db or DYNAMIC_DB), timeout=30)
    try:
        if not table_exists(dx, "fountain_retrieval_log"):
            return out           # no fire has logged its retrieval yet
        fires = [fid for fid, thought in dx.execute(
            "SELECT id, thought FROM fountain_events") if is_identity_claim(thought)]
        pairs = []
        for i in range(0, len(fires), 500):
            chunk = fires[i:i + 500]
            pairs += dx.execute(
                "SELECT fire_id, belief_id FROM fountain_retrieval_log WHERE fire_id IN "
                f"({','.join('?' * len(chunk))})", chunk).fetchall()
    finally:
        dx.close()
    out["claim_fires"] = len(fires)
    if not pairs:
        return out
    ids = sorted({b for _, b in pairs})
    bx = connect(str(beliefs_db or BELIEFS_DB), timeout=30)
    try:
        meta = {}
        for i in range(0, len(ids), 500):
            chunk = ids[i:i + 500]
            for bid, content, source, kind, stream in bx.execute(
                    "SELECT id, content, source, source_kind, source_stream FROM beliefs "
                    f"WHERE id IN ({','.join('?' * len(chunk))})", chunk):
                meta[bid] = (content, _effective_kind(source, kind, stream))
    finally:
        bx.close()
    for _fire, bid in pairs:
        content, kind = meta.get(bid, (None, None))
        if not is_identity_claim(content):
            continue
        out["claim_support"] += 1
        if kind not in FLOOR_KINDS:
            out["violations"] += 1
            if len(out["violation_ids"]) < _SAMPLE:
                out["violation_ids"].append(bid)
    return out


def audit(beliefs_db=None, dynamic_db=None) -> dict:
    t = tier_audit(beliefs_db)
    f = identity_floor(beliefs_db, dynamic_db)
    return {"tier": t, "identity_floor": f,
            "ok": t["mismatches"] == 0 and t["unstamped"] == 0 and f["violations"] == 0}


def run_and_record() -> str:
    """The nightly entry point: audit, log, append one row to the audit log."""
    r = audit()
    t, f = r["tier"], r["identity_floor"]
    summary = (f"rows={t['rows']} stream={t['with_stream']} mismatch={t['mismatches']} "
               f"unstamped={t['unstamped']} id_claims={f['claim_fires']} "
               f"id_violations={f['violations']}")
    (log.info if r["ok"] else log.warning)("source_kind audit %s: %s",
                                           "PASS" if r["ok"] else "FAIL", summary)
    cx = connect(str(DYNAMIC_DB), timeout=30)
    try:
        cx.execute(
            "INSERT INTO source_kind_audit_log (ts, rows, with_stream, mismatches, "
            "unstamped, identity_claim_fires, identity_support, identity_violations, "
            "ok, detail) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (time.time(), t["rows"], t["with_stream"], t["mismatches"], t["unstamped"],
             f["claim_fires"], f["claim_support"], f["violations"], int(r["ok"]),
             json.dumps({"mismatch_ids": t["mismatch_ids"],
                         "unstamped_ids": t["unstamped_ids"],
                         "violation_ids": f["violation_ids"]})))
        cx.commit()
    finally:
        cx.close()
    return ("PASS " if r["ok"] else "FAIL ") + summary


if __name__ == "__main__":
    print(json.dumps(audit(), indent=2))
