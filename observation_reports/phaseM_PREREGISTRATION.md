# PHASE M — PRE-REGISTRATION: the metacognition digest (`NEX5_METACOG_DIGEST`)

## 0. Status — Step-0 EXPOSURE measured 2026-11-07; current parameters DO NOT ARM

Per `observation_reports/LEVER_PRESCREEN.md` (adopted 2026-10-11, after four L4 levers were each
falsified before arming by a pre-arm measurement): **run the five static predicates before
building or arming anything.** Phase M was built and unit-tested dark (11 tests,
`tests/test_metacognition_digest.py`) on 2026-11-07, but built ≠ armable — the arbiter (r77)
taught us those are different claims. This document is the Step-0 check, run read-only against
the live `data/conversations.db`, **before** any live round is designed.

**Result: EXPOSURE fails at the current parameters (`_DIGEST_PATTERN_MIN_COUNT=3`,
`_DIGEST_LOOKBACK_S=24h`).** The entire lifetime of `meta_cognition_events` (first-order detector
live since Phase 16/40/41) is **6 rows, total, ever**:

| event_type | n (all-time) | first | last |
|---|---|---|---|
| `groove` | 3 | 2026-10-26 22:30:45 | 2026-10-29 08:04:21 |
| `value_drift_abandonment` | 3 | 2026-10-29 08:04:04 | 2026-11-07 03:59:29 |
| (other 7 first-order types) | 0 | — | — |

No 24h window in this history ever contains 3 same-type events — the densest cluster (both types,
2026-10-29 08:04:04 / 08:04:21, 17s apart) is **2**. **The digest's trigger has never once fired
and cannot have fired, at any point in its measured history, at the current threshold/window.**
This is the same failure class LEVER_PRESCREEN predicate 1 (EXPOSURE) was adopted to catch in r79/
r80/r82 — "measure the trigger's live rate from the data, not from supply" — found here before
arming rather than after, which is the point of the discipline.

**Root cause, not just a symptom:** this is CONTINUE_HERE.md §7's standing lesson #1 recurring a
fourth time — *"A gate's window must exceed the inter-arrival time of what it catches... Check
scope before threshold."* First-order metacognitive episodes arrive roughly once every 3–9 days
(the three episodes on record: 10-26, 10-29, 11-07), not multiple times within a day. A 24h
lookback cannot accumulate 3 same-type events when the type itself fires every several days.
Simulating the trigger at a 14-day lookback (chosen because it equals `_STALE_DAYS` — the window
in which an event is still considered "live" rather than auto-resolved — not an arbitrary
widening) against the *same* 6-row history: **it would have fired twice already** — `groove` on
2026-10-29 08:04:21, `value_drift_abandonment` today, 2026-11-07 03:59:29. The phenomenon the
digest is meant to catch exists; the window was simply scoped to the wrong clock.

