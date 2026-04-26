"""
atlas_builder.py — Compile probe results into a condition × opcode matrix.

The atlas is a structured summary of which input configurations reliably
produce which output templates (opcodes). It answers:

  Given mode=X, sense_pattern=Y, prior_context=Z → which opcode fires?
  What is the probability distribution over opcodes for each condition?
  Which conditions are high-entropy (unpredictable) vs. low-entropy (locked)?

Output formats:
  - Console table (print_atlas)
  - JSON export (export_json)
  - Plain-text report (export_report)
"""
from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Optional

from decryption.probes_db import ProbesDB
from decryption.probe_set import DIMENSIONS

TEMPLATE_CATEGORIES = [
    "ABSTRACT_NOMINAL", "DIALECTICAL", "SENSE_OBS", "SIMILE",
    "QUESTION", "ACTION", "RECEPTIVITY", "UNCATEGORIZED",
]


# ---------------------------------------------------------------------------
# Atlas cell — one condition's template distribution.
# ---------------------------------------------------------------------------

class AtlasCell:
    def __init__(self, condition_hash: str, condition_meta: dict, results: list):
        self.hash = condition_hash
        self.meta = condition_meta  # {mode, sense_pattern, prior_context, ...}
        self.n_total = len(results)
        self.n_valid = sum(1 for r in results if r["output_template"]
                          not in (None, "TIMEOUT", "ERROR", "DRY_RUN"))
        self.template_counts = Counter(
            r["output_template"] for r in results
            if r["output_template"] and r["output_template"]
               not in ("TIMEOUT", "ERROR", "DRY_RUN")
        )
        self.dominant = self.template_counts.most_common(1)[0][0] if self.template_counts else None
        self.dominant_frac = (
            self.template_counts[self.dominant] / self.n_valid
            if self.dominant and self.n_valid else 0.0
        )
        self.entropy = self._entropy()

    def _entropy(self) -> float:
        if not self.n_valid:
            return float("nan")
        probs = [c / self.n_valid for c in self.template_counts.values()]
        return -sum(p * math.log2(p) for p in probs if p > 0)

    def prob(self, template: str) -> float:
        if not self.n_valid:
            return 0.0
        return self.template_counts.get(template, 0) / self.n_valid

    def label(self) -> str:
        parts = [self.meta.get(d, "?") for d in DIMENSIONS]
        return "|".join(parts)


# ---------------------------------------------------------------------------
# Atlas — the full collection of cells.
# ---------------------------------------------------------------------------

class Atlas:
    def __init__(self, cells: list[AtlasCell]):
        self.cells = cells
        self._by_hash = {c.hash: c for c in cells}

    def get(self, condition_hash: str) -> Optional[AtlasCell]:
        return self._by_hash.get(condition_hash)

    def cells_for_mode(self, mode: str) -> list[AtlasCell]:
        return [c for c in self.cells if c.meta.get("mode") == mode]

    def cells_for_dimension(self, dimension: str, value: str) -> list[AtlasCell]:
        return [c for c in self.cells if c.meta.get(dimension) == value]

    def locked_cells(self, threshold: float = 0.8) -> list[AtlasCell]:
        """Cells where dominant template fires ≥ threshold of the time."""
        return [c for c in self.cells if c.dominant_frac >= threshold]

    def high_entropy_cells(self, threshold: float = 1.5) -> list[AtlasCell]:
        """Cells with Shannon entropy ≥ threshold (unpredictable conditions)."""
        return [c for c in self.cells
                if not math.isnan(c.entropy) and c.entropy >= threshold]

    def dominant_template_for(self, **kwargs) -> Optional[str]:
        """
        Find the dominant template for conditions matching kwargs.
        E.g.: atlas.dominant_template_for(mode="mind", prior_context="observer_saturated")
        """
        matching = [
            c for c in self.cells
            if all(c.meta.get(k) == v for k, v in kwargs.items())
        ]
        if not matching:
            return None
        combined = Counter()
        for c in matching:
            combined.update(c.template_counts)
        return combined.most_common(1)[0][0] if combined else None


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------

