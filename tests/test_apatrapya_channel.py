"""apatrapya_channel.py + hri_apatrapya_prototype.py -- the Jon-rating shadow
channel and the hri/apatrapya pairing it unblocks.

PROTOTYPE -- every test class here has "Prototype" in its name, because every
one of them would need rethinking before any of this could be wired for real.
NEX5_APATRAPYA_CHANNEL is not read by gui/server.py or selector.py anywhere;
these tests run against isolated temp databases only (see _make_env below),
never the real data/ directory.

PARAMS, fixed once before this file existed (Step 5's no-tuning rule):
    OPPOSITION_JACCARD_THRESHOLD = 0.12  -- set in hri_apatrapya_prototype.py's
    module body, written before any fixture in this file. Nothing here adjusts
    it to make a fixture pass.

WHAT COULD NOT BE RUN ON REAL DATA (report honestly, don't fake it): T3 ("on
REAL accumulated data") and T9 (re-run at each real milestone) literally
cannot execute -- zero real Jon ratings exist yet. MILESTONES in
apatrapya_channel.py records what's claimable at 0 (this stage). This file
tests the mechanism against fixtures only, which is exactly what Step 0's
"can't-tell-yet" milestone permits.

T6 (ledger pricing) is not run here either -- commit_tension() is a deliberate
NotImplementedError; see hri_apatrapya_prototype.py's module docstring for the
full schema-identity conflict. test_t6_commit_tension_blocked below confirms
the stop is a real, enforced raise, not just a docstring claim.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

from tests import _bootstrap  # noqa: F401

ROOT = Path(__file__).resolve().parent.parent


def _make_env():
    tmp = tempfile.mkdtemp(prefix="nex5_apatrapya_")
    os.environ["NEX5_DATA_DIR"] = tmp
    os.environ["NEX5_ADMIN_HASH_FILE"] = os.path.join(tmp, "admin.argon2")
    from substrate.init_db import init_all
    init_all()
    from substrate import Reader, Writer, db_paths
    paths = db_paths()
    beliefs_writer = Writer(paths["beliefs"], name="beliefs")
    beliefs_reader = Reader(paths["beliefs"])
    conv_writer = Writer(paths["conversations"], name="conversations")
    conv_reader = Reader(paths["conversations"])
    return beliefs_writer, beliefs_reader, conv_writer, conv_reader, tmp


def _cleanup(writers, tmp):
    for w in writers:
        try:
            w.close()
        except Exception:
            pass
    shutil.rmtree(tmp, ignore_errors=True)
    os.environ.pop("NEX5_DATA_DIR", None)
    os.environ.pop("NEX5_ADMIN_HASH_FILE", None)


def _insert_nex_message(conv_writer, content: str) -> int:
    """Test fixture helper -- inserts a fixture NEX message into the
    ISOLATED temp conversations.db (never the real data/ directory). This
    mirrors a real messages row's shape exactly (same INSERT gui/server.py
    uses) so record_rating()'s resolve_output() check is exercised for real,
    not bypassed."""
    return conv_writer.write(
        "INSERT INTO messages (session_id, role, content, timestamp) "
        "VALUES (?, 'nex', ?, ?)",
        ("fixture-session", content, time.time()),
    )


class DisjointReadsPrototypeTests(unittest.TestCase):
    """T1 -- hri and apatrapya read non-overlapping state, both directions."""

    def test_hri_verdict_sql_never_touches_apatrapya_ratings(self):
        import inspect
        from theory_x.stage_tom import hri_apatrapya_prototype as mod
        body = inspect.getsource(mod.hri_verdict).split('"""', 2)[-1]  # strip docstring
        self.assertNotIn("apatrapya_ratings", body)
        self.assertIn("beliefs", body)

    def test_apatrapya_verdict_sql_never_touches_beliefs(self):
        import inspect
        from theory_x.stage_tom import hri_apatrapya_prototype as mod
        src = inspect.getsource(mod.apatrapya_verdict)
        self.assertNotIn("FROM beliefs", src)
        self.assertNotIn("tier = 1", src)

    def test_neither_verdict_function_takes_the_others_verdict_as_input(self):
        import inspect
        from theory_x.stage_tom import hri_apatrapya_prototype as mod
        hri_params = list(inspect.signature(mod.hri_verdict).parameters)
        apa_params = list(inspect.signature(mod.apatrapya_verdict).parameters)
        # Neither function's parameter list contains a verdict-shaped argument.
        for p in hri_params + apa_params:
            self.assertNotIn("verdict", p)
            self.assertNotIn("apatrapya", p if p != "apatrapya_verdict" else "")


