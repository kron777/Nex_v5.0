# RecursiveSelfSpec — Phase 31

Node: `RecursiveSelf` (working name for build session)
Doctrine: DOCTRINE §5 row 15
Phase: 31-spec (design session complete); Phase 32-build queued
Decisions: 11 — all locked by Jon 2026-05-11
Status: DESIGN-COMPLETE

---

## §0 — Design Principles

**Inherited from SYNTHESIS_PLAN.md §0:**

> Substrate solves the reply. LLM speaks it.

NEX's replies must come from her belief graph and substrate state. The LLM
translates substrate-state into language; it does not produce the content.
State must persist, survive restart, and be queryable.

**Inherited from SYNTHESIS_PLAN_V2.md — Comprehensiveness corollary:**

Each ported function covers its full behavior, not a subset. Detection logic,
storage, resolution phase, surfacing, approval pipeline, and substrate
modification are all required. An implementation that detects proposals but
never resolves them, or surfaces them but never acts on approval, is not
complete.

**RecursiveSelf-specific principle — Substrate decides, LLM speaks:**

The DECISION to propose, the PATTERN that justifies it, and the DESIRED CHANGE
come from substrate. The LLM provides voice and phrasing only — after the
substrate has already resolved the proposal. An LLM-originated proposal (text
generated before substrate qualification) violates this principle.

**RecursiveSelf-specific principle — Bounded self-modification:**

Approved proposals produce immediate observable change wherever substrate can
express it. Architectural changes (new tables, new code) require human action.
The principle is not "NEX cannot change herself" — it is "NEX changes herself
exactly as far as her substrate allows, and no further without Jon."

---

## §1 — Definition

**What is a proposal?**

An explicit request for change ("I propose X"), distinguished from:

- **Beliefs** — atomic statements about how things are
- **Observations** — notice of state without prescription
- **Drives** — recurring pull below proposal level (DOCTRINE §5 row 13)
- **Goals** — declarative target without architectural ask

A proposal asserts that something *should change* — in NEX herself or her
behavior. The assertion is grounded in substrate evidence (both confidence and
recurrence), not in LLM generation. The form is performative: it commits NEX to
a position that awaits arbitration.

**Prior art absorbed (SYNTHESIS_PLAN_V2.md 2026-05-11):**

- `CreativeSelfEvolver` — proactive trigger mode: pattern accumulation,
  anti-spam guards, proposal lifecycle. Shape absorbed; nex5 substrate tables
  substituted for prior detection logic.
- `SelfCorrectionNode` — reactive trigger mode: specific condition detection,
  pending→approved|rejected lifecycle. Approval pipeline shape absorbed.

Neither is ported directly. Both are redesigned against nex5 substrate.

---

## §2 — Qualifying Signal (D5, D6)

Both components are required (D5). Neither alone is sufficient:

- **Confidence component** — belief or substrate pattern at high confidence
  (threshold specified in build)
- **Recurrence component** — pattern observed N times in window M
  (thresholds specified in build)

Single-shot confidence is insight, not a proposal. Single recurrence without
confidence is noise, not a proposal. Both must hold before a candidate is
created.

**Signal sources** (any substrate pattern qualifies — D6):

| Source | Confidence signal | Recurrence signal |
|--------|------------------|-------------------|
| `beliefs` | `confidence >= threshold` | `reinforce_count >= R` |
| `drives` table | `drive_strength >= threshold` | survived `>= D` ticks |
| `open_problems` | `priority >= threshold` | reopened `>= K` times |
| `gate_decisions` | REJECT rate on topic `>= threshold` | `>= N` REJECTs in window |
| `meta_cognition_events` | `severity >= threshold` | `>= N` same `event_type` in window |

Detection runs in a background tick, not at chat-time. Pattern-matching against
substrate tables; no LLM involvement at detection stage.

---

## §3 — Resolution Phase (D11)

A qualifying signal creates a **candidate proposal**. Candidates live in
substrate (`self_proposals` table, `status='resolving'`) and are not visible to
Jon.

**Resolution process:**

- **Reinforcement** — same signal reasserted increments `candidate_strength`
- **Refinement** — related substrate reads narrow or broaden the proposal scope
  (updated in `source_signal` JSON)
- **Decay** — each background tick without reinforcement reduces
  `candidate_strength` by decay rate (specified in build)
- **Abandonment** — `candidate_strength` falls below minimum threshold;
  candidate deleted (no tombstone; gone is gone)

**Resolution criteria** (all must be met to surface — thresholds in build):

