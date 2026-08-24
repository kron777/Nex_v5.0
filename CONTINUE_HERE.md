# CONTINUE HERE

**Written:** 2026-08-24 · **NEX is SHUT DOWN.** Nothing is running. Nothing is lost.

---

## 1. Current state — OFF

Shut down 2026-08-24 ~01:55 SAST under memory pressure. Clean SIGTERM, so the WAL
checkpointed properly; no torn writes.

| | |
|---|---|
| `run.py` | not running |
| `nex5-keepalive.service` | **stopped AND disabled** (2026-08-24) |
| `nex_tor_pool` (docker) | Exited (137) |
| port 8765 | free |
| last `fountain_insight` | **2026-08-23 23:55:27 UTC** |

### To bring her back

```bash
systemctl --user start nex5-keepalive.service
docker start nex_tor_pool
```

The 24 external feeds **auto-start on boot** (`stage1_sense/scheduler.py:149`) — no need
to call `/api/sense/start`. Verify with `curl -s localhost:8765/api/sense/status`.

**She will NOT come back on reboot.** A full autostart audit was done 2026-08-24 and every
user-level vector is disabled:

| vector | state |
|---|---|
| `nex5-keepalive.service` (user) | **disabled** |
| `nex-gpu-cleanup.service` (user) | **disabled + stopped** |
| `nex5.service` (user) | masked (was already) |
| hourly `scripts/trajectory.py` cron | **commented out** — it was live and running every hour |
| `nex_tor_pool` docker | `unless-stopped` policy, but explicitly stopped, so it will **not** auto-start |
| XDG autostart / `.bashrc` | nothing (only shell aliases, harmless) |

**Two SYSTEM units still need root** — they were left running because they need a password:

```bash
sudo systemctl disable --now nex-brain-log.service   # tails nex-brain's journal, ~2 MB, pointless (nex-brain is inactive)
sudo systemctl disable --now ollama.service          # NEX's LLM backend -- see note below
```

`ollama` is what `NEX5_VOICE_URL` points at (`localhost:11434`). Its *runner* (2.2 GB with a
model loaded) unloads itself on idle and already has; only `ollama serve` (~450 MB) persists.
**Disable it only if nothing else on the machine uses ollama** — it is a general-purpose tool,
not NEX-exclusive.

To re-enable everything: `systemctl --user enable --now nex5-keepalive.service`, restore the
cron line, `docker start nex_tor_pool`.

### The thing that wastes an hour if you don't know it

**`nex_keepalive.sh` is NOT the top of the process tree.** `nex5-keepalive.service` is a
**systemd user unit** that restarts the supervisor whenever it dies. `pkill` and `kill -9`
on the script will respawn within seconds — during this shutdown it respawned NEX three
times (pids 904155 → 904949 → 904975) before the unit itself was stopped. Use
`systemctl --user stop nex5-keepalive.service`. Nothing else works.

---

## 2. Last dev — R76, shipped and verified

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

## 3. What is live in the code (active on next start)

| round | change | commit |
|---|---|---|
| R70 | signals reaper — already drained 1,394,502 → ~77,000 rows | `bc5a51e` |
| R71 | burst types removed from `_PROMOTABLE_TYPES` | `d3c6e03` |
| R72 | entity recurrence counted over the **window**, not the tick batch; `4_branch` promotable | `4027449` |
| R74 | `register_exclusion.json` v3 (+`item`, `aligns`, `discusses`, `highlights`) | `b67cc52` |
| R76 | hot-observer widen + dedup | `250d498` |

R72 and R76 both went live on the 2026-08-23 12:59Z restart and have **~11 hours of
runtime** before shutdown. Neither has a full evaluation window yet.

---

## 4. THE OPEN MEASUREMENT — read this before anything else

R75 predicted `advancements` would **peak then decay** once the amplifier was cut.
Its falsifier: *it keeps climbing*.

**State at shutdown (OBSERVED):**

| day | `advancements` DF | `societal` DF |
|---|---|---|
| 08-19 | 21.5% | 8.9% |
| 08-20 | 22.2% | 24.7% |
| 08-21 | 22.2% | 13.9% |
| **08-22** | **27.4%** | 9.6% |
| 08-23 | 24.6% | **1.6%** |

Final `maxDF*` at shutdown: **24.0% on `advancements`**, no breach (threshold 25%).

