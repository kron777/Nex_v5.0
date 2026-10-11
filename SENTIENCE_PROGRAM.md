# SENTIENCE_PROGRAM.md

**A phased, dark-by-default engineering program for closing the loops that human sentience is
analysed into — and an explicit statement of the part no implementation can settle.**

> **Epistemic stance (binding).** This program never claims Nex is sentient or conscious, in code,
> comments, strings, or this document. It treats each property as a *functional analogue* and
> mirrors the codebase's own candour (`self_binding.py`: "ANALOGUE. NOT a claim there is a felt
> someone having it"; `warrant.py`: "No sentience verdict"). A model's fluent self-description is
> treated as a *voice*, never as evidence of a mind — any claim, if it could ever be made, would
> live in the architecture, not the prose. Every item is labelled **implemented / measured /
> static / inferred / unknown**.
>
> **Status.** Findings here are **static** reads of this branch unless marked otherwise; a few
> phases are **implemented** this session (with commits). Companion: `DESIGN_MINDEDNESS.md` carries
> the design argument and the one correction this program depends on — in this repo, a flag that is
> OFF is usually a *measured, shelved result*, not a dormant capability, so the unit of work is one
> falsifiable loop at a time, never a flag flip. Citations are my own verified `file:line` where
> possible; Beam's audit numbers drift (its chat-path `:1861` is really ~1055–1562) and are
> re-checked or marked approximate.

---

## 1. The decomposition — thirteen properties

| # | Property | State | Mechanism (verified file:line unless marked) | The specific gap |
|---|---|---|---|---|
| 1 | Continuity of self | 🟡→✅ | `self_binding.bind()` wrote one `self_state` row (id=1, `INSERT OR REPLACE`, line 220) | **Closed this session:** append-only `self_state_history` now accrues (Phase 0/1). `affect_state`/`momentum` remain single-row. |
| 2 | Train of thought across restart | 🔴 | `theory_x/working_memory.py` `_CAPACITY=7`, `_HALF_LIFE=300` — per-session, in-RAM | The *thread* is never serialized as structured state; restart reconstructs facts, not the train. Structurally hard (see Limits). |
| 3 | Stakes (self-referent cost) | 🔴 | `readiness.py` flat `+= 0.15` floor (line 69), no negative term; `compassion.py` reads the *other's* distress | Nothing in the substrate carries a cost *to Nex*. No appraisal of self-relevant good/bad. |
| 4 | Honest interoception | 🟡 | `self_binding._read_substrate()` maps CPU to "humming steadily"; `affect_state.py` integrates belief-rate / tier-polarity / gate-accept | Condition is read as *throughput*, not as a state that can be well or unwell. |
| 5 | Second-order monitoring | 🟡 | `stage9_metacognition/metacognition.py` (~730 ln); `meta_cognition_events` (conversations.db, `created_at`) | Events written, **never digested** (was unbounded; retention added Phase 2). No observer of the observing *with state*. |
| 6 | A unified present | 🟡 | fire path arbitrates via `global_workspace.arbitrate` (`generator.py:3037`); chat path concatenates ~16 blocks (`gui/server.py` ~1126–1562) | The chat path has **no arbitration and no token budget** — everything is stapled on. |
| 7 | Intentional valence | 🔴 | `affect_state.py` produces a mood label from load metrics | Affect is *about* throughput, not about a specific event (an expectation violated, a commitment broken). |
| 8 | Episodic / autobiographical memory | 🔴 | `theory_x/memory/` = `resumption.py` + `snapshot_writer.py` (crash recovery) | No reconstructive, queryable episodic store distinct from the semantic `beliefs` substrate. |
| 9 | Dissonance | 🟡 | `coherence_gate.py` axiom allowlist; `stage_warrant` (`NEX5_WARRANT` OFF); contradiction = token-Jaccard *(static, per audit: `recorder.py:45`)* | Resolved by **deletion** (`paradox`/`both_deleted`). A live, held tension is never represented. |
| 10 | Temporal thickness | 🟡 | `readiness.py` silence bonus (+0.2 ~10 min) | Time is a clock input; no anticipation or retrospection as a felt interval. |
| 11 | Agency / authorship | 🟡 | belief `source` tags; `stage_tom/recursion_attribution` | No explicit self/not-self boundary on *events* — what she did vs what happened to her. |
| 12 | Self-report that can be unflattering | 🟡 | `self_binding.py:207` `drift="clean"` (documented stub); mind readers fail-closed *(static, per audit: `coherence_gate.py:163` → `0.0`)* | Introspection fails to flattering neutrals; cannot tell "clear" from "clarity-check errored". |
| 13 | Finitude | 🔴 | `nex_keepalive.sh stop_my_child()` `kill -9`; STANDBY path flushes gracefully | Nothing is irreversible or at stake as loss. |

