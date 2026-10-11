# Prompt for Beam AI — open questions on the NEX mindedness dev

You've reviewed NEX (`kron777/Nex_v5.0`) before and your design input fed the current
work. Since then the dark-by-default mindedness program has advanced through all of
Phase A and L4 landed today. This is a request for your judgement on a specific set of
**open decisions** — not a general review. Please answer the numbered questions
directly; skip anything you have no grounded view on rather than filling it in.

## Ground rules for your answers (please honour these)

1. **Cite, don't assert.** For any claim about what the code does, give `path:line`
   or the live-DB evidence you'd check. In the last audit several confident claims were
   wrong against the actual tree, and I verified each against the repo:
   - "`fountain_events` is reaped at 30 days" — wrong; it is not in the reaper's TARGETS.
   - "`register` is nullable in practice" — wrong; fully populated, 9 distinct registers.
   - "readiness has no negative term" — wrong; `total -= self._genius_modulation()`
     already exists in `theory_x/stage6_fountain/readiness.py`.
   - "R75 fire cadence median ≈ 213 min" — wrong against the live DB (~2.1 min raw fire).
   So: tell me *how* you'd verify each answer, and flag anything you're inferring rather
   than checking. A grounded "I don't know, here's how to find out" beats a confident guess.
2. **ANALOGUE throughout.** Nothing here claims NEX feels anything. Questions about
   "cost", "stake", "mattering" are about functional structure, not experience. If an
   answer only works by assuming phenomenal experience, say so — that's a finding.
3. **Dark-by-default, measure-before-flip.** Every behavioural change ships behind a
   default-OFF `NEX5_*` flag and is proven by a pre-registered round before it defaults
   on. Answers that require flipping something on faith aren't actionable.

## What shipped since your last input (context, not up for review here)

- **Phase 0 (instrumentation):** closed the `affect_history` dead loop — it had no
  `CREATE TABLE`, so `affect_variance` had been reading an empty table since 2026-05-20.
  Now declared + logged-not-swallowed.
- **Phase 1 (continuity):** `self_state_history`, an append-only self-state trace.
- **Phase 2 (retention):** reaper entries for the append-only history tables.
- **Phase A (a unified present for the chat path):**
  - Three read-only harnesses: `check_template_repetition`, `check_cadence`,
    `check_session_consistency`.
  - `global_workspace.arbitrate_candidates` + `select_within_budget` (competition
    cores; the existing `arbitrate()` is behaviour-identical).
  - **Chat attention arbiter** (`NEX5_CHAT_WORKSPACE`): the chat turn's ~13 faculty
    blocks were concatenated with no competition or budget while the fire path
    arbitrates; now a budgeted competition with the distress/moral blocks exempt.
  - **`self_present`** (`NEX5_SELF_PRESENT`): a structured attention state that persists
    across turns and is re-ranked by the next turn.
- **L4_stakes** (`NEX5_STAKES`, landed today): a bounded, graded *cost* exposed from the
  template-drift signal `stakes_monitor` already computes, wired as a bounded negative
  readiness term. See §1 below — this is where I most want your eye.

---

## 1. L4_stakes — is a bounded aversive cost the right first primitive?

