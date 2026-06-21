#!/usr/bin/env python3
"""
nex_next_dev.py — compute the next development from the sentience dependency DAG.

The mind-map's build order is the TOPOLOGICAL SORT of a dependency graph. This
reads that graph (sentience_dag.json) and mechanically answers "what's next?":

  BUILDABLE NOW  — every prereq is satisfied (built/live), node itself is a gap.
  BLOCKED        — a prereq is still unproven; advancing past it needs proof.
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

_SATISFIED = ("built", "live_unproven")


def load() -> dict:
    with open(DAG_PATH) as f:
        return json.load(f)


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
    """Apply the buildable-now rule to every node."""
    out = {"buildable_now": [], "blocked": [], "built": [],
           "live_unproven": [], "gorge": []}
    for n, d in nodes.items():
        st = d.get("status")
        prereqs = d.get("prereqs", [])
        if st == "built":
            out["built"].append(n)
        elif st == "live_unproven":
            out["live_unproven"].append(n)
        elif st == "gorge":
            out["gorge"].append(n)
        elif st == "gap":
            # buildable iff all prereqs satisfied
            prereq_status = [nodes[p]["status"] for p in prereqs if p in nodes]
            if all(s in _SATISFIED for s in prereq_status):
                # but flag if it leans on an UNPROVEN prereq
                unproven = [p for p in prereqs
                            if p in nodes and nodes[p]["status"] == "live_unproven"]
                out["buildable_now"].append((n, unproven))
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
    for n, unproven in c["buildable_now"]:
        note = nodes[n].get("note", "")[:70]
        flag = f"  [LEANS ON UNPROVEN: {', '.join(unproven)}]" if unproven else ""
        print(f"  • {n}{flag}")
        print(f"      {note}")

    print("\n>>> BLOCKED (waiting on an unbuilt/unproven prereq):")
    if not c["blocked"]:
        print("    (none)")
    for n, missing in c["blocked"]:
        print(f"  • {n}  <- needs: {', '.join(missing)}")
        print(f"      {nodes[n].get('note','')[:70]}")

    print("\n>>> LIVE BUT UNPROVEN (the gates — prove these to advance):")
    for n in c["live_unproven"]:
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
    print("THE ONE GATE RIGHT NOW:")
    # the binding constraint = the live_unproven node closest to the frontier
    if c["live_unproven"]:
        gate = c["live_unproven"][0]
        print(f"  Prove '{gate}' (its teeth) before advancing the layer above it.")
        print(f"  Until then, building higher layers rests on an unproven floor.")
    print("-" * 66)


if __name__ == "__main__":
    dag = load()
    if "--order" in sys.argv:
        print("Topological build order:")
        for i, n in enumerate(topo_sort(dag["nodes"]), 1):
            print(f"  {i:2d}. {n}  [{dag['nodes'][n]['status']}]")
    elif "--buildable" in sys.argv:
        c = classify(dag["nodes"])
        for n, unproven in c["buildable_now"]:
            flag = f"  (leans on unproven: {','.join(unproven)})" if unproven else ""
            print(f"{n}{flag}")
    else:
        report(dag)
