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
obligation discovered two ways is recorded once, with both provenances. Every
stop is recorded with its reason, so the unresolved frontier stays visible.
"""
from __future__ import annotations

from typing import Callable, Dict, List, Optional, Tuple

from .model import (ANTI_REQUIREMENT, CONDITIONAL, NECESSARY, Obligation,
                    RECON_UNKNOWN, REUSE_EXISTING, Relationship)

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
        ("runtime_verification", NECESSARY, "the effect must be observed at runtime", None),
        ("test", NECESSARY, "the consumer must be tested", None),
    ],
    "score": [
        ("calibration", NECESSARY, "a score must be calibrated against evidence", None),
        ("persistence", CONDITIONAL, "scores are usually persisted", None),
    ],
}

# Kinds that do not decompose further.
TERMINAL_KINDS = {
    "schema", "write_path", "read_path", "provenance", "migration", "test",
    "boot_wiring", "lifecycle", "error_handling", "state_decay", "route",
    "serializer", "data_source", "training_data", "fit", "refit_handling",
    "bounded_influence", "reversibility", "gate", "runtime_verification",
    "anti_second_model",
}


def _child_key(parent: Obligation, child_kind: str, shared_target: Optional[str]) -> str:
    return f"{shared_target}.{child_kind}" if shared_target else f"{parent.key}.{child_kind}"


def expand(seeds: List[Obligation],
           reconcile_fn: Optional[Callable[[Obligation], str]] = None,
           max_depth: int = 4) -> Tuple[Dict[str, Obligation], List[Relationship], List[dict]]:
    """Breadth-first controlled expansion.

    `reconcile_fn(obligation) -> recon_status` is consulted before expanding: a
    reconciled REUSE_EXISTING obligation is recorded but not expanded. Returns
    (obligations_by_key, relationships, frontier). `frontier` lists every point
    where expansion stopped, with the reason.
    """
    reconcile_fn = reconcile_fn or (lambda _o: RECON_UNKNOWN)
    obligations: Dict[str, Obligation] = {}
    relationships: List[Relationship] = []
    frontier: List[dict] = []

    def _merge(ob: Obligation) -> Obligation:
        existing = obligations.get(ob.key)
        if existing is None:
            obligations[ob.key] = ob
            return ob
        # convergent discovery: keep one record, accumulate provenance
        if ob.provenance not in existing.provenance:
            existing.provenance += f"; {ob.provenance}"
        return existing

    queue: List[Obligation] = []
    for s in seeds:
        queue.append(_merge(s))

    while queue:
        ob = queue.pop(0)
        # reconcile first so stopping can consult "already exists"
        if ob.recon_status == RECON_UNKNOWN:
            ob.recon_status = reconcile_fn(ob)

        # ---- stopping rules (§14) ----
        if ob.classification == ANTI_REQUIREMENT:
            frontier.append({"key": ob.key, "reason": "anti-requirement (not developed)"})
            continue
        if ob.kind in TERMINAL_KINDS:
            continue
        if ob.depth >= max_depth:
            frontier.append({"key": ob.key, "reason": f"max_depth {max_depth} reached"})
            continue
        if ob.recon_status == REUSE_EXISTING:
            frontier.append({"key": ob.key,
                             "reason": "already satisfied by an existing mechanism; not expanded"})
            continue
        rules = EXPANSION_RULES.get(ob.kind)
        if not rules:
            frontier.append({"key": ob.key, "reason": f"no expansion rule for kind '{ob.kind}'"})
            continue

        # ---- expand ----
        for child_kind, classification, rationale, shared in rules:
            ck = _child_key(ob, child_kind, shared)
            child = Obligation(
                key=ck, title=f"{child_kind.replace('_', ' ')} for {ob.title}",
                kind=child_kind, classification=classification,
                parent_key=ob.key, depth=ob.depth + 1, rationale=rationale,
                provenance=f"expansion_rule:{ob.kind}->{child_kind}")
            merged = _merge(child)
            relationships.append(Relationship(ob.key, merged.key, "depends_on",
                                              note=rationale))
            if merged is child:  # newly added -> consider for further expansion
                queue.append(child)

    return obligations, relationships, frontier
