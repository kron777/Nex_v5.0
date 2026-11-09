# CONTINUE HERE

**Written:** 2026-08-24 · **corrected 2026-10-31** (see §9 change log — this pass fixes
several claims that had gone stale, found and verified against the live machine and git
history, not inferred). **NEX is ON and running right now.** The "shut down" framing below
describes a point-in-time snapshot from 2026-08-24, not a durable state: development and
restarts continued for weeks afterward, and she is awake as of this edit. See §1.

---

## 1. Current state — ON, live-verified 2026-10-31

Checked directly against the running machine, not inferred from a doc:

| | |
|---|---|
| `run.py` (port 8765) | **running**, `/api/health` → all 6 DBs `ok` |
| `power_switch.py` (port 8766) | **running**, `/api/power` → `{"state":"on"}` |
| `~/.nex/STANDBY` | **absent** → ON (see §1a for what this file means) |
| `nex5-keepalive.service` | **active** |
| `nex5-power-switch.service` | **active**, confirmed standalone (own cgroup) |
| sense adapters | polling live — `last_poll_at` timestamps current to the minute |

She came back up at some point after a brief standby earlier on 2026-10-31 (the sentinel
briefly read `off since 2026-10-31 10:56:56`, then was cleared). That standby is unrelated
to the 2026-08-24 shutdown this document originally described — see §1b for the real
timeline in between.

## 1a. The on/off model — v3, STANDBY-sentinel based

This corrects a claim about this exact mechanism that was itself wrong earlier today —
verified directly against `power_switch.py` and `nex_keepalive.sh` source rather than
repeated secondhand.

**Single source of truth: `~/.nex/STANDBY`.** Present = OFF, absent = ON. Both
`power_switch.py` and `nex_keepalive.sh` read the same file and converge on it independently.

- **To check:** `curl -s localhost:8766/api/power` → `{"state": "on"|"off"}`, or just
  `ls ~/.nex/STANDBY`.
- **To turn off:** `curl -s -X POST localhost:8766/api/power -d '{"action":"off"}'` — this
  writes the sentinel *and* gracefully SIGTERMs the running NEX process. (Equivalently,
  `systemctl --user stop nex5-keepalive.service` also works — see below.)
- **To turn on:** `curl -s -X POST localhost:8766/api/power -d '{"action":"on"}'` — deletes
  the sentinel; the keepalive supervisor relaunches NEX on its own.

