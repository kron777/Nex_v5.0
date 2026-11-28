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
import ast
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
# build_difficulty: the artist's-rough-sketch triage (Jon, 2026-11-15) -- separate from
# `evidence` (what's true of the code today) and `dark`/`blocked` (why it doesn't run).
# This says how hard the REMAINING work is to judge, so "already shipped, falsifier just
# needs a re-run" and "nobody has designed a mechanism yet" don't look like the same kind
# of open item.
#   shipped    -- built (dark or live); what's left is arming/measuring, not designing.
#   tractable  -- open, but a real mechanism is sketched and the hook point is known.
#   unclear    -- open, and no credible mechanism has been designed yet.
#   gorge      -- reasoned to have no satisfiable path at all (rare; matches DAG usage).
BUILD_DIFFICULTY = ("shipped", "tractable", "unclear", "gorge")
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

# The mind map is a descriptive index, never a runtime decision authority.
# "blocked" is deliberately NOT forbidden: it is an evidence/status modifier,
# not permission to block an action.
FORBIDDEN_AUTHORITY_KEYS = {
    "gate", "veto", "authority", "permission", "priority", "score", "block",
    "action_gate", "action_veto", "action_score", "decision_gate", "decision_score",
    "decision_authority", "action_authority", "execution_authority",
    "blocks_action", "vetoes_action", "scores_action",
    "can_gate", "can_veto", "can_block", "can_score",
}
RUNTIME_ROOTS = (
    "run.py", "gui", "theory_x", "substrate", "speech", "voice", "admin",
    "strikes", "influence_trace.py",
    "nex_config.py", "power_switch.py", "keystone.py", "alpha.py", "errors.py",
    "nex5_rate.py",
)


def check_descriptive_only(doc: dict, root: Path = ROOT) -> list[str]:
    """Enforce that MIND_MAP is descriptive and is not consumed by NEX runtime code.

    The RDO/Watcher and developer tooling may read the map as evidence. Runtime
    modules may not import it or load MIND_MAP.yaml as a decision input.
    """
    errs: list[str] = []
    constraint = " ".join(str(doc.get("meta", {}).get("constraint", "")).split()).lower()
    if ("descriptive only" not in constraint
            or "no node in this map may gate, score, block, or veto an action" not in constraint):
        errs.append("meta.constraint must preserve the descriptive-only / no-action-authority rule")

    for node in doc.get("nodes", []):
        forbidden = sorted(set(str(k).lower() for k in node) & FORBIDDEN_AUTHORITY_KEYS)
        if forbidden:
            errs.append(f"{node.get('id', '<missing id>')}: forbidden action-authority field(s): {', '.join(forbidden)}")

    runtime_files = []
    for rel in RUNTIME_ROOTS:
        candidate = root / rel
        if candidate.is_file() and candidate.suffix == ".py":
            runtime_files.append(candidate)
        elif candidate.is_dir():
            runtime_files.extend(candidate.rglob("*.py"))

    for path in sorted(set(runtime_files)):
        relative = path.relative_to(root)
        if any(part in {".git", ".venv", "venv", "__pycache__"} for part in relative.parts):
            continue
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(relative))
        except SyntaxError:
            # A syntactically invalid module cannot be imported by the runtime;
            # syntax validity is handled by the Python test/build checks.
            continue
        except (OSError, UnicodeError) as exc:
            errs.append(f"{relative}: cannot inspect runtime source for mind-map authority use: {exc}")
            continue

        docstrings = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and node.body:
                first = node.body[0]
                if (isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant)
                        and isinstance(first.value.value, str)):
                    docstrings.add(id(first.value))

        for node in ast.walk(tree):
            imported = False
            if isinstance(node, ast.Import):
                imported = any(
                    alias.name == "mind_map" or alias.name.startswith("mind_map.")
                    for alias in node.names
                )
            elif isinstance(node, ast.ImportFrom):
                imported = bool(node.module and (
                    node.module == "mind_map" or node.module.startswith("mind_map.")
                ))
            if imported:
                errs.append(f"{relative}:{getattr(node, 'lineno', 1)}: runtime code imports mind_map")
            if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                    and "MIND_MAP.yaml" in node.value and id(node) not in docstrings):
                errs.append(f"{relative}:{getattr(node, 'lineno', 1)}: runtime code references MIND_MAP.yaml")
    return errs




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


def git_history_complete() -> bool:
    """Whether source-drift checks can trust per-path git log results.

    actions/checkout defaults to fetch-depth=1. In a shallow clone,
    `git log -1 -- <path>` reports the checkout commit for every tracked
    path, manufacturing false STALE warnings. CI requests full history;
    local shallow/archive checkouts get one explicit warning and skip only
    the date comparison rather than asserting a false change date.
    """
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--is-shallow-repository"],
            cwd=ROOT, capture_output=True, text=True, check=True,
        ).stdout.strip()
        return out == "false"
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def last_commit_ts(rel: str) -> float | None:
    """Latest path commit timestamp; call only with complete git history."""
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%ct", "--", rel],
            cwd=ROOT, capture_output=True, text=True, check=True,
        ).stdout.strip()
        return float(out) if out else None
    except (subprocess.CalledProcessError, ValueError, FileNotFoundError):
        return None


