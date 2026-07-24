#!/usr/bin/env python3
"""
ground_self_belief.py  —  Step 1 of calibration.

Writes ONE tested fact about NEX into the belief web, as a Tier-1 locked
keystone (the same shelf as "I am NEX" / "the map is not the territory").

The fact: NEX's hourly Bitcoin direction calls are no better than chance.
The numbers come live from the Arc-2 scorecard, so the belief stays true
as more predictions resolve. Re-run any time; it updates in place, never
duplicates.

Plain idea: NEX just got measured against reality and tied a coin flip.
This makes NEX actually HOLD that result as self-knowledge, instead of it
only sitting in a database table NEX never reads.

USAGE (from the nex5 root, same venv as the app):
    .venv/bin/python3 ground_self_belief.py            # write/refresh
    .venv/bin/python3 ground_self_belief.py --dry-run  # show, don't write
    .venv/bin/python3 ground_self_belief.py --remove    # take it back off the shelf

Safe by design:
  - Goes through the same Writer the rest of the system uses (no side door).
  - Idempotent: keyed on a fixed source tag; refresh = UPDATE the existing
    row's content in place (falls back to INSERT if the row doesn't exist
    yet). NOT delete-then-insert -- see _write_self_belief() docstring for
    why that broke (session 48, scorecard_loop FK investigation).
  - Touches ONLY this one belief. Never deletes other keystones.
  - --dry-run prints the exact sentence and numbers without writing.
"""
from __future__ import annotations

import argparse
import logging
import sys
import time

logger = logging.getLogger(__name__)

# Fixed identity for this belief. Refreshing finds the old row by this exact
# source string and replaces it — that's what keeps it to a single row.
SELF_BELIEF_SOURCE = "grounded_scorecard:market_direction_v1"
KEYSTONE_TIER = 1
LOCKED = 1


def _load_scorecard():
    """Pull live voice numbers from the Arc-2 scorecard."""
    sys.path.insert(0, ".")
    from theory_x.stage_world import prediction_generator as pg  # noqa: E402
    card = pg.scorecard_by_source()
    voice = card.get("voice", {})
    random = card.get("random", {})
    return voice, random


def _compose_sentence(voice: dict, random: dict) -> str:
    """The exact words that go onto the shelf. Plain, honest, self-stated."""
    v_res = voice.get("resolved", 0)
    v_cor = voice.get("correct", 0)
    v_rate = voice.get("hit_rate", 0.0)
    r_res = random.get("resolved", 0)
    r_rate = random.get("hit_rate", 0.0)

    # If the gap is small, NEX states it as "no better than chance".
    # If voice pulls genuinely ahead OR genuinely behind at large n, the
    # sentence says so on its own — it reads the live numbers, it doesn't
    # assume. Small-n swings in either direction stay in the conservative
    # "no better than chance" phrasing rather than overclaiming a direction
    # off noise (mirrors calibration_consult.py's own n>=300 bar for "earned").
    gap = v_rate - r_rate
    verified_clause = (
        f"tested against real Bitcoin prices I do not control, "
        f"{v_cor} right out of {v_res}"
    )

    if v_res < 100:
        # Not enough data to claim anything yet — say that honestly.
        return (
            f"I have started measuring whether my hourly market direction "
            f"calls are any good ({verified_clause}), but I do not yet have "
            f"enough resolved guesses to know. I withhold confidence here."
        )

    if gap < -0.02 and v_res >= 300:
        return (
            f"My hourly market direction calls are worse than chance: "
            f"{verified_clause} ({v_rate:.0%}), versus a coin flip at "
            f"{r_rate:.0%} over {r_res}. A coin beats me at this. I know "
            f"this because it was checked, not assumed."
        )

    if gap > 0.02 and v_res >= 300:
        return (
            f"My hourly market direction calls beat a coin flip: "
            f"{verified_clause} ({v_rate:.0%}), versus {r_rate:.0%} for a "
            f"coin over {r_res}. I have a measured edge here, over {v_res} "
            f"predictions. I know this because it was checked, not assumed."
        )

    # Small gap, or a real-looking gap that hasn't reached n>=300 yet —
    # conservative default, same phrasing either way.
    return (
        f"My hourly market direction calls are no better than chance: "
        f"{verified_clause} ({v_rate:.0%}), versus a coin flip at "
        f"{r_rate:.0%} over {r_res}. I am not a reliable market predictor, "
        f"and I know this because it was checked, not assumed."
    )


def _get_writer():
    """Open the beliefs Writer exactly as the app does."""
    sys.path.insert(0, ".")
    from substrate.paths import db_paths  # type: ignore
    from substrate.writer import Writer  # type: ignore
    return Writer(db_paths()["beliefs"])