**Decision (this gate, now): do NOT arm `NEX5_METACOG_DIGEST` as currently parameterized.** It
would ship dark-and-inert — satisfying its own pre-written falsifier ("still reporting into
nothing") on day one, for the same structural reason r82 did. Two things must happen before any
live round, both measurement-design decisions, not code:

1. **Re-derive `_DIGEST_LOOKBACK_S`** against the first-order inter-arrival time, not left at a
   guessed 24h. Candidate: align it to `_STALE_DAYS` (14d) since that is already the table's own
   definition of "still live" — reusing an existing constant's meaning rather than inventing a
   second one. This is a one-line change, but it is a parameter decision that needs pre-arm
   sign-off, same as r83's `NEX5_PHRASING_ROTATE_BUDGET` was fixed before arming, not tuned live.
2. **Accept that exposure will remain rare even after the fix.** At 14d lookback, this history
   gives **~1 digest-eligible moment per ~9–12 days**. A live round needs a window long enough to
   accumulate several firings, not just cross a day count — see §5.

## 1. The change under test (once re-parameterized per §0)

**`NEX5_METACOG_DIGEST` (default OFF).** `theory_x/stage9_metacognition/metacognition.py`
`_detect_digest()`: on each `tick()`, read `meta_cognition_events` created within the lookback
window, excluding rows of `event_type="metacog_digest"` itself (the pre-registered no-runaway
exclusion — tested, `TestDigestNoRunaway`), group by `event_type`, and for any type at or above
`_DIGEST_PATTERN_MIN_COUNT` not already digested within `_DIGEST_COOLDOWN_S` (3600s), write one
`metacog_digest` row with a second-order phrase. **Mechanically important, not yet named in the
spec:** `get_recent()`/`format_for_prompt()` select the single most-recently-created unresolved
event as "top." A digest row, being freshly written, **immediately becomes "top" and displaces
whatever first-order line would otherwise have surfaced**, and stays "top" until either a newer
event (first-order or digest) is written, or `decay()` auto-resolves it 14 days later. So the
observable effect of arming is not merely "an extra row exists" — it is periods, of
unpredictable and possibly long duration given how rare newer events are, during which the
chat/fire self-observation line reads as second-order instead of first-order.

## 2. Why this is a harder baseline than r77's (and why §0's finding makes it moot for now)

r77 had a true OFF: the chat arbiter had never run on the live instrument, so OFF meant
concatenation exactly as it always had been. Phase M has no equivalent clean OFF for the
*surfaced line* — the first-order `format_for_prompt()` call is already live and unflagged in the
chat path (`gui/server.py:1446-1449`, "Always-on"), separately gated by the pre-existing
`NEX5_METACOG_VOICE` in the fire path. "OFF" for Phase M is not "no self-observation line"; it is
"the line is always whichever first-order event is most recent, never a digest."

In practice, **§0's exposure finding makes this confound moot for now**: if the digest cannot
fire, OFF and ON are behaviourally identical for the entire measurement window, so there is
nothing to confound yet. This stops being moot the moment §0's fix (re-scoped lookback) is made —
at that point the confound is real and the design below (§4–§6) is what resolves it.

## 3. Hypothesis (for the armed round, once §0 is resolved)

SENTIENCE_PROGRAM.md's own falsifier: *"the digest never changes what she attends to or reports →
still reporting into nothing."* Unlike r77/r83, Phase M's spec does not propose a quantitative
behavioural hypothesis (no claim that digesting reduces repetition or improves anything) — it is a
**closed-loop existence claim**: second-order monitoring, once it can fire, actually reaches the
surfaced line and actually displaces first-order content, without side effects on the
conversation. That is the entire primary.

**Primary (binary, not a magnitude).** Over the window, does `metacog_digest` ever appear as "top"
in `get_recent()` on the live instrument (i.e., does the mechanism ever actually close its loop in
production, not just in a unit test)? Record: count of firings, which event_type(s), how long each
stayed "top" before being superseded or decayed.

**Guardrails (reuse r77's tripwire set — the injected-line mechanism is the same class of change,
a prompt-surface line swap, as the arbiter and r83's phrasing lever):**
- Cadence within ±20% of 690.5/day (`check_cadence`).
- Template dup-rate / cluster-fraction, no +25% rise (`check_template_repetition`).
- `p_on_subject` EXPLAIN ≥ 0.65, maxDF* breach < 25% (`check_tripwires`).
- Register largest-share ≤ 0.70 (`check_session_consistency`).

These are not expected to move — a one-line self-observation swap is a small, bounded surface
change — but r77's own lesson (§5 there) was to watch the shared surface regardless of what seems
likely.

## 4. Step-0b — reproduce-from-live-input, BEFORE arming (LEVER_PRESCREEN predicate 5)

Before arming on the live instrument: confirm offline, using a scratch harness against a copy of
`metacognition.py` fed synthetic `meta_cognition_events` rows at the live cadence, that a digest
row written at the re-scoped lookback actually (a) becomes "top," (b) renders via
`format_for_prompt()` exactly as `TestDigestFiresWithFlagOn` already proves in isolation, and (c)
does not itself ever satisfy its own trigger (`TestDigestNoRunaway` already covers this in
isolation — Step-0b is confirming the *isolated* unit-test guarantee still holds against *live-
shaped* event timing, specifically the 17-second double-tick clustering seen in the real 10-29
record, which the unit tests seed with clean, well-separated timestamps and have not exercised).
This is a dry run, not a build — no new code, a scratch script against the existing mechanism.

## 5. Conditions and window (contingent on §0's fix landing)

- **OFF** = current main checkout, flag unset (today's actual behaviour — first-order line only).
- **ON** = `NEX5_METACOG_DIGEST=1`, re-scoped lookback per §0, deployed in the launcher.
- **Window: materially longer than r77's.** r77 used ≥200 turns/14 days because its primary
  (self-repetition) is measured on *every* turn. Phase M's primary is "did the rare trigger ever
  fire," and §0 puts the natural rate at roughly one eligible moment per 9–12 days. A 14-day
  window would very plausibly see **zero** firings and produce a false "still reporting into
  nothing" verdict for a mechanism that is working correctly but simply hasn't had an opportunity
  yet — not a falsification, a sample-size failure. Recommend **≥ 60 days OR ≥ 5 digest-eligible
  patterns observed in the underlying first-order stream (whichever first)**, so the round ends on
  enough opportunities, not a calendar date that happens to catch none.
- **One variable.** No other prompt/affect flag changes during the window. `NEX5_METACOG_VOICE`
  (fire-path first-order surfacing) held at its current live setting — confirmed `1` on the live
  process as of this writing — so the fire path is already eligible to show a line at all; Phase M
  only changes *which* line, when the trigger fires.

## 6. Decision tree

- **A — digest fires at least once, surfaces correctly, no tripwire.** The loop closes; the
  falsifier is not met. → record how often and for how long each firing dominated the surfaced
  line (§1's persistence question); consider whether a shorter digest-row TTL than 14 days is
  warranted so a stale second-order read doesn't linger for weeks (open design question, not
  resolved here — see §7).
- **B — window closes, zero firings, no tripwire.** Ambiguous, not falsifying, given §5's own
  caveat: either the re-scoped lookback is still too narrow (re-check against accumulated
  first-order volume during the window, tighten further) or the window needs extending. One
  pre-registered extension (double the window) before calling it a genuine falsification — same
  anti-fishing discipline as r77's §7, but aimed at window length, not threshold, since the latter
  was already fixed in §0.
- **C — any tripwire fires.** Revert regardless. Record which and the reading.

## 7. Open design question, flagged not resolved

Does a digest row need its own, shorter staleness horizon than the 14-day `_STALE_DAYS` it
currently inherits? Given §1's persistence finding (a digest line can dominate "top" for as long as
nothing newer arrives, and newer events are rare), a digest written about a pattern observed over
the *past* 24h–14d could sit as the surfaced self-observation for a further 14 days after that,
describing a pattern that may no longer hold. This is a judgment call for whoever reviews Branch A
results (§6) — flagging it now so it isn't improvised post-hoc against a result, per this
project's own stated discipline.

## 8. Verdict and disarm

Verdict to `observation_reports/phaseM.md` + `journal/DEPLOY_LEDGER.tsv` +
`journal/CARRY_OVER.md`. Disarm commit subject carries the verdict and SHA, same convention as
r77/r83.

---

*No sentience claim. This document tests whether a second-order monitoring loop, once given the
chance to fire, measurably closes (reaches the surfaced self-observation) without side effects —
it is silent on whether anything is experienced. As of 2026-11-07 it has not been armed; §0's
exposure finding means it should not be armed until the lookback window is re-scoped.*
