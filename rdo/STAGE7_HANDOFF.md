# Stage 7 — bounded handoff manifest and human decision record

**Status:** First real-objective handoff increment. It is not the Stage 7 exit criterion and does not execute work.

## Purpose

A persisted RDO objective cycle and eligible work package can now be converted into an immutable handoff manifest that a human or external coding agent can inspect. The manifest binds the exact objective input revision, RDO cycle, repository commit, work-package key, obligations, relationships, path scope, constraints, exclusions, deliverables and evidence needs.

The handoff adapter is in \`rdo_adapters/handoff.py\`, outside the 14-module RDO reasoning package.

## Create a handoff

First submit and persist an objective with \`python -m rdo intake\`. Select a work package from the saved cycle and run:

\`\`\`bash
python -m rdo handoff-create \\
  --objective-id <objective-id> \\
  --revision 1 \\
  --cycle-id <cycle-id> \\
  --work-package <work-package-key> \\
  --repo . \\
  --out rdo/.cycles
\`\`\`

The command accepts only an RDO-native planning cycle whose objective ID, revision and input digest match the append-only intake ledger. The selected checkout must still be clean and at the exact commit used by the cycle. A changed repository requires a new RDO cycle and reconciliation.

A work package must be eligible and the objective must include explicit affected paths to be considered pending human review. A blocked or unbounded work package can still be represented as a blocked manifest for inspection, but it cannot receive scope approval.

The manifest records both the caller-declared path and its resolved in-repository target. A lexical path or parent symlink that resolves outside the checkout is refused; internal symlink aliases retain both names for traceability.

The manifest is stored once at:

\`rdo/.cycles/handoffs/<handoff_id>.json\`

Its canonical JSON payload has a SHA-256 digest. Repeated creation for the same source cycle/work package returns the existing record only if all immutable content matches. A changed or tampered manifest is rejected.

## Human scope review

Inspect the manifest before any external work. A human-attributed review can be appended:

\`\`\`bash
python -m rdo handoff-review \\
  --handoff-id <handoff-id> \\
  --decision approved \\
  --reviewer "reviewer attribution" \\
  --source-reference "reference to the actual approval" \\
  --permitted-action prepare_scoped_patch \\
  --note "Prepare a patch only; do not execute tests."
\`\`\`

The only permitted action values are:

- \`prepare_scoped_patch\`
- \`edit_documentation_within_scope\`
- \`edit_rdo_tooling_within_scope\`
- \`create_review_branch\`

Tests, arbitrary command execution, live NEX writes, database changes, experiment changes, runtime flags, service restarts and deployment are always rejected by this handoff boundary. A scope-review approval authorizes preparation of the named proposal within the manifest's exact allowed paths; it does not launch an agent and does not authorize tests.

Decision records are append-only JSON Lines, linked to the immutable manifest digest and each other by a SHA-256 chain:

\`rdo/.cycles/handoffs/<handoff_id>.events.jsonl\`

The recorded reviewer and source reference are **caller-attributed, not identity-authenticated**. This local ledger preserves what was stated and the referenced approval source; it does not prove who operated the computer or independently authenticate the referenced approval.

## Human acceptance is a different decision

After a delivery is made and reviewed by a human, acceptance can be recorded separately:

\`\`\`bash
python -m rdo handoff-acceptance \\
  --handoff-id <handoff-id> \\
  --decision accepted \\
  --reviewer "reviewer attribution" \\
  --source-reference "reference to the actual acceptance" \\
  --delivery-reference "patch/commit/review artifact reference" \\
  --evidence-references evidence-references.json \\
  --out rdo/.cycles
\`\`\`

The evidence-reference JSON must name three independent arrays:

\`\`\`json
{
  "source_implemented": ["reference to source diff or inspection"],
  "test_verified": [],
  "runtime_observed": []
}
\`\`\`

Empty arrays remain empty. A test reference is not a test pass; a source reference is not runtime proof; runtime evidence is not human acceptance. The acceptance event records a separate human judgement and leaves the immutable manifest's creation-time evidence statuses unchanged. The latest human acceptance is surfaced separately by \`handoff-history\`.

## Inspect the record

\`\`\`bash
python -m rdo handoff-history --handoff-id <handoff-id> --out rdo/.cycles
\`\`\`

The history view validates the manifest digest and every decision-event link before reporting the latest scope review and human-acceptance event.

## Non-execution guarantees and limitations

- Creating, reviewing and inspecting a handoff does not launch Claude Code or any other agent.
- No tests or arbitrary commands are run by this adapter.
- The initial evidence dimensions are \`source_implemented=not_collected\`, \`test_verified=not_authorized\`, \`runtime_observed=unknown_host_only\`, and \`human_acceptance=not_recorded\`.
- The existing \`rdo/execution.py::verify()\` still performs source inspection and test invocation inside the RDO process; it is not yet an independent Watcher process boundary.
- Its exact-path pytest allowlist is not an OS sandbox. Pytest configuration, \`conftest.py\`, plugins and test code may execute. Arbitrary test execution remains unapproved until a disposable environment with no secrets, no live NEX data mounts and restricted network access is independently designed and verified.
- Reviewer attribution is not authentication. Human scope approval and human acceptance are stored as separate append-only events.
- A blocked package, changed repository snapshot, mismatched objective revision, or tampered manifest/ledger is refused.

This increment enables objective → persisted cycle → exact handoff manifest → human scope review. It does **not** yet provide independent Watcher-process verification or the complete objective-to-verified-delivery pathway required by RDO v1.3 §16 Stage 7. Issue #87 remains open.