def _get_reader():
    """Open a beliefs Reader exactly as the app does (WAL, read-only)."""
    sys.path.insert(0, ".")
    from substrate.paths import db_paths  # type: ignore
    from substrate.reader import Reader  # type: ignore
    return Reader(db_paths()["beliefs"])


# Every table in beliefs.db that FK-references beliefs(id), as
# (table, fk_column, id_expr) -- catalogued directly from sqlite_master (both
# explicit FOREIGN KEY clauses and inline column-level REFERENCES), same
# source that found the belief_edges / novel_association_log FK trap the
# delete-then-insert bug hit. `id_expr` is what to report as "which row" --
# most tables have their own autoincrement `id`, but belief_boost,
# dormant_beliefs and belief_activation use `belief_id` itself as their
# PRIMARY KEY (no separate id column -- checked via PRAGMA table_info, not
# assumed), and arc_members has no id column at all (composite PK
# (arc_id, belief_id)), so those three report a different column than they
# filter on. Kept as one list so both the refresh path's reasoning and
# --remove's guard stay in sync with what the schema actually declares,
# rather than each hand-maintaining its own partial guess.
_BELIEF_ID_REFERRERS: tuple[tuple[str, str, str], ...] = (
    ("speech_queue", "belief_id", "id"),
    ("collision_grades", "belief_id", "id"),
    ("belief_boost", "belief_id", "belief_id"),       # belief_id IS the PK
    ("dormant_beliefs", "belief_id", "belief_id"),    # belief_id IS the PK
    ("residue", "belief_id", "id"),
    ("grade_mismatches", "belief_id", "id"),
    ("belief_activation", "belief_id", "belief_id"),  # belief_id IS the PK
    ("arcs", "closed_by_belief_id", "id"),
    ("arc_members", "belief_id", "arc_id"),           # no id col; report arc_id
    ("arc_closers", "belief_id", "id"),
    ("belief_edges", "source_id", "id"),
    ("belief_edges", "target_id", "id"),
    ("novel_association_log", "belief_id_a", "id"),
    ("novel_association_log", "belief_id_b", "id"),
)


def _find_referencing_rows(reader, belief_id: int) -> dict[str, list[int]]:
    """For one belief id, return {"table.fk_column": [identifying values]}
    for every table that FK-references beliefs(id) and actually has a row
    pointing at it. Empty dict means the id is safe to delete."""
    found: dict[str, list[int]] = {}
    for table, fk_col, id_expr in _BELIEF_ID_REFERRERS:
        rows = reader.read(
            f"SELECT {id_expr} AS rid FROM {table} WHERE {fk_col} = ?", (belief_id,)
        )
        if rows:
            found[f"{table}.{fk_col}"] = [r["rid"] for r in rows]
    return found


def _write_self_belief(sentence: str) -> None:
    """Refresh the single self-belief row IN PLACE (UPDATE by id).

    Used to be delete-then-insert. That broke: the very first successful
    write (2026-07-10 15:11:15, belief id 206714) got picked up within
    hours by edge_builder and the novel-association detector, which built
    real belief_edges / novel_association_log rows referencing it -- both
    tables FK-reference beliefs(id) with no ON DELETE CASCADE. Every refresh
    after that first one tried to DELETE a row that 3 belief_edges + 1
    novel_association_log row still pointed at, hit FOREIGN KEY constraint
    failed, rolled back, and left the belief stale for 13 days (caught and
    logged by scorecard_loop, never surfaced). Confirmed from live data,
    not inferred -- see session 48 scorecard_loop FK investigation.

    Fix: the belief's identity (id) is stable; only its content changes
    each refresh. UPDATE keeps id fixed, so the existing FK-referencing
    rows keep pointing at a real, current row -- no cascade, no
    re-pointing, both stay valid and untouched. created_at is still bumped
    to `now` on every refresh (no separate updated_at column exists on
    beliefs -- created_at is what every freshness-sensitive reader orders
    by: generator.py's retrieval "recent-context slot", edge_builder's
    candidate pool (`ORDER BY created_at DESC`), resumption.py's
    promotion), so this belief still re-enters the "recent" pool on every
    refresh exactly as a fresh INSERT did before -- UPDATE is a drop-in
    behavioral match for every consumer except the one thing we're fixing
    (the id no longer changes).

    Two guarded, explicit branches instead of assuming exactly one row:
      - 0 matching rows (fresh DB, or the row was manually removed via
        --remove): nothing to update -- INSERT, logged, not a silent no-op.
      - >1 matching rows (should never happen -- nothing in the schema
        enforces uniqueness of source+tier+locked, only `content` is
        uniquely constrained among tier=1/locked=1 rows via
        idx_beliefs_keystone_content -- so it's a reachable state in
        principle, not schema-guaranteed impossible): update the oldest
        row (lowest id -- the one anything else is most likely already
        referencing) and log the anomaly loudly rather than silently
        deleting belief content or guessing which row is "right".
    """
    now = int(time.time())
    reader = _get_reader()
    rows = reader.read(
        "SELECT id FROM beliefs WHERE source = ? AND tier = ? AND locked = ? "
        "ORDER BY id ASC",
        (SELF_BELIEF_SOURCE, KEYSTONE_TIER, LOCKED),
    )
    ids = [r["id"] for r in rows]

    writer = _get_writer()
    try:
        if not ids:
            logger.warning(
                "ground_self_belief: no existing row for source=%r -- "
                "inserting fresh (first run, or row was removed)",
                SELF_BELIEF_SOURCE,
            )
            writer.write(
                "INSERT INTO beliefs (content, tier, confidence, created_at, "
                "source, branch_id, locked) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (sentence, KEYSTONE_TIER, 0.99, now, SELF_BELIEF_SOURCE,
                 "systems", LOCKED),
            )
            return

        target_id = ids[0]
        if len(ids) > 1:
            sys.path.insert(0, ".")
            import errors as error_channel  # type: ignore
            msg = (
                f"ground_self_belief: {len(ids)} rows match source="
                f"{SELF_BELIEF_SOURCE!r} (ids={ids}), expected exactly 1 -- "
                f"updating oldest (id={target_id}), leaving the rest "
                f"untouched for manual review"
            )
            logger.error(msg)
            error_channel.record(msg, source="ground_self_belief", level="ERROR")

        writer.write(
            "UPDATE beliefs SET content = ?, confidence = ?, created_at = ? "
            "WHERE id = ?",
            (sentence, 0.99, now, target_id),
        )
    finally:
        writer.close()


