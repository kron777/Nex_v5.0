"""One-pen census -- read-only static scan for database writes that bypass the Writers.

SPECIFICATION.md section 8: one Writer per database; writes elsewhere are a bug by
definition. This tool lists every write-capable ``connect()`` call outside
``substrate/`` and the tests, and classifies each site:

- ``writes``: the enclosing function contains write SQL (INSERT/UPDATE/DELETE/
  REPLACE/CREATE/ALTER/DROP), ``executescript`` or ``.commit()``;
- ``hands_off``: the connection is returned or passed to another call, so a
  caller or helper may write through it -- review those by hand;
- ``runtime``: the file is under a runtime package (theory_x/, gui/, voice/,
  strikes/, ...) rather than a standalone script or tool.

It is a heuristic over source text, not proof: SQL built in variables elsewhere,
connections stored on attributes and dynamic imports can evade it, and it says
nothing about reachability (a dormant or flag-gated module still appears). It
never opens a database. Usage::

    python tools/one_pen_census.py [--json] [ROOT]
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

RUNTIME_PREFIXES = ("theory_x/", "gui/", "voice/", "strikes/", "alpha/", "speech/")
_SKIP_PREFIXES = ("tests/", "ci/", "substrate/", ".git/")
_WRITE_SQL = re.compile(
    r"\b(INSERT\s+(OR\s+\w+\s+)?INTO|UPDATE\s+\w+\s+SET|DELETE\s+FROM|REPLACE\s+INTO|"
    r"CREATE\s+(TABLE|INDEX|TRIGGER|VIEW)|ALTER\s+TABLE|DROP\s+(TABLE|INDEX))\b",
    re.I,
)


def _is_read_only(call_src: str) -> bool:
    return "mode=ro" in call_src or "read_only=True" in call_src


def _bound_name(call: ast.Call, parents: dict) -> str | None:
    p = parents.get(call)
    while p is not None:
        if isinstance(p, ast.Assign) and isinstance(p.targets[0], ast.Name):
            return p.targets[0].id
        if isinstance(p, ast.withitem) and isinstance(p.optional_vars, ast.Name):
            return p.optional_vars.id
        if isinstance(p, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Module)):
            return None
        p = parents.get(p)
    return None


def scan_file(path: Path, rel: str) -> list[dict]:
    src = path.read_text(errors="ignore")
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []
    parents = {c: n for n in ast.walk(tree) for c in ast.iter_child_nodes(n)}
    sites = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        name = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
        if name != "connect" or _is_read_only(ast.unparse(node)):
            continue
        scope = node
        while scope in parents and not isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef)):
            scope = parents[scope]
        if not isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef)):
            scope = tree
        seg = ast.get_source_segment(src, scope) or src
        var = _bound_name(node, parents)
        returned = bool(var) and any(
            isinstance(n, ast.Return) and n.value is not None
            and isinstance(n.value, ast.Name) and n.value.id == var
            for n in ast.walk(scope))
        passed = bool(var) and any(
            isinstance(n, ast.Call) and any(isinstance(a, ast.Name) and a.id == var for a in n.args)
            for n in ast.walk(scope))
        sites.append({
            "site": f"{rel}:{node.lineno}",
            "function": getattr(scope, "name", "<module>"),
            "writes": bool(_WRITE_SQL.search(seg)) or ".commit()" in seg or "executescript" in seg,
            "hands_off": returned or passed,
            "runtime": rel.startswith(RUNTIME_PREFIXES),
        })
    return sites


def census(root: Path) -> list[dict]:
    out = []
    for path in sorted(root.rglob("*.py")):
        rel = path.relative_to(root).as_posix()
        if rel.startswith(_SKIP_PREFIXES) or "/tests/" in rel:
            continue
        out.extend(scan_file(path, rel))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("root", nargs="?", default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    sites = census(Path(args.root))
    if args.json:
        json.dump(sites, sys.stdout, indent=1)
        print()
        return 0
    groups = {
        "runtime, writes": [s for s in sites if s["runtime"] and s["writes"]],
        "runtime, hands its connection off (review)": [
            s for s in sites if s["runtime"] and not s["writes"] and s["hands_off"]],
        "runtime, read-only use of a write-capable connection": [
            s for s in sites if s["runtime"] and not s["writes"] and not s["hands_off"]],
        "script/tool, writes": [s for s in sites if not s["runtime"] and s["writes"]],
        "script/tool, read-only use": [s for s in sites if not s["runtime"] and not s["writes"]],
    }
    print(f"{len(sites)} write-capable connect() sites outside substrate/ and tests")
    for title, rows in groups.items():
        print(f"\n{title}: {len(rows)}")
        if title.endswith("writes") or "review" in title:
            for s in rows:
                print(f"  {s['site']}  {s['function']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
