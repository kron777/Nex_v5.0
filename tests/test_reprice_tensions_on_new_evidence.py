"""kaukṛtya dev round (2026-11-15) — re-pricing a held tension on new evidence.

A Phase D tension (`NEX5_HELD_TENSION`) previously only ever closed three ways:
its basis left the pool ('belief_left_pool'), it aged past _TENSION_STALE_DAYS
('stale_retention'), or a bridge was found (retry_bridge_for_tensions,
'bridge_found'). All three are time-driven or a fixed retry; none of them ever
looks at whether something NEW, written since the tension opened, actually
bears on it. reprice_tensions_on_new_evidence() is that fourth path:
kaukṛtya's own distinction is evidence-driven reconsideration, not expiry.

It does not compute a new verdict -- re-pricing here means un-freezing (handing
the tension back to ordinary reconciliation on its own next pass), not
re-deciding the content itself. "Relevant" reuses the exact token-overlap test
_find_synthesis_candidate already applies (>=2 shared tokens), against EITHER
side rather than both.

Like sweep_resolved_tensions and retry_bridge_for_tensions, this has no
explicit NEX5_HELD_TENSION check of its own -- with the flag off, no rows
ever get written to held_tensions in the first place, so there is nothing for
this to find regardless.

Not currently invoked by any live loop (see Harmonizer.decay()'s docstring),
same status as its two siblings. This file proves the method itself, not
reachability.
"""
from __future__ import annotations

import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path

from tests._bootstrap import *  # noqa: F401, F403

_FLAG = "NEX5_HELD_TENSION"


def _make_env():
    tmp = tempfile.mkdtemp(prefix="nex5_reprice_")
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


def _seed_belief(writers, content, tier=5, locked=0, paused=0, created_at=None):
    created_at = int(time.time()) if created_at is None else int(created_at)
    return writers["beliefs"].write(
        "INSERT INTO beliefs (content, tier, confidence, created_at, source, locked, paused) "
        "VALUES (?, ?, 0.65, ?, 'test', ?, ?)",
        (content, tier, created_at, locked, paused),
    )


def _clear_keystone_noise(writers):
    """init_all() seeds pre-existing tier<=5 unpaused keystone beliefs that would
    otherwise be picked up as spurious 'new evidence' candidates. Same isolation
    reason as test_retry_bridge_for_tensions.py."""
    writers["beliefs"].write("DELETE FROM beliefs WHERE tier <= 5")


def _seed_tension(writers, a_id, b_id, created_at=None):
    created_at = time.time() if created_at is None else created_at
    return writers["dynamic"].write(
        "INSERT INTO held_tensions (belief_id_a, belief_id_b, created_at) "
        "VALUES (?, ?, ?)",
        (min(a_id, b_id), max(a_id, b_id), created_at),
    )


def _make_harmonizer(writers, readers):
    from theory_x.stage3_world_model.promotion import BeliefPromoter
    from theory_x.stage3_world_model.harmonizer import Harmonizer
    p = BeliefPromoter(writers["beliefs"], readers["beliefs"])
    return Harmonizer(
        beliefs_writer=writers["beliefs"], beliefs_reader=readers["beliefs"],
        dynamic_writer=writers["dynamic"], dynamic_reader=readers["dynamic"],
        promoter=p,
    )


_A_CONTENT = "Markets trend upward over decades"
_B_CONTENT = "Markets do not trend upward over decades"


