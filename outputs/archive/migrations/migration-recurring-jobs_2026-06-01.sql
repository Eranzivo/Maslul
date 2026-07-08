-- Migration: recurring jobs
-- Date: 2026-06-01
-- Run in Supabase SQL Editor (project pxpqcdfxogaajwstwdtk)
-- Safe to run multiple times (IF NOT EXISTS).

-- ─── 1. New table: recurring_templates ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS recurring_templates (
  id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id              UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  client_name            TEXT NOT NULL,
  client_phone           TEXT,
  city                   TEXT NOT NULL,
  street                 TEXT,
  category_id            UUID,
  category_name          TEXT,
  notes                  TEXT,
  day_of_week            INTEGER NOT NULL CHECK (day_of_week BETWEEN 0 AND 6),
  scheduled_time         TEXT NOT NULL,       -- HH:MM
  interval_weeks         INTEGER NOT NULL DEFAULT 1 CHECK (interval_weeks IN (1, 2, 4)),
  preferred_technician_id UUID REFERENCES technicians(id) ON DELETE SET NULL,
  lookahead_weeks        INTEGER NOT NULL DEFAULT 6,
  active                 BOOLEAN NOT NULL DEFAULT true,
  last_generated_date    DATE,
  created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- RLS: same pattern as all other tables
ALTER TABLE recurring_templates ENABLE ROW LEVEL SECURITY;

CREATE POLICY IF NOT EXISTS "tenant_isolation" ON recurring_templates
  USING (tenant_id = get_tenant_id() OR is_super_admin());

-- ─── 2. FK on tasks ─────────────────────────────────────────────────────────
ALTER TABLE tasks
  ADD COLUMN IF NOT EXISTS recurring_template_id UUID
    REFERENCES recurring_templates(id) ON DELETE SET NULL;

-- ─── 3. Index for fast lookup per template ───────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_tasks_recurring_template
  ON tasks (recurring_template_id, scheduled_date)
  WHERE recurring_template_id IS NOT NULL;
