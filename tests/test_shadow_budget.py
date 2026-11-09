"""Shadow budget module (theory_x/stage_finitude/budget_shadow.py), p13_finitude.

SHADOW MODULE — these tests exercise a stand-in, not the live chat path.
A test name without "shadow" would claim more than was measured; every test
here says so in its name on purpose.

Covers: spend() persists one immutable ledger row per draw and decrements
`remaining` atomically with it; overdraw raises (never clamps); `remaining`
is read by selection (delegated to the real, pure select_within_budget) and
actually changes what gets picked — the evidence this is a Price, not a
label; and `remaining` is never used by anything here as a veto.

Corpus for tests 4/5: a SYNTHETIC set of candidates modeled on the real
13 chat-block kinds and salience weights in gui/server.py's
_CHAT_BLOCK_SALIENCE (read directly, 2026-11-09), with plausible per-kind
text lengths chosen to resemble real block sizes. This is not live chat
traffic — the shadow has never run against live data by design (nothing
imports it) — so the BINDING fraction below is a statement about this
synthetic corpus only. Whether real chat turns bind against the real
NEX5_CHAT_WORKSPACE_BUDGET ceiling is a separate, open question this shadow
does not answer.
"""
from __future__ import annotations

import os
import random
import shutil
import tempfile
import unittest

from tests import _bootstrap  # noqa: F401

# Real salience table, gui/server.py:188-196 (copied as data, not imported --
# this test must not depend on gui/server.py).
_REAL_CHAT_BLOCK_SALIENCE = {
    "convo": 0.90, "compassion": 0.90, "compass": 0.85, "operator": 0.75,
    "operator_anchor": 0.70, "affect_carry": 0.55, "spectrum": 0.50, "tag": 0.50,
    "equanimity": 0.45, "apramada": 0.45, "virya": 0.40, "sraddha": 0.40,
    "prasrabdhi": 0.40,
}
_REAL_CHAT_BLOCK_EXEMPT = {"compassion", "compass"}


def _make_env():
    tmp = tempfile.mkdtemp(prefix="nex5_shadow_budget_")
    os.environ["NEX5_DATA_DIR"] = tmp
    os.environ["NEX5_ADMIN_HASH_FILE"] = os.path.join(tmp, "admin.argon2")
    from substrate.init_db import init_all
    init_all()
    from substrate import Writer, db_paths
    paths = db_paths()
    writer = Writer(paths["dynamic"], name="dynamic")
    return writer, tmp


def _cleanup(writer, tmp):
    try:
        writer.close()
    except Exception:
        pass
    shutil.rmtree(tmp, ignore_errors=True)
    os.environ.pop("NEX5_DATA_DIR", None)
    os.environ.pop("NEX5_ADMIN_HASH_FILE", None)


def _fixed_moment_candidates() -> "list[tuple[float, str, bool]]":
    """Deterministic, all-13-kinds-present moment for the reordering test —
    no jitter, so the full-vs-half comparison is not at the mercy of a draw
    that happens to tie. Same shape rule as the probabilistic generator
    below (exempt kinds at 220 chars, others scaled by salience)."""
    out = []
    for kind, sal in _REAL_CHAT_BLOCK_SALIENCE.items():
        exempt = kind in _REAL_CHAT_BLOCK_EXEMPT
        length = 220 if exempt else int(60 + 340 * sal)
        out.append((sal, "x" * length, exempt))
    return out


def _synthetic_moment_candidates(rng: random.Random) -> "list[tuple[float, str, bool]]":
    """One synthetic moment. Exempt kinds (compassion, compass) are always
    present, matching gui/server.py's own "never evicted" comment. Each
    non-exempt kind fires with probability 0.6 (not every faculty has
    something to say every turn) and, when present, gets a plausible
    jittered length (higher-salience kinds run longer, as a rough proxy for
    "more to say"). This is still synthetic, not sampled live traffic.
    """
    out = []
    for kind, sal in _REAL_CHAT_BLOCK_SALIENCE.items():
        exempt = kind in _REAL_CHAT_BLOCK_EXEMPT
        if not exempt and rng.random() > 0.6:
            continue
        base = 220 if exempt else int(60 + 340 * sal)
        length = max(10, base + rng.randint(-40, 40))
        out.append((sal, "x" * length, exempt))
    return out


