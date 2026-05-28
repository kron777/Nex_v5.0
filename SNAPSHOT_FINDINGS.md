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
