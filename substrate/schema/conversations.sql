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
    timestamp   INTEGER NOT NULL
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

-- Tool use record — which tool was used per message
ALTER TABLE messages ADD COLUMN tool_used TEXT;
