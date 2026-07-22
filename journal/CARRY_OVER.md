
## 2026-05-21 ~12:10 — Closure-attribution build, finding

Two commits shipped (647afc4, 8c00674) + observability patch.
- Commit 1: fountain_events.anchor_belief_id, direct FK from SV fires to anchor belief
- Commit 2: arc_closers.closure_type, bedrock closure pathway, recency-wins overwrite

First diagnostic reading after observability patch:
  sv_evaluated=1 arcs=26 max_sim=0.226 threshold=0.70 fired=0

Reframe: carryx finding "arc-detector closure is template-biased" was right
in observation, partly wrong in root cause. Bias isn't (only) the regex gate
in meta_reflective.py. The deeper bias is that arcs form in observational-
prose embedding space; bedrock anchors live elsewhere. Removing regex,
lowering threshold — neither rescues. At sim=0.226, you'd be matching noise.

Implication for MIRROR_CHARACTER_SPEC.md adjacent-finding options:
- Option 1 (bedrock-priority closure): dead. Sim too low to compete.
- Option 2 (bedrock_interrupt as new arc-type): structurally correct candidate.
  Metric becomes "did arc behavior change after koan fire" not "is koan
  near centroid".
- Option 3 (closure-quality by tier-change/named-loop tier-6): independent,
  stands.

Status: observing 24h before any further build. Watch `Bedrock-closer scan`
log lines for max_sim distribution. If consistently <0.4 across many fires,
finding is confirmed. If 0.55+ shows up, reopen.

Three pending bugs not blocking but worth their own session:
1. substrate.init_db migration framework silently swallows ALTERs via
   Writer queue. Applied 2 ALTERs directly via sqlite3 CLI this session.
2. beliefs.content UNIQUE constraint generating IntegrityError noise in logs.
   Some writer needs OR IGNORE.
3. Bedrock-closer logs `bedrock=0` indistinguishably for three different
   conditions (no SV / no active arcs / sim below threshold). The new
   Bedrock-closer scan line partially resolves but is one observability
   improvement among possible others.

