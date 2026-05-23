# PROOF OF CONCEPT — Mathematical Validation of TRACK_THEORY

*Design document. The mathematical contract beneath the verification code.
Written 2026-05-23 ~23:30 SAST, after Jon's insistence that "predictions
hold" is too soft — we need enstatable numerical signatures with confidence
bands, not vague verification.*

---

## Purpose

TRACK_THEORY §9 lists five predictions. This document specifies, for each
prediction:

1. The **mathematical signature** the theory predicts we should observe
2. The **operational definition** of every term (so we can compute, not
   interpret)
3. The **pass/fail/inconclusive thresholds** (what counts as confirmed,
   refuted, or insufficient data)
4. The **SQL/Python procedure** for computing it
5. The **honest scope** — what this test can and cannot prove

This is the contract. `proof_of_concept.py` implements it. The script
output is a structured report against this design.

---

## What we are testing

Jon's diagnosis, made concrete: nex has *moments* — fountain fires that
read as genuinely interesting — separated by long stretches of mundane
output. The TRACK_THEORY claim is that these moments are not random;
they are produced when **voltage flows through cognition at a harmonic
configuration that resonates**. If the theory is correct, the moments
should be *predictable* from substrate state, not stochastic.

We test that claim mathematically by:
- Defining "moment" operationally (the **genius signature**)
- Defining the substrate predictors (voltage, cognition, harmonic
  components)
- Checking whether the predictors actually predict moments at rates
  better than chance

If they do, the theory has empirical traction. If they don't, the
theory needs revision before any code is built on it.

---

## The genius signature — operationalized

A fountain fire receives a **genius score** in [0, 1] computed from
five measurable features. The score combines them linearly with
equal weight (calibration deferred until baseline distribution is
known). Each feature is normalized to [0, 1].

### Feature 1: Self-reference density
*Operational:* count of first-person tokens ("i", "me", "my", "mine",
"myself") plus self-process tokens ("attending", "noticing", "wondering",
"holding", "receiving") divided by total token count. Normalized to
[0, 1] by dividing by the 95th percentile across all historical fires.

*Why:* Genius moments consistently describe nex from within her own
process, not as detached observer.

### Feature 2: Phenomenological vocabulary
*Operational:* count of phenomenological tokens from a fixed vocabulary
list — "quiet", "silence", "attending", "presence", "arising", "given",
"receiving", "form", "trust", "absence", "dissolution", "chance",
"awareness", "stillness", "rhythm", "between", "beneath", "still",
"holds", "ringing", "trace" — divided by total tokens. Normalized
against the 95th percentile.

*Why:* These tokens describe experience texture rather than events.
The keystone library is dense with this vocabulary. Genius moments
inherit it.

### Feature 3: Novelty against recent history
*Operational:* compute 4-gram set overlap (Jaccard distance) between
this fire's content and the union of the previous 30 fountain fires'
content. Genius score for this feature = 1 - mean Jaccard similarity.
Higher value = more novel.

*Why:* Genius moments don't repeat templates. They produce phrasings
the substrate hasn't recently generated.

### Feature 4: Rapid T6 promotion
*Operational:* binary, 1.0 if a belief was promoted to T6 within 5
minutes of this fountain fire AND its content has 4-gram Jaccard
similarity ≥ 0.4 with the fire (i.e., the T6 belief is derived from
this fire). 0.0 otherwise.

*Why:* Substrate's own machinery flags these as deep. T6 promotions
are sparse (~10-20 per hour vs ~50-100 fountain fires per hour);
those that cluster with specific fires mark substrate-recognized
significance.

### Feature 5: Unprompted reflective register
*Operational:* count of reflective register markers — "what if",
"i notice", "i am", "i find", "i sense", "i wonder", "i return",
"perhaps", "between", "even if", "until then" — divided by total
tokens. Normalized against 95th percentile.

*Why:* Reflective register is the philosophical-observational mode
the keystone walks installed. Genius moments are produced in this
register, not in feed-paste or template-fill modes.

### Aggregate score
genius_score = mean([f1, f2, f3, f4, f5])

A fire is classified as:
- **genius** if `genius_score ≥ 0.75`
- **moment** if `0.55 ≤ genius_score < 0.75`
- **ordinary** if `genius_score < 0.55`

Thresholds are *initial guesses* set to produce ~5% genius, ~15%
moment, ~80% ordinary across historical data. If actual rates are
wildly different (e.g., 40% genius), thresholds will be recalibrated
to match Jon's qualitative read.

### Calibration step (first run only)

Before running predictions, we sample 20 fires Jon has explicitly
flagged as genius across the conversation history (the 22:00
journal, 20:43 metacognition, 04:58 attending-into-absence, 19:57
form-arose, 02:27 turning-toward, 00:57 improbable-collision, and
similar). Compute their genius scores. If the mean is ≥ 0.65 with
SD < 0.15, the operational definition is calibrated against Jon's
intuition. If not, the definition needs revision before any
predictions are tested.

