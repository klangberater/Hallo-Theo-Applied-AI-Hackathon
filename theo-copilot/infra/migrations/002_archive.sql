-- Mark-as-done / Archive feature (per spec).
--
-- States are derived from done_at:
--   open       = done_at IS NULL AND status != 'closed'
--   done       = done_at >= now() - INTERVAL '72 hours'    (stays in inbox)
--   archived   = done_at <  now() - INTERVAL '72 hours'    (moved to archive)
--                OR status = 'closed' (legacy seed tickets are already archived)
--
-- We deliberately don't store `archived_at` — it's a derived state, computed
-- at read time. No background job needed.
--
-- This migration is also applied idempotently from
-- theo-copilot/app/db_sync.py::_ensure_schema() on every connection, so the
-- demo doesn't depend on a manual migration step.

ALTER TABLE theo.tickets
    ADD COLUMN IF NOT EXISTS done_at         TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS done_by         TEXT,
    ADD COLUMN IF NOT EXISTS resolution_note TEXT;

CREATE INDEX IF NOT EXISTS idx_tickets_done_at ON theo.tickets(done_at)
    WHERE done_at IS NOT NULL;
