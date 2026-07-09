-- amorae_db — initial schema.
--
-- Level-2 isolation (design §4.4, decision #15/#18): adult chat text lives
-- ONLY here. This database is on the same Patroni cluster as yral_agent_db
-- but is a SEPARATE database; YRAL/v2 services hold no credentials to it.
-- Nothing in here ever flows back into yral_agent_db.
--
-- Squawk-friendly: empty DB, all-additive, IDENTITY counters, guarded
-- statement_timeout so a slow migration can't hang the cluster.

SET statement_timeout = '30s';

-- web_sessions — backs our OWN httpOnly session cookie. user_id is the
-- v2 identity resolved via the valet-ticket handoff (§4.7); null for the
-- dev-only anonymous path. This is the wristband, not the login.
CREATE TABLE IF NOT EXISTS web_sessions (
    session_id   text PRIMARY KEY,
    user_id      text,
    is_anonymous boolean     NOT NULL DEFAULT false,
    bot_handle   text,
    created_at   timestamptz NOT NULL DEFAULT now(),
    last_seen_at timestamptz NOT NULL DEFAULT now(),
    expires_at   timestamptz NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_web_sessions_user ON web_sessions (user_id);

-- web_consent — the 18+ audit trail on the web side. The cookie is the
-- LIVE gate; this table is the record ("user said 18+ on <date>"). For
-- logged-in users v2 ALSO gets a per-account audit row via its own
-- endpoint — this is the web-local copy.
CREATE TABLE IF NOT EXISTS web_consent (
    id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id   text        NOT NULL REFERENCES web_sessions (session_id) ON DELETE CASCADE,
    user_id      text,
    bot_handle   text,
    confirmed_at timestamptz NOT NULL DEFAULT now(),
    source_ip    inet,
    user_agent   text
);

CREATE INDEX IF NOT EXISTS idx_web_consent_session ON web_consent (session_id);

-- conversations — one adult thread per (identity, bot) on the web brand.
-- user_id when logged in; session_id ties anon/dev threads together.
CREATE TABLE IF NOT EXISTS conversations (
    id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id    text,
    session_id text,
    bot_handle text        NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_conversations_user_bot ON conversations (user_id, bot_handle);
CREATE INDEX IF NOT EXISTS idx_conversations_session_bot ON conversations (session_id, bot_handle);

-- messages — THE adult chat text. Never leaves amorae_db.
CREATE TABLE IF NOT EXISTS messages (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    conversation_id bigint      NOT NULL REFERENCES conversations (id) ON DELETE CASCADE,
    role            text        NOT NULL,  -- 'user' | 'assistant'
    content         text        NOT NULL,
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages (conversation_id, created_at);
