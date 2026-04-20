-- 0002_add_outbox_events.sql
-- Adds outbox table for reliable event publication.

CREATE TABLE IF NOT EXISTS auth_outbox_events (
    id UUID PRIMARY KEY,
    event_type TEXT NOT NULL,
    payload JSONB NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    published_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_auth_outbox_status_created_at
    ON auth_outbox_events (status, created_at);

-- DOWN
-- DROP INDEX IF EXISTS idx_auth_outbox_status_created_at;
-- DROP TABLE IF EXISTS auth_outbox_events;
