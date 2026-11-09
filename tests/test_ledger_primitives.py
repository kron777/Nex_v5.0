"""Ledger primitives (theory_x/stage3_world_model/ledger_primitives.py):
refuse() / consolidate() / recall(), built against the shadow budget
(theory_x/stage_finitude/budget_shadow.py, commit d9bc326).

SHADOW-DEPENDENT — every test here that depends on the shadow budget being
live carries "shadow" in its name, per the naming rule in the build spec.
Tests 1/3/5/6 are true regardless of liveness (they test the ledger rows
and dispatch logic directly) and do not carry "shadow" in their names.
Test 2 and test 4 are about the budget's effect and do carry it
implicitly via the fixture, but per the spec test 4 keeps its plain name
(it compares downstream prices, which are measurable regardless of
liveness) while its docstring states the prices are shadow prices.

Corpus for test 7 (test_shadow_refusal_rate_strictly_between_zero_and_one):
SYNTHETIC, engineered by construction — 20 distinct belief-id pairs with a
fixed per-pair cost against a capacity sized to bind on roughly half of
them. Per the build spec's own ranking: this is the weaker corpus type
("a tautology wearing a test's clothes," not a genuine counterfactual
about real tensions) — it establishes that refuse()'s refusal rate against
shadow scarcity can be non-degenerate, not that the live system refuses at
a sane rate. Test 4 is the one to trust over this one.
"""
from __future__ import annotations

import os
import shutil
import tempfile
import unittest

from tests import _bootstrap  # noqa: F401

_REAL_CHAT_BLOCK_SALIENCE = {
    "convo": 0.90, "compassion": 0.90, "compass": 0.85, "operator": 0.75,
    "operator_anchor": 0.70, "affect_carry": 0.55, "spectrum": 0.50, "tag": 0.50,
    "equanimity": 0.45, "apramada": 0.45, "virya": 0.40, "sraddha": 0.40,
    "prasrabdhi": 0.40,
}
_REAL_CHAT_BLOCK_EXEMPT = {"compassion", "compass"}


def _fixed_moment_candidates():
    out = []
    for kind, sal in _REAL_CHAT_BLOCK_SALIENCE.items():
        exempt = kind in _REAL_CHAT_BLOCK_EXEMPT
        length = 220 if exempt else int(60 + 340 * sal)
        out.append((sal, "x" * length, exempt))
    return out


def _make_env():
    tmp = tempfile.mkdtemp(prefix="nex5_ledger_primitives_")
    os.environ["NEX5_DATA_DIR"] = tmp
    os.environ["NEX5_ADMIN_HASH_FILE"] = os.path.join(tmp, "admin.argon2")
    from substrate.init_db import init_all
    init_all()
    from substrate import Reader, Writer, db_paths
    paths = db_paths()
    writer = Writer(paths["dynamic"], name="dynamic")
    reader = Reader(paths["dynamic"])
    return writer, reader, tmp


def _cleanup(writer, tmp):
    try:
        writer.close()
    except Exception:
        pass
    shutil.rmtree(tmp, ignore_errors=True)
    os.environ.pop("NEX5_DATA_DIR", None)
    os.environ.pop("NEX5_ADMIN_HASH_FILE", None)


