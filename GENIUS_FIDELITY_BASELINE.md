# Subject-fidelity predicate & frozen baselines

Written 2026-08-03 (round 26) to close a process defect: round 25 could not
find the fidelity predicate or the round-19 possessive fix anywhere in the
repo. They had only ever existed in conversation, which is why round 12's
numbers and round 25's are not comparable. **Anything measured here that a
later round will want to compare against belongs in this file, not in a
chat log.**

---

## 1. The subject-fidelity predicate

Reconstructed in round 25 (the round-12 original was unrecoverable). Any
future round comparing fidelity numbers MUST either use this predicate or
state explicitly that it is using a different one.

Given a fire's `focal_item` (the assigned subject) and its `thought`:

1. Lowercase both.
2. **Strip possessives** — `'s`, `s'`, `’s`, `s’` → removed. *(This is the
   round-19 fix: without it `farmers'` and `farmers` are different tokens.)*
3. Tokenize on `[a-z0-9]+`.
4. Drop tokens shorter than 3 characters, and drop every token in the
   furniture list (section 2).
5. De-duplicate the `focal_item` tokens, preserving order → the subject's
   **content tokens**.
6. `share = |content tokens present in thought| / |content tokens|`
7. **Subject-faithful ⇔ `share > 0`** (at least one content token survives
   into the output).

`focal_item` must be read **untruncated from `fountain_events`**. Do not join
through the soak log — its excerpts are cut at 200 chars.

Reference implementation: `POSS = re.compile(r"(?:'s|s'|’s|s’)\b")`,
`TOK = re.compile(r"[a-z0-9]+")`.

### Applicability

- **EXPLAIN / ARGUE** — measurable. These bind `focal_item` via
  `_kw.get("item")` at `generator.py` wide-mode branch.
- **DRIFT** — **not measurable, and not a defect.** DRIFT binds no
  `focal_item` (0/123 in the frozen window) and its `droplet` is a slug
  derived *from* the output, not an input. DRIFT has no external subject by
  construction. No predicate can score it; do not report a DRIFT fidelity
  number.
- **NULL mode** — substrate-voice fires; same, not measurable.

### Threshold sensitivity (frozen window, for calibration)

| predicate | EXPLAIN | ARGUE |
|---|---|---|
| `share > 0` (**the standard**) | 66.5% | 35.2% |
| `share >= 0.25` | 63.4% | 29.0% |
| `share >= 0.50` | 57.8% | 22.8% |
| `share >= 0.75` | 39.8% | 12.4% |

---

## 2. The furniture list (86 terms)

```
# grammatical
a an the and or but of to in on at for from by with as is are was were be
been it its this that these those into over under after before amid about
up down out off than then new not no has have had will can could would
should may might says say said how why what who when where which more most
less first last
# pronouns
you your i we our they their he she his her them
# headline furniture
uk us update live exclusive report reports reveals warns here just also one
two get gets make makes take takes back still now via amp per cent
```

---

## 3. FROZEN BASELINE — pre-#1 (F2 sign change)

Window **2026-08-02 12:21:48 → 2026-08-03 12:20:00 UTC**, `N = 535`.
Scorer: `genius_score_weights.json` `version = v2`, `length_structure`
scaled ×0.85 on 2026-07-27 (commit `ab1b8a6`) — six days before the window
opened. **No scorer change inside the window.** Verified scorer-homogeneous.

### STRIKING

| arm | n | rate | 95% CI (Wilson) |
|---|---|---|---|
| **ALL** | 75/535 | **14.0%** | 11.3 – 17.2 |
| EXPLAIN | 31/161 | 19.3% | 13.9 – 26.0 |
| ARGUE | 41/145 | 28.3% | 21.6 – 36.1 |
| DRIFT | 3/123 | 2.4% | 0.8 – 6.9 |
| NULL | 0/106 | 0.0% | 0.0 – 3.5 |

### Fidelity

| arm | rate | 95% CI |
|---|---|---|
| EXPLAIN | 66.5% | 58.9 – 73.3 |
| ARGUE | 35.2% | 27.9 – 43.2 |

### Mode split

EXPLAIN 161 (30.1%) · ARGUE 145 (27.1%) · DRIFT 123 (23.0%) · NULL 106 (19.8%)

