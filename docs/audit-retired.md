# Audit items retired (with evidence)

Static-audit findings that were investigated and found to need no code change, or
whose fix is not what the raw finding implied. Recorded so a later audit pass does
not re-raise them. Branch of record: `claude/nex-v5-audit-review-53ouqv` (PR #11).

## M11 — `print()` → `logging`: RETIRED (not deferred)

The audit flagged ~949 `print()` calls tree-wide as logging debt. That was a raw
grep count with no context check. On inspection the real runtime-stdout-print debt
is **zero**:

- `gui/server.py` (the live service) has **no** runtime stdout prints — it already
  logs through named loggers.
- All 224 `print()` in `theory_x/` and the ones in `substrate/` are one of:
  - inside an `if __name__ == "__main__"` CLI/demo block,
  - inside a report helper (`show_map()`, `verdict()`, `check()`) called only from
    such a block,
  - a `file=sys.stderr` error diagnostic,
  - a seed / spectrum / init CLI script,
  - an offline training-progress line (`genius/score_v2.py: fit_logistic`).

All of these are correct uses of `print`. Converting them (e.g. the `stage_tom`
detectors' demo output) would break the CLIs.

**Disposition:** the one useful piece of D-C was shipped — `nex_config.setup_logging()`
(one logging authority; third-party loggers quieted to WARNING via `setLevel` only;
root stays INFO so all 8 app namespaces keep emitting). No print→logging conversion
is warranted.

## M5 — prompt token budget / arbitration: ALREADY IMPLEMENTED

The audit asked for a token-budget / priority layer over the ~13 chat faculty
blocks. It already exists, shipped dark: `gui/server.py:_assemble_chat_blocks()` +
the `NEX5_CHAT_WORKSPACE` flag — salience-ordered admission under a char budget
(`NEX5_CHAT_WORKSPACE_BUDGET`, default 1400), safety-exempt blocks
(`{compassion, compass}`) never evicted, optional cross-turn salience continuity
(`NEX5_SELF_PRESENT`), fail-safe to full concatenation, and byte-identical when the
flag is off (test: `tests/test_chat_blocks_budget.py`).

**Disposition:** no new budget mechanism needed. A redundant token-ceiling module
written during this review (`prompt_budget.py`) was removed. Remaining M5 work is
runtime tuning the owner does — flip `NEX5_CHAT_WORKSPACE=1`, tune the budget and
salience weights, optionally `NEX5_SELF_PRESENT=1`. A per-turn measurement line
(`chat prompt chars: blocks=… voice_prompt=…`) was added so the owner can see
whether the assembled prompt ever approaches the model context window; only then is
a hard token clamp worth adding.

## Drift surfaced by the generalized schema guard — RESOLVED

`tests/test_schema_indexes.py::TestBeliefsInsertColumnsExist` found three columns
used in `INSERT INTO beliefs` but absent from the central schema/migrations. All
three are now resolved (the test's allow-list is empty again):

- `parent_belief_id`, `variant_index` — formalised as plain nullable `INTEGER`
  columns in `_MIGRATIONS["beliefs"]`. No FK (`parent_belief_id` holds sentinel
  markers `-2`/`-99`, not real parent ids), no index at this row count, and no
  partial UNIQUE (that can fail on existing data — measure first, follow-up).
- `updated_at` — removed from `decryption/probe_runner.py`'s INSERT (column and
  value dropped together). It was write-only, unread, and `ground_self_belief.py:190`
  documents that beliefs has no `updated_at` column.

Follow-up (optional, not drift): the sentinels `-2` (process cluster) / `-99`
(probe exclusion) are magic numbers duplicated across those two modules; a shared
named constant would be cleaner. Left out of the drift fix to avoid parameterising
SQL in a possibly-experimental `decryption/` path.