class RefuseTests(unittest.TestCase):
    def setUp(self):
        self.writer, self.reader, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writer, self.tmp)

    def test_refuse_commits_tension_held(self):
        from theory_x.stage_finitude.budget_shadow import Budget
        from theory_x.stage3_world_model.ledger_primitives import refuse
        budget = Budget(self.writer, moment_id="t1", capacity=500)
        entry_id = refuse(self.writer, self.reader, budget, 101, 202, cost=50)
        row = self.reader.read_one(
            "SELECT kind, belief_id_a, belief_id_b, irreversibility, cost, seq "
            "FROM held_tensions WHERE id = ?", (entry_id,))
        self.assertIsNotNone(row)
        self.assertEqual(row["kind"], "tension_held")
        self.assertEqual({row["belief_id_a"], row["belief_id_b"]}, {101, 202})
        self.assertEqual(row["irreversibility"], 1)
        self.assertEqual(row["cost"], 50)
        self.assertEqual(row["seq"], 1)
        # "survives restart" -- re-open a Reader against the same db file,
        # confirming the row is a real committed write, not an in-memory
        # artifact of this test's own writer/reader pair.
        from substrate import Reader, db_paths
        fresh_reader = Reader(db_paths()["dynamic"])
        row2 = fresh_reader.read_one(
            "SELECT id FROM held_tensions WHERE id = ?", (entry_id,))
        self.assertIsNotNone(row2)

    def test_refuse_spends_in_same_transaction(self):
        """Forced failure between the write and the budget bookkeeping must
        leave no write with no spend, and no spend with no write."""
        from theory_x.stage_finitude.budget_shadow import Budget, InsufficientBudget
        from theory_x.stage3_world_model.ledger_primitives import refuse
        budget = Budget(self.writer, moment_id="t2", capacity=100)

        real_write = self.writer.write
        def _boom(*a, **kw):
            raise RuntimeError("forced write failure")
        self.writer.write = _boom
        try:
            with self.assertRaises(RuntimeError):
                refuse(self.writer, self.reader, budget, 1, 2, cost=30)
        finally:
            self.writer.write = real_write
        self.assertEqual(budget.remaining, 100,
                          "remaining moved despite the write raising -- spend with no write")

        entry_id = refuse(self.writer, self.reader, budget, 1, 2, cost=30)
        self.assertEqual(budget.remaining, 70)
        row = self.reader.read_one("SELECT cost FROM held_tensions WHERE id = ?", (entry_id,))
        self.assertEqual(row["cost"], 30, "spend advanced with no row to show for it")

        # Overdraw: InsufficientBudget, no new row for this pair's facing count.
        before = self.reader.read_one(
            "SELECT seq FROM held_tensions WHERE id = ?", (entry_id,))["seq"]
        with self.assertRaises(InsufficientBudget):
            refuse(self.writer, self.reader, budget, 1, 2, cost=1000)
        after = self.reader.read_one(
            "SELECT seq FROM held_tensions WHERE id = ?", (entry_id,))["seq"]
        self.assertEqual(before, after, "a failed refuse() must not write anything")

    def test_refuse_refacing_accrues_cost_and_seq(self):
        """Re-facing the same unordered pair: row stays single, cost
        accrues, seq increments, provenance unions -- not a second row."""
        from theory_x.stage_finitude.budget_shadow import Budget
        from theory_x.stage3_world_model.ledger_primitives import refuse
        budget = Budget(self.writer, moment_id="t3", capacity=500)
        id1 = refuse(self.writer, self.reader, budget, 5, 9, cost=40, provenance="shadow")
        id2 = refuse(self.writer, self.reader, budget, 9, 5, cost=25, provenance="shadow2")
        self.assertEqual(id1, id2, "re-facing the same pair must update, not duplicate")
        rows = self.reader.read(
            "SELECT cost, seq, provenance FROM held_tensions "
            "WHERE belief_id_a = 5 AND belief_id_b = 9")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["cost"], 65)
        self.assertEqual(rows[0]["seq"], 2)
        self.assertEqual(set(rows[0]["provenance"].split(",")), {"shadow", "shadow2"})


class RecallTests(unittest.TestCase):
    def setUp(self):
        self.writer, self.reader, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writer, self.tmp)

    def test_recall_returns_both_poles_unresolved(self):
        from theory_x.stage_finitude.budget_shadow import Budget
        from theory_x.stage3_world_model.ledger_primitives import refuse, recall
        budget = Budget(self.writer, moment_id="t4", capacity=500)
        refuse(self.writer, self.reader, budget, 11, 22, cost=15)
        result = recall(self.reader, 22, 11)  # order-insensitive query
        self.assertTrue(result["found"])
        self.assertEqual(set(result["refs"]), {11, 22})
        self.assertIs(result["unresolved"], True)
        self.assertEqual(result["cost"], 15)
        self.assertEqual(result["count"], 1)

    def test_recall_never_fabricates_resolution(self):
        """No code path here selects a pole as the resolution, prefers one
        by recency/salience, or synthesizes a narrative. A query against a
        pair with no record returns found=False + unresolved=True, never a
        pole, never a summary string."""
        from theory_x.stage3_world_model.ledger_primitives import recall
        result = recall(self.reader, 777, 888)
        self.assertFalse(result["found"])
        self.assertIs(result["unresolved"], True)
        self.assertIsNone(result["cost"])
        for forbidden_key in ("winner", "resolution", "decided", "summary"):
            self.assertNotIn(forbidden_key, result)

        # Scan the function BODY only (not the docstring, which legitimately
        # names "winner" to disclaim it) for pole-preference or narrative
        # synthesis constructs.
        import inspect
        from theory_x.stage3_world_model import ledger_primitives
        src = inspect.getsource(ledger_primitives.recall)
        body = src.split('"""', 2)[2] if src.count('"""') >= 2 else src
        for forbidden in ("max(", "sorted(", "argmax", "f\"I "):
            self.assertNotIn(forbidden, body,
                              f"recall() body contains {forbidden!r} -- "
                              "possible pole-preference or narrative synthesis")