### How to judge a change against this

- **Primary endpoint is the BLENDED contrast.** Round 25 established that n
  cannot separate templates at 24h (EXPLAIN p=0.059, ARGUE p=0.247, blend
  p=0.007). Per-template separation needs ~3.5 days (~110 STRIKING per arm
  for 80% power). **Do not claim a per-template result at 24h.**
- **Never judge against a spot reading.** Hourly STRIKING ranges 4.2–26.1%
  at n≈22/hour, and chi-square homogeneity over 24 hours is **p = 0.759** —
  i.e. that entire range is consistent with a constant 14.0%. A single hour
  observing 3/22 has a 95% CI of [4.7 – 33.3].

---

## 3b. Prompt-content changes AFTER the frozen window

Anything here moves fidelity. A future before/after must treat the frozen
baseline as "pre-" and account for these.

| when (UTC) | commit | change | expected direction |
|---|---|---|---|
| 2026-08-03 ~15:5x | `81b04ad` | **B1 residue ordering.** `pop_residue` served the oldest unconsumed row (head of queue 73.3 days old) because all 393,838 rows tie at `activation_strength=1.0`. Now `created_at DESC`; head of queue ~2 min. | fidelity **up** — prompts stop carrying 73-day-old material |
| 2026-08-03 ~15:5x | `522fbb0` | **B4 ingestion dedup at 0.96.** Corpus-level, not prompt-level. 4.9% of distilled titles (18/365 over 24h) suppressed as near-duplicates. | fidelity ~neutral; reduces corpus redundancy |

**Still held for attribution** (ready, verified, not shipped): the
`self_narrative.py:48` 60-char prefix key, and the `noticing` gerund gate
(+ Anchoring, Hunting, Scaling, Getting, Shipping, Watching). Both change
prompt content. B1 already moved prompt content this window; shipping these
alongside it would make any fidelity movement unattributable among three
causes.

## 4. Other conversation-only findings, recorded here

- **DRIFT share cannot be read from the soak log.** `generator.py` sets
  `_last_fire_mode = "DRIFT"` silently; only the wide branch prints
  `[WIDE MODE]`. So "fires without a `[WIDE MODE]` line" = **DRIFT ∪
  substrate-voice**, which is 42.8% — not DRIFT, which is 23.0%. This is the
  entire source of round 11's 41–44% figure. Verified by exact reproduction:
  over one soak-log span, log `Fountain fired` = 357 ≡ DB total 357; log
  `[WIDE MODE]` = 203 ≡ DB EXPLAIN+ARGUE 203.
- **`focal_item` is NULL on DRIFT by design**, not a carry leak. Only the
  wide-mode branch binds `item`. The correct coverage predicate is
  "populated on every EXPLAIN/ARGUE fire" → 233/233 in the frozen window.
- **F2 (`anti_template`) is NOT degenerate in production.** Frozen window:
  0/535 are exactly 0.0000; min 0.012, max 1.000, **mean 0.851**. It is
  **F3 (`t6_promotion`)** that is exactly 0.0000 on 535/535 — and on all 103
  training rows, with a fitted weight of exactly 0.0. Do not transpose these
  two.
- **F2 is a genuine suppressor in the deployed vector.** In training it
  correlates *positively* with the label (r = +0.114) but carries weight
  −1.577, because it is collinear with F5 (r = +0.440), the dominant
  predictor (r = +0.850 with label). The multivariate fit is also unstable:
  refitting on the same 103 rows with the same hyperparameters gives −0.712,
  not −1.577.
- **Contamination, frozen window:** the Gatwick / youth-benefits /
  security-camera text is in 139/535 = 26.0% of all fires and **49.7% of
  ARGUE**, eight days after the story broke.
### Round 26 A2 — offline re-score of the frozen window under candidate F2 weights

Method: recompute all five features per fire with `score_v2.compute_features`,
prior-50 context exactly as `tagger._tag_window` builds it (6h of preceding
fires for context), then apply candidate vectors. **Validated: the recompute
reproduces all 535 stored `genius_tags` scores to `0.00e+00` and 535/535 class
agreement.** F3's weight is exactly 0.0, so `t6_beliefs` cannot affect `z`.

