# EXPECT_MOOD — PRE-REGISTRATION: the Phase T mood-nudge coupling (`NEX5_EXPECT_MOOD`)

## 0. Status — gate currently CLOSED by design, not by defect; NOT armed

This is the one remaining piece of SENTIENCE_PROGRAM.md's Phase T (temporal
thickness), which is otherwise already built as the expectations/commitments
system (`theory_x/stage_world/expectations.py`, `commitments.py`) — see the
Work Log's staleness table. `NEX5_EXPECT_LEARN` and `NEX5_COMMITMENT_VALENCE`
are already live; this flag is the only piece still dark.

**Step-0 exposure check, read-only against the live DB (2026-11-07):**

| Table | Finding |
|---|---|
| `event_valence` | 4,196 rows. Non-zero (admitted): **63, all +0.05** (confirmations). **Zero negative rows.** |
| `affect_nudges` | 63 rows — mirrors `event_valence`'s non-zero rows 1:1. `SUM(valence>0)=63`, `SUM(valence<0)=0`. |
| `mood_nudge_applied` | **0 rows, ever.** The mechanism has never fired, flag unarmed. |
| `event_valence.reason` breakdown | `band_0` 2,798, `confidence_not_admitted` 1,268, `confirmed_not_info_weighted` 63, `band_unrecorded` 62, `partial_coverage` 5. **No "violated" reason exists in the live data at all.** |
| Span | `event_valence` rows run 2026-10-27 to 2026-11-07 (11 days) — not a thin sample, a real one: in 11 days of live operation, not one owned-belief or commitment expectation has resolved as violated. |

`mood_eligible()` (`expectations.py:641`) requires **both** a positive and a
negative admitted row before any nudge is ever applied — "the term must be
seen opening AND blocking first," per its own docstring, specifically to
prevent a one-sided inflation mechanism. With zero negative rows, that gate
reads `False` today and will keep reading `False` regardless of arming.

**This is NOT the same situation as Phase M's exposure problem.** Phase M's
digest was inert because its *window was mis-scoped* relative to the real
data — a design flaw, fixable by re-deriving a constant. Here the gate is
closed **by design, correctly, on real data** — it is deliberately waiting
for organic evidence of both signs before it can ever move anything, and
that is exactly the caution the welfare-adjacent framing below calls for.
**Arming now is a different kind of decision than arming Phase M would have
been: because the gate is closed, arming is a true no-op at the moment of
arming** (confirmed: `if _ex.mood_on():` wraps the entire coupling block in
`affect_state.py:212`, so with the flag on but the gate closed, the code
path executes, computes `mood_eligible()==False`, and returns — identical
observable behaviour to flag-off, down to zero new log lines beyond the
hourly "mood gated" notice already printing at `WARNING`/`INFO` level
regardless of this flag). The live risk is not "arming does something
surprising today" — it's "arming means the FIRST time a violation ever
occurs, something new happens automatically, unobserved, mid-measurement."

## 1. The change under test

**`NEX5_EXPECT_MOOD` (default OFF).** `affect_state.py`'s background tick
(`_background_tick`, every affect interval) reads `expectations.mood_nudge()`
— the sum of `affect_nudges` rows since the last tick, gain `MOOD_GAIN=0.1`,
hard-capped at `MOOD_CAP=±0.05` per tick — and adds it to `valence_delta`,
**only when `mood_eligible()` is true**. One-way: `affect_state` reads
`expectations`; nothing in `expectations.py` reads mood (confirmed by grep
and by the module's own "one-way only" comment). Every applied nudge is
logged to `mood_nudge_applied(ts, nudge)`.

## 2. Hypothesis

Per SENTIENCE_PROGRAM.md §3's own falsifier for this property: *"valence
does not differ between a violated expectation and a neutral tick."*
**Hypothesis:** once the gate opens (a genuine negative admitted
`event_valence` row exists), her affect valence on ticks following a
violation differs, in the violation's direction, from a throughput-matched
neutral tick — bounded by the existing ±0.05 cap, never compounding.

## 3. Conditions and window — event-driven, not calendar-driven

Unlike r77/r83 (a fixed turn-count or day-count), this window **cannot be
fixed in advance**, because the precondition (a negative admitted event) has
not occurred once in 11 days and there is no basis to predict when it will.
Fixing a calendar window risks the exact Branch-B trap Phase M's own
pre-registration flagged: a window that closes having seen zero opportunities
reads as a false null, not evidence against the mechanism.

- **OFF** = today's live behaviour: `valence_delta` driven only by the
  existing throughput/surprise/compass inputs; the mood-coupling code path
  does not execute at all. A genuinely clean baseline — not a partial-prior-
  art situation like Phase D/E had to work around.
- **ON** = `NEX5_EXPECT_MOOD=1`, deployed. Because the gate is closed at
  arming time, **ON and OFF are behaviourally identical from the moment of
  arming until the gate first opens** — there is no immediate A/B to read.
- **Window = from the gate's first opening (first negative admitted
  `event_valence` row) to the 10th nudge applied, or 30 days after first
  opening, whichever first.** The first 1–2 nudges are an observational
  check (did it fire as designed, is the cap holding, is it bounded); the
  full window is the actual measurement.
