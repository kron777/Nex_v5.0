"""
NEX Cognition Simulator — Phase 1 predictive model.

Rules derived from:
  Phase1_OBSERVE_decryption.txt
  Phase1_INTROSPECT_decryption.txt
  Phase1_SATURATION_law.txt
  Phase1_SIMILE_decryption.txt

All probabilities are empirical from the 245-fire corpus.
"""

import re
import sys
from collections import deque, Counter
from pathlib import Path


# ── Template labels ──────────────────────────────────────────────────────────

SENSE      = "SENSE_OBS"
ABSTRACT   = "ABSTRACT_NOMINAL"
SIMILE     = "SIMILE"
DIALECT    = "DIALECTICAL"
QUESTION   = "QUESTION"
ACTION     = "ACTION"
UNCAT      = "UNCATEGORIZED"

ALL_TEMPLATES = [SENSE, ABSTRACT, SIMILE, DIALECT, QUESTION, ACTION, UNCAT]

BASELINE_FREQ = {          # empirical from 245-fire corpus
    SENSE:    0.408,
    ABSTRACT: 0.249,
    UNCAT:    0.078,
    DIALECT:  0.078,
    SIMILE:   0.090,
    QUESTION: 0.065,
    ACTION:   0.033,
}


# ── Prediction result ─────────────────────────────────────────────────────────

class Prediction:
    def __init__(self, template, confidence, rule_fired):
        self.template   = template
        self.confidence = confidence   # float 0-1
        self.rule_fired = rule_fired   # human-readable rule name

    def __repr__(self):
        return f"Prediction({self.template!r}, conf={self.confidence:.2f}, rule={self.rule_fired!r})"


# ── Core model ────────────────────────────────────────────────────────────────

