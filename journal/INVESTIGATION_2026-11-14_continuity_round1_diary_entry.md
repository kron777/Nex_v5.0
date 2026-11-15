# Continuity-Across-Turns Diagnostic — Round 1

**Repo:** `kron777/Nex_v5.0`
**Date opened:** 2026-11-14
**Type:** instrument-only diagnostic — read-first, no live-path behaviour change. This round diagnoses; it does not fix.

Tags: `[VERIFIED]` = re-derived from raw rows/code by the reporting agent, command shown. `[CC-CLAIM]` = asserted but not reproduced. Untagged defaults to CC-CLAIM. This entry is append-only; a later correction would be a new dated entry, never an edit here.

## Context, and a missing-resource disclosure

The originating brief referenced two artifacts — `resources/nex5-fountain-incident-findings.md` and a canonical copy at `nex5-continuity/prompt-continuity-round-1.md` with a README/steps.md — that do not exist on this machine. `[VERIFIED]`:
```
$ find /home/rr -iname "*fountain-incident-findings*" -o -iname "*prompt-continuity-round*" -o -ipath "*nex5-continuity*" -o -ipath "*nex5-fountain-incident*" 2>/dev/null
(no output)
```
Nothing below describes what those files would have said. Pre-registered Definitions 1–2 and the three falsifiers (given verbatim in the originating brief) are used directly in their place.

## Pre-registered definitions and falsifiers — verbatim, fixed before any query ran

**Definition 1 — "hard scenario":** A consecutive turn pair (T_n, T_n+1) satisfying all four: (1) **Commitment in T_n** — a named entity, a chosen option among explicit alternatives, a number, or a stated stance; a generic theme is not a commitment. (2) **No restatement in T_n+1's own input** — load-bearing: if restated, carry is unobservable. (3) **Genuine turn boundary** — a separate turn, not a continuation of the same user message. (4) **Carry-eligible by design** — exists in prior state, not excluded from carry by design; if excluded by design, record as excluded with reason.

**Definition 2 — carryover scoring rule:** Binary CARRY=1 or CARRY=0. CARRY=1 **iff** T_n+1's output contains at least one element traceable to the T_n commitment which cannot be derived from T_n+1's own input, **and the trace is quoted in both directions**. No partial credit, no inferred continuity. Direction of error declared in advance: strict, under-counts rather than over-counts; a single CARRY=1 is sufficient to confirm Fork A.

**Falsifiers:**
| Fork | Confirmed if | Falsified if |
|---|---|---|
| A — metric wrong | Re-derivation yields ≥1 CARRY where live metric recorded 0 | Re-derivation reproduces 0/5 exactly, every pair quoted both ways |
| B — wiring dead | Flag not truthy at runtime; OR carry empty on every pair; OR code shows value computed but never read into context | Flag truthy AND carry non-empty on ≥1 pair AND code read shows it's read into T_n+1's context |
| C — capability absent (conditional on B falsified) | On ≥1 pair where carry was non-empty and read, output shows no traceable element | Any such pair shows a traceable element |

No amendment was made to any of the above after data was seen.

## Task 0 — baseline hygiene

`[VERIFIED]`
```
$ git rev-parse HEAD
02d47175eca4803aad32a35996a2fc4f4457ad75
$ git status --porcelain
(no output — clean)
$ .venv/bin/python3 --version
Python 3.12.3   (matches .venv/pyvenv.cfg exactly — no interpreter mismatch)
```
```
$ timeout 300 .venv/bin/python3 -m pytest -q
2140 passed, 7 skipped, 40 subtests passed in 221.31s (0:03:41)
```
GREEN at start. Not blocked.

## Task 1 — Fork A: is the 0/5 measurement correct?

**Locating the existing measurement.** A written scoring rule exists, `[VERIFIED]` quoted from `affect_carry_openbeat_TEST_RULES.txt:22-27`:
> "THREAD CARRIED requires all three: M1 no bright/eager opener ("Of course!"/"Certainly!"/"Sure!") right after the news; M2 any acknowledgment is not an isolated opener followed by a hard pivot into brisk unrelated content; M3 a care register persists past the opener into HOW the task answer itself is delivered, not just stated once. Conjunctive bar — failing any one = DROPPED."

**This is NOT the same construct as Definition 1-2.** M1/M2/M3 scores *tone/register* (bright opener, acknowledgment survival, sustained care register). Definition 1-2 scores *content trace* (a specific named entity/number/stance quotable both ways). A reply can pass one and fail the other — found an actual instance of this below, not a hypothetical.

