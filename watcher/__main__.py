"""CLI entry point — `python -m watcher ...`. All commands are passive/read-only.

  python -m watcher recon [--repo .] [--out DIR]    # cloud recon -> report.md + .json
  python -m watcher graph                           # runtime graph + feedback cycles (JSON)
  python -m watcher host-request                    # read-only host-side spec (for Claude Code)
  python -m watcher host-template [--out FILE]      # blank host-results file for Claude Code to fill
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
import subprocess
import sys

from . import __version__
from .architecture import build_runtime_graph, runtime_graph_evidence
from .collector import collect_cloud, collect_combined
from .host import host_requests_as_data, host_results_template, load_host_results
from .regression import detect, summarize
from .report import render_json, render_markdown
from .ripple import collect_offline_ripple, test_outcomes
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


def _host_template(args) -> int:
    tpl = json.dumps(host_results_template(), indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(tpl)
        print(f"wrote blank host-results template to {args.out} "
              f"(Claude Code fills `data` on the machine, then: watcher combined --results {args.out})")
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


def _changed_from_base(repo: str, base: str) -> list:
    """Files the working tree + HEAD differ from `base` by (read-only git)."""
    changed = set()
    for args in (["diff", "--name-only", base], ["diff", "--name-only", base, "HEAD"]):
        try:
            out = subprocess.run(["git", "-C", repo, *args], capture_output=True,
                                 text=True, timeout=60)
            if out.returncode == 0:
                changed.update(l for l in out.stdout.splitlines() if l.strip())
        except Exception:
            pass
    return [os.path.join(repo, c) for c in sorted(changed)]


def _ripple(args) -> int:
    changed = list(args.changed.split(",")) if args.changed else []
    changed = [c if os.path.isabs(c) else os.path.join(args.repo, c) for c in changed if c]
    if args.base:
        changed += _changed_from_base(args.repo, args.base)
    changed = sorted(set(changed))
    if not changed:
        print("no changed files given — pass --changed a.py,b.py or --base <gitref>", file=sys.stderr)
        return 2
    before = _load_json(args.before) if args.before else None
    after = _load_json(args.after) if args.after else None
    records = collect_offline_ripple(args.repo, changed, before=before, after=after)
    _emit(records, "NEX Watcher — Offline Ripple (repo-proven, live-confirm pending)",
          args.out, "watcher_ripple")
    return 0


def _test_run(args) -> int:
    result = test_outcomes(args.repo, target=args.target, timeout=args.timeout)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=2, default=str)
        print(f"wrote test-outcome snapshot to {args.out} "
              f"(total={result.get('total')}, summary={result.get('summary')})")
    else:
        print(json.dumps({k: v for k, v in result.items() if k != "outcomes"},
                         indent=2, default=str))
    return 0


def _load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


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

    ht = sub.add_parser("host-template", help="emit a blank host-results file for Claude Code")
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

    rp = sub.add_parser("ripple", help="offline ripple of a change: source-dependents + test-delta")
    rp.add_argument("--repo", default=".")
    rp.add_argument("--changed", default=None, help="comma-separated changed files")
    rp.add_argument("--base", default=None, help="git ref; changed files = diff(base..working/HEAD)")
    rp.add_argument("--before", default=None, help="test-outcome JSON from before the change (test-run)")
    rp.add_argument("--after", default=None, help="test-outcome JSON from after the change (test-run)")
    rp.add_argument("--out", default=None, help="output directory (default: print)")
    rp.set_defaults(fn=_ripple)

    tr = sub.add_parser("test-run", help="run the suite, capture per-test outcomes (before/after a wire)")
    tr.add_argument("--repo", default=".")
    tr.add_argument("--target", default=None, help="pytest target (default: whole repo)")
    tr.add_argument("--out", default=None, help="write outcome JSON here (default: print summary)")
    tr.add_argument("--timeout", type=int, default=1800)
    tr.set_defaults(fn=_test_run)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
