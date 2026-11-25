# NEX v5.0 — Repository Reality Report

> **Historical snapshot — superseded for current branch status.** This report records the earlier audit at fb87e24. For the active host checkout at de93134f34adac07a3a41c2a05b33720510a2bfc, use [NEX_PHASE0_CURRENT_RECONCILIATION_2026-11-25.md](NEX_PHASE0_CURRENT_RECONCILIATION_2026-11-25.md). In particular, the old test baseline and the claim that no Phase 1 change had started are not current.


**Master Roadmap v3.0 Phase 0 — Reality Audit (deliverables M0.1–M0.2)**

- **Branch:** `claude/nex-v5-audit-review-53ouqv`
- **Head at audit:** `fb87e24` (`keepalive: turn on the provenance affinity scorer + frame flag changes`)
- **Method:** every figure below is reproduced from the actual tree with the git /
  shell command shown beside it. No figure is taken from a governing document, a
  prior report, or memory.

---

## 0. Governing-document reconciliation (read this first)

The directive names three governing specifications — the **NEX v5.0 Master
Technical, Research & Commercialization Roadmap v3.0**, **RDO v1.3**, and the
**NEX Integration Watcher v3.0**. **None of the three is resident in this
repository.**

```
$ git grep -il "Master Technical, Research\|Master Roadmap" ; echo "---"
$ find . -iname '*roadmap*' -not -path './.git/*'
# (no roadmap document file)
```

Consequences, handled honestly rather than by fabrication:

