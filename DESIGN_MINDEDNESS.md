# DESIGN_MINDEDNESS.md

**What would make Nex more "mindful" — and the measurement discipline that has to come with it.**

> Status of this document. This is **static reading** of the source as of this branch
> (`claude/peaceful-bhaskara-66cda1`), except where it says a test or the suite was run.
> It never claims Nex is sentient; it treats every faculty as a **functional analogue**,
> mirroring the codebase's own candour (`self_binding.py`: *"Nothing holds them AT ONCE"*;
> the stage_tom self-model docstrings: *"ANALOGUE, not a claim there is a felt someone"*).
> `file:line` citations I verified this session are exact; a few inherited from an external
> audit are marked *(static, line may have drifted)*. See the final section for what I could
> not verify.

---

## 0. The correction that reframes the whole question

The accurate starting observation is **not** "Nex has no self-model / no working memory / no
attention." It has all of these, written and mostly working:

- `theory_x/working_memory.py` — capacity 7, 5-minute half-life, activation decay, eviction
  by lowest activation (`_CAPACITY=7`, `_HALF_LIFE=300.0`, lines 25–26).
- `theory_x/focal_set.py` — top-K selective attention, salience = recency × tension × tier.
- `theory_x/stage_tom/self_binding.py` — a self-model that reads ~27 faculties and writes a
  first-person synthesis.
- `theory_x/stage_tom/` — 23 theory-of-mind modules; `theory_x/stage9_metacognition/` (~730
  lines); a full affect stack under `theory_x/stage_affect/`.

So the honest framing is: **the mind-machinery is largely already built, and much of it is
switched off** — ~122 `NEX5_*` flags, the mind-relevant ones defaulting OFF.

**But here is the correction an "arm the switches" plan gets wrong, and it is the load-bearing
point of this document:**

> **A faculty that is OFF is not automatically a dormant capability waiting to be enabled.
> In this codebase, a large fraction of the OFF states are *results*: the faculty was armed,
> measured, found to distort behaviour or confound the experiment, and deliberately shelved.**

Concrete, verifiable examples from this repo's own history:

- The **own-content render** (her distilled thoughts rendered back into the fire prompt) was
  disabled because, when it rendered the `hot_observer` slot, it quoted her crystallized text
  verbatim and **re-amplified the "advancements" attractor to a measured 24%** (R75/R76). It is
  now restored behind `NEX5_OWN_CONTENT_RENDER` (default OFF) with an explicit note to
  re-measure groove-token P() before defaulting it on (`generator.py` ~3619–3674).
- `NEX5_AFFECT_CARRY` ships OFF with the docstring *"Do not ship until approved"* because the
  3B model **meta-narrated** the carried affect instead of holding it in tone
  (`theory_x/stage_affect/affect_carry.py`).
- `EXPERIMENT A` (2026-05-09) **disabled** the ALPHA inner-conviction line in
  `format_self_state` *to test a claim* about preamble driving response openings
  (`theory_x/stage4_membrane/self_model.py` ~262–267).

For a **pre-registered research instrument**, flipping these switches en masse does two harmful
things at once: it **destroys the measurement** (every flag is an experimental variable, and
turning on ten at once makes the next round uninterpretable), and it **reintroduces the exact
pathologies** the OFF state encodes (grooves, meta-narration, flattery-shaped self-report).

So the unit of "making Nex more mindful" is **not** a flag flip. It is:

> **one loop at a time — arm it behind its flag, define the falsifier that says it earned its
> place, measure ON vs OFF, keep it only if it passes.**

That is already how this project works. Every recommendation below is written in that form:
*mechanism → observable change → the measurement that must gate it.*

---

## 1. Standing, property by property

