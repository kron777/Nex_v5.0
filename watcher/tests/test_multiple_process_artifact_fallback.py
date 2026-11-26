"""Regression coverage for ambiguous process-candidate artifact fallback.

The helper functions are extracted from the exact host collection request, then
exercised only against temporary fixture directories. No host commands are run.
"""
import importlib.util
from pathlib import Path


def _existing_host_helpers():
    source = Path(__file__).with_name("test_phase0_host_evidence.py")
    spec = importlib.util.spec_from_file_location("_phase0_host_test_helpers", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module._artifact_helper_namespace()


def test_multiple_process_candidates_fall_back_to_named_historical_roots(tmp_path, capsys):
    helpers = _existing_host_helpers()
    choose = helpers["choose_artifact_roots"]
    scan = helpers["scan_artifact_roots"]

    checkouts = []
    for name in ("runtime_checkout", "audit_checkout", "preserved_runtime_checkout"):
        checkout = tmp_path / name
        (checkout / "substrate").mkdir(parents=True)
        (checkout / "run.py").write_text("# fixture marker", encoding="utf-8")
        (checkout / "substrate" / "paths.py").write_text(
            "# fixture marker", encoding="utf-8"
        )
        (checkout / "data").mkdir()
        (checkout / "snapshots").mkdir()
        checkouts.append(checkout)

    custom_a = tmp_path / "custom_a"
    custom_b = tmp_path / "custom_b"
    custom_a.mkdir()
    custom_b.mkdir()
    candidates = [
        ("1111", checkouts[0], str(custom_a)),
        ("2222", checkouts[1], str(custom_b)),
    ]

    selected = choose(candidates, checkouts)

    assert [item[0] for item in selected] == [
        "known_checkout_1_data",
        "known_checkout_2_data",
        "known_checkout_3_data",
    ]
    assert all(
        item[2] == "known_checkout_default_candidate_active_root_unknown"
        for item in selected
    )
    assert all(item[3] is None for item in selected)
    assert all(item[1] not in (custom_a, custom_b) for item in selected)

    scan(selected)
    output = capsys.readouterr().out
    assert output.count(
        "runtime_process_identity=UNKNOWN; no unique process candidate"
    ) == 3
    assert "pid=1111" not in output
    assert "pid=2222" not in output