1. The repository already uses the term **"Phase 0" in its own, unrelated
   senses** — Theory-X instrumentation (`SENTIENCE_PROGRAM.md` §"Phase 0 —
   Instrumentation"), grounding (`SPECIFICATION.md` §354 "Phase 0 — Grounding"),
   and doctrine (`theory_x/DOCTRINE.md` "Phase 0 — Foundational document"). These
   are **not** the Master Roadmap's "Phase 0: Reality Audit." This report uses the
   Master-Roadmap sense throughout and flags the collision so the two are never
   conflated.
2. The deliverable taxonomy (M0.1–M0.5), the **L0–L4 evidence ladder**, **Gate 0**,
   and **ADR-001** come from the directive, not from a repo-resident spec. Where a
   precise field-level requirement would come from the governing PDF, it is marked
   **UNRESOLVED (governing text not in workspace)** rather than invented.
3. The **v1.3 / v1.4 precedence question remains explicitly unresolved** (carried
   over from the prior RDO review; code paths cite v1.4, the roadmap under review
   is v1.3; neither PDF is in the tree).

**Pre-existing Phase-0 (Master-Roadmap) deliverables found: none.**
No `NEX_REPOSITORY_REALITY_REPORT.md`, `NEX_ARCHITECTURE_CROSSWALK*.md`,
`ADR-*.md`, or `InfluenceRecord` / causal-trace implementation existed on this
branch before this increment:

```
$ git grep -il "InfluenceRecord\|causal_trace\|causal trace"      # -> (none)
$ find . \( -iname '*reality*' -o -iname '*crosswalk*' -o -iname 'ADR*' \) \
       -not -path './.git/*'                                       # -> (none)
```

So "continue the InfluenceRecord implementation" begins from zero on this line;
this increment **establishes** the minimal overlay (see §6 and ADR-001).

---

## 1. Repository baseline (M0.1)

```
$ git ls-files | wc -l                       # 663 tracked files
$ git ls-files '*.py' | xargs wc -l | tail -1 # 96,220 Python LOC
```

| Type | Count | Notes |
|---|---:|---|
| `.py` | 483 | implementation + 134 test files |
| `.md` | 134 | specs, doctrine, design, observation reports |
| `.json` | 20 | weights, DAG, snapshots, fountain register exclusions |
| `.sql` | 6 | substrate schema (see §3) |
| `.txt` / `.sh` / `.yml` / other | 14 | prereg, keepalive, CI, systemd |
| **Total tracked** | **663** | |

**Top-level entry points / modules** (root `.py`, the system's seams):
`run.py` (boot + wiring of the living loop, ~900 lines), `nex_config.py`,
`power_switch.py`, `errors.py` (central error channel), `keystone.py`, `alpha.py`,
`ground_self_belief.py`, `nex_db_reaper.py`, `nex_db_backup.py`,
`nex_affinity_backfill.py`, `verifier_probe_stage1.py`, `verifier_stage2.py`,
`proof_of_concept.py`, `train_curator.py`, `nex_next_dev.py`,
plus **`influence_record.py`** (new this increment).

**Major subsystems** (directories):
`theory_x/` (the cognitive architecture — ~40 stage packages, `stage1_sense` …
`stage10_imagination`, `stage6_fountain`, `stage_affect`, `stage_drives`,
`stage9_metacognition`, `genius/`, `memory/`, `life/`, …), `substrate/` (the
data layer — 6 DBs, readers/writers), `speech/` (voice governor + queue),
`gui/` (Flask cockpit + chat column), `voice/` (LLM client + registers),
`strikes/`, `tools/`, `scripts/`, `tests/`.

> **Note — `watcher/` is not tracked on this branch.** The NEX Integration Watcher
> lives on the RDO branch family (`claude/rdo-*`), not on this NEX line:
> `git ls-files 'watcher/*'` returns nothing here. The "RDO v1.3 Stage 1 Watcher
> increment" named in the directive is therefore a **parallel RDO-branch concern**,
> not part of this branch's tree (see §7, Outstanding).

---

## 2. Boot / execution-path baseline (M0.2)

`run.py:main()` wires the living system and starts the autonomous loops. The two
**output-producing** paths the Phase-0 causal trace must cover:

- **Fountain cycle** (spontaneous thought). Built by
  `theory_x/stage6_fountain/__init__.py:build_fountain()`, driven by the
  `fountain_loop` thread; the single producer call is
  `FountainGenerator.generate(dynamic_state, beliefs_reader) -> Optional[str]`
  (`generator.py:1356`). Writes to `sense`, `dynamic`, and `beliefs` (via
  `FountainCrystallizer`).
- **Chat turn** (dialogue). `gui/server.py:api_chat()` (`POST /api/chat`,
  line 1145); the reply finalises at `gui/server.py:2163` and returns at `:2180`.
  Writes the reply to `conversations.messages`.

These two seams are mapped in full in `NEX_ARCHITECTURE_CROSSWALK_v2.md`.

---

## 3. Database baseline (M0.1)

Six separate SQLite databases (one file per concern — `substrate/paths.py`,
`SPECIFICATION.md §8`), resolved at `<repo>/data/` by default, overridable via
`NEX5_DATA_DIR`.

```
$ for s in substrate/schema/*.sql; do echo "$s: $(grep -ciE 'CREATE TABLE' $s)"; done
```

| DB | Schema file | Tables | Representative tables |
|---|---|---:|---|
| `beliefs.db` | `beliefs.sql` | 25 | `beliefs`, `belief_edges`, `belief_blacklist`, `belief_boost`, `belief_lineage`, `dormant_beliefs`, `arcs`, `arc_closers`, `patterns` |
| `dynamic.db` | `dynamic.sql` | 14 | `fountain_events`, `fountain_crystallizations`, `signals`, `drive_proposals`, `meta_cognition_events`, `speech_queue` |
| `conversations.db` | `conversations.sql` | 4 | `sessions`, `messages`, … |
| `intel.db` | `intel.sql` | 3 | `news_events`, `market_data`, … |
| `probes.db` | `probes.sql` | 3 | `probes`, `probe_context`, `probe_tags` |
| `sense.db` | `sense.sql` | 1 | `sense_events` |
| **Total** | | **50** | |

**The Phase-0 causal-trace overlay writes to none of these.** Its only sink is a
dedicated append-only file (`logs/influence_trace.jsonl`, git-ignored), verified
by `tests/test_influence_record.py::test_sink_is_never_a_substrate_db`.

---

## 4. Snapshot baseline (M0.1)

```
$ git ls-files 'snapshots/*' ; git ls-files '*snapshot*'
```

- Committed snapshots: `snapshots/2026-05-22_0913.json`,
  `snapshots/2026-05-22_0938_state.json`, `snapshots/README.md`.
- Snapshot tooling: `scripts/snapshot.py`, `tools/snapshots.py`,
  `theory_x/snapshots/snapshots.py`, `theory_x/memory/snapshot_writer.py`
  (`StateSnapshotWriter`, called each fountain tick), `theory_x/probes/context_snapshot.py`.
- Live DB state (`data/*.db`) is **not** committed (git-ignored) — runtime
  database content is therefore **UNKNOWN from the repository alone** and is a
  host-side observation, kept UNKNOWN here.

---

## 5. Test baseline (M0.2)

```
$ python -m pytest -q --continue-on-collection-errors
1568 tests collected
107 failed, 1406 passed, 5 skipped, 62 errors, 30 subtests passed in 132.82s
```

Honest classification of the 169 non-passing outcomes:

| Cause | Count | Evidence |
|---|---:|---|
| `ModuleNotFoundError` (missing optional deps) | **138** | `sentence_transformers` (107 refs), `psutil` (62), `argon2` (59), `flask` (17) |
| `AssertionError`, clustered in embedding-dependent tests | **~40** | e.g. `test_amoha.py` "`0.0 not greater than 0.3`" — score collapses to 0.0 with no embedding model; **candidate env-downstream, not individually root-caused** |

**Interpretation.** The local baseline is **environment-limited**: the four
missing packages are heavyweight optional ML/system/web deps absent from this
container. They were **not** installed here (heavy ML wheels risk the disk
allowance, and installing them changes the test environment) — the authoritative
green baseline is **CI, with dependencies installed**. The ~40 `AssertionError`s
are consistent with the absent embedding model returning null scores; they are
reported as a candidate cluster, not asserted as logic defects, because they were
not individually root-caused.

**Overlay tests added this increment:** `tests/test_influence_record.py` — **16
passed** in 0.23s (`python -m pytest tests/test_influence_record.py -q`).

---

## 6. What this increment changed (grounded)

```
$ git status --short        # Phase-0 files only; watcher/ left untracked
M gui/server.py                              # chat seam (default-OFF trace call)
M theory_x/stage6_fountain/__init__.py       # fountain seam (default-OFF trace call)
A influence_record.py                        # the overlay (M0.5)
A tests/test_influence_record.py             # 16 tests incl. off==on identity
A docs/phase0_influence_capture_fixture.jsonl# fixture-capture evidence
A NEX_REPOSITORY_REALITY_REPORT.md           # this file (M0.1–M0.2)
A NEX_ARCHITECTURE_CROSSWALK_v2.md           # the two seams (M0.3–M0.4 seed)
A ADR-001.md                                 # overlay design decision
A PHASE0_HANDOFF.md                          # what remains incomplete
```

The two seam edits are **inert by default** (the env flag `NEX5_INFLUENCE_TRACE`
is unset), so the existing suite sees no behavioural change — the regression
evidence for zero-delta of the real integration. See ADR-001 and the crosswalk.

---

## 7. Phase-0 completion status against the directive

| Deliverable | Status | Where |
|---|---|---|
| M0.1 repository/DB/snapshot baseline | **Done** | §1, §3, §4 |
| M0.2 test baseline | **Done (env-limited; CI authoritative)** | §5 |
| M0.3–M0.4 architecture crosswalk, DAG, producers/consumers, L0–L4 | **Seeded for the two output paths; full-system crosswalk OUTSTANDING** | `NEX_ARCHITECTURE_CROSSWALK_v2.md` |
| M0.3–M0.4 ADR-001 | **Done (overlay decision)** | `ADR-001.md` |
| M0.5 minimal default-OFF InfluenceRecord + zero-delta | **Done (fixture-level); live L4 capture host-gated UNKNOWN** | `influence_record.py`, tests, §6 |
| RDO v1.3 Stage 1 Watcher increment | **Not on this branch** (RDO branch family) | §1 note, `PHASE0_HANDOFF.md` |
| Gate 0 founder approval | **PENDING — not assumed** | — |

No Phase 1 behavioural modification has been started, per the Gate-0 constraint.