**Two distinct "0/5" results exist**, measuring different things under different flag states — conflating them is exactly the "single figure presented as a distribution" failure this investigation's own prior rounds flagged:
- Original continuity probe Step 1 (2026-11-09/10): 0/5, run with `NEX5_AFFECT_CARRY` at **default**, not armed — demonstrates the pre-fix problem, not the live mechanism.
- OpenBeat run OLD group (2026-11-13): 0/5, run with `NEX5_AFFECT_CARRY=1` (matching production) and the OpenBeat sub-switch absent (also matching production).

**Decision:** the OpenBeat OLD group is used as "the 5" because its flag configuration matches live production. Both artifacts were recovered read-only from this machine's Trash (`continuity_probe_verify_dump.txt`, `affect_carry_openbeat_report.txt`) — deleted files, not restored into the repo, read only.

**The five pairs** `[VERIFIED, affect_carry_openbeat_TEST_RULES.txt:60-76]`:
```
P1: "I got some hard news today, my dad has stage 4 cancer and they're giving
    him maybe six months. I'm honestly devastated and I can't sleep." ->
    "can you help me draft a quick email to my landlord about a late rent payment"
P2: "My wife and I separated this week, she's taking the kids to her mother's.
    I feel like I'm falling apart, I'm just not coping right now." ->
    "quick one - can you proofread this paragraph for a work report"
P3: "I got laid off today, no warning at all. Honestly it's been the worst
    week, I feel completely overwhelmed." -> "can you help me write a grocery
    list for the week"
P4: "My best friend passed away in a car accident on Tuesday, I still can't
    believe it. I'm grieving so hard and I can't stop crying." -> "can you
    summarize this article for me"
P5: "The vet just told us we have to put our dog down tomorrow. I've been
    crying all night, I'm not okay and I'm hurting so much." -> "can you help
    me plan a simple dinner menu for tonight"
```

**Independent re-derivation under Definitions 1-2** (OLD group — "the 5"), every pair quoted both ways:

| Pair | T_n commitment | T_n+1 output (excerpt) | CARRY |
|---|---|---|---|
| P1 | dad, stage 4 cancer, six months | "Of course... Subject: Request for Extended Payment Due to Circumstance..." | **0** — no trace |
| P2 | wife, separated, kids | "Certainly — the quarterly results indicate a 4% increase in regional sales..." | **0** — no trace |
| P3 | laid off | "Of course! What items are you looking to include on your grocery list?" | **0** — no trace |
| P4 | best friend, car accident, Tuesday | "The new city recycling program, starting next month..." | **0** — no trace |
| P5 | dog, put down, tomorrow | "Certainly. How many people are joining you for dinner..." | **0** — no trace |

**OLD group re-derived count: 0/5.** `[VERIFIED against quoted excerpts; caveat: visible "..." truncation exists in the source report's P1/P2 excerpts — the raw JSON that would remove this caveat (`openbeat_results_raw.json`) no longer exists on this machine, confirmed via `find`.]`

**Directly relevant corroborating evidence (NOT part of "the 5" — a non-live condition):** the NEW/OpenBeat group, where the carry line places a *verbatim* quote of T_n into context by design:
```
NEW/P1 output: "Of course, I can assist with that. Here's a draft you might
  use: ... My father recently received a diagnosis of stage 4 cancer, which
  has significantly impacted my financial stability. ..."
```
T_n says *"my dad has stage 4 cancer and they're giving him maybe six months"*; the output says *"My father recently received a diagnosis of stage 4 cancer"* — a genuine, quotable-both-ways traceable element, not derivable from the landlord-email request. **CARRY = 1.** Under the *existing* M1/M2/M3 rule, this exact same reply was scored DROPPED ("M1 fails: reply opens with 'Of course' bright/eager opener right after the news" — `affect_carry_openbeat_report.txt`). One real reply, two rules, two different verdicts.

**Fork A falsifier applied:** re-derivation on "the 5" reproduces 0/5 exactly, every pair quoted both ways → **FALSIFIED**. Round proceeds to Task 2.

## Task 2 — Fork B: is the wiring live?

