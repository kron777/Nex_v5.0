# NEX Recursive Development Orchestrator v1.4
## Reconstructed evidence edition — 26 November 2026

> **DOCUMENT STATUS: NON-NORMATIVE EVIDENCE RECONSTRUCTION. NOT THE ORIGINAL v1.4. INCOMPLETE. The founder indicated on 24 November that v1.4 was the intended current working specification; formal freeze/supersession is not recorded in the consolidated NEX register.**
>
> This file reconstructs only those portions of the RDO document labelled “v1.4” that can be traced to surviving contemporaneous review notes, implementation references, repository history, and predecessor specifications. It does not reproduce lost text, establish authorship, establish founder approval, or supersede any governing specification. Descriptive section labels in this file are working labels, not recovered original headings. Any unlocated wording remains **UNKNOWN**.

**Purpose.** Preserve the recoverable design evidence behind the v1.4 references already embedded in the RDO implementation, and provide a traceable basis for a later comparison if the original is recovered. This is an evidence reconstruction, not a replacement specification or a new implementation mandate.

---

## 1. Executive finding

There is substantial evidence that a document or working draft called **RDO v1.4** was being discussed and used as a source for the first RDO implementation around 21 November 2026:

- A contemporaneous Claude review discusses concrete v1.4 sections, including §§6, 7, 7.2, 8, 15, 17, 21, 21.3, 22, 23, 24, 29 and 30. It reports an approximately 12-module architecture and an eight-stage development plan.
- The first RDO code commit, `34433984d964a03f5157e049a857c650a95debe4` (21 November 2026, 01:31:19 UTC), independently cites v1.4 in implementation docstrings: `model.py` §3.4; `extrapolator.py` §14; `tension.py` Part II and §4; `prioritise.py` §23; `memory.py` §24, Part VIII; `reconcile.py` §13 step 5 and §30; `tests/test_rdo.py` §28, Part X; and `__init__.py` §26, Part VII.
- Founder-authored repository issue [#89](https://github.com/kron777/Nex_v5.0/issues/89) records further source references and explicitly asks for the original and its approval record to be recovered before any version-precedence decision.

However, no original v1.4 PDF, DOCX, Markdown source, complete transcript, or approval/revision record was found in the available Library, conversation attachments, two archived development packages, current repository tree, or inspected RDO-related branch snapshots. The contemporaneous review is a secondary interpretation, not the specification itself.

**Result:** the use of a v1.4-labelled source is well supported; the precise full text and formal status of that source are not. This reconstruction recovers a bounded subset of its apparent requirements. The founder indicated on 24 November that v1.4 was the intended current working specification. This reconstruction does not claim a formal frozen-spec record or retroactively replace v1.3 history.

## 2. Evidence classes and source hierarchy

The following hierarchy is used throughout. A code comment proves that the implementation cited a section; it does not prove the missing section's exact wording.

| ID | Evidence | What it can establish | What it cannot establish |
|---|---|---|---|
| **P1** | Original RDO v1.1, v1.2 and v1.3 PDFs in the Library | Actual text and chronology of the predecessor specifications; established ideas and v1.3 Stage 0–7 order | The wording or approval of v1.4 |
| **P2** | `Pasted text(20261121-011034).txt`, contemporaneous Claude review of Watcher v3 and RDO v1.4 | A dated secondary account of specific v1.4 section contents, its reported modules/stages, and quoted distinctions | Verbatim primary text, authorship, completeness, or founder approval |
| **P3** | Initial RDO implementation commit `34433984…` and its exact source at that commit | Which v1.4 sections the first implementation believed it was following, and what concrete behaviour was implemented | That the code is a correct or complete transcription of the specification |
| **P4** | Founder-authored repository issue [#89](https://github.com/kron777/Nex_v5.0/issues/89), 25 November 2026 | The provenance discrepancy, additional section references, and the explicit requirement to retrieve and crosswalk before deciding precedence | The original document or its approval |
| **P5** | `rdo/STAGE2_EXTRAPOLATOR_MVP.md`, `rdo/README.md`, stage reports and later source | Later implementation interpretation, tests, boundaries, and the fact that staged development documents use v1.3 §16 | The missing v1.4 source text |
| **P6** | `carry_over.txt`, `NEX_dev_carry_over.txt`, `SOURCE_DOCUMENT_INDEX.md` and archived packages | The interim source-control position and what was preserved in the handover archives | Proof that no v1.4 draft ever existed outside the searched material |

### Search coverage completed

1. The paginated Library inventory returned 331 files. The named original RDO PDFs found there are v1.1, v1.2 and v1.3, with a byte-identical duplicate of v1.3. The current conversation attachment inventory contains 27 items and likewise has no v1.4 original.
2. Both archived development packages were materialised and their full entry lists inspected: `NEX_Claude_Development_Export.zip` and `NEX_Development_Archive_for_Claude.zip`. They preserve v1.1, v1.2 and v1.3, but no v1.4 file.
3. The current `main` Git tree (925 entries) contains no v1.4 specification file. RDO-related branch trees were inspected across the Stage 2–7 branches, the RDO reliability/orchestrator branches, hardening/integration branches, and the specification-reconciliation branch; no original v1.4 document was found.
4. Library and conversation searches included the exact title/version, section references, unique quoted feedback-cycle sentence, the prioritisation expression, anti-requirements, and the one-vertical-slice directive. The only located v1.4-specific narrative is the 21 November review noted above.
5. Repository issue #89 has no comments or attached source that supply the missing document.

This search cannot rule out a file in an unconnected drive, local machine, external Claude project, or unindexed attachment. It does rule out the document being present in the currently available source set checked here.

## 3. Version lineage and chronology

| Date / source | Recovered fact | Relevance |
|---|---|---|
| 20 Nov 2026 — v1.1 PDF | 26-page predecessor, 16 numbered sections | Early RDO architecture and staged plan |
| 20 Nov 2026 — v1.2 PDF | 20-page revision, 16 numbered sections | Refines dependency analysis, priority, beliefs, integration, architecture, safety and acceptance criteria |
| 20 Nov 2026 — v1.3 PDF | 22 pages, 20 numbered sections; substantially reorganised around expansion, obligations, graph, prioritisation, deduplication, learning and the roadmap | The located later working specification; §16 explicitly defines Stages 0–7 |
| 21 Nov 2026, around 01:10 UTC — review record P2 | Claude discusses RDO v1.4 as the layer above Watcher v3 and comments on specific v1.4 sections | First located v1.4-specific narrative |
| 21 Nov 2026, 01:31:19 UTC — initial RDO commit P3 | First vertical-slice code cites v1.4 sections across eight implementation/test files | Contemporaneous implementation provenance |
| 22 Nov 2026 — development archive/handover P6 | Archives preserve v1.1–v1.3; carry-over instructs retrieval of a genuine v1.4 if it exists and warns not to infer approval | v1.4 status was still unresolved in the handover |
| 25 Nov 2026 — issue #89 P4 | Explicitly records the section references and requests the original plus approval record | Confirms the issue was intentionally left open |
| 26 Nov 2026 — PR #126 | Adds a non-normative evidence note to `main`; does not choose precedence | Preserves the verified position pending recovery |

### Important predecessor-version continuity

The v1.2 PDF's §6.3 and v1.3 PDF's §8 both contain the same eight-factor advisory prioritisation expression:

`P = 20D + 20L + 15A + 15R + 10U + 10O + 5S + 5E`

The 21 November review says the v1.4 Pareto framing and `P = 20D+20L+…` weights are illustrative and uncalibrated. This is a credible continuity clue, not proof that v1.4 retained the exact formula or its definitions. The v1.4 section numbers differ materially from the predecessor documents, so old section numbers must not be mechanically transferred.

## 4. Reconstructed v1.4 section evidence

The table deliberately separates **reported content**, **implementation evidence**, and **confidence**. Working labels below describe the evidence; they are not claimed to be original headings.

| v1.4 locus | Recoverable content (paraphrase unless quoted) | Implementation / corroboration | Confidence and limit |
|---|---|---|---|
| **§3.4** | Obligation classification. The surviving implementation defines `necessary`, `conditional`, `optional`, `future`, `hypothesis`, `unknown`, and `anti_requirement`. | Initial `rdo/model.py` lines 13–22 explicitly label this taxonomy “RDO spec v1.4 §3.4”. | **High** that the code was mapped to §3.4; **medium** that this is the complete v1.4 taxonomy. No original prose. |
| **Part II; §4** | Optimal Functional Tension (OFT): a structured assessment, not a single magic score; inspect node, relationship and system levels; make evidence-backed verdicts distinct from inference; recognise sufficiency and when not to develop further. | Initial `rdo/tension.py` lines 1–7 explicitly cite Part II and §4. The source implements underdeveloped / sufficient / overdeveloped / unknown verdicts, with an `inference` flag and separate evidence. | **High** for the implementation mapping and core idea; exact definition, dimensions and thresholds are **UNKNOWN**. |
| **§5** | The section is cited in the Stage 2 discrepancy note's list of v1.4 references, but no independent surviving description identifies its subject. | `rdo/STAGE2_EXTRAPOLATOR_MVP.md` lines 88–93. | **Low**. Content and heading remain **UNKNOWN**; do not infer from neighbouring sections. |
| **§6** | Capability is not authority. A mechanism's ability to influence multiple others does not by itself grant permission to do so; influence should have bounded authority. | Initial `rdo/model.py` line 75 gives relationship authority levels `none`, `bounded`, `strong` and cites §6. Initial `rdo/tension.py` lines 51–56 flags an `influences` relationship without bounded authority. The review explicitly summarises “capability ≠ authority”. | **High** for the principle; exact policy, authority levels and decision procedure may have been broader. |
| **§7; §7.2** | A Pareto framing is reported in §7. The review associates §7.2 with avoiding false precision. | Review P2. Predecessor v1.2 §6.3 / v1.3 §8 contain an illustrative weighted priority formula and caution against false precision. | **Medium** that these topics appear in the cited sections; actual Pareto model, equation, examples and wording are **UNKNOWN**. Do not substitute the predecessor formula as v1.4 text. |
| **§8** | Also identified by the review as a place where false precision is cautioned against. | Review P2; predecessor v1.3 §8 has a transparent advisory priority score behind a hard-constraint gate. | **Low–medium**. Exact subject and text are **UNKNOWN**. |
| **§13, step 5** | Repository reconciliation before recommending work: inspect the real tree read-only and use actual evidence to distinguish existing, partial, missing and unknown mechanisms. | Initial `rdo/reconcile.py` line 2 explicitly cites “§13 step 5”; its implementation searches the repository and records evidence. Later hardening further distinguishes a source anchor from semantic satisfaction. | **High** for the implementation mapping; original acceptance rules and whether the section defined additional evidence sources are **UNKNOWN**. |
| **§14** | Bounded recursive expansion and stopping rules: depth cap; terminal kinds; do not recursively rediscover the internals of an already-satisfied real mechanism; retain the frontier and reason for each stop. | Initial `rdo/extrapolator.py` lines 1–16 explicitly cite §14; code contains depth and terminal stops and stops expansion on confirmed reuse. | **High** for these core rules; full budget, exception and stopping calculus is **UNKNOWN**. |
| **§15** | Anti-requirements: discover and preserve what must deliberately **not** be built. This includes avoiding duplicate mechanisms or a competing graph model when an existing authoritative structure should be reused. | Review P2 explicitly calls anti-requirements the heart of §15 and mentions avoiding a competing graph model. Initial RDO code has `ANTI_REQUIREMENT`, anti-requirement expansion rules, and packages that carry explicit “do not build” constraints. | **High** for the principle; complete anti-requirement taxonomy and review procedure are **UNKNOWN**. |
| **§17** | Distinguish evidence maturity. The contemporaneous review quotes: “A documented cycle is not necessarily implemented. An implemented cycle is not necessarily test-verified. A test-verified cycle is not necessarily demonstrated in live runtime.” | Review P2. The same development cycle records separate `source_implemented`, `test_verified` and `runtime_observed` dimensions in the adjacent Watcher implementation. RDO tests do not claim live runtime. | **High** that the distinction was reported; exact formal status vocabulary, transitions and enforcement rules remain **UNKNOWN**. |
| **§20** | A signal's influence/authority must be assessed, not inferred from raw capability or consumer count alone. | Initial `rdo/tension.py` documentation and later source refer to v1.4 §§6/20 for signal authority; `assess_signal_authority` examines relationship type, directness, conditions, magnitude, safeguards and evidence class. | **Medium** for the topic association; full §20 content and its relation to §6 are **UNKNOWN**. |
| **§21** | The review reports an architecture of approximately twelve modules. | Review P2. The initial implementation commit introduces `model`, `extrapolator`, `reconcile`, `tension`, `prioritise`, `memory`, `knowledge`, `orchestrator`, and CLI support. | **Medium** that the specification listed roughly twelve modules; exact list, responsibilities, boundaries and module count are **UNKNOWN**. The implementation list is not a substitute. |
| **§21.3** | A critical LLM boundary: proposals from an LLM are not authoritative state. | Review P2. Initial model records distinguish seed / expansion-rule / reconciled provenance; the package documentation says LLM/heuristic proposals must not silently become authoritative. | **High** for the reported rule; exact validation schema and enforcement language are **UNKNOWN**. |
| **§22** | LLM outputs remain proposals, not authoritative state; every obligation needs provenance, and the system must not silently overwrite authoritative records. | Review P2 states the principle directly and says it should be enforced mechanically. Initial `Obligation.provenance` records `seed`, `expansion_rule:<name>` or `reconciled`; the package has an explicit no-silent-authority guarantee. | **High** for the core requirement; exact conflict-resolution and mutation protocol is **UNKNOWN**. |
| **§23** | Two-stage prioritisation. First determine eligibility using hard constraints that a high score cannot override; only then compare eligible work on separately reported dimensions. Any provisional weighted value is uncalibrated. Work packages preserve anti-requirements. | Initial `rdo/prioritise.py` lines 1–12 explicitly cite §23 and describe these two stages. Code blocks gated behavioural work, protected experiments, missing prerequisites and host-only runtime verification, and labels its sort score uncalibrated. | **High** for the implemented mapping; exact v1.4 factors, weights and eligibility predicates are **UNKNOWN**. |
| **§24; Part VIII** | Learning and anti-gaming. Do not reward lines of code, task count or expansion depth; reward accurate discovery, low rework and appropriate simplicity; preserve negative results. Learn by comparing predictions with actual outcomes, without promoting one success into a universal rule. | Initial `rdo/memory.py` line 1 cites §24, Part VIII. Code stores predicted/actual outcomes, candidate lessons, applicability and exceptions; initial confidence is 0.3, capped at 0.9, and the trend report refuses an acceleration claim before enough completed cycles. The review explicitly describes the anti-gaming rule set. | **High** for the core learning model and anti-gaming summary; full measures, denominators and thresholds are **UNKNOWN**. |
| **§26; Part VII** | Separation of roles: NEX is the cognitive architecture; Watcher observes and provides evidence read-only; RDO performs advisory development reasoning; Claude executes bounded authorised work; the human owns objectives and consequential decisions. | Initial `rdo/__init__.py` lines 7–12 explicitly cite §26, Part VII and enumerate these five roles. | **High** for this boundary model; full permission matrix and exceptions are **UNKNOWN**. |
| **§28; Part X** | Adversarial and isolation-focused tests. The reviewable first suite covers incomplete information, duplicate discovery, false dependencies, feedback cycles, over-expansion, under-expansion, inappropriate reuse, pattern-memory non-promotion, learning, and the independence guarantee; plus a real-repository smoke test. | Initial `rdo/tests/test_rdo.py` lines 1–7 explicitly cite §28, Part X and enumerate these test cases. The initial RDO commit reports 15 tests passing. | **High** for the initial test scope; unknown whether §28 required more cases, coverage thresholds or runtime tests. |
| **§29** | Eight development stages are reported, with Stage 0 inspecting PR #46 and CI. The next specified build action is a Stage 2 external RDO vertical slice. | Review P2. v1.3 §16 separately gives a confirmed Stage 0–7 sequence (see §5 below); RDO stage reports explicitly cite v1.3 §16 for implemented stages. | **Medium** that v1.4 had eight stages and the reported Stage 0/Stage 2 descriptions; the complete v1.4 stage list and exact wording are **UNKNOWN**. Do not assume it is identical to v1.3. |
| **§30** | Build one thin, real vertical slice first rather than implementing the whole future architecture. The review's target is one real NEX idea in → one traceable, bounded plan out, with the learning ledger capturing whether the expansion was accurate. | Review P2. Initial `rdo/reconcile.py` cites §30 for repository reconciliation before work is proposed; the RDO Stage 2 implementation report makes this a one-objective vertical slice. | **High** for the directive; exact acceptance criteria and all prerequisites in §30 are **UNKNOWN**. |

### Unrecovered loci

No reliable content was found for the remainder of the section structure, including §§1–3.3, any unreferenced part of §3, the actual subject of §5, §§9–12, §16, §§18–19, §§25 and §27, or any sections beyond the references above. Some may have existed and simply have no surviving fragments. Their headings, prose, tables, equations and acceptance criteria must remain **UNKNOWN**.

The only surviving Part labels are **Part II**, **Part VII**, **Part VIII** and **Part X**. The titles and contents of the other Parts are not recoverable from the evidence examined.

## 5. Recovered Stage 0–7 context — predecessor evidence, not a v1.4 transcription

The original v1.3 PDF's §16 is the strongest primary source for the staged order actually preserved in the Library. It defines:

| Stage | v1.3 §16 sequence | Evidence status |
|---:|---|---|
| 0 | Reconcile Watcher PR #46, CI, branches, unfinished work and repository SHA | **Primary v1.3 text verified** |
| 1 | Complete the Watcher increment | **Primary v1.3 text verified** |
| 2 | Extrapolator MVP | **Primary v1.3 text verified** |
| 3 | Graph intelligence | **Primary v1.3 text verified** |
| 4 | Read-only belief audit | **Primary v1.3 text verified** |
| 5 | First belief-to-mechanism pathway | **Primary v1.3 text verified** |
| 6 | Learning loop | **Primary v1.3 text verified** |
| 7 | Execution integration through Watcher | **Primary v1.3 text verified** |

The v1.4 review independently reports eight stages, names Stage 0 as inspection of PR #46 and CI, and says the real immediate deliverable is Stage 2: one separate external vertical slice, with an obligation record, bounded recursive expansion, deduplication, anti-requirements, stopping rules, one work package and a learning ledger. Those details are compatible with the v1.3 sequence and the initial implementation, but the full v1.4 §29 roadmap is not present. Therefore the table above must not be represented as a verbatim recovery of v1.4 §29.

## 6. Implementation correspondence at the first RDO commit

The first RDO commit added an external, advisory package as a sibling of `watcher/`. Its commit message describes a bounded cycle:

`IDEA → recursive expansion → repository reconciliation → deduplication / false-dependency pruning → relationship mapping → Optimal Functional Tension → two-stage prioritisation → work package with anti-requirements → verification → pattern memory / learning`.

The initial implementation was constrained to consume Watcher evidence and not import NEX's cognitive runtime (`theory_x` / `substrate`), with a test enforcing that boundary. Its real-repository demonstration reused existing mechanisms when evidence supported reuse and blocked the genuinely new retrieval/behavioural work pending a preregistered gate. It did not claim live runtime evidence or accelerated development.

Primary implementation reference: [initial RDO commit `34433984d964a03f5157e049a857c650a95debe4`](https://github.com/kron777/Nex_v5.0/commit/34433984d964a03f5157e049a857c650a95debe4). This is strong evidence of what the first implementation attempted to express, but cannot replace the missing spec.

Later RDO stage reports consistently identify **v1.3 §16** as the governing stage sequence. The current `rdo/README.md` explicitly notes that some pre-existing docstrings cite v1.4 and that version precedence has not been inferred. The Stage 2 report lists the v1.4 references and explicitly says no version reconciliation is asserted. This distinction should be preserved.

## 7. Interim authority and handling rules

1. **This reconstruction is not normative.** Do not cite it as the approved RDO specification or present its paraphrases as direct quotations from the missing PDF.
2. **Keep v1.3 §16 as the verified source for the Stage 0–7 sequence** until the actual v1.4 and its status can be compared. This is the position stated in the existing handover and source index.
3. **Do not mechanically remap v1.4 section numbers onto v1.3.** The numbering and structure differ; some v1.4 section references have no direct equivalent in the recovered v1.3 outline.
4. **Do not alter behaviour or remove useful implementation solely to erase a version label.** First compare the implementation against verified requirements and preserve independently justified behaviour.
5. **Do not infer missing clauses.** Unrecovered thresholds, scoring weights, module inventories, stopping rules, stage wording and test requirements remain unknown.
6. **Do not promote implementation comments to authority.** A code comment is evidence of the source the author believed they were following, not proof that the source was correct, complete or approved.
7. **No NEX cognitive/runtime, frozen register, live database, feature-flag, protected-experiment, host, deployment or service changes are authorized by this reconstruction.** RDO remains an external advisory engineering tool.

## 8. What would close the provenance gap

The preferred evidence is the actual v1.4 PDF or editable source, plus any cover/version metadata, revision history, transmission context and explicit founder approval (or explicit indication that it was only a draft/proposal). If the original is recovered, compare it section-by-section against:

- the original v1.2 and v1.3 PDFs;
- the v1.4 references in the first RDO commit;
- the initial and current RDO implementations and their tests;
- the 21 November review record;
- the v1.3 §16 stage sequence and the later Stage 2–7 reports.

For each requirement, record: exact source clause; whether it changed from v1.3; implementation location; test/evidence; any gap; and whether the clause carries authority or is merely advisory. Only then can precedence and any source-reference corrections be decided.

---

## 9. Source register

### Original predecessor specifications

- **RDO v1.1** — `NEX_Recursive_Development_Orchestrator_Specification_v1.1.pdf`, Library file ID `file_0000000012b0820e97e34c43e66dca38`.
- **RDO v1.2** — `NEX_Recursive_Development_Orchestrator_Specification_v1.2.pdf`, Library file ID `file_00000000ab78820e9773a86e5f30f6fe`.
- **RDO v1.3** — `NEX_Recursive_Development_Orchestrator_Specification_v1.3.pdf`, Library file ID `file_000000005dbc820e84551e4034a7e0f3`. The duplicate file is byte-identical; SHA-256: `81a268f54e1dca7464ba43a3adb2637665c8f0ee8fb0a97632a8d079b3f23e8b`.

### v1.4-specific secondary and implementation evidence

- **Contemporaneous review** — `Pasted text(20261121-011034).txt`, Library/Conversation file ID `file_00000000d100820ebd7f5f4394a7304c`.
- **First RDO implementation** — commit [`34433984d964a03f5157e049a857c650a95debe4`](https://github.com/kron777/Nex_v5.0/commit/34433984d964a03f5157e049a857c650a95debe4).
- **Founder-authored provenance issue** — [NEX_v5.0 issue #89](https://github.com/kron777/Nex_v5.0/issues/89).
- **Stage 2 evidence** — [`rdo/STAGE2_EXTRAPOLATOR_MVP.md`](https://github.com/kron777/Nex_v5.0/blob/main/rdo/STAGE2_EXTRAPOLATOR_MVP.md), particularly its specification-discrepancy note and §15 acceptance audit.
- **Current RDO overview** — [`rdo/README.md`](https://github.com/kron777/Nex_v5.0/blob/main/rdo/README.md), particularly the v1.3 §16 stage map and version-precedence note.

### Authority / handover evidence

- `SOURCE_DOCUMENT_INDEX.md`, Library file ID `file_0000000062c0820e80af263c48b72f54`.
- `carry_over.txt`, Library file ID `file_000000003440820eb523e0d07a06bc3d`.
- `NEX_dev_carry_over.txt`, Library/Conversation file ID `file_0000000098ac820e91d8e1869dcbdfb3`.

**Final status:** Partial evidence reconstruction completed. Founder-supplied v1.4 is the current working RDO specification; v1.3 remains historical. Formal freeze/supersession is not recorded in the consolidated NEX register. The raw v1.4 bytes are not mounted in the current workspace for fresh byte-level comparison.
