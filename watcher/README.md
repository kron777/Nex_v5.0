# NEX Integration Watcher

An **external, read-only** observation and test coordinator for NEX. It is an
instrument to **understand** NEX, not a mechanism that changes it. Observation,
interpretation and intervention are kept separate on purpose.

## Guarantees

- **Independent of NEX's cognitive runtime.** Nothing in `watcher/` imports
  `theory_x` or `substrate`. It reads files (YAML/JSON), Git state, and — on the
  host only — SQLite **read-only**.
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

## Founder constraints honored

1. **Learning ↔ belief-confidence loop** — surfaced as an **implemented** feedback
   cycle (`reconciler → beliefs.confidence → producers → expectations → reconciler`).
   The Watcher characterizes it; it does not touch the live safeguards.
2. **Candidate mood loop** — any cycle through `affect_state` is labeled
   **HYPOTHESIS** and its edges carry an explicit note; it is never promoted to
   fact without a live runtime trace.
3. **Third runtime graph** — a separate artifact; the DAG and mind map are inputs,
   never rewritten.

## Run it (all passive)

```bash
# cloud/static reconnaissance -> report.md + report.json
python -m watcher recon --out watcher/reports

# the runtime graph + feedback cycles (JSON)
python -m watcher graph

# the read-only host-side spec, for Claude Code to execute on the machine
python -m watcher host-request

# the passive-safety + behaviour tests
python -m pytest watcher/tests -q
```

## File inventory

| File | Purpose |
|---|---|
| `evidence.py` | the one `Evidence` record (origin, timestamp, evidence class, source; data vs interpretation separate) |
| `safety.py` | passive-mode read-only enforcement (the data-access choke point) |
| `provenance.py` | checkout provenance + deployment-drift detection (cloud; host placeholders) |
| `architecture.py` | mind_map + DAG readers; the **separate** runtime graph + cycle detection |
| `registry.py` | ingest the rNN experiment registry read-only; flag active/pending windows |
| `adapters.py` | classify existing tools by side effects; passive-only adapters (host-executed) |
| `collector.py` | orchestrate cloud collectors; baseline/treatment comparator |
| `report.py` | structured Markdown/JSON reports |
| `host.py` | the host-side read-only spec + ingestion of Claude Code's host findings |
| `__main__.py` | CLI (`python -m watcher …`) |
| `tests/` | passive-safety proofs + behaviour tests (isolated fixtures, temp data) |

## Scope of this first version

This is the **passive observation foundation** (spec Phase D MVP). It performs no
intervention. Host-side collection is *described* for Claude Code to run locally
(`watcher host-request`), not executed here. Isolated-testing and active-experiment
modes are **not** built — they require explicit, per-experiment approval and are
out of scope until the gate review authorizes them.
