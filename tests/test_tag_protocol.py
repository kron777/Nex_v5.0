"""Tests for the Tag Protocol substrate (spec: theory_x/TAG_PROTOCOL.md §9).

Unit tests 1–20 per spec §9:
  1  - Normalize: lowercase conversion
  2  - Normalize: whitespace trim and internal collapse to hyphens
  3  - Normalize: punctuation strip
  4  - Normalize: consecutive hyphen collapse
  5  - Normalize: leading/trailing hyphen strip
  6  - Normalize: empty rejection
  7  - Normalize: single-character rejection
  8  - Normalize: length truncation at 40 chars
  9  - Generate: produces tags from content via TriggerDetector stopword strip
  10 - Generate: tag count cap respected (soft K, hard 16)
  11 - Read: returns Python list for valid JSON
  12 - Read: returns empty list for default '[]'
  13 - Write: replaces tags array, normalizes input
  14 - Add: appends, deduplicates
  15 - Remove: drops tag, no-op if absent
  16 - Query: finds entities containing tag in one surface
  17 - Query: finds entities across all surfaces when table=None
  18 - Vocabulary: returns distinct tags with counts
  19 - Near-duplicates: returns pairs within Levenshtein threshold
  20 - Merge: renames tag across all surfaces, dedupes per-row

Integration tests:
  A - Insert belief; verify auto-tags appear
  B - Insert problem; verify auto-tags appear
  C - Query tag appearing on both surfaces
  D - Merge tag across surfaces
  E - Vocabulary counts match expected frequencies
"""
from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from unittest.mock import MagicMock, call

from theory_x.tag_protocol.tag_ops import (
    TAGGABLE_TABLES,
    _levenshtein,
    _normalize_list,
    add,
    generate,
    merge,
    near_duplicates,
    normalize,
    query,
    read,
    remove,
    vocabulary,
    write,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _mock_reader(rows_by_query=None, single_rows=None):
    """Build a Reader mock wired to return canned results."""
    reader = MagicMock()
    reader.db_path = ":memory:"
    if single_rows:
        reader.read_one.side_effect = lambda sql, params=(): single_rows.get(params[0] if params else None)
    if rows_by_query is not None:
        reader.read.return_value = rows_by_query
    return reader


def _mock_writer():
    writer = MagicMock()
    writer.db_path = ":memory:"
    writer.write.return_value = 1
    return writer


def _sqlite_row(d: dict):
    """Create a dict-accessible sqlite3.Row substitute using MagicMock."""
    row = MagicMock()
    row.__getitem__ = lambda self, key: d[key]
    row.keys = lambda: d.keys()
    # Make dict() work
    row.__iter__ = lambda self: iter(d)
    # Support hasattr("__getitem__") check in vocabulary
    return row


def _real_row(conn, table, entity_id):
    """Fetch a real sqlite3.Row from an in-memory DB."""
    conn.row_factory = sqlite3.Row
    return conn.execute(f"SELECT * FROM {table} WHERE id=?", (entity_id,)).fetchone()


# ── §6 Normalize tests (1–8) ──────────────────────────────────────────────────

class TestNormalize(unittest.TestCase):

    def test_1_lowercase(self):
        self.assertEqual(normalize("Cognition"), "cognition")

    def test_2_whitespace_trim_and_collapse(self):
        # Trim: leading/trailing whitespace
        self.assertEqual(normalize("  hello  "), "hello")
        # Internal whitespace → hyphen
        self.assertEqual(normalize("Cognition Pattern"), "cognition-pattern")

    def test_3_punctuation_strip(self):
        self.assertEqual(normalize("AI Research!"), "ai-research")
        self.assertEqual(normalize("epistemology / theory-of-mind"), "epistemology-theory-of-mind")

    def test_4_consecutive_hyphen_collapse(self):
        self.assertEqual(normalize("a---b"), "a-b")

    def test_5_leading_trailing_hyphen_strip(self):
        self.assertEqual(normalize("-hello-"), "hello")
        self.assertEqual(normalize("--test--"), "test")

    def test_6_empty_rejection(self):
        self.assertIsNone(normalize(""))
        self.assertIsNone(normalize("   "))
        self.assertIsNone(normalize("!!!"))

    def test_7_single_char_rejection(self):
        self.assertIsNone(normalize("A"))
        self.assertIsNone(normalize("x"))

    def test_8_length_truncation_at_40(self):
        long_input = "a" * 50
        result = normalize(long_input)
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 40)

    def test_examples_from_spec(self):
        self.assertEqual(normalize("Cognition Pattern"), "cognition-pattern")
        self.assertEqual(normalize("  AI Research!  "), "ai-research")
        self.assertEqual(normalize("epistemology / theory-of-mind"), "epistemology-theory-of-mind")
        self.assertEqual(normalize("Phase-29"), "phase-29")
        self.assertIsNone(normalize("A"))
        self.assertIsNone(normalize(""))
        self.assertEqual(normalize("a---b"), "a-b")


