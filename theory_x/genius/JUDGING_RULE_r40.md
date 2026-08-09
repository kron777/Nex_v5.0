# Judging rule — round 40 self-labelling

Written and committed **before any fire in the frozen set was read**. Git
history is the proof. Applied unchanged to all 120.

## What this rule is calibrated to — read first

`GENIUS_SCORE_v2.md` is explicit that the scorer targets **Jon's particular
intuitions**: *"we are trying to track what Jon recognizes as nex's genius
moments, not establish a universal genius detector"*, and it anticipates this
exact situation — *"additional flaggers can mark a held-out set and the
agreement rate between flaggers can be [measured]"*.

So this rule is a **second flagger's** rule. It is derived from the worked
examples in `GENIUS_SCORE_v2.md` "What v1 got wrong" (ranks 1–7 template,
ranks 8–10 striking), which is the only written record of the target concept.
It is not, and cannot be, Jon's rule.

## STRIKING

Mark STRIKING only if **all three** hold:

1. **It has content.** It makes a claim, distinction, or observation that
   could be disagreed with, or could be wrong. Something is asserted.
2. **It is not an instance of a recurring frame.** Not a fill-in-the-blank of
   a template — "The quiet between X feels Y", "I notice X aligns with Y",
   "What if X holds the key to Z". The doc's ranks 1–7 are the canonical
   failure and they scored *high*.
3. **Its specificity is load-bearing.** Remove the particulars and the
   sentence collapses. If swapping the subject for an unrelated one leaves it
   equally true, it is decoration.

## ORDINARY

Mark ORDINARY if **any** of:

- Raw feed payload, `[stream.name]` dump, or `[tick]`.
- A template instance per (2) above.
- A summary of the focal item that adds no move beyond restating it.
- Stance-assertion with no content — "I am the attending that…", "I lean
  towards prioritising…" — where the sentence would survive unchanged in any
  context.
- Boilerplate hedging or scaffolding.

## Edge rules, to keep this reproducible rather than moody

- **Length is not evidence** in either direction. F1 is the deployed scorer's
  second-largest weight; this rule must not import that bias or the AUC test
  becomes circular.
- **First person is not evidence** in either direction. This is precisely the
  engagement-gate confound from R33/R38; importing it would contaminate the
  F4 test.
- **On-subject-ness is not evidence.** A fire can be faithful to its item and
  dull, or off-item and striking. That is a separate metric.
- **Genuine 50/50 → ORDINARY.** Striking is the marked case and should carry
  the burden of proof. This biases my labels toward ordinary; the direction
  is declared so it can be read in the results.
- The deployed score is **not consulted before judging**. Fires are exported
  without scores, judged, then joined back.
