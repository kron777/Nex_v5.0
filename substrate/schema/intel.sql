-- intel.db — scaffold only. Populated in Phase 3+ as intel work accrues.
-- Columns are a minimal baseline; expect additions as the shape settles.

CREATE TABLE IF NOT EXISTS market_data (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol     TEXT NOT NULL,
    source     TEXT NOT NULL,
    price      REAL,
    payload    TEXT,
    timestamp  INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_market_symbol ON market_data(symbol);
CREATE INDEX IF NOT EXISTS idx_market_ts     ON market_data(timestamp);

CREATE TABLE IF NOT EXISTS news_events (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    source     TEXT NOT NULL,
    headline   TEXT NOT NULL,
    body       TEXT,
    url        TEXT,
    timestamp  INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_news_ts ON news_events(timestamp);

CREATE TABLE IF NOT EXISTS analysis_snapshots (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    subject    TEXT NOT NULL,
    summary    TEXT,
    payload    TEXT,
    timestamp  INTEGER NOT NULL
);
