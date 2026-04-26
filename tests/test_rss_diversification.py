"""Tests for the 6 new RSS feed diversification adapters."""
from __future__ import annotations

import json
import unittest
from unittest.mock import MagicMock


# Minimal RSS fixture — valid enough for feedparser to parse
_RSS_FIXTURE = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <link>https://example.com</link>
    <description>Test</description>
    <item>
      <title>On the Riemann Hypothesis and its implications</title>
      <link>https://example.com/1</link>
      <description>A fascinating conjecture about prime distributions.</description>
      <pubDate>Thu, 24 Apr 2026 12:00:00 +0000</pubDate>
    </item>
    <item>
      <title>Second article title here</title>
      <link>https://example.com/2</link>
      <description>Second article summary text goes here in brief.</description>
      <pubDate>Thu, 24 Apr 2026 11:00:00 +0000</pubDate>
    </item>
  </channel>
</rss>"""

_ATOM_FIXTURE = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Test Atom Feed</title>
  <link href="https://example.com"/>
  <entry>
    <title>Featured: History of Computing</title>
    <link href="https://example.com/article"/>
    <summary>A summary of the history of computing machines.</summary>
    <updated>2026-04-24T12:00:00Z</updated>
  </entry>
</feed>"""


def _stub_writer():
    w = MagicMock()
    w.write.return_value = 1
    return w


def _make_adapter(cls, fixture=_RSS_FIXTURE):
    writer = _stub_writer()
    adapter = cls.__new__(cls)
    adapter._writer = writer
    adapter.enabled = False
    adapter._request_fn = lambda url, params=None: fixture
    return adapter


class TestArxivMathAdapter(unittest.TestCase):
    def setUp(self):
        from theory_x.stage1_sense.feeds.arxiv_math import ArxivMath
        self.cls = ArxivMath

    def test_poll_returns_events(self):
        adapter = _make_adapter(self.cls)
        events = adapter.poll()
        self.assertGreater(len(events), 0)

    def test_event_payload_is_valid_json(self):
        adapter = _make_adapter(self.cls)
        events = adapter.poll()
        payload = json.loads(events[0].payload)
        self.assertIn("title", payload)
        self.assertTrue(payload["title"])

    def test_stream_name(self):
        self.assertEqual(self.cls.stream, "mathematics.arxiv")

    def test_poll_interval_gte_600(self):
        self.assertGreaterEqual(self.cls.poll_interval_seconds, 600)

    def test_id_is_unique_string(self):
        self.assertIsInstance(self.cls.id, str)
        self.assertTrue(self.cls.id)


class TestAeonAdapter(unittest.TestCase):
    def setUp(self):
        from theory_x.stage1_sense.feeds.aeon import AeonEssays
        self.cls = AeonEssays

    def test_poll_returns_events(self):
        adapter = _make_adapter(self.cls)
        events = adapter.poll()
        self.assertGreater(len(events), 0)

    def test_event_payload_is_valid_json(self):
        adapter = _make_adapter(self.cls)
        events = adapter.poll()
        payload = json.loads(events[0].payload)
        self.assertIn("title", payload)

    def test_stream_name(self):
        self.assertEqual(self.cls.stream, "philosophy.aeon")

    def test_poll_interval_gte_600(self):
        self.assertGreaterEqual(self.cls.poll_interval_seconds, 600)

    def test_provenance_is_url(self):
        self.assertTrue(self.cls.provenance.startswith("http"))


class TestQuantaAdapter(unittest.TestCase):
    def setUp(self):
        from theory_x.stage1_sense.feeds.quanta import QuantaMagazine
        self.cls = QuantaMagazine

    def test_poll_returns_events(self):
        adapter = _make_adapter(self.cls)
        events = adapter.poll()
        self.assertGreater(len(events), 0)

    def test_stream_name(self):
        self.assertEqual(self.cls.stream, "science.quanta")

    def test_poll_interval_gte_600(self):
        self.assertGreaterEqual(self.cls.poll_interval_seconds, 600)

    def test_id_uniqueness(self):
        self.assertEqual(self.cls.id, "quanta")


class TestLessWrongAdapter(unittest.TestCase):
    def setUp(self):
        from theory_x.stage1_sense.feeds.lesswrong import LessWrong
        self.cls = LessWrong

    def test_poll_returns_events(self):
        adapter = _make_adapter(self.cls)
        events = adapter.poll()
        self.assertGreater(len(events), 0)

    def test_stream_name(self):
        self.assertEqual(self.cls.stream, "cognition.lesswrong")

    def test_poll_interval_gte_600(self):
        self.assertGreaterEqual(self.cls.poll_interval_seconds, 600)

    def test_provenance_is_url(self):
        self.assertTrue(self.cls.provenance.startswith("http"))


class TestWikipediaFeaturedAdapter(unittest.TestCase):
    def setUp(self):
        from theory_x.stage1_sense.feeds.wikipedia_featured import WikipediaFeatured
        self.cls = WikipediaFeatured

    def test_poll_returns_events(self):
        adapter = _make_adapter(self.cls, fixture=_ATOM_FIXTURE)
        events = adapter.poll()
        self.assertGreater(len(events), 0)

    def test_event_payload_is_valid_json(self):
        adapter = _make_adapter(self.cls, fixture=_ATOM_FIXTURE)
        events = adapter.poll()
        payload = json.loads(events[0].payload)
        self.assertIn("title", payload)

    def test_stream_name(self):
        self.assertEqual(self.cls.stream, "history.wikipedia_featured")

    def test_poll_interval_gte_600(self):
        self.assertGreaterEqual(self.cls.poll_interval_seconds, 600)


