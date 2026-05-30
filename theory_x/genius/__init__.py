"""Theory X — Genius subsystem.

GENIUS_SCORE_v2.md §7 — the auto-tagger that deploys the calibrated
v2 score as a continuous substrate signal. The morality-table from
SUBSTRATE_NOTES §1.

Phase 1 (this build): GeniusTagger SentienceNode + genius_tags table.
  Tag every fountain fire as it happens with the v2 score and class
  (STRIKING / ordinary). Backfill historical fires on first run.
  Log-only — no behavioral effect on other nodes yet.

Phase 2 (later): consumers read genius_tags and shift behavior —
  retrieval favoring high-score fires, fountain readiness modulated
  by recent tag rate, theory's organ outputs reading tag rate.

The score itself (score_v2.py) is already fitted on Jon's 103
hand-flagged training examples (97.1% training accuracy). This
subsystem deploys it.
"""
from __future__ import annotations

from theory_x.genius.tagger import GeniusTagger

__all__ = ["GeniusTagger"]
