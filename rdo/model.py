"""RDO data model — the records the pipeline produces and persists.

Everything is a plain dataclass with `to_dict()` so cycles serialise to JSON and
resume after interruption. Nothing here reasons; the engine modules do.
"""
from __future__ import annotations

import dataclasses
import datetime
from typing import Any, Dict, List, Optional

from watcher.evidence import utc_now  # reuse Watcher infra (RDO obeys OFT: don't rebuild)

# ---- obligation classification (RDO spec v1.4 §3.4) ----
NECESSARY = "necessary"
CONDITIONAL = "conditional"
OPTIONAL = "optional"
FUTURE = "future"
HYPOTHESIS = "hypothesis"
UNKNOWN = "unknown"
ANTI_REQUIREMENT = "anti_requirement"
CLASSIFICATIONS = (NECESSARY, CONDITIONAL, OPTIONAL, FUTURE, HYPOTHESIS, UNKNOWN,
                   ANTI_REQUIREMENT)

# ---- reconciliation outcome (vs the real codebase) ----
SIGNATURE_MATCHED = "signature_matched"  # configured source signatures matched; not semantic satisfaction
REUSE_EXISTING = "reuse_existing"   # semantic satisfaction separately reviewed
PARTIAL = "partial"                 # some evidence, not complete
MISSING = "missing"                 # no mechanism found
RECON_UNKNOWN = "unknown"           # no signature to check -> honest inference
RECON_STATES = (SIGNATURE_MATCHED, REUSE_EXISTING, PARTIAL, MISSING, RECON_UNKNOWN)


def _has_traceable_evidence(value) -> bool:
    """Evidence fields must be non-empty lists of non-blank text references."""
    return (isinstance(value, list) and bool(value) and
            all(isinstance(item, str) and bool(item.strip()) for item in value))


def has_valid_reuse_review(obligation) -> bool:
    """Return whether an obligation carries the evidence required for reuse.

    Accept both the dataclass used by reconciliation and serialized obligation
    dictionaries used by cycle metrics. Both evidence lists must contain only
    non-blank text references; a truthy container is not sufficient evidence.
    """
    if isinstance(obligation, dict):
        get = obligation.get
    else:
        get = lambda name, default=None: getattr(obligation, name, default)
    return bool(
        _has_traceable_evidence(get("recon_evidence")) and
        get("confidence") == "measured" and
        get("recon_semantic_verified") is True and
        _has_traceable_evidence(get("recon_semantic_review_evidence"))
    )

# ---- functional-tension verdicts (OFT) ----
UNDERDEVELOPED = "underdeveloped"
SUFFICIENT = "sufficient"
OVERDEVELOPED = "overdeveloped"
TENSION_UNKNOWN = "unknown"


@dataclasses.dataclass
class Obligation:
    """One discovered development obligation. `key` is the stable, canonical
    identity used for deduplication; `id` mirrors it."""
    key: str
    title: str
    kind: str                       # persistence|daemon|boot_wiring|api|ui|provenance|
                                    # test|consumer|calibration|runtime_verification|...
    classification: str = NECESSARY
    parent_key: Optional[str] = None
    depth: int = 0
    rationale: str = ""
    provenance: str = "seed"        # seed | expansion_rule:<name> | reconciled
    assumptions: List[str] = dataclasses.field(default_factory=list)
    recon_status: str = RECON_UNKNOWN
    recon_evidence: List[str] = dataclasses.field(default_factory=list)
    # Source-anchor matches do not establish semantic satisfaction. A reviewed
    # reuse claim needs both an explicit decision and traceable review evidence.
    recon_semantic_verified: bool = False
    recon_semantic_review_evidence: List[str] = dataclasses.field(default_factory=list)
    confidence: str = "stated"      # stated | measured | inferred
    note: str = ""
    impact: Optional[str] = None  # consequence if this obligation is omitted
    # Required proof needs for this candidate; these are requests for evidence, not evidence itself.
    evidence_needs: List[str] = dataclasses.field(default_factory=list)

    def __post_init__(self) -> None:
        if self.classification not in CLASSIFICATIONS:
            raise ValueError(f"bad classification {self.classification!r}")
        if self.recon_status not in RECON_STATES:
            raise ValueError(f"bad recon_status {self.recon_status!r}")
        self.id = self.key

    def to_dict(self) -> dict:
        d = dataclasses.asdict(self)
        d["id"] = self.key
        return d


INTERFACE_EVIDENCE_STATUSES = ("measured", "implemented", "static", "inferred", "unknown")


