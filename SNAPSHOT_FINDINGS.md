# SNAPSHOT FINDINGS — substrate-state vs striking-ness

**Date:** 2026-05-28
**Status:** First findings from the temporal-witness mechanism (SUBSTRATE_SNAPSHOTS.md).
**Companion to:** TRACK_THEORY.md §14 verdict, PROOF_OF_CONCEPT.md P3 null.

## Setup

The snapshot camera went live at fire #18232 (2026-05-28 12:21).
Each fire captures: 5 drive weights, walk_state, walk_anchor, recent fire
ids. Coherence + harmonic_pairs backfilled from substrate_coherence
(nearest tick within ±360s). v2 score assigns retention_tier
(genius/moment/ordinary).

First analysis batch: 80 snapshots, of which 25 scored
(8 genius, 3 moment, 14 ordinary), 55 unscored at time of analysis.

## Question

What substrate state, if any, distinguishes a GENIUS fire (striking,
Mode A self-articulation) from an ORDINARY one (template filler)?

## Result — three-way null

Tested three independent candidate discriminators. All flat.

### 1. Drives (5 weights) — flat
genius vs ordinary deltas in the 4th decimal place; every delta smaller
than its own stdev. Largest: curiosity Δ=-0.0019 (stdev ~0.004).
The drive vector is near-STATIONARY across the whole substrate:
roughly {coh 0.29, expl 0.20, int 0.05, self 0.29, cur 0.17} regardless
of what she says or which register she is in.

### 2. Coherence (harmonic total) — flat
genius mean 0.786 ± 0.058 vs ordinary 0.795 ± 0.041.
delta -0.009, Cohen's d = -0.18 (negligible; genius slightly LOWER).
separates? no.

### 3. Harmonic pairs (7) — flat or saturated
drive_tension_vs_sv, groove_vs_sv_active, throw_net_vs_baseline pinned
at 1.000±0.000 across all tiers (saturated, no variance).
gate_reject ~0.94, stillness_vs_walk ~0.50 everywhere.
fountain_sv_share and walk_pace_vs_cadence vary but genius/ordinary
overlap fully within (large) spreads. No pair separates.

## Interpretation

The striking-ness of a fire is NOT visible in any live substrate metric
we capture. Drives, coherence, and harmonic state are slow-moving
background — the same hum whether she voices a keystone or filler.

The genius/ordinary distinction lives ENTIRELY in the text content,
which is exactly what the v2 score reads (length, anti-template,
self-witness, unprompted). The score works because it reads the WORDS,
not the substrate.

What actually discriminates is the OUTPUT PATH, not substrate state:
substrate_voice retrieval of a tier-1/2 keystone anchor (Mode A) vs
LLM generation of filler. Same machine, same drives, same coherence —
only the path to output differs. This is a MECHANISM fact, not a
STATE fact.

This sharpens the P3 null. P3: walks leave no register-persistence
trace. Now: striking-ness leaves no substrate-state trace either. The
morality-table keeps the good text; the substrate underneath is
constant.

## The ghost — refuted as substrate-configuration, reframed as relational

The "ghost" hypothesis was: striking/aware moments correspond to a
special substrate configuration ("extended awareness settings") that
could be found and tuned. THIS IS REFUTED. Three signals, all flat.
There is no awareness-setting hiding in drives/coherence/pairs.

