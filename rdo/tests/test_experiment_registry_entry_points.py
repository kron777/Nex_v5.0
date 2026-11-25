"""Ensure Stage 2 and Stage 3 do not bypass the protected-experiment registry."""
from types import SimpleNamespace

import pytest

from rdo import report


@pytest.mark.parametrize(
    "runner_name",
    ["run_stage2_belief_decay", "run_stage3_graph_intelligence"],
)
def test_stage_entry_points_propagate_unknown_registry(monkeypatch, tmp_path, runner_name):
    captured = {}

    def fake_run_one(_cycle_id, _idea, _repo_dir, _memory, _store, active):
        captured["active"] = active
        return SimpleNamespace(
            objective="isolated fixture objective",
            obligations=[{"depth": 0}],
            relationships=[],
            counts={},
            reused=[],
            missing=[],
            anti_requirements=[],
            frontier=[],
            work_packages=[],
            verification={},
        )

    monkeypatch.setattr(report, "_active_experiments", lambda _repo: None)
    monkeypatch.setattr(report, "_run_one", fake_run_one)
    if runner_name == "run_stage3_graph_intelligence":
        monkeypatch.setattr(
            report,
            "graph_analyse",
            lambda *_args: {
                "typed_edges": [],
                "scc": {"nontrivial_components": [], "has_cyclic_components": False},
                "duplicate_candidates": [],
                "completeness": {
                    "discovered": 1,
                    "unresolved_count": 0,
                    "complete_against_objective": True,
                },
                "implementation_sequence": {
                    "levels": [],
                    "parallel_width": 0,
                    "cyclic_components": [],
                },
            },
        )

    runner = getattr(report, runner_name)
    runner(repo_dir=str(tmp_path), workdir=str(tmp_path / "cycles"))

    assert captured["active"] is None
