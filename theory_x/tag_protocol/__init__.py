"""Tag Protocol — comprehensive auto-tagging across NEX's cognition substrate.

Spec: theory_x/TAG_PROTOCOL.md (commit eff2497).
One vocabulary across all surfaces: beliefs, open_problems, and future surfaces.
"""
from theory_x.tag_protocol.tag_ops import (
    TAGGABLE_TABLES,
    normalize,
    generate,
    read,
    write,
    add,
    remove,
    query,
    vocabulary,
    merge,
    near_duplicates,
)

__all__ = [
    "TAGGABLE_TABLES",
    "normalize",
    "generate",
    "read",
    "write",
    "add",
    "remove",
    "query",
    "vocabulary",
    "merge",
    "near_duplicates",
]
