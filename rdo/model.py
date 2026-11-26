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
class Relationship:
    src: str
    dst: str
    kind: str                       # depends_on | produces_for | reuses | duplicates | influences
    authority: str = "none"         # none | bounded | strong  (capability != authority, §6)
    reversible: Optional[bool] = None   # None = unknown
    note: str = ""

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
    """A reusable lesson from a completed cycle. Never a universal rule just
    because it worked once: confidence is bounded and exceptions are kept."""
    key: str
    statement: str
    provenance: str                 # cycle id + source
    confidence: float = 0.3         # starts low; rises slowly with corroboration
    applicability: str = ""         # when this pattern applies
    exceptions: List[str] = dataclasses.field(default_factory=list)
    observed_count: int = 1

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


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
    assumptions: List[str] = dataclasses.field(default_factory=list)
    obligations: List[dict] = dataclasses.field(default_factory=list)
    relationships: List[dict] = dataclasses.field(default_factory=list)
    reused: List[str] = dataclasses.field(default_factory=list)
    signature_matches: List[str] = dataclasses.field(default_factory=list)
    missing: List[str] = dataclasses.field(default_factory=list)
    anti_requirements: List[str] = dataclasses.field(default_factory=list)
    uncertainties: List[str] = dataclasses.field(default_factory=list)
    tension: List[dict] = dataclasses.field(default_factory=list)
    work_packages: List[dict] = dataclasses.field(default_factory=list)
    predicted: Dict[str, Any] = dataclasses.field(default_factory=dict)
    actual: Optional[Dict[str, Any]] = None
    verification: Dict[str, Any] = dataclasses.field(default_factory=dict)
    lessons: List[str] = dataclasses.field(default_factory=list)
    created_at: str = dataclasses.field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if self.kind not in CYCLE_KINDS:
            raise ValueError(f"bad cycle kind {self.kind!r}")

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)