**`nex5-keepalive.service` and `nex5-power-switch.service` are independent systemd units
that never share a cgroup.** Stopping the keepalive supervisor does **not** kill the power
switch — its own unit description says so, and `nex_keepalive.sh`'s exit trap only
gracefully stops *its own child* (the NEX process it launched) and explicitly logs "power
switch is now its own systemd unit and is left running." So `systemctl --user stop
nex5-keepalive.service` is safe on its own; you do not lose the wake path by using it.

`nex_keepalive.sh` also refuses to launch NEX at boot if `~/.nex/STANDBY` is present
("Wake her from the power pill on :8766" is its own log line), and separately refuses to
launch at all if `~/.nex/KEEPALIVE_FAILED` exists (a giveup marker, exit code 3, cleared
with `rm` then a manual restart).

## 1b. What actually happened between R76 (08-23) and now (10-31)

The previous version of this document ended at `b94214a`, 2026-08-23T23:55:23Z, and
implied that was the end of the story. It was not. Verified directly from `git log` and
`journal/DEPLOY_LEDGER.tsv`, in order:

- **2026-10-18T11:30:07Z** — `journal/DEPLOY_LEDGER.tsv` has one more real entry after the
  long gap, not a silent file as previously stated: commit `14ae986`, "D‑A affinity
  provenance SHIPPED + reserve" — `NEX5_AFFINITY_PROVENANCE=on` (affinity now derived from
  `beliefs.source` instead of an LLM self-rating) and `NEX5_INTAKE_T6_RESERVE=50` (reserves
  standing-voice slots for high-affinity non-authored beliefs), from PR #12/#13. This entry
  was missed in earlier analysis this session that assumed the ledger went silent at 08-23
  by design — it didn't go fully silent, it just has one entry per deploy rather than one
  per restart.
- **PRs #32 through #43** (current `HEAD`) — a long, continuous chain of feature work, most
  recent first:
  - `e2b5e78` **(HEAD)** PR #43 — learning guards G1–G4 + dark attribution subtraction; pin
    timing + ownership wall
  - PR #42 — left-censoring, deletion as bookkeeping, split gap report
  - PR #41 — activation: commitment-valence ON, learning ON (subtractability met)
  - PR #40 — learning-delta provenance + subtractability; ever-fired lines
  - PR #39 — undo log: append-only per-belief undo events
  - PR #38 — keepalive commitments producer (dark)
  - PR #37 — commitment faculty (dark)
  - PR #36 — B tightening: falsifiability canary, mood hard gate, external-drift canary
  - PR #35 — B ledger flags (owned-belief producer + reconciler)
  - PR #34 — B PR2: expectations ledger, single reconciler, `event_valence` (dark)
  - PR #33 — B PR1: frozen basis snapshot + cost band on every producer
  - PR #32 — B phase 0: confidence, tolerance, stakes frozen at `made_at`
  - *(full detail in each PR's own commit message; not re-summarized here to avoid
    restating something this document hasn't independently verified the substance of)*
- **`journal/keepalive_runtime.tsv`** (the untracked, local-only restart log — see §1c)
  records real restart activity on **2026-10-26 and 2026-10-27** (commits `d99c671`,
  `f60ad25`, `804a8fe`, `721323f`, `32df838`), then a cluster of **six restarts on
  2026-10-31 between 01:43 and 08:14 UTC**, all at the current `e2b5e78`.

None of this was visible from the 2026-08-24 snapshot. **Treat `e2b5e78` as the real
current `HEAD`, not `250d498` (R76) or `bed1f79`** (the newest commit any prior doc in this
workspace had actually named).

## 1c. Where restart history actually lives

`journal/DEPLOY_LEDGER.tsv` is git-tracked and hand-curated — it gets an entry per
*deliberate deploy*, not per restart, which is why it looks sparse. Routine supervisor
restarts (crash, OOM, manual bounce) are recorded separately in
**`journal/keepalive_runtime.tsv`**, which is **untracked and local-only** (deliberately —
it would otherwise dirty the git tree on every respawn). Check both: the ledger for what
shipped and why, the runtime tail for what's actually been running and when.

---

## 2. Last dev — R76, shipped and verified *(historical — Aug 2026 window; superseded by §1b)*

**Commits:** `250d498` (code) · `b94214a` (ledger). Both pushed.

The hot-observer retrieval slot was the amplifier behind the `advancements` groove that
R75 diagnosed: `hot_observer` beliefs quote the fountain's own crystallized text
**verbatim**, exactly one is injected into **every** fire, and the pick was
`ORDER BY RANDOM() LIMIT 1` with **no near-duplicate filtering** — the few-shot repetition
loop Phase 43 removed, re-entering by a different door.

**Fix:** widened the candidate pool 24h → 72h **and** deduped it, both halves together.

- 168h + dedup measured best (7.5%) and was **deliberately rejected** — the slot exists to
  supply a *live* self-observation, and a week-old one is not that.
- Dedup reuses R32's exemplar mechanism unchanged (first-sentence 5-gram Jaccard ≥ 0.5).
- **Order of operations is load-bearing:** dedup is greedy and the first row always
  survives, so *dedup-then-take-first* reproduces the original distribution exactly and
  buys nothing. Implemented as fetch-random → dedup-all → uniform pick from survivors.

**Measured at shipped settings:** pool 186 → 145 distinct, P(pick carries `advancements`)
**15.9%**, zero empty-pool events. Against a *concurrent* baseline of 19.4% that is a
**~3.5 pp** effect — **not** the 9.1 pp you get by comparing to the stale pre-pause 25.0%
snapshot. Do not cite 9.1 pp; it credits the fix with baseline drift.

Tests: 8 failed / 95 passed, **identical failure set with and without the change**.

---

## 3. What was live in the code as of R76 *(historical — 20+ commits behind `HEAD`; see §1b)*

| round | change | commit |
|---|---|---|
| R70 | signals reaper — already drained 1,394,502 → ~77,000 rows | `bc5a51e` |
| R71 | burst types removed from `_PROMOTABLE_TYPES` | `d3c6e03` |
| R72 | entity recurrence counted over the **window**, not the tick batch; `4_branch` promotable | `4027449` |
| R74 | `register_exclusion.json` v3 (+`item`, `aligns`, `discusses`, `highlights`) | `b67cc52` |
| R76 | hot-observer widen + dedup | `250d498` |

R72 and R76 both went live on the 2026-08-23 12:59Z restart and had **~11 hours of
runtime** before the 2026-08-24 shutdown snapshot below was taken. **Nothing in this table
has been re-evaluated against the 20+ commits that followed (§1b).** Whatever
`advancements`/`societal` are doing now needs fresh measurement, not inference from §4.

---

## 4. THE OPEN MEASUREMENT, as it stood 2026-08-23 *(historical — not re-measured since)*

R75 predicted `advancements` would **peak then decay** once the amplifier was cut.
Its falsifier: *it keeps climbing*.

**State at the 2026-08-24 snapshot (OBSERVED):**

| day | `advancements` DF | `societal` DF |
|---|---|---|
| 08-19 | 21.5% | 8.9% |
| 08-20 | 22.2% | 24.7% |
| 08-21 | 22.2% | 13.9% |
| **08-22** | **27.4%** | 9.6% |
| 08-23 | 24.6% | **1.6%** |

Final `maxDF*` at the snapshot: **24.0% on `advancements`**, no breach (threshold 25%).
As of 2026-09-10 (r76.md, the newest first-party diagnostic that exists — see §8),
`maxDF*` was reading **24.0% on `systems`** instead — a different token, and `r76.md`
records it as a **DECAYED** verdict with a zero-fire outage 2026-08-25→09-07. Whether
either of `advancements`, `societal`, or `systems` is still live now, 20+ commits and two
months later, **has not been checked**. Do not assume this table still describes current
behaviour.

**Two things had happened that nobody had acted on as of the snapshot:**

1. **R75's tripwire #1 FIRED.** It read *"`advancements` DF exceeds 25% on any full day →
   it has ignited; intervene."* **08-22 hit 27.4%** — and that was *before* R76 shipped on
   08-23. The tripwire fired unobserved.
2. **The fusion broke.** R75 established that `advancements` and `societal` fused on 08-19
   into one groove (3.5× lift, zero co-occurrence before). **`societal` had decayed to
   1.6% while `advancements` held at 24.6%** by the snapshot. They had separated. R75's
   "one object" reading held for roughly three days and no longer described what was there.

**Attribution warning:** R72 changed the fountain prompt in the *same* restart as R76. If
`advancements` moves, check R72's pre-registered bars (`677c9b4`, and r72.md §2.3/§2.4)
**before** attributing anything to the dedup.

**R76's own tripwire, unchecked at the snapshot:** hot-observer block empty on >2% of
fires → dedup is over-dropping → revert the dedup, leave R72. Replay showed 0 empty events
in 200 picks, but this had never been checked against live fires as of 08-24, and still
hasn't been reported on since.

---

## 5. Blocked / deferred as of the snapshot — re-check before trusting

- **maxDF\* stability test (R67):** was BLOCKED. Not on corpus size — the clean corpus had
  passed 800 — but on **single-regime-ness**. Live convergences sit inside the window. See
  r73.md §1. The re-date rule: `societal` and `advancements` each under **5% for 3
  consecutive days**, then open a *fresh* window and accrue 800 docs, reusing nothing from
  before it. Given two months and 20+ commits have passed, this may have long since
  resolved itself one way or the other — unverified.
- **Register refit (R50/R73):** needed ~1,000 clean **post-R29** docs; the clean stretch
  was 575 as of the snapshot. r73.md §B. `systems` re-add was deferred to this refit —
  worth noting `systems` is exactly the token r76.md later found at 24.0% maxDF*.
- **`_was_recently_semantically_similar` window** (R75 §D2, 30 min vs a 213-min groove
  inter-arrival): designed, **not shipped** as of the snapshot, deliberately.
- **`beliefs.db` has never been VACUUMed** since the R70 reaper freed ~326 MB (status as of
  the snapshot; not re-checked).

---

## 6. Memory — why she was shut down on 2026-08-24 *(historical incident, not current)*

Reported as 19.4 / 23.4 GiB. **NEX's own RSS was 2.24 GB (9.1%)** — real growth, but not
the headline number; most of the rest was reclaimable `buff/cache` over the database files,
plus comparable neighbours (ollama 2.23 GB, qemu 1.44 GB). systemd reported the unit at
**1.3 G peak, 171 tasks**. The 2026-08-24 shutdown recovered ~4 GiB of `used`.

**The WALs were not the leak** — all small (`beliefs` 1.1M, `dynamic` 4.0M, `sense` 4.6M).
**The size was in the databases: 9.3 GB total** at the time, dominated by:

| | |
|---|---|
| `dynamic.db` | **4.9 G** |
| `sense.db` | **3.5 G** |
| `beliefs.db` | 763 M (pre-VACUUM) |

**Neither `dynamic.db` nor `sense.db` had ever been audited for retention** as of the
snapshot. R70 reaped `signals` in `beliefs.db` only. `fountain_retrieval_log` lives in
`dynamic.db` and had no pruning. Given she has been running again for weeks since, this
is worth re-checking if memory pressure recurs — current size unverified.

---

## 7. Standing lessons that keep costing rounds

- **A gate's window must exceed the inter-arrival time of what it catches.** Three
  instances in five rounds (R69 title throttle, R71/R72 batch-vs-window, R75 30-min
  similarity gate). Check *scope* before threshold.
- **Supply is not eligibility.** R71 predicted 5/day from 60.9/day of supply and measured 0.
- **"Staged-inactive" is not durable** — the supervisor restarts on its own. An edit on disk
  ships itself. R70 and R71 both went live unplanned this way.
- **Derived statistics go stale and get cited as constants.** The 25.0% baseline in §2
  drifted to 19.4% within hours — and this whole document is a second instance of the same
  lesson at a larger scale: a two-month-old snapshot got cited as current state.
- **A silent record is not a quiet system.** The 2026-08-23→10-18 ledger gap read as "went
  dark by design," and that was only half true — restart history moved to an untracked
  file (§1c), but real deploys kept landing (§1b). Three places hold a partial record
  (ledger, runtime log, git history); no single one is authoritative alone.

---

## 8. Reports

`observation_reports/` — verified by directory listing, not assumed:

- **`r76.md` exists** (3,932 bytes) — the earlier claim in this document that it didn't,
  and that "writing r76.md is outstanding," was false. It carries a **DECAYED** verdict on
  the `advancements`/`societal` question (§4), records a zero-fire outage
  2026-08-25→09-07, and finds `maxDF*` at 24.0% on **`systems`** instead — dated
  2026-09-10, and it is the **newest fully-written report that exists.**
- **r69 through r76 are complete, final reports.** r77 through r84 exist only as
  **preregistrations and baseline directories** (`r77_PREREGISTRATION.md`,
  `r79_L4_stakes_PREREGISTRATION.md`, `r80_L4_approach_PREREGISTRATION.md`,
  `r81_L4_teeth_PREREGISTRATION.md`, `r82_L4_teeth_retrieval_PREREGISTRATION.md`,
  `r83_phrasing_PREREGISTRATION.md`, `r84_arbiter_competition_PREREGISTRATION.md`, plus
  `r77_baselines/`, `r79_baselines/`, `r80_baselines/`, `r83_baselines/`) — rounds that were
  **planned**, not rounds with a written verdict. Treat "the listing runs through r84" as
  "an r84 round was designed," not "an r84 round concluded."
- **r78 does not exist in any form** — no `r78.md`, no preregistration, no baseline dir. A
  real gap, not a renumbering artifact (r77 and r79 both exist).
- None of r77–r84's preregistrations have been read for content as part of this correction
  pass — only their existence and filenames are confirmed. What they actually propose is
  unverified from this document.

---

## 9. Change log

**2026-10-31** — corrected against the live machine and git/filesystem history (not
inferred from any cached doc), after this document was found to contain two false claims
(§1, §8) during setup of an automated daily continuity-check agent meant to catch exactly
this kind of drift going forward:

- §1 rewritten: NEX is ON (was described as durably OFF since 08-24; that was a
  point-in-time snapshot, not a current fact).
- §1a added: the real v3 STANDBY-sentinel on/off model, sourced directly from
  `power_switch.py` / `nex_keepalive.sh` — correcting a claim stated *earlier today* (not
  in the original 08-24 text) that stopping `nex5-keepalive.service` also kills the power
  switch via a shared exit trap. It does not; the two are independent systemd units and the
  source confirms it explicitly.
- §1b added: the real history between R76 (08-23) and now, including a
  `DEPLOY_LEDGER.tsv` entry from 2026-10-18 that earlier analysis this session missed, and
  the full PR #32–#43 chain ending at current `HEAD` `e2b5e78`.
- §1c added: where restart history actually lives now (`journal/keepalive_runtime.tsv`,
  untracked, separate from the hand-curated ledger).
- §8 corrected: `r76.md` **exists** (the document previously said it didn't). Rounds
  r77–r84 are preregistrations only, not completed reports; r78 is a genuine gap.
- §§2–7 kept as the historical record of the R76 round and the 08-24 snapshot — explicitly
  relabelled as historical rather than rewritten, since nothing in them has been
  re-verified against current state and they remain accurate for the window they describe.

A daily continuity-check agent (Beam AI, 07:00 Africa/Johannesburg, reads this file plus
the runtime log and observation-reports listing from GitHub) is now deployed specifically
to stop this kind of staleness from reaching two months again. Its first scheduled run is
2026-11-01.

**2026-11-08** — docs-only addition, no code change, no current-state claims revised:

- Added `SENTIENCE_SYNTHESIS.md` at repo root, a design memo (companion to
  `SENTIENCE_PROGRAM.md`) arguing the phases (A/S/E/T/M/D/F) are one closed cycle rather
  than a feature list, and proposing a shared Cost-and-Trace Ledger primitive so A, S, E,
  and F are one organ instead of four separately-bookkept features. From a design/ideology
  discussion with Beam. Commit `d805e8c`.
- Flagging one item back to Jon specifically, per Beam's note on the commit: §8 Q5 of the
  new memo — "a program with no designed failure demonstration is one that can't tell
  progress from activity" — has no answer yet anywhere in this repo. Worth deciding what
  that demonstration is before the amalgamation work goes further.

**2026-11-09** — docs-only addition, no code change, answering the Q5 flag above:

- Added §9 to `SENTIENCE_SYNTHESIS.md` — a concrete, pre-registered failure demonstration
  (the "forced-tradeoff trial") proposed as the answer to §8 Q5. It is a test design, not a
  result: it presupposes the ledger (§4) exists with `commit`/`spend`/`refuse`/`consolidate`
  wired to real balance, which nothing in the codebase has shipped yet. Stated now so the
  pass/fail bar can't move once something is built to run it against.