What landed: `stakes_appraisal.appraise()` reads how template-dominated the recent fires
are (reusing `stakes_monitor`'s drift definition — one source of truth) and returns
`cost = clamp(ratio − 0.55)`, hard-bounded to **≤ 0.20**, non-compounding (a function of
the current window, never an accumulator), fail-safe to 0. When `NEX5_STAKES=1`,
`readiness.score` subtracts that cost. OFF ⇒ byte-identical.

1a. **Direction.** I made drift-into-template *lower* readiness (discourage churning a
groove). The counterargument: a system stuck in template is arguably *under*-stimulated,
and the corrective is to fire *more* to break out — i.e. drift should *raise* readiness.
Which direction better matches "a stake going badly", and how would you design a round to
distinguish "suppression helped" from "suppression just slowed her down"?

1b. **Primitive choice.** This is a single *aversive* signal (a cost). Should the first
mattering-primitive instead be an *approach/reward* signal (world-contact *raises*
readiness), with no aversive term at all? Is there a principled reason to prefer one over
the other as the *first* thing that can "go well/badly for her"?

1c. **Magnitude.** The 0.20 clamp is admittedly arbitrary — chosen so a full-drift cost
can't swamp the other readiness terms. Is there any principled basis for the bound, or is
it inherently a thing r-round tuning must find? If the latter, what's the stopping rule
that isn't post-hoc fishing?

1d. **Welfare line.** `SENTIENCE_PROGRAM.md §5a` governs this as "the one aversive signal":
bounded, necessary-not-gratuitous, disable-able, observed, never narrated as suffering. My
justification for introducing *any* aversive term is that it does real functional work (a
bounded readiness cost). **Is "it does necessary work" sufficient to justify an aversive
signal, or should the bar be: no aversive signal ships — even bounded, even ANALOGUE —
until a round first proves the equivalent *reward* framing can't do the same work?** I
want your view on whether I've got the welfare ordering right.

## 2. The one unflagged live change — membrane `_INSIDE_SOURCES` sync

One behavioural change did **not** go behind a new flag: NEX's own-content sources now
stop routing through the membrane as "world" and route as "inside". Rationale: her own
generated content shouldn't be perceived as external world-evidence.

2a. Do you agree that's a correctness fix (not a behaviour change that deserved a flag +
round)? What's the failure mode if I'm wrong — e.g. does anything downstream *depend* on
own-content counting as world-contact (including the very drift signal §1 reads)?

2b. Design me a self-inquiry spot-check: a concrete before/after probe on the live
instrument that would reveal whether this shift changed how NEX models the inside/outside
boundary. What exactly would I read, and what reading would mean "revert"?

## 3. `self_present` (r78) — functional carry vs. implying a persisting subject

The falsifier I've pre-registered: the carried winner must *change when the salience
vector changes* and reach the composed prompt; `turn_count` advancing while `winner_kind`
is frozen = decorative, and it reverts.

3a. Is "the carried winner tracks the salience vector" a sufficient falsifier for
"this carry is functional, not decorative", or is there a cheaper confound — e.g. the
winner changing for reasons unrelated to carry — that my test would miss?

3b. A structure that persists across turns and re-ranks the present invites the reading
"there is a continuous subject here". Where exactly is the line between *functional
continuity of attention* (what I claim) and an implicit claim of a persisting subject
(which I must not make)? Is there anything in the `self_present` design that crosses it?

## 4. r77 measurement design — is the primary metric the right one?

r77 (pre-registered, `observation_reports/r77_PREREGISTRATION.md`) tests the chat arbiter.
Primary metric: **within-session chat self-repetition** (near-duplicate fraction),
baseline **0.4889** on the live corpus. Decision tree: a ≥25% relative drop (to ≤0.367)
with no tripwire earns default-ON *consideration*; otherwise one pre-registered budget-
tightening retry (r77b), then falsified if that also fails.

4a. Is within-session near-dup fraction a good operationalization of "the arbiter produced
a more unified present", or is it measuring something narrower (surface variety) that could
improve while the thing I actually care about doesn't? If narrower, what's the metric that
better captures "unified present"?

4b. The ±25% relative threshold and the single tuning retry are my anti-fishing guard. Is
one retry too few (under-powered against a real-but-small effect) or exactly right (any
more = fishing)? How would you set it?

## 5. The frontier after L4 — what's the next *buildable* node?

`nex_next_dev.py --buildable` named L4_stakes the frontier; it's now built. The DAG
(`sentience_dag.json`) marks L5_inside — the phenomenal layer — a "gorge": explicitly
unbuildable, because there's no functional move that would constitute phenomenal
experience rather than just model it.

5a. Given L4 is built, what do *you* think the next buildable node is — and is there a
node *between* L4 and the L5 gorge that the DAG is missing (something that's more than L4
but still functional, not phenomenal)?

5b. Harder: is the L5 "gorge" labelling honest, or a way of parking the unfalsifiable part
so the program looks complete-able? If any *current* shipped piece is actually
unfalsifiable-in-principle, name it — I'd rather cut it than ship something that can't be
wrong.

