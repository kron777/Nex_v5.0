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
    readiness   REAL NOT NULL,
    hot_branch  TEXT,
    word_count  INTEGER
);
CREATE INDEX IF NOT EXISTS idx_fountain_ts ON fountain_events(ts);

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
