# Phase 0 — Durable Handoff

**Master Roadmap v3.0 Phase 0 (Reality Audit & End-to-End Causal Trace).**
Branch `claude/nex-v5-audit-review-53ouqv`, built on head `fb87e24`.

This is the state after one safe, authorised increment. It is written to be picked
up cold.

## What is DONE (this increment)

| Item | Deliverable | Artifact |
|---|---|---|
| Repository / DB / snapshot baseline | M0.1 | `NEX_REPOSITORY_REALITY_REPORT.md` §1,3,4 |
| Test baseline (env-limited; CI authoritative) | M0.2 | reality report §5 |
| Crosswalk of the two output paths + L0–L4 ladder | M0.3–M0.4 (seed) | `NEX_ARCHITECTURE_CROSSWALK_v2.md` |
| ADR for the overlay decision | M0.3–M0.4 | `ADR-001.md` |
| Minimal default-OFF InfluenceRecord overlay + 16 tests (off==on identity proven) | M0.5 | `influence_record.py`, `tests/test_influence_record.py` |
| Fixture-level capture of one Fountain fire + one Chat turn | M0.5 (fixture) | `docs/phase0_influence_capture_fixture.jsonl` |

**Zero-delta status:** proven at fixture/seam level (off==on output + DB writes).
Default-OFF means the existing suite is unchanged. **Live zero-delta verification
is still owed** (see below).

## What remains INCOMPLETE (precise)

1. **Live L4 capture + live zero-delta verification.** Run the live NEX with
   `NEX5_INFLUENCE_TRACE=1 NEX5_INFLUENCE_TRACE_CONTEXT=runtime`, capture one real
   Fountain cycle and one real Chat turn, and diff behaviour/DB state against a
   flag-off run. **Blocked on:** a running NEX (voice endpoint at
   `NEX5_VOICE_URL`, `flask`) **and founder authorisation** to enable the flag on
   the live process. Until then L4 = **UNKNOWN**.
2. **Belief-level / faculty-block attribution.** The `L0/UNKNOWN` gaps in the
   crosswalk — deeper hooks inside `FountainGenerator.generate()` and
   `_assemble_chat_blocks()`. A separate, larger increment.
3. **Full-system producer/consumer DAG** (M0.3–M0.4 complete) across `theory_x/`
   (~40 stages), `substrate`, `speech`, `gui`. v2 covers only the two output paths.
4. **RDO v1.3 Stage 1 Watcher increment** vs Watcher v3.0. **Not on this branch** —
   it lives on the `claude/rdo-*` branch family (`git ls-files 'watcher/*'` is empty
   here). Reconcile it there, preserving the three separate evidence dimensions and
   the Watcher approval gates; do not merge the RDO line into this NEX line without
   direction.
5. **Governing PDFs.** Master Roadmap v3.0, RDO v1.3, Watcher v3.0 are absent from
   the workspace. Supplying them would settle M0.5's exact field requirements, the
   L0–L4 canonical definitions, and the **v1.3/v1.4 precedence (still UNRESOLVED)**.
6. **Trace retention** (rotation/size cap for `logs/influence_trace.jsonl`) — only
   relevant once the flag is enabled.

## Gate 0

**PENDING — not assumed.** The old claim that no Phase-1 behavioural modification had started is stale: commit f9ac58d added a default-OFF Phase 1 continuity consumer. It has not been live-armed or behaviourally validated. Do not enable it before the Gate 0 review and explicit authorisation; see the current reconciliation.
Enabling the overlay on the live NEX is itself a live-process change and awaits
founder authorisation.

## How to use the overlay

```bash
# default: OFF — nothing is traced, zero behavioural delta
#
# enable (fixture/dev):   produces L3 records
export NEX5_INFLUENCE_TRACE=1
# enable (authorised live run): produces L4 records
export NEX5_INFLUENCE_TRACE=1 NEX5_INFLUENCE_TRACE_CONTEXT=runtime
# optional sink override (default logs/influence_trace.jsonl, git-ignored)
export NEX5_INFLUENCE_TRACE_PATH=/path/to/trace.jsonl

python -m pytest tests/test_influence_record.py -q   # 16 tests
```

## Branch / PR safety

The RDO stage branches and PRs (#45–48) are untouched and preserved. This
increment adds only Phase-0 files on `claude/nex-v5-audit-review-53ouqv`; the
untracked `watcher/` directory (RDO-line leftover) was deliberately **not** added.
No live NEX state, flags, databases, or runtime were altered.
