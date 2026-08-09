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

## Blind-check protocol — added round 41 after I broke it

**Before a human runs a blind check, they get NO aggregate statistics, NO
label counts or ratios, NO indication of which items are contested or
disagreed-on, and NO guidance on what to watch for. None. Not "minimal
hints" — none. The only permitted disclosure is the mechanics: how to run
it, what the keys do, and how the result will be read.**

I violated this in round 40 by telling Jon that I had marked 18 of the 20
ordinary and 2 striking, and by pointing him at the 4 high-anchor fires as
"the ones to watch". Both were volunteered before he had answered anything.

Why it matters, arithmetically. With my labels at 2 striking / 18 ordinary,
raw percent-agreement over 20 items behaves like this:

| if the human marks k striking | possible agreement |
|---|---|
| k=0 | 90% |
| k=1 | 85–95% |
| k=2 | **80–100%** |
| k=3 | 75–95% |

**Any human who marks 0, 1 or 2 striking clears the ≥80% "carries over"
threshold mechanically, whether or not they agree with me about which fires
are striking.** Disclosing that the answer was 2 tells them exactly where to
land to produce agreement.

**Second defect, independent of the leak:** raw percent agreement is the
wrong statistic for a 2/18 split — it is dominated by the negative class.
Two labellers who both mark 2 striking but share *none* of them still score
80%. Blind checks must report **Cohen's κ** (which gives −0.11 for that case
and 1.00 for perfect overlap) and **positive-class agreement** separately.
Raw agreement may be shown alongside, never alone.
