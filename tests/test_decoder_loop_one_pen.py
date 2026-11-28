"""The live coincidence decoder uses the canonical Writer transaction."""
from __future__ import annotations

import os
import tempfile
import time
import unittest
from unittest.mock import patch

from tests import _bootstrap  # noqa: F401


class TestDecoderLoopOnePen(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="nex5_decoder_writer_")
        os.environ["NEX5_DATA_DIR"] = self.tmp.name
        from substrate.init_db import init_all
        init_all()
        from substrate import Reader, Writer, db_paths
        paths = db_paths()
        self.writers = {name: Writer(path, name=name) for name, path in paths.items()}
        self.readers = {name: Reader(path) for name, path in paths.items()}

    def tearDown(self):
        for writer in self.writers.values():
            writer.close()
        os.environ.pop("NEX5_DATA_DIR", None)
        self.tmp.cleanup()

    def test_tick_uses_shared_writer_transaction_and_sense_reader(self):
        from theory_x.coincidence import decoder_loop as decoder

        now = time.time()
        self.writers["sense"].write(
            "INSERT INTO sense_events (stream, payload, provenance, timestamp) "
            "VALUES (?, ?, ?, ?)",
            ("external.test", "fresh feed", "test://decoder", int(now - 10)),
        )
        fid = self.writers["dynamic"].write(
            "INSERT INTO fountain_events (ts, thought, readiness, hot_branch, word_count) "
            "VALUES (?, ?, ?, ?, ?)",
            (now, "The quiet astronomy engine is working.", 0.8, "systems", 6),
        )

        with patch.object(
            decoder,
            "Writer",
            side_effect=AssertionError("decoder opened a second dynamic Writer"),
        ):
            result = decoder.decoder_tick(
                dynamic_writer=self.writers["dynamic"],
                sense_reader=self.readers["sense"],
            )

        self.assertEqual(result["processed"], 1)
        self.assertGreater(result["words"], 0)
        rows = self.readers["dynamic"].read(
            "SELECT word, seconds_since_feed FROM word_contexts "
            "WHERE fountain_event_id=?",
            (fid,),
        )
        self.assertGreater(len(rows), 0)
        self.assertTrue(all(row["seconds_since_feed"] is not None for row in rows))
        cursor = self.readers["dynamic"].read_one(
            "SELECT value FROM daemon_kv WHERE key='decoder_last_fid'"
        )
        self.assertEqual(int(cursor["value"]), fid)

    def test_loop_passes_state_handles_into_each_tick(self):
        from theory_x.coincidence import decoder_loop as decoder

        class StopAfterOneTick:
            def __init__(self):
                self.wait_calls = 0
            def is_set(self):
                return False
            def wait(self, seconds):
                self.wait_calls += 1
                return self.wait_calls >= 2

        stop = StopAfterOneTick()
        state = type("State", (), {
            "writers": self.writers,
            "readers": self.readers,
        })()
        with patch.object(
            decoder, "decoder_tick", return_value={"processed": 0, "words": 0}
        ) as tick:
            decoder.decoder_loop(state, stop)
        tick.assert_called_once_with(
            dynamic_writer=self.writers["dynamic"],
            sense_reader=self.readers["sense"],
            stop_event=stop,
        )


if __name__ == "__main__":
    unittest.main()
