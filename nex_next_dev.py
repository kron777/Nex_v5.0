#!/usr/bin/env python3
"""
nex_next_dev.py — compute the next development from the sentience dependency DAG.

The mind-map's build order is the TOPOLOGICAL SORT of a dependency graph. This
reads that graph (sentience_dag.json) and mechanically answers "what's next?":

  BUILDABLE NOW  — every prereq is in the DAG's satisfied set; caveats are shown.
  BLOCKED        — at least one prereq is outside that set; node itself is a gap.
  GAP            — a hole the graph predicts (incl. sibling-clusters).
  GORGE          — node with no satisfiable dependency path (the hard problem).

This turns "what should I build next" from a judgment call into a computation.
NOT topology (continuous-shape math) — that would be overreach. It IS a
topological SORT of a DAG, which is the real, honest math here.

USAGE:
    python3 nex_next_dev.py                 # full report
    python3 nex_next_dev.py --buildable     # just the buildable-now list
    python3 nex_next_dev.py --order         # the topological build order
"""
from __future__ import annotations
import json
import sys
import os

DAG_PATH = os.path.join(os.path.dirname(__file__), "sentience_dag.json")

_SATISFIED = ("built", "live_unproven", "terminal")


def load() -> dict:
    with open(DAG_PATH) as f:
        return json.load(f)


def validate_prerequisites(nodes: dict) -> None:
    """Reject prerequisite references that do not resolve to a DAG node.

    Unknown references must not be silently treated as satisfied: doing so can
    make an incomplete graph appear buildable or produce a false topological
    order. Report every unresolved edge in deterministic order.
    """
    unresolved = sorted(
        (node, prereq)
        for node, data in nodes.items()
        for prereq in data.get("prereqs", [])
        if prereq not in nodes
    )
    if unresolved:
        details = ", ".join(f"{node} -> {prereq}" for node, prereq in unresolved)
        raise ValueError(f"unknown DAG prerequisite reference(s): {details}")


def topo_sort(nodes: dict) -> list[str]:
    """Kahn's algorithm — the build order. Raises if a cycle exists (shouldn't:
    it's a DAG by construction)."""
    indeg = {n: 0 for n in nodes}
    for n, d in nodes.items():
        for p in d.get("prereqs", []):
            if p in nodes:
                indeg[n] += 1
    queue = sorted([n for n, k in indeg.items() if k == 0])
    order = []
    while queue:
        n = queue.pop(0)
        order.append(n)
        for m, d in nodes.items():
            if n in d.get("prereqs", []):
                indeg[m] -= 1
                if indeg[m] == 0:
                    queue.append(m)
        queue.sort()
    if len(order) != len(nodes):
        raise ValueError("cycle detected — not a DAG")
    return order


def classify(nodes: dict) -> dict:
    """Apply the buildable-now rule after validating every prerequisite edge."""
    validate_prerequisites(nodes)
    out = {"buildable_now": [], "blocked": [], "built": [],
           "live_unproven": [], "terminal": [], "gorge": []}
    for n, d in nodes.items():
        st = d.get("status")
        prereqs = d.get("prereqs", [])
        if st == "built":
            out["built"].append(n)
        elif st == "live_unproven":
            out["live_unproven"].append(n)
        elif st == "terminal":
            out["terminal"].append(n)
        elif st == "gorge":
            out["gorge"].append(n)
        elif st == "gap":
            # buildable iff all prereqs satisfied
            prereq_status = [nodes[p]["status"] for p in prereqs if p in nodes]
            if all(s in _SATISFIED for s in prereq_status):
                # flag if it leans on an UNPROVEN prereq, or rests on one
                # settled TERMINAL-null (resolved, not open, but still worth
                # surfacing so it doesn't read as plain "built")
                unproven = [p for p in prereqs
                            if p in nodes and nodes[p]["status"] == "live_unproven"]
                terminal_null = [p for p in prereqs
                                  if p in nodes and nodes[p]["status"] == "terminal"]
                out["buildable_now"].append((n, unproven, terminal_null))
            else:
                missing = [p for p in prereqs
                           if p in nodes and nodes[p]["status"] not in _SATISFIED]
                out["blocked"].append((n, missing))
    return out


def report(dag: dict) -> None:
    nodes = dag["nodes"]
    c = classify(nodes)

    print("=" * 66)
    print("NEX SENTIENCE DAG — next-development report")
    print("=" * 66)

    print("\n>>> BUILDABLE NOW (prereqs satisfied, node is a gap):")
    if not c["buildable_now"]:
        print("    (none)")
    for n, unproven, terminal_null in c["buildable_now"]:
        note = nodes[n].get("note", "")[:70]
        flags = []
        if unproven:
            flags.append(f"LEANS ON UNPROVEN: {', '.join(unproven)}")
        if terminal_null:
            flags.append(f"RESTS ON TERMINAL NULL: {', '.join(terminal_null)}")
        flag = f"  [{'; '.join(flags)}]" if flags else ""
        print(f"  • {n}{flag}")
        print(f"      {note}")

    print("\n>>> BLOCKED (at least one prerequisite is outside the DAG satisfied set):")
    if not c["blocked"]:
        print("    (none)")
    for n, missing in c["blocked"]:
        print(f"  • {n}  <- needs: {', '.join(missing)}")
        print(f"      {nodes[n].get('note','')[:70]}")

    print("\n>>> LIVE BUT UNPROVEN (dependency-satisfied caveats; not validated):")
    for n in c["live_unproven"]:
        print(f"  • {n} — {nodes[n].get('note','')[:70]}")

    print("\n>>> TERMINAL (investigated to a dead end; resting state, not a park):")
    for n in c["terminal"]:
        print(f"  • {n} — {nodes[n].get('note','')[:70]}")

    print("\n>>> GORGE (no satisfiable path — the hard problem):")
    for n in c["gorge"]:
        print(f"  • {n} — {nodes[n].get('note','')[:64]}")

    # predicted clusters
    pc = dag.get("_predicted_clusters", {})
    if pc:
        print("\n>>> PREDICTED CLUSTERS (siblings the graph implies):")
        for name, info in pc.items():
            print(f"  {name}: built={info.get('members_built')}, "
                  f"gap={info.get('members_gap')}")

    print("\n" + "-" * 66)
    print("UNPROVEN DEPENDENCY CAVEATS (not hard blockers under the current DAG rule):")
    if c["live_unproven"]:
        for gate in c["live_unproven"]:
            print(f"  • {gate} — {nodes[gate].get('note', '')[:70]}")
        print("  These prerequisites remain eligible for dependency progression;")
        print("  the caveat is surfaced, not treated as a blocking status.")
    else:
        print("  (none)")
    print("-" * 66)


def main(argv: list[str] | None = None) -> None:
    """Run the CLI; argv is injectable so command modes can be regression-tested."""
    args = sys.argv[1:] if argv is None else argv
    dag = load()
    if "--order" in args:
        print("Topological build order:")
        for i, n in enumerate(topo_sort(dag["nodes"]), 1):
            print(f"  {i:2d}. {n}  [{dag['nodes'][n]['status']}]")
    elif "--buildable" in args:
        c = classify(dag["nodes"])
        for n, unproven, terminal_null in c["buildable_now"]:
            flags = []
            if unproven:
                flags.append(f"leans on unproven: {', '.join(unproven)}")
            if terminal_null:
                flags.append(f"rests on terminal null: {', '.join(terminal_null)}")
            flag = f"  [{'; '.join(flags)}]" if flags else ""
            print(f"{n}{flag}")
    else:
        report(dag)


if __name__ == "__main__":
    main()
