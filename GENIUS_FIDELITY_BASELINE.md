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

## 2. The furniture list (108 terms)

*(Round 31: the heading previously read "86 terms". The list below is correct
and matches `crystallizer.py` exactly — `len(frozenset(...)) == 108`. Only the
count was wrong; nothing measured against it needs redoing.)*

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

### ⚠️ The predicate IS production code as of round 29

`crystallizer.py` `_is_on_subject()` / `_fidelity_tokens()` implement section 1
and gate the crystallization length limit: **on-subject → 600 chars,
everything else → 300**. This file is the authority; **the two must be kept in
step.** If you change the furniture list or the tokenizer here, change it
there, and re-read section 3b — the predicate now affects which beliefs exist.

Fail-safe contract: `_is_on_subject` swallows every exception and returns
`False`, which yields the *current* 300 limit. It can never fail open.

*(Superseded below: the statement that the predicate has no consumer was true
through round 28 and is retained for history.)*

### The predicate had NO consumer inside NEX5 — round 27, superseded by round 29

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

---

## 5. maxDF* — the corpus-convergence metric (round 31)

Shipped as `theory_x/stage6_fountain/corpus_convergence.py` +
`theory_x/stage6_fountain/register_exclusion.json`. **Read-only
instrumentation.** Not on the fire path, gates nothing, writes nothing, opens
the DB `mode=ro`. Run it with:

```
python3 -m theory_x.stage6_fountain.corpus_convergence [--history N]
```

### What it measures, and why nothing else could see it

Every per-fire check — the fidelity predicate, the scorer, `_quality_check` —
scores **one row at a time**. The failure mode documented in round 27 is not a
property of any row: a single story scores STRIKING, saturates the exemplar
pool, is copied into the next prompt, and scores STRIKING again. Each fire in
that loop passes every check. What has degraded is the **corpus**.

    maxDF* = over the rolling 50 most recent crystallized beliefs
             (`source='fountain_insight'`), the largest document-frequency
             share reached by any single content token, after excluding
             NEX5's own standing register.

Document frequency = the share of those 50 beliefs a token appears in *at all*.
Tokenisation is `_fidelity_tokens()` **imported from `crystallizer.py`** — not
re-declared — so section 1's predicate keeps exactly one definition.

maxDF* is **not** a fidelity metric. Fidelity asks "did this fire stay on its
assigned subject". maxDF* asks "is the corpus still about more than one thing".
A run can be 100% subject-faithful and still converging, because the *subjects*
are what collapsed. Round 30's Gatwick finding is the worked example.

### The register exclusion is the whole trick

Without it the answer is always `quiet` or `hum` — that is her voice, not a
convergence. The 40 excluded terms are the top-40 by DF over the fitting
corpus. `societal`, the token now driving the reading, is **not** in the list
(1.2% global DF), so the signal survives its own exclusion.

**This list is fitted data and it will drift.** `register_exclusion.json`
carries `fitted_on`, the corpus definition, the window, and `n_documents`
precisely so a later session knows whether to refit. **Refit only on a corpus
with no active convergence in it** — otherwise the convergence gets absorbed
into the register and the metric goes blind to it.

Fitted 2026-08-04 on 1,101 `fountain_insight` beliefs, 45-day window.
Stability: withholding the last 7 or 14 days keeps **33/40** terms and leaves
the backtest quantiles **identical**. The metric does not depend on the churn
in the tail of the list.

### Backtest — 45 days to 2026-08-04, 1,054 rolling windows

| statistic | value |
|---|---|
| median | **12%** |
| p90 | **18%** |
| p99 | **22%** |
| threshold | **25%** |

The threshold sits just above the observed p99 and is deliberately coarse: at
N=50 one belief is 2 percentage points, so anything finer is quantisation
noise. Insensitive to the fit: lagging the exclusion-list fit by 0, 7 or 14
days reproduces 12 / 18 / 22 exactly.

### Reading at ship time — 2026-08-04 10:32 UTC

**maxDF\* = 26.0%, driven by `societal` (13/50 beliefs). Over threshold.**
Runners-up: `broader` 16%, `technologies` 14%, `research` 12%.

`societal` **is still climbing**, and monotonically. Rolling-50 DF by day:

| day | 07-20 → 07-29 | 07-30 | 07-31 | 08-01 | 08-02 | 08-03 | 08-04 |
|---|---|---|---|---|---|---|---|
| maxDF*(`societal`) | 0% | 2% | 6% | 6% | 2% | 12% | **26%** |

It crossed 25% for the first time on 2026-08-04 at ~10:20 UTC. Note this is a
**successor** to the Gatwick attractor, not the same one: the run of readings
immediately before it was driven by `benefits`.

### Is this checked by hand, or should it alert?

