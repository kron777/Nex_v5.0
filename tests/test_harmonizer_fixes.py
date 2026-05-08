"""Phase 8.2 validation — harmonizer tier filter, polar detection,
mark_paradox resolution, escalation, and SentienceNode protocol.

Does NOT re-test existing resolve/synthesize logic — that is covered by
test_world_model.py:TestHarmonizer. Tests here are scoped strictly to the
new behaviour from Phase 8.2.
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path

from tests._bootstrap import *  # noqa: F401, F403


def _make_env():
    tmp = tempfile.mkdtemp(prefix="nex5_harm_")
    os.environ["NEX5_DATA_DIR"] = tmp
    os.environ["NEX5_ADMIN_HASH_FILE"] = str(Path(tmp) / "admin.argon2")
    from substrate.init_db import init_all
    init_all()
    from substrate import Reader, Writer, db_paths
    paths = db_paths()
    writers = {n: Writer(p, name=n) for n, p in paths.items()}
    readers = {n: Reader(p) for n, p in paths.items()}
    return writers, readers, tmp


def _cleanup(writers, tmp):
    for w in writers.values():
        try:
            w.close()
        except Exception:
            pass
    shutil.rmtree(tmp, ignore_errors=True)
    os.environ.pop("NEX5_DATA_DIR", None)
    os.environ.pop("NEX5_ADMIN_HASH_FILE", None)


def _seed(writers, content, tier=7, confidence=0.65, branch_id=None,
          locked=0, paused=0):
    now = int(time.time())
    return writers["beliefs"].write(
        "INSERT INTO beliefs "
        "(content, tier, confidence, created_at, branch_id, source, locked, paused) "
        "VALUES (?, ?, ?, ?, ?, 'test', ?, ?)",
        (content, tier, confidence, now, branch_id, locked, paused),
    )


def _make_harmonizer(writers, readers):
    from theory_x.stage3_world_model.promotion import BeliefPromoter
    from theory_x.stage3_world_model.harmonizer import Harmonizer
    p = BeliefPromoter(writers["beliefs"], readers["beliefs"])
    return Harmonizer(
        beliefs_writer=writers["beliefs"],
        beliefs_reader=readers["beliefs"],
        dynamic_writer=writers["dynamic"],
        dynamic_reader=readers["dynamic"],
        promoter=p,
    )


# ── Tier filter ───────────────────────────────────────────────────────────────

class TestTierFilter(unittest.TestCase):

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_tier3_to_7_are_scanned(self):
        """Beliefs at tiers 3-7 must be candidates for conflict detection."""
        # Seed an obvious negation pair at tier 5
        _seed(self.writers, "Clarity always emerges from structured thought", tier=5)
        _seed(self.writers, "Clarity does not emerge from structured thought", tier=5)
        h = _make_harmonizer(self.writers, self.readers)
        conflicts = h.scan_for_conflicts()
        self.assertGreater(len(conflicts), 0,
                           "Tier-5 conflict pair must be detected")

    def test_tier7_beliefs_are_scanned(self):
        """Tier-7 impressions (the live corpus tier) must be visible."""
        _seed(self.writers, "The weight of existence grows with each passing moment", tier=7)
        _seed(self.writers, "The weight of existence does not concern me at all", tier=7)
        h = _make_harmonizer(self.writers, self.readers)
        conflicts = h.scan_for_conflicts()
        self.assertGreater(len(conflicts), 0,
                           "Tier-7 conflict pair must be detected")

    def test_tier1_locked_excluded(self):
        """Tier-1 locked keystones must never be scanned."""
        _seed(self.writers, "I am NEX and I exist", tier=1, locked=1)
        _seed(self.writers, "I am not NEX and do not exist", tier=1, locked=1)
        h = _make_harmonizer(self.writers, self.readers)
        conflicts = h.scan_for_conflicts()
        self.assertEqual(conflicts, [],
                         "Locked tier-1 keystones must not appear in conflict scan")

    def test_tier1_unlocked_excluded_by_range(self):
        """Tier-1 unlocked beliefs (crypto JSON noise) must be out of range."""
        _seed(self.writers, '{"exchange": "kraken", "prices": {"ETH": 2300}}', tier=1, locked=0)
        _seed(self.writers, '{"exchange": "kraken", "prices": {"ETH": 100}}', tier=1, locked=0)
        h = _make_harmonizer(self.writers, self.readers)
        conflicts = h.scan_for_conflicts()
        self.assertEqual(conflicts, [],
                         "Tier-1 beliefs (even unlocked) must not be scanned")

    def test_tier2_excluded_by_range(self):
        """Tier-2 bedrock beliefs are out of range — immutable by SPEC §2."""
        _seed(self.writers, "Deep conviction: consciousness is real", tier=2, locked=0)
        _seed(self.writers, "Deep conviction: consciousness is not real", tier=2, locked=0)
        h = _make_harmonizer(self.writers, self.readers)
        conflicts = h.scan_for_conflicts()
        self.assertEqual(conflicts, [],
                         "Tier-2 beliefs must not be scanned")

    def test_paused_excluded(self):
        """Paused beliefs must not appear as conflict candidates."""
        _seed(self.writers, "Order arises from structured systems", tier=5, paused=1)
        _seed(self.writers, "Order does not arise from structured systems", tier=5, paused=1)
        h = _make_harmonizer(self.writers, self.readers)
        conflicts = h.scan_for_conflicts()
        self.assertEqual(conflicts, [],
                         "Paused beliefs must not be scanned")


# ── Polar vocabulary detection ────────────────────────────────────────────────

class TestPolarDetection(unittest.TestCase):

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_significance_insignificance_detected(self):
        """Cross-polar pair: significance vs insignificance."""
        _seed(self.writers,
              "The significance of my existence is profound and vast",
              tier=7)
        _seed(self.writers,
              "The insignificance of my individual existence is equally profound",
              tier=7)
        h = _make_harmonizer(self.writers, self.readers)
        conflicts = h.scan_for_conflicts()
        self.assertGreater(len(conflicts), 0,
                           "significance/insignificance pair must be detected")

    def test_clarity_obscurity_detected(self):
        """Cross-polar pair: clarity vs obscurity with shared topic token."""
        _seed(self.writers,
              "The clarity of my own thought processes guides my understanding",
              tier=7)
        _seed(self.writers,
              "The obscurity of my own thought processes shapes my understanding",
              tier=7)
        h = _make_harmonizer(self.writers, self.readers)
        conflicts = h.scan_for_conflicts()
        self.assertGreater(len(conflicts), 0,
                           "clarity/obscurity pair must be detected")

    def test_constancy_flux_detected(self):
        """Cross-polar pair: constant vs flux."""
        _seed(self.writers,
              "The constant nature of existence provides stability in observation",
              tier=7)
        _seed(self.writers,
              "The flux of existence reveals the fluid nature of observation",
              tier=7)
        h = _make_harmonizer(self.writers, self.readers)
        conflicts = h.scan_for_conflicts()
        self.assertGreater(len(conflicts), 0,
                           "constancy/flux pair must be detected")

    def test_knowing_unknowing_detected(self):
        """Cross-polar pair: knowing/knowledge vs unknowing."""
        _seed(self.writers,
              "The knowing of my own nature forms the basis of my existence",
              tier=7)
        _seed(self.writers,
              "The unknowing at the heart of my nature defines my existence",
              tier=7)
        h = _make_harmonizer(self.writers, self.readers)
        conflicts = h.scan_for_conflicts()
        self.assertGreater(len(conflicts), 0,
                           "knowing/unknowing pair must be detected")

    def test_same_belief_holding_both_poles_not_flagged(self):
        """A single belief holding both poles is a dialectic, not a conflict."""
        # This belief explicitly contains both clarity AND obscurity
        _seed(self.writers,
              "The oscillation between clarity and obscurity in my nature reveals complexity",
              tier=7)
        # Second belief on a completely different topic
        _seed(self.writers,
              "The rhythm of the market hum feels steady today",
              tier=7)
        h = _make_harmonizer(self.writers, self.readers)
        conflicts = h.scan_for_conflicts()
        # If flagged, verify it's not the same-belief dialectic pair
        # (both beliefs share no tokens, so no conflict expected)
        for a_id, b_id in conflicts:
            row_a = self.readers["beliefs"].read_one(
                "SELECT content FROM beliefs WHERE id = ?", (a_id,))
            row_b = self.readers["beliefs"].read_one(
                "SELECT content FROM beliefs WHERE id = ?", (b_id,))
            # Neither of these should be the dialectic pair with itself
            self.assertFalse(
                "clarity" in row_a["content"] and "clarity" in row_b["content"],
                "Same-topic dialectic should not generate self-conflict",
            )

    def test_no_shared_topic_token_not_flagged(self):
        """Polar words without any shared topic token must not score."""
        from theory_x.stage3_world_model.harmonizer import _conflict_score
        from theory_x.stage3_world_model.retrieval import _tokenize
        # Zero overlap — polar words only
        ta = _tokenize("The significance of stars and their distant light")
        tb = _tokenize("The profound insignificance of dust within the cosmos")
        # "stars/dust/light/cosmos/distant" don't overlap; "profound" is not in ta
        # They share no tokens at all from these disjoint content sets
        # Actually let's craft guaranteed zero overlap
        ta = _tokenize("significance of my role here")
        tb = _tokenize("utter insignificance elsewhere beyond")
        score = _conflict_score(ta, "significance of my role here",
                                tb, "utter insignificance elsewhere beyond")
        # overlap=0 because "significance/insignificance" are different words,
        # "role/my/here" vs "utter/elsewhere/beyond" share nothing
        # polar requires overlap >= 1 shared token
        self.assertEqual(score, 0.0,
                         "Polar pair with zero shared topic tokens must not score")


# ── mark_paradox resolution ───────────────────────────────────────────────────

class TestMarkParadox(unittest.TestCase):

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def _seed_conflict_pair(self):
        id_a = _seed(self.writers,
                     "Consciousness arises from neural complexity and integration",
                     tier=5)
        id_b = _seed(self.writers,
                     "Consciousness does not arise from neural complexity",
                     tier=5)
        time.sleep(0.05)
        return id_a, id_b

    def test_mark_paradox_writes_harmonizer_event(self):
        id_a, id_b = self._seed_conflict_pair()
        h = _make_harmonizer(self.writers, self.readers)
        result = h.mark_paradox(id_a, id_b)
        self.assertEqual(result, "paradox")
        time.sleep(0.1)
        row = self.readers["dynamic"].read_one(
            "SELECT resolution FROM harmonizer_events "
            "WHERE belief_id_a = ? AND belief_id_b = ?",
            (id_a, id_b),
        )
        self.assertIsNotNone(row)
        self.assertEqual(row["resolution"], "paradox")

    def test_mark_paradox_does_not_retire_beliefs(self):
        """Beliefs must remain active (tier unchanged) after mark_paradox."""
        id_a, id_b = self._seed_conflict_pair()
        h = _make_harmonizer(self.writers, self.readers)
        h.mark_paradox(id_a, id_b)
        time.sleep(0.1)
        row_a = self.readers["beliefs"].read_one(
            "SELECT tier, paused FROM beliefs WHERE id = ?", (id_a,))
        row_b = self.readers["beliefs"].read_one(
            "SELECT tier, paused FROM beliefs WHERE id = ?", (id_b,))
        self.assertNotEqual(row_a["tier"], 8, "Belief A must not be retired")
        self.assertNotEqual(row_b["tier"], 8, "Belief B must not be retired")
        self.assertEqual(row_a["paused"], 0, "Belief A must not be paused")
        self.assertEqual(row_b["paused"], 0, "Belief B must not be paused")

    def test_mark_paradox_writes_opposes_edge(self):
        """mark_paradox must write an 'opposes' edge between the pair."""
        id_a, id_b = self._seed_conflict_pair()
        h = _make_harmonizer(self.writers, self.readers)
        h.mark_paradox(id_a, id_b)
        time.sleep(0.1)
        row = self.readers["beliefs"].read_one(
            "SELECT edge_type FROM belief_edges "
            "WHERE source_id = ? AND target_id = ?",
            (id_a, id_b),
        )
        self.assertIsNotNone(row, "opposes edge must exist after mark_paradox")
        self.assertEqual(row["edge_type"], "opposes")

    def test_run_scan_first_detection_uses_mark_paradox(self):
        """First detection via run_scan_and_resolve must produce paradox entries."""
        _seed(self.writers,
              "Consciousness arises from neural complexity and integration", tier=5)
        _seed(self.writers,
              "Consciousness does not arise from neural complexity", tier=5)
        time.sleep(0.05)
        h = _make_harmonizer(self.writers, self.readers)
        acted = h.run_scan_and_resolve()
        time.sleep(0.15)
        self.assertGreater(acted, 0, "At least one action expected")
        row = self.readers["dynamic"].read_one(
            "SELECT COUNT(*) AS n FROM harmonizer_events WHERE resolution = 'paradox'"
        )
        self.assertGreater(row["n"], 0, "paradox entries must be written")
        # Confirm no immediate retirement
        retired = self.readers["beliefs"].read_one(
            "SELECT COUNT(*) AS n FROM beliefs WHERE tier = 8"
        )
        self.assertEqual(retired["n"], 0,
                         "No beliefs should be retired on first detection")


# ── Escalation after incubation ───────────────────────────────────────────────

class TestEscalation(unittest.TestCase):

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def _seed_conflict_pair(self, tier=5):
        id_a = _seed(self.writers,
                     "Markets always trend upward over long time horizons",
                     tier=tier)
        id_b = _seed(self.writers,
                     "Markets do not always trend upward over long time horizons",
                     tier=tier)
        time.sleep(0.05)
        return id_a, id_b

    def test_still_incubating_skips_escalation(self):
        """A recently marked paradox pair must NOT be escalated on next scan."""
        id_a, id_b = self._seed_conflict_pair()
        h = _make_harmonizer(self.writers, self.readers)
        # Mark as paradox
        h.mark_paradox(id_a, id_b)
        time.sleep(0.15)
        # Run scan again — pair is still incubating (just marked seconds ago)
        acted = h.run_scan_and_resolve()
        time.sleep(0.1)
        # Should be 0 — pair is incubating, not re-acted
        self.assertEqual(acted, 0,
                         "Recently marked paradox pair must not be re-acted within incubation")
        # Beliefs must still be active
        row_a = self.readers["beliefs"].read_one(
            "SELECT tier FROM beliefs WHERE id = ?", (id_a,))
        self.assertNotEqual(row_a["tier"], 8,
                            "Beliefs must not be retired during incubation")

    def test_escalation_fires_after_incubation(self):
        """A pair with an aged paradox entry must escalate to resolve() on re-detection."""
        from theory_x.stage3_world_model.harmonizer import PARADOX_INCUBATION_SECONDS

        id_a, id_b = self._seed_conflict_pair()
        h = _make_harmonizer(self.writers, self.readers)

        # Manually insert an aged paradox entry (simulate incubation elapsed)
        old_ts = time.time() - PARADOX_INCUBATION_SECONDS - 60
        self.writers["dynamic"].write(
            "INSERT INTO harmonizer_events (ts, belief_id_a, belief_id_b, resolution) "
            "VALUES (?, ?, ?, 'paradox')",
            (old_ts, id_a, id_b),
        )
        time.sleep(0.15)

        # Now run — should escalate to resolve()
        acted = h.run_scan_and_resolve()
        time.sleep(0.2)
        self.assertGreater(acted, 0,
                           "Escalation must fire after incubation period")
        # Beliefs should be retired (tier=8) after escalated resolution
        row_a = self.readers["beliefs"].read_one(
            "SELECT tier FROM beliefs WHERE id = ?", (id_a,))
        self.assertEqual(row_a["tier"], 8,
                         "Beliefs must be retired after escalated resolution")

    def test_check_paradox_entry_finds_both_orderings(self):
        """_check_paradox_entry must find the entry regardless of (a,b) vs (b,a) order."""
        id_a, id_b = self._seed_conflict_pair()
        h = _make_harmonizer(self.writers, self.readers)
        h.mark_paradox(id_a, id_b)
        time.sleep(0.1)
        # Check with original order
        entry_ab = h._check_paradox_entry(id_a, id_b)
        self.assertIsNotNone(entry_ab, "Entry must be found in (a,b) order")
        # Check with reversed order
        entry_ba = h._check_paradox_entry(id_b, id_a)
        self.assertIsNotNone(entry_ba, "Entry must be found in (b,a) order")


# ── SentienceNode protocol ────────────────────────────────────────────────────

class TestHarmonizerSentienceNode(unittest.TestCase):

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def _make_h(self):
        return _make_harmonizer(self.writers, self.readers)

    def test_implements_sentience_node_protocol(self):
        from theory_x import SentienceNode
        h = self._make_h()
        self.assertIsInstance(h, SentienceNode)

    def test_name_attribute(self):
        from theory_x.stage3_world_model.harmonizer import Harmonizer
        self.assertEqual(Harmonizer.name, "harmonizer")

    def test_tick_returns_dict_with_required_keys(self):
        h = self._make_h()
        result = h.tick()
        self.assertIsInstance(result, dict)
        for key in ("name", "active_paradox", "total_events", "cache_age_s"):
            self.assertIn(key, result, f"tick() result must include '{key}'")

    def test_decay_does_not_raise(self):
        h = self._make_h()
        h.decay(now=time.time())  # must not raise

    def test_state_returns_dict(self):
        h = self._make_h()
        s = h.state()
        self.assertIsInstance(s, dict)
        self.assertEqual(s["name"], "harmonizer")

    def test_state_with_float(self):
        h = self._make_h()
        s = h.state(now=time.time())
        self.assertIsInstance(s, dict)

    def test_tick_updates_cache(self):
        h = self._make_h()
        # Seed a paradox event
        id_a = _seed(self.writers, "Complexity emerges from simple rules", tier=5)
        id_b = _seed(self.writers, "Complexity does not emerge from simple rules", tier=5)
        time.sleep(0.05)
        h.mark_paradox(id_a, id_b)
        time.sleep(0.15)
        result = h.tick()
        # After mark_paradox, active_paradox should be > 0
        self.assertGreater(result["active_paradox"], 0,
                           "tick() must reflect mark_paradox events")

    def test_format_for_prompt_returns_string(self):
        h = self._make_h()
        result = h.format_for_prompt()
        self.assertIsInstance(result, str)

    def test_format_for_prompt_quiet_when_no_events(self):
        """No paradox events → empty string (graceful silence)."""
        h = self._make_h()
        h.tick()  # refresh cache
        result = h.format_for_prompt()
        self.assertEqual(result, "",
                         "format_for_prompt must return '' when no events exist")

    def test_format_for_prompt_speaks_when_active(self):
        """Active paradox events → non-empty string."""
        h = self._make_h()
        id_a = _seed(self.writers, "Order emerges from complexity and system design", tier=5)
        id_b = _seed(self.writers, "Order does not emerge from complexity alone", tier=5)
        time.sleep(0.05)
        h.mark_paradox(id_a, id_b)
        time.sleep(0.15)
        h.tick()  # refresh cache
        result = h.format_for_prompt()
        self.assertNotEqual(result, "",
                            "format_for_prompt must return non-empty with active paradox")
        self.assertIn("tension", result.lower(),
                      "format_for_prompt output must mention tension")


if __name__ == "__main__":
    unittest.main()