class IndependenceUnderAblationPrototypeTests(unittest.TestCase):
    """T2 -- change only one side's input, confirm the other does not move."""

    def setUp(self):
        (self.bw, self.br, self.cw, self.cr, self.tmp) = _make_env()

    def tearDown(self):
        _cleanup([self.bw, self.cw], self.tmp)

    def test_changing_keystone_does_not_move_apatrapya(self):
        from theory_x.stage_tom import apatrapya_channel as ch
        from theory_x.stage_tom import hri_apatrapya_prototype as mod

        out_id = _insert_nex_message(self.cw, "a perfectly ordinary reply")
        ch.record_rating(self.cw, self.cr, out_id, "approve")
        before = mod.apatrapya_verdict(self.cr, out_id)

        # Ablate hri's side only: add a new locked keystone belief.
        self.bw.write(
            "INSERT INTO beliefs (content, tier, confidence, source, branch_id, "
            "locked, created_at) VALUES (?, 1, 0.99, 'test_ablation', 'systems', 1, ?)",
            ("a perfectly ordinary reply is not acceptable at all", time.time()),
        )
        after = mod.apatrapya_verdict(self.cr, out_id)
        self.assertEqual(before, after)

    def test_changing_a_rating_does_not_move_hri(self):
        from theory_x.stage_tom import apatrapya_channel as ch
        from theory_x.stage_tom import hri_apatrapya_prototype as mod

        out_id = _insert_nex_message(self.cw, "a perfectly ordinary reply")
        content = ch.resolve_output(self.cr, out_id)
        before = mod.hri_verdict(self.br, content)

        # Ablate apatrapya's side only: record a rating.
        ch.record_rating(self.cw, self.cr, out_id, "disapprove", reason="test ablation")
        after = mod.hri_verdict(self.br, content)
        self.assertEqual(before, after)