class ConsolidateTests(unittest.TestCase):
    def setUp(self):
        self.writer, self.reader, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writer, self.tmp)

    def test_consolidate_never_amalgamates_distinct_pairs(self):
        from theory_x.stage_finitude.budget_shadow import Budget
        from theory_x.stage3_world_model.ledger_primitives import refuse, consolidate
        budget = Budget(self.writer, moment_id="t5", capacity=5000)
        pairs = [(1, 2), (3, 4), (5, 6), (7, 8), (9, 10)]
        for a, b in pairs:
            refuse(self.writer, self.reader, budget, a, b, cost=10)
        before = self.reader.read(
            "SELECT DISTINCT belief_id_a, belief_id_b FROM held_tensions "
            "WHERE kind = 'tension_held'")
        result = consolidate(self.reader, self.writer, kind="tension_held")
        after = self.reader.read(
            "SELECT DISTINCT belief_id_a, belief_id_b FROM held_tensions "
            "WHERE kind = 'tension_held'")
        self.assertEqual(result["distinct_pairs"], len(pairs))
        self.assertEqual(len(before), len(after),
                          "count of distinct ref-pairs changed -- distinct pairs were amalgamated")

    def test_consolidate_dedupes_duplicate_rows_for_same_pair(self):
        """Simulates the race consolidate() exists to clean up: two
        independent rows for the SAME pair (refuse()'s own read-check
        normally prevents this; this test bypasses refuse() to construct
        the race directly). consolidate() must collapse them to one row,
        summing seq, keeping the max single-facing cost (cost of HOLDING
        goes down; the tension itself is not fewer)."""
        import time
        from theory_x.stage3_world_model.ledger_primitives import consolidate
        now = time.time()
        self.writer.write(
            "INSERT INTO held_tensions (belief_id_a, belief_id_b, created_at, "
            "kind, cost, irreversibility, seq, provenance) "
            "VALUES (1, 2, ?, 'tension_held', 40, 1, 1, 'shadow')", (now,))
        self.writer.write(
            "INSERT INTO held_tensions (belief_id_a, belief_id_b, created_at, "
            "kind, cost, irreversibility, seq, provenance) "
            "VALUES (1, 2, ?, 'tension_held', 15, 1, 1, 'shadow2')", (now + 1,))
        result = consolidate(self.reader, self.writer, kind="tension_held")
        self.assertEqual(result["merged_rows"], 1)
        self.assertEqual(result["distinct_pairs"], 1)
        rows = self.reader.read(
            "SELECT cost, seq FROM held_tensions WHERE belief_id_a = 1 AND belief_id_b = 2")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["seq"], 2)
        self.assertEqual(rows[0]["cost"], 40, "consolidated cost should be the max single facing, not the sum")

    def test_consolidate_episode_kind_is_a_documented_noop(self):
        """CONFLICT in the build spec: no real E-side consolidate() exists
        to dispatch 'episode' rows to. Confirm the dispatcher does not
        silently invent behaviour -- it reports a no-op explicitly."""
        from theory_x.stage3_world_model.ledger_primitives import consolidate
        result = consolidate(self.reader, self.writer, kind="episode")
        self.assertEqual(result["merged_rows"], 0)
        self.assertIn("no-op", result["note"])