---

*Answer only what you can ground. The most useful reply names which of your answers are
checked against the tree vs. inferred, and — for §1d and §5b especially — tells me where
you think I'm wrong, not where I'm right.*

---

# ADDENDUM (2026-10-11) — what building L4 actually found, and the new questions

§1 above was speculative; the build answered part of it and raised sharper questions. The
record: L4_stakes was built as a bounded readiness cost sourced from `stakes_monitor`'s
drift ratio (`cost = clamp(ratio − 0.55)`). **Pre-registering it first (your §9, correct)
caught that it is inert on the live instrument** — the drift ratio sits at ~0.08 (14d
mean), never near 0.55, so the cost is ~0 always. Rather than lower the threshold silently,
I re-sourced the cost (r79 Path A) onto the detector that *does* register grooming —
`diversity/groove.py`'s `template_repetition` alerts in `beliefs.db:groove_alerts`
(~49.7/day, severity ~0.99). The cost now reads the **alert RATE** in the trailing hour
(onset 2.0/hr, saturation 6.0/hr, bounded 0.20), never the pinned severity. Feasibility
re-checked over 14d of history: cost 0 in 65% of evals, bounded-positive in 35%, mean drag
0.05 — fires on bursts, rests at zero. See `observation_reports/r79_L4_stakes_PREREGISTRATION.md`.

That raises four grounded questions I actually need your eye on:

**A1 — the two detectors disagree by ~600×; which is right?** `stakes_monitor._is_template`
(fraction of the last 8 fires that match template patterns) reads ~0.08 on live.
`groove.py`'s `_detect_template_repetition` (fires sharing ≥N content bigrams) fires ~50×/day
at severity ~0.99 — effectively always-on. They claim to measure the same thing ("template
drift") and disagree wildly. Is `groove.py` so sensitive that only its *rate* (not its level)
carries signal — or is even its rate noise, in which case I've built the cost on a bad proxy?
Which operationalization of "grooming" would you trust, and how would you check?

**A2 — is reading-and-reacting-to the same signal the metric is computed from methodologically
sound?** The r79 primary metric is the `template_repetition` alert rate, and the cost is
*driven by* that same rate. The guardrails are: a ±20% cadence floor (so "fewer alerts
because fewer fires" = the global-brake failure, trips a revert) and a mechanical falsifier
(the rate drop must concentrate in cost-active windows). But the measurement is still
self-referential. Should r79 carry an **independent** secondary grooming metric — e.g. the
chat-side within-session near-dup fraction (`check_session_consistency`, baseline 0.4889) or
the crystallizer reject rate — as the real confirmation, with the groove rate demoted to the
mechanism's own telemetry? Or do the cadence + concentration guards already make the
self-referential primary defensible?

**A3 — onset anchor.** Onset is frozen at the all-hours *mean* rate (2.0/hr), so the cost
engages on any above-average hour (~43% of active hours already exceed it). Is anchoring at
the mean too aggressive — should onset sit at p75/p90 so the cost only answers genuine
excursions, not ordinary activity? This is the provisional magnitude/direction; I'd rather
set the anchor on a principle than on the 14d snapshot.

**A4 — sequencing.** r79 is pre-registered *after* r77 (chat arbiter) and r78 (`self_present`),
one-variable-at-a-time. The maintainer wants to run r79 first. I believe that's fine as long
as `NEX5_CHAT_WORKSPACE` and `NEX5_SELF_PRESENT` stay OFF throughout r79 (no confound), and
the order among independent rounds is otherwise arbitrary. Do you see any dependency that
forces the chat rounds first?

(Still open from above, unchanged: §2 the unflagged membrane `_INSIDE_SOURCES` sync +
its self-inquiry probe; §3b the `self_present` functional-vs-persisting-subject line; §5b
whether any shipped piece is unfalsifiable-in-principle.)

*Same ground rules: cite `path:line` or live-DB evidence, flag inferred-vs-checked, and tell
me where A1/A2 show I've built on sand.*