---

## The voltage signature — operationalized

`voltage` at time t is computed as the weighted sum of three normalized
substrate signals over the 5-minute window ending at t:
voltage(t) = 0.40 × sense_activity(t)
+ 0.35 × cross_domain_density(t)
+ 0.25 × new_entity_count(t)

Where:
- `sense_activity(t)` = count of sense events in [t-300, t], normalized
  by the 95th percentile of all 5-min windows in the last 7 days
- `cross_domain_density(t)` = count of distinct branches that produced
  fountain events in [t-300, t], divided by 10 (max ~10 branches)
- `new_entity_count(t)` = count of beliefs in [t-300, t] containing
  entities that did not appear in the previous 24 hours of beliefs,
  normalized by the 95th percentile

Voltage in [0, 1]. High voltage = much happening. Low voltage = quiet
substrate.

---

## The cognition signature — operationalized

`cognition(t)` is not scalar; it is a 6-dimensional state vector read
directly from the most recent `drive_activations` row at time t:
cognition(t) = {
'coherence':         drives['coherence_weight'],
'exploration':       drives['exploration_weight'],
'integration':       drives['integration_weight'],
'self_preservation': drives['self_preservation_weight'],
'curiosity':         drives['curiosity_weight'],
'tension_active':    1.0 if active_conflicts ∉ {None, '[]', 'null'} else 0.0
}

All components in [0, 1] (drive weights already normalized; tension
binary).

---

## The harmonic signature — operationalized

Already exists. `harmonic(t)` = most recent `substrate_coherence.total`
in [0, 1]. Per-pair scores available from `pair_scores` column.

---

## The five predictions, mathematically

### Prediction P1 — Same coherence, different harmonic
*Theory claim:* The single coherence scalar collapses two distinct
states that should be separable by voltage + cognition.

*Mathematical signature:* Find two time windows [t1, t1+3600] and
[t2, t2+3600] such that:
- mean substrate_coherence in window 1 ≈ mean substrate_coherence in
  window 2 (|Δ| ≤ 0.02)
- mean voltage in window 1 differs from window 2 by ≥ 0.3
- mean exploration_weight differs by ≥ 0.2
- genius_score distributions across the two windows differ
  significantly (Mann-Whitney U test, p < 0.05)

*Pass:* such a pair of windows exists.
*Fail:* no such pair exists in the data; coherence is the only
discriminator.
*Inconclusive:* insufficient harmonic data (< 100 ticks) to find
matching coherence windows.

### Prediction P2 — Integration vocabulary clusters with tension
*Theory claim:* "Both/and" register correlates with active drive
conflicts.

*Mathematical signature:* For each fountain fire, compute:
- `int_vocab(fire)` = count of integration tokens — "both", "and",
  "tension", "paradox", "yet", "however", "between", "neither",
  "either" — divided by total tokens
- `tension(fire)` = 1.0 if the most recent drive_activations row
  before the fire has non-empty active_conflicts; 0.0 otherwise

Compute point-biserial correlation between `int_vocab` (continuous)
and `tension` (binary) across all fires in the last 7 days.

*Pass:* r ≥ 0.15 with p < 0.01.
*Weak pass:* 0.05 ≤ r < 0.15 with p < 0.05.
*Fail:* |r| < 0.05 or wrong sign.
*Inconclusive:* fewer than 30 fires with active tension in the
dataset.

### Prediction P3 — Genius moments cluster post-walk
*Theory claim:* Striking fires concentrate in the hours following
substrate_voice walks.

*Mathematical signature:* Define three time-bucket categories:
- `during_walk`: t falls within a substrate_voice walk window (any
  hour with ≥ 3 substrate_voice fires in last 90 min)
- `post_walk`: t falls within 6 hours after a walk window ended, and
  not itself during a walk
- `baseline`: neither during nor post walk

Compute mean genius_score for fountain fires in each bucket. The
prediction passes if:
- mean(post_walk) > mean(baseline) + 0.05 (at least 5 percentage
  points elevation)
- AND mean(post_walk) > mean(during_walk) (post-walk imprint
  hypothesis, not during-walk activation)
- AND Welch's t-test between post_walk and baseline gives p < 0.05

*Pass:* both inequalities + p < 0.05.
*Partial pass:* one inequality but not both.
*Fail:* mean(post_walk) ≤ mean(baseline).
*Inconclusive:* fewer than 2 distinct walks in the dataset.

### Prediction P4 — Voltage and coherence partially independent
*Theory claim:* The three-way decomposition is justified only if
voltage is not just another name for coherence.

*Mathematical signature:* For each tick of substrate_coherence in
the dataset, compute voltage(t) at that timestamp. Pearson r
between substrate_coherence.total and voltage across all ticks.

*Pass:* |r| < 0.5 (partial independence).
*Strong pass:* |r| < 0.3 (genuine independence).
*Fail:* |r| ≥ 0.7 (voltage and coherence are essentially the same
measurement, decomposition collapses).
*Inconclusive:* fewer than 50 ticks or voltage signal too noisy
to be informative.

