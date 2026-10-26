"""Schema invariants — fire-path indexes (H2) and no duplicate tables (M3)."""
import tempfile
import unittest
from pathlib import Path

from tests import _bootstrap  # noqa: F401

from substrate import connect

_SCHEMA = Path(__file__).resolve().parent.parent / "substrate" / "schema"


class TestFirePathIndexes(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.conn = connect(str(Path(self._tmp.name) / "beliefs.db"))
        self.conn.executescript((_SCHEMA / "beliefs.sql").read_text())

    def tearDown(self):
        self.conn.close()
        self._tmp.cleanup()

    def test_fire_path_indexes_present(self):
        idx = {r[1] for r in self.conn.execute("PRAGMA index_list(beliefs)")}
        self.assertIn("idx_beliefs_created_at", idx)
        self.assertIn("idx_beliefs_source_created", idx)

    def test_recency_order_served_by_index(self):
        # The recency pool orders by created_at DESC with a LIMIT; with the
        # index that must not fall back to a transient sort.
        for i in range(200):
            self.conn.execute(
                "INSERT INTO beliefs (content, tier, confidence, created_at, source) "
                "VALUES (?, 2, 0.5, ?, 'fountain')",
                (f"b{i}", i),
            )
        plan = " ".join(
            str(r[-1])
            for r in self.conn.execute(
                "EXPLAIN QUERY PLAN "
                "SELECT id FROM beliefs ORDER BY created_at DESC LIMIT 50"
            )
        )
        self.assertIn("idx_beliefs_created_at", plan)
        self.assertNotIn("TEMP B-TREE FOR ORDER BY", plan.upper())


class TestAffinityColumns(unittest.TestCase):
    """D-A: affinity columns are registered as migrations, additive, nullable.

    Also pins the fresh-init fix: affinity / affinity_updated_at were read and
    written by affinity_loop but created in no schema or migration, so a fresh
    beliefs table lacked them and affinity_tick raised 'no such column'.
    """

    _AFFINITY_COLS = ("affinity", "affinity_updated_at",
                      "affinity_model", "affinity_legacy")

    def _affinity_alters(self):
        from substrate.init_db import _MIGRATIONS
        return [s for s in _MIGRATIONS["beliefs"]
                if "ADD COLUMN affinity" in s]

    def test_columns_registered_in_migrations(self):
        alters = " ".join(self._affinity_alters())
        for col in self._AFFINITY_COLS:
            self.assertIn(f"ADD COLUMN {col} ", alters + " ")

    def test_columns_created_nullable_and_query_works(self):
        with tempfile.TemporaryDirectory() as tmp:
            conn = connect(str(Path(tmp) / "beliefs.db"))
            try:
                conn.executescript((_SCHEMA / "beliefs.sql").read_text())
                for stmt in self._affinity_alters():
                    conn.execute(stmt)
                cols = {r[1]: r for r in conn.execute("PRAGMA table_info(beliefs)")}
                for col in self._AFFINITY_COLS:
                    self.assertIn(col, cols)
                    self.assertEqual(cols[col][3], 0, f"{col} should be nullable")
                # The affinity_loop SELECT must not raise 'no such column' now.
                conn.execute(
                    "SELECT id, affinity, affinity_updated_at, affinity_model, "
                    "affinity_legacy FROM beliefs "
                    "WHERE affinity IS NULL OR affinity_updated_at < ?", (0,)
                ).fetchall()
            finally:
                conn.close()

    def test_affinity_loop_real_queries_run_on_migrated_db(self):
        """Generalise the drift fix: build a beliefs DB via the real migration
        list and run affinity_loop's actual SELECT and UPDATE. A column that any
        schema/migration forgot surfaces here, not on the next fresh deploy."""
        from substrate.init_db import _MIGRATIONS
        from theory_x.life import affinity_loop
        with tempfile.TemporaryDirectory() as tmp:
            conn = connect(str(Path(tmp) / "beliefs.db"))
            try:
                conn.executescript((_SCHEMA / "beliefs.sql").read_text())
                for stmt in _MIGRATIONS["beliefs"]:
                    try:
                        conn.execute(stmt)
                    except Exception:
                        pass  # CREATE IF NOT EXISTS / duplicate ALTER — idempotent
                conn.commit()
                # The candidate SELECT reads every affinity-path column.
                affinity_loop._pick_candidates(conn, 5)          # must not raise
                # The write path's columns must exist too.
                conn.execute("UPDATE beliefs SET affinity=?, affinity_updated_at=? "
                             "WHERE id=?", (0.5, 0.0, -1))
            finally:
                conn.close()


class TestBeliefsInsertColumnsExist(unittest.TestCase):
    """Generalise the affinity drift fix: every column named in any static
    `INSERT INTO beliefs (...)` across the codebase must exist in the migrated
    beliefs table. Two columns drifted once; this closes the class for inserts."""

    def _migrated_columns(self):
        from substrate.init_db import _MIGRATIONS
        with tempfile.TemporaryDirectory() as tmp:
            conn = connect(str(Path(tmp) / "beliefs.db"))
            try:
                conn.executescript((_SCHEMA / "beliefs.sql").read_text())
                for stmt in _MIGRATIONS["beliefs"]:
                    try:
                        conn.execute(stmt)
                    except Exception:
                        pass
                return {r[1] for r in conn.execute("PRAGMA table_info(beliefs)")}
            finally:
                conn.close()

    def test_insert_columns_are_a_subset_of_schema(self):
        import re
        root = Path(__file__).resolve().parent.parent
        pat = re.compile(r"INSERT\s+INTO\s+beliefs\s*\(([^)]*)\)",
                         re.IGNORECASE | re.DOTALL)
        ident = re.compile(r"^[a-z_][a-z0-9_]*$")
        referenced = {}
        for py in root.rglob("*.py"):
            s = str(py)
            if "/tests/" in s or py.name.startswith("test_"):
                continue
            text = py.read_text(errors="ignore")
            if "INSERT INTO beliefs" not in text:
                continue
            stripped = text.replace('"', "").replace("'", "")
            for m in pat.finditer(stripped):
                collist = m.group(1)
                if "{" in collist or "%" in collist:
                    continue  # dynamically-built column list — can't check statically
                for tok in collist.split(","):
                    c = tok.strip()
                    if ident.match(c):
                        referenced.setdefault(c, str(py.relative_to(root)))
        self.assertTrue(referenced, "found no INSERT INTO beliefs column lists")
        # Allow-list is empty: the drift this test first surfaced is resolved --
        # parent_belief_id and variant_index were added to the migration, and the
        # updated_at INSERT (a no-such-column bug) was fixed in probe_runner. Any
        # entry appearing here now is fresh drift and must fail.
        known_drift: set = set()
        cols = self._migrated_columns()
        missing = {c: w for c, w in referenced.items()
                   if c not in cols and c not in known_drift}
        self.assertEqual(missing, {},
                         f"columns used in INSERT but absent from schema: {missing}")


class TestDynamicSchemaNoDupes(unittest.TestCase):
    def test_substrate_snapshots_single_definition(self):
        with tempfile.TemporaryDirectory() as tmp:
            conn = connect(str(Path(tmp) / "dynamic.db"))
            try:
                conn.executescript((_SCHEMA / "dynamic.sql").read_text())
                n = conn.execute(
                    "SELECT COUNT(*) FROM sqlite_master "
                    "WHERE type='table' AND name='substrate_snapshots'"
                ).fetchone()[0]
                self.assertEqual(n, 1)
            finally:
                conn.close()


class TestFreshInitLazyTables(unittest.TestCase):
    """Fresh-store boot: tables/columns that live code writes but that existed
    only in the long-lived production DB. A boot against an empty data dir
    logged 'no such table' for each of these; init_all() must now create them
    in the database their producer actually writes to."""

    def test_init_all_creates_them_where_producers_write(self):
        import os
        from unittest import mock
        from substrate.init_db import init_all
        from substrate.paths import db_paths
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.dict(os.environ, {"NEX5_DATA_DIR": tmp}):
            init_all()
            paths = db_paths()
            # The producers' own statements, verbatim shapes.
            writes = {
                "beliefs": [(
                    "INSERT INTO intake_resonance_log "
                    "(content, resonance, top_match_belief_id, ts) "
                    "VALUES (?, ?, ?, ?)", ("x", 0.5, None, 1.0))],
                "conversations": [(
                    "INSERT OR REPLACE INTO drives_competing "
                    "(id, coherence, exploration, integration, "
                    " self_preservation, curiosity, tension_pairs, computed_at) "
                    "VALUES (1, ?, ?, ?, ?, ?, ?, ?)",
                    (0.2, 0.2, 0.2, 0.2, 0.2, "[]", 1.0)), (
                    "INSERT INTO drives_competing_log "
                    "(tick_at, weights_json, inputs_json, tension_active) "
                    "VALUES (?, ?, ?, ?)", (1.0, "{}", "{}", 0))],
                "dynamic": [(
                    "INSERT OR IGNORE INTO daily_activities "
                    "(activity, date_local, fired_at, details) VALUES (?, ?, ?, ?)",
                    ("walk", "2026-10-26", 1.0, "")), (
                    "INSERT OR IGNORE INTO daily_activities "
                    "(activity, date_local, fired_at, details) VALUES (?, ?, ?, ?)",
                    ("walk", "2026-10-26", 2.0, "dup"))],
            }
            for db, stmts in writes.items():
                conn = connect(str(paths[db]))
                try:
                    for sql, params in stmts:
                        conn.execute(sql, params)
                    conn.commit()
                finally:
                    conn.close()
            conn = connect(str(paths["dynamic"]))
            try:
                # once-per-day: the duplicate (activity, date_local) is ignored
                self.assertEqual(conn.execute(
                    "SELECT COUNT(*) FROM daily_activities").fetchone()[0], 1)
                # decoder_loop's read of the coincidence tag
                conn.execute("SELECT id, ts, thought, hot_branch, tag "
                             "FROM fountain_events").fetchall()
            finally:
                conn.close()


class TestEveryReferencedTableExistsOnFreshInit(unittest.TestCase):
    """Generalise the fresh-init fix to the whole class: every table named by a
    SQL statement in live code must exist after init_all() on an empty data dir,
    or be created lazily by some module (CREATE TABLE IF NOT EXISTS). A dozen
    tables once existed only in the long-lived production DB; a fresh store
    then failed their writes silently. This turns the next one red in CI."""

    # Tables whose schema is owned by an integration not wired into run.py.
    # stage7_moltbook (external social posting, dry-run by default) creates
    # its own store when launched; its readers elsewhere fail soft.
    _NOT_BOOTED = {"moltbook_dms", "moltbook_pending_replies",
                   "moltbook_post_queue", "moltbook_posts"}

    def test_referenced_tables_exist_or_have_a_lazy_creator(self):
        import ast
        import os
        import re
        from unittest import mock
        from substrate.init_db import init_all
        from substrate.paths import db_paths

        # SQL in this codebase is upper-case; matching the verb case-sensitively
        # keeps docstrings ("Update the ...") out.
        sql_start = re.compile(r"^\s*(SELECT|INSERT|UPDATE|DELETE|WITH|REPLACE)\b")
        ref = re.compile(
            r"\b(?:INSERT(?:\s+OR\s+\w+)?\s+INTO\s+([a-z_]\w*)\s*\("
            r"|UPDATE(?:\s+OR\s+\w+)?\s+([a-z_]\w*)\s+SET\b"
            r"|FROM\s+([a-z_]\w*)(?![\w.(])"
            r"|JOIN\s+([a-z_]\w*)(?![\w.(]))", re.I)
        cte = re.compile(r"\b([a-z_]\w*)\s+AS\s*\(", re.I)
        create = re.compile(r"CREATE\s+(?:VIRTUAL\s+)?TABLE\s+"
                            r"(?:IF\s+NOT\s+EXISTS\s+)?([a-z_]\w*)", re.I)

        def literals(tree):
            for n in ast.walk(tree):
                if isinstance(n, ast.Constant) and isinstance(n.value, str):
                    yield n.value
                elif isinstance(n, ast.JoinedStr):
                    # an interpolated {table} is dynamic -- leave a non-identifier
                    yield "".join(v.value if isinstance(v, ast.Constant) else "{}"
                                  for v in n.values)

        root = Path(__file__).resolve().parent.parent
        referenced, lazy = {}, set()
        for py in root.rglob("*.py"):
            s = str(py)
            if any(k in s for k in ("/.venv/", "/venv/", "/tests/", "/archive/")) \
                    or py.name.startswith("test_"):
                continue
            try:
                tree = ast.parse(py.read_text(errors="ignore"))
            except SyntaxError:
                continue
            for lit in literals(tree):
                lazy.update(m.lower() for m in create.findall(lit))
                if not sql_start.match(lit):
                    continue
                ctes = {c.lower() for c in cte.findall(lit)}
                for m in ref.finditer(lit):
                    name = next(g for g in m.groups() if g).lower()
                    if name not in ctes:
                        referenced.setdefault(name, str(py.relative_to(root)))
        self.assertTrue(referenced, "found no SQL table references")

        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.dict(os.environ, {"NEX5_DATA_DIR": tmp}):
            init_all()
            created = set()
            for path in db_paths().values():
                conn = connect(str(path))
                try:
                    created.update(r[0].lower() for r in conn.execute(
                        "SELECT name FROM sqlite_master "
                        "WHERE type IN ('table', 'view')"))
                finally:
                    conn.close()

        missing = {t: where for t, where in referenced.items()
                   if t not in created and t not in lazy
                   and not t.startswith("sqlite_")  # SQLite's own catalogue
                   and t not in self._NOT_BOOTED}
        self.assertEqual(missing, {},
                         f"tables used in SQL but created nowhere: {missing}")


if __name__ == "__main__":
    unittest.main()
