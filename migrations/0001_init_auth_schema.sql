-- 0001_init_auth_schema.sql
-- Creates base schema for auth-related persistent data.

CREATE TABLE IF NOT EXISTS auth_users (
    id UUID PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS auth_sessions (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
    refresh_token_hash TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_auth_sessions_user_id ON auth_sessions (user_id);
CREATE INDEX IF NOT EXISTS idx_auth_sessions_expires_at ON auth_sessions (expires_at);

-- DOWN
-- DROP INDEX IF EXISTS idx_auth_sessions_expires_at;
-- DROP INDEX IF EXISTS idx_auth_sessions_user_id;
-- DROP TABLE IF EXISTS auth_sessions;
-- DROP TABLE IF EXISTS auth_users;
