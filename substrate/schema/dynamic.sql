-- dynamic.db — bonsai tree, A-F pipeline, accumulator, crystallization.

CREATE TABLE IF NOT EXISTS bonsai_branches (
    id               TEXT PRIMARY KEY,
    name             TEXT NOT NULL UNIQUE,
    is_seed          INTEGER NOT NULL DEFAULT 0,
    curiosity_weight REAL NOT NULL,
    parent_id        TEXT,
    created_at       INTEGER NOT NULL,
    last_attended_at INTEGER
);

-- Pipeline events (written by A-F pipeline)
CREATE TABLE IF NOT EXISTS pipeline_events (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    ts               REAL NOT NULL,
    step             TEXT NOT NULL,
    sensation_source TEXT,
    branch_id        TEXT,
    magnitude        REAL,
    valence          TEXT,
    meta             TEXT
);
CREATE INDEX IF NOT EXISTS idx_pipeline_ts     ON pipeline_events(ts);
CREATE INDEX IF NOT EXISTS idx_pipeline_branch ON pipeline_events(branch_id, ts);

-- Tree snapshots (written every 60s)
CREATE TABLE IF NOT EXISTS tree_snapshots (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    ts                  REAL NOT NULL,
    tree_json           TEXT NOT NULL,
    total_branches      INTEGER,
    active_branch_count INTEGER,
    aggregate_texture   TEXT,
    membrane_aperture   REAL
);
CREATE INDEX IF NOT EXISTS idx_tree_ts ON tree_snapshots(ts);

