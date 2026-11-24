# NEX Integration Watcher

An **external, read-only** observation and test coordinator for NEX. It is an
instrument to **understand** NEX, not a mechanism that changes it. Observation,
interpretation and intervention are kept separate on purpose.

## Guarantees

- **Independent of NEX's cognitive runtime.** Nothing in `watcher/` imports
  `theory_x` or `substrate`. It reads files (YAML/JSON), Git state, and — on the
  host only — SQLite **read-only**. (Because it must not import `substrate`, its one
  guarded `sqlite3` choke point is scanned separately by NEX's architecture tests —
  see `--exclude-dir=watcher` in `tests/test_*.py::*test_no_direct_sqlite3_outside_substrate`.)
- **Passive mode, enforced.** `watcher/safety.py` is the single data-access choke
  point: SQLite is opened `mode=ro` with a write-denying authorizer, and
  `guard_sql` rejects mutating statements before they run. If read-only can't be
  guaranteed, the operation is refused — never downgraded. Proven by
  `tests/test_watcher_safety.py`.
- **Cloud vs host, never conflated.** `origin='cloud'` evidence is static/GitHub
  (what this package collects). `origin='host'` evidence is the live machine,
  collected only by Claude Code and ingested via `watcher.host`. Cloud-side code
  never pretends to have observed the live machine — unavailable facts are
  recorded as honest `unknown` placeholders.
- **Existing artifacts untouched.** The readers parse `mind_map/MIND_MAP.yaml` and
  `sentience_dag.json` read-only. The runtime graph is a **separate
  reconstruction**, not a modification of either.

## Three evidence dimensions, kept distinguishable

Source implementation, test verification and runtime observation are **three
different claims**, and the Watcher never collapses them:

| dimension | means | who can establish it |
|---|---|---|
| `source_implemented` | the code exists (read in source) | cloud |
| `test_verified` | a curated graph assertion cites a test intended to assert the scoped relationship; the ledger does not run it | cloud |
| `runtime_observed` | seen firing in a live trace | **host only** |

Every runtime-graph `Edge` carries all three as explicit booleans; its `level` is
the strongest it has, and a feedback cycle's status is its **weakest** edge. These
flags are curated review assertions, not dynamically derived proofs. Ledger
`TEST_WRITTEN`/`TEST_PASSED` entries cite `test_ref`, but mirror the curated
`test_verified` flag; they do not represent a test run or captured CI result. NEX is
in STANDBY, so nothing is `runtime_observed` yet — that stays an honest gap, not an
assumption.

## Founder constraints honored

1. **Learning ↔ belief-confidence loop** — surfaced as a **test_verified** feedback
   cycle (`reconciler → beliefs.confidence → producers → expectations → reconciler`):
   it has code and tests, but is **not** claimed `runtime_observed` while NEX is off.
   The Watcher characterizes it; it does not touch the live safeguards.
2. **Candidate mood loop** — any cycle through `affect_state` is labeled
   **hypothesis** and its edges carry an explicit `HYPOTHESIS` note; it is never
   promoted to fact without a live runtime trace.
3. **Third runtime graph** — a separate artifact; the DAG and mind map are inputs,
   never rewritten.

## Run it (all passive)

```bash
# cloud/static reconnaissance -> report.md + report.json
python -m watcher recon --out watcher/reports

# the runtime graph + feedback cycles, with the three dimensions per edge (JSON)
python -m watcher graph

# capture before/after snapshots of the evidence set (for diff / regression / trend)
python -m watcher snapshot --label pre-integration --stage s0 --out watcher/reports
python -m watcher snapshot --label post-integration --stage s1 --out watcher/reports

# regressions between two snapshots (exit 1 if any critical)
python -m watcher regression --before watcher/reports/snapshot_pre-integration_*.json \
                             --after  watcher/reports/snapshot_post-integration_*.json

# the read-only host-side spec, and a blank results file for Claude Code to fill
python -m watcher host-request
python -m watcher host-template --out host_results.json

# cloud + host evidence in one report, origins preserved (host.json optional)
python -m watcher combined --results host_results.json --out watcher/reports

# the passive-safety + behaviour tests
python -m pytest watcher/tests -q
```

## File inventory

| File | Purpose |
|---|---|
| `evidence.py` | the one `Evidence` record (origin, timestamp, evidence class, source; data vs interpretation separate) |
| `safety.py` | passive-mode read-only enforcement (the data-access choke point) |
| `provenance.py` | checkout provenance + deployment-drift detection (cloud; host placeholders) |
| `architecture.py` | mind_map + DAG readers; the **separate** runtime graph with per-edge source/test/runtime dimensions + cycle detection |
| `registry.py` | ingest the rNN experiment registry read-only; flag active/pending windows |
| `adapters.py` | classify existing tools by side effects; passive-only adapters (host-executed) |
| `collector.py` | orchestrate cloud collectors; `collect_combined` (cloud+host); baseline/treatment comparator |
| `snapshot.py` | before/after snapshots of the evidence set; load/reconstruct/diff |
| `ledger.py` | append-only **connection-level** test recording (DECLARED→…→RUNTIME_OBSERVED lifecycle) |
| `regression.py` | regression detection between two snapshots (weakened evidence, passive→active tool, cycle-level drop) |
| `longitudinal.py` | track a subject across an ordered series of snapshots (integration stages over time) |
| `report.py` | structured Markdown/JSON reports |
| `host.py` | the host-side read-only spec; host-results template + ingestion of Claude Code's host findings |
| `__main__.py` | CLI (`python -m watcher …`) |
| `tests/` | passive-safety proofs + behaviour tests (isolated fixtures, temp data) |

## Scope of this version

This is the **passive observation + comparison foundation**. It performs no
intervention: no live mutation, injection, flag change, DB write or restart.
Host-side collection is *described* for Claude Code to run on the machine
(`watcher host-request` / `host-template`), not executed here. Snapshots,
regression detection and longitudinal series are the comparison layer over passive
evidence — they observe change, they do not cause it. Isolated-testing and
active-experiment modes are **not** built — they require explicit, per-experiment
approval and are out of scope until the gate review authorizes them.
