"""Phase 0 authority boundary: MIND_MAP is descriptive, not an action controller."""
from __future__ import annotations

import ast
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOTS = (
    ROOT / "run.py",
    ROOT / "gui",
    ROOT / "speech",
    ROOT / "substrate",
    ROOT / "theory_x",
)
FORBIDDEN_PATHS = ("MIND_MAP.yaml", "sentience_dag.json")


def _runtime_python_files():
    for root in RUNTIME_ROOTS:
        if root.is_file():
            yield root
        elif root.is_dir():
            yield from sorted(root.rglob("*.py"))


def test_mind_map_declares_descriptive_only_authority():
    doc = yaml.safe_load((ROOT / "mind_map" / "MIND_MAP.yaml").read_text())
    constraint = str(doc.get("meta", {}).get("constraint", ""))
    assert "Descriptive only." in constraint
    assert "gate, score, block, or veto" in constraint


def test_runtime_source_does_not_import_or_read_descriptive_maps():
    violations = []
    for path in _runtime_python_files():
        source = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError as exc:
            violations.append(f"{path.relative_to(ROOT)}: cannot inspect AST: {exc}")
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "mind_map" or alias.name.startswith("mind_map."):
                        violations.append(
                            f"{path.relative_to(ROOT)}:{node.lineno}: imports {alias.name}"
                        )
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module == "mind_map" or module.startswith("mind_map."):
                    violations.append(
                        f"{path.relative_to(ROOT)}:{node.lineno}: imports from {module}"
                    )
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                for forbidden in FORBIDDEN_PATHS:
                    if forbidden in node.value:
                        violations.append(
                            f"{path.relative_to(ROOT)}:{node.lineno}: references {forbidden}"
                        )

    assert not violations, (
        "Runtime code must not consume descriptive architecture maps as action "
        "controllers; keep map use in external development/visualization tools:\n"
        + "\n".join(violations)
    )