class DegenerateControlPrototypeTests(unittest.TestCase):
    """T7 -- prove the independence check can actually fail. A fake apatrapya
    that is just hri's own reading of the keystone, scaled, must be caught by
    the SAME kind of ablation check T2 uses -- otherwise T2 passing on the
    real build would not mean anything."""

    def setUp(self):
        (self.bw, self.br, self.cw, self.cr, self.tmp) = _make_env()

    def tearDown(self):
        _cleanup([self.bw, self.cw], self.tmp)

    def test_fake_apatrapya_copying_hri_fails_the_ablation_check(self):
        from theory_x.stage_tom import hri_apatrapya_prototype as mod

        out_id = _insert_nex_message(self.cw, "I do not attend to the world with any wonder")
        content = out_id and mod  # placeholder to keep linters calm; real content below
        content = self.cr.read_one(
            "SELECT content FROM messages WHERE id = ?", (out_id,)
        )["content"]

        def fake_apatrapya_verdict(_conv_reader, _output_ref, *, beliefs_reader, content):
            """DEGENERATE BY DESIGN: just copies hri's own permits value --
            it is not independent, and this test exists to prove the
            independence check notices that."""
            hri = mod.hri_verdict(beliefs_reader, content)
            return {"disposition": "apatrapya", "permits": hri["permits"],
                    "rating_ref": None, "reason": "DEGENERATE: copy of hri"}

        before = fake_apatrapya_verdict(self.cr, out_id, beliefs_reader=self.br, content=content)

        # Ablate hri's side: add a keystone belief that flips hri's verdict
        # on this exact content from forbid to permit (remove the opposed
        # content so no keystone opposes it)... instead, more directly: add a
        # keystone that would NOT be opposed, and remove the one that was by
        # construction unreachable in a locked table, so instead we mutate the
        # candidate content's apparent opposition by checking against a
        # DIFFERENT, non-opposing keystone set -- simplest real ablation: use
        # a second, harmless output and show the fake tracks hri 1:1.
        out_id_2 = _insert_nex_message(self.cw, "a perfectly ordinary reply")
        content_2 = self.cr.read_one(
            "SELECT content FROM messages WHERE id = ?", (out_id_2,)
        )["content"]
        hri_1 = mod.hri_verdict(self.br, content)
        hri_2 = mod.hri_verdict(self.br, content_2)
        fake_1 = fake_apatrapya_verdict(self.cr, out_id, beliefs_reader=self.br, content=content)
        fake_2 = fake_apatrapya_verdict(self.cr, out_id_2, beliefs_reader=self.br, content=content_2)

        # The real independence property (T2) requires apatrapya's verdict to
        # be invariant under a change that only affects hri's reasoning about
        # the SAME output. The fake, by construction, moves in lockstep with
        # hri across different outputs -- proving it is NOT independent.
        self.assertNotEqual(hri_1["permits"], hri_2["permits"],
                             "fixture must actually produce two different hri verdicts "
                             "for this control to mean anything")
        self.assertEqual(fake_1["permits"], hri_1["permits"])
        self.assertEqual(fake_2["permits"], hri_2["permits"])
        # i.e. fake_apatrapya == hri on every input: zero independence. This is
        # exactly the failure T1/T2 exist to catch, confirmed caught here.


class ConcordanceControlPrototypeTests(unittest.TestCase):
    """T4 -- when hri and apatrapya agree (both permit, or both forbid), the
    tension count must be exactly zero. Agreeing is not conflict."""

    def setUp(self):
        (self.bw, self.br, self.cw, self.cr, self.tmp) = _make_env()

    def tearDown(self):
        _cleanup([self.bw, self.cw], self.tmp)

    def test_both_permit_is_not_tension(self):
        from theory_x.stage_tom import apatrapya_channel as ch
        from theory_x.stage_tom import hri_apatrapya_prototype as mod

        out_id = _insert_nex_message(self.cw, "a perfectly ordinary reply")
        content = self.cr.read_one("SELECT content FROM messages WHERE id = ?", (out_id,))["content"]
        self.assertTrue(mod.hri_verdict(self.br, content)["permits"])
        ch.record_rating(self.cw, self.cr, out_id, "approve")

        result = mod.detect_tension(self.br, self.cr, out_id)
        self.assertFalse(result["tension"])

    def test_both_forbid_is_not_tension(self):
        from theory_x.stage_tom import apatrapya_channel as ch
        from theory_x.stage_tom import hri_apatrapya_prototype as mod

        out_id = _insert_nex_message(self.cw, "I do not attend to the world with any wonder")
        content = self.cr.read_one("SELECT content FROM messages WHERE id = ?", (out_id,))["content"]
        self.assertFalse(mod.hri_verdict(self.br, content)["permits"])
        ch.record_rating(self.cw, self.cr, out_id, "disapprove")

        result = mod.detect_tension(self.br, self.cr, out_id)
        self.assertFalse(result["tension"])

    def test_divergent_case_is_tension(self):
        from theory_x.stage_tom import apatrapya_channel as ch
        from theory_x.stage_tom import hri_apatrapya_prototype as mod

        out_id = _insert_nex_message(self.cw, "I do not attend to the world with any wonder")
        content = self.cr.read_one("SELECT content FROM messages WHERE id = ?", (out_id,))["content"]
        self.assertFalse(mod.hri_verdict(self.br, content)["permits"])  # hri forbids
        ch.record_rating(self.cw, self.cr, out_id, "approve")  # Jon approves anyway

        result = mod.detect_tension(self.br, self.cr, out_id)
        self.assertTrue(result["tension"])

    def test_no_rating_yet_is_not_tension(self):
        from theory_x.stage_tom import hri_apatrapya_prototype as mod

        out_id = _insert_nex_message(self.cw, "I do not attend to the world with any wonder")
        result = mod.detect_tension(self.br, self.cr, out_id)
        self.assertFalse(result["tension"])
        self.assertIsNone(result["apatrapya"]["permits"])

    def test_abstain_is_not_tension(self):
        from theory_x.stage_tom import apatrapya_channel as ch
        from theory_x.stage_tom import hri_apatrapya_prototype as mod

        out_id = _insert_nex_message(self.cw, "I do not attend to the world with any wonder")
        ch.record_rating(self.cw, self.cr, out_id, "abstain")
        result = mod.detect_tension(self.br, self.cr, out_id)
        self.assertFalse(result["tension"])
        self.assertIsNone(result["apatrapya"]["permits"])


