"""The Recursive Extrapolator — discovers the development network hidden inside an
idea, under controlled expansion.

An idea is given as a small set of SEED obligations. Each obligation expands,
via generic engineering rules, into the sub-obligations it implies (a persistence
obligation implies a schema, a write path, provenance, a test, ...). Expansion
recurses but is bounded by stopping rules (RDO spec v1.4 §14):

  * depth cap,
  * terminal (leaf) kinds that do not decompose,
  * an obligation already satisfied by a real mechanism (reconciled REUSE_EXISTING)
    is NOT expanded — you don't rediscover the internals of something that exists.

Convergent branches merge during expansion (dedup by canonical key), so the same
obligation discovered two ways is recorded once, with both provenances. Merging is
SAFE: only obligations that mean the same thing (same kind, compatible classification)
may collapse onto one key; an incompatible collision is SURFACED as a MergeConflict,
never silently merged. Every stop is recorded with its reason, so the unresolved
frontier stays visible.
"""
from __future__ import annotations

import re
from typing import Callable, Dict, List, Optional, Tuple

from .rule_proposals import ApprovedRuleCatalogue
from .model import (ANTI_REQUIREMENT, CONDITIONAL, FUTURE, HYPOTHESIS, NECESSARY,
                    OPTIONAL, UNKNOWN, Obligation, RECON_UNKNOWN, REUSE_EXISTING,
                    SIGNATURE_MATCHED, Relationship, has_valid_reuse_review)

# classification strength, strongest -> weakest, for resolving a compatible convergence
_CLASS_RANK = {NECESSARY: 5, CONDITIONAL: 4, OPTIONAL: 3, FUTURE: 2, HYPOTHESIS: 1, UNKNOWN: 0}


class MergeConflict(ValueError):
    """Two obligations share a canonical key but do not mean the same thing. Surfaced
    rather than silently merged, so a key collision can never hide incompatible work."""

# A rule: (child_kind, classification, rationale, shared_target|None).
# shared_target lets independent parents converge on one canonical obligation.
Rule = Tuple[str, str, str, Optional[str]]

EXPANSION_RULES: Dict[str, List[Rule]] = {
    "persistence": [
        ("schema", NECESSARY, "data needs a defined schema", None),
        ("write_path", NECESSARY, "something must write the rows", None),
        ("read_path", NECESSARY, "something must read the rows", None),
        ("provenance", NECESSARY, "rows need traceable origin", None),
        ("migration", CONDITIONAL, "existing stores may need migration", None),
        ("test", NECESSARY, "persistence must be tested", None),
    ],
    "daemon": [
        ("boot_wiring", NECESSARY, "a daemon must be started at boot", None),
        ("lifecycle", NECESSARY, "start/stop/tick lifecycle", None),
        ("error_handling", NECESSARY, "errors must not propagate out of the loop", None),
        ("state_decay", CONDITIONAL, "a SentienceNode exposes state/decay", None),
        ("test", NECESSARY, "the daemon must be tested", None),
    ],
    "api": [
        ("route", NECESSARY, "an HTTP route must expose it", None),
        ("serializer", NECESSARY, "payload must be serialised", None),
        ("ui", CONDITIONAL, "a surface may consume the route", None),
        ("test", NECESSARY, "the route must be tested", None),
    ],
    "ui": [
        ("data_source", NECESSARY, "a panel needs a data source", None),
        ("test", CONDITIONAL, "UI logic may be tested", None),
    ],
    "calibration": [
        ("training_data", NECESSARY, "a fit needs labelled data", None),
        ("fit", NECESSARY, "weights must be fit and stored", None),
        ("refit_handling", CONDITIONAL, "re-fits must be handled without data loss", None),
        ("anti_second_model", ANTI_REQUIREMENT,
         "do NOT build a second/competing model when a calibrated one exists", None),
    ],
    "consumer": [
        ("read_path", NECESSARY, "a consumer reads the produced signal", None),
        ("bounded_influence", NECESSARY,
         "a consumer's influence on other nodes must be bounded (capability != authority)", None),
        ("reversibility", NECESSARY, "the influence must be reversible / flag-gated", None),
        ("gate", NECESSARY, "an active behavioural change needs a preregistered gate", None),
        # SHARED prerequisite: multiple consumers of one objective's signal are verified
        # in a SINGLE live runtime-observation session (OFT: observe once, not per consumer).
        # Independent consumer parents converge on this one obligation via `_merge`.
        ("runtime_verification", NECESSARY, "the effect must be observed at runtime",
         "shared_runtime_effect"),
        ("test", NECESSARY, "the consumer must be tested", None),
    ],
    "score": [
        ("calibration", NECESSARY, "a score must be calibrated against evidence", None),
        ("persistence", CONDITIONAL, "scores are usually persisted", None),
    ],
    # a THIRD pattern class: proactively guarding an invariant that currently holds
    # (no defect to fix) — distinct responsibility from defect remediation, so it
    # earns its own rule rather than being forced into 'defect' (OFT).
    "invariant": [
        ("specify", NECESSARY, "state the invariant precisely", None),
        ("scope", NECESSARY, "define what it ranges over, with exclusions", None),
        ("guard_test", NECESSARY, "a test that fails if the invariant is violated", None),
        ("verification", NECESSARY, "confirm the guard is non-vacuous", None),
    ],
    # a DIFFERENT development pattern: defect remediation (vs feature deployment).
    "defect": [
        ("reproduce", NECESSARY, "a defect must be reproducible before fixing", None),
        ("root_cause", NECESSARY, "fix the cause, not the symptom", None),
        ("fix", NECESSARY, "the corrective change", None),
        ("regression_test", NECESSARY, "guard against recurrence", None),
        ("migration", CONDITIONAL, "existing data may need backfill/cleanup", None),
        ("verification", NECESSARY, "confirm the defect is resolved", None),
    ],
}

