-- conversations.db — user sessions and messages.

CREATE TABLE IF NOT EXISTS sessions (
    id          TEXT PRIMARY KEY,
    started_at  INTEGER NOT NULL,
    ended_at    INTEGER,
    admin       INTEGER NOT NULL DEFAULT 0,
    user_label  TEXT
);

CREATE TABLE IF NOT EXISTS messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT NOT NULL,
    role        TEXT NOT NULL CHECK (role IN ('user', 'nex', 'system')),
    content     TEXT NOT NULL,
    register    TEXT,
    timestamp   INTEGER NOT NULL,
    tool_used   TEXT
);

CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
CREATE INDEX IF NOT EXISTS idx_messages_ts      ON messages(timestamp);

-- Working memory — open problems persist across conversations.
CREATE TABLE IF NOT EXISTS open_problems (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT NOT NULL,
    description     TEXT NOT NULL,
    state           TEXT NOT NULL DEFAULT 'open',
    created_at      REAL NOT NULL,
    last_touched_at REAL NOT NULL,
    plan            TEXT NOT NULL DEFAULT '',
    observations    TEXT NOT NULL DEFAULT '[]',
    resolved_at     REAL
);
CREATE INDEX IF NOT EXISTS idx_problems_state ON open_problems(state);

-- PHASE 16 METACOGNITION 2026-05-09: self-observations persist across restart.
-- Reversion: drop this table + the metacognition module.
CREATE TABLE IF NOT EXISTS meta_cognition_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type  TEXT NOT NULL,
    description TEXT NOT NULL,
    severity    REAL NOT NULL DEFAULT 0.5,
    source      TEXT NOT NULL,
    created_at  REAL NOT NULL,
    resolved_at REAL,
    session_id  TEXT
);
CREATE INDEX IF NOT EXISTS idx_mcog_type ON meta_cognition_events(event_type);
CREATE INDEX IF NOT EXISTS idx_mcog_ts   ON meta_cognition_events(created_at DESC);

