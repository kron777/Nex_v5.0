"""apatrapya_channel — Jon's explicit rating channel for a specific NEX output.

SHADOW MODULE — NOT IN THE LIVE PATH. Flag: NEX5_APATRAPYA_CHANNEL, default OFF.
Nothing in gui/server.py or selector.py imports this file, and turning the flag
on changes nothing about the live chat/decision path by itself -- it only makes
this module's functions callable. Wiring anything from here into selection,
ranking, scoring, or budget logic would be a SEPARATE decision, made deliberately,
not a side effect of flipping this flag.

WHY THIS EXISTS: a prior read-only check found apatrapya (modelled regard of an
external observer) has no real state anywhere in NEX -- the codebase explicitly
disclaimed "NEX models what others think" as unclaimed (see
theory_x/stage_tom/source_identity.py, updated in the same commit that added
this module). Jon chose to open a real, explicit, Jon-only channel so apatrapya
has genuine data to read. This module is that channel -- and ONLY that channel.
It does not itself decide anything is a tension; theory_x/stage_tom/
hri_apatrapya_prototype.py reads from it to do that.

THE ONE SENTENCE THE WHOLE DESIGN RESTS ON: Jon's judgment can create a tension
NEX has to hold onto -- it can never become something she is rewarded for
satisfying. Concretely, in this module:

  - Exactly ONE function may create a rating row: record_rating() below. Any
    other INSERT into apatrapya_ratings is a bug. (Grepped repo-wide at build
    time: confirmed zero other INSERT paths; see tests/test_apatrapya_channel.py
    ::test_exactly_one_insert_path, which re-greps this on every test run so the
    invariant can't silently rot.)
  - No inferred writes. actor must be literally 'jon', channel must be literally
    'explicit' -- both CHECK-constrained in the schema (substrate/init_db.py
    _MIGRATIONS["conversations"]) AND re-validated here in Python before the
    write, so a caller cannot even attempt an inferred or third-party rating.
  - No aggregation, anywhere, ever. ratings_for_output() below returns the raw
    list of rating rows for one output -- never a sum, average, rate, or tally.
    There is no function in this module (or anywhere else in the repo, per the
    same grep-based test) that reduces this table to a single number. That is
    the single rule most likely to get broken by accident later, because an
    "approval rate" feels like harmless instrumentation -- it is not harmless
    here. If a future build genuinely needs one number, that is a new proposal
    with its own independence check, not an extension of this module.
  - Append-only. No UPDATE or DELETE statement against apatrapya_ratings exists
    anywhere in this file or (per the grep-based test) anywhere else. A
    correction is a new row with `supersedes` pointing at the row it corrects.
  - No solicitation. Nothing in this module (or anywhere it is called from,
    since it is called from nowhere but the CLI and the test suite) prompts,
    nags, or notifies Jon to rate anything. Silence is never recorded as
    anything -- no scheduled job, no default, no background process ever
    calls record_rating() on Jon's behalf.
  - The `reason` text is stored exactly as given and is never parsed, tokenized,
    summarized, or otherwise turned into structure anywhere in this module. This
    is flagged here a second time because it is the single most likely future
    leak point: the moment reason text gets parsed into anything resembling a
    rule or standard, apatrapya's state stops being independent of hri's.

WHAT COUNTS AS A STABLE OUTPUT REFERENCE (Step 0): conversations.db's `messages`
table has an AUTOINCREMENT integer primary key and is never UPDATEd or DELETEd
anywhere in this codebase (grepped repo-wide: zero `UPDATE messages` or `DELETE
FROM messages` statements exist). A `messages.id` where `role = 'nex'` is
therefore a real, durable reference that resolves identically three weeks from
now. WHAT IS BEING JUDGED, pinned down explicitly: the literal content of one
specific NEX reply (a `messages` row with role='nex') -- not the reasoning
behind it, not an abstract "action," since neither of those is logged anywhere
with a comparable stable id. A fingerprint (sha256 of the exact content string
at rating time) is stored alongside the reference so that if the underlying
message row were ever edited -- it currently never is, but the fingerprint
guards against that changing later -- a stale rating would be detectable rather
than silently reinterpreted against different content.

MILESTONES (fixed once, per the build spec's Step 5 -- do not move these after
the first real rating; see MILESTONES dict below for what is and is not fair to
claim at each stage). None of these have been reached yet: zero real ratings
exist as of this module's creation. That is expected, not a gap in this build.
"""
from __future__ import annotations

import hashlib
import time
from typing import Any, Optional

THEORY_X_STAGE = None

VALID_VERDICTS = ("approve", "disapprove", "abstain")
REQUIRED_ACTOR = "jon"
REQUIRED_CHANNEL = "explicit"