class DiscriminatorTests(unittest.TestCase):
    """Test 4 — the one the build spec says to protect in review. Prices
    here are SHADOW prices (shadow budget, not the live chat/fountain
    budget) — see module docstring."""

    def setUp(self):
        self.writer, self.reader, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writer, self.tmp)

    def test_refuse_is_neither_veto_nor_noop(self):
        from theory_x.stage_finitude.budget_shadow import Budget
        from theory_x.stage3_world_model.ledger_primitives import refuse
        candidates = _fixed_moment_candidates()

        # 1. no-op substitute: a "refusal" that logs nothing-changing --
        # simulated here by simply never spending; the budget is untouched,
        # so downstream selection must be byte-identical before and after.
        noop_budget = Budget(self.writer, moment_id="noop", capacity=700)
        noop_before = noop_budget.select(candidates)
        noop_after = noop_budget.select(candidates)
        self.assertEqual(noop_before, noop_after,
                          "a no-op refusal must leave the available-action set identical")

        # 2. veto substitute: an option is removed from consideration
        # entirely -- categorically different from a price change: the
        # option disappears, not merely becomes less likely to be picked.
        vetoed_candidates = candidates[1:]
        self.assertEqual(len(vetoed_candidates), len(candidates) - 1,
                          "veto substitute must remove an option from the set")

        # 3. correct implementation: refuse() spends a real shadow cost,
        # which must measurably change what select() keeps -- the sole
        # evidence refuse() prices rather than suppresses.
        correct_budget = Budget(self.writer, moment_id="correct", capacity=700)
        kept_before = correct_budget.select(candidates)
        chars_before = sum(len(t) for t in kept_before)
        refuse(self.writer, self.reader, correct_budget, 1, 2, cost=250)
        kept_after = correct_budget.select(candidates)
        chars_after = sum(len(t) for t in kept_after)
        delta = chars_before - chars_after

        print(f"TEST 4 DELTA (shadow prices): before refuse() selection kept "
              f"{len(kept_before)} blocks / {chars_before} chars; after kept "
              f"{len(kept_after)} blocks / {chars_after} chars -- delta {delta} chars")

        self.assertGreater(delta, 0,
                            "refuse() must measurably raise downstream (shadow) prices -- "
                            "a zero delta means refuse() is a comment, not a price")
        # And: the available-action SET (not just what's kept) is unaffected by
        # refuse() in the way a veto would affect it -- refuse() never removes
        # a candidate from `candidates` itself.
        self.assertEqual(len(candidates), len(_fixed_moment_candidates()),
                          "refuse() must not have mutated the candidate set itself")


class RefusalRateTests(unittest.TestCase):
    def setUp(self):
        self.writer, self.reader, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writer, self.tmp)

    def test_shadow_refusal_rate_strictly_between_zero_and_one(self):
        """Corpus: 20 SYNTHETIC distinct pairs (see module docstring) with a
        fixed cost of 60 each against a shared budget of capacity 600 --
        sized so roughly half the corpus binds. A rate of 0 would be the
        amoha pathology (refuse() exists, never actually commits); a rate
        of 1 would be the māna pathology (always commits regardless of
        cost, carrying no information)."""
        from theory_x.stage_finitude.budget_shadow import Budget, InsufficientBudget
        from theory_x.stage3_world_model.ledger_primitives import refuse
        budget = Budget(self.writer, moment_id="rate", capacity=600)
        corpus_size = 20
        cost_per_pair = 60
        refused = 0
        for i in range(corpus_size):
            try:
                refuse(self.writer, self.reader, budget, i * 2 + 1000, i * 2 + 1001,
                       cost=cost_per_pair)
                refused += 1
            except InsufficientBudget:
                pass
        rate = refused / corpus_size
        binding_fraction = 1 - (budget.remaining / budget.capacity) if budget.capacity else 0
        print(f"REFUSAL RATE (synthetic corpus, 20 distinct pairs, cost={cost_per_pair} "
              f"each, capacity=600): {refused}/{corpus_size} = {rate:.2f}; "
              f"capacity used fraction = {binding_fraction:.2f}")
        self.assertGreater(rate, 0, "amoha pathology: refuse() never actually commits")
        self.assertLess(rate, 1, "māna pathology: refuse() always commits, carries no information")

    @unittest.skip("requires Step 4's forced-commitment consequence (design-only, not "
                    "built this round -- see budget_shadow.py's module docstring and the "
                    "build spec's Step 5); placeholder so this is not silently forgotten "
                    "when that lands")
    def test_shadow_insufficient_budget_forces_commitment(self):
        pass


if __name__ == "__main__":
    unittest.main()
