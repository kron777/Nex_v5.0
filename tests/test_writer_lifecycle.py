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

def test_writer_constructor_start_failure_after_thread_creation_rolls_back(
    tmp_path, monkeypatch
):
    path = tmp_path / "writer-start-failure.db"
    _database(path)

    instances = []
    original_init = Writer.__init__

    def capture_init(self, *args, **kwargs):
        instances.append(self)
        original_init(self, *args, **kwargs)

    original_start = threading.Thread.start
    started_threads = []

    def start_then_fail(thread):
        started_threads.append(thread)
        original_start(thread)
        # Wait until the worker has opened its connection and reached its
        # queue wait before injecting the post-create failure.
        assert instances[0]._started.wait(timeout=2)
        raise RuntimeError("injected Thread.start failure after creation")

    monkeypatch.setattr(Writer, "__init__", capture_init)
    monkeypatch.setattr(threading.Thread, "start", start_then_fail)

    with pytest.raises(RuntimeError, match="after creation"):
        Writer(path, name="writer-start-failure")

    writer = instances[0]
    assert len(started_threads) == 1
    assert not started_threads[0].is_alive()
    assert writer._thread is None
    assert writer._queue.empty()
    assert writer._accepting is False
    assert writer._sentinel_enqueued is False

