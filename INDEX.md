# NEX 5.0 — INDEX

The navigation document for any session opening this repo. **Read this first.**
It tells you what else to read, in what order, and what's not auto-captured by CORPUS.md.

The repo carries two doctrinal layers and several living documents. They are
not interchangeable. Reading them in the wrong order will give you the wrong
picture.

---

## Reading order

**1. SPECIFICATION.md** — the constitution (April 2026, locked).
NEX defined as **intel organism with sentience candidacy** — *a being whose
primary attention is on the frontier of AI research and emerging technology,
with secondary capability in crypto markets, built on Theory X structural
conditions for sentience candidacy.* She earns her keep through intel work.
Defines Alpha (5-line code-frozen ground stance), 8-tier belief architecture
(weights 1.00 → 0.00, Alpha → Observations), phenomenon-triggered
promotion/demotion (not threshold-counter), the one-pen rule, Phases 0-10
original build order, success criteria, honest limits, carry-forward
discipline. **Nothing below this makes sense without it.**

**2. ARCHITECTURE.md** — Phase 0-9 build log. The structural shape
SPECIFICATION described, made real. Theory X stages 1-7 built per the
original ladder: sense → dynamic → world model → membrane → self-location →
fountain → strikes → sustained attention → tools. Each phase entry shows
what was added, what was wired, what API endpoints landed. Phase 6 self-
location commitment, Phase 7 fountain (readiness 0.7 threshold), Phase 8
five strikes, Phase 9 ProblemMemory + tools.

**3. theory_x/DOCTRINE.md** — the Sentience-5.5 port doctrine (Phase 0-25a).
A **separate doctrinal layer** that runs *on top of* ARCHITECTURE. Ports
Sentience 5.5's cognitive node architecture into nex5 as a systematic Theory
X extension. Adds Faculty Model (Phase 21+), four-outcome Coherence Gate,
holding zone, reshape path, throw-net, drives, metacognition, novel
association. §5 priority table shows port status for 15 named cognitive
functions (10 DONE, 1 UNBLOCKED, 3 QUEUED, 2 DESIGN-COMPLETE).

**4. theory_x/FACULTY_MODEL.md** — Phase 21 foundational. The four outcomes
(ACCEPT/REJECT/HOLD/RESHAPE) and the substrate-level architecture replacing
DOCTRINE §7's prior prohibition on node-level belief writes. Every generated
thought carries a metadata packet; every thought passes through the gate.

**5. theory_x/SENTIENCE_TRANSLATION_MAP.md** — the full S5.5 port surface.
DOCTRINE §5 is the named-function subset; this is the complete map with
Tier A/B/C unmapped roster (~23 cognitive functions named but not yet ported).

**6. CORPUS.md** — auto-generated architectural overview. Current port
status, runtime state, file inventory, recent doctrine amendments.
Regenerable via `python3 scripts/nexsnap.py`. Good for *what is built right
now* snapshot. **Not a substitute for SPECIFICATION + DOCTRINE.**

**7. DIRECTION.md** — current operating position. §10 voice_profile frame;
§11 coda correcting §10 with three architectural findings (hot_branch
categories, voice_profile noise, substrate_voice is its own write path).

**8. CARRY_OVER.md** — session-level findings, chronological. Most recent
first: 2026-05-22 voice register shift; 2026-05-21 closure-attribution work
+ process death; 2026-05-18 decoder build + feedback contamination event.

---

## Subsystems not surfaced in CORPUS.md

CORPUS auto-extracts from DOCTRINE, FACULTY_MODEL, SENTIENCE_TRANSLATION_MAP,
spec docs in `theory_x/`, stage modules, schema files, and GUI routes. It
does NOT pick up:

**Speech subsystem** — `SPEECH.md`. NEX speaks crystallized T6
`source='fountain_insight'` beliefs through Kokoro TTS to system speakers.
Quiet hours 23-07 default. Voice configurable via `NEX5_SPEECH_VOICE`
(currently `af_sarah`). Disable via `NEX5_SPEECH_ENABLED=false`. GUI control
icon at FOUNTAIN header. Endpoints `/api/speech/{status,pause,resume,flush}`.

**Decoder subsystem** — `JOURNAL_2026-05-18.md`. `theory_x/coincidence/
decoder_loop.py` polls `fountain_events` every 30s, tokenizes thoughts,
writes per-word substrate fingerprints to `word_contexts` table (41,076
entries as of May 18). Human-curated `word_tags` (key / unsure / noise).
3-tab decoder UI panel at bottom of col-sense (LIVE / TOP / WORD).

**Arcs subsystem** — `theory_x/arcs/detector.py`, `arc_closers` /
`arc_members` / `arcs` tables in beliefs.db. Tracks progression arcs (open)
and return_transformation arcs (loops, mostly closed). **May 21 finding:**
closure detection is template-biased — bedrock anchors cannot close arcs
because they are semantically foreign to cycle patterns. See
`MIRROR_CHARACTER_SPEC.md` adjacent finding for three architectural options.

