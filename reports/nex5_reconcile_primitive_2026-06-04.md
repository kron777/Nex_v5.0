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
