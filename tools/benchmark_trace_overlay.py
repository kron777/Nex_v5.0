#!/usr/bin/env python3
"""Diagnostic latency probe for the Phase 0 trace overlay.

Run from the repository root:
    python tools/benchmark_trace_overlay.py --iterations 1000 --workers 1,4

This is a measurement aid, not a CI performance gate or a proof of host-wide
latency neutrality. It compares the same begin/record/end call sequence with
tracing disabled and enabled, using a temporary JSONL artifact outside the
repository and configured NEX data directory.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import platform
import statistics
import sys
import tempfile
import time
from pathlib import Path

from substrate import trace_overlay


TRACE_RECORDS_PER_CYCLE = 3


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int((len(ordered) - 1) * fraction)))
    return ordered[index]


def _cycle() -> float:
    started = time.perf_counter_ns()
    handle = trace_overlay.begin_trace(
        "latency_benchmark",
        source_ref="tools/benchmark_trace_overlay.py",
    )
    trace_overlay.record(
        "benchmark_observation",
        producer="latency_benchmark",
        source_ref="tools/benchmark_trace_overlay.py",
        outcome="measured",
        payload={"kind": "small_metadata_record"},
    )
    trace_overlay.end_trace(
        handle,
        source_ref="tools/benchmark_trace_overlay.py",
        outcome="completed",
    )
    return (time.perf_counter_ns() - started) / 1_000_000


def _measure(iterations: int, workers: int, enabled: bool, artifact: Path) -> dict:
    os.environ["NEX5_TRACE_OVERLAY"] = "1" if enabled else "0"
    os.environ["NEX5_TRACE_PATH"] = str(artifact)

    def worker(count: int) -> list[float]:
        return [_cycle() for _ in range(count)]

    # Warm filesystem/import paths before collecting samples.
    warmup = max(10, min(50, iterations // 10))
    if workers == 1:
        for _ in range(warmup):
            _cycle()
        samples = worker(iterations)
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            list(pool.map(worker, [warmup] * workers))
            batches = list(pool.map(worker, [iterations] * workers))
        samples = [sample for batch in batches for sample in batch]

    record_count = 0
    byte_count = artifact.stat().st_size if artifact.exists() else 0
    if artifact.exists():
        with artifact.open("r", encoding="utf-8") as stream:
            record_count = sum(1 for _ in stream)

    return {
        "samples": len(samples),
        "median_ms_per_cycle": statistics.median(samples),
        "p95_ms_per_cycle": _percentile(samples, 0.95),
        "p99_ms_per_cycle": _percentile(samples, 0.99),
        "trace_records": record_count,
        "artifact_bytes": byte_count,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=1000,
                        help="measured cycles per worker (default: 1000)")
    parser.add_argument("--workers", default="1,4",
                        help="comma-separated worker counts (default: 1,4)")
    args = parser.parse_args()
    if args.iterations < 20:
        parser.error("--iterations must be at least 20")

    try:
        worker_counts = [int(value) for value in args.workers.split(",")]
    except ValueError:
        parser.error("--workers must be comma-separated positive integers")
    if not worker_counts or any(value < 1 for value in worker_counts):
        parser.error("--workers must contain positive integers")

    previous = {
        key: os.environ.get(key)
        for key in ("NEX5_TRACE_OVERLAY", "NEX5_TRACE_PATH", "NEX5_DATA_DIR")
    }
    results = []
    try:
        with tempfile.TemporaryDirectory(prefix="nex5-trace-bench-") as temp:
            root = Path(temp)
            os.environ["NEX5_DATA_DIR"] = str(root / "nex-data")
            (root / "nex-data").mkdir()
            for workers in worker_counts:
                off_path = root / f"off-{workers}.jsonl"
                on_path = root / f"on-{workers}.jsonl"
                off = _measure(args.iterations, workers, False, off_path)
                on = _measure(args.iterations, workers, True, on_path)
                results.append({
                    "workers": workers,
                    "iterations_per_worker": args.iterations,
                    "trace_records_per_cycle": TRACE_RECORDS_PER_CYCLE,
                    "off": off,
                    "on": on,
                    "median_added_ms_per_cycle": (
                        on["median_ms_per_cycle"] - off["median_ms_per_cycle"]
                    ),
                    "p95_added_ms_per_cycle": (
                        on["p95_ms_per_cycle"] - off["p95_ms_per_cycle"]
                    ),
                })
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    print(json.dumps({
        "classification": "diagnostic_only_not_a_performance_gate",
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "results": results,
        "limitations": [
            "temporary local filesystem only; not a deployed-host measurement",
            "synthetic begin/record/end cycle, not an end-to-end NEX workload",
            "concurrent writers contend on the overlay's process-local lock",
            "no acceptance threshold is applied",
        ],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
