"""NEX Recursive Development Orchestrator (RDO).

An **external, advisory** engineering system that turns Watcher evidence into
bounded development decisions. It is NOT a NEX cognitive faculty and NOT a
replacement for the Watcher.

Separation of concerns it must preserve (RDO spec v1.4 §26, Part VII):
  * NEX      — the cognitive architecture (theory_x / substrate). RDO never imports it.
  * Watcher  — observation & evidence (read-only). RDO *consumes* it.
  * RDO      — development reasoning, planning, learning (this package). Advisory.
  * Claude   — engineering execution (bounded, authorised).
  * Human    — objectives and consequential decisions.

Governing principle: **Optimal Functional Tension** — discover the necessary
development, develop to functional sufficiency, preserve headroom, avoid
complexity that does not earn its place. The RDO obeys this principle itself:
it reuses Watcher infrastructure rather than rebuilding it, and it is lean.

Guarantees:
  * `ADVISORY_ONLY = True` — this package proposes work; it does not execute
    changes to NEX. Nothing here imports `theory_x` or `substrate`.
  * Every obligation keeps its provenance (seed vs expansion-rule vs reconciled);
    LLM/heuristic proposals never silently become authoritative state.
  * Reconciliation is performed against the REAL repository (read-only), so
    "already built / reuse" is evidence, not assumption.
"""
from __future__ import annotations

__version__ = "0.1.0"
ADVISORY_ONLY = True