def build_atlas(db: ProbesDB) -> Atlas:
    all_results = db.fetch_all_results()
    if not all_results:
        return Atlas([])

    by_hash: dict[str, list] = defaultdict(list)
    meta: dict[str, dict] = {}
    for row in all_results:
        h = row["condition_hash"]
        by_hash[h].append(row)
        if h not in meta:
            meta[h] = {d: row[d] for d in DIMENSIONS}

    cells = [
        AtlasCell(h, meta[h], by_hash[h])
        for h in by_hash
    ]
    return Atlas(cells)


# ---------------------------------------------------------------------------
# Output / reporting
# ---------------------------------------------------------------------------

def print_atlas(atlas: Atlas, group_by: str = "mode") -> None:
    if not atlas.cells:
        print("Atlas is empty. Run probes first.")
        return

    cats_abbrev = {
        "ABSTRACT_NOMINAL": "ABS",
        "DIALECTICAL":      "DIA",
        "SENSE_OBS":        "SNS",
        "SIMILE":           "SIM",
        "QUESTION":         "QST",
        "ACTION":           "ACT",
        "RECEPTIVITY":      "REC",
        "UNCATEGORIZED":    "UNC",
    }
    header_cats = list(cats_abbrev.values())

    print(f"\n=== OPCODE ATLAS (grouped by {group_by}) ===\n")
    print(f"{'Condition':<55} {'n':>4} {'H':>5}  " + "  ".join(header_cats))
    print("-" * (55 + 4 + 5 + 3 * len(header_cats) + 2 * len(header_cats)))

    groups: dict[str, list[AtlasCell]] = defaultdict(list)
    for cell in sorted(atlas.cells, key=lambda c: c.meta.get(group_by, "")):
        groups[cell.meta.get(group_by, "?")].append(cell)

    for group_val, cells in groups.items():
        print(f"\n  [{group_by}={group_val}]")
        for cell in cells:
            short_label = "|".join([
                cell.meta.get(d, "?")[:12]
                for d in DIMENSIONS if d != group_by
            ])
            h_str = f"{cell.entropy:.2f}" if not math.isnan(cell.entropy) else "  nan"
            prob_strs = [f"{cell.prob(t)*100:3.0f}" for t in TEMPLATE_CATEGORIES]
            print(f"  {short_label:<55} {cell.n_valid:>4} {h_str:>5}  " + "  ".join(prob_strs))


def export_json(atlas: Atlas, path: Path) -> None:
    data = []
    for cell in atlas.cells:
        data.append({
            "condition_hash":   cell.hash,
            "condition":        cell.meta,
            "n_total":          cell.n_total,
            "n_valid":          cell.n_valid,
            "dominant_template": cell.dominant,
            "dominant_frac":    round(cell.dominant_frac, 4),
            "entropy":          round(cell.entropy, 4) if not math.isnan(cell.entropy) else None,
            "template_probs":   {
                t: round(cell.prob(t), 4) for t in TEMPLATE_CATEGORIES
            },
        })
    path.write_text(json.dumps(data, indent=2))


def export_report(atlas: Atlas, path: Optional[Path] = None) -> str:
    lines = [
        "=== PROBE ATLAS REPORT ===",
        f"Total conditions: {len(atlas.cells)}",
        f"Locked cells (≥80% dominant): {len(atlas.locked_cells())}",
        f"High-entropy cells (H≥1.5): {len(atlas.high_entropy_cells())}",
        "",
    ]

    lines.append("LOCKED CONDITIONS (dominant template fires ≥80% of reps):")
    for cell in sorted(atlas.locked_cells(), key=lambda c: -c.dominant_frac):
        lines.append(
            f"  [{cell.dominant} {cell.dominant_frac*100:.0f}%] "
            f"n={cell.n_valid}  {cell.label()}"
        )

    lines.append("")
    lines.append("HIGH-ENTROPY CONDITIONS (H≥1.5, unpredictable):")
    for cell in sorted(atlas.high_entropy_cells(), key=lambda c: -c.entropy):
        lines.append(
            f"  [H={cell.entropy:.2f}] n={cell.n_valid}  {cell.label()}"
        )

    report = "\n".join(lines)
    if path:
        path.write_text(report)
    return report


if __name__ == "__main__":
    from decryption.probes_db import init_db
    db = init_db()
    atlas = build_atlas(db)
    print_atlas(atlas)
    print()
    print(export_report(atlas))