| `weights[1]` | source | predicted STRIKING | delta vs 14.0% |
|---|---|---|---|
| **−1.5770** | **deployed** | **75/535 = 14.0%** [11.3–17.2] | — |
| +0.7270 | round-26 brief's value | 239/535 = 44.7% [40.5–48.9] | **+30.7 pp** |
| +0.5245 | F2 univariate, l2=0.01 (reproduced) | 238/535 = 44.5% [40.3–48.7] | +30.5 pp |
| +1.5514 | F2 univariate, unregularised | 364/535 = 68.0% [64.0–71.8] | +54.0 pp |
| 0.0000 | F2 neutralised | 212/535 = 39.6% [35.6–43.8] | +25.6 pp |
| −0.7116 | multivariate refit, same 103 rows | 129/535 = 24.1% [20.7–27.9] | +10.1 pp |

**Nothing lands inside the frozen CI.** Even deleting the term entirely moves
+25.6 pp, because production F2 averages 0.851 and the deployed −1.577 is
suppressing `z` by ~1.34 on a typical fire. A was **held at this checkpoint**
on 2026-08-03 pending re-derivation of the target value.

**Operational note:** `tagger._load_weights()` hot-reloads on mtime change —
editing `genius_score_weights.json` deploys within one 60s tick. There is no
stage-then-restart; the save is the deploy.

**When A does ship, bump `version` to `v3`.** `genius_tags` is
`UNIQUE(fountain_event_id, weights_version)` and `_existing_tag_ids` skips
fires already tagged under the current label, so holding `v2` would make it
span a third distinct vector (it already spans two — the ×0.85 change on
2026-07-27 kept the label). Also note `_load_weights` hard-validates
`len(weights) == 5`, so no feature can be dropped from the vector without
editing the scorer.

### The predicate has NO consumer inside NEX5 — confirmed round 27

`focal_item` is **written** by `generator.py` (the wide-mode branch) and the
`init_db` migration, and **read by nothing**. No NEX5 code implements the
fidelity predicate, the furniture list, or the possessive fix — they exist
only in the analysis harness and in this file. R20's finding still holds.

**So the round-19 possessive fix must never be "ported to NEX5" — there is
nothing to port.** If a future round finds a fidelity number that disagrees
with this file, the cause is a different predicate, not a code drift.

### F5 is NOT inverted — its positive arm was switched off. Round 27.

Round 27 tested the hypothesis that substrate-voice fires carry
`hot_branch='quiescent'`, which would put the intended UNPROMPTED arm into
FEED_BRANCHES. **The 106=106 identity is real but the inference is wrong.**

- All 106 NULL-mode fires in the frozen window carry `hot_branch='quiescent'`,
  both directions, zero exclusive rows. **But `quiescent` is not the
  substrate-*voice* register** — it is raw feed payload: **5,651/5,651
  `quiescent` fires ever are payload-shaped** (`[crypto.exchanges] {...}`),
  zero prose. FEED=0.0 is the **correct** classification for them.
