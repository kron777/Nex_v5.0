"""TaggingBeliefWriter — wraps a beliefs Writer to auto-inject tags on INSERT.

Intercepts explicit-column-list INSERT [OR IGNORE] INTO beliefs statements,
extracts the content value, generates tags via tag_protocol.generate(), and
appends the tags column+value to the statement.

Pass-through (unchanged + stderr log) when:
- Not an INSERT INTO beliefs
- Column list already contains 'tags' (caller set it)
- No explicit column list (positional INSERT)
- 'content' not in the column list
- Parsing fails for any reason

INSERTs that arrive from non-cognition paths (seed scripts, admin tools) that
use positional form or lack 'content' are logged once per occurrence so the
count is visible for follow-up.
"""
from __future__ import annotations

import json
import re
import sys
from typing import Any, Sequence

from theory_x.tag_protocol.tag_ops import generate

# Matches any INSERT [OR IGNORE] INTO beliefs statement
_INSERT_BELIEFS_RE = re.compile(
    r"INSERT\s+(?:OR\s+IGNORE\s+)?INTO\s+beliefs\b",
    re.IGNORECASE,
)

# Matches explicit-column-list form and captures (col_list, val_list)
_COL_LIST_RE = re.compile(
    r"INSERT\s+(?:OR\s+IGNORE\s+)?INTO\s+beliefs\s*"
    r"\(\s*([^)]+?)\s*\)\s*VALUES\s*\(\s*([^)]+?)\s*\)",
    re.IGNORECASE | re.DOTALL,
)


def _parse_insert(sql: str) -> tuple[list[str], list[str]] | None:
    """Extract (col_names, val_tokens) from a beliefs INSERT, or None."""
    m = _COL_LIST_RE.search(sql)
    if not m:
        return None
    col_names = [c.strip().lower() for c in m.group(1).split(",")]
    val_tokens = [v.strip() for v in m.group(2).split(",")]
    if len(col_names) != len(val_tokens):
        return None
    return col_names, val_tokens


def _content_param_index(col_names: list[str], val_tokens: list[str]) -> int | None:
    """Return the params[] index for the 'content' column, or None."""
    if "content" not in col_names:
        return None
    col_idx = col_names.index("content")
    param_count = 0
    for i, tok in enumerate(val_tokens):
        if i == col_idx:
            return param_count if tok == "?" else None
        if tok == "?":
            param_count += 1
    return None


def _inject_tags_into_sql(
    sql: str, params: tuple, content: str
) -> tuple[str, tuple]:
    """Rewrite sql+params to append 'tags' column and its JSON value."""
    m = _COL_LIST_RE.search(sql)
    if not m:
        return sql, params

    try:
        tags_json = json.dumps(generate(content))
    except Exception as exc:
        print(f"TaggingBeliefWriter: generate() failed: {exc}", file=sys.stderr)
        tags_json = "[]"

    # m.end(1) = position right after the column list content
    # m.end(2) = position right after the VALUES content
    # Inserting at these positions appends to each list without disturbing
    # the surrounding parentheses or whitespace.
    new_sql = (
        sql[: m.end(1)]
        + ", tags"
        + sql[m.end(1) : m.end(2)]
        + ", ?"
        + sql[m.end(2) :]
    )
    return new_sql, tuple(params) + (tags_json,)


class TaggingBeliefWriter:
    """Wraps a beliefs Writer to auto-generate tags on INSERT.

    Drop-in replacement at the writers["beliefs"] slot in run.py /
    gui/server.py. All other Writer API methods are delegated unchanged.
    """

    def __init__(self, inner_writer) -> None:
        self._inner = inner_writer
        self.db_path = inner_writer.db_path
        self.name = getattr(inner_writer, "name", "beliefs")

    def write(self, sql: str, params: Sequence[Any] = ()) -> Any:
        params = tuple(params)

        # 1 — only intercept INSERT INTO beliefs
        if not _INSERT_BELIEFS_RE.search(sql):
            return self._inner.write(sql, params)

        # 2 — parse the column list
        parsed = _parse_insert(sql)
        if parsed is None:
            print(
                f"TaggingBeliefWriter: no explicit col list, pass-through: "
                f"{sql[:100]!r}",
                file=sys.stderr,
            )
            return self._inner.write(sql, params)

        col_names, val_tokens = parsed

        # 3 — skip if caller already provided tags
        if "tags" in col_names:
            return self._inner.write(sql, params)

        # 4 — locate content in params
        content_idx = _content_param_index(col_names, val_tokens)
        if content_idx is None or content_idx >= len(params):
            print(
                f"TaggingBeliefWriter: content not extractable, pass-through: "
                f"{sql[:100]!r}",
                file=sys.stderr,
            )
            return self._inner.write(sql, params)

        # 5 — rewrite SQL+params with injected tags
        new_sql, new_params = _inject_tags_into_sql(
            sql, params, str(params[content_idx])
        )
        return self._inner.write(new_sql, new_params)

    def write_many(self, statements) -> list[Any]:
        return self._inner.write_many(statements)

    def queue_depth(self) -> int:
        return self._inner.queue_depth()

    def close(self) -> None:
        self._inner.close()

    def start(self) -> None:
        self._inner.start()
