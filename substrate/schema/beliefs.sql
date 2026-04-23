-- beliefs.db — the belief graph.
-- Tier 0 (Alpha) does not live here; it lives in alpha.py.
-- Tier 1 (Keystone) is seeded by keystone.reseed() with locked=1.

CREATE TABLE IF NOT EXISTS beliefs (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    content           TEXT NOT NULL,
    tier              INTEGER NOT NULL CHECK (tier BETWEEN 0 AND 8),
    confidence        REAL NOT NULL,
    created_at        INTEGER NOT NULL,
    last_promoted_at  INTEGER,
    last_demoted_at   INTEGER,
    promotion_log     TEXT NOT NULL DEFAULT '[]',
    branch_id         TEXT,
    source            TEXT,
    locked            INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_beliefs_tier   ON beliefs(tier);
CREATE INDEX IF NOT EXISTS idx_beliefs_branch ON beliefs(branch_id);

-- Locked keystone rows are unique by content within tier 1; INSERT OR IGNORE
-- at reseed time relies on this partial unique index.
CREATE UNIQUE INDEX IF NOT EXISTS idx_beliefs_keystone_content
    ON beliefs(content)
    WHERE tier = 1 AND locked = 1;
