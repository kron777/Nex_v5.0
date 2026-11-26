# RDO Stage 7 — Execution Integration Verified Through the Watcher

**Governing scope:** RDO v1.3 §16 Stage 7 — the capstone that closes the loop:

> objective → recursive expansion → obligation graph → work package → **execution** →
> **independent Watcher evidence** → outcome comparison → learning.

A success is **never** inferred from a completion claim, a commit, or a file's existence: the verdict
comes from the Watcher's independent evidence along **three separate dimensions** — source-implemented,
test-verified, runtime-observed. Runtime observation stays host-only and **UNKNOWN**.

**OFT / reuse (no second Watcher, no general execution framework):** `rdo/execution.py` reuses
`watcher.ledger.ConnectionLedger` (the three-dimension lifecycle), `watcher.evidence`
(Evidence / host_placeholder for provenance + honest unknowns), and the RDO's read-only grep. It feeds
the verified outcome into the Stage-6 learning loop with provenance preserved.

**Coordination.** Branch `claude/rdo-stage7-execution-watcher`, based on `0693e7f` (Stage 6 head).
`rdo/`-only; earlier branches untouched. No live NEX writes/injections/restarts/flags/experiments;
no unauthorised Watcher activation or host probing; no commits/merges/deploys beyond isolated dev.
`python -m rdo stage7`.

## The pathway (durable execution record)

`create_execution_record` links a work package to its **originating objective + obligations**, with
acceptance criteria, a Claude-Code **handoff** spec (agent, instruction, evidence required), and the
per-obligation **evidence requirements** (a source signature + an optional test). `record_claim` stores
the agent's self-reported claim — **recorded, not trusted**.

## Independent Watcher verification (three separate dimensions)

`verify` records each obligation through the Watcher's append-only `ConnectionLedger`:

| dimension | how | who |
|---|---|---|
| `source_implemented` | read-only grep of the after-state for the signature → `SOURCE_CONFIRMED` | cloud |
| `test_verified` | run the required test independently only when its exact repo-relative path is explicitly supplied in the caller's `approved_test_files` allowlist; otherwise `not_authorized` | cloud |
| `runtime_observed` | **host-only** `host_placeholder` — `UNKNOWN` (NEX in standby) | host (not performed) |

Per-obligation verdict: **verified** (source + test), **failed** (test fails), **partial** (source, no
test), **claim_unverified** (no independent source evidence). The overall verdict takes the worst, and
**ignores the completion claim**.

## Vertical slice (isolated fixture)

`run_stage7_execution_integration` runs two controlled tasks in a throwaway temp dir:

- **Verified:** a guard mechanism + its passing test → `verdict = verified`; dimensions
  `source=static, test=passed, runtime=UNKNOWN(host)`; ledger state `TEST_PASSED`.
- **Claim-only (negative):** completion **claimed**, and an unrelated test passes, but the required
  **source is absent** → `verdict = claim_unverified` — **not accepted**. (A claim / passing test alone
  is never success.)

The verified outcome feeds the learning loop as an `actual` with `review_kind=watcher_verified_execution`;
`learning_provenance` classifies it `independent_watcher_verified` — a distinct category, **not** human
review and **not** RDO self-assessment. Failed/unverified obligations are **reopened**.

## Requirements → evidence (tests)

`rdo/tests/test_stage7_execution_watcher.py` now includes explicit test-execution authorization and path-containment regressions. The Stage-7 test file now contains 12 tests. The earlier local report of 10 Stage-7 tests / 108 RDO tests predates these additions; the updated full-suite count and pass status are pending exact-head CI.

- traceability objective→obligations · three separate dimensions → `test_verified_*`, `test_traceability_*`
- **claim / passing test alone ≠ success** → `test_claim_without_source_evidence_is_not_accepted`, `test_missing_all_evidence_is_claim_unverified`
- conflicting/failing evidence → `test_failing_test_overrides_a_completion_claim`, `test_source_without_test_is_partial`
- runtime never verified from cloud → `test_runtime_dimension_is_never_verified_from_cloud`
- persistence + fresh-process resume (append-only ledger) → `test_record_and_ledger_persist_and_resume`
- rollback/reopen + learning feedback with provenance → `test_failed_verification_reopens_and_feeds_learning_with_provenance`
- isolated rollback, no live state → `test_rollback_is_isolated_nothing_live_touched`

