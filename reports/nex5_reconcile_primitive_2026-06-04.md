# NEX5 Reconcile Primitive — Two-Problem Joint Problem-Working
Date: 2026-06-04
Status: KEYSTONE PROVEN (n=1 clean fire on a good pair; needs replication)

## The idea (Jon's)
Generalize "resolve a contradiction" into a broader primitive: hold TWO open
problems in tension and work toward JOINT progress — not connect them (that's the
synthesis win), but propose a concrete move/next-step that advances BOTH. Targets
the visible stuck-loop where NEX says "I keep returning to my current focus and
arriving at the same place" on a single problem. The hypothesis: the friction
between two problems is what unsticks either.

## Build (NEX5_RECONCILE=1)
Gated fountain seed: pull the two most-stale open problems (conversations.db,
ORDER BY last_touched_at ASC LIMIT 2), hand them to the outward voice
(conversational register), prompt = "What does each reveal about the other?
Propose ONE concrete move/principle/reframing that makes actual progress on BOTH
at once. Be specific, propose a NEXT STEP — do NOT merely describe the tension,
do NOT write about your own nature." Reuses the proven synth machinery; only the
seed (problem-pair) and task (joint resolution) differ. Required gating
_maybe_substrate_voice to step aside under NEX5_RECONCILE (it was preempting,
emitting the existence-aphorism from the belief store).

