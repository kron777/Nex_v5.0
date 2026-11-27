# NEX Phase 0 — Verified Defect and Evidence-Gap Backlog (Mainline)

**Snapshot:** `main` at `612022e81f749a99de665372704d7acc0645de67`  
**Date:** 27 November 2026  
**Purpose:** Separate confirmed documentation/source discrepancies from unknown host/runtime evidence and incomplete audits. This backlog is not approval to change cognition or policy.

## A. Confirmed documentation discrepancies

### D-01 — Sense adapter count / startup overview (partially corrected)

- **Evidence:** The factory wires 28 adapters (4 internal, 24 external); the scheduler constructor calls `start_all()`. The scheduler overview and `ARCHITECTURE.md` were corrected in PR #148.
- **Remaining at this snapshot:** `run.py`'s module overview still says five DBs and paused external feeds; `gui/server.py`'s module overview still says 23 adapters.
- **Disposition:** correction submitted in PR #153 (documentation-only; CI pending at report cut).

### D-02 — MIND_MAP node-count convention unresolved

- **Evidence:** Current `MIND_MAP.yaml` has 39 `nodes:` entries plus 5 arms; comments/roadmap references still refer to 30 nodes.
- **Impact:** audits can conflate the 30 substantive aspect nodes, structural/placeholder entries and full YAML entry count.
- **Disposition:** preserve the map as-is; request owner reconciliation of the counting convention. Do not delete or merge entries to force 30.

### D-03 — MIND_MAP doctrine references absent

- **Evidence:** CI verifier warns that `VIRTUE_SLATE.md` and `mental_factors_inventory_alobha_spec.txt` are missing.
- **Disposition:** identify the authoritative source copies and restore/repoint references through a traceable documentation change; do not fabricate substitutes.

## B. Verified policy / documentation boundary

### P-01 — Coherence Gate exception fallback is fail-open

- **Evidence:** `CoherenceGate.check()` catches evaluation exceptions, records them, and returns ACCEPT with `gate_error_fallback`.
- **Disposition:** current behavior is documented; no change to outcomes or policy in Phase 0. Any fail-closed or other policy change requires the governing specification and the applicable founder approval.

### P-02 — Coherence Gate outcome documentation had drifted

- **Evidence:** code persists HOLD through the Holding Zone and queues RESHAPE; old module docs described them as logged-only.
- **Disposition:** corrected in PR #149 (merged), doc-only.

### P-03 — DAG buildability description had drifted

- **Evidence:** executable `_SATISFIED` set is `built`, `live_unproven`, `terminal`, not `built` only.
- **Disposition:** corrected in PR #150 (merged), text-only; caveats retained.

## C. Evidence gaps / incomplete verification (not code defects)

### E-01 — Current host/runtime baseline absent

No current host collection establishes which checkout is deployed, whether a NEX process is running, whether user services are active, or the current OS/kernel/hardware/process state. The older 25-Nov report belongs to a different host/branch snapshot and must not be relabelled as current.

### E-02 — Live database integrity inventory absent

No current SHA-256/size/WAL inventory was collected for the six substrate databases or runtime snapshots. No private data was copied into Git.

### E-03 — Model/runtime performance baseline absent

Python/SQLite/Ollama exact versions on host, exact Qwen model digest, loaded-model state, idle/load RAM/VRAM and prefill/decode tokens/sec remain UNKNOWN.

### E-04 — Full faculty producer/consumer DAG incomplete

The boot graph and key Chat/Fountain paths have been mapped from source. A complete forward (declaration → boot → scheduler → emission → consumer) and backward (output/write → upstream producers) audit for every `theory_x/` faculty is not yet complete.

### E-05 — MIND_MAP freshness warnings

CI emitted stale-source verification warnings for numerous nodes, plus the past-due `p13_finitude` unblock marker. These need source review and evidence refresh, not timestamp-only edits.

### E-06 — L4/runtime causal trace not captured

M0.5 currently has L3 synthetic fixtures and paired test evidence. No authorised live run has set `NEX5_TRACE_OVERLAY_CONTEXT=runtime`; L4 remains UNKNOWN.

### E-07 — V2.1 / doctrine authority boundary

Roadmap v3.0 M0.5 (technical causal trace) is distinct from V2.1 M0.5 (six doctrine questions). This backlog does not claim the six doctrine questions are answered, does not recreate a missing Frozen V2.1 source, and does not alter the frozen S-01–S-25 register.

## D. Test / CI evidence

- Exact M0.5 PR head `6d371fe385fc02a2c238247b39aff82681888745`: 2,491 passed, 7 skipped, 40 subtests, baseline OK, CI run #1392.
- Mind-map verification: completed with warnings only; no hard errors. Warnings include 2 missing doctrine references, stale verification dates and one past-due unblock marker.
- The post-merge push run `45939220368` on `612022e81f749a99de665372704d7acc0645de67` was still pending/in progress at the time this backlog was drafted. Append its final result after completion.

## E. Gate boundary

This backlog is evidence input for Gate 0. It is not permission to enable Phase 1 experiments, change prompts, change confidence/belief revision, modify Coherence Gate policy, alter dark flags, start/restart services or touch live databases.
