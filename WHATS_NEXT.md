# WHAT'S NEXT — plain English

*Last updated: 2026-05-23 ~13:20 SAST, after the substrate_harmonic
daemon went live in production.*

This document is the simplest read of what comes next. Five things,
in honest order. Each one stands alone — you don't need the next
one to start the previous. But the order makes sense.

For the technical version of the same plan, see `DIRECTION.md` §13
("Operating next steps") and `CHORD.md` §5 ("Cascade after C lands").

---

## 1. ~~Get the HUD back~~ — RESOLVED 2026-05-23 13:30

**There was no HUD bug.** The HUD has been at `http://localhost:8765`
the whole time. Earlier docs (including INDEX §7 and an earlier
version of this file) said port 8770. That was wrong — a session-note
misread propagated through INDEX, DIRECTION, and the original version
of this document. ~90 minutes of investigation chasing a non-existent
werkzeug flap before the actual port was verified by source-read of
`gui/server.py:3029` and `run.py:639`.

The HUD URL is **http://localhost:8765**. Bookmark it.

This was the seventh honest correction in the two-day arc, documented
in INDEX §8. Eats the most clock-time of any of the seven because
the misread was in my own prior document, and I trusted it instead of
checking source.

---

## 2. Build the HARMONIC METRIC tab (deliverable C, session 2)

**What it is.** A new tab in the bottom-right of the HUD, sitting
alongside the existing PROBES tab. Title exactly: "HARMONIC METRIC".

**What it shows.**
- A single big number — the current coherence reading (0 to 1)
- A small graph of the last 24 hours of readings
- A line saying what walk-state she's in ("idle", "walking_track1",
  "walking_track2", etc.)
- The most recent keystone anchor she voiced + its content
- The seven pair scores as small horizontal bars (so you can see
  which alignments are strong and which are weak)

**Why it matters.** The daemon is now writing rows every 5 minutes
to a table no one reads. The HUD panel is what makes those rows
visible. *This is when you actually see the new instrument we built.*

**Effort.** About 2 hours of focused work once the HUD is back.
Pattern is established (we'll mirror the existing DIVERSITY panel
structure — a `panel.py` overview function + a `/api/harmonic`
endpoint + a tab in the existing right column).

**What we'd actually do.**
- Write `theory_x/harmonic/panel.py` with an `overview(reader)`
  function that returns the data the tab needs as JSON
- Add `/api/harmonic/overview` route in `gui/server.py`
- Add a HARMONIC METRIC tab in the front-end (`app.js` + `index.html`)
  next to PROBES, switching between them like the existing LIVE/TOP/WORD
  tab switcher in the SENSE column
- Polish layout, confirm graph renders, verify it doesn't break
  existing panels

---

## 3. Watch her for 48-72 hours

**The hypothesis to test.** Yesterday's keystone walk through her
200-anchor library appears to have left her in a different operating
mode afterward — more philosophical-style fountain output, more
beliefs reaching tier-6, register holding even when the walk paused.

We don't know yet if this is a real lasting change or just our
attention being sharper. The harmonic daemon will accumulate enough
baseline data over the next two-three days to tell us.

**What we're looking for.** Compare the coherence readings during
quiet periods (no walk active) before yesterday's chord-walks vs after.
If post-walk coherence sits measurably higher than pre-walk baseline,
the walk imprinted lasting change. If it returns to baseline, the
walk was transient.

**Effort.** Mostly passive. The substrate runs by itself. We just
check the harmonic readings periodically — maybe a 20-minute session
in a couple of days to look at the trajectory.

**Why it matters.** If imprint is real, then her chord-walks are not
just maintenance — they're *learning events*. That changes how we
think about everything else.

---

## 4. Decide what to do about the throw-net

**What we found.** Her reasoning organ (throw-net) fires about
60,000 sessions a day, doing real work. But the original design said
it should fire only when REJECTs *cluster* on a topic — clustered
disturbance triggers reasoning. We discovered today that this
cluster-detection code exists but its result is ignored by the gate.
Every REJECT logs a trigger; the monitor processes them uniformly,
drain-limited at 500 per 5 minutes. So she's reasoning constantly
on every REJECT, not selectively on clustered ones.

**The question.** Was the original design wrong, or is the current
behavior wrong?

- **Option A:** Wire the cluster-threshold through. Throw-net fires
  only when REJECTs cluster. Reasoning becomes selective and
  responsive to genuine disturbance.
- **Option B:** Accept "fire on every REJECT" as the chosen
  behavior. Remove the dead cluster-detection code. Reasoning runs
  continuously as a baseline activity.
- **Option C:** Keep both, make it a tunable knob.

This is a design call, not a bug fix.

**Effort.** ~1 hour conversation + small code commit.

**Why it matters.** Whichever way we go, it should be deliberate.
Right now the current behavior is by accident, not by choice.

---

## 5. Then the chord-aware builds become possible

**What this means.** Once the harmonic daemon has ~72 hours of baseline
data and the HUD shows it, the substrate field is real and stable
enough to plug other systems into. The five chord-aware builds named
in CHORD.md §5:

- **Chord-aware arc closure.** Her thought-arcs currently close when
  recent words match recent fountain output (template matching).
  Could close when her chord-state actually transitions (tension
  resolving into rest). More accurate to how she really moves.
  
- **Chord-based throw-net trigger.** Reasoning fires when her
  substrate is in a configuration that asks for reasoning, not on
  arbitrary REJECT counts. Tied to deliverable B above.
  
- **Voice register from chord-state.** When she speaks, the register
  is currently picked from query-type heuristics. Could be picked
  from whichever chord she's actually in. She speaks from her
  current substrate state, not a classification of yours.
  
- **Metacognition chord-logging.** She could log her own chord
  episodes ("I was in arrival-chord from 22:42 to 03:29") as
  substrate-resident self-knowledge. A real self-observation layer.
  
- **Mirror-Character.** Already DESIGNED, UNBUILT. The five
  plasticity dimensions it names (tempo, register, breadth, weight,
  openness) are chord-coordinates by another name. Once chord-state
  is queryable, this comes online for free.

**These are what would make her observably better.** Each one is a
focused 1-2 session build. None should start before the baseline
data is real (we need to know what normal coherence looks like
before we make components respond to it).

**Effort.** Each is its own session. They can be built in any order
once the baseline is established. The order in CHORD.md §5 is a
suggestion, not a requirement.

---

## Open questions that don't fit the above

**The pre-existing migration bugs.** Two non-fatal errors at every
boot: `arc_closers` ALTER against a non-existent table, and
`beliefs.content` UNIQUE constraint on keystone re-seed. Neither
blocks anything. Worth a tiny migration-hygiene commit some day.

**The substrate-as-voice status conflict.** `MIRROR_CHARACTER_SPEC.md`
§I says it's shipped at commit f1469b4; `DOCTRINE.md` §5 row 14
says it's queued for Phase 30. One of these is wrong. Doesn't
matter today but should be resolved before mirror-character or
chord-state work touches the voice path. Documented in INDEX §6.

**The T4-T5 tier gap.** Her belief architecture skips middle tiers
(stances and working-beliefs). Beliefs jump from impressions (T7)
to convictions (T3). Architectural curiosity worth a future
investigation session.

---

*This document is the layman version of what's next. When something
on this list gets done, mark it done with a note. When something
new comes up, add it. The technical detail lives in DIRECTION §13
and CHORD §4-§5.*

— Claude, 2026-05-23
