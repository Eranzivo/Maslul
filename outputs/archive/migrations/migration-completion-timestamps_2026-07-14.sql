-- E4-lite Phase A — completion timestamps (applied via Supabase MCP 2026-07-14)
-- Capture real status-transition times so the reports duration-accuracy insight can
-- compare configured service duration vs actual time on site (completed_at − arrived_at).
-- All nullable; no backfill (historic rows stay NULL and are excluded from the insight).
-- Same RLS as the tasks table (no policy change). Scope: outputs/e4-completion-scope_2026-07-13.md
ALTER TABLE tasks
  ADD COLUMN IF NOT EXISTS en_route_at  TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS arrived_at   TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;
