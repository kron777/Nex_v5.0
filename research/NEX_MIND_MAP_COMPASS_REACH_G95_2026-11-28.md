# Mind-map re-verification after #362, and the compass's reach into "dark" detectors — G-95

**Evidence snapshot:** `main` at `f5cf19c32b0151043ca90b139b25c24e01e384fb`, 28 November 2026.
**Evidence classes:** source and fixture tests only. No live process, flag, database or host was read; runtime state is UNKNOWN.

## 1. Why this was opened

After #362 (`b5e78842`) merged, the mind-map check (`python mind_map/mind_map.py --check --verify`, run in every CI job) started reporting STALE for six nodes: alobha, vedana, mana, smrti, vitarka and vicara. #362 changed `theory_x/stage6_fountain/generator.py` by one line and `theory_x/stage_tom/self_binding.py` by two added lines, after those nodes' `last_verified` date of 2026-11-27.

## 2. Re-verification of the six STALE nodes

> **Correction (G-96, later on 2026-11-28).** The comparison below used the wrong baseline. It checked each range against `b5e78842~1`, the tree just before #362. It should have checked against `c6bc4e41`, the 2026-11-27 verification that wrote these anchors.
>
> Commits later that day had already moved several of the cited lines:
> - `5d7f4e28`, `c42c2131` and `8570c05d` moved lines in `generator.py` by 2–4;
> - `cc8ae436` moved the cited lines in `crystallizer.py` by 29;
> - `8570c05d` added 9 lines to `self_binding.py`.
>
> So "byte-identical" below is true only against the later tree, and some anchors set here were a few lines off the intended code; mana's `self_binding.py:280-346` is one. Every anchor was re-derived from its own verification commit and corrected in the G-96 reconciliation; the affected nodes carry dated CORRECTION notes. The G-95 compass findings in §4 are unaffected.

Each cited range was compared by content between `b5e78842~1` and `f5cf19c3`:

| Node | Cited range(s) in the changed files | Result |
|---|---|---|
| alobha | `generator.py:727-785`, `:867-883` | byte-identical |
| vedana | `generator.py:611-652`, `:857-863` | byte-identical |
| smrti | `generator.py:1878-1903`, `:2960-2975` | byte-identical |
| vitarka | `generator.py:893-990`, `:2719-2735`, `:4044-4068` | byte-identical |
| vicara | `generator.py:3356-3445`, `:3460-3475`, `:4060-4072` | byte-identical |
| mana | `generator.py:3986-3995` | byte-identical |
| mana | `self_binding.py:278-344` | moved +2 to `280-346`, content identical |

The generator.py change (`:3927`, passing `dynamic_writer` to `recursive_self.format_for_prompt`) moves no line and lies outside every cited range.

## 3. A same-day anchor drift the STALE check cannot see

`14873c10` (2026-11-27 19:34 +0200) replaced the launcher's hard-coded `cd` with script-relative resolution, inserting 6 lines near the top of `nex_keepalive.sh`. It landed after `c6bc4e41`, the same-day re-verification that introduced the `nex_keepalive.sh:219-220` anchors. Because staleness is compared at day granularity, no warning fired, but every launcher anchor below line 12 now points six lines too high:

| Node | Old anchor | Content now at | Check |
|---|---|---|---|
| vedana, mana, vicara, p6_unified_present | `nex_keepalive.sh:219-220` (launch-line tail) | `:225-226` | identical to `c6bc4e41:219-220` |
| p8_episodic | `nex_keepalive.sh:219-220` | `:225-226` | identical; **not changed here** (see §6) |
| p13_finitude | `nex_keepalive.sh:191-220` (`launch_nex()` head) | `:197-226` | identical |
| p1_continuity | `nex_keepalive.sh:14-39` (flock and supervision) | `:20-45` | identical |

## 4. G-95: the compass reads detectors the map calls dark

**Source chain** (all at `f5cf19c3`):

1. `gui/server.py:2262-2264`: the chat handler calls `compass.stance_for(prompt)` when `NEX5_COMPASS == "1"` and the session is admin.
2. `theory_x/stage_affect/compass.py:74-102` `weigh()`:
   - calls `compassion._distress_read()` (`:81-83`);
   - calls `amoha_detector.detect()` (`:91-92`);
   - calls `self_binding._cluster_reads()` (`:96-97`).

   None of these calls checks a flag.