@dataclasses.dataclass
class InterfaceEvidence:
    """One interface dimension with explicit UNKNOWN-by-default evidence state.

    Values and thresholds are deliberately not inferred. A populated value is only
    meaningful alongside its unit (where applicable), evidence references and
    confidence/provenance supplied by the assessor.
    """
    status: str = "unknown"
    value: Any = None
    unit: Optional[str] = None
    evidence: List[str] = dataclasses.field(default_factory=list)
    confidence: Optional[str] = None

    def __post_init__(self) -> None:
        if self.status not in INTERFACE_EVIDENCE_STATUSES:
            raise ValueError(f"invalid interface evidence status: {self.status!r}")


@dataclasses.dataclass
class InterfaceTensionProfile:
    """Evidence-bearing profile for one provider/consumer interface.

    This is a structural container, not a score or verdict. Missing dimensions
    remain absent/UNKNOWN until a source or measurement supports them.
    """
    provider: Optional[str] = None
    consumer: Optional[str] = None
    purpose: Optional[str] = None
    direction: Optional[str] = None
    contract: InterfaceEvidence = dataclasses.field(default_factory=InterfaceEvidence)
    schema: InterfaceEvidence = dataclasses.field(default_factory=InterfaceEvidence)
    provenance: InterfaceEvidence = dataclasses.field(default_factory=InterfaceEvidence)
    data_quality: InterfaceEvidence = dataclasses.field(default_factory=InterfaceEvidence)
    timing: InterfaceEvidence = dataclasses.field(default_factory=InterfaceEvidence)
    latency: InterfaceEvidence = dataclasses.field(default_factory=InterfaceEvidence)
    frequency: InterfaceEvidence = dataclasses.field(default_factory=InterfaceEvidence)
    freshness: InterfaceEvidence = dataclasses.field(default_factory=InterfaceEvidence)
    influence_magnitude: InterfaceEvidence = dataclasses.field(default_factory=InterfaceEvidence)
    authority_boundary: InterfaceEvidence = dataclasses.field(default_factory=InterfaceEvidence)
    coupling: InterfaceEvidence = dataclasses.field(default_factory=InterfaceEvidence)
    reversibility: InterfaceEvidence = dataclasses.field(default_factory=InterfaceEvidence)
    error_handling: InterfaceEvidence = dataclasses.field(default_factory=InterfaceEvidence)
    fallback: InterfaceEvidence = dataclasses.field(default_factory=InterfaceEvidence)
    recovery: InterfaceEvidence = dataclasses.field(default_factory=InterfaceEvidence)
    observability: InterfaceEvidence = dataclasses.field(default_factory=InterfaceEvidence)
    capacity: InterfaceEvidence = dataclasses.field(default_factory=InterfaceEvidence)
    headroom: InterfaceEvidence = dataclasses.field(default_factory=InterfaceEvidence)
    feedback_sufficiency: InterfaceEvidence = dataclasses.field(default_factory=InterfaceEvidence)
    feedback_stability: InterfaceEvidence = dataclasses.field(default_factory=InterfaceEvidence)
    duplication: InterfaceEvidence = dataclasses.field(default_factory=InterfaceEvidence)
    failure_propagation: InterfaceEvidence = dataclasses.field(default_factory=InterfaceEvidence)

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclasses.dataclass
class PerformanceMargin:
    """Evidence-bearing q/tau margin input for one normalized quality metric.

    q and tau must already be expressed in the same normalized unit and direction
    (higher means better). This record computes only the arithmetic m=q-tau;
    it does not choose thresholds, tolerances, confidence cut-offs, or verdicts.
    Missing/invalid inputs keep m UNKNOWN. Exact zero is a boundary, not a pass.
    """
    metric: str
    q: Optional[float] = None
    tau: Optional[float] = None
    unit: Optional[str] = None
    q_evidence: List[str] = dataclasses.field(default_factory=list)
    tau_evidence: List[str] = dataclasses.field(default_factory=list)
    q_confidence: Optional[str] = None
    tau_confidence: Optional[str] = None
    normalization: Optional[str] = None
    operating_envelope: str = "unknown"

    def __post_init__(self) -> None:
        if not isinstance(self.metric, str) or not self.metric.strip():
            raise ValueError("performance margin metric must be non-blank")
        valid_envelopes = ("normal", "busy", "degraded", "stress", "recovery", "unknown")
        if self.operating_envelope not in valid_envelopes:
            raise ValueError(f"invalid performance margin operating envelope: {self.operating_envelope!r}")

    @staticmethod
    def _finite_number(value) -> bool:
        import math
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return False
        try:
            return math.isfinite(value)
        except (OverflowError, TypeError, ValueError):
            return False

    @property
    def margin(self) -> Optional[float]:
        if (not self._finite_number(self.q) or not self._finite_number(self.tau)
                or not isinstance(self.unit, str) or not self.unit.strip()
                or not isinstance(self.normalization, str)
                or not self.normalization.strip()):
            return None
        margin = float(self.q) - float(self.tau)
        return margin if self._finite_number(margin) else None

    @property
    def margin_state(self) -> str:
        value = self.margin
        if value is None:
            return "unknown"
        if value < 0:
            return "below_requirement"
        if value > 0:
            return "above_requirement"
        return "boundary"

    @property
    def evidence_complete(self) -> bool:
        # References and confidence labels do not complete a margin when its
        # arithmetic inputs remain unknown or incomparable.
        return (self.margin is not None
                and _has_traceable_evidence(self.q_evidence)
                and _has_traceable_evidence(self.tau_evidence)
                and isinstance(self.q_confidence, str) and bool(self.q_confidence.strip())
                and isinstance(self.tau_confidence, str) and bool(self.tau_confidence.strip()))

    def to_dict(self) -> dict:
        data = dataclasses.asdict(self)
        data["margin"] = self.margin
        data["margin_state"] = self.margin_state
        data["evidence_complete"] = self.evidence_complete
        return data


