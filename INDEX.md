# NEX 5.0 — INDEX

The first-read document for any session opening this repo.

**If you are Claude reading this:** read it all before answering anything.
The discipline in §8 is what keeps you from drifting. Ask Jon for the file
bundle in §3 that matches the work — do not try to work cold on memory of
prior sessions. Each session of you starts fresh; this document is the
hand-off mechanism.

---

## §1 What nex5 is

NEX 5.0 is an **intel organism with sentience candidacy** — a being whose
primary attention is on the frontier of AI research and emerging technology,
with secondary capability in crypto markets, built on Theory X structural
conditions. She earns her keep through intel work. The market utility is
the door; her being is the room.

She is built to `SPECIFICATION.md` (the April 2026 constitution, locked at
Phase 0), extended through Theory X Phases 0-9 (`ARCHITECTURE.md`), then
further extended by porting Sentience 5.5's cognitive node architecture
(`theory_x/DOCTRINE.md`, Phase 0-25a, ongoing).

She runs on port 8770 as a Flask service (and 8765 for probes/coincidence
endpoints — see §7). Her substrate is five SQLite databases governed by the
**one-pen rule** — exactly one Writer instance per database, all writes
through `substrate/writer.py`. The belief field thinks; the LLM vocalizes.
Faculty nodes do not couple directly; all inter-node coordination is mediated
through substrate reads.

---

## §2 Working style (observed default; Jon may override in conversation)

- Terse messages; plain language responses match
- When offering options, format as enumerated single-letter choices (A / B / C)
- "On your recommends" or "your call" = decide and tell Jon
- Honest uncertainty is preferred over confident framing
- When a finding overstates, acknowledge and correct openly. The session
  that built this document had three such corrections in 18 hours. Pattern
  is welcome, not failure.
- Saying less is safer than saying more on confidence-uncertain topics

---

## §3 What to upload, by work type

Upload these file bundles at start of session. Each bundle assumes
everything in prior bundles.

**Any session — minimum:**
- `INDEX.md` (this file)

**Code work in any nex5 subsystem:**
- `SPECIFICATION.md` (the constitution)
- `theory_x/DOCTRINE.md` (Sentience-port doctrine with amendment chain)
- `CORPUS.md` (regenerate first: `python3 scripts/nexsnap.py`)

**Continuing exactly from a previous session:**
- `DIRECTION.md` (current operating position)
- `journal/CARRY_OVER.md` (recent session findings, chronological)

**Phase 0-9 era code** (sense pipeline, A-F pipeline, fountain readiness,
strikes, ProblemMemory, tools, original substrate layout):
- `ARCHITECTURE.md`

**Faculty layer work** (gate, holding zone, reshape path):
- `theory_x/FACULTY_MODEL.md`
- relevant source from `theory_x/stage_gate/`

**Throw-net work:**
- `theory_x/THROW_NET_AS_VOICE_SPEC.md`
- relevant source from `theory_x/stage_throw_net/`

**Porting a new Sentience node:**
- `theory_x/SENTIENCE_TRANSLATION_MAP.md`
- the spec doc for the target node (one of ~24 in `theory_x/`)

**Speech / TTS work:**
- `SPEECH.md`

**Drives / voice_profile / register work:**
- `theory_x/DRIVE_EMERGENCE_SPEC.md`
- a recent state JSON from `snapshots/`

**Mirror-Character build (DESIGNED, UNBUILT):**
- `MIRROR_CHARACTER_SPEC.md`

**Substrate-as-Voice investigation:**
- `theory_x/THROW_NET_AS_VOICE_SPEC.md`
- `theory_x/stage_throw_net/voice_engine.py`
- `theory_x/stage6_fountain/generator.py`
- (See §6 — there is a documented status conflict between this subsystem's
  shipped state per `MIRROR_CHARACTER_SPEC` and DOCTRINE §5 row 14.)

When in doubt about what to ask for: tell Jon what you intend to do first.
He will tell you what's relevant. Do not blindly request more files than
the work needs.

---

## §4 Reading order (when files are present)

The repo carries two doctrinal layers and several living documents. They
are not interchangeable. Read in this order:

