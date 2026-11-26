"""CI policy tests: the descriptive mind map cannot become a runtime action authority."""
from mind_map.mind_map import ROOT, check_descriptive_only, load


_VALID_CONSTRAINT = (
    "Descriptive only. No node in this map may gate, score, block, or veto an action."
)


def test_current_mind_map_is_descriptive_and_not_a_runtime_dependency():
    assert check_descriptive_only(load(), ROOT) == []


def test_action_authority_fields_are_rejected():
    doc = {
        "meta": {"constraint": _VALID_CONSTRAINT},
        "nodes": [{"id": "x", "blocked": True, "action_gate": True}],
    }
    errors = check_descriptive_only(doc, ROOT / "tests-do-not-scan")
    assert any("action_gate" in error for error in errors)
    assert not any("blocked" in error for error in errors)


def test_missing_descriptive_only_constraint_is_rejected():
    doc = {"meta": {}, "nodes": []}
    errors = check_descriptive_only(doc, ROOT / "tests-do-not-scan")
    assert any("meta.constraint" in error for error in errors)


def test_runtime_import_of_mind_map_is_rejected(tmp_path):
    runtime = tmp_path / "theory_x"
    runtime.mkdir()
    (runtime / "decision.py").write_text("from mind_map import load\n", encoding="utf-8")
    errors = check_descriptive_only(
        {"meta": {"constraint": _VALID_CONSTRAINT}, "nodes": []}, tmp_path
    )
    assert any("runtime code imports mind_map" in error for error in errors)


def test_runtime_loading_of_mind_map_yaml_is_rejected(tmp_path):
    runtime = tmp_path / "gui"
    runtime.mkdir()
    (runtime / "decision.py").write_text(
        'from pathlib import Path\nPath("mind_map/MIND_MAP.yaml").read_text()\n',
        encoding="utf-8",
    )
    errors = check_descriptive_only(
        {"meta": {"constraint": _VALID_CONSTRAINT}, "nodes": []}, tmp_path
    )
    assert any("runtime code references MIND_MAP.yaml" in error for error in errors)


def test_external_rdo_tool_may_read_map_as_evidence(tmp_path):
    rdo = tmp_path / "rdo"
    rdo.mkdir()
    (rdo / "planner.py").write_text("from mind_map import load\n", encoding="utf-8")
    assert check_descriptive_only(
        {"meta": {"constraint": _VALID_CONSTRAINT}, "nodes": []}, tmp_path
    ) == []