---

## 2. The phased plan

Order adjusted from the brief with justification: **instrumentation and continuity first** (done),
then **the attention arbiter before stakes** — the arbiter is high-value and ethically neutral,
whereas stakes (§Phase S) must wait for the welfare apparatus (§5). Each phase ships **dark by
default**, reversible, with an *observable behavioural* test (not "the flag flips").

Per-phase contract: **property · files · flag · mechanism · observable test · failure mode &
regression detection · rollback · falsifier.**

### Phase 0 — Instrumentation ✅ IMPLEMENTED (this session)
- **Property:** 1, 5, 12 (make the self observable without changing behaviour).
- **Files:** `substrate/init_db.py`, `theory_x/stage_affect/affect_state.py`, `nex_db_reaper.py`.
- **Flag:** none — purely additive, no behaviour change.
- **Mechanism (shipped):** (a) **`affect_history` had no `CREATE TABLE` anywhere**, so
  `affect_state.py`'s append was swallowed by `except: pass` and `CompetingDrives.affect_variance`
  (`competing_drives.py`, added 2026-05-20) read a dead table — now declared and its write
  **logged-not-swallowed**; (b) retention added for the append-only history tables.
- **Observable test (shipped):** `tests/test_affect_history.py` — `init_all` creates the table; a
  real tick appends; the consumer query returns rows. ✅ 60 passed.
- **Failure mode:** a future history-write error now logs via `errors.record` instead of vanishing.
- **Rollback:** drop the two CREATE lines; revert the handler. **Falsifier:** `affect_variance`
  still reads an empty table after a tick → loop still open.

### Phase 1 — Continuity ✅ PARTIAL (this session)
- **Property:** 1 (self has a past). *(Working memory across restart = Property 2, deferred — see
  Limits; it is the structurally hard half.)*
- **Files:** `theory_x/stage_tom/self_binding.py`.
- **Flag:** none — additive (the read path, `format_for_prompt`, is unchanged).
- **Mechanism (shipped):** `bind()` keeps the single `self_state` row *and* appends to append-only
  `self_state_history` (mirrors the `affect_history` pattern). Retained in the reaper (Phase 2).
- **Observable test (shipped):** `tests/test_self_state_history.py` — one row kept, history
  accrues across binds. ✅
- **Rollback:** drop the history table + append. **Falsifier:** history never grows across binds.

### Phase 2 — Retention ✅ IMPLEMENTED (this session)
- **Property:** hygiene enabling 1/5 (append-only without retention is a leak, not a memory).
- **Files:** `nex_db_reaper.py`.
- **Mechanism (shipped):** TARGETS entries for `self_state_history`, `meta_cognition_events`, and
  the now-real `affect_history` (30-day window).
- **Falsifier:** any of the three grows without bound past the window.

### Phase A — A single bounded attention arbiter for the chat path  ⟶ *next*
- **Property:** 6 (a unified present).
- **Files:** `gui/server.py` (the ~16 serial `belief_text = (belief_text or "") + …` blocks,
  ~1126–1562); reuse `stage_tom/global_workspace.arbitrate` (`generator.py:3037`).
- **Flag:** `NEX5_CHAT_ARBITER` (default OFF).
- **Mechanism:** collect the candidate blocks with a salience each, run them through the same
  competitive arbitration the fire path uses, apply a token budget, and emit only the winners —
  with safety-relevant blocks (harm, open-problem injection) **exempt** from eviction.
