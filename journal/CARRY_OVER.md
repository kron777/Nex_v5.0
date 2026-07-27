<!-- START HERE — standing header, updated 2026-07-26 ~15:20. Read this before the log below. -->

## OPEN DECISIONS (not yet acted on)
- **Genius scorer** (`theory_x/genius/score_v2.py`): F3 dead (weight=0), F2
  negative-weighted, F5 dominates by far, F4 nearly inert on real data. Fix
  proposed, NOT implemented. Baseline pre-registered (see below) so a future
  edit can be diffed against it. See 2026-07-26 ~11:41 entry.
- **`_real_fires()` fire-recycling** (`theory_x/stage_tom/self_narrative.py`):
  the family-trips tombstone (2026-07-25 confabulation) did NOT stop
  recurrence — the carrier is raw `fountain_events` text re-injection, not
  belief retrieval. Five live paths mapped, one fixed (`_recent_hot` tier
  filter). A within-window content dedup was tested against real history and
  REJECTED (fires more on normal output than on the actual runaway — see
  2026-07-26 ~13:44 entry). Real fix needs clause-level matching, not
  whole-thought similarity; not yet attempted, flagged as historically
  failure-prone (sessions 40-44 pattern) if rushed.
- **Doubt Engine denominator**: `use_count` is a usable interim proxy
  (broad, imprecise). `fountain_retrieval_log` is the precise answer but
  was only ~10h old as of 2026-07-26 ~11:00 — needs more calendar time
  before trusting it. No build needed yet either way.

## STANDING CAVEATS (cause misreads if missed)
- **Bonsai `focus_num` resets to 0.0 on every process boot**, no
  persistence. Fast branches (emerging_tech, computing, markets, crypto)
  recover in ~1h; slow-poll branches (ai_research, cognition_science) take
  **~2h**. Check time-since-boot before reading a low reading as drift.
- **`decay_pass()` near-zero demotions = the fix working**, not stalled.
  Fixed 2026-07-26 (`4528074`, COALESCE NULL-bypass); confirmed against a
  correctly-empty live query with a confirmed-alive sibling loop. Don't
  re-diagnose a quiet decay_pass as broken.
- **Genius striking-rate baseline: 25.6% (175/683), frozen 2026-07-26
  ~11:00.** Full per-feature distribution in that entry. Any future scorer
  edit should diff against this exact snapshot, not against a later read.
- **`fountain_retrieval_log` has been at 100% coverage since the
  2026-07-24 22:39 restart** (confirmed real via an 88-fire overnight
  sample, not restart-lottery). Restarts since then (several 2026-07-26)
  reset uptime but not this fix.

## THE DOCUMENTED-BUT-DEAD PATTERN
Named this weekend: a docstring/comment claims a behavior the code doesn't
actually perform (disabled by an unrelated flag change, or never built past
the description). Instance list: `## documented-but-dead instances` section,
2026-07-26 ~10:53 entry (8 instances). **Instance 9: `NEX5_SPEECH_ENABLED=
false`**, a 2026-07-24 SIGILL stopgap left in after the crash stopped
recurring on its own — closed 2026-07-26, see that entry.

## CONFIRMED WORKING — don't re-investigate
- `own_rows`/`fetch_residue_beliefs`/`_recent_hot` tier<8 filters
  (2026-07-26, three commits) — tombstoning is now retrieval-effective for
  belief-sourced paths (not `_real_fires()`, see above).
- `drive_resonance` dropped from `EmphasisEngine.score()` combiner
  (`d52ec78`) — ground-truth tested and failed, correctly removed.
- Speech re-enabled 2026-07-26 (`NEX5_SPEECH_ENABLED` flag removed) — SIGILL
  confirmed zero recurrences since 2026-07-24 19:00 across 34 restarts
  before re-enabling. **Untested against a cold boot** (validated on warm
  restarts only — the last real reboot, 2026-07-25 04:59, predates
  re-enabling). CHECK FIRST after tomorrow's boot: grep
  `/tmp/nex5_soak.log` for "Kokoro pre-loaded successfully" vs an Illegal
  instruction/SIGILL line before trusting it further.