# Kinds that do not decompose further.
TERMINAL_KINDS = {
    "schema", "write_path", "read_path", "provenance", "migration", "test",
    "boot_wiring", "lifecycle", "error_handling", "state_decay", "route",
    "serializer", "data_source", "training_data", "fit", "refit_handling",
    "bounded_influence", "reversibility", "gate", "runtime_verification",
    "anti_second_model", "reproduce", "root_cause", "fix", "regression_test",
    "verification", "specify", "scope", "guard_test",
}


def _child_key(parent: Obligation, child_kind: str, shared_target: Optional[str]) -> str:
    return f"{shared_target}.{child_kind}" if shared_target else f"{parent.key}.{child_kind}"


# -------- generalisation: obligation SCOPE + rule catalogue (RDO §5 of the brief) --------
# Every kind with a rule here is a GENERAL engineering pattern, reusable across domains;
# domain specificity lives only in rdo/knowledge.py seeds — the engine stays uncontaminated.

def classify_scope(ob: dict) -> str:
    """Scope of a single obligation: general | domain_specific | context_dependent |
    anti_requirement | novel. Derived from existing fields, no new state."""
    cls = ob.get("classification")
    if cls == ANTI_REQUIREMENT:
        return "anti_requirement"
    if cls == CONDITIONAL:
        return "context_dependent"
    provenance = {part.strip() for part in str(ob.get("provenance", "")).split(";")}
    if "seed" in provenance:
        return "domain_specific"          # preserve seed identity after convergent merges
    kind = ob.get("kind")
    if kind not in EXPANSION_RULES and kind not in TERMINAL_KINDS:
        return "novel"                    # no pattern covers it -> a new requirement class
    return "general"                      # produced by a general engineering rule


def scope_summary(obligations: List[dict]) -> Dict[str, List[str]]:
    out: Dict[str, List[str]] = {"general": [], "domain_specific": [], "context_dependent": [],
                                 "anti_requirement": [], "novel": []}
    for ob in obligations:
        out[classify_scope(ob)].append(ob.get("key"))
    return out


def rule_catalogue() -> dict:
    """The expansion-rule catalogue — evidence that domain rules can be reused and
    compared WITHOUT contaminating the engine."""
    return {
        "general_engineering_patterns": sorted(EXPANSION_RULES),
        "terminal_kinds": sorted(TERMINAL_KINDS),
        "domain_knowledge_location": "rdo/knowledge.py (per-domain seeds + reconciliation "
                                     "signatures) — NOT in the engine",
        "engine_contamination_check": "EXPANSION_RULES/TERMINAL_KINDS name only generic engineering "
                                      "kinds; no project-specific/domain name appears in this engine",
        "pattern_promotion_rule": "a pattern is NOT promoted for appearing twice — confidence is "
                                  "capped and rises slowly, provenance + exceptions are retained "
                                  "(memory.PatternMemory).",
    }


