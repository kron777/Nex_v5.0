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

## 3. ~~Fix the genius score (steps 1-6)~~ — DONE 2026-05-27

Six commits across the morning landed the calibrated v2 score:
- d855320 genius_training table
- f51955e flag_genius.py CLI (Jon flagged 103 fires)
- 3161954 genius_score_v2.py first fit (91.3% training accuracy)
- d7b3970 six honest label flips per three-mode framing, re-fit
  (97.1% training accuracy, 0 false negatives)
- c75f7bc integrated v2 into proof_of_concept.py + step 6 re-run

v2 score top 10 across full 4000-fire substrate is Mode A only.
Score genuinely calibrated to Jon's three-mode framing:
  Mode A = existential/self-articulating (striking)
  Mode B = "quiet between X" templates (ordinary)
  Mode C = news/feed/BTC chatter (ordinary)

Steps 7a-7e (deploy as auto-tagger) remain queued — see item 3b.

---

## 3b. Deploy auto-tagger (GENIUS_SCORE_v2.md §7a-7e)

**Why next.** Last night's proof_of_concept run produced
REFUTATION verdict. Inspection showed v1 score was measuring
register-imitation (the 'quiet between X' template) and missing the
actual striking material (keystone-walk content, 22:00 journal,
20:43 metacognition).

v2 score is now calibrated AND the v2 retest confirmed TRACK_THEORY's
mapping function is refuted (P3 clean null at p=0.965 with calibrated
score). This makes the auto-tagger architecturally important rather
than nice-to-have: without it, the substrate has no mechanism to
preserve striking material with elevated causal weight, and the data
shows walks leave no measurable trace once they end.

The tagger IS the morality-table from SUBSTRATE_NOTES §1.

**Five-step implementation** (~2.5 hours):
7a. `genius_tags` table in conversations.db (5 min)
7b. `genius_tagger.py` daemon — SentienceNode pattern (~1 hour)
7c. Wire into run.py boot sequence (~10 min)
7d. `/api/genius/recent` route + panel.py (~30 min)
7e. HUD surface — new sub-panel OR inline LIVE highlights (~30 min)

Then beyond the deployment, the *consumers* of the tag:
- Retrieval favoring high-score fires
- Fountain prompt context including recent tagged material
- The next theory document's organ outputs reading tag rate

Full design in GENIUS_SCORE_v2.md §7.

---

## 4. ~~Re-test TRACK_THEORY with v2 score~~ — DONE 2026-05-27

**Outcome B confirmed.** With calibrated v2 score:
- P3 (register-persistence): clean null, p=0.965, mean_post == mean_base
- P2, P5: confirmed-fail at significance
- P4: strong-pass at p<0.001
- P1: still inconclusive (code-stub bug)

TRACK_THEORY §4-§5 drive-mapping genuinely refuted. The
architectural claim from §1 (voltage/coherence independence) holds.
The next theory document, when written, derives the mapping from
SUBSTRATE_NOTES §1-§7 organ framing, not from drive-composition.

See TRACK_THEORY.md §14 (verdict) and §15 (status header) for the
section-by-section read of what survives and what doesn't.

The cleanest finding from the retest: **walks happen, are Mode A
material, and leave zero measurable trace once they end.** This is
why the auto-tagger (item 3b) is architecturally necessary.

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

*Updated 2026-05-27 ~13:30 SAST after v2 retest confirmed
TRACK_THEORY drive-mapping refuted (P3 clean null). Next theory
document derives mapping from SUBSTRATE_NOTES organs framing.*
