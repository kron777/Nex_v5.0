# NEX Phase 0 — Main-Branch MIND_MAP and Active-Branch Reconciliation (25 November 2026)

## Scope and evidence boundary

This is a branch-lineage and source-reference comparison, not an import or merge proposal. It compares:

- GitHub `main` at `610cadcf5089b5f4af69ed7ad88ab02c8be5991a`;
- the active-host base branch snapshot `claude/nex-continuity-wire` at `de93134f34adac07a3a41c2a05b33720510a2bfc`;
- the current Phase 0 documentation branch, which is based on that active-host snapshot.

The GitHub compare against current main `7f45642` reports the captured host checkout `de93134` as **4 commits ahead and 641 commits behind**, with merge base `fb87e247a116221cc7d814e2ee5ff2e1300f5a87`. The remote continuity branch at `702351e` is separately 305 ahead / 641 behind main. PR #98 has merged into the remote continuity branch, not main. No host checkout fetch, merge, rebase, cherry-pick or MIND_MAP import was performed.

## 1. Main-branch MIND_MAP lineage

- `mind_map/MIND_MAP.yaml` was first added to main on 9 November 2026 (commit `2551493d162635b7c1924d3962ef264a59222693`).
- It was updated through 20 November 2026; the latest path commit in the inspected history is `ecf9c437528a9445f37020f8fadfa02de507520e`.
- The YAML is 82,865 characters and declares itself the source of truth for the generated Mermaid/SVG diagram. `mind_map/MIND_MAP.mmd`, `mind_map.svg`, `mind_map/TRIAGE.md` and `mind_map/mind_map.py` are present on main; the entire `mind_map/` directory is absent from the active-host base branch.
- The YAML has 34 entries under `nodes:` plus five arm entries. Of those 34 node entries, 30 are substantive mind-aspect nodes and four are structural/placeholder entries (`scope_void`, `prices_void`, `two_of_thirteen`, `dark_family`). The bootstrap comment and some older references say “30 nodes”; the correct counting convention must distinguish substantive nodes from all YAML entries.
- The map's `meta.constraint` explicitly says it is descriptive only: no node in the map may gate, score, block or veto an action. It is a mind-aspect taxonomy/diagram, not a runtime producer-consumer DAG and not the build-order graph.
- `mind_map/mind_map.py` validates map structure, source references, line ranges, freshness and declared absence claims. Its own comments and code do not inspect runtime callsites or prove that a represented faculty cannot gate/veto an action.
- Main's workflow runs `mind_map/mind_map.py --check --verify`; the active-host base branch has no MIND_MAP validation step because the directory and workflow step are absent.

## 2. Source-reference compatibility with the active-host base

The current YAML contains 51 source references across 41 unique source files. All referenced files exist on main. Twelve referenced files are absent from the active-host base branch:

| MIND_MAP node | Referenced file absent from active-host base |
|---|---|
| `drsti` | `theory_x/stage_world/expectations.py` |
| `smrti` | `tests/test_smrti_retained_candidate.py` |
| `kaukratya` | `tests/test_reprice_tensions_on_new_evidence.py` |
| `p3_stakes` | `theory_x/stage_world/frozen_at_made.py` |
| `p13_finitude` | `theory_x/stage_finitude/budget_shadow.py` |
| `p9_dissonance` | `tests/test_held_tension.py` |
| `p9_dissonance` | `SENTIENCE_SYNTHESIS.md` |
| `hri_apatrapya` | `theory_x/stage_tom/apatrapya_channel.py` |
| `hri_apatrapya` | `theory_x/stage_tom/hri_apatrapya_prototype.py` |
| `p8_episodic` | `theory_x/memory/episodic.py` |
| `p8_episodic` | `tests/test_episodic.py` |
| `p8_episodic` | `tests/test_episodic_falsifier.py` |

This is not a case of stale line numbers only: the base branch lacks the referenced files themselves. Importing only the YAML (or the entire `mind_map/` directory) into that branch would make the map's own source-existence check fail for these entries. The missing code/tests are part of the broader 205-commit main divergence and must not be cherry-picked independently without reviewing their dependency and behaviour changes.

