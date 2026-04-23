"""Belief edge graph + spreading activation tests.

Covers:
- belief_edges table created by init_db
- write_edge() writes correctly, duplicate updates weight
- ActivationEngine.activate() propagates scores through support edges
- Activation decays correctly across hops
- opposes edge produces negative score
- epistemic_temperature() returns 0.0 for empty activation
- typed_roles() correctly categorizes seed, support, bridge, tension
- BeliefRetriever falls back to keyword-only when no edges exist
- BeliefRetriever uses activation when edges exist
- Cross-domain detection writes edge between beliefs from different branches
- /api/beliefs/stats returns edge_count field
- No direct sqlite3 outside substrate/ (strikes/catalogue.py excepted by design)
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

from tests import _bootstrap  # noqa: F401


def _make_env():
    tmp = tempfile.mkdtemp(prefix="nex5_edges_")
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


def _insert_belief(writer, content, tier=5, confidence=0.7, branch_id=None):
    now = int(time.time())
    return writer.write(
        "INSERT INTO beliefs (content, tier, confidence, created_at, branch_id) "
        "VALUES (?, ?, ?, ?, ?)",
        (content, tier, confidence, now, branch_id),
    )


class TestBeliefEdgesTable(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_table_exists(self):
        row = self.readers["beliefs"].read_one(
            "SELECT COUNT(*) as cnt FROM belief_edges"
        )
        self.assertIsNotNone(row)
        self.assertEqual(row["cnt"], 0)

    def test_write_edge_creates_row(self):
        from theory_x.stage3_world_model.promotion import BeliefPromoter
        w = self.writers["beliefs"]
        r = self.readers["beliefs"]
        promoter = BeliefPromoter(w, r)

        id_a = _insert_belief(w, "The mind arises from neural activity", tier=5)
        id_b = _insert_belief(w, "Consciousness depends on brain states", tier=5)

        promoter.write_edge(id_a, id_b, "supports", 0.7)

        edge = r.read_one(
            "SELECT * FROM belief_edges WHERE source_id = ? AND target_id = ?",
            (id_a, id_b),
        )
        self.assertIsNotNone(edge)
        self.assertEqual(edge["edge_type"], "supports")
        self.assertAlmostEqual(edge["weight"], 0.7, places=3)

    def test_write_edge_duplicate_updates_weight(self):
        from theory_x.stage3_world_model.promotion import BeliefPromoter
        w = self.writers["beliefs"]
        r = self.readers["beliefs"]
        promoter = BeliefPromoter(w, r)

        id_a = _insert_belief(w, "Pattern recognition drives learning", tier=5)
        id_b = _insert_belief(w, "Learning requires pattern matching", tier=5)

        promoter.write_edge(id_a, id_b, "supports", 0.5)
        promoter.write_edge(id_a, id_b, "supports", 0.8)  # same type — updates weight

        rows = r.read(
            "SELECT * FROM belief_edges WHERE source_id = ? AND target_id = ? "
            "AND edge_type = 'supports'",
            (id_a, id_b),
        )
        self.assertEqual(len(rows), 1)
        self.assertAlmostEqual(rows[0]["weight"], 0.8, places=3)


class TestActivationEngine(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_activate_empty_edges_returns_empty(self):
        from theory_x.stage3_world_model.activation import ActivationEngine
        engine = ActivationEngine(self.readers["beliefs"])
        result = engine.activate([1, 2, 3])
        self.assertEqual(result, {})

    def test_activate_propagates_scores(self):
        from theory_x.stage3_world_model.promotion import BeliefPromoter
        from theory_x.stage3_world_model.activation import ActivationEngine
        w = self.writers["beliefs"]
        r = self.readers["beliefs"]
        promoter = BeliefPromoter(w, r)

        id_a = _insert_belief(w, "Attention focuses cognition", tier=5)
        id_b = _insert_belief(w, "Cognition shapes attention and focus", tier=5)

        promoter.write_edge(id_a, id_b, "supports", 1.0)

        engine = ActivationEngine(r)
        scores = engine.activate([id_a], hops=1, decay=0.55)

        self.assertAlmostEqual(scores[id_a], 1.0)
        self.assertGreater(scores.get(id_b, 0.0), 0.0)

    def test_activation_decay_across_hops(self):
        from theory_x.stage3_world_model.promotion import BeliefPromoter
        from theory_x.stage3_world_model.activation import ActivationEngine
        w = self.writers["beliefs"]
        r = self.readers["beliefs"]
        promoter = BeliefPromoter(w, r)

        id_a = _insert_belief(w, "World perception begins with sensation", tier=5)
        id_b = _insert_belief(w, "Sensation leads to perception of world", tier=5)
        id_c = _insert_belief(w, "Awareness follows sensation and perception", tier=5)

        promoter.write_edge(id_a, id_b, "supports", 1.0)
        promoter.write_edge(id_b, id_c, "supports", 1.0)

        engine = ActivationEngine(r)
        scores = engine.activate([id_a], hops=2, decay=0.55)

        score_b = scores.get(id_b, 0.0)
        score_c = scores.get(id_c, 0.0)
        # hop-2 target weaker than hop-1 target
        self.assertGreater(score_b, score_c)

    def test_opposes_edge_reduces_score(self):
        from theory_x.stage3_world_model.promotion import BeliefPromoter
        from theory_x.stage3_world_model.activation import ActivationEngine
        w = self.writers["beliefs"]
        r = self.readers["beliefs"]
        promoter = BeliefPromoter(w, r)

        id_a = _insert_belief(w, "Consciousness is substrate independent", tier=5)
        id_b = _insert_belief(w, "Consciousness requires biological substrate", tier=5)

        promoter.write_edge(id_a, id_b, "opposes", 0.8)

        engine = ActivationEngine(r)
        scores = engine.activate([id_a], hops=1, decay=0.55)
        self.assertLess(scores.get(id_b, 0.0), 0.0)


class TestEpistemicTemperature(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_empty_returns_zero(self):
        from theory_x.stage3_world_model.activation import ActivationEngine
        engine = ActivationEngine(self.readers["beliefs"])
        self.assertEqual(engine.epistemic_temperature({}), 0.0)

    def test_single_belief_returns_zero(self):
        from theory_x.stage3_world_model.activation import ActivationEngine
        engine = ActivationEngine(self.readers["beliefs"])
        self.assertEqual(engine.epistemic_temperature({1: 0.9}), 0.0)


class TestTypedRoles(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_roles_categorized(self):
        from theory_x.stage3_world_model.promotion import BeliefPromoter
        from theory_x.stage3_world_model.activation import ActivationEngine
        w = self.writers["beliefs"]
        r = self.readers["beliefs"]
        promoter = BeliefPromoter(w, r)

        id_seed = _insert_belief(w, "Attention directs cognition", branch_id="neuro")
        id_support = _insert_belief(w, "Focus guides cognitive processing", branch_id="neuro")
        id_bridge = _insert_belief(w, "Attention spans systems and domains", branch_id="systems")
        id_tension = _insert_belief(w, "Attention has no direction without cue", branch_id="neuro")

        promoter.write_edge(id_seed, id_support, "supports", 0.8)
        promoter.write_edge(id_seed, id_bridge, "cross_domain", 0.6)
        promoter.write_edge(id_seed, id_tension, "opposes", 0.7)

        engine = ActivationEngine(r)
        scores = engine.activate([id_seed], hops=1, decay=0.55)
        roles = engine.typed_roles(scores, [id_seed])

        seed_ids = [e["id"] for e in roles["seed"]]
        self.assertIn(id_seed, seed_ids)

        tension_ids = [e["id"] for e in roles["tension"]]
        self.assertIn(id_tension, tension_ids)


class TestRetrieverFallback(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_keyword_only_when_no_edges(self):
        from theory_x.stage3_world_model.retrieval import BeliefRetriever
        w = self.writers["beliefs"]
        r = self.readers["beliefs"]

        _insert_belief(w, "Consciousness arises from integration of information",
                       tier=4, confidence=0.9)
        _insert_belief(w, "Integration enables conscious experience", tier=5, confidence=0.8)

        retriever = BeliefRetriever(r)
        results = retriever.retrieve("consciousness integration")
        self.assertGreater(len(results), 0)
        # No role badge when no edges
        self.assertNotIn("_role", results[0])

    def test_activation_used_when_edges_exist(self):
        from theory_x.stage3_world_model.promotion import BeliefPromoter
        from theory_x.stage3_world_model.retrieval import BeliefRetriever
        w = self.writers["beliefs"]
        r = self.readers["beliefs"]
        promoter = BeliefPromoter(w, r)

        id_a = _insert_belief(w, "Memory consolidation occurs during sleep",
                               tier=4, confidence=0.85)
        id_b = _insert_belief(w, "Sleep enables memory and learning processes",
                               tier=5, confidence=0.75)
        promoter.write_edge(id_a, id_b, "supports", 0.9)

        retriever = BeliefRetriever(r)
        results = retriever.retrieve("memory sleep learning")
        self.assertGreater(len(results), 0)
        # Activation metadata present
        self.assertIn("_epistemic_temperature", results[0])


class TestCrossDomainDetection(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_cross_domain_edge_written(self):
        from theory_x.stage3_world_model.promotion import BeliefPromoter
        from theory_x.stage3_world_model.harmonizer import Harmonizer
        w = self.writers["beliefs"]
        r = self.readers["beliefs"]
        dw = self.writers["dynamic"]
        promoter = BeliefPromoter(w, r)
        harmonizer = Harmonizer(w, r, dw, promoter)

        # Identical keyword sets, different branches → high Jaccard overlap
        _insert_belief(
            w,
            "attention memory learning pattern recognition overlap test cross domain",
            tier=3, branch_id="neuro",
        )
        _insert_belief(
            w,
            "attention memory learning pattern recognition overlap test cross domain",
            tier=3, branch_id="systems",
        )

        written = harmonizer.detect_cross_domain()
        self.assertGreaterEqual(written, 1)

        rows = r.read("SELECT * FROM belief_edges WHERE edge_type = 'cross_domain'")
        self.assertGreater(len(rows), 0)


class TestGuiEdgeStats(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def test_stats_returns_edge_count(self):
        from gui.server import create_app, AppState
        from voice.llm import VoiceClient

        state = AppState(
            writers=self.writers,
            readers=self.readers,
            voice=VoiceClient(),
        )
        app = create_app(state)
        with app.test_client() as client:
            resp = client.get("/api/beliefs/stats")
            self.assertEqual(resp.status_code, 200)
            data = resp.get_json()
            self.assertIn("edge_count", data)
            self.assertIsInstance(data["edge_count"], int)
            self.assertIn("epistemic_temperature", data)


class TestNoDirectSqlite(unittest.TestCase):
    def test_no_direct_sqlite3_outside_substrate(self):
        """No file outside substrate/ should import sqlite3 directly.

        strikes/catalogue.py is the known intentional exception (its own
        read path pre-dates the substrate abstraction).
        """
        result = subprocess.run(
            ["grep", "-rl", "import sqlite3",
             "--include=*.py",
             "--exclude-dir=substrate",
             "--exclude-dir=.venv",
             "--exclude-dir=tests",
             "."],
            capture_output=True, text=True,
            cwd=Path(__file__).parent.parent,
        )
        KNOWN_EXCEPTIONS = {"./strikes/catalogue.py"}
        matches = [
            line for line in result.stdout.splitlines()
            if line and line not in KNOWN_EXCEPTIONS
        ]
        self.assertEqual(matches, [], f"Direct sqlite3 imports found: {matches}")


if __name__ == "__main__":
    unittest.main()