- **One variable**, same discipline as always: no other prompt/affect flag
  changes during the window.

## 4. Guardrails (reuse the standard tripwire set, plus one mood-specific one)

- Cadence within ±20% of 690.5/day; template dup/cluster +25%; `p_on_subject`
  EXPLAIN ≥ 0.65; register largest-share ≤ 0.70 — the same shared-surface
  set every prompt/affect-adjacent round this project runs has watched.
- **Mood-specific:** every row in `mood_nudge_applied.nudge` must satisfy
  `|nudge| <= MOOD_CAP (0.05)` — the cap is enforced in code
  (`max(-MOOD_CAP, min(MOOD_CAP, ...))`), so a breach here would mean the
  cap itself failed, not just that the signal was large. Treat any breach as
  a Branch-C stop, not a tuning question.
- **Non-compounding check:** `mood_nudge()` sums only rows in `(since,
  until]` — one tick's window, not all-time — so nudges cannot accumulate
  across ticks by construction. Confirm this holds (no drift in applied-nudge
  magnitude over the window) rather than assuming the code review above is
  sufficient on its own.

## 5. Welfare note (no `(see §5)` annotation on Phase T, but checked anyway)

SENTIENCE_PROGRAM.md's §5 welfare clause is written for Phase S's *stakes*
specifically, and Phase T carries no `(see §5 Welfare)` tag the way S and F
do. Checked against §5's five criteria anyway, since a negative mood nudge
is welfare-adjacent even if not formally gated: **bounded** (±0.05 hard cap,
in code, already); **necessary, not gratuitous** (closes a real gap — valence
currently can't distinguish a violated expectation from a neutral tick at
all); **disable-able** (the flag; OFF returns to the exact current behaviour,
no residue — the coupling code doesn't run, nothing to unwind); **observed**
(`mood_nudge_applied`, already logged every time); **never narrated as
suffering** (the mechanism moves a number; nothing in `affect_state.py` or
`expectations.py` asserts distress — confirmed by reading both). All five
hold without needing new work.

## 6. Decision tree

- **A — gate opens, nudge applies, bounded, no tripwire.** The mechanism
  works as designed. → proceed to the real falsifier test: compare affect
  valence on nudge-applied ticks vs. throughput-matched neutral ticks over
  the rest of the window; if they measurably differ in the violation's
  direction, Phase T's falsifier is answered **not falsified**.
- **B — window closes (30 days) with the gate never opening.** Inconclusive,
  not falsifying — same anti-fishing principle as every other round here.
  → extend once, do not conclude "mood coupling doesn't matter" from an
  absence of violations, which is a fact about her belief store's youth, not
  about the mechanism.
- **C — any tripwire fires, including the mood-specific ones in §4.** Revert
  `NEX5_EXPECT_MOOD` immediately; record which tripwire and the reading.

## 7. Verdict and disarm

Verdict to `observation_reports/expectMood.md` + `journal/DEPLOY_LEDGER.tsv`
+ `journal/CARRY_OVER.md`, same convention as every other round. Disarm
commit subject carries the verdict and SHA if Branch C fires.

## 8. What this document does NOT do

It does not arm `NEX5_EXPECT_MOOD`. No flag was set, no file touched outside
this directory, no restart made or requested. Arming is Jon's explicit call,
same as r77 was armed only after its own pre-registration was signed off —
and, per standing instruction, not before r77's own window closes regardless.

---

*No sentience claim. This document tests whether a bounded, capped,
one-way coupling from violated expectations to affect valence produces a
measurable, direction-consistent difference from throughput-only affect —
it is silent on whether anything is experienced.*