@dataclasses.dataclass
class Relationship:
    src: str
    dst: str
    kind: str                       # depends_on | produces_for | reuses | duplicates | influences
    authority: str = "none"         # none | bounded | strong  (capability != authority, §6)
    reversible: Optional[bool] = None   # None = unknown
    note: str = ""
    interface_profile: Optional[InterfaceTensionProfile] = None
    # Optional operating-envelope evidence for this relationship/interface.
    # Kept trailing to preserve legacy positional Relationship construction.
    operating_envelope: Optional[Any] = None
    # Per-metric q/tau margin evidence; never aggregated into a relationship verdict
    # without calibrated criteria. Trailing to preserve all legacy positional fields.
    performance_margins: Optional[Dict[str, Any]] = None

    def to_dict(self) -> dict:
        data = dataclasses.asdict(self)
        if isinstance(self.performance_margins, dict):
            data["performance_margins"] = {
                key: (value.to_dict() if isinstance(value, PerformanceMargin) else value)
                for key, value in self.performance_margins.items()
            }
        return data


@dataclasses.dataclass
class TensionAssessment:
    level: str                      # node | relationship | system
    subject: str
    verdict: str                    # underdeveloped | sufficient | overdeveloped | unknown
    inference: bool                 # True when not evidence-backed (uncertainty visible)
    evidence: List[str] = dataclasses.field(default_factory=list)
    dimensions: Dict[str, Any] = dataclasses.field(default_factory=dict)
    note: str = ""

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclasses.dataclass
class WorkPackage:
    key: str
    title: str
    obligation_keys: List[str]
    eligibility: str                # eligible | blocked
    blockers: List[str] = dataclasses.field(default_factory=list)
    priority_dimensions: Dict[str, Any] = dataclasses.field(default_factory=dict)
    anti_requirements: List[str] = dataclasses.field(default_factory=list)
    reversible: Optional[bool] = None
    note: str = ""

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


CONTEXT_REQUIREMENT_CLASSIFICATIONS = {
    "intent": NECESSARY,
    "scope": NECESSARY,
    "affected_path": NECESSARY,
    "assumption": CONDITIONAL,
    "constraint": NECESSARY,
    "exclusion": ANTI_REQUIREMENT,
    "acceptance_criterion": NECESSARY,
}


