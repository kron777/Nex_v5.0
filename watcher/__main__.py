"""CLI entry point — `python -m watcher ...`. All commands are passive/read-only.

  python -m watcher recon [--repo .] [--out DIR]    # cloud recon -> report.md + .json
  python -m watcher graph                           # runtime graph + feedback cycles (JSON)
  python -m watcher host-request                    # read-only host-side spec (for Claude Code)
  python -m watcher host-template [--out FILE]      # blank host-results file
  python -m watcher host-collect [--out FILE] [--repo-root DIR]  # execute fixed read-only host collection locally
  python -m watcher snapshot [--repo .] --label L [--out DIR] [--stage S]
                                                    # capture a before/after evidence snapshot
  python -m watcher combined [--repo .] [--results host.json] [--out DIR]
                                                    # cloud + host evidence, origins preserved
  python -m watcher regression --before A.json --after B.json
                                                    # regressions between two snapshots
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from . import __version__
from .architecture import build_runtime_graph, runtime_graph_evidence
from .collector import collect_cloud, collect_combined
from .host import host_requests_as_data, host_results_template, load_host_results
from .regression import detect, summarize
from .report import render_json, render_markdown
from .snapshot import load_snapshot, take_snapshot


def _recon(args) -> int:
    records = collect_cloud(args.repo)
    _emit(records, "NEX Watcher — Cloud/Static Reconnaissance", args.out, "watcher_report")
    return 0


def _graph(_args) -> int:
    g = build_runtime_graph()
    ev = runtime_graph_evidence(g)
    print(json.dumps({"graph": g.to_dict(), "summary": ev.data}, indent=2, default=str))
    return 0


def _host_request(_args) -> int:
    print(json.dumps(host_requests_as_data(), indent=2))
    return 0


def _host_collect(args) -> int:
    from .host_runner import collect_host_evidence, write_results

    if not args.skip_artifact_hashes:
        print(
            "NOTICE: SHA-256 fingerprinting reads selected DB/snapshot files in full; "
            "this may cause substantial disk I/O. Use --skip-artifact-hashes to omit it.",
            file=sys.stderr,
            flush=True,
        )
    try:
        results = collect_host_evidence(
            timeout=args.timeout,
            include_artifact_hashes=not args.skip_artifact_hashes,
            repo_root=Path(args.repo_root).expanduser().resolve() if args.repo_root else None,
        )
        path = write_results(results, Path(args.out), force=args.force)
    except (OSError, ValueError) as exc:
        print(f"host collection failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    failures = sum(
        row.get("data", {}).get("failed_command_count", 0)
        for key, row in results.items() if not key.startswith("_")
    )
    skipped = sum(
        row.get("data", {}).get("status") == "SKIPPED_BY_OPERATOR"
        for key, row in results.items() if not key.startswith("_")
    )
    print(f"wrote {path}; requests={len(results) - 1}; command_failures={failures}; skipped_requests={skipped}")
    return 0 if failures == 0 else 1


def _host_template(args) -> int:
    tpl = json.dumps(host_results_template(), indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(tpl)
        print(f"wrote blank host-results template to {args.out} "
              f"(fill `data` with provenance-bearing host observations, then: watcher combined --results {args.out})")
    else:
        print(tpl)
    return 0


def _snapshot(args) -> int:
    records = collect_cloud(args.repo)
    out = args.out or "watcher/reports"
    path = take_snapshot(records, args.label, out, stage=args.stage)
    print(f"wrote snapshot {path} ({len(records)} observations, all origin=cloud)")
    return 0


def _combined(args) -> int:
    host_results = load_host_results(args.results) if args.results else {}
    records = collect_combined(args.repo, host_results=host_results)
    title = "NEX Watcher — Combined Cloud + Host Evidence"
    _emit(records, title, args.out, "watcher_combined")
    return 0


def _regression(args) -> int:
    before, after = load_snapshot(args.before), load_snapshot(args.after)
    findings = detect(before, after)
    print(json.dumps({"summary": summarize(findings), "findings": findings},
                     indent=2, default=str))
    return 1 if any(f["severity"] == "critical" for f in findings) else 0


def _emit(records, title, out_dir, stem) -> None:
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, f"{stem}.md"), "w", encoding="utf-8") as fh:
            fh.write(render_markdown(records, title))
        with open(os.path.join(out_dir, f"{stem}.json"), "w", encoding="utf-8") as fh:
            fh.write(render_json(records))
        origins = sorted({r.origin for r in records})
        print(f"wrote {out_dir}/{stem}.md and .json ({len(records)} observations, origins={origins})")
    else:
        print(render_markdown(records, title))


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="watcher", description="NEX Watcher (passive, read-only)")
    p.add_argument("--version", action="version", version=f"watcher {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("recon", help="run cloud/static reconnaissance")
    r.add_argument("--repo", default=".")
    r.add_argument("--out", default=None, help="output directory (default: print)")
    r.set_defaults(fn=_recon)

    sub.add_parser("graph", help="print the runtime graph + feedback cycles").set_defaults(fn=_graph)
    sub.add_parser("host-request", help="print the host-side read-only spec").set_defaults(fn=_host_request)

    hc = sub.add_parser("host-collect", help="run the fixed read-only host collection locally")
    hc.add_argument("--out", default="host_results.json", help="results JSON path")
    hc.add_argument("--timeout", type=int, default=600, help="timeout per command in seconds")
    hc.add_argument("--repo-root", default=None, help="verified NEX checkout used as the working directory for relative read-only inspections")
    hc.add_argument("--skip-artifact-hashes", action="store_true", help="skip full-file DB/snapshot fingerprinting")
    hc.add_argument("--force", action="store_true", help="replace an existing output file")
    hc.set_defaults(fn=_host_collect)

    ht = sub.add_parser("host-template", help="emit a blank host-results file")
    ht.add_argument("--out", default=None)
    ht.set_defaults(fn=_host_template)

    s = sub.add_parser("snapshot", help="capture a before/after evidence snapshot")
    s.add_argument("--repo", default=".")
    s.add_argument("--label", required=True, help="snapshot label (e.g. 'pre-integration')")
    s.add_argument("--out", default=None, help="output directory (default: watcher/reports)")
    s.add_argument("--stage", default=None, help="optional integration-stage tag")
    s.set_defaults(fn=_snapshot)

    c = sub.add_parser("combined", help="cloud + host evidence (origins preserved)")
    c.add_argument("--repo", default=".")
    c.add_argument("--results", default=None, help="host-results JSON (from Claude Code)")
    c.add_argument("--out", default=None, help="output directory (default: print)")
    c.set_defaults(fn=_combined)

    g = sub.add_parser("regression", help="detect regressions between two snapshots")
    g.add_argument("--before", required=True)
    g.add_argument("--after", required=True)
    g.set_defaults(fn=_regression)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