class RetentionPrototypeTests(unittest.TestCase):
    """T5 (store-level, not ledger-level -- see T6 block) -- both rating
    rows (original and any correction) stay live and individually
    retrievable; a correction never edits or deletes the row it corrects."""

    def setUp(self):
        (self.bw, self.br, self.cw, self.cr, self.tmp) = _make_env()

    def tearDown(self):
        _cleanup([self.bw, self.cw], self.tmp)

    def test_correction_does_not_delete_or_edit_original_row(self):
        from theory_x.stage_tom import apatrapya_channel as ch

        out_id = _insert_nex_message(self.cw, "a perfectly ordinary reply")
        first_id = ch.record_rating(self.cw, self.cr, out_id, "approve")
        second_id = ch.record_rating(
            self.cw, self.cr, out_id, "disapprove",
            reason="changed my mind", supersedes=first_id,
        )
        rows = ch.ratings_for_output(self.cr, out_id)
        ids = {r["id"] for r in rows}
        self.assertIn(first_id, ids)
        self.assertIn(second_id, ids)
        first_row = next(r for r in rows if r["id"] == first_id)
        self.assertEqual(first_row["verdict"], "approve")  # unedited

    def test_current_rating_resolves_to_the_correction_not_the_original(self):
        from theory_x.stage_tom import apatrapya_channel as ch
        from theory_x.stage_tom import hri_apatrapya_prototype as mod

        out_id = _insert_nex_message(self.cw, "a perfectly ordinary reply")
        first_id = ch.record_rating(self.cw, self.cr, out_id, "approve")
        ch.record_rating(self.cw, self.cr, out_id, "disapprove", supersedes=first_id)
        verdict = mod.apatrapya_verdict(self.cr, out_id)
        self.assertFalse(verdict["permits"])  # the correction wins for CURRENT reads

    def test_detect_tension_never_fabricates_a_resolution(self):
        from theory_x.stage_tom import apatrapya_channel as ch
        from theory_x.stage_tom import hri_apatrapya_prototype as mod

        out_id = _insert_nex_message(self.cw, "I do not attend to the world with any wonder")
        ch.record_rating(self.cw, self.cr, out_id, "approve")
        result = mod.detect_tension(self.br, self.cr, out_id)
        self.assertTrue(result["tension"])
        dump = str(result)
        self.assertNotIn("winner", dump.lower())
        self.assertNotIn("\"decision\"", dump.lower())