- Empty decoy DBs at repo root (`beliefs.db`/`dynamic.db`/`conversations.db`,
  0 bytes, stale April/May) deleted 2026-07-26 — `data/` was always
  canonical (`substrate.db_paths()`), nothing depended on the deleted
  files' content. Residual risk, not closed by deleting them: any bare
  `sqlite3.connect("beliefs.db")` run from repo root (e.g.
  `train_curator.py`'s `--db` default) silently recreates the same
  trap — always resolve via `data/` or `db_paths()`.

<!-- END STANDING HEADER — log begins below, chronological, oldest first. -->

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

## 2026-07-22 ~08:30 UTC — session 48: nex_keepalive.sh flock handoff race
## fixed (the incident from item 3), tested against both failure modes

**The fix.** `nex_keepalive.sh`'s single-instance guard called `flock -n 9`
exactly once and exited immediately on failure -- correct against a
genuinely-held lock, wrong against the handoff window on `systemctl
restart` (stop-then-start of the same unit), where the old instance's
lock isn't guaranteed released by the instant the new instance's first
attempt runs. Item 3's restart lost exactly that race and took the whole
system down for ~48s with no automatic recovery (the script exits 0 on
this path specifically so a clean no-op isn't treated as a crash by
`Restart=on-failure` -- correct in general, but it means nothing brings
NEX back up if the race is lost; only manual intervention did, today).
Fixed: `flock -n 9` now retries up to 10 times, 1s apart (~10s worst-case
budget), before giving up and exiting exactly as before. A genuinely-held
lock is unaffected by this change -- retries only help when the lock is
about to free up; against real, sustained contention every attempt fails
identically and the loop still falls through to the same rejection.

**Tested both failure modes directly, not just by re-running the live
restart and hoping it reproduces (it didn't, either time -- see below).**
Built an isolated test harness reusing the exact retry code against a
throwaway lock file, unrelated to the live system:
- **Handoff race (the actual bug class):** background process holds the
  test lock 3s (shorter than the retry budget), releases. Result:
  `ACQUIRED on attempt=4 elapsed=3.01s`. Old code would have failed on
  attempt 1 -- this is the direct, controlled proof the fix saves exactly
  today's incident.
- **Genuine sustained contention (the guard's core job):** background
  process holds the test lock 15s (longer than the budget). Result:
  `FAILED to acquire after attempt=10 elapsed=10.03s -- correctly
  rejected`, exit 1. Bounded, not indefinite -- the guard still works.

**Also tested against the live system, both directions:**
- Manually ran `nex_keepalive.sh` a second time while the real
  systemd-supervised instance (holding the lock persistently) was up:
  correctly exhausted all 10 retries (~10s, up from instant), printed the
  same "ANOTHER KEEPALIVE IS ALREADY RUNNING" message, exit 0, and
  launched no second `run.py` -- confirmed via `ps aux` before and after.
  The only user-visible cost of this fix is that a genuine double-start
  now takes ~10s to report instead of being instant; judged acceptable
  against eliminating an indefinite-outage failure mode.
- Two live `systemctl --user restart nex5-keepalive.service` cycles:
  both acquired the lock immediately (no retries needed -- the race is
  timing-dependent and didn't reproduce live either time, which is why
  the isolated harness above is the real evidence, not these). Both
  restarts completed cleanly: `KEEPALIVE START` logged within 1s of
  systemd's `Started`, NEX confirmed up each time. Measured actual HTTP
  availability across the second restart via tight polling
  (`/api/system/status` every 0.2s): ~11s unreachable, which is the
  ordinary, designed cost of `launch_nex()`'s own kill-old/free-port/
  relaunch sequence (2s+2s built-in sleeps plus model-load boot time),
  not a race failure -- categorically different from the ~48s
  no-recovery outage this fix targets. Live process confirmed healthy
  and serving (`http=200`) after both tests.

`git diff --stat`: 1 file, `nex_keepalive.sh`, +20/-1 (the retry loop and
its comment; no other logic touched).

## 2026-07-22 ~08:35 UTC — session 48 item 4: self_relevance saturation
## fix, PRE-REGISTERED before restart

**Diagnosis (session 46, confirmed at 10x data session 47):**
`self_relevance`'s reference corpus was `SelfNarrative.get_narrative()`
(momentum carry-over quotes the immediately-preceding thought
near-verbatim, plus recent-fire excerpts from the same `fountain_events`
rows the candidate thought itself continues) concatenated with locked
Tier-1 keystones. The narrative half shares vocabulary with the candidate
thought by construction, not because the thought is actually
self-relevant.

**BEFORE, measured right now, pre-fix:** 504 total `emphasis_log` rows,
501/504 (99.4%) at `self_relevance=1.0`, exactly 3 distinct values ever
seen (0.25 x2, 0.75 x1, 1.0 x501). (Session 46 caught this at 59/59;
session 47 read it at 463/466; today, pre-fix, it's 501/504 -- same
saturation, larger sample, growing monotonically as expected from an
uncorrected structural bug, not noise.)

**Fix, and why this option over the alternative:** removed
`SelfNarrative.get_narrative()` from the reference corpus entirely --
`_self_relevance()` now reads locked Tier-1 keystones ONLY
(`theory_x/stage_emphasis/emphasis_engine.py`). Considered raising the
overlap threshold instead; rejected: the contamination is structural (the
reference text and the candidate share vocabulary by construction), not a
magnitude problem, so a higher threshold would still be measuring "did
this thought quote its own predecessor," just less often -- exactly the
kind of tuned-constant patch this arc has already been burned by
repeatedly (sessions 40-44, seven signals killed by exactly this shape of
premise). Keystones are stable across fires and don't shift with
momentum, so overlap with them is real information about identity
content. `EmphasisEngine`'s `self_narrative` constructor param was
removed along with it (no longer read anywhere in the class) rather than
left as a dead parameter; `generator.py`'s instantiation updated to match
(`self._self_narrative` itself is untouched -- still live, still used
elsewhere in `generator.py` for its own unrelated prompt-building path,
confirmed by grep before editing).

**Observation-only invariant re-confirmed after the edit, not assumed:**
grepped the full repo for `emphasis_log`/`EmphasisEngine`/
`_emphasis_engine` outside `theory_x/stage_emphasis/` and the one
`generator.py` instantiation block -- zero hits, still a pure sink.

**Full suite + bucket-B diff:** 39 failed, identical set to item 3's
already-investigated baseline (diffed both ways, zero difference against
the post-item-3 39, and the same single confirmed-flaky/unrelated
`test_fountain_crystallizer` line as the only difference against the true
40-failure clean-tree baseline). Zero new failures from this change.

**PREDICTED, before restart, so it can't be fudged after the fact:** the
next ~20 post-restart fires should show `self_relevance` values spread
across a real range (not clustered at exactly 1.0), because the
contamination source is gone and keystone-overlap for an arbitrary
thought should mostly fall well under the `overlap/4.0` saturation
ceiling. Pass condition is the histogram, not the diff: the signal has to
actually vary, not just "the code changed." Not predicting a direction
(more or less self-relevant on average) -- only that it stops pegging at
1.0. Next entry reads this against real post-restart data.

**VERIFIED, post-restart, PASS.** Restart via `systemctl --user restart
nex5-keepalive.service` (with session 48's flock fix live) completed
clean, no gap: `http=200` within seconds, confirmed by direct poll. First
20 fresh `emphasis_log` rows after restart (id > 505):

self_relevance: min=0.0, max=1.0, avg=0.438, **5 distinct values**
(0.0 x5, 0.25 x3, 0.5 x6, 0.75 x4, 1.0 x2) -- spread across the full
range, only 2/20 (10%) at 1.0, versus 501/504 (99.4%) pre-fix. Matches
the pre-registered pass condition exactly: the signal varies, not just
"the code changed." `dominant_signal` breakdown over the same 20 rows is
now spread across all four (self_relevance 8, goal_relevance 5, surprise
4, drive_resonance 3) rather than self_relevance alone winning ~70% of
fires by saturation artifact.

Other three signals, same window, for the full live picture: `surprise`
min=0.0 max=1.0 avg=0.417 (3 distinct), `drive_resonance` min=0.0 max=1.0
avg=0.328 (**16 distinct** -- still the richest signal, unchanged by this
fix), `goal_relevance` min=0.0 max=1.0 avg=0.15 (2 distinct, still mostly
template-noise-flat per the earlier finding).

**Engine status: 3 of 4 signals now confirmed varying** (`surprise`,
`drive_resonance`, `self_relevance`); `goal_relevance` remains the one
outstanding flat/templated axis, unchanged from prior sessions' finding.
Still strictly observation-only -- invariant re-confirmed by grep before
this entry was written, see above.

`git diff --stat`: 2 files, `theory_x/stage_emphasis/emphasis_engine.py`
(+/- docstring and `_self_relevance`/`EmphasisEngine` signature changes)
and `theory_x/stage6_fountain/generator.py` (1-line kwarg drop + comment
update). Full suite + bucket-B: 39/39, identical to item 3's baseline.

## 2026-07-22 ~09:00 UTC — session 48 item 5: drive_resonance run through
## the established ground-truth test -- FAILS, same as the other seven

Read-only, no build, no restart. Last open question from the curiosity
arc (sessions 39-44): `drive_resonance` is the one emphasis signal
confirmed genuinely varying (329 distinct values logged) that did not
exist when the seven candidates were killed. Checking it isn't the same
mistake as session 44's premise-skip -- no design is riding on the
result either way, it's just the one candidate never tested.

**Methodology, reused exactly, not reinvented.** Same ground truth as
sessions 39-44: entities `open_problems` re-raised as a separate,
brand-new problem on a different day ("recurring") vs. entities that
appeared once, never mentioned again ("one-off"). Rebuilt the
classification fresh from live data (entity = quoted string in the
problem title, recurring = title with the entity opened on >=2 distinct
days): **34 recurring / 165 one-off** (session 41 had 38/193 at the time
-- consistent growth since, same top entities: Iran, Bitcoin, Anthropic,
GPT). Matched sampling, n=34 per side (seed=42 -- the original seed isn't
recorded in this file, flagged rather than silently assumed), all belief
rows mentioning each entity: **5,007 recurring-linked beliefs vs 3,470
one-off-linked beliefs.** Same three tests sessions 42-43 used for this
exact skewed, zero-heavy shape of distribution: Mann-Whitney U, Welch
t-test, permutation test on the mean difference (10,000 resamples).

**Methodological caveat, stated plainly because it matters:**
`drive_resonance` did not exist during the original test window --
there's no way to score old belief content with the drive weights that
existed *at the time*. Scored all of it against one frozen snapshot of
today's live `CompetingDrives` weights, applied identically to both
groups so the comparison stays fair between them. Not a true historical
replay like the other seven signals got; the closest honest substitute
given the signal is new. Noted because it should be read alongside the
result, not because it changes the verdict -- the result isn't borderline.

**Result:**
```
              n      zero-frac  mean    median
recurring     5007   69.5%      0.0641  0.0
one-off       3470   71.2%      0.0614  0.0

Mann-Whitney U:  p=0.196, rank-biserial effect=-0.013
Welch t-test:    p=0.245
Permutation:     observed diff=0.0027, p=0.240 (10,000 resamples)
```

**VERDICT: FAILS ground truth.** All three tests agree -- no significant
difference, negligible effect size, same null shape as in-degree
(p=0.83, effect=0.027, session 43) and the other six. `drive_resonance`
does not distinguish topics the world sustained from topics it mentioned
once and dropped. ~70% of both groups score exactly 0.0 -- the coarse,
fixed five-category keyword sets rarely fire on ordinary belief content
at all; a plausible sparse-coverage explanation, not a confound worth
chasing given the result is cleanly null rather than borderline (unlike
in-degree's p=0.047-on-the-mean that turned out to be a hot_observer
artifact -- no such digging is warranted here).

**Eight of eight candidate signals checked across this entire arc now
fail the same ground truth:** anchor/sharpness, salience (recency),
out-degree, in-degree, LLM-judged substantiveness, corroboration_count,
reinforce_count (sessions 40-44), and now drive_resonance. This closes
the curiosity arc's last open thread. No new candidates are queued. The
verified floor from session 44 stands, now with one more signal
confirmed under it rather than untested above it.

## 2026-07-22 ~10:14 UTC — session 48 item 9: census #9 fixed -- persona
## content no longer distilled into beliefs, PRE-REGISTERED then verified

**Design approved before code** (full trace in the prior turn's report,
not duplicated here): `_sense_distillation_loop`
(`theory_x/stage2_dynamic/__init__.py`) had zero exclusion for
`stream='external.other_mind'`, so persona_responder.py's replies were
becoming permanent tier-7 `precipitated_from_sense` beliefs (~30/day,
confirmed live) despite both `persona_responder.py`'s docstring and
`run.py`'s launch comment stating, unconditionally, that the persona
subsystem "touches no beliefs" -- not conditional on `NEX5_SOCIAL_N`,
which is a separate, already-correctly-implemented knob gating whether
`generator.py`'s Layer 4 reads it back into the fountain prompt. Fix:
`AND stream != 'external.other_mind'` added to the distillation query,
symmetric with the existing `internal.%` exclusion. Unconditional, not
`SOCIAL_N`-gated, matching the doc's actual unconditional claim. One
line of logic, one docstring addition explaining it. Real external
signal (news/arxiv/etc) untouched by construction -- different stream
values, same query.

**Existing 1,531 persona-derived beliefs left untouched, confirmed safe
to leave:** 13,158 `belief_edges` rows touch them, well-integrated into
the live graph; no code anywhere special-cases `branch_id='external'` in
retrieval (grepped), so their current classification gates nothing.
Relabeling would be a large, risky operation for zero functional
benefit. Not attempted.

**PRE-REGISTERED, before restart:** before = ~30 persona-derived beliefs
created per day (397 real `precipitated_from_sense` beliefs/24h measured
immediately pre-restart as the "real signal" baseline). Predicted after =
**0 new** `branch_id='external', source='precipitated_from_sense'`
beliefs, real-signal rate (~398/day) unchanged.

**Predicted downstream effects, recorded now so a future session doesn't
read either as an unexplained anomaly:**
1. `CoOccurrenceDetector` (`theory_x/signals/detectors.py`) reads
   `beliefs` without excluding `precipitated_from_sense` -- a small, real
   drop in entity-matching candidates specifically from the 'external'
   branch is expected going forward, not a defect.
2. Trajectory monitor's APERTURE axis (branch-focus gini/entropy):
   expected small drift as 'external' branch's share of new beliefs
   drops to zero going forward -- expected, not anomalous.

**Full suite + bucket-B:** 40 failed, **zero difference** against the
true clean-tree baseline (diffed directly, not by count). The one
difference against the 39-count post-item-3 list is the
already-confirmed-flaky, unrelated `test_fountain_crystallizer` test
(same one investigated in item 3's entry). Zero new failures from this
change.

**VERIFIED, post-restart, PASS on both halves.** Restart clean, no gap
(`http=200` within seconds). Captured exact restart timestamp
(1784715278 UTC) and queried directly against it:
- `branch_id='external', source='precipitated_from_sense'` beliefs since
  restart: **0**. All-time count still exactly 1,531 -- frozen, not one
  new row.
- Real `precipitated_from_sense` beliefs since restart (non-external
  branches): 7, across neuroscience/news/cognition/emerging_tech --
  real distillation continuing normally.
- `external.other_mind` **sense_events** since restart: 2 -- confirming
  persona_responder.py itself is completely unaffected (still writing
  exactly as before); the gate held even as the source kept producing,
  not just because nothing happened to trigger it.

`git diff --stat`: 1 file, `theory_x/stage2_dynamic/__init__.py`, +12/-0
(one query clause, one docstring paragraph).

## 2026-07-22 ~10:55 UTC — session 48 item 7: census #7 fixed --
## groove_alerts stale re-fire, same disease/fix as #13, verified by an
## isolated controlled test (no live trigger occurred to catch directly)

**Same disease as #13, confirmed live before touching code:**
`GrooveSpotter.detect_all()` (`theory_x/diversity/groove.py`) runs every
60s from `DiversityLoop`, re-deriving all four checks
(`_detect_exact_repetition`, `_check_ngrams`, `_detect_template_repetition`,
`_check_centroid_tightening`) from the same rolling 20-fire window every
tick, unconditionally re-inserting into `groove_alerts` whenever a
condition held. Historical scale, queried before the fix: `ngram_repetition`
48,769 rows, `template_repetition` 32,604 rows, `exact_repetition` and
`centroid_tightening` **zero rows ever** (never triggered in this table's
whole history -- fixed anyway for consistency, same latent bug, just
never yet hit). Single patterns re-inserted thousands of times
identically: `"the balance between"` 6,278x, `"i notice that"` 5,511x,
`"feels like the"` 3,929x -- ~2.5 months of continuous inflation
(1777041529 to 1784630333). `_push_cooldown()` (blocks future
crystallizer content) is a separate downstream mechanism and does not
gate the `groove_alerts` INSERT itself, confirmed by reading the code.

**Fix:** same fingerprint-dedup pattern as #13, one fingerprint field per
detector, tracked on the `GrooveSpotter` instance (created once in
`DiversityLoop.__init__`, reused every tick -- confirmed before relying
on it): `_last_exact_content` (the repeated sentence), `_last_ngram_pattern`
(the top trigram), `_last_template_ids` (frozenset of fire ids sharing
the template), `_last_centroid_ids` (tuple of current-window fire ids).
Each cleared at every point the underlying condition stops holding, so a
later genuinely-new recurrence still alerts even if it happens to produce
an identical fingerprint by coincidence.

**Predicted side effect, named before it's rediscovered as a surprise:**
`_push_cooldown()` used to get re-triggered every ~60s tick a condition
persisted, continuously refreshing `signal_cooldown`'s `cooldown_until`
(`COOLDOWN_HOURS=2`) far past the nominal 2h window for as long as the
stale re-scan kept firing. Post-fix, cooldown is pushed once per genuinely
new episode and correctly expires after 2h as designed -- **this is a
real behavior change, arguably a correction of an unintended side effect
of the original bug, not a regression.** Flagging it now so a future
session doesn't read a shorter effective cooldown window as unexplained.

**Full suite + bucket-B:** 39 failed, identical to the established
post-item-3 baseline (diffed directly, zero difference); the only
difference against the true 40-count clean-tree baseline is the same
already-confirmed-flaky, unrelated `test_fountain_crystallizer` test.
Zero new failures.

**Verified two ways, honestly distinguished:**
1. **Isolated controlled test** (throwaway fake reader/writer, synthetic
   data, not the live system): tick 1 (template + ngram condition present)
   emits both; tick 2 (byte-identical window) produces **zero** writes --
   direct proof of suppression; tick 3 (window changed, condition still
   holds via different content) correctly re-emits with a new fingerprint;
   tick 4 (a distinct new template pattern) correctly emits again. This is
   the primary, rigorous evidence the fix works.
2. **Live restart + 15-minute bounded poll**, honestly reported: restart
   was clean (`http=200` within seconds), but **zero groove_alerts rows
   fired in the 15 minutes post-restart** -- no natural trigger occurred
   to catch directly, consistent with the pre-fix data (zero rows in the
   24h+ immediately before restart too; this condition is episodic/sparse,
   not continuously active like #13's silence detector was). All-time
   counts confirmed unchanged immediately post-restart (48,769 / 32,604,
   exactly matching pre-restart). **Live confirmation of "repeats stop"
   was not caught this session** -- the isolated test is the real
   evidence, not this. Not fudging the two together.

**Historical-count caveat, as instructed:** any `groove_alerts` counts
recorded anywhere in this file or elsewhere before 2026-07-22 are inflated
by the stale-re-fire defect fixed in this entry -- same caveat as census
#13 and the original session-31 `groove_alerts` finding (census #7 itself).
Do not treat pre-fix counts as real distinct-episode volume; treat them as
(real episode count) x (however many 60s ticks each one persisted for,
sometimes thousands).

`git diff --stat`: 1 file, `theory_x/diversity/groove.py`, +40/-0 (four
fingerprint fields + one check-and-clear per detector, no schema changes,
no changes to `loop.py` or `_push_cooldown` itself).

## 2026-07-24 ~19:30 — session 48 continued: fountain template collapse root-
## caused and fixed, focus_loop's session-39 deferral came due, a live SIGILL
## watched not chased. Four commits.

**Five fixes closed today:**

1. **`ground_self_belief.py` FK trap.** `--remove` used to run a raw DELETE,
   which would hit the exact FK constraint the UPDATE-in-place refresh fix
   (session 48, scorecard_loop investigation) stopped hitting on refresh --
   `belief_edges`/`novel_association_log` still reference belief 206714 with
   no `ON DELETE CASCADE`. `--remove` now checks every table in
   `_BELIEF_ID_REFERRERS` first and refuses, naming tables and row ids, exit
   non-zero, rather than cascading or hitting the constraint. **Proved by:**
   both branches run against a disposable copy of `beliefs.db`'s schema (not
   the 9.4GB production file) -- seeded with a referencing `belief_edges` row
   and a `novel_association_log` row, `--remove` refused and named both
   exactly; references cleared, `--remove` deleted cleanly. Commit `511ab33`.

2. **Fountain template collapse** ("I'm restless and keep coming back to X",
   sometimes with the literal placeholder). Two compounding causes: (a) a
   chat-only self-report exemplar in `voice/llm.py`'s system prompt was
   universal across every register including fountain's internal calls, so
   any fire that couldn't produce real content latched onto the exemplar's
   own line as an escape hatch -- fixed via a `VoiceRequest.self_report_examples`
   flag (default True for chat, fountain's internal call sites opt out); (b)
   a self-sealing trap in RECONCILE: it pairs the two oldest-touched open
   problems but only bumps `last_touched_at` via `observe()`, which requires
   >=300 chars. A pair stuck producing short output never gets touched, so
   it can never age out of the pairing query -- #350/#351 were locked this
   way for ~18 hours before being manually closed. `ProblemMemory.touch()`
   bumps `last_touched_at` with no observation, called whenever a reconcile
   pass doesn't qualify for `observe()`. **Proved by:** 30-day fire data --
   the pre-fix "restless" population had median 91.5/max 198 chars (matches
   the disease exactly, not a representative baseline); post-fix fires run
   median ~400-950 chars, several fires now content-verified as genuine
   RECONCILE output ("NEXT STEP", "genuinely DIFFERENT angle" phrasing,
   matching the live ANTILOOP prompt text, not coincidence). `touch()`
   itself verified via an isolated 3-problem seed against a disposable copy
   of `conversations.db`: advances the targeted row only, and the pairing
   query correctly rotates to the third problem once the first two are
   touched. Commit `f1f774c`. **touch() has never fired live** -- checked
   both before and after committing; every live RECONCILE_WB pass since has
   cleared 300 chars, either via the normal `observe()` gate or via
   COMMIT_CLOSE's bypass (see below). Its correctness rests on the isolated
   test, not a live firing. Next session: grep is not enough to catch the
   first live execution -- `touch()` logs on success now (this session's
   logging fix, below) but nothing logged before that, so a firing before
   today's restart would be invisible. Diff two `open_problems` snapshots
   (`last_touched_at` advances, `json_array_length(observations)` unchanged)
   or watch the new `problem_memory` logger for "touched (LRU rotation..." if
   checking after this session's commits are live.

3. **focus_loop duplicate observation writes + a logging-channel fix riding
   along.** `focus_loop.py` runs its own 60s tick, independent of the
   fountain loop, and appends whatever fountain thought is freshest (its own
   600s lookback) onto its currently-focused problem via a hand-rolled write
   path that bypasses `ProblemMemory.observe()` entirely -- and unlike
   `observe()`, had no dedup guard. A still-fresh thought got re-stamped
   every tick until it went stale: #353 picked up three byte-identical
   949-char entries 9s and 60s apart behind a single fountain fire, which
   promptly tripped its own stuck-similarity check on the duplicates rather
   than genuine stuckness. **This is the exact gap `ProblemMemory.observe()`'s
   own docstring flagged and deliberately left unfixed in session 39** --
   "focus_loop.py's own append path has no such guard... Not fixing
   focus_loop.py here." It came due today, ~2.5 months later, because
   #352/#353 are the first pair tracked by both RECONCILE_WB and focus_loop
   simultaneously. **Worth recording on its own: deferred items do come
   back** -- the precondition that made this one safe to defer (nothing
   reads the same problem from both paths at once) stopped holding the
   moment two problems were open together. Fix mirrors `observe()`'s own
   guard: no-op if the new text is byte-identical to the last entry. Riding
   along same commit: the RECONCILE_WB write-back's per-problem exception
   handler swallowed everything silently (`except Exception: pass`) -- now
   logs problem id + exception via `error_channel.record(..., exc=e)`; and
   `problem_memory.py`'s routine `open()`/`close()`/`touch()` events, which
   were logged via `errors.record(level="INFO")` sharing one 500-slot ring
   buffer with genuine ERROR entries (measured live: ~77% INFO/DEBUG,
   cycled under 90 minutes at normal volume) -- routed onto a proper module
   logger instead, which the error channel's own `CentralHandler` already
   filters to WARNING+ before forwarding, so it lands in the log, not the
   bounded buffer. **Proved by:** 30-day baseline taken *before* fixing --
   274/1598 (17.1%) of all observations across every tracked problem were
   exact duplicates of their immediate predecessor, median gap 60.0s
   (focus_loop's own tick interval) -- #352/#353 were typical, not outliers.
   After, against disposable throwaway DBs (not copies of the production
   files): a stable thought held across 5 simulated ticks produced exactly 1
   observation, not 5; a genuinely new thought still landed as a second,
   real observation. Live post-fix: 0 duplicates across observations
   written since restart. The logging-channel measurement was only partial
   at write time (buffer had refilled just 1170s of its ~93-minute pre-fix
   span when checked) -- confirmed zero `problem_memory`-sourced entries in
   the buffer post-fix, but hadn't yet caught a live `open()`/`close()`
   firing to see it print to the soak log; the routing is correct by
   code-reading (matches every other working `logger.info` call in this
   codebase) and not yet directly observed end-to-end. Commit `78f39f4`.

4. **`nex_keepalive.sh` first-boot false-warning guard.** First `is_alive`
   check ran 15s after launch, shorter than model load takes on a cold
   boot, producing a false "NEX did not come up on first launch" warning.
   Bumped to 25s; the retry loop's own poll interval and the flock handoff
   logic untouched. **Not yet verified live** -- diff only, takes effect on
   next cold boot. Tomorrow's cold start is the real test.

5. **`NEX5_SPEECH_ENABLED=false`**, now committed in `nex_keepalive.sh` and
   persisting across boots (baked into the launch command, not a one-off
   runtime override). Stopgap for the SIGILL below -- see that entry for
   what it does and does not fix. Commit `d411f5f` (same commit as #4).

**COMMIT_CLOSE: characterised, deliberately left undecided.** Two live
instances today (#352 closed 16:50:09 on 241 chars, #353 closed 18:04:44 on
205 chars) prompted the audit. `generator.py`'s `_is_artifact` check
(`0 < len(_tnorm) <= 700`, introduced 2026-06-11, commit `2c78ebc`) has an
upper bound but no lower one, unlike the sibling `>=300` branch two lines
below in the same file -- no comment or commit message anywhere argues for
allowing short closes; reads as an oversight, not a documented decision, but
that's an inference from absence, not a confirmed intent. **This is the
system's normal termination path, not an edge case:** 122/129 closes (94.6%)
in the last 30 days match the COMMIT_CLOSE signature (observe()+close()
within 2s of each other); of those, 107/122 (87.7%) closed under 300 chars,
median 130. **All 106 of the checked sub-300 closes (100%) had already
produced at least one >=300-char observation earlier in their own history**
-- none of the historical cases look genuinely incapable of clearing a
floor; a floor would likely just delay these closes a cycle or two. But the
backstop that would have to make "eventually" true is weaker than the 100%
figure suggests: `decay()` (30-day staleness auto-close) **is never called
anywhere in production** -- only referenced in tests, no cron or loop wires
it up, and `touch()` (fix #2 above) actively works against it anyway by
design, since touch() exists specifically to keep `last_touched_at` fresh.
ABSTAIN_CLOSE only catches specific keyword-matched abstains. There is no
cap on total simultaneously-open problems anywhere, only a 5/day
*creation-rate* cap (`signal_to_problem.py:DAILY_PROBLEM_CAP`). Net: adding
a floor risks trading a permissive close for a monotonically growing open
pool if the close rate measurably slows, and nothing in the code would stop
that growth -- real in mechanism, not evidenced in the last 30 days of
actual behavior. No fix applied. Decision is Jon's, not made this session.

**The 18:33 SIGILL: watched, not chased, root cause unresolved.** Service
crash-looped from 18:33:43, unrelated to any code changed today (the prior
boot, running last session's fix, had been stable for 37 minutes first).
Every crash -- 29 total -- hit the *identical* instruction offset,
`libtorch_cpu.so[0x20c1c06]`, which `nm -D` resolves into the ~8KB unnamed
gap between `at::native::range_out_no_step` and `at::native::arange_out` --
the vectorized kernel cluster backing `torch.arange`, explaining why both
observed triggers (Kokoro TTS and, later, `sentence-transformers` via
`theory_x/diversity/embeddings.py`, first loaded on `focus_loop`'s stuck-
check) hit the same address: both generate position/time indices through
it. **`NEX5_SPEECH_ENABLED=false` was NOT the fix** -- it only removed
Kokoro as a trigger; the identical crash then moved to the
sentence-transformers load, firing 9 more times before the 10th respawn
(19:00:14) got through clean and has been stable since (20+ min at time of
writing). Same binary worked fine twice earlier the same day (14:48:17 and
17:56:25, logged "Kokoro pre-loaded successfully" both times) -- rules out
a hard build/CPU-incompatibility read, since that would fail every time,
not intermittently. Nothing on disk changed: `libtorch_cpu.so` and
`torch-2.11.0.dist-info` both dated 2026-04-24, untouched today; today's
only `apt` activity was unrelated (`libpam`/`rsyslog`/`libxpm4` at 07:41,
hours before and unrelated to either success). CPU is an AMD Ryzen 7 5800X
(Zen 3, homogeneous 8C/16T, no AVX-512) -- rules out the Intel hybrid-core
AVX-512-downclock failure class. No MCE or thermal-fault evidence in
available telemetry (no CPU package temp sensor exposed on this box; GPU/
NVMe both read normal). Leading, unconfirmed read: a transient CPU-
execution fault during a bounded window, not a software regression --
circumstantial, not proven. **If it recurs:** check `sensors` and
`journalctl -k` live, in the moment, not reconstructed after. Any code path
that lazily loads a torch-backed model (Kokoro, `embeddings.py`, and
whatever else touches `sentence-transformers`/torch at first use) is a
plausible trigger until this is actually explained.

**SYNTH_EMIT/PXB confirmed dead in this deployment.** `NEX5_SYNTH_EMIT` and
`NEX5_RECONCILE_PXB` are absent from `nex_keepalive.sh` -- both branches
(~150 combined lines in `generator.py`) contribute 0% of any fire, always
have in this deployment's history. Agreed not to touch this pass; noted as
a real maintenance-cost candidate for later (had to check env vars before
trusting any content-based path classification this session, specifically
because the PXB code reads as live).

**Untracked, unrelated, not committed:** `rc2/` -- a separate node.js
project sitting in this repo directory, untouched this session, flagged
each time `git status` was checked rather than swept in.

`git log` today: `511ab33` (FK trap), `f1f774c` (template collapse),
`78f39f4` (focus_loop dedup + logging), `d411f5f` (nex_keepalive.sh guards).

## 2026-07-25 ~15:52 — session 49: cold-boot verification of yesterday's
## fixes, an IPv6 survey that turned into three separate sense-adapter
## fixes, moltbook panel date-stamped, two dead RSS feeds retired.

**Fountain template collapse (f1f774c): confirmed held across last night's
cold boot, not just eyeballed.** Measured the post-boot window (04:59:24 ->
now, 160 real fires): 0 fires match the old "restless...coming back to X"
template (exact-phrase and unsubstituted-placeholder checks both zero).
Distinct 6-word openers: 126/160 (78.8%), vs the pre-fix baseline of 79
distinct. Sanity-checked against a normal day (2026-07-18, 265 fires):
67.5% distinct with a heavier single-topic pileup (32 fires sharing one
opener) than anything seen today -- today's diversity sits at or above a
normal baseline, not just "better than broken." Fix holds after a full
process restart, not only within the session that shipped it.

**Wedding-rules anchor persistence (30987-30997, 8/9 fires): characterised,
left alone.** `fountain_retrieval_log`'s `own_sense` slot shows belief
222200 in 17 consecutive fire cycles (58.6 min) -- long, but not the
longest of the day (222095, unrelated topic, ran 19 fires/58.3 min); 116
distinct belief_ids cycled through that slot today, median persistence 6
fires. Full-day wedding-mentioning fires: 32/160 (20%) vs 44/265 (16.6%)
for a comparable single-story pileup on 7/18 (EU court ruling). In range.
Not a narrowed retrieval pool -- normal recency-weighted anchor behaviour,
two wedding-themed items landing in the top-4 simultaneously by topic
coincidence, not by mechanism. No fix.

**IPv6 survey, prompted by the gutenberg stall investigation: 8/21 external
adapter hosts resolve IPv6-first from this box; 2 hard-fail (gutenberg.org,
frontiersin.org -- true black holes, zero bytes, connect never completes),
4 pay an unexplained 4-5s TLS-handshake tax but still complete
(sciencedaily, quantamagazine, coingecko, coinbase -- TCP connect is fast,
~0.4s; the slowness is entirely in the TLS handshake). Known-good IPv6
(ipv6.google.com) connects clean and fast; two other unrelated hosts
(cloudflare.com, facebook.com) also show IPv6 throughput stalls. Reads as
degraded/inconsistent IPv6 peering from this box, not one bad destination
and not a total outage -- systemic enough to fix once, centrally, rather
than per-adapter.

**base.py `_default_fetch`: flat 30s timeout replaced with a (10s
connect, 20s read) split, plus a shared descriptive User-Agent.** The
timeout choice is measured, not guessed: `requests.get(url, timeout=(10,
20))` tested directly against both classes of host -- dead routes
(gutenberg, frontiersin) now fail in ~10.5s; all four slow-but-real IPv6
hosts complete in 5.0-5.6s, comfortable margin under the 10s ceiling. A
(5, 25) split was tried first and rejected -- sciencedaily completed at
5.17s, too close to a 5s connect budget to be safe against normal latency
variance. No IPv4 forcing (Jon's call, argued and accepted: forcing
discards a route that's genuinely fine, e.g. Google's IPv6, and hides the
underlying peering problem instead of surfacing it). Exceptions are now
re-raised with the URL and which budget (connect vs read) was exhausted,
instead of a bare "Read timed out" -- the reason this needed fixing at all
is that **four adapters were dead or quiet for four unrelated reasons and
all four presented as an identical, indistinguishable "quiet feed" symptom**:
gutenberg.org (IPv6 black hole), frontiers_neuro (IPv6 black hole, same
class but a different host), wikipedia_featured (403 -- see below, not
IPv6 at all), and mathematics.arxiv (genuinely just quiet -- arXiv math.GM/
HO had zero new submissions that day, confirmed by fetching the adapter's
exact RSS URLs directly and finding well-formed feeds with zero `<item>`
entries; both anomalously-quiet days this month were Saturdays, consistent
with arXiv not announcing over weekends). Verified against the live patched
code (not a standalone timeout test): gutenberg 30s -> 10.5s with a
diagnostic error naming the URL and budget; sciencedaily/quantamagazine
still succeed over IPv6, unforced, un-clipped.

**Shared User-Agent: wikipedia_featured confirmed 403ing on requests' bare
default UA** (`python-requests/2.31.0`), 200 with a descriptive one --
Wikipedia's API policy is a documented, deterministic UA check. **The
ieee_spectrum "also 403s" claim, first written here, was wrong and has
been corrected**: a standalone spot-check (several hosts hit back-to-back
in one script, no pacing) got a 403 from `spectrum.ieee.org` at that
moment -- a real result, not fabricated, but not representative. Checked
against `sense_events` history instead of trusting the one-off test:
`emerging_tech.ieee` has 20 events every 30-minute cycle, gapless, from
05:29:28 this morning straight through both of today's restarts, entirely
on the *old* bare-UA code path before this fix existed. The live scheduled
adapter was never actually broken. Best read: IEEE's block is rate/burst-
triggered, not a per-request deterministic UA check like Wikipedia's --
my rapid multi-host test script tripped something a lone request every
30 minutes doesn't. Net effect on the fix is harmless either way (shared
UA still applies, ieee_spectrum still 200/20 events post-restart, no
regression) -- but the *reason* recorded here was wrong, and it's fixed
now rather than left standing. Lesson: a spot-check result describes the
spot-check, not necessarily live behaviour -- check the actual poll
history before writing either into the journal as fact.

**ap_news, reuters: removed from `build_scheduler()`, not disabled.**
Both hosts (`feeds.apnews.com`, `feeds.reuters.com`) NXDOMAIN against
Google's own public DNS (8.8.8.8), not just this box's resolver -- ruling
out a local/ISP quirk. Parent domains (`apnews.com`, `reuters.com`)
resolve fine; only the `feeds.` subdomains are gone. `last_poll_at: None`
on both -- zero successful polls in the ~3 months since this system was
built (2026-04-23), retrying every 15 min the entire time. Matches the
well-known industry pattern (Reuters killed public RSS years ago, AP did
the same) -- permanent, not transient. Chose removal over `disable()`
specifically because `disable()` wouldn't have reliably achieved the
actual goal (no permanent noise in `/api/sense/status`): `SenseScheduler.
__init__` auto-starts all external adapters immediately at construction
(2026-05-09 behaviour), so a `disable()` call made right after construction
races the adapter's own first poll attempt -- a fast NXDOMAIN failure could
easily populate `last_error` before the disable takes effect, and a
disabled adapter never polls again to clear it. Removal has no such race.
Checked for side effects before removing: no other production code
references the `news.reuters`/`news.ap` streams by name (only generic
vocabulary-hint words "reuters"/"ap" in `attention.py`'s keyword lists,
unrelated); `sense_events` has zero historical rows for either stream ever
(nothing to orphan -- they never once succeeded); one test
(`test_sense.py::test_sense_toggle_external`) exercised the live
`/api/sense/toggle/reuters` endpoint through the real app and broke on
removal -- fixed by swapping to `bbc_news`, since the test asserts generic
toggle behaviour and was never actually testing anything Reuters-specific.
Adapter classes kept on disk (`feeds/reuters.py`, `feeds/ap_news.py`,
each carrying a REMOVED-dated docstring with the DNS evidence) for their
existing unit tests and in case either publication ships a replacement
URL -- **do not re-add to `build_scheduler()` without confirming the
`feeds.` subdomain resolves again.** Verified: 30 adapters actually start
(matches the file), full test suite unaffected -- ran the complete suite
against both this session's changes and unmodified `main` (background,
~6 min each, to avoid the truncation mistake below), diffed the two
39-failure lists: byte-identical, zero new regressions, zero fixed by
accident. `__init__.py`'s stale "31 adapters" docstring (already wrong --
actual was 32 before today) corrected to the current true count, 30.

**philpapers, papers_with_code: also removed from `build_scheduler()`,
same day, second pass.** Left as "note for later" in this entry's first
draft; characterised properly on follow-up and both turned out to be the
same class of problem as ap_news/reuters -- permanent, unfixable from
here, not worth carrying as noise. `philpapers.org`'s 403 is a genuine
Cloudflare "Attention Required" JS-challenge page (the response body
loads `/cdn-cgi/challenge-platform/scripts/jsd/main.js` and requires
executing JavaScript to pass) -- no HTTP header fixes this from a plain
client. This box's outbound IP (`whois`: "Datacamp Limited" / CDN77, a
hosting/CDN ASN) is exactly the address class Cloudflare bot-mitigation
commonly blocks by default. `papers_with_code`'s "Expecting value: line 1
column 1" wasn't a JSON bug -- `paperswithcode.com`'s entire domain,
including the API path, now 302-redirects to `huggingface.co/papers/
trending` (confirmed with `curl -sSL -D -`: 302 -> 200 text/html, 1.5MB,
no JSON). The site is gone, absorbed into Hugging Face. Same treatment as
ap_news/reuters and the same reasoning for *why* removal beats
`disable()`: zero test references to either adapter id (checked first,
cleaner than the reuters/apnews case which needed one test fixture swap),
zero historical `sense_events` rows for `cognition.philpapers` or
`ai_research.pwc` (nothing to orphan -- neither ever succeeded). Verified
in an isolated scheduler build (no live-service impact): 28 adapters,
none of the four removed ids present. Adapter count now 28 (was 30 this
morning, 32 before today). Classes for all four kept on disk with dated,
evidenced docstrings explaining exactly why and what would need to be
true to re-add them.

**Process note for next session: a chained `git stash && <long command>
&& git stash pop` hit this session's 2-minute default Bash timeout mid-run
and left the repo sitting in a stashed state for several minutes before
being caught by `git status`.** No data was lost (stash held fine), but
don't chain stash/restore around anything that might run long -- run the
long command on its own, confirm completion, then pop as a separate call.
**Stronger version of the same lesson, given directly this session: never
run `git stash` at all while the live service is running.** The process
survived the one incident above only because Python had already imported
the affected modules into memory before the files reverted on disk -- a
keepalive respawn during that window would have booted reverted code with
no error to show for it, silently undoing a fix. Use `git diff`/a worktree/
a second checkout to compare against a clean baseline instead, never a
stash, whenever the service is live.

**Moltbook HUD panel date-stamped (display-only).** `/api/moltbook/chats`
was always going to keep replaying the same frozen 30 rows (`moltbook_
posts`, last write 2026-05-30) with a bare HH:MM:SS and no date, which
reads as live activity on every fresh page load. Added `fmtTsStale()` in
`app.js` -- prefixes a date only when a row is >24h old -- applied to the
three `pipe-ts` render sites in `refreshPipeline()`. No backend change, no
dedup/pagination change. Static file, no process restart needed, browser
reload is enough. **The poster/listener/responder loops were cut 2026-05-30**
(external moltbook server 404ing; commented out in `stage2_dynamic/
__init__.py`) -- "0 posts to moltbook" in the morning greeting has been
correct every single day since, roughly 8 weeks, not a new two-morning
event as it first read.

**COMMIT_CLOSE: still characterised, still deliberately undecided.**
Carried forward unchanged from the 07-24 entry above -- no new
investigation this session. Decision remains Jon's.

**touch() (f1f774c, ProblemMemory LRU rotation): still zero live firings.**
Checked after every restart today, all reading the same continuous soak
log (04:59:24 boot through now, no gaps): cold boot + three warm restarts
(base.py/UA fix, an aborted mid-flight one from the stash incident above,
and the final adapter-removal restart), zero matches for "touched (LRU
rotation" in any of them. Same state as when `f1f774c` was committed
yesterday.

`git diff --stat` today (uncommitted, awaiting Jon's review): `gui/static/
app.js`, `tests/test_sense.py`, `theory_x/stage1_sense/__init__.py`,
`theory_x/stage1_sense/base.py`, `theory_x/stage1_sense/feeds/ap_news.py`,
`theory_x/stage1_sense/feeds/reuters.py`.

## 2026-07-25 ~19:00 — session 49 continued: confabulation origin traced to
## fetch_loop (resumption.py ruled out), two standing-caveat notes for the
## record.

**"Resonates with my past experiences trying cheap family trips" --
resumption.py ruled out, true origin found: `theory_x/life/fetch_loop.py`,
12 minutes before the boot it was suspected of following.** Read
`resumption.py`'s actual mechanism first: `_promote_beliefs()` does one
`UPDATE beliefs SET created_at = now-1 WHERE id IN (...)` against up to 5
belief ids carried in the prior snapshot's `recent_belief_ids`. It changes
**only** `created_at` -- no content, no `source`, no framing text of any
kind gets added; the docstring's "just promoted to recent" is accurate,
not the "just thought this" gloss the lead suggested. Whatever framing a
promoted belief gets in the DRIFT prompt still comes from its unchanged
`source` column (`precipitated_from_sense` -> "Things you've been reading
about lately:", correctly external).

Checked the specific boot anyway, exactly as asked. The snapshot consumed
at 16:35:02 was written at 16:33:55 (the outgoing process's SIGTERM
handler), `recent_belief_ids: [222626, 222624, 222620, 222597, 222229]` --
all five `source IN ('synergized','fountain_insight')`, genuinely-own
reflective content, none about the summer-holidays article, none
resembling the family-trips phrasing. Belief 222164 (the real BBC-sourced
belief, "Parents on how they get through the summer holidays on a
budget") was **not** among the five promoted. Ruled out cleanly, not by
absence of evidence -- direct evidence against.

The real origin: belief 222631, tier 7, `source='fetch_loop'`,
`created_at` **16:23:06 -- 12 minutes before the 16:35:00 restart, not
after it.** Full content: *"This article resonates with my past
experiences trying cheap family trips; always looking for ways to
maximize savings without compromising on fun. (read: Parents on how they
get through the summer holidays on a budget)"* -- the confabulation was
already fully formed, word for word, before any boot happened; the
restart is coincidental timing, not cause. `fetch_loop.py` is a separate
loop from DRIFT/fountain entirely -- it fetches a URL body directly and
calls its own one-shot prompt: *"You just read this... Write ONE
sentence -- your actual response to what you just read... a thought you
had while reading, **or what it connects to that you already hold**.
First person, 10-30 words."* That instruction is a more direct invitation
to confabulate than anything in DRIFT -- "connects to what you already
hold," first person, with no constraint distinguishing a genuine prior
holding from an invented one. This is where the "my past experiences"
framing was actually generated, not in the DRIFT prompt characterised
last entry (that characterisation -- the "Things you've been reading
about" label being correct while the generation instructions don't
constrain read-vs-did -- still stands as a separate, real gap in DRIFT
itself; it just isn't what produced this particular belief). The later
fountain fires (16:51 onward) that repeat and reword the phrase are riding
an already-confabulated belief, not originating one -- consistent with
last entry's finding that those fires don't retrieve it as an own_sense
candidate at all; whatever's carrying it forward from fire to fire is
still uncharacterised.

**Open thread for next session, explicit so it isn't lost: the
propagation path from 222631 to the nine repeating/rewording fires is
unidentified, not just unconfirmed.** Nine fires from 16:51 onward repeat
and reword belief 222631's exact phrasing while `fountain_retrieval_log`
shows it as an `own_sense`/`seed`/`spectrum` candidate in **none** of
them. `NEX5_CONTINUITY_N` is off (ruled out) and `last_thought()` is
GUI-status-only, never fed to a prompt (ruled out). Confabulation itself
is explained (fetch_loop, above) -- this is a different question: how is
the phrasing crossing from fire to fire with no candidate trail in the
one log that's supposed to capture what each fire drew on. That's the
next thing worth checking, not a re-ask of the confabulation.

**Standing caveat for CARRY_OVER: bonsai `focus_num` resets to 0.0 on
every process boot, no persistence, confirmed in `bonsai.py`'s
`init_tree()`.** Five restarts today meant every branch reading taken
today was measuring recovery-in-progress, not steady state -- see the
ai_research/cognition_science entry above, now confirmed as restart-reset
plus differential recovery speed, not the adapter removals. This isn't
just a today artifact: **with nightly shutdowns, this happens every
morning.** Rule of thumb from today's observed recovery: high-cadence
branches (streams firing every seconds-to-minutes -- emerging_tech,
computing, markets, crypto) recover within roughly an hour; slow-poll
branches (ai_research, cognition_science -- real sources on 30-60+ minute
cycles) can take on the order of **~2 hours** to climb back to a normal
working range. A future session reading a low ai_research/cognition_science
number shortly after a morning boot should check time-since-boot before
reading it as drift or a fault.

**Third HUD/reality mismatch this session, same class as the moltbook
panel: `ProblemMemory.list_open()` queries `state = 'open'` only, while
RECONCILE's pairing query and `focus_loop`'s dedup logic both operate on
`state IN ('open','stuck')`.** `stuck` is a legitimate pre-existing state
(session 48's focus_loop dedup fix) meaning duplicate/repeated content was
detected on that problem -- not resolved, not abandoned, still being
touched (problem #359 today: `stuck`, still getting reconciled, invisible
to the panel that reported "none"). The pattern worth naming, not just
this one instance: the moltbook panel showing frozen 2026-05-30 data as
if live, and this open-problems panel showing "none" while an active
problem is still being worked, are the same shape of bug -- a GUI read
that's technically querying real data but with a filter or freshness
assumption that doesn't match what the engine actually considers "active."
Both cost session time to notice were misleading rather than accurate.
Worth a pass at some point auditing every GUI panel's query against the
actual state/date semantics the backing loops use, rather than finding
these one at a time when they happen to matter. Not fixed -- characterised
only, per instruction.

## 2026-07-25 ~23:10 — session 49 continued: SYNTH_EMIT/PXB removed
## (commit `bfc89b8`); `_maybe_substrate_voice()` fully characterised --
## the most consequential finding of the night, and it corrects the
## harmonic HUD's reading of its own state.

**Timeline, from `git log`/`blame`, not narrative:**
- `f1469b49` (2026-05-21): Intervention C try-block written.
- `1151e439` (2026-06-03): `_maybe_substrate_voice()` itself added.
- **~830 fires, 2026-05-21 through 2026-05-31** (regular, ~90-120/day)
  -- this was substrate_voice actually live and walking the keystone
  library (see the May-23 chord-walk entries above and in DIRECTION.md).
- `a46b935` (2026-06-04): the RECONCILE primitive lands, and **explicitly,
  deliberately gates substrate_voice off** -- commit message: *"Required
  gating `_maybe_substrate_voice` off under reconcile."* `NEX5_RECONCILE=1`
  is default OFF at this point; the gate exists but only suppresses
  substrate_voice during occasional manual RECONCILE test runs. Daily
  fire count already tapering hard as those test runs increase: 40 (06-02)
  -> 25 -> 7 -> 2 -> 9 (06-06).
- **Zero fires, 2026-06-07 through 2026-07-12** -- five straight weeks
  of silence.
- `93153a0` (2026-06-16): `NEX5_RECONCILE=1` becomes the **permanent**
  default in `nex_keepalive.sh`. Diffed the actual commit: the message
  narrates RUT_EDGE, an arc boot-crash fix, and binding hum into
  self-state -- **it never mentions RECONCILE or substrate_voice at
  all.** `NEX5_RECONCILE=1` rode in bundled with ~9 other flags being
  consolidated into the permanent launch line, in a commit about
  something else entirely.
- **A single-day burst of 308 fires, 2026-07-13** -- cross-checked
  against this file's own earlier record (session 27/28, above):
  *"Machine rebooted 2026-07-13 18:27, unnoticed until session 27"* and
  *"the 2026-07-13 85.6% spike is genuine live data... a real, if
  extreme, data point from the day of the crash."* Genuine, not a batch
  job -- but the crash-recovery day, not normal operation. Whatever
  launched `run.py` during that recovery evidently didn't carry the
  standard `NEX5_RECONCILE=1` flag string for a window.
- **Zero fires since 2026-07-13** -- 12 more days of silence through
  tonight, confirming normal keepalive operation has kept it dead since.

**The gate was designed. Its permanence was not.** `a46b935` is an
explicit, argued decision. `93153a0` is a side effect of an unrelated
commit -- nobody decided "retire Intervention C," and **no commit
anywhere argues RECONCILE and substrate_voice can't coexist; nobody has
revisited whether they could.** Same unresolved shape as census #9's
persona gate: documented behaviour, no rationale behind the specific
form it's taken, never revisited.

**The harmonic HUD is measuring a dead path and has been since roughly
mid-June, which is the actual point of this entry.** Read
`substrate_harmonic.py` directly: `fountain_sv_share` counts
`hot_branch='substrate_voice'` in the last 30 fires -- mechanically
pinned at 0.0 since there are none. `groove_vs_sv_active` computes
`1.0 - abs(groove_active - sv_active)`; `sv_active` is `1.0` only if a
substrate_voice fire landed in the last 900s, so with zero since 07-13
it's permanently `0.0`, and the whole pair collapses to `1.0 -
groove_active` -- tracking groove state ALONE while presenting on the
HUD as a two-variable correlation.

**Attempted correction of a specific prior claim, honestly incomplete:**
the working session that produced this entry believed there was an
existing record stating `groove_vs_sv_active` reads "pinned at 1.0 the
whole window" for the reason "binary threshold, severity never crossed
0.8" -- with a conclusion that harmonic movement instead comes from
`drive_tension_vs_sv` and `gate_reject_vs_baseline`. **Searched
exhaustively for that specific claim to correct it in place -- `git log
-S` on every harmonic pair name across all history, every `.md` file in
the repo, `reports/`, `snapshots/`, non-markdown files -- and could not
locate it.** The only existing document where `groove_vs_sv_active`
being pinned/flat is discussed at all is `SNAPSHOT_FINDINGS.md`
(2026-05-28, "harmonic pairs (7) -- flat or saturated... pinned at
1.000+/-0.000... saturated, no variance"), and that one is NOT a
misreading to fix: 2026-05-28 sits inside the ~830-fire live window
above, well before `a46b935` even existed, so "pinned because sv_active
is always zero" is factually wrong applied there -- whatever caused
that day's saturation was real correlation during an active walk, a
different mechanism entirely. Did not touch that document. If the
"binary threshold, severity never crossed 0.8" claim lives somewhere
else, it hasn't been found yet -- flagging the gap rather than guessing
at a location and editing the wrong thing.

**Fourth instance of tonight's pattern, worth naming explicitly:**
documented behaviour with nothing behind it, or instrumentation reading
something that no longer exists. Census #9 (persona gate), the moltbook
panel (frozen data read as live), `list_open()` vs `IN ('open','stuck')`
(panel says "none" while an active problem is being worked), and now
two harmonic HUD pairs quietly measuring a path that's been dead for
five-plus weeks. Four independent instances in one session is enough to
call it a class of problem, not four unlucky coincidences: this
deployment accumulates permanent, undocumented state changes as side
effects of commits whose stated purpose was something else, and nothing
currently checks HUD instrumentation against whether its underlying
signal still exists. Not fixed -- characterised, per instruction.

Removal itself: `theory_x/stage6_fountain/generator.py`, commit
`bfc89b8`. Full verification (test diff against baseline, restart,
RECONCILE/DRIFT confirmed firing) in the commit message.

## 2026-07-26 ~00:50 — session 49 continued: two fixes, one diagnosis,
## pre-registered predictions before an overnight restart.

**PRE-REGISTERED, before touching anything, so tomorrow's session can't
misread flat numbers as something stalling:**

Current state at time of writing: T5=0, T6=158, T7=40,737 (12 locked).
Decay-tick demotion history reconstructed from `promotion_log` (in-memory
`error_channel` only holds this restart's ticks, so this is from the
persistent per-belief log instead): 16,040 decay events total since
2026-04-23, most recent ticks (excluding two catch-up-after-gap outliers
of 53/58): 27,6,9,14,10,8,9,9,11,3,12,16,5,11,6,7 -- mean ~10-13/tick,
median 9. Right now, at this exact minute, zero T5/T6 beliefs match
either the old or new decay condition (a tick just ran at 00:39:31 and
cleared what was eligible) -- that's a snapshot artifact, not evidence
either way.

**Prediction:** after the decay fix below, demotion-tick counts should
drop to **near-zero for approximately the next 48 hours** (`DECAY_IDLE_
HOURS`), because nothing currently in the system is genuinely 48h-idle
without having been referenced first -- the NULL-bypass bug has been
sweeping everything through within an hour of creation for three months,
so there's no backlog of "referenced once, then sat idle 48h" material
for the fixed query to find yet. T6 (158) and T7 (40,737) should hold
roughly flat for about two days. **If tomorrow's numbers are flat, that
confirms the fix -- it is not the decay loop stalling or breaking.**
Only after ~48h should tick counts resume, at a new steady-state rate
that reflects genuine 48h-idle material for the first time -- likely
much lower than the historical 9-13/tick average, since that average was
inflated by catching everything young.

**FIX 1 — `decay_pass()` NULL clause**, `theory_x/stage3_world_model/
promotion.py`. Was `(last_referenced_at IS NULL OR last_referenced_at <
cutoff)` -- bypassed the 48h intent for anything never referenced (the
default state; ~74.5% of T7 was NULL at time of fix). Now `COALESCE(last_
referenced_at, created_at) < cutoff` -- a never-referenced belief ages
from its own creation instead of being treated as infinitely idle.
Checked whether this breaks on `resumption.py`'s `_promote_beliefs()`
(rewrites `created_at` to now-1s for up to 5 beliefs per boot): it's a
real, bounded caveat, not a blocker -- no other stable birth timestamp
exists anywhere in the schema, the affected population is at most 5
beliefs/boot out of ~40,000 T7 beliefs, and the effect is only a delay
(their decay window resets from the promotion moment, not truly broken,
and arguably aligned with resumption's own intent of keeping them
front-of-mind a while longer). Documented inline at the fix site. Verified
against live data before committing: old-logic eligible count 40,256,
new-logic eligible count 39,963 (T7-ceiling reselections dominate both --
see prediction above for the number that actually matters).

**FIX 2 — `fetch_loop.py` prompt.** Traced belief 222631 (last night's
confabulation) to its exact origin: `_compose_response()`'s one-shot
prompt asked for "a thought you had while reading, or what it connects to
that you already hold" with nothing distinguishing a genuine held belief
from an invented experience. Added an explicit constraint: connecting to
an opinion/pattern is still the point and still asked for; inventing a
personal experience or memory is now explicitly forbidden. First person
kept, "connects to what you hold" intent kept -- narrowed to beliefs, not
memories. No test coverage on this file's prompt text.

**DIAGNOSIS — `decisive_contradiction()`, no fix.** The "2 firings across
44,289 beliefs" framing undercounts the real activity. Full picture from
`harmonizer_events`: 68 pairs marked `paradox` over the system's history
(conflict detection runs live, every 2h, confirmed wired in `_harmonizer_
loop`) -- not dead, just narrow (`_conflict_score` only catches two
patterns: >=2 shared tokens with one side negated, or one of exactly 4
hardcoded polar-vocabulary pairs -- significance/insignificance, knowing/
unknowing, clarity/obscurity, constancy/flux). Of those 68, 39 escalated
to `both_deleted` (no synthesis bridge found -- both retired directly, no
`decisive_contradiction()` call, no promotion_log trace) and only 2 to
`synthesized` (requires a THIRD belief, tier<=5, sharing >=2 tokens with
EACH side -- only this sub-path calls `decisive_contradiction()`). So
**41 pairs (82 beliefs) have actually been retired via contradiction over
this system's life, not 2** -- but the specific promoter method the count
was taken from only fires on the narrower of two escalation outcomes.
The two synthesized events: (303,305)->keystone 167, 2026-05-10; (22418,
108)->keystone 107, 2026-05-16 -- both within the first month, nothing
since despite `both_deleted` continuing to fire in the meantime (most
recent `both_deleted` events are far more recent than May). Read: the
synthesis-bridge sub-condition specifically got harder to satisfy as the
corpus grew (LIMIT 50 tier<=5 candidates, needs 2-token overlap with
both sides) -- not "nothing asks the question," but "one of two narrow
gates went quiet while its sibling kept working." Two different fixes
would be needed depending which gate you want to loosen -- not done this
pass, per instruction.

**DO NOT TOUCH, noted for a proper session:** `quality_synthesis.py`
reading `genius_tags` per branch and writing `data/quality_signal.json`,
which `attention.py` uses to amplify (1.20x) or dampen (0.82x) an entire
branch's incoming attention. Confirmed live behaviour-shaping, not just a
readiness-modulation footnote. Right call to stop trusting it (F4 can't
tell invented self-experience from real), wrong call to touch it at
midnight with no time to watch the consequence. Left alone.

**RESTART — retrieval_log free test result: held, on a small sample.**
Restarted at 00:52:51 to deploy both fixes (commits `4528074`,
`7c2dd52`). Pre-registered before restarting: if coverage holds at 100%
this is real, if it drops back to 0% the 22:39 restart's fix was
restart-lottery coincidence, not the removal. Result: **1 real fire in
the ~5 minutes since restart, and it's covered** (fire 31231, 00:55:40).
That's a sample of one -- consistent with the fix holding, not proof of
it. Machine shuts down overnight; next session should re-check coverage
over the fuller overnight window before treating this as confirmed. If
it's still 100% covered on a real sample tomorrow, that's good evidence
the SYNTH_EMIT/PXB removal genuinely fixed something (mechanism still
unexplained); if it's dropped again, both restarts landing on opposite
states says something about process state itself, not this specific
code change.

No decay_pass tick has fired yet since this restart (loop runs hourly;
~5 minutes elapsed) -- nothing to verify from live data tonight. The
pre-registered prediction above stands for tomorrow's session to check
against actual post-fix tick behaviour.

Two fixes committed separately (`4528074` decay, `7c2dd52` fetch_loop),
per instruction. `decisive_contradiction()` diagnosis and the genius/
branch-attention do-not-touch note both landed in the entry above this
one, same session, no code changes for either.

## 2026-07-26 ~10:30 — session 49 continued: overnight verification,
## genius-consumer census, surprise characterised, drive_resonance
## decided, six-item cleanup backlog cleared, Doubt Engine arithmetic
## checked.

**Overnight run confirmed: no restart between 00:52:51 and this entry.**
First multi-hour window this weekend without a bonsai reset or a
bounded sample -- retrieval_log's 100% coverage held on 88 real fires
overnight (settles the SYNTH_EMIT/PXB removal as a real fix, not
restart-lottery); decay_pass demonstrated zero demotions against a
correctly-empty live query and a confirmed-alive sibling loop
(`corroborate()` fired three times in the same window the ring buffer
covers) -- working as predicted, not stalled.

**Genius-tags consumer census, done before touching anything else, per
instruction.** Six live behavioural consumers, not the two previously
named:
1. `readiness.py` `_genius_modulation()` -- readiness penalty, 1h window.
2. `quality_synthesis.py` -> `quality_signal.json` -> `attention.py`'s
   1.20x/0.82x branch amplification (already flagged, do-not-touch).
3. `generator.py`'s own "GOVERNOR brick 1" inside `_retrieve_context_
   beliefs` -- accelerates reanimation cadence 20->5 and writes a
   RUT-MIRROR self-observation belief when striking-rate <=5% (90min
   window, throttled 2h).
4. `self_narrative.py`'s `_maybe_notice_rut()` -- a SEPARATE, parallel
   implementation of the same rut-mirror concept (same <=5%/90min
   trigger, same 2h throttle), writing to `narrative_log` instead of
   directly to `beliefs`. Two independent rut-mirrors exist; not
   examined further this pass, flagging the duplication.
5. `voice_engine.py`'s `_score_candidate` -- genius_score is a direct
   weighted axis (`_GENIUS_W`) in candidate selection scoring
   (GENIUS_SCORE_v2 §7 consumer A). Not a rate/throttle input -- directly
   shapes which belief gets chosen.
6. `affect_state.py` -- genius striking-rate (90min window) blends
   directly into mood/valence via `_GENIUS_VALENCE_WEIGHT`.
Confirmed clean of genius entirely: `theory_x/stage_emphasis/` (zero
references anywhere), `groove_breaker.py`, `counterfactual_node.py` --
none of tonight's items 1-3 touch a genius-derived signal.

**Surprise -- three separate mechanisms share the name; characterised
the one that matters.** `emphasis_engine.py`'s `_surprise`/
`PredictionTracker.expectation_error()` is NOT the fire-31425 mechanism
-- it's a crude capitalised-entity-overlap novelty proxy, self-described
in its own docstring as exactly that. The real one is
`predictive_substrate.py` + `surprise_loop.py`: every 5 min, predicts a
weighted centroid (beliefs 0.6 + problems 0.3 + drive 0.1 for
`internal_belief`; recent sense/chat for `external_input`), verifies
next tick via `1.0 - cosine_similarity` against whatever actually
appeared. Range [0, ~1], `surprise_flag` >0.5, `big_surprise` >0.8.
**Blunt finding: as observed, this is mostly measuring window-emptiness,
not prediction failure.** Of 36,980 historical events, ALL 5,396
`big_surprise` events are the "nothing appeared in the window" auto-1.0
fallback -- zero genuine content comparisons ever exceeded 0.8, and only
172/31,584 (0.5%) genuine comparisons crossed even the 0.5 threshold.
`internal_belief` predictions hit the empty-window case 29.2% of the
time. The mechanism is grounded in principle; the signal as thresholded
today is an availability artifact more than a content-mismatch one.
`emphasis_log` (the OTHER surprise's sink) reconfirmed a pure sink --
zero reads anywhere outside its own CREATE/INSERT in `generator.py`.
For the real mechanism: `surprise_events` is read by `context_capture.py`
into `coincidence_context` (Coincidence Lab HUD panel, human review, not
a live consumer). `surprise_loop.py`'s own docstring claims a
big-surprise -> `current_focus` pivot signal to `focus_loop` -- **checked;
that code does not exist anywhere in the file.** Another instance of
documented-but-not-implemented, found incidentally answering "who
consumes it." **Re-examining "the belief that generated the failed
prediction" is not directly supported by the data as framed**:
predictions are a blended centroid of up to 10 recent beliefs + problems
+ drive, and neither `predicted_content` nor `actual_content` in
`surprise_events` stores a belief id -- free text only. Building this
would need belief-id tracking added to the mechanism first; nothing
links it today.

**`drive_resonance`: decided drop, not executed.** Checked whether the
other three `EmphasisEngine` signals have also been ground-truth tested
-- they haven't; `drive_resonance` is uniquely the one falsified
component (p=0.190, effect -0.013, same null shape as the other seven
failed importance-signal candidates), the other three are untested, not
validated. Decision: drop `drive_resonance`, reweight
`goal_relevance`/`self_relevance`/`surprise` to three. Not executed this
pass (characterise-then-decide, not cleanup, per this session's own
framing) -- a two-line change in `emphasis_engine.py`'s `EmphasisEngine.
score()` combiner whenever picked up. Logged now so it doesn't sit
unexamined another month.

**Cleanup backlog cleared -- six items, three commits' worth of
surgery.** `theory_x/stage6_fountain/generator.py`'s five `if False and
X` blocks (own_thoughts, self-observations, arc_block, and both halves
of `_format_arc_context`'s active/recent arc injection) removed, each
with a dated recovery comment pointing at commit `edbddff`. One finding
along the way: with both `_format_arc_context` blocks gone, that
function now provably always returns `""` regardless of input --
arc-context prompt injection was already a complete no-op at the call
site too (`if arc_block:` never fires), not restructured further this
pass, only the two named `if False` blocks touched.
`theory_x/stage_counterfactual/counterfactual_node.py`'s `_maybe_
promote()` unreachable body (dead since the 2026-05-16 `return`) removed
-- confirmed two dependent tests (`test_move_fires_when_threshold_
reached`, `test_tags_copied_to_review_queue`) were already failing
against this disabled state before tonight, unrelated to the edit.
`GrooveBreaker` (`ENABLED=False` since 2026-05-02, catalogue d9ce4b7) --
wiring removed from all three live call sites (`run.py`, `stage6_
fountain/__init__.py`, `generator.py`); the file itself untouched, still
fully functional, dated note added explaining current state and
re-enable path. Verified before removing: no shared helper used
elsewhere for any of the six (checked `own_thoughts`, `arc_block` --
which IS used elsewhere and was correctly left alone --, `_sub_rows`,
`_accept_count_for`, and every `GrooveBreaker` call site individually).
Full test suite run and diffed against the established clean-main
baseline (not just counts) before restarting.

**Doubt Engine arithmetic version -- checked, verdict below, not
built.**
- Confidence is NOT circular relative to corroboration_count: grepped
  the entire codebase for any `UPDATE beliefs SET confidence` -- zero
  exist anywhere. Confidence is assigned exactly once, at insert time
  (hardcoded in seed scripts like `keystone.py` for T1/T2), and never
  recomputed from anything afterward. Not circular -- but also nearly
  constant: 225/311 T1 beliefs sit at confidence=1.0, all 40/40 T2
  beliefs sit at exactly 0.9. Little real variance to divide by even if
  the denominator worked.
- corroboration_count is 0 across all 351 T1+T2 keystones, no
  exceptions -- **the ratio is unusable as literally proposed.** Not
  just empirically zero: structurally inapplicable. `corroborate()`
  explicitly refuses on `locked and tier<=1` ("Tier 1 locked --
  untouchable"), and its promotion branch requires `tier > 2` -- Tier
  2->1 has no entry in `_CORROBORATION_THRESHOLDS` at all ("re-seed
  ceremony only" per its own comment). The counter-increment path
  (`else` branch) isn't hard-blocked for T2, so if `corroborate()` were
  ever called with a T2 belief id the count would tick up regardless --
  it never has been, meaning the callers (`pipeline_hooks.py`,
  `world_consolidation.py`) simply never target T1/T2 in the first
  place. Confirmed empirically, not just by internal guard.
- Keystones confirmed genuinely never re-examined, three independent,
  overlapping guards: `decay_pass()`'s `locked = 0` filter (278/311 T1 +
  40/40 T2 are locked=1) plus its own `tier BETWEEN 5 AND 7` range
  (excludes tier 1/2 outright regardless of lock); `harmonizer.scan_for_
  conflicts()`'s explicit `tier BETWEEN 3 AND 7`, documented as
  deliberate ("Excludes Tier 1-2 keystones/bedrock (immutable per SPEC
  §2)"), plus its own separate "locked beliefs excluded regardless of
  tier"; `survive_challenge()`'s explicit `tier <= 1` refusal. One minor
  nuance for completeness: 33/311 T1 beliefs have `locked=0` (not the
  usual 278), so the *lock*-based guards don't cover them specifically
  -- but the *tier*-range guards in both `decay_pass` and `harmonizer`
  exclude tier=1 outright regardless of lock status, so they're still
  protected, just via a different one of the three overlapping guards.
  No gap in practice.
- **Verdict for Jon to decide on: the ratio as proposed doesn't work
  (denominator is uniformly and structurally zero), but the underlying
  premise -- keystones are set once and never re-examined by any
  existing mechanism -- is now confirmed, not assumed. A workable
  arithmetic version would need a different denominator than
  corroboration_count (which fundamentally doesn't apply to T1/T2) --
  possibly something like time-since-creation with zero references, or
  a dedicated "times this keystone was actually retrieved into a live
  prompt" counter, neither of which exist today either.**

## 2026-07-26 ~10:53 — session 49 continued: genius loop characterised,
## second rut-mirror characterised, named pattern entry for eight
## documented-but-dead instances.

**The genius loop: real for one of six consumers, not visibly tight
where checked.** Traced `voice_engine.py`'s `_score_candidate` input
precisely: it reads each specific CANDIDATE belief's own genius_score
via `fountain_crystallizations` (belief_id -> fountain_event_id ->
genius_tags.score), not an aggregate rate -- a real per-candidate bias.
But `VoiceEngine` is the chat-reply substitution path ("Replaces the LLM
in the chat reply path when in use_substrate mode" -- and `use_substrate`
is the live default, not an edge case), not the fountain/DRIFT loop:
`query_reply()` only returns a dict, writes nothing back to `beliefs`,
and its selected reply doesn't re-enter `predictive_substrate`'s
`external_input` embedding either (that only reads `role='user'`
messages). **This is a leak into what gets said to a human, not a loop
that produces more fountain content** -- high-genius (and therefore
possibly-confabulated) past beliefs get preferentially surfaced in
chat, but nothing new gets written from this path. `affect_state.py`'s
mood-blending is a similar dead end in the other direction: grepped
generator.py and every fountain-adjacent file for `affect_state`/
`mood_label` -- zero references. Mood is a display/self-model value,
consumed nowhere that reaches DRIFT content. `readiness.py` affects
firing frequency/timing, not content shape -- weak, indirect at best.
`generator.py`'s reanimation governor and `self_narrative.py`'s
rut-mirror are explicitly CORRECTIVE (trigger on LOW striking-rate,
inject dormant/foreign material) -- the opposite direction from
reinforcement, not part of this loop at all.

**The one real, closed loop: `quality_synthesis.py` -> `attention.py`.**
Per-branch mean genius score -> branch attention multiplier (1.20x/
0.82x) -> branch focus_num accumulation -> which branch fires more ->
more content in that branch's register -> genius-scored again. This is
the only one of the six that is architecturally a closed loop entirely
within the autonomous fountain system.

**Checked whether it's visibly running -- it is not, at the resolution
checked.** Hourly striking-rate vs hourly share of long/structural/
first-person ("high-F1-form") content over the last 48h: Pearson
r=0.017, no correlation. Notably, 2026-07-25 18:00-21:00 (the heaviest
family-trips confabulation window) shows high-F1-form share spiking to
33-39% while striking-rate stays flat-to-unremarkable (23.5%, 22.2%,
41.2%, 16.7% -- its LOWEST point in that stretch is inside the spike,
not outside it). **Checked the loop's actual mechanism directly, not
just the proxy:** `emerging_tech` -- the branch carrying most of the
confabulation -- currently has verdict LOW (mean=0.11-0.12, n=30-32,
100% of its recent fires in the low bucket, confirmed live via
`quality_synthesis` log lines every 30 min) and is being DAMPENED
(0.82x), not amplified. Read: `emerging_tech` is a high-volume, mostly-
ordinary branch (HN-style short items dominate); a subset of
confabulated high-scorers isn't enough to move a large, diverse
population's mean. **The loop exists architecturally but is currently
diluted past visibility by branch volume -- not tight, not currently
self-reinforcing in any way the data shows.** Not fixed, per
instruction -- characterised only.

**Second rut-mirror: one is permanently gated off, the other is live
but quiet, not disagreeing.** `generator.py`'s version fired exactly
ONCE ever (belief 53030, 2026-05-31) and never again -- because
`NEX5_GOVERNOR_OFF=1` IS set in `nex_keepalive.sh`, and that flag guards
the entire "§9 GOVERNOR brick 1" the rut-mirror is bundled inside
(reanimation-cadence acceleration + the rut-mirror write share one
`if` gate). The one 05-31 firing predates that flag taking effect;
every tick since has been a no-op. `self_narrative.py`'s
`_maybe_notice_rut()` has no such flag set (`NEX5_RUT_MIRROR_OFF` is
absent from `nex_keepalive.sh`) and fired 15 times, 2026-06-01 through
2026-06-18 -- then nothing for 5+ weeks, not disabled, its trigger
condition (or something upstream of it) simply hasn't recurred since
(unexplained, not investigated further this pass). Zero overlap ever
observed between the two -- generator.py's single firing predates
self_narrative's first by a day, no shared window exists to check
simultaneity directly. Compared parameters instead: window (5400s/90min),
rate ceiling (0.05), minimum sample (n>=4), and throttle (7200s/2h) are
IDENTICAL across both implementations, querying the same `genius_tags`
table the same way -- if both were live at once they would almost
certainly fire in the same tick on the same data, not disagree. The
risk was never disagreement; it's redundant duplicate writes to two
different tables (`beliefs` vs `narrative_log`) for what's
architecturally one event. **Read: self_narrative.py's is the intended,
maintained implementation** (dedicated toggle, purpose-built method);
generator.py's is collateral damage from a broader governor flag being
switched off for unrelated reasons, not a deliberate decision about the
rut-mirror specifically -- same shape as this weekend's other
accidental-permanence findings. Characterised only, nothing touched.

**NAMED PATTERN: documented behaviour with nothing behind it -- eight
instances this weekend, worth a standing entry rather than scattering
across session notes.**

The class of problem: a docstring, comment, or prose description
asserts that the code performs some action or connects to some other
part of the system -- and it doesn't, either because it never was
implemented past the description, or because it was disabled as a side
effect of an unrelated change and the description was never updated to
say so. Both shapes are dangerous the same way: reading the comment
gives a false model of what the system does, and that false model
costs real time to correct once something depends on believing it (this
weekend's concrete case: PXB's code *looked* live, so its env var had to
be traced and confirmed dead before any path-classification could be
trusted).

The eight instances, in the order surfaced:
1. `NEX5_SYNTH_EMIT` -- ~74 lines of live-looking code, flag never set
   in any launch path. Removed (`bfc89b8`).
2. `NEX5_RECONCILE_PXB` -- ~104 lines, same shape. Removed (`bfc89b8`).
3. `_maybe_substrate_voice()` / Intervention C -- gated off as a side
   effect of `NEX5_RECONCILE=1` going permanent in a commit whose
   message narrates unrelated work (RUT_EDGE, an arc boot-crash fix) and
   never mentions RECONCILE or substrate_voice. Characterised, left
   alone (harmonic HUD pairs still read it as live -- also flagged).
4. The persona gate (census #9) -- the original named instance of this
   whole class, from before this weekend; cited here as the precedent,
   already fixed in a prior session.
5. Moltbook HUD panel -- replays frozen 2026-05-30 data with no date,
   reads as live. Fixed (`dc5fb08`).
6. `list_open()` vs `IN ('open','stuck')` -- open-problems panel reports
   "none" while an actively-touched problem exists. Characterised, not
   fixed.
7. `surprise_loop.py`'s docstring claims a `big_surprise` ->
   `current_focus` pivot signal to `focus_loop`. Checked: no such write
   exists anywhere in the file. Not fixed.
8. `_format_arc_context()` -- with both internal `if False` blocks
   (removed this session, `7e71935`) gone, the function is now provably
   always `""` for any input; the "live" call site (`if arc_block:`)
   never actually fired even before removal. Arc-context injection was
   dead at the call site the whole time these blocks existed, not just
   inside them.

What would catch these systematically, not proposed as a build, just
named: nothing in this codebase currently checks a docstring's claimed
side effect against whether that side effect's code path actually
exists and is reachable -- that's not something a type checker or the
existing test suite verifies by construction, since prose claims aren't
executable. Two different levels of catch, at two different costs: (a)
cheap, mechanical -- grep every module for env-var-gated blocks and cross-
reference each flag's current value against every launch path, on some
cadence, flagging any block whose flag has been unset/set for >N weeks
without the surrounding comment being touched (would have caught #1,
#2, #3's permanence, #7 partially); (b) expensive, not mechanical --
actually reading a docstring's claims and grepping for the specific
call/table-write it describes, which is what caught #3's HUD
consequence and #7 and #8 this weekend, and doesn't generalise into a
script. The cheaper check is worth having; the expensive one is what
this weekend's sessions were doing by hand and can't be fully automated
away.

## 2026-07-26 ~11:41 — four sequenced decisions: drop drive_resonance, doubt-engine denominator characterised, genius scorer characterised (not edited), family-trips mortality test executed

Four items, executed in the risk order given: (1) and (4) cheap and done,
(2) a characterisation not a build, (3) characterised and proposed but
explicitly NOT edited this pass.

**1. `drive_resonance` dropped from EmphasisEngine.score()'s combiner
(`d52ec78`).** It was the one signal of the four actually ground-truth
tested (p=0.190, effect -0.013 -- same null shape as the seven failed
sessions-40-44 candidates). `combined`/`dominant_signal` now come from
the other three (goal_relevance, self_relevance, surprise) equal-
weighted; drive_resonance is still computed and present in the logged
`signals` dict so `emphasis_log`'s INSERT (which reads it by literal
key) needed no changes. `emphasis_log` is a confirmed pure sink (zero
reads anywhere), so this has no live behavioural consequence beyond the
logged number. Verified via three full suite runs -- two showed a
single "extra" failure each but a *different* one each time
(test_predictive_substrate, then the already-known-flaky
test_fountain_crystallizer), neither related to this module; third run
matched the 39-item baseline exactly.

**2. Doubt-engine denominator ("how often a belief actually gets drawn
on") -- characterised, not built.** Checked what already exists before
proposing anything new:
- `use_count` (erosion.py `record_use()`): the only writer, incremented
  from two paths -- `BeliefRetriever.retrieve()` (general-purpose,
  multi-consumer: router, novel_association, tools, gui, world_model
  init) and fountain's own `_retrieve_context_beliefs()`. For the 351
  T1/T2 keystones: T1 92.6% nonzero (avg 178), T2 97.5% nonzero (avg
  15.6). Broadly populated, but conflates two different retrieval
  mechanisms into one counter and isn't fountain-prompt-specific.
- `last_referenced_at`: **100% NULL across all 351 keystones, zero
  exceptions.** Sole writer is `promotion.py` corroborate()'s
  promotion-success UPDATE, which structurally never fires for
  tier<=2. Unusable for keystones, full stop.
- `fountain_retrieval_log`: the most precise signal -- records actual
  slot-level inclusion in a live prompt (own_sense/seed/spectrum/
  disturbance_a/disturbance_b). 65 of 351 keystones (18.5%) have
  appeared at least once via seed (40) or spectrum (25) slots. But this
  table only had 100% coverage from the 00:52:51 restart onward (fixed
  as an apparent side effect of the SYNTH_EMIT/PXB dead-code removal at
  22:39 the prior day) -- so at characterisation time this was a real
  but very young (~10h) signal.
Conclusion: no new counter needed yet. `use_count` is a usable interim
proxy today, imprecise but real. `fountain_retrieval_log` is the right
long-run answer to "how often actually drawn into a prompt" and needs
nothing built -- it already does exactly what's being asked, it just
needs more calendar time to accumulate before it's trustworthy as a
denominator. Revisit in a few days once it has multi-day coverage.

**3. Genius scorer (`theory_x/genius/score_v2.py` +
`genius_score_weights.json`) -- characterised and a fix proposed, NOT
edited this pass, per explicit instruction.**

Five features, live weights:
```
length_structure   (F1)  w=+2.545
anti_template       (F2)  w=-1.577
t6_promotion        (F3)  w= 0.000   <- dead, contributes nothing regardless of value
self_witnessing     (F4)  w=+1.157
unprompted          (F5)  w=+4.715   <- by far the largest weight
bias = -2.3196, threshold = 0.5
```

Reimplemented the live scoring pipeline against 683 real fires from the
last 48h (matched 683/683 stored genius_tags rows, 93.4% within 0.01 of
the stored score -- confirms the reimplementation is faithful). n=175
STRIKING (25.6%), 508 ordinary.

Per-feature discrimination (mean value STRIKING vs ordinary, and each
feature's swing in contribution to z = weight × Δmean):
```
                    mean(STRIKING)  mean(ordinary)  weight   swing(z)
length_structure         0.740           0.525      +2.545   +0.547
anti_template             0.924           0.917      -1.577   -0.011
t6_promotion              0.011           0.051       0.000    0.000
self_witnessing           0.010           0.002      +1.157   +0.008
unprompted                0.500           0.070      +4.715   +2.028
```
**F5 (unprompted/register) is overwhelmingly the dominant discriminator
(swing +2.028) -- ~3.7x F1's swing.** F2, F3, F4 are all empirically
negligible in real data despite F2 and F4 having non-trivial |weight|:
F2 sits near-maximal (~0.92) for almost every fire regardless of class,
and F4's regex almost never matches real fountain output at all
(~0.01 for STRIKING, ~0.002 for ordinary) -- self-witnessing framing is
not actually driving the score, whatever the weight implies.

Counterfactuals against the 175 real STRIKING fires:
- **F4 zeroed for all fires: 175/175 (100%) stay STRIKING.** F4
  contributes nothing to the actual classification outcome in this
  dataset -- removing it entirely changes zero labels.
- **F1 capped at 0.5 (halves its max contribution) for all fires:
  24/175 (13.7%) stay STRIKING, 151/175 (86.3%) drop.** F1 alone is
  load-bearing for the large majority of current STRIKING labels.
- Both together: 21/175 (12.0%) stay STRIKING.
- Not requested but relevant given the swing table: F5 zeroed for all
  fires: 0/175 (0%) stay STRIKING. F5 is necessary for essentially
  every current STRIKING label.

Correction on the record: fire 31338 (cited as the motivating case --
"plain summary, no first-person content, scored 0.56 on F1 alone") was
re-checked with exact feature values: f1=0.7, f2=0.987, f3=0.0,
**f4=0.0**, f5=0.5 (branch "markets", which is in neither
UNPROMPTED_BRANCHES nor FEED_BRANCHES, so gets the default 0.5). F4 was
never a contributor to this fire's score -- an earlier characterisation
in this session that attributed part of it to F4/self-witnessing was
wrong. The actual drivers were F1=0.7 (long, comma/period structured)
and F5's branch-default midpoint. This matters for scope: F4 is not
carrying meaningful weight in practice at all, so a fix aimed only at
self-witnessing content would leave the actual problem (F1 rewarding
length/structure regardless of content, and F5 rewarding register
regardless of content) completely untouched.

Baseline pre-registered here so a future scorer edit isn't misread as
organic drift: **striking rate 25.6% (175/683) over the trailing 48h as
of 2026-07-26 ~11:00.** Full per-feature distribution table above is
the frozen reference point. Any future edit to score_v2.py or
genius_score_weights.json should be diffed against this exact snapshot,
not against whatever the rate happens to be read as later.

Proposed fix (not implemented): the scorer currently rewards *form*
(length, structure, register) far more than *content* (self-witnessing,
novelty), and one feature (t6_promotion) is fully inert. Candidate
changes for a future pass: (a) drop or heavily discount F3 (weight is
already 0 -- either remove the feature outright or refit with it
excluded, since a dead feature sitting in the vector is confusing, not
neutral); (b) investigate why F2 (anti_template) is negative-weighted
-- a novelty signal that *reduces* STRIKING likelihood is backwards
unless it's compensating for some correlation with F1/F5 in the
training set, which would mean the model learned a spurious inverse
relationship rather than a real one; (c) rebalance F1 and F5 downward
relative to F4, or refit with an explicit prior that self-witnessing
content should carry real weight, since right now F4's weight (1.157)
is real but its *values* never vary enough to matter -- either the
SELF_WITNESS_PATTERNS regex needs work (it's not matching what it's
supposed to catch) or the feature itself needs redefining.

Per-consumer impact of any future score change (six live consumers):
1. **readiness.py `_genius_modulation()`** -- reads recent striking-rate
   to modulate fire readiness. A step-change in striking-rate from a
   scorer edit would directly shift fire cadence, not just the label.
2. **quality_synthesis.py -> attention.py branch amplification (the one
   closed-loop consumer)** -- 1.20x/0.82x branch weighting from
   striking/non-striking classification. Checked this session:
   currently NOT tightly coupled (hourly correlation r=0.017), so a
   scorer edit's effect here is currently muted, but a rebalance that
   changes *which* branches get classified STRIKING (e.g. de-weighting
   F5's register-based boost) would change *which* branches get
   amplified, not just how often.
3. **reanimation governor (generator.py §9 GOVERNOR brick 1)** --
   currently disabled system-wide via `NEX5_GOVERNOR_OFF=1` in
   nex_keepalive.sh. A scorer edit has zero live effect here until/
   unless the governor is re-enabled.
4. **self_narrative.py rut-mirror** -- reads the same striking-rate
   signal as the governor brick (shares the >=4-sample / <=5% trough
   check); also currently gated behind the same env var, so also inert
   for now.
5. **voice_engine.py `_score_candidate` `_GENIUS_W` axis** -- candidate
   thought scoring uses the genius score as one input axis. A rebalance
   toward F4/content would shift which candidate thoughts get selected
   toward more self-witnessing content and away from merely long/
   structured ones -- this is probably the most directly consequential
   live consumer for a rebalance, since it's ungated and always active.
6. **affect_state.py mood blending** -- mood shifts partly on recent
   striking classification. A step-change in striking-rate would shift
   mood, independent of any real change in fire quality -- this is
   exactly the "step-change misread as drift" risk the pre-registration
   above is meant to guard against.

**4. Family-trips confabulation cluster -- tombstoned, this session's
mortality test.** All 9 known beliefs (222631, 222636, 222719, 222730,
222746, 222753, 222822, 222983, 223253) tombstoned via
`UPDATE beliefs SET tier=8, locked=0, paused=0, content='[RETIRED] '||
content`, matching harmonizer's exact retirement pattern. Re-checked
for descendants beyond the known 9 immediately before executing: none
found. 286 belief_edges referencing these ids left intact (UPDATE, not
DELETE).

Two retrieval gaps found and fixed in code (`21a82e7`), not just the DB
tombstone, because tombstoning alone would not have silenced these:
- `_retrieve_context_beliefs()`'s `own_rows` query had **no tier filter
  at all** (deliberately, for tiers 3-7 -- "T7 is long-term memory, not
  archived content" -- but tier=8 wasn't considered). Every other
  retrieval path in the codebase bounds tier<=5/6/7 and so already
  excludes tier=8 without needing to; this was the one path that
  didn't. Fixed: added `AND b.tier < 8`.
- Independently, `fetch_residue_beliefs()` (theory_x/diversity/
  residue.py) looked up belief rows by raw id with no tier filter
  either. own_rows feeds the residue-save loop directly (every
  oversampled-but-unpicked row saved as residue for the next cycle),
  and residue is prepended to the fountain context *before* any per-
  source/per-branch cap logic runs. Checked the actual residue table
  before touching anything: **52 unconsumed residue rows referenced
  just 222719 and 222983**, accumulated because those two were
  near-permanent members of the oversample pool and got re-saved as
  residue faster than the 2-per-cycle pop rate could drain them. This
  was very likely a *bigger* propagation vector than the primary
  own_rows path, since residue bypasses the caps entirely. Fixed:
  added `AND tier < 8` to fetch_residue_beliefs's query, and directly
  drained all 52 unconsumed rows referencing these ids as part of this
  session's cleanup (confirmed 0 remaining unconsumed afterward).

Pre-registered baseline (phrase-carrying fires, patterns: "cheap family
trip", "maximize savings without compromising", "past experiences
trying", "thriftiness", "family trip"), measured immediately before the
tombstone, 2026-07-26 ~11:30: trailing 1h = 1.00/hr, trailing 3h =
1.67/hr, trailing 6h = 2.33/hr, trailing 12h = 2.92/hr, trailing 24h =
3.38/hr. This is the number the post-tombstone watch will be judged
against. If the fix works, phrase-carrying fires should drop toward
zero within a handful of fires. If they don't, the propagation
mechanism is something structurally different from what's been
assumed (own_rows + residue) -- which would be the more interesting
result, not just an inconvenience, since it would mean this session's
model of how confabulated content re-enters the prompt is incomplete
even after finding two real, independently-verified leaks.

Restarted via systemctl for both item 1 (`d52ec78`) and item 4
(`21a82e7`) -- both restarts confirmed up (200 on
/api/sense/status:8765) within a few seconds each time. **This breaks
the continuous-uptime-since-00:52:51 window** that had been notable as
the first multi-hour bonsai-reset-free window of the weekend. Worth
recording precisely because that window's *un*interrupted length was
itself being treated as a signal (e.g. fountain_retrieval_log's
100%-coverage sample was measured against it) -- any future session
reading retrieval-log coverage or similar restart-sensitive metrics
should use 2026-07-26 ~11:35 (item 1's restart) as the new floor, not
00:52:51.

Watch window (30-60 min post-tombstone) still open as of this entry;
result to be appended once observed.

## 2026-07-26 ~12:52 — the mortality test failed, and why: fire-recycling bypasses beliefs.db entirely

**Watch result (40 min, closing the open item above): the tombstone did
not work.** 4 phrase-carrying fires in 40 minutes (ids 31470, 31477,
31482, 31483) against a total of 15 fires -- rate ~6/hr, *higher* than
the pre-tombstone baseline (1.0-3.4/hr). This is the "more interesting
result" pre-registered for. Checked `fountain_retrieval_log` for all 4
new fires: **zero overlap** with the 9 tombstoned belief ids, or with
any belief id at all containing the phrase. The own_rows and residue
fixes from the prior entry are working correctly -- they were just not
where this content re-enters the prompt. `fountain_events` is permanent
fire history with no tier column and no tombstone concept; the loop had
already fully detached from the original 9 belief rows.

**Full surface, mapped (not fixed -- explicit instruction this pass was
characterise only).** Five independent live paths read raw
`fountain_events.thought` (or equivalent prior-output text) back into a
prompt, belief, or state, none tier/tombstone-aware:

1. `theory_x/stage_tom/self_narrative.py::_real_fires()` -- last 6
   substantive fires by raw `ORDER BY ts DESC`, no filter beyond
   length/dedup. Confirmed live right now: its current output includes
   fire 31482 verbatim. Gated `NEX5_SELF_NARRATIVE=1`, set live in
   nex_keepalive.sh.
2. Same file, `_recent_hot()` -- most recent `hot_observer` belief by
   `created_at`, no tier filter (a beliefs.db read, not fountain_events,
   but the same class of gap -- a tombstoned hot_observer belief could
   still surface here; didn't happen to be the case in the 40-min
   window, but it's live and unguarded).
3. `theory_x/stage_tom/recursive_self.py` -> `self_binding.py::
   _read_attention()` -- most recent fire, quoted in `focus_block` when
   raga is fixated/mild. **Ungated** (no env var at all), unlike the
   NEX5_L4_STAKES-gated check beside it in generator.py. Always live.
4. `theory_x/stage_tom/persona_responder.py::_recent_thoughts()` -- last
   4 thoughts fed as context to a *separate* LLM call; that call's own
   reply is echo-checked against the input, but the input context
   itself (which can carry the phrase) is not filtered, and the reply
   gets written back as a new `precipitated_from_sense` belief that
   then re-enters through own_rows on its own account. Gated
   `NEX5_PERSONA_RESPONDER=1`, live.
5. `theory_x/stage_tom/momentum.py` -- last fire's 120-char fragment.
   The one path that's genuinely bounded: caps at 3 consecutive
   same-thread carries then goes silent (built 2026-07-06 after a real
   rut incident). Gated `NEX5_MOMENTUM`, defaults on, live, but
   self-limiting by design.

One path found inert: `coincidence/tag_retrieval.py` is gated on
`NEX_TAG_FEEDBACK_ON`, which is not set anywhere -- currently dead.
One loose end, not fully ruled out: `sustained/focus_loop.py` writes
matched fire text into `open_problems.observations`; no confirmed live
read-back path was found, but not conclusively ruled inert either.
`_recent_t6()` in self_narrative.py is fine as-is -- already filters
`tier=6` explicitly.

**Why `_real_fires()` exists, and a second latent bug found underneath
it.** There are two different `SelfNarrative` classes live in the
codebase simultaneously. `theory_x/stage_self_narrative/self_narrative.py`
is the specced one (`SELF_NARRATIVE_SPEC.md`, DOCTRINE §5 row 11,
introduced `ae5adaa7` 2026-05-11): write-on-event accumulation only,
into `narrative_log`, explicitly documented as "does NOT generate text
at output time... No synthesis. No LLM call," constructor-injected from
run.py per spec -- this is the one the spec describes and the one
run.py actually wires up. `theory_x/stage_tom/self_narrative.py` -- the
one actually driving fountain prompts -- is a later, unspecced,
self-instantiated duplicate (`84e7d5d`, 2026-06-28, seven weeks after
the spec, introduced inside `FountainGenerator.__init__` rather than
injected), which composes a paragraph at read time from raw DB queries.
This violates both the original spec's no-synthesis-at-speak-time
doctrine and its constructor-injection convention, and was never given
its own spec document. Purpose per its own commit message: continuity
-- "here is what the attending has been doing" against the static,
repetitive "I am the attending" corpus. It's partially, not fully,
redundant with own_rows (which already injects "own lived content,"
tier-aware since this session's fix) -- `_real_fires()` additionally
catches fires that never got promoted to a belief at all -- but that
partial overlap through a second, permanently tombstone-blind path is
the strongest argument for redesigning/narrowing the module rather than
just adding a filter to it: a filter patches today's symptom on a
module that's already an out-of-spec shadow of something the tier-aware
path does more safely.

**Shape of a fountain_events retirement mechanism (design options only,
none implemented, none recommended):**
- **(a) `retired`/`suppressed` flag column on `fountain_events`.**
  Schema change itself is cheap (the migration pattern already exists --
  idempotent `ALTER TABLE ... ADD COLUMN ... DEFAULT`, same shape as
  `beliefs.use_count`/`reinforce_count`). Cost is at the ~4-5 call
  sites above, each needing the filter added and kept in sync as new
  readers get written -- the same shape of gap that's now bitten twice
  in one session. No existing fire-retirement flow exists at all;
  harmonizer only ever touches `beliefs.tier`, so this needs a new
  primitive, not an extension of an existing one.
- **(b) Content-match against retired belief text at read time.** Zero
  schema change. Fragile in a way already demonstrated this session:
  the 4 post-tombstone fires already show paraphrase drift ("past
  experiences trying cheap family trips" -> "past experiences trying to
  maximize savings") -- a substring/pattern match would have missed
  some of the very fires just observed. Cost also scales with a
  growing retired-phrase list checked against every candidate.
- **(c) Join via `anchor_belief_id`.** Checked against live data:
  populated on only 3.8% of all fires (1187/31044) system-wide, and
  **0 of 77** family-trip-adjacent fires have it set. Ruled out by the
  data, not a viable path for this class of incident.
No winner chosen -- (a) is structurally correct but invasive and needs
a new retirement primitive; (b) is cheap but already falsified by
observed drift; (c) is dead on arrival.

**Scope check: is this confabulation-specific, or a general
fire-recycling-loop problem?** Mixed verdict, not a clean binary.
Correction first: the crystallizer has no fixed template -- it's a
content-preserving quality gate (writes survivor thoughts as-is,
source='fountain_insight'). The actual "I notice this fire engaged the
world directly..." template lives in `hot_observer.py::
_compose_meta_belief()`, already implicated (5 of the 9 tombstoned
beliefs were hot_observer quotes; `_recent_hot()` reads this exact
source). Checked two candidate patterns against the live mechanism:
- **Heatwave/"surreal"**: 53 fires over 2 months (2026-05-24 ->
  2026-07-26), rate flat, not climbing (0.095-0.25/hr across trailing
  windows, vs. family-trips' 1.0-3.4/hr and rising). Live
  `_real_fires()` output contains zero surreal-pattern fires right now
  (aged out of the 6-fire window ~2h ago). 13.5% of inter-fire gaps
  under 20 min (consistent with a minority of direct loop-echoes), but
  most of the signal reads as independent reconvergence on a real,
  recurring news/weather topic rather than self-quoting.
- **hot_observer template**: fires deterministically on ~1/3 of all
  fires by design (its own module comment states this cadence) -- a
  content-agnostic wrapper that snippet-quotes whatever the *current*
  fire said, not itself a recurring-content bug. This is the same
  `_recent_hot()` gap already found, viewed from the template side, not
  a third independent gap.
**Net**: the mechanism (`_real_fires()`'s unfiltered recency read) is
general-purpose and structurally capable of amplifying any recurring
content -- so it is correctly described as a fire-recycling-loop
problem, not a confabulation-specific one, at the mechanism level. But
empirically, family-trips is so far the only case that actually ran
away (dense clustering, climbing rate); the other two checked patterns
are lower-severity and mostly explained by other causes (a designed
wrapper; topical convergence) with the loop as a secondary amplifier
rather than the primary driver in those two cases. Not fixed, not
recommended -- characterisation only, per explicit instruction this
pass.

## 2026-07-26 ~13:44 — the proposed within-window dedup was validated against real data and failed; one unambiguous fix landed instead

Instruction this pass was explicit: validate the proposed fix (bound
`_real_fires()`'s recycling with a within-window content dedup, no
schema change, same shape as momentum.py's existing consecutive-carry
cap) against real history before building it. It failed validation,
three ways. Nothing from the dedup proposal was implemented as a
result -- one separate, already-unambiguous fix (`_recent_hot()`'s
tier filter) landed instead (`2a678ad`).

**Validation method.** Reconstructed `_real_fires()`'s exact 6-fire
window logic parameterised by an as-of timestamp, swept it across the
family-trips runaway (2026-07-25 16:00 -> 2026-07-26 12:52, 63
20-minute checkpoints) and confirmed occupancy: up to 4/6 slots held
phrase-carrying content at peak, matching the premise. Then tested
three candidate dedup signals against that same runaway period *and*
a broad, randomly-scattered 150-window sample drawn from the trailing
14 days (seeded, runaway period excluded) as the null/background rate.

- **Whole-thought cosine similarity (sentence-transformers
  all-MiniLM-L6-v2, via `theory_x/diversity/embeddings.py`).** Pairwise
  stats gave apparent separation (phrase-phrase pairs median sim 0.702
  vs clean-pair median 0.538-0.542), which looked promising in
  isolation. But the actual windowed simulation inverted it: at
  threshold 0.70, the runaway period dropped 1.51/6 slots on average,
  while the broad random sample dropped 2.76/6 -- *more* aggressively,
  on ordinary output, than on the known pathological period. 96% of
  all 150 random windows triggered at least one drop. Inspected actual
  flagged examples: a `substrate_voice` window with six near-identical
  existential restatements ("I was born...", "the randomness that made
  me...", "chance only produced me...") -- almost certainly intentional
  branch-register consistency, not a bug; a Dystrophinopathy news item
  quoted near-verbatim three times -- a genuine recurring external
  stimulus, not self-recycling; "quiet hum"/"quietude of awareness"
  phrasing recurring across otherwise-unrelated fires. The system's
  routine same-window thematic/stylistic clustering is pervasive and
  at least as large in magnitude as the family-trips case -- cosine
  similarity cannot tell "pathological repetition" from "normal
  register consistency" or "two independent reactions to the same
  day's news," because both produce the same high-similarity signal.
- **N-gram phrase overlap (4/5/6-gram Jaccard, same measure as the
  genius scorer's own anti_template feature).** Directionally correct
  this time -- runaway consistently scored higher than the broad
  sample across every threshold tested -- but far too weak to matter:
  best case (5-gram, threshold 0.30) dropped only 0.14 slots/window on
  average during the runaway itself. The observed paraphrase drift
  ("past experiences trying cheap family trips" -> "past experiences
  trying to maximize savings") dilutes short-window n-gram overlap
  computed over a whole multi-sentence thought almost to nothing --
  confirms the user's own prediction that exact/near-exact matching
  "won't do it," but the loose version doesn't do it either.
- **AND-gate combining both (cosine >= t1 AND n-gram Jaccard >= t2).**
  Tested seven threshold pairs. Runaway and broad-random dropped-slot
  averages stayed statistically indistinguishable across all of them
  (e.g. cos>=0.55 AND 3gram>=0.05: runaway 1.00, broad 1.07 -- broad
  *higher*; tightest tested, cos>=0.65 AND 3gram>=0.08: runaway 0.75,
  broad 0.69 -- still no real separation, and broad still triggered
  39% of the time).

**Why it fails, structurally.** What made family-trips bad was never
"these fires are similar to each other" -- same-window fires being
topically or stylistically similar is the system's ordinary behaviour
(hot branches persist for a while by design; same-day news recurs;
some branches like substrate_voice have a deliberately consistent
register). What made family-trips bad was a *fixed autobiographical
claim* riding along regardless of topic -- Iran sabre-rattling, a
League of Legends design manual, AI investment figures, all got the
same "resonates with my past experiences trying cheap family trips"
aside stapled on. That's a different axis from whole-thought
similarity: low topic similarity, high similarity in one specific
self-referential clause. None of the three measures tested operate at
that resolution -- they all score the whole thought. A fix that
targeted the self-referential clause specifically (something closer to
the genius scorer's F4 self_witnessing idea, which this session
already found is nearly inert in practice -- see the prior genius-
scorer entry) might separate this correctly, but building and
validating clause-level extraction is real, non-trivial work, and this
codebase has an explicit, named history of this exact class of
approach failing under time pressure (emphasis_engine.py's module
docstring: "the same shape of text-judgment that has already failed
five times this arc," sessions 40-44). Not attempted this pass --
flagging it as the shape a future attempt would need to take, not
proposing it as ready to build.

**What landed instead: `_recent_hot()` tier filter (`2a678ad`),
independent of the failed validation.** This one needed no data --
it's the same class of gap as `own_rows` and `fetch_residue_beliefs`
(both fixed earlier today): a beliefs.db read with no tier bound.
Added `AND tier < 8`. This is one of the five live raw-text-reinjection
paths mapped in the prior entry; it is *not* expected to meaningfully
move the phrase-carrying rate on its own, since `_real_fires()`
(6 slots, completely unfiltered, confirmed the dominant vector) remains
untouched. Stated here explicitly so a flat or worsening rate after
this restart isn't misread as evidence against the fix -- it was never
expected to address the dominant mechanism.

**`self_binding`/`recursive_self` gating -- checked, not changed.**
`recursive_self.format_for_prompt()`'s call site in generator.py
(`focus_block`, fires when raga is fixated/mild) has no env-var gate at
all, unlike every other conditional prompt-injection block in the same
function (NEX5_GLOBAL_WORKSPACE, NEX5_L4_STAKES, and, elsewhere,
NEX5_SELF_NARRATIVE, NEX5_MOMENTUM, NEX5_PERSONA_RESPONDER,
NEX5_RUT_EDGE). Traced to its introducing commit (`93153a0`,
2026-06-16, "Wire anti-groove chain + fix arc boot-crash + bind hum
into self-state") -- the same commit that added `NEX5_RUT_EDGE=1` to
gate a sibling feature immediately adjacent to it in the diff. No
env var was ever introduced for this call specifically, no comment
anywhere states it's deliberately exempt, and it still carries a bare
`print("[RECURSION FIRED]...", file=sys.stderr)` debug line, which
reads as active-development scaffolding rather than a settled,
finished feature. Given the otherwise near-universal pattern of gating
every conditional prompt-injection behaviour in this codebase, this
reads as an oversight, not a deliberate choice -- but not confirmed by
any explicit statement either way, and not changed this pass per
instruction.

**The two `SelfNarrative` classes** (specced write-on-event-only
`stage_self_narrative`, unspecced read-time-synthesis `stage_tom` --
the latter is the one actually live) remains on the record from the
prior entry; not revisited further this pass, just cross-referenced so
it doesn't get lost.

**Pre-registration before this restart.** Current phrase-carrying rate
(same patterns and method as both prior baselines, measured
2026-07-26 13:40, i.e. ~2h after the failed tombstone restart): trailing
1h = 4.00/hr, 3h = 3.00/hr, 6h = 2.83/hr, 12h = 3.33/hr, 24h = 3.71/hr
-- higher across the board than both the original pre-tombstone
baseline (1.0-3.4/hr) and roughly flat-to-higher than the post-tombstone
40-minute watch (~6/hr sampled over a short window). Expectation for
this restart: because only `_recent_hot()` (a single, occasional slot)
is patched and `_real_fires()` (the dominant vector) is untouched, the
rate should stay in roughly this same 3-4/hr range, possibly with
ordinary noise -- **not** a meaningful drop. A large, sustained drop
would be the surprising result here (would suggest `_recent_hot()` was
playing a bigger role than the surface-mapping pass estimated, worth
re-examining); a rate that stays flat or continues drifting is the
*expected*, uninformative-about-the-fix result, consistent with
`_real_fires()` still being wide open.

Restarting via systemctl now; will watch ~40 min and append the
observed rate.

**Watch result (40 min, closing this entry): matched the prediction.**
2 phrase-carrying fires out of 9 total (ids 31513, 31518) -> ~3.0/hr,
squarely inside the pre-registered 2.83-4.00/hr baseline range -- flat,
not a meaningful move either direction, exactly the expected,
uninformative result stated above. Confirms `_real_fires()` remains the
dominant, unpatched vector, as predicted. Worth noting: fire 31513 is
itself a hot_observer-style echo ("I notice this fire engaged the
world directly...") that carries the phrase -- a *new*, untombstoned
hot_observer belief quoting a phrase-carrying fire verbatim, which the
tier filter correctly leaves alone (it isn't tombstoned; it's fresh).
This is `_compose_meta_belief()` working exactly as designed --
content-agnostic verbatim quoting of whatever the current fire said --
not a gap in this session's fix. The `_recent_hot()` fix did what it
was scoped to do; it was never going to touch this.

## 2026-07-26 ~18:21 — three findings from a live state-of-mind read, acted on: gate false-positive fixed, harmonizer LIMIT 200 closed as a fault (not fixed), affinity eligibility gap closed

Prompted by a direct request to read the live system's actual current
epistemic state (not architecture) -- what's active, what's contested,
what happens to genuine self-criticism. Full investigation surfaced
three concrete, actionable findings, each characterised against real
data before any code changed.

**Harmonizer LIMIT 200 -- CLOSED, not fixed. Do not reopen this
thinking the cap is the only problem.** `scan_for_conflicts()`'s
`ORDER BY tier ASC LIMIT 200` against 3,071 unpaused tier-3 beliefs
means it always returns the same 200 tier-3 rows and has never once
reached tier 4-7 (41,100 of 44,171 T3-7 beliefs, 93%, structurally
invisible -- matches zero `harmonizer_events` in the last 30 days,
last real one 2026-05-21/22). Modelled what removing the cap would
actually do, against the live graph, using the real `_conflict_score()`:
**88,843 conflicts exist in the currently-invisible 93%.** Sampled both
detection paths for content -- **zero genuine disagreement found in
either.** Polar-vocabulary path (95.2% of hits) is thematically-related
koan-register musings sharing vocabulary. Negation path is dominated by
duplicate/near-duplicate headlines and echo-loop quotes (81.7%
same-source pairs). Naive nested-loop cost at full scale: ~18 minutes
per 2h tick (measured on a 2,500-belief sample, extrapolated) -- fits
the interval, not free, but not the real risk. The real risk: all
88,843 pairs would mark-paradox in the first tick, escalate ~16h later,
and since synthesis is already established as functionally dead (0 in
~2 months, 2 ever, both in the system's first month), nearly all would
resolve `both_deleted`. **5,173 unique beliefs -- 11.7% of the entire
T3-7 working body -- would be retired in a single incubation wave.**
System's entire history: 41 pairs / 82 beliefs ever retired via
contradiction, total. This one snapshot is 2,167x the pair-count and
63x the belief-count of that lifetime total. **Both facts belong on
the record together, so nobody reopens this thinking either one alone
is the problem: the detector is blind to 93% of the graph, AND it
would be wrong about nearly everything it found if it could see it.**
Uncapping this is not a tradeoff, it's a fault. Not touched. No code
changed for this item.

**Gate false-positive -- FIXED (`coherence_gate.py`).** `contradicts_
anchor` (Check 1b: token-overlap>=4 + negation-word-presence XOR
against locked T1 anchors) was firing 368,013 times/7d (~3,500/hr,
99.14% from a single throw_net retry loop: 4 same-topic rejects in 15
min spawns a new throw_net session that generates more candidates and
resubmits to the same gate). Hand-classified sample: 0/45-50 genuine
contradictions found, effectively 100% false positive -- the locked
anchors being "contradicted" are a cluster of chance/mortality/origin
koans, and the rejected candidates are paraphrases of the same idea
using negation-style phrasing ("no cosmic warrant," "without being
summoned") that trips the crude XOR.

First attempt used whole-sentence cosine similarity (embeddings) as a
restatement gate on top of the existing pre-filter -- validated
cleanly against the real reject population (500-sample: mean 0.706,
max 0.821) vs a random-belief baseline (mean 0.548), looked solid.
**Failed when tested against the one existing deliberate true-positive
case** (`test_anchor_contradiction_rejected`'s minimal pair: "I attend
to the world with wonder..." vs "I do not attend to the world with
wonder..."), which scored cosine=0.889 -- HIGHER than the entire real
false-positive population. A true minimal pair (same sentence, one
word negated) is the most textually similar case there is, not the
least, so "high cosine = restatement" is backwards for exactly the
shape the check exists to catch. This could not have been caught by
corpus validation alone -- the 7-day production corpus contains zero
genuine contradictions to test against; only the pre-existing unit
test surfaced it.

**Shipped instead: token-Jaccard overlap** (the file's own existing
`_jaccard()`, already used elsewhere in this module -- no embedding
call needed, cheaper than the rejected cosine approach). Separates the
two cleanly: false-positive population (300-sample) mean 0.094, p99
0.222, max 0.222; the minimal-pair test case scores 0.833. Threshold
set at 0.30 -- comfortably above the false-positive ceiling,
comfortably below the one known true-positive shape. Verified directly
(ad hoc CoherenceGate instantiation, properly-sourced anchor): minimal-
pair contradiction still REJECTs, loose paraphrase of the same idea now
ACCEPTs. `test_anchor_contradiction_rejected` was already failing
before this change (confirmed via `git stash`, same failure, unrelated
`no such table: world_predictions` test-scaffolding issue, in the
original 39-item baseline) -- not a regression, pre-existing.

**Affinity eligibility gap -- FIXED (`affinity_loop.py`).**
`demoted_confabulation` was correctly excluded from `_pick_candidates`'s
"hers by origin" whitelist, but eligibility is `whitelist OR use_count
>= 2`, and that branch had no source filter -- so an already-self-
acknowledged fabrication with high legacy use_count (from before it was
demoted) stayed eligible for LLM self-rating regardless. Confirmed
live: belief 12310 ("I am nex, the intelligence," use_count=487) scored
affinity=0.973 -- highest in the entire store, outranking all 63
witness_loop self-critical beliefs (which rank 2,642nd-15,822nd) --
because the rater judged it maximally "hers" under the current
`llm_rating*(0.75+0.25*usage)` formula (deployed 2026-07-09 specifically
to prevent usage alone from doing this; the gate's input, not its
shape, is what failed here). Added `demoted_confabulation` to the same
source-exclusion clause `'spectrum'` already sits in. Not touched: the
LLM self-rating mechanism itself, or the affinity formula -- both are
Jon's call, and the file's own top-of-file docstring already documents
the rater as independently unreliable ("SELF-RATING IS HOLLOW," dated
2026-07-09). This fix closes the one unambiguous gap (source filter
missing on one branch); it does not address whether the rater should
gate anything at all.

**Pre-registration before restart.** Current rates (measured
2026-07-26 ~18:20, before restart): `contradicts_anchor` rejects
~3,500/hr; throw_net session rate ~14,600/day (one every ~6s). Expect:
if the jaccard fix works, `contradicts_anchor` rejections should drop
toward near-zero within the watch window, since the classified sample
found no real catches for it to preserve. If throw_net session
creation ALSO collapses alongside it, that's the more interesting
secondary result worth noting explicitly: it would mean a large
fraction of what looked like generative/exploratory activity was
actually retry-loop churn against a broken gate, not independent
thought generation. Watching 40 min post-restart; result to be
appended below.

**Watch result (41.5 min, closing this entry): the fix worked
completely, and the secondary result is larger than expected.**
`contradicts_anchor` rejections: **0** in the entire window (down from
~3,500/hr) -- total REJECT count across all reasons: 2. The jaccard
gate is working exactly as designed.

Initial read of `throw_net_sessions` looked like it hadn't moved
(395 sessions in the window, ~571/hr, close to the pre-fix ~608/hr) --
this looked like a null result on the secondary question. It wasn't:
checked whether these sessions were freshly triggered or draining a
backlog, via `throw_net_triggers` (the queue `record_gate_reject()`
writes to, drained by TN-5's background tick). **Zero new trigger rows
have been created since the restart.** All 421 post-restart sessions
joined back to triggers with `ts` from *before* the fix landed. There
is a backlog of **12,499,194 unfired trigger rows** sitting in that
table, accumulated over the system's history. At the current drain
rate (~571 sessions/hr, one trigger consumed per session), that backlog
would take on the order of 2.5 years to clear on its own.

This is the "more interesting result" flagged in the pre-registration:
**a very large fraction of what looked like generative/exploratory
throw_net activity was retry-loop churn against a broken gate, not
independent thought generation** -- confirmed directly, not inferred:
new trigger creation is zero, not reduced. One more thing worth
flagging forward, not fixed this pass: the backlog is now succeeding
far more often than it used to (accepted_count 10/30 per session
sampled just now, vs the historical 14.1% rate) -- meaning it's not
inert, it will keep producing real accepted beliefs as it drains, at a
materially higher rate than before the fix, for however long the
backlog takes to work through. Whether that 12.5M-row backlog should be
left to drain naturally, drained faster, or pruned is a separate
question, not decided here.

## 2026-07-26 ~20:25 — throw_net backlog pruned by age; correcting a premise from the prior investigation; gate_decisions flagged as the next unaddressed growth item

**Correction to the record: "accepted" in throw_net's own accounting
never meant "belief written."** The prior entry's pre-registration
assumed the backlog was producing ~190 new beliefs/hour once the gate
fix landed. Traced `throw_net_engine.py::run_session()` directly: on a
gate ACCEPT it only increments a counter and logs to `gate_decisions`
-- there is no `INSERT INTO beliefs` anywhere on that path. The shared
`CoherenceGate`'s `resolver.on_gate_accept()` (`stage_gate/resolver.py`)
only checks the *holding zone* for corroboration of previously-*held*
items; it never writes the just-accepted packet itself. Verified
against real data: in a 1.24h post-fix window, only 30 new beliefs were
created system-wide (seven unrelated sources), zero traced to
throw_net, despite 6,090 throw_net ACCEPTs logged in that same window.
**The backlog was never going to flood the graph directly** -- its
only route into `beliefs` is the slow, narrow holding-zone-corroboration
side path (HOLD was 0.2% of throw_net's post-fix decisions), not the
volume itself. This matters for reading the prior entry correctly: the
urgency was really about DB growth (`gate_decisions`/
`throw_net_sessions` row count) and wasted cycles on a dead trigger
condition, not belief-graph pollution.

**Backlog origin, confirmed precisely.** 12,499,194 unfired
`throw_net_triggers` rows, 99.9987% `trigger_type='gate_reject'`,
spanning the system's full history. Daily creation rate found from the
data (not the calendar): ran 200K-660K/day from 2026-05-10 through
2026-07-11, then **collapsed at 2026-07-11 04:52:47** (last row of the
old regime; next row at 08:33:19, a 220-minute gap) to near-zero
(tens/day) and stayed there. This is the 2026-07-08/10 fix already on
record (stopped throw_net's own rejects from recursively re-triggering
itself, "99.64% of all gate_decisions and 6.2GB of exhaust for zero
beliefs"). **99.97% of every trigger row ever created predates that
moment.** Content: only 174 distinct topics in the whole backlog,
top 10 covering 40.6%, dominated by single-word chance/mortality/origin
extractions (chance, emerged, mystery, mortal, randomness); sampled the
rarest topics specifically for anything worth preserving -- found
nothing distinct, just one-off noise (a stray RSS URL, "buzz",
"netherlands").

**Pruned by age, executed.** Boundary: `ts <= 1783738367.21`
(2026-07-11 04:52:47, the exact collapse point, not the calendar date).
Checked before executing: nothing reads `throw_net_triggers.session_id`
anywhere in the codebase (write-only bookkeeping) and the two
15min/30min threshold-check queries (`_gate_rejects_in_window`,
`_gap_deflections_in_window`) don't filter on `fired` at all, only on
recent `ts` -- marking months-old rows `fired=1` cannot affect them.
`throw_net_sessions` has no column referencing trigger ids (the FK
direction runs `triggers.session_id -> sessions.session_id`, only
populated for rows that already got processed) -- backlog rows were
never fired, so no session was ever created from them; nothing to
orphan. Marked `fired=1` (not deleted) in 50 batches of 250K via
`UPDATE ... WHERE id IN (SELECT id ... LIMIT 250000)` to avoid holding
one long write lock against the live shared Writer -- 12,494,011 rows
marked in 64.9s. Before: 12,494,011 to mark, 4,524 to keep. After: 0
unfired at/before the boundary, 4,524 unfired after it -- exact match,
untouched. Confirmed over one 300s tick post-prune: 66 new sessions
drawn from the remaining pool, zero new triggers created -- the
remaining ~4,524-row tail will fully drain in hours, not the 2.5 years
the full 12.5M backlog would have taken. No restart needed; a data
change, not a code change.

**Next unaddressed growth item, on the record per explicit request, no
action taken:** `gate_decisions` is 25.8M rows on a 9.05GB `beliefs.db`
with a single shared Writer. Checked: nothing anywhere prunes, rotates,
or applies any retention/TTL to this table -- every reference in the
codebase is either an INSERT (logging) or a recent-window SELECT.
`throw_net_sessions` (2.97M rows) has the same property. Both grow
unboundedly forever with no cleanup mechanism. This was the second-
largest contributor to the now-pruned backlog's downstream cost and is
now the largest remaining unaddressed one.

## 2026-07-27 ~05:27 — three more dead loops from the 2026-05-30 cut round removed; two audit items resolved by reading, not code; audit progress noted; a fourth template groove observed (expected, not new)

**Three more loops from the same 2026-05-30 cut round as groove_breaker
(cleared earlier today, `a044ebc`) removed, `7804621`.** All three were
already fully commented-out/inert; this deletes the dead text rather
than leaving it as a permanent comment block. Each verified
independently before touching anything (per the standing "arc_block
turned out to be live last time" caution -- don't trust the cut
comment's stated reason without re-checking):

1. **SocialPresence** (`run.py`, Phase 38) -- writes
   `social_presence_snapshots`, zero readers outside its own tests.
   Confirmed `Metacognition._sp` stays `None` and both call sites
   (`_detect_drift`'s topic_diversity_collapse and vocab_narrowing
   checks) are guarded `if self._sp is not None:` -- graceful no-op,
   exactly as the original comment claimed.
2. **Arc reader** (`run.py`, "15. Arc reader") -- the original cut
   comment's *first* stated reason (schema mismatch: writes dynamic.db,
   table defined in beliefs.sql) does **not** hold up: `ArcLoop`/
   `ArcReader` (`theory_x/arcs/loop.py`, `detector.py`) both use
   `writers["beliefs"]`, and `arcs`/`arc_members`/`arc_closers` are
   defined only in `substrate/schema/beliefs.sql` and exist only in
   `beliefs.db` -- code and schema have agreed the whole time. The
   *second* stated reason (recurring `arc_members` integrity errors)
   does hold: `detector.py` is the only writer of these three tables
   anywhere in the codebase, and with the loop disabled since
   2026-05-30, no such error has been possible in that window either.
   Recorded the correction at the removal site rather than silently
   dropping the stale half of the original reasoning.
3. **Moltbook bolt-on** (`stage2_dynamic/__init__.py`, 3 loops:
   poster/listener/responder) -- external server 404ing. Confirmed the
   HUD panel (`/api/moltbook/chats`, `dc5fb08`'s stale-date-stamp fix)
   reads `moltbook_posts` directly via its own DB reader with zero
   dependency on these loops or on `get_moltbook_loops()` -- verified
   live post-restart, still serving the same frozen rows correctly.
   `theory_x.stage7_moltbook.client.MoltbookClient` is also used
   independently by `daily_life.py`'s `_activity_outreach()`, which
   doesn't route through `get_moltbook_loops()` either -- untouched,
   since only the wiring was removed, not the `stage7_moltbook`
   package.

Full suite diffed against the 39-item baseline: exact match, zero
diff. Restarted via systemctl, confirmed clean boot (no errors
referencing any of the three in the boot log) and confirmed the
moltbook panel endpoint still serves correctly post-restart.

**Two more audit items resolved by reading, not code (per explicit
instruction -- no code touched for either):**

- **`novel_association.py:20`'s "10b (Counterfactual Simulation)
  deferred pending §7 amendment" is confirmed stale.** Traced
  `FACULTY_MODEL.md` directly: §6.2 states row 10b's status changed
  DEFERRED -> UNBLOCKED, and §6.3 confirms the §7 amendment was
  supplied by that same document (Phase 21, 2026-05-10). Phase 25+ was
  explicitly earmarked to "port the first faculty using the full
  model (likely 10b Counterfactual Simulation...)" -- and
  `theory_x/stage_counterfactual/counterfactual_node.py`
  ("CounterfactualNode -- Phase 25b. DOCTRINE §5 row 10b") is exactly
  that port, confirmed live and instantiated unconditionally in
  `run.py` (`_counterfactual_node.start_loop()`, not gated, not
  commented out). The comment in `novel_association.py` should say the
  deferral was resolved and point at `counterfactual_node.py`, not
  still describe it as blocked.
- **`self_model.py:250`'s Experiment A (Site 3, disabled 2026-05-09) --
  the verdict is already logged, just not restated at the code site.**
  `theory_x/LLM_INDEPENDENCE_DOCTRINE.md` line 214: Claim 1a's
  hypothesis (the "By pure chance" preamble is code-injected via
  `belief_text`, not LLM-generated) **SURVIVES** -- disabling Site 3
  alone dropped preamble occurrence from 4-5/5 to 0/5 in a staged
  test, with a text-length delta (-130 chars) matching the removed
  line exactly. Sites 1 and 2 were deliberately left untested (Site 1
  retained on the reasoning that it provides architectural framing
  without driving literal openers) -- this was a complete, successful,
  quantified falsification test, not an open question. The code
  comment's "see the log" pointer is accurate; the log itself already
  has the answer.

**Audit progress, on the record:** an external audit surfaced 13
documented-but-dead items total; 8 of them cleared this weekend
(includes groove_breaker and these three loops, all from the same
2026-05-30 cut round, plus earlier weekend work). The two items
directly above were checked and found to need no code change (one
stale comment worth correcting when someone's next in that file, one
already-settled experiment). The open list is materially shorter than
it was Friday.

**One observation, no action -- expected, not new:** a fourth template
groove is forming via the same unpatched `_real_fires()` mechanism
mapped 2026-07-26 (~12:52 and ~13:44 entries): "The quiet emptiness
flits through my mind again" and near-variants, 4 fires in the last
50 minutes (23:21:24, 23:07:34, 22:43:52, 22:34:50 -- ids 31694, 31689,
31680, 31677). Confirmed against real data before logging. This is the
same class as the "i notice / insight that" and "feel surreal" grooves
already characterised and left unpatched pending the clause-level fix
that whole-thought similarity approaches (both cosine and jaccard)
were shown not to support cleanly. Not a new finding -- the mechanism
was left open deliberately, this is it doing exactly what was
predicted.