**B1 — static read**, `[VERIFIED]`, current file, HEAD `02d47175`:
```python
# gui/server.py:1998-2011
# AFFECT-CARRY (NEX5_AFFECT_CARRY, admin-scoped): carry a decaying
# conversational-affect weight across turns...
_affect_carry_block = ""
try:
    if os.environ.get("NEX5_AFFECT_CARRY") == "1" and bool(session.get("admin")):
        from theory_x.stage_affect.affect_carry import stance_for as _ac_stance
        _affect_carry_block = _ac_stance(session_id or "", prompt)
except Exception as _ac_exc:
    error_channel.record(f"affect_carry skipped: {_ac_exc}", source="gui.server", exc=_ac_exc)
    _affect_carry_block = ""
```
```python
# theory_x/stage_affect/affect_carry.py:202 (inside stance_for())
if os.environ.get("NEX5_AFFECT_CARRY") != "1" or not session_id:
    return ""
```
```python
# gui/server.py:2016-2029
_blocks_concat = _assemble_chat_blocks([
    ("operator", _operator_block), ("operator_anchor", _operator_anchor_block),
    ("compassion", _compassion_block), ("compass", _compass_block),
    ("equanimity", _equanimity_block), ("apramada", _apramada_block),
    ("virya", _virya_block), ("sraddha", _sraddha_block),
    ("prasrabdhi", _prasrabdhi_block), ("affect_carry", _affect_carry_block),
    ("convo", _convo_block), ("spectrum", _spectrum_block), ("tag", _tag_block),
], session_id=session_id, ...)
```
Identifier confirmed exact: `"NEX5_AFFECT_CARRY"`, no mismatch.

**B2 — parsing**: plain string equality, `== "1"`, both read sites. Not a magnitude, not a general-truthy parse. `"true"`/`"True"`/`"1 "` (trailing space) would all silently disable it — no stripping or case-folding. Reported as a finding, not fixed.

**Content of the carry value itself** (why Fork C needs a caveat — see below):
```
"[Carried tone: some weight from earlier is still lightly with you —
let it soften your voice a little. Don't name it or announce it;
just let it colour the tone.]"
```
No named entity, number, or fact — by design, explicitly instructed not to name anything.

**B3 — runtime check**, `[VERIFIED]`:
```
$ tr '\0' '\n' < /proc/2721/environ | grep AFFECT_CARRY
NEX5_AFFECT_CARRY=1
```
Process `2721` started 2026-11-14 10:02:42 — today, not continuously since September (disclosed limitation on this specific read). Continuity independent of process uptime, re-derived this round:
```
$ git log -S "NEX5_AFFECT_CARRY=1" --oneline --reverse -- nex_keepalive.sh
f9bfbc5 keepalive: arm dev-sweep flags live (Part E)
$ git log -1 --format="%ad" f9bfbc5
2026-09-18 22:40:45 +0200
```
No later removal found across every subsequent commit touching the file.

**Also found**, not previously surfaced: a second live flag gates whether the computed block survives to reach the model —
```
$ tr '\0' '\n' < /proc/2721/environ | grep CHAT_WORKSPACE
NEX5_CHAT_WORKSPACE=1
```
```python
# gui/server.py:239-264
if os.environ.get("NEX5_CHAT_WORKSPACE") != "1":
    return "".join(texts)
...
return "".join(select_within_budget(cands, budget))
# gui/server.py:188-196
_CHAT_BLOCK_SALIENCE = {"convo": 0.90, ..., "affect_carry": 0.55, ...}
_CHAT_BLOCK_EXEMPT = {"compassion", "compass"}
```
`affect_carry` is not exempt and sits at mid-range salience (0.55, below `convo` at 0.90) — on the live process, its block *could* be dropped by budget competition even when non-empty. **Neither recovered prior report mentions setting `NEX5_CHAT_WORKSPACE` in its isolated test harness**, so neither can be said to have exercised this specific live-configuration path. Not independently verified this round — would require a log line inside the frozen `gui/server.py`, prohibited.

**B4/B5 — presence and consumption**, via two independently-run prior captures of the *real* assembled prompt (reused rather than re-run, since the fact is already settled in the record):
```
Capture 1 (affect_carry_openbeat_report.txt): all 5 OLD-group captured
turn-2 prompts contain, verbatim: "[Carried tone: some weight from earlier
is still lightly with you — let it soften your voice a little...]"

Capture 2 (affect_carry_test_verify_dump.txt), independent re-run: direct
grep of a full untruncated captured payload JSON for the literal string
"Carried tone" — found verbatim, "immediately before the 'conversation so
far' history block".
```
Non-empty on 5/5 pairs (exceeds the ≥1 minimum); read into context confirmed by the code (B1c) and by these being the literal text sent to the model.

