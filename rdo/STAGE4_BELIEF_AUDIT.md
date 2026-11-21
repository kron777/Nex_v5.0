# RDO Stage 4 — Read-only Belief Audit

**Governing scope:** RDO v1.3 §16 Stage 4. A source-grounded, **read-only** map of NEX's belief
lifecycle with provenance for every finding and a traceable gap map. Tooling: `rdo/belief_audit.py`
(`python -m rdo stage4`). **Authority boundary honoured:** no live-DB query/write, no injection,
config change, restart or experiment modification. Facts only the live machine can establish are
recorded as honest **host placeholders**, never guessed.

**Coordination.** Branch `claude/rdo-stage4-belief-audit`, based on `c9cb946` (Stage 3 head). `rdo/`-only.
Reuses `reconcile`-style read-only grep (extended to `.sql` so the externalised schema is visible)
and the Watcher's `Evidence` / `host_placeholder` provenance vocabulary (imported, not modified).

## Belief lifecycle (all six phases evidenced — file:line provenance)

| Phase | Mechanism | Evidence |
|---|---|---|
| **origin / creation** | writes to `beliefs` (seed loaders, source stamping, spectrumizer); each row records `source` | `substrate/.../INSERT INTO beliefs`, `beliefs.sql:source` |
| **persistence** | stores: `beliefs` (content, **confidence**, created_at, source, tier, …), `belief_edges`, `belief_blacklist`, `belief_activation` | `substrate/schema/beliefs.sql`, `substrate/init_db.py` |
| **provenance** | `source_kind` — per-stream provenance stamped at the write boundary | `substrate/source_kind.py` |
| **update / lifecycle** | promote/demote with timestamps + log, recency, erosion, use/reinforce counts | `beliefs.sql` columns; `belief_activation.last_touched_at`; `source_kind.py` UPDATE |
| **relationship** | `belief_edges` are **typed**: supports / opposes / synthesises / cross_domain / refines | `substrate/schema/beliefs.sql:edge_type` |
| **consumption / influence** | **92** source files read `FROM beliefs`; generation/retrieval biased by beliefs; `belief_boost` lever | `theory_x/stage6_fountain/*`, `theory_x/stage4_membrane/*`, … |

**Correction recorded (discipline: inspect behaviour, don't assume from a name).** An initial
draft flagged "belief updates are not timestamped." The audit of the real `beliefs` columns
**refuted** this: the row tracks `last_promoted_at`, `last_demoted_at`, `promotion_log`,
`last_referenced_at`, `reinforce_count`, `use_count`, `erosion_stage`, `corroboration_count`. The
gap map records this as **resolved**, not a false gap.

## Gap map (traceable; host-only items flagged, never guessed)

| Gap | Severity | Status | Evidence / note |
|---|---|---|---|
| `belief_update_tracking` | tracking | **resolved** | lifecycle IS tracked in-row (promote/demote timestamps + `promotion_log`) |
| `belief_boost_inert` | inconsistency | **open** | `belief_boost` exists but is documented decision-INERT ("do NOT build") — `tools/check_belief_headroom.py:196` |
| `untracked_influence_surface` | unresolved | **open** | 92 belief-reading files; the Watcher runtime graph tracks only a subset of belief→behaviour edges — a review surface, not a proven defect |
| `provenance_completeness_unverified` | unresolved (host-only) | **open** | whether every live write stamps a `source` (no NULL rows) is host-only; unknown from the cloud |

**Host-only unknowns (honest placeholders):** live belief row count, the actual confidence
distribution, and what is firing at runtime — all `origin=host, class=unknown, modifier=unverified`,
`data=None`. NEX is in standby and this audit does not touch the live DB.

## Read-only guarantee

`rdo/belief_audit.py` imports no `sqlite3`, opens no file for writing, and runs only `grep`
(read-only) + file reads. Verified by `test_audit_is_read_only` (no `sqlite3` import, no write-mode
`open`, no files created by `audit()`/`gap_map()`). The runner's only write is the RDO's own
`belief_audit.json` artefact (not a NEX store).

## Tests & durability

`rdo/tests/test_stage4_belief_audit.py` (10 tests): every phase evidenced with provenance;
host-only facts flagged not guessed; typed belief relationships found; the gap map asserts no false
gap and backs every real gap with evidence; read-only proof; traceable repo-relative evidence; and
an end-to-end run that persists `belief_audit.json` and resumes in a fresh process. Full RDO suite:
**83 passing**.

## Remaining gaps / next step

- **Open for review:** `belief_boost_inert` (inconsistency), `untracked_influence_surface`,
  `provenance_completeness_unverified` (host-only). These feed **Stage 5 — first belief-to-mechanism
  pathway** (selecting one low-risk, falsifiable pathway with baseline/tests/rollback), which is
  **not** started here.
- **Host-only confirmation** of live belief state remains unauthorised/unavailable.

## Specification-precedence note (unchanged, unresolved)

The implementation cites **RDO v1.4** in docstrings; the governing sequence is **v1.3 §16**. The
v1.2 / v1.3 / v1.4 texts, Watcher v3.0 and the Master Roadmap v3.0 are not in the workspace; no
version reconciliation is assumed, and the precedence remains for founder resolution.