def expand(seeds: List[Obligation],
           reconcile_fn: Optional[Callable[[Obligation], str]] = None,
           max_depth: int = 4,
           approved_catalogue: Optional[ApprovedRuleCatalogue] = None) -> Tuple[Dict[str, Obligation], List[Relationship], List[dict]]:
    """Breadth-first controlled expansion.

    `reconcile_fn(obligation) -> recon_status` is consulted before expanding: a
    reconciled REUSE_EXISTING obligation is recorded but not expanded. Returns
    (obligations_by_key, relationships, frontier). `frontier` lists every point
    where expansion stopped, with the reason.
    """
    rules_by_kind = dict(EXPANSION_RULES)
    if approved_catalogue is not None:
        if not isinstance(approved_catalogue, ApprovedRuleCatalogue):
            raise ValueError("approved_catalogue must come from RuleProposalStore.approved_catalogue()")
        if (isinstance(approved_catalogue.version, bool)
                or not isinstance(approved_catalogue.version, int)
                or approved_catalogue.version < 1
                or not re.fullmatch(r"[0-9a-f]{64}", approved_catalogue.sha256)):
            raise ValueError("approved rule catalogue has invalid version or digest")
        for kind, rule_steps in approved_catalogue.rules.items():
            if kind in rules_by_kind or kind in TERMINAL_KINDS:
                raise ValueError(f"approved rule kind {kind!r} conflicts with a built-in rule")
            if not isinstance(kind, str) or not isinstance(rule_steps, list) or not rule_steps:
                raise ValueError("approved rule catalogue contains an invalid rule")
            for step in rule_steps:
                if (not isinstance(step, tuple) or len(step) != 4
                        or not isinstance(step[0], str) or not isinstance(step[1], str)
                        or not isinstance(step[2], str)):
                    raise ValueError(f"approved rule for {kind!r} has an invalid step")
            rules_by_kind[kind] = rule_steps
    reconcile_fn = reconcile_fn or (lambda _o: RECON_UNKNOWN)
    obligations: Dict[str, Obligation] = {}
    relationships: List[Relationship] = []
    frontier: List[dict] = []

    def _merge(ob: Obligation) -> Obligation:
        existing = obligations.get(ob.key)
        if existing is None:
            obligations[ob.key] = ob
            return ob
        # SAFE convergence — refuse to collapse obligations that do not mean the same thing:
        #   * a different KIND under one key is a genuine collision (e.g. a schema vs a daemon);
        #   * a build obligation and an ANTI_REQUIREMENT under one key is a build/don't-build
        #     contradiction. Either is surfaced, never silently merged.
        if existing.kind != ob.kind:
            raise MergeConflict(
                f"canonical key {ob.key!r} reached as kind {existing.kind!r} and {ob.kind!r} "
                f"— incompatible, not merged")
        if (existing.classification == ANTI_REQUIREMENT) != (ob.classification == ANTI_REQUIREMENT):
            raise MergeConflict(
                f"canonical key {ob.key!r} is both an anti-requirement and buildable work "
                f"({existing.classification!r} vs {ob.classification!r}) — not merged")
        # compatible: keep one record, accumulate provenance, and take the STRONGER
        # classification (recording the raise) so convergence never weakens an obligation.
        if ob.provenance not in existing.provenance:
            existing.provenance += f"; {ob.provenance}"
        for evidence_need in ob.evidence_needs:
            if evidence_need not in existing.evidence_needs:
                existing.evidence_needs.append(evidence_need)
        if (existing.classification != ob.classification
                and _CLASS_RANK.get(ob.classification, 0) > _CLASS_RANK.get(existing.classification, 0)):
            existing.note = (existing.note
                             + f" ; classification raised {existing.classification}->"
                               f"{ob.classification} on convergence").strip(" ;")
            existing.classification = ob.classification
        return existing

    queue: List[Obligation] = []
    for s in seeds:
        queue.append(_merge(s))

    while queue:
        ob = queue.pop(0)
        # A caller-supplied reuse assertion is stale until this cycle performs a
        # fresh source scan and a current semantic-satisfaction review.
        if ob.recon_status == REUSE_EXISTING:
            ob.recon_status = RECON_UNKNOWN
            ob.recon_evidence = []
            ob.recon_semantic_verified = False
            ob.recon_semantic_review_evidence = []
            ob.confidence = "inferred"
            ob.note = (ob.note + " ; prior reuse assertion invalidated; fresh review required").strip(" ;")

        # Reconcile before any stopping decision. A source signature is an anchor,
        # not proof that the existing mechanism semantically satisfies this obligation.
        if ob.recon_status == RECON_UNKNOWN:
            ob.recon_status = reconcile_fn(ob)

        # ---- stopping rules (§14) ----
        if ob.classification == ANTI_REQUIREMENT:
            frontier.append({"key": ob.key, "reason": "anti-requirement (not developed)"})
            continue
        if ob.kind in TERMINAL_KINDS:
            frontier.append({"key": ob.key,
                             "reason": f"terminal kind '{ob.kind}' (leaf; no further decomposition)"})
            continue
        if ob.depth >= max_depth:
            frontier.append({"key": ob.key, "reason": f"max_depth {max_depth} reached"})
            continue
        if ob.recon_status == REUSE_EXISTING:
            if has_valid_reuse_review(ob):
                frontier.append({"key": ob.key,
                                 "reason": "semantic satisfaction independently reviewed"})
                continue
            frontier.append({"key": ob.key,
                             "reason": "reuse status lacks semantic-review evidence; "
                                       "expanded conservatively"})
        elif ob.recon_status == SIGNATURE_MATCHED:
            frontier.append({"key": ob.key,
                             "reason": "source signature matched; semantic satisfaction unreviewed; "
                                       "expanded conservatively"})
        rules = rules_by_kind.get(ob.kind)
        if not rules:
            frontier.append({
                "key": ob.key,
                "reason": f"no expansion rule for kind '{ob.kind}'",
                "frontier_type": "novel_kind_requires_rule_proposal",
                "rule_proposal_request": {
                    "schema_version": 1,
                    "target_kind": ob.kind,
                    "source_obligation": ob.to_dict(),
                    "known_rule_kinds": sorted(rules_by_kind),
                    "terminal_kinds": sorted(TERMINAL_KINDS),
                    "proposal_requirements": [
                        "decomposition_steps",
                        "applicability_and_scope",
                        "preconditions_and_constraints",
                        "exceptions_and_anti_requirements",
                        "evidence_and_provenance",
                        "disconfirming_cases",
                        "positive_and_negative_tests",
                    ],
                    "activation_policy": "candidate_only_until_explicit_review",
                },
            })
            continue

        # ---- expand ----
        for child_kind, classification, rationale, shared in rules:
            ck = _child_key(ob, child_kind, shared)
            child = Obligation(
                key=ck, title=f"{child_kind.replace('_', ' ')} for {ob.title}",
                kind=child_kind, classification=classification,
                parent_key=ob.key, depth=ob.depth + 1, rationale=rationale,
                impact=f"Inferred impact if omitted: {rationale}",
                evidence_needs=[f"Evidence needed to verify: {rationale}"],
                confidence="inferred",
                provenance=f"expansion_rule:{ob.kind}->{child_kind}")
            merged = _merge(child)
            relationships.append(Relationship(ob.key, merged.key, "depends_on",
                                              note=rationale))
            if merged is child:  # newly added -> consider for further expansion
                queue.append(child)

    return obligations, relationships, frontier


def frontier_breakdown(frontier: List[dict]) -> Dict[str, int]:
    """Categorise frontier stops by their reason, so the complete frontier is retained but
    intentional stops are not miscounted as deferred work:
      * deferred         — budget (`max_depth`) or no expansion rule: genuinely unexpanded;
      * anti_requirement — a deliberate 'do not build' stop;
      * already_satisfied— reconciled to an existing mechanism (counted under reuse);
      * other            — any other terminal stop reason.
    """
    out = {"deferred": 0, "anti_requirement": 0, "already_satisfied": 0, "other": 0}
    for f in frontier:
        r = f.get("reason", "")
        if "max_depth" in r or "no expansion rule" in r:
            out["deferred"] += 1
        elif "anti-requirement" in r:
            out["anti_requirement"] += 1
        elif ("already satisfied" in r
              or "semantic satisfaction independently reviewed" in r):
            out["already_satisfied"] += 1
        else:
            out["other"] += 1
    return out
