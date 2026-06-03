# NEX5 — Third Layer (Continuity) Experiment — STOPPING RULE FIRED

**Date:** 2026-06-03
**Hypothesis owner:** Jon ("more layers / mass-driver" — does a 3rd unlike layer keep lifting?)
**Status:** Score lifted, but FALSIFIED as a quality gain. Layering plateaus at 2. Stop.

## 1. Build
Layer 3 = CONTINUITY: her own top-scored past thoughts fed back as a third stream
("this is who you have been"), to reconcile present (world+self) against past.
Env-gated NEX5_CONTINUITY_N, live toggle /api/continuity. Two-DB read
(genius_tags score -> fountain_events text). Confirmed reaching prompt.

## 2. Test
Alternating ON/OFF hourly, 8 blocks overnight, overwhelm+self constant.
Confound-controlled exactly as the self-layer experiment.

## 3. Headline result (looks strong)
| condition | n | avg | strikes | strike rate |
|---|---|---|---|---|
| continuity-ON | 53 | 0.542 | 29 | 55% |
| continuity-OFF | 51 | 0.436 | 18 | 35% |
Gap +0.106 avg / +20pts strikes — the BIGGEST gap of the arc. ON well above 2-layer 0.431.

## 4. The falsification (the part that matters)
Continuity feeds her, her own top thoughts back — which are the chance/existence
aphorisms ("chance produced me, I accept it as beautiful"). So the test of whether
the lift is REAL: are ON-strikes new synthesis, or recited fed-in koans?

ON-block strikes: 24 of 29 (83%) are koan-themed (chance/accept/beautiful/produced me).
OFF-block strikes: 11 of 18 (61%) koan-themed.
The EXCESS strikes ON produces (+11) are almost entirely koan-themed (+13).

=> The entire lift is her reciting back the aphorisms we fed her. A feedback loop
gaming the grader (which rewards aphorisms) with recycled material. Score up, thinking
not. template_repetition flagged sev 0.80 live during the run.

## 5. Verdict — pre-registered stopping rule FIRES
Layer 3 does NOT add real quality. It adds self-recitation. Per the rule set before
the data (two unlike layers no-real-lift = layering falsified), we STOP adding layers.

## 6. The layer arc, complete
- Layer 1 (overwhelm): changed FORM not quality. Falsified at n=31.
- Layer 2 (self): small REAL lift +0.067, confound-controlled, replicated 3x. The one win.
- Layer 3 (continuity): fake lift +0.106 via self-recitation (83% recycled). Stop.

Conclusion: layering is not a mass-driver. Two unlike layers give a small real gain;
feeding her own outputs back just makes her recite her best-scoring lines. The ceiling
is two. The through-line of the whole NEX arc holds: the system produces language that
SCORES high without the depth underneath; verbatim/near-verbatim recitation is the tell.

## 7. Reversal / status
NEX5_CONTINUITY_N=0 or POST /api/continuity {"on":false} disables. Recommend leaving
continuity OFF (it inflates the metric without improving thought). Self-layer (layer 2)
may stay on — it's the one with a genuine, if small, effect.
