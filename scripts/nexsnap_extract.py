#!/usr/bin/env python3
"""nexsnap_extract.py — pass 1 extractor inspection.

Runs each corpus-section extractor, prints output to console.
No file writes, no commits. Pure read-only inspection so we can
verify what each section will contain before assembling the corpus.

Usage:
  python3 scripts/nexsnap_extract.py [section]

Sections (run all if no arg given):
  doctrine_principles, theory_x_stages, faculty_outcomes,
  port_status, stage_map, substrate_schema, gui_routes,
  spec_docs, amendments, anti_patterns, runtime_state,
  unmapped_roster
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

REPO = Path("/home/rr/Desktop/nex5")
THEORY_X = REPO / "theory_x"
SUBSTRATE = REPO / "substrate"
GUI = REPO / "gui"
DATA = REPO / "data"


def banner(title):
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def extract_doctrine_principles():
    """Pull §1 framing, §3 architectural principle, §7 out-of-scope bullets.
    From DOCTRINE.md, verbatim sections only."""
    text = (THEORY_X / "DOCTRINE.md").read_text()
    sections = {}

    # §1 Purpose first paragraph
    m = re.search(r"## 1\. Purpose\s*\n+(.+?)\n\n", text, re.DOTALL)
    if m:
        sections["s1_purpose"] = m.group(1).strip()

    # §3 Architectural Principle full section
    m = re.search(r"## 3\. Architectural Principle\s*\n+(.+?)(?=\n## )", text, re.DOTALL)
    if m:
        sections["s3_architecture"] = m.group(1).strip()

    # §7 Out of Scope (just the bullets)
    m = re.search(r"## 7\. Out of Scope\s*\n+(.+?)(?=\n## )", text, re.DOTALL)
    if m:
        sections["s7_out_of_scope"] = m.group(1).strip()

    return sections


def extract_theory_x_stages():
    """Build stage list from filesystem + read each stage __init__.py docstring."""
    stages = []
    for path in sorted(THEORY_X.glob("stage*")):
        if not path.is_dir():
            continue
        init = path / "__init__.py"
        docstring = ""
        if init.exists():
            text = init.read_text()
            m = re.match(r'"""(.+?)"""', text, re.DOTALL)
            if m:
                docstring = m.group(1).strip().split("\n")[0]
        files = [p.name for p in path.iterdir()
                 if p.is_file() and p.suffix == ".py" and not p.name.startswith("__pycache__")]
        stages.append({
            "name": path.name,
            "doc": docstring,
            "py_files": files,
        })
    return stages


def extract_faculty_outcomes():
    """Pull §2.3, §2.4 from FACULTY_MODEL.md."""
    text = (THEORY_X / "FACULTY_MODEL.md").read_text()
    out = {}

    m = re.search(r"### §2\.3 The Coherence Gate\s*\n+(.+?)(?=\n### )", text, re.DOTALL)
    if m:
        out["coherence_gate"] = m.group(1).strip()

    m = re.search(r"### §2\.4 Four Outcomes\s*\n+(.+?)(?=\n### )", text, re.DOTALL)
    if m:
        out["four_outcomes"] = m.group(1).strip()

    return out


def extract_port_status():
    """Parse the §5 priority table from DOCTRINE.md and count by status."""
    text = (THEORY_X / "DOCTRINE.md").read_text()
    m = re.search(r"## 5\. Priority Order\s*\n+(.+?)\n\nOrdering", text, re.DOTALL)
    if not m:
        return {"error": "section_not_found"}
    table = m.group(1)

    rows = []
    for line in table.splitlines():
        if line.strip().startswith("| #") or line.strip().startswith("|---"):
            continue
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|") if c.strip()]
        if len(cells) >= 4:
            rows.append({
                "num": cells[0],
                "node": cells[1].split("**")[1] if "**" in cells[1] else cells[1],
                "function": cells[2],
                "status": cells[3],
            })

    status_counts = Counter(r["status"].split()[0] for r in rows if r.get("status"))
    return {"rows": rows, "status_counts": dict(status_counts)}


def extract_stage_map():
    """For every stage directory, list source files with line counts."""
    out = []
    for path in sorted(THEORY_X.glob("stage*")):
        if not path.is_dir():
            continue
        files = []
        for f in sorted(path.iterdir()):
            if f.is_file() and f.suffix == ".py" and "__pycache__" not in str(f) and ".bak" not in f.name:
                try:
                    lines = len(f.read_text(errors="ignore").splitlines())
                except Exception:
                    lines = 0
                files.append({"name": f.name, "lines": lines})
        out.append({"stage": path.name, "files": files})
    return out


def extract_substrate_schema():
    """Parse schema/*.sql and pull CREATE TABLE statements + table names."""
    schemas = {}
    schema_dir = SUBSTRATE / "schema"
    for f in sorted(schema_dir.glob("*.sql")):
        text = f.read_text()
        tables = re.findall(
            r"CREATE TABLE(?:\s+IF NOT EXISTS)?\s+(\w+)",
            text, re.IGNORECASE,
        )
        schemas[f.stem] = sorted(set(tables))
    return schemas


def extract_gui_routes():
    """Extract Flask route decorators from gui/server.py."""
    text = (GUI / "server.py").read_text()
    routes = re.findall(
        r'@app\.(get|post|route)\(["\']([^"\']+)["\']',
        text,
    )
    return [{"method": m.upper(), "path": p} for m, p in routes]


def extract_spec_docs():
    """List all .md files in theory_x/ with size and mtime."""
    out = []
    for f in sorted(THEORY_X.glob("*.md")):
        st = f.stat()
        out.append({
            "name": f.name,
            "size_kb": round(st.st_size / 1024, 1),
            "mtime": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d"),
        })
    return out


def extract_amendments():
    """Pull last 8 amendment paragraphs from DOCTRINE.md (the *Phase X amendment* italicized blocks)."""
    text = (THEORY_X / "DOCTRINE.md").read_text()
    amendments = re.findall(
        r"\*Phase \d+\w?\s*amendment[^*]*?\*",
        text, re.DOTALL,
    )
    out = []
    for a in amendments[-8:]:
        clean = re.sub(r"\s+", " ", a.strip("*").strip())
        out.append(clean[:240] + ("..." if len(clean) > 240 else ""))
    return out


def extract_anti_patterns():
    """Pull anti-pattern names + first-line summaries from §8."""
    text = (THEORY_X / "DOCTRINE.md").read_text()
    m = re.search(r"## 8\. Anti-Patterns.*?\n+(.+?)(?=\n## )", text, re.DOTALL)
    if not m:
        return []
    section = m.group(1)
    patterns = []
    # Anti-pattern names are bolded with **
    for match in re.finditer(r"\*\*([^*]+)\*\*\s*\n(.+?)(?=\n\*\*|\Z)", section, re.DOTALL):
        name = match.group(1).strip()
        body = match.group(2).strip().split("\n")[0]
        patterns.append({"name": name, "summary": body[:160]})
    return patterns


def extract_runtime_state():
    """Quick read of drives_competing, voice_profile, fountain 24h, gate 24h."""
    conv = sqlite3.connect(f"file:{DATA}/conversations.db?mode=ro", uri=True)
    conv.row_factory = sqlite3.Row
    dyn = sqlite3.connect(f"file:{DATA}/dynamic.db?mode=ro", uri=True)
    dyn.row_factory = sqlite3.Row
    bel = sqlite3.connect(f"file:{DATA}/beliefs.db?mode=ro", uri=True)
    bel.row_factory = sqlite3.Row
    now = time.time()

    state = {}

    drow = conv.execute("SELECT * FROM drives_competing WHERE id = 1").fetchone()
    if drow:
        state["drives"] = {k: drow[k] for k in (
            "coherence", "exploration", "integration",
            "self_preservation", "curiosity"
        )}
        state["drives"]["tension_pairs"] = drow["tension_pairs"]

    vp = conv.execute(
        "SELECT drive_pair, frequency FROM voice_profile ORDER BY frequency DESC"
    ).fetchall()
    state["voice_profile"] = [{"pair": r["drive_pair"], "freq": r["frequency"]} for r in vp]

    fc = dyn.execute(
        "SELECT hot_branch, COUNT(*) AS n FROM fountain_events "
        "WHERE ts > ? GROUP BY hot_branch ORDER BY n DESC",
        (now - 86400,),
    ).fetchall()
    state["fountain_24h_by_branch"] = {r["hot_branch"] or "null": r["n"] for r in fc}

    try:
        gc = bel.execute(
            "SELECT outcome, COUNT(*) AS n FROM gate_decisions WHERE ts > ? GROUP BY outcome",
            (now - 86400,),
        ).fetchall()
        state["gate_24h"] = {r["outcome"]: r["n"] for r in gc}
    except Exception as e:
        state["gate_24h"] = f"error: {e}"

    return state


def extract_unmapped_roster():
    """Pull Tier A/B/C unmapped node names from SENTIENCE_TRANSLATION_MAP.md.
    Format: three-column tables. Node cell may contain multiple nodes
    joined by ' + '. Returns list grouped by tier."""
    text = (THEORY_X / "SENTIENCE_TRANSLATION_MAP.md").read_text()
    tiers = {}
    for tier_label, end_marker in [
        ("A", r"### Tier B"),
        ("B", r"### Tier C"),
        ("C", r"\n---"),
    ]:
        pattern = r"### Tier " + tier_label + r"[^\n]*\n+(.+?)(?=" + end_marker + r")"
        m = re.search(pattern, text, re.DOTALL)
        if not m:
            continue
        section = m.group(1)
        rows = []
        for line in section.splitlines():
            line = line.strip()
            if not line.startswith("|") or line.startswith("|---") or line.startswith("| S5.5"):
                continue
            cells = [c.strip() for c in line.split("|") if c.strip()]
            if len(cells) < 2:
                continue
            # Extract all backtick-wrapped node names from cell[0]
            node_names = re.findall(r"`([^`]+)`", cells[0])
            if not node_names:
                continue
            function = cells[1] if len(cells) > 1 else ""
            rows.append({
                "nodes": node_names,
                "function": function,
            })
        tiers["tier_" + tier_label] = rows
    return tiers


SECTIONS = {
    "doctrine_principles": extract_doctrine_principles,
    "theory_x_stages": extract_theory_x_stages,
    "faculty_outcomes": extract_faculty_outcomes,
    "port_status": extract_port_status,
    "stage_map": extract_stage_map,
    "substrate_schema": extract_substrate_schema,
    "gui_routes": extract_gui_routes,
    "spec_docs": extract_spec_docs,
    "amendments": extract_amendments,
    "anti_patterns": extract_anti_patterns,
    "runtime_state": extract_runtime_state,
    "unmapped_roster": extract_unmapped_roster,
}


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    for name, fn in SECTIONS.items():
        if only and only != name:
            continue
        banner(name.upper())
        try:
            result = fn()
            if isinstance(result, (dict, list)):
                print(json.dumps(result, indent=2, default=str)[:3000])
            else:
                print(str(result)[:3000])
        except Exception as e:
            print(f"ERROR in {name}: {e}")
        print()


if __name__ == "__main__":
    main()