class TestGutenbergAdapter(unittest.TestCase):
    def setUp(self):
        from theory_x.stage1_sense.feeds.gutenberg import Gutenberg
        self.cls = Gutenberg

    def test_poll_returns_events(self):
        adapter = _make_adapter(self.cls)
        events = adapter.poll()
        self.assertGreater(len(events), 0)

    def test_stream_name(self):
        self.assertEqual(self.cls.stream, "literature.gutenberg")

    def test_poll_interval_gte_600(self):
        self.assertGreaterEqual(self.cls.poll_interval_seconds, 600)

    def test_id_uniqueness(self):
        self.assertEqual(self.cls.id, "gutenberg")


class TestArxivCsAIAdapter(unittest.TestCase):
    def setUp(self):
        from theory_x.stage1_sense.feeds.arxiv_cs_ai import ArxivCsAI
        self.cls = ArxivCsAI

    def test_poll_returns_events(self):
        adapter = _make_adapter(self.cls)
        events = adapter.poll()
        self.assertGreater(len(events), 0)

    def test_event_payload_is_valid_json(self):
        adapter = _make_adapter(self.cls)
        events = adapter.poll()
        payload = json.loads(events[0].payload)
        self.assertIn("title", payload)

    def test_stream_name(self):
        self.assertEqual(self.cls.stream, "agi.arxiv_cs_ai")

    def test_poll_interval_gte_600(self):
        self.assertGreaterEqual(self.cls.poll_interval_seconds, 600)

    def test_id_uniqueness(self):
        self.assertEqual(self.cls.id, "arxiv_cs_ai")


class TestArxivQbioNCAdapter(unittest.TestCase):
    def setUp(self):
        from theory_x.stage1_sense.feeds.arxiv_qbio_nc import ArxivQbioNC
        self.cls = ArxivQbioNC

    def test_poll_returns_events(self):
        adapter = _make_adapter(self.cls)
        events = adapter.poll()
        self.assertGreater(len(events), 0)

    def test_event_payload_is_valid_json(self):
        adapter = _make_adapter(self.cls)
        events = adapter.poll()
        payload = json.loads(events[0].payload)
        self.assertIn("title", payload)

    def test_stream_name(self):
        self.assertEqual(self.cls.stream, "neuroscience.arxiv_qbio")

    def test_poll_interval_gte_600(self):
        self.assertGreaterEqual(self.cls.poll_interval_seconds, 600)

    def test_id_uniqueness(self):
        self.assertEqual(self.cls.id, "arxiv_qbio_nc")


class TestAllAdapterIdsUnique(unittest.TestCase):
    def test_ids_are_unique(self):
        from theory_x.stage1_sense.feeds.arxiv_math import ArxivMath
        from theory_x.stage1_sense.feeds.aeon import AeonEssays
        from theory_x.stage1_sense.feeds.quanta import QuantaMagazine
        from theory_x.stage1_sense.feeds.lesswrong import LessWrong
        from theory_x.stage1_sense.feeds.wikipedia_featured import WikipediaFeatured
        from theory_x.stage1_sense.feeds.gutenberg import Gutenberg
        from theory_x.stage1_sense.feeds.arxiv_cs_ai import ArxivCsAI
        from theory_x.stage1_sense.feeds.arxiv_qbio_nc import ArxivQbioNC
        new_ids = [
            ArxivMath.id, AeonEssays.id, QuantaMagazine.id,
            LessWrong.id, WikipediaFeatured.id, Gutenberg.id,
            ArxivCsAI.id, ArxivQbioNC.id,
        ]
        self.assertEqual(len(new_ids), len(set(new_ids)), "Adapter IDs must be unique")

    def test_adapter_count_in_scheduler(self):
        """build_scheduler should produce 31 adapters."""
        import os, shutil, tempfile
        from pathlib import Path
        tmp = tempfile.mkdtemp(prefix="nex5_sched_")
        try:
            os.environ["NEX5_DATA_DIR"] = tmp
            os.environ["NEX5_ADMIN_HASH_FILE"] = str(Path(tmp) / "admin.argon2")
            from substrate.init_db import init_all
            init_all()
            from substrate import Reader, Writer, db_paths
            paths = db_paths()
            writers = {n: Writer(p, name=n) for n, p in paths.items()}
            readers = {n: Reader(p) for n, p in paths.items()}
            from theory_x.stage1_sense import build_scheduler
            sched = build_scheduler(writers, readers)
            self.assertEqual(len(sched._threads), 31)
        finally:
            for w in writers.values():
                try: w.close()
                except Exception: pass
            shutil.rmtree(tmp, ignore_errors=True)
            os.environ.pop("NEX5_DATA_DIR", None)
            os.environ.pop("NEX5_ADMIN_HASH_FILE", None)


if __name__ == "__main__":
    unittest.main()
