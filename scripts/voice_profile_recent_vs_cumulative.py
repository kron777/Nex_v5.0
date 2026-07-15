#!/usr/bin/env python3
"""voice_profile_recent_vs_cumulative.py

Diagnostic: compare cumulative voice_profile signature against a
recent-window log-ratio signature computed on the fly.

When cumulative and recent diverge, register is shifting.
When they converge, the shift has settled into character.

Read-only on both DBs. No writes. Safe to re-run.

Usage:
  python3 scripts/voice_profile_recent_vs_cumulative.py [hours]

hours: lookback window for recent signature (default 9).

Baseline established 2026-05-22 03:45 — see CARRY_OVER.md.
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

REPO = Path("/home/rr/Desktop/Desktop/nex5")
CONV_DB = REPO / "data" / "conversations.db"
DYNAMIC_DB = REPO / "data" / "dynamic.db"
DRIVE_PAIR_LIKE = "%integration%self_preservation%"
DRIVE_PAIR_LABEL = "integration_vs_self_preservation"

STOPWORDS = frozenset({
    "the","a","an","is","are","was","were","be","been","being",
    "do","does","did","done","have","has","had","will","would","shall","should",
    "may","might","can","could","must",
    "i","you","he","she","it","we","they","me","him","her","us","them",
    "my","your","his","its","our","their",
    "this","that","these","those","what","how","why","when","where","which","who","whom",
    "and","or","but","not","if","of","in","on","at","to","for","from","with","by","as",
    "about","into","than","then","so","too","very","just","also","only",
    "no","yes","up","down","out","over","under","off","again",
    "more","most","less","least","such","some","any","all","both","each",
    "other","another","same","own","few","many",
})


def tokenize(text: str) -> list[str]:
    if not text:
        return []
    text = re.sub(r"\[[^\]]*\]", "", text)
    return [
        w for w in re.findall(r"[a-zA-Z\']+", text.lower())
        if len(w) > 2 and w not in STOPWORDS
    ]


def main(hours: int = 9) -> int:
    window_s = hours * 3600

    # Get IDs of recent fires under the drive-pair from conversations.db
    conv = sqlite3.connect(f"file:{CONV_DB}?mode=ro", uri=True)
    conv.row_factory = sqlite3.Row
    rows = conv.execute(
        "SELECT fountain_event_id FROM drive_activations "
        "WHERE active_conflicts LIKE ? "
        "  AND timestamp > strftime('%s','now') - ?",
        (DRIVE_PAIR_LIKE, window_s),
    ).fetchall()
    ids = [int(r["fountain_event_id"]) for r in rows if r["fountain_event_id"] is not None]

    if not ids:
        print(f"No fires under {DRIVE_PAIR_LABEL} in last {hours}h.")
        return 0

    print(f"Window: last {hours}h. Fires under {DRIVE_PAIR_LABEL}: {len(ids)}")
    print(f"ID range: {min(ids)} to {max(ids)}\n")

    # Read pair thoughts + background from dynamic.db
    dyn = sqlite3.connect(f"file:{DYNAMIC_DB}?mode=ro", uri=True)
    dyn.row_factory = sqlite3.Row
    placeholders = ",".join("?" * len(ids))

    pair_rows = dyn.execute(
        f"SELECT thought FROM fountain_events "
        f"WHERE id IN ({placeholders}) "
        f"  AND thought IS NOT NULL AND thought != \'\'",
        ids,
    ).fetchall()

    # Background: same approximate id range, NOT in pair set
    background_rows = dyn.execute(
        f"SELECT thought FROM fountain_events "
        f"WHERE id NOT IN ({placeholders}) "
        f"  AND id > ? "
        f"  AND thought IS NOT NULL AND thought != \'\'",
        ids + [min(ids) - 500],
    ).fetchall()

    pair_tokens: Counter = Counter()
    pair_total = 0
    for r in pair_rows:
        toks = tokenize(r["thought"])
        pair_tokens.update(toks)
        pair_total += len(toks)

    bg_tokens: Counter = Counter()
    bg_total = 0
    for r in background_rows:
        toks = tokenize(r["thought"])
        bg_tokens.update(toks)
        bg_total += len(toks)

    print(f"Pair window:       {pair_total:4d} tokens, {len(pair_tokens):4d} unique")
    print(f"Background:        {bg_total:4d} tokens, {len(bg_tokens):4d} unique\n")

    # Compute log-ratio signature
    signature = []
    for word, count in pair_tokens.most_common(100):
        if count < 2:
            continue
        pair_rate = count / pair_total
        bg_rate = (bg_tokens.get(word, 0) / bg_total) if bg_total > 0 else 0
        ratio = (pair_rate + 1e-6) / (bg_rate + 1e-6)
        signature.append((word, count, round(ratio, 3)))
    signature.sort(key=lambda x: -x[2])
    top12_recent = signature[:12]

    # Cumulative signature from voice_profile
    sig_row = conv.execute(
        "SELECT signature_vocabulary, frequency, "
        "datetime(updated_at,\'unixepoch\',\'localtime\') AS updated_str "
        "FROM voice_profile WHERE drive_pair = ?",
        (DRIVE_PAIR_LABEL,),
    ).fetchone()

    if sig_row is None:
        print("No cumulative voice_profile row found.")
        return 1

    cumulative = json.loads(sig_row["signature_vocabulary"])
    top12_cumulative = cumulative[:12]

    print("=" * 70)
    print(f"CUMULATIVE (voice_profile, freq={sig_row['frequency']}, updated {sig_row['updated_str']}):")
    print("=" * 70)
    for e in top12_cumulative:
        print(f"  {e['word']:20s}  count={e['count']:3d}  ratio={e['ratio']:.1f}")

    print()
    print("=" * 70)
    print(f"RECENT {hours}h (computed live, {len(pair_rows)} fires):")
    print("=" * 70)
    for w, c, r in top12_recent:
        print(f"  {w:20s}  count={c:3d}  ratio={r:.1f}")

    cumulative_words = {e["word"] for e in top12_cumulative}
    recent_words = {w for w, _, _ in top12_recent}
    overlap = cumulative_words & recent_words
    only_recent = recent_words - cumulative_words
    only_cumulative = cumulative_words - recent_words

    print()
    print("=" * 70)
    print("DIFF:")
    print("=" * 70)
    print(f"  In both ({len(overlap):2d}):           {sorted(overlap)}")
    print(f"  Only in recent ({len(only_recent):2d}):    {sorted(only_recent)}")
    print(f"  Only in cumulative ({len(only_cumulative):2d}): {sorted(only_cumulative)}")

    # Interpretation hint
    print()
    print("=" * 70)
    print("INTERPRETATION:")
    print("=" * 70)
    if len(overlap) == 0:
        print("  FULL DIVERGENCE — recent register is statistically distinct")
        print("  from cumulative character. Either a real shift in progress,")
        print("  or a transient mode that has not yet reverted.")
    elif len(overlap) < 4:
        print("  HIGH DIVERGENCE — recent and cumulative share only a few")
        print("  words. Register is shifting; watch for direction over days.")
    elif len(overlap) < 8:
        print("  PARTIAL DIVERGENCE — moderate shift in progress, or noise")
        print("  on a stable underlying register.")
    else:
        print("  CONVERGED — recent matches cumulative character. Stable.")
    return 0


if __name__ == "__main__":
    hours = int(sys.argv[1]) if len(sys.argv) > 1 else 9
    sys.exit(main(hours))
