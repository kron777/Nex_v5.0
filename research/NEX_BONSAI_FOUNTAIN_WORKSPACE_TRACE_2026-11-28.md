# NEX Bonsai-to-Fountain and Global Workspace trace

**Date:** 28 November 2026  
**Base:** `kron777/Nex_v5.0` main at `3377197` (post-G-84 producer and StrikeProtocol shutdown integration)  
**Branch:** `test/affect-faculty-interactions-current-main-2026-11-28`  
**Status:** test-only characterization ported onto current main; exact-head CI pending.

## 1. Source path

The Stage-2 A–F pipeline maps external sense events to a branch, computes magnitude, applies the membrane aperture, derives valence and calls `BonsaiTree.attend()`. Bonsai's branch focus/texture is the shared state read by downstream consumers.

### Fountain branch choice

`FountainGenerator.fire → status["branches"] → sort by focus_num → _weighted_branch_pick(sorted_branches, top_pick)`

- With `NEX5_BRANCH_TEMP` unset, zero, invalid or non-positive, the true top-focus branch is returned unchanged.
- With a positive temperature, the function applies softmax weights to all non-empty branch IDs and performs a roulette draw. This can surface a lower-focus branch; the temperature is an explicit feature flag and defaults OFF.
- Errors fall back to the hottest branch.

### Global Workspace framing

`GlobalWorkspace.arbitrate → _bonsai_candidate(status) → (focus_num × _W_BONSAI, framing_text) → arbitrate_candidates(candidates)`

The hottest branch is admitted only when focus exceeds 0.1. Its salience is focus multiplied by the Bonsai weight. The pure arbitration helper chooses the highest-salience candidate and prepends its framing text; it does not remove other faculty blocks.

These are two independent consumers of the same Bonsai state: Fountain selects a branch for credit/carry, while Global Workspace chooses the leading frame for the thought.

## 2. Test added

`tests/test_dynamic.py::TestPipeline.test_bonsai_focus_propagates_to_fountain_branch_pick_and_workspace_frame`:

1. Sends 40 external `ai_research.arxiv` events through the real A–F pipeline using isolated temporary substrate writers.
2. Asserts the resulting Bonsai focus exceeds the Global Workspace threshold.
3. Asserts default Fountain selection returns the highest-focus branch.
4. Patches the random draw deterministically and verifies that positive temperature can select a lower-focus branch.
5. Passes the same branch snapshot to the Global Workspace Bonsai candidate and pure arbiter, verifying that the branch frames over a lower-salience momentum candidate.

The prior Stage-2 test remains the negative control for internal telemetry: `internal.proprioception` matches `systems` but its magnitude is zero, so it produces no Bonsai focus change, no F-step event and no Global Workspace Bonsai candidate from the unchanged snapshot.

## 3. Limits

This is a deterministic fixture characterization, not a live Fountain fire or runtime observation. It demonstrates that the code wires the same attention state into two downstream decisions. It does not establish that either decision improves reasoning, relevance or output quality.

The next experiment should measure winner-kind shifts and downstream output under one-variable perturbations: branch focus, workspace candidate salience and competing-drive weights separately. Do not activate production flags or modify salience weights for this characterization.
