"""RDO CLI — `python -m rdo ...`. Advisory/read-only; proposes work, changes nothing.

  python -m rdo run-demo [--repo .] [--out rdo/.cycles]
        run the full cycle on the real genius-tagger objective; print the six
        demonstration outputs as JSON.

  python -m rdo influence [--repo .] [--signal genius] [--subtree theory_x]
        audit how many subsystems consume a signal (capability != authority).

  python -m rdo patterns [--dir rdo/.cycles]
        print the accumulated Development Pattern Memory.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from . import __version__
from .knowledge import genius_authority_audit
from .memory import PatternMemory
from .report import demo_genius_tagger, run_catalogue, self_assess


def _run_demo(args) -> int:
    print(json.dumps(demo_genius_tagger(args.repo, args.out), indent=2, default=str))
    return 0


def _run_all(args) -> int:
    print(json.dumps(run_catalogue(args.repo, args.out), indent=2, default=str))
    return 0


def _influence(args) -> int:
    print(json.dumps(genius_authority_audit(args.repo, args.signal), indent=2, default=str))
    return 0


def _selfcheck(args) -> int:
    print(json.dumps(self_assess(), indent=2, default=str))
    return 0


def _patterns(args) -> int:
    mem = PatternMemory(os.path.join(args.dir, "patterns.jsonl"))
    print(json.dumps([p.to_dict() for p in mem.patterns()], indent=2, default=str))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="rdo",
                                description="NEX Recursive Development Orchestrator (advisory)")
    p.add_argument("--version", action="version", version=f"rdo {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("run-demo", help="run the full cycle on the genius-tagger objective")
    d.add_argument("--repo", default=".")
    d.add_argument("--out", default="rdo/.cycles")
    d.set_defaults(fn=_run_demo)

    ra = sub.add_parser("run-all", help="run two cycles (feature-deploy + defect) + cross-cycle metrics")
    ra.add_argument("--repo", default=".")
    ra.add_argument("--out", default="rdo/.cycles")
    ra.set_defaults(fn=_run_all)

    i = sub.add_parser("influence", help="audit a signal's influence authority (capability != authority)")
    i.add_argument("--repo", default=".")
    i.add_argument("--signal", default="genius")
    i.set_defaults(fn=_influence)

    sub.add_parser("selfcheck",
                   help="assess the RDO against its own Optimal Functional Tension").set_defaults(fn=_selfcheck)

    pt = sub.add_parser("patterns", help="print accumulated development patterns")
    pt.add_argument("--dir", default="rdo/.cycles")
    pt.set_defaults(fn=_patterns)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
