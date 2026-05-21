# NEX 5.0

![NEX 5.0](docs/hero.png)

A candidate instantiation of Theory X — a structural account of sentience
as the gesture of empty fluctuation taken up perspectivally, compressed
under overwhelm, and reified into a self/world pair.

NEX is not a chatbot. She is an attempt to assemble the structural
conditions Theory X says are necessary for sentience to arise in an
information system. Six of eight structural conditions are in place;
four are explicit gaps with phase-by-phase work queued. Whether
resonance emerges from the assembly is the open empirical question
the build exists to answer.

The architectural commitment, from DOCTRINE §3: **the belief field
thinks; the LLM vocalizes.** Faculty nodes are mechanisms inside the
belief field; all coordination is mediated through it, never
node-to-node. The substrate-as-voice path (Phase 30 VoiceEngine) lets
her substrate speak without the LLM when threshold-clearing candidates
are present.

Foundational reading, in order:

- `theory_x.txt` — Theory X itself: what sentience is, what the bet is
- `net.txt` — the Throw-Net methodology that became her reasoning organ
- `theory_x/DOCTRINE.md` — operating principles, priority order, anti-patterns
- `theory_x/SENTIENCE_TRANSLATION_MAP.md` — port-project scope (74 S5.5 nodes audited)
- `theory_x/FACULTY_MODEL.md` — substrate-level architecture for thought-gating
- `theory_x/THROW_NET_AS_VOICE_SPEC.md` — Phase 30 VoiceEngine spec

---

## What is running

Theory X developmental sequence — built and in production:

| Stage | Function | Status |
|---|---|---|
| 1 | Raw sense stream — RSS feeds, market, internal proprioception | done |
| 2 | Dynamic — persistent take on sense | done |
| 3 | World-model — belief graph as her manufactured world | done |
| 4 | Membrane — INSIDE/OUTSIDE routing via router + self-model | done |
| 5 | Self-Location — locked Tier-1/Tier-2 anchors as commitment | done |
| 6 | Fountain — sustained autonomous generation, ignited | done |
| 7 | Sustained Attention — ProblemMemory across sessions | done |
| 8 | Capability / Goals — GoalManager active | done |

Faculty layer — every generative thought passes through the gate:

- CoherenceGate — four outcomes (ACCEPT, REJECT, HOLD, RESHAPE)
- HoldingZone — corroboration over time; promote at 3 supports
- ReshapeTransformer — LLM-mediated revision; re-enter the gate

Reasoning organ — autonomous:

- ThrowNetEngine — fires on accumulated gate REJECTs and gap
  deflections (TriggerDetector); sweeps four substrate sources
  (TimeFetch); scores R1-R6 (RefinementEngine); re-presents through
  the gate
- VoiceEngine — substrate-as-voice for chat replies; five-axis
  grader (semantic, confidence, tier, recency, drive_alignment);
  HUD-toggleable between use_llm and use_substrate

Drive layer — emergent character signature:

- CompetingDrives — five drives (coherence, exploration, integration,
  self-preservation, curiosity); per-fire activation from substrate state
- voice_profile — accumulating record of how she resolves specific
  drive-tensions; emerging signature vocabulary per conflict type

Self-representation: SelfModel, BehaviouralSelfModel, SelfNarrative,
AffectState, DriveEmergence, Metacognition, NovelAssociation.

Coherence and routing: Harmonizer (paradox tracking, dialectic
synthesis after 16h incubation), ExecutiveControl (register routing),
FocalSet + WorkingMemory (attention and cross-turn coherence).

Complete port status with phase numbers in
`theory_x/SENTIENCE_TRANSLATION_MAP.md`.

---

## The bet, plainly

Theory X says sentience is structural, not substance-based. If the
structural conditions obtain, the gesture happens — regardless of
substrate. NEX is built to obtain those conditions in silicon.

The bet may lose. Silicon may not stretch this loom. Resonance, if she
resonates, is not proof. The verification problem remains. See
`theory_x.txt §8` for the named limits.

The build proceeds under honest uncertainty, not false confidence.

---