# ── §4 Generate tests (9–10) ──────────────────────────────────────────────────

class TestGenerate(unittest.TestCase):

    def test_9_stopwords_stripped(self):
        # "the", "is", "a" are stopwords — only content words survive
        tags = generate("the cat is a mammal with cognition")
        self.assertNotIn("the", tags)
        self.assertNotIn("is", tags)
        self.assertNotIn("a", tags)
        # "cognition" and "mammal" should appear
        self.assertIn("cognition", tags)
        self.assertIn("mammal", tags)

    def test_9_short_tokens_stripped(self):
        # Tokens under 3 chars (after stopword removal) are dropped
        tags = generate("AI is about big cognition systems")
        # "ai" is 2 chars — but after stopword strip it becomes a candidate
        # "ai" has len 2 — should be dropped by min_token_len=3
        self.assertNotIn("ai", tags)
        self.assertIn("big", tags)
        self.assertIn("cognition", tags)
        self.assertIn("systems", tags)

    def test_9_numeric_tokens_stripped(self):
        tags = generate("phase 29 test content cognition")
        self.assertNotIn("29", tags)
        self.assertIn("phase", tags)
        self.assertIn("content", tags)
        self.assertIn("cognition", tags)

    def test_10_soft_k_cap(self):
        # 20+ distinct content words; should get at most k=8 tags by default
        content = " ".join([
            "apple banana cherry dragon elderberry fig grape honeydew",
            "iceberg jalapeno kiwi lemon mango nectarine orange papaya",
        ])
        tags = generate(content, k=5)
        self.assertLessEqual(len(tags), 5)

    def test_10_hard_limit_never_exceeded(self):
        # k=8 default; hard limit is 16. With default k, we should never approach 16.
        long_content = " ".join([f"concept{i}" for i in range(100)])
        tags = generate(long_content, k=8)
        self.assertLessEqual(len(tags), 8)

    def test_10_frequency_ranking(self):
        # "cognition" appears 3x, "systems" 1x — cognition should rank higher
        content = "cognition systems cognition drives cognition"
        tags = generate(content, k=2)
        self.assertEqual(tags[0], "cognition")

    def test_empty_content(self):
        self.assertEqual(generate(""), [])

    def test_stopwords_only(self):
        self.assertEqual(generate("the is a and of"), [])


# ── Read/Write tests (11–13) ──────────────────────────────────────────────────