**By hand for now, and it should eventually alert — but not yet.** The honest
reason is that the threshold has been crossed exactly once, so its false-alarm
rate is unmeasured. The p99 = 22% comes from a corpus that *contains* the
Gatwick episode, which means the baseline is contaminated by the very thing the
metric is for; a clean baseline needs a stretch of corpus with no attractor in
it, and there isn't one yet in the 45 days available.

What makes it alertable later, and what does not:

- **It is cheap and stateless** — one query, one pass over 50 short strings.
- **It names the token**, so an alert would be actionable rather than just a
  number going red.
- **But it has no hysteresis.** It sat at 22% for three separate readings on
  08-04 before crossing. A naive threshold alert would flap.
- **And the register list drifts.** An alerter that silently uses a stale
  `fitted_on` list will drift into either constant firing or permanent silence.
  Any alerting must read `fitted_on` and warn when it is stale.

The sequencing that follows from this: **check it by hand for one clean
attractor-free stretch, refit the register list on that stretch, re-derive p99
from it, and only then decide the alert threshold.** Alerting built before that
would be calibrated on a contaminated baseline.

---

## 6. Round 31 corrections to the standing record

- **The fidelity tripwire's denominator is FOCAL-BEARING CRYSTALLIZATIONS
  ONLY.** DRIFT and substrate-voice bind no `focal_item`, so `_is_on_subject`
  returns `False` for them **by construction** — they can never pass, and
  including them makes the tripwire read low no matter what the wide modes do.
  Measured since the R29 restart: **19/23 = 82.6%** on the correct denominator;
  the same numerator over all 38 crystallizations reads **50.0%** and would
  have caused a false revert.
- **The furniture list in section 2 is 108 terms, not 86.** The list itself is
  correct and matches `crystallizer.py`; only the count in the heading was
  wrong. Nothing measured against it needs redoing.
- **The 60-char-prefix convergence metric is discarded as degenerate.**
  Superseded by section 5.
- **There is no ~200 beliefs/day ceiling.** Normal is 495–736/day.
- **Cadence band is ~124–203s**, not 124–195s.

### Restart discipline — and a correction to the round-30 note

One change per restart, and record the restart time in the commit. The journal
(`journalctl --user -u nex5-keepalive.service`) is the authority. Round 30
recorded R27 and R29 as sharing a 16:32 restart and being permanently
unseparable. **That is not what happened.** The three restarts on 2026-08-03,
mapped against commit times (all UTC):

| restart (UTC) | carried | separable? |
|---|---|---|
| 14:02:30 | `3d91731` — documentation only | n/a, no code |
| 15:58:36 | `81b04ad` (B1 residue) **+** `522fbb0` (B4 dedup) | **no — these two are confounded with each other** |
| 16:30:02 | `7c04a56` (R29 fidelity-gated crystallization) | **yes — R29 shipped alone** |

So R29 is cleanly separable and does not need reverting for attribution.
**What is confounded is B1 with B4.**

The real trap is a different one: R29's live window opens at 16:30 UTC, which
is entirely *downstream* of B1+B4. Comparing R29-live against the frozen window
therefore measures R29 **and** B1 **and** B4 together. Any before/after across
that boundary must say so — see the EXPLAIN fidelity drop in section 8, which
is **not** attributable to R29.

---

## 7. Where the preamble enters (round 31, investigation only — no change made)

Round 30 established that the contamination is **positional**: it arrives at
the start of the output, and 0 of the affected wide fires had a contaminated
focal item. Thirty rounds had looked for a block whose *content* leaks. This
section answers the different question — why it is a **preamble**.

Contaminant is matched as the cluster `gatwick | youth benefit | security
camera | welfare benefit`. That definition reproduces section 4's recorded
figures exactly (**139/535 = 26.0%** of all fires, **49.7% of ARGUE**), so it
is the same population earlier rounds measured. Within the frozen window it is
**135/306 wide fires** (EXPLAIN 63/161 = 39.1%, ARGUE 72/145 = 49.7%).
*(Round 30 reported 103; the literal-`gatwick` count is 129. The 103 is not
reproducible from the frozen window and should not be re-used.)*

### 7.1 Position — OBSERVED

| measure | value |
|---|---|
| first cluster mention in **sentence 0** | **113/135 = 83.7%** |
| sentence 1 | 12 (8.9%) |
| sentence 2+ | 10 (7.4%) |
| first **clause** of its own sentence | **128/135 = 94.8%** |
| character offset, as fraction of output | median **0.090**, p90 0.423 |
| cluster present in the fire's own `focal_item` | **0/135** |

It is a preamble, quantitatively.

### 7.2 The continuation hypothesis is FALSE — OBSERVED

The model is **not** completing the last thing in the prompt.

