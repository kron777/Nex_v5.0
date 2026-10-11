# R81 — PRE-REGISTRATION: L4_teeth, mechanical selection shift (`NEX5_L4_TEETH`)

> **⚠ AMENDED 2026-10-11 (Beam's C1/C2 reply, verified by grep) — RE-SCOPED; do not arm on the old primary.**
> Two confirmed problems:
> - **C2 — this is FRAME-only, not retrieval teeth.** Grep settled it: the arbiter winner `_gw_line`
>   appears ONLY at the import/compute/prepend (`generator.py:3037,3044,3050`); `focus_block`'s body is
>   fetched before the prepend and never uses the winner. So L4_teeth demotes *which framing line leads*,
>   not *what is retrieved*. It is a legitimate **framing-selection** round (substitutive, more falsifiable
>   than r79/r80), but it is NOT the mechanical-retrieval teeth the L3 lesson named. The **true** L4_teeth
>   is a retrieval-weight shift at the focus_num-weighted branch/seed selection
>   (`generator.py:184-198` keystone seed, `:1874-1877` branch pick, `_retrieve_context_beliefs:2624`) —
>   a separate build (see §8 / L4_teeth DAG node).
> - **C1 — the old primary (`p_on_subject`) is partly DEFINITIONAL.** When momentum leads, the fire
>   continues a prior thread, so it scores off the current item *by the selection's definition*, not
>   because attention degraded. Demoting momentum ⇒ fewer continuation fires ⇒ higher on-subject is
>   **arithmetically guaranteed**, and the 43→35 baseline is a replay of the motivating observation.
>   **New primary (the side being bought, not sold):** item COVERAGE — distinct items fired on per 100
>   fires at matched cadence — and/or thread-switch concentration (HHI over fired items). Both are blind
>   to winner-kind. If on-subject is kept at all, only per-fire (not pooled) and reported *within* the
>   momentum-led stratum. §3/§5 below are superseded by this primary.

## 0. Status — built (FRAME version), feasibility PASS, but RE-SCOPED per C1/C2 — see banner

The readiness arms (r79 aversive, r80 reward) are near decision-inert: readiness is saturated at
fire (96% of fires ≥0.90; r80 §1c), so a bounded readiness term rarely flips a decision. L4_teeth
is the **selection** lever instead — it changes WHICH candidate leads a fire, not how often she
fires. Crucially, unlike r79/r80 its target is confirmed live: `arbitrate` runs on every fire
(`generator.py:3035-3050`, `NEX5_GLOBAL_WORKSPACE` default-on) and its winner is prepended to
`focus_block`. Built behind `NEX5_L4_TEETH` (default OFF, `arbitrate` byte-identical when OFF).
Arming is the maintainer's step on the live launcher.

## 1. The change under test

**`NEX5_L4_TEETH` (default OFF).** In `arbitrate`, the momentum (groove-continuer) candidate's
salience is multiplied by `_W_MOMENTUM_TEETH_FACTOR = 0.6` (bounded to (0,1] — demotes, never
inverts) before the `max()` competition, so a novel candidate (surprise/bonsai/drive) can lead.
Code: `theory_x/stage_tom/global_workspace.py` (`_teeth_momentum_factor`, applied to the momentum
candidate in `arbitrate`). Single-turn, no persistence (that is L4b). OFF ⇒ factor 1.0 ⇒ byte-
identical. The factor is PROVISIONAL (this round measures the effect before any default-on).

## 2. Feasibility — WIRED and MOTIVATED by the code's own record

- **Wired:** `arbitrate` is called on every fire (`generator.py:3037,3044`), gated by
  `NEX5_GLOBAL_WORKSPACE` (default "1"). The winner leads `focus_block` (`:3050`). So demoting
  momentum changes a real, live prompt — not an inert signal (contrast r79's 0.55 threshold).
- **Motivated:** `generator.py:3051-3054` records that the winner "is almost always the momentum
  line … which pulled EXPLAIN/ARGUE off the item (on-subject 43→35/60 in the item-2 probe)." So
  momentum-winning is a documented harm with a known direction on an independent metric. L4_teeth
  is the direct fix (demote the groove-continuer in the competition), complementing the existing
  partial mitigation (the GWT line is already withheld from wide fires, `:3051`).
- **Determinism of the mechanism:** momentum (0.55) → 0.33 when armed, so it loses to any
  competitor in [0.34, 0.55) that previously lost to it (e.g. a bonsai branch at focus≈0.9 → 0.45).
  The mechanism fires by construction whenever momentum would otherwise beat a mid-weight rival.

## 3. Hypothesis and metrics

**Hypothesis.** Demoting the momentum candidate **raises on-subject fidelity** — reversing the
documented 43→35/60 drop momentum caused — **at constant cadence**. Mechanism: a novel/engaged
candidate leads instead of "continue the live thread", so the fire stays on the item.

**Primary (independent of the mechanism).** `p_on_subject` from `check_tripwires`, baseline
(hardened read, 2026-10-11) **overall 0.655 / EXPLAIN 0.782 / ARGUE 0.542**. This is a fidelity
metric, NOT the winner-kind the teeth acts on — so it escapes the self-reference that sank r79/r80
(Beam A2). Effect sought: on-subject **rises** (MDE **+0.03 absolute** overall; at n≈400/window the
Wilson CI half-width is ≈0.045, so the round should run to ≥800 fires for +0.03 to clear — stated
per Beam 4b; if the rise is < MDE with CI excluding it, that is a real null, not inconclusive).

**Co-primary (Beam 1a).** Cadence (`check_cadence --baseline`) within **±20%** of 690.5/day —
"helped" = on-subject up at constant cadence; a cadence swing means the teeth changed volume, not
selection.

**Mechanism-fired (telemetry, optional confirm).** The momentum line leads a smaller fraction of
fires. Not currently logged; a winner-kind tag in `arbitrate` would confirm it. Structural
determinism (§2) stands in until then.

## 4. Tripwires — revert if ANY fires

- Cadence outside ±20% of 690.5/day.
- `p_on_subject` EXPLAIN reverts **< 0.65** (the existing revert tripwire) — we expect a RISE; a
  drop means demoting momentum hurt fidelity → revert.
- maxDF* breach ≥ 25%; register largest-share > 0.70.

## 5. The falsifier (Beam's standard) and decision tree

Falsifier: the demotion must change **what leads** and move the independent outcome. If on-subject
does **not** rise even though momentum is demoted, then momentum-winning was **not** the on-subject
driver (the documented 43→35 was confounded) — L4_teeth is falsified for its stated purpose.

- **BRANCH A — on-subject up ≥ 0.03 at cadence in band, no tripwire.** Selection-coupling WORKS —
  the lever readiness is not. → default-ON consideration; one pre-registered factor-tuning pass
  (r81b: `_W_MOMENTUM_TEETH_FACTOR` toward the value that maximizes on-subject without a cadence
  hit), then stop. Promotes L4_teeth toward `built`; motivates `L4b_persistent_stake`.
- **BRANCH B — on-subject flat (< MDE, CI excludes +0.03), cadence in band, no tripwire.** Demoting
  the winner did not move fidelity → the documented momentum→on-subject link doesn't hold under a
  clean manipulation. Record; selection via this candidate is not the lever; reconsider the hook
  (retrieval-weight shift rather than framing-line demotion).
- **BRANCH C — any tripwire.** Revert; record which and the reading.

## 6. Sequencing

Independent of r77/r78/r80; `NEX5_L4_TEETH` is its own flag. Run alone (all other `NEX5_*`
prompt/affect/stake flags OFF). Note: `NEX5_GLOBAL_WORKSPACE` must stay ON (default) — L4_teeth is
a no-op if the workspace is disabled.

## 7. Verdict and disarm

Verdict to `observation_reports/r81.md` + `journal/DEPLOY_LEDGER.tsv` + `journal/CARRY_OVER.md`;
the disarm commit's subject carries the verdict and SHA.

---

*No sentience claim. r81 tests whether a bounded, mechanical shift in which candidate leads a fire
measurably changes an independent behaviour (on-subject fidelity) — selection, not excitability. It
is silent on whether anything is experienced.*
