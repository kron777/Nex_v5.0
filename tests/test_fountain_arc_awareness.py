"""Test that arc context reaches the fountain prompt."""
from __future__ import annotations

import time
import unittest
from unittest.mock import MagicMock


class TestFountainArcAwareness(unittest.TestCase):

    def test_no_arcs_produces_empty_block(self):
        """When arcs table is empty, arc context is empty string."""
        from theory_x.stage6_fountain.generator import FountainGenerator
        reader = MagicMock()
        reader.read.return_value = []
        fg = FountainGenerator.__new__(FountainGenerator)
        fg._beliefs_reader = reader
        ctx = fg._fetch_arc_context()
        self.assertEqual(ctx["active"], [])
        self.assertEqual(ctx["recent_closed"], [])
        self.assertEqual(fg._format_arc_context(ctx), "")

    def test_active_arc_renders_in_context(self):
        """Active arc appears in rendered arc context."""
        from theory_x.stage6_fountain.generator import FountainGenerator
        reader = MagicMock()
        now = time.time()
        reader.read.side_effect = [
            [{
                "id": 1,
                "arc_type": "progression",
                "theme_summary": "The hum of the computer fades",
                "member_count": 6,
                "quality_grade": 0.54,
                "last_active_at": now - 180,
            }],
            [],
        ]
        fg = FountainGenerator.__new__(FountainGenerator)
        fg._beliefs_reader = reader
        ctx = fg._fetch_arc_context()
        rendered = fg._format_arc_context(ctx)
        self.assertIn("hum of the computer fades", rendered)
        self.assertIn("6 fires", rendered)
        self.assertIn("progression", rendered)

    def test_recent_closed_renders_in_context(self):
        """Recently-closed arc appears in the recent section."""
        from theory_x.stage6_fountain.generator import FountainGenerator
        reader = MagicMock()
        now = time.time()
        reader.read.side_effect = [
            [],
            [{
                "id": 2,
                "arc_type": "return_transformation",
                "theme_summary": "Why don't I grab lunch",
                "member_count": 4,
                "quality_grade": 0.49,
                "last_active_at": now - 3600,
                "closed_by_belief_id": 100,
            }],
        ]
        fg = FountainGenerator.__new__(FountainGenerator)
        fg._beliefs_reader = reader
        ctx = fg._fetch_arc_context()
        rendered = fg._format_arc_context(ctx)
        self.assertIn("Recently completed", rendered)
        self.assertIn("Why don't I grab lunch", rendered)
        self.assertIn("closed", rendered)

    def test_arc_context_failure_is_silent(self):
        """If arc fetch raises, return empty context without breaking."""
        from theory_x.stage6_fountain.generator import FountainGenerator
        reader = MagicMock()
        reader.read.side_effect = RuntimeError("db unavailable")
        fg = FountainGenerator.__new__(FountainGenerator)
        fg._beliefs_reader = reader
        ctx = fg._fetch_arc_context()
        self.assertEqual(ctx["active"], [])
        self.assertEqual(ctx["recent_closed"], [])

    def test_none_reader_returns_empty_context(self):
        """_fetch_arc_context returns empty when beliefs_reader is None."""
        from theory_x.stage6_fountain.generator import FountainGenerator
        fg = FountainGenerator.__new__(FountainGenerator)
        fg._beliefs_reader = None
        ctx = fg._fetch_arc_context()
        self.assertEqual(ctx["active"], [])
        self.assertEqual(ctx["recent_closed"], [])

    def test_format_arc_context_no_trailing_whitespace(self):
        """Rendered arc context has no trailing whitespace or blank lines."""
        from theory_x.stage6_fountain.generator import FountainGenerator
        fg = FountainGenerator.__new__(FountainGenerator)
        fg._beliefs_reader = None
        now = time.time()
        ctx = {
            "active": [{
                "id": 1,
                "arc_type": "progression",
                "theme_summary": "A test theme",
                "member_count": 3,
                "last_active_at": now - 60,
            }],
            "recent_closed": [],
        }
        rendered = fg._format_arc_context(ctx)
        self.assertFalse(rendered.endswith("\n"))
        self.assertFalse(rendered.endswith(" "))


if __name__ == "__main__":
    unittest.main()
