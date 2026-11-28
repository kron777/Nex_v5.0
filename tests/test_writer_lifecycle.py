from __future__ import annotations

import threading

import pytest

from substrate import Reader, Writer
from substrate.writer import WriteRequest


def _database(path):
    writer = Writer(path, name="writer-lifecycle-schema")
    writer.write(
        "CREATE TABLE items (id INTEGER PRIMARY KEY AUTOINCREMENT, value TEXT NOT NULL)"
    )
    writer.close()


def test_close_drains_accepted_requests_and_rejects_late_submissions(tmp_path):
    path = tmp_path / "writer.db"
    _database(path)
    writer = Writer(path, name="writer-lifecycle-drain")
    entered = threading.Event()
    release = threading.Event()

    def blocked_insert(cx):
        entered.set()
        assert release.wait(3), "test did not release the blocked Writer callback"
        return cx.execute(
            "INSERT INTO items(value) VALUES ('first')"
        ).lastrowid

    first = writer.submit(WriteRequest(transaction=blocked_insert))
    assert entered.wait(2), "Writer did not start the first request"

    # This request is accepted before close and must remain ahead of the sentinel.
    second = writer.submit(WriteRequest(
        sql="INSERT INTO items(value) VALUES (?)",
        params=("second",),
    ))
    worker = writer._thread

    with pytest.raises(TimeoutError, match="did not stop"):
        writer.close(timeout=0.01)

    # A timed-out close must retain the real worker reference; start must not
    # accidentally create a second writer while the original is still alive.
    assert writer._thread is worker
    writer.start()
    assert writer._thread is worker

    # Anything submitted after shutdown began fails immediately rather than
    # becoming a Future that can never complete behind the sentinel.
    with pytest.raises(RuntimeError, match="closed or not running"):
        writer.write("INSERT INTO items(value) VALUES ('late')")

    release.set()
    writer.close(timeout=2)
    assert first.result(timeout=1) == 1
    assert second.result(timeout=1) == 2
    assert writer._thread is None

    reader = Reader(path)
    assert [row["value"] for row in reader.read(
        "SELECT value FROM items ORDER BY id"
    )] == ["first", "second"]


def test_writer_can_be_explicitly_restarted_after_clean_close(tmp_path):
    path = tmp_path / "writer.db"
    _database(path)
    writer = Writer(path, name="writer-lifecycle-restart")
    writer.close()

    writer.start()
    try:
        row_id = writer.write(
            "INSERT INTO items(value) VALUES ('after restart')"
        )
        assert row_id == 1
    finally:
        writer.close()


def test_submit_close_race_never_strands_an_accepted_request(tmp_path):
    path = tmp_path / "writer-race.db"
    _database(path)
    writer = Writer(path, name="writer-submit-close-race")
    barrier = threading.Barrier(3)
    outcome = {}

    def submit():
        barrier.wait()
        try:
            future = writer.submit(WriteRequest(
                sql="INSERT INTO items(value) VALUES ('raced')"
            ))
        except RuntimeError as exc:
            outcome["rejected"] = str(exc)
            return
        outcome["accepted_result"] = future.result(timeout=3)

    def close():
        barrier.wait()
        try:
            writer.close(timeout=3)
        except Exception as exc:  # captured for assertion in the test thread
            outcome["close_error"] = repr(exc)

    submitter = threading.Thread(target=submit, name="writer-race-submit")
    closer = threading.Thread(target=close, name="writer-race-close")
    submitter.start()
    closer.start()
    barrier.wait()
    submitter.join(timeout=4)
    closer.join(timeout=4)

    assert not submitter.is_alive()
    assert not closer.is_alive()
    assert "close_error" not in outcome
    assert ("accepted_result" in outcome) != ("rejected" in outcome)
    assert writer._thread is None

    reader = Reader(path)
    rows = reader.read("SELECT value FROM items ORDER BY id")
    if "accepted_result" in outcome:
        assert outcome["accepted_result"] == 1
        assert [row["value"] for row in rows] == ["raced"]
    else:
        assert "closed or not running" in outcome["rejected"]
        assert rows == []


def test_multiple_submitters_racing_close_all_resolve_or_reject(tmp_path):
    path = tmp_path / "writer-multi-race.db"
    _database(path)
    writer = Writer(path, name="writer-multi-submit-close-race")
    submitter_count = 8
    barrier = threading.Barrier(submitter_count + 2)
    accepted = []
    rejected = []
    close_errors = []

    def submit(index):
        barrier.wait()
        try:
            future = writer.submit(WriteRequest(
                sql="INSERT INTO items(value) VALUES (?)",
                params=(f"item-{index}",),
            ))
        except RuntimeError:
            rejected.append(index)
            return
        future.result(timeout=5)
        accepted.append(index)

    def close():
        barrier.wait()
        try:
            writer.close(timeout=5)
        except Exception as exc:
            close_errors.append(repr(exc))

    submitters = [
        threading.Thread(target=submit, args=(i,), name=f"writer-race-submit-{i}")
        for i in range(submitter_count)
    ]
    closer = threading.Thread(target=close, name="writer-race-close-many")
    for thread in submitters:
        thread.start()
    closer.start()
    barrier.wait()
    for thread in submitters:
        thread.join(timeout=6)
    closer.join(timeout=6)

    assert all(not thread.is_alive() for thread in submitters)
    assert not closer.is_alive()
    assert close_errors == []
    assert sorted(accepted + rejected) == list(range(submitter_count))
    assert set(accepted).isdisjoint(rejected)
    assert writer._thread is None

    rows = Reader(path).read("SELECT value FROM items ORDER BY value")
    assert [row["value"] for row in rows] == [
        f"item-{index}" for index in sorted(accepted)
    ]