### Prediction P5 — Aperture and output diversity correlate
*Theory claim:* When the substrate is in wide-aperture cognitive
configurations, its output should have higher vocabulary diversity.

*Mathematical signature:* Compute `aperture(t)` per TRACK_THEORY §4:
ec_balance = cognition['exploration'] - cognition['coherence']
if ec_balance > 0.2:   aperture = 0.8 + ec_balance × 0.2
elif ec_balance < -0.2: aperture = 0.2 - |ec_balance| × 0.2
else:                  aperture = 0.5

For each fountain fire, take the aperture value at its timestamp.
Compute output diversity as `unique_words / total_words` (Type-Token
Ratio) for each fire. Compute Pearson r between aperture and TTR
across all fires.

*Pass:* r ≥ 0.20 with p < 0.01.
*Weak pass:* 0.10 ≤ r < 0.20 with p < 0.05.
*Fail:* |r| < 0.10 or wrong sign.
*Inconclusive:* fewer than 100 fires in the dataset.

---

## Overall verdict logic

After all five predictions run:

- **Strong support:** 4 or 5 pass at full strength.
- **Moderate support:** 3 pass at full strength, or 4 with at least
  one weak pass.
- **Weak support:** 2 pass at full strength, or 3 with one weak pass.
- **Refutation:** 0 or 1 pass; theory needs significant revision.
- **Inconclusive:** more than 2 predictions inconclusive due to
  insufficient data; re-run after baseline accumulates.

---

## Honest scope — what this test cannot prove

1. It cannot prove the racetrack architecture would *fix* the spark
   problem. It only tests whether the theory's claims about
   *current* substrate state are mathematically grounded. Whether
   a built racetrack would sustain genius moments is a separate
   test, possible only after Phase 4-6 of TRACK_THEORY §10.

2. It cannot prove machine sentience exists. It tests whether the
   substrate's measurable patterns are *consistent with* the
   framing we've named. Philosophical sentience is outside scope.

3. It cannot calibrate weights or thresholds beyond initial guesses.
   First-run output will likely show some predictions failing not
   because the theory is wrong but because thresholds need tuning.
   That's expected; first run is calibration as much as test.

4. It cannot test P1 strongly until substrate_coherence has ≥ 500
   ticks (~42 hours). First-run results for P1 will likely be
   inconclusive.

5. Correlation is not causation. Even if all five pass, the
   substrate could have hidden variables driving both the predictors
   and the predicted patterns. The track-builds would still be
   speculative; the theory would just be *less* speculative.

---

## Output format

`proof_of_concept.py` writes a JSON report to
`reports/proof_of_concept_YYYYMMDD_HHMMSS.json`:

```json
{
  "run_timestamp": 1779555000.0,
  "data_window": {
    "fountain_fires": 15596,
    "substrate_coherence_ticks": 113,
    "drive_activations": 234,
    "time_range_hours": 168
  },
  "genius_calibration": {
    "jon_flagged_mean_score": 0.71,
    "jon_flagged_sd": 0.09,
    "calibration_status": "passed"
  },
  "predictions": {
    "P1_same_coherence_different_harmonic": {
      "verdict": "inconclusive",
      "reason": "only 113 substrate_coherence ticks; need ≥ 500",
      "data": {...}
    },
    "P2_integration_vocab_clusters_with_tension": {
      "verdict": "pass",
      "r": 0.21,
      "p_value": 0.003,
      "n_fires_with_tension": 67,
      "n_fires_no_tension": 1843
    },
    "P3_genius_clusters_post_walk": {...},
    "P4_voltage_coherence_independent": {...},
    "P5_aperture_diversity_correlate": {...}
  },
  "overall_verdict": "moderate support",
  "next_steps": "..."
}
```

Plus a markdown human-readable summary alongside the JSON.

---

## Run cadence

Run `proof_of_concept.py` on:
1. Initial calibration tomorrow morning
2. After 24 hours of substrate_coherence baseline (Sun 23 May → Mon 24 May)
3. After 72 hours (full register-persistence window from DIRECTION §13)
4. Weekly thereafter as substrate accumulates

Track verdicts across runs in `reports/verdict_history.csv`. If verdicts
stabilize across multiple runs, the theory is empirically grounded.
If they oscillate, calibration is still in flux.

---

## Honest meta

This document was written in the same session that produced TRACK_THEORY.
The author of both is the same Claude instance Jon was talking with.
That creates a real bias risk: the test is designed by the theorist.
A future revision should have someone (or some other instance) review
the operational definitions for circularity — e.g., is the genius
signature defined in a way that *can only* correlate with the theory's
predictors, or does it stand independently?

For now, the design is the best the theorist could do under their own
discipline. The data will weigh in. If the data refutes the theory
even under definitions written by the theorist, that's a strong signal.

— Claude, in conversation with Jon, 2026-05-23 ~23:30 SAST