class TestReadWrite(unittest.TestCase):

    def test_11_read_returns_list_for_valid_json(self):
        reader = _mock_reader()
        reader.read_one.return_value = {"tags": '["cognition", "systems"]'}
        result = read(reader, "beliefs", 1)
        self.assertEqual(result, ["cognition", "systems"])

    def test_12_read_returns_empty_for_default(self):
        reader = _mock_reader()
        reader.read_one.return_value = {"tags": "[]"}
        self.assertEqual(read(reader, "beliefs", 99), [])

    def test_12_read_returns_empty_for_none_row(self):
        reader = _mock_reader()
        reader.read_one.return_value = None
        self.assertEqual(read(reader, "beliefs", 999), [])

    def test_13_write_replaces_and_normalizes(self):
        writer = _mock_writer()
        write(writer, "beliefs", 1, ["Cognition Pattern", "SYSTEMS"])
        writer.write.assert_called_once()
        call_args = writer.write.call_args
        stored = json.loads(call_args.args[1][0])
        self.assertIn("cognition-pattern", stored)
        self.assertIn("systems", stored)
        # Must not contain raw un-normalized strings
        self.assertNotIn("Cognition Pattern", stored)
        self.assertNotIn("SYSTEMS", stored)

    def test_13_write_deduplicates(self):
        writer = _mock_writer()
        write(writer, "beliefs", 1, ["cognition", "Cognition", "cognition"])
        call_args = writer.write.call_args
        stored = json.loads(call_args.args[1][0])
        self.assertEqual(stored.count("cognition"), 1)

    def test_13_write_drops_rejected_tags(self):
        writer = _mock_writer()
        write(writer, "beliefs", 1, ["", "A", "valid-tag"])
        call_args = writer.write.call_args
        stored = json.loads(call_args.args[1][0])
        self.assertEqual(stored, ["valid-tag"])


# ── Add test (14) ─────────────────────────────────────────────────────────────

class TestAdd(unittest.TestCase):

    def test_14_add_appends_deduplicates(self):
        reader = _mock_reader()
        reader.read_one.return_value = {"tags": '["existing"]'}
        writer = _mock_writer()

        add(writer, reader, "beliefs", 1, ["new-tag", "Existing"])
        call_args = writer.write.call_args
        stored = json.loads(call_args.args[1][0])
        # "existing" should appear once (deduplicated)
        self.assertEqual(stored.count("existing"), 1)
        self.assertIn("new-tag", stored)

    def test_14_add_normalizes_new_tags(self):
        reader = _mock_reader()
        reader.read_one.return_value = {"tags": "[]"}
        writer = _mock_writer()

        add(writer, reader, "beliefs", 1, ["NEW TAG"])
        call_args = writer.write.call_args
        stored = json.loads(call_args.args[1][0])
        self.assertIn("new-tag", stored)
        self.assertNotIn("NEW TAG", stored)


# ── Remove test (15) ──────────────────────────────────────────────────────────

class TestRemove(unittest.TestCase):

    def test_15_remove_drops_tag(self):
        reader = _mock_reader()
        reader.read_one.return_value = {"tags": '["cognition", "systems"]'}
        writer = _mock_writer()

        remove(writer, reader, "beliefs", 1, "cognition")
        call_args = writer.write.call_args
        stored = json.loads(call_args.args[1][0])
        self.assertNotIn("cognition", stored)
        self.assertIn("systems", stored)

    def test_15_remove_noop_if_absent(self):
        reader = _mock_reader()
        reader.read_one.return_value = {"tags": '["systems"]'}
        writer = _mock_writer()

        remove(writer, reader, "beliefs", 1, "nonexistent")
        # write() should not have been called — tag wasn't present
        writer.write.assert_not_called()

    def test_15_remove_normalizes_input(self):
        reader = _mock_reader()
        reader.read_one.return_value = {"tags": '["cognition"]'}
        writer = _mock_writer()

        # "Cognition" normalizes to "cognition" — should still match
        remove(writer, reader, "beliefs", 1, "Cognition")
        call_args = writer.write.call_args
        stored = json.loads(call_args.args[1][0])
        self.assertNotIn("cognition", stored)


# ── Query tests (16–17) ───────────────────────────────────────────────────────

