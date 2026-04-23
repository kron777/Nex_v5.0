-- sense.db — raw sense events, Tier 8 observations.
-- Written by Phase 2 stream adapters; Phase 1 only creates the table.

CREATE TABLE IF NOT EXISTS sense_events (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    stream     TEXT NOT NULL,
    payload    TEXT NOT NULL,
    provenance TEXT,
    timestamp  INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sense_stream ON sense_events(stream);
CREATE INDEX IF NOT EXISTS idx_sense_ts     ON sense_events(timestamp);
