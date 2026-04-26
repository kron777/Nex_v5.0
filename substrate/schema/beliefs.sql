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

CREATE TABLE IF NOT EXISTS config (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL,
    updated_at  REAL NOT NULL
);

-- Signal detection layer — LLM-free structural pattern detection.
CREATE TABLE IF NOT EXISTS signals (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    detected_at     REAL NOT NULL,
    detector_name   TEXT NOT NULL,
    signal_type     TEXT NOT NULL,
    payload         TEXT NOT NULL,
    branches        TEXT,
    entities        TEXT,
    confidence      REAL NOT NULL DEFAULT 0.5
);
CREATE INDEX IF NOT EXISTS idx_signals_detected_at ON signals(detected_at);
CREATE INDEX IF NOT EXISTS idx_signals_detector    ON signals(detector_name);

CREATE TABLE IF NOT EXISTS patterns (
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    matched_at               REAL NOT NULL,
    template_name            TEXT NOT NULL,
    signal_ids               TEXT NOT NULL,
    predicted_window_seconds INTEGER,
    prediction               TEXT,
    template_confidence      REAL DEFAULT 0.5,
    validated_at             REAL,
    outcome_score            REAL,
    outcome_notes            TEXT
);
CREATE INDEX IF NOT EXISTS idx_patterns_matched_at ON patterns(matched_at);
CREATE INDEX IF NOT EXISTS idx_patterns_validated  ON patterns(validated_at);

CREATE TABLE IF NOT EXISTS pattern_template_scores (
    template_name    TEXT PRIMARY KEY,
    total_matches    INTEGER DEFAULT 0,
    validated        INTEGER DEFAULT 0,
    hits             INTEGER DEFAULT 0,
    cumulative_score REAL DEFAULT 0.0,
    updated_at       REAL NOT NULL
);

-- Diversity ecology tables --------------------------------------------------

CREATE TABLE IF NOT EXISTS collision_grades (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    belief_id          INTEGER NOT NULL,
    parent_a_id        INTEGER NOT NULL,
    parent_b_id        INTEGER NOT NULL,
    input_distance     REAL NOT NULL,
    output_distance    REAL NOT NULL,
    rarity             REAL NOT NULL,
    grade              REAL NOT NULL,
    grader_version     INTEGER NOT NULL DEFAULT 1,
    graded_at          REAL NOT NULL,
    FOREIGN KEY (belief_id) REFERENCES beliefs(id)
);
CREATE INDEX IF NOT EXISTS idx_collision_grade  ON collision_grades(grade DESC);
CREATE INDEX IF NOT EXISTS idx_collision_belief ON collision_grades(belief_id);

CREATE TABLE IF NOT EXISTS belief_lineage (
    child_id           INTEGER NOT NULL,
    parent_id          INTEGER NOT NULL,
    relationship       TEXT NOT NULL,
    weight             REAL DEFAULT 1.0,
    created_at         REAL NOT NULL,
    PRIMARY KEY (child_id, parent_id, relationship)
);
CREATE INDEX IF NOT EXISTS idx_lineage_parent ON belief_lineage(parent_id);
CREATE INDEX IF NOT EXISTS idx_lineage_child  ON belief_lineage(child_id);

CREATE TABLE IF NOT EXISTS belief_boost (
    belief_id          INTEGER PRIMARY KEY,
    boost_value        REAL NOT NULL DEFAULT 1.0,
    boosted_at         REAL NOT NULL,
    source_grade       REAL,
    decay_rate         REAL DEFAULT 0.0,
    FOREIGN KEY (belief_id) REFERENCES beliefs(id)
);

CREATE TABLE IF NOT EXISTS groove_alerts (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    detected_at        REAL NOT NULL,
    alert_type         TEXT NOT NULL,
    severity           REAL NOT NULL,
    pattern            TEXT,
    sample_belief_ids  TEXT,
    window_size        INTEGER NOT NULL,
    acknowledged_at    REAL
);

