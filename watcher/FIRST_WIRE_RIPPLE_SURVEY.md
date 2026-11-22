# First-wire ripple survey — read-only (wire nothing)

Produced with `watcher ripple` against the real repo, to make the first-wire pick
with ripple-cost **visible, not guessed**. **Repo-proven, live-confirm pending** —
every figure is the static source graph + the test set, not her runtime.

- Survey tree: `main` (= this branch's base); cross-checked against dev head
  `claude/nex-v5-audit-review-53ouqv` where arm-flags matter. Import structure of
  these faculties is identical on both.
- Method: `watcher.ripple.source_dependents(seam)` → direct importers + downstream
  tests; arm status from `nex_keepalive.sh`; frozen check by grep; sequencing from
  `SENTIENCE_PROGRAM.md` vs `SENTIENCE_SYNTHESIS.md`.

## The menu

| Candidate (SENTIENCE phase) | Seam | Ripple (importers / tests / unique) | Size | Dark? | Offline-doable now |
|---|---|---|---|---|---|
| **Chat bounded arbitration** (A — "next") | `gui/server.py` + `stage_tom/global_workspace.py` | 3+5 imp / **23+5 tests** / **35** | **Large** | partial budget armed on main, full arbiter unbuilt | **Yes** (wiring+correctness); quality live |
| **Metacog digest** (M) | `stage9_metacognition/metacognition.py` | 2 imp / 6 tests / 8 | **Small** | yes (`NEX5_METACOG_DIGEST` off) | **Yes** (deterministic digest) |
| **Held-tension** (D) | `stage3_world_model/harmonizer.py` | 2 imp / **12 tests** / 14 | **Medium** | yes (`NEX5_HELD_TENSION`, never armed live) | Mechanism yes; **meaning needs live** |
| **Episodic memory** (E) | `theory_x/memory/episodic.py` | **0 imp** / 2 tests / 2 | **Tiny ripple, but unconsumed** | yes (nothing imports it) | Build consumer offline; **meaning needs live + D** |
| **Continuity record** (Phase 1) | `stage_tom/self_binding.py` | 4 imp / 3 tests / 7 | **Small** | **already implemented** (history accrues); not consumed for decisions | Consumer buildable; **meaning needs live accrual** |

## Per-candidate detail

### Chat bounded arbitration — Phase A (PROGRAM's "next")
- **Ripple into:** `gui.server` (→ `run`, `tools.provenance_harness`, `tools.voice_harness`) and the shared arbiter `global_workspace` (→ **the fire path** `stage6_fountain.generator`, `stage_finitude.budget_shadow`, `forced_tradeoff_harness`). **23 chat tests + 5 arbiter tests.**
- **Landmines (3):** (1) the seam is the **~1000-line `gui/server.py` chat handler** — largest blast radius here; (2) `global_workspace.arbitrate` is a **shared reader with the fire path** — a change there ripples into fountain generation, not just chat; (3) **SYNTHESIS veto-adjacent:** "A and S must never be specified independently — if the arbiter's budget can be widened by the caller, stakes are decorative." Building the arbiter alone risks a decorative budget. (4) Flag confusion: `NEX5_CHAT_WORKSPACE` (budget-trim) is **armed on main** but not the dev head; PROGRAM's Phase A wants a *fuller* competitive arbiter under `NEX5_CHAT_ARBITER` (unbuilt).
- **Sequencing:** PROGRAM = do this next. SYNTHESIS = do **not** do A without S (stakes). Genuine conflict.

### Metacog digest — Phase M
- **Ripple into:** `gui.server`, `run`; 6 tests. **Smallest coupled ripple.** Flag-gated internally (`NEX5_METACOG_DIGEST`), "surfaced only by swapping which line `format_for_prompt()` returns."
- **Landmines:** **self-referential feedback loop** — the digest writes a second-order row back into `meta_cognition_events`, which metacognition also reads (a second-order event can re-trigger). SYNTHESIS: **"Do not build Phase M first"** (metacognition is "inherently lossy and late"; instrumenting it first smuggles the designer's ontology in as what she can notice about herself).
- **Sequencing:** PROGRAM = buildable-dark-now. SYNTHESIS = explicit **don't-do-first**.

### Held-tension — Phase D
- **Ripple into:** `forced_tradeoff_harness`, `stage_warrant.recorder`; **12 world-model tests** (harmonizer is world-model core). When armed, holds contradictory tensions instead of retiring them → feeds `episodic`.
- **Landmines:** heavily-tested world-model core (12 tests); changes the **retire-vs-hold feedback** into episodic; `NEX5_HELD_TENSION` has **never been armed on a live run**.
- **Sequencing:** SYNTHESIS cares about this one — "a persistence mechanism so the tension resurfaces rather than being silently resolved by recency." But **meaning requires live tensions flowing**; offline you can prove it holds, not that holding matters.

### Episodic memory — Phase E
- **Ripple into:** **nothing — 0 importers.** It is fully built but **unconsumed**; wiring it = building a consumer. Its episode production is **gated on `NEX5_HELD_TENSION`** (coupled to D).
- **Landmines:** downstream of held-tension (can't be meaningfully first); unconsumed means the real work is a new reader, not a flag.
- **Sequencing:** after D; meaning needs live.

### Continuity record — Phase 1 (already implemented)
- **Status:** `self_state_history` is **written and accruing** (`self_binding.bind()`), reaped for retention. Its only reader is `episodic` (affect tagging). **Does it inform later decisions? No** — `self_binding`'s importers (`fountain.generator`, `compass`, `recursive_self`, `self_mind_view`) consume the **current** self-state via `bind()`, not the **history** series.
- **Landmine:** `self_binding` is a **shared reader on the fountain decision path** — touch `bind()` and you ripple into the fire path. But adding a *new* history-consumer (read-only of the series) is isolated.
- **Sequencing:** the continuity substrate SYNTHESIS wants already exists; what's missing is a consumer, and that only **matters once history has accrued over a live run**.

## Offline-doable NOW vs live-gated

- **Offline-provable now (wiring + correctness, repo-proven):** Chat arbiter (deterministic: high-salience kept, low omitted, safety blocks exempt) and Metacog digest (deterministic template/count trigger). The ripple tool can show zero/known test-delta on the wire before she's live.
- **Buildable offline, but meaning is live-gated:** Held-tension (needs live tensions), Episodic (needs D + live episodes), Continuity-consumer (needs accrued history). You can build + test the mechanism; you cannot prove it *matters* until she runs.

## The sequencing tension, stated plainly

- **PROGRAM:** chat arbiter (A) next; A/M/D/E all buildable dark.
- **SYNTHESIS:** persistence/CTL first; **don't build M first**; **don't build A independent of S (stakes)**; held-tension's value is its *persistence* of a contradiction, not the hold itself.
- **Smallest, cleanest ripple that is also offline-provable now:** Metacog digest (8 unique, 6 tests) — but SYNTHESIS explicitly vetoes it first.
- **PROGRAM's "next" (chat arbiter):** largest ripple (35 unique, 28 tests), touches the shared fire-path arbiter and the 1000-line chat file, and SYNTHESIS warns it's hollow without stakes.
- **The decision is genuinely Jon + Claude's:** the cheap-ripple pick (M) is the one SYNTHESIS says not to do first; the PROGRAM pick (A) is the expensive one SYNTHESIS says not to do alone. This survey makes that trade visible; it does not resolve it.

*Read-only survey. Nothing wired, no faculty changed, nothing merged, host untouched.
Repo-proven, live-confirm pending.*