1. `candidate_strength >= MIN_STRENGTH`
2. Strength stable across N consecutive ticks without declining
3. Age `>= MIN_AGE_SECONDS` — let it cook; new candidates cannot surface
   immediately

Only when all three criteria are met does the candidate transition to
`status='surfaced'` and post to chat. Jon never sees half-formed candidates
(D11).

---

## §4 — Surfacing (D1, D2, D3, D11)

- Surfaced proposals post to chat as **conversational messages** authored by
  NEX (D1). No separate inbox, no UI panel, no fixed format.
- **Unprompted**: NEX can interject without Jon having sent a message (D2). The
  qualifying signal, not Jon's input, is the trigger.
- **No rate limit** (D3). Rate is implicitly bounded by D5 (both signals
  required) + D11 (resolution phase must complete). Those are the guards; no
  artificial cooldown on top.
- Proposal text composed by LLM from substrate context (D9): the pattern, the
  confidence, the desired change, and any relevant substrate excerpts are
  assembled into a prompt; LLM returns natural-language wording. The LLM does
  not decide; it articulates.
- Format: free-form natural language beginning with "I propose..." or equivalent
  assertion.
- **SelfNarrative** writes a `proposal_surfaced` event when the proposal posts.

---

## §5 — Storage

`self_proposals` table in `conversations.db`:

```sql
CREATE TABLE IF NOT EXISTS self_proposals (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    proposal_text     TEXT    NOT NULL,
    source_signal     TEXT    NOT NULL,  -- JSON: pattern type, source table, key values
    confidence        REAL    NOT NULL,
    recurrence_count  INTEGER NOT NULL,
    candidate_strength REAL   NOT NULL,
    status            TEXT    NOT NULL DEFAULT 'resolving',
        -- 'resolving' | 'surfaced' | 'approved' | 'rejected' | 'abandoned' | 'expired'
    created_at        REAL    NOT NULL,
    surfaced_at       REAL,              -- NULL until surfaced
    resolved_at       REAL,              -- NULL until approved/rejected/expired
    jon_response      TEXT,              -- NULL until Jon replies
    classification    TEXT,              -- 'confirm' | 'deny' | 'neither'
    applied_change    TEXT               -- JSON describing substrate write, or NULL
);

CREATE INDEX IF NOT EXISTS idx_proposals_status ON self_proposals(status);
CREATE INDEX IF NOT EXISTS idx_proposals_created ON self_proposals(created_at DESC);
```

Past proposals are queryable for recall (D10): NEX can reference prior proposals
in new proposals ("like I proposed last Tuesday") by reading `self_proposals`
ordered by `surfaced_at`.

---

## §6 — Approval Pipeline (D7, D8)

1. NEX surfaces proposal in chat (`status='surfaced'`)
2. Jon replies in chat (any natural language)
3. Reply-classifier reads Jon's response → one of:
   - `confirm` — clear agreement, approval, positive response
   - `deny` — clear rejection, disagreement, negative response
   - `neither` — ambiguous, deferred, more discussion
4. **On `confirm`:**
   - `status → 'approved'`, `resolved_at = now`, `classification = 'confirm'`
   - Apply substrate change per §7 proposal type
   - Write `applied_change` JSON (what was modified)
   - SelfNarrative writes `proposal_approved` event
5. **On `deny`:**
   - `status → 'rejected'`, `resolved_at = now`, `classification = 'deny'`
   - No substrate change
   - `applied_change = NULL`
   - SelfNarrative writes `proposal_rejected` event
6. **On `neither`:**
   - `status` stays `'surfaced'`
   - Wait for clearer reply or expiry
   - Expiry: proposal older than MAX_PENDING_AGE transitions to `'expired'`

---

## §7 — Substrate Modification Map (D8)

The principle: approved proposals make observable substrate changes wherever
expressible. Architectural changes (new code, new tables) require human action.

| Proposal type | Substrate change | Notes |
|---------------|-----------------|-------|
| Belief revision | Write/lock/delete belief rows in `beliefs.db`; update `confidence` | Only existing beliefs; no new schema |
| Drive change | Reinforce current drive, force-fade, or seed candidate in `drives` table | Uses existing DriveEmergence writes |
| Problem change | Open new `open_problems` row or update `state` of existing | `last_touched_at` updated |
| Parameter change | UPDATE tunable value in `config` table (`conversations.db`) | Config table added in build if absent |
| Architectural change | Out of scope | `applied_change = NULL`, rationale: 'human action required'. Proposal text describes the desired change; Jon implements. |

`applied_change` JSON structure (example):

