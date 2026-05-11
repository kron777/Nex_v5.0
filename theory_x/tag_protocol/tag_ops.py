"""Tag Protocol operations — normalize, generate, CRUD, query, curation.

Spec: theory_x/TAG_PROTOCOL.md §2–§7.
All write paths flow through normalize(); no raw strings reach storage.
"""
from __future__ import annotations

import json
import re
import sys
from typing import Any, Optional

from theory_x.stage_throw_net.trigger_detector import _STOPWORDS

# ── Registry ──────────────────────────────────────────────────────────────────

TAGGABLE_TABLES: list[tuple[str, str]] = [
    ("beliefs", "beliefs"),           # (table_name, db_key)
    ("open_problems", "conversations"),
]

_TABLE_TO_DB_KEY: dict[str, str] = {t: k for t, k in TAGGABLE_TABLES}

# ── Constants ─────────────────────────────────────────────────────────────────

_HARD_TAG_LIMIT = 16
_DEFAULT_K = 8
_MAX_TAG_LEN = 40
_MIN_TOKEN_LEN = 3

_PUNCT_STRIP_RE = re.compile(r"[^a-z0-9-]")
_MULTI_HYPHEN_RE = re.compile(r"-+")
_WHITESPACE_RE = re.compile(r"\s+")
_TOKEN_EDGE_PUNCT = '.,?!;:\'"()[]{}—–'


# ── §6 Normalization ──────────────────────────────────────────────────────────

def normalize(tag: str) -> Optional[str]:
    """Apply §6 normalization rules in order. Returns None if rejected."""
    # Rule 1: lowercase
    t = tag.lower()
    # Rule 2: trim leading/trailing whitespace
    t = t.strip()
    # Rule 3: replace internal whitespace runs with a single hyphen
    t = _WHITESPACE_RE.sub("-", t)
    # Rule 4: strip non-alphanumeric except hyphens
    t = _PUNCT_STRIP_RE.sub("", t)
    # Rule 5: collapse consecutive hyphens
    t = _MULTI_HYPHEN_RE.sub("-", t)
    # Rule 6: strip leading and trailing hyphens
    t = t.strip("-")
    # Rule 7: reject if empty
    if not t:
        return None
    # Rule 8: reject if length < 2
    if len(t) < 2:
        return None
    # Rule 9: truncate to 40 chars (no rejection)
    return t[:_MAX_TAG_LEN]


# ── §4 Generation ─────────────────────────────────────────────────────────────

def generate(content: str, k: int = _DEFAULT_K) -> list[str]:
    """Extract and normalize tags from content text.

    Reuses _STOPWORDS from TriggerDetector (TN-1) per §0 doctrine.
    Returns at most k tags, ranked by frequency in content.
    """
    if not content:
        return []

    freq: dict[str, int] = {}
    for raw_token in content.lower().split():
        # Strip edge punctuation
        token = raw_token.strip(_TOKEN_EDGE_PUNCT)
        if not token:
            continue
        # Strip stopwords
        if token in _STOPWORDS:
            continue
        # Drop pure-numeric tokens
        if token.isdigit():
            continue
        # Drop tokens below minimum length
        if len(token) < _MIN_TOKEN_LEN:
            continue
        # Normalize
        norm = normalize(token)
        if norm is None:
            continue
        freq[norm] = freq.get(norm, 0) + 1

    # Sort by frequency descending, deduplicated by key already
    ranked = sorted(freq, key=lambda x: -freq[x])
    result = ranked[:k]

    # Hard limit guard — should never fire given soft cap
    if len(result) > _HARD_TAG_LIMIT:
        raise ValueError(
            f"generate() produced {len(result)} tags, exceeds hard limit {_HARD_TAG_LIMIT}"
        )

    return result


# ── §5 CRUD Operations ────────────────────────────────────────────────────────

def read(reader, table: str, entity_id: int) -> list[str]:
    """Return the tags list for one entity. Empty list on any failure."""
    try:
        row = reader.read_one(
            f"SELECT tags FROM {table} WHERE id = ?", (entity_id,)
        )
        if row is None:
            return []
        return json.loads(row["tags"] or "[]")
    except Exception:
        return []


def write(writer, table: str, entity_id: int, tags: list[str]) -> None:
    """Replace the tags array for one entity. Normalizes all input tags."""
    normalized = _normalize_list(tags)
    if len(normalized) > _HARD_TAG_LIMIT:
        raise ValueError(
            f"write() received {len(normalized)} tags, exceeds hard limit {_HARD_TAG_LIMIT}"
        )
    writer.write(
        f"UPDATE {table} SET tags = ? WHERE id = ?",
        (json.dumps(normalized), entity_id),
    )


def add(writer, reader, table: str, entity_id: int, tags: list[str]) -> None:
    """Append tags to an entity, deduplicating against existing tags."""
    current = read(reader, table, entity_id)
    current_set = set(current)
    new_normalized = _normalize_list(tags)
    merged = current + [t for t in new_normalized if t not in current_set]
    write(writer, table, entity_id, merged)


def remove(writer, reader, table: str, entity_id: int, tag: str) -> None:
    """Remove a tag from an entity. No-op if the tag is absent."""
    norm = normalize(tag)
    if norm is None:
        return
    current = read(reader, table, entity_id)
    updated = [t for t in current if t != norm]
    if updated != current:
        write(writer, table, entity_id, updated)