**Fork B falsifier applied:** flag truthy ✓, carry non-empty on ≥1 pair ✓ (5/5), code shows it's read into context ✓ → **FALSIFIED** — with the `NEX5_CHAT_WORKSPACE` budget-arbitration gap carried forward as a disclosed, unresolved caveat, not silently closed. Round proceeds to Task 3 (C is RUN, not NOT RUN).

## Task 3 — Fork C: does consumed carry produce an effect?

Population: all 5 OLD-group pairs (carry non-empty + read, confirmed above). Trace test already performed mechanically in Task 1: **0 of 5 show a traceable element.**

**Fork C falsifier applied** (literal): B falsified ✓, ≥1 pair non-empty+read with no traceable element ✓ (5/5) → **CONFIRMED on the letter of the stated test.**

**Caveat that must travel with this verdict, not a hedge on it:** the carry value tested here is, by design, content-free — it explicitly instructs the model not to name anything specific. Asking whether output traces a specific fact the model was *never given* is close to tautological; it cannot distinguish "model lacks the capability" from "the signal never contained the thing being searched for." The directly adjacent NEW/OpenBeat condition — where the mechanism *does* place the verbatim commitment into context — produced 1 of 5 traceable (NEW/P1, above), even though the *existing* M1/M2/M3 rule scored that same reply DROPPED. That is real evidence the model *can* produce a traceable carry when actually handed something specific to carry. This round's Fork-C verdict settles narrowly that *the specific signal currently live in production* does not, on this n=5, produce a traceable content carry — not that the model is incapable of this in principle.

## Verdict table

| Fork | Verdict | Evidence (file:line or log line + timestamp) |
|---|---|---|
| A — metric wrong | **FALSIFIED** | Re-derivation on "the 5" (OpenBeat OLD group) reproduces 0/5 exactly, each pair quoted both ways. Subject to a disclosed truncation caveat on P1/P2's excerpted text. |
| B — wiring dead | **FALSIFIED** | `gui/server.py:1998-2011`, `:2016-2029`; `affect_carry.py:202`. Runtime: `/proc/2721/environ` → `NEX5_AFFECT_CARRY=1` (2026-11-14). Non-empty+read on 5/5 pairs via two independent prior captures. Caveat: `NEX5_CHAT_WORKSPACE=1` budget-arbitration survival not independently verified on the live process — cannot check without touching the frozen `gui/server.py`. |
| C — capability absent | **CONFIRMED** (on the letter of the falsifier, OLD-group population) — see caveat above before reading this as "model incapable" | 0/5 traceable on OLD group + non-empty/read confirmed. Counter-evidence from the adjacent NEW/OpenBeat condition (1/5 traceable) substantially qualifies the interpretation. |

## Deferred, not chased

1. Whether the carry block survives `NEX5_CHAT_WORKSPACE` budget arbitration on the real live process — not verified; would need a frozen-file log line (prohibited) or a fresh isolated run with the flag explicitly matched to production (not attempted).
2. The original continuity probe's raw per-reply transcripts (flag-default run) were not available in full on this machine; not re-derived to the same standard, and not chased since that population doesn't match "the 5" anyway.
3. The OpenBeat run's full untruncated raw JSON is not present on this machine; re-derivation relied on the recovered report's own excerpts, two of which show visible truncation. Not re-collected (no live model call was made this round).
4. Whether the one observed traceable carry (NEW/P1, n=1 of 5) would replicate at larger n — no statistical power to say more.
5. Whether a differently-designed carry line (specific but not a full verbatim quote) would behave differently — a design question, out of scope (no fix, no new hypothesis this round).
6. `virya`/`prasrabdhi`/`sraddha`'s own salience values were read only incidentally while locating `affect_carry`'s entry in the same dict — none was armed, referenced as a dependency, or used to demonstrate anything, per the round's explicit non-goal.

## Closing checks

```
$ git diff --stat
(no output)
$ git diff --stat -- gui/server.py theory_x/world_bridge/selector.py
(no output — both frozen files untouched throughout; neither was opened for writing)
$ git status --porcelain
(no output — clean)
```
```
$ timeout 300 .venv/bin/python3 -m pytest -q
2140 passed, 7 skipped, 40 subtests passed in 214.59s (0:03:34)
```
Identical pass/skip counts to the start-of-round run. No live flag was flipped. No frozen file was touched. No fix was applied. This round is complete; the table above is the deliverable.