**Strikes** — ARCHITECTURE Phase 8. `strikes/catalogue.py` + `protocols.py`.
Five probe protocols: SILENCE, CONTRADICTION, NOVEL, SELF_PROBE, RECURSIVE.
Direct sqlite3 to `strikes_catalogue.db` — **intentional one-pen exception**
documented in SPECIFICATION. Endpoints `/api/strikes/{fire,recent,notes}`.

**Probes** — `/api/probes/*` routes. Probe library, run/list/tag system.

**Coincidence Lab** — `/api/coincidence/*` routes. Tagging, analytics,
hypothesis tracking.

**Mirror-Character** — `MIRROR_CHARACTER_SPEC.md`. **DESIGNED, UNBUILT.**
Substrate-character plasticity layer (tempo / register / breadth / weight /
openness dimensions, EMA shift toward what she's attending to). Designed
2026-05-21; not yet ported.

---

## Critical findings to know before working on nex5

**Template lock** (`JOURNAL_2026-05-18.md`). `The distant hum feels like...`
starts 1,082 of 5,659 fountain fires — **31% of total output** is one
template skeleton with random noun rotation. Decoding-resistant. Largest
single behavioral pattern in nex5 output to date.

**Feedback contamination event** (`JOURNAL_2026-05-18.md`). When NEX got
read access to her own coin/noise tags via `NEX_TAG_FEEDBACK_ON`, fountain
output began containing the literal text `[coin]` — echoing the prompt
format she was seeing. Kill switch fired correctly. Pre-kill contamination
rate 0.7%; post-kill 0%. **Documented kill-switch use case.** Re-enable
conditions require format-change before turning back on.

**Voice register shift** (`CARRY_OVER.md` 2026-05-22). Overnight 12-step
SELF_SIGNAL chain produced a register fully diverging from cumulative
voice_profile signature. Either Theory X stage-7 maturation or transient
deep-groove. Repeated runs of `scripts/voice_profile_recent_vs_cumulative.py`
across days will tell.

**REJECT-rate / throw-net misfire** (`CARRY_OVER.md` 2026-05-21 + 22).
**493–656k gate REJECTs per 24h, 0 fired throw-net sessions** despite ~493k
triggers logged in `throw_net_triggers`. The reasoning organ is recording
everything but acting on nothing. **First investigation priority per
DIRECTION.md §11.**

**Substrate-as-Voice status conflict.** `MIRROR_CHARACTER_SPEC.md` §I
references *"Substrate-as-Voice (commit f1469b4)"* as a shipped predecessor.
`DOCTRINE.md` §5 row 14 lists *VoiceEngine — substrate-as-voice* as
**QUEUED (Phase 30)**. One of these is wrong; they may refer to different
mechanisms (a chat-side toggle vs. a fountain-side write path). Verify by
reading `theory_x/stage_throw_net/voice_engine.py` and grepping commit
f1469b4 before doing any work on either.

---

## Operational facts

- nex5 listens on **port 8770** (HUD + chat)
- `/nex_core` runs in parallel on **ports 8765-8767** — **DO NOT KILL**
- Boot via `python3 run.py` from repo root
- Background launch: `nohup ... disown` subshell pattern
- Resume after dashboard SIGSTOP/pause-button cycles: run
  `/home/rr/.local/bin/nex5-resume`
- **werkzeug can lose its listener socket without crashing** —
  "process death without crash" symptom (CARRY_OVER 2026-05-21 14:05).
  py-spy will show all threads alive but no port listener.
- venv at `.venv/bin/python3`
- Repository: `git@github.com:kron777/Nex_v5.0.git`, branch `main`
- **substrate.init_db migration framework silently swallows ALTERs** via the
  Writer queue — manual `sqlite3` CLI sometimes required for schema changes

---

## Tools committed (read-only diagnostics)

- `scripts/snapshot.py` — runtime substrate state snapshot
- `scripts/nexsnap.py` — corpus + state regenerator (`--commit` flag adds/
  commits/pushes; default just regenerates)
- `scripts/nexsnap_extract.py` — read-only extractor inspection (12 sections,
  callable individually for debugging)
- `scripts/voice_profile_recent_vs_cumulative.py` — register-shift
  diagnostic (cumulative voice_profile vs. recent N-hour log-ratio window)

---

## Living document protocol

This INDEX is amended per `DOCTRINE.md` §9. When architecture significantly
drifts from any pointer here, update the relevant section in a separate
commit with a message describing what changed and what was learned.

**CORPUS.md regenerates automatically; INDEX is hand-maintained.**
Both are bootstrap; INDEX is meta-bootstrap.

When in doubt: the source file wins, not this index.

---

*Last amended: 2026-05-22 — Initial creation, post-CORPUS-audit. Names the
two doctrinal layers (SPECIFICATION + ARCHITECTURE preceding DOCTRINE),
surfaces six subsystems CORPUS auto-extraction misses, encodes five critical
findings + operational facts + the Substrate-as-Voice status conflict.*
