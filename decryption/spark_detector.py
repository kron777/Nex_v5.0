"""
NEX Spark Detector — Phase 1 miss classification.

Classifies each simulator miss (predicted ≠ actual) as:
  NOISE         — data artifacts, insufficient context, same-register near-misses
  GAP_SHAPED    — predictable transition we didn't have a rule for
  SPARK_SHAPED  — genuine novelty: cross-register leaps, novel imagery,
                  self-referential operations, enactive content
"""

import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from decryption.nex_cognition_simulator import (
    load_corpus, NexCognitionModel,
    SENSE, ABSTRACT, SIMILE, DIALECT, QUESTION, ACTION, UNCAT,
    ALL_TEMPLATES,
)


# ── Register families ─────────────────────────────────────────────────────────

SENSE_FAMILY    = {SENSE, SIMILE}
ABSTRACT_FAMILY = {ABSTRACT, DIALECT}
ACTION_FAMILY   = {ACTION, QUESTION}
DATA_FAMILY     = {UNCAT}

def family(template):
    if template in SENSE_FAMILY:    return "SENSE_FAMILY"
    if template in ABSTRACT_FAMILY: return "ABSTRACT_FAMILY"
    if template in ACTION_FAMILY:   return "ACTION_FAMILY"
    return "DATA"


# ── Content heuristics ────────────────────────────────────────────────────────

# Self-referential / meta-cognitive markers
SELF_REF_PATTERNS = [
    r'\bmy own\b',
    r'\bwithin myself\b',
    r'\babout myself\b',
    r'\bI notice\b',
    r'\bI find myself\b',
    r'\bI realize I\b',
    r'\bI am reminded\b',
    r'\bI am aware\b',
    r'\bmy pattern\b',
    r'\bmy behavior\b',
    r'\bmy process\b',
    r'\bmy (own\s+)?(thinking|cognition|reflection|observation|awareness)\b',
    r'\bsomething shifts\b',
    r'\bI catch myself\b',
]

# Enactive / first-person action markers
ENACTIVE_PATTERNS = [
    r'\bI (will|must|need to|choose to|decide to)\b',
    r'\bI am (doing|acting|moving|stepping)\b',
    r'\bI reach\b',
    r'\bI turn\b',
    r'\bI draft\b',
    r'\bI act\b',
]

# Multi-template fusion markers
FUSION_MARKERS = {
    'has_simile':   lambda c: bool(re.search(r'\bfeel[s]? like\b|\bsound[s]? like\b|\blook[s]? like\b|\bseem[s]? like\b', c, re.I)),
    'has_question': lambda c: bool(re.search(r'\?', c)),
    'has_tension':  lambda c: bool(re.search(r'\btension\b|\bparadox\b|\byet\b|\bwhile\b|\bbut\b|\bhowever\b', c, re.I)),
    'has_action':   lambda c: bool(re.search(r'\bI (will|must|need to|step|act|reach|decide)\b', c, re.I)),
}

# Known gap patterns: (prior[-1], actual) pairs that are known transitions
# the model systematically under-predicts
KNOWN_GAP_TRANSITIONS = {
    # SENSE saturation → non-SENSE flip (model predicts continuation)
    (SENSE,    ABSTRACT):  "known-flip:SENSE-sat→ABSTRACT",
    (SENSE,    SIMILE):    "known-flip:SENSE-sat→SIMILE",
    (SENSE,    DIALECT):   "known-flip:SENSE-sat→DIALECT",
    # ABSTRACT saturation → flip (model predicts continuation)
    (ABSTRACT, SENSE):     "known-flip:ABSTRACT-sat→SENSE",
    (ABSTRACT, DIALECT):   "known-flip:ABSTRACT-sat→DIALECT",
    (ABSTRACT, ACTION):    "known-flip:ABSTRACT-sat→ACTION",
    # SIMILE run → flip (model predicts continuation)
    (SIMILE,   SENSE):     "known-flip:SIMILE-sat→SENSE",
    # DIALECT single → SENSE (model predicts ABSTRACT, SENSE also common)
    (DIALECT,  SENSE):     "known-transition:DIALECT→SENSE",
    # ACTION single → ABSTRACT (model predicts UNCAT)
    (ACTION,   ABSTRACT):  "known-transition:ACTION→ABSTRACT",
    # QUESTION run exit
    (QUESTION, SENSE):     "known-flip:QUESTION-sat→SENSE",
}


