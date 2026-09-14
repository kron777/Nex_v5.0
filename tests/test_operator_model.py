"""Tests for the operator model (NEX5_OPERATOR_MODEL) — NEX's held read of Jon.

Enforces the two hard guards from NEX_Operator_Intake.md:
  GUARD 1 — informs stance, not cognition: the block is additive stance/tone
    context with NO directive that gates/filters/forbids what she may think.
  GUARD 2 — hers to know, not to broadcast: operator content has NO code route
    to any published output (fountain_insight thoughts, external.other_mind).
    Verified structurally — the module is imported ONLY by the Jon-facing chat
    path, never by the fountain generator or the persona responder.
"""
from __future__ import annotations

import os
import tempfile
import unittest

from tests import _bootstrap  # noqa: F401

from theory_x.stage_tom import operator_model as om

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_SAMPLE = """# NEX · OPERATOR MODEL — INTAKE

## 1 · Who you are
- Who is Jon?
  › Call me Jon. I am the architect, she is my beloved creation.

## 4 · What you value
- What matters most:
  › Honesty, integrity, accuracy — and inspiration.

## 5 · How you want her to be with you
- Tone:
  › Casual, easy.

## 8 · Boundaries
- What she should never model or raise:
  › Keep my characteristics semi-secret — hers to know but not to broadcast.

## 9 · The humility dial
  › Confident. State it with certainty.
"""


def _write(text):
    fd, path = tempfile.mkstemp(suffix=".md")
    with os.fdopen(fd, "w") as f:
        f.write(text)
    return path


class TestOperatorModel(unittest.TestCase):

    def setUp(self):
        self.doc = _write(_SAMPLE)

    def tearDown(self):
        try:
            os.remove(self.doc)
        except Exception:
            pass

    # ---- parsing: only Jon's own answer lines ----
    def test_parses_answer_lines(self):
        r = om.load_operator_read(self.doc)
        self.assertIn("1 · Who you are", r)
        self.assertIn("Call me Jon. I am the architect, she is my beloved creation.",
                      r["1 · Who you are"])

    def test_meeting_block_built(self):
        b = om.format_for_meeting(self.doc)
        self.assertIn("Call me Jon", b)
        self.assertIn("Casual, easy", b)          # tone shapes how she meets him
        self.assertIn("Honesty, integrity", b)    # values

    # ---- GUARD 1: stance, not a cognition filter ----
    def test_guard1_block_says_it_does_not_limit_thought(self):
        b = om.format_for_meeting(self.doc).lower()
        self.assertIn("does not limit what you may think", b)

    def test_guard1_no_thought_gating_directives(self):
        b = om.format_for_meeting(self.doc).lower()
        for banned in ("do not think about", "you may not think", "forbidden to think",
                       "may not consider", "must not think", "cannot think about"):
            self.assertNotIn(banned, b)

    # ---- GUARD 2: hers to know, not to broadcast ----
    def test_guard2_block_carries_not_to_broadcast_instruction(self):
        b = om.format_for_meeting(self.doc).lower()
        self.assertIn("not to broadcast", b)
        self.assertIn("do not recite", b)

    def test_guard2_not_imported_by_published_paths(self):
        # The fountain generator publishes fountain_insight; the persona responder
        # writes external.other_mind. Operator content must have NO route there.
        for rel in ("theory_x/stage6_fountain/generator.py",
                    "theory_x/stage_tom/persona_responder.py"):
            with open(os.path.join(_REPO, rel), encoding="utf-8") as f:
                src = f.read()
            self.assertNotIn("operator_model", src,
                             f"{rel} must not reference operator_model (guard 2)")

    def test_guard2_used_only_by_chat_path(self):
        # It SHOULD be wired into the Jon-facing chat path (positive control).
        with open(os.path.join(_REPO, "gui/server.py"), encoding="utf-8") as f:
            self.assertIn("operator_model", f.read())

    def test_guard2_reads_from_disk_not_committed(self):
        # Content is read from a path (env-overridable), not hardcoded; and the
        # real doc is NOT committed inside the repo tree.
        self.assertEqual(om.load_operator_read("/nonexistent/x.md"), {})
        os.environ["NEX5_OPERATOR_DOC"] = self.doc
        try:
            self.assertTrue(om.load_operator_read())  # honours the env path
        finally:
            os.environ.pop("NEX5_OPERATOR_DOC", None)
        self.assertFalse(os.path.exists(os.path.join(_REPO, "NEX_Operator_Intake.md")),
                         "the intake doc must not be committed into the repo")

    # ---- fail-safe ----
    def test_missing_doc_empty(self):
        self.assertEqual(om.format_for_meeting("/nope.md"), "")

    def test_headers_but_no_answers_empty(self):
        p = _write("# T\n\n## 1 · Who you are\n- q?\n")   # no '›' answers
        try:
            self.assertEqual(om.format_for_meeting(p), "")
        finally:
            os.remove(p)


if __name__ == "__main__":
    unittest.main()
