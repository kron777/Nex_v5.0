# Phase 0 p12_selfreport provenance reconciliation

**Date:** 26 November 2026  
**Status:** Evidence clarification only; M0.2 remains partial.  
**Scope:** Historical failure identity, current branch comparison and evidence limits.

## Finding

The identifier `p12_selfreport` is a **MIND_MAP node**, as stated in the founder-provided frozen register/Part 3. The historical failure was the node's MIND_MAP absence-claim validator check, not a pytest node named `p12_selfreport`. V2.1 §13.2 describes the work as the “`p12_selfreport` test and callers”; the recovered founder context identifies the object as the MIND_MAP node and its absence-check, not an independent pytest test.

A prior 18 November audit record reported:

- `ERROR p12_selfreport: absence claim falsified`;
- eight matching lines in `theory_x/stage_tom/hri_apatrapya_prototype.py`;
- a proposed resolution to correct the false absence claim or reclassify the node with a recorded reason.

The source-history record is specific: commit `ecf9c437528a9445f37020f8fadfa02de507520e` (20 November) explicitly states that CI's absence-grep was failing because this node still had `source.kind: absent` and `last_verified: 2026-11-09`, even though the prototype had been built on 10 November. The commit records the correction to `source.kind: inferred`, `source.from: hri_apatrapya`, `evidence: implemented`, `dark: true`, and `last_verified: 2026-11-20`. It identifies the exact CI step as `python mind_map/mind_map.py --check --verify` and records that it exited 0 after the correction, with the full suite at 2,166 passed, 7 skipped, 40 subtests and 0 failed. The raw failing workflow log itself has not been recovered, so the commit message is the preserved historical evidence rather than a raw CI transcript.

## Current main-branch source evidence

At the inspected `main` snapshot:

- `mind_map/MIND_MAP.yaml` contains node `p12_selfreport`. It now has `source.kind: inferred` and `source.from: hri_apatrapya`, rather than an active `source.kind: absent` check.
- Its notes explicitly state that the earlier absence check for `hri|apatrapya|NEX5_SHAME|NEX5_SELF_REPORT` was stale: the `hri_apatrapya_prototype.py` build landed on 10 November (commit `7ad9942`), while the absence check remained pinned to 9 November. The node was corrected on 20 November.
- The same notes distinguish the still-absent `NEX5_SHAME` / `NEX5_SELF_REPORT` flags from the now-present hri/apatrapya source. The false part of the old absence claim was the hri/apatrapya portion.
- `mind_map/mind_map.py` performs the absence-grep verification only when a node's source kind is `absent`. The current `p12_selfreport` node is `inferred`, so that old absence check is no longer active for this node.
- This historical failure is therefore classified as a **genuine MIND_MAP CI validation failure caused by a stale/obsolete absence claim, corrected on 20 November**. It is not evidence of a currently failing pytest node named `p12_selfreport`.
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

- **Historical MIND_MAP finding:** classified as a genuine validator failure caused by a stale/obsolete absence claim; corrected on `main` by commit `ecf9c437` on 20 November. The current `p12_selfreport` node no longer carries the false absence check.
- **V2.1 M0.2 `p12_selfreport` item:** the founder-provided frozen register identifies it as the MIND_MAP node. Its historical absence-check failure is reproduced in the repository's 20 November source-history record and classified as a genuine validator failure caused by a stale/obsolete absence claim. The node was reclassified to an inferred source relationship; the post-fix `--check --verify` step exited 0. No separate pytest node named `p12_selfreport` is identified in the current test inventory.
- **Current active-host test baseline:** clean for the reported run. The active-host branch lacks both the MIND_MAP and prototype source, so the main-branch correction cannot be reproduced on that checkout.
- **Remaining M0.2 scope:** the earlier environment-limited run (107 failures and 62 errors) remains only an aggregate historical result in the available report; per-test identities/classifications are not present. The current `tests/known_failures.txt` has no active allowlist entries.

The `p12_selfreport` node's historical validator failure is now classified and corrected. M0.2 remains **PARTIAL** because the available evidence does not enumerate/classify the earlier environment-limited failures individually, and the active-host branch does not contain the MIND_MAP/source pair for an on-branch rerun.

This note does not amend the frozen register, V2.1 proposal, roadmap, MIND_MAP authority, test baseline or runtime. It records the distinction between a corrected historical main-branch absence claim and the still-unresolved M0.2 failure reference.