-- Tier-count snapshots (session 29, instrument #3). Piggybacks the same
-- 60s _snapshot_loop tick as tree_snapshots. One row per (tier, count) per
-- tick, so a given ts groups into as many rows as tiers currently populated.
CREATE TABLE IF NOT EXISTS tier_snapshots (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    ts    REAL NOT NULL,
    tier  INTEGER NOT NULL,
    count INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tier_snapshots_ts ON tier_snapshots(ts);

-- Crystallizer rejections (session 33, census specimen #10/#16). Every one
-- of FountainCrystallizer._quality_check's 11 reject reasons (empty,
-- too_short, too_long, no_engagement, blacklisted, performance_insight_
-- repetition, near_duplicate, recent_repeat, semantic_repeat, cooldown,
-- droplet_repetition) previously reached only errors.record()'s in-memory
-- deque(maxlen=500), which churns over in ~24min under real load and never
-- survives a restart. This is the first durable, queryable record of any
-- crystallizer rejection. matched_pattern carries the specific fragment
-- that triggered the reject where one exists (cooldown/blacklist/dedup
-- families); NULL for reasons with no distinct matched fragment (empty,
-- too_short, too_long, no_engagement).
CREATE TABLE IF NOT EXISTS crystallization_rejects (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ts              REAL NOT NULL,
    reason          TEXT NOT NULL,
    thought_excerpt TEXT,
    matched_pattern TEXT
);
CREATE INDEX IF NOT EXISTS idx_crystallization_rejects_ts     ON crystallization_rejects(ts);
CREATE INDEX IF NOT EXISTS idx_crystallization_rejects_reason ON crystallization_rejects(reason);

-- Persona-reply rejections (session 35, the "bouncer"). A2 (session 34,
-- 5c6081c) rewrote persona_responder.py's prompt to its documented intent
-- and FAILED verification: 1 pass of 3 live fires, the 3B echoed NEX's own
-- words back with a question mark attached (one case verbatim). Rather than
-- keep tuning the prompt, every reply is now checked against the recent
-- NEX thoughts it was generated from BEFORE being written to
-- sense_events — same near_duplicate Jaccard mechanism as
-- crystallizer.py, plus a stopword-filtered shared-phrase check for the
-- verbatim-echo shape (measured: crystallizer's stock 0.6 Jaccard is a
-- total no-op on this data — max observed 0.385 across 50 historical
-- replies; 0.10 was the measured cut that separates the one known PASS
-- from the two known FAILs). Follows crystallization_rejects' pattern
-- exactly, same reason for existing: this gate does not get to run blind.
CREATE TABLE IF NOT EXISTS persona_rejects (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ts              REAL NOT NULL,
    reason          TEXT NOT NULL,
    reply_excerpt   TEXT,
    matched_pattern TEXT,
    jaccard         REAL
);
CREATE INDEX IF NOT EXISTS idx_persona_rejects_ts     ON persona_rejects(ts);
CREATE INDEX IF NOT EXISTS idx_persona_rejects_reason ON persona_rejects(reason);

-- Crystallization events (Phase 3)
CREATE TABLE IF NOT EXISTS crystallization_events (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    ts        REAL NOT NULL,
    branch_id TEXT NOT NULL,
    belief_id INTEGER,
    content   TEXT,
    magnitude REAL
);

-- Cursor: tracks last processed sense_event id across restarts
CREATE TABLE IF NOT EXISTS dynamic_cursor (
    key   TEXT PRIMARY KEY,
    value INTEGER NOT NULL DEFAULT 0
);
INSERT OR IGNORE INTO dynamic_cursor (key, value) VALUES ('last_sense_id', 0);

CREATE TABLE IF NOT EXISTS accumulator (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    branch_id TEXT,
    content   TEXT,
    weight    REAL NOT NULL DEFAULT 0.0,
    timestamp INTEGER NOT NULL
);

-- Fountain events (Phase 7)
CREATE TABLE IF NOT EXISTS fountain_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          REAL NOT NULL,
    thought     TEXT NOT NULL,
    droplet     TEXT,
    readiness   REAL NOT NULL,
    hot_branch  TEXT,
    word_count  INTEGER,
    anchor_belief_id INTEGER
);
CREATE INDEX IF NOT EXISTS idx_fountain_ts ON fountain_events(ts);
CREATE INDEX IF NOT EXISTS idx_fountain_anchor ON fountain_events(anchor_belief_id) WHERE anchor_belief_id IS NOT NULL;

-- Harmonizer events (Phase 4)
CREATE TABLE IF NOT EXISTS harmonizer_events (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    ts                  REAL NOT NULL,
    belief_id_a         INTEGER,
    belief_id_b         INTEGER,
    resolution          TEXT,
    synthesis_belief_id INTEGER
);

-- Emergent drive proposals (Build 6)
CREATE TABLE IF NOT EXISTS drive_proposals (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    ts                     REAL NOT NULL,
    branch_id              TEXT NOT NULL,
    pressure               REAL NOT NULL,
    representative_beliefs TEXT NOT NULL,
    proposed_curiosity     REAL NOT NULL,
    status                 TEXT NOT NULL DEFAULT 'pending'
);

-- Substrate snapshots (SUBSTRATE_SNAPSHOTS.md) — temporal-witness mechanism.
-- One snapshot per fountain_event when capture is enabled.
-- Joins to fountain_events via fountain_event_id.
-- See SUBSTRATE_SNAPSHOTS.md for retention strategy.
CREATE TABLE IF NOT EXISTS substrate_snapshots (
    id                         INTEGER PRIMARY KEY AUTOINCREMENT,
    fountain_event_id          INTEGER NOT NULL UNIQUE,
    ts                         REAL NOT NULL,
    coherence                  REAL,
    voltage                    REAL,
    drives_json                TEXT,
    walk_state                 TEXT,
    walk_anchor_id             INTEGER,
    hot_branches_json          TEXT,
    harmonic_pairs_json        TEXT,
    gate_composition_json      TEXT,
    groove_severity            REAL,
    recent_fires_ids_json      TEXT,
    beliefs_in_attention_json  TEXT,
    retention_tier             TEXT,
    pinned                     INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_snapshots_ts ON substrate_snapshots(ts);
CREATE INDEX IF NOT EXISTS idx_snapshots_fire ON substrate_snapshots(fountain_event_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_tier ON substrate_snapshots(retention_tier);
CREATE INDEX IF NOT EXISTS idx_snapshots_pinned ON substrate_snapshots(pinned) WHERE pinned = 1;

-- Substrate snapshots (SUBSTRATE_SNAPSHOTS.md) — temporal-witness mechanism.
-- One snapshot per fountain_event when capture is enabled.
-- Joins to fountain_events via fountain_event_id.
-- See SUBSTRATE_SNAPSHOTS.md for retention strategy.
CREATE TABLE IF NOT EXISTS substrate_snapshots (
    id                         INTEGER PRIMARY KEY AUTOINCREMENT,
    fountain_event_id          INTEGER NOT NULL UNIQUE,
    ts                         REAL NOT NULL,
    coherence                  REAL,
    voltage                    REAL,
    drives_json                TEXT,
    walk_state                 TEXT,
    walk_anchor_id             INTEGER,
    hot_branches_json          TEXT,
    harmonic_pairs_json        TEXT,
    gate_composition_json      TEXT,
    groove_severity            REAL,
    recent_fires_ids_json      TEXT,
    beliefs_in_attention_json  TEXT,
    retention_tier             TEXT,
    pinned                     INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_snapshots_ts ON substrate_snapshots(ts);
CREATE INDEX IF NOT EXISTS idx_snapshots_fire ON substrate_snapshots(fountain_event_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_tier ON substrate_snapshots(retention_tier);
CREATE INDEX IF NOT EXISTS idx_snapshots_pinned ON substrate_snapshots(pinned) WHERE pinned = 1;

-- Ghost flags (SUBSTRATE_SNAPSHOTS.md companion) — Jon's intuition log.
-- Separate from fountain_events.tag (which is constrained to coin/maybe/non);
-- ghost is a different concept: subtle awareness moments where the substrate
-- seems to catch something it shouldn't have caught by routine retrieval.
-- One fire can be both coin-tagged AND ghost-flagged; they're orthogonal.
CREATE TABLE IF NOT EXISTS ghost_flags (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    fountain_event_id  INTEGER NOT NULL UNIQUE,
    ts                 REAL NOT NULL,
    reason             TEXT
);
CREATE INDEX IF NOT EXISTS idx_ghost_flags_ts ON ghost_flags(ts);
CREATE INDEX IF NOT EXISTS idx_ghost_flags_fire ON ghost_flags(fountain_event_id);
