"""CLI entry point — `python -m watcher ...`. All commands are passive/read-only.

  python -m watcher recon [--repo .] [--out DIR]   # run cloud recon -> report.md + .json
  python -m watcher graph                          # print the runtime graph + feedback cycles
  python -m watcher host-request                   # print the read-only host-side spec (for Claude Code)
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from . import __version__
from .architecture import build_runtime_graph, runtime_graph_evidence
from .collector import collect_cloud
from .host import host_requests_as_data
from .report import render_json, render_markdown


def _recon(args) -> int:
    records = collect_cloud(args.repo)
    md = render_markdown(records, "NEX Watcher — Cloud/Static Reconnaissance")
    js = render_json(records)
    if args.out:
        os.makedirs(args.out, exist_ok=True)
        with open(os.path.join(args.out, "watcher_report.md"), "w") as fh:
            fh.write(md)
        with open(os.path.join(args.out, "watcher_report.json"), "w") as fh:
            fh.write(js)
        print(f"wrote {args.out}/watcher_report.md and .json  "
              f"({len(records)} observations, all origin=cloud)")
    else:
        print(md)
    return 0


def _graph(_args) -> int:
    g = build_runtime_graph()
    ev = runtime_graph_evidence(g)
    print(json.dumps({"graph": g.to_dict(), "summary": ev.data}, indent=2, default=str))
    return 0


def _host_request(_args) -> int:
    print(json.dumps(host_requests_as_data(), indent=2))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="watcher", description="NEX Watcher (passive, read-only)")
    p.add_argument("--version", action="version", version=f"watcher {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("recon", help="run cloud/static reconnaissance")
    r.add_argument("--repo", default=".")
    r.add_argument("--out", default=None, help="output directory (default: print to stdout)")
    r.set_defaults(fn=_recon)
    sub.add_parser("graph", help="print the runtime graph + feedback cycles").set_defaults(fn=_graph)
    sub.add_parser("host-request", help="print the host-side read-only spec").set_defaults(fn=_host_request)
    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