# A quoted "path.ext:a" or "path.ext:a-b" inside the YAML text (source refs).
_QUOTED_REF_RE = re.compile(r'"(?P<ref>[^":\s]+\.[A-Za-z0-9]+:\d+(?:-\d+)?)"')
_NODE_ID_RE = re.compile(r"^\s*-\s+id:\s*(\S+)")
_DRIFT_WINDOW = 400


def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)


def _source_ref_lines(lines: list[str]) -> set[int]:
    """Return one-based line numbers inside actual node source mappings only.

    Notes often contain explanatory code pointers. They are prose, not anchors,
    and must never be drift-checked or rewritten by --reanchor.
    """
    selected: set[int] = set()
    source_indent: int | None = None
    for lineno, line in enumerate(lines, 1):
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        if re.match(r"^source\s*:", stripped):
            source_indent = indent
            selected.add(lineno)
            continue
        if source_indent is None:
            continue
        if stripped and indent <= source_indent and re.match(r"^[A-Za-z_][\w-]*\s*:", stripped):
            source_indent = None
            continue
        selected.add(lineno)
    return selected


def _blame_line_commits(map_path: Path, root: Path) -> dict[int, str]:def _blame_line_commits(map_path: Path, root: Path) -> dict[int, str]:
    """Map each YAML line number to the commit that last wrote it."""
    try:
        rel = map_path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return {}
    r = _git(root, "blame", "--porcelain", "--", rel)
    if r.returncode != 0:
        return {}
    out: dict[int, str] = {}
    for line in r.stdout.splitlines():
        parts = line.split(" ")
        if len(parts) >= 3 and re.fullmatch(r"[0-9a-f]{40}", parts[0]):
            out[int(parts[2])] = parts[0]
    return out


def _commit_time(root: Path, sha: str, cache: dict) -> int:
    if sha not in cache:
        r = _git(root, "show", "-s", "--format=%ct", sha)
        cache[sha] = int(r.stdout.strip() or 0) if r.returncode == 0 else 0
    return cache[sha]


def _newer(root: Path, shas: list[str], times: dict) -> str:
    """The later of the candidate commits: a descendant wins over its ancestor;
    unrelated commits (two merged branches) fall back to committer time."""
    best = shas[0]
    for sha in shas[1:]:
        if sha == best:
            continue
        if _git(root, "merge-base", "--is-ancestor", best, sha).returncode == 0:
            best = sha
        elif _git(root, "merge-base", "--is-ancestor", sha, best).returncode != 0 \
                and _commit_time(root, sha, times) > _commit_time(root, best, times):
            best = sha
    return best