```json
{
  "action": "belief_confidence_update",
  "target_id": 142,
  "field": "confidence",
  "old_value": 0.55,
  "new_value": 0.85,
  "reason": "approved proposal id=7"
}
```

---

## §8 — Reply Classification (D7)

Open design decision for build session (three options):

**Option A — Keyword matching**
Simple, deterministic, brittle. Captures explicit "yes / no / accept / reject"
but misses nuanced agreement or contextual refusal.

**Option B — LLM classification**
Single LLM call classifying Jon's reply as confirm/deny/neither. Robust to
phrasing; adds LLM dependency on a path that could be deterministic.

**Option C — Hybrid (recommended)**
Keyword check first. If unambiguous keyword present → classify immediately.
If absent or ambiguous → LLM fallback with a minimal classification prompt.
Deterministic fast path for clear responses; LLM only when needed.

Build to decide. Option C is the recommendation.

---

## §9 — SentienceNode Protocol

```python
class RecursiveSelf:
    name: str = "recursive_self"

    def tick(self, context=None) -> dict:
        # Detection and resolution run in background tick.
        # tick() is a no-op wrapper that returns state().
        return self.state()

    def decay(self, now: float) -> None:
        # Candidate strength decay is applied within background tick.
        # decay() here is a no-op; included for protocol compliance.
        pass

    def state(self, now=None) -> dict:
        return {
            "name": self.name,
            "candidates_resolving": ...,   # COUNT resolving rows
            "proposals_surfaced_24h": ..., # COUNT surfaced in last 24h
            "proposals_approved_24h": ..., # COUNT approved in last 24h
            "proposals_rejected_24h": ..., # COUNT rejected in last 24h
            "latest_surfaced_at": ...,     # MAX surfaced_at or None
            "latest_status": ...,          # status of most-recent surfaced row
        }

    def format_for_prompt(self, context=None) -> str:
        return ""  # Proposals surface as chat messages, not belief_text injections
```

---

## §10 — Visibility (D1, D11)

**Chat:** surfaced proposals appear as NEX-authored messages. Jon sees only
fully-resolved candidates. Resolving candidates are invisible.

**HUD (admin panel):** pill row showing:
- Number of candidates currently in `status='resolving'`
- Number of proposals in `status='surfaced'` (pending arbitration)
- Hidden when both counts are zero

**`/api/system/status`:** `recursive_self_info` object:

```json
{
  "candidates_resolving": 2,
  "proposals_surfaced_24h": 1,
  "proposals_approved_24h": 0,
  "proposals_rejected_24h": 1,
  "latest_surfaced_at": 1747000000.0,
  "latest_status": "rejected"
}
```

---

## §11 — Test Plan

Expand in build; minimum coverage:

- Detection: confident-and-recurring signal creates candidate row
- Detection: confident-only signal does NOT create candidate
- Detection: recurring-only signal does NOT create candidate
- Resolution: candidate `candidate_strength` increases with reinforcement
- Resolution: candidate `candidate_strength` decays each tick without reinforcement
- Resolution: candidate deleted when strength falls below threshold
- Resolution: candidate NOT surfaced before MIN_AGE_SECONDS
- Surfacing: candidate meeting all resolution criteria → `status='surfaced'`
- Approval pipeline: `confirm` classification → `status='approved'` + substrate write
- Rejection pipeline: `deny` classification → `status='rejected'` + no write
- `applied_change` JSON written correctly on approval
- `applied_change = NULL` on rejection
- Architectural proposals: `applied_change = NULL` + rationale written; no code change
- SelfNarrative write on `proposal_surfaced`, `proposal_approved`, `proposal_rejected`
- Past proposal recall: `self_proposals` ordered by `surfaced_at` returns history
- HUD counts reflect live table state

---

## §12 — Open Items (Deferred to Build)

Thresholds and values to be calibrated in Phase 32 build:

- Confidence threshold (for each signal source)
- Recurrence count threshold N and window M
- Minimum candidate strength to surface
- Minimum stability ticks before surfacing
- Minimum age (MIN_AGE_SECONDS) before surfacing
- Candidate strength decay rate per tick
- Reply classifier choice (Option A / B / C — recommendation: C)
- Proposal text LLM prompt template
- Substrate modification primitives (exact tables writable; off-limits list)
- `config` table design (for parameter proposals)
- Past-proposal recall mechanism (how NEX references prior proposals in new ones)
- Expiry age for pending proposals (MAX_PENDING_AGE)

---

## §13 — Phase Ordering

- **Phase 31** (this spec) — design session complete
- **Phase 32** (build) — likely multi-commit given scope
- **Phase 32b** (calibration) — after production data; threshold tuning