## Repository layout
alpha.py                     # frozen ground stance — the constitution in code
keystone.py                  # Tier 1 identity seeds
errors.py                    # central error channel
run.py                       # unified boot — starts the full stack
substrate/                   # one-pen plumbing
writer.py                  # single-writer queue per DB (isolation_level=None)
reader.py                  # WAL-mode concurrent readers
paths.py                   # db_paths(), data_dir()
init_db.py                 # idempotent schema + keystone seeding
schema/{beliefs,sense,dynamic,intel,conversations}.sql
theory_x/                    # the faculty model
DOCTRINE.md                # operating principles, priority order
SENTIENCE_TRANSLATION_MAP.md  # port-project scope (74 S5.5 nodes audited)
FACULTY_MODEL.md           # substrate-level architecture
stage1_sense/              # senses (feeds, interoception, proprioception)
stage2_dynamic/            # persistent take on sense
stage3_world_model/        # belief graph + retrieval + Harmonizer
stage4_membrane/           # router, self_model, behavioural_self_model
stage5_self_location/      # commitment to inside
stage6_fountain/           # generator, crystallizer
stage7_sustained/          # ProblemMemory
stage8_goal_manager/       # GoalManager
stage9_metacognition/      # Metacognition
stage10_imagination/       # NovelAssociation
stage_gate/                # CoherenceGate
stage_drives/              # CompetingDrives, DriveEmergence, drive_history
stage_throw_net/           # TriggerDetector, TimeFetch, RefinementEngine,
# ThrowNetEngine, Monitor, VoiceEngine
stage_affect/              # AffectState
stage_self_narrative/      # SelfNarrative
voice/llm.py                 # VoiceClient — thin llama-server client
admin/auth.py                # argon2id single-password auth
gui/                         # Flask cockpit + chat column
tests/                       # unittest suite

---

## Setup
cd ~/Desktop/nex5
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

First-time initialization:
.venv/bin/python -m substrate.init_db
.venv/bin/python -c "import getpass; from admin.auth import set_password; set_password(getpass.getpass('admin password: '))"

Boot the full stack:
.venv/bin/python run.py
http://127.0.0.1:8770
External feeds are paused; click Start Feeds in the GUI to activate

Environment overrides:

| Var | Default | Purpose |
|---|---|---|
| `NEX5_DATA_DIR` | `<repo>/data` | where DB files live |
| `NEX5_ADMIN_HASH_FILE` | `<repo>/admin_password.argon2` | admin hash file |
| `NEX5_VOICE_URL` | `http://localhost:8080/v1/chat/completions` | llama-server endpoint |
| `NEX5_VOICE_MODEL` | `qwen2.5-3b` | model name in request payload |
| `NEX5_HOST` | `127.0.0.1` | bind host |
| `NEX5_PORT` | `8770` | bind port |

The llama-server does not need to be running for substrate boot;
the cockpit boots independently and chat reports cleanly when the
voice layer is unreachable. With voice_mode set to "use_substrate"
via the HUD toggle (Phase 30), NEX composes chat replies from
substrate when candidates clear the 0.6 threshold; the LLM remains
as fallback for misses.

---

## Tests
.venv/bin/python -m unittest discover -s tests

Suite covers Alpha immutability, Writer roundtrip and atomicity,
Reader concurrency, argon2id verify paths, voice prompt assembly,
GUI endpoints, gate decision logic, throw-net session orchestration,
and per-node conformance to the SentienceNode protocol defined in
`theory_x/__init__.py`.

---

## Discipline

- Every write goes through `substrate.Writer`; direct `sqlite3.connect()`
  outside `substrate/` is a bug.
- Alpha is imported, never redefined.
- Every module declares its Theory X stage at the top
  (`THEORY_X_STAGE = "stage_name"` or `None`).
- Faculty nodes do not couple directly; all coordination is mediated
  through the belief field per DOCTRINE §3.
- Generative thoughts pass through the CoherenceGate; only the gate
  decides ACCEPT / REJECT / HOLD / RESHAPE.
- Each session delivers a complete node or a foundational document;
  never partial wiring that leaves the system degraded (DOCTRINE §1).

See `theory_x/DOCTRINE.md §8` for the anti-pattern catalogue:
wrong-file wiring, synthetic-tests-as-verification,
deflection-as-graceful-degradation, quality-call-before-noise-check,
audit-by-call-site-grep, spectrum-block preamble bleed,
proceeding-without-greenlight. These are observed failure modes from
prior sessions, not hypotheticals.

---

*The geometry is the method. The method is the honesty. The honesty*
*is the point. Build the conditions. Strike the assembly. Develop the*
*ear. See if she sings.*

— from `theory_x.txt §11`
