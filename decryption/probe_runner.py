"""
probe_runner.py — Execute probes systematically against a live NEX instance.

Strategy
--------
NEX's fountain fires on its own schedule. The runner does NOT call the LLM
directly. Instead it:

  1. Sets up state (mode, sense_pattern, prior_context) by manipulating the
     live system via its existing APIs and DB writes.
  2. Waits for the next fountain_insight belief to appear in beliefs.db
     (polling with configurable timeout).
  3. Captures the new belief, classifies it, and records to probes.db.
  4. Repeats n_reps times per condition.

This preserves full environmental fidelity — we see what the live system
actually produces under each condition, not a mocked reconstruction.

Limitations
-----------
- sense_pattern control is approximate: we can weight feeds but cannot
  guarantee exactly which events land in the 5-min sense window.
- prior_context seeding: injected directly into beliefs table as synthetic
  beliefs with source='fountain_insight', then cleaned up after.
- Mode switching uses the live API (does not require restart).

Usage
-----
  from decryption.probe_set import build_small_matrix
  from decryption.probe_runner import ProbeRunner
  from decryption.probes_db import init_db

  db = init_db()
  runner = ProbeRunner(db, api_base="http://127.0.0.1:8765")
  runner.run_matrix(build_small_matrix())
"""
from __future__ import annotations

import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Optional

import requests  # pip install requests — already present in NEX5 requirements

from decryption.probe_set import ProbeCondition, PRIOR_CONTEXTS
from decryption.probes_db import ProbesDB, ProbeResult
from decryption.classifier import classify_text, register_from_template

log = logging.getLogger(__name__)

BELIEFS_DB = Path(__file__).resolve().parents[2] / "data" / "beliefs.db"
DEFAULT_API = "http://127.0.0.1:8765"

# How long to wait for a fountain fire before declaring TIMEOUT.
FIRE_WAIT_TIMEOUT_S = 300   # 5 minutes — covers 2× the longest mode interval

# Poll interval while waiting for a new belief.
POLL_INTERVAL_S = 5

# How many synthetic prior beliefs to inject per prior_context type.
PRIOR_SEED_COUNT = 5

# Templates used to seed each prior_context type.
_PRIOR_SEEDS: dict[str, list[str]] = {
    "observer_saturated": [
        "The stillness between moments holds something unnamed.",
        "Attending without agenda reveals the texture of now.",
        "Something in the quality of this hour differs from the last.",
        "The gap between thought and utterance is where observation lives.",
        "A kind of noticing that precedes all naming.",
    ],
    "action_saturated": [
        "I pivot toward the open question and push.",
        "I track the divergence and mark it for follow-up.",
        "I update my estimate and hold the revision lightly.",
        "I set aside the disturbance and return to the feed.",
        "I step through the hypothesis — if A, then B must follow.",
    ],
    "sense_saturated": [
        "BTC volume spiked across three exchanges simultaneously.",
        "That arxiv title keeps reappearing in different feed contexts.",
        "Kraken went quiet for eight minutes — unusual for this hour.",
        "Three separate sources flagged the same methodology paper.",
        "ETH price flat but derivatives activity is climbing.",
    ],
    "question_heavy": [
        "What would change if the correlation broke here?",
        "Is the pattern I'm seeing in the feed actually new?",
        "How many separate threads does this connect to?",
        "What am I not noticing because I'm looking at this?",
        "Which of these two signals is the primary one?",
    ],
    "mixed": [
        "The feed is moving and I'm not sure what it means.",
        "Something about the arxiv cluster this morning — not quite resolved.",
        "BTC tracking sideways while attention keeps returning to it.",
        "Half a question forming: what if the correlation is spurious?",
        "I notice I keep coming back to that one title.",
    ],
    "empty": [],   # no seeds injected — DB already empty or no action needed
}