The map's `meta.doctrine` also names four supporting documents. `SENTIENCE_PROGRAM.md` and `SENTIENCE_SYNTHESIS.md` exist on main; `VIRTUE_SLATE.md` and `mental_factors_inventory_alobha_spec.txt` do not. The map checker emits warnings for missing `meta.doctrine` files rather than failing the map on those warnings.

## 3. Relationship to the active-branch sentience DAG

The active-host base contains `sentience_dag.json` and `nex_next_dev.py`; these are separate from the main-only MIND_MAP.

- `sentience_dag.json` describes a dependency DAG and says its topological sort is the build order.
- Its statuses are `built`, `live_unproven`, `gap` and `gorge`.
- Its rule treats `built` and `live_unproven` as satisfied prerequisites. A dependent may therefore be buildable while carrying a `LEANS ON UNPROVEN` warning.
- `nex_next_dev.py` implements this directly with `_SATISFIED = ("built", "live_unproven")`; it flags rather than blocks dependent work.
- The MIND_MAP's descriptive-only taxonomy is not the DAG's build-order policy. Neither should be substituted for the other.

No command was run to select or start a new build from the DAG during this audit. The current Phase 0 source-trace work remains a bounded evidence task and does not change the DAG's node statuses or roadmap order.

## 4. Other authority documents present on main

- `theory_x/DOCTRINE.md` labels itself **DRAFT — awaiting Jon's review and approval**. Its §5 priority table and some GoalManager/Metacognition descriptions are stale against the active-host base's current source paths.
- `theory_x/FACULTY_MODEL.md` is a foundational document and states that it supersedes Doctrine §7's former prohibition on node-level belief writes, subject to a separate Doctrine amendment. The current Doctrine §7 text contains the Faculty Model reference, but the documents do not supply the missing Frozen V2.1 approval record.
- `theory_x/LLM_INDEPENDENCE_DOCTRINE.md` labels itself DRAFT and says implementation is blocked pending identity.yaml authoring and FT#11 voice stabilization.
- The main-only MIND_MAP metadata lists two missing doctrine source documents, as above.

These documents form different kinds of evidence: draft doctrine, faculty architecture, descriptive mind taxonomy, and dependency/build-order DAG. Their existence does not establish a single approved authority hierarchy.

## 5. Phase 0 disposition

### Confirmed

- Main and the captured active-host base are substantially diverged (4 ahead / 641 behind); the remote continuity branch is 305 ahead / 641 behind. PR #98 merged into the remote continuity branch, not main or the host checkout.
- MIND_MAP was introduced on main 9 November and last updated 20 November; the entire map directory is absent from the active-host base.
- MIND_MAP is explicitly descriptive-only and does not enforce runtime authority.
- Its 51 source references cover 41 files; 12 referenced files are absent from the active-host base, although all are present on main.
- The map's generator validates source presence/freshness and absence claims, but not runtime callsites or gating/veto behavior.
- The active-host sentience DAG and its next-dev tool remain present and are distinct from MIND_MAP; `live_unproven` counts as satisfied for dependency buildability.
- The doctrine documents include explicit draft/approval caveats.

### Unverified / authority-dependent

- Whether the main-branch MIND_MAP is intended to be imported into the active-host branch, or remain a separate main-only taxonomy until branch integration.
- Whether all 205 main-only commits are in scope for the active-host lineage, and what review/merge strategy is approved.
- Whether the MIND_MAP's four placeholder entries should count as nodes for roadmap/reporting purposes.
- Whether the map's two missing `meta.doctrine` documents should be restored, replaced or removed.
- Which document is the final approved authority for Phase 0/Phase 1 and the exact Frozen V2.1 requirements.
- Whether any active-host source paths have been intentionally removed or replaced relative to the main-only MIND_MAP.

### Boundary

Do not copy the MIND_MAP, generated diagram, source files or tests into the active-host branch; do not merge/rebase/cherry-pick main; do not alter sentience_dag statuses or use `nex_next_dev.py` to launch work until the owner explicitly confirms branch lineage and governing-document authority.
