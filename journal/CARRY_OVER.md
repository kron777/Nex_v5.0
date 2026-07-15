
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

