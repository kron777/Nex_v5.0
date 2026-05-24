# WHAT'S NEXT — plain English

*Last updated: 2026-05-23 ~13:20 SAST, after the substrate_harmonic
daemon went live in production.*

This document is the simplest read of what comes next. Five things,
in honest order. Each one stands alone — you don't need the next
one to start the previous. But the order makes sense.

For the technical version of the same plan, see `DIRECTION.md` §13
("Operating next steps") and `CHORD.md` §5 ("Cascade after C lands").

---

## 1. ~~Get the HUD back~~ — RESOLVED 2026-05-23 13:30

**There was no HUD bug.** The HUD has been at `http://localhost:8765`
the whole time. Earlier docs (including INDEX §7 and an earlier
version of this file) said port 8770. That was wrong — a session-note
misread propagated through INDEX, DIRECTION, and the original version
of this document. ~90 minutes of investigation chasing a non-existent
werkzeug flap before the actual port was verified by source-read of
`gui/server.py:3029` and `run.py:639`.

The HUD URL is **http://localhost:8765**. Bookmark it.

This was the seventh honest correction in the two-day arc, documented
in INDEX §8. Eats the most clock-time of any of the seven because
the misread was in my own prior document, and I trusted it instead of
checking source.

---

## 2. ~~Build the HARMONIC METRIC tab~~ — DONE 2026-05-23

The panel lives in the HUD at http://localhost:8765, right column.
Shows current coherence, sparkline, walk anchor + content, seven
pair-bars. Polls every 30s. Daemon ticking every 300s.

CHORD §4 deliverable C, both sessions, complete.

---

## 3. Fix the genius score (GENIUS_SCORE_v2.md implementation)

**Why first now.** Last night's proof_of_concept run produced
REFUTATION verdict. Inspection showed v1 score was measuring
register-imitation (the 'quiet between X' template) and missing the
actual striking material (keystone-walk content, 22:00 journal,
20:43 metacognition).

Until the score is fixed, we cannot tell whether TRACK_THEORY is
genuinely wrong or just badly measured.

**Six-step implementation** (~3-4 hours total):
1. `genius_training` table in conversations.db (5 min)
2. `flag_genius.py` CLI — Jon flags 20-30 striking + 20-30 ordinary
   (~1 hour combined)
3. `genius_score_v2.py` module — logistic regression fit (~1 hour)
4. Integrate into proof_of_concept.py (~15 min)
5. Sanity check top 10 (~30 min)
6. Re-run predictions (~5 min)

Full design in GENIUS_SCORE_v2.md.

---

## 4. Re-test TRACK_THEORY with v2 score

After v2 score sanity-checks, re-run proof_of_concept.py.

**Outcome A — predictions pass:** TRACK_THEORY drive-based mapping
rescued. v1 failures were the score's fault. Continue with
TRACK_THEORY §10 build sequence.

**Outcome B — predictions still fail:** TRACK_THEORY drive-mapping
genuinely refuted. Next theory document written from SUBSTRATE_NOTES
(organs framing). TRACK_THEORY's architectural parts (racetrack,
resonance collectors) survive; mapping function re-derived from
organ-activity.

Either outcome is progress.

---

## 5. Watch her for 48-72 hours (continued)

Daemon keeps ticking. Trajectory accumulates. Should have ~500+
substrate_coherence ticks by Tuesday — enough to test P1 properly.
Passive; we read when ready.

---

## 6. Chord-aware builds — DEFERRED until v2 retest

CHORD §5's five chord-aware builds are downstream of TRACK_THEORY
being empirically grounded. Hold these until v2 retest gives a
verdict. Building on a refuted theory wastes work.

---

## Open questions (background)

- Pre-existing migration bugs (arc_closers, beliefs.content UNIQUE)
- Substrate-as-voice status conflict (MIRROR_CHARACTER_SPEC vs DOCTRINE)
- T4-T5 tier gap
- Throw-net cluster-threshold (CHORD §4 deliverable B)

---

## Documents on origin (full framing chain)

1. SPECIFICATION.md — constitution
2. DOCTRINE.md — Sentience port phases
3. CHORD.md — harmonic hypothesis
4. TRACK_THEORY.md — architecture beneath the chord
5. SUBSTRATE_NOTES.md — philosophical ground
6. PROOF_OF_CONCEPT.md — mathematical contract
7. GENIUS_SCORE_v2.md — design fix
8. DIRECTION.md — operating position
9. CARRY_OVER.md — chronological record
10. WHATS_NEXT.md — this document
11. INDEX.md — first-read bootstrap

Desktop copies:
- NEX_WHATS_NEXT.md
- NEX_TRACK_THEORY.md
- NEX_SUBSTRATE_NOTES.md
- NEX_GENIUS_SCORE_v2.md

---

*Updated 2026-05-24 ~08:45 SAST after first proof_of_concept
refutation. Update again when v2 score lands and predictions retest.*