## Limitations / remaining gates

- **Runtime observation is host-only and NOT performed.** Source + test verification is cloud-side; a
  live runtime trace (the `runtime_observed` dimension) requires **host access + experiment-specific
  approval** and remains UNKNOWN. This is the one standing gate for a fully runtime-verified outcome.
- The slice executes a **controlled fixture**, not a live NEX change; real execution of an RDO work
  package against NEX would require human approval for any consequential/live operation.
- `_confidence` calibration weights remain heuristic.

## Roadmap status

The fixture demonstrates the Stage-7 verification mechanism, but it does **not** complete
the Stage-7 objective-to-verified-delivery exit criterion. **Integration status (26 Nov 2026):**
foundational PR #46 and the consolidated Stage 2–7 integration PR #124 have merged. The older
stage PRs remain source-history references and are not to be merged separately.

The **v1.3/v1.4 precedence** is still **not** resolved by assumption, and the host-only live
confirmations across Stages 1/5/7 remain for founder authority.


### Test-execution safety boundary (added after source review)

A test path listed in an execution record is an evidence requirement, not permission to execute it.
`verify()` now runs pytest only when the caller supplies the exact repo-relative path in
`approved_test_files`. Absolute paths, `..` traversal and symlinks resolving outside
`repo_dir` are refused. An unapproved / unsafe path is recorded as
`test_verified.status = not_authorized`; source-only evidence remains `partial` and the
Watcher ledger does not advance to `TEST_WRITTEN`.

The controlled Stage-7 demonstration explicitly allowlists only `test_demo_guard.py` inside its
throwaway temporary repository. New tests prove that a declared but unapproved test is not executed
and that even an allowlisted path cannot escape the repository root. This is a per-call explicit
authorization boundary; it does not claim arbitrary test suites are side-effect-free.

## Bounded objective-to-handoff increment (26 Nov 2026)

The generic intake interface is merged and a first durable handoff path now exists:

- A manifest is derived from an RDO-native persisted cycle and one named work package.
- The intake revision digest and original wording/intent are preserved.
- The selected repository must still be clean and at the exact commit used by the cycle.
- The exact affected paths, obligations, dependencies, acceptance criteria, constraints, exclusions, anti-requirements and evidence needs are included.
- Allowed paths are resolved against the repository root; outside-pointing symlinks are refused and internal aliases retain their resolved target.
- The manifest is immutable and SHA-256 checked. A separate append-only, hash-chained event ledger records human-attributed scope reviews and a separate human-acceptance event.
- Reviewer/source fields are caller-attributed and **not authenticated** by this local mechanism.
- A scope approval can only record preparation of a proposed patch within scope. It cannot authorize pytest, arbitrary commands, live NEX changes, database writes, experiment changes, services or deployment.
- Human acceptance is a distinct judgement and does not rewrite source/test/runtime evidence.

Commands and file format are documented in [STAGE7_HANDOFF.md](STAGE7_HANDOFF.md).

### What remains before Stage 7 can be called complete

1. Verify source evidence through a separate Watcher process boundary rather than importing Watcher ledger/evidence into the RDO process.
2. Retain distinct source, test, host-runtime and human-acceptance evidence with no substitution.
3. Demonstrate a real, non-behavioural objective through intake → persisted cycle → exact manifest → human review → independent Watcher verification.
4. Design and verify a disposable no-secrets/no-live-data test environment before any arbitrary repository test code is run. The existing exact-path allowlist is not a sandbox.
5. Obtain the appropriate host/runtime approval before any runtime observation; runtime remains UNKNOWN until actually observed.

The handoff manifest is a planning/review artifact, not an execution launcher. The Stage-7 completion issue remains open; no RDO Stage 8 is inferred.