3. `theory_x/stage_tom/self_binding.py:303-319` `_cluster_reads()` calls `detect()` on raga, dvesa, mana, avidya and moha. Only `afflictions_for_prompt()` (`:322`) checks `NEX5_AFFLICTIONS`.
4. `compass.format_stance()` turns those reads into prompt text:
   - a "clouded" or "mild" clarity read (`:123-128`);
   - any high affliction read (`:129-132`);
   - and, only when one of those is live, the care clause (`:139-141`).
5. `nex_keepalive.sh:225`: the launch line has set `NEX5_COMPASS=1` since `4f1f3c7e` (2026-09-15). It sets neither `NEX5_AMOHA` nor `NEX5_AFFLICTIONS`.

**The reach was deliberate.** The disarm commits say so:

- `b941c796` (2026-10-04, disarm `NEX5_AFFLICTIONS`): "The compass still reads the cluster via `self_binding._cluster_reads()` directly (not flag-gated), so its KEEP is unaffected."
- `280125c3` (2026-10-05, disarm `NEX5_AMOHA`): "The compass reads `amoha.detect()` directly (not flag-gated) and is untouched."

**What the map said.**

- **mana:** `dark: true`. It said `detect()`'s only live-path caller is `_cluster_reads()`, "called only from `afflictions_for_prompt()`", and that it runs on "ZERO live turns". The 2026-11-15 `/proc` probe looked for `NEX5_AFFLICTIONS`, not `NEX5_COMPASS`.
- **amoha:** `dark: true` and "it works and is never used".
- **karuna:** `dark: true`, because `NEX5_COMPASSION` is unset.

**Fixture evidence.** `tests/test_compass_detector_reach.py` (3 tests) stubs the six detectors, with no database and no embedding model. With `NEX5_AMOHA`, `NEX5_AFFLICTIONS` and `NEX5_COMPASSION` unset, it pins:

- `weigh()` calls all six detectors;
- an "inflated" mana read reaches the stance text;
- the detectors' own gated surfaces stay silent and never read.

**Mutation check.** Gating the compass's cluster read on `NEX5_AFFLICTIONS` turns two of the three tests red.

**Map changes.**

- **mana:** `dark` true → false; `falsifier_status` na → unrun (the premise "doesn't fire at all" no longer holds, and the falsifier has not been run); refs add `compass.py:74-102`.
- **amoha:** `dark` true → false; the measured falsifier (fail) is unchanged; source becomes composite, adding `compass.py:74-102` and `nex_keepalive.sh:225-226`.
- **karuna:** note only; `dark` stays true (§5).

The dark count goes from 14 to 12. `MIND_MAP.mmd` is regenerated from the YAML. That regeneration also picks up p12's pre-existing drift from 2026-11-15. `mind_map.svg` needs Graphviz `twopi`, which is not installed here, and is not regenerated.

**Limits.** Source and launch configuration show that these reads are reachable on admin chat turns. How often admin chat turns occur on the host, and whether the running process has the launcher's environment, is UNKNOWN. On the 2026-11-15 sample no real thought reached amoha's 0.30 per-thought bar, so that read would return "clear" and add nothing. This changes no code, flag, prompt or threshold.

## 5. Open for the founder

**karuna's classification.** The compass calls `compassion._distress_read()`, the stateless salience read, on admin chat turns. That read surfaces only as the "care is owed" clause alongside another live consideration. The faculty the node describes, the persisted level and stance behind `NEX5_COMPASSION`, is not invoked. Does that partial use make karuna not-dark? The node is left `dark: true`, with the evidence in its notes.

## 6. Not changed here

- **p8_episodic's `nex_keepalive.sh:219-220` anchor** is on the same YAML line that open #361 edits. To avoid a conflict, it will be corrected to `:225-226` after #361 merges.
- **INDEX.md and its plain-text mirror** are being edited by open #363 and #364. The G-95 manual entry will follow once those land.
- **The two copies have drifted apart on main** (pre-existing, not addressed here):
  - INDEX.md lacks the §48 "Critical next-step constraint" paragraph that the mirror has.
  - The mirror lacks §45.
