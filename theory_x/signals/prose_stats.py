"""Corpus-derived entity discrimination.

Closes the open-ended tail of the single-word confabulation problem
(Large/You/Adaptive/Informed/Cross/Without/Anchoring...). Rather than
maintaining ever-growing word-lists, this asks the corpus a question the
lists can never answer: does this token ever appear capitalized in ordinary
prose, or only inside title-cased headlines?

A proper noun (Postgres, Beijing, Anthropic) is capitalized mid-sentence by
human writers. An adjective (Large, Adaptive) never is -- it only wears a
capital inside a headline, where every content word is capitalized.

Measured on the live store: every offender scores 0-2 prose capitalizations;
every real entity scores 9+. Floor of 3 separates them with headroom.

LIMITATION: unigram stats cannot represent multi-word entities. "World Cup"
shreds into "world"/"cup", both scoring high as fragments. Harmless because
multi-word entities short-circuit as substantive before this check runs.
"""
from __future__ import annotations

import re
import time
import logging

logger = logging.getLogger("theory_x.signals.prose_stats")

# Minimum mid-sentence prose capitalizations for a single-word entity to be
# considered real. Offenders score 0-2; Postgres/Beijing/Stripe score 8-9.
PROSE_CAP_FLOOR = 3

# Stats older than this are stale; the gate then skips the check (fail-safe).
STALE_SECONDS = 7 * 24 * 3600

# A token is mid-sentence only if preceded by a lowercase word (or comma /
# semicolon / colon) plus whitespace. Positive evidence of position -- cannot
# be fooled by newlines, quote-closers, or multiple spaces the way an
# exclusionary lookbehind can.
# NOTE: colon and semicolon are deliberately EXCLUDED. ": How" and "; The"
# are sentence-starts wearing a disguise -- headline subtitle structure
# ("AlphaEvolve: How our agent works", "NYT and vaping: How to lie").
# Including them inflated how=48, why=31, bitcoin=96 (JSON feed dumps like
# "picking this from crypto.coingecko: {...}"). With ':' removed: how=0,
# why=1, bitcoin=25 -- and every real entity is unchanged (boeing=5,
# postgres=9, beijing=9, stripe=9, altman=9).
_MID_SENTENCE = re.compile(r"(?<=[a-z,]\s)([A-Za-z]{3,})\b")
_WORD = re.compile(r"\b[A-Za-z]{2,}\b")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS token_prose_stats (
    token       TEXT PRIMARY KEY,
    prose_cap   INTEGER NOT NULL DEFAULT 0,
    prose_lower INTEGER NOT NULL DEFAULT 0,
    updated_at  REAL    NOT NULL
)
"""


def _is_title_case(text: str) -> bool:
    """True if >50% of words are capitalized -- i.e. a headline, not prose."""
    words = _WORD.findall(text)
    if len(words) < 3:
        return False
    caps = sum(1 for w in words if w[0].isupper())
    return caps / len(words) > 0.5


def build(beliefs_writer, beliefs_reader, source: str = "precipitated_from_sense") -> int:
    """Rebuild token_prose_stats from the world-contact belief corpus.

    Returns the number of distinct tokens recorded. Measured at ~0.1s over
    21k beliefs, so no incremental logic is warranted.
    """
    from collections import Counter

    try:
        beliefs_writer.write(_SCHEMA)
    except Exception as exc:
        logger.warning("prose_stats schema error: %s", exc)
        return 0

    try:
        rows = beliefs_reader.read(
            "SELECT content FROM beliefs WHERE source = ?", (source,)
        )
    except Exception as exc:
        logger.warning("prose_stats read error: %s", exc)
        return 0

    cap: Counter = Counter()
    low: Counter = Counter()
    for r in rows:
        text = (r["content"] or "").replace("\n", " ")
        if _is_title_case(text):
            continue
        for m in _MID_SENTENCE.finditer(text):
            w = m.group(1)
            (cap if w[0].isupper() else low)[w.lower()] += 1

    now = time.time()
    tokens = set(cap) | set(low)
    written = 0
    for tok in tokens:
        try:
            beliefs_writer.write(
                "INSERT INTO token_prose_stats (token, prose_cap, prose_lower, updated_at) "
                "VALUES (?,?,?,?) ON CONFLICT(token) DO UPDATE SET "
                "prose_cap=excluded.prose_cap, prose_lower=excluded.prose_lower, "
                "updated_at=excluded.updated_at",
                (tok, cap.get(tok, 0), low.get(tok, 0), now),
            )
            written += 1
        except Exception:
            pass

    logger.info("prose_stats rebuilt: %d tokens from %d beliefs", written, len(rows))
    return written


def prose_cap_count(cx, token: str) -> int | None:
    """Mid-sentence prose capitalizations for token, via an open connection.

    Takes the caller's existing sqlite3.Connection (the tick already holds
    one on BELIEFS_DB) rather than opening its own -- no contention, no
    timeout under live write load.

    Returns None when stats are missing, empty, or stale. Callers MUST then
    SKIP the check rather than reject, so an absent table can never blind
    the system to real entities.
    """
    try:
        row = cx.execute(
            "SELECT prose_cap, updated_at FROM token_prose_stats WHERE token=?",
            (token.lower(),),
        ).fetchone()
    except Exception:
        return None  # table absent -> skip check
    if row is not None:
        if time.time() - (row["updated_at"] or 0) > STALE_SECONDS:
            return None
        return int(row["prose_cap"] or 0)
    try:
        any_row = cx.execute(
            "SELECT updated_at FROM token_prose_stats LIMIT 1"
        ).fetchone()
    except Exception:
        return None
    if any_row is None:
        return None  # empty table -> skip check
    if time.time() - (any_row["updated_at"] or 0) > STALE_SECONDS:
        return None
    return 0  # populated, fresh, token genuinely never seen in prose


def build_direct(db_path) -> int:
    """Rebuild using a plain connection. For callers without Writer/Reader."""
    import sqlite3
    from collections import Counter
    try:
        cx = sqlite3.connect(str(db_path), timeout=15)
        cx.row_factory = sqlite3.Row
    except Exception as exc:
        logger.warning("prose_stats connect failed: %s", exc)
        return 0
    try:
        cx.execute(_SCHEMA)
        rows = cx.execute(
            "SELECT content FROM beliefs WHERE source='precipitated_from_sense'"
        ).fetchall()
        cap: Counter = Counter()
        low: Counter = Counter()
        for r in rows:
            text = (r["content"] or "").replace("\n", " ")
            if _is_title_case(text):
                continue
            for m in _MID_SENTENCE.finditer(text):
                w = m.group(1)
                (cap if w[0].isupper() else low)[w.lower()] += 1
        now = time.time()
        payload = [
            (t, cap.get(t, 0), low.get(t, 0), now)
            for t in (set(cap) | set(low))
        ]
        cx.executemany(
            "INSERT INTO token_prose_stats (token, prose_cap, prose_lower, updated_at) "
            "VALUES (?,?,?,?) ON CONFLICT(token) DO UPDATE SET "
            "prose_cap=excluded.prose_cap, prose_lower=excluded.prose_lower, "
            "updated_at=excluded.updated_at",
            payload,
        )
        cx.commit()
        logger.info("prose_stats rebuilt: %d tokens from %d beliefs",
                    len(payload), len(rows))
        return len(payload)
    except Exception as exc:
        logger.warning("prose_stats build_direct error: %s", exc)
        return 0
    finally:
        try: cx.close()
        except Exception: pass