CREATE TABLE IF NOT EXISTS dormant_beliefs (
    belief_id          INTEGER PRIMARY KEY,
    last_active_at     REAL NOT NULL,
    dormancy_score     REAL NOT NULL,
    flagged_at         REAL NOT NULL,
    reanimated_at      REAL,
    FOREIGN KEY (belief_id) REFERENCES beliefs(id)
);

CREATE TABLE IF NOT EXISTS residue (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    cycle_id           TEXT NOT NULL,
    belief_id          INTEGER NOT NULL,
    activation_strength REAL NOT NULL,
    created_at         REAL NOT NULL,
    consumed_at        REAL,
    FOREIGN KEY (belief_id) REFERENCES beliefs(id)
);

CREATE TABLE IF NOT EXISTS grader_versions (
    version            INTEGER PRIMARY KEY,
    w_input_distance   REAL NOT NULL,
    w_output_distance  REAL NOT NULL,
    w_rarity           REAL NOT NULL,
    rationale          TEXT,
    created_at         REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS consolidations (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    clock              TEXT NOT NULL,
    ran_at             REAL NOT NULL,
    fire_count_at_run  INTEGER NOT NULL,
    actions_taken      TEXT,
    findings           TEXT
);

CREATE TABLE IF NOT EXISTS grade_mismatches (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    belief_id          INTEGER NOT NULL,
    original_grade     REAL NOT NULL,
    retrospective_value REAL NOT NULL,
    mismatch_direction TEXT NOT NULL,
    detected_at        REAL NOT NULL,
    grader_version     INTEGER NOT NULL,
    FOREIGN KEY (belief_id) REFERENCES beliefs(id)
);

-- Arc Reader tables ---------------------------------------------------------

CREATE TABLE IF NOT EXISTS arcs (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    arc_type            TEXT NOT NULL,
    detected_at         REAL NOT NULL,
    window_start        REAL NOT NULL,
    window_end          REAL NOT NULL,
    theme_summary       TEXT,
    member_count        INTEGER NOT NULL,
    progression_score   REAL,
    transformation_score REAL,
    centroid_embedding  BLOB,
    closed_by_belief_id INTEGER,
    quality_grade       REAL,
    last_active_at      REAL NOT NULL,
    dormancy_score      REAL DEFAULT 0.0,
    FOREIGN KEY (closed_by_belief_id) REFERENCES beliefs(id)
);
CREATE INDEX IF NOT EXISTS idx_arcs_active  ON arcs(last_active_at DESC);
CREATE INDEX IF NOT EXISTS idx_arcs_type    ON arcs(arc_type);
CREATE INDEX IF NOT EXISTS idx_arcs_quality ON arcs(quality_grade DESC);

CREATE TABLE IF NOT EXISTS arc_members (
    arc_id              INTEGER NOT NULL,
    belief_id           INTEGER NOT NULL,
    position            INTEGER NOT NULL,
    role                TEXT NOT NULL,
    distance_from_centroid REAL,
    joined_at           REAL NOT NULL,
    PRIMARY KEY (arc_id, belief_id),
    FOREIGN KEY (arc_id) REFERENCES arcs(id),
    FOREIGN KEY (belief_id) REFERENCES beliefs(id)
);
CREATE INDEX IF NOT EXISTS idx_arc_members_belief ON arc_members(belief_id);

CREATE TABLE IF NOT EXISTS arc_closers (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    arc_id              INTEGER NOT NULL,
    belief_id           INTEGER NOT NULL,
    detected_at         REAL NOT NULL,
    meta_confidence     REAL NOT NULL,
    FOREIGN KEY (arc_id) REFERENCES arcs(id),
    FOREIGN KEY (belief_id) REFERENCES beliefs(id)
);

-- Anti-rut cooldown: groove spotter writes here; crystallizer respects it.
CREATE TABLE IF NOT EXISTS signal_cooldown (
    content_hash    TEXT PRIMARY KEY,
    content         TEXT NOT NULL,
    cooldown_until  REAL NOT NULL,
    reason          TEXT,
    created_at      REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_signal_cooldown_until ON signal_cooldown(cooldown_until);