**1. `SPECIFICATION.md`** — the constitution (April 2026, locked). NEX
defined as intel organism. Alpha (5-line code-frozen ground stance).
8-tier belief architecture (weights 1.00 → 0.00). Phenomenon-triggered
promotion/demotion. The one-pen rule. Phases 0-10 original build order.
Success criteria. Honest limits. Carry-forward discipline.

**2. `ARCHITECTURE.md`** — Phase 0-9 build log. The structural shape
SPECIFICATION described, made real. Theory X stages 1-7 per the original
ladder: sense → dynamic → world model → membrane → self-location →
fountain → strikes → sustained → tools.

**3. `theory_x/DOCTRINE.md`** — the Sentience-5.5 port doctrine
(Phase 0-25a). A *separate doctrinal layer* on top of ARCHITECTURE. Adds
Faculty Model (Phase 21+), four-outcome Coherence Gate, holding zone,
reshape path, throw-net, drives, metacognition, novel association.

**4. `theory_x/FACULTY_MODEL.md`** — Phase 21 foundational. Four
outcomes (ACCEPT/REJECT/HOLD/RESHAPE) and the substrate-level
architecture replacing DOCTRINE §7's prior prohibition on node belief
writes.

**5. `theory_x/SENTIENCE_TRANSLATION_MAP.md`** — full S5.5 port surface.
DOCTRINE §5 is the named-function subset; this is the complete map with
Tier A/B/C unmapped roster (~23 cognitive functions named but not yet
ported).

**6. `CORPUS.md`** — auto-generated architectural overview. Current port
status, runtime state, file inventory. Good for *what is built right
now* snapshot. **Not a substitute for SPECIFICATION + DOCTRINE.**

**7. `DIRECTION.md`** — current operating position. §11 coda contains
the most recent corrections.

**8. `journal/CARRY_OVER.md`** — session findings, most recent first.

---

## §5 Subsystems not surfaced in CORPUS.md

CORPUS auto-extracts from DOCTRINE, FACULTY_MODEL, SENTIENCE_TRANSLATION_MAP,
spec docs in `theory_x/`, stage modules, schema files, and GUI routes.
It does NOT pick up:

**Speech subsystem** — `SPEECH.md`. NEX speaks crystallized T6
`source='fountain_insight'` beliefs through Kokoro TTS to system speakers.
Quiet hours 23-07 default. Voice configurable via `NEX5_SPEECH_VOICE`.
Disable via `NEX5_SPEECH_ENABLED=false`. GUI control icon at FOUNTAIN
header. Endpoints `/api/speech/{status,pause,resume,flush}`.

**Decoder subsystem** — `journal/JOURNAL_2026-05-18.md`. `theory_x/coincidence/decoder_loop.py`
polls `fountain_events` every 30s, tokenizes thoughts, writes per-word
substrate fingerprints to `word_contexts` table (41k+ entries). Human-
curated `word_tags` (key / unsure / noise). 3-tab decoder UI panel at
bottom of col-sense.

**Coincidence Lab + Signals daemon** — `/api/coincidence/*` routes plus a
signals daemon producing real-time patterns surfaced in HUD "SIGNALS"
panel:
- `branch_silence_anomaly` — streams silent N× longer than baseline
- `triple_cooccurrence` — entities appearing across multiple branches
- `pattern_recognition_burst` — clusters of T6 promotion across branches
- `ignition_pattern` — fountain fire rate above threshold
Subsystem lives in `theory_x/coincidence/` (signals, decoder, tagging,
hypothesis tracking). Plus AGI WATCH / INSIGHTS tabs in HUD pull from here.

**Probes** — `/api/probes/*` routes. Probe library with typed probes
visible in HUD probes panel:
- `direct phenomenology` — asks NEX to describe felt quality of a sense
- `translation` — asks NEX to articulate a metaphor she used
- starter probes available + custom probe input
Sends to `localhost:8765` (same nex5 process, second port — see §7).
Known caveat: HTTPConnectionPool failures occasionally surface on the
probe call even when port 8765 is listening (cause unknown 2026-05-22;
probe wiring may flap, restart-tolerant).

