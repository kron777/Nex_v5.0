# Watcher offline ripple — premise-check + built extension

**Job:** after a wire is connected, tell the reasoning side **what rippled**, so
those effects can be smoothed before the next wire — without hand-reading the whole
codebase. (The "read the karma, then settle it" step of the dev loop.) Offline tier
only; no live NEX required.

## Step 0 — premise-check of PR #46 (adopt vs rebuild)

**Verdict: ADOPT #46 and extend.** Reuse was the default and it held.

PR #46 (`claude/watcher-mvp`) is an adequate, spec-aligned foundation:
- external & read-only, independent of NEX's runtime (no `theory_x`/`substrate`),
- one `Evidence` record type (origin cloud/host, 5-class evidence ladder, data vs
  interpretation kept separate), the `safety.py` read-only choke point,
  before/after `snapshot` + `regression`, and a clean `collect → report` CLI.

But **neither offline-tier capability the job needs existed yet**:
- `architecture.py` reads the **curated** `MIND_MAP.yaml` + `sentience_dag.json` and
  builds a runtime-wiring graph — it is **not** a computed source-level
  reverse-dependency map of "who imports/calls what a wire touched."
- `regression.py` diffs two **Watcher evidence snapshots** (evidence weakening,
  passive→active, cycle-level drop) — it is **not** a pytest-suite pass/fail delta.

So the gap is exactly the two offline views; the fix is the smallest extension that
adds them on top of #46's plumbing (not a rebuild — a rebuild would have been
stopped and reported first, per instruction).

## Built extension (smallest, reuses #46)

`watcher/ripple.py` + two CLI verbs + tests + this doc. No change to any existing
`watcher` module beyond a one-line import and two subparsers in `__main__.py`.

| View | Function | Output |
|---|---|---|
| (a) source-dependency ripple | `source_dependents(repo, changed)` | `Evidence(cloud, static)` — direct reverse-import map of the changed modules + `downstream_tests` (run those first) + their top-level symbols |
| (b) test-suite delta | `test_outcomes(repo, target)` → `test_delta(before, after)` | per-test outcomes via pytest **JUnit XML**; diff → `newly_failing` (critical) / `newly_passing` / `appeared` / `removed`, as `Evidence(cloud, implemented)` |
| runtime tier (NOT built) | `runtime_ripple_placeholder()` | honest `Evidence(host, unknown, unverified)` + ingestion hook via `watcher.host` |

CLI:
```
python -m watcher ripple   --changed a.py,b.py | --base <gitref>  [--before X.json --after Y.json] [--out DIR]
python -m watcher test-run  [--target T] [--out FILE]            # outcome snapshot (before/after a wire)
```

### Dogfood (real, this repo)
- `ripple --changed watcher/evidence.py` → **13 direct importers**
  (incl. `rdo.memory/model/orchestrator` across lines) + **3 downstream tests**,
  16 unique downstream modules. That is the karma of touching a core type.
- `test-run` ×2 on `watcher/tests` (32 tests) → **zero delta** (clean), with the
  `ripple.test_delta` (cloud/implemented) + `ripple.runtime` (host/unknown) records.

### Tests
`watcher/tests/test_watcher_ripple.py` — 10 tests: reverse-import (incl. relative
imports), non-Python change listing, test-delta classification (newly failing /
passing / appeared / removed), live JUnit parse, runtime-placeholder honesty,
assembly shape + Evidence validity, and an **AST independence scan** asserting no
`watcher/*.py` imports `theory_x`/`substrate` (a guard #46 documented but did not
enforce). Full `watcher/tests`: **42 passed** (32 prior + 10 new).

## Guarantees honored

External, read-only, never a NEX organ, never steers her. `ripple.py` imports no
`theory_x`/`substrate` (test-enforced). The offline tier executes only the repo's
own test suite in isolation (tmp fixtures) — **nothing on the live host is
touched**, and no live NEX state/flag/DB/runtime is read or changed.

## Status label

Everything the offline tier reports is **repo-proven, live-confirm pending** — it
is the source graph and the test suite, not her runtime. It is not "done-done"
until NEX is live and the Watcher's runtime tier has seen the change behave. That
tier is left as a clean host-only hook; it does not block the offline tier.

## Not done (deliberately, per direction)

- Runtime tier (what fired / behaviour delta) — host-only, batched for when she's live.
- Symbol-level call graph beyond import bindings (import-level reverse map is the
  minimal useful primitive; a full call graph is not needed for the job).
- Nothing merged; isolated branch `claude/watcher-offline-ripple` stacked on #46.