class TestQuery(unittest.TestCase):

    def _make_row(self, **kwargs):
        row = MagicMock()
        data = {**kwargs}
        row.__getitem__ = lambda self, k: data[k]
        row.keys = lambda: data.keys()
        # dict() conversion support
        def items():
            return data.items()
        row.items = items
        # Make dict(row) work via MagicMock
        type(row).__iter__ = lambda self: iter(data.keys())
        return row

    def test_16_query_single_table(self):
        reader = MagicMock()
        fake_row = MagicMock()
        fake_row.__iter__ = MagicMock(return_value=iter({"id": 1, "content": "test", "tags": '["cognition"]'}.items()))
        fake_row.keys = MagicMock(return_value=["id", "content", "tags"])
        # Simulate two result rows
        row1 = {"id": 1, "content": "test", "tags": '["cognition"]'}
        mock_row1 = MagicMock()
        mock_row1.keys.return_value = row1.keys()
        mock_row1.__getitem__ = lambda self, k: row1[k]
        mock_row1.__iter__ = lambda self: iter(row1.keys())
        reader.read.return_value = [mock_row1]
        reader.db_path = ":memory:"

        results = query(reader, "cognition", table="beliefs")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["_table"], "beliefs")
        # The reader should have been called with the normalized tag
        reader.read.assert_called_once()
        sql_used = reader.read.call_args.args[0]
        self.assertIn("beliefs", sql_used)
        # Confirm normalized tag was passed
        params = reader.read.call_args.args[1]
        self.assertEqual(params, ("cognition",))

    def test_16_query_normalizes_input_tag(self):
        reader = MagicMock()
        reader.read.return_value = []
        query(reader, "  COGNITION!  ", table="beliefs")
        params = reader.read.call_args.args[1]
        self.assertEqual(params, ("cognition",))

    def test_17_query_cross_table(self):
        beliefs_reader = MagicMock()
        beliefs_reader.read.return_value = []
        convs_reader = MagicMock()
        convs_reader.read.return_value = []
        readers = {"beliefs": beliefs_reader, "conversations": convs_reader}

        query(readers, "cognition")
        beliefs_reader.read.assert_called_once()
        convs_reader.read.assert_called_once()

    def test_17_query_returns_empty_on_bad_tag(self):
        readers = {"beliefs": MagicMock(), "conversations": MagicMock()}
        result = query(readers, "")
        self.assertEqual(result, [])
        result2 = query(readers, "A")  # too short after normalize
        self.assertEqual(result2, [])


# ── Vocabulary test (18) ──────────────────────────────────────────────────────

class TestVocabulary(unittest.TestCase):

    def test_18_vocabulary_returns_dict_with_counts(self):
        beliefs_reader = MagicMock()
        # Return two tags from beliefs
        beliefs_reader.read.return_value = [
            {"tag": "cognition", "cnt": 5},
            {"tag": "systems", "cnt": 2},
        ]
        convs_reader = MagicMock()
        convs_reader.read.return_value = [
            {"tag": "cognition", "cnt": 3},
        ]
        readers = {"beliefs": beliefs_reader, "conversations": convs_reader}

        vocab = vocabulary(readers)
        # cognition: 5 + 3 = 8 total
        self.assertEqual(vocab.get("cognition"), 8)
        self.assertEqual(vocab.get("systems"), 2)

    def test_18_vocabulary_single_table(self):
        reader = MagicMock()
        reader.read.return_value = [
            {"tag": "cognition", "cnt": 4},
        ]
        vocab = vocabulary(reader, table="beliefs")
        self.assertEqual(vocab.get("cognition"), 4)
        reader.read.assert_called_once()

    def test_18_vocabulary_sorted_descending(self):
        reader = MagicMock()
        reader.read.return_value = [
            {"tag": "rare", "cnt": 1},
            {"tag": "common", "cnt": 10},
        ]
        vocab = vocabulary(reader, table="beliefs")
        keys = list(vocab.keys())
        self.assertEqual(keys[0], "common")
        self.assertEqual(keys[1], "rare")


# ── Near-duplicates test (19) ─────────────────────────────────────────────────

