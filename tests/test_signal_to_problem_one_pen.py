"""SignalToProblem tick: one-pen persistence and a recoverable two-file order.

signal_to_problem_tick() opens problems in conversations.db and marks the
source signals actioned in beliefs.db. The two databases cannot share a
transaction, so the contract pinned here is:

- every write goes through the canonical Writer for its database (one pen);
  beliefs reads go through a read-only Reader connection;
- open_problems are committed BEFORE the signals are marked actioned, so a
  failure between the two commits can never lose a problem: the signal stays
  unactioned and the next tick re-decides it;
- that re-decision is idempotent -- a problem already opened from signal #N
  (its description carries "Auto-opened from signal #N (type: ...)") is never
  opened a second time; the signal is just marked.

Isolated temporary databases only. Gates, thresholds, the daily cap and titles
are the module's own; these tests assert persistence, not policy.
"""
from __future__ import annotations

import json
import os
import time
import unittest
from unittest import mock

from tests import _bootstrap  # noqa: F401
from tests.test_fountain import _cleanup, _make_env

from theory_x.signals import signal_to_problem as S

_ENTITY = "Chat Control"            # multi-word: substantive without corpus stats


class _Base(unittest.TestCase):
    def setUp(self):
        self._flags = {f: os.environ.pop(f, None) for f in
                       ("NEX5_SIG_QUALITY", "NEX5_PROBLEM_SELF_GATE")}
        self.writers, self.readers, self.tmp = _make_env()

    def tearDown(self):
        _cleanup(self.writers, self.tmp)
        for f, v in self._flags.items():
            if v is not None:
                os.environ[f] = v

    def _signal(self, signal_type="3_branch", payload=None, confidence=0.9):
        payload = payload if payload is not None else {
            "entity": _ENTITY, "branches": ["politics", "systems", "markets"],
            "window_seconds": 1800, "contexts": []}
        return self.writers["beliefs"].write(
            "INSERT INTO signals (detected_at, detector_name, signal_type, payload, "
            "confidence) VALUES (?, 'co_occurrence', ?, ?, ?)",
            (time.time() - 60, signal_type, json.dumps(payload), confidence))

    def _actioned(self, sig_id):
        cols = [r[1] for r in self.readers["beliefs"].read("PRAGMA table_info(signals)")]
        if "actioned_at" not in cols:
            return None
        return self.readers["beliefs"].read_one(
            "SELECT actioned_at FROM signals WHERE id = ?", (sig_id,))[0]

    def _problems_from(self, sig_id):
        return self.readers["conversations"].read(
            "SELECT id, title, state FROM open_problems WHERE description LIKE ?",
            (f"Auto-opened from signal #{sig_id} (type:%",))

    def _shared(self, **override):
        handles = dict(beliefs_writer=self.writers["beliefs"],
                       beliefs_reader=self.readers["beliefs"],
                       conversations_writer=self.writers["conversations"])
        handles.update(override)
        return handles


def _reject_write_capable(path, *args, **kwargs):
    if kwargs.get("read_only") or "mode=ro" in os.fspath(path):
        from substrate import connect
        return connect(path, *args, **kwargs)
    raise AssertionError(f"write-capable direct connection bypassed the Writer: {path}")


class TestOnePen(_Base):
    def test_standalone_tick_opens_no_write_capable_direct_connection(self):
        sig = self._signal()
        with mock.patch.object(S, "connect", side_effect=_reject_write_capable, create=True):
            stats = S.signal_to_problem_tick()
        self.assertEqual(stats["opened"], 1)
        self.assertEqual(len(self._problems_from(sig)), 1)
        self.assertIsNotNone(self._actioned(sig))

    def test_shared_handles_are_used_and_no_writer_is_opened(self):
        sig = self._signal()
        with mock.patch.object(S, "connect", side_effect=_reject_write_capable, create=True), \
             mock.patch.object(S, "Writer", side_effect=AssertionError(
                 "signal_to_problem opened its own Writer despite shared handles"), create=True):
            stats = S.signal_to_problem_tick(**self._shared())
        self.assertEqual(stats["opened"], 1)
        [problem] = self._problems_from(sig)
        self.assertEqual((problem["title"], problem["state"]),
                         (f"Signal: investigate '{_ENTITY}'", "open"))
        self.assertIsNotNone(self._actioned(sig))


class _FailOnce:
    """Shared Writer whose first call of `method` raises after nothing is written."""

    def __init__(self, inner, method):
        self._inner, self._method, self.failed = inner, method, False

    def __getattr__(self, name):
        attr = getattr(self._inner, name)
        if name != self._method or self.failed:
            return attr

        def _boom(*a, **k):
            self.failed = True
            raise RuntimeError(f"injected {name} failure")
        return _boom