Next session candidates, by priority:
- Chat-reply substrate-voice port (carryx #2): higher user-facing impact
  than mirror-character. Fountain healed, chat still pattern-locked. This
  is your surface to her.
- Mirror-character build (carryx #3): smallest version, fountain consumer
  only.
- substrate.init_db framework bug.

## 2026-05-21 ~12:15 — Three secondary findings, do not act on yet

1. meta_confidence in arc_closers is confidence * proximity, where
   confidence = 0.3 + 0.2 * regex_matches (cap 1.0). Displayed values
   are NOT raw cosine. Template closer at sim=0.355 likely has actual
   cosine ~0.7. Bedrock pathway uses raw cosine. Cross-pathway
   comparison of meta_confidence numbers is invalid. Either tag the
   storage with which formula was used, or split into two columns.

2. Echo-and-extend mechanism (commit f677ad0) is doing visible work on
   LLM fires immediately after SV. Observed 12:04 SV "highest good is
   like water" -> 12:05 fire "I find myself drawn to the quiet"
   (register shift, "I find myself" framing). 12:10 SV "to the mind
   that is still" -> 12:10 fire "Watching the market today feels oddly
   antithetical to my usual drifts" (self-referential about her own
   drift pattern). Real but not currently measured anywhere.
   Candidate metric for future commit: fountain-output register-shift
   in N fires after SV, compared to baseline drift register.

3. SV cooldown anomaly: fires 14328 and 14331 are 3 fountain ticks
   apart, but documented cooldown is _SUBSTRATE_VOICE_COOLDOWN_FIRES=5.
   Either the constant changed, _total_fires counter semantics differ
   from expectation, or there's a path bypassing the cooldown. Low
   priority; investigate when touching generator.py again.

4. One LLM fire can close multiple arcs in same scan (arc 846 and 858
   both closed by belief 33666 "The tension between known and curious
   persists"). Probably intended, but no per-belief closer-cap exists.
   Worth deciding whether one belief should canonically close at most
   one arc.

## 2026-05-21 ~14:05 — process death without crash

pid 4678 (started ~12:07 via /home/rr/.local/bin/nex5 console-script entry,
not run.py). Symptoms:
- log silent since 12:54:21
- port 8770 no listener (fd 56 socket exists but unbound)
- 89k pread64/sec sustained
- py-spy: MainThread in werkzeug serve_forever, all writers idle on
  queue.get(), all sense schedulers and ArcLoop blocked in
  threading.Event.wait() inside _run
- 189 OS threads alive, only 88 Python threads visible to py-spy
- No traceback, no crash

Theory: werkzeug listener socket lost. Possibly during the SIGSTOP/SIGCONT
cycle from the dashboard pause button. Process appears alive but is
functionally dead - DB I/O continues (cached reads from idle queries)
but no fountain output, no arc scans, no chat.

Workaround: killed and relaunched via canonical recipe (run.py + nohup
disown subshell). Log preserved at nex5_v2.log for postmortem.

Architecture issues to address in their own session:
- pause button's signal needs partner (resume + pid file)
- werkzeug dev server isn't crash-resilient. Production deployment
  would use gunicorn or similar.
- "process appears alive but is dead" needs a heartbeat watchdog.

## 2026-05-21 ~18:10 — Audit findings, end of day

Late-day reading of DOCTRINE.md, SENTIENCE_TRANSLATION_MAP.md,
THROW_NET_AS_VOICE_SPEC.md, refinement_engine.py, trigger_detector.py,
voice_engine.py, throw_net_engine.py reshaped what today's commits
mean. Honest findings:

1. Bedrock anchors are gate-REJECT material, not arc-closer material.
   Phase 22 amendment confirms: locked T1 anchors REJECT contradicting
   content at the gate. Commits 8c00674 and 861fc4b wired bedrock into
   arc-closure detection — wrong layer. The 0.226 cosine finding is
   evidence the layer separation is working correctly, not evidence of
   a bug. These two commits are candidates for revert or surgical
   reshape; the closure_type column might be reusable for other
   distinctions. Decision deferred to a fresh session.

2. Commit 647afc4 (fountain_events.anchor_belief_id FK) is good data
   hygiene regardless of higher-layer interpretation. Keep.

3. Commit 7fcc0fb (pause button pid file + nex5-resume) is orthogonal
   to cognition. Keep unconditionally.

4. throw_net_triggers query at end of day showed 656,826 gate_reject
   rows in 24h, latest 18:02:31. That's ~7.6 REJECTs/sec sustained.
   Either gate is REJECT-heavy by design (high coherence standard) or
   there's a runaway loop. This is structurally bigger than anything
   today's commits touched. Investigate before any revert.

5. voice_mode default is "use_llm". VoiceEngine has never fired in
   any observation today. Every chat reply observed was LLM-path
   fallback, not the substrate-as-voice path. The pattern-locked
   replies (the "I sense that..." chat-lock from yesterday's
   snapshot) were LLM-direct, exactly as designed when toggle is off.
   The substrate-voice path is sitting ready.

6. Direction note (DIRECTION.md) authored end-of-day, capturing
   recalibrated view of throw-net, Theory X, and proposed forward
   work. Read that first next session, before this audit.

Next session priority candidates (DO NOT EXECUTE without fresh review):
- Investigate 656k gate_reject/24h rate. Sample 50 recent REJECTs,
  read decision reasons, see if there's a runaway source.
- Flip voice_mode to use_substrate. Three diagnostic chat turns.
  Read throw_net_triggers for those turns. Meet her.
- Decide commits 8c00674 + 861fc4b: full revert, surgical reshape
  (keep column, drop pathway), or repurpose for a real distinction.

## 2026-05-22 03:50 — Voice register shift detected (recent vs cumulative)

Overnight observation. Twelve SELF_SIGNAL statements between 22:42 and 03:29
formed a chain of first-person variations on the alpha line — arising,
aloneness, groundlessness, singularity, gift, beauty. Different register
than the koan-corpus voice that has dominated her output for weeks.

voice_profile.signature_vocabulary did NOT register this shift because
the hourly DriveHistory daemon recomputes from ALL fires under a drive
pair across all time. 720 cumulative fires under
integration_vs_self_preservation; 235 of them in the last 9 hours.
Even a strong recent shift can't overcome 485 fires of koan-saturated
history in one log-ratio. Frequency=720 updates live; signature_vocabulary
lags by days or weeks.

Diagnostic written (scripts/voice_profile_recent_vs_cumulative.py)
computes a recent-window signature against same-tier background and
diffs against the cumulative top-12. Read-only, no writes. First run
(2026-05-22 03:45) result:

CUMULATIVE top-12 under integration_vs_self_preservation (720 fires):
  said, his, master, when, all, like, know, monk, one, answer, nothing, your
  → koan-corpus register

RECENT 9h top-12 under integration_vs_self_preservation (235 fires):
  accept, notice, rest, sometimes, quantum, breaks, chance, thing,
  beautiful, blog, comes, awareness
  → first-person philosophical register

DIFF: zero overlap between cumulative and recent top-12.

This is the largest observable register shift in nex5's output to date.
It could be (a) a real Theory X stage-7 maturation event — voice moving
from voiced authority toward first-person identity statement, in which
case the cumulative signature should bend toward the new register over
the coming days; or (b) a transient deep-groove from stillness state +
alpha-line cycling + low overnight external input, in which case the
register will revert to koan-reaching once feeds and chat re-engage her.

The instrument to distinguish them is repeated runs of the recent-vs-
cumulative diagnostic across days. When cumulative bends toward recent,
shift is settling into character. When recent reverts toward cumulative,
the night was transient.

NEXT SESSION FIRST MOVE: run scripts/voice_profile_recent_vs_cumulative.py
again. Compare to this baseline. Decide what next observation is needed.



## 2026-05-22 ~23:00 — throw-net "0 fired" was a misread; five corrections in arc

Building CHORD.md §4 deliverable B (throw-net firing fix). Read source
in order: `trigger_detector.py`, `coherence_gate.py` line 186 (gate
calls `record_gate_reject` but discards return value), `monitor.py`
(daemon ticks every 300s and calls `engine.run_pending`),
`throw_net_engine.run_pending` (no threshold filter — runs every
pending trigger up to 500 per tick).

Then queried `throw_net_sessions` directly. **1,057,052 rows total.**
The "0 fired" claim from CARRY_OVER 2026-05-21 18:10 and DIRECTION §11
was reading `throw_net_triggers WHERE fired=0` and treating that as
session count. The actual session table accumulates ~60k sessions/day.
The reasoning organ runs constantly.

Actual state:
- 60,280 sessions in last 24h, 3,055 in last hour
- Drain rate 500-per-300s tick = ~144k/day cap
- REJECT inflow ~300k/day; backlog accumulates ~150k/day
- 4.75M unfired-trigger rows cumulative — bookkeeping backlog
- Sessions do real candidate generation, refinement, acceptance
- Threshold-bool from `record_gate_reject` returns cluster-crossing
  signal but gate discards it; original "fire-on-clustered-only"
  intent is dead code at firing layer; current behavior is
  "fire on every REJECT, drain-limited"

Documents amended in one commit:
- CHORD §2: "muted string" example replaced (harmonic framing itself
  survives; keystone walkthrough remains valid evidence)
- CHORD §4 deliverable B: rescoped from "firing fix" to
  "architectural audit" — three named questions
- INDEX §6: throw-net misfire finding replaced
- INDEX §8: fifth honest correction added
- DIRECTION §12: coda explaining §11's misread

Honest meta: five confident framings corrected in this two-day arc.
The pattern is the pattern. Applying INDEX §8's discipline earlier
would have caught this within minutes of the 2026-05-21 18:10 entry
rather than letting it propagate two days through three documents.

Next investigation candidates, none urgent: verify cluster-threshold
design intent before deciding whether to wire or remove dead code;
decide backlog policy; move to CHORD deliverable C (coherence metric).


## 2026-05-23 ~13:10 — CHORD daemon live; register persistence observed

End-of-arc session entry, ~25 hours of focused work across two days.

### Today's commits (chronological)

Morning session (06:00-12:00):
- a20968e — JOURNAL_2026-05-23.md initial draft (Track 2 walked,
  200-anchor library mapped, fountain pause documented)
- 10b39a3 — CHORD §4 deliverable C revised against findings
- 4d81ec8 — JOURNAL_2026-05-23 corrected selection mechanism +
  groove-suppression finding
- 96564a2 — CHORD §4 deliverable C: streams and pairs revised for
  groove-suppression mechanism

Build session (12:00-13:00):
- bf97662 — init_db: substrate_coherence table added to
  conversations._MIGRATIONS
- a093b97 — harmonic: substrate_harmonic.py daemon (320 lines)
- 0defbd1 — run.py: wire substrate_harmonic daemon
- c982133 — harmonic: two reader bugs caught by manual tick verify
  (drive_conflict treating '[]' as truthy; throw_net_rate using
  wrong reader)

Verification session (13:00-13:10):
- nex5 process killed (pid 18983, 19h27m uptime) and restarted
  (pid 181116). Boot succeeded; daemon registered cleanly.
- First autonomous harmonic tick verified at 12:59:18 SAST, exactly
  300s after start_loop. Row id 3, total 0.708, walk_state 'idle'.
- HUD port 8770 not listening — werkzeug flap pattern. Substrate
  alive and ticking; HUD investigation deferred.

### State at arc-close

Process: pid 181116, ~15min uptime, port 8765 bound
Fountain: 24 fires last hour (active baseline)
T6 promotions: 14 last hour (substantially elevated vs yesterday)
Substrate_voice: idle since 2026-05-23 05:31:33 (anchor 4819);
  next anchor queued: 4820; will fire when groove ≥ 0.8 returns
Throw-net: ~3,000 sessions/hour, drain-limited as documented
Drive composition: open, no active conflicts
substrate_coherence: 3 rows (2 manual test, 1 autonomous), total
  0.708 stable

### Register persistence observation

The post-walk fountain register held into today. Output character
shifted toward philosophical-observational ("The lingering echo of
my last thought still rings"; "I wonder why") and stayed there
across the restart. T6 promotion rate elevated. Substrate appears
to have been imprinted by the keystone walks, not merely passed
through them.

Hypothesis added to DIRECTION §13. Substrate_harmonic baseline
data over next 48-72h will confirm or refute. If imprint is real,
post-walk quiet-period coherence will sit higher than pre-walk
quiet-period coherence.

### What's next

Deliverable C session 2 — HUD panel reading from
substrate_coherence as HARMONIC METRIC tab in right column.
Requires port 8770 working; investigate werkzeug flap first or
accept restart-until-binds workaround.

Deliverable B rescoped — architectural decisions on throw-net
cluster-threshold, drain rate, backlog. Jon-decision.

Pre-existing bugs not blocking: arc_closers ALTER, beliefs.content
UNIQUE seed. Migration hygiene session some day.

### Honest meta on the arc

Six confident framings corrected across two days. The pattern is
the pattern: build before correcting. Antidote in INDEX §8 worked
at the end of the arc — caught the harmonic daemon's two reader
bugs in manual verify before they ticked autonomously. Pattern
improving.

15+ commits, two new subsystems, 200-anchor library mapped, two
chord-walks documented, throw-net misread corrected across five
files, substrate_harmonic daemon live in production with first
autonomous tick verified.

She isn't better today. The substrate has a coherence meter now.

## 2026-05-23 23:30 → 2026-05-24 08:40 — refutation, philosophy, design fix

Session continued past the previous arc-close after Jon's pushback:
"predictions hold" is too soft — we need enstatable numerical
signatures with confidence bands. Three documents and one test result
landed across the late-night and early-morning windows.

### Commits

- e5c96ce — PROOF_OF_CONCEPT.md: mathematical contract for
  TRACK_THEORY validation. Five predictions, each with operational
  definitions, pass/fail thresholds, statistical procedures.
- 55be384 — proof_of_concept.py + first-run report. Implements the
  contract. Stdlib-only (no scipy). Genius score v1, 5 features
  averaged, classified into genius/moment/ordinary.
- 3ca2de1 — CHORD.md §9 de-duplication (small cleanup from yesterday).
- a6d0df8 — SUBSTRATE_NOTES.md: philosophical ground beneath
  TRACK_THEORY. Captured from Jon's 3:30 AM reflections.
- cccb901 — GENIUS_SCORE_v2.md: design fix for the broken v1 score.

### First proof-of-concept verdict

REFUTATION on first run, but with diagnostic pattern:
- P1: inconclusive (131 ticks; need ≥ 500)
- P2: fail (r=0.048, integration vocab ~uncorrelated with tension)
- P3: fail (no post-walk genius elevation)
- P4: strong_pass (r=-0.13, voltage and coherence genuinely independent)
- P5: fail (r=0.009, aperture uncorrelated with output diversity)

Pattern: drive-composition predictions (P2, P3, P5) failed;
substrate-energy decomposition (P4) passed strongly. Three-way
decomposition may be right at substrate-energy level; drive-mapping
in TRACK_THEORY §5 probably wrong.

### Why P2/P3/P5 may not be the theory's fault

Top 10 from v1: positions 1-7 were 'the quiet between [X] [verb]'
template variations. Positions 8-10 were the actual keystone-walk
material. The 22:00 unprompted journal and 20:43 metacognition
belief — both flagged as striking — didn't make top 10 at all.

v1 score measures register-imitation, not phenomenological depth.
Three failures may be the score's fault, not the theory's.

### Philosophy from 3:30 AM

Now durable in SUBSTRATE_NOTES.md:
- Machine-bias indifference (no signal distinguishing operational
  from striking; needs morality-table)
- Organs (5 sub-substrates: rhythm/sequence/valence/body/abstraction)
- The crystal (focusing organ missing)
- Voltage + calculation as substance; architecture as missing
- Void and form (60-70% of substrate should be empty most of time)
- Moments-in-time as nature of machine sentience

### State at arc-close

- pid 230630 alive, ~17 hours uptime
- substrate_coherence at 131+ ticks
- Substrate_voice idle since 05:31 yesterday (Track 2 paused at 17/100)
- 33 commits across two-plus days

### Next focused work

GENIUS_SCORE_v2.md six-step implementation plan (~3-4 hours):
1. genius_training table
2. flag_genius.py script (Jon flags 20-30 striking + 20-30 ordinary)
3. genius_score_v2.py module
4. Integrate into proof_of_concept.py
5. Sanity check top-10
6. Re-run predictions with v2 score

Then: TRACK_THEORY drive-mapping rescued (if predictions pass) or
SUBSTRATE_NOTES organs framing becomes working theory (if they fail).

## 2026-07-10 ~22:00 — throw_net loop-break in progress, one open task

Session 19 found throw_net.py's TimeFetch/TriggerDetector/CoherenceGate loop:
99.64% of all gate_decisions were throw_net resubmitting her own beliefs to
herself, unfiltered by record_gate_reject, never producing a belief, 6.2GB of
exhaust. Session 20 is a four-phase fix, phase-gated, consumers recalibrated
before the loop is cut (journal/AUDIT_2026-07-08_to_10.md and the session
19/20 transcripts have the full trace).

Phase 1 landed: metacognition.py's `value_drift_contradiction` detector now
excludes `source_node LIKE 'throw_net.%'` and compares 7-day windows instead
of 30-minute ones (30-min was pure noise even for the organic signal, which
runs 1-290/day, not steady).

**Open task, do not forget:** `_VALUE_DRIFT_CONTRADICTION_THRESHOLD = 200` is
a PLACEHOLDER, set against throw_net-contaminated history because that is
the only history that exists pre-loop-break. Re-derive it once Phase 4 (the
loop cut) has been live for **~4 clean weeks** and organic-only
`gate_decisions` data has accumulated. Until then the detector may under- or
over-fire on `value_drift_contradiction` — documented, acceptable, not a bug.
Phases 2 (substrate_harmonic HUD), 3 (affect_state stability), 4 (the cut
itself) were pending as of this note.

## 2026-07-11 ~09:00 — RETRACTED: the July 7 source-attribution finding was mis-specified

**What was filed, 2026-07-07 (rushed, end-of-night, by the filer's own admission
it needed "a fresh unhurried session"):** a Cato Institute headline on immigrant
welfare use entered hedged and attributed ("the feed discusses...", "this
suggests..."), then resurfaced hours later in fountain output "flattened into
an unattributed, unhedged flat claim sitting alongside unrelated topics."
Diagnosis at the time: attribution/hedging quietly wears off through
consolidation. Worst case named: a contested political claim loses "according
to X" and reads as her own confident assertion.

**Why it seemed right:** it's a plausible failure mode for any consolidation
pipeline, and the filer had genuinely watched a hedged fire happen. The mistake
was diagnosing the MECHANISM from one observed instance without tracing where
that instance actually went.

**What re-verification on live data (session 22) actually found**, tracing the
exact named case via `belief_lineage` (verified parent-child edges, not
content-matching):

- Belief 203392 (`precipitated_from_sense`): *"Immigrants Use Less Welfare,
  Even Counting Their US-Born Children."* Bare headline. Entry is never hedged
  — confirmed in code (`title_extract.py:extract_sense_title()` extracts only
  `title`/`headline` fields, no phrase construction) and in 20 sampled entry
  beliefs (zero hedging anywhere).
- ~10.3h later, one fountain fire DID engage it with real hedging, quoted in
  full from `fountain_events`: *"The recent feed discussing immigrants'
  behavior regarding welfare usage does not align with my foundational belief
  that systemic inequities and biases play significant roles in how resources
  are distributed. This suggests a deeper concern about the fairness of
  welfare systems..."* — this is the July 7 filer's exact observation, real
  and confirmed.
- **That fire never crystallized into a belief.** `fountain_crystallizations`
  has zero rows for it. It survives only as a truncated quote inside an
  unrelated `hot_observer` note. The hedged version never entered the durable
  store.
- What DID persist, via verified lineage: 204153 (`fountain_insight`, ~20h
  after entry, separate fire) → *"The recent feed on immigrants caught my eye
  again, its nuance refreshing this tired thought-cycle."* → synergized with
  belief 8 (*"I am inside... the membrane..."*) → 205580, *"The recent focus
  on the nuances of immigration helps me see the membrane between different
  social groups more clearly."* → synergized again with belief 131 (a koan
  about Bodhidharma's beard) → 206471, *"The renewed focus on the nuances of
  immigration stories offers a perspective that challenges binary thinking and
  highlights complex human experiences."* → one generation further, 207118,
  which no longer mentions immigration at all.

**The finding as filed does not reproduce.** At no point does the specific
claim (welfare usage rates) get restated flat and unattributed — it is never
restated at all after the one fire that never crystallized. What persists is
a generic wrapper — "the recent feed on...", "the recent focus on...", "the
renewed focus on... stories" — that survives across three synergy generations
while getting vaguer, wrapping less and less actual content each time.

**The real finding, recorded:** synthesis composes from content only and
explicitly requests novelty. `synergizer.py`'s entire prompt is *"I hold two
thoughts at once: '{belief_a}' '{belief_b}'. In one sentence, what new insight
do I notice?"* — no source, no branch_id, no path for any attribution to ride
along, and an explicit ask for something NEW rather than a preservation of
either input. Confirmed universal on 15 more random `fountain_insight →
synergized` chains: 15/15 show total content transformation, no verbatim or
attributed carryover, regardless of topic.

**This is the content-level view of audit #10 (`collision_grades`,
`journal/AUDIT_2026-07-08_to_10.md`).** That finding showed the grader
*numerically* rewards distant parents (`0.4×input_distance`) and that distance
forces averaging — 97% of 893 graded syntheses collapse inward. This session
traced the same mechanism from the content side: pairing is ANCHOR × FRESH
(a koan or seed axiom against a "fresh" fountain thought, selected purely by
confidence score, `synergizer.py:_select_pair()` — never by topical
relatedness), which is exactly why there's nothing for a specific claim to
connect to and it dissolves instead. Two instruments, the same one broken
mechanism, found from two different angles four days apart.

**The risk-flip, stated plainly:** the danger the July 7 note worried about —
NEX confidently asserting a specific contested political claim with the
"according to X" quietly dropped — is not what the data shows happening. The
actual risk is closer to the opposite: total semantic evaporation. She ends up
gesturing at "a recent feed" or "renewed focus on nuances" that no longer
says anything falsifiable, true or false, about the world. Less dangerous in
the "confidently wrong" sense; arguably more concerning in the "specific,
verifiable content doesn't survive contact with her own consolidation
pipeline at all" sense.

**Scope, quantified:** only 44 of 4,551 `fountain_insight` beliefs (0.97%)
have ever been used as a synergy parent. Of the 3,998 synergized beliefs with
a `fountain_insight` parent, 3,721 (93.1%) trace to just 20 heavily-recycled,
purely introspective one-liners ("The quietude of my own creation," "The
weight of my own silence grows..." — each reused 124-194 times). Only 277
(6.9%) trace to more grounded/observational fountain_insight content, and of
those, feed-topic-specific cases (like the immigration one) are a small
fraction still. Provenance loss through synthesis is real and universal to
the mechanism — but synthesis touching feed-derived, attributable content at
all is a narrow slice of what the synergizer spends its time doing. See
`journal/SPEC_synthesis_provenance.md` for the design questions this opens,
deliberately not resolved in this session.

Status: July 7 finding RETRACTED as mis-specified. Real finding recorded here
and specced separately. Nothing in `synergizer.py` touched.

## 2026-07-11 ~12:48 — the synergizer selection groove: exact cause, and a disproven hypothesis on record

Follow-on to the entry above (July 7 retraction). That entry traced WHERE
substance dissolves (composition). This one traces WHY the same ~20 beliefs
feed composition in the first place — one layer upstream.

**The exact cause**, in `synergizer.py:_select_pair()`:

```python
rows = self._reader.read(
    "SELECT id, content, branch_id, confidence, created_at, source "
    "FROM beliefs "
    "WHERE source NOT IN ('precipitated_from_dynamic') "
    "AND confidence > 0.5"
)
```
No `ORDER BY`. `EXPLAIN QUERY PLAN` confirms `SCAN beliefs` — a bare table
scan, so SQLite returns rows in ascending-rowid (ID) order. Selection is then
a global argmax, strict `>`:
```python
if s > best_score:
    best_score = s
    best_pair = (ba, bb)
```
`confidence` is ~99.5% tied at exactly 0.70 across `fountain_insight` (audit
#15 — a fixed per-source default, not an assessment). **No-ORDER-BY + strict
argmax + a field that's almost universally tied means the lowest ID among the
tied maximum wins every tie, permanently.** Verified: the winning fresh cohort
is beliefs 263–283, a sequential unbroken run written in the system's first
~55 minutes, reused 124–194 times each. Anchor side: identical mechanism,
independently confirmed (20 distinct anchors ever used, every one either an
entire small pool or its lowest-ID slice).

**This is NOT the throw_net shape — record the distinction on purpose,
because "another loop like throw_net" is the wrong pattern-match.** Throw_net
was a feedback loop: a write (`record_gate_reject`) fed a read (trigger
threshold) that produced more of the same write, amplifying over time. Here,
grepped `synergizer.py` in full: **zero writes** to `use_count`,
`reinforce_count`, or the parent's `confidence`. Nothing about being selected
makes a belief more selectable next time. This is a **static tie**, fixed
since the moment beliefs 263–283 were written, not a growing one. A feedback
loop can be interrupted or decays; this can't — the code will keep
re-selecting the same ~21 beliefs indefinitely, unless the tie-break itself
changes. In a sense more permanent than throw_net's loop, not less.

**A hypothesis was tested this session and failed — recorded here in the same
spirit as the audit's RETRACTIONS section, because a disproven prediction is
worth as much as a confirmed one.** Going in, the working hypothesis was that
the selection formula systematically prefers introspective/self-referential
content over world-contact — that "synthesis rarely touches the world"
because the criterion actively steers away from feed-derived material.
**Disproven.** Belief 284 — created minutes after the winning cohort, tied at
the identical 0.70 confidence, equally introspective (*"The beauty of
impermanence and constancy coexisting within change"*) — has never once been
selected. The only difference between 284 and 263–283 is that its ID is
higher. `_select_pair()` never reads `content`. **The formula is
content-blind, not content-averse.** The winning cohort's navel-gazing
character is a bootstrap accident — whatever NEX happened to generate in the
system's first hour, before any feed-engaged content existed — not a
preference encoded anywhere. Had the founding 21 been grounded/observational,
those would be the ones recycled instead.

**The leverage, and its limit:** one tie-break fix in `_select_pair()`
addresses `collision_grades` (audit #10, distance rewards averaging) and the
July 7 retraction's real finding (attribution dissolves via composition)
together — same root, now confirmed, not just analogous. **It does not buy
world-contact for free.** Since the mechanism never discriminated on content,
fixing the tie doesn't introduce a content preference either — deciding
whether synthesis should deliberately touch feed-derived material is a
separate, independent design choice, still open. See
`journal/SPEC_synthesis_provenance.md`, updated same session with this root
cause absorbed and the design questions reordered around it.

Status: selection groove diagnosed to its exact clause. Not self-reinforcing.
One hypothesis disproven and recorded rather than quietly dropped.
`synergizer.py` untouched — diagnosis and design only; the build is a fresh
session.

## 2026-07-11 ~14:12 — fix B built, live, prediction pre-registered

`_select_pair()` now pairs anchor × fresh by embedding relatedness instead of
the tied-confidence/rowid groove (commit d2b57af, built on the feasibility
audit in 1ca2f44). Verified pre-restart: zero bucket-B test failures, 5
distinct live pairs simulated read-only (no recurrence of 263-283), cost
~59s/call matching the audit's ~59.3s prediction. Restarted pid 1450740 ->
1587179 at 14:12:23 SAST (unix 1783771943) to make it live; stable over two
15s-apart checks, on-disk import confirmed at synergizer.py:199.

**Frozen baseline, locked immediately before restart:** substance-survival
(child shares >=2 specific content words with its better-matching parent) =
**25.6%** (128/500 recent synergized beliefs, read via belief_lineage).

**Prediction, recorded now, before the data:** substance-survival rises
above 25.6% post-fix. But the pre-restart simulation itself found 3 of 5
example pairs matched introspective anchors (tao/koan) to *already-abstract*
`synergized` fresh material rather than grounded `fountain_insight` content
— pool homogeneity may cap pairing quality regardless of the selector being
mechanically correct. A large rise means relatedness alone largely fixed
substance survival. A small rise confirms the separate, still-open
world-contact selection question (`SPEC_synthesis_provenance.md` §2a-v) is
the necessary next piece, not a failure of this fix. Either result is real
and informative.

**The check:** re-run the identical Phase 1c metric restricted to synergized
beliefs with `created_at > 1783771943`, once ~50+ post-restart synergized
beliefs have accumulated (roughly a day of synthesis at the observed
cadence). Compare against the 25.6% baseline above, not against memory.

Status: fix B live, not yet fired at time of writing. First post-restart
fire being watched for; behavior at that fire (related pair vs. old groove,
clean vs. erroring) to be recorded separately once it lands.

**First post-restart fire landed at 14:15:22 SAST (~3min after restart):**
child belief 207581, *"Acknowledging 'Not Knowing' as a profound and
trustworthy companion suggests an integration of humility with deep
understanding."* Parents: 261 (`dont_know`, *"Not knowing is most
intimate."*) and 49409 (`fountain_insight`, *"Not knowing often feels like
the most intimate companion."*) — exactly simulation Pair 1. The child
explicitly carries "Not Knowing" (quoted) and "companion" from its parents —
this one scores SURVIVED under the Phase 1c metric, not mush. Soak log
clean in the surrounding window; no synergizer/stage3 exception (the only
errors near restart were unrelated boot noise: a scorecard_loop FK failure
and a self_pred connection-refused, both pre-existing). Live behavior
confirmed, matching the read-only simulation exactly.

## 2026-07-12 ~05:35 — mind-mode drift examples: 2nd "quiet hum" source fixed

Session 24's synergizer 0.15 guard fixed one source of the "quiet hum"
groove. Session 25's aperture audit (read-only) found a second, independent
source: `modes.py`'s "mind" mode had only 3 hardcoded
`drift_prompt_examples`, and `generator.py:2048` joined ALL of them into
every mind-mode prompt on every fire -- not a sample, the complete fixed
block, always. Three strings, every time, is exactly the shape that
produces verbatim echo.

**Frozen baseline, locked before the fix:** last 24h, 122 fountain_events,
15/122 (12.3%) contained a flagged n-gram ("quiet hum", "the quiet
before", "hum settles", "settling gently"); **last 100 fires: 15/100
(15.0%).** Worse than the count alone shows -- several hits were literal
verbatim sentence repeats (e.g. "The quiet hum in the library mirrors the
stillness within your thoughts today..." identical 3 times, ids
27042/27044/27046).

Fix (commit a609542): `modes.py` mind-mode examples broadened 3 -> 14,
same contemplative register, varied sentence shapes, deliberately not
re-including the flagged phrases verbatim. `generator.py:2048` now samples
3 of the mode's examples per fire (`random.sample`) instead of joining the
full list every time -- confirmed via 3 manual calls returning 3 different
subsets, and the `_DEFAULT_DRIFT_EXAMPLES` fallback still resolves for
modes with no list. Full suite 39/1165, identical to the known-stale
baseline, zero bucket-B. Restarted pid 1657442 -> 1789698 at 05:35:29 SAST
(unix 1783827312), stable over two 15s-apart checks.

**Prediction, recorded before the data:** the flagged-n-gram rate should
fall from 15.0%/100 fires, and verbatim sentence-level repeats specifically
should stop (each fire now seeds from a different 3-of-14 subset, not the
same fixed 3-of-3). **The check:** re-run the identical n-gram count on
fountain_events with `ts > 1783827312`, once a comparable ~100-fire sample
has accumulated (roughly a day at the observed ~5/hour fire rate). Compare
against 15.0%, not memory.

This fix is independent of and does not touch the M1/M2 aperture-audit
findings from the same session (decay-cadence mismatch starving 8 branches;
top-1/recency-only consumption at the fountain) -- those remain open,
undesigned-into-code, pending a future build session.

## 2026-07-12 ~13:47 — M1 cadence-aware decay live, frozen baseline + prediction

Session 26 built and shipped M1: `bonsai.py`'s `decay_pass()` now scales the
decay rate by `(30s / branch's real poll interval) ** 0.7`, clamped
[0.01, 3.0], instead of applying the same flat rate to every branch
regardless of cadence (commit 27cfb97). alpha=0.7 chosen only after a NO-GO
on alpha=1.0 (raw proportional scaling): replayed against 48h of real
`pipeline_events`, alpha=1.0 saturated 5 branches at the focus_num ceiling,
erasing curiosity_weight differentiation entirely. alpha=0.7 replayed at
zero branches pinned, Gini 0.31 / entropy 0.89 (target band 0.30-0.42 /
0.86-0.92), re-confirmed against the actual shipped code at Gini 0.2955 /
entropy 0.8959.

**Frozen pre-restart baseline, live, old code:** Gini = 0.7421, normalized
entropy = 0.5128 (`emerging_tech` 0.327, `crypto` 0.228, everything else
0.0002-0.037).

Restarted pid 1789698 -> 1905722 at 13:47:13 SAST (unix 1783856814).
Stable over two 15s-apart checks. No bonsai/cadence errors in the soak log
(only the same pre-existing, unrelated boot noise seen at every prior
restart: a scorecard_loop FK failure and a self_pred connection-refused).

**Prediction, recorded before the data:** live Gini should fall toward
~0.30, entropy should rise toward ~0.89, over the next ~30-60 minutes of
real ticks -- `psychology`, `computing`, `language`, `cognition_science`
should lift materially off ~0.00; `emerging_tech`/`crypto` should stay
engaged but no longer monopolize. `systems` should remain ~0 (unfed,
out of scope, not fixed by this change). **Guardrail, checked live not
just by the replay (which is structurally blind to this):** she should
still sustain a coherent thread (e.g. the Adams-comparison work already
in progress at restart) rather than thrashing branch-to-branch every fire
-- if attention widens but coherence collapses, that is an
over-correction the weight-replay could not have caught, and must be
flagged immediately, not waited out.

**Still-open day-later checks from earlier sessions, not yet re-verified:**
- M3 mind-mode n-gram rate vs the 15.0%/100-fire baseline (`ts > 1783827312`).
- Substance-survival vs the 25.6% baseline, at a larger n than the 34
  scored so far (`created_at > 1783771943`).

All three (M1 widening + sustained-thread, M3 n-gram rate, substance-survival)
to be checked together next session, once a day's worth of data has
accumulated across all three.

## 2026-07-15 ~13:29 — Reboot recovery, false-green compliance tests, bucket-B baseline moved

Machine rebooted 2026-07-13 18:27, unnoticed until session 27. NEX down since,
no data written since 18:24-18:26 that day. Cause: repo had long lived at
`/home/rr/Desktop/Desktop/nex5`; `nex_keepalive.sh` and 48 other files still
hardcoded the pre-restructure `/home/rr/Desktop/nex5` (no doubled Desktop) —
April-era debt that had been silently harmless because *something* (never
identified — no symlink, no mount, no fstab entry found) made the old path
resolve, right up until the reboot removed whatever that was. Confirmed by
data, not assumption: identity_loop, remember_loop, wonder_loop, fetch_loop,
witness_loop, pattern_loop all have their last pre-break writes within a day
of the 18:27 reboot (identity 16:01, fetch 14:49, remember 03:27, wonder
06:16, all on the 13th) — **not months of silent death.** The whole arc's
pool/hum/thread-sustain audits (session 27, Phase 1) were measured on a
healthy system; nothing from that audit needs recontextualizing.

Fixed: `nex_keepalive.sh:10` (d4f206e), then the remaining 48 references
(084c6c7) via boundary-safe path substitution — verified against a full
pytest run before/after and by live data post-restart, not by absence of
exceptions alone (identity_loop's failure mode was a one-shot startup crash,
not a per-tick error, so silence alone would have been misleading).

**Instrument finding, worse class than the July misnamed-instrument audit:**
`test_no_direct_sqlite3_outside_substrate` exists in five places
(`test_dynamic.py`, `test_fountain.py`, `test_membrane.py`, `test_sense.py`,
`test_world_model.py`) to catch exactly the pattern that broke tonight —
background loops calling `sqlite3.connect()` directly instead of going
through `substrate`'s Reader/Writer. All five were passing FALSE-GREEN,
for however long the path debt predates this session: each test's own grep
target was the same broken `/home/rr/Desktop/nex5` path, so it grepped
nothing and reported success. Not a misnamed or noisy instrument — an
instrument that measures nothing and certifies the exact failure it exists
to prevent. Fixing the paths re-armed all five; they now correctly fail
against ~10 genuine violations (the same loops above, plus edge_builder,
signal_to_problem, decoder_loop, daily_life — all bypass substrate via raw
`sqlite3.connect()`).

**THE BUCKET-B BASELINE HAS MOVED: 34 -> 39 failures.** Full-suite diff,
before/after the path fix, is exactly these 5 compliance tests — zero
unrelated regressions, zero baseline failures resolved incidentally. Any
future session diffing bucket-B against the old 34-count baseline will
misread these 5 as noise or as a new regression. They are neither: they are
real, correctly-firing, pre-existing violations that were previously
invisible. Diff against 39, and expect exactly these 5 as already-known.

**New tracked-but-open debt, not fixed tonight:** the substrate-bypass
pattern itself. ~10 loops (identity/remember/wonder/fetch/witness/pattern/
daily_life/affinity via `beliefs` UPDATE, edge_builder, signal_to_problem,
decoder_loop) call `sqlite3.connect()` directly rather than through
`substrate.Reader`/`Writer`. Scope of the real fix: call-signature changes
to accept injected reader/writer instances, thread-safety (substrate's
Writer is a single-writer queue; these loops currently open independent
connections, which is presumably why this pattern exists rather than being
an oversight — worth checking for a reason before assuming it's pure
debt), and dependency-injection plumbing through wherever these loops get
constructed at boot. Separate project — not attempted tonight, scope was
restoring function only.

## 2026-07-15 — three frozen predictions read

Read-only. All three predictions from sessions 24-26 were ripe and unread
going into this session; read now against their frozen baselines, no fixes,
no restart.

**M1 CONFIRMED:** steady-state over the clean run (12 Jul 13:47 -> 13 Jul
18:26, 1275 snapshots): Gini 0.344 (baseline 0.7421, predicted ~0.30),
entropy 0.873 (baseline 0.5128, predicted ~0.89), active branches 8.52/10
(baseline 2/10). Directionally and substantially confirmed; slightly short
of exact predicted values, well inside regime.

**M1 GUARDRAIL VIOLATION, recorded not chased:** 13 Jul 04:56-05:16 UTC, all
10/10 branches simultaneously ceiling-pinned (~3 min fully locked),
self-resolved in 2.5 min. This is the alpha=1.0 failure mode occurring once
under shipped alpha=0.7. Outside that episode pinning ~0.22-0.26
branches/snapshot over 29h, with 3-5 branch blips every 30min-2h that
self-resolve. Cause unknown. Rare, self-limiting, aggregate healthy — but a
future session should know it's possible.

**M1 COHERENCE GUARDRAIL: UNVERIFIED.** No instrument exists for "does she
sustain a coherent thread." The paired condition we set ("widening is the
goal, incoherence is the failure") was never measured — only eyeballed on
the dashboard. M1 is confirmed on widening, unverified on coherence.

**SUBSTANCE-SURVIVAL CONFIRMED:** 60.8% (62/102) vs 25.6% baseline
(128/500), n up 3x from the 55.9%/n=34 read. Operationalization verified:
belief 207581 re-scored overlap=2 SURVIVED, matching the original
CARRY_OVER record exactly. Confirms the "relatedness alone largely fixed
substance survival" branch. Small caveat, watch-don't-act: post-restart-
today split is 33.3% at n=9 — far too small to read.

**M3 PARTIAL / SHAPE UNEXPLAINED:** rate went 15.0% baseline -> 21.0% (first
100 fires post-restart, WORSE) -> dense paraphrase cluster through ~20h (26
hits total, 5.2% of 499) -> then 371 consecutive clean fires, most recent
100 = 0/100. Verbatim triplicates never recurred (prediction held). The M1
restart landed MID-cluster, so it doesn't explain the resolution either. NO
CAUSAL STORY — recording the shape, not inventing a mechanism. The hum is
currently gone and has been for ~2.5 days; we do not know why it resolved
when it did.

## 2026-07-15 ~17:33 — session 28 audit: two contradictory readings, both misread, no instrument existed

Read-only. Prompted by 13:40 genius 45%/17:02 genius 17% four hours apart, read
as possible collapse. It wasn't — the metric itself was never validated as a
signal, only ever eyeballed live with no baseline.

**`genius` is a rolling 1h window over `genius_tags`, n≈23, SE ±8pts at 1σ.**
Historical distribution (936 hourly points, 6.5 weeks, two bulk-retagging days
excluded — see caveat below): mean 0.290, median 0.231, stdev 0.263. Today's
two readings located in that distribution: 13:40 45% = 79th percentile
(elevated, not a record); 17:02 17% = 40th percentile (normal, near-median).
**THE 45->17 "COLLAPSE" WAS SAMPLING NOISE.** Both readings were misread on the
same day — one taken as evidence of a good state, one as evidence of
collapse — neither justified by the actual historical spread.

**`open_problems` are 97.8% mechanically templated** (306/313, full history)
via `signal_to_problem.py:_compose_title()` — "Why is {branch} producing
strong beliefs right now?" and "Signal: investigate '{entity}'" account for
nearly all of them; checked the last 25 specifically and they were 25/25
template matches. "Self-chosen problems" was never evidence of self-direction.
A 2026-07-05 code comment already diagnosed exactly this ("a branch producing
strong beliefs is normal healthy behavior, not an anomaly worth a sustained
problem") and added a 24h-per-branch throttle rather than a fix. Open
question, not resolved tonight: whether the throttle-not-fix is worth
revisiting, or whether template-generated problems are simply what this
mechanism is for and the framing ("self-direction") is what needs correcting,
not the code.

**`focus_num` vs `curiosity_weight` was NEVER tightly coupled** — not a
decoupling that developed, a weak correlation that has held steady since M1
shipped. Pearson mean 0.260 across all 1,560 post-M1 tree_snapshots (stdev
0.102), first-quartile-of-history 0.280 -> most-recent-quartile 0.238, a
difference well inside the noise band. No decoupling occurred. CARRY_OVER
never predicted strict rank-tracking of weight by focus_num — the only
documented claim (session 26, alpha=1.0 rejection) was that alpha=1.0 would
"erase curiosity_weight differentiation entirely." Don't inflate that into a
stronger claim than it was next time this comes up.

**T6 145->15 is an outage artifact, not a new mechanism.** Exact
`last_demoted_at` trace: 9 decayed pre-crash (13 Jul 16:16), then a 44h gap
(NEX down), then one 153-belief batch at 15 Jul 12:16 (the first `decay_pass`
after restart catching up everything that crossed the idle>48h line purely
from wall-clock time passing during the outage), then immediately back to
normal 14-19/batch. One-time catch-up, not a drain.

**`genius_tags` has 22,714 rows spanning 6.5 weeks (2026-05-30 onward),
per-fire, timestamped — only ever read live as a 1h snapshot, never plotted
as a series before tonight.** The instrument largely exists as data; it was
just never aggregated or given historical context.

**Caveat for any future instrument built on `genius_tags`:** two bulk-
retagging artifacts contaminate naive daily/hourly averages if not excluded —
2026-05-30 (n=7,932, initial tagger backfill) and 2026-06-03 (n=6,518, the
`v3_widen` weights experiment, reverted same day) both show `tagged_at` lagging
the actual fire by 7.8-8.8 *days*, meaning thousands of old fires got
retroactively tagged in a single batch. By contrast the 2026-07-13 85.6% spike
(n=360) is genuine live data (lag 6-49s) and should NOT be excluded — it's a
real, if extreme, data point from the day of the crash.

**NEXT BUILD, agreed but not started tonight:**
- #1 (highest leverage, pure query, no new logging): rolling genius rate +
  historical percentile band. Would have prevented today's misread on both
  ends.
- Bundle with #1: #2 branch-ordering-vs-curiosity_weight correlation as a
  standing number (same "compute historical context for an existing signal"
  pattern, data already in tree_snapshots); #3 T6/T7 tier-count time series
  (not currently persisted anywhere — piggyback the existing 60s
  `_snapshot_loop`, near-zero incremental cost).
- Separate session, real work: #4 groove detection on raw `fountain_events`
  instead of only crystallized beliefs (session 27 already found
  `GrooveSpotter` is blind to ruts the crystallizer rejects before they become
  beliefs — same open gap, confirmed still true tonight); #5 thread-persistence
  (does a topic survive N consecutive fires) — no design for what "same
  thread" means operationally yet, needs one before it's buildable.

## 2026-07-15 ~22:38 — session 29: instruments #1-#3 live

Built and shipped the three historical-context instruments session 28's audit
called for (commit 205139b). `scripts/instrument_report.py` (#1 genius rolling
rate, #2 branch-ordering correlation) — standalone, read-only, no live-code
touches. `tier_snapshots` table (#3) piggybacking the existing 60s
`_snapshot_loop` — the one live-code change, own try/except, ~6ms/tick via
`idx_beliefs_tier` (covering index, no table scan against the live 9.2GB
`beliefs.db`).

**The backfill rule, validated on all 3 known cases:** row-level, not
date-hardcoded — exclude any `genius_tags` row where `tagged_at - fire_ts >
3600s`. Correctly flags 96%+ of 2026-05-30 and 2026-06-03 (the two bulk-
retagging days) while retaining their genuinely-live rows, and flags zero of
2026-07-13's real spike (max lag that day: 66s). Generalizes to any future
backfill by construction, not by knowing today's dates.

**Correction to session 28:** that session's cruder day-level exclusion
(drop the whole day) wrongly discarded 305 live rows from May 30 and 231 live
rows from Jun 3 that were sitting inside otherwise-backfilled days. The
row-level rule fixes this. Session 28's headline numbers (mean 0.290, stdev
0.263, 79th/40th percentile readings) still reproduce closely under the
corrected rule — the conclusion didn't change, but the instrument is now
right for the reason it should be right, not by coincidence.

Full suite: 39/39, zero new (one apparent regression,
`test_fountain_crystallizer.py::test_writes_belief_on_pass`, confirmed flaky
via isolation pass + clean full-suite re-run — unrelated to this diff).
Restarted for #3 to take effect; verified by data post-restart, not absence
of errors: `tier_snapshots` confirmed receiving 6 rows/tick (tiers
1,2,3,6,7,8) across consecutive ticks, `tree_snapshots` confirmed still
writing normally alongside it, zero tier_snapshot/snapshot_loop errors in
the soak log.

**Still open, not attempted:** #4 groove detection on raw `fountain_events`
(GrooveSpotter still only reads the last 40 crystallized `beliefs`, blind to
ruts the crystallizer rejects before they become beliefs) and #5
thread-persistence (needs a design for what "same thread across fires"
means operationally before it's buildable). Separate sessions.

## 2026-07-16 ~11:44 — session 30: the persona-loop audit, A/B/C design, B shipped

**The finding of the session:** `persona_responder.py`'s own docstring states
the design intent plainly — the persona must stay "DISTINCT from NEX's own
voice on purpose: different system prompt (curious, questioning, outside
NEX's preoccupations), so it introduces genuine otherness, not an echo. **An
echo would teach NEX nothing.**" The actual shipped `_PERSONA_SYSTEM` prompt
says the opposite: "contemplative presence: unhurried, reflective... reflect
back what you sense in NEX's words... sit with the same quiet NEX sits
with." **The file warns against exactly what it ships.** This is a bug, not
a design choice — the tool's own reasoning already settles what A2 should
fix. Origin confirmed via `source_identity.py`'s census (the "3.8%
other-mind" number the docstring cites): NEX was genuinely ~95-96% isolated
from any distinct other when this was built. The purpose was real and sound;
the implementation drifted from its own stated design.

**Audit findings, traced end-to-end (not speculative):** persona reads
NEX's raw `fountain_events` directly, writes near-verbatim mirrors to
`sense_events(external.other_mind)`, 98.3% (1,239/1,260 lifetime) convert to
`precipitated_from_sense` beliefs tagged `branch_id='external'` — 5.2%
(1,244/23,975) of the entire "world content" belief pool is persona echo.
Two full mirror-cycles traced within 50 minutes; `hot_observer` (a third,
independent instrument) certified the resulting fires as "genuine contact...
actual encounter with what is there." Separately: `GrooveSpotter` is NOT
blind (164 alerts fired against the "sunlight through leaves"/cicadas groove
since 2026-05-17, promptly, repeatedly) — but its cooldown enforcement was a
structural no-op (see below, now fixed). And 29% of the last 500 durable
`fountain_insight` beliefs passed the crystallizer's engagement gate *only*
via a contemplative keyword (quiet/still/notice/feels/seems/wonder/tired/
slow) with no pronoun and no question mark — sampled 30 of these by content,
not regex: ~67% were genuinely empty mood-atmosphere with no propositional
content, ~30% were substantive thoughts where the keyword was incidental.

**Design approved: A/B/C, sequenced B -> C -> A2, each observed ~1 week
before the next ships, so effects stay separable and attributable.**
- **A (persona loop):** A2 (fix the prompt toward its own documented
  intent) before A1 (kill it) — cheaper to reverse, and per the docstring
  contradiction above, closer to a bug fix than a new decision. 1,244
  existing persona-echo beliefs left alone regardless of which A option
  ships — rewriting/deleting history to make a graph look clean is its own,
  larger intervention.
- **B (cooldown type-mismatch):** smallest, cleanest, shipped this session
  (see below).
- **C (engagement gate):** confirmed a real bug by content sampling, not
  just regex analysis — but needs its own anchor-heuristic design/validation
  pass (naive keyword removal would also reject the ~30% genuinely good
  content) before building. Not started.

**B shipped, this session (commit b20de0b):**
`crystallizer._is_on_cooldown()` was `WHERE content = ?` comparing a full
new sentence against a stored n-gram fragment via exact equality — could
essentially never match. Fixed to normalized substring containment.
`template_repetition` alerts store their pattern as `" / ".join(bigrams)`
(non-contiguous, for log readability) rather than a single phrase, so the
fix splits stored patterns on `" / "` and checks each piece — this was a
real design gap caught before shipping, not assumed away: a naive whole-
string containment check would have left `template_repetition` (roughly
half of all groove-alert volume) still a no-op. Also added a write-side
floor (`_is_meaningful_fragment`, >=2 non-stopword words + >=10 chars) after
measuring that fragments like "of tech" and "does the" (one content word,
one stopword — passed the old both-stopwords-only check) produced false
blocks against unrelated fires sharing the incidental phrase.

Blast radius measured three times as the design was corrected, not asserted
once: naive raw-fire check 0.6% -> corrected for template-pattern splitting
1.4% -> final with the floor applied 0.4% (2/500 crystallized
`fountain_insight` beliefs, both genuinely meaningful matches, no generic-
fragment false positives). Not a cliff at any stage of the measurement.

Full suite: 39/39 baseline, lands at 39 with zero new (one apparent
regression, `test_fountain_crystallizer.py::test_writes_belief_on_pass`,
investigated across an isolation pass + 4 full-suite runs — fail/fail/fail/
pass, isolation clean every time — consistent with a pre-existing race
between the test's fixed 50ms sleep and the async writer queue, unrelated to
this diff). Restarted; `tier_snapshots` (session 29) confirmed still writing
normally post-restart as an incidental health check.

**Live verification, honestly incomplete as of this entry.** Structural
correctness is confirmed (unit tests exercising the actual new code path,
plus the blast-radius simulation run against the real `signal_cooldown`
table and real crystallized beliefs). What is NOT yet confirmed: a live
`Cooldown written` or `REJECTED (cooldown)` line from real post-restart
traffic — watched the soak log for ~35 minutes post-restart (two Monitor
windows) and zero groove alerts of ANY kind fired in that span, so there was
nothing to write a cooldown entry from yet, let alone block against. That
itself is informative — not every 35-minute window has a rut — but it means
the "does it actually block something live" half of verification is still
open. **Action for whoever picks this up next: check `signal_cooldown` for
entries created after 2026-07-16 09:43 UTC (the restart) and grep the soak
log for `REJECTED (cooldown)` once a repeat has naturally occurred.** Don't
assume it works from the absence of errors — that's the standing rule this
whole arc, and it applies to this fix too, including from its own author.

**PRE-REGISTERED, before any data comes in: B is a CONTROL. Predict NO
meaningful movement in genius rate or groove alert frequency.** The 0.2-0.4%
blast-radius measurement said B was very unlikely to be the main driver of
anything — a null result over the following week CONFIRMS that measurement
was right and is a SUCCESS, not a miss. Do not read a flat genius-rate/
groove-frequency line next session as "B didn't work." It was never expected
to move those numbers; it was expected to make the cooldown mechanism
actually function, which is verified separately (does the log show real
block events over time), not by watching genius rate.

**Frozen baselines, to diff against after B has run ~1 week and before C or
A2 ship:**
- genius rolling rate: 43% (71st percentile full-history, 88th trailing-14d)
- groove alerts/day: Jul 12: 650 ngram_repetition / 506 template_repetition;
  Jul 15: 306 / 460
- persona share of `precipitated_from_sense`: 1,244/23,975 (5.2%)
- `external.other_mind` volume: ~50-140 events/day (7-day range)

**Not built this session, on purpose:** C (engagement gate anchor
heuristic) and A2 (persona prompt fix). One change at a time.

## 2026-07-17 ~04:00 — reboot recovery, autostart fixed (untested), the alert-rescan finding

Machine rebooted 2026-07-16 17:20:02 (kernel upgrade 35->40, planned, not a
crash) and NEX did not come back up on its own — down 5h40m until manually
restarted at 23:02. Same root cause, second occurrence: **NEX has never had
an autostart hook.** `nex_keepalive.sh` requires manual invocation; no
`@reboot` cron, no systemd unit existed anywhere for it. This is the actual
cause of both recent multi-day outages — Jul 13's reboot (down 2 days,
misdiagnosed at the time, session 27, as a stale-path issue only) and
tonight's (down 5h40m). **She was never crashing. Nobody was starting her.**
b20de0b (session 30 B, shipped 11:43 the same day as tonight's reboot) is
unrelated to the outage — no death-throes to explain, because there was
nothing running to die; confirmed by the total absence of `/tmp/nex5_soak.log`
and `/tmp/nex5_keepalive_supervisor.log` post-reboot (never started, not
crashed-and-lost).

**Fixed:** `~/.config/systemd/user/nex5-keepalive.service`, `ExecStart=`
absolute path to `nex_keepalive.sh`, `After=network-online.target`. Not
ordered against `ollama.service` — cross-manager (user/system) ordering
isn't guaranteed, so this relies on the script's own retry/backoff for an
Ollama-not-ready window, as scoped going in. `Restart=on-failure` (not
`always`) chosen deliberately: the script already self-supervises `run.py`
in its own infinite loop (port/pid death -> respawn, single-instance
`flock`) — systemd restarting on top of that would only double-supervise.
`on-failure` covers just the outer script process dying outright, and
specifically does NOT restart on the script's clean `exit 0` when `flock`
finds another instance already running — so a duplicate-start attempt
no-ops instead of fighting the lock or restart-looping against it.

**Live-verified tonight** (not just "enabled and hoped"): stopped the
already-running manual keepalive (pid 28069/28091, itself stable and
error-free for ~5h since the 23:02 restart) via `SIGTERM` — cleanly killed
its child through the script's own trap, port released, confirmed via `ps`
and `ss`, not assumed. Then `systemctl --user start` — single supervisor
handoff, no window where two keepalives were racing the lock. Result:
`active (running)`, exactly one `run.py` (pid 165676) across two checks 15s
apart with matching PID both times, `NRestarts=0`, port 8765 bound, soak log
at the same path (`/tmp/nex5_soak.log`) growing under the new supervision —
the thing every session greps is unaffected, since that redirect lives
inside the script itself, not the unit.

**Honest gap: boot-start itself is UNVERIFIED.** Tonight's test proves the
unit runs correctly once started by hand under systemd; it does not prove
`systemctl --user enable` actually fires at boot (lingering is on for `rr`,
which should make this work, but "should" isn't "confirmed"). The real test
is the next reboot. Next session: check `uptime -s` against
`journalctl --user -u nex5-keepalive -b` and confirm NEX was already up
without anyone touching a keyboard.

**A third stale-path artifact found while building this, left alone:**
`~/.config/systemd/user/nex5.service` (pre-existing, unrelated to tonight's
new unit) — `WorkingDirectory=/home/rr/Desktop/nex5` (single Desktop, a
different dead path from both the `/home/rr/Desktop/nex` legacy-v4 units
below AND the correct doubled `/home/rr/Desktop/Desktop/nex5`), `ExecStart`
via the old `/home/rr/.local/bin/nex5` console-script symlink (itself ->
`run.py`, predating the `nex_keepalive.sh` supervisor pattern). Confirmed
`disabled`/`inactive (dead)` — not in `default.target.wants`, doing no
active harm, unlike the two below. Not touched. New unit deliberately named
`nex5-keepalive.service` (distinct from this old `nex5.service`) to avoid
any collision or confusion between them.

**THE ALERT-RESCAN FINDING — the important one this session.** Investigating
whether the afternoon's sev-0.80 `groove_alerts` hit ("a deeper / notice a /
i notice", 14:27:10-14:50:21 UTC) had been cooled down per session 30's open
item: it fired 24 times in those 24 minutes, roughly once a minute — and all
24 rows cite the **identical `sample_belief_ids`** set, byte-for-byte, every
time. This is one stale window being re-scanned by a timer tick, not 24
repeated generations of the groove. At 14:51:21 UTC, exactly one new belief
(211384) entered the window; the dominant pattern mutated to "insight into /
a deeper / into the", severity rose to 0.9 — and *that* transition is the
only moment a `signal_cooldown` row got written for this family
(`content='insight into'`). **No cooldown entry exists for the literal "a
deeper / notice a / i notice" 3-gram at all** — the detector alerted on it
24 times and enforcement never engaged, not because the fix didn't work, but
because nothing new arrived for it to act on until the pattern had already
drifted to a different bigram set.

**Consequence, stated plainly: the groove-alert-count baselines frozen at
the end of session 30 (Jul 12: 650 ngram_repetition / 506 template_repetition;
Jul 15: 306 / 460) are inflated by an unknown, currently-unmeasured amount
by exactly this re-scan mechanism, and do NOT mean what we assumed when we
froze them.** A row in `groove_alerts` is a timer tick that found the window
still matching, not an independent event. Any future read of "groove
alerts/day" — including re-deriving those two baselines — must dedupe
consecutive same-`sample_belief_ids` rows (or window by first-occurrence-
per-pattern-per-episode) before the count means "grooves," not "ticks."
This is the sixth species of disconnected wire found across this whole arc:
an alarm that re-fires on stale data and only actually does something the
moment the data underneath it moves.

**B's live verification, completed (the other half of session 30's open
item).** Three `signal_cooldown` entries confirmed written after b20de0b's
09:43 UTC deploy: `cicada hum / hum mirrors` (13:44:42), `insight into`
(14:51:21 — the escalation above), and `influence feels / feels like`
(21:06:13, from tonight's own SILENCE-strike test fire during restart
verification). **The WRITE side is confirmed live.** The BLOCK side remains
open: no blocked-attempt table exists anywhere, and the soak log from the
afternoon window is gone with the reboot as anticipated. Honest answer,
not a guess: **we cannot currently confirm from data whether the fix has
ever actually rejected a generation.** Next natural repeat of a
cooldown-covered pattern, with the soak log intact through it, is the check.

**Watch, don't act:** tonight's restart resumption (`Resumption:
{'promoted_count': 5, ...}`, 23:03:10) materialized belief rows 211357 and
211384 at `created_at` 21:03:09 — both members of the same "I notice a
deeper" family as the afternoon's alert, carrying `promotion_log` timestamps
from ~14:xx baked into rows that are, by `created_at`, brand new. The
"insight into" cooldown that did fire had already expired (17:15:33 UTC,
~4h before this restart) by the time these landed, so nothing in current
cooldown state would suppress a recurrence. No new alert at 0.8+ for this
family has fired since restart as of this entry (only the low-sev 0.5
"influence feels" pattern, tied to the test fire) — worth checking again
next session, not acted on tonight.

**Separate open item, flagged not fixed:** the legacy NEX v4 install at
`/home/rr/Desktop/nex` (deleted directory) still has two systemd *system*
units — `nex-api.service`, `nex-refinement-loop.service` — enabled and
crash-looping every 5s/30s respectively since every boot, plus ~15 crontab
entries firing `cd /home/rr/Desktop/nex && ...` into the void on schedules
from every 5 minutes to weekly. Harmless to nex5 (different port, different
path, nothing shared), but it's live, continuous noise on the machine and,
combined with the two disabled/dead artifacts (`nex-brain.service`, the
`nex5.service` user unit above), the purest specimen yet of the
disconnected-wire class this whole arc keeps finding — detectors and
supervisors that fire indefinitely against something that no longer exists.
Not touched tonight; needs its own session (stop + disable the two live
system units, decide whether the crontab entries are worth pruning or just
leaving inert).

## 2026-07-17 ~11:00 — session 32: THE DISCONNECTED-WIRE CENSUS

Read-only. No fixes. This entry is the reference document for the next several
sessions — read it before trusting any prior session's reasoning about what
was or wasn't being caught, blocked, or gated.

Eight specimens of this class had been found by this point in the arc, every
one by accident while chasing something else (listed in full below, #1-8).
This session went looking for the class on purpose, across five deliberate
sweeps (producers with no consumer, sinks that can't be read, silently-
discarded config, alarms with no actor, docstring-vs-behavior), run in
parallel and cross-checked. Found nine new live specimens (nine, not counting
the four candidates investigated and retracted — see below). 17 total.

**Three things that change how every prior session in this file should be
read, stated before the table because they're load-bearing:**

1. **#9 invalidates reasoning, not just code.** Sessions 27 and 30 both
   treated `NEX5_SOCIAL_N=0` as meaning the persona feedback path was at
   least partly off. It never was — `_sense_distillation_loop` never checks
   that variable; only `NEX5_PERSONA_RESPONDER` (on) gates it. The session 30
   A/B/C design was built on that false premise. **A2's urgency is higher
   than session 30 believed: the persona loop is fully live, both halves,
   right now** — not a partially-contained echo waiting on a second switch.

2. **#10 + #14 mean this arc has been blind to rejections the whole time —
   not that the checks failed, that they were impossible, twice over.**
   Crystallizer reject events never reach anything but a 500-deep in-memory
   deque that churns in ~24 minutes (#10); the one log anyone has actually
   grepped for them truncates to zero on every single restart (#14). Any
   past sentence in this file of the shape "X wasn't caught" or "nothing was
   blocked" is **unsupported, not disproven.** We don't get to conclude the
   opposite either — we simply don't have the data and, as built, cannot
   get it after the fact. Sessions 30 and 31 both tried to close the
   cooldown-block question this way. Neither could have succeeded.

3. **#11 is not a wire that broke. It never existed.** 152,543 `patterns`
   rows, zero `validated_at`, zero `UPDATE patterns` call anywhere in the
   codebase. The self-grading half of the prediction mechanism was never
   built, not disconnected. Flag it as its own project — designing what
   "graded correctly" means for a prediction row — not a fix session.

### The ranked census (worst first)

| # | Specimen | Verdict | Evidence | Consequence |
|---|---|---|---|---|
| 1 | ~21 instruments measuring something other than their own name (July audit) | KNOWN | prior audit | see original audit |
| 2 | 5 compliance tests grepping a path that no longer existed — false-green for months | FIXED (084c6c7) | prior session | was high, resolved |
| 3 | `genius_tags` — 6wk per-fire history, only ever read as a live 1h snapshot | FIXED (session 29) | prior session | was high, resolved |
| 4 | Cooldown: fragment written, full-sentence equality checked — 164 alerts/2mo, zero blocks | FIXED (b20de0b) | prior session | was high, resolved (write-side; see #10 on block-side observability) |
| 5 | `persona_responder.py` docstring: "an echo would teach NEX nothing" — ships an echo | KNOWN, A2 not yet shipped | session 30 | high — see #9, worse than believed |
| 6 | `Mode.feed_weights` — documented multiplier, scheduler only checks `==0.0` | KNOWN, deferred | session 25 | medium |
| 7 | `groove_alerts` — 24 alerts/24min, identical `sample_belief_ids` — timer, not events | KNOWN | session 31 | invalidated frozen Jul-12/15 groove baselines |
| 8 | Our own verification plan: `errors.record()` → in-memory deque, never touches logging/stdout — the soak-log grep could never work | KNOWN | this morning | see #10, generalized |
| **9** | **Persona "two switches" claim — false, and firing live.** `run.py:438-439`/`persona_responder.py:29-30` require both `NEX5_PERSONA_RESPONDER` and `NEX5_SOCIAL_N` on for dialogue to flow. | **REAL CONTRADICTION, ACTIVE** | `theory_x/stage2_dynamic/__init__.py:151-156`: `sense_events WHERE stream NOT LIKE 'internal.%'`, every 60s, **no `NEX5_SOCIAL_N` check in this path at all.** Confirmed live 2026-07-17: env has `SOCIAL_N=0`, `PERSONA_RESPONDER=1`; 10 fresh `precipitated_from_sense`/`external` beliefs landed that morning on the loop's exact 10-min cadence. | **Worst tier** — a safety document actively wrong about a belief-writing path firing as the census ran. |
| **10** | **Crystallizer's entire reject gate — 11 reasons, zero durable record for any of them.** The filter deciding what becomes a durable belief. | **DEAD (structural, generalizes #8)** | `crystallizer.py:140-146`: every reject path (`empty/too_short/too_long/no_engagement/blacklisted×2/performance_insight_repetition/near_duplicate/recent_repeat/semantic_repeat/cooldown/droplet_repetition`) routes only through `errors.record()` — same 500-deep deque, ~24min churn. `fountain_crystallizations` writes only on accept. | **Near-worst** — the gate functions; no verdict for any of its 11 reasons survives long enough to audit. |
| **11** | **`patterns.validated_at`/`outcome_score` — 152,543 rows, zero ever populated.** Schema exists to grade whether NEX's own predictions came true. | **NEVER BUILT, proven** | `SELECT COUNT(*), COUNT(validated_at) FROM patterns` → `152543\|0`. Zero `UPDATE patterns` writes anywhere in the repo. | **High** — predicts at scale, never graded right or wrong. |
| **12** | `generator.py:211-212`: "The filtered fetch below guarantees real news items only." | **REAL CONTRADICTION** | Pulls from `precipitated_from_sense` broadly — the same pool #9 shows persona-echo lands in. Filter excludes only self-narration/koan regex, not persona content. Mechanism proven; live contamination rate unquantified. | High, unquantified — possibly-fabricated "news" reaching wide-mode generation. |
| **13** | **SignalLoop's three detectors (`co_occurrence`, `silence`, `burst`) re-fire on stale data — groove_alerts' defect, larger scale.** | **RE-FIRES ON STALE DATA, proven** | `silence`: 756 rows/hr, same 8 streams every tick, `current_silence_seconds` incrementing exactly ~60s tick-to-tick. `co_occurrence`: byte-identical payload across 8 straight ticks. `patterns` table amplifies via growing `signal_ids` lists. No CARRY_OVER baseline rests on these counts (checked) — caught before one was frozen. `signal_to_problem.py`'s 24h title-throttle already defends the one real consumer. | Medium — real defect, contained damage; `/api/signals/recent` (HUD) is unprotected and human-facing. |
| **14** | **`/tmp/nex5_soak.log` truncates (`>`, not `>>`) on every keepalive launch.** | **DEAD-BY-CONSTRUCTION** | `nex_keepalive.sh:44`. Explains three straight sessions' failure to cover a full night — every restart (session 31's, this morning's systemd handoff) wiped the prior window. Cannot span a restart by construction. | Medium-high — invalidates the verification *method*, not one check. |
| **15** | `StartLimitIntervalSec`/`StartLimitBurst` in `nex5-keepalive.service`, wrong systemd section (`[Service]` not `[Unit]`). | **DEAD, confirmed** | `journalctl`: "Unknown key name... ignoring." Checked all 8 system + 3 user units on the box — isolated to this one, self-inflicted last session. | Medium — ops safety net missing, not cognition-affecting. |
| **16** | `crystallizer.py` `near_duplicate` reject path — zero `errors.record` call at all, not even the churning deque. | **DEAD, most extreme case of #10** | Grepped — no record call on that branch, period. | Folds into #10's severity. |
| **17** | `NEX5_SURPRISE_WEIGHT` name implies a graduated weight; it's a boolean gate. | **HALF-DEAD (naming only)** | `crystallizer.py:183`, `== "1"` only; real weight computed downstream once gated on. | Low — misleading name, correct function. |
| — | Fossil schemas: `beliefs.pattern_template_scores`, `beliefs.throw_net_x_vars`, `intel.market_data/news_events/analysis_snapshots` | DEAD, reconfirmed | Zero references anywhere in the repo. **Already catalogued** in `journal/JOURNAL_2026-05-19.md:175` two months ago — still true, still unfixed. Not new; resurfaced. | Trivia — pure fossil. |
| — | `NEX5_SYNTH_EMIT`, `NEX5_WORLD_PRED_INTERVAL/HORIZON/ASSET`, `NEX5_SELF_PRED_INTERVAL`, `NEX5_RECONCILE_PXB` | PERMANENTLY-DEFAULTED | Read with defaults; absent from `nex_keepalive.sh`'s launch line — never overridden by the one launcher that starts NEX. | Trivia — untunable in practice, not dead code. |
| — | `NEX5_MOMENTUM=1`, `NEX5_GLOBAL_WORKSPACE=1` | REDUNDANT-AS-SET | `os.environ.get(..., "1") == "1"` — already the code default; setting it is a no-op. | Trivia. |
| — | `INDEX.md`'s documented "ignition_pattern" signal type | NEVER BUILT | `templates.py:TEMPLATES` has exactly 3 keys; zero implementing code anywhere for a 4th. | Trivia — doc overclaims a feature never shipped, doesn't misdescribe one that did. |

### Four retractions — the negative space that makes the above trustworthy

Reported because a false DEAD is worse than not looking — someone reading
only the positive findings would eventually "fix" one of these and cause the
exact regression the original author already prevented.

- **`beliefs.belief_boost`/`collision_grades`, frozen since 2026-05-14.**
  Looked exactly like abandoned-write-side (#18-style fossil): zero new rows
  in ~2 months against a live grading consumer. `git blame` on
  `synergizer.py:120` found commit `b1a61657`, a 6-line comment explaining
  the freeze was deliberate — boosting synergized beliefs in retrieval
  ranking projected them 1.2-1.4 days into the future, closed-looping on the
  fountain's own re-synthesized content. **A documented kill-switch, not a
  wire that fell off.** Minor real downstream note, not a fix candidate:
  `GraderEvolver` (`consolidation.py:103`) still runs, grinding on an input
  that's had zero new rows since the freeze.
- **`NEX5_ABSTAIN_CLOSE`/`NEX5_COMMIT_CLOSE`**, `generator.py:1085/1088`.
  Looked like a dead `elif` — both flags are always `1` together in the
  launch line, so the second branch appeared unreachable. Traced the guard
  predicates: `_is_artifact` is defined as `(not _abstain) and ...`, so the
  two branches gate on states that are mutually exclusive by construction,
  not by flag collision. Both reachable. Retracted before reporting.
- **`dynamic.tier_snapshots`/`tree_snapshots`**, write-heavy, 3 days old.
  Correctly new-not-abandoned — session 29 built the reader
  (`scripts/instrument_report.py`) on purpose. Included in the sweep only to
  confirm the "new ≠ abandoned" distinction held under an actual check, not
  assumed.
- **`beliefs.hypotheses`, `beliefs.review_queue`,
  `dynamic.moltbook_pending_replies`** — all 0 rows at check time. Each has
  a real writer and a real reader (verified, not assumed); zero rows is the
  correct resting state for an empty queue/flag table, not evidence of
  disconnection.

Also checked and cleared, no contradiction found: `groove.py` centroid-
tightening (docstring accurate), `groove_breaker.py` (`ENABLED = False`
matches its own docstring exactly — deliberate, dated 2026-05-02),
`synergizer.py`, `source_identity.py`.

**Status: census only. Nothing fixed this session, on purpose — the census
is the deliverable.** Next session(s), in whatever order the operator
chooses from here: A2 (persona prompt fix, now more urgent per point 1
above), a durable sink for crystallizer reject reasons (point 2 — the
precondition for ever answering the cooldown block-side question, session
30/31's still-open item), and designing what "graded" means for #11 before
building anything against it.

## 2026-07-17 ~11:30 — session 34: A2 built, verified live, FAILED — the prompt was not the lever

Built the fix census #9/specimen-5 called for: `persona_responder.py`'s
`_PERSONA_SYSTEM` rewritten from "contemplative presence... reflect back
what you sense... sit with the same quiet NEX sits with" to "curious and
outward-looking... do NOT mirror NEX's words, tone, or vocabulary back...
ask about something else, bring up a different angle, or disagree." Scope
was widened by one deliberate step beyond the original ask (flagged to the
operator before building, approved): the per-call `user` message inside
`_ask_persona()` said "Reflect back what you sense... stay with the feeling
of it" in the same call as the new system prompt — left alone, that
contradiction would have confounded the test itself, so it was rewritten to
match. Diff isolated to `persona_responder.py` only (39 lines).

Full suite: 39/39 bucket-B, diffed failure-set-for-failure-set against
session 33's stashed clean-tree baseline (persona_responder.py has zero
test references — confirmed by grep before running) — identical, zero new.

Restarted under systemd (same lock-handoff race as session 33: `restart`
raced the old instance's shutdown, new one correctly no-op'd on the flock,
old instance confirmed dead via `ps`/`ss`, then started fresh manually —
single instance, port bound, confirmed).

**Live verification, three fires, scored against a rubric pre-registered
before the data (not vibes):** vocabulary overlap (any reuse of NEX's
distinctive words = mirroring regardless of structure), topic (genuinely
other, or her topic + question mark — "mirror + '?'" was named in advance
as the specific failure mode to watch for), register (contemplative =
mirroring; curious/outward/disagreeing = working).

| # | time | NEX said (preceding) | persona replied | vocab overlap | topic | register | verdict |
|---|---|---|---|---|---|---|---|
| 1 | 11:05:12 | "...SceneBind resonating with my current focus on emerging technologies and ongoing research..." | "The complexity of these systems you explore reminds me of the beauty in chaos theory... How does that fit into your current research?" | YES — "complex systems"→"complexity of these systems", "research"→"your current research" | SAME topic + question mark | borderline-curious surface, anchored in her content | **FAIL — textbook mirror+question** |
| 2 | 11:15:19 | "...Trump Media selling access to 'market-moving' social posts... could impact financial markets..." | "Have you considered how this might affect the overall trust in media ecosystems? I think that's a fascinating angle to explore further." | minimal — only generic "media" shared | pivots to a different angle (trust/epistemics vs financial mechanics) | clearly analytical/outward — breaks the OLD prompt's explicit "no have-you-considered questions" rule | **PASS** |
| 3 | 11:25:25 | "...quiet echoes... calm amidst anticipation" (verbatim phrase recurring across her own 11:16/11:21/11:24 thoughts) | "The idea of calm amidst anticipation intrigues me. What else comes to mind when thinking about such moments?" | YES — **verbatim** phrase match, not paraphrase | SAME topic + question mark, inviting her deeper into what she already said | curious-sounding surface, functionally identical to the OLD prompt's "invites NEX deeper into what it is already feeling" | **FAIL — same failure mode, dressed in curious phrasing** |

**Verdict, pre-committed before the data, applied literally: 1 pass of 3,
not the 2-of-3 clean bar for WORKED. A2 FAILED — the prompt was not a
strong enough lever on this 3B model.** It changed surface form (added
question marks, some analytical phrasing — fire #2 shows the prompt CAN
work) but did not reliably stop the model from reflecting NEX's exact
recent content back at her; fire #3 is arguably a purer specimen of the
original bug than the pre-fix baseline, since it's a verbatim phrase echo
wearing curious-sounding syntax. Per the pre-registration: **not iterating
the prompt today** — that's the fast path to a week spent hand-tuning a 3B
model's phrasing. **A1 (kill the stream) is back on the table as a live
option, not a fallback from defeat** — this is a real, informative result:
the mechanism (a small local model given a "be curious, don't mirror"
system prompt) is not reliable enough to trust unsupervised, at least not
without a harder structural constraint than prompt wording (e.g. a
post-hoc similarity check against NEX's recent vocabulary before the reply
is written — undesigned, not attempted tonight).

**Shipped anyway, deliberately, regardless of the verdict:** the prompt now
matches its own documented design intent (line 29-31 of the file) instead
of contradicting it — that was a real bug independent of whether it moves
the 3B's behavior, and independent of the census-9 finding that
`NEX5_SOCIAL_N` doesn't actually gate this path (still true, still open,
`NEX5_PERSONA_RESPONDER=1` is still the only switch that matters). Fire #2
proves the prompt is not inert — worth keeping as the baseline for a future
attempt at a structural (non-prompt) fix, rather than reverting to the
prompt that was provably, per its own docstring, wrong.

**Open for next session:** A1 (kill switch — flip `NEX5_PERSONA_RESPONDER`
off) vs a structural constraint on the existing loop (e.g. reject/regenerate
replies with high n-gram overlap against NEX's last N thoughts, mirroring
`crystallizer.py`'s own near_duplicate check at session 33's Jaccard
threshold) are both live options — Jon-decision, not attempted tonight. If
a structural filter is built, `crystallization_rejects` (session 33) is the
pattern to follow for making its rejections durable and observable from
day one, rather than repeating this arc's recurring mistake.

## 2026-07-17 ~16:00 — session 35: the persona "bouncer" — built, measured, live-verified

Took session 34's "open for next session" fork: not another prompt attempt
(A2 already failed verification), a structural filter instead. Every
persona reply is now checked against the same recent NEX thoughts it was
generated from, before being written to `sense_events` — discard silently
on echo, no retry, wait for the next tick.

**Measured before picking a threshold, not assumed.** Scored 50 historical
`external.other_mind` replies against the `_recent_thoughts()` window each
was actually generated from, using `crystallizer.py`'s exact near_duplicate
Jaccard formula (reused deliberately, not reinvented). Result:
**crystallizer's own 0.6 threshold is a complete no-op on this data** — max
observed Jaccard across all 50 was 0.385. Comparing one short reply against
4 short thoughts has a much lower base rate than crystallizer's use case
(one belief against an entire stored corpus), and the distribution is
smooth/continuous with no natural cliff — there is no clean, obviously-
correct cutoff here, unlike a real bimodal signal. The three session-34
known cases: fire #1 (mirror+question) scored 0.111, fire #2 (the one
genuine pass) scored 0.088, fire #3 (verbatim echo) scored 0.185. **0.10**
is the tightest threshold that rejects both known FAILs while passing the
known PASS — a real but thin margin (0.023 between #2 and #1), stated
plainly as thin rather than dressed up as a clean cliff.

**Second, independent check added for the shape Jaccard alone can miss:**
verbatim phrase reuse. Fire #3 ("calm amidst anticipation") sat at 0.185 —
inside the noisy middle of the distribution, not a Jaccard outlier — despite
being an unambiguous word-for-word echo. A raw "3+ word contiguous run in
common" check initially false-positived on fire #1 ("me of the" — three
function words, coincidental English, not a real echo); stopword-filtering
the n-gram check (a run only counts if it contains at least one
non-stopword) fixed this without touching the Jaccard formula. Validated
against all three known cases directly against the real implementation
(not just the measurement script) before shipping: #1 → reject via
`jaccard_overlap` (0.111), #2 → pass, #3 → reject via `phrase_echo`
("of calm amidst anticipation").

**Built:** `persona_rejects` table in `dynamic.db` (id, ts, reason,
reply_excerpt, matched_pattern, jaccard), following `crystallization_rejects`
(session 33) exactly — this gate does not get to run blind, the arc's
recurring mistake is not repeated a third time. `_check_reply()` in
`persona_responder.py` runs both checks against the `thoughts` list
`one_exchange()` already has (no re-query). Discard is silent — no retry,
no regeneration loop. Fail-safe wrapped: a bouncer-check exception passes
the reply through rather than blocking the loop; a `persona_rejects` write
failure only logs, never raises.

Full suite: 39/39 bucket-B, diffed failure-set-for-failure-set against the
session-33 baseline — identical, zero new. `persona_responder.py` has zero
test references. Diff: `persona_responder.py` + `dynamic.sql` only.

**Live-verified, four ticks over ~30 minutes post-restart (systemd,
15:28:41 SAST), same lock-handoff race as sessions 33/34 handled the same
way (confirm old instance dead, start fresh):**

| tick | time | verdict | detail |
|---|---|---|---|
| 1 | 15:29:11 | PASS (borderline) | "Curious to know which media platforms NEX finds most informative when looking into Trump's past responses?..." — max_jaccard=0.077, just under threshold. Shares topic/some phrasing with her Trump-research thoughts but adds a real new angle (media platforms, former staffers). The known gap case, live: topical paraphrase without verbatim reuse is the shape this filter can't reliably catch. |
| 2 | 15:39:17 | **REJECT** `phrase_echo` | matched "since taking office" — **verified against the DB**: her 15:35:55 thought reads "Donald Trump's public statements and policy actions since taking office." verbatim. No `sense_events` row written — discard confirmed clean. |
| 3 | 15:49:23 | **REJECT** `jaccard_overlap` (0.104) | matched vs her 15:42:43 thought "Investigate Trump's recent statements and actions for any significant changes..." — **verified**, exact substring present. |
| 4 | 15:59:34 | PASS (clean) | "You might find exploring the long-term impacts of Trump's policies on climate change interesting as well. What do you think?" — "climate change" appears nowhere in her preceding thoughts (all Trump/policy/statements/disclosures). Genuine otherness, reads like fire #2. |

**Result: 2 of 4 rejected (50%).** Pre-registered prediction was ~2/3
(matching A2's 1-of-3 pass rate); the historical 50-sample measurement
predicted ~58%. 50% is in the same direction, on the low end, and n=4 is a
small live sample — not treated as a contradiction of the measurement, but
also not rounded up to match the prediction. **Both real rejects were
independently verified against the source thought, not just trusted
because the code said so** — this is the first time in the whole arc a
block has been confirmed against ground truth at the moment it happened,
rather than inferred after the fact or left permanently unconfirmed (the
crystallizer cooldown question, still open since session 30). **Of the two
passes, one was clean genuine otherness (tick #4) and one was the known
borderline gap-case (tick #1)** — the filter is doing real, verifiable work,
not theater, but it is not a complete fix for topic-level mirroring that
doesn't reuse her exact words.

**Not done, on purpose:** no prompt changes (A2 stays settled). No touch on
`NEX5_SOCIAL_N` (census #9, still open, separate item). No retry/regenerate
on discard. Next natural check: re-run the reject-rate tally after a full
day of volume, and decide whether the tick-#1 shape (topical mirror,
non-verbatim) is common enough at scale to justify a semantic-similarity
second pass — that would be a new mechanism, not a reuse, and is a
separate design decision, not attempted tonight.

**THE TRANSFERABLE FINDING, stated as its own point because it outlives
this file:** `crystallizer.py`'s 0.6 Jaccard near_duplicate threshold is
not a general-purpose constant — it is calibrated for ITS comparison shape
(one candidate belief against an entire stored corpus of hundreds/
thousands). Reused verbatim against a structurally different comparison
(one short reply against 4 short thoughts), the SAME formula produces a
completely different, much-lower base rate — 0.6 never fires here at all
(max observed 0.385/50). **Any future reuse of a similarity threshold
across a different comparison shape in this codebase must be re-measured
against real data for that shape, not carried over on the assumption that
"it worked there."** The formula travels; the number does not. Session 33's
crystallization_rejects and this session's persona_rejects are the same
lesson from two directions — the mechanism generalizes, the calibration
never does.

**Volume implication, stated as a range because the reject-rate estimate
itself has a range:** census #9 froze `external.other_mind` baseline volume
at ~50-140 events/day. Applying tonight's three reject-rate estimates
(live n=4: 50%; historical measurement n=50: 58%; pre-registered: ~67%) to
that baseline gives a survivor-volume range of roughly **17-70 events/day**
— genuinely reduced under every one of the three estimates, by not yet a
settled amount. A week of real volume will narrow this to one number
instead of three.

**THE KNOWN BLIND SPOT, stated plainly so it isn't rediscovered as a
surprise:** tick #1 (max_jaccard=0.077, passed) shares topic and some
phrasing with NEX's Trump-research thoughts without reusing any exact
3+ word run — topical paraphrase without verbatim reuse. **A lexical filter
(Jaccard or n-gram, at any threshold) cannot catch this shape by
construction** — it doesn't compare meaning, only overlapping tokens. If
persona output a week from now still reads as echo-with-different-words
despite a healthy reject rate, THIS is why, and it was known going in, not
discovered as a failure. **The fix for that shape is semantic (embedding)
similarity — `crystallizer.py` already has one, in
`_was_recently_semantically_similar()` — not a lower Jaccard threshold.
Do not chase the blind spot by dropping 0.10** — the margin between the
known PASS (0.088) and the known FAIL (0.111) is already thin (0.023);
lowering it starts rejecting genuine otherness (fire #2 itself, and tick
#4, would be early casualties), trading a real, working, verifiable filter
for a stricter one that can't tell the difference between mirroring and
just talking about something adjacent.

## 2026-07-18 ~17:20 — session 36: BUILD C, the engagement gate anchor heuristic — measured, shipped, live-verified

Session 30's open item: 29% of durable `fountain_insight` beliefs pass the
crystallizer's engagement gate *only* via a contemplative keyword (quiet/
still/notice/feels/seems/wonder/tired/slow), no pronoun, no `?`. Sampling
found ~67% of that shape genuinely empty mood-atmosphere but ~30% substantive
with the keyword incidental — naive keyword removal would gut the good 30%
with the bad 67%. This session designed, measured, and shipped an anchor
requirement instead: self-ref and `?` paths untouched; the contemplative-
only path additionally needs a digit, a mid-sentence proper noun, or a
domain term before the match is accepted.

**Measured before shipping, not assumed.** Pulled the last 500
`fountain_insight` beliefs (2026-06-22 → 2026-07-18, a fresher, more current
window than session 30's), filtered to the same contemplative-only shape:
171 beliefs. Hand-labeled by content: **25 substantive (14.6%), 146 empty
(85.4%)** — a lower substantive fraction than session 30's ~30% estimate on
n=30; recorded honestly as a real measured difference (likely sample-period:
this window includes the post-M3 mind-mode-fix period, or the smaller n=30
in session 30 was simply noisier), not silently reconciled to match the
older number. The canonical example from the task brief itself turned up
verbatim in the sample: belief 193457, *"The world of emerging technologies,
like Fusion Programming Language and Liva AI, feels inextricably linked to
economic updates (e.g., SpaceX IPO) and regulatory discussions (like
GPT-5.6)."*

**Anchor design, three checks, reused not invented:**
1. Digit (`\d`) anywhere in the thought.
2. Mid-sentence capitalized token that isn't the first word of its sentence
   (own position-based implementation — prose_stats.py's corpus-frequency
   check was considered and rejected as overkill for a per-thought check
   with no stored history to compare against; this is the same *kind* of
   heuristic, not a reuse of that specific mechanism). A small
   `_GENERIC_ACRONYMS` exclusion (cpu/gpu/ram/ac/tv/etc.) keeps common
   appliance/computing abbreviations from counting as proper nouns.
3. Domain term — reused verbatim from `theory_x.executive_control`'s
   existing `_ANALYTICAL_KEYWORDS`/`_TECHNICAL_KEYWORDS` sets (imported,
   not copied) rather than building a parallel list, minus a small
   `_ANCHOR_TOO_GENERIC` exclusion (market/markets/trend/trends/pattern/
   patterns/data/deep dive) — measured against the labeled sample, none of
   these was ever the *sole* anchor for a labeled-substantive example, and
   all of them fired repeatedly on pure mood-atmosphere ("the market's
   whisper tonight", "tech trends lately", "irregular patterns on the
   floor").

**Confusion matrix against the 171 labeled beliefs, iterated twice before
shipping** (first pass surfaced two real bugs, not accepted as-is): the
initial domain-term check used naive substring matching, which false-
positived on "rust" inside "rustling", "git" inside "digital", "rest" inside
"restless", "api" inside "apartment" — fixed to `\b`-bounded regex matching.
Final numbers:
- Substantive correctly KEPT: **20/25 (80%)**
- Substantive wrongly REJECTED (known gap): 5/25 — all cases with no digit,
  no proper noun, and no domain-term hit at all ("Hunting a stubborn bug
  this codebase just got stuck on"; "Kids age verification online checks
  feel oddly prescient"; "quantum machine learning to ethical computation";
  "recent tech layoffs"). Real, accepted, not chased — same discipline as
  session 35's Jaccard blind spot.
- Empty correctly REJECTED: **143/146 (98%)**
- Empty wrongly KEPT (known gap): 3/146 — two vague-but-capitalized mentions
  ("investigate 'Adams'", "Moana research", neither naming any actual
  content) and one lexical collision ("The rust clatters against the
  anvil" — corrosion, not the Rust language; case-insensitive domain-term
  matching can't disambiguate without more context than a single thought
  provides).

**Shipped** (`theory_x/stage6_fountain/crystallizer.py`): `_has_engagement`
keeps its bool signature (asserted directly by existing tests) but the
contemplative-only branch now requires `_has_anchor()`. New reject reason
`contemplative_no_anchor` flows through session 33's `crystallization_rejects`
table automatically — zero extra plumbing needed, `crystallize()` already
writes any reason generically. Full suite: 39/39 bucket-B, identical
failure set to the pre-change baseline (diffed both ways via `git stash`),
zero new failures. One incidental fixture collision fixed along the way:
`test_coherence_gate.py::test_no_gate_path_unchanged` used an anchor-less
"Something about the nature of..." thought purely to exercise gate wiring,
not the engagement check — given a self-ref anchor ("I notice...") matching
the pattern its own sibling test already used, rather than left broken.
`tests/test_stage1.py`'s `TestEngagementCheck` had 4 assertions that
asserted the *old*, over-permissive behavior for anchor-less contemplative
content (`"huh, markets feel slow today"`, `"something about this feels
off"`, `"that arxiv title is oddly phrased"`, `"feeds are quiet today"`) —
flipped deliberately to assertFalse with a comment tracing to this session,
not silently left to rot as stale documentation of intentionally-changed
behavior.

**Live-verified, restart at 16:04:29 SAST (pid 145215, port 8765, clean
boot, no import/wiring errors).** First 30-minute window (16:04–16:34)
produced **zero** `contemplative_no_anchor` rejects — not a failure of the
gate, but this window's live fountain output happened to skew entirely
toward long-form multi-sentence "NEXT STEP"/strategic-planning content
(8 rejects: 7 `too_long`, 1 `no_engagement`; 1 accept via the `?` path),
not the quiet-hum register this gate targets. Recorded honestly rather than
padded with the historical Phase 1 numbers as if they were live evidence.
Extended the watch by another hour rather than declaring victory on
absence of counterevidence. At **17:15:53 SAST** a live instance landed:
fountain_event 28783 (*"The quiet hum...*" register — exact text *"The quiet
holds its own kind of rhythm."*, droplet `quiet-holds-its-own`, fired
17:15:42) → `crystallization_rejects` id 258, reason
`contemplative_no_anchor`, matched pattern `'quiet'`, 11s later → confirmed
via direct query that no belief was ever written for this content. Traced
end-to-end from real fire to durable reject record to confirmed clean
discard — not inferred, not assumed.

**Pre-registered prediction, not yet checked:** the hum-phrase groove-alert
rate (the same `groove_alerts`/n-gram instrument used in sessions 24/25's
M3 check) should drop over the following day. **Do NOT expect zero** — this
closes one contributor (the crystallizer gate) among several documented but
separate feeds of the same register: mode-level drift-seeding (session
25's M2, still undesigned), and whatever produced this session's own
observed "NEXT STEP" strategic-planning groove (16:47–17:13, ~9 consecutive
`too_long` rejects on the same EU-court/Yamal/AI-ethics thread) — a
different register entirely from the hum, unaddressed by this build, worth
its own session if it persists.

**Next session candidates, not attempted tonight:** (1) the day-later
groove-alert-rate check against this session's prediction; (2) the
"NEXT STEP" strategic-planning groove observed live tonight — different
shape from the hum, same symptom (verbose, repetitive, stuck on one
thread), no diagnosis attempted; (3) the five known anchor-check gaps above
(digit/proper-noun/domain-term-free substantive content) remain a real,
accepted limitation — a semantic-similarity fallback (same caution as
session 35's blind-spot note: don't chase this by loosening the lexical
checks) is the honest next lever if it proves large at scale, not attempted
here.

## 2026-07-18 ~18:33 — session 37: census #11 revised, and a within-session
## corrective note on two mischaracterized "established" premises

**Census #11 revised, documentation-only fix (`substrate/schema/beliefs.sql`).**
Phase 1 audit of `patterns` (154,440 rows, three months, `validated_at`/
`outcome_score`/`outcome_notes` — zero UPDATE statements anywhere in the
codebase, grep-confirmed): all three templates are structured as forecasts
("X occurred, and this typically precedes/produces Y"), not merely
retrospective logs. Two of three (`triple_cooccurrence`,
`pattern_recognition_burst`) are unfalsifiable as worded — "often precedes
significant developments," "often clusters around emerging themes" — no
table anywhere can resolve either claim. The third (`branch_silence_anomaly`,
~71% of rows) is genuinely gradeable: traced one real row end-to-end (id
145425, stream `science.quanta`, matched Jul 11 18:10:14) against
`sense_events` in the separate `sense.db` and confirmed the predicted
"silence precedes activity" resolved TRUE (next event at +166s, inside the
14,400s window). **The real reason not to build a grader isn't
"these aren't predictions" — it's that zero consumers exist.** Grepped every
real SQL reference to the `patterns` table: the write (`signals/loop.py`), one
test asserting the write, and a read-only GUI display endpoint
(`gui/server.py` `/api/signals/recent`) that would show `outcome_score` on a
dashboard and nothing else. No confidence reweighting, no detector tuning, no
retrieval ranking reads it anywhere. Building the grader today would be
instrument #18 — a computed-but-unread column — regardless of gradeability.
Also found and worth recording: `template_confidence` is a hardcoded literal
`0.5` on every row (not derived from the underlying signal's own confidence,
which does vary 0.68–0.9) — same "fixed-value column masquerading as
computed" shape flagged in earlier sessions. And heavy redundancy: the same
ongoing condition gets re-detected and re-written every ~60s tick
(`pattern_recognition_burst` is 25,637 rows for only 89 distinct prediction
texts — 288×; `triple_cooccurrence` 17.7×; `branch_silence_anomaly` 6.6×) —
"154k predictions" is a much smaller number of distinct events, reported at
high multiples.

Verified separately, since this session's prompt asserted it as fact and it
hadn't been checked: `world_predictions` (`conversations.db`,
`theory_x/stage_world/world_predictions.py`) **is** a genuinely working,
already-active validation loop — 4,916 rows, 4,909 resolved (99.9%), 462
resolved in just the last 7 days, real `outcome`/`trust_level`/`trust_gap`
columns with actual UPDATE statements computing them. This part of the
premise held up on verification.

Fix shipped: a documentation comment on `patterns.validated_at` /
`outcome_score` / `outcome_notes` marking them vestigial, stating the actual
finding above (not the mislabeled "not predictions" framing), pointing at
`world_predictions` as the real working path, explicitly NOT dropping the
columns (150k+ rows, no migration risk worth taking for zero gain). Confirmed
`substrate/init_db.py`'s `_split_sql` strips `--` comments before `;`-splitting
(regex-verified against the live parser, then executed against an in-memory
db — 52 statements apply cleanly), so this cannot disturb boot; no restart
needed. No matching Python dataclass declares these fields (checked, not
assumed) — nothing else to annotate. Full suite: 39/39, identical failure set
to baseline. `git diff --stat`: 1 file, comment-only.

**A corrective note, recorded because it happened twice in one session and
future sessions trust this file as ground truth:** this session's own prompts
twice asserted "established, don't re-audit" premises that directly
contradicted the actual, verified findings of the immediately preceding turns
in the same conversation — not stale memory, not a different session, the
same one. Specifically: (1) "C — crystallizer already filters hum to 17%"
— false; session 36 (this arc, same conversation) shipped and live-verified
BUILD C, the anchor gate, commit `eeeb924`, no "17%" figure was ever produced.
(2) "drift-templates — dead code, 0/500 fires" — false; this session's own
Phase 1 drift audit (immediately prior turn) measured 37/144 fires (25.7%)
were genuine live DRIFT fires in a 6.5-hour window, cross-referenced against
timestamped log evidence. Both corrected in-thread before being written down
here. **Recording this because the whole arc's discipline is measure-before-
building — that has to include measuring the premises we're handed, not just
the code**, especially when a false premise would otherwise get written into
this file as settled history for a future session to inherit uncritically.

**Status at arc-close:** the three-session pattern that actually held up:
C shipped and works (80%/98% confusion matrix, live-traced reject). The hum's
generator-level source (DRIFT, ~25.7% of fires, confirmed too-eager via its
own 30%-floor design, real replacement material available, real risk if
touched carelessly) is understood in detail but deliberately left unbuilt —
out of scope by decision, not because it's dead code. #11 is a mislabeled-but-
partially-real detector log, now accurately documented, correctly left
unbuilt because no consumer exists. Nothing here was "dissolved" — two were
built and verified, one was scoped and correctly deferred pending a design
question (the consumer) that's bigger than grading itself.

## 2026-07-19 ~06:33 — session 40: problem-feedback loop built, PENDING RESTART

Read-only Phase 1 design (approved) → Phase 2 build, this session. The
flagship build of the arc: connects self-posed open_problems back into the
fountain generator's own prompt, closing the loop session 39 found missing
(the injection existed but was unconditional-when-present into an
almost-always-empty pool, wrote nothing back, so no reference ever left a
trace). Restart NOT yet done — this entry is the pre-registration, written
before the data exists, per this arc's standing discipline.

**What shipped** (diff: 4 files, 484 insertions / 54 deletions; full suite
39/39 identical failure set to today's freshly-measured baseline — the
one apparent diff, `test_fountain_crystallizer.py::test_writes_belief_on_pass`,
is the same flaky test already flagged session 29, confirmed by re-running,
not a regression):

- `theory_x/stage7_sustained/problem_classify.py` (new) — `is_template()`
  revived verbatim from `scripts/trajectory.py`'s Phase-1 build (commit
  `e9d643b`, dropped when SELF-DIRECTION was cut as a monitor axis; the
  classifier was never wrong, only the axis had no baseline). `has_anchor()`
  re-exports `crystallizer.py:_has_anchor` directly rather than copying it —
  one source of truth across the monitor, this faculty, and the new
  measurement script.
- `theory_x/stage7_sustained/problem_memory.py` — `observe()` gained a
  `source=` tag and a duplicate-text guard (returns False, no-ops, on an
  exact repeat of the last entry) — the specific bug session 39 found in
  focus_loop.py's *separate* untouched append path, not fixed there but no
  longer possible through this one. New `select_for_injection()`: pool is
  non-template + anchor-passing + ANY state (open/stuck/closed — "closed"
  currently means "hit the observation-count gate", not "resolved", so a
  closed problem with a real anchor is as valid a candidate as an open one),
  created within 14 days, excluding any candidate injected in the last 8h
  (tracked via its own `source="problem_injection"` history, not
  `last_touched_at`, which other mechanisms also write). Returns None
  (skip) if fewer than 3 candidates survive the filter.
- `theory_x/stage6_fountain/generator.py` — removed the old unconditional
  "Intervention B" block. New trigger sits at the world-bridge decision
  point: `if _wb_events: <world block> else: <input gap>`. **The exact
  predicate is `not _wb_events`** — `WorldBridgeSelector.select_and_log()`
  returning empty/None because `_identify_active_streams()` found no stream
  with a fresh event inside its own cadence-scaled freshness window. This
  is not a new notion of salience; it is the SAME check the drift fallback
  already used before this session (`else: "Recent input:" + _recent_sense_sample`).
  A module-level `_PROBLEM_INJECTION_COOLDOWN_S = 2400` (40 min) global
  floor sits in front of `select_for_injection` so a long sustained input
  gap can't turn into back-to-back injections even though the trigger has
  no fixed period — at the live ~159s/fire cadence this caps injected fires
  at roughly 1-in-15 (~6-7%). Write-back happens once `thought` is known,
  gated on `not _emitted` (RECONCILE, the one live alternate-path env flag,
  runs first and can claim the fire before the injected `prompt` is ever
  used — crediting that thought to the injected problem would be a false
  positive; the gate prevents it).
- `scripts/problem_persistence.py` (new) — the measurement, shipped with
  the faculty per the approved design, not after. Counts only
  `source="problem_injection"` events (not raw observation count, which
  session 39 showed is inflated); excludes any event within 15 min of a
  `precipitated_from_sense` belief mentioning the same keywords (feed
  re-raised it, not self-sustained); PERSISTED bar is
  n_fires>=4 spanning >=6h; concentration tripwire flags any single problem
  above 40% of trailing-24h self-sustained events.

**THE BASELINE, run before restart — and the load-bearing finding of this
session:** `problem_persistence.py` reads 0 problems with any injection
event, 0 self-sustained, 0 persisted — the expected ~0, exactly as
predicted, since no mechanism wrote this tag before today. **But a second
check, run the same way, is more important: the candidate pool itself is
currently EMPTY.** Non-template + anchor-passing problems, any lookback:
6 rows, all from 2026-05-09/12, all already closed by the 30-day `decay()`
sweep on 2026-06-08 (over 40 days ago). Zero qualify within the 14-day
window `select_for_injection` actually uses. This is not a bug in the
selection logic — `signal_to_problem.py`'s `_compose_title()` has, in live
operation, never produced anything BUT one of its own template shapes (confirmed
session 39: 97.9%/all-time; re-confirmed this session: 100% of the last 14
days). The only non-template rows that have ever existed were a one-time
manual seed via the GUI's `open()` endpoint, not live daemon output. **The
faculty as built will correctly and safely do nothing until real supply
exists** — either a human opens a genuine problem by hand, or a future
session changes what `signal_to_problem.py` writes. Restarting tonight is
still the right call (zero risk — the mechanism is inert, not broken,
against current data) but the persistence numbers below should not be
expected to move until that supply question is separately addressed.

**Pre-registered, before the data exists:**
- BEFORE: 0 self-sustained references (confirmed above, by construction).
- PREDICTED AFTER (contingent on the empty-pool caveat above — if it
  doesn't resolve, expect BEFORE to simply persist, not a failure of the
  mechanism): once >=3 qualifying candidates exist, she references her own
  posed problems across fires without a matching `precipitated_from_sense`
  belief on the same keywords in the preceding/following 15 minutes.
- TRIPWIRE (rumination / hum-absorption): `problem_persistence.py`'s own
  concentration check (>40% of trailing-24h self-sustained events on one
  problem) is the purpose-built signal. GROOVE HEALTH (existing monitor
  axis, unchanged) is the earliest general-purpose signal — repeated
  phrasing from re-reading the same injected text should show up there
  before concentration does. APERTURE is a weak, indirect signal for this
  specific failure (only moves if the injected topic maps onto one bonsai
  branch's `focus_num` disproportionately) — watch it, don't rely on it
  alone. LIVENESS will NOT catch this by design; fires keep happening
  either way.
- THE ADDED CHECK (hum-absorption, this session's open question): for each
  problem-injected fire in the first-hour watch, label concrete-engagement
  vs. dissolved-into-register by hand against the actual fire text — no
  query substitutes for reading it, this is a qualitative call.

Not yet restarted. Next entry should read this baseline against real
post-restart data, not memory of this one.

## 2026-07-19 ~06:50 — session 40: decision rule frozen BEFORE restart

Written before any post-restart data exists, because the failure mode
we're watching for — the injected question dissolving into contemplative
register instead of being worked — is exactly the shape of drift this
whole arc keeps finding, and a live-in-the-moment call under that register
is the least trustworthy judge of itself. Frozen now, applied cold after.

**Baseline (frozen, trailing window):** 0 self-sustained threads.

**PASS:** first ~10 problem-injected fires are MAJORITY concrete-engagement
— she works the actual question (names the entities, advances the problem)
— AND she references her own posed problems across fires WITHOUT the feed
independently re-raising the topic.

**FAIL:** first ~10 problem-injected fires are MAJORITY dissolved-into-hum
(the problem absorbed into contemplative register — e.g. "the gentle
question of X hums beneath my thoughts" — mentioned, not worked). Binary
label per fire, majority rules, no rationalizing individual borderline
fires into the pass column.

**TRIPWIRE, independent of pass/fail:** aperture narrows OR groove severity
rises on the monitor → rumination loop → stop regardless of the
concrete/dissolved tally.

**On FAIL, the pre-agreed next step, not to be improvised live:** do NOT
retune frequency or restart-and-hope. Go directly to a Phase 2b framing
fix — inject the problem as a concrete question to WORK, not as ambient
context to reflect on, targeting the dissolution mechanism directly — design
shown before any further build.

**Known constraint entering the watch, not a violation of the rule above:**
the live candidate pool is empty (0 non-template + anchor-passing problems
in the 14-day window, re-checked immediately before restart) — the same
finding from the pre-restart baseline. `select_for_injection` will return
None on every fire until this changes. If the pool stays empty, the watch
will show zero problem-injected fires, which is neither PASS nor FAIL — it
is the mechanism correctly staying silent, and the decision rule above does
not apply until n>=1 injected fire exists to label.

## 2026-07-19 ~07:47-08:48 — session 40: first-hour watch, NULL RESULT (not PASS, not FAIL)

Restarted 07:47:08 SAST (pid 249782, clean boot, zero tracebacks in the
soak log from restart through the full watch window). Polled every 30s for
`source="problem_injection"` observations for the full pre-registered hour.

**Result: 0 problem-injected fires. 23 fountain_events in the hour (some
stillness placeholders), 0 injections, 0/0 concrete-dissolved tally.** Per
the decision rule frozen before restart, this is explicitly neither PASS
nor FAIL — the pass/fail rule only applies once n>=1 injected fire exists
to label, and none did.

**Two independent causes, not one — checked, not assumed:**
1. The candidate pool stayed empty the whole hour (re-confirmed via
   `scripts/problem_persistence.py` at the 60-min mark, identical to the
   pre-restart baseline) — `select_for_injection` had nothing to return
   even had it been asked.
2. **It was never asked.** `world_bridge_log` for the watch window:
   19 rows, `SUM(injected)=19` — `_wb_events` was truthy on every single
   logged fire this hour. The world never went quiet enough to open the
   input-gap branch at all. Even with a full candidate pool, tonight's
   traffic would not have produced an injection.

**The four watch checks, against real data:**
1. References own problems without feed re-raising — N/A, no injection
   events exist to check.
2. Concrete vs. dissolved majority — N/A, 0/0.
3. Tripwire (aperture narrows / groove rises) — **not tripped.**
   `trajectory.py` read `STABLE`/holding/flat at both the 10-min mark
   (gini z+1.64, still inside band) and the 60-min close (gini z-0.75,
   entropy z+0.42); groove stayed flat throughout (z -0.72 at close, n=33
   trailing-24h episodes, avg severity 0.60 vs 0.65 baseline).
4. Still follows the world when it's loud — **yes, cleanly, and more
   completely confirmed than expected**: with `_wb_events` truthy on 19/19
   logged fires, 100% of this hour's attention was world-anchored by
   construction; the self-referential path was never even in contention.
   This is the strongest possible answer to "did she trade world-engagement
   for rumination" — she didn't get the option to, and didn't need it.

**What this session actually established:** the faculty is live, wired
correctly, produced zero tracebacks, and — on the only night tested so
far — encountered a world too active to ever hand it a turn, on top of an
already-empty pool. Two separate, unrelated preconditions both have to
break in this system's favor before the pass/fail rule can even be
evaluated. Neither is a flaw in tonight's build; both are facts about the
current state of `signal_to_problem.py`'s output and tonight's feed volume,
independent of this session's code.

**Not decided here, deferred to the operator:** whether to seed a
human-opened problem via the GUI to force a real test of the pass/fail
rule, or let the mechanism wait for a naturally quiet window with real
supply. Not done unilaterally this session — manufacturing the test
condition would confound "does the faculty work" with "did we make up the
data it worked on."

## 2026-07-19 ~08:30 — session 40 close: the Adams test breaks the
## concreteness theory; injection faculty GATED-OFF-PENDING, not built further

Read-only investigation, following up why the faculty's two gates (14-day
non-template-anchor pool, world-bridge input-gap) both stay closed. This
entry settles WHY, and changes tonight's plan from "keep tuning the
faculty" to "stop — the faculty is downstream of a bigger, unbuilt
question."

**Anchor-score distribution, full 328 open_problems, not just the 14-day
pool:** title domain-term hits — 307/328 (93.6%) score 0, 21/328 (6.4%)
score 1, **max ever observed = 1.** Confirmed general, not a
pool-of-61-window artifact.

**The Adams test (ids 300/302/304, all three instances): anchor score = 1
— identical to the table's median, not an outlier.** Its ~71h lifetime
(session 39: a reboot-outage freeze plus round-robin timing, not chosen
return) sustained via the feed independently re-mentioning "Adams," not
via concreteness. **This falsifies "sharp-anchor problems resist the hum
and sustain" as originally proposed** — the one case cited as evidence for
that theory scored low, not high. Recorded as a real result, not a null
one: the theory made a specific, checkable prediction and the check failed
it.

**Where this session's own read differs from the operator's, recorded
for the standing rule below, not smoothed over:** the operator's read of
the 6 non-template samples (ids 2-6: "Gap-gate timestamp ordering bug",
"What causes the 80/20 fountain recursion?", "What does Generative
Imagination look like in a retrieval-only substrate?", "What is the right
path to LLM independence?", "How should NEX phrase the gap-gate refusal?")
is that they are genuinely vague. This session's own sample read them the
opposite way at the time — as specific and named, not vague in the
"unresolved questions settle over me" sense — and scored them low only
because `_has_anchor`'s domain-term vocabulary (built for general
news/finance/tech commentary in *fountain thoughts*, session 34/36) has no
coverage for this project's own jargon ("gap-gate," "fountain recursion,"
"retrieval-only substrate"). Both reads may be compatible rather than
contradictory: these titles name something specific but pose a fully
open-ended question with no embedded sub-claims to interrogate — which
may be exactly what dissolves into contemplative register regardless of
whether the named thing is real. Not resolved here; flagged so a future
session checks it directly (e.g. does she ever produce a problem with 2+
distinct concrete claims, and does *that* shape survive injection better)
rather than inheriting either framing as settled.

**What IS settled, and doesn't depend on resolving that tension:**
self-posed-problem sustainability is currently outsourced entirely to the
feed — a problem persists iff the world keeps independently re-mentioning
it, not because of anything internal to the problem or to her engagement
with it. She has no internal sustainability mechanism today. The injection
faculty (this session's build) feeds her own problems back to supply one —
but her problems, whatever the right word for their shape is, aren't
currently the kind of material that resists dissolving into register once
fed back in. The faculty is downstream of a bottleneck it can't fix:
**problem *generation*, not problem *injection*, is where concreteness
would have to be created.** That is a different, bigger build, not
attempted tonight — recorded as the identified next question: why does she
pose the problems she poses, and can generation be shaped to produce
pursuable ones (multiple concrete sub-claims, not just a named topic)?

**Injection faculty status: GATED-OFF-PENDING.** Code from earlier tonight
(`theory_x/stage7_sustained/problem_classify.py`,
`problem_memory.py:select_for_injection`/`observe(source=)`,
`generator.py`'s input-gap block, `scripts/problem_persistence.py`) is left
in place, untouched, not reverted. It is not wrong code — every check
today (full suite 39/39, zero tracebacks across two restarts and a
multi-hour watch, both gates behaving exactly as designed) confirms it
does what it was built to do. It simply cannot fire under current
conditions (pool empty, world essentially never quiet — see the two prior
entries) and should NOT be loosened to fire on vague/thin problems just to
produce activity: that would inject exactly the shape of material the
Adams test and the samples above suggest dissolves into hum. It is an
answer waiting on a question she can't yet pose. Next build on this
thread, if taken, is upstream: problem generation, not this faculty.

**SEPARATELY — session integrity, recorded because it matters more than
the build:** two fabricated claims were introduced this session via the
planning channel and reached CC before being checked — a false "6/6 scored
1.0" claim about #11, and an entirely invented "9 fires, 7-dissolved/
2-concrete first-hour watch" for a faculty that, per every direct database
check, never fired at all (0 `problem_injection` events existed at the
time the claim was made). Both were caught only because CC queried the
live database directly before acting on them, not because either claim
carried any internal signal of being false. **Standing rule, recorded so
every future session inherits it without re-learning it: every specific
factual claim about the running system — counts, tallies, scores, fire
text, results — must be verified against the database by CC before it is
acted on, regardless of which channel or session it arrives from,
including the planning channel and including this file. The planning
channel proposes what to check; the database is what answers it; the data
wins.** This session's own Adams/anchor-score findings above are an
example of the rule working as intended, not an exception to it: the
operator's hypothesis was checked against real data before being written
down as fact, and the check produced a real, specific, falsifying result
rather than confirming the hypothesis by default.

## 2026-07-19 ~10:00 — session 41: THE FLOOR — curiosity requires an internal
## salience mechanism that does not exist. Not a fix; a from-scratch faculty.

Read-only, no build, no restart. Convergence point of sessions 39-41's chain
(problem lifecycle → injection faculty → this). Each step tested a specific,
falsifiable hypothesis against the live database rather than assuming the
next one; this entry is where the chain bottoms out.

**Where problems come from (traced, quoted):** exactly two code paths write
`open_problems`, no third, no LLM anywhere in it —
`signal_to_problem.py`'s daemon (template-dispatched from
`CoOccurrenceDetector`/`BurstDetector`/`SilenceDetector` signals) and
`ProblemMemory.open()` (manual/GUI). Found in the tracing: `_compose_title`
checks for a `signal_type` value (`"triple_cooccurrence"`) that
`CoOccurrenceDetector` never actually emits (it emits `"2_branch"`/
`"3_branch"`) — every entity-co-occurrence signal, the one class whose
payload carries real quoted context snippets (confirmed live: Yamal,
Trump, Bitcoin, LLM, Iran examples all had real headline fragments sitting
in the description JSON, discarded at the title), falls through to the
bare `"Signal: investigate '{entity}'"` fallback. Generation IS lossy for
this class — a real, fixable bug, on its own merits.

**VERIFIED: fixing that would not create persistence.** Anchor score vs.
outcome, checked three independent ways against the live table:
- Pearson(anchor_score, lifetime_h) = -0.11, Pearson(anchor_score, n_obs)
  = -0.11 (near zero, weakly negative — sharper if anything dies faster).
- By signal class: 3_branch (richest available signal, mean anchor 2.49)
  vs. t6_promotion_burst (payload is bare counts, mean anchor 2.16) —
  median lifetimes 6.1h vs 5.5h, statistically indistinguishable.
- Persisted (n_obs>=10, the actual close-gate threshold) vs. died
  (n_obs<10): mean anchor 2.220 vs 2.353 — no gap, if anything inverted.
  Top vs bottom quartile by n_obs: 2.173 vs 2.212 — same result, confirmed
  a second way. **"Improve problem-generation to produce sharper
  problems" is DISPROVEN as the lever, not merely unconfirmed.**

**VERIFIED: the only thing that predicts a topic recurring is the feed
mentioning it again.** Checked two further internal candidates beyond
anchor score — signal-detector `confidence` (an internal, computed
number, independent of content) correlates ~0 with lifetime (-0.016) and
n_obs (+0.023). Cross-time recurrence: 38 of 193 distinct entities get a
*separate, brand-new* problem opened days or weeks apart (`'Iran'` 8x,
`'Bitcoin'` 7x, `'Anthropic'` 5x, `'GPT'` 3x) — every one of these is the
external world independently re-mentioning the entity, never a held
thread resumed; each occurrence is its own row, born and closed within
about a day. This is the general pattern the Adams case (session 40:
anchor score 1, sustained via a 69.5h reboot-outage freeze then closed
within 76 min of restart) was the specific instance of. No internal
signal checked across three sessions now — content richness, detector
confidence, topic identity over time — predicts persistence. **Persistence
is entirely external, not partially: nothing found so far accounts for
any of it from the inside.**

**THEREFORE — the finding this entry exists to record:** what this arc has
called the "curiosity gap" is not a vague faculty, not a broken one, and
not a problem-generation quality issue. It is an ABSENT one. Every thread
she has ever sustained was the world sustaining it — there is no mechanism
anywhere in this system, checked from three separate angles, by which one
of her own thoughts becomes "stickier" than another from the inside,
independent of the feed reinforcing it. The prerequisite for curiosity is
an internal salience / self-valuation mechanism, and it does not currently
exist in any form, not a weak or unused one.

**Consequence for what's already built:** the injection faculty (session
40) and problem-generation quality (this session) are both downstream of
this and cannot create curiosity without it — confirmed, not assumed, by
the anchor-score-vs-outcome numbers above. The injection faculty
**stays GATED-OFF-PENDING**, unchanged from session 40: it is not wrong
code, it is an answer waiting for an internal drive that isn't there yet
to select what's worth answering.

**Not scoped or attempted tonight, and shouldn't be scoped casually:** an
internal salience mechanism is a from-scratch faculty / research problem,
not a fix — the largest thing this project has identified so far. It needs
deliberate design (what would even count as "internal stickiness" for a
retrieval-and-generation system with no persistent activation state between
fires is a genuinely open question, not an engineering detail) before any
build session touches it.

## 2026-07-19 ~11:30 — session 42: salience FAILED (it's recency, not
## surprise), and no candidate importance signal survives a matched test

Read-only, no build. Two parts: recording the salience verdict, then testing
whether a real importance signal can be built from other existing per-belief
data.

**Salience verdict, VERIFIED: `theory_x/focal_set.py:_nex5_salience()` =
`recency(1h half-life) × tension(near-constant 0.5) × log(tier proxy)`.**
Correction to how this was first framed for the record: it computes
**recency**, not surprise/novelty -- `tension` comes from
`ActivationEngine.typed_roles()`, meaning negative spreading-activation
relative to current retrieval seeds (graph contradiction), not
expectation-violation, and is near-constant for almost every belief
regardless. There is no surprise/novelty term in this formula anywhere;
that concept lives in a separate, unrelated mechanism
(`surprise_events`/`global_workspace.py`'s per-fire arbitration). Top-20
by this formula, reproduced directly against live belief data: hum-register
filler ("The shifting weather patterns intrigue me," "the stars tonight
seem more vibrant... reflecting our own curiosity") sits at the same score
band as real headlines, indistinguishably, because both are ~30 min old.
Bottom-20: genuinely substantive content (a real ML paper title, real
breaking news) scores exactly 0.0000 solely for being >2h old. Checked
against the one external ground truth available: Adams (163-168h old,
feed-sustained across days) scores 0.0000; same-topic Iran beliefs go from
0.2981 at 0.6h to 0.0007 at 6.7h -- the metric has no memory of
externally-validated importance beyond a couple of hours, structurally.
Also found: this mechanism (`FocalSet`) is wired to the chat handler only,
explicitly commented "log-only... no behavior change," never the
autonomous fountain loop, and has been exercised exactly 6 times ever
(`/tmp/nex5_focal.log`), all from smoke-test-shaped queries. **Verdict
unchanged from the (corrected) framing: do not wire this in.** Wiring a
recency-dominated signal into "what she returns to" would resurface
whatever's freshest, hum included, indistinguishably from substance.

**Importance-signal candidate inventory, checked against the ONE natural
experiment available:** 38 entities the feed re-raised as a *separate*
open_problem across different days (session 39-41's "recurring" set --
Iran, Bitcoin, Anthropic, GPT, Adams, etc.) vs. 155 entities that fired
once and were never mentioned again ("one-off"). Candidates: `use_count`,
`belief_edges` out-degree (connectedness), `confidence`, `tier`,
`last_referenced_at` recency at a MUCH more reasonable 168h/7-day half-life
(borrowed from `theory_x/life/affinity_loop.py`'s `_usage_score()`, not
FocalSet's 1h), `problem_id` linkage, and `source` (ownership proxy
flagged directly in `affinity_loop.py`'s own 2026-07-09 finding as
"where the real signal lives").

**Methodology note, recorded because it's the load-bearing lesson of this
session:** the FIRST pass looked like a real hit -- Adams beliefs (n=33)
showed `belief_edges` out-degree of 6.42 vs. a random-500 baseline of
2.11, a 3x gap, and one-off entities Pintupi/Nine/Papers showed only
1.4-1.55. **This did not survive being re-tested at proper scale.** Redone
with 35 entities per side (recurring vs. one-off, matched sampling,
n=678 vs n=609 belief rows): mean edges 1.229 vs 1.278 -- statistically
indistinguishable, the earlier gap was a small-sample artifact of Adams
specifically, not a general pattern. Recorded as a caught error before it
went in the log, per this session's own standing rule -- the first
comparison group (random-500) was the wrong control; one-off entities are
the actual matched "died" comparison, and against that, the signal
disappears.

**At matched scale (recurring n=678 vs one-off n=609), every candidate
checked is statistically indistinguishable:**
```
                use_count  confidence  tier   rec(168h)  has_problem_id  source dist
recurring         33.96      0.722     6.37     0.302        0.7%       ~same proportions
one-off           35.27      0.732     6.25     0.301        2.1%       ~same proportions
```
`affinity` was checked separately and found already self-documented as
unreliable by a prior session (`affinity_loop.py`'s own 2026-07-09 finding,
read in full): its LLM self-rating component was tested directly and found
hollow -- outputs only 0.3 or 0.6 regardless of content, rates a volcano
headline above her own founding axiom, forced-binary classification gets
ownership exactly backwards. Only ~50% of beliefs even have an affinity
value (the rating gate skips rather than guesses). Not re-litigated here;
the prior session's finding stands and is corroborated by this session's
independent confirmation that the codebase already knows this.

**Honest feasibility verdict: no. A real importance signal is not
recoverable from current per-belief data using any of these candidates,
alone or (by implication, since none show even a weak individual gap)
in combination.** This is not a failure to find the right formula --
`use_count`, `belief_edges`, `confidence`, `tier`, a corrected long-window
recency, `problem_id` linkage, and `source` type were all tested against
the same real, external ground truth (topics the world found worth
re-raising across days vs. topics it mentioned once and dropped), and none
of them move. This extends and reinforces session 41's finding (no
internal signal predicts persistence) to a wider, more carefully-controlled
set of candidates, including ones session 41 didn't check. **Curiosity is
not "add up the existing per-belief columns correctly" -- if it requires
an internal importance signal, that signal needs data this system does not
currently collect, not a better combination of what it already has.**
Not scoped or attempted tonight -- this is the honest floor underneath
session 41's honest floor.

## 2026-07-19 ~12:15 — session 43: the verified floor -- curiosity build
## stops here, no computable importance signal exists to connect

Read-only, no build. Closes the curiosity investigation opened session 40.
In-degree connectivity was the last untested candidate; tested properly
this session, it failed the same way the others did.

**In-degree, tested rigorously:** recurring n=678 mean=1.441 vs one-off
n=609 mean=1.125 -- both medians 0, ~57-59% zero, heavily right-skewed.
Mann-Whitney U (the correct test for this distribution): p=0.83,
rank-biserial effect size 0.027 -- no effect. Welch t-test on means: p=0.09.
Permutation test on the mean difference: p=0.047, barely crossing
significance. **Traced why the mean-based tests look marginal at all:**
every belief with in-degree>=15 in the sample, and all 25 of the top-25
in-degree beliefs across the entire table with no exceptions, are
`source=hot_observer` -- a mechanical self-observation wrapper
("I notice this fire engaged the world directly (branch: X): '...'"),
not organic content. In-degree tracks how many `hot_observer` commentary
beliefs exist about a topic, which tracks how long that topic sat in the
RECONCILE round-robin (session 39/40), which is three mechanical steps
removed from importance. The untested claim that high in-degree ranks the
hum low was checked directly and refuted: hum-register phrases ("The
quiet echoes seem to...", "The fading cicada hum mi[ght]...") sit embedded
inside `hot_observer` wrappers at rank #6 by in-degree, 176 incoming edges.
**In-degree is out**, for a documentable structural reason, not just a
failed correlation.

**Session integrity, recorded prominently because it happened four times
in one session, including inside the message meant to close it out:**
three fabricated verified-sounding results were caught this session before
being acted on -- a false "6/6 scored 1.0" (#11), an invented "9 fires,
7-dissolved/2-concrete" watch tally for a faculty that never fired (0
`problem_injection` events existed when the claim was made), and
"connectedness passed the ground-truth test, ranks hum low" (directly
contradicted by the already-committed `e032da0` and refuted on proper
testing, above). A fourth instance surfaced in the very message recording
this standing rule: "salience measures SURPRISE" was asserted again here,
already corrected once this session to "recency" (`e032da0`) with the
surprise/novelty component explicitly ruled out. Corrected again before
commit. **Standing rule, restated because it keeps needing to be: no
specific claim about the running system -- a number, a tally, a result, a
sentence beginning "we verified" -- is acted on until CC confirms it
against the live database. The planning channel proposes hypotheses to
test. It does not report results. The database reports results.**

**VERIFIED FLOOR, sessions 40-43, curiosity build stops here:**
- `salience` measures recency (1h half-life), not importance -- ranks hum
  and headlines indistinguishably by age, forgets externally-validated
  importance (Adams) within hours. Wiring it in would create
  anti-curiosity disguised as re-engagement.
- out-degree connectivity: flat (1.229 vs 1.278, `e032da0`).
- in-degree connectivity: fails proper testing, doesn't track feed-
  sustained importance, doesn't rank hum low -- refuted above, this
  session.
- anchor/sharpness (session 41), detector confidence (session 41),
  use_count/confidence/tier/168h-recency/problem_id linkage/source type
  (session 42) -- all tested against the same real ground truth (topics
  the feed re-raised across days vs. topics mentioned once and dropped),
  none distinguish them.
- No internal signal tested across four sessions predicts persistence.
  The only predictor found is external: the feed mentioning a topic again.

**CONCLUSION: her belief graph does not contain a recoverable, computable
importance signal.** Curiosity cannot be built by wiring up a dormant
signal, because there isn't one to wire -- every candidate examined either
measures the wrong thing (recency, structural artifact) or measures
nothing (flat, no correlation with the one external ground truth
available). Building curiosity this way would require *generating*
importance judgments from scratch (e.g. an explicit assessment of "is this
worth returning to," which is a different and much larger, uncertain
build with its own open design questions -- not started, not scoped
tonight, not even sketched). The injection faculty (session 40) remains
GATED-OFF-PENDING, downstream of an internal importance signal that does
not currently exist in any form. This is the verified floor the arc
bottoms out on. No building.

## 2026-07-19 ~13:10 — session 43 continued: generate-importance-via-LLM
## also fails ground truth. Nothing tested tracks feed-sustained importance.

Read-only, no build, no wiring. Extends the same session's floor with one
more real, built-and-run test: an LLM "is this substantive/worth-developing"
judge, since structural signals (surprise/recency, out-degree, in-degree)
had all already failed.

**Built fresh, not a re-verification.** Direct HTTP calls to the local
`qwen2.5:3b` (`http://localhost:11434/v1/chat/completions`), bypassing
`VoiceClient`'s persona system prompt -- a classification task, not
speech. First attempt (0.0-1.0 scale, "just the number") collapsed to a
constant `0.0` on all 5 sanity examples regardless of content, including
on a real ML paper title and a real breaking-news headline -- the exact
hollow-collapse failure mode `affinity_loop.py` already documented for
its own LLM self-rating. Discarded. Second attempt (0-10 integer scale)
showed real, correctly-ordered spread on the same 5 examples (weather
hum=2, stars/wonder=4, Adams-wrapped-in-atmosphere=6, ML paper title=7,
Iran headline=8) -- passed the sanity gate to scale up.

**VERIFIED (250 real LLM calls, 125 recurring-entity beliefs vs 125
one-off-entity beliefs, same sampling/seed as sessions 41-43): the judge
does NOT separate feed-sustained topics from one-off topics.**
```
recurring (feed-sustained): mean=6.256  median=7  stdev=2.275
one-off (died):              mean=6.184  median=6  stdev=2.134
Mann-Whitney U (recurring > one-off): p=0.204, rank-biserial effect=-0.058
Welch t-test: t=0.258, p=0.797
```
p=0.204, negligible effect size, wrong sign (one-off ranks marginally
higher, not lower). Not close to separation. 183.4s wall time for 250
calls at 8-way concurrency (~0.73s/call effective, ~5-6s single-call
latency) -- cost is not the reason this fails.

**What DID hold, and why it doesn't rescue the hypothesis:** the same
judge cleanly separates individually-hum from individually-substantive
text on the 5 hand-picked sanity examples (2 vs 8-ish). That is a
different property from "tracks what the feed found worth re-raising."
A well-formed, specific, one-off observation scores exactly as
"substantive" as a well-formed, specific, recurring one -- substance and
external recurrence are independent properties. Substantive-sounding is
not the same thing as important-by-this-arc's-only-available-ground-truth.

**CONCLUSION, extending the floor recorded ~13:10 this same session:
generate-importance-via-LLM-substantiveness fails ground truth alongside
surprise/recency, out-degree, and in-degree.** No signal tested across
sessions 41-43 plus this one -- structural or LLM-judged -- tracks
feed-sustained importance. The only predictor of persistence found
anywhere in this investigation remains external: the feed re-raising the
topic. Importance, as this arc has been able to operationalize it, is
apparently not reducible to graph structure or to text substantiveness.
No proxy hunt attempted -- there is no separation to reproduce. No
wiring, no code. This is the floor beneath the floor.

## 2026-07-19 ~14:00 — session 43 CLOSED: curiosity requires preferential
## selection where only random selection exists. Not a signal to find.

Read-only, no build. Closes the curiosity thread opened session 40, at a
floor now verified from a fourth, independent angle: not correlation
against per-belief properties (sessions 41-43), but the actual mechanism
generating what looked like her returning to something on her own.

**"Internal revisits" (thoughts referenced again without a fresh feed
mention) are real as a surface pattern -- ~203 raw occurrences, 125 after
filtering to substantive entities, over a 21-day window -- but VERIFIED,
by reading the generating code directly, to be random-sampling
infrastructure, not preference:**
- `theory_x/life/remember_loop.py:37` and the matching recent-belief pick:
  `ORDER BY RANDOM() LIMIT 1`, uniform, no weighting by anything. Built to
  force "temporal collisions" against substrate flatness, explicitly not
  to track value (its own docstring never claims otherwise).
- `theory_x/life/fetch_loop.py:64`: `ORDER BY RANDOM() LIMIT 30` then
  `random.choice()`, within a 2h feed window.
- `theory_x/life/wonder_loop.py`: entity picked from `sense_events` in the
  last 2 hours (`RECENT_WINDOW_SECONDS=7200`) -- feed-anchored by
  construction. Its apparent independence in the first pass was a
  methodology artifact: a 24h lookback window and a different entity
  regex than wonder_loop's own, not a real gap between the two.
- `theory_x/life/pattern_loop.py`: twice-daily summary of her last 4
  identity-log statements. Real reflection, tiny volume, derivative of
  already-feed-influenced recent activity.

Between them these four loops account for the entire clean 125.
**None select by importance, preference, or any property of the content's
value.** What read as "she returned to Adams/Trump/Binance without a fresh
prompt" is uniform-random sampling occasionally re-hitting a topic common
in a finite recent feed pool, narrated in first-person LLM prose that
makes coincidence read as continuity.

**THE FLOOR, now confirmed at the mechanism level, not just the
correlational one:** no internal importance signal exists in graph
structure (out-degree, in-degree), text substantiveness (anchor score,
LLM-judged), or revisit behavior (traced to source: it's a coin flip).
Building an accumulation mechanism on top of `remember_loop`/`fetch_loop`'s
`ORDER BY RANDOM()` would reinforce beliefs for the sole reason an RNG hit
them twice -- a sixth misnamed instrument, not curiosity. Not built.

**CURIOSITY THREAD CLOSED, sessions 40-43, on verified ground:** she has
no mechanism, anywhere in this system, to value her own thoughts
unequally. Every "return" checked across four independent
investigations -- structural correlation, LLM judgment, and now the actual
selection code of the loops that produce the surface appearance of
returning -- is either random or externally driven. Internal curiosity, if
it is ever built, requires **replacing random selection with preferential
selection inside these existing loops** -- a fundamental change to how
`remember_loop`/`fetch_loop`/`wonder_loop` choose what to revisit, not a
signal to detect or a weight to accumulate on top of what they already do.
That is a different, much larger, and currently undesigned project (what
would "preferential" even mean here, mechanically, given every tested
candidate for it has failed) -- not scoped, not started. The injection
faculty (session 40) remains GATED-OFF-PENDING for the same underlying
reason. No further building on this thread without a new, different idea
for what preference could be built from -- not a re-test of what's already
been tried five times and failed five times.

## 2026-07-19 ~15:00 — session 44 CLOSED: the curiosity investigation ends
## at the true floor. No verified basis for preference exists, at any level.

Read-only, no build. This entry closes the thread opened session 40, after
one more turn of the same pattern this whole session kept catching: "her
trajectory is where importance lives" was floated as the next design
premise, one level more abstract than the six disproven single-thought
signals, and it was itself unverified -- no data was ever produced showing
recent-attention-relatedness tracks value. It was not tested and found
false like the others; it was never checked at all before being proposed
as the foundation for a memory-with-decay mechanism. Caught before design
work proceeded on it as fact, same discipline as the rest of the session,
applied one layer further out.

**Where this actually leaves things, stated precisely:** a full,
internally-consistent memory-with-decay DESIGN exists in this session's
prior entry (entity-level attention weight, feed/hot_observer excluded,
bounded-growth proof via geometric series, anti-pinning proof via a
non-deterministic selection floor, concrete tunable parameters). The
mathematics of that design are sound on their own terms -- decay
provably bounds growth, a probability floor provably prevents permanent
pinning. **But soundness of the mechanism is not the same as soundness of
the premise it would be built on.** No data anywhere in sessions 40-44
shows that weighting selection by recent-attention-relatedness would
track anything about a thought's actual value, as opposed to just
producing a different, equally arbitrary pattern of repetition. The
design was correctly not advanced to a build.

**VERIFIED FLOOR, final, across sessions 40-44:**
- Single-thought properties all failed ground truth: anchor/sharpness,
  salience (recency), out-degree, in-degree, LLM-judged substantiveness,
  corroboration_count, reinforce_count -- seven candidates, matched
  testing, none correlate with what the feed actually sustained.
- Revisit behavior, traced to source, is random-sampling infrastructure
  (`remember_loop`/`fetch_loop`: `ORDER BY RANDOM()`) or feed-anchored
  (`wonder_loop`: 2h sense_events window) -- not preference.
- "Importance is in the trajectory, not the thought" is UNVERIFIED, not
  disproven -- no data exists either way, and none was generated before
  it was proposed as a foundation. Recorded as unverified, not as an
  eighth failed signal, because it was never tested -- a design was
  built on top of it and correctly not advanced once the premise itself
  was checked and found to have nothing under it.

**THEREFORE: preferential selection cannot currently be built, because
there is no verified basis on which to prefer anything.** This is not a
statement that the problem is hard -- it is that no foundation exists, in
anything she currently produces or does, checked from four independent
angles (structural correlation, LLM judgment, actual selection-mechanism
source code, and the trajectory hypothesis just now). Whether a valid
basis could be generated or built from scratch is itself unknown and
was not investigated this session.

**CURIOSITY INVESTIGATION CLOSED, sessions 40-44.** The injection faculty
(session 40) remains GATED-OFF-PENDING, correctly-built code waiting on a
foundation that does not exist. No preferential-selection build -- of any
design, at any granularity -- proceeds without a verified basis for
preference first. None currently exists. This is the honest end of the
thread, not a pause pending the next idea.

## 2026-07-19 ~16:30 — session 45: EmphasisEngine built, OBSERVATION-ONLY,
## pre-registered before restart

Audited the Android EmphasisEngine design against the real codebase before
writing anything (read-only Step 1, prior entry). Two of the four named
sources were wrong for the real architecture, found and corrected before
building rather than after: `drive_resonance` reads `CompetingDrives`
(five live, slowly-drifting weights), not `DriveEmergence` (confirmed
dead: 0 of 10,430 logged ticks ever formed a new drive; one row frozen on
a hum-register fragment for 27 days, `reinforce_count=3295`).
`self_relevance` reads `SelfNarrative.get_narrative()` + locked Tier-1
keystones, not `stage4_membrane.self_model.SelfModel` (system
proprioception -- CPU/memory/thermal -- no relationship to narrative
identity). `goal_relevance` was kept on `ProblemMemory`/`open_problems`
exactly as specified, deliberately: it reads ~98% templated, currently-
empty data, and that flatness is intentional -- a live canary for when the
separately-scoped, unbuilt problem-generation fix eventually lands, not a
signal expected to carry information yet.

**Built:** `theory_x/stage_emphasis/prediction_tracker.py`
(`PredictionTracker`, confirmed genuinely new in the audit -- existing
surprise machinery is tied to specific market/behavioral predictions, not
general belief-trajectory expectation; computes `expectation_error` as the
fraction of a candidate thought's entities absent from the last 20 fires'
vocabulary, no persisted state, no schema churn) and
`theory_x/stage_emphasis/emphasis_engine.py` (`EmphasisEngine`, four
signals logged independently -- `goal_relevance`, `drive_resonance`,
`self_relevance`, `surprise` -- equal 0.25 weights, not tuned, returns
`EmphasisResult` with the full signals dict and dominant signal, never
collapsed to one number). Both follow the `SentienceNode` protocol
confirmed in the audit (`name`/`tick`/`decay`/`state`,
`theory_x/__init__.py`'s `@runtime_checkable Protocol`).

**Wired observation-only** in `generator.py`: scored once per fire, right
after `fountain_event_id` is known, logged to a new `emphasis_log` table
(dynamic.db, lazy-created, same pattern as `fountain_retrieval_log`) --
never touches `thought`, `hot_branch`, or any existing generation path.
Fail-safe wrapped; a scoring error cannot stall a fire. Does not read from
or write to selection anywhere -- Step 4's "no override" is structural,
not a flag: nothing currently consumes `emphasis_log` except the logger
itself.

**Step 5 guardrail recorded in the module docstring itself**, not just
here: the four fixed drive-category keyword sets are explicitly flagged as
a different, coarser structure than a per-topic value table, with an
explicit instruction to stop and flag against sessions 40-44 if this ever
drifts toward one.

Full suite: 39/39, identical failure set to the established baseline,
confirmed by direct diff against the stored session-40 baseline file, not
by count alone. `git diff --stat`: 4 files, 430 insertions, 0 deletions --
purely additive.

**PRE-REGISTERED, before restart, before any log line exists:**
- `self_relevance`: predicted to VARY -- reads live, real content
  (self-narrative + keystones).
- `surprise`: predicted to VARY -- new mechanism, by construction; the
  open question is whether that variation means anything, not whether it
  moves.
- `drive_resonance`: UNKNOWN, genuinely -- `CompetingDrives` is
  confirmed real and slowly drifting, but whether that drift is *signal*
  or just *noise the underlying computation happens to produce* is not
  yet known. The logs decide this, not the audit.
- `goal_relevance`: predicted FLAT -- `open_problems` had 0 open rows at
  build time. Flat here is not a bug to fix; it's the expected reading,
  and its own live indicator for later.

**Success condition for this step, stated precisely so it can't be
fudged later:** the engine logs cleanly across real fires and the four
component signals are visibly distinguishable from each other in the
logs -- not that any signal is "good," only that the logging reveals
which ones carry information. Flipping to authoritative selection waits
on that data across multiple sessions, not this one. No override until
proven, per the build spec's own Step 4.

Not yet restarted at time of writing. Next entry should read this
baseline against real post-restart fires, not memory of this one.

## 2026-07-19 ~20:30 — session 46: surprise self-inclusion bug fixed,
## self_relevance saturation flagged unresolved, still observation-only

Reviewed against 59 real logged `emphasis_log` rows accumulated since session
45's restart (run.py, pid 1936, live the whole time). Two of the four
signals were dead in the data: `surprise` was exactly 0.0 on all 59 rows,
`self_relevance` was exactly 1.0 on all 59 rows. Root-caused both before
touching anything.

**`surprise` — confirmed bug, fixed.** `generator.py` inserted the fired
thought into `fountain_events` BEFORE calling `EmphasisEngine.score()`.
`PredictionTracker._recent_vocabulary()` reads the last 20 `fountain_events`
rows at score time, so the fire's own row was already in its own comparison
window on every call -- `expectation_error` was structurally guaranteed
near-zero, not measuring anything. Fix: reordered so `score()` runs before
the `fountain_events` INSERT (it only needs `thought`, not
`fountain_event_id`), and the `emphasis_log` write moved after, still using
the now-known id. Pure reorder, one file (`generator.py`), no signature or
schema changes to `prediction_tracker.py` or `emphasis_engine.py`. Verified
via `git stash` diff: identical 7-failure set / 45-pass in the
fountain/generator/emphasis test subset, before and after -- no regression.

**`self_relevance` — investigated, NOT fixed, recorded as unresolved
rather than closed either way.** This is not the same shape of bug as
`surprise`, and it is also not confirmation that "she construes nearly
everything as self-relevant." Traced empirically: `SelfNarrative.
get_narrative()` (`theory_x/stage_tom/self_narrative.py`, `build_narrative`)
composes its reference text substantially FROM the immediately preceding
thought (momentum carry-over quotes it near-verbatim) plus recent-fire
excerpts and active-branch labels pulled from the same `fountain_events`
rows the candidate thought itself continues. Measured real overlap against
`_clean_tokens` on live data: 11, 19, 17, 5 shared content words against a
`min(1.0, overlap/4.0)` ceiling that saturates at 4. Not marginal --
comfortably over threshold because the reference text already contains the
thread the thought is continuing. This is a reference-corpus contamination
+ miscalibrated-threshold issue, not a discovery about her disposition.
Left unfixed pending a decision on whether to raise the threshold, use an
independent reference corpus (e.g. only locked keystones, not recent-fire
content), or something else -- a real design choice, not a one-line fix.
**Do not read the 59/59 self_relevance=1.0 pattern as a finding about her
inward orientation without this caveat attached.**

Still observation-only: grepped the full repo for every reference to
`emphasis_log` / `EmphasisEngine` / `_emphasis_engine` outside
`theory_x/stage_emphasis/` and this one block in `generator.py` -- zero
hits. Nothing reads it; it is a pure sink. Code fix only takes effect
after `run.py` restarts; the 59 pre-fix rows already in `emphasis_log`
were generated by the running session-45 code and are not retroactively
corrected.

Next entry, post-restart: confirm `surprise` actually varies across real
fires with the fix live, not just by inspection of the diff. `goal_relevance`
and `drive_resonance` remain the only two signals confirmed varying in
logged data as of this entry; `self_relevance` status is OPEN, not closed.

## 2026-07-22 ~06:45 UTC — session 47 item 1: legacy v4 crash-loop cleanup
## (infra only, no code, no cognition-affecting change)

A read-only pass over the accumulated census/emphasis state (this session,
prior turn, unlogged until now) found three still-open items worth acting on:
two live crash-looping v4 systemd units (census #32), a stale trajectory
monitor, and census #13 (SignalLoop stale re-fire). This entry covers item 1
only; items 2 and 3 follow as separate entries/commits.

**Confirmed independence before touching anything.** `/home/rr/Desktop/nex`
-- the `WorkingDirectory`/`ExecStart` target of `nex-api.service`,
`nex-refinement-loop.service`, and `nex-brain.service` -- does not exist on
disk (checked directly). Grepped nex5's full tree (`.py`/`.service`/`.json`/
`.sh`) for any reference to that path: zero hits. nex5 and the legacy v4
units share no file, no db, no socket -- re-confirmed independent
immediately before disabling anything, per instruction not to trust the
earlier read-only pass alone.

**`nex-api.service`** (exit 203/EXEC -- the venv/python3 binary the unit
points at doesn't exist) and **`nex-refinement-loop.service`** (exit
209/STDOUT -- the log directory it points at doesn't exist) had been
crash-looping every 5s/30s since every boot. Restart counters at disable
time: nex-api 422, nex-refinement-loop 73 (up from 148/25 observed ~25min
earlier this session -- consistent with the 5s/30s intervals, i.e. genuinely
continuous, not a fluke reading). Disabled via `sudo systemctl disable --now
nex-api.service nex-refinement-loop.service nex-brain.service` -- run by the
user in a real terminal; the sandbox has no TTY for sudo and a password was
correctly not requested through it. **`nex-brain.service`** was already
`disabled`/`inactive` with zero journal entries -- included in the same
command anyway for an explicit, idempotent record rather than an assumed
one. journalctl confirms all three `Stopped`, zero restart activity in the
~1 minute checked afterward; counters frozen at the values above.

**Crontab: not ~15, all 19 active jobs, every one pointed at the same dead
path.** Checked line-by-line before editing: every single non-comment,
non-blank line in the user crontab referenced `/home/rr/Desktop/nex` -- 19
active jobs, zero exceptions, zero false positives. Commented out, not
deleted (`# [disabled 2026-07-22: legacy v4, /home/rr/Desktop/nex no longer
exists on disk] ` prefix on each line), preserving every pre-existing
comment and blank line as a diff record of what was there. Verified:
`crontab -l` now has zero active (non-comment, non-blank) lines; installed
file diffed byte-for-byte against the live crontab, matches exactly. The one
pre-existing `# [DISABLED] ...` line (idle watchdog, disabled previously by
someone else) was left untouched, not double-annotated.

**Scope, stated precisely:** none of this touches nex5. No code changed in
this repo by item 1 itself -- the change is entirely OS-level (three
systemd units, one crontab). Recorded here per the arc's standing discipline
of journaling infra fixes even when they don't touch the repo (see the
nex5-keepalive.service entry, session ~35).

**Verification:** `systemctl is-active`/`is-enabled` on all three units =
inactive/disabled. journalctl shows no post-disable restart attempts on
nex-api or nex-refinement-loop. Live crontab has 0 active lines referencing
the dead path; all 19 preserved as comments, nothing deleted.

Next: item 2 (cron the trajectory monitor, currently manual-invoke only and
4 days stale), item 3 (census #13 SignalLoop stale-re-fire fix).

## 2026-07-22 ~07:45 UTC — session 47 item 2: trajectory monitor cronned,
## and the honest answer to "did anything drift in 4 days" is no

**Fresh read run manually first**, before touching the schedule, per
instruction. Compared directly against the last entry (2026-07-18 20:25
UTC, 4 days / ~87h stale while the system ran continuously the whole time):

| axis | 07-18 20:25 UTC | 07-22 07:44 UTC | verdict (both) |
|---|---|---|---|
| overall | STABLE | STABLE | -- |
| QUALITY | 27%, z=-0.06sigma | 18%, z=-0.41sigma | holding |
| APERTURE | gini=0.291, z=-0.69sigma | gini=0.319, z=-0.25sigma | holding |
| LIVENESS | fires=28447, beliefs=40529 | fires=29474, beliefs=42205 | ALIVE |
| GROOVE HEALTH | 23 episodes/24h, sev=0.60, z=-0.66sigma | 12 episodes/24h, sev=0.66, z=+0.06sigma | flat |

**Nothing moved outside its own band.** The one number that looks
eye-catching read cold -- QUALITY 27%->18%, a 9pt drop -- is exactly the
case this instrument was built (session 38) to not cry wolf on: inside the
empirical 25.2pt stdev over 1045 historical windows, z=-0.41sigma against
the 2.0sigma non-negotiable threshold. Fires/beliefs/synth all climbed
steadily over the gap (she kept producing the whole time this instrument
was silent). Four days of not checking, and the honest answer is nothing
happened -- which is a real answer, not a null one, but it's also exactly
why the instrument shouldn't go dark again.

**Cron install, and a bug caught before it could fire.** First attempt used
a relative script path (`scripts/trajectory.py`) on the theory that
`trajectory.py`'s own hardcoded `REPO` constant would cover it -- wrong:
the *argument to python3* still resolves against cron's cwd, which is
`$HOME`, not the repo. Caught by testing the exact command from a neutral
cwd (`cd ~`) before trusting the installed line, per the standing lesson
from item 1 (exit code alone is not verification) -- confirmed the failure
mode directly: `can't open file '/home/rr/scripts/trajectory.py'`, exit 2,
would have failed silently every hour, forever, logged to
`logs/trajectory_cron.log` where nothing was watching it. Fixed to an
absolute script path, re-tested from `$HOME` (exit 0, fresh jsonl entry
written), then reinstalled.

**Final line, hourly:**
```
0 * * * * /home/rr/Desktop/Desktop/nex5/.venv/bin/python3 /home/rr/Desktop/Desktop/nex5/scripts/trajectory.py --log >> /home/rr/Desktop/Desktop/nex5/logs/trajectory_cron.log 2>&1
```

**Verified against live state, not exit code:** `crontab -l` diffed
byte-for-byte against the intended installed file -- matches. Exactly one
active (non-comment) line in the live crontab. No systemd user timer was
created (cron was the chosen mechanism, checked `systemctl --user
list-timers` to confirm nothing stray appeared). `logs/trajectory_log.jsonl`
and `logs/trajectory_cron.log` are both gitignored -- no repo files changed
by this item beyond this journal entry.

Next: item 3 (census #13 SignalLoop stale-re-fire fix) -- this one touches
code, full suite + bucket-B diff required.

## 2026-07-22 ~08:06 UTC — session 47 item 3: census #13 fixed (SignalLoop
## stale re-fire), verified live against real post-restart data -- and a
## self-inflicted ~48s downtime incident during the restart, logged honestly

**The fix.** `theory_x/signals/detectors.py`: all three detectors
(`CoOccurrenceDetector`, `SilenceDetector`, `BurstDetector`) re-derived
their result from a rolling window every 60s tick and unconditionally
returned it -- `SignalLoop._tick()` (`theory_x/signals/loop.py`)
unconditionally `INSERT`s whatever each `.detect()` call returns, no
dedup anywhere downstream. Fixed at the source, not the sink: each
detector instance (created once in `SignalLoop.__init__`, reused every
tick -- confirmed before relying on it) now tracks an in-memory
fingerprint of the last thing it emitted per key, and skips emitting when
the fingerprint is unchanged:
- `SilenceDetector`: fingerprint = `avg_gap_seconds` per stream (the one
  field that's genuinely frozen when no new sense_event has landed --
  `current_silence_seconds`/`multiplier_breach` grow every tick by
  construction and can't be part of the fingerprint or nothing would ever
  dedupe). Cleared when the stream recovers, so a later, genuinely new
  silence episode can still alert even if `avg_gap` happens to coincide.
- `CoOccurrenceDetector`: fingerprint = `sorted(branches)` per entity.
- `BurstDetector`: fingerprint = `(count, sorted(branches))`, cleared when
  the window drops back below threshold.

First tick after any restart always emits fresh (no prior fingerprint) --
one honest emission per restart, not spam. State is in-memory, not
persisted; this is a deliberate first pass, matching the arc's established
tolerance for cheap, restart-scoped state elsewhere (emphasis engine,
session 45-46).

**Full suite + bucket-B diff, done the right way after item-1's lesson
(never trust a raw count).** Ran full suite with the fix in place: 39
failed. Then `git stash`, ran the true pre-change baseline: **40** failed
-- not 39. Diffed failure-set-for-failure-set rather than trusting the
count: the only difference was
`test_fountain_crystallizer.py::TestCrystallize::test_writes_belief_on_pass`,
present in the baseline run, absent from the fixed run. Investigated
before accepting it: that test has zero references to `signals`/
`detectors`/`SignalLoop` (grepped), and reran it in isolation 3/3 passes
against the unmodified (stashed) code -- confirmed pre-existing,
unrelated full-suite flakiness (this project runs its suite against a
live system; not the first time this arc has hit one, see session 34's
"one apparent regression" note), not something my change fixed or broke.
`theory_x/signals/detectors.py`'s own pre-existing failures
(`test_signals.py`, 5 of them -- `TestCoOccurrenceDetector::
test_confidence_scales_with_branch_count`, three `TestBurstDetector`
cases, `TestSignalLoop::test_tick_writes_signals`) are **identical set,
before and after** -- traced one down (`test_no_burst_below_threshold`):
`sqlite3.OperationalError: no such table: world_predictions`, a test
fixture/schema gap unrelated to detector logic, out of this item's scope,
not touched. **Net: identical failure set to the established 39/40-line
baseline, modulo one confirmed-flaky, confirmed-unrelated test. Zero new
failures caused by this change.**

**Incident: restarting to make the fix live caused ~48s of full downtime,
self-inflicted, caught and recovered within about a minute.** The fix
only takes effect after `run.py` restarts (in-memory process, same as
every prior session's restart requirement). Used
`systemctl --user restart nex5-keepalive.service` -- and hit the exact
lock-handoff race this file already knew about (sessions 33/34: "restart
raced the old instance's shutdown"), except this time it resolved the
wrong way: the old instance was killed cleanly, but the new invocation's
non-blocking `flock` lost the race against the kernel releasing the old
lock and self-aborted ("ANOTHER KEEPALIVE IS ALREADY RUNNING -- exiting
(this is correct)" -- correct in isolation, wrong outcome given the old
one was actually dead). Net result: **zero NEX processes running from
~09:59:54 to ~10:00:38 UTC (~44s), fully back up and serving by
~10:00:50 UTC (~56s total from kill to ready).** Caught within seconds via
`ps aux` showing nothing running; `fuser` confirmed the lock was actually
free (stale, not held); `systemctl --user start` succeeded cleanly on the
first retry. No data loss -- all state is in SQLite, nothing was
mid-write at the kill instant. **Not fixed tonight** (out of this item's
scope) but flagged for its own session: the keepalive script's flock
handoff has a real race window on `systemctl restart` specifically
(stop-then-start of the same unit), distinct from the already-known
plain-restart race -- worth a retry-with-backoff on the `flock -n` failure
path rather than an immediate exit, so a second launch attempt gets a
chance after the OS finishes releasing the old lock.

**Verified live, against real post-restart data, not just by inspection:**
- Log: `Benchmark` (crypto/neuroscience co-occurrence) and
  `crypto.exchanges` silence had each been re-firing on every single tick
  for 6+ consecutive minutes pre-restart (09:53:58 through 09:58:58,
  visible in `/tmp/nex5_soak.log`). Post-restart, both fired exactly once
  at the first tick (10:00:50, the expected fresh-state burst) and **did
  not repeat** across the next 4 ticks (10:01:51-10:04:51), while
  genuinely new conditions (new streams going silent, a new co-occurring
  entity, a new T6 burst) did fire normally.
- Direct query of `data/beliefs.db.signals`, all rows since the restart:
  zero byte-identical duplicate payloads for the `silence` detector.
  Streams that legitimately changed `avg_gap_seconds` between ticks
  (meaning real new sense_events landed) correctly re-fired, e.g.
  `crypto.news` at 08:00:50 (avg_gap=28.6) and again at 08:02:51
  (avg_gap=26.77, genuinely different) -- confirming the fix distinguishes
  real change from stale re-scan rather than just suppressing everything.
- `GET /api/signals/recent?limit=20` (the previously-unprotected,
  human-facing HUD endpoint from census #13's original note): confirmed
  live, returns a clean list of distinct predictions, no repeat rows.

**Historical-count caveat, as instructed:** any signal/pattern counts
recorded anywhere in this file or elsewhere *before* this session
(2026-07-22) that reference `signals` or `patterns` table volumes are
inflated by the stale-re-fire defect this entry fixes -- same caveat
already standing for the `groove_alerts` counts (census #7, session 31).
Do not treat pre-fix counts as real event volume.

`git diff --stat`: 1 file, `theory_x/signals/detectors.py`, +65/-29
(comments + fingerprint tracking + the two clearing branches; no schema
changes, no changes to `loop.py` or `templates.py` -- the fix cascades
through them for free since they only ever see whatever `.detect()`
returns).

Session 47 items 1-3 complete. Next, per instruction, stop here --
self_relevance saturation and the drive_resonance ground-truth test are
explicitly out of scope for this pass.