@dataclasses.dataclass(frozen=True)
class ContextRequirement:
    """Typed review obligation derived from one immutable objective-context field.

    This is deliberately separate from the executable work-package graph. It
    preserves the source item and its candidate classification until a reviewer
    maps it to one or more canonical graph obligations with evidence.
    """

    item_id: str
    kind: str
    text: str
    source_field: str
    source_index: int
    source_ref: str
    classification: str
    status: str = "unmapped"
    mapped_obligation_keys: List[str] = dataclasses.field(default_factory=list)
    evidence: List[str] = dataclasses.field(default_factory=list)
    review_required: bool = True

    def __post_init__(self) -> None:
        for name in ("item_id", "kind", "text", "source_field", "source_ref"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"context requirement {name} must be non-blank")
        if self.kind not in CONTEXT_REQUIREMENT_CLASSIFICATIONS:
            raise ValueError(f"invalid context requirement kind: {self.kind!r}")
        expected = CONTEXT_REQUIREMENT_CLASSIFICATIONS[self.kind]
        if self.classification != expected:
            raise ValueError(
                f"context requirement {self.kind!r} must use classification {expected!r}"
            )
        if isinstance(self.source_index, bool) or not isinstance(self.source_index, int) or self.source_index < 0:
            raise ValueError("context requirement source_index must be a non-negative integer")
        expected_source_suffix = f":{self.source_field}[{self.source_index}]"
        if not self.source_ref.endswith(expected_source_suffix):
            raise ValueError("context requirement source_ref must identify its source_field and source_index")
        if self.status not in ("unmapped", "mapped"):
            raise ValueError("context requirement status must be unmapped|mapped")
        if not isinstance(self.review_required, bool):
            raise ValueError("context requirement review_required must be a boolean")
        for name in ("mapped_obligation_keys", "evidence"):
            values = getattr(self, name)
            if not isinstance(values, list) or any(
                not isinstance(value, str) or not value.strip() for value in values
            ):
                raise ValueError(f"context requirement {name} must contain non-blank references")
            if len(values) != len(set(values)):
                raise ValueError(f"context requirement {name} references must be unique")
        if self.status == "unmapped":
            if self.mapped_obligation_keys or self.evidence or not self.review_required:
                raise ValueError("unmapped context requirements must remain unresolved and review-required")
        else:
            if not _has_traceable_evidence(self.mapped_obligation_keys):
                raise ValueError("mapped context requirements need mapped obligation keys")
            if not _has_traceable_evidence(self.evidence):
                raise ValueError("mapped context requirements need traceable mapping evidence")
            if self.review_required:
                raise ValueError("mapped context requirements cannot remain review-required")

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


ACCEPTANCE_VERIFICATION_STATES = ("unknown", "pending", "passed", "failed", "not_applicable")


@dataclasses.dataclass(frozen=True)
class AcceptanceVerificationRecord:
    """Separate UNKNOWN-first verification contract for one acceptance criterion."""

    criterion_id: str
    source_ref: str
    criterion: str
    status: str = "unknown"
    mapped_obligation_keys: List[str] = dataclasses.field(default_factory=list)
    verification_method: Optional[str] = None
    evidence_refs: List[str] = dataclasses.field(default_factory=list)
    verified_at: Optional[str] = None
    verifier: Optional[str] = None
    confidence: Optional[str] = None
    note: str = ""

    def __post_init__(self) -> None:
        for name in ("criterion_id", "source_ref", "criterion"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"acceptance verification {name} must be non-blank")
        if self.status not in ACCEPTANCE_VERIFICATION_STATES:
            raise ValueError(f"invalid acceptance verification status: {self.status!r}")
        for name in ("mapped_obligation_keys", "evidence_refs"):
            values = getattr(self, name)
            if not isinstance(values, list) or any(
                not isinstance(value, str) or not value.strip() for value in values
            ):
                raise ValueError(f"acceptance verification {name} must contain non-blank references")
            if len(values) != len(set(values)):
                raise ValueError(f"acceptance verification {name} references must be unique")
        if self.status in ("pending", "passed", "failed"):
            if not _has_traceable_evidence(self.mapped_obligation_keys):
                raise ValueError(f"{self.status} acceptance verification needs mapped obligation keys")
            if not isinstance(self.verification_method, str) or not self.verification_method.strip():
                raise ValueError(f"{self.status} acceptance verification needs a verification method")
        if self.status in ("passed", "failed", "not_applicable"):
            if not _has_traceable_evidence(self.evidence_refs):
                raise ValueError(f"{self.status} acceptance verification needs traceable evidence")
            if not isinstance(self.verifier, str) or not self.verifier.strip():
                raise ValueError(f"{self.status} acceptance verification needs a verifier")
            if not isinstance(self.confidence, str) or not self.confidence.strip():
                raise ValueError(f"{self.status} acceptance verification needs a confidence label")
            if not isinstance(self.verified_at, str) or not self.verified_at.strip():
                raise ValueError(f"{self.status} acceptance verification needs verified_at")
            try:
                parsed = datetime.datetime.fromisoformat(self.verified_at.replace("Z", "+00:00"))
            except ValueError as exc:
                raise ValueError("acceptance verification verified_at must be ISO-8601") from exc
            if parsed.tzinfo is None or parsed.utcoffset() is None:
                raise ValueError("acceptance verification verified_at must include a timezone offset")
        if self.status == "unknown" and (
            self.evidence_refs or self.verified_at is not None or self.verifier is not None
        ):
            raise ValueError("unknown acceptance verification cannot carry a completion claim")
        if not isinstance(self.note, str):
            raise ValueError("acceptance verification note must be text")

    @property
    def review_required(self) -> bool:
        return self.status in ("unknown", "pending")

    def to_dict(self) -> dict:
        data = dataclasses.asdict(self)
        data["review_required"] = self.review_required
        return data