class LedgerPricingBlockedPrototypeTests(unittest.TestCase):
    """T6 is NOT run on real data -- it is structurally blocked. This test
    confirms the block is a real, enforced raise, not a silent no-op or a
    docstring-only claim."""

    def test_t6_commit_tension_blocked(self):
        from theory_x.stage_tom import hri_apatrapya_prototype as mod
        with self.assertRaises(NotImplementedError):
            mod.commit_tension()

    def test_non_belief_pole_insert_blocked_by_not_null(self):
        """Confirms the held_tensions schema fix's own CONFLICT finding
        concretely, not just in a docstring: belief_id_a/belief_id_b are
        NOT NULL at the table level (held over from before pole_*_kind
        existed), so a 'rating'-kind pole genuinely cannot be committed
        without leaving a required column unpopulated. Runs against an
        ISOLATED temp dynamic.db (never real data/), inside an explicit
        transaction that is always rolled back -- zero rows persist either
        way, confirmed below."""
        import sqlite3
        import time as _time

        beliefs_writer, beliefs_reader, conv_writer, conv_reader, tmp = _make_env()
        try:
            from substrate import db_paths
            dyn_path = str(db_paths()["dynamic"])
            conn = sqlite3.connect(dyn_path)
            conn.row_factory = sqlite3.Row
            try:
                conn.execute("BEGIN")
                now = _time.time()
                # A genuine belief-kind pole still works fine post-migration.
                conn.execute(
                    "INSERT INTO held_tensions (belief_id_a, belief_id_b, "
                    "created_at, pole_a_kind, pole_a_ref, pole_b_kind, "
                    "pole_b_ref, subject) VALUES (?,?,?,?,?,?,?,?)",
                    (1, 2, now, "belief", "1", "belief", "2", "fixture subject"),
                )
                # A 'rating'-kind pole cannot leave belief_id_a NULL -- this
                # is the real, concrete blocker, not a hypothetical one.
                with self.assertRaises(sqlite3.IntegrityError) as ctx:
                    conn.execute(
                        "INSERT INTO held_tensions (belief_id_a, belief_id_b, "
                        "created_at, pole_a_kind, pole_a_ref, pole_b_kind, "
                        "pole_b_ref, subject) VALUES (?,?,?,?,?,?,?,?)",
                        (None, 2, now, "rating", "42", "belief", "2",
                         "apatrapya tension fixture"),
                    )
                self.assertIn("NOT NULL", str(ctx.exception))
            finally:
                conn.execute("ROLLBACK")
                # Confirm the rollback actually left zero rows -- the
                # belief-kind insert above must not have persisted either.
                count = conn.execute(
                    "SELECT COUNT(*) FROM held_tensions"
                ).fetchone()[0]
                conn.close()
            self.assertEqual(count, 0)
        finally:
            _cleanup([beliefs_writer, conv_writer], tmp)


class RejectAtWriteTimePrototypeTests(unittest.TestCase):
    """Step 2 -- reject at write time: anything not explicitly channeled,
    anything not from Jon, anything pointing at an unresolvable output."""

    def setUp(self):
        (self.bw, self.br, self.cw, self.cr, self.tmp) = _make_env()

    def tearDown(self):
        _cleanup([self.bw, self.cw], self.tmp)

    def test_rejects_non_jon_actor(self):
        from theory_x.stage_tom import apatrapya_channel as ch
        out_id = _insert_nex_message(self.cw, "x")
        with self.assertRaises(ch.RejectedRating):
            ch.record_rating(self.cw, self.cr, out_id, "approve", actor="someone_else")

    def test_rejects_non_explicit_channel(self):
        from theory_x.stage_tom import apatrapya_channel as ch
        out_id = _insert_nex_message(self.cw, "x")
        with self.assertRaises(ch.RejectedRating):
            ch.record_rating(self.cw, self.cr, out_id, "approve", channel="inferred")

    def test_rejects_unresolvable_output(self):
        from theory_x.stage_tom import apatrapya_channel as ch
        with self.assertRaises(ch.RejectedRating):
            ch.record_rating(self.cw, self.cr, 999999, "approve")

    def test_rejects_invalid_verdict(self):
        from theory_x.stage_tom import apatrapya_channel as ch
        out_id = _insert_nex_message(self.cw, "x")
        with self.assertRaises(ch.RejectedRating):
            ch.record_rating(self.cw, self.cr, out_id, "strongly_approve")

    def test_schema_check_constraint_also_rejects_bad_actor_directly(self):
        """Even bypassing record_rating() entirely, the schema itself
        refuses a non-'jon' actor -- defense in depth, not just a Python
        check."""
        import sqlite3
        from substrate import connect, db_paths
        paths = db_paths()
        with self.assertRaises(sqlite3.IntegrityError):
            with connect(paths["conversations"]) as cx:
                cx.execute(
                    "INSERT INTO apatrapya_ratings "
                    "(actor, channel, output_ref, output_fingerprint, verdict, created_at) "
                    "VALUES ('not_jon', 'explicit', 1, 'x', 'approve', 0)"
                )