**Two things happened that nobody has acted on yet:**

1. **R75's tripwire #1 FIRED.** It read *"`advancements` DF exceeds 25% on any full day →
   it has ignited; intervene."* **08-22 hit 27.4%** — and that was *before* R76 shipped on
   08-23. The tripwire fired unobserved.
2. **The fusion broke.** R75 established that `advancements` and `societal` fused on 08-19
   into one groove (3.5× lift, zero co-occurrence before). **`societal` has now decayed to
   1.6% while `advancements` holds at 24.6%.** They have separated. R75's "one object"
   reading held for roughly three days and no longer describes what is there.

**The shutdown puts a hole in this series.** Corpus accrual stopped at 08-23 23:55 UTC. Any
resumed measurement has a gap, and the restart itself is a regime boundary. Do not compare
post-restart days to pre-shutdown days as if they were continuous.

**Attribution warning:** R72 changed the fountain prompt in the *same* restart as R76. If
`advancements` moves, check R72's pre-registered bars (`677c9b4`, and r72.md §2.3/§2.4)
**before** attributing anything to the dedup.

**R76's own tripwire, unchecked:** hot-observer block empty on >2% of fires → dedup is
over-dropping → revert the dedup, leave R72. Replay showed 0 empty events in 200 picks, but
this has never been checked against live fires.

---

## 5. Blocked / deferred — do not restart these blind

- **maxDF\* stability test (R67):** BLOCKED. Not on corpus size — the clean corpus passed
  800 — but on **single-regime-ness**. Live convergences sit inside the window. See r73.md §1.
  The re-date rule: `societal` and `advancements` each under **5% for 3 consecutive days**,
  then open a *fresh* window and accrue 800 docs, reusing nothing from before it.
  **`societal` is now at 1.6% — day 1 of that clock may have started. `advancements` has not.**
- **Register refit (R50/R73):** needs ~1,000 clean **post-R29** docs; the clean stretch is
  575. r73.md §B. `systems` re-add stays deferred to this refit.
- **`_was_recently_semantically_similar` window** (R75 §D2, 30 min vs a 213-min groove
  inter-arrival): designed, **not shipped**, deliberately.
- **`beliefs.db` has never been VACUUMed** since the R70 reaper freed ~326 MB.

---

## 6. Memory — why she was shut down

Reported as 19.4 / 23.4 GiB. **NEX's own RSS was 2.24 GB (9.1%)** — real growth, but not
the headline number; most of the rest was reclaimable `buff/cache` over the database files,
plus comparable neighbours (ollama 2.23 GB, qemu 1.44 GB). systemd reported the unit at
**1.3 G peak, 171 tasks**. Shutdown recovered ~4 GiB of `used`.

**The WALs are not the leak** — all small (`beliefs` 1.1M, `dynamic` 4.0M, `sense` 4.6M).
**The size is in the databases: 9.3 GB total**, dominated by:

| | |
|---|---|
| `dynamic.db` | **4.9 G** |
| `sense.db` | **3.5 G** |
| `beliefs.db` | 763 M (pre-VACUUM) |

**Neither `dynamic.db` nor `sense.db` has ever been audited for retention.** R70 reaped
`signals` in `beliefs.db` only. `fountain_retrieval_log` lives in `dynamic.db` and has no
pruning. That is the obvious next place to look if memory pressure recurs, and it is
untouched work.

---

## 7. Standing lessons that keep costing rounds

- **A gate's window must exceed the inter-arrival time of what it catches.** Three
  instances in five rounds (R69 title throttle, R71/R72 batch-vs-window, R75 30-min
  similarity gate). Check *scope* before threshold.
- **Supply is not eligibility.** R71 predicted 5/day from 60.9/day of supply and measured 0.
- **"Staged-inactive" is not durable** — the supervisor restarts on its own. An edit on disk
  ships itself. R70 and R71 both went live unplanned this way.
- **Derived statistics go stale and get cited as constants.** The 25.0% baseline above drifted
  to 19.4% within hours.

---

## 8. Reports

`observation_reports/` — r69 through r75 are published. **There is no `r76.md`**: that round
went straight to code and ledger under time pressure. The full detail is in the
`DEPLOY_LEDGER.tsv` entry dated `2026-08-23T13:05:00+0000` and in `250d498`'s commit message.
Writing r76.md is outstanding.
