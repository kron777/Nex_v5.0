"""
differential_analyzer.py — Pairwise divergence analysis between probe conditions.

For each pair of conditions that differ in exactly one experimental dimension,
compute output divergence on two axes:
  1. String distance — average pairwise Levenshtein ratio across all rep pairs
  2. Template distribution distance — Jensen-Shannon divergence over template counts

Output: which dimensions drive output divergence, with magnitude.
"""
from __future__ import annotations

import math
from collections import Counter, defaultdict
from itertools import combinations
from typing import Optional

from decryption.probes_db import ProbesDB
from decryption.probe_set import ProbeCondition


TEMPLATE_CATEGORIES = [
    "ABSTRACT_NOMINAL", "DIALECTICAL", "SENSE_OBS", "SIMILE",
    "QUESTION", "ACTION", "RECEPTIVITY", "UNCATEGORIZED",
]

DIMENSIONS = ["mode", "sense_pattern", "prior_context", "prompt_framing", "foundation_type"]


# ---------------------------------------------------------------------------
# String distance — normalized Levenshtein ratio (0=identical, 1=completely different)
# ---------------------------------------------------------------------------

def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        curr = [i]
        for j, cb in enumerate(b, 1):
            curr.append(min(prev[j] + 1, curr[j - 1] + 1,
                            prev[j - 1] + (ca != cb)))
        prev = curr
    return prev[-1]


def string_distance(texts_a: list[str], texts_b: list[str]) -> float:
    """
    Average normalized Levenshtein distance across all cross-pairs.
    Returns value in [0, 1].
    """
    if not texts_a or not texts_b:
        return float("nan")
    total, count = 0.0, 0
    for a in texts_a:
        for b in texts_b:
            maxlen = max(len(a), len(b), 1)
            total += _levenshtein(a, b) / maxlen
            count += 1
    return total / count if count else float("nan")


# ---------------------------------------------------------------------------
# Template distribution distance — Jensen-Shannon divergence
# ---------------------------------------------------------------------------

def _normalize(counter: Counter, keys: list[str]) -> list[float]:
    total = sum(counter.get(k, 0) for k in keys) or 1
    return [counter.get(k, 0) / total for k in keys]


def _js_divergence(p: list[float], q: list[float]) -> float:
    """Jensen-Shannon divergence in nats. Returns value in [0, ln(2)]."""
    m = [(pi + qi) / 2 for pi, qi in zip(p, q)]

    def kl(a: list[float], b: list[float]) -> float:
        return sum(ai * math.log(ai / bi) for ai, bi in zip(a, b)
                   if ai > 0 and bi > 0)

    return (kl(p, m) + kl(q, m)) / 2


def template_distance(templates_a: list[str], templates_b: list[str]) -> float:
    """
    Jensen-Shannon divergence between template distributions.
    Normalized to [0, 1] (divides by ln(2)).
    """
    ca = Counter(templates_a)
    cb = Counter(templates_b)
    p = _normalize(ca, TEMPLATE_CATEGORIES)
    q = _normalize(cb, TEMPLATE_CATEGORIES)
    jsd = _js_divergence(p, q)
    return jsd / math.log(2)  # normalize to [0,1]


# ---------------------------------------------------------------------------
# Condition pair analysis
# ---------------------------------------------------------------------------

def _diff_dimensions(a: dict, b: dict) -> list[str]:
    """Return which dimensions differ between two condition dicts."""
    return [dim for dim in DIMENSIONS if a.get(dim) != b.get(dim)]


def _condition_key(row) -> dict:
    return {dim: row[dim] for dim in DIMENSIONS}


def analyze_pairs(db: ProbesDB) -> list[dict]:
    """
    For every pair of conditions that differ in exactly one dimension,
    compute string distance and template JS-divergence.

    Returns list of records:
      {
        condition_hash_a, condition_hash_b,
        varying_dimension, value_a, value_b,
        string_distance, template_jsd,
        n_a, n_b,
      }
    """
    all_results = db.fetch_all_results()
    if not all_results:
        return []

    # Group results by condition_hash.
    by_hash: dict[str, list] = defaultdict(list)
    meta: dict[str, dict] = {}
    for row in all_results:
        h = row["condition_hash"]
        by_hash[h].append(row)
        if h not in meta:
            meta[h] = _condition_key(row)

    hashes = list(by_hash.keys())
    records = []

    for ha, hb in combinations(hashes, 2):
        diff = _diff_dimensions(meta[ha], meta[hb])
        if len(diff) != 1:
            continue  # only single-dimension pairs

        dim = diff[0]
        texts_a = [r["output_text"] for r in by_hash[ha] if r["output_text"]]
        texts_b = [r["output_text"] for r in by_hash[hb] if r["output_text"]]
        tmpl_a  = [r["output_template"] for r in by_hash[ha] if r["output_template"]]
        tmpl_b  = [r["output_template"] for r in by_hash[hb] if r["output_template"]]

        sd  = string_distance(texts_a, texts_b)
        jsd = template_distance(tmpl_a, tmpl_b)

        records.append({
            "condition_hash_a":   ha,
            "condition_hash_b":   hb,
            "varying_dimension":  dim,
            "value_a":            meta[ha][dim],
            "value_b":            meta[hb][dim],
            "string_distance":    sd,
            "template_jsd":       jsd,
            "n_a":                len(texts_a),
            "n_b":                len(texts_b),
        })

    return records


def dimension_summary(records: list[dict]) -> dict[str, dict]:
    """
    Aggregate records by varying_dimension.
    Returns {dimension: {mean_string_dist, mean_template_jsd, n_pairs}}.
    """
    by_dim: dict[str, list] = defaultdict(list)
    for r in records:
        by_dim[r["varying_dimension"]].append(r)

    summary = {}
    for dim, pairs in by_dim.items():
        valid_sd  = [p["string_distance"]  for p in pairs if not math.isnan(p["string_distance"])]
        valid_jsd = [p["template_jsd"]     for p in pairs if not math.isnan(p["template_jsd"])]
        summary[dim] = {
            "mean_string_dist":   sum(valid_sd)  / len(valid_sd)  if valid_sd  else float("nan"),
            "mean_template_jsd":  sum(valid_jsd) / len(valid_jsd) if valid_jsd else float("nan"),
            "n_pairs":            len(pairs),
        }

    # Sort by mean_template_jsd descending (primary driver first).
    return dict(sorted(
        summary.items(),
        key=lambda kv: kv[1]["mean_template_jsd"] if not math.isnan(kv[1]["mean_template_jsd"]) else -1,
        reverse=True,
    ))


def print_report(db: ProbesDB) -> None:
    records = analyze_pairs(db)
    if not records:
        print("No pair data available yet. Run probes first.")
        return

    summary = dimension_summary(records)
    print("\n=== DIFFERENTIAL ANALYSIS — DIMENSION RANKING ===\n")
    print(f"{'Dimension':<20} {'JS-div':>8} {'StrDist':>8} {'Pairs':>6}")
    print("-" * 48)
    for dim, s in summary.items():
        jsd = f"{s['mean_template_jsd']:.3f}" if not math.isnan(s['mean_template_jsd']) else "  nan"
        sd  = f"{s['mean_string_dist']:.3f}"  if not math.isnan(s['mean_string_dist'])  else "  nan"
        print(f"{dim:<20} {jsd:>8} {sd:>8} {s['n_pairs']:>6}")

    print(f"\nTotal pairs analyzed: {len(records)}")
