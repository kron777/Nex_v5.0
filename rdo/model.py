"""RDO data model — the records the pipeline produces and persists.

Everything is a plain dataclass with `to_dict()` so cycles serialise to JSON and
resume after interruption. Nothing here reasons; the engine modules do.
"""
from __future__ import annotations

import dataclasses
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

    @staticmethod
    def _finite_number(value) -> bool:
        import math
        return (isinstance(value, (int, float)) and not isinstance(value, bool)
                and math.isfinite(value))

    @property
    def margin(self) -> Optional[float]:
        if (not self._finite_number(self.q) or not self._finite_number(self.tau)
                or not isinstance(self.unit, str) or not self.unit.strip()
                or not isinstance(self.normalization, str)
                or not self.normalization.strip()):
            return None
        return float(self.q) - float(self.tau)

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

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


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
    # Full immutable objective context copied from intake, separate from revision identity.
    objective_context: Dict[str, Any] = dataclasses.field(default_factory=dict)
    # Explicit UNKNOWN-first mapping assessment; never infer satisfaction from planning.
    context_assessment: Dict[str, Any] = dataclasses.field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.kind not in CYCLE_KINDS:
            raise ValueError(f"bad cycle kind {self.kind!r}")

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)