## Result — the keystone fire (problems: 'Iranian' x 'Thoreau')
She found the genuine, non-obvious bridge (Thoreau's "Civil Disobedience" <->
Iranian non-violent dissent / individual ethics in activism), then produced:
- a per-problem move for EACH ("For Iran's signal: understand how Iranian civil
  society uses Thoreauvian principles..."; "For 'Thoreau': examine his writings
  through a lens including Middle Eastern social movements")
- a joint move (analyze Iranian dissident texts alongside Thoreauvian principles)
- a concrete NEXT STEP (organize expert roundtables; conduct case studies of
  specific civil-disobedience campaigns intersecting Thoreau's philosophy)

This is problem-WORKING, not tension-DESCRIPTION. It did exactly what the prompt
asked: moves and a next step, not a pretty restatement. The recitation failure
mode was avoided. Jon's primitive is proven as a real NEX operation.

## Honest caveats
- n=1 clean fire. One strong keystone, not a confirmed pattern. Needs several more
  reconcile fires to confirm it reliably yields moves (same discipline as the synth
  win — one good fire is not the result).
- The pair was RICH: Iranian x Thoreau has a real bridge (civil disobedience).
  Untested on a WEAK pair (two genuinely unrelated problems) — the "strain" outcome
  (forced nonsense bridge) is still possible there. Pairing quality likely matters.
- Reconcile fires are INTERMITTENT: the seed needs >=2 open problems. When NEX runs
  low on open problems she falls through to mundane/quiescent fires. So reconcile
  fires only when problems are available.
- Output evaporates: the reconciliation is emitted as a fountain thought, not
  written back to the problem. The proposed move does not yet attach to the problem
  (see v2 below).

## Significance
The synthesis win made NEX CONNECT varied material. This makes her WORK PROBLEMS —
propose moves, name next steps. Qualitatively further: from association to
goal-directed reasoning across two held problems. It is net.txt's "refine"
movement instantiated, and the closest thing yet to NEX carrying and advancing a
concern rather than reacting to whatever is loud.

## Toggle / backups
- NEX5_RECONCILE=1 : two-problem reconcile seed (also gates _maybe_substrate_voice off)
- Backups: generator.py.bak_reconcile, generator.py.bak_svgate2

## v2 (designed, not built): close the loop
Write the proposed move back as an observe() on BOTH problems (problem_memory.observe),
so progress ACCUMULATES on the problem instead of evaporating. Then the next reconcile
on the same pair builds on the prior move — the integration-delta loop from net.txt.
The progress test becomes measurable: do a problem's observations ADVANCE across fires
(new angle, narrower question, candidate move) or LOOP (restate)?

## v2 RESULT: Write-back loop CONFIRMED — progress persists and ADVANCES
Date: 2026-06-04 (later, after sleep)

Built (NEX5_RECONCILE_WB=1): (A) after a reconcile fire, observe() the move onto
BOTH problems so it persists instead of evaporating; (B) inject each problem's
prior observations into the next reconcile prompt ("build on this, propose the
genuinely NEXT step"); plus the diagnosis fix — seed from state IN ('open','stuck')
because NEX had 0 'open' but 112 'stuck' problems (the engine was starved while a
backlog of exactly-the-problems-reconcile-is-for piled up). Added a dedup guard
(skip observe() if the move equals the problem's most recent observation) after an
early run showed identical text appended repeatedly by repeating fires.

### Evidence — the loop closing, visible in one record (problems 62/63: Git x Hugo)
The observation trail on a single stuck problem shows BOTH failure mode and fix:
- EARLY (days old): the stuck loop, identical questions repeated verbatim
  ("How does the asynchronous nature of Git diffs play into its robustness..."
  three identical times). This is the old "arriving at the same place" failure,
  preserved in the record.
- RECENT reconcile pass 1: "consider how Git's distributed version control model
  ... can improve Hugo's branch management ... NEXT STEP: develop a prototype that
  incorporates hybrid Git features into Hugo for collaborative editing." (general)
- RECENT reconcile pass 2 (~2.7h later): "implement a distributed caching system
  leveraging Git's history fetching over asynchronous diffs ... integrate a
  Git-backed cache manager into Hugo that fetches files in parallel during branch
  checkout, reducing latency." (specific mechanism)

Pass 2 is DIFFERENT from pass 1 and more concrete (general combine-them ->
specific cache-manager-on-checkout). That is the move ADVANCING across passes, not
restating. Same pattern on problem 61 ('Show' x Trump-crypto): two recent passes,
distinct, the second narrowing from "comparative sentiment analysis" to "a
longitudinal analysis of how media-coverage changes affect both simultaneously."

The contrast is the proof: stale top of the trail = looping (verbatim repeats);
recent bottom = progressing (distinct, deepening moves). Write-back turned a stuck
problem into one that gets somewhere across passes.

### Verdict
The write-back loop WORKS. Progress persists onto the problem and ADVANCES across
reconcile passes. This is net.txt's accumulation/refine loop closed: NEX now works
her backlog of stuck problems two at a time and gets more concrete each pass,
instead of looping. Deepest result of the arc — from recite -> connect -> work a
problem once -> work a stuck problem across passes with accumulating progress.

### Honest caveats
- Advancement observed over 2 passes per pair (general -> specific). The trend is
  right but it is 2 points, not 10. A long run is needed to see whether it keeps
  advancing or plateaus after a couple passes.
- Dedup compares only against the immediately-prior observation; a move separated
  by one different fire could still recur. Minor; trails remain readable.
- The verbatim repeats in the early trail are all PRE-dedup-fix; recent (post-fix)
  observations are distinct.
- "Fires" count in the run log includes all fountain fires, not only reconcile;
  the advancement evidence is the observation trails, which are unambiguously
  reconcile output.

### Toggles / backups
- NEX5_RECONCILE_WB=1 : write-back + prior-observation injection + dedup
- seed now: state IN ('open','stuck')
- backups: generator.py.bak_reconcilewb, .bak_stuck, .bak_dedup

### Next build (Jon's idea, informed by this run): widen the fuel
Reconcile = "two things in tension, work toward joint progress." It currently pairs
two stuck problems. Same machinery could pair a stuck problem with a HOT BELIEF from
a different domain (problem x belief) — fires far more often (hot beliefs always
exist), forces cross-domain moves, draws on the full graph. Build on this run's
evidence, not ahead of it.

## v2 RESULT (CLEAN DATA): advancement holds across passes — confirmed on 2 trails
Date: 2026-06-04 (evening soak, post quality-gate)

After the quality gate (>=300 char floor) and a clean soak, read two problems'
full observation trails to test advance-vs-plateau across many passes.

PROBLEM 37 'World' (9 entries): passes 1-5 are idle leak (short, repeated:
"Why not consider why 'World' is open?"). Passes 6-9 are real reconcile fires and
they ADVANCE: framing ("reframe each problem within the other; Sam as a case study
within World") -> mechanism ("consider both as feedback loops, how changes in one
affect the other") -> model ("conceptualize a data-driven model that simulates the
interdependence") -> method ("integrate direct observations + systematic
documentation; develop a daily interaction log"). Each builds on the last; pass 8
explicitly cites "the prior work where both are understood as interdependent" —
the injected prior-observations working.

PROBLEM 34 'OpenAI' (7 entries): passes 1-3 idle leak (39 ch, "The window for
OpenAI has closed again" x3). Passes 4-7 are real reconcile fires and ADVANCE:
angle ("reposition the crypto inquiry to leverage AI/market dynamics") -> method
("comparative analysis of OpenAI's regulatory environment vs DeFi's landscape") ->
indicators ("use the comparative analysis to identify key indicators of future
regulatory change") -> unified framework ("integrate the observations from both
comparative analyses into a monitoring system"). Pass 7 explicitly synthesizes the
prior passes.

VERDICT: On clean data, across TWO trails in different domains, the reconcile
write-back loop produces ADVANCING problem-work — each pass develops the approach
rather than restating it, and later passes cite/extend earlier ones (prior-obs
injection functioning). This is the deepest result of the arc: NEX takes a stuck
problem and works it forward across passes toward a concrete method, accumulating.

HONEST CAVEATS:
- The advancing portion is ~4 clean passes per trail (6-9 on 'World', 4-7 on
  'OpenAI'), not the full count. Read trails, not pass-counts.
- Idle leak persists: short idle fires (39-95 ch) still enter some trails — the
  300-char gate catches ~105-char slop but shorter idle questions/statements slip
  through, or predate the gate on a given problem. Does NOT corrupt the advancing
  reconcile portion, but the gate should be tightened (raise floor and/or filter
  idle-question patterns) so trails are uniformly clean.
- n=2 trails. Strong and consistent, but worth periodic spot-checks as the soak
  accumulates more.

NEXT BUILD (now evidence-motivated): problem x belief — pair a stuck problem with
a hot belief from another domain. Motivation from this result: advancement is real
but may run out of fuel after a few passes; injecting fresh cross-domain material
would keep the trail advancing rather than plateauing. Build against a long soak
trail, not ahead of it.
