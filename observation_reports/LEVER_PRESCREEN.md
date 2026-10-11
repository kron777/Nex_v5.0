# LEVER PRE-SCREEN — five static predicates to run BEFORE building any dark-flag lever

Adopted 2026-10-11 (Beam E4), after four L4 levers were each falsified *before* arming by a pre-arm
measurement (r79 threshold, r80 saturation, r82 branch base-rate, r83 referent) and the r83 groove
turned out to be voice, not a defect. A lever is **inert-by-construction** if ANY predicate fails.
Attach the answers to each new round's pre-registration; do not build until all five pass.

1. **EXPOSURE (base-rate).** The lever's trigger must fire often enough to matter.
   Check: P(trigger) on the live instrument × expected per-fire effect ≥ a stated floor.
   Killed r82 — the fixation trigger needs a repeated branch, but branches switch 88% (s=0.878),
   so exposure was ~2% of fires. *Measure the trigger's live rate from the data, not from supply.*

2. **HEADROOM (saturation).** A lever that adds/subtracts on a thresholded quantity must have mass
   in the **pivotal band** [threshold − bound, threshold).
   Check: the fraction of evaluations in that band.
   Killed r79/r80 — at-fire readiness is median 1.000, 96% ≥ 0.90, only ~4% in [0.70, 0.90), so a
   ≤0.20 term almost never flips a fire. *Confirm `score()` is a gate, not a ranker, first.*

3. **LOCUS (shared state).** Trace from the TARGET's producer back to the lever. If the lever writes
   a variable the producer never reads, it cannot move the target — one grep.
   Would have flagged r81 (arbitrate winner only prepends a framing line, `generator.py:3050`; the
   body is fetched independently) and r82 (carry writes beliefs/momentum; `focus_num` reads only
   `sense_events`, `stage2_dynamic/__init__.py:286`).

4. **DEFINITIONAL COUPLING.** If the target is a function of the lever's own input, it moves by
   construction (fake pass) or re-derives (fake null) — either way it is not a test.
   Flagged r81's first primary `p_on_subject` (momentum-led fires continue a thread, so score off
   the current item by the selection's own definition). Use a target blind to the lever's input.

5. **REPRODUCE-FROM-LIVE-INPUT.** Before building any INPUT-side (prompt/retrieval) lever, require the
   phenomenon be reproducible offline by feeding the exact live input at the **live sampling config**
   to the model. No prompt-side lever can move a groove the prompt does not produce.
   Would have redirected r83 immediately: minimal reconstructions gave 0.000 opener-repeat; the cue only
   appeared once the **multi-belief** presentation was reproduced at the live config (temp 1.0 +
   repeat_penalty 1.30). Check the live sampling config (`voice/llm.py:_SAMPLING`) matches the probe.

**And after it reproduces, before building: the defect-vs-voice gate (Beam E2).** A located cue is not
automatically a bug. Measure conditional content entropy / item-responsiveness with the frame present vs
absent: if the frame LOWERS them it is a defect worth levering; if it preserves them it is VOICE (identity)
and levering it out only flattens distinguishability. r83's opener frame passed reproduction (cue located:
multi-belief presentation) but failed the defect test (entropy equal) → kept as voice, not built.