`_build_prompt` ends, invariably, with the world-bridge block
(`"What's happening in the world right now:"`) or its fallback, then the single
line `Time: … | Beliefs held: …`. `world_bridge_log` records the exact injected
payload per selection, so the true prompt tail is recoverable. Matching each of
the 135 fires to its world-bridge row (**135/135 matched within 400s**):

- cluster text in the **last** world-bridge line: **0/135**
- cluster text **anywhere** in the injected world-bridge block: **0/135**
- 430 world-bridge rows in the frozen window carry the cluster: **0**

Reconstructed tails are proprioception JSON, Alexandre Dumas, opioid
pharmacology. The last ~200 characters of a contaminated prompt are never the
contaminant. **Rule this out and do not re-test it.**

### 7.3 The insertion point — OBSERVED

`generator.py:2443` → `_build_recent_striking_block()`, rendered under the
header **`"Recent voice of yours that landed as itself:"`**, two exemplars
sampled from the top-10 STRIKING of the last 24h, each truncated to 280 chars.

Replaying that pool exactly from `genius_tags` for every wide fire in the
frozen window:

| | fires with ≥1 cluster exemplar in pool | cluster share of pool slots |
|---|---|---|
| cluster-carrying fires (135) | **135/135 = 100%** | **1350/1350 = 100%** |
| clean fires (171) | **171/171 = 100%** | **1710/1710 = 100%** |

This reproduces round 27's 240/240. Saturation is total and it is **identical
in both groups** — so the block is the **carrier**, but it has **zero
discriminating power** as a trigger. Every prompt in the window contained the
contaminant. Only 44% of outputs emitted it.

Two other candidates were tested and eliminated: the identity block
(`identity_log`, exactly replayable) carries the cluster in **0/135** and
**0/171**; the world-bridge block in 0/430 as above.

### 7.4 The mechanism is verbatim transcription, not paraphrase — OBSERVED

For every wide fire, the 5-gram overlap between the **first sentence of the
output** and the first sentence of the best-matching exemplar then in its pool:

| group | n | median overlap | ≥0.5 | ≥0.8 | exact (1.0) |
|---|---|---|---|---|---|
| cluster-carrying | 135 | **1.00** | 76.3% | 67.4% | **60.0%** |
| clean | 171 | **0.00** | **0.0%** | 0.0% | 0.0% |

Perfect separation. Not one clean fire copies an exemplar opening; 60% of
contaminated fires reproduce one **verbatim**.

The opening 6 words say the same thing. Contaminated: `"this headline
discusses changes to youth"` ×70, `"the headline discusses changes to youth"`
×24. Clean: `"the item you provided is about"`, `"this item discusses a
technique called"` — i.e. answering the instruction, which names its subject
as *"One item from your feeds"*.

**The two populations are behaviourally binary: a fire either answers the
instruction or transcribes the exemplar.** Round 30's "hybrids" are the fires
that do the second and then recover into the first.

### 7.5 The mechanism — REASONED

The exemplar block is a **few-shot demonstration presented as the model's own
best voice**, placed ~10 blocks below the task instruction and separated from
it by thousands of characters. Few-shot exemplars teach form, and the first
thing a form specifies is how to open. When 10/10 exemplars open with the same
sentence, "how to open" and "what to say first" are indistinguishable in the
demonstration — so the opening is copied with its content attached. The fire
then either has enough grip on its own focal item to pivot (hybrid) or does
not (fully off-subject).

This also explains the **closed loop** round 27 identified, and why it
ratchets: a transcribed opening is scored by a scorer that (section on F5)
is in production a branch lookup carrying no fidelity signal, so the copy
scores as well as the original and re-enters the pool.

The block has a groove filter, but its static term list is
`("gentle thread", "hum indeed", "weave a gentle", "resonate for you")` — the
2026-05 hum groove. It cannot see a new attractor.

### 7.6 Ignition timeline — OBSERVED

Cluster share of the top-10 exemplar pool, sampled at 00:00 UTC daily:

| 07-24 → 07-27 | 07-28 | 07-29 | 07-30 | 07-31 | 08-01 → 08-04 |
|---|---|---|---|---|---|
| 0% | 60% | 80% | 70% | 80% | **100%** |

Seed: belief **225184**, `source='precipitated_from_sense'`, created
2026-07-26 23:10 — `"UK papers: Youth benefits 'crack down' and Gatwick 'Fly
and dry'"`. It is the **only** ingested item carrying the cluster; the
"security camera system" detail appears nowhere in it and is confabulated,
then propagated verbatim from that point on. By 08-01 the pool is fully closed.

Her own crystallized copies now also sit in the affinity pool
(belief 234481, affinity 0.484, `use_count` 15; belief 233368, affinity 0.524)
— above the 0.40 threshold of the "Beliefs you've come to feel as deeply
yours" block at `generator.py:2418`. **REASONED:** that is a second, slower
re-entry path that outlives the 24h exemplar window.