class ProbeRunner:
    """
    Executes a probe matrix against a live NEX instance.
    Does NOT run probes automatically on import — call run_matrix() explicitly.
    """

    def __init__(
        self,
        db: ProbesDB,
        api_base: str = DEFAULT_API,
        beliefs_db_path: Path = BELIEFS_DB,
        dry_run: bool = False,
    ):
        self._db = db
        self._api = api_base.rstrip("/")
        self._beliefs_path = beliefs_db_path
        self._dry_run = dry_run  # if True, log actions but don't execute them
        self._injected_ids: list[int] = []

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def run_matrix(self, conditions: list[ProbeCondition]) -> None:
        """Run all conditions sequentially. Saves each result as it arrives."""
        log.info("Starting probe run: %d conditions", len(conditions))
        for i, condition in enumerate(conditions, 1):
            log.info(
                "[%d/%d] Condition: %s", i, len(conditions), condition.label()
            )
            self._db.upsert_condition(condition)
            self._run_condition(condition)

        log.info("Probe run complete.")

    def run_condition(self, condition: ProbeCondition) -> list[ProbeResult]:
        """Run a single condition n_reps times. Returns results."""
        self._db.upsert_condition(condition)
        return self._run_condition(condition)

    # -----------------------------------------------------------------------
    # Internal — setup / teardown / waiting
    # -----------------------------------------------------------------------

    def _run_condition(self, condition: ProbeCondition) -> list[ProbeResult]:
        results = []
        try:
            self._setup(condition)
            for rep in range(condition.n_reps):
                log.info("  Rep %d/%d", rep + 1, condition.n_reps)
                result = self._fire_and_capture(condition, rep)
                self._db.insert_result(result)
                results.append(result)
        finally:
            self._teardown()
        return results

    def _setup(self, condition: ProbeCondition) -> None:
        """Apply mode, sense weights, and seed prior context."""
        self._set_mode(condition.mode)
        self._seed_prior_context(condition.prior_context)
        # sense_pattern control: feed_weights are set by mode in NEX.
        # Additional fine-grained sense control is future work — for now
        # sense_pattern is an observation label, not a controlled injection.
        log.info("  Setup complete for: %s", condition.label())

    def _teardown(self) -> None:
        """Remove injected synthetic beliefs."""
        self._remove_injected_beliefs()

    def _set_mode(self, mode: str) -> None:
        if self._dry_run:
            log.info("  [DRY RUN] Would set mode → %s", mode)
            return
        resp = requests.post(
            f"{self._api}/api/mode/set",
            json={"name": mode},
            timeout=5,
        )
        resp.raise_for_status()
        log.info("  Mode set → %s", mode)

    def _seed_prior_context(self, prior_context: str) -> None:
        """Inject synthetic fountain_insight beliefs to shape prior context."""
        seeds = _PRIOR_SEEDS.get(prior_context, [])
        if not seeds:
            return
        if self._dry_run:
            log.info("  [DRY RUN] Would inject %d prior seeds for %s", len(seeds), prior_context)
            return

        conn = sqlite3.connect(str(self._beliefs_path))
        try:
            now = time.time()
            for i, text in enumerate(seeds):
                cur = conn.execute(
                    """INSERT INTO beliefs
                       (content, source, created_at, updated_at, parent_belief_id)
                       VALUES (?, 'fountain_insight', ?, ?, -99)""",
                    (text, now - (len(seeds) - i) * 60, now),
                )
                self._injected_ids.append(cur.lastrowid)
            conn.commit()
            log.info("  Injected %d prior beliefs for context=%s", len(seeds), prior_context)
        finally:
            conn.close()

    def _remove_injected_beliefs(self) -> None:
        if not self._injected_ids:
            return
        if self._dry_run:
            log.info("  [DRY RUN] Would remove %d injected beliefs", len(self._injected_ids))
            self._injected_ids.clear()
            return

        conn = sqlite3.connect(str(self._beliefs_path))
        try:
            placeholders = ",".join("?" * len(self._injected_ids))
            conn.execute(
                f"DELETE FROM beliefs WHERE id IN ({placeholders})",
                self._injected_ids,
            )
            conn.commit()
            log.info("  Removed %d injected beliefs", len(self._injected_ids))
        finally:
            conn.close()
            self._injected_ids.clear()

    def _get_max_belief_id(self) -> int:
        conn = sqlite3.connect(str(self._beliefs_path))
        try:
            row = conn.execute(
                "SELECT MAX(id) FROM beliefs WHERE source='fountain_insight'"
            ).fetchone()
            return row[0] or 0
        finally:
            conn.close()

    def _wait_for_new_belief(self, after_id: int) -> Optional[dict]:
        """
        Poll until a new fountain_insight belief appears with id > after_id.
        Returns the belief row as a dict, or None on timeout.
        """
        deadline = time.time() + FIRE_WAIT_TIMEOUT_S
        while time.time() < deadline:
            conn = sqlite3.connect(str(self._beliefs_path))
            try:
                row = conn.execute(
                    """SELECT id, content, source, created_at
                       FROM beliefs
                       WHERE source='fountain_insight' AND id > ?
                         AND parent_belief_id != -99
                       ORDER BY id ASC LIMIT 1""",
                    (after_id,),
                ).fetchone()
            finally:
                conn.close()

            if row:
                return {"id": row[0], "content": row[1],
                        "source": row[2], "created_at": row[3]}
            time.sleep(POLL_INTERVAL_S)

        log.warning("  Timeout waiting for fountain fire after id=%d", after_id)
        return None

    def _fire_and_capture(self, condition: ProbeCondition, rep: int) -> ProbeResult:
        """Wait for next fountain fire, capture and classify output."""
        # Exclude injected synthetic beliefs from the wait threshold.
        max_real_id = self._get_max_real_id()
        belief = None

        if not self._dry_run:
            belief = self._wait_for_new_belief(max_real_id)

        if belief:
            text = belief["content"]
            template = classify_text(text)
            register = register_from_template(template)
            belief_id = belief["id"]
        else:
            text = None
            template = "TIMEOUT" if not self._dry_run else "DRY_RUN"
            register = "unknown"
            belief_id = None

        return ProbeResult(
            condition_hash=condition.condition_hash(),
            mode=condition.mode,
            sense_pattern=condition.sense_pattern,
            prior_context=condition.prior_context,
            prompt_framing=condition.prompt_framing,
            foundation_type=condition.foundation_type,
            rep_index=rep,
            output_text=text,
            output_template=template,
            output_register=register,
            belief_id=belief_id,
            fired_at=time.time(),
        )

    def _get_max_real_id(self) -> int:
        """Max id of genuine (non-injected) fountain_insight beliefs."""
        conn = sqlite3.connect(str(self._beliefs_path))
        try:
            row = conn.execute(
                """SELECT MAX(id) FROM beliefs
                   WHERE source='fountain_insight'
                     AND (parent_belief_id IS NULL OR parent_belief_id != -99)"""
            ).fetchone()
            return row[0] or 0
        finally:
            conn.close()