# ── §5 Cross-surface Operations ───────────────────────────────────────────────

def query(readers, tag: str, table: Optional[str] = None) -> list[dict]:
    """Find entities containing a tag.

    readers: dict[db_key, Reader] for cross-table (table=None),
             or a single Reader when table is specified.
    Returns list of row dicts with '_table' key added.
    """
    norm = normalize(tag)
    if norm is None:
        return []

    tables = [(table, _TABLE_TO_DB_KEY[table])] if table else TAGGABLE_TABLES
    results: list[dict] = []

    for tbl_name, db_key in tables:
        reader = readers[db_key] if isinstance(readers, dict) else readers
        try:
            rows = reader.read(
                f"SELECT * FROM {tbl_name} WHERE EXISTS ("
                f"SELECT 1 FROM json_each({tbl_name}.tags) WHERE value = ?)",
                (norm,),
            )
            for row in rows:
                d = dict(row)
                d["_table"] = tbl_name
                results.append(d)
        except Exception as exc:
            print(f"tag_protocol.query error on {tbl_name}: {exc}", file=sys.stderr)

    return results


def vocabulary(readers, table: Optional[str] = None) -> dict[str, int]:
    """Return distinct tags with occurrence counts, sorted by frequency descending.

    readers: dict[db_key, Reader] or single Reader.
    """
    tables = [(table, _TABLE_TO_DB_KEY[table])] if table else TAGGABLE_TABLES
    counts: dict[str, int] = {}

    for tbl_name, db_key in tables:
        reader = readers[db_key] if isinstance(readers, dict) else readers
        try:
            rows = reader.read(
                f"SELECT t.value AS tag, COUNT(*) AS cnt "
                f"FROM {tbl_name}, json_each({tbl_name}.tags) AS t "
                f"GROUP BY t.value"
            )
            for row in rows:
                tag = row["tag"] if hasattr(row, "__getitem__") else row[0]
                cnt = row["cnt"] if hasattr(row, "__getitem__") else row[1]
                counts[tag] = counts.get(tag, 0) + int(cnt)
        except Exception as exc:
            print(f"tag_protocol.vocabulary error on {tbl_name}: {exc}", file=sys.stderr)

    return dict(sorted(counts.items(), key=lambda x: -x[1]))


def merge(writers, readers, old_tag: str, new_tag: str) -> int:
    """Rename old_tag to new_tag across all taggable tables.

    writers/readers: dict[db_key, Writer/Reader].
    Returns total rows modified.
    """
    old_norm = normalize(old_tag)
    new_norm = normalize(new_tag)
    if old_norm is None or new_norm is None:
        return 0
    if old_norm == new_norm:
        return 0

    total = 0
    for tbl_name, db_key in TAGGABLE_TABLES:
        reader = readers[db_key]
        writer = writers[db_key]
        try:
            rows = reader.read(
                f"SELECT id, tags FROM {tbl_name} WHERE EXISTS ("
                f"SELECT 1 FROM json_each({tbl_name}.tags) WHERE value = ?)",
                (old_norm,),
            )
            for row in rows:
                entity_id = row["id"]
                current = json.loads(row["tags"] or "[]")
                updated = _dedupe([new_norm if t == old_norm else t for t in current])
                writer.write(
                    f"UPDATE {tbl_name} SET tags = ? WHERE id = ?",
                    (json.dumps(updated), entity_id),
                )
                total += 1
        except Exception as exc:
            print(f"tag_protocol.merge error on {tbl_name}: {exc}", file=sys.stderr)

    return total


def near_duplicates(readers, threshold: int = 2) -> list[tuple[str, str]]:
    """Return pairs of tags within Levenshtein distance <= threshold."""
    vocab = vocabulary(readers)
    tags = list(vocab.keys())
    pairs: list[tuple[str, str]] = []

    for i in range(len(tags)):
        for j in range(i + 1, len(tags)):
            if _levenshtein(tags[i], tags[j]) <= threshold:
                pairs.append((tags[i], tags[j]))

    return pairs


# ── Internals ─────────────────────────────────────────────────────────────────

def _normalize_list(tags: list[str]) -> list[str]:
    """Normalize a list of tags, drop rejected, deduplicate preserving order."""
    seen: set[str] = set()
    result: list[str] = []
    for t in tags:
        norm = normalize(t)
        if norm is not None and norm not in seen:
            seen.add(norm)
            result.append(norm)
    return result


def _dedupe(tags: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for t in tags:
        if t not in seen:
            seen.add(t)
            result.append(t)
    return result


def _levenshtein(s1: str, s2: str) -> int:
    """Pure-Python Levenshtein distance."""
    if s1 == s2:
        return 0
    if len(s1) < len(s2):
        s1, s2 = s2, s1
    if not s2:
        return len(s1)
    prev = list(range(len(s2) + 1))
    for c1 in s1:
        curr = [prev[0] + 1]
        for j, c2 in enumerate(s2):
            cost = 0 if c1 == c2 else 1
            curr.append(min(curr[j] + 1, prev[j + 1] + 1, prev[j] + cost))
        prev = curr
    return prev[-1]