### 7.7 Is a preamble effect compatible with round 18's nulls? — REASONED

**Yes, and R18 is not wrong.** But the reason is not the one proposed.

R18 added each block to a clean baseline and measured no effect. That design
would in fact have detected a purely positional effect, since adding a block
places it somewhere. What it cannot detect is what is actually happening:

1. **The block's harm is a function of its contents, and its contents are
   state.** `_build_recent_striking_block` renders whatever the STRIKING
   top-10 currently holds. Tested against a diverse pool it is inert — that is
   R18's null, and it was a true reading of the system at the time. Tested
   against a 100%-saturated pool it transcribes. The block is a mirror; R18
   measured the mirror in a clean room.
2. **The effect is a feedback loop, and R18's design is single-shot.** The
   mechanism requires the block's output to re-enter its own input. One-fire
   A/B cannot express a fixed point. The ignition curve in 7.6 takes **five
   days** to close.

So R18's nulls and the preamble effect are both correct and describe different
regimes. **Consequence: no additive A/B on the exemplar block will ever
reproduce this.** The block must be tested against a *saturated* pool, or the
saturation itself must be measured — which is what section 5's maxDF* does.

---

## 8. Why EXPLAIN missed its R29 prediction (round 31, investigation only)

R29 predicted EXPLAIN 0.0% → 34.8%. Delivered, over the 17.9h since the
16:30:02 UTC restart: **EXPLAIN 6/118 = 5.1%**, ARGUE 17/101 = 16.8%,
DRIFT 15/82 = 18.3%.

### 8.1 EXPLAIN did not lengthen — it shortened. OBSERVED.

| | frozen window | post-R29 live |
|---|---|---|
| EXPLAIN median length | 491 | **426** |
| EXPLAIN p75 / p90 | 688 / 859 | 576 / 731 |
| EXPLAIN >600 chars | 34.2% | **23.7%** |
| ARGUE median length | 432 | 403 |

**Length is not the problem.** The R29 ceiling is doing its job: EXPLAIN
`too_long` rejects fell 153 → 65.

### 8.2 The gate it fails is `no_engagement`, not `too_long`. OBSERVED.

`_quality_check` is sequential — length is checked at `crystallizer.py:584`,
engagement at `:587`. Raising the ceiling did not admit fires; it **moved them
to the next gate**. EXPLAIN `no_engagement` rejects went **5 → 43**.

Replaying the real gates in code order:

| gate (survivors) | EXPLAIN | ARGUE |
|---|---|---|
| fires | 118 (100%) | 101 (100%) |
| survive `too_long` (R29 gate) | 53 (44.9%) | 49 (48.5%) |
| **survive engagement gate** | **10 (8.5%)** | **32 (31.7%)** |
| *of the length-survivors, fail engagement* | **43 (81.1%)** | 17 (34.7%) |

### 8.3 The cause is that two prompts contradict each other. OBSERVED + REASONED.

`_has_engagement` passes on `_SELF_REF_RE = \b(I|my|me|myself|mine|within|
inside)\b`, or a `?`, or an engagement keyword **with** a concrete anchor.
Among post-R29 length-survivors:

| | first-person self-ref | contains `?` | engagement keyword |
|---|---|---|---|
| EXPLAIN | **15.1%** | 0.0% | 5.7% |
| ARGUE | **65.3%** | 0.0% | 20.4% |

`_MODE_EXPLAIN` instructs: *"Do NOT be contemplative, **do NOT write about
yourself**"*. `_MODE_ARGUE` instructs: *"in plain **first person**"*. The
engagement gate's main door is first-person reference. **EXPLAIN is told to do
the one thing the crystallizer requires; ARGUE is told to do it.** The 8.5%
vs 31.7% split is that instruction, measured.

### 8.4 The prediction was wrong against its own frozen window. OBSERVED.

Replaying the frozen window under the *shipped* R29 code gives EXPLAIN
**30/161 = 18.6%**, not 34.8%. 34.8% ≈ 56/161 is what the length gate alone
admits (64) less the dedup/blacklist gates (~8) — i.e. **the offline
prediction did not apply the engagement gate**, which removes a further 34.
This is a harness error in the R29 prediction, not a covariate shift.

There is *additionally* a covariate shift: EXPLAIN fidelity fell
**66.5% → 46.6%** across the boundary. Per section 6 that boundary also
contains B1 and B4, so **this drop is not attributable to R29.**

### 8.5 Answer to "is the fix a higher ceiling for EXPLAIN?"

**No.** EXPLAIN clears the ceiling at 44.9% and dies at the engagement gate at
81.1%. Raising the ceiling further can add at most the 23.7% now over 600, and
those fires face the same 81.1% engagement failure. Nothing is proposed here.