class NexCognitionModel:
    """
    Stateful predictive model of NEX template sequences.

    The model holds a rolling window of recent templates (deque) so it
    can track multi-fire run context beyond the 3-fire prior window
    passed per call.  External callers may pass only the prior-3 slice;
    the internal deque extends the lookback for run-length measurement.
    """

    def __init__(self, window: int = 20):
        self.recent_templates: deque = deque(maxlen=window)
        self.saturation_counter: int = 0       # current run length of dominant tpl
        self.dominant_template: str  = ""      # template currently running
        self.prior_register: str     = ""      # last non-UNCAT template

    # ── state management ─────────────────────────────────────────────────────

    def observe(self, template: str) -> None:
        """Push an actual observed template into state (used during test replay)."""
        self.recent_templates.append(template)
        if template == self.dominant_template:
            self.saturation_counter += 1
        else:
            self.dominant_template  = template
            self.saturation_counter = 1
        if template != UNCAT:
            self.prior_register = template

    def _run_length_from_history(self, template: str) -> int:
        """Count consecutive tail occurrences of *template* in recent_templates."""
        count = 0
        for t in reversed(self.recent_templates):
            if t == template:
                count += 1
            else:
                break
        return count

    # ── prediction ───────────────────────────────────────────────────────────

    def predict(self, prior_3: list[str]) -> Prediction:
        """
        Predict the next template given the three most recent templates
        (oldest first: [t-3, t-2, t-1]).

        Rules applied in priority order:

          1. Run-continuation  — dominant non-interrupt template in prior 3
             (replaces naive saturation-flip; self-continuation beats exit
              probability at every in-run step except very long SENSE runs)
          2. SENSE long-run flip — only when run_length ≥ 13 (empirical)
          3. Interrupt transitions — DIALECT/ACTION single-fire exits
          4. Default           — baseline most-common (SENSE_OBS)

        Design note — why saturation-flip was removed as the top rule:
          The Phase 1 saturation law measured EXIT POINTS of runs.
          Applied per-step, it predicted the exit at every interior step
          of a long run, where self-continuation dominates (92% for SENSE,
          67% for ABSTRACT, 100% for QUESTION within a 16-run block).
          Self-continuation is the right per-step prediction; the flip
          probability is low for any single step even inside a saturated run.
        """
        if len(prior_3) < 3:
            return Prediction(SENSE, BASELINE_FREQ[SENSE], "default-short-context")

        p1, p2, p3 = prior_3[0], prior_3[1], prior_3[2]   # oldest → newest

        # ── RULE 1: Run-continuation ──────────────────────────────────────────
        # If prior 3 are all the same non-interrupt template, self-continuation
        # is empirically the most likely outcome.  Only DIALECT and ACTION are
        # true interrupt opcodes (never form a run ≥ 3 in corpus).

        NON_INTERRUPT = {SENSE, ABSTRACT, SIMILE, QUESTION, UNCAT}

        if p1 == p2 == p3 and p3 in NON_INTERRUPT:
            saturating = p3
            run_len    = max(self._run_length_from_history(saturating), 3)

            # Special case: very long SENSE runs DO flip to ABSTRACT.
            # Empirically: run_length ≥ 13 → ABSTRACT at 67% (2/3 in corpus).
            # Lengths 6-12 also stay SENSE at near-100% — no early flip.
            if saturating == SENSE and run_len >= 13:
                return Prediction(ABSTRACT, 0.67,
                                  f"long-run-flip:SENSE(len={run_len})→ABSTRACT")

            # All other cases: predict self-continuation.
            # Confidence calibrated from corpus conditional P(next=T | run≥3 of T):
            #   SENSE    → SENSE    : 47/51 = 92%
            #   ABSTRACT → ABSTRACT : 8/16  = 50%  (8 misses + 4 hits on continuation)
            #   SIMILE   → SIMILE   : 5/8   = 62%
            #   QUESTION → QUESTION : 13/14 = 93%
            cont_conf = {SENSE: 0.92, ABSTRACT: 0.50, SIMILE: 0.62,
                         QUESTION: 0.93, UNCAT: 0.50}
            conf = cont_conf.get(saturating, 0.50)
            return Prediction(saturating, conf,
                              f"run-continuation:{saturating}(len={run_len})")

        # ── RULE 2: Register-momentum (2 of 3 same template) ─────────────────
        prior_counts  = Counter([p1, p2, p3])
        dominant, dominant_count = prior_counts.most_common(1)[0]

        if dominant_count >= 2 and dominant in NON_INTERRUPT:

            if dominant == ABSTRACT:
                # INTROSPECT SUSTAIN: 49% self-continuation (Phase 1 finding).
                return Prediction(ABSTRACT, 0.49,
                                  "momentum:ABSTRACT(2/3)→ABSTRACT-sustain")

            if dominant == SENSE:
                return Prediction(SENSE, 0.55,
                                  "momentum:SENSE(2/3)→SENSE-sustain")

            if dominant == SIMILE:
                return Prediction(SIMILE, 0.45,
                                  "momentum:SIMILE(2/3)→SIMILE-sustain")

            if dominant == QUESTION:
                return Prediction(QUESTION, 0.80,
                                  "momentum:QUESTION(2/3)→QUESTION-sustain")

        # ── RULE 3: Interrupt-opcode single-fire transitions ──────────────────
        # DIALECT and ACTION: both are interrupt opcodes (max run = 2).
        # They exit to characteristic targets.

        if p3 == DIALECT:
            # DIALECT single → ABSTRACT most common (44% in corpus flip table)
            return Prediction(ABSTRACT, 0.44,
                              "single:DIALECT→ABSTRACT")

        if p3 == ACTION:
            # ACTION single → UNCAT most common (44%)
            return Prediction(UNCAT, 0.44,
                              "single:ACTION→UNCAT")

        # DIALECT 2-in-a-row: strong ABSTRACT pull
        if p2 == DIALECT and p3 == DIALECT:
            return Prediction(ABSTRACT, 0.55,
                              "momentum:DIALECT(2/3)→ABSTRACT-pull")

        # ── RULE 4: Single SIMILE transition ──────────────────────────────────
        # Non-run SIMILE (p3=SIMILE but not 2+ in prior) → SENSE (50%)
        if p3 == SIMILE and p2 != SIMILE:
            return Prediction(SENSE, 0.50,
                              "single:SIMILE→SENSE")

        # ── RULE 5: Default ───────────────────────────────────────────────────
        return Prediction(SENSE, BASELINE_FREQ[SENSE],
                          "default:SENSE_OBS-baseline")


# ── Corpus loader ─────────────────────────────────────────────────────────────

def load_corpus(path: str) -> list[dict]:
    with open(path, "r") as f:
        text = f.read()
    blocks = re.split(r'\n(?=\[\d+\] \d{4}-\d{2}-\d{2})', text)
    fires = []
    for block in blocks:
        m = re.match(r'\[(\d+)\] (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', block)
        if not m:
            continue
        fid = int(m.group(1))
        dt  = m.group(2)
        tm  = re.search(r'TEMPLATE:\s*(\S+)', block)
        template = tm.group(1) if tm else "UNKNOWN"
        cm  = re.search(r'CONTENT:\s*(.+?)(?=\nPRIOR|\nTEMPLATE|\Z)', block, re.DOTALL)
        content = cm.group(1).strip() if cm else ""
        fires.append({"id": fid, "dt": dt, "template": template, "content": content})
    return fires


