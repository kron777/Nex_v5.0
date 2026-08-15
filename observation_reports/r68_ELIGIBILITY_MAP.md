# NEX5 — R68: eligibility map for in-window work (read-only)

**Not a pre-registered round.** A read-only survey to decide what can safely be built
while the corpus accrues toward the Aug 18 stability test. **No fixes proposed here.**

**Date:** 2026-08-15 11:35 UTC · **Report only. No code, no refit, no file edits.**

---

## 0. TEST PROTECTION — checked first

| | |
|---|---|
| clean corpus (`fountain_insight`, `≥ 2026-08-09`) | **525 documents** |
| 08-15 partial | 43 in 11.6 h = **89/day**, on trend |
| measured accrual (6 full days) | **80.3/day** |
| **fire path unchanged since R57** | `git log 2e7157e..HEAD` over crystallizer / generator / competing_drives / groove → **empty** |
| **working tree clean on all four** | `git status --porcelain` on those paths → **empty** |
| fountain | alive, pid 1657, 22 h uptime |

**Schedule holds:**

| target | shortfall | at 80.3/day | ETA |
|---|---|---|---|
| 700 (brief's figure) | 175 | 2.2 d | **~2026-08-17 15:00 UTC** |
| **800 (R67 recommended)** | 275 | 3.4 d | **~2026-08-18 20:00 UTC** |

**None of the three items below requires touching any of the four fire-path files.**
Confirmed by static import closure (below), not by inspection alone.

### The instrument used for all three rulings

A static import closure was computed from the four fire-path files (recursive, following
both `import` and `from … import`, module-level and function-local). **The closure is 50
modules.** Membership in it is the eligibility test used throughout.

---

## 1. EXTRACTION BUG — `CoOccurrenceDetector`

### Where it actually is — the note's line number is stale

| | |
|---|---|
| file | `theory_x/signals/detectors.py` |
| class | **line 29** |
| **extraction regex** | **line 62** — note said "~line 49" |
| entity added | line 67 |
| context captured | lines 68–70 |
| context emitted | line 92 |

The drift is explained: `af104f5` (2026-07-22, census #13 fix) inserted ~13 lines of
de-duplication state into `__init__`, pushing the extraction point down.

### The current code

```python
for m in re.finditer(r"\b[A-Z][a-zA-Z]{2,}\b", content):      # line 62
    w = m.group()
    if w.lower() in _ENTITY_STOPWORDS:
        continue
    start = m.start()
    branch_entities[branch].add(w)                             # line 67
    snippet = content[max(0, start - 40):start + len(w) + 40].strip()
    if len(entity_contexts[w]) < 3:
        entity_contexts[w].append(snippet)
```

### Is it still the shape described? — **PARTLY. One clause of the note is now false.**

**Still true:** the regex grabs **bare single capitalized words**. `branch_entities.add(w)`
stores one token; the emitted `Signal` carries `entities=[entity]`. Multi-word entities
("Digital Signal Processing", a person's full name) are fragmented into separate
single-token entities. **That is intact and is the surviving part of the root cause.**

**No longer true: "discards surrounding context at extraction."** Context capture exists —
±40 characters around each hit, up to 3 per entity, propagated into the signal payload as
`"contexts"` (line 92). It was added by **`b0a4051` (2026-07-08) "Carry source context
through CoOccurrence entity extraction"**, which post-dates the note.

**So the note describes a two-part defect of which one part was already fixed in July.**
Whether downstream consumers *use* `contexts` is a separate question this survey did not
open.

### Is it outside the fire path? — **YES**

| | |
|---|---|
| `theory_x/signals/detectors.py` in the 50-module closure | **NO** |
| any `theory_x/signals` module in the closure | **NONE** |
| does the signal path write `fountain_insight` beliefs | **NO** — grep for `fountain_insight` across `theory_x/signals/` returns nothing; it only *reads* `precipitated_from_sense` |

Consumers are `signals/loop.py`, `signals/__init__.py`, `run.py:603`
(`build_signal_loop`, at startup), `signals/templates.py`, and tests.

**The one caveat that matters:** `run.py` imports it at process start, so an edit is
**inert until a restart** — the staged-inactive pattern the ledger already uses (R40,
R53). **The restart is the risk, not the edit.** A restart would reset in-memory
fingerprint state in `groove.py` and `detectors.py` (both reset by design), which
perturbs crystallization briefly and would put a discontinuity inside the accrual window.

### → **ELIGIBLE THIS WINDOW — as a staged-inactive edit only. No restart before the test.**

---

## 2. SOURCE-ATTRIBUTION EROSION

### The gating question, answered plainly: **YES, it shares modules with the fire path.**

| module | in fire-path closure? | reached via |
|---|---|---|
| **`theory_x/diversity/consolidation.py`** (`ClockRunner`) | **IN CLOSURE** | `generator.py:1468` → `diversity/loop.py:29` |
| **`theory_x/diversity/lineage.py`** (`record_synergy`) | **IN CLOSURE** | `diversity/loop.py:69`; also the synergizer's own write path |
| **`theory_x/diversity/grader.py`** | **IN CLOSURE** | `diversity/loop.py:26` |
| **`theory_x/diversity/dormancy.py`** | **IN CLOSURE** | `diversity/loop.py:28` |
| **`theory_x/stage_gate/coherence_gate.py`** | **IN CLOSURE** | `crystallizer.py:341` |
| `theory_x/stage2_dynamic/consolidation.py` | not in closure | — |
| `theory_x/stage3_world_model/synergizer.py` | not in closure | — |

`readiness.py` (in closure, imported by `generator.py:257`) also reads
`consolidation_active` at line 78 — so consolidation **state** feeds fountain readiness,
a second coupling independent of the import graph.

### → **INELIGIBLE. PARK UNTIL AFTER THE AUG 18 TEST.**

Per the brief's own rule. The consolidation path is entangled with the fire path at four
distinct modules plus a state read.

### One thing found while tracing, which matters for later sequencing

**The mechanism in the July note is not reproduced.** The obvious candidate is the
synergizer, whose prompt structurally discards attribution:

```
I hold two thoughts at once:
"{belief_a}"
"{belief_b}"
In one sentence, what new insight do I notice?
```

First-person reframing, no instruction to preserve source. Output is duly unattributed —
*"Noticing that…"*, *"The realization that…"*. **But it never sees attributed input:**

| synergizer pairs since 08-09 | **346** |
|---|---|
| pairs where **either** input carried `this item` / `the item` / `the feed` | **0** |
| fresh-slot inputs drawn from `fountain_insight` | **17** (4.9%) |
| fresh-slot inputs drawn from **`synergized`** | **338 (97.7%)** |

**97.7% of syntheses pair an anchor with another *synergized* belief** — the closed loop
the file's own comment (lines ~120–126) warns about. Attributed fountain beliefs
(~26% of the clean corpus carry `this item`/`the item`) essentially never enter the
synthesis path at all.

**So this dev needs a root-cause round before a fix round, even once it is unparked** —
the described flattening is not happening where the note says, because the input never
arrives.

---

## 3. REPO HYGIENE

### Still outstanding

**16 `.bak*` files, dated 2026-07-05 → 07-09**, all untracked and gitignored (which is
why `git status` has never shown them):

```
run.py.bak_persona                                    30,267
theory_x/stage6_fountain/generator.py.bak_workspace  133,724
theory_x/stage6_fountain/generator.py.bak_gwdebug    134,845
theory_x/signals/signal_to_problem.py.bak             16,835
theory_x/signals/signal_to_problem.py.bak2            18,631
theory_x/signals/signal_to_problem.py.bak_burstgate   12,999
theory_x/signals/signal_to_problem.py.bak_singleword  14,534
theory_x/signals/signal_to_problem.py.bak_countrylist 15,067
theory_x/signals/signal_to_problem.py.bak_posgate     15,208
theory_x/signals/detectors.py.bak                      5,879
theory_x/signals/prose_stats.py.bak                    6,402
theory_x/life/affinity_loop.py.bak                     6,141
theory_x/life/affinity_loop.py.bak2                    7,105
theory_x/stage_world/self_prediction.py.bak            9,887
theory_x/stage_tom/momentum.py.bak_carrycap            4,403
substrate/writer.py.bak_dupefix                        6,929
```

Two of these corroborate §1's history: **`detectors.py.bak` (07-08)** is the
pre-context-fix copy, and **`signal_to_problem.py.bak_singleword`** is a surviving
artefact of exactly the downstream single-word patching the note describes.

**`rc2/` — 196 MB, untracked, and a nested git repository** (contains its own `.git`).
It is the only thing `git status` reports. It cannot be committed as-is without being
made a submodule or removed.

### Clean

- **0** `__pycache__` paths tracked
- largest tracked files are legitimate: `docs/hero.png` 2.3 MB,
  `docs/nex_v5_banner.png` 2.0 MB, `journal/CARRY_OVER.md` 322 KB

### → **ELIGIBLE THIS WINDOW — safe and corpus-neutral.**

Every item is untracked or ignored; removing them imports no module, touches no
fire-path file, and requires no restart.

---

## Eligibility summary

| # | item | ruling |
|---|---|---|
| 1 | `detectors.py` single-token extraction | **ELIGIBLE — staged-inactive edit only, no restart before the test** |
| 2 | source-attribution erosion | **PARK UNTIL AFTER THE TEST** — shares 4 closure modules + a state read with the fire path |
| 3 | repo hygiene | **ELIGIBLE — safe, corpus-neutral** |

**Two corrections to the standing notes, recorded so they are not re-inherited:**
§1's "discards surrounding context" was fixed on 2026-07-08 and the line number moved
49 → 62; §2's flattening mechanism is not reproduced at the synergizer, which sees
attributed input in **0 of 346** pairs.

**No fixes proposed. Sequencing is the next decision.**
