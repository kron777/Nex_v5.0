"""Isolated tests for the read-only systemd service audit."""
from pathlib import Path
from types import SimpleNamespace

from watcher import service_audit


def test_parse_properties_keeps_key_value_lines_only():
    parsed = service_audit.parse_properties(
        "LoadState=loaded\nActiveState=failed\nExecMainStatus=203\n"
    )
    assert parsed == {
        "LoadState": "loaded",
        "ActiveState": "failed",
        "ExecMainStatus": "203",
    }


def test_build_record_finds_missing_script_without_emitting_raw_arguments(tmp_path):
    fragment = tmp_path / "nex-vitals.service"
    fragment.write_text("[Service]\n", encoding="utf-8")
    working = tmp_path / "checkout"
    working.mkdir()
    missing_script = working / "tools" / "nex_vitals.py"
    executable = Path("/usr/bin/python3")

    record = service_audit.build_service_record(
        "nex-vitals.service",
        {
            "LoadState": "loaded",
            "ActiveState": "failed",
            "SubState": "failed",
            "Result": "exit-code",
            "ExecMainStatus": "203",
            "FragmentPath": str(fragment),
            "WorkingDirectory": str(working),
            "ExecStart": (
                "{ path=/usr/bin/python3 ; argv[]=/usr/bin/python3 "
                + str(missing_script)
                + " --api-token DO_NOT_EMIT ; ignore_errors=no ; }"
            ),
            "Restart": "no",
        },
    )

    assert record["properties"]["ActiveState"] == "failed"
    assert record["fragment"]["exists"] is True
    assert record["working_directory"]["exists"] is True
    assert record["exec_executable"]["path"] == str(executable)
    assert record["exec_executable"]["exists"] is True
    assert record["exec_path_arguments"] == [
        {"path": str(missing_script), "exists": False}
    ]
    assert str(missing_script) in record["missing_paths"]
    assert "DO_NOT_EMIT" not in repr(record)
    assert "api-token" not in repr(record)
    assert record["exec_start_arguments_redacted"] is True


def test_build_record_handles_systemd_escaped_path():
    executable, arguments = service_audit._exec_paths(
        r"{ path=/usr/bin/python3 ; argv[]=/usr/bin/python3 /tmp/a\x2db.py ; ignore_errors=no ; }"
    )
    assert executable == "/usr/bin/python3"
    assert arguments == ["/tmp/a-b.py"]


def test_collect_service_audit_queries_only_fixed_units_and_selected_properties(monkeypatch):
    calls = []
    monkeypatch.setattr(service_audit.shutil, "which", lambda name: "/usr/bin/systemctl")

    def fake_run(argv, **kwargs):
        calls.append(argv)
        if argv[1:] == ["--user", "show-environment"]:
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        unit = argv[3]
        return SimpleNamespace(
            returncode=0,
            stdout=(
                "LoadState=loaded\n"
                "ActiveState=inactive\n"
                "SubState=dead\n"
                "FragmentPath=/nonexistent/" + unit + "\n"
                "WorkingDirectory=-\n"
                "ExecStart=\n"
            ),
            stderr="",
        )

    monkeypatch.setattr(service_audit.subprocess, "run", fake_run)
    result = service_audit.collect_service_audit()

    assert result["status"] == "COLLECTED"
    assert [row["unit"] for row in result["services"]] == list(service_audit.SERVICES)
    assert all(row["status"] == "COLLECTED" for row in result["services"])
    assert all(row["missing_paths"] for row in result["services"])
    assert len(calls) == 1 + len(service_audit.SERVICES)
    assert all("start" not in call and "restart" not in call for call in calls)
    assert all("--property=ExecStart" in call for call in calls[1:])
    assert result["read_only"] is True


def test_user_manager_failure_is_unknown_not_empty(monkeypatch):
    monkeypatch.setattr(service_audit.shutil, "which", lambda name: "/usr/bin/systemctl")
    monkeypatch.setattr(
        service_audit.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=1, stdout="", stderr="unavailable"),
    )
    result = service_audit.collect_service_audit()

    assert result["status"] == "USER_MANAGER_UNAVAILABLE"
    assert result["services"] == []
    assert "unknown" in result["note"].lower()


def test_missing_systemctl_is_unknown(monkeypatch):
    monkeypatch.setattr(service_audit.shutil, "which", lambda name: None)
    result = service_audit.collect_service_audit()

    assert result["status"] == "SYSTEMCTL_UNAVAILABLE"
    assert result["services"] == []