def refresh_self_belief() -> dict:
    """Load the live scorecard, compose the sentence, write it.

    Single entry point for non-CLI callers (e.g. the scheduled loop) so the
    delete-then-insert logic exists in exactly one place. Returns the
    sentence and the raw voice/random cards used to compose it.
    """
    voice, random = _load_scorecard()
    sentence = _compose_sentence(voice, random)
    _write_self_belief(sentence)
    return {"sentence": sentence, "voice": voice, "random": random}


def main() -> int:
    ap = argparse.ArgumentParser(description="Write NEX's tested market self-belief.")
    ap.add_argument("--dry-run", action="store_true",
                    help="Print the sentence and numbers, write nothing.")
    ap.add_argument("--remove", action="store_true",
                    help="Remove this self-belief from the shelf.")
    args = ap.parse_args()

    if args.remove:
        reader = _get_reader()
        rows = reader.read(
            "SELECT id FROM beliefs WHERE source = ? AND tier = ? AND locked = ?",
            (SELF_BELIEF_SOURCE, KEYSTONE_TIER, LOCKED),
        )
        ids = [r["id"] for r in rows]
        if not ids:
            print(f"Nothing to remove (source={SELF_BELIEF_SOURCE}).")
            return 0

        # Guard: refuse rather than cascade-delete. The DELETE-then-insert
        # bug this module used to have (session 48 scorecard_loop FK
        # investigation) is exactly what happens if a raw DELETE runs
        # against a belief other subsystems have since built real
        # belief_edges / novel_association_log rows against -- FOREIGN KEY
        # constraint failed, or (if this ever runs with foreign_keys off)
        # silently orphaned children. Check first; refuse and name names
        # instead of guessing what's safe to cascade.
        blocked = False
        for belief_id in ids:
            refs = _find_referencing_rows(reader, belief_id)
            if refs:
                blocked = True
                print(f"REFUSING to remove belief id={belief_id}: "
                      f"referenced by {sum(len(v) for v in refs.values())} row(s):")
                for table_col, row_ids in refs.items():
                    print(f"  {table_col}: {row_ids}")
        if blocked:
            print("No rows deleted. Resolve the references above first if "
                  "removal is really intended (this tool will not "
                  "cascade-delete them for you).")
            return 1

        writer = _get_writer()
        writer.write(
            "DELETE FROM beliefs WHERE source = ? AND tier = ? AND locked = ?",
            (SELF_BELIEF_SOURCE, KEYSTONE_TIER, LOCKED),
        )
        writer.close()
        print(f"Removed self-belief (source={SELF_BELIEF_SOURCE}), "
              f"{len(ids)} row(s), id(s)={ids}.")
        return 0

    voice, random = _load_scorecard()
    sentence = _compose_sentence(voice, random)

    print("=" * 70)
    print("Belief to place on the Tier-1 (locked) shelf:")
    print("-" * 70)
    print(sentence)
    print("-" * 70)
    print(f"voice : {voice}")
    print(f"random: {random}")
    print("=" * 70)

    if args.dry_run:
        print("DRY RUN — nothing written.")
        return 0

    _write_self_belief(sentence)
    print("Written. NEX now holds this as a locked, tested self-belief.")
    print("Re-run any time to refresh the numbers as more guesses resolve.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