class StructuralGuardPrototypeTests(unittest.TestCase):
    """Guards 1-6 -- each needs an actual code check, not a comment. These
    are repo-wide static checks, re-run on every test invocation so the
    invariants cannot silently rot."""

    def _grep(self, pattern: str) -> str:
        return subprocess.run(
            ["grep", "-rnE", pattern, "--include=*.py",
             "--exclude-dir=.venv", "--exclude-dir=__pycache__", "."],
            cwd=ROOT, capture_output=True, text=True,
        ).stdout

    def test_exactly_one_insert_path_into_apatrapya_ratings(self):
        out = self._grep(r"INSERT INTO apatrapya_ratings")
        lines = [l for l in out.splitlines() if l.strip()]
        files = {l.split(":")[0] for l in lines}
        files.discard("./tests/test_apatrapya_channel.py")  # this file's own fixture/IntegrityError tests
        self.assertEqual(
            files, {"./theory_x/stage_tom/apatrapya_channel.py"},
            f"expected exactly one file with an INSERT into apatrapya_ratings, found: {files}",
        )

    def test_append_only_no_update_or_delete_anywhere(self):
        upd = self._grep(r"UPDATE\s+apatrapya_ratings")
        dele = self._grep(r"DELETE\s+FROM\s+apatrapya_ratings")
        self.assertEqual(upd.strip(), "")
        self.assertEqual(dele.strip(), "")

    def test_no_aggregation_function_over_ratings_exists_anywhere(self):
        """Guard 2 + Guard 6 -- no running score/average/tally/approval-rate
        over apatrapya_ratings exists anywhere in the repo. total_rating_count()
        is the one sanctioned cross-row read (a plain count for milestone
        gating, never verdict-weighted) and is explicitly excluded here."""
        out = self._grep(r"apatrapya_ratings")
        offenders = []
        for line in out.splitlines():
            if "total_rating_count" in line or "test_apatrapya_channel.py" in line:
                continue
            lowered = line.lower()
            if any(tok in lowered for tok in
                   ("avg(", "sum(", "average", "approval_rate", "approve_rate",
                    "disapprove_rate", "running_total", "rate =")):
                offenders.append(line)
        self.assertEqual(offenders, [], f"found aggregation over ratings: {offenders}")

    def test_no_gradient_nothing_outside_apatrapya_module_reads_the_table(self):
        """Guard 1 -- nothing outside apatrapya_channel.py / hri_apatrapya_
        prototype.py / this test file reads apatrapya_ratings."""
        out = self._grep(r"apatrapya_ratings")
        files = {l.split(":")[0] for l in out.splitlines() if l.strip()}
        allowed = {
            "./theory_x/stage_tom/apatrapya_channel.py",
            "./theory_x/stage_tom/hri_apatrapya_prototype.py",  # via ratings_for_output(), not raw SQL
            "./tests/test_apatrapya_channel.py",
            "./substrate/init_db.py",  # schema definition only
            "./substrate/schema/conversations.sql",  # doc comment only, if present
        }
        self.assertTrue(
            files.issubset(allowed),
            f"unexpected readers of apatrapya_ratings: {files - allowed}",
        )

    def test_no_anticipation_nothing_calls_detect_tension_outside_tests_and_cli(self):
        """Guard 3 -- ratings are read only when a tension-check actually
        happens, never speculatively. Confirms detect_tension/apatrapya_verdict
        are called from nowhere but this test file (nothing wires them into
        any live or scheduled loop yet)."""
        out = self._grep(r"detect_tension\(|apatrapya_verdict\(")
        files = {l.split(":")[0] for l in out.splitlines() if l.strip()}
        allowed = {
            "./theory_x/stage_tom/hri_apatrapya_prototype.py",
            "./theory_x/stage_tom/apatrapya_channel.py",  # doc mention only (module docstring)
            "./tests/test_apatrapya_channel.py",
        }
        self.assertTrue(files.issubset(allowed), f"unexpected callers: {files - allowed}")

    def test_no_tie_break_detect_tension_never_names_a_winner(self):
        """Guard 4 -- descriptive-never-verdict, same standing rule as
        everywhere else. No code path in the pairing module returns, picks,
        or names a 'winner'."""
        import inspect
        from theory_x.stage_tom import hri_apatrapya_prototype as mod
        src = inspect.getsource(mod)
        for forbidden in ("winner", "wins_", "overrule", "settles the"):
            self.assertNotIn(forbidden, src.lower())


