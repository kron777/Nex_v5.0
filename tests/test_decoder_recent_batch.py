"""api_decoder_recent: the IN(...) batching is behaviour-preserving (H3).

The live decoder ticker polled every 2s and ran 2 point queries per fountain
id (41 statements at limit=20). It now runs two IN(...) queries. This asserts
the batched assembly yields byte-identical output to the old point-query
assembly across several limits and word orderings.
"""
import tempfile
import unittest
from pathlib import Path

from tests import _bootstrap  # noqa: F401

from substrate import connect, Row


def _seed(path):
    c = connect(path)
    c.execute("CREATE TABLE fountain_events "
              "(id INTEGER PRIMARY KEY, ts REAL, thought TEXT, tag TEXT)")
    c.execute("CREATE TABLE word_contexts "
              "(fountain_event_id INTEGER, word TEXT)")
    for fid, ts, th in [(1, 10.0, "a"), (2, 20.0, "b"), (3, 30.0, "c"),
                        (5, 50.0, "e")]:
        c.execute("INSERT INTO fountain_events (id, ts, thought, tag) "
                  "VALUES (?,?,?,?)", (fid, ts, th, "coin"))
    # fid 4 has words but NO fountain_events row (exercises the `if row` skip).
    for fid, w in [(1, "zebra"), (1, "apple"), (2, "mango"), (3, "kiwi"),
                   (3, "fig"), (4, "orphan"), (5, "pear")]:
        c.execute("INSERT INTO word_contexts (fountain_event_id, word) "
                  "VALUES (?,?)", (fid, w))
    c.commit()
    c.close()


def _old(path, limit):
    cx = connect(path)
    cx.row_factory = Row
    fids = cx.execute(
        "SELECT DISTINCT fountain_event_id FROM word_contexts "
        "ORDER BY fountain_event_id DESC LIMIT ?", (limit,)).fetchall()
    out = []
    for f in fids:
        fid = f["fountain_event_id"]
        row = cx.execute("SELECT id, ts, thought, tag FROM fountain_events "
                         "WHERE id=?", (fid,)).fetchone()
        words = cx.execute("SELECT word FROM word_contexts "
                           "WHERE fountain_event_id=? ORDER BY word",
                           (fid,)).fetchall()
        if row:
            out.append({"fid": row["id"], "ts": row["ts"],
                        "thought": row["thought"], "tag": row["tag"],
                        "words": [w["word"] for w in words]})
    cx.close()
    return out


def _new(path, limit):
    cx = connect(path)
    cx.row_factory = Row
    fids = [f["fountain_event_id"] for f in cx.execute(
        "SELECT DISTINCT fountain_event_id FROM word_contexts "
        "ORDER BY fountain_event_id DESC LIMIT ?", (limit,)).fetchall()]
    out = []
    if fids:
        ph = ",".join("?" * len(fids))
        params = tuple(fids)
        rows = {r["id"]: r for r in cx.execute(
            f"SELECT id, ts, thought, tag FROM fountain_events "
            f"WHERE id IN ({ph})", params).fetchall()}
        wbf = {}
        for w in cx.execute(
                f"SELECT fountain_event_id, word FROM word_contexts "
                f"WHERE fountain_event_id IN ({ph}) ORDER BY word",
                params).fetchall():
            wbf.setdefault(w["fountain_event_id"], []).append(w["word"])
        for fid in fids:
            row = rows.get(fid)
            if row:
                out.append({"fid": row["id"], "ts": row["ts"],
                            "thought": row["thought"], "tag": row["tag"],
                            "words": wbf.get(fid, [])})
    cx.close()
    return out


class TestDecoderBatchEquivalence(unittest.TestCase):
    def test_batched_equals_pointwise(self):
        with tempfile.TemporaryDirectory() as d:
            p = str(Path(d) / "dyn.db")
            _seed(p)
            for lim in (1, 2, 3, 20):
                self.assertEqual(_old(p, lim), _new(p, lim), f"limit={lim}")
            # Sanity: fid 4 (orphan words, no event row) is excluded; order DESC.
            self.assertEqual([o["fid"] for o in _new(p, 20)], [5, 3, 2, 1])


if __name__ == "__main__":
    unittest.main()
