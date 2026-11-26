# RDO specification-version reconciliation

**Date:** 26 November 2026  
**Status:** Evidence reconciled; version precedence remains **UNRESOLVED**.  
**Authority:** This is a non-normative audit note. It does not amend, replace or interpret either specification.

## Question

The staged development documents merged through PR #124 identify **RDO v1.3 §16** as the governing sequence. Several RDO source-module docstrings that were already present on the pre-PR-124 `main` base cite **RDO v1.4** and sections numbered up to §24. The available evidence must establish what those references point to before any version-precedence decision is made.

## 1. Original v1.3 source located

The Library contains the original file:

- `NEX_Recursive_Development_Orchestrator_Specification_v1.3.pdf`
- Cover: **Version 1.3 | 20 November 2026 | Prepared for Claude / Claude Code**
- 22 pages; PDF title metadata: *NEX Recursive Development Orchestrator Specification v1.3*.
- SHA-256: `81a268f54e1dca7464ba43a3adb2637665c8f0ee8fb0a97632a8d079b3f23e8b`.

A second Library copy, `NEX_Recursive_Development_Orchestrator_Specification_v1.3(1).pdf`, has the same byte size and identical SHA-256. It is a duplicate, not independent corroboration.

The earlier original v1.2 PDF is also present in the Library (20 pages; cover says Version 1.2 | 20 November 2026). Its structure differs materially: its §12 is the provisional roadmap, §13 is the MVP acceptance criteria, §15 is the immediate assignment, and §16 is “Research basis, design rationale and limitations”. Its roadmap table begins with “2. RDO foundation” and uses a different stage grouping. The Library source-document index labels v1.2 the earlier specification and v1.3 the later specification; the 22 November carry-over likewise records v1.3 as the later working specification replacing v1.2. This supports the v1.2 → v1.3 chronology. It does not establish a subsequent v1.4 revision.

The original v1.3 PDF's printed **§16, “Roadmap and immediate execution order” (PDF page 17)** specifies:

| Stage | Work |
|---|---|
| 0 | Reconcile Watcher PR #46, CI, current branches, unfinished work and repository SHA |
| 1 | Complete the Watcher increment |
| 2 | Extrapolator MVP |
| 3 | Graph intelligence |
| 4 | Read-only belief audit |
| 5 | First belief-to-mechanism pathway |
| 6 | Learning loop |
| 7 | Execution integration through Watcher |

Its immediate instruction says to reconcile the repository and PR #46 first, then implement the Extrapolator MVP as a new external RDO subsystem, demonstrate it on the belief-development objective, and keep live NEX changes and protected experiments untouched. §19 separately requires verification against the current checkout and preserves the approval boundary for consequential live changes.

This matches the Stage 2–7 documents and execution sequence merged in PR #124. The merged PR's stage documents explicitly cite v1.3 §16.

**Section-number check:** the retrieved v1.3 PDF ends at §20. In v1.3, §14 is “Safety, authority and experiment integrity”; §15 is “MVP and acceptance criteria”; §16 is the roadmap; §§17–20 cover evaluation, risks, the Claude operating contract and final synthesis. Therefore, citations to v1.4 §§23 or 24 cannot be citations to this v1.3 document.

## 2. What the v1.4 references establish

The following references are in the RDO foundation at base commit `ef704e1f33c92f865234fb8d5c5d5bcd40696210` (the PR #46 merge commit, before PR #124):

| Repository source | Existing reference |
|---|---|
| `rdo/prioritise.py:1` | “RDO spec v1.4 §23” |
| `rdo/memory.py:1` | “RDO spec v1.4 §24, Part VIII” |
| `rdo/tension.py:1` | “RDO spec v1.4 Part II & §4” |
| `rdo/tension.py:197` | “RDO spec v1.4 §6, §20” |
| `rdo/model.py:13` | “RDO spec v1.4 §3.4” |
| `rdo/extrapolator.py:7` | “RDO spec v1.4 §14” |

These references predate PR #124; they were not introduced by the Stage 2–7 integration. They establish that the earlier RDO foundation was written with a v1.4-labelled section structure in mind. **They do not establish the contents, authorship, approval status or precedence of an original v1.4 specification.**

## 3. What was not located

The Library filename inventory and searches for the exact v1.4 title, “RDO v1.4”, and “Recursive Development Orchestrator Version 1.4” found:

- Original v1.1, v1.2 and v1.3 PDFs.
- Two byte-identical copies of v1.3.
- A pasted Claude conversation/analysis dated in its filename 21 November 2026, which discusses an alleged v1.4 and cites §§6, 7, 15, 17, 21–24, 29 and 30.

No original v1.4 PDF, DOCX or complete source text was located in the available Library material. No v1.4 branch was returned by the repository branch search. Repository code references are not substitutes for the specification they cite.

The pasted Claude conversation is commentary about a purported v1.4, not the original normative document. It includes an opinion that v1.4 was a “green light”, but it does not provide the complete source, version metadata, approval record or an auditable change history. It cannot establish approval or supersession.

The 22 November carry-over handoff independently identifies the Library v1.3 PDF as the RDO governing specification, records the v1.3/v1.4 precedence question as unresolved, and explicitly instructs the next assistant not to assume precedence or treat the pasted analysis as the original v1.4 document. The Library's source-document index also lists v1.2 and v1.3 as the original RDO PDFs; it does not list a v1.4 source.

## 4. Findings and safe interim treatment

**Established:**

1. An original v1.3 specification exists and its §16 unambiguously defines the eight-stage (0–7) RDO sequence.
2. PR #124's stage sequence is consistent with that v1.3 §16 sequence.
3. Multiple RDO foundation docstrings already cite a differently numbered v1.4 structure before PR #124.
4. The retrieved v1.3 PDF has only 20 numbered sections, so the v1.4 §23/§24 citations are not valid references to v1.3.
5. The original v1.4 source and its approval/precedence evidence have not been located in the available Library/repository material.

**Not established:**

- That v1.4 was formally issued.
- That v1.4 was approved by the founder or superseded v1.3.
- That the v1.4 references in code are accurate rather than stale, copied from a draft, or erroneous.
- That the pasted v1.4 analysis is itself an authority-bearing document.

**Interim handling (not a version-precedence decision):**

- Use the located v1.3 §16 as the source for claims about the already-merged Stage 0–7 sequence.
- Keep the v1.4 citations marked as unresolved provenance. Do not silently remap them to v1.3 or infer missing v1.4 clauses from their section numbers.
- Do not rewrite the existing code docstrings or change implementation requirements on the basis of the pasted analysis.
- Once the original v1.4 is supplied or recovered, compare its title/version/date, authorship, approval status, section text and revision history against v1.3, then map every affected code/document reference before deciding precedence.

## 5. Required founder resolution

One of the following is needed to close the authority question:

1. The original v1.4 document and, where applicable, its approval/revision record; or
2. Founder confirmation that no approved original v1.4 governs this work and that v1.3 remains the governing RDO specification.

Until then, version precedence remains **UNKNOWN**. This note records evidence; it does not make that decision.

## Scope and integrity

This audit changed no specification PDF, NEX cognitive/runtime source, live database, feature flag, experiment, baseline, tripwire or deployment setting. It does not modify the frozen consolidated NEX S-register. It does not invent an RDO Stage 8 or extend the v1.3 roadmap.

**Repository baseline for this note:** PR #124 merge commit `70db12169a8d38f2e93e6cdf536a1c71a3e66ee2`.
