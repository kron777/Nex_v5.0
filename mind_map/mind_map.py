#!/usr/bin/env python3
"""Render mind_map/MIND_MAP.yaml -> Mermaid / DOT / Markdown.

    python mind_map/mind_map.py --check
    python mind_map/mind_map.py --format mermaid > mind_map/MIND_MAP.mmd
    python mind_map/mind_map.py --format dot | twopi -Tsvg -o mind_map/mind_map.svg
    python mind_map/mind_map.py --format md >> mind_map/STATUS.md

The YAML is the only source of truth. Generated files are never hand-edited.
Mermaid cannot draw a radial ring -- use twopi for the literal spider, Mermaid
for the diffable, CI-checkable artifact.

Drafted by Beam AI (2026-11-09), reconstructed and reviewed by Claude for CC
to commit, test and wire into CI. Verify the --check / --verify behavior
against mind_map/MIND_MAP.yaml before trusting the output.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import date, datetime, time
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("pyyaml required:  pip install pyyaml")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
MAP = HERE / "MIND_MAP.yaml"

EVIDENCE = ("measured", "implemented", "static", "inferred", "unknown")
SOURCE_KINDS = ("file", "absent", "composite", "inferred")
LAYERS = ("arm", "boundary", "ring", "straddle")
FILL = {
    "measured":    ("#1b5e20", "#ffffff"),
    "implemented": ("#66bb6a", "#0b1d0d"),
    "static":      ("#90caf9", "#0b1d2f"),
    "inferred":    ("#cfd8dc", "#1b2227"),
    "unknown":     ("#ffffff", "#1b2227"),
}
REQUIRED = ("id", "label", "layer", "role_note", "evidence", "dark",
            "blocked", "falsifier_status", "source", "last_verified")
# Matches "path", "path:N", or "path:N-M"
REF_RE = re.compile(r"^(?P<path>[^:]+)(?::(?P<a>\d+)(?:-(?P<b>\d+))?)?$")
# A shadow/stand-in's self-declared wiring deadline, e.g. "UNBLOCK 2026-11-21".
UNBLOCK_RE = re.compile(r"UNBLOCK:?\s*(\d{4}-\d{2}-\d{2})")


# ─────────────────────────────── loading ───────────────────────────────
def load(path: Path = MAP) -> dict:
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _paths_of(src: dict) -> list[str]:
    if src.get("kind") == "file":
        m = REF_RE.match(str(src.get("ref", "")))
        return [m.group("path")] if m else []
    if src.get("kind") == "composite":
        out = []
        for ref in src.get("refs", []):
            m = REF_RE.match(str(ref))
            if m:
                out.append(m.group("path"))
        return out
    return []


def last_commit_ts(rel: str) -> float | None:
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%ct", "--", rel],
            cwd=ROOT, capture_output=True, text=True, check=True,
        ).stdout.strip()
        return float(out) if out else None
    except (subprocess.CalledProcessError, ValueError, FileNotFoundError):
        return None


# ─────────────────────────────── checking ──────────────────────────────
def check(doc: dict, verify_absent: bool = False) -> tuple[list, list]:
    errs: list[str] = []
    warns: list[str] = []
    arm_ids = {a["id"] for a in doc.get("arms", [])}
    seen: set[str] = set()
    node_ids_all = {n["id"] for n in doc.get("nodes", []) if "id" in n}

    # meta.doctrine lists the source documents the map's claims are drawn from.
    # A doctrine file that doesn't exist is how a never-wired "veto" (cited only
    # in notes prose, never as a node's own source.ref) slips past every other
    # check -- see hri_apatrapya's VIRTUE_SLATE.md correction, 2026-11-10.
    for rel in doc.get("meta", {}).get("doctrine", []):
        if not (ROOT / rel).exists():
            warns.append(f"meta.doctrine: cited file missing: {rel}")

    for n in doc.get("nodes", []):
        nid = n.get("id", "<missing id>")
        if nid in seen:
            errs.append(f"{nid}: duplicate id")
        seen.add(nid)

        for f in REQUIRED:
            if f not in n:
                errs.append(f"{nid}: missing required field `{f}`")
        if n.get("evidence") not in EVIDENCE:
            errs.append(f"{nid}: evidence must be one of {EVIDENCE}")
        if n.get("layer") not in LAYERS:
            errs.append(f"{nid}: layer must be one of {LAYERS}")
        if n.get("layer") == "arm" and n.get("arm") not in arm_ids:
            errs.append(f"{nid}: layer=arm requires a valid `arm`")

        lv = n.get("last_verified")
        if lv == "unverified":
            warns.append(f"{nid}: unverified")
        else:
            try:
                d = date.fromisoformat(str(lv))
                if d > date.today():
                    errs.append(f"{nid}: last_verified is in the future")
            except ValueError:
                errs.append(f"{nid}: last_verified must be YYYY-MM-DD or 'unverified'")

        src = n.get("source") or {}
        kind = src.get("kind")
        if kind not in SOURCE_KINDS:
            errs.append(f"{nid}: source.kind must be one of {SOURCE_KINDS}")
            continue

        if kind == "inferred":
            frm = src.get("from")
            if not frm:
                errs.append(f"{nid}: inferred source needs `from`")
            elif frm not in node_ids_all:
                errs.append(f"{nid}: inferred source `from` {frm!r} is not a real node id")

        if kind in ("file", "composite"):
            refs = [src["ref"]] if kind == "file" else src.get("refs", [])
            if not refs:
                errs.append(f"{nid}: {kind} source has no refs")
            for ref in refs:
                m = REF_RE.match(str(ref))
                if not m:
                    errs.append(f"{nid}: unparseable ref {ref!r}")
                    continue
                p = ROOT / m.group("path")
                if not p.exists():
                    errs.append(f"{nid}: source path missing: {m.group('path')}")
                    continue
                if m.group("a"):
                    n_lines = sum(1 for _ in p.open("rb"))
                    hi = int(m.group("b") or m.group("a"))
                    if hi > n_lines:
                        errs.append(
                            f"{nid}: line range {hi} exceeds {m.group('path')} ({n_lines} lines)")
                else:
                    warns.append(f"{nid}: weak anchor — no line number in {m.group('path')}")

        if kind == "absent":
            if not src.get("claim"):
                errs.append(f"{nid}: absent source needs `claim`")
            if not src.get("check"):
                errs.append(f"{nid}: absent source needs `check` (a command that must return nothing)")
            elif verify_absent:
                r = subprocess.run(src["check"], shell=True, cwd=ROOT,
                                    capture_output=True, text=True)
                if r.stdout.strip():
                    errs.append(f"{nid}: absence claim falsified — `{src['check']}` returned output")

        # drift: has the source changed since last_verified?
        if lv != "unverified" and kind in ("file", "composite"):
            cutoff = datetime.combine(date.fromisoformat(str(lv)), time(23, 59, 59)).timestamp()
            for rel in _paths_of(src):
                ts = last_commit_ts(rel)
                if ts and ts > cutoff:
                    warns.append(
                        f"{nid}: STALE — {rel} changed "
                        f"{datetime.fromtimestamp(ts):%Y-%m-%d} after last_verified {lv}")

        # UNBLOCK: a shadow/stand-in's own self-set deadline for being wired
        # into the live path. Only a PAST-due one is a warning (the failure
        # `dark` exists to make visible: a shadow quietly gone permanent) --
        # a future-dated one is listed (see --check output) but not warned.
        for m in UNBLOCK_RE.finditer(str(n.get("notes") or "")):
            if date.fromisoformat(m.group(1)) < date.today():
                warns.append(f"{nid}: UNBLOCK {m.group(1)} PAST DUE")

    node_ids = {n["id"] for n in doc.get("nodes", [])}
    targets = node_ids | arm_ids
    for grp in ("constraints", "dependencies"):
        for e in doc.get(grp, []):
            for side in ("from", "to"):
                if e[side] not in targets:
                    errs.append(f"{grp}: unknown {side} {e[side]!r}")
    for p in doc.get("pairs", []):
        for side in ("a", "b"):
            if p[side] not in node_ids:
                errs.append(f"pairs: unknown {side} {p[side]!r}")
    return errs, warns


# ─────────────────────────────── emitting ──────────────────────────────
def _cls(ev: str, dark: bool, blocked: bool) -> str:
    return f"c_{ev}_{int(dark)}{int(blocked)}"


def _badges(n: dict) -> str:
    b = ""
    if n.get("blocked"):
        b += "[blocked] "
    if n.get("last_verified") == "unverified":
        b += "[unverified] "
    if n.get("dark"):
        b += "[dark] "
    return b


def emit_mermaid(doc: dict) -> str:
    out = ["%% GENERATED from MIND_MAP.yaml -- do not edit by hand", "flowchart LR"]
    for ev, (fill, color) in FILL.items():
        for dark in (False, True):
            for blocked in (False, True):
                parts = [f"fill:{fill}", f"color:{color}",
                         "stroke-width:3px" if blocked else "stroke-width:1px",
                         "stroke:#c62828" if blocked else "stroke:#455a64"]
                if dark:
                    parts.append("stroke-dasharray:5 3")
                out.append(f"  classDef {_cls(ev, dark, blocked)} {','.join(parts)}")

    by_layer: dict[str, list] = {}
    for n in doc["nodes"]:
        by_layer.setdefault(n["layer"], []).append(n)

    def node_line(n: dict) -> str:
        label = (_badges(n) + n["label"]).replace('"', "'")
        return f'    n_{n["id"]}["{label}<br/><i>{n["evidence"]}</i>"]'

    for arm in doc["arms"]:
        members = [n for n in by_layer.get("arm", []) if n.get("arm") == arm["id"]]
        out.append(f'  subgraph arm_{arm["id"]}["{arm["label"]}"]')
        out.append("    direction TB")
        if members:
            out += [node_line(n) for n in members]
        else:
            out.append(f'    arm_{arm["id"]}_void["(empty) no 51 factor"]:::c_unknown_00')
        out.append("  end")

    for layer, title in (("straddle", "straddles Writes <-> Readers"),
                          ("boundary", "Boundary -- adjacent only"),
                          ("ring", "Substrate -- no 51-factor slot")):
        members = by_layer.get(layer, [])
        if not members:
            continue
        out.append(f'  subgraph grp_{layer}["{title}"]')
        out.append("    direction TB")
        out += [node_line(n) for n in members]
        out.append("  end")

    arm_ids = {a["id"] for a in doc["arms"]}
    for e in doc.get("constraints", []):
        tgt = f'arm_{e["to"]}' if e["to"] in arm_ids else f'n_{e["to"]}'
        out.append(f'  n_{e["from"]} -->|{e["label"]}| {tgt}')
    for e in doc.get("dependencies", []):
        out.append(f'  n_{e["from"]} -.->|{e["label"]}| n_{e["to"]}')
    for p in doc.get("pairs", []):
        out.append(f'  n_{p["a"]} <-->|"{p["label"]}"| n_{p["b"]}')

    for n in doc["nodes"]:
        out.append(f'  class n_{n["id"]} {_cls(n["evidence"], n["dark"], n["blocked"])}')
    return "\n".join(out) + "\n"


def emit_dot(doc: dict) -> str:
    colors = {k: v[0] for k, v in FILL.items()}
    out = ["digraph mind_map {", "  layout=twopi; overlap=false; splines=true;",
           '  node [shape=box, style="rounded,filled", fontname="Helvetica"];']
    for a in doc["arms"]:
        out.append(f'  subgraph cluster_{a["id"]} {{ label="{a["label"]}"; color="#b0bec5"; }}')
    for n in doc["nodes"]:
        style = "rounded,filled"
        if n["dark"]:
            style += ",dashed"
        label = (_badges(n) + n["label"]).replace('"', "'")
        attrs = [f'label="{label}"', f'fillcolor="{colors[n["evidence"]]}"', f'style="{style}"']
        if n["blocked"]:
            attrs += ['color="#c62828"', "penwidth=3"]
        out.append(f'  n_{n["id"]} [{",".join(attrs)}];')
    arm_ids = {a["id"] for a in doc["arms"]}
    for a in doc["arms"]:
        members = [n for n in doc["nodes"] if n.get("arm") == a["id"]]
        for m in members:
            out.append(f'  n_{m["id"]} -> arm_dot_{a["id"]} [style=invis];')
    for e in doc.get("constraints", []):
        tgt = f'arm_dot_{e["to"]}' if e["to"] in arm_ids else f'n_{e["to"]}'
        out.append(f'  n_{e["from"]} -> {tgt} [label="{e["label"]}", style=dashed, color="#546e7a"];')
    for e in doc.get("dependencies", []):
        out.append(f'  n_{e["from"]} -> n_{e["to"]} [label="{e["label"]}", style=bold, color="#c62828"];')
    for p in doc.get("pairs", []):
        out.append(f'  n_{p["a"]} -> n_{p["b"]} [dir=both, label="{p["label"]}", color="#8e24aa"];')
    return "\n".join(out) + "\n}\n"


def emit_md(doc: dict) -> str:
    rows = ["| Node | Layer | Role | Evidence | Flags | Falsifier | Verified |",
            "|---|---|---|---|---|---|---|"]
    for n in doc["nodes"]:
        flags = ", ".join(f for f, on in (("dark", n["dark"]), ("blocked", n["blocked"]),
                                           ("unverified", n["last_verified"] == "unverified")) if on) or "-"
        rows.append(
            f'| {n["label"]} | {n["layer"]} | {n.get("arm") or n.get("property") or "-"} '
            f'| {n["evidence"]} | {flags} | {n["falsifier_status"]} | {n["last_verified"]} |')
    return "\n".join(rows) + "\n"


# ──────────────────────────────── main ─────────────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--format", choices=("mermaid", "dot", "md"), default="mermaid")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--verify", action="store_true", help="also run source.absent checks")
    ap.add_argument("--map", type=Path, default=MAP)
    args = ap.parse_args()

    doc = load(args.map)
    errs, warns = check(doc, verify_absent=args.verify)

    if args.check:
        nodes = doc.get("nodes", [])
        unver = sum(1 for n in nodes if n["last_verified"] == "unverified")
        dark = sum(1 for n in nodes if n["dark"])
        blkd = sum(1 for n in nodes if n["blocked"])
        print(f"{len(nodes)} nodes | {unver} unverified | {dark} dark | {blkd} blocked")
        for w in warns:
            print(f"  warn  {w}")
        for e in errs:
            print(f"  ERROR {e}")
        for n in nodes:
            for m in UNBLOCK_RE.finditer(str(n.get("notes") or "")):
                print(f"  unblock  {n['id']}: {m.group(1)}"
                      + (" (past due — see warn above)"
                         if date.fromisoformat(m.group(1)) < date.today() else ""))
        if doc["meta"].get("bootstrap") is False and unver:
            errs.append("bootstrap is false but unverified nodes remain")
            print(f"  ERROR bootstrap is false but {unver} nodes are still unverified")
        return 1 if errs else 0

    for e in errs:
        print(f"ERROR {e}", file=sys.stderr)
    if errs:
        return 1

    emit = {"mermaid": emit_mermaid, "dot": emit_dot, "md": emit_md}[args.format]
    sys.stdout.write(emit(doc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