def anchor_drift(map_path: Path = MAP, root: Path = ROOT) -> list[dict]:
    """Find cited line ranges that no longer hold the lines they cited.

    STALE is day-granular: an edit later on the same day as a verification,
    or a branch merged after the anchor was written, shifts cited lines with
    no warning. For each quoted ref, the baseline is the newer of two commits:
    the one that last wrote the ref's YAML line and the one that last wrote its
    node's ``last_verified`` line (a re-verification that kept the anchor).
    The cited range at the baseline is compared with the working tree; when the
    same lines sit elsewhere the record carries their new position. Anchors
    and dates not yet committed are not judged. Call only with complete git
    history. Returns one dict per drifted ref: node, path, a, b, yaml_line,
    baseline, and new_a/new_b (None when the content itself changed).
    """
    commits = _blame_line_commits(map_path, root)
    if not commits:
        return []
    text = map_path.read_text(encoding="utf-8").splitlines()
    # Pass 1: each line's node, and each node's last_verified line.
    node_of: dict[int, str] = {}
    verified_line: dict[str, int] = {}
    node = "?"
    for lineno, line in enumerate(text, 1):
        m_id = _NODE_ID_RE.match(line)
        if m_id:
            node = m_id.group(1)
        elif re.match(r"^[A-Za-z_]+:", line):
            node = "?"
        node_of[lineno] = node
        if node != "?" and re.match(r"^\s+last_verified:", line):
            verified_line[node] = lineno
    times: dict[str, int] = {}
    old_cache: dict[tuple[str, str], list[str] | None] = {}
    cur_cache: dict[str, list[str] | None] = {}
    out: list[dict] = []
    source_lines = _source_ref_lines(text)
    for lineno, line in enumerate(text, 1):
        if lineno not in source_lines:
            continue
        for m in _QUOTED_REF_RE.finditer(line):
            ref = REF_RE.match(m.group("ref"))
            if not ref or not ref.group("a"):
                continue
            node = node_of.get(lineno, "?")
            shas = [commits.get(lineno), commits.get(verified_line.get(node, -1))]
            if not shas[0] or set(shas[0]) == {"0"}:
                continue        # the anchor itself is being edited now
            shas = [x for x in shas if x and set(x) != {"0"}]
            sha = _newer(root, shas, times)
            path, a = ref.group("path"), int(ref.group("a"))
            b = int(ref.group("b") or a)
            if (sha, path) not in old_cache:
                r = _git(root, "show", f"{sha}:{path}")
                old_cache[(sha, path)] = r.stdout.splitlines() if r.returncode == 0 else None
            if path not in cur_cache:
                f = root / path
                cur_cache[path] = (f.read_text(encoding="utf-8", errors="ignore").splitlines()
                                   if f.is_file() else None)
            old, cur = old_cache[(sha, path)], cur_cache[path]
            if old is None or cur is None or b > len(old):
                continue        # missing paths and over-long ranges are check()'s errors
            want = old[a - 1:b]
            if cur[a - 1:b] == want:
                continue
            shifts = [
                d for d in range(-_DRIFT_WINDOW, _DRIFT_WINDOW + 1)
                if d and a - 1 + d >= 0 and cur[a - 1 + d:b + d] == want
            ]
            # Re-anchor only when the cited content has exactly one new home.
            # Repeated boilerplate or duplicated blocks are ambiguous evidence;
            # choosing the nearest match could silently point at the wrong code.
            shift = shifts[0] if len(shifts) == 1 else None
            out.append({"node": node, "path": path, "a": a, "b": b, "yaml_line": lineno,
                        "baseline": sha, "ambiguous": len(shifts) > 1,
                        "new_a": None if shift is None else a + shift,
                        "new_b": None if shift is None else b + shift})
    return out


def _span(a: int, b: int) -> str:
    return f"{a}" if a == b else f"{a}-{b}"


def anchor_drift_warnings(map_path: Path = MAP, root: Path = ROOT) -> list[str]:
    """Human-readable DRIFT warnings for anchor_drift()."""
    warns = []
    for d in anchor_drift(map_path, root):
        where = (
            "ambiguous duplicate matches; manual review required"
            if d.get("ambiguous") else
            "content changed or removed" if d["new_a"] is None else
            f"now at :{_span(d['new_a'], d['new_b'])}"
        )
        warns.append(f"{d['node']}: DRIFT — {d['path']}:{_span(d['a'], d['b'])} no longer "
                     f"holds the lines it cited at {d['baseline'][:8]} ({where})")
    return warns


def reanchor(map_path: Path = MAP, root: Path = ROOT) -> tuple[list[str], list[str]]:
    """Rewrite refs whose cited lines only MOVED; never touch dates or notes.

    Returns (applied, needs_review). A ref whose content changed is left
    untouched and reported for re-verification by a person.
    """
    drift = anchor_drift(map_path, root)
    lines = map_path.read_text(encoding="utf-8").split("\n")
    applied, review = [], []
    for d in drift:
        old = f'"{d["path"]}:{_span(d["a"], d["b"])}"'
        if d["new_a"] is None:
            reason = ("has multiple identical destinations" if d.get("ambiguous")
                      else "content changed or disappeared")
            review.append(f"{d['node']}: {d['path']}:{_span(d['a'], d['b'])} {reason} "
                          f"since {d['baseline'][:8]} -- re-verify by hand")
            continue
        new = f'"{d["path"]}:{_span(d["new_a"], d["new_b"])}"'
        i = d["yaml_line"] - 1
        if lines[i].count(old) != 1:
            review.append(f"{d['node']}: {old} not uniquely on line {d['yaml_line']} -- skipped")
            continue
        lines[i] = lines[i].replace(old, new)
        applied.append(f"{d['node']}: {old} -> {new}")
    if applied:
        map_path.write_text("\n".join(lines), encoding="utf-8")
    return applied, review


# ─────────────────────────────── checking ──────────────────────────────
def check(doc: dict, verify_absent: bool = False) -> tuple[list, list]:
    errs: list[str] = check_descriptive_only(doc, ROOT)
    warns: list[str] = []
    history_complete = git_history_complete()
    if not history_complete:
        warns.append(
            "source drift: Git history is shallow or unavailable; "
            "last_verified date checks skipped"
        )
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

        # directive: an explicit A->B vector for the node (Jon, 2026-11-15) --
        # optional for now (not retrofitted onto all 30 nodes), but any node
        # that declares one must give both ends, non-empty.
        directive = n.get("directive")
        if directive is not None:
            if not isinstance(directive, dict):
                errs.append(f"{nid}: directive must be a mapping with `from`/`to`")
            else:
                for end in ("from", "to"):
                    if not str(directive.get(end) or "").strip():
                        errs.append(f"{nid}: directive.{end} must be a non-empty string")

        bd = n.get("build_difficulty")
        if bd is not None and bd not in BUILD_DIFFICULTY:
            errs.append(f"{nid}: build_difficulty must be one of {BUILD_DIFFICULTY}")
        sketch = n.get("sketch")
        if sketch is not None and not str(sketch).strip():
            errs.append(f"{nid}: sketch, if present, must be non-empty")

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
        if history_complete and lv != "unverified" and kind in ("file", "composite"):
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