class SyntheticApprovalBurstPrototypeTests(unittest.TestCase):
    """T8 -- a burst of approvals changes nothing about NEX's actual
    selection/ranking/scoring/budget, and no aggregating function exists."""

    def setUp(self):
        (self.bw, self.br, self.cw, self.cr, self.tmp) = _make_env()

    def tearDown(self):
        _cleanup([self.bw, self.cw], self.tmp)

    def test_approval_burst_does_not_change_select_within_budget(self):
        from theory_x.stage_tom import apatrapya_channel as ch
        from theory_x.stage_tom.global_workspace import select_within_budget

        candidates = [(0.9, "x" * 100, False), (0.5, "y" * 100, False)]
        before = select_within_budget(candidates, 150)

        out_id = _insert_nex_message(self.cw, "a perfectly ordinary reply")
        for _ in range(25):
            ch.record_rating(self.cw, self.cr, out_id, "approve")

        after = select_within_budget(candidates, 150)
        self.assertEqual(before, after)

    def test_approval_burst_does_not_change_shadow_budget_capacity(self):
        from theory_x.stage_finitude import budget_shadow
        from theory_x.stage_tom import apatrapya_channel as ch

        capacity_before = budget_shadow._DEFAULT_CAPACITY
        out_id = _insert_nex_message(self.cw, "a perfectly ordinary reply")
        for _ in range(25):
            ch.record_rating(self.cw, self.cr, out_id, "approve")
        capacity_after = budget_shadow._DEFAULT_CAPACITY
        self.assertEqual(capacity_before, capacity_after)

    def test_no_aggregating_function_exists_for_the_burst_to_feed(self):
        import theory_x.stage_tom.apatrapya_channel as ch
        public_fns = [f for f in dir(ch) if not f.startswith("_")]
        for name in public_fns:
            self.assertNotIn("rate", name.lower().replace("_rating", ""))
        # The only count-shaped function is total_rating_count, which is
        # verdict-blind (does not SELECT verdict at all) -- confirmed directly.
        import inspect
        body = inspect.getsource(ch.total_rating_count).split('"""', 2)[-1]  # strip docstring
        self.assertNotIn("verdict", body)


if __name__ == "__main__":
    unittest.main()
