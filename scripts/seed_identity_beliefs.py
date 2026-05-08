"""Seed identity beliefs from seeds/identity.yaml into beliefs.db.

Usage (from nex5 root):
    .venv/bin/python scripts/seed_identity_beliefs.py [--dry-run] [--verbose]

Schema:
    tier=1, source='identity', locked=1, confidence=1.0, branch_id='systems'

Idempotent: beliefs.db has a UNIQUE INDEX on (content) WHERE tier=1 AND locked=1.
INSERT OR IGNORE means re-running is safe — existing claims are not touched.

Integration:
    SelfModel._get_inside_beliefs() classifies source='identity' as INSIDE via
    stage4_membrane/classifier.py _INSIDE_SOURCES set. Claims surface in
    belief_text for self-inquiry queries (router._inside_route).
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# Resolve nex5 root and add to sys.path so substrate imports work
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

_SEEDS_FILE = _ROOT / "seeds" / "identity.yaml"


def _load_claims(path: Path) -> list[str]:
    """Parse identity.yaml and return list of claim strings."""
    try:
        import yaml
    except ImportError:
        print("ERROR: pyyaml not found. Run: pip install pyyaml", file=sys.stderr)
        sys.exit(1)

    if not path.exists():
        print(f"ERROR: seeds file not found: {path}", file=sys.stderr)
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    if not isinstance(data, dict) or "beliefs" not in data:
        print(f"ERROR: expected 'beliefs' key in {path}", file=sys.stderr)
        sys.exit(1)

    raw = data["beliefs"]
    if raw is None:
        return []

    claims = [str(c).strip() for c in raw if c is not None and str(c).strip()]
    return claims


def seed_identity_beliefs(
    *,
    dry_run: bool = False,
    verbose: bool = False,
) -> int:
    """Seed identity claims. Returns count of INSERT attempts."""
    from substrate import Writer, db_paths

    claims = _load_claims(_SEEDS_FILE)

    if not claims:
        print("No claims found in seeds/identity.yaml — nothing to seed.")
        print("Add claims under the 'beliefs:' key and re-run.")
        return 0

    try:
        display_path = _SEEDS_FILE.relative_to(_ROOT)
    except ValueError:
        display_path = _SEEDS_FILE
    print(f"Found {len(claims)} claim(s) in {display_path}")

    if dry_run:
        print("\n[dry-run] Would insert:")
        for i, claim in enumerate(claims, 1):
            print(f"  {i:2d}. {claim[:100]}{'...' if len(claim) > 100 else ''}")
        return len(claims)

    paths = db_paths()
    writer = Writer(paths["beliefs"], name="seed_identity")
    now = time.time()
    inserted = 0
    skipped = 0

    for claim in claims:
        try:
            writer.write(
                "INSERT OR IGNORE INTO beliefs "
                "(content, tier, confidence, created_at, source, branch_id, locked) "
                "VALUES (?, 1, 1.0, ?, 'identity', 'systems', 1)",
                (claim, now),
            )
            inserted += 1
            if verbose:
                print(f"  [+] {claim[:100]}{'...' if len(claim) > 100 else ''}")
        except Exception as exc:
            skipped += 1
            print(f"  [!] SKIP (error): {exc} — {claim[:60]}", file=sys.stderr)

    try:
        writer.close()
    except Exception:
        pass

    # Report actual rows now in DB (INSERT OR IGNORE means inserted >= actual new rows)
    from substrate import Reader
    reader = Reader(paths["beliefs"])
    try:
        row = reader.read_one(
            "SELECT COUNT(*) AS n FROM beliefs WHERE source='identity' AND tier=1 AND locked=1"
        )
        total_in_db = row["n"] if row else 0
    except Exception:
        total_in_db = "unknown"

    print(f"\nDone. Attempted: {inserted} | Errors: {skipped} | "
          f"Total identity beliefs in DB: {total_in_db}")
    return inserted


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed identity beliefs from seeds/identity.yaml into beliefs.db"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print claims that would be seeded without writing to DB",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Print each claim as it is inserted",
    )
    args = parser.parse_args()
    seed_identity_beliefs(dry_run=args.dry_run, verbose=args.verbose)


if __name__ == "__main__":
    main()