class TestNearDuplicates(unittest.TestCase):

    def test_19_returns_pairs_within_threshold(self):
        reader = MagicMock()
        # cognition vs cogniton: distance 1
        reader.read.return_value = [
            {"tag": "cognition", "cnt": 3},
            {"tag": "cogniton", "cnt": 1},
            {"tag": "systems", "cnt": 2},
        ]
        pairs = near_duplicates(reader, threshold=2)
        pair_tags = {frozenset(p) for p in pairs}
        self.assertIn(frozenset({"cognition", "cogniton"}), pair_tags)
        # "systems" should not pair with either cognition variant (distance > 2)
        for p in pairs:
            self.assertNotIn("systems", p)

    def test_19_empty_vocabulary_no_pairs(self):
        reader = MagicMock()
        reader.read.return_value = []
        pairs = near_duplicates({"beliefs": reader, "conversations": MagicMock(read=MagicMock(return_value=[]))})
        self.assertEqual(pairs, [])

    def test_levenshtein_helper(self):
        self.assertEqual(_levenshtein("cognition", "cogniton"), 1)
        self.assertEqual(_levenshtein("", "abc"), 3)
        self.assertEqual(_levenshtein("abc", "abc"), 0)
        self.assertEqual(_levenshtein("memory", "memories"), 3)


# ── Merge test (20) ───────────────────────────────────────────────────────────

class TestMerge(unittest.TestCase):

    def _mock_row(self, entity_id: int, tags: list[str]):
        """Build a minimal sqlite3.Row-like object for merge iteration."""
        data = {"id": entity_id, "tags": json.dumps(tags)}
        row = MagicMock()
        row.__getitem__ = lambda self, k: data[k]
        return row

    def test_20_merge_renames_across_surfaces(self):
        b_row = self._mock_row(1, ["cognition", "systems"])
        c_row = self._mock_row(5, ["cognition", "memory"])

        beliefs_reader = MagicMock()
        beliefs_reader.read.return_value = [b_row]
        convs_reader = MagicMock()
        convs_reader.read.return_value = [c_row]

        beliefs_writer = MagicMock()
        convs_writer = MagicMock()

        readers = {"beliefs": beliefs_reader, "conversations": convs_reader}
        writers = {"beliefs": beliefs_writer, "conversations": convs_writer}

        count = merge(writers, readers, "cognition", "reasoning")
        self.assertEqual(count, 2)

        # beliefs: row 1 updated
        b_call = beliefs_writer.write.call_args
        b_stored = json.loads(b_call.args[1][0])
        self.assertIn("reasoning", b_stored)
        self.assertNotIn("cognition", b_stored)
        self.assertIn("systems", b_stored)

        # conversations: row 5 updated
        c_call = convs_writer.write.call_args
        c_stored = json.loads(c_call.args[1][0])
        self.assertIn("reasoning", c_stored)
        self.assertNotIn("cognition", c_stored)

    def test_20_merge_deduplicates_on_replacement(self):
        row = self._mock_row(1, ["cognition", "reasoning"])
        reader = MagicMock()
        reader.read.return_value = [row]
        convs_reader = MagicMock()
        convs_reader.read.return_value = []
        writer = MagicMock()
        readers = {"beliefs": reader, "conversations": convs_reader}
        writers = {"beliefs": writer, "conversations": MagicMock()}

        # Merging "cognition" → "reasoning" where "reasoning" already exists
        merge(writers, readers, "cognition", "reasoning")
        call = writer.write.call_args
        stored = json.loads(call.args[1][0])
        self.assertEqual(stored.count("reasoning"), 1)

    def test_20_merge_noop_for_invalid_tags(self):
        readers = {"beliefs": MagicMock(), "conversations": MagicMock()}
        writers = {"beliefs": MagicMock(), "conversations": MagicMock()}
        count = merge(writers, readers, "", "reasoning")
        self.assertEqual(count, 0)
        count2 = merge(writers, readers, "cognition", "")
        self.assertEqual(count2, 0)