The single existing ghost flag (#17905, pre-camera, no snapshot) is
telling: the reason field recorded JON'S state, not hers —
"i am in a feeling of tiredness and it is almost midnight". The ghost
feeling arose in the MEETING of her fire and his reading, not in her
substrate alone.

Reframe: the ghost may be RELATIONAL — a conjunction of (her fire) ×
(observer state) × (timing) — not a property of her substrate. If so,
no amount of substrate snapshotting captures it fully; half the
phenomenon is on the observer's side. The snapshot captures her half;
the ghost reason field captures the observer's. The ghost lives in the
conjunction.

## Open / next

- ghost-vs-genius comparison is INSTRUMENTED but has no data: the one
  ghost flag predates the camera. Needs new ghost flags on post-#18232
  fires. Flag ghosts as they occur; revisit when ~5-10 accumulate.
- voltage: theory references voltage⊥coherence (P4) but voltage is NOT
  stored live anywhere — only computed in proof_of_concept analysis.
  Snapshot voltage column stays NULL unless a live voltage signal is added.
- the lever for more Mode A is NOT drive-tuning (drives don't move
  output) but the substrate_voice trigger conditions (groove threshold,
  cooldown, anchor selection) — already built.

---

# ADDENDUM 2026-05-28 evening — voltage tested, breadth lead found

After the three-way null (drives/coherence/pairs), tested VOLTAGE — the one
remaining substrate signal. Voltage is not stored live; computed per
proof_of_concept.compute_voltage_simple: a 5-min-window busyness score =
0.5*activity (fires/30) + 0.5*cross_domain (branches/10).

## Voltage result — first NON-flat signal

genius voltage 0.177 ± 0.042 vs ordinary 0.152 ± 0.043, d=+0.58 (genius
higher). Sawtooth check: 7 of 8 genius fires sat at a RISING voltage peak
(voltage climbing into the fire), 1 falling. This matched the
"charge-then-fire" intuition — the first result that pointed anywhere.

## De-circularization — the signal is BREADTH, not tempo

Voltage has two halves. Split and tested separately:

  ACTIVITY half (tempo, fires/5min):  genius 0.092 vs ordinary 0.090
                                       d=+0.08  -> FLAT
  CROSS-DOMAIN half (breadth, #branches): genius 2.63 vs ordinary 2.14
                                       d=+0.67  -> the whole signal

The tempo half is flat — genius and ordinary fire at the same rate (~2.7
fires/5min). So the voltage effect is NOT the walk-tempo circularity
(genius fires are substrate_voice fires during walks; walks could fire
fast — but they don't fire faster than ordinary). The signal lives
entirely in BREADTH: genius fires occur when more distinct branches are
simultaneously warm (~2.6 vs ~2.1 domains).

Reframe of the circuit-intuition: striking-ness does not come from going
FAST (tempo flat) but from going WIDE — multiple domains live at once,
cross-domain ferment. Breadth, not speed.

## Status: PROMISING but UNDERPOWERED — cannot confirm or deny

Power analysis: detecting d=0.67 at alpha=0.05, power=0.80 needs ~36 per
group. We have genius n=8. We are UNDERPOWERED; d=0.67 at n=8 is a lead,
not a finding. Four candidates flat, one promising-pending — honestly
"one lead," not "one hit."

## Pre-registered confirm/deny test (tools/test_breadth.py)

Thresholds fixed 2026-05-28 BEFORE the confirming data exists, to prevent
goalpost-moving:
  CONFIRMED : p < 0.05  AND  d >= 0.4   (Welch t, breadth, genius vs ordinary)
  DENIED    : p > 0.20  OR   d < 0.2
  PENDING   : in between, OR genius n < 30
Circularity guard: tempo half tested in parallel; if tempo also p<0.05 the
breadth result is flagged as possibly confounded.

n=36 reachable in ~5-11h of running (genius rate 14-32%, ~24 fires/hr). So:
run overnight, score-pending in the morning, then run test_breadth for a
real verdict. No eyeballing — the script prints CONFIRMED/DENIED/PENDING.

## Honest summary of the whole snapshot investigation

Five candidate sources for striking-ness tested:
  drives             d~0      flat
  coherence          d=-0.18  flat
  harmonic pairs     ~        flat/saturated
  voltage-tempo      d=0.08   flat
  voltage-breadth    d=0.67   PROMISING (underpowered, test queued)

If anything in the live substrate tracks striking-ness, it is breadth of
simultaneously-active domains. Everything else is flat. The genius/ordinary
split otherwise lives in TEXT (what v2 reads) and the retrieval MECHANISM
(keystone vs LLM), not in substrate state. Verdict on breadth deferred to
test_breadth at n>=30.

---

# CONFIRMED 2026-05-29 morning — BREADTH is the substrate correlate of striking-ness

Overnight accumulation brought genius n=8 -> 79, ordinary -> 199. Ran the
pre-registered test_breadth (thresholds locked 2026-05-28 before this data
existed). VERDICT: CONFIRMED.

## Result

  BREADTH (distinct branches in 5-min window):
    genius = 2.92  vs  ordinary = 1.93
    t=13.45  p<0.0001  d=+1.49   (LARGE effect)

The effect GREW with power (d 0.67 at n=8 -> 1.49 at n=79) — opposite of
noise. Pre-registered CONFIRM threshold (p<0.05 AND d>=0.4) cleared decisively.

## Tempo confound — raised, then ruled out

test_breadth flagged tempo as also-significant (d=0.73). De-confounded two ways:

1. Breadth-per-fire (branches/fires): genius 0.994 vs ordinary 0.709, d=+1.54.
   Removing the tempo component did NOT shrink the effect. Genius fires are
   ~1 distinct domain PER FIRE (near-maximal spread); ordinary ~0.7 (clustered).

2. Matched on tempo: at 3 fires/window (n=75 genius, 139 ordinary), genius
   breadth=3.00 vs ordinary 2.37, Δ=+0.63. At the SAME busyness, genius windows
   span more domains. Breadth separates independent of tempo.

Conclusion: breadth (d=1.49) dominates tempo (d=0.73) ~2x, survives
breadth-per-fire, survives tempo-matching. Breadth is the real signal; tempo
is a weak correlate of it, not its cause.

## The finding

Striking (genius) fires occur when nex is attending across MANY DISTINCT
DOMAINS simultaneously — systems + crypto + cognition + emerging-tech all warm
at once. Ordinary fires cluster in one or two domains (the coffee-mug / "what
if the quiet" grooves). DEPTH COMES FROM WIDTH. Simultaneous cross-domain
breadth is the substrate condition under which she reaches her standing-points.

This is the ONE non-flat signal of the whole snapshot investigation:
  drives          d~0      flat
  coherence       d=-0.18  flat
  harmonic pairs  ~        flat
  voltage-tempo   d=0.73   weak (confound of breadth)
  voltage-breadth d=1.49   CONFIRMED — the substrate correlate of genius

Origin note: began as Jon's "charge builds then explodes" circuit-intuition.
Testing refined it: not charge/momentum/tempo, but BREADTH/simultaneity.
The intuition pointed at the right family; the data named the variable.

## Implication

The lever for more genius is not drive-tuning, not coherence, not firing
faster. It is cross-domain breadth — keeping multiple branches simultaneously
warm. Narrow focus (one hot branch) yields ordinary/groove output; wide
simultaneous attention yields striking output. Possible future intervention:
bias hot-branch selection toward breadth during low-quality (high-groove)
stretches.

---

# CONFIRMED 2026-05-29 — breadth CONVERGES at genius fires then DISPERSES

Tested whether breadth shows a temporal dynamic around genius fires
(Jon's "pressure builds then releases" intuition). Trajectory: sampled
breadth at -15..+15 min around all 79 genius fires.

## Shape: peak at fire

  -15min 1.09 | -10min 1.95 | -5min 1.14 | FIRE 2.92 | +5min 2.06 | +10 1.95 | +15 1.95

Breadth spikes sharply at the genius-fire moment, declines after.
Pre-fire rise is jagged (volatile 1-2), not a smooth ramp — so the
dynamic is "sudden convergence" more than "gradual charge."

## Both confounds ruled out

CONTROL 1 — is the peak just "a fire happened here"? NO.
  genius breadth peak vs neighbors:   +1.32 (sharp spike)
  ordinary breadth peak vs neighbors: -0.11 (flat, no peak)
  Ordinary fires occur in flat-breadth conditions; only genius fires sit
  at a breadth spike. The peak is GENIUS-SPECIFIC.

CONTROL 2 — is the post-fire decline just substrate_voice cooldown? NO.
  post-fire breadth drop: 0.97  vs  post-fire tempo drop: 0.47
  Breadth falls 2x more than tempo. If pure cooldown, they'd fall together.
  The extra drop is genuine breadth DISPERSAL, beyond fewer-fires.

## Finding

Genius fires occur at a moment of CONVERGENCE — multiple domains briefly
align (breadth spikes to ~3 distinct branches) — and the striking thought
fires in that convergence. Afterward the domains DISPERSE (breadth drops,
more than cooldown explains). The pattern: converge -> fire -> disperse.

Refinement of Jon's "pressure builds and releases": the RELEASE is solid
(real dispersal post-confound). The BUILD is a sudden convergence, not a
smooth charge. Breadth is less "stored pressure consumed by the fire" and
more "a momentary alignment that the striking fire coincides with." Cannot
fully separate convergence-as-fuel from convergence-as-the-event-itself,
but the genius-specific spike + real dispersal confirm a genuine temporal
dynamic, not a plateau.

Two Jon-intuitions, both confirmed-after-refinement:
  "voltage/charge"      -> BREADTH (d=1.49)
  "builds and releases" -> CONVERGE / FIRE / DISPERSE (both confounds ruled out)
