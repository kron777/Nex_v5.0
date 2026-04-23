-- dynamic.db — scaffold only. Populated in Phase 3 (A-F pipeline,
-- bonsai growth, accumulator). Tables exist so Phase 1 smoke tests
-- can verify the DB is initialized; rows are not written until Phase 3.

CREATE TABLE IF NOT EXISTS bonsai_branches (
    id               TEXT PRIMARY KEY,
    name             TEXT NOT NULL UNIQUE,
    is_seed          INTEGER NOT NULL DEFAULT 0,
    curiosity_weight REAL NOT NULL,
    parent_id        TEXT,
    created_at       INTEGER NOT NULL,
    last_attended_at INTEGER
);

CREATE TABLE IF NOT EXISTS pipeline_events (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    stage      TEXT NOT NULL,
    branch_id  TEXT,
    payload    TEXT,
    timestamp  INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_pipeline_stage ON pipeline_events(stage);
CREATE INDEX IF NOT EXISTS idx_pipeline_ts    ON pipeline_events(timestamp);

CREATE TABLE IF NOT EXISTS accumulator (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    branch_id  TEXT,
    content    TEXT,
    weight     REAL NOT NULL DEFAULT 0.0,
    timestamp  INTEGER NOT NULL
);