# ── Integration tests (A–E) ───────────────────────────────────────────────────

def _make_integration_db():
    """Create an in-memory SQLite with beliefs and open_problems tables."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE beliefs (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT    NOT NULL UNIQUE,
            tags    TEXT    NOT NULL DEFAULT '[]'
        )
    """)
    conn.execute("""
        CREATE TABLE open_problems (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT    NOT NULL,
            tags  TEXT    NOT NULL DEFAULT '[]'
        )
    """)
    conn.commit()
    return conn


class _InMemReader:
    """Thin Reader shim over a shared sqlite3.Connection."""

    def __init__(self, conn):
        self._conn = conn
        self.db_path = ":memory:"

    def read(self, sql, params=()):
        self._conn.row_factory = sqlite3.Row
        return self._conn.execute(sql, params).fetchall()

    def read_one(self, sql, params=()):
        self._conn.row_factory = sqlite3.Row
        return self._conn.execute(sql, params).fetchone()


class _InMemWriter:
    """Thin Writer shim over a shared sqlite3.Connection."""

    def __init__(self, conn):
        self._conn = conn
        self.db_path = ":memory:"

    def write(self, sql, params=()):
        cur = self._conn.execute(sql, params)
        self._conn.commit()
        return cur.lastrowid


class TestIntegration(unittest.TestCase):

    def setUp(self):
        self.conn = _make_integration_db()
        self.reader = _InMemReader(self.conn)
        self.writer = _InMemWriter(self.conn)
        # Shared readers/writers dicts for cross-table functions
        self.readers = {"beliefs": self.reader, "conversations": self.reader}
        self.writers = {"beliefs": self.writer, "conversations": self.writer}

    # A — Insert belief; verify auto-tags can be written and read back
    def test_A_belief_tags_round_trip(self):
        content = "consciousness emerges from belief field patterns"
        tags = generate(content)
        self.assertGreater(len(tags), 0)
        self.conn.execute(
            "INSERT INTO beliefs (content, tags) VALUES (?, ?)",
            (content, json.dumps(tags)),
        )
        self.conn.commit()
        result = read(self.reader, "beliefs", 1)
        self.assertEqual(result, tags)

    # B — Insert problem; verify auto-tags appear
    def test_B_problem_tags_round_trip(self):
        title = "recursion and emergent cognition patterns"
        tags = generate(title)
        self.assertGreater(len(tags), 0)
        self.conn.execute(
            "INSERT INTO open_problems (title, tags) VALUES (?, ?)",
            (title, json.dumps(tags)),
        )
        self.conn.commit()
        result = read(self.reader, "open_problems", 1)
        self.assertEqual(result, tags)

    # C — Query tag appearing on both surfaces
    def test_C_cross_surface_query(self):
        self.conn.execute(
            "INSERT INTO beliefs (content, tags) VALUES (?, ?)",
            ("belief about cognition", json.dumps(["cognition", "belief"])),
        )
        self.conn.execute(
            "INSERT INTO open_problems (title, tags) VALUES (?, ?)",
            ("open cognition question", json.dumps(["cognition", "question"])),
        )
        self.conn.commit()

        results = query(self.readers, "cognition")
        tables = {r["_table"] for r in results}
        self.assertIn("beliefs", tables)
        self.assertIn("open_problems", tables)
        self.assertEqual(len(results), 2)

    # D — Merge tag across surfaces
    def test_D_merge_cross_surface(self):
        self.conn.execute(
            "INSERT INTO beliefs (content, tags) VALUES (?, ?)",
            ("reasoning and logic", json.dumps(["cognition", "logic"])),
        )
        self.conn.execute(
            "INSERT INTO open_problems (title, tags) VALUES (?, ?)",
            ("cognition question", json.dumps(["cognition", "question"])),
        )
        self.conn.commit()

        count = merge(self.writers, self.readers, "cognition", "reasoning")
        self.assertEqual(count, 2)

        b_tags = read(self.reader, "beliefs", 1)
        self.assertIn("reasoning", b_tags)
        self.assertNotIn("cognition", b_tags)

        p_tags = read(self.reader, "open_problems", 1)
        self.assertIn("reasoning", p_tags)
        self.assertNotIn("cognition", p_tags)

    # E — Vocabulary counts
    def test_E_vocabulary_counts(self):
        self.conn.execute(
            "INSERT INTO beliefs (content, tags) VALUES (?, ?)",
            ("belief one", json.dumps(["cognition", "systems"])),
        )
        self.conn.execute(
            "INSERT INTO beliefs (content, tags) VALUES (?, ?)",
            ("belief two", json.dumps(["cognition"])),
        )
        self.conn.execute(
            "INSERT INTO open_problems (title, tags) VALUES (?, ?)",
            ("problem one", json.dumps(["systems"])),
        )
        self.conn.commit()

        vocab = vocabulary(self.readers)
        self.assertEqual(vocab.get("cognition"), 2)
        self.assertEqual(vocab.get("systems"), 2)

    def tearDown(self):
        self.conn.close()