class ShadowBudgetSpendTests(unittest.TestCase):
    def setUp(self):
        self.writer, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writer, self.tmp)

    def test_shadow_spend_decrements_and_persists_entry(self):
        from theory_x.stage_finitude.budget_shadow import Budget
        b = Budget(self.writer, moment_id="m1", capacity=100)
        receipt = b.spend(30)
        self.assertEqual(receipt.amount, 30)
        self.assertEqual(receipt.remaining_after, 70)
        self.assertEqual(b.remaining, 70)
        row = self.writer.read_row if hasattr(self.writer, "read_row") else None
        from substrate import Reader, db_paths
        reader = Reader(db_paths()["dynamic"])
        rows = reader.read("SELECT moment_id, amount, remaining_after FROM "
                            "shadow_budget_spend WHERE id = ?", (receipt.entry_id,))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["moment_id"], "m1")
        self.assertEqual(rows[0]["amount"], 30)
        self.assertEqual(rows[0]["remaining_after"], 70)

    def test_shadow_overdraw_raises(self):
        from theory_x.stage_finitude.budget_shadow import Budget, InsufficientBudget
        b = Budget(self.writer, moment_id="m2", capacity=50)
        b.spend(40)
        with self.assertRaises(InsufficientBudget):
            b.spend(20)  # only 10 remaining
        # overdraw must not have been silently clamped to 10
        self.assertEqual(b.remaining, 10)

    def test_shadow_atomicity(self):
        """A write with no spend, or a spend with no write, must be
        impossible. Force the write to fail and assert `remaining` did not
        move; a real (non-forced) spend must advance both together."""
        from theory_x.stage_finitude.budget_shadow import Budget
        b = Budget(self.writer, moment_id="m3", capacity=100)

        real_write = self.writer.write
        def _boom(*a, **kw):
            raise RuntimeError("forced write failure")
        self.writer.write = _boom
        try:
            with self.assertRaises(RuntimeError):
                b.spend(10)
        finally:
            self.writer.write = real_write
        self.assertEqual(b.remaining, 100, "remaining moved despite the write raising")

        receipt = b.spend(10)
        self.assertEqual(b.remaining, 90)
        from substrate import Reader, db_paths
        reader = Reader(db_paths()["dynamic"])
        rows = reader.read("SELECT id FROM shadow_budget_spend WHERE id = ?",
                            (receipt.entry_id,))
        self.assertEqual(len(rows), 1, "spend advanced remaining with no row to show for it")

    def test_shadow_spend_is_not_a_gate(self):
        """Nothing in this module branches on `remaining` to veto a candidate;
        spend() only ever refuses money (InsufficientBudget), never a
        candidate or action. Assert directly against the module source."""
        import inspect
        from theory_x.stage_finitude import budget_shadow
        src = inspect.getsource(budget_shadow)
        # select() must not filter/drop candidates itself -- it must hand the
        # whole list to the real selector and return exactly what it returns.
        select_src = inspect.getsource(budget_shadow.Budget.select)
        self.assertNotIn(" if ", select_src,
                          "select() branches internally instead of delegating whole")
        self.assertIn("return select_within_budget(candidates, self.remaining)", select_src)
        # no boolean "can afford" / "is_allowed" helper exists for a caller to veto on
        self.assertNotIn("def can_afford", src)
        self.assertNotIn("def is_allowed", src)


class ShadowBudgetSelectionTests(unittest.TestCase):
    def setUp(self):
        self.writer, self.tmp = _make_env()
        self.rng = random.Random(20261109)

    def tearDown(self):
        _cleanup(self.writer, self.tmp)

    def test_shadow_budget_reorders_real_selection(self):
        """Claim this test establishes: varying `remaining` (full vs half
        capacity) changes what the REAL select_within_budget picks, for a
        fixed synthetic candidate set. Claim it does NOT establish: that the
        live gui/server.py caller actually passes it a `remaining` debited by
        real spend()s -- that stays an open claim until the post-r77 swap.
        """
        from theory_x.stage_finitude.budget_shadow import Budget
        candidates = _fixed_moment_candidates()
        full = Budget(self.writer, moment_id="sel-full", capacity=700)
        half = Budget(self.writer, moment_id="sel-half", capacity=350)
        kept_full = full.select(candidates)
        kept_half = half.select(candidates)
        self.assertNotEqual(
            set(kept_full), set(kept_half),
            "halving capacity left selection identical -- the budget is decorative")
        delta_chars = sum(len(t) for t in kept_full) - sum(len(t) for t in kept_half)
        self.assertGreater(delta_chars, 0)
        print(f"TEST 4 DELTA: full-capacity selection kept {len(kept_full)} blocks / "
              f"{sum(len(t) for t in kept_full)} chars; half-capacity kept "
              f"{len(kept_half)} blocks / {sum(len(t) for t in kept_half)} chars "
              f"-- delta {delta_chars} chars, {len(kept_full) - len(kept_half)} blocks dropped")

    def test_shadow_budget_binds(self):
        """Corpus: 200 synthetic moments (see module docstring), each built
        from the real 13 chat-block kinds/saliences with jittered per-kind
        lengths. 'Binds' = at least one non-exempt candidate is dropped at
        the default shadow capacity (700, half of the real
        NEX5_CHAT_WORKSPACE_BUDGET default of 1400)."""
        from theory_x.stage_finitude.budget_shadow import Budget, _DEFAULT_CAPACITY
        corpus_size = 200
        bound = 0
        for i in range(corpus_size):
            candidates = _synthetic_moment_candidates(self.rng)
            total_chars = sum(len(t) for _, t, _ in candidates)
            b = Budget(self.writer, moment_id=f"bind-{i}", capacity=_DEFAULT_CAPACITY)
            kept = b.select(candidates)
            if sum(len(t) for t in kept) < total_chars:
                bound += 1
        fraction = bound / corpus_size
        print(f"BINDING: {bound}/{corpus_size} synthetic moments ({fraction:.2%}) "
              f"hit the default shadow capacity ({_DEFAULT_CAPACITY} chars); "
              f"corpus = 200 synthetic moments, 13 real kinds each, jittered lengths")
        self.assertGreater(bound, 0, "ceiling never binds on this corpus -- a constant, not a price")

    @unittest.skip("requires refuse() -- see budget_shadow.py Step 4 design note; "
                    "placeholder so this is not silently forgotten when the "
                    "ledger primitives unblock")
    def test_shadow_insufficient_budget_forces_commitment(self):
        pass


if __name__ == "__main__":
    unittest.main()