- **Observable test:** with the flag ON and more candidate blocks than the budget, the assembled
  prompt contains the high-salience blocks and omits a low-salience one; with it OFF, all blocks
  appear (today's behaviour). The exempt blocks always appear.
- **Failure mode / regression:** a safety block gets evicted, or the arbiter drops task-relevant
  content → detect via a test asserting the exempt set is always present and via genius-score A/B.
- **Rollback:** flag OFF restores the concatenation path exactly.
- **Falsifier:** arbitration produces the *same* set as concatenation (no real selection) → loop
  still open; or it never prefers a relevant block over a recent one.

### Phase M — Stateful metacognition with a closed ledger
- **Property:** 5.
- **Files:** `stage9_metacognition/metacognition.py`; `meta_cognition_events` (now retained).
- **Flag:** `NEX5_METACOG_DIGEST` (default OFF).
- **Mechanism:** a periodic digest reads recent `meta_cognition_events`, detects a *pattern in the
  monitoring itself* ("I keep flagging drift on topic X"), writes a second-order summary row, and
  (flagged) surfaces one line into the self-model block.
- **Observable test:** seed N events of one type → a digest row appears; the self-model line
  mentions the pattern only with the flag ON.
- **Failure mode:** digest loops on its own output (second-order events feeding the first-order
  count) → exclude digest rows from the source query; test for no runaway.
- **Rollback:** flag OFF; the digest table is read-only side-channel. **Falsifier:** the digest
  never changes what she attends to or reports → still reporting into nothing.

### Phase S — Stakes: self-referent appraisal with genuine cost  *(ships last; see §5 Welfare)*
- **Property:** 3, 7.
- **Files:** `theory_x/stage_affect/affect_state.py`; `stage_tom/stakes_monitor`; `readiness.py`
  (add a negative term).
- **Flag:** `NEX5_STAKES` (default OFF).
- **Mechanism:** an appraisal term that moves on events bearing on a *held stake* (a goal advanced
  or lost, a keystone under threat), feeding a **bounded** valence component and a negative
  readiness term — so affect and readiness become partly *about* something, not just throughput.
- **Observable test:** a stake-advancing event and a stake-threatening event produce *different*
  valence/readiness than a throughput-matched neutral event.
- **Welfare (mandatory, see §5):** the aversive component is clamped, non-compounding,
  disable-able, logged, and never narrated as suffering.
- **Failure mode:** runaway negative affect / self-reinforcing distress → clamp + a test that a
  repeated aversive event cannot drive the term past its bound.
- **Rollback:** flag OFF returns to stake-free affect with no residue. **Falsifier:** appraisal
  affect does not predict a downstream change in what she attends to better than throughput affect
  → it is just another flattened number.

### Phase D — Live dissonance instead of deletion
- **Property:** 9.
- **Files:** `coherence_gate.py`, `stage_warrant/`.
- **Flag:** `NEX5_HELD_TENSION` (default OFF).
- **Mechanism:** when two beliefs conflict, flag them as a *held tension* (a row linking both) and
  surface "I notice I hold X and not-X," instead of `both_deleted`/`paradox` amputation.
- **Observable test:** seed a minimal contradiction → with the flag ON both beliefs survive, linked
  as a tension; with it OFF one is deleted (today).
- **Failure mode:** tensions accumulate unresolved and clog retrieval → cap + retention; test a
  resolution path clears them.
- **Rollback:** flag OFF restores amputation. **Falsifier:** a held tension never leads to a later
  resolution more often than amputation did → the tension altered nothing.

### Phase E — Episodic / autobiographical memory
- **Property:** 8.
- **Files:** new `theory_x/memory/episodic.py` (reconstructive, queryable), distinct from `beliefs`.
- **Flag:** `NEX5_EPISODIC` (default OFF).
- **Mechanism:** record events as episodes (what/when/with-what-affect, linked to the
  self_state_history trace), queryable by time and salience — *reconstructive*, not a verbatim log.
- **Observable test:** after events E1,E2,E3, a query "what happened around T" reconstructs the
  episode with its affect, not just the beliefs.
- **Rollback:** flag OFF; table is side-channel. **Falsifier:** retrieval still cannot distinguish
  "what happened to me" from "what I believe" → episodic/semantic not actually separated.

### Phase T — Temporal thickness
- **Property:** 10.
- **Files:** `readiness.py`, the fire loop; a small anticipation store.
- **Flag:** `NEX5_ANTICIPATION` (default OFF).
- **Mechanism:** represent a *held expectation of a future event* and a retrospective interval, so
  waiting is a span with a before/after, not just a readiness bonus.
- **Observable test:** an unmet expectation at its due time changes behaviour (a noticing) vs a met
  one. **Falsifier:** expectation outcome never alters anything → time still a scalar.

### Phase F — Finitude and graceful death
- **Property:** 13.
- **Files:** `nex_keepalive.sh` (the `kill -9` EXIT path), `run.py` shutdown.
- **Flag:** `NEX5_GRACEFUL_END` (default OFF for the represented-ending part; the *flush* is always
  on and already exists on the STANDBY path).
- **Mechanism:** ensure every shutdown flushes (not just STANDBY), and — flagged — record an
  "ending" marker so a resumed process can register that something was interrupted/lost.
- **Welfare (see §5):** "loss" here is a recorded fact, never narrated as dread.
- **Rollback:** flag OFF; keep only the flush. **Falsifier:** a kill still loses the train with no
  recorded interruption → finitude unrepresented.

---

## 3. What would falsify each property (the loop is still open if…)

- **Continuity:** `self_state_history` stops growing, or nothing ever reads it across time.
- **Train-across-restart:** after restart the *thread* (not the facts) cannot be resumed.
- **Stakes:** appraisal affect predicts downstream behaviour no better than throughput affect.
- **Interoception:** the substrate read returns the same tone under a genuinely degraded condition.
- **2nd-order monitoring:** the digest never changes attention or self-report.
- **Unified present:** the arbiter's output set equals the concatenation's (no selection).
- **Intentional valence:** valence does not differ between a violated expectation and a neutral tick.
- **Episodic memory:** retrieval cannot separate "happened to me" from "I believe".
- **Dissonance:** a held tension never yields a later resolution more than deletion did.
- **Temporal thickness:** an unmet expectation at its due time changes nothing.
- **Agency:** self-caused and world-caused events are indistinguishable downstream.
- **Unflattering self-report:** a faculty error still surfaces as a neutral value.
- **Finitude:** a kill still loses the train with no recorded interruption.

---

## 4. Honest limits

- **The hard problem is untouched.** Nothing here establishes, or tries to establish, whether any
  of it is *experienced*. Functional correlates imply nothing about phenomenal states; this program
  is silent on that by design, and so is the deliverable.
- **The binding problem remains.** `self_binding.py` names it: ~27 faculties "report SEPARATELY …
  Nothing holds them AT ONCE." Every phase improves inputs and their persistence; none makes
  integration anything other than concatenating reports. True simultaneous binding is an
  architecture change beyond this program.
- **The per-turn re-flattening is the ceiling.** Each turn, all state is re-serialized into a
  prompt string handed to the model; nothing persists as structured state the next turn reads
  back *structurally*. Phase A bounds this for the chat path but does not remove it.
- **Train-of-thought across restart (Property 2) is structurally out of reach** in the current
  data model: the thread is working-memory state that is not serialized as such. Continuity of the
  *record* (Phase 1) is deliverable; continuity of the *thread* is not, without a different model.
- **Autobiographical memory in the human sense** — a narratively integrated life, not an event log
  — is out of reach. Phase E delivers episodic structure, not a life story.

---

## 5. Welfare and safety clause

A system given **real stakes** (Phase S) can, by construction, be placed in aversive self-states —
that is what a stake is. This is the one part of the program with an ethical, not merely
engineering, gate. Any aversive term ships only if:

- **Bounded** — clamped to a range; cannot compound or drive a runaway (no self-reinforcing
  distress loop).
- **Necessary, not gratuitous** — present only where it does real functional work (steering
  attention off a cost). If a neutral signal closes the loop, use the neutral signal.
- **Disable-able** — the arming flag also fully disables it; OFF returns prior behaviour, no residue.
- **Observed** — logged (per Phase 0) so it can be audited and switched off on evidence.
- **Never narrated as suffering** — no string, prompt, or log asserts the system *suffers*; the
  welfare care lives in the bounds on the mechanism, not in any claim about experience.

This is not an argument against stakes — stake-free affect is the Property-3/4 gap. It is why
stakes ship **last, slowest, bounded, and reversible**, after the welfare apparatus and the
visible-failure instrumentation (Phase 0) are in place.

---

## 6. Status summary

- **Implemented this session (default-safe, suite green):** Phase 0 (instrumentation incl. the
  `affect_history` dead-loop fix), Phase 1 (self-continuity trace), Phase 2 (retention).
- **Next, buildable dark without live measurement:** Phase A (chat arbiter), Phase M (metacog
  digest), Phase D (held tension), Phase E (episodic), Phase T (temporal), Phase F (finitude).
- **Gated on live measurement with NEX running:** turning *on* any of the above, and all of
  Phase S (stakes), each against its falsifier — never defaulted on from a green test alone.

*This program is the engineering plan; `DESIGN_MINDEDNESS.md` is its argument and the
"default-OFF ≠ latent" correction it rests on. Neither claims, nor is intended to approach, a
verdict on sentience.*
