"""Tests for the non-gating Phase 0 trace-overlay diagnostic probe."""
import json

from tools import benchmark_trace_overlay


def test_benchmark_probe_reports_off_on_samples_without_performance_gate(
    monkeypatch, tmp_path, capsys
):
    monkeypatch.setattr(
        "sys.argv",
        [
            "benchmark_trace_overlay.py",
            "--iterations",
            "20",
            "--workers",
            "1,2",
        ],
    )

    assert benchmark_trace_overlay.main() == 0
    report = json.loads(capsys.readouterr().out)

    assert report["classification"] == "diagnostic_only_not_a_performance_gate"
    assert len(report["results"]) == 2
    for result in report["results"]:
        workers = result["workers"]
        expected_cycles = 20 * workers
        assert result["off"]["samples"] == expected_cycles
        assert result["on"]["samples"] == expected_cycles
        assert result["off"]["trace_records"] == 0
        # Each worker warms up for 10 cycles; each cycle appends three records.
        assert result["on"]["trace_records"] == (expected_cycles + 10 * workers) * 3
        assert "median_added_ms_per_cycle" in result
        assert "p95_added_ms_per_cycle" in result
