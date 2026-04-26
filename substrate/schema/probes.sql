-- probes.db — Probe Archaeology (Lens Theory).

CREATE TABLE IF NOT EXISTS probes (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    category             TEXT NOT NULL,
    probe_text           TEXT NOT NULL,
    response_text        TEXT NOT NULL,
    response_mode        TEXT,
    asked_at             REAL NOT NULL,
    response_received_at REAL,
    response_latency_ms  INTEGER,
    notes                TEXT
);

CREATE TABLE IF NOT EXISTS probe_context (
    probe_id       INTEGER NOT NULL,
    snapshot_key   TEXT NOT NULL,
    snapshot_value TEXT NOT NULL,
    PRIMARY KEY (probe_id, snapshot_key),
    FOREIGN KEY (probe_id) REFERENCES probes(id)
);

CREATE TABLE IF NOT EXISTS probe_tags (
    probe_id INTEGER NOT NULL,
    tag      TEXT NOT NULL,
    PRIMARY KEY (probe_id, tag),
    FOREIGN KEY (probe_id) REFERENCES probes(id)
);

CREATE INDEX IF NOT EXISTS idx_probes_category_time ON probes(category, asked_at);
