"""RDO data model — the records the pipeline produces and persists.

Everything is a plain dataclass with `to_dict()` so cycles serialise to JSON and
resume after interruption. Nothing here reasons; the engine modules do.
"""
from __future__ import annotations

import dataclasses
import math
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
class PerformanceMargin:
    """Evidence-backed v1.4 performance margin: m = q - tau.

    q is the observed/declared performance measure and tau its required
    threshold. A numeric margin without measured provenance is still UNKNOWN.
    No threshold is inferred by the model.
    """
    metric: str
    q: Optional[float] = None
    tau: Optional[float] = None
    unit: str = ""
    confidence: str = "unknown"  # measured | stated | inferred | unknown
    evidence: List[str] = dataclasses.field(default_factory=list)

    def __post_init__(self) -> None:
        if not isinstance(self.metric, str) or not self.metric.strip():
            raise ValueError("performance margin requires a metric name")
        if self.confidence not in ("measured", "stated", "inferred", "unknown"):
            raise ValueError(f"bad performance-margin confidence {self.confidence!r}")
        for name, value in (("q", self.q), ("tau", self.tau)):
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(value)
            ):
                raise ValueError(f"performance margin {name} must be a finite number or None")
        if not isinstance(self.evidence, list) or any(
            not isinstance(item, str) or not item.strip() for item in self.evidence
        ):
            raise ValueError("performance-margin evidence must be nonblank text references")

    @property
    def margin(self) -> Optional[float]:
        if self.q is None or self.tau is None:
            return None
        return float(self.q) - float(self.tau)

    @property
    def status(self) -> str:
        margin = self.margin
        if margin is None or self.confidence != "measured" or not self.evidence:
            return TENSION_UNKNOWN
        return "below_threshold" if margin < 0 else "met"

    def to_dict(self) -> dict:
        d = dataclasses.asdict(self)
        d["margin"] = self.margin
        d["status"] = self.status
        return d