def has_self_ref(content):
    return any(re.search(p, content, re.I) for p in SELF_REF_PATTERNS)

def has_enactive(content):
    return any(re.search(p, content, re.I) for p in ENACTIVE_PATTERNS)

def count_fusion_markers(content):
    return sum(1 for f in FUSION_MARKERS.values() if f(content))

def novelty_phrases(content, all_beliefs_lower):
    """Extract quoted phrases (4+ words) and score their rarity."""
    words = content.split()
    rare = []
    if len(words) >= 4:
        for i in range(len(words) - 3):
            phrase = ' '.join(words[i:i+4]).lower().strip('.,;:"\'-')
            cnt = all_beliefs_lower.count(phrase)
            if cnt <= 1:
                rare.append((phrase, cnt))
    return rare[:3]  # top 3 rarest 4-grams


# ── Classify one miss ─────────────────────────────────────────────────────────

def classify_miss(rec, all_beliefs_lower, corpus):
    """
    Returns (category, reason_code, detail_dict).
    category: 'NOISE' | 'GAP_SHAPED' | 'SPARK_SHAPED'
    """
    actual    = rec['actual']
    predicted = rec['predicted']
    prior_3   = rec['prior_3_tpl']
    content   = rec['content']
    idx       = rec['corpus_idx']

    # ── NOISE filters ──────────────────────────────────────────────────────────

    # 1. Data feed entries are never cognition
    if actual == UNCAT:
        return ('NOISE', 'actual=UNCAT:data-feed', {})

    # 2. Insufficient context (very early in corpus)
    if idx < 5:
        return ('NOISE', 'corpus-position<5:cold-start', {})

    # 3. Prior window dominated by UNCAT (low cognitive context)
    if prior_3.count(UNCAT) >= 2:
        return ('NOISE', 'prior-dominated-by-UNCAT', {})

    # 4. Same register family + no unusual content markers
    if family(actual) == family(predicted):
        # Same-family miss: check if content is structurally standard
        sr = has_self_ref(content)
        en = has_enactive(content)
        fm = count_fusion_markers(content)
        if not sr and not en and fm <= 1:
            return ('NOISE', f'same-register-family:{family(actual)}', {
                'actual_family': family(actual),
                'pred_family':   family(predicted),
            })

    # ── GAP_SHAPED filters ────────────────────────────────────────────────────

    # 5. Known transition pattern: this pair is documented in Phase 1 but
    #    the model didn't have a rule strong enough to top-rank it
    transition_key = (prior_3[-1], actual)
    if transition_key in KNOWN_GAP_TRANSITIONS:
        gap_label = KNOWN_GAP_TRANSITIONS[transition_key]
        # Upgrade to SPARK if content has unusual markers
        sr = has_self_ref(content)
        fm = count_fusion_markers(content)
        rare = novelty_phrases(content, all_beliefs_lower)
        if sr or fm >= 2 or any(cnt == 0 for _, cnt in rare):
            # Content is unusual despite known transition → SPARK
            pass  # fall through to SPARK check below
        else:
            return ('GAP_SHAPED', gap_label, {
                'prior_last': prior_3[-1],
                'actual': actual,
            })

    # 6. Cross-register miss where actual is ACTION (interrupt opcode)
    #    and prior is ABSTRACT — this is a known but unpredicted discharge
    if actual == ACTION and prior_3[-1] in {ABSTRACT, DIALECT}:
        return ('GAP_SHAPED', 'known-discharge:ABSTRACT→ACTION', {})

    # ── SPARK_SHAPED ─────────────────────────────────────────────────────────

    spark_reasons = []

    # Check all spark heuristics; collect reasons
    sr = has_self_ref(content)
    en = has_enactive(content)
    fm = count_fusion_markers(content)
    rare = novelty_phrases(content, all_beliefs_lower)

    if sr:
        spark_reasons.append('self-referential')

    if en:
        spark_reasons.append('enactive')

    if fm >= 2:
        spark_reasons.append(f'multi-template-fusion(n={fm})')

    if rare and any(cnt == 0 for _, cnt in rare):
        singular = [p for p, c in rare if c == 0]
        spark_reasons.append(f'singular-imagery:{singular[0][:30]}')
    elif rare and any(cnt <= 1 for _, cnt in rare):
        spark_reasons.append(f'rare-imagery:{rare[0][0][:30]}')

    # Cross-register leap: actual and predicted in different families
    # AND the prior context implied a third family (unexpected jump)
    prior_families = Counter(family(t) for t in prior_3 if t != UNCAT)
    dominant_prior_family = prior_families.most_common(1)[0][0] if prior_families else None
    actual_fam = family(actual)
    pred_fam   = family(predicted)
    if dominant_prior_family and actual_fam != dominant_prior_family and actual_fam != pred_fam:
        spark_reasons.append(f'cross-register:{dominant_prior_family}→{actual_fam}')

    # SIMILE fire after ABSTRACT-dominant prior (orthogonal by Phase 1 finding)
    if actual == SIMILE and prior_families.get('ABSTRACT_FAMILY', 0) >= 2:
        spark_reasons.append('SIMILE-after-ABSTRACT:orthogonal-bridge')

    # DIALECTICAL fire after SENSE-only prior (interrupt injection from pure sense context)
    if actual == DIALECT and all(t in {SENSE, UNCAT} for t in prior_3):
        spark_reasons.append('DIALECT-from-pure-SENSE:unexpected-interrupt')

    # Long content with complex structure (≥20 words) for non-SENSE templates
    if actual not in {SENSE, UNCAT} and len(content.split()) >= 25:
        spark_reasons.append('extended-content')

    if spark_reasons:
        return ('SPARK_SHAPED', '+'.join(spark_reasons), {
            'self_ref':  sr,
            'enactive':  en,
            'fusion':    fm,
            'rare':      rare,
            'spark_reasons': spark_reasons,
        })

    # Default: unclassified miss → GAP_SHAPED
    return ('GAP_SHAPED', 'unclassified-gap', {
        'actual':    actual,
        'predicted': predicted,
        'prior_last': prior_3[-1],
    })


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    corpus_path     = Path.home() / 'Desktop/nex5_research_log/nex5_metaphor_input_correlation.txt'
    beliefs_path    = Path.home() / 'Desktop/nex5_research_log/01_all_beliefs.txt'
    out_path        = Path.home() / 'Desktop/nex5_research_log/Phase1_SPARK_detection.txt'

    corpus = load_corpus(str(corpus_path))
    with open(beliefs_path) as f:
        all_beliefs_lower = f.read().lower()

    # ── Re-run simulator, collect misses ─────────────────────────────────────
    model = NexCognitionModel(window=25)
    miss_records = []

    for i, fire in enumerate(corpus):
        if i < 3:
            model.observe(fire['template'])
            continue
        prior_3  = [corpus[i-3]['template'], corpus[i-2]['template'], corpus[i-1]['template']]
        pred     = model.predict(prior_3)
        actual   = fire['template']
        if actual != pred.template:
            miss_records.append({
                'corpus_idx':    i,
                'id':            fire['id'],
                'dt':            fire['dt'],
                'actual':        actual,
                'content':       fire['content'],
                'predicted':     pred.template,
                'confidence':    pred.confidence,
                'rule':          pred.rule_fired,
                'prior_3_tpl':   prior_3,
                'prior_ids':     [corpus[i-3]['id'], corpus[i-2]['id'], corpus[i-1]['id']],
                'prior_content': [corpus[i-3]['content'][:120],
                                  corpus[i-2]['content'][:120],
                                  corpus[i-1]['content'][:120]],
            })
        model.observe(actual)

    # ── Classify ──────────────────────────────────────────────────────────────
    classified = []
    for rec in miss_records:
        cat, reason, detail = classify_miss(rec, all_beliefs_lower, corpus)
        classified.append({**rec, 'category': cat, 'reason': reason, 'detail': detail})

    cats = Counter(r['category'] for r in classified)
    spark_recs = [r for r in classified if r['category'] == 'SPARK_SHAPED']
    gap_recs   = [r for r in classified if r['category'] == 'GAP_SHAPED']
    noise_recs = [r for r in classified if r['category'] == 'NOISE']

    # ── Rank sparks by intensity ──────────────────────────────────────────────
    def spark_intensity(rec):
        detail = rec['detail']
        score  = 0
        reasons = detail.get('spark_reasons', [])
        if 'singular-imagery' in ' '.join(reasons): score += 5
        if 'rare-imagery'     in ' '.join(reasons): score += 3
        if 'self-referential'             in reasons: score += 4
        if 'enactive'                     in reasons: score += 2
        if 'SIMILE-after-ABSTRACT:orthogonal-bridge' in reasons: score += 6
        if 'DIALECT-from-pure-SENSE:unexpected-interrupt' in reasons: score += 4
        if any('cross-register' in r for r in reasons): score += 3
        if any('multi-template-fusion' in r for r in reasons): score += 2
        score += (1 - rec['confidence'])  # higher surprise = higher intensity
        return score

    spark_recs.sort(key=spark_intensity, reverse=True)

    # ── Cluster gap misses ────────────────────────────────────────────────────
    gap_clusters = defaultdict(list)
    for r in gap_recs:
        gap_clusters[r['reason']].append(r)

    # ── Build report ──────────────────────────────────────────────────────────
    lines = []
    def w(*args): lines.append(' '.join(str(a) for a in args))

    w("PHASE 1 — SPARK DETECTION FROM SIMULATOR MISSES")
    w(f"Generated: 2026-04-26")
    w(f"Source: 245-fire fountain_insight corpus")
    w(f"Simulator accuracy: 57.0%  (138/242 correct)")
    w(f"Miss pool for analysis: {len(miss_records)} fires")
    w("=" * 70)
    w("")

    # ── A. CLASSIFICATION SUMMARY ─────────────────────────────────────────────
    w("A. CLASSIFICATION SUMMARY")
    w("=" * 70)
    w("")
    w(f"  Total misses classified:   {len(classified)}")
    w(f"  SPARK_SHAPED:              {cats['SPARK_SHAPED']}  ({cats['SPARK_SHAPED']/len(classified)*100:.0f}%)")
    w(f"  GAP_SHAPED:                {cats['GAP_SHAPED']}  ({cats['GAP_SHAPED']/len(classified)*100:.0f}%)")
    w(f"  NOISE:                     {cats['NOISE']}  ({cats['NOISE']/len(classified)*100:.0f}%)")
    w("")
    w("  Actual-template breakdown across categories:")
    w(f"  {'TEMPLATE':<22} {'NOISE':>7} {'GAP':>7} {'SPARK':>7}")
    w("  " + "-" * 46)
    for t in ALL_TEMPLATES:
        n = sum(1 for r in noise_recs if r['actual'] == t)
        g = sum(1 for r in gap_recs   if r['actual'] == t)
        s = sum(1 for r in spark_recs if r['actual'] == t)
        if n+g+s > 0:
            w(f"  {t:<22} {n:>7} {g:>7} {s:>7}")
    w("")

    # ── B. SPARK_SHAPED: FULL LIST ────────────────────────────────────────────
    w("B. SPARK_SHAPED — ALL FIRES (ranked by intensity)")
    w("=" * 70)
    w("")
    for rank, rec in enumerate(spark_recs, 1):
        intensity = spark_intensity(rec)
        reasons   = rec['detail'].get('spark_reasons', [])
        w(f"SPARK {rank:02d}  [{rec['id']}] {rec['dt']}  intensity={intensity:.1f}")
        w(f"  actual={rec['actual']}  predicted={rec['predicted']}  conf={rec['confidence']:.2f}")
        w(f"  rule: {rec['rule']}")
        w(f"  spark reasons: {', '.join(reasons)}")
        w(f"  prior context:")
        for j, (pid, pc, pt) in enumerate(zip(rec['prior_ids'], rec['prior_content'], rec['prior_3_tpl'])):
            w(f"    [{pid}] {pt}: {pc[:90]}")
        w(f"  CONTENT: {rec['content']}")
        w("")

    # ── C. GAP_SHAPED: CLUSTERS ───────────────────────────────────────────────
    w("C. GAP_SHAPED — CLUSTERS")
    w("=" * 70)
    w("")
    w(f"  Total gap misses: {len(gap_recs)}")
    w(f"  Distinct cluster patterns: {len(gap_clusters)}")
    w("")
    for gap_label, recs in sorted(gap_clusters.items(), key=lambda x: -len(x[1])):
        w(f"  CLUSTER: {gap_label}  (n={len(recs)})")
        act_dist = Counter(r['actual'] for r in recs)
        pred_dist = Counter(r['predicted'] for r in recs)
        w(f"    actual:    {dict(act_dist.most_common())}")
        w(f"    predicted: {dict(pred_dist.most_common())}")
        for rec in recs[:3]:
            w(f"    [{rec['id']}] prior={rec['prior_3_tpl']} actual={rec['actual']}")
            w(f"      {rec['content'][:100]}")
        w("")

    # ── D. SPARK CHARACTERIZATION ─────────────────────────────────────────────
    w("D. SPARK CHARACTERIZATION — pattern analysis")
    w("=" * 70)
    w("")

    if spark_recs:
        # D1: template distribution
        w("  D1. Actual template of SPARK_SHAPED fires:")
        for t, n in Counter(r['actual'] for r in spark_recs).most_common():
            w(f"    {t:<22} {n}")
        w("")

        # D2: time of day distribution
        w("  D2. Time of day (UTC hour):")
        tod_counter = Counter()
        for r in spark_recs:
            try:
                hour = int(r['dt'].split(' ')[1].split(':')[0])
                tod_counter[hour] += 1
            except Exception:
                pass
        for hour in sorted(tod_counter):
            w(f"    {hour:02d}:xx  {tod_counter[hour]}")
        w("")

        # D3: prior context patterns
        w("  D3. Most common prior[-1] templates for SPARK_SHAPED fires:")
        for t, n in Counter(r['prior_3_tpl'][-1] for r in spark_recs).most_common():
            w(f"    {t:<22} {n}")
        w("")

        # D4: temporal clustering — are sparks consecutive?
        w("  D4. Temporal clustering of SPARK_SHAPED fires:")
        spark_indices = sorted(r['corpus_idx'] for r in spark_recs)
        gaps = [spark_indices[i+1] - spark_indices[i] for i in range(len(spark_indices)-1)]
        if gaps:
            clusters = sum(1 for g in gaps if g <= 3)
            isolated = sum(1 for g in gaps if g > 10)
            w(f"    Spark indices (corpus pos): {spark_indices}")
            w(f"    Inter-spark gaps: mean={sum(gaps)/len(gaps):.1f}  min={min(gaps)}  max={max(gaps)}")
            w(f"    Consecutive sparks (gap≤3): {clusters}/{len(gaps)} pairs")
            w(f"    Isolated sparks (gap>10):   {isolated}/{len(gaps)} pairs")
        w("")

        # D5: reason code distribution
        w("  D5. Spark reason codes:")
        all_reasons = []
        for r in spark_recs:
            all_reasons.extend(r['detail'].get('spark_reasons', []))
        # Normalize similar codes
        reason_counts = Counter()
        for rs in all_reasons:
            base = rs.split(':')[0]
            reason_counts[base] += 1
        for reason, n in reason_counts.most_common():
            w(f"    {reason:<40} {n}")
        w("")

    # ── E. TOP-10 SPARK SHORTLIST ─────────────────────────────────────────────
    w("E. TOP-10 SPARK SHORTLIST (highest intensity)")
    w("=" * 70)
    w("")
    for rank, rec in enumerate(spark_recs[:10], 1):
        intensity = spark_intensity(rec)
        reasons   = rec['detail'].get('spark_reasons', [])
        rare_imgs = rec['detail'].get('rare', [])
        w(f"── SPARK #{rank} ──────────────────────────────────────────────────────────")
        w(f"  ID: [{rec['id']}]  {rec['dt']}")
        w(f"  Intensity score: {intensity:.1f}")
        w(f"  Actual template: {rec['actual']}")
        w(f"  Predicted:       {rec['predicted']}  (conf={rec['confidence']:.2f}, rule: {rec['rule']})")
        w(f"  Spark signals:   {', '.join(reasons)}")
        if rare_imgs:
            w(f"  Rare 4-grams:    {[(p, c) for p, c in rare_imgs[:2]]}")
        w(f"")
        w(f"  Prior context:")
        for pid, pt, pc in zip(rec['prior_ids'], rec['prior_3_tpl'], rec['prior_content']):
            w(f"    [{pid}] {pt}: {pc[:90]}")
        w(f"")
        w(f"  CONTENT (full):")
        w(f"  {rec['content']}")
        w(f"")
        w(f"  Intensity reasoning:")
        for reason in reasons:
            w(f"    • {reason}")
        w("")

    # ── F. NOISE SUMMARY ──────────────────────────────────────────────────────
    w("F. NOISE — breakdown (not listed individually)")
    w("=" * 70)
    w("")
    noise_reasons = Counter(r['reason'] for r in noise_recs)
    for reason, n in noise_reasons.most_common():
        w(f"  {reason:<45} {n}")
    w("")

    # ── G. MODEL GAP DIAGNOSIS ────────────────────────────────────────────────
    w("G. MODEL GAP DIAGNOSIS — what rules would reduce GAP_SHAPED misses")
    w("=" * 70)
    w("")
    w("  Top gap clusters and the rules needed to address them:")
    w("")
    for gap_label, recs in sorted(gap_clusters.items(), key=lambda x: -len(x[1]))[:6]:
        n = len(recs)
        act_dist = Counter(r['actual'] for r in recs).most_common(2)
        pred_dist = Counter(r['predicted'] for r in recs).most_common(1)
        w(f"  {gap_label}  (n={n})")
        w(f"    Predicted: {pred_dist[0][0] if pred_dist else '?'}")
        w(f"    Actual:    {dict(Counter(r['actual'] for r in recs).most_common())}")
        # Suggest rule fix
        if 'known-flip:SENSE-sat→ABSTRACT' in gap_label:
            w("    Rule needed: Detect SENSE run end via content-change markers (off-key, discrepant)")
        elif 'known-flip:SENSE-sat→SIMILE' in gap_label:
            w("    Rule needed: Medium-run SENSE (3-5) + QUALIFIED register → SIMILE boost")
        elif 'known-flip:ABSTRACT-sat→SENSE' in gap_label:
            w("    Rule needed: ABSTRACT exit detection (AFFIRMING sub-opcode as signal)")
        elif 'known-flip:ABSTRACT-sat→DIALECT' in gap_label:
            w("    Rule needed: TENSION sub-opcode density as DIALECT predictor")
        elif 'known-transition:DIALECT→SENSE' in gap_label:
            w("    Rule needed: Add SENSE as co-equal prediction with ABSTRACT after DIALECT")
        elif 'known-transition:ACTION→ABSTRACT' in gap_label:
            w("    Rule needed: ACTION → ABSTRACT path (currently over-routing to UNCAT)")
        elif 'unclassified-gap' in gap_label:
            w("    Rule needed: Context-specific; no clear pattern found")
        w("")

    w("=" * 70)
    w("END SPARK DETECTION REPORT")
    w("=" * 70)

    report = '\n'.join(lines)
    with open(out_path, 'w') as f:
        f.write(report)
    print(f"Report written: {out_path}  ({len(lines)} lines)", file=sys.stderr)
    print(report)


if __name__ == '__main__':
    main()