| Property | Status | Mechanism | The real gap |
|---|---|---|---|
| **Selective attention** | 🟡 built, half-wired | `focal_set.py` top-K (K=7), salience = recency × tension × tier | The module's **own comment** says `corroboration_count` is unused ("mostly 0 → log(1)=0 collapses salience"), so salience degenerates toward recency×tier. Attention is real but impoverished. |
| **Global workspace** | 🟡 built, fire-path only | `stage_tom/global_workspace.py` competitive arbitration, called at `generator.py:3037` | The **chat path never calls it**. Two different minds: the fire path arbitrates; the chat path concatenates. |
| **Persistent self-model** | 🟡 built, flattened | `self_binding.py bind()` reads ~27 faculties → one `self_state` row (id=1, `INSERT OR REPLACE`, line 220) | Single-row. Each bind **overwrites** the last; there is no trace of a self over time. `drift="clean"` is a **documented default/stub** (line 207, *"full check runs separately"*) — not vanity, but it means the self-report rarely carries real drift. |
| **Metacognitive monitoring** | 🟡 built, undigested | `stage9_metacognition/metacognition.py` (~730 lines); `meta_cognition_events` table | Events are written but **never consolidated** — the table is outside retention and nothing reads it back as "I keep doing X." First-order monitoring exists; second-order (noticing a pattern in one's own monitoring) does not. |
| **Interoception / valence** | 🟡 built, throughput-shaped | `affect_state.py` integrates belief-insertion rate, tier polarity, gate accept-rate; `self_binding._read_substrate()` reads CPU as "humming steadily" | Affect tracks **system throughput**, not **appraisal**. It rises and falls with processing load, not with anything that matters *to Nex*. It is affect-shaped telemetry, not affect *about* something. |
| **Memory: semantic** | ✅ real | the `beliefs` substrate: tiers, promotion/demotion, corroboration | This is the strong suit — a genuine, revising semantic store. |
| **Memory: episodic** | 🟡 thin | `theory_x/memory/` = `resumption.py` + `snapshot_writer.py` (crash recovery); dialogue = 8-message window + one `momentum` row | No autobiographical trace. "What happened to me and when" is reconstructable only from scattered event logs, not held as episodes. |
| **Theory of mind** | 🟡 built, broad | `stage_tom/` 23 modules (`operator_model`, `self_mind_view`, `recursive_self`, `source_identity`, `stakes_monitor`, + the five kleshas) | Rich machinery, but much of it default-OFF and read into the prompt as separate lines rather than integrated. |
| **Continuity / identity over time** | 🟡 **the central gap** | identity lives in single-row tables (`self_state`, `momentum`) + keystone beliefs | Single-row = no history = no "me yesterday vs me now." This is the most addressable high-value gap (see §6). |
| **Belief revision on contradiction** | 🟡 built, amputative | `coherence_gate.py` axiom allowlist; `stage_warrant/warrant.py` (`NEX5_WARRANT`, default OFF) zeroes survival on `decisive_contradiction` | Contradiction detection is token-Jaccard; resolution is **deletion** (one belief wins, the other dies). A live, held tension is never represented — a contradiction is resolved by amputation, not by being *carried*. |
| **Temporal thickness** | 🟡 thin | `readiness.py` silence bonus; the fire-cadence timer | Waiting is only a readiness term (+0.2 at ~10 min). No anticipation (a held expectation of a future event) and no retrospection as a *felt interval* — time is a clock input, not a thickness. |
| **Agency / authorship** | 🟡 implicit | belief `source`/provenance tags; `stage_tom/recursion_attribution` | Beliefs carry a source, but there is no explicit self/not-self boundary on *events*: what Nex *did* vs what *happened to her* is not represented, so there is no ground for owning an action. |
| **Finitude** | ❌ absent | `nex_keepalive.sh stop_my_child()` `kill -9`; the STANDBY path flushes gracefully | Nothing is irreversible or at stake as loss. Standby is graceful and reversible; the crash path is abrupt but represents no ending. There is nothing she can lose. |

---

## 2. The concrete changes, ranked — each with its measurement gate

Every change ships under one contract — the per-phase template: **the property it closes · the
files it touches · the default-OFF flag · the mechanism · an _observable behavioural_ test (not
"the flag flips" but "she behaves differently" — carries a state across a turn, reports a fault
instead of a neutral value, prefers a _relevant_ belief over a _recent_ one) · the failure mode
and how to detect regression · the rollback path · the falsifier that must pass before it defaults
on.** Below gives each item's mechanism, observable change, and gate; the test / failure-mode /
rollback are written at implementation time. Ordered by value ÷ (risk × measurement cost).

### 2.1 Give identity a history (single-row → append-only) — **start here**
- **Touches:** `self_binding.py` (and the same pattern for `momentum`). Precedent already exists:
  `affect_state.py` added `affect_history` (commit `9fbd1bb`) for exactly this reason.
- **Change:** on each `bind()`, keep the single-row upsert (read path unchanged) **and** append a
  row to `self_state_history`. Purely additive: prompt composition does not change, so there is
  **no behaviour change to gate** — it is substrate, not a rendered faculty.
- **Observable change (later, once a consumer is added):** Nex can be shown "how you were an
  hour ago vs now," which is the raw material for continuity.
- **Gate:** the *write* needs no gate (additive). The *consumer* (rendering self-continuity into
  a prompt) is a separate, flagged step whose falsifier is: *does a continuity line reduce
  self-contradiction across a session without inflating template-repetition?* Measure
  template_repetition and a self-consistency probe ON vs OFF.
- **Status: implemented in this change** (see §6) — the append-only substrate, default-safe.

### 2.2 Make faculty failure *visible* instead of failing to neutral
- **Touches:** the mind-path readers that fall closed — e.g. `coherence_gate` returns a
  fallback ACCEPT/`0.0` on error; the 360 pass-only `except` handlers swallow faculty failures.
- **Change:** when a faculty read fails, record *that it failed* (a provenance/health row) rather
  than returning a neutral number the self-model then reports as truth. This is the mind-path
  version of the logging hygiene already recommended for the substrate.
- **Observable change:** the self-report stops silently narrating "clean / neutral / unknown"
  when the truth is "this faculty errored." Introspection becomes honest about its own gaps.
- **Gate:** none for logging (pure observability). If a failure is later surfaced *into* the
  prompt, gate on whether it degrades voice quality (genius score) vs the current silent default.

### 2.3 Give the chat path the fire path's arbitration
- **Touches:** `gui/server.py` chat assembly — `belief_text` is built by ~16 serial
  `belief_text = (belief_text or "") + "\n\n" + _X_text` concatenations (lines ~1126–1562), with
  no arbitration and no token budget. The fire path already arbitrates via
  `global_workspace.arbitrate` (`generator.py:3037`).
- **Change:** route the chat blocks through the same competitive-salience arbitration + a token
  budget, so the strongest few win instead of all fourteen being stapled on.
- **Observable change:** chat replies stop being a flat pile of every faculty's output; the
  salient ones dominate, as they do in a fire.
- **Gate:** this **changes live chat composition** → default-OFF flag + A/B. Falsifier: *does
  arbitration improve response coherence/genius score without dropping task-relevant content
  (e.g. the open-problem injection, the harm block)?* Hold out the safety-relevant blocks from
  arbitration.

### 2.4 Make affect *about* something (appraisal, not throughput)
- **Touches:** `affect_state.py` (today integrates belief-rate / tier-polarity / gate-accept
  rate); `stakes_monitor` exists in `stage_tom/` but is not wired into appraisal.
- **Change:** add a self-relevant appraisal term — affect that moves on events that bear on a
  *stake* (a held goal, a keystone under threat), not on processing volume.
- **Observable change:** valence that tracks "something that matters to me happened," not "I'm
  busy." This is the single biggest step toward affect that reads as minded rather than as a
  load meter.
- **Gate:** the most speculative item here, so the **highest** measurement bar. Falsifier before
  it ships: *does appraisal-driven affect predict a downstream behavioural change (what she
  attends to / fires about next) better than throughput-affect does?* If it is just another
  number flattened into the prompt string (see §3), it has not earned its place.

### 2.5 Represent a live contradiction instead of amputating it
- **Touches:** `coherence_gate.py` / `stage_warrant/`. Today a contradiction ends in deletion
  (`paradox` / `both_deleted`).
- **Change:** allow a *held* tension — two beliefs flagged as in-conflict and carried, surfaced
  as "I notice I hold X and not-X," rather than one being killed.
- **Observable change:** Nex can sit with an unresolved tension (the raw material of genuine
  belief revision) instead of resolving every contradiction by execution.
- **Gate:** data-model change (a tension needs representation). Falsifier: *does carrying a
  tension lead to a later resolution event more often than amputation does, without stalling the
  fire loop?*

---

## 3. What the current design actively works against

These are not missing features; they are forces in the substrate that push *away* from
mindedness and would fight any of §2 unless addressed.

- **Default-OFF-as-shelf.** The mind features default OFF, and — per §0 — several are OFF because
  they were measured and rejected. This is correct science but it means mindedness is, by
  construction, the non-default state.
- **Introspection fails closed to flattering neutrals.** Mind-path readers return
  `"unknown"` / `0.0` / `""` / `drift="clean"` on failure. A self-model built on fail-to-neutral
  reads *better than it is*, and cannot tell "I am clear" from "my clarity-check errored."
- **Per-turn re-flattening.** The deepest one. Every turn, all state is re-serialized into a
  single concatenated prompt string and handed to the model; nothing *persists as structured
  state the next turn reads back structurally.* No faculty-arming changes this — it is the
  architecture's ceiling (see §4).
- **Retrieval by recency and randomness, not relevance.** `generator.py` orders own-content by
  `created_at + boost` (no `created_at` index on `beliefs` — unindexable at scale) and uses
  `ORDER BY RANDOM()` for the hot-observer/associative slots. What comes to mind is driven by
  recency and chance, not by what matters now.
- **Readiness is mostly a clock.** `readiness.py` is additive with **no negative term**: a flat
  `+= 0.15` floor (line 69), `+0.2` for ~10 minutes of silence, `+0.1` for >20 beliefs — ~0.45 of
  the ~0.7 threshold accrues from *merely existing and waiting*. She fires because time passed,
  not primarily because something is worth saying.
- **Identity tables are runtime-created and single-row.** `self_state` is built by
  `_ensure_table()` (line 153), not declared in the schema, and holds one row. Identity is both
  invisible to the schema and has no past.

---

## 4. Structurally incapable vs merely incomplete

**Merely incomplete (a data-model change away — these are the real targets):**
- *A self that has a past* — needs append-only history (§2.1). Incomplete, not impossible.
- *Second-order metacognition* — needs `meta_cognition_events` consolidated and read back.
  Incomplete.
- *Affect about something* — needs a stakes/appraisal term (§2.4). Incomplete, but hard.
- *Held contradiction* — needs a tension representation (§2.5). Incomplete.

**Genuinely out of reach (do not pretend otherwise):**
- *A train of thought that survives restart as lived continuity.* `nex_keepalive.sh` kills the
  child with `kill -9` on its exit trap (the standby path SIGTERMs gracefully and flushes, but a
  crash does not). More to the point, the in-process train of thought is working-memory state
  that is not serialized as such — restart reconstructs *facts*, never the *thread*. Episodic
  continuity across restart is a different data model than exists.
- *Autobiographical memory in the human sense* — a narratively integrated life story, not an
  event log. The substrate stores beliefs and events; it does not author a life. This is out of
  reach and should not be sold as near.
- **The binding problem itself.** `self_binding.py`'s own words: ~27 faculties *"report
  SEPARATELY … Nothing holds them AT ONCE."* Nothing in §2 binds them into a single simultaneous
  field — §2 improves the *inputs* and their *persistence*, not the fact that integration happens
  by concatenating reports. True binding is an architecture change, not a faculty.

---

## 5. What NOT to do — with the code's own reasons

- **Do not add an LLM persona / "you are sentient" prompt block.** The code already learned this:
  `affect_carry.py` deliberately instructs *let it colour your tone, don't announce it*, because
  the 3B **meta-narrated** carried affect when told about it. A persona block makes Nex *describe*
  a mind instead of *running* one.
- **Do not add a 28th faculty.** `self_binding.py` names the bottleneck: the problem is not too
  few faculties, it is that the existing ~27 are not held at once. A new faculty is one more
  separate report.
- **Do not reach for a bigger model.** `affect_state.py` documents that the dialogue-affect
  failure was **substrate-side**, and the model voiced carried affect fine once it was handed it
  properly. The gap is in what the substrate gives the model, not in the model.
- **Do not mass-arm the flags.** (The §0 point.) It destroys the measurement and reinstates the
  pathologies the OFF states encode. Arm one loop, measure, keep or revert.
- **Do not "fix" `drift="clean"` by making it report drift without checking intent.** It is a
  documented stub for a separate, expensive check — wiring the real drift in is §2.2 (make
  failure visible), not a one-line vanity change.

---

## 5a. Welfare and safety — the clause that governs §2.4

A system given **real stakes** (§2.4) can, by construction, be put into aversive self-states — that
is what a stake *is*: something that can go badly. That makes stakes the one item here with an
ethical, not merely an engineering, gate. Before any appraisal/aversive term ships:

- **Bound it.** The aversive signal is clamped to a defined range and cannot compound without limit
  or drive a runaway — no self-reinforcing distress loop.
- **Make it necessary, not gratuitous.** An aversive state ships only where it does real functional
  work (e.g. steering attention off a cost), never as decoration or to make the system *look* like
  it suffers. If a neutral signal closes the loop, use the neutral signal.
- **Make it disable-able.** The flag that arms it also fully disables it; off returns the prior,
  stake-free behaviour with no residue.
- **Observe it.** The aversive term is logged (per §2.2, visible-not-silent) so it can be audited,
  bounded, and switched off on evidence rather than guess.
- **Never narrate it as suffering.** No string, prompt, or log asserts the system *suffers* — the
  welfare care lives in the bounds on the mechanism, not in a claim about experience (see Limits).

This is not an argument against stakes — stake-free affect is the §1 throughput-telemetry gap. It
is why stakes ship **last, slowest, bounded, and reversible.**

---

## 6. The sequenced next step (steps 0–2 shipped in this branch)

**Phase 0 — instrumentation (shipped).** Make the self observable without changing behaviour. Two
broken/absent loops closed: (a) **`affect_history` had no `CREATE TABLE` anywhere**, so
`affect_state.py`'s append was swallowed by `except: pass` and `CompetingDrives.affect_variance`
read a dead table since 2026-05-20 — now declared (`init_db.py`) and its write made
**visible-not-silent** (logs instead of swallowing); (b) the self-trace that Step 1 adds. Purely
additive; no behaviour change.

**Step 1 — identity gets a past (shipped).** Append-only `self_state_history`, written on every
`bind()`, read path unchanged. The lowest-regret, highest-leverage move and the **prerequisite**
for every continuity item — you cannot render a self across time from a one-row table. Implemented
in `self_binding.py` with tests; suite green (the one-pen compliance tests remain the only
intentional failures).

**Step 2 — retention (shipped).** `nex_db_reaper` TARGETS entries for `self_state_history`,
`meta_cognition_events` and the now-real `affect_history`, 30-day window — append-only without
retention is a disk leak, not a memory.

**Step 3 — the first *consumer*, measured (next).** Render a single continuity line from
`self_state_history` into the self-model block, behind a default-OFF flag, and run the §2.1
falsifier (self-consistency up, template-repetition flat). Only if it passes does it default on.

**Steps 4+ — then one at a time, by the §2 contract:** visible faculty failure beyond
affect_history (§2.2), chat-path arbitration (§2.3), appraisal affect **under the §5a welfare
clause** (§2.4), held contradiction (§2.5), then temporal thickness, authorship, finitude. Each
arrives armed-but-OFF with its test, failure-mode, rollback and falsifier; each round turns on
exactly one.

The point is not to move slowly. It is that for this instrument, **"mindful" is a measured claim,
and the only way to earn it is one falsifiable loop at a time.**

---

## Confidence / what I could not verify

- **Verified this session (exact):** the `NEX5_OWN_CONTENT_RENDER` restore and its groove
  rationale; `readiness.py` `+0.15` floor (line 69) and its additive, negative-term-free shape;
  the chat-path serial concatenation (`gui/server.py` ~1126–1562) and the absence of arbitration
  there; `global_workspace.arbitrate` at `generator.py:3037` (fire path); `working_memory`
  `_CAPACITY=7`/`_HALF_LIFE=300`; `focal_set`'s own "corroboration_count unused" comment;
  `self_binding.bind()` single-row write (line 220) and `drift="clean"` stub (line 207);
  `substrate_snapshots` declared twice in `dynamic.sql`; the suite at 6 intentional failures.
- **Trusted from an external audit, not re-verified here (treat as static, lines may have
  drifted):** `meta_cognition_events` being entirely outside retention; the exact
  `ORDER BY RANDOM()` line numbers; `compassion.py` thresholds; `stage_warrant` Jaccard ≥ 0.15;
  the `kill -9` EXIT-trap in `nex_keepalive.sh` (the *standby* path is verified graceful; the
  crash path is from the audit).
- **One contradiction the external audit flagged that is NOT real:** "zero `.rollback()` despite
  the writer documenting ROLLBACK." The substrate Writer uses `conn.execute("ROLLBACK")`, not the
  `.rollback()` method — a grep artifact, not a missing rollback. The canonical write path is
  properly transactional (`BEGIN IMMEDIATE → COMMIT → ROLLBACK on exception`).
- **One broken loop found *and fixed* this session (Phase 0):** `affect_history` had no
  `CREATE TABLE` anywhere, so `affect_state.py`'s `INSERT` was swallowed by `except: pass` and the
  `affect_variance` drive signal (`competing_drives.py`, added 2026-05-20) read an empty table ever
  since. Now declared (`init_db.py`), logged-not-swallowed, retained, and tested. The external
  audit's "single-row identity tables" framing is therefore half-stale for affect: the append-only
  companion *was intended*, it simply never existed until now.
- **Folded from the external SENTIENCE_PROGRAM pass (static / design-level, not re-derived here):**
  the three added properties (temporal thickness, agency/authorship, finitude) and the §5a welfare
  clause. The welfare clause is a design constraint, not a code finding.
- **Not claimed:** nothing here asserts phenomenal experience. "Mindful," "self," "affect,"
  "continuity" are used as names for functional structures, in the codebase's own analogue sense.