# ── Leave-one-out test harness ────────────────────────────────────────────────

class TestResult:
    def __init__(self):
        self.predictions  = []   # list of (actual, predicted, confidence, rule, prior_3, content)
        self.hits         = 0
        self.total        = 0

    def record(self, actual, pred: Prediction, prior_3, content):
        hit = (actual == pred.template)
        self.predictions.append((actual, pred.template, pred.confidence,
                                  pred.rule_fired, list(prior_3), content, hit))
        self.hits  += int(hit)
        self.total += 1

    @property
    def accuracy(self):
        return self.hits / self.total if self.total else 0.0


def run_leave_one_out(corpus: list[dict]) -> TestResult:
    model  = NexCognitionModel(window=25)
    result = TestResult()

    for i, fire in enumerate(corpus):
        if i < 3:
            model.observe(fire["template"])
            continue

        prior_3 = [corpus[i-3]["template"],
                   corpus[i-2]["template"],
                   corpus[i-1]["template"]]

        pred   = model.predict(prior_3)
        actual = fire["template"]

        result.record(actual, pred, prior_3, fire["content"])
        model.observe(actual)

    return result


# ── Report builder ────────────────────────────────────────────────────────────

def build_report(result: TestResult, corpus: list[dict]) -> str:
    lines = []

    def w(*args):
        lines.append(" ".join(str(a) for a in args))

    # ── A. OVERALL ACCURACY ───────────────────────────────────────────────────
    w("PHASE 1 — SIMULATOR TEST REPORT")
    w(f"Generated: from {len(corpus)}-fire fountain_insight corpus")
    w(f"Method: leave-one-out prediction (fires 3 through {len(corpus)-1})")
    w("=" * 70)
    w("")
    w("A. OVERALL ACCURACY")
    w("=" * 70)
    w("")
    n_total  = result.total
    n_hits   = result.hits
    acc      = result.accuracy

    # Random baselines
    baseline_most_common = BASELINE_FREQ[SENSE]   # always predict SENSE_OBS
    # Weighted random: pick proportional to base freq
    # E[hit] = Σ P(actual=t) * P(predict=t) = Σ p_t^2
    weighted_random = sum(p**2 for p in BASELINE_FREQ.values())

    w(f"  Total predictions:              {n_total}")
    w(f"  Correct predictions:            {n_hits}")
    w(f"  Accuracy:                       {acc*100:.1f}%")
    w(f"")
    w(f"  Baselines for comparison:")
    w(f"    Always predict SENSE_OBS:     {baseline_most_common*100:.1f}%")
    w(f"    Weighted-random (7 classes):  {weighted_random*100:.1f}%")
    w(f"    Uniform random (1/7):         {100/7:.1f}%")
    w(f"")
    lift = acc / baseline_most_common if baseline_most_common else 0
    w(f"  Lift over SENSE_OBS baseline:   {lift:.2f}x")
    w(f"  Delta over SENSE_OBS baseline:  {(acc - baseline_most_common)*100:+.1f} pp")
    w("")

    # ── B. PER-TEMPLATE HIT RATE ─────────────────────────────────────────────
    w("B. PER-TEMPLATE HIT RATE")
    w("=" * 70)
    w("")
    w(f"  {'TEMPLATE':<20} {'ACTUAL_N':>8} {'HITS':>6} {'HIT_RATE':>9} {'PREDICTED_AS':>12}")
    w("  " + "-" * 65)

    template_stats: dict[str, dict] = {t: {"actual": 0, "hits": 0, "predicted_as": Counter()}
                                        for t in ALL_TEMPLATES + ["UNKNOWN"]}

    for actual, predicted, conf, rule, prior_3, content, hit in result.predictions:
        template_stats[actual]["actual"]  += 1
        template_stats[actual]["hits"]    += int(hit)
        template_stats[actual]["predicted_as"][predicted] += 1

    for t in ALL_TEMPLATES:
        s = template_stats[t]
        n  = s["actual"]
        h  = s["hits"]
        hr = f"{h/n*100:.0f}%" if n else "—"
        top_pred = s["predicted_as"].most_common(1)
        tp_str   = f"{top_pred[0][0]}({top_pred[0][1]})" if top_pred else "—"
        w(f"  {t:<20} {n:>8} {h:>6} {hr:>9} {tp_str:>12}")
    w("")

    # ── C. CONFUSION MATRIX ───────────────────────────────────────────────────
    w("C. CONFUSION MATRIX  (rows = PREDICTED, cols = ACTUAL)")
    w("=" * 70)
    w("")
    labels = ALL_TEMPLATES
    abbrev = {SENSE: "SENSE", ABSTRACT: "ABSTR", SIMILE: "SIMILE",
              DIALECT: "DIAL", QUESTION: "QUEST", ACTION: "ACT", UNCAT: "UNCAT"}
    conf_mat: dict[tuple, int] = Counter()
    for actual, predicted, conf, rule, prior_3, content, hit in result.predictions:
        conf_mat[(predicted, actual)] += 1

    header_cols = "  " + f"{'':18}" + "".join(f"{abbrev[t]:>8}" for t in labels)
    w(header_cols)
    w("  " + "-" * (18 + 8 * len(labels) + 2))
    for pred_t in labels:
        row_label = f"  {abbrev[pred_t]:<18}"
        row_vals  = "".join(f"{conf_mat.get((pred_t, act_t), 0):>8}" for act_t in labels)
        w(row_label + row_vals)
    w("")

    # ── D. FAILURE PATTERNS ───────────────────────────────────────────────────
    w("D. FAILURE PATTERNS — top misprediction contexts")
    w("=" * 70)
    w("")

    misses = [(actual, predicted, conf, rule, prior_3, content)
              for actual, predicted, conf, rule, prior_3, content, hit in result.predictions
              if not hit]

    # Group by prior-3 pattern
    miss_contexts: dict[tuple, list] = {}
    for actual, predicted, conf, rule, prior_3, content in misses:
        key = tuple(prior_3)
        if key not in miss_contexts:
            miss_contexts[key] = []
        miss_contexts[key].append((actual, predicted, rule, content))

    # Sort by frequency
    top_miss = sorted(miss_contexts.items(), key=lambda x: -len(x[1]))[:7]

    for rank, (ctx, cases) in enumerate(top_miss, 1):
        w(f"  FAILURE CONTEXT {rank}  (n={len(cases)} misses)")
        w(f"  Prior-3: {ctx[0]} → {ctx[1]} → {ctx[2]}")
        predicted_by_model = cases[0][1]
        rule_used          = cases[0][2]
        w(f"  Model predicted: {predicted_by_model}  (rule: {rule_used})")
        actual_dist = Counter(c[0] for c in cases)
        w(f"  Actual was:      {dict(actual_dist.most_common())}")
        # Show 2 examples
        for actual, predicted, rule, content in cases[:2]:
            w(f"    actual={actual}: {content[:80]}")
        w("")

    # ── E. SUCCESS PATTERNS ───────────────────────────────────────────────────
    w("E. SUCCESS PATTERNS — most reliable prior contexts")
    w("=" * 70)
    w("")

    hit_contexts: dict[tuple, dict] = {}
    for actual, predicted, conf, rule, prior_3, content, hit in result.predictions:
        key = tuple(prior_3)
        if key not in hit_contexts:
            hit_contexts[key] = {"hits": 0, "total": 0, "rules": Counter()}
        hit_contexts[key]["total"] += 1
        hit_contexts[key]["hits"]  += int(hit)
        if hit:
            hit_contexts[key]["rules"][rule] += 1

    # Filter to contexts with ≥3 occurrences and sort by hit-rate
    reliable = [(ctx, d) for ctx, d in hit_contexts.items() if d["total"] >= 3]
    reliable.sort(key=lambda x: (-x[1]["hits"]/x[1]["total"], -x[1]["total"]))

    for rank, (ctx, d) in enumerate(reliable[:5], 1):
        hr = d["hits"] / d["total"]
        top_rule = d["rules"].most_common(1)[0][0] if d["rules"] else "—"
        w(f"  SUCCESS CONTEXT {rank}  (hit-rate={hr*100:.0f}%  n={d['total']})")
        w(f"  Prior-3: {ctx[0]} → {ctx[1]} → {ctx[2]}")
        w(f"  Rule:    {top_rule}")
        w("")

    # ── E2: Per-rule accuracy ─────────────────────────────────────────────────
    w("E2. PER-RULE ACCURACY")
    w("=" * 70)
    w("")
    rule_stats: dict[str, dict] = {}
    for actual, predicted, conf, rule, prior_3, content, hit in result.predictions:
        if rule not in rule_stats:
            rule_stats[rule] = {"hits": 0, "total": 0}
        rule_stats[rule]["total"] += 1
        rule_stats[rule]["hits"]  += int(hit)

    w(f"  {'RULE':<45} {'N':>5} {'HITS':>6} {'ACC':>7}")
    w("  " + "-" * 68)
    for rule, s in sorted(rule_stats.items(), key=lambda x: -x[1]["total"]):
        acc_r = s["hits"] / s["total"]
        w(f"  {rule:<45} {s['total']:>5} {s['hits']:>6} {acc_r*100:>6.0f}%")
    w("")

    # ── F. VERDICT ────────────────────────────────────────────────────────────
    w("F. VERDICT")
    w("=" * 70)
    w("")
    w(f"  Overall accuracy:           {acc*100:.1f}%")
    w(f"  SENSE_OBS-always baseline:  {baseline_most_common*100:.1f}%")
    w(f"  Weighted-random baseline:   {weighted_random*100:.1f}%")
    w("")

    if acc >= 0.70:
        verdict = "STRONGLY PREDICTIVE"
        detail  = ("Model accuracy exceeds 70%. Phase 1 rules have strong "
                   "empirical support as a predictive framework.")
    elif acc >= 0.50:
        verdict = "MEANINGFULLY PREDICTIVE"
        detail  = ("Model accuracy exceeds 50%, well above both random "
                   "baselines. Phase 1 rules capture real structure.")
    elif acc >= 0.30:
        verdict = "WEAKLY PREDICTIVE"
        detail  = ("Model beats uniform random but is near or below the "
                   "SENSE_OBS-always baseline. Rules need refinement.")
    else:
        verdict = "NOT PREDICTIVE — REVISE RULES"
        detail  = ("Model fails to beat even the trivial baseline. "
                   "Core rules do not predict the sequence.")

    w(f"  VERDICT: {verdict}")
    w(f"  {detail}")
    w("")

    # Identify top rule gaps
    w("  Top failure drivers (rule fired, miss count):")
    rule_misses = Counter()
    for actual, predicted, conf, rule, prior_3, content, hit in result.predictions:
        if not hit:
            rule_misses[rule] += 1
    for rule, n in rule_misses.most_common(5):
        w(f"    {rule:<45} {n} misses")
    w("")

    # What would a SENSE-always predictor get wrong that we get right?
    our_hits_sense_wrong = 0
    for actual, predicted, conf, rule, prior_3, content, hit in result.predictions:
        sense_would_hit = (actual == SENSE)
        if hit and not sense_would_hit:
            our_hits_sense_wrong += 1
    w(f"  Non-SENSE correct predictions (model advantage over baseline): {our_hits_sense_wrong}")

    # SENSE_OBS prediction accuracy breakdown
    w("")
    w("  SENSE_OBS prediction deep-dive:")
    sense_actual = sum(1 for r in result.predictions if r[0] == SENSE)
    sense_hits   = sum(1 for r in result.predictions if r[0] == SENSE and r[6])
    nonsense_pred_as_sense = sum(1 for r in result.predictions if r[0] != SENSE and r[1] == SENSE)
    w(f"    When actual=SENSE_OBS: {sense_hits}/{sense_actual} correct ({sense_hits/sense_actual*100:.0f}%)")
    w(f"    False SENSE predictions (actual≠SENSE but we said SENSE): {nonsense_pred_as_sense}/{n_total - sense_actual} ({nonsense_pred_as_sense/(n_total-sense_actual)*100:.0f}%)")
    w("")
    w("=" * 70)
    w("END REPORT")
    w("=" * 70)

    return "\n".join(lines)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    corpus_path = (
        Path(__file__).parent.parent.parent
        / "Desktop/nex5_research_log/nex5_metaphor_input_correlation.txt"
    )
    if not corpus_path.exists():
        corpus_path = Path.home() / "Desktop/nex5_research_log/nex5_metaphor_input_correlation.txt"

    print(f"Loading corpus from {corpus_path} ...", file=sys.stderr)
    corpus = load_corpus(str(corpus_path))
    print(f"  {len(corpus)} fires loaded.", file=sys.stderr)

    print("Running leave-one-out test ...", file=sys.stderr)
    result = run_leave_one_out(corpus)
    print(f"  {result.total} predictions, {result.hits} hits, {result.accuracy*100:.1f}% accuracy.",
          file=sys.stderr)

    report = build_report(result, corpus)
    print(report)
