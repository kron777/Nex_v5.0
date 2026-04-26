"""Tests for fountain retrieval: own thoughts dominate context over seeds."""
import tempfile
import os
import time
import unittest


def _make_env():
    tmp = tempfile.mkdtemp()
    os.environ["NEX5_DATA_DIR"] = tmp
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
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
    os.environ.pop("NEX5_DATA_DIR", None)


def _make_generator(writers, readers):
    from theory_x.stage6_fountain.generator import FountainGenerator
    from voice.llm import VoiceClient
    return FountainGenerator(
        sense_writer=writers["sense"],
        dynamic_writer=writers["dynamic"],
        voice_client=VoiceClient.__new__(VoiceClient),
        dynamic_reader=readers["dynamic"],
        beliefs_writer=writers.get("beliefs"),
        beliefs_reader=readers.get("beliefs"),
        sense_reader=readers.get("sense"),
    )


class TestFountainRetrieval(unittest.TestCase):

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.gen = _make_generator(self.writers, self.readers)

    def tearDown(self):
        _cleanup(self.writers, self.tmp)

    def _insert_belief(self, content, source, tier=6, confidence=0.70, offset_secs=0):
        ts = time.time() - offset_secs
        self.writers["beliefs"].write(
            "INSERT INTO beliefs (content, tier, confidence, created_at, source, branch_id, locked) "
            "VALUES (?, ?, ?, ?, ?, 'systems', 0)",
            (content, tier, confidence, ts, source),
        )

    def test_own_content_dominates_retrieval(self):
        # Insert 20 fountain_insight beliefs and 40 seeds
        for i in range(20):
            self._insert_belief(f"My own thought number {i}", "fountain_insight")
        for i in range(40):
            self._insert_belief(f"Seed content item {i}", "koan", tier=1, confidence=0.95)

        time.sleep(0.1)
        from theory_x.stage6_fountain.generator import _OWN_CONTENT_SOURCES, _SEED_SOURCES
        rows = self.gen._retrieve_context_beliefs(own_n=7, seed_n=2)
        own = [r for r in rows if r["source"] in _OWN_CONTENT_SOURCES]
        seeds = [r for r in rows if r["source"] in _SEED_SOURCES]

        self.assertEqual(len(own), 7)
        self.assertEqual(len(seeds), 2)

    def test_cold_start_with_no_own_content(self):
        # DB only has seed material (from init_all keystone seeds)
        rows = self.gen._retrieve_context_beliefs(own_n=7, seed_n=2)
        own = [r for r in rows if r["source"] in ("fountain_insight", "synergized")]
        # No own content — should return 0 own rows without error
        self.assertEqual(len(own), 0)
        # Seeds still retrieved
        self.assertGreater(len(rows), 0)

    def test_own_content_ordered_by_recency(self):
        # Insert beliefs with different ages
        for i in range(5):
            self._insert_belief(f"Thought {i}", "fountain_insight", offset_secs=i * 60)

        time.sleep(0.1)
        rows = self.gen._retrieve_context_beliefs(own_n=5, seed_n=0)
        own = [r for r in rows if r["source"] == "fountain_insight"]

        # Should be newest first
        for i in range(len(own) - 1):
            self.assertGreaterEqual(own[i]["created_at"], own[i + 1]["created_at"])

    def test_tier_ignored_retrieves_t7(self):
        # T7 beliefs should still be retrieved
        self._insert_belief("A T7 thought I had a while ago", "fountain_insight", tier=7)
        time.sleep(0.1)
        rows = self.gen._retrieve_context_beliefs(own_n=7, seed_n=0)
        own = [r for r in rows if r["source"] == "fountain_insight"]
        self.assertEqual(len(own), 1)
        self.assertEqual(own[0]["tier"], 7)

    def test_build_prompt_includes_own_content_section(self):
        self._insert_belief("I notice bitcoin feels quiet today.", "fountain_insight")
        time.sleep(0.1)
        prompt = self.gen._build_prompt({}, 10, {})
        self.assertIn("Some of what you've been thinking recently:", prompt)
        self.assertIn("bitcoin", prompt)

    def test_build_prompt_no_own_content_skips_section(self):
        # No fountain_insight beliefs seeded
        prompt = self.gen._build_prompt({}, 10, {})
        self.assertNotIn("Some of what you've been thinking recently:", prompt)

    def test_build_prompt_includes_beliefs_held(self):
        prompt = self.gen._build_prompt({}, 42, {})
        self.assertIn("Beliefs held: 42", prompt)


if __name__ == "__main__":
    unittest.main()
