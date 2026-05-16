"""Idempotent loader for outward spectrum beliefs.

Reads substrate/seed/outward_spectrum.txt and inserts each belief
into beliefs.db as source='spectrum' matching the existing schema.

Idempotent: skips beliefs whose content already exists (relies on
the UNIQUE indexes on beliefs.content).

Usage: python3 substrate/seed/load_spectrum.py
"""
import sqlite3
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DB = REPO / "data" / "beliefs.db"
SEED = Path(__file__).parent / "outward_spectrum.txt"


def parse_seed():
    if not SEED.exists():
        print(f"ERROR: seed file missing at {SEED}", file=sys.stderr)
        sys.exit(1)
    beliefs = []
    for line in SEED.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        beliefs.append(line)
    return beliefs


def load():
    if not DB.exists():
        print(f"ERROR: beliefs.db missing at {DB} — run substrate init first", file=sys.stderr)
        sys.exit(1)

    beliefs = parse_seed()
    print(f"parsed {len(beliefs)} beliefs from seed file")

    cx = sqlite3.connect(DB, timeout=30)
    cx.row_factory = sqlite3.Row
    sample = cx.execute(
        "SELECT tier, confidence, branch_id, tags FROM beliefs "
        "WHERE source='spectrum' LIMIT 1"
    ).fetchone()
    if not sample:
        print("ERROR: no existing spectrum entries found — schema may not be initialized")
        sys.exit(1)

    tier = sample["tier"]
    confidence = sample["confidence"]
    branch_id = sample["branch_id"]
    tags = sample["tags"]
    print(f"matching schema: tier={tier} confidence={confidence} branch_id={branch_id}")

    inserted = 0
    skipped = 0
    now = int(time.time())
    for content in beliefs:
        try:
            cx.execute(
                "INSERT INTO beliefs "
                "(content, tier, confidence, created_at, source, branch_id, tags) "
                "VALUES (?, ?, ?, ?, 'spectrum', ?, ?)",
                (content, tier, confidence, now, branch_id, tags)
            )
            cx.commit()
            inserted += 1
        except sqlite3.IntegrityError:
            skipped += 1

    cx.close()
    print(f"\ninserted: {inserted}")
    print(f"skipped (already exist): {skipped}")


if __name__ == "__main__":
    load()