class TestNewEvidenceReprices(unittest.TestCase):
    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        os.environ[_FLAG] = "1"

    def tearDown(self):
        os.environ.pop(_FLAG, None)
        _cleanup(self.writers, self.tmp)

    def test_new_relevant_belief_reprices_tension(self):
        _clear_keystone_noise(self.writers)
        tension_created = time.time() - 3600  # opened an hour ago
        a_id = _seed_belief(self.writers, _A_CONTENT, created_at=tension_created - 100)
        b_id = _seed_belief(self.writers, _B_CONTENT, created_at=tension_created - 100)
        tension_id = _seed_tension(self.writers, a_id, b_id, created_at=tension_created)
        # written AFTER the tension opened, overlaps >=2 tokens with side A
        _seed_belief(self.writers, "Markets trend upward this decade specifically",
                     created_at=tension_created + 60)

        h = _make_harmonizer(self.writers, self.readers)
        repriced = h.reprice_tensions_on_new_evidence()
        self.assertEqual(repriced, 1)

        tension = self.readers["dynamic"].read_one(
            "SELECT resolved_at, resolved_reason FROM held_tensions WHERE id = ?",
            (tension_id,),
        )
        self.assertIsNotNone(tension["resolved_at"])
        self.assertEqual(tension["resolved_reason"], "new_evidence")

        # re-pricing un-freezes; it must NOT itself alter the original pair's content/tier.
        row_a = self.readers["beliefs"].read_one("SELECT tier, content FROM beliefs WHERE id = ?", (a_id,))
        row_b = self.readers["beliefs"].read_one("SELECT tier, content FROM beliefs WHERE id = ?", (b_id,))
        self.assertEqual(row_a["tier"], 5)
        self.assertEqual(row_b["tier"], 5)
        self.assertEqual(row_a["content"], _A_CONTENT)
        self.assertEqual(row_b["content"], _B_CONTENT)

    def test_no_new_evidence_leaves_tension_open(self):
        _clear_keystone_noise(self.writers)
        a_id = _seed_belief(self.writers, _A_CONTENT)
        b_id = _seed_belief(self.writers, _B_CONTENT)
        tension_id = _seed_tension(self.writers, a_id, b_id)
        # unrelated content, no token overlap with either side
        _seed_belief(self.writers, "Completely unrelated topic about kitchen tiles",
                     created_at=time.time() + 60)

        h = _make_harmonizer(self.writers, self.readers)
        repriced = h.reprice_tensions_on_new_evidence()
        self.assertEqual(repriced, 0)

        tension = self.readers["dynamic"].read_one(
            "SELECT resolved_at FROM held_tensions WHERE id = ?", (tension_id,))
        self.assertIsNone(tension["resolved_at"])

    def test_evidence_predating_tension_does_not_count(self):
        """A belief relevant to the tension but written BEFORE it opened is not
        'new' -- the harmonizer's own normal escalation path already had the
        chance to use it when the tension was first created."""
        _clear_keystone_noise(self.writers)
        tension_created = time.time()
        a_id = _seed_belief(self.writers, _A_CONTENT, created_at=tension_created - 200)
        b_id = _seed_belief(self.writers, _B_CONTENT, created_at=tension_created - 200)
        # relevant content, but predates the tension
        _seed_belief(self.writers, "Markets trend upward this decade specifically",
                     created_at=tension_created - 100)
        tension_id = _seed_tension(self.writers, a_id, b_id, created_at=tension_created)

        h = _make_harmonizer(self.writers, self.readers)
        repriced = h.reprice_tensions_on_new_evidence()
        self.assertEqual(repriced, 0)

        tension = self.readers["dynamic"].read_one(
            "SELECT resolved_at FROM held_tensions WHERE id = ?", (tension_id,))
        self.assertIsNone(tension["resolved_at"])

    def test_multiple_open_tensions_processed_independently(self):
        _clear_keystone_noise(self.writers)
        t0 = time.time()
        a1, b1 = _seed_belief(self.writers, _A_CONTENT, created_at=t0 - 100), \
            _seed_belief(self.writers, _B_CONTENT, created_at=t0 - 100)
        tension1 = _seed_tension(self.writers, a1, b1, created_at=t0)
        _seed_belief(self.writers, "Markets trend upward this decade specifically",
                     created_at=t0 + 60)  # new evidence for tension1 only

        a2 = _seed_belief(self.writers, "Completely unrelated topic alpha", created_at=t0 - 100)
        b2 = _seed_belief(self.writers, "Completely unrelated topic beta", created_at=t0 - 100)
        tension2 = _seed_tension(self.writers, a2, b2, created_at=t0)  # no new evidence

        h = _make_harmonizer(self.writers, self.readers)
        repriced = h.reprice_tensions_on_new_evidence()
        self.assertEqual(repriced, 1)

        t1_row = self.readers["dynamic"].read_one(
            "SELECT resolved_at FROM held_tensions WHERE id = ?", (tension1,))
        t2_row = self.readers["dynamic"].read_one(
            "SELECT resolved_at FROM held_tensions WHERE id = ?", (tension2,))
        self.assertIsNotNone(t1_row["resolved_at"])
        self.assertIsNone(t2_row["resolved_at"])

    def test_ineligible_side_is_skipped_not_force_resolved(self):
        """If one side was already promoted/locked since the tension opened,
        this is sweep_resolved_tensions' job -- must not force a verdict here."""
        _clear_keystone_noise(self.writers)
        t0 = time.time()
        a_id = _seed_belief(self.writers, _A_CONTENT, created_at=t0 - 100, locked=1)
        b_id = _seed_belief(self.writers, _B_CONTENT, created_at=t0 - 100)
        tension_id = _seed_tension(self.writers, a_id, b_id, created_at=t0)
        _seed_belief(self.writers, "Markets trend upward this decade specifically",
                     created_at=t0 + 60)

        h = _make_harmonizer(self.writers, self.readers)
        repriced = h.reprice_tensions_on_new_evidence()
        self.assertEqual(repriced, 0)

        tension = self.readers["dynamic"].read_one(
            "SELECT resolved_at FROM held_tensions WHERE id = ?", (tension_id,))
        self.assertIsNone(tension["resolved_at"])

    def test_flag_off_is_harmless_noop_with_no_tensions_to_find(self):
        """With NEX5_HELD_TENSION off, held_tensions is simply empty -- the
        method itself has no gate, same convention as its two siblings."""
        os.environ.pop(_FLAG, None)
        h = _make_harmonizer(self.writers, self.readers)
        self.assertEqual(h.reprice_tensions_on_new_evidence(), 0)


if __name__ == "__main__":
    unittest.main()
