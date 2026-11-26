# Phase 0 p12_selfreport provenance reconciliation

**Date:** 26 November 2026  
**Status:** Evidence clarification only; M0.2 remains partial.  
**Scope:** Historical failure identity, current branch comparison and evidence limits.

## Finding

The historical `p12_selfreport` finding has a documented connection to the MIND_MAP absence-claim validator. It is **not established from the available evidence that this is the same item meant by the V2.1 M0.2 reference to `p12_selfreport`**, nor is it established as an ordinary pytest node.

A prior 18 November audit record reported:

- `ERROR p12_selfreport: absence claim falsified`;
- eight matching lines in `theory_x/stage_tom/hri_apatrapya_prototype.py`;
- a proposed resolution to correct the false absence claim or reclassify the node with a recorded reason.

A later correction record states that the exact CLI invocation/output had been reconstructed rather than captured verbatim. Therefore the historical error text and source finding are retained as prior audit evidence, not represented as a preserved raw CI log.

## Current main-branch source evidence

At the inspected `main` snapshot:

- `mind_map/MIND_MAP.yaml` contains node `p12_selfreport`. It now has `source.kind: inferred` and `source.from: hri_apatrapya`, rather than an active `source.kind: absent` check.
- Its notes explicitly state that the earlier absence check for `hri|apatrapya|NEX5_SHAME|NEX5_SELF_REPORT` was stale: the `hri_apatrapya_prototype.py` build landed on 10 November (commit `7ad9942`), while the absence check remained pinned to 9 November. The node was corrected on 20 November.
- The same notes distinguish the still-absent `NEX5_SHAME` / `NEX5_SELF_REPORT` flags from the now-present hri/apatrapya source. The false part of the old absence claim was the hri/apatrapya portion.
- `mind_map/mind_map.py` performs the absence-grep verification only when a node's source kind is `absent`. The current `p12_selfreport` node is `inferred`, so that old absence check is no longer active for this node.
- `theory_x/stage_tom/hri_apatrapya_prototype.py` exists on `main`. Its module docstring describes it as a shadow prototype, not in the live path, with `NEX5_APATRAPYA_CHANNEL` default OFF. The map points to fixture tests in `tests/test_apatrapya_channel.py`; it does not identify a pytest test named `p12_selfreport`.

## Active-host branch comparison

At the audited active-host branch `claude/nex-continuity-wire` / `de93134f34adac07a3a41c2a05b33720510a2bfc`:

- `mind_map/MIND_MAP.yaml` is absent.
- `theory_x/stage_tom/hri_apatrapya_prototype.py` is absent.
- `tests/known_failures.txt` has no active allowlist entries.
- The founder-provided host test run reported 1,610 passed, 5 skipped and 30 subtests, with no unexpected failures.

Consequently, the old MIND_MAP validator condition cannot be reproduced against this active-host branch snapshot: both the map and the referenced source file are absent there. Main-branch correction evidence must not be silently substituted for active-host evidence.

## M0.2 classification boundary

The evidence supports this narrow conclusion:

- **Historical MIND_MAP finding:** stale/falsified absence claim; the current main-branch map records the correction by changing the node to an inferred source relationship.
- **V2.1 M0.2 `p12_selfreport` failure identity:** unresolved. No originating pytest node ID, test file, raw failure output or run context has been recovered to establish whether the V2.1 reference denotes this validator finding or a separate test failure.
- **Current active-host test baseline:** clean for the reported run, but that does not by itself classify the historical `p12_selfreport` item.

Do not label the V2.1 item genuine, expected, obsolete or environment-dependent until its identity and originating evidence are established. M0.2 therefore remains **PARTIAL**, not closed.

This note does not amend the frozen register, V2.1 proposal, roadmap, MIND_MAP authority, test baseline or runtime. It records the distinction between a corrected historical main-branch absence claim and the still-unresolved M0.2 failure reference.
