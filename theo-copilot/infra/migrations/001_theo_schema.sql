-- Theo Copilot — initial schema
-- Per PRODUCT_SPEC §6.1. Target: fletcher-db (postgres:16 + pgvector).
--
-- Apply with:
--   docker exec -i fletcher-db psql -U fletcher -d fletcher \
--     < theo-copilot/infra/migrations/001_theo_schema.sql
--
-- All tables live under the `theo` schema. The agent's connection should
-- set search_path = theo, public before queries.

CREATE SCHEMA IF NOT EXISTS theo;
SET search_path TO theo, public;

-- ---------------------------------------------------------------------------
-- Core entities
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS properties (
    id        TEXT PRIMARY KEY,
    name      TEXT,
    address   TEXT,
    owner     TEXT,
    metadata  JSONB
);

CREATE TABLE IF NOT EXISTS units (
    id           TEXT PRIMARY KEY,
    property_id  TEXT REFERENCES properties(id),
    label        TEXT,
    qm           REAL,
    type         TEXT
);

CREATE TABLE IF NOT EXISTS tenants (
    id        TEXT PRIMARY KEY,
    name      TEXT,
    email     TEXT,
    phone     TEXT,
    metadata  JSONB
);

CREATE TABLE IF NOT EXISTS leases (
    id          TEXT PRIMARY KEY,
    unit_id     TEXT REFERENCES units(id),
    tenant_id   TEXT REFERENCES tenants(id),
    start_date  DATE,
    end_date    DATE,
    rent_cold   NUMERIC(10,2),
    status      TEXT,
    full_text   TEXT
);

CREATE TABLE IF NOT EXISTS vendors (
    id              TEXT PRIMARY KEY,
    name            TEXT,
    trade           TEXT,
    status          TEXT,
    contract_until  DATE,
    notes           TEXT
);

-- ---------------------------------------------------------------------------
-- Events / artifacts
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS tickets (
    id                  TEXT PRIMARY KEY,
    unit_id             TEXT REFERENCES units(id),
    category            TEXT,
    priority            TEXT,
    opened_at           TIMESTAMPTZ,
    closed_at           TIMESTAMPTZ,
    resolution          TEXT,
    cost                NUMERIC(10,2),
    vendor_id           TEXT REFERENCES vendors(id),
    full_text           TEXT,
    source_thread_id    TEXT,
    classified_intent   TEXT,
    status              TEXT,         -- open | enriching | ready_for_review |
                                      -- awaiting_vendor | awaiting_tenant | closed
    enrichment          JSONB,        -- cached EnrichmentPayload
    suggested_actions   JSONB
);

CREATE TABLE IF NOT EXISTS invoices (
    id              TEXT PRIMARY KEY,
    vendor_id       TEXT REFERENCES vendors(id),
    unit_id         TEXT REFERENCES units(id),
    amount_brutto   NUMERIC(10,2),
    issued_at       DATE,
    line_items      TEXT,
    raw_text        TEXT,
    has_itemization BOOLEAN
);

CREATE TABLE IF NOT EXISTS emails (
    id            TEXT PRIMARY KEY,
    from_address  TEXT,
    to_address    TEXT,
    subject       TEXT,
    body          TEXT,
    received_at   TIMESTAMPTZ,
    thread_id     TEXT,
    unit_id       TEXT
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id         TEXT PRIMARY KEY,
    thread_id  TEXT,
    sender     TEXT,
    body       TEXT,
    sent_at    TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS nka (
    id         TEXT PRIMARY KEY,
    unit_id    TEXT REFERENCES units(id),
    year       INTEGER,
    total      NUMERIC(10,2),
    breakdown  JSONB,
    raw_text   TEXT
);

CREATE TABLE IF NOT EXISTS vendor_offers (
    id         TEXT PRIMARY KEY,
    vendor_id  TEXT REFERENCES vendors(id),
    unit_id    TEXT REFERENCES units(id),
    scope      TEXT,
    amount     NUMERIC(10,2),
    status     TEXT,
    issued_at  DATE
);

-- ---------------------------------------------------------------------------
-- Channel-side state
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS channel_threads (
    id               TEXT PRIMARY KEY,
    channel          TEXT,                              -- whatsapp | email | voicemail | portal
    external_id      TEXT,                              -- WhatsApp chat id, email thread id
    tenant_id        TEXT REFERENCES tenants(id),
    unit_id          TEXT REFERENCES units(id),
    last_message_at  TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS channel_messages (
    id                 TEXT PRIMARY KEY,
    thread_id          TEXT REFERENCES channel_threads(id),
    direction          TEXT,                            -- inbound | outbound
    sender             TEXT,
    body               TEXT,
    sent_at            TIMESTAMPTZ,
    media_attachments  JSONB
);

CREATE TABLE IF NOT EXISTS vendor_dispatches (
    id              SERIAL PRIMARY KEY,
    ticket_id       TEXT REFERENCES tickets(id),
    vendor_id       TEXT REFERENCES vendors(id),
    scope           TEXT,
    urgency         TEXT,
    dispatched_at   TIMESTAMPTZ
);

-- The agent writes proposals here; the UI is the approval gate.
CREATE TABLE IF NOT EXISTS proposed_actions (
    id           SERIAL PRIMARY KEY,
    proposed_at  TIMESTAMPTZ,
    action_type  TEXT,
    payload      JSONB,
    rationale    TEXT,
    status       TEXT            -- pending | approved | rejected | edited
);

-- ---------------------------------------------------------------------------
-- Trace / audit (for the "Why?" toggle in the UI, §8 View 3)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS trace_events (
    id          BIGSERIAL PRIMARY KEY,
    ticket_id   TEXT,
    step        INTEGER,        -- monotonic per ticket
    kind        TEXT,           -- llm_call | tool_use | tool_result | enrichment | error
    payload     JSONB,
    created_at  TIMESTAMPTZ DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- Indexes (only the ones likely to matter under demo load)
-- ---------------------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_tickets_status         ON tickets(status);
CREATE INDEX IF NOT EXISTS idx_tickets_unit           ON tickets(unit_id);
CREATE INDEX IF NOT EXISTS idx_channel_messages_thread ON channel_messages(thread_id, sent_at);
CREATE INDEX IF NOT EXISTS idx_tenants_phone          ON tenants(phone);
CREATE INDEX IF NOT EXISTS idx_trace_events_ticket    ON trace_events(ticket_id, step);
