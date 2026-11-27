# NEX Integration Watcher

An **external, non-mutating to NEX runtime** observation and test coordinator.
It may write Watcher-owned reports and evidence ledgers, but it does not change
NEX cognitive/runtime state. It is an instrument to **understand** NEX, not a
mechanism that changes it. Observation, interpretation and intervention are
kept separate on purpose.

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
`test_verified` flag; they do not represent a test run or captured CI result.

A `runtime_observed` edge must also carry `runtime_origin="host"` and a nonblank
`runtime_ref`, and it must be source-confirmed. The append-only ledger requires nonblank `evidence_refs` for
`SOURCE_CONFIRMED`, `TEST_WRITTEN`, `TEST_PASSED`, `TEST_FAILED`,
`RUNTIME_OBSERVED` and `REGRESSED` transitions. It additionally rejects
`RUNTIME_OBSERVED` unless its origin is `host`. Graph seeding passes the edge's
explicit runtime reference through; it never manufactures a host-origin observation.
Evidence-reference lists are snapshotted on append, and `record()`,
`history()` and `entries` return detached views so caller mutation cannot rewrite
in-memory history. The ledger validates the presence of references, not that the
referenced traces or source/test artifacts have been independently opened or
authenticated. This repository snapshot contains no
current host collection; `runtime_observed` therefore remains unknown until a
separately authorised host observation supplies evidence.

## Founder constraints honored

1. **Learning ↔ belief-confidence loop** — surfaced as a **test_verified** feedback
   cycle (`reconciler → beliefs.confidence → producers → expectations → reconciler`):
   it has code and tests, but is **not** claimed `runtime_observed` because no current host trace has been collected.
   The Watcher characterizes it; it does not touch the live safeguards.
2. **Candidate mood loop** — any cycle through `affect_state` is labeled
   **hypothesis** and its edges carry an explicit `HYPOTHESIS` note; it is never
   promoted to fact without a live runtime trace.
3. **Third runtime graph** — a separate artifact; the DAG and mind map are inputs,
   never rewritten.

## Run it (passive with respect to NEX)

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

# inspect the fixed host-side read-only specification
python -m watcher host-request

# run the fixed collection locally on the NEX workstation
# SHA-256 fingerprinting reads selected DB/snapshot files in full (disk I/O warning shown)
python -m watcher host-collect --out host_results.json

# optional: collect everything except full-file DB/snapshot fingerprints
python -m watcher host-collect --skip-artifact-hashes --out host_results.json

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
| `host.py` | the host-side read-only spec; host-results template + provenance-aware ingestion |
| `host_runner.py` | local executor for the fixed host request commands; writes a provenance-bearing JSON result |
| `service_audit.py` | selected systemd state and referenced-path checks for four fixed NEX user services plus the Vitals timer; emits no raw ExecStart arguments and performs no lifecycle actions |
| `__main__.py` | CLI (`python -m watcher …`) |
| `tests/` | passive-safety proofs + behaviour tests (isolated fixtures, temp data) |

## Scope of this version

This is the **passive observation + comparison foundation**. It performs no
intervention: no live mutation, injection, flag change, DB write or restart.
Host-side collection is executed locally by the operator with `watcher host-collect`; cloud-side code never claims to have observed the workstation. Snapshots,
regression detection and longitudinal series are the comparison layer over passive
evidence — they observe change, they do not cause it. Isolated-testing and
active-experiment modes are **not** built — they require explicit, per-experiment
approval and are out of scope until the gate review authorizes them.


## Independent RDO handoff source verification

Use the RDO-facing command: `python -m rdo handoff-verify --handoff-id <handoff-id> --repo . --out rdo/.cycles`.

The RDO adapter creates a versioned, exclusive temporary request in the handoff store, then starts `python -m watcher verify-handoff` as a separate process from the trusted RDO/Watcher installation root. The inspected repository is passed as data; its Python modules are never imported as the verifier. The request file is removed after the response is checked. The internal Watcher CLI accepts a request file, but users should invoke the RDO-facing command rather than hand-authoring or relying on a fixed request path.

The Watcher verifies the immutable manifest digest, complete human scope-review event chain, current approved scope, planning-commit ancestry, Git-derived changed paths (committed, staged, unstaged and non-ignored untracked), exact-file allowlist and symlink boundaries. It fingerprints bounded in-scope changed files and appends source-only transitions to its own connection ledger under `rdo/.cycles` with a process lock covering ledger load, transition checks and append.

This is source/path verification only. It does not run pytest, arbitrary commands, project scripts, agents, services, deployments or NEX runtime operations. The report keeps `test_verified=not_authorized` and `runtime_observed=unknown_host_only`; file presence/hash does not prove semantic satisfaction or human acceptance. Reviewer attribution is integrity-checked but not identity-authenticated. The Watcher ledger write is a Watcher-owned evidence artifact, not a NEX cognitive/runtime write.
