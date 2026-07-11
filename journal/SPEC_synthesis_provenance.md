# SPEC — Synthesis Provenance: designing against the real failure, not the filed one

*Written 2026-07-11, design session, no code. Session 22 retracted the July 7
"attribution erodes" finding as mis-specified (see `journal/CARRY_OVER.md`,
2026-07-11 ~09:00 entry — read that first) and traced the real mechanism:
synthesis dissolves substance by construction, universally, not just for
feed-attributed claims. Updated same day, same session, part 4-5: that
mechanism (composition) turned out to be downstream of a second, separate
root cause in pair SELECTION (see §0 and `journal/CARRY_OVER.md`,
2026-07-11 ~12:48 entry). This spec designs against BOTH findings, in the
right order. It does not propose a fix — it proposes what to decide before
there is one, per the same discipline `SPEC_persistence_channel.md` used
before the persistence-channel build. DO NOT BUILD from this document.
`synergizer.py` is untouched.*

---

## 0. ROOT CAUSE FOUND (session 22 part 4) — read this before §1

Everything below §1 was written believing the problem started at
*composition* (the synthesis prompt dropping substance). It doesn't. It
starts one layer upstream, in `synergizer.py:_select_pair()`:

```python
rows = self._reader.read(
    "SELECT id, content, branch_id, confidence, created_at, source "
    "FROM beliefs WHERE source NOT IN ('precipitated_from_dynamic') "
    "AND confidence > 0.5"
)
```
No `ORDER BY` — confirmed via `EXPLAIN QUERY PLAN` (`SCAN beliefs`, a bare
table scan returning rows in ascending-ID order). Selection is a global
argmax with strict `>` over `avg_conf`, and `confidence` is ~99.5% tied at
exactly 0.70 for `fountain_insight` (audit #15). **No-ORDER-BY + strict
argmax + an almost-universally-tied field means the lowest ID among the tied
maximum wins every tie, permanently.** Verified: the winning fresh cohort is
beliefs 263–283, a sequential run written in the system's first ~55 minutes,
reused 124–194 times each; the anchor side shows the identical mechanism.

**Confirmed not self-reinforcing** — grepped `synergizer.py` in full, zero
writes to `use_count`/`reinforce_count`/confidence. This is a *static* tie,
not a feedback loop like throw_net's. It doesn't grow; it also can't decay
or be interrupted on its own. Worse in that sense, not better.

**A hypothesis was tested and failed, on record:** the working assumption
going in was that the selection formula prefers introspective content over
world-contact. Belief 284 — created minutes after the winning cohort, same
0.70 confidence, equally introspective, never once selected — disproves it.
`_select_pair()` never reads `content`. The formula is content-blind, not
content-averse. The winning cohort's navel-gazing character is a bootstrap
accident, not a preference.

**What this means for the rest of this document:** §1's "real problem"
(composition dissolves substance) is still true, but it's the second of two
problems, not the first. Which beliefs *reach* composition is decided by
§0's tie-break, upstream and independent. §2 is reordered below so the
selection question comes first — fixing composition while leaving selection
untouched still means only ever composing from the same ~20 recycled lines.

## 1. The real problem, stated exactly

Not attribution loss. **Substance dissolution via novelty-seeking synthesis
over pairs selected without regard to relatedness.** Two instruments found the
same mechanism four days apart, from two different angles — and, per §0, both
of them are downstream of a third, upstream cause (pair selection) found on a
third angle a few hours later still:

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

Three sub-questions. The first is new (§0's discovery); the other two were
this document's original focus and are now explicitly downstream of it.

### (a) SELECTION — what should `_select_pair()` select ON? (the root question)

Right now it selects on `confidence`, tie-broken by accident of row order.
Five options, none picked here — this is a design doc, not a decision:

- **(i) Break ties by recency (newest-first).** Cheap — reverse the row
  order or add `ORDER BY created_at DESC`. Breaks the specific groove on
  263–283 immediately. **Against:** recency isn't quality; nothing stops a
  *new* groove forming on whatever's newest once that becomes the tie-break
  — the same mechanism, relocated, not removed.
- **(ii) Break ties randomly among the tied maximum.** Cheap, no groove
  forms (different pair each time). **Against:** no signal either —
  synthesis becomes arbitrary-among-equals rather than arbitrary-but-fixed.
  Solves recycling, doesn't add anything in its place.
- **(iii) Make confidence actually vary, so ties are rare.** Sounds
  principled — but `confidence` being ~99.5% tied per source is audit #15
  (meaningless, one fixed value per module, not an assessment). "Fix the
  tie-break by fixing confidence" relocates the problem into a field
  already known broken, and fixing #15 is its own, larger, separate
  question — this option is really "solve a different audit finding first."
- **(iv) Select for semantic relatedness between anchor and fresh** (the
  original §2(a) of this document, folded in here since it's the same
  question). **What the data actually shows** (`collision_grades`,
  `input_distance` is the only distance ever explored, because selection has
  never varied it):

  | distance | n | collapse rate | avg output_distance |
  |---|---|---|---|
  | 0.33 | 42 | 95.2% | 0.254 |
  | 0.35–0.39 | 470 | 92.7–98.9% | 0.22–0.27 |
  | 0.40–0.46 | 381 | 100.0% | 0.24–0.34 |

  Collapse is uniformly high (92.7–100%) across the *entire observed
  range*, trending toward **more** reliable collapse at higher distance —
  the opposite of a sweet spot. **But this cannot show whether closer pairs
  would collapse less, because the system has never tried one.**
  `_select_pair()`'s preferred path is always anchor-vs-fresh; there is zero
  data on two topically related fresh beliefs paired together. Most
  principled option here — **feasibility audited session 23, see the
  resolved subsection immediately below: MEDIUM, wiring not a build, with a
  sizing decision still open.**
- **(v) Select deliberately for world-contact** (prefer feed-derived fresh
  beliefs). This is the separate design choice §0 flagged: fixing the
  tie-break does not make this happen automatically, because the current
  mechanism never discriminated on content one way or the other. This
  option is now explicitly optional and independent of (i)–(iv) — it can be
  layered on top of whichever tie-break gets chosen, or left out entirely.

#### §2a RESOLVED: fix B is feasible (session 23 audit) — MEDIUM, wiring not a build

Jon chose option (iv) — pair by semantic relatedness. Session 23 audited
whether that's a one-clause change or a major build, read-only, before
anything got picked further. Verdict: **MEDIUM.**

**Reachability, proven, not assumed:**
- No belief embeddings are stored anywhere — no column, no table, no file.
  `theory_x/diversity/embeddings.py` holds only an in-memory LRU cache (2048
  entries, dies on restart) over `sentence-transformers/all-MiniLM-L6-v2`
  (384-dim), computed on demand via a real `model.encode()` call.
- **The machinery already exists and is already proven working**:
  `grader.py` (the `collision_grades` grader, audit #10) computes its
  `input_distance` via exactly this — `embed_belief()` + `1 - cosine` —
  today, on real beliefs, correctly.
- **Reachable from `_select_pair()` with a one-line import.** Checked
  `synergizer.py`'s imports directly: `embeddings.py` is not currently
  imported anywhere in the file — zero reachability today. But
  `_select_pair()` runs in the same process as everything else, its own
  query already returns `content` for every candidate row, and
  `embed_belief(id, content)` needs nothing else. **This is explicitly NOT
  the throw_net/TimeFetch reachability trap** (session 19: arXiv was
  ingested into `sense.db` but `TimeFetch` had no query path to it — a real
  cross-process/cross-database gap). Here there is no such gap: same
  process, same interpreter, content already in hand. Checked and ruled out
  on purpose, not assumed absent because the general shape looked similar.
- **Cost, measured, not assumed:** 6.9ms/belief (timed on this system, 500
  real belief contents, model warm). The actual fresh pool matching
  `_select_pair()`'s own `WHERE` clause is **8,580** (not the ~4,500
  estimated in session 22 — `synergized` beliefs count too), plus ~20
  anchors. A full cold sweep: **≈59.3 seconds.** Distance computation once
  vectors exist is numpy dot products — sub-second, not the bottleneck.
  Synergizer cadence (`theory_x/stage3_world_model/__init__.py:
  _synergizer_loop`): fires at most once per 5-minute cooldown, 25-minute
  timer trigger — not a hot loop. ~60s against a 5–25 minute cadence is
  tolerable. **But the 2048-entry cache cannot hold an 8,580-item pool** —
  a full sweep every tick will churn the cache and largely re-pay that ~60s
  on every single tick, not once at cold start.

**The sizing decision — this is the fork the BUILD session must settle
first, not something to pick here:**

- **FULL SWEEP.** Embed all ~8,580 fresh candidates every tick. Simple,
  considers every possible pair, no sampling rule to get wrong. Costs
  ~60s/tick, recurring (cache too small to amortize it away) — tolerable
  against the measured cadence, but a real, permanent per-tick cost, not a
  one-time one.
- **BOUNDED SAMPLE.** Embed only N fresh candidates per tick (some cheap
  pre-filter — recency, or a random subsample). Cheap and bounded. Against:
  needs a sampling rule, and a bad one could silently re-introduce a groove
  one level down (session 22's own point about breaking ties by recency
  alone: relocates the problem, doesn't remove it, unless the sample is
  large or varied enough to matter).
- **PERSIST THE EMBEDDINGS** — a third option worth naming plainly: add the
  store the system currently lacks (a column or sidecar table caching each
  belief's vector permanently), so the ~60s is paid once per belief, ever,
  not once per tick. Larger change than the other two — it's "wiring plus a
  persistent store," not just wiring — but it doesn't only serve fix B: all
  15 files that currently call `embed_belief()` on demand (`crystallizer.py`,
  `drive_emergence.py`, `metacognition.py`, the `arcs/` cluster, and others)
  are re-computing the same vectors from an in-memory cache that evicts
  under load and dies on every restart. Persisting once would remove a
  recurring cost from the whole system, not just from the synergizer. Worth
  weighing against the other two options' simplicity, not dismissing as
  scope creep.

**Cheaper proxy, documented, not chosen:** `tags` (JSON keyword array,
already on every belief via `tag_ops.generate()`) would let relatedness be
scored via set-overlap — no model call, no embedding cost at all. **Untested
for whether keyword overlap actually distinguishes related from unrelated
well enough to escape the mush pattern** — that's a real open question, not
a known answer, and would need the same falsifiable substance-survival check
(§4) run against it before trusting it over embeddings. Worth spiking first
if the ~60s embedding cost turns out to matter more in practice than the
cadence measurement here suggests.

**The measurement instrument is unchanged.** §4's substance-survival metric
applies to fix B exactly as written — whichever sizing option gets chosen,
run the baseline first, then check whether the chosen change moves the
survival rate. Feasibility being confirmed here doesn't change what counts
as evidence that the fix worked.

### (b) THE PROMPT — downstream of (a); only matters once selection varies

What would each alternative actually produce?

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

### (c) PROVENANCE — downstream of (a) AND (b); only meaningful last

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

**Also do not fix composition (§2b/§2c) while leaving selection (§2a)
untouched.** A better prompt or a source field bolted onto whichever pair
`_select_pair()` hands it still only ever fires on the same ~20 recycled
beliefs (§5). That would be a real improvement to a narrow, already-tiny
slice of synergizer activity while leaving the larger pattern — 93.1% of all
synthesis recombining the same 20 lines — completely unaddressed. Composition
fixes without a selection fix are worth doing only with that scope
limitation stated up front, not discovered later.

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

**This metric measures the whole chain, which is why it stays the right
instrument regardless of which layer in §2 gets fixed.** A selection-only
fix (§2a) that keeps the current prompt should still raise the survival rate
if it works, simply by feeding composition better material. A
composition-only fix (§2b/§2c) with selection untouched should raise it only
on the narrow slice of synthesis events that happen to touch the 6.9%
grounded cohort (§5) — and should show close to no change on the other
93.1%, which is itself a useful, falsifiable confirmation that a
composition-only fix leaves the selection groove exactly where it was.

## 5. Grounding numbers, read live — how much of this is worth fixing at all

*Updated session 22 part 4: these numbers originally read as an open
question ("why these 20?"). §0 answers it — a no-`ORDER BY` tie-break on a
~99.5%-tied confidence field, permanent by construction, content-blind. The
numbers below are unchanged; what they mean is no longer a mystery.*

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
build: a "preserve feed attribution" fix (§2b/§2c) would touch a small
fraction of synergizer activity. "Why does the same 20-line pool get reused
hundreds of times while 4,507 other fountain_insight beliefs are never
touched" is no longer an open question sitting next to this one — §0 answered
it, and it's the same document's §2a now. Worth deciding which of §2a/b/c
this build is actually for, in that order, before starting.

---

*This spec resolves nothing. It exists so the next session — fresh, per the
July 7 note's own request, honored five days later than intended — designs
against what session 22 actually found, not against what looked plausible at
11pm on a Tuesday, and not against the first thing this same session found
either: the original draft of this document designed around composition
(§1) before diagnosis reached one layer further upstream and found selection
(§0) underneath it. That's the reason for the phase-gate discipline the rest
of this week has used — a fix aimed at composition alone would have been
real, tested, and one layer too low. The three sub-questions in §2 are
genuine trade-offs, not puzzles with a hidden correct answer, and §2a is the
one to resolve first, not last; §5's numbers say the problem is real but
narrower in scope than assumed, which should shape ambition, not kill it.
Build nothing from this file directly — read it, decide §2a before §2b/§2c,
then write code in a session that starts with that decision already made.*