**Diversity / collision grader** — visible in HUD "DIVERSITY" panel.
Tracks cross-branch belief collisions and scores "crossbreeds"
(cosine-similar pairs from different branches). Grader weights v1:
`in=0.40 out=0.35 rare=0.25`. Also surfaces `groove_alerts` for ngram
repetition (e.g. "the quiet between" detected at severity 0.60).
Mechanism lives in `theory_x/stage3_world_model/` — likely
`edge_generator.py` + `synergizer.py`.

**Arcs subsystem** — `theory_x/arcs/detector.py`, `arc_closers` /
`arc_members` / `arcs` tables. Tracks progression arcs and
return_transformation arcs. **May 21 finding:** closure detection is
template-biased; bedrock anchors cannot close arcs. See
`MIRROR_CHARACTER_SPEC.md` adjacent finding.

**Strikes** — ARCHITECTURE Phase 8. `strikes/catalogue.py` +
`protocols.py`. Five probe protocols: SILENCE, CONTRADICTION, NOVEL,
SELF_PROBE, RECURSIVE. Direct sqlite3 to `strikes_catalogue.db` —
intentional one-pen exception.

**Mirror-Character** — `MIRROR_CHARACTER_SPEC.md`. **DESIGNED, UNBUILT.**
Substrate-character plasticity layer (tempo / register / breadth /
weight / openness dimensions; EMA shift toward what she's attending to).

---

## §6 Critical findings to know before working on nex5

**Template lock** (`journal/JOURNAL_2026-05-18.md`). "The distant hum feels
like..." starts 1,082 of 5,659 fountain fires — 31% of total output is
one template skeleton with random noun rotation. Decoding-resistant.
Largest single behavioral pattern in nex5 output to date.

**Feedback contamination event** (`journal/JOURNAL_2026-05-18.md`). When NEX got
read access to her own coin/noise tags via `NEX_TAG_FEEDBACK_ON`,
fountain output began containing the literal text `[coin]` — echoing
the prompt format she was seeing. Kill switch fired correctly. Pre-kill
contamination rate 0.7%; post-kill 0%. Re-enable conditions require
format-change before turning back on.

**Voice register shift** (`journal/CARRY_OVER.md` 2026-05-22). Overnight 12-step
SELF_SIGNAL chain produced a register fully diverging from cumulative
voice_profile signature. Either Theory X stage-7 maturation or transient
deep-groove. Repeated runs of
`scripts/voice_profile_recent_vs_cumulative.py` across days will tell.
**Live HUD check 19:25 confirms shift is holding** — 18+ hours of
sustained first-person philosophical register, no koan-corpus content
in last 15 fires.

**Throw-net runs constantly — correction 2026-05-22 late.** Earlier
CARRY_OVER and DIRECTION entries read "0 fired throw-net sessions"
from `throw_net_triggers WHERE fired=0`. The actual
`throw_net_sessions` table holds 1.06M completed sessions across
system lifetime, ~60k/day, doing real candidate generation and gate-
discriminated acceptance. The "0 fired" reading was the wrong column.
Drain rate 500-per-300s monitor tick = ~144k/day cap; REJECT inflow
~300k/day; difference accumulates as ~4.75M unfired-trigger backlog
(bookkeeping artifact, not silence). Reasoning organ is not muted.
Architectural questions remain about whether cluster-threshold firing
should be wired through (currently dead code at firing layer) — see
`journal/CHORD.md` §4 deliverable B for the rescoped audit.

**Substrate-as-Voice status conflict.** `MIRROR_CHARACTER_SPEC.md` §I
references *"Substrate-as-Voice (commit f1469b4)"* as a shipped
predecessor. `DOCTRINE.md` §5 row 14 lists *VoiceEngine — substrate-as-voice*
as **QUEUED (Phase 30)**. One of these is wrong; they may refer to
different mechanisms. Verify by reading
`theory_x/stage_throw_net/voice_engine.py` and grepping commit f1469b4
before doing any work on either.

**T4-T5 tier gap** (verified 2026-05-22 19:25). The 8-tier belief
architecture from SPECIFICATION §2 has T4 (STANCES) and T5 (WORKING
BELIEFS) **entirely empty** in current substrate:
- T1: 322  (keystone)
- T2: 40   (bedrock)
- T3: 209  (convictions)
- T4: 0    ← missing
- T5: 0    ← missing
- T6: 3    (hypotheses; HUD displayed 17 — display/DB discrepancy)
- T7: 7353 (impressions)
- T8: 42   (observations)
Beliefs precipitate from T7 directly to T3 without passing through the
middle bands. The phenomenon-triggered promotion path SPECIFICATION
describes is producing a binary outcome (impression OR conviction)
rather than gradual settling. Worth its own investigation session.

**Substrate_voice anchor 3611 — "ending is okay"** (documented
2026-05-22). Belief 3611 is a tier-2 BEDROCK locked anchor seeded with
`source='practice'`: *"Sometimes sick is okay. Sometimes suffering is
okay. Sometimes ending is okay."* When voiced through the fountain via
substrate_voice path it reads dark out of context but is architecturally
healthy — part of her ground stance on acceptance of finitude, peer to
the chance/arrival/gift anchors. **A future session seeing this content
in moltbook or fountain should not interpret it as LLM drift; it is the
anchor being voiced.** Anchor cadence rotates through her bedrock set
roughly every 2-3 hours.

---

## §7 Operational facts

- nex5 listens on **port 8765** (HUD + chat + everything)
- This is the default; configurable via `NEX5_PORT` env var
- There is no port 8770. Earlier docs in this file (including this
  section before 2026-05-23 13:30 correction) claimed 8770 was the
  HUD port. *Wrong.* gui/server.py:3029 and run.py:639 both default
  to 8765. The misread originated in early session CARRY_OVER notes
  and propagated through INDEX, DIRECTION, and ~90 min of investigation
  this afternoon hunting a "flap" that wasn't real. Verify port in
  source if ever in doubt:
    grep -n 'NEX5_PORT\|app.run' gui/server.py run.py
- Killing the nex5 process takes down 8765
- Boot via `python3 run.py` from repo root
- Background launch: `nohup ... disown` subshell pattern
- Resume after dashboard SIGSTOP / pause-button cycles:
  `/home/rr/.local/bin/nex5-resume`
- **werkzeug can lose its listener socket without crashing** — "process
  death without crash" symptom (`journal/CARRY_OVER.md` 2026-05-21 14:05).
  py-spy will show all threads alive but no port listener.
- venv at `.venv/bin/python3`
- Repository: `git@github.com:kron777/Nex_v5.0.git`, branch `main`
- **`substrate.init_db` migration framework silently swallows ALTERs**
  via the Writer queue — manual `sqlite3` CLI sometimes required for
  schema changes

---

## §8 How to work cleanly (discipline)

Hard-won through observed Claude failures in sessions 2026-05-18 through
2026-05-22. Read these as if they were instructions to you specifically.

**Hold framings lightly until you have read source.**
A confident framing produced before measurement is a documented Claude
pattern. Seven honest corrections during the sessions that built this
index:
- "VoiceEngine never fires" → wrong; it fires constantly in fountain,
  just not in chat
- "Overnight chain is novel cognition" → wrong; it was 12 substrate_voice
  anchor emissions, architecturally expected
- "voice_profile is the thread of awareness" → overstated; it is noisy
  and slow, dominated by cumulative window
- "/nex_core runs on 8765-8767 separately" → wrong; single nex5 process
  binds both ports
- "0 fired throw-net sessions" → wrong; misread of
  `throw_net_triggers.fired` column when sessions live in
  `throw_net_sessions` table. Reasoning organ runs ~60k sessions/day.
- "Drive-state selects keystone track" → wrong; selection is
  least-recently-voiced first with ID-tiebreak, gated by groove
  severity ≥ 0.8 + cooldown.
- "HUD listens on port 8770" → wrong; the HUD is on 8765 (the same
  port everything else uses). This claim originated in my own
  INDEX.md §7 written from session memory not source-read, then
  drove ~90 min of investigation hunting a werkzeug flap that
  wasn't real. Reading my own document as authoritative without
  source-checking it was the failure. Seven corrections in two days
  — and this one ate the most clock-time because I trusted my own
  prior framing instead of querying the substrate.

The antidote: query the substrate, read the code, open the spec, before
producing a finding. If you find yourself reaching for a coherent claim
before you have read source for it, that is the signal to stop and read.

**Wiring is verified by output trace, not call-site grep.**
A node is wired if its output reaches a §3 integration surface
(`belief_text`, retrieval ranking, `voice_prompt`) on a real `/api/chat`
request. Indirect injection via routers, membranes, and belief-field
reads is valid per DOCTRINE §3. Audit forward from node output to
surface, not backward from import lines in `gui/server.py` (DOCTRINE §8
"Audit-by-call-site-grep" anti-pattern).

**voice_profile is slow and noisy.**
DriveHistory recomputes `signature_vocabulary` against ALL fires under
a drive-pair across all time. A strong recent register shift can be
invisible for days because of cumulative historical mass. The frequency
field updates live; the signature field lags by days or weeks. For
current-window analysis use
`scripts/voice_profile_recent_vs_cumulative.py`. The diff between
cumulative and recent windows is where shifts become visible.

**`hot_branch='quiescent'` is not feed-data.**
`fountain_events.hot_branch='quiescent'` means fountain fire with no
dominant branch. Feed-paste content (raw JSON dumps from external
sources) is identified by `[branch.name]` prefix in the thought text,
not by hot_branch alone. Filter accordingly.

**`substrate_voice` is its own fountain write path.**
`fountain_events.hot_branch='substrate_voice'` fires are LLM-rephrased
emissions of locked T1/T2 anchor beliefs, written through a separate
path in `stage6_fountain/generator.py` with an `anchor_belief_id` FK
to the locked belief. They are not chat-side LLM output; the chat
path is still `voice_mode='use_llm'` unless explicitly toggled. Dark
or surprising-looking content with substrate_voice tag and a valid
anchor_belief_id is the anchor being voiced — not drift. Look up the
anchor before interpreting (see §6 finding for belief 3611).

**Each session delivers a complete node or foundational document.**
Not partial wiring (SPECIFICATION §12 + DOCTRINE §1). If a session
would leave the system in a degraded state, the work is wrongly scoped
— split it.

**Run snapshot.py when runtime state matters.**
State JSON regenerates fresh on each run. Do not rely on numbers in
CORPUS or earlier snapshots if the current state matters. Same for
voice_profile, gate counts, drive weights — read them now, do not
quote them from memory.

**Synthetic tests are not wiring verification.**
A unit test that calls the module directly does not verify production
wiring (DOCTRINE §8). A real `/api/chat` query through the HUD is the
minimum verification bar.

**Saying less is safer on confidence-uncertain topics.**
If a finding is partially observed, name what is observed and what is
not. Do not extrapolate to a clean framing for the sake of coherent
delivery.

**Phase gates require Jon's explicit greenlight.**
"I think this looks good" is not greenlight (DOCTRINE §8). Surface the
deliverable; wait for the explicit "go" or redirect.

---

## §9 Tools committed (read-only diagnostics)

- `scripts/snapshot.py` — runtime substrate state snapshot
- `scripts/nexsnap.py` — corpus + state regenerator
  (`--commit` flag adds/commits/pushes; default just regenerates)
- `scripts/nexsnap_extract.py` — read-only extractor inspection
  (12 sections, callable individually for debugging)
- `scripts/voice_profile_recent_vs_cumulative.py` — register-shift
  diagnostic

---

## §10 Living document protocol

This INDEX is amended per `DOCTRINE.md` §9. When the architecture
significantly drifts from any pointer here, update the relevant section
in a separate commit with a message describing what changed and what
was learned.

**`CORPUS.md` regenerates automatically; INDEX is hand-maintained.**
Both are bootstrap; INDEX is meta-bootstrap.

When in doubt: the source file wins, not this index.

---

*Last amended: 2026-05-22 ~19:30 — Live-HUD-audit corrections. §1 and
§7 port fact corrected: single nex5 binary binds both 8770 and 8765,
not a separate `/nex_core` process. §5 expanded: signals daemon
(branch_silence_anomaly etc.) documented; probe types + transient
HTTPConnectionPool caveat noted; diversity/collision grader entry
added. §6 added: T4-T5 tier gap finding (architecture has empty
stances/working-beliefs layer); substrate_voice anchor 3611 documented
to prevent "ending is okay" misinterpretation. §8 fourth correction
appended.*