@dataclasses.dataclass
class Pattern:
    """A reusable, defeasible lesson. Confidence is derived from bounded evidence
    counts; corroboration and disconfirmation remain separately traceable."""
    key: str
    statement: str
    provenance: str
    confidence: float = 0.3
    applicability: str = ""
    exceptions: List[str] = dataclasses.field(default_factory=list)
    observed_count: int = 1
    base_confidence: float = 0.3
    disconfirmed_count: int = 0
    confirmations: List[str] = dataclasses.field(default_factory=list)
    disconfirmations: List[str] = dataclasses.field(default_factory=list)
    # When true, applicability is an exact objective match, not token overlap.
    exact_scope: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.exact_scope, bool):
            raise ValueError("pattern exact_scope must be a boolean")
        if self.exact_scope and (
            not isinstance(self.applicability, str) or not self.applicability.strip()
        ):
            raise ValueError("exact-scope patterns require a non-blank applicability")

    def to_dict(self) -> dict:
        d = dataclasses.asdict(self)
        d["reliable"] = self.confidence > 0.0 and self.observed_count > self.disconfirmed_count
        return d


# cycle provenance kinds — kept DISTINCT so imported history is never counted as a
# completed RDO-guided development cycle (founder constraint).
NATIVE_PLANNING = "native_planning"            # RDO ran it; no work executed yet (outcome pending)
IMPORTED_RETROSPECTIVE = "imported_retrospective"  # a historical record seeded into learning
EXECUTED_VERIFIED = "executed_verified"        # RDO-recommended work actually built + verified
CYCLE_KINDS = (NATIVE_PLANNING, IMPORTED_RETROSPECTIVE, EXECUTED_VERIFIED)


@dataclasses.dataclass
class CycleRecord:
    """A complete development cycle, persisted for resume + learning."""
    id: str
    objective: str
    kind: str = NATIVE_PLANNING
    work_type: str = "unspecified"
    engineering_pattern: str = "unspecified"
    assumptions: List[str] = dataclasses.field(default_factory=list)
    obligations: List[dict] = dataclasses.field(default_factory=list)
    relationships: List[dict] = dataclasses.field(default_factory=list)
    reused: List[str] = dataclasses.field(default_factory=list)
    signature_matches: List[str] = dataclasses.field(default_factory=list)
    missing: List[str] = dataclasses.field(default_factory=list)
    anti_requirements: List[str] = dataclasses.field(default_factory=list)
    uncertainties: List[str] = dataclasses.field(default_factory=list)
    frontier: List[dict] = dataclasses.field(default_factory=list)
    counts: Dict[str, int] = dataclasses.field(default_factory=dict)
    tension: List[dict] = dataclasses.field(default_factory=list)
    work_packages: List[dict] = dataclasses.field(default_factory=list)
    predicted: Dict[str, Any] = dataclasses.field(default_factory=dict)
    actual: Optional[Dict[str, Any]] = None
    verification: Dict[str, Any] = dataclasses.field(default_factory=dict)
    lessons: List[str] = dataclasses.field(default_factory=list)
    created_at: str = dataclasses.field(default_factory=utc_now)
    # Exact immutable intake revision reference; empty for legacy/domain-demo cycles.
    objective_input: Dict[str, Any] = dataclasses.field(default_factory=dict)
    # Exact reviewed proposal/alternative/approval provenance; empty for ordinary intake.
    objective_lineage: Dict[str, Any] = dataclasses.field(default_factory=dict)
    # Full immutable objective context copied from intake, separate from revision identity.
    objective_context: Dict[str, Any] = dataclasses.field(default_factory=dict)
    # Explicit UNKNOWN-first mapping assessment; never infer satisfaction from planning.
    context_assessment: Dict[str, Any] = dataclasses.field(default_factory=dict)
    # Observed endpoint evidence; separate from structural failure-path candidates.
    observed_failure_evidence: List[dict] = dataclasses.field(default_factory=list)
    # Append-only feedback-loop measurement/review events applied to tension records.
    feedback_loop_evidence_events: List[dict] = dataclasses.field(default_factory=list)

    def __post_init__(self) -> None:
        if self.kind not in CYCLE_KINDS:
            raise ValueError(f"bad cycle kind {self.kind!r}")

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)
