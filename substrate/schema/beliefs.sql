-- beliefs.db — the belief graph.
-- Tier 0 (Alpha) does not live here; it lives in alpha.py.
-- Tier 1 (Keystone) is seeded by keystone.reseed() with locked=1.

CREATE TABLE IF NOT EXISTS beliefs (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    content              TEXT NOT NULL,
    tier                 INTEGER NOT NULL CHECK (tier BETWEEN 0 AND 8),
    confidence           REAL NOT NULL,
    created_at           INTEGER NOT NULL,
    last_promoted_at     INTEGER,
    last_demoted_at      INTEGER,
    promotion_log        TEXT NOT NULL DEFAULT '[]',
    branch_id            TEXT,
    source               TEXT,
    locked               INTEGER NOT NULL DEFAULT 0,
    corroboration_count  INTEGER NOT NULL DEFAULT 0,
    last_referenced_at   INTEGER,
    paused               INTEGER NOT NULL DEFAULT 0,
    reinforce_count      INTEGER NOT NULL DEFAULT 0,
    use_count            INTEGER NOT NULL DEFAULT 0,
    erosion_stage        TEXT NOT NULL DEFAULT 'external'
);

CREATE INDEX IF NOT EXISTS idx_beliefs_tier   ON beliefs(tier);
CREATE INDEX IF NOT EXISTS idx_beliefs_branch ON beliefs(branch_id);

-- Locked keystone rows are unique by content within tier 1; INSERT OR IGNORE
-- at reseed time relies on this partial unique index.
CREATE UNIQUE INDEX IF NOT EXISTS idx_beliefs_keystone_content
    ON beliefs(content)
    WHERE tier = 1 AND locked = 1;

-- Contamination blacklist — patterns that must never crystallise into beliefs.
CREATE TABLE IF NOT EXISTS belief_blacklist (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern     TEXT NOT NULL UNIQUE,
    reason      TEXT NOT NULL DEFAULT '',
    added_at    REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_blacklist_pattern ON belief_blacklist(pattern);

-- Belief edge graph — grows organically through corroboration, contradiction, synthesis.
CREATE TABLE IF NOT EXISTS belief_edges (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id        INTEGER NOT NULL REFERENCES beliefs(id),
    target_id        INTEGER NOT NULL REFERENCES beliefs(id),
    edge_type        TEXT NOT NULL CHECK (edge_type IN (
                         'supports',     -- source strengthens target
                         'opposes',      -- source contradicts target
                         'synthesises',  -- source combines with target into something new
                         'cross_domain', -- source and target from different branches, pattern-match
                         'refines'       -- source adds precision to target
                     )),
    weight           REAL NOT NULL DEFAULT 0.5,
    created_at       REAL NOT NULL,
    last_traversed_at REAL
);

CREATE INDEX IF NOT EXISTS idx_edges_source ON belief_edges(source_id);
CREATE INDEX IF NOT EXISTS idx_edges_target ON belief_edges(target_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_edges_pair
    ON belief_edges(source_id, target_id, edge_type);

-- Koan reading tracker — records which koan was last presented to the fountain.
-- gate_id is the belief.id (as text) of the koan belief that was read.
CREATE TABLE IF NOT EXISTS koan_reads (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    gate_id  TEXT NOT NULL,
    read_at  REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_koan_reads_gate ON koan_reads(gate_id);

-- Synergizer log — records every synthesis attempt and its outcome.
CREATE TABLE IF NOT EXISTS synergizer_log (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    ts               REAL NOT NULL,
    belief_id_a      INTEGER NOT NULL,
    belief_id_b      INTEGER NOT NULL,
    result_content   TEXT,
    result_belief_id INTEGER
);
CREATE INDEX IF NOT EXISTS idx_synergizer_ts ON synergizer_log(ts);

-- Fountain crystallizations — links fountain_events rows to the beliefs they became.
CREATE TABLE IF NOT EXISTS fountain_crystallizations (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    fountain_event_id INTEGER NOT NULL,
    belief_id         INTEGER NOT NULL,
    ts                REAL NOT NULL,
    content           TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_crystal_event  ON fountain_crystallizations(fountain_event_id);
CREATE INDEX IF NOT EXISTS idx_crystal_belief ON fountain_crystallizations(belief_id);

-- Speech queue — fountain insights awaiting TTS playback.
CREATE TABLE IF NOT EXISTS speech_queue (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    belief_id  INTEGER NOT NULL,
    content    TEXT NOT NULL,
    voice      TEXT DEFAULT 'af_sarah',
    queued_at  REAL NOT NULL,
    spoken_at  REAL,
    status     TEXT DEFAULT 'pending',
    error      TEXT,
    FOREIGN KEY (belief_id) REFERENCES beliefs(id)
);
CREATE INDEX IF NOT EXISTS idx_speech_queue_status
    ON speech_queue(status, queued_at);