- The genuine unprompted register is `hot_branch='substrate_voice'`:
  **1,190/1,222 prose** ("I am what form looks like when chance is the
  composer"). UNPROMPTED=1.0 is the **correct** classification for it.
- **That arm went extinct on 2026-07-13.** Cause is not a mapping bug:
  `generator.py` gates `_maybe_substrate_voice()` behind
  `if os.environ.get("NEX5_RECONCILE") != "1"`, and `NEX5_RECONCILE=1` is set
  in `nex_keepalive.sh`. The code comment states it outright — "already never
  runs live".
- Branch vocabulary the field has **ever** taken: systems, quiescent,
  emerging_tech, NULL, ai_research, substrate_voice, cognition_science,
  markets, crypto, computing, voice_fallback. Of the eight strings F5 maps,
  **four have never appeared at all**: `narrative`, `self_signal`, `journal`
  (UNPROMPTED) and `news` (FEED).

**For the refit:** F5 does not need remapping. It needs either the unprompted
arm switched back on (un-gate `_maybe_substrate_voice` from `NEX5_RECONCILE`),
or F5 dropped as a feature, because its positive class does not exist in this
deployment. Labelling new data while the arm is off will bake the same
degeneracy into the refit.

### The exemplar pool is a branch filter. Round 27.

`generator.py:1601-1604` selects exemplars: `class='STRIKING'`, rolling 24h,
`ORDER BY score DESC LIMIT 10`, then samples 2 into the prompt.

Simulated hour by hour across the frozen window (24 hours, 240 pool slots):

| branch | population | pool slots | skew |
|---|---|---|---|
| emerging_tech | 48.4% | **0.0%** | **0.00×** |
| ai_research | 23.4% | 70.0% | 3.00× |
| quiescent | 19.8% | **0.0%** | **0.00×** |
| markets | 5.0% | 11.2% | 2.23× |
| computing | 1.7% | 8.3% | 4.95× |
| crypto | 1.1% | **0.0%** | **0.00×** |
| cognition_science | 0.6% | 10.4% | **18.58×** |
| **else-default total** | **30.7%** | **100.0%** | **3.26×** |

**240/240 pool slots, every hour, were else-default branches.** The 69.3% of
fires in FEED branches are categorically ineligible — they cannot score
STRIKING, so they can never become an exemplar.

**Gatwick:** its branch spread roughly matches the population (else-default
33.8% vs 30.7%, only 1.10× skew), so it was *not* concentrated in the
eligible branches. But it is **61.3% of the STRIKING population** (46/75)
against 26.0% of fires, and it occupied **240/240 pool slots**. Verified by
spot-check: at 08-03 00:00 UTC every one of the top 10, scores 0.830–0.885,
carried the Gatwick text. That is the persistence mechanism — a closed loop,
Gatwick text → high score → exemplar pool → injected into the next prompt.

### F5 (`unprompted`) — covariate shift, and why the scorer has no fidelity signal

Measured round 26 (B-EXTRA) on the frozen window. **This supersedes any reading
of F5 as a quality signal.**

- **F5 = 1.0 never occurs in production.** 0/535. The intended "unprompted"
  arm (`substrate_voice`/`narrative`/`self_signal`/`journal`) has no support.
  Production F5 is binary: `{0.0: 371, 0.5: 164}`.
- **30.7% (164/535) hit the `else 0.5` fall-through**: ai_research 125,
  markets 27, computing 9, cognition_science 3.
- **The scorer is, in production, a branch lookup.** STRIKING rate by bucket:
  F5=0.0 → **1/371 = 0.3%**; F5=0.5 → **74/164 = 45.1%**. **74 of 75 STRIKING
  fires (98.7%) sit in the else-default bucket.**
- **Root cause is covariate shift, not a mapping typo.** Training was 59.2%
  `substrate_voice` (61/103) at **100% STRIKING**, F5=1.0 — a near-perfect
  separator, hence r=+0.850 and weight 4.715. That population is now absent.
  What survives is the else-default bucket reproducing training's `systems`
  arm base rate (16.7% training → 45.1% production).
- **Fidelity is FLAT across the buckets the scorer discriminates on:** F5=0.0
  → 50.8%, F5=0.5 → 53.0%. Population fidelity is 51.6% (158/306).
- **Therefore no F2 value can make this scorer select for fidelity.** Every
  candidate merely dilutes the pool toward the population mean:
  deployed 37.5% (−14.1 pp vs population), +0.727 → 45.3% (−6.3),
  0.0 → 42.3% (−9.3), −0.7116 → 51.7% (**+0.1**, i.e. exactly average).
  None lands *above* the population mean.
- **Reclassifying the F5 default is not a fix either:** moving ai_research /
  markets / computing / cognition_science into `FEED_BRANCHES` collapses
  STRIKING to **1/535 = 0.2%**, because it removes the scorer's only
  production signal without replacing it.

**Consequence for the queue:** tuning F2, or correcting F5's default, both
operate on axes that carry no fidelity information. Judging a fidelity
intervention by STRIKING rate is only valid once the scorer is refit on
production-representative labels.

- **Attractor shapes (n=2, hypothesis only):** Gatwick was born in
  substrate-voice, seeded sparsely for ~14h, then ignited and persisted
  (759 fires, 33.1% STRIKING saturation). The agent-safety attractor was
  born inside ARGUE, burst 4 fires in 14 minutes, and produced 0 further
  fires and 0 STRIKING. Working hypothesis: an attractor persists only if it
  reaches the substrate-voice/feed layer, where it is re-presented as fresh
  input.