class _CommitFailsOnce:
    """Shared conversations Writer whose first transaction does its work and
    then fails at commit time, so everything it wrote rolls back."""

    def __init__(self, inner):
        self._inner, self.failed = inner, False

    def __getattr__(self, name):
        return getattr(self._inner, name)

    def transaction(self, callback):
        if self.failed:
            return self._inner.transaction(callback)

        def _then_fail(conn):
            callback(conn)
            self.failed = True
            raise RuntimeError("injected conversations commit failure")
        return self._inner.transaction(_then_fail)


class TestTwoFileFailureWindow(_Base):
    def test_conversations_failure_leaves_signal_unactioned_and_retryable(self):
        sig = self._signal()
        conv = _CommitFailsOnce(self.writers["conversations"])
        with self.assertRaises(RuntimeError):
            S.signal_to_problem_tick(**self._shared(conversations_writer=conv))
        self.assertTrue(conv.failed)
        self.assertEqual(self._problems_from(sig), [])
        self.assertIsNone(self._actioned(sig))           # not lost: still eligible

        self.assertEqual(S.signal_to_problem_tick(**self._shared())["opened"], 1)
        self.assertEqual(len(self._problems_from(sig)), 1)
        self.assertIsNotNone(self._actioned(sig))

    def test_mark_failure_after_commit_recovers_without_duplicate(self):
        sig = self._signal()
        beliefs = _FailOnce(self.writers["beliefs"], "write_many")
        with self.assertRaises(RuntimeError):
            S.signal_to_problem_tick(**self._shared(beliefs_writer=beliefs))
        self.assertTrue(beliefs.failed)
        self.assertEqual(len(self._problems_from(sig)), 1)  # committed first
        self.assertIsNone(self._actioned(sig))

        stats = S.signal_to_problem_tick(**self._shared())
        self.assertEqual(stats["opened"], 0)
        self.assertEqual(len(self._problems_from(sig)), 1)  # no duplicate
        self.assertIsNotNone(self._actioned(sig))


class TestIdempotency(_Base):
    def test_problem_already_opened_from_signal_is_not_reopened(self):
        """An unactioned signal whose problem already exists -- the state a
        failure between the two commits leaves -- is marked, not reopened.
        The prior problem is closed, so neither the entity dupe check nor the
        drift debounce (both open/stuck only) can stand in for the key."""
        payload = {"token": "loop", "max_df_star": 0.5}
        sig = self._signal("advancements_drift", payload, confidence=0.8)
        now = time.time()
        self.writers["conversations"].write(
            "INSERT INTO open_problems (title, description, state, created_at, "
            "last_touched_at, plan, observations, tags) "
            "VALUES (?, ?, 'closed', ?, ?, '', '[]', ?)",
            ("prior", S._compose_description("advancements_drift", payload, sig),
             now - 3600, now - 3600, json.dumps(["auto", "signal:advancements_drift"])))

        stats = S.signal_to_problem_tick(**self._shared())

        self.assertEqual(stats["opened"], 0)
        self.assertEqual([p["state"] for p in self._problems_from(sig)], ["closed"])
        self.assertIsNotNone(self._actioned(sig))


class TestBehaviourUnchanged(_Base):
    def test_gates_cap_and_marking_are_unchanged(self):
        # ORDER BY confidence DESC: the vague row is decided first, the
        # sixth substantive row is the one the cap stops before.
        vague = self._signal(payload={"entity": "Data", "branches": ["a", "b", "c"]},
                             confidence=0.95)
        good = [self._signal(payload={"entity": f"Flipper Zero {i}",
                                      "branches": ["a", "b", "c"]},
                             confidence=0.9 - i * 0.01) for i in range(6)]
        stats = S.signal_to_problem_tick(**self._shared())
        # identical to unmodified main's no-arg tick on the same fixture
        self.assertEqual(stats, {"considered": 7, "opened": S.DAILY_PROBLEM_CAP,
                                 "skipped_dupe": 1})
        self.assertEqual(self._problems_from(vague), [])
        self.assertIsNotNone(self._actioned(vague))       # gated rows are marked
        opened = [s for s in good if self._problems_from(s)]
        self.assertEqual(len(opened), S.DAILY_PROBLEM_CAP)
        [left] = [s for s in good if not self._problems_from(s)]
        self.assertEqual(left, good[-1])
        self.assertIsNone(self._actioned(left))           # beyond the cap: untouched
        self.assertEqual(S.signal_to_problem_tick(**self._shared()),
                         {"considered": 0, "opened": 0, "skipped_cap": 1})


if __name__ == "__main__":
    unittest.main()