def test_constructor_rolls_back_if_thread_start_raises_after_os_thread_starts(
    tmp_path, monkeypatch
):
    path = tmp_path / "writer-start-failure.db"
    real_start = threading.Thread.start
    captured = {}

    def start_then_raise(thread):
        target = thread._target
        if thread.name == "Writer(start-failure-after-os-start)":
            captured["thread"] = thread
            captured["writer"] = target.__self__
            real_start(thread)
            raise RuntimeError("injected start failure after OS thread creation")
        return real_start(thread)

    monkeypatch.setattr(threading.Thread, "start", start_then_raise)

    try:
        with pytest.raises(RuntimeError, match="injected start failure"):
            Writer(path, name="start-failure-after-os-start")

        worker = captured["thread"]
        assert not worker.is_alive(), (
            "Writer constructor raised but left its already-created worker alive"
        )
    finally:
        worker = captured.get("thread")
        if worker is not None and worker.is_alive():
            # Keep the failing regression isolated: clean up the baseline leak
            # after recording the assertion failure.
            captured["writer"].close(timeout=10)


def test_start_failure_before_os_thread_creation_leaves_writer_restartable(
    tmp_path, monkeypatch
):
    path = tmp_path / "writer-start-fails-before-thread.db"
    real_start = threading.Thread.start
    captured = {}

    def fail_before_start(thread):
        if thread.name == "Writer(start-fails-before-thread)":
            captured["writer"] = thread._target.__self__
            raise RuntimeError("injected failure before OS thread creation")
        return real_start(thread)

    monkeypatch.setattr(threading.Thread, "start", fail_before_start)
    with pytest.raises(RuntimeError, match="before OS thread creation"):
        Writer(path, name="start-fails-before-thread")

    writer = captured["writer"]
    assert writer._thread is None
    assert writer._accepting is True
    assert writer._queue.empty()

    monkeypatch.setattr(threading.Thread, "start", real_start)
    writer.start()
    try:
        writer.write("CREATE TABLE retry_ok (id INTEGER PRIMARY KEY)")
    finally:
        writer.close()


def test_start_rollback_discards_sentinel_when_worker_open_fails(
    tmp_path, monkeypatch
):
    path = tmp_path / "writer-open-fails-during-start.db"
    real_start = threading.Thread.start
    real_open = Writer._open
    captured = {}

    def fail_open(_self):
        raise OSError("injected database-open failure")

    def start_then_raise(thread):
        if thread.name == "Writer(open-fails-during-start)":
            captured["thread"] = thread
            captured["writer"] = thread._target.__self__
            real_start(thread)
            raise RuntimeError("injected caller-side start failure")
        return real_start(thread)

    monkeypatch.setattr(Writer, "_open", fail_open)
    monkeypatch.setattr(threading.Thread, "start", start_then_raise)

    with pytest.raises(RuntimeError, match="caller-side start failure"):
        Writer(path, name="open-fails-during-start")

    worker = captured["thread"]
    writer = captured["writer"]
    assert not worker.is_alive()
    assert writer._thread is None
    assert writer._queue.empty()
    assert writer._accepting is True

    monkeypatch.setattr(Writer, "_open", real_open)
    monkeypatch.setattr(threading.Thread, "start", real_start)
    writer.start()
    try:
        writer.write("CREATE TABLE retry_after_open_failure (id INTEGER PRIMARY KEY)")
    finally:
        writer.close()




def test_start_rollback_timeout_retains_worker_then_retries_without_stale_sentinel(
    tmp_path, monkeypatch
):
    path = tmp_path / "writer-start-rollback-timeout.db"
    real_start = threading.Thread.start
    captured = {}

    def start_then_raise_with_join_timeout(thread):
        if thread.name == "Writer(start-rollback-timeout)":
            captured["thread"] = thread
            captured["writer"] = thread._target.__self__
            real_start(thread)
            # Deterministically simulate the bounded join not completing,
            # without sleeping or leaving a worker behind after the test.
            captured["real_join"] = thread.join
            thread.join = lambda timeout=None: None
            raise RuntimeError("injected start failure with rollback timeout")
        return real_start(thread)

    monkeypatch.setattr(threading.Thread, "start", start_then_raise_with_join_timeout)
    with pytest.raises(RuntimeError, match="rollback timeout"):
        Writer(path, name="start-rollback-timeout")

    writer = captured["writer"]
    worker = captured["thread"]
    try:
        assert worker.is_alive()
        assert writer._thread is worker
        assert writer._accepting is False
        assert writer._sentinel_enqueued is True

        # start() must not create a replacement while the original worker lives.
        writer.start()
        assert writer._thread is worker
    finally:
        # Restore the real join and allow the already-enqueued sentinel to
        # finish the original worker, even if an assertion above fails.
        worker.join = captured["real_join"]
        monkeypatch.setattr(threading.Thread, "start", real_start)
        worker.join(3)
        if worker.is_alive():
            writer.close(timeout=3)

    assert not worker.is_alive()
    writer.start()
    replacement = writer._thread
    assert replacement is not worker
    try:
        writer.write("CREATE TABLE retry_after_rollback_timeout (id INTEGER PRIMARY KEY)")
    finally:
        writer.close()
