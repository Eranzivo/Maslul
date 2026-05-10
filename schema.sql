-- ═══════════════════════════════════════════════════════════════
-- MASLUL — Complete Database Schema
-- Run this in the Supabase SQL editor for fresh setup.
-- For existing databases, see the ALTER / MIGRATION section at bottom.
-- ═══════════════════════════════════════════════════════════════

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ─── TENANTS ─────────────────────────────────────────────────────
-- One row per business. config drives all labels and defaults.
CREATE TABLE IF NOT EXISTS tenants (
  id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name       TEXT NOT NULL,
  plan       TEXT NOT NULL DEFAULT 'pilot',  -- 'pilot' | 'starter' | 'pro'
  config     JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
-- config JSONB shape:
-- {
--   "labels": {
--     "worker": "טכנאי",   "workers": "טכנאים",
--     "task":   "קריאה",   "tasks":   "קריאות",
--     "zone":   "אזור",    "zones":   "אזורים",
--     "dispatch": "שיבוץ קריאה"
--   },
--   "defaults": {
--     "regular_job_minutes": 30,  "package_job_minutes": 45,
--     "arrival_window_hours": 3,  "max_daily_jobs": 9,
--     "lookahead_days": 30,       "monthly_volume": 300,
--     "work_start": "07:00",      "work_end": "18:00"
--   },
--   "features": {
--     "whatsapp_enabled": true,   "demo_mode": false,
--     "google_maps_enabled": false, "odoo_integration": false
--   }
-- }

-- ─── USERS ───────────────────────────────────────────────────────
-- One row per human who logs in. id matches Supabase Auth uid.
CREATE TABLE IF NOT EXISTS users (
  id         UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  tenant_id  UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  role       TEXT NOT NULL DEFAULT 'coordinator', -- 'admin' | 'coordinator' | 'worker'
  name       TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── TECHNICIANS ─────────────────────────────────────────────────
-- Field workers (technicians, drivers, cleaners, etc.)
CREATE TABLE IF NOT EXISTS technicians (
  id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id      UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  name           TEXT NOT NULL,
  phone          TEXT,
  base_city      TEXT,
  color          TEXT DEFAULT '#2563EB',
  min_daily      INTEGER NOT NULL DEFAULT 2,
  max_daily      INTEGER NOT NULL DEFAULT 9,
  start_time     TEXT NOT NULL DEFAULT '07:00',  -- HH:MM
  end_time       TEXT NOT NULL DEFAULT '17:00',  -- HH:MM
  blocked_cities TEXT[] NOT NULL DEFAULT '{}',
  skills         TEXT[] NOT NULL DEFAULT '{}',   -- array of category UUIDs
  cat_limits     JSONB NOT NULL DEFAULT '{}'::jsonb, -- { "cat_uuid": max_per_day }
  rotation       JSONB NOT NULL DEFAULT '{}'::jsonb, -- { "0": zone_uuid, ..., "5": zone_uuid }
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── ZONES ───────────────────────────────────────────────────────
-- Geographic service areas. Each technician has one zone per weekday via rotation.
CREATE TABLE IF NOT EXISTS zones (
  id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id  UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  name       TEXT NOT NULL,
  cities     TEXT[] NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── CATEGORIES ──────────────────────────────────────────────────
-- Types of work / service types.
CREATE TABLE IF NOT EXISTS categories (
  id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id        UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  name             TEXT NOT NULL,
  duration_minutes INTEGER NOT NULL DEFAULT 30,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── PACKAGES ────────────────────────────────────────────────────
-- Bundles of multiple categories in one job (e.g. "garbage disposal + water system").
CREATE TABLE IF NOT EXISTS packages (
  id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id  UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  name       TEXT NOT NULL,
  items      JSONB NOT NULL DEFAULT '[]'::jsonb,  -- [{ "catId": uuid, "qty": int }]
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── TASKS ───────────────────────────────────────────────────────
-- Individual work orders / jobs / deliveries.
-- category_id and technician_id are stored as TEXT to support both UUID and legacy formats.
CREATE TABLE IF NOT EXISTS tasks (
  id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id      UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  assign_id      TEXT,                          -- MSL-XXXXX display ID
  client_name    TEXT NOT NULL,
  client_phone   TEXT DEFAULT '',
  city           TEXT,
  street         TEXT,
  category_id    TEXT,                          -- category UUID
  category_name  TEXT,                          -- denormalized for display speed
  technician_id  TEXT,                          -- technician UUID (null = unassigned)
  status         TEXT NOT NULL DEFAULT 'pending',
  -- pending | assigned | en_route | arrived | completed | issue | cancelled
  scheduled_date DATE,
  scheduled_time TEXT,                          -- HH:MM
  notes          TEXT DEFAULT '',
  cancelled_at   TIMESTAMPTZ,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── DAY OFFS ────────────────────────────────────────────────────
-- Technician unavailability (full day or partial hours).
CREATE TABLE IF NOT EXISTS day_offs (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id     UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  technician_id TEXT NOT NULL,   -- technician UUID
  date          DATE NOT NULL,
  type          TEXT NOT NULL DEFAULT 'full',  -- 'full' | 'partial'
  from_time     TEXT,            -- HH:MM, only when type='partial'
  to_time       TEXT,            -- HH:MM, only when type='partial'
  reason        TEXT DEFAULT '',
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ═══════════════════════════════════════════════════════════════
-- ROW LEVEL SECURITY
-- Every table is fully isolated by tenant_id.
-- ═══════════════════════════════════════════════════════════════

ALTER TABLE tenants     ENABLE ROW LEVEL SECURITY;
ALTER TABLE users       ENABLE ROW LEVEL SECURITY;
ALTER TABLE technicians ENABLE ROW LEVEL SECURITY;
ALTER TABLE zones       ENABLE ROW LEVEL SECURITY;
ALTER TABLE categories  ENABLE ROW LEVEL SECURITY;
ALTER TABLE packages    ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks       ENABLE ROW LEVEL SECURITY;
ALTER TABLE day_offs    ENABLE ROW LEVEL SECURITY;

-- Helper function: resolves the current auth user's tenant_id.
-- SECURITY DEFINER so it runs with elevated rights to read the users table.
CREATE OR REPLACE FUNCTION get_tenant_id()
RETURNS UUID
LANGUAGE sql SECURITY DEFINER STABLE AS $$
  SELECT tenant_id FROM users WHERE id = auth.uid();
$$;

-- Tenants: users can only read their own tenant row.
DROP POLICY IF EXISTS "tenant_select" ON tenants;
CREATE POLICY "tenant_select" ON tenants
  FOR SELECT USING (id = get_tenant_id());

-- All other tables: full CRUD scoped to the authenticated user's tenant.
DROP POLICY IF EXISTS "users_all"   ON users;       CREATE POLICY "users_all"   ON users       USING (tenant_id = get_tenant_id());
DROP POLICY IF EXISTS "techs_all"   ON technicians; CREATE POLICY "techs_all"   ON technicians USING (tenant_id = get_tenant_id());
DROP POLICY IF EXISTS "zones_all"   ON zones;       CREATE POLICY "zones_all"   ON zones       USING (tenant_id = get_tenant_id());
DROP POLICY IF EXISTS "cats_all"    ON categories;  CREATE POLICY "cats_all"    ON categories  USING (tenant_id = get_tenant_id());
DROP POLICY IF EXISTS "pkgs_all"    ON packages;    CREATE POLICY "pkgs_all"    ON packages    USING (tenant_id = get_tenant_id());
DROP POLICY IF EXISTS "tasks_all"   ON tasks;       CREATE POLICY "tasks_all"   ON tasks       USING (tenant_id = get_tenant_id());
DROP POLICY IF EXISTS "dayoffs_all" ON day_offs;    CREATE POLICY "dayoffs_all" ON day_offs    USING (tenant_id = get_tenant_id());

-- ═══════════════════════════════════════════════════════════════
-- MIGRATION: if tables already exist (upgrade from settings → config)
-- Run only once on existing databases.
-- ═══════════════════════════════════════════════════════════════

-- Add missing columns if upgrading from earlier schema
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS plan TEXT NOT NULL DEFAULT 'pilot';
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS config JSONB NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

ALTER TABLE technicians ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
ALTER TABLE zones       ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
ALTER TABLE categories  ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
ALTER TABLE packages    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
ALTER TABLE tasks       ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
ALTER TABLE tasks       ADD COLUMN IF NOT EXISTS cancelled_at TIMESTAMPTZ;
ALTER TABLE day_offs    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
ALTER TABLE users       ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

-- Migrate existing `settings` JSONB into the new `config` structure
-- (only affects rows where config is still empty)
UPDATE tenants
SET config = jsonb_build_object(
  'labels', jsonb_build_object(
    'worker', 'טכנאי', 'workers', 'טכנאים',
    'task',   'קריאה', 'tasks',   'קריאות',
    'zone',   'אזור',  'zones',   'אזורים',
    'dispatch', 'שיבוץ קריאה'
  ),
  'defaults', COALESCE(settings, '{}'::jsonb),
  'features', jsonb_build_object(
    'whatsapp_enabled', true,
    'demo_mode', false,
    'google_maps_enabled', false,
    'odoo_integration', false
  )
)
WHERE config = '{}'::jsonb;

-- ═══════════════════════════════════════════════════════════════
-- ONBOARD A NEW TENANT
-- Copy this block, fill in the values, run once per client.
-- ═══════════════════════════════════════════════════════════════

/*
-- STEP 1: Create the tenant row
INSERT INTO tenants (id, name, plan, config) VALUES (
  uuid_generate_v4(),       -- or a fixed UUID for easy reference
  'Company Name Here',
  'pilot',
  '{
    "labels": {
      "worker": "טכנאי", "workers": "טכנאים",
      "task":   "קריאה", "tasks":   "קריאות",
      "zone":   "אזור",  "zones":   "אזורים",
      "dispatch": "שיבוץ קריאה"
    },
    "defaults": {
      "regular_job_minutes": 30,  "package_job_minutes": 45,
      "arrival_window_hours": 3,  "max_daily_jobs": 9,
      "lookahead_days": 30,       "monthly_volume": 300,
      "work_start": "07:00",      "work_end": "18:00"
    },
    "features": {
      "whatsapp_enabled": true,   "demo_mode": false,
      "google_maps_enabled": false, "odoo_integration": false
    }
  }'::jsonb
) RETURNING id;  -- copy this UUID for steps below

-- STEP 2: Create a Supabase Auth user
-- Use the Supabase dashboard → Authentication → Users → Add user
-- OR via API: POST /auth/v1/admin/users with email + password

-- STEP 3: Link the Auth user to the tenant
INSERT INTO users (id, tenant_id, role, name) VALUES (
  '<paste-auth-user-uuid-from-step-2>',
  '<paste-tenant-uuid-from-step-1>',
  'admin',
  'Name Here'
);

-- STEP 4: Seed zones (example for field service in Israel)
INSERT INTO zones (tenant_id, name, cities) VALUES
  ('<tenant_id>', 'גוש דן', ARRAY['תל אביב','חולון','בת ים','ראשון לציון','רמת גן','גבעתיים','פתח תקווה','בני ברק']),
  ('<tenant_id>', 'שרון',   ARRAY['נתניה','הרצליה','כפר סבא','רעננה','הוד השרון']),
  ('<tenant_id>', 'שפלה',   ARRAY['רחובות','נס ציונה','לוד','רמלה','מודיעין']),
  ('<tenant_id>', 'דרום',   ARRAY['אשדוד','אשקלון','באר שבע','קריית גת']);

-- STEP 5: Seed categories (customize per business type)
INSERT INTO categories (tenant_id, name, duration_minutes) VALUES
  ('<tenant_id>', 'טוחן אשפה',   30),
  ('<tenant_id>', 'מערכת מים',   30),
  ('<tenant_id>', 'מרכך אבנית',  30),
  ('<tenant_id>', 'קריאת שירות', 30);
*/

-- ═══════════════════════════════════════════════════════════════
-- USEFUL INDEXES (add after data grows)
-- ═══════════════════════════════════════════════════════════════

CREATE INDEX IF NOT EXISTS idx_tasks_tenant_date     ON tasks(tenant_id, scheduled_date);
CREATE INDEX IF NOT EXISTS idx_tasks_tenant_status   ON tasks(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_tasks_technician      ON tasks(technician_id);
CREATE INDEX IF NOT EXISTS idx_dayoffs_tech_date     ON day_offs(technician_id, date);
CREATE INDEX IF NOT EXISTS idx_technicians_tenant    ON technicians(tenant_id);