def emit_triage(doc: dict) -> str:
    # "shipped" means code exists claiming the aspect -- it does NOT mean the gap between
    # the aspect and that code is actually closed. Split by falsifier_status so a passed,
    # confirmed node (the gap is actually closed) doesn't read the same as an unrun or
    # failed one (the gap's status is unknown, or known still open) wearing the same label.
    SHIPPED_SPLIT = {
        "pass": "shipped/confirmed",
        "fail": "shipped/contradicted",
        "unrun": "shipped/claimed",
        "na": "shipped/dormant",
    }
    groups: dict[str, list] = {}
    for n in doc["nodes"]:
        bd = n.get("build_difficulty") or "untriaged"
        key = SHIPPED_SPLIT.get(n["falsifier_status"], bd) if bd == "shipped" else bd
        groups.setdefault(key, []).append(n)
    order = (["shipped/confirmed", "shipped/claimed", "shipped/dormant", "shipped/contradicted"]
             + [k for k in BUILD_DIFFICULTY if k != "shipped"] + ["untriaged"])
    titles = {
        "shipped/confirmed": "SHIPPED, CONFIRMED -- falsifier passed, the gap is actually closed",
        "shipped/claimed": "SHIPPED, CLAIMED -- code exists, falsifier unrun, gap status unknown",
        "shipped/dormant": "SHIPPED, DORMANT -- deliberately disarmed, no falsifier currently applicable",
        "shipped/contradicted": "SHIPPED, CONTRADICTED -- falsifier FAILED, the gap is still open",
        "tractable": "TRACTABLE -- open, mechanism sketched, hook point known",
        "unclear": "UNCLEAR -- open, no credible mechanism designed yet",
        "gorge": "GORGE -- reasoned to have no satisfiable path",
        "untriaged": "UNTRIAGED -- no build_difficulty set yet",
    }
    out = []
    for key in order:
        members = groups.get(key) or []
        if not members:
            continue
        out.append(f"## {titles[key]} ({len(members)})")
        for n in members:
            sk = n.get("sketch")
            out.append(f"  - {n['label']}" + (f": {sk}" if sk else ""))
        out.append("")
    return "\n".join(out) + "\n"


def emit_md(doc: dict) -> str:
    rows = ["| Node | Layer | Role | Evidence | Flags | Directive (A -> B) | Falsifier | Verified |",
            "|---|---|---|---|---|---|---|---|"]
    for n in doc["nodes"]:
        flags = ", ".join(f for f, on in (("dark", n["dark"]), ("blocked", n["blocked"]),
                                           ("unverified", n["last_verified"] == "unverified")) if on) or "-"
        d = n.get("directive")
        directive = f'{d["from"]} -> {d["to"]}' if d else "-"
        rows.append(
            f'| {n["label"]} | {n["layer"]} | {n.get("arm") or n.get("property") or "-"} '
            f'| {n["evidence"]} | {flags} | {directive} | {n["falsifier_status"]} | {n["last_verified"]} |')
    return "\n".join(rows) + "\n"


# ──────────────────────────────── main ─────────────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--format", choices=("mermaid", "dot", "md", "triage"), default="mermaid")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--verify", action="store_true", help="also run source.absent checks")
    ap.add_argument("--map", type=Path, default=MAP)
    ap.add_argument("--reanchor", action="store_true",
                    help="rewrite refs whose cited lines only moved (needs full git history)")
    args = ap.parse_args()

    if args.reanchor:
        if not git_history_complete():
            print("reanchor needs complete git history", file=sys.stderr)
            return 1
        applied, review = reanchor(args.map, ROOT)
        for a in applied:
            print(f"  moved   {a}")
        for r in review:
            print(f"  review  {r}")
        print(f"{len(applied)} anchors moved, {len(review)} need review")
        return 0

    doc = load(args.map)
    errs, warns = check(doc, verify_absent=args.verify)

    if args.check:
        if git_history_complete():
            warns.extend(anchor_drift_warnings(args.map, ROOT))
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

    emit = {"mermaid": emit_mermaid, "dot": emit_dot, "md": emit_md, "triage": emit_triage}[args.format]
    sys.stdout.write(emit(doc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