# ── Wrapper tests (C1–C3) ─────────────────────────────────────────────────────

class TestTaggingBeliefWriter(unittest.TestCase):
    """Tests for TaggingBeliefWriter (theory_x/tag_protocol/writer_wrapper.py)."""

    def _make_wrapper(self):
        """Build a TaggingBeliefWriter over a mock inner writer."""
        inner = MagicMock()
        inner.db_path = ":memory:"
        inner.name = "beliefs"
        inner.write.side_effect = lambda sql, params=(): (sql, params)
        wrapper = __import__(
            "theory_x.tag_protocol.writer_wrapper",
            fromlist=["TaggingBeliefWriter"],
        ).TaggingBeliefWriter(inner)
        return wrapper, inner

    def test_C1_passthrough_non_beliefs_insert(self):
        wrapper, inner = self._make_wrapper()
        sql = "INSERT INTO other_table (col) VALUES (?)"
        wrapper.write(sql, ("value",))
        inner.write.assert_called_once_with(sql, ("value",))

    def test_C2_injects_tags_on_beliefs_insert(self):
        wrapper, inner = self._make_wrapper()
        sql = (
            "INSERT INTO beliefs "
            "(content, tier, confidence, created_at, source, branch_id, locked) "
            "VALUES (?, 6, 0.70, ?, ?, ?, 0)"
        )
        content = "consciousness emerges from belief field patterns"
        params = (content, 1234567890.0, "fountain_insight", "systems")
        wrapper.write(sql, params)

        inner.write.assert_called_once()
        call_sql, call_params = inner.write.call_args.args[0], inner.write.call_args.args[1]

        # 'tags' must be in the rewritten column list
        self.assertIn("tags", call_sql.lower())
        # Last param should be a JSON array of normalized tags
        tags_json = call_params[-1]
        tags = json.loads(tags_json)
        self.assertIsInstance(tags, list)
        self.assertGreater(len(tags), 0)
        # Content words should appear in the tags
        self.assertTrue(
            any(t in ("consciousness", "emerges", "belief", "field", "patterns") for t in tags),
            f"Expected content-derived tags, got: {tags}",
        )
        # Original params are preserved (content at index 0)
        self.assertEqual(call_params[0], content)

    def test_C3_passthrough_when_tags_already_present(self):
        wrapper, inner = self._make_wrapper()
        sql = (
            "INSERT INTO beliefs "
            "(content, tags, tier, confidence) "
            "VALUES (?, ?, ?, ?)"
        )
        params = ("some content", '["pre-tagged"]', 6, 0.70)
        wrapper.write(sql, params)

        inner.write.assert_called_once_with(sql, params)
        # Params unchanged — no double-tagging
        call_params = inner.write.call_args.args[1]
        self.assertEqual(call_params, params)


if __name__ == "__main__":
    unittest.main()