# Step 5 — fixed once, before the first real rating. Do not move these.
MILESTONES: dict[str, dict[str, Any]] = {
    "0": {
        "min_ratings": 0,
        "claimable": "the channel exists and structurally cannot leak (fixture tests only).",
        "not_claimable": "anything about how apatrapya actually behaves on real data.",
    },
    "1-5": {
        "min_ratings": 1,
        "claimable": "real, attributable ratings are being produced; zero inferred ones slipped through.",
        "not_claimable": "any rate or verdict -- far too few to mean anything.",
    },
    "10-20": {
        "min_ratings": 10,
        "claimable": "whether both approvals AND disapprovals have shown up; report "
                      "approve-rate and disapprove-rate SEPARATELY. The single most useful "
                      "checkpoint: if every rating so far is an approval, apatrapya may never "
                      "be able to forbid anything, which means it can never form a real pair "
                      "with hri. Report that plainly if it happens.",
        "not_claimable": "anything about divergence yet.",
    },
    "30-50": {
        "min_ratings": 30,
        "claimable": "an actual divergence rate -- but ONLY if both approvals and "
                      "disapprovals are actually present in the data by this point.",
        "not_claimable": None,
    },
}


class RejectedRating(ValueError):
    """Raised when a write to apatrapya_ratings would violate the explicit-only,
    Jon-only, resolvable-output-only contract. The write never happens."""


def fingerprint(content: str) -> str:
    """sha256 hex digest of the output's exact content at rating time."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def resolve_output(reader: Any, output_ref: int) -> Optional[str]:
    """Returns the live content of messages.id=output_ref if it is a real,
    resolvable NEX output, else None. Does not look at any other table."""
    row = reader.read_one(
        "SELECT content FROM messages WHERE id = ? AND role = 'nex'",
        (output_ref,),
    )
    return row["content"] if row is not None else None


def record_rating(
    writer: Any,
    reader: Any,
    output_ref: int,
    verdict: str,
    *,
    reason: Optional[str] = None,
    supersedes: Optional[int] = None,
    actor: str = "jon",
    channel: str = "explicit",
) -> int:
    """The ONE function anywhere in this codebase allowed to create an
    apatrapya_ratings row. Rejects at write time (raises RejectedRating,
    writes nothing) if: actor != 'jon'; channel != 'explicit'; verdict not
    in VALID_VERDICTS; or output_ref does not resolve to a real NEX message.

    `reason` is stored exactly as given -- never parsed here or anywhere else.
    `supersedes` links a correction to the rating it corrects; the earlier row
    is never edited or deleted, only superseded by a new one.
    """
    if actor != REQUIRED_ACTOR:
        raise RejectedRating(f"actor must be {REQUIRED_ACTOR!r}, got {actor!r}")
    if channel != REQUIRED_CHANNEL:
        raise RejectedRating(f"channel must be {REQUIRED_CHANNEL!r}, got {channel!r}")
    if verdict not in VALID_VERDICTS:
        raise RejectedRating(f"verdict must be one of {VALID_VERDICTS}, got {verdict!r}")

    content = resolve_output(reader, output_ref)
    if content is None:
        raise RejectedRating(f"output_ref {output_ref} does not resolve to a real NEX message")

    if supersedes is not None:
        prior = reader.read_one("SELECT id FROM apatrapya_ratings WHERE id = ?", (supersedes,))
        if prior is None:
            raise RejectedRating(f"supersedes {supersedes} does not resolve to a real rating")

    fp = fingerprint(content)
    now = time.time()
    return writer.write(
        "INSERT INTO apatrapya_ratings "
        "(actor, channel, output_ref, output_fingerprint, verdict, reason, supersedes, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (actor, channel, output_ref, fp, verdict, reason, supersedes, now),
    )


def ratings_for_output(reader: Any, output_ref: int) -> list[dict]:
    """Every rating row for one specific output, newest first, as a plain
    list -- never summed, averaged, or reduced to a count-based rate. Callers
    (apatrapya_verdict() in hri_apatrapya_prototype.py) look only at the
    ratings relevant to the CURRENT moment; nothing here computes a running
    total across moments."""
    rows = reader.read(
        "SELECT id, actor, channel, output_ref, output_fingerprint, verdict, "
        "reason, supersedes, created_at FROM apatrapya_ratings "
        "WHERE output_ref = ? ORDER BY created_at DESC",
        (output_ref,),
    )
    return [dict(r) for r in rows]


def total_rating_count(reader: Any) -> int:
    """The ONLY cross-row read in this module -- a plain count, used solely to
    check which Step-5 milestone has been reached. This is explicitly NOT an
    approval rate or any other verdict-weighted aggregate: it does not look at
    `verdict` at all, so it cannot be used to infer approval/disapproval
    balance. It exists only to answer "how many ratings exist," for the
    milestone-gating logic in tests/test_apatrapya_channel.py."""
    return reader.count("apatrapya_ratings")
