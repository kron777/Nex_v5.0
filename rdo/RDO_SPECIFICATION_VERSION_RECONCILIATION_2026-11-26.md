# RDO specification-version reconciliation

**Date:** 26 November 2026  
**Status:** Original v1.4 text recovered from the founder's prior conversation attachment; version precedence remains **UNRESOLVED**.  
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

## 3. Original v1.4 source recovered; archival availability limits

The original v1.4 text **was supplied by the founder in a prior conversation on 24 November 2026**. It is not merely the later assistant-authored commentary file.

Recorded attachment metadata from that prior session:

- Title: **NEX — RECURSIVE DEVELOPMENT ORCHESTRATOR**
- Version: **1.4 — Optimal Functional Tension**
- Date: **20 November 2026**
- Status on cover: **Proposed implementation specification**
- Intended recipient: Claude / Claude Code
- Project/repository: NEX v5.0 / kron777/Nex_v5.0
- Local attachment name recorded at the time: NEX — RECURSIVE DEVELOPMENT ORCHESTRATOR## Version 1.4.txt
- Size: **47,172 bytes**
- SHA-256 recorded in the prior session: 382d634d03bc15701d9de4dcbc2629b966ffd8370c370f0307a57a853f4db926

The original text is not currently present as a standalone file in the Library inventory or either inspected NEX archive, and it is not in the repository. The metadata/hash above are recovered from the prior conversation record; the attachment bytes have not been re-hashed in this session. This is an access/archival limitation, **not evidence that the founder never supplied the original**.

The prior-session extraction identifies these v1.4 sections:

- §6 — **Capability Versus Authority**
- §15 — **Anti-Requirements**
- §17 — **Feedback Cycles**
- §24 — **The RDO Must Learn from Its Own Performance**
- §29 — **Recommended Development Order**
- §31 — governing development philosophy

The recorded §29 sequence is: repository reconciliation → Watcher → Extrapolator MVP → graph intelligence → tension assessment → belief audit → bounded pathway → learning loop → expansion. This is a recovered summary of the founder-supplied source, not a fresh byte-level transcription; exact numbered stage labels, exit conditions and surrounding wording are not reproduced here until the original attachment is available for direct reinspection.

### Approval and precedence evidence

When asked on 24 November whether v1.4 had been approved, the founder replied: **“yeah i think i did, we devd RDO couple days ago”**. This supports that v1.4 was intended as the current working specification. It is not an unambiguous written Founder Sign-Off or an explicit statement that v1.4 formally supersedes v1.3. The cover itself says “Proposed implementation specification”. Therefore, do not upgrade this evidence into a claim that v1.4 was formally frozen or that version precedence was settled.

The separate file Pasted text(20261121-011034).txt is assistant-authored commentary discussing v1.4. Its opinion that v1.4 was a “green light” is not the original specification and is not approval evidence.

The 22 November carry-over handoff correctly instructed the next assistant not to assume v1.3/v1.4 precedence. Its statement that no original v1.4 had been located is now superseded by the recovered 24 November founder-attachment record. The distinction remains: v1.4 was supplied; formal supersession/approval remains unresolved.

## 4. Findings and safe interim treatment

**Established:**

1. The original v1.3 PDF exists; its §16 unambiguously defines Stage 0–7, including Stage 7 execution integration through Watcher.
2. PR #124's integrated Stage 2–7 sequence is consistent with v1.3 §16.
3. The founder also supplied the original v1.4 text in a prior conversation; its cover status is “Proposed implementation specification”, and its recorded section structure extends through §31.
4. v1.4 contains substantive concepts not represented by the v1.3 section numbering, including capability-versus-authority (§6), anti-requirements (§15), feedback cycles (§17), learning from RDO performance (§24), and a distinct recommended development order (§29).
5. The recorded v1.4 §29 order includes a tension-assessment step and a later expansion step, so it is not safe to describe the v1.3 Stage 0–7 sequence as a complete implementation of v1.4.
6. The v1.4 attachment's prior-session metadata and SHA-256 are known, but its raw bytes are not available in the current Library/repository for a fresh hash or full section-by-section comparison.

**Not established:**

- That v1.4 was formally frozen or signed off.
- That the founder's recollection on 24 November constitutes explicit approval or formally supersedes v1.3.
- That all pre-existing v1.4 code citations accurately implement the corresponding v1.4 clauses.
- That the v1.3 Stage 0–7 sequence should be replaced, renumbered or retroactively reinterpreted under v1.4.

**Interim handling (not a version-precedence decision):**

- Use v1.3 §16 when describing the sequence actually implemented and merged through PR #124.
- Treat founder-supplied v1.4 as the intended current working specification for comparison, but do not claim formal supersession until the founder confirms the precedence decision.
- Preserve v1.4 citations in code as unresolved provenance; do not silently remap them to v1.3.
- Do not rewrite the existing stage documents, code docstrings or implementation requirements until the exact v1.4 source is available for direct comparison and the founder confirms which version governs.

## 5. Required founder resolution

The original v1.4 text has already been supplied by the founder; asking the founder to re-supply it should not be the default. To complete the direct section-by-section comparison, the original 47,172-byte attachment must be available again in the active working context, or an equivalent exact source copy must be made accessible.

The remaining founder decision is narrow:

**Does RDO v1.4 — Optimal Functional Tension formally supersede v1.3 as the governing RDO specification for future work, or should v1.3 §16 remain the controlling roadmap while v1.4 is treated as a proposed/current-working refinement pending explicit sign-off?**

Until that precedence decision is explicit, version precedence remains **UNKNOWN**. This note records evidence; it does not make that decision.

## Scope and integrity

This audit changed no specification PDF, NEX cognitive/runtime source, live database, feature flag, experiment, baseline, tripwire or deployment setting. It does not modify the frozen consolidated NEX S-register. It does not invent an RDO Stage 8 or extend the v1.3 roadmap.

**Repository baseline for this note:** PR #124 merge commit `70db12169a8d38f2e93e6cdf536a1c71a3e66ee2`.
