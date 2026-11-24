# Wire 1 — Continuity record → self-view (SENTIENCE Phase 1 consumer)

**First real faculty wire.** The accruing bound self-state history now informs one
real, bounded decision that previously ignored it. Default-OFF, offline-proven.
**Repo-proven, live-confirm pending** — whether she is *actually* more continuous
waits for her to be live and for the Watcher's runtime tier to see it behave.

## What was wired
- `self_binding.continuity_for_prompt()` (new, read-only, `NEX5_SELF_CONTINUITY`,
  default OFF): reads the recent `self_state_history` rows and returns a short
  **descriptive** clause — "this '<emotion>' has held steady" vs "a shift from how
  I was (I was '<prev>')" vs "moving rather than settling."
- `SelfMindView.current_summary()` appends that clause when armed. One call site.

## Hard guardrail (honored)
The clause **colours** the self-view; it **never gates, scores, blocks or vetoes**
any choice — same descriptive-not-verdict line as the Throw-Net Compass. It is
read-only (SELECT only, test-proven), fail-safe (`''` on any error), and dark by
default so every current reader is byte-identical until armed.

## Step 0 — consumer choice (reported before building)
`SelfMindView.current_summary()` was chosen as the smallest honest consumer:
`self_binding.format_for_prompt()` has **zero callers**; the bound self reaches NEX
only via `bind()` from `recursive_self` (**the fire path — off-limits**) and
`self_mind_view` (**off** the fire path). `current_summary` is her self-model, is
descriptive by construction, and ignored the history entirely. Clean, not risky,
cannot disturb the fire path → built.

## The four buckets (dev-pattern log)
- **Upstream — was the history there/usable?** Yes. `self_state_history`
  (emotion/raga/drive/readiness/synthesis) is written every `bind()` and reaped for
  retention; it had **one** reader (`episodic`, affect tagging) and informed **no
  decision**. Usable as-is; no schema change needed.
- **Shared readers — what rippled (esp. the fire path)?** `self_binding` has 4
  importers incl. **`stage6_fountain.generator` (the fire path)** + `compass`,
  `recursive_self`, `self_mind_view`. The fire path imports `self_binding` only for
  `afflictions_for_prompt`/`recursive_self` — **not** `continuity_for_prompt` and
  **not** `current_summary`. So the shared reader is present but **not on the path I
  touched**. `self_mind_view` has 0 importers (leaf consumer).
- **Already there?** The continuity *record* (Phase 1) already existed and accrued;
  what was missing was any *consumer*. `SelfMindView` already captured the bound
  self synthesis into its own snapshots but never reflected its **trajectory**.
  Nothing was double-built.
- **Proof.** `watcher ripple` before/after on the seam: test-delta = **8
  `test_appeared` (the new tests), 0 newly_failing, 0 warning/critical**; **no
  fountain/fire test in the delta**. Reproduced full-suite comparison using the
  same Python environment: parent **1602 passed / 0 failed / 0 errors / 5 skipped /
  30 subtests**; continuity branch **1610 passed / 0 failed / 0 errors / 5 skipped /
  30 subtests**. Net **+8 passing tests, with no regressions**. `generator.py` not in the diff
  (only `self_binding.py` +42/−0 and `self_mind_view.py` +13/−1). Fire path proven
  unaffected.

## To arm (host, when she's live — needs Gate-0 authority)
`NEX5_SELF_CONTINUITY=1`. Then confirm via the Watcher runtime tier that her
self-view carries the continuity clause and that fountain behaviour is unchanged.

Isolated branch `claude/nex-continuity-wire` (on the NEX dev head). Nothing merged;
no live NEX state/flag/DB/runtime touched.
