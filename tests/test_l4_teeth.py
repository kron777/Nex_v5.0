"""L4_teeth (NEX5_L4_TEETH): MECHANICAL selection shift in the fire arbiter.

Default OFF -> arbitrate() byte-identical. ON -> the momentum (groove-continuer)
candidate is demoted by a bounded factor so a novel candidate can LEAD. This tests
the lever readiness is not: readiness is saturated at fire (r80 §1c), so it changes
how OFTEN she fires, not WHAT; selection changes what fires. ANALOGUE.
"""
from __future__ import annotations

import os
import shutil
import sqlite3
import tempfile
import time
import unittest

from tests._bootstrap import *  # noqa: F401, F403


class TestL4Teeth(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="nex5_teeth_")
        self.db = os.path.join(self.tmp, "dynamic.db")
        con = sqlite3.connect(self.db)
        con.execute(
            "CREATE TABLE momentum (id INTEGER PRIMARY KEY CHECK (id = 1), "
            "updated_at REAL NOT NULL, branch TEXT, thought_fragment TEXT)")
        con.execute(
            "INSERT INTO momentum (id, updated_at, branch, thought_fragment) "
            "VALUES (1, ?, 'b', 'the live thread topic that keeps pulling')",
            (time.time(),))
        con.commit()
        con.close()
        # bonsai candidate = focus_num(0.9) * _W_BONSAI(0.5) = 0.45, which sits
        # between demoted momentum (0.55*0.6=0.33) and full momentum (0.55).
        self.status = {"branches": [{"branch_id": "b1", "focus_num": 0.9}],
                       "consolidation_active": False}

    def tearDown(self):
        os.environ.pop("NEX5_L4_TEETH", None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_factor_off_is_noop_on_is_bounded(self):
        from theory_x.stage_tom.global_workspace import (
            _teeth_momentum_factor, _W_MOMENTUM_TEETH_FACTOR)
        os.environ.pop("NEX5_L4_TEETH", None)
        self.assertEqual(_teeth_momentum_factor(), 1.0)             # OFF = no-op
        os.environ["NEX5_L4_TEETH"] = "1"
        f = _teeth_momentum_factor()
        self.assertEqual(f, _W_MOMENTUM_TEETH_FACTOR)
        self.assertGreater(f, 0.0)
        self.assertLessEqual(f, 1.0)                                # demotes, never amplifies

    def test_off_momentum_leads(self):
        from theory_x.stage_tom.global_workspace import arbitrate
        os.environ.pop("NEX5_L4_TEETH", None)
        w = arbitrate(self.status, dynamic_db=self.db)
        self.assertIn("mid-thought", w)        # momentum 0.55 > bonsai 0.45 -> momentum leads

    def test_on_teeth_flips_the_leader_to_novel(self):
        from theory_x.stage_tom.global_workspace import arbitrate
        os.environ["NEX5_L4_TEETH"] = "1"
        w = arbitrate(self.status, dynamic_db=self.db)
        self.assertIn("attention is settled", w)   # momentum demoted 0.33 < bonsai 0.45
        self.assertNotIn("mid-thought", w)         # the LEADING candidate changed

    def test_teeth_does_not_touch_a_louder_candidate(self):
        # bonsai loud enough to beat full momentum: focus 1.0 -> 0.5 > 0.55? no.
        # Use a branch that already outranks momentum; teeth must not change the winner.
        from theory_x.stage_tom.global_workspace import arbitrate
        hot = {"branches": [{"branch_id": "b1", "focus_num": 1.2}],  # 1.2*0.5=0.60 > 0.55
               "consolidation_active": False}
        os.environ.pop("NEX5_L4_TEETH", None)
        off = arbitrate(hot, dynamic_db=self.db)
        os.environ["NEX5_L4_TEETH"] = "1"
        on = arbitrate(hot, dynamic_db=self.db)
        self.assertIn("attention is settled", off)  # bonsai already led
        self.assertEqual(off, on)                    # teeth changed nothing here


if __name__ == "__main__":
    unittest.main()