@dataclasses.dataclass
class InterfaceTensionProfile:
    """Recovered v1.4 interface dimensions, with unknowns explicit by default.

    This is an additive profile attached to a Relationship. Existing persisted
    relationships without a profile remain readable but cannot be called
    sufficient merely because no defect was detected.
    """
    provider: str = ""
    consumer: str = ""
    purpose: str = ""
    direction: str = "unknown"
    contract_schema: str = ""
    provenance_quality: str = "unknown"  # measured | stated | inferred | unknown
    timing: str = "unknown"  # synchronous | asynchronous | event_driven | periodic | unknown
    latency_ms: Optional[float] = None
    frequency_hz: Optional[float] = None
    influence_magnitude: str = "unknown"  # none | low | moderate | high | unknown
    failure_semantics: str = "unknown"  # defined | partial | unknown | not_applicable
    observability: str = "unknown"  # observed | partial | unknown | not_applicable
    capacity: Optional[float] = None
    headroom: Optional[float] = None
    feedback_sufficiency: str = "unknown"  # sufficient | insufficient | unknown | not_applicable
    feedback_stability: str = "unknown"  # stable | unstable | unknown | not_applicable
    duplication: str = "unknown"  # none | shared | duplicate | unknown | not_applicable
    failure_propagation: str = "unknown"  # contained | bounded | unbounded | unknown | not_applicable
    operating_envelope: str = "unknown"  # normal | busy | degraded | stress | recovery | unknown
    margins: List[PerformanceMargin] = dataclasses.field(default_factory=list)
    evidence: List[str] = dataclasses.field(default_factory=list)
    not_applicable: List[str] = dataclasses.field(default_factory=list)

    def __post_init__(self) -> None:
        choices = {
            "direction": {"provider_to_consumer", "consumer_to_provider", "bidirectional", "unknown"},
            "provenance_quality": {"measured", "stated", "inferred", "unknown"},
            "timing": {"synchronous", "asynchronous", "event_driven", "periodic", "unknown"},
            "influence_magnitude": {"none", "low", "moderate", "high", "unknown"},
            "failure_semantics": {"defined", "partial", "unknown", "not_applicable"},
            "observability": {"observed", "partial", "unknown", "not_applicable"},
            "feedback_sufficiency": {"sufficient", "insufficient", "unknown", "not_applicable"},
            "feedback_stability": {"stable", "unstable", "unknown", "not_applicable"},
            "duplication": {"none", "shared", "duplicate", "unknown", "not_applicable"},
            "failure_propagation": {"contained", "bounded", "unbounded", "unknown", "not_applicable"},
            "operating_envelope": {"normal", "busy", "degraded", "stress", "recovery", "unknown"},
        }
        for field_name, allowed in choices.items():
            if getattr(self, field_name) not in allowed:
                raise ValueError(f"bad interface-profile {field_name} {getattr(self, field_name)!r}")
        for name, value in (
            ("latency_ms", self.latency_ms), ("frequency_hz", self.frequency_hz),
            ("capacity", self.capacity), ("headroom", self.headroom),
        ):
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(value) or (name != "headroom" and value < 0)
            ):
                raise ValueError(
                    f"interface-profile {name} must be a finite "
                    + ("number or None" if name == "headroom" else "non-negative number or None")
                )
        if not isinstance(self.margins, list) or any(
            not isinstance(item, PerformanceMargin) for item in self.margins
        ):
            raise ValueError("interface-profile margins must be PerformanceMargin records")
        if not isinstance(self.evidence, list) or any(
            not isinstance(item, str) or not item.strip() for item in self.evidence
        ):
            raise ValueError("interface-profile evidence must be nonblank text references")
        if not isinstance(self.not_applicable, list) or any(
            not isinstance(item, str) or not item.strip() for item in self.not_applicable
        ):
            raise ValueError("interface-profile not_applicable must be nonblank field names")

    def missing_dimensions(self, *, authority: str = "none",
                           reversible: Optional[bool] = None) -> List[str]:
        """Return every dimension still UNKNOWN; N/A must be declared explicitly."""
        missing: List[str] = []
        required_text = (
            "provider", "consumer", "purpose", "contract_schema",
        )
        for name in required_text:
            if not getattr(self, name).strip():
                missing.append(name)
        for name in (
            "direction", "timing", "influence_magnitude", "failure_semantics",
            "observability", "feedback_sufficiency", "feedback_stability",
            "duplication", "failure_propagation", "operating_envelope",
        ):
            if getattr(self, name) == "unknown":
                missing.append(name)
        if self.provenance_quality != "measured":
            missing.append("measured_provenance_quality")
        for name in ("latency_ms", "frequency_hz", "capacity", "headroom"):
            if getattr(self, name) is None and name not in self.not_applicable:
                missing.append(name)
        if reversible is None and "reversible" not in self.not_applicable:
            missing.append("reversible")
        if self.influence_magnitude not in ("none", "unknown") and authority != "bounded":
            missing.append("bounded_authority")
        if not self.margins and "margins" not in self.not_applicable:
            missing.append("performance_margins")
        if not self.evidence:
            missing.append("profile_evidence")
        if any(m.status == TENSION_UNKNOWN for m in self.margins):
            missing.append("measured_margin_evidence")
        return sorted(set(missing))

    def to_dict(self) -> dict:
        d = dataclasses.asdict(self)
        d["margins"] = [margin.to_dict() for margin in self.margins]
        return d


@dataclasses.dataclass
class Relationship:
    src: str
    dst: str
    kind: str                       # depends_on | produces_for | reuses | duplicates | influences
    authority: str = "none"         # none | bounded | strong  (capability != authority, §6)
    reversible: Optional[bool] = None   # None = unknown
    note: str = ""
    interface_profile: Optional[InterfaceTensionProfile] = None

    def to_dict(self) -> dict:
        d = dataclasses.asdict(self)
        if self.interface_profile is not None:
            d["interface_profile"] = self.interface_profile.to_dict()
        return d


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

    def __post_init__(self) -> None:
        if self.kind not in CYCLE_KINDS:
            raise ValueError(f"bad cycle kind {self.kind!r}")

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)
