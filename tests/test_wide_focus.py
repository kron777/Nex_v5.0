"""NEX5_WIDE_FOCUS — EXPLAIN/ARGUE fires carry the inner-faculty lines.

Repair queue 2026-10-05 item 2. The wide templates replaced focus_block
wholesale, so the faculty lines (workspace, mood, metacog, amoha, self,
stakes) reached DRIFT fires only. With the flag on they follow the wide task
text; the mode's own drift focus, the (parked) drive line and the workspace line never do.
"""
from __future__ import annotations

import os
import unittest
from unittest import mock

from tests import _bootstrap  # noqa: F401
from tests.test_fountain import (_cleanup, _make_env, _mock_dynamic_state,
                                 _mock_voice_client)

_ITEM = "A new battery chemistry doubles storage density"


class _Drive:
    def format_for_prompt(self):
        return "Drawn lately to: pope artistry flattering persuade conscious"


class TestWideFocus(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self._env = {k: os.environ.get(k) for k in ("NEX5_WIDE_FOCUS", "NEX5_MOOD")}
        os.environ["NEX5_MOOD"] = "1"

    def tearDown(self):
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        _cleanup(self.writers, self.tmp)

    def _prompt(self, wide: bool) -> str:
        from theory_x.stage6_fountain import generator as g
        gen = g.FountainGenerator(
            sense_writer=self.writers["sense"],
            dynamic_writer=self.writers["dynamic"],
            voice_client=_mock_voice_client(),
            dynamic_reader=self.readers["dynamic"],
        )
        gen._drive_emergence = _Drive()
        import dataclasses
        from theory_x.modes.modes import get_mode as _real_get_mode
        mode = dataclasses.replace(_real_get_mode("normal"),
                                   drift_prompt_focus="MODE-DRIFT-FOCUS contemplative register")
        status = _mock_dynamic_state("systems").status()
        with mock.patch.object(g, "_WIDE_MODES_ON", wide), \
             mock.patch.object(g, "_select_wide_mode",
                               return_value=(g._MODE_EXPLAIN, {"item": _ITEM})), \
             mock.patch("theory_x.modes.modes.get_mode", return_value=mode), \
             mock.patch("theory_x.stage_tom.global_workspace.arbitrate",
                        return_value="[WORKSPACE] test winner line"), \
             mock.patch("theory_x.stage_affect.compositional_emotion.format_for_prompt",
                        return_value="My internal signals currently compose to 'calm' (test)."), \
             mock.patch("theory_x.stage_tom.recursive_self.format_for_prompt",
                        return_value="SELF: test self line"):
            prompt, _manifest = gen._build_prompt(status, 5, {"5": 5})
            return prompt

    def test_flag_off_wide_prompt_has_no_faculty_lines(self):
        os.environ.pop("NEX5_WIDE_FOCUS", None)
        p = self._prompt(wide=True)
        self.assertIn(_ITEM, p)
        self.assertNotIn("[WORKSPACE] test winner line", p)
        self.assertNotIn("compose to 'calm'", p)

    def test_flag_on_wide_prompt_carries_faculty_lines(self):
        os.environ["NEX5_WIDE_FOCUS"] = "1"
        p = self._prompt(wide=True)
        self.assertIn(_ITEM, p)
        self.assertIn("compose to 'calm'", p)
        self.assertIn("SELF: test self line", p)
        # faculty lines follow the task text, not precede it
        self.assertLess(p.index(_ITEM), p.index("SELF: test self line"))

    def test_flag_on_excludes_mode_drift_focus_drive_and_workspace(self):
        os.environ["NEX5_WIDE_FOCUS"] = "1"
        p = self._prompt(wide=True)
        self.assertNotIn("MODE-DRIFT-FOCUS", p)
        self.assertNotIn("Drawn lately to:", p)
        # item 2b: the workspace (momentum "continue it") line stays DRIFT-only
        self.assertNotIn("[WORKSPACE] test winner line", p)

    def test_drift_prompt_unchanged_by_flag(self):
        os.environ.pop("NEX5_WIDE_FOCUS", None)
        off = self._prompt(wide=False)
        os.environ["NEX5_WIDE_FOCUS"] = "1"
        on = self._prompt(wide=False)
        for p in (off, on):
            self.assertIn("idle, drifting", p)
            self.assertIn("[WORKSPACE] test winner line", p)
            self.assertIn("MODE-DRIFT-FOCUS", p)


if __name__ == "__main__":
    unittest.main()
