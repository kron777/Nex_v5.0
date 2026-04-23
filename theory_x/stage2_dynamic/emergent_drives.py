"""Emergent Drive Detector — belief pressure proposes new curiosity branches.

When beliefs in a non-seed branch accumulate sufficient pressure
(verb_density × avg_confidence × belief_count > threshold), a new drive
is proposed. Jon approves/rejects from the GUI.
"""
from __future__ import annotations

import json
import time
from typing import Optional

import errors
from substrate import Reader, Writer

THEORY_X_STAGE = 2

_LOG_SOURCE = "emergent_drives"

PRESSURE_THRESHOLD = 0.4

_VERB_SUFFIXES = ("ing", "ed", "ize", "ise", "ate", "ify")

# Seed branch IDs — never re-proposed
_SEED_BRANCH_IDS = {
    "ai_research", "emerging_tech", "cognition_science", "computing",
    "systems", "crypto", "markets", "language", "history", "psychology",
}


def _verb_density(content: str) -> float:
    """Fraction of tokens that look like verbs (heuristic suffix check)."""
    tokens = content.lower().split()
    if not tokens:
        return 0.0
    verb_count = sum(
        1 for t in tokens if any(t.endswith(suf) for suf in _VERB_SUFFIXES)
    )
    return verb_count / len(tokens)


class EmergentDriveDetector:
    def __init__(self, dynamic_writer: Writer) -> None:
        self._dynamic_writer = dynamic_writer

    def scan_for_pressure(self, beliefs_reader: Reader,
                          dynamic_state) -> list[dict]:
        """Scan Tier 4+ beliefs grouped by branch; return pressure proposals."""
        try:
            rows = beliefs_reader.read(
                "SELECT id, content, branch_id, confidence FROM beliefs "
                "WHERE tier <= 4 AND confidence > 0.6 AND branch_id IS NOT NULL "
                "AND paused = 0 AND locked = 0 LIMIT 500"
            )
        except Exception as exc:
            errors.record(f"scan_for_pressure read error: {exc}", source=_LOG_SOURCE, exc=exc)
            return []

        # Group by branch_id
        grouped: dict[str, list[dict]] = {}
        for row in rows:
            bid = row["branch_id"]
            if bid not in grouped:
                grouped[bid] = []
            grouped[bid].append(dict(row))

        # Also collect existing non-seed branches from the tree
        existing_branches: set[str] = set(_SEED_BRANCH_IDS)
        try:
            if dynamic_state is not None:
                status = dynamic_state.status()
                for b in status.get("branches", []):
                    existing_branches.add(b["branch_id"])
        except Exception:
            pass

        proposals = []
        for branch_id, beliefs in grouped.items():
            if branch_id in _SEED_BRANCH_IDS:
                continue

            belief_count = len(beliefs)
            avg_conf = sum(b["confidence"] for b in beliefs) / belief_count
            combined_text = " ".join(b["content"] for b in beliefs)
            vd = _verb_density(combined_text)
            pressure = vd * avg_conf * min(belief_count, 10) / 10

            if pressure > PRESSURE_THRESHOLD:
                top3 = [b["content"][:120] for b in beliefs[:3]]
                proposals.append({
                    "branch": branch_id,
                    "pressure": round(pressure, 4),
                    "representative_beliefs": top3,
                    "proposed_curiosity": round(min(1.0, pressure), 3),
                })

        return proposals

    def log_proposals(self, proposals: list[dict]) -> None:
        """Log proposals to errors channel and write to drive_proposals table."""
        now = time.time()
        for p in proposals:
            errors.record(
                f"emergent drive proposal: branch='{p['branch']}' "
                f"pressure={p['pressure']:.3f} "
                f"curiosity={p['proposed_curiosity']:.3f}",
                source=_LOG_SOURCE, level="INFO",
            )
            try:
                self._dynamic_writer.write(
                    "INSERT INTO drive_proposals "
                    "(ts, branch_id, pressure, representative_beliefs, "
                    "proposed_curiosity, status) "
                    "VALUES (?, ?, ?, ?, ?, 'pending')",
                    (
                        now,
                        p["branch"],
                        p["pressure"],
                        json.dumps(p["representative_beliefs"]),
                        p["proposed_curiosity"],
                    ),
                )
            except Exception as exc:
                errors.record(f"log_proposals write error: {exc}", source=_LOG_SOURCE, exc=exc)

    def apply_approved(self, dynamic_state, beliefs_writer: Writer,
                       dynamic_reader: Reader) -> int:
        """Apply approved proposals to the bonsai tree. Returns count applied."""
        try:
            rows = dynamic_reader.read(
                "SELECT id, branch_id, proposed_curiosity FROM drive_proposals "
                "WHERE status = 'approved'"
            )
        except Exception as exc:
            errors.record(f"apply_approved read error: {exc}", source=_LOG_SOURCE, exc=exc)
            return 0

        applied = 0
        for row in rows:
            branch_id = row["branch_id"]
            curiosity = row["proposed_curiosity"]
            try:
                dynamic_state.tree.add_branch(branch_id, curiosity_weight=curiosity)
            except Exception:
                pass  # branch may already exist

            try:
                beliefs_writer.write(
                    "INSERT INTO beliefs "
                    "(content, tier, confidence, created_at, source, branch_id, locked) "
                    "VALUES (?, 5, 0.45, ?, 'emergent_drive', ?, 0)",
                    (
                        f"I have developed a new area of attention: {branch_id}",
                        int(time.time()),
                        branch_id,
                    ),
                )
            except Exception as exc:
                errors.record(f"apply_approved belief write error: {exc}", source=_LOG_SOURCE, exc=exc)

            try:
                self._dynamic_writer.write(
                    "UPDATE drive_proposals SET status = 'applied' WHERE id = ?",
                    (row["id"],),
                )
            except Exception:
                pass

            errors.record(
                f"emergent drive applied: branch='{branch_id}' curiosity={curiosity}",
                source=_LOG_SOURCE, level="INFO",
            )
            applied += 1

        return applied
