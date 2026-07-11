# SPEC — Synthesis Provenance: designing against the real failure, not the filed one

*Written 2026-07-11, design session, no code. Session 22 retracted the July 7
"attribution erodes" finding as mis-specified (see `journal/CARRY_OVER.md`,
2026-07-11 ~09:00 entry — read that first) and traced the real mechanism:
synthesis dissolves substance by construction, universally, not just for
feed-attributed claims. This spec designs against THAT finding. It does not
propose a fix — it proposes what to decide before there is one, per the same
discipline `SPEC_persistence_channel.md` used before the persistence-channel
build. DO NOT BUILD from this document. `synergizer.py` is untouched.*

---

## 1. The real problem, stated exactly

Not attribution loss. **Substance dissolution via novelty-seeking synthesis
over pairs selected without regard to relatedness.** Two instruments found the
same mechanism four days apart, from two different angles:

**The grader (`theory_x/diversity/grader.py`, audit #10, `journal/AUDIT_2026-07-08_to_10.md`):**
```python
grade = (
    w["w_input_distance"]  * input_dist   +   # 0.4
    w["w_output_distance"] * output_dist  +   # 0.35
    w["w_rarity"]          * rarity           # 0.25
)
```
Rewards distant parents numerically. Distance forces averaging: two
near-orthogonal beliefs share nothing, so whatever relation gets written
between them has to live in the abstract space between them, not in either
one's actual content. 97% of 893 graded syntheses collapsed inward (audit #10).

**The composer (`theory_x/stage3_world_model/synergizer.py`):**
```python
_SYNTHESIS_PROMPT = """\
I hold two thoughts at once:
"{belief_a}"
"{belief_b}"
In one sentence, what new insight do I notice?\
"""
```
No source, no branch_id, no path for any attribution or specific claim to
ride along — only the two bare `content` strings, and an explicit ask for
something NEW. Traced on the actual July 7 case (`belief_lineage`, verified
edges): a feed headline about immigrant welfare use, three synergy
generations later, no longer mentions immigration. 15/15 more random
`fountain_insight → synergized` chains sampled show the identical pattern,
regardless of topic — this is not politically-contested-content-specific.

**These are the same mechanism, confirmed from two directions**: pair
selection (`synergizer.py:_select_pair()`) is **ANCHOR × FRESH** — a
seed/koan/keystone belief matched against a "fresh" fountain thought, chosen
purely by average confidence score, never by topical relatedness. That's
*why* the grader's distances cluster at 0.33–0.46 (§5 below) — it's not a
deliberately explored range, it's what falls out of always pairing
philosophical axioms against everyday observations. Nothing between them, so
the LLM's "new insight" has nothing to connect to and produces mush instead.

## 2. The design question, honestly framed

### (a) Pairing: arbitrary, or constrained to related beliefs?

**Against arbitrary:** produces mush — that's most of this document.
**For arbitrary:** distant connections are sometimes where real insight
lives; constraining pairs to already-related beliefs risks making synthesis
merely associative — restating what's already obviously connected, never
actually creative.

**What the data shows, precisely** (`collision_grades`, input_distance is the
only distance ever explored, because pair selection has never varied it):

| distance | n | collapse rate | avg output_distance |
|---|---|---|---|
| 0.33 | 42 | 95.2% | 0.254 |
| 0.35–0.39 | 470 | 92.7–98.9% | 0.22–0.27 |
| 0.40–0.46 | 381 | 100.0% | 0.24–0.34 |

Collapse is uniformly high (92.7–100%) across the *entire observed range*,
with a slight trend toward **more** reliable collapse at higher distance, not
less — the opposite of a "sweet spot." **But this cannot answer whether
closer pairs would collapse less, because the system has never tried a
closer pair.** `_select_pair()`'s preferred path is always anchor-vs-fresh;
the fallback (cross-branch) and last-resort (temporally distant) paths exist
in code but the preferred path fires whenever any anchors and any fresh
beliefs both exist — which is always. There is zero data on what happens
when two *topically related* fresh beliefs (two different headlines about
the same story, two fountain thoughts on the same topic) get paired. **The
honest answer is: we know arbitrary-distance pairing (in the specific
axiom-vs-observation form this system actually uses) collapses reliably. We
do not know whether related pairing would do better, because it has never
been tried.** Any design that assumes it would is a hypothesis, not a
finding — state it as one.

### (b) The prompt: what would each alternative actually produce?

- **Current** ("what new insight do I notice?"): guaranteed paraphrase-and-
  compress. Explicitly asks for something the inputs don't already say. This
  is *why* it dissolves substance — not a bug in execution, the correct
  output of the instruction as given.
- **"Preserve the more specific/factual parent's content, connect the other
  to it"**: requires deciding *which* parent is "more specific" — a real
  sub-problem (proper nouns? numbers? presence of a quoted claim?). If
  solved, this turns synthesis into "extend claim A, gesture at B" rather
  than a true two-way synthesis — changes what the operation IS, not just
  how it's worded. Would likely preserve substance far better; would also
  make "synergized" a less accurate name for what's produced.
- **"What connects them?" instead of "what's new?"**: still asks for one
  new compressed sentence — the request for *novelty* is what drives
  compression, and reframing toward "connection" doesn't remove the
  one-sentence compression step. Probably reduces dissolution somewhat
  (anchoring on the actual relationship rather than an invented new angle)
  but is not obviously sufficient on its own — untested, would need the same
  before/after measurement as any other option (§4).

Each of these is a different *definition* of synthesis, not a parameter
tweak. Decide which one is wanted before implementing any of them.

### (c) Provenance: only after substance is solved, and only as secondary

If a feed-derived factual claim is one parent, should its source ride along?
**Only meaningful once (a)/(b) preserve enough substance for a source tag to
attach to something real.** Tagging a claim that dissolves into "the recent
feed on..." three generations later with its original URL doesn't fix
anything — the URL would sit on a sentence that no longer says the thing the
URL supports. **This is an explicit ordering dependency: provenance is
downstream of substance-preservation, not a parallel fix.** Building it first
is how you get instrument 24 (§3).

## 3. What NOT to do

Do not "add a source column" as the fix. That targets the retired July 7
finding (a claim survives but loses its hedge) — which does not reproduce.
The actual finding is that claims don't survive long enough for a source
column to matter. Attribution bolted onto content that dissolves anyway is a
label on an empty box: technically present, functionally decorative,
exactly the shape of the twenty-one other instruments this repo already has
that measure something other than their name. Do not build twenty-two
without building thirty-eight.

## 4. Measurement — propose the test before the fix

**`collision_grades` is dead** (audit #10: stopped writing 2026-05-14, killed
by the same commit that disabled the synergized boost it was scoring for).
Even if reactivated, its current formula is part of the problem (rewards
distance, doesn't measure substance) — reactivating it unmodified would
reinforce the mechanism being investigated, not test a fix for it.

**Proposed new metric, falsifiable, substance- not distance-based:**
for a sample of synergy events, extract a cheap proxy for "specific content"
from each parent — proper nouns, numbers, quoted phrases, or named entities
(the same kind of token-level extraction already used elsewhere in this
codebase, e.g. `trigger_detector._extract_topic()`'s frequent-token method,
or `tag_ops.generate()`). Check whether *any* of those tokens survive,
verbatim or as a clear paraphrase, in the child. Score: fraction of synergy
events where at least one parent-specific token survives to the child.

This is directly falsifiable before any fix is built: **run it against the
current 4,016 synergized beliefs first, get a baseline rate** (prediction,
stated now, before measuring: given the traced chain and the 15/15 sample,
expect this to be low — under 10%). Whatever change gets chosen in §2 should
be judged against whether it moves that number, not against whether the
grade "looks" less collapsed or the prose "feels" richer. If a chosen fix
doesn't move the survival rate, it didn't work, regardless of how the output
reads.

## 5. Grounding numbers, read live — how much of this is worth fixing at all

- **44 of 4,551 `fountain_insight` beliefs (0.97%)** have ever been selected
  as a synergy parent, ever, in the system's history.
- Of **4,016 total synergized beliefs**, 3,998 (99.6%) trace to a
  `fountain_insight` parent. But those 3,998 draw from only the 44 above.
- **3,721 of 3,998 (93.1%)** trace to just **20 heavily-recycled, purely
  introspective one-liners** — "The quietude of my own creation," "The
  weight of my own silence grows, yet within it finds a form of clarity" —
  each reused **124–194 times**. These carry no external claim to begin
  with; there is nothing feed-attributable to lose.
- **277 of 3,998 (6.9%)** trace to more grounded/observational
  `fountain_insight` content (personal sensory noticing, and a handful of
  actual feed-topic engagement like the traced immigration case, used 8
  times). This is the *entire* population where "did a specific claim
  survive" is even a meaningful question to ask.
- `collision_grades`'s 893 graded rows are frozen at 2026-05-14 — they cover
  roughly 22% of the *current* synergized population and none of it recent.
  Any reactivated version starts with a coverage gap, not just a formula
  problem.

**Read plainly: provenance loss through synthesis is real and mechanically
universal (confirmed 15/15), but synthesis touching content that was ever
externally attributable at all is a narrow slice — well under 10% — of what
the synergizer actually does most of the time, which is recombine the same
twenty recycled self-referential lines against koans, hundreds of times
each.** That doesn't make the finding unimportant — but it reframes the
build: a "preserve feed attribution" fix would touch a small fraction of
synergizer activity. A "why does the same 20-line pool get reused hundreds
of times while 4,507 other fountain_insight beliefs are never touched"
question is a different, and by this count larger, problem sitting right
next to it. Worth deciding which one this build is actually for before
starting.

---

*This spec resolves nothing. It exists so the next session — fresh, per the
July 7 note's own request, honored five days later than intended — designs
against what session 22 actually found, not against what looked plausible at
11pm on a Tuesday. The three sub-questions in §2 are genuine trade-offs, not
puzzles with a hidden correct answer; §5's numbers say the problem is real
but small in scope, which should shape ambition, not kill it. Build nothing
from this file directly — read it, decide the three questions in §2 on
purpose, then write code in a session that starts with that decision
already made.*
