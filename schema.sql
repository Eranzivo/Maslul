-- ═══════════════════════════════════════════════════════════════
-- MASLUL — Complete Database Schema (authoritative, as of May 2026)
-- Run on a FRESH Supabase project for new deployments.
-- For existing DBs, see the MIGRATION section at the bottom.
-- ═══════════════════════════════════════════════════════════════

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ─── TENANTS ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tenants (
  id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name       TEXT NOT NULL,
  plan       TEXT NOT NULL DEFAULT 'pilot',  -- 'pilot' | 'starter' | 'pro'
  config     JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
-- config shape:
-- {
--   "labels":   { "worker","workers","task","tasks","zone","zones","dispatch" },
--   "defaults": { "regularTime","packageTime","window","maxDaily","lookahead",
--                 "monthlyVolume","startTime","endTime" },
--   "features": { "whatsapp_enabled","crm_enabled","files_enabled",
--                 "checklists_enabled","reports_enabled",
--                 "demo_mode","google_maps_enabled","odoo_integration" }
-- }

-- ─── USERS ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
  id          UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  tenant_id   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  role        TEXT NOT NULL DEFAULT 'coordinator',  -- 'admin'|'coordinator'|'worker'
  name        TEXT NOT NULL,
  super_admin BOOLEAN NOT NULL DEFAULT false,        -- Maslul product owner only
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── TECHNICIANS ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS technicians (
  id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id      UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  name           TEXT NOT NULL,
  phone          TEXT,
  base_city      TEXT,
  return_city    TEXT NOT NULL DEFAULT '',
  base_address   TEXT,
  color          TEXT DEFAULT '#2563EB',
  min_daily      INTEGER NOT NULL DEFAULT 2,
  max_daily      INTEGER NOT NULL DEFAULT 9,
  start_time     TEXT NOT NULL DEFAULT '07:00',
  end_time       TEXT NOT NULL DEFAULT '17:00',
  blocked_cities TEXT[] NOT NULL DEFAULT '{}',
  skills         TEXT[] NOT NULL DEFAULT '{}',      -- array of category UUIDs
  cat_limits     JSONB NOT NULL DEFAULT '{}'::jsonb, -- { "cat_uuid": max_per_day }
  rotation       JSONB NOT NULL DEFAULT '{}'::jsonb, -- { "0": zone_uuid, ... "5": zone_uuid }
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── ZONES ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS zones (
  id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id  UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  name       TEXT NOT NULL,
  cities     TEXT[] NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── CATEGORIES ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS categories (
  id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id        UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  name             TEXT NOT NULL,
  duration_minutes INTEGER NOT NULL DEFAULT 30,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── PACKAGES ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS packages (
  id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id  UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  name       TEXT NOT NULL,
  items      JSONB NOT NULL DEFAULT '[]'::jsonb,  -- [{ "catId": uuid, "qty": int }]
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── TASKS ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tasks (
  id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id      UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  assign_id      TEXT,
  client_name    TEXT NOT NULL,
  client_phone   TEXT DEFAULT '',
  city           TEXT,
  street         TEXT,
  category_id    TEXT,
  category_name  TEXT,
  technician_id  TEXT,
  status         TEXT NOT NULL DEFAULT 'pending',
  scheduled_date DATE,
  scheduled_time TEXT,
  notes          TEXT DEFAULT '',
  cancelled_at   TIMESTAMPTZ,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── DAY OFFS ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS day_offs (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id     UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  technician_id TEXT NOT NULL,
  date          DATE NOT NULL,
  type          TEXT NOT NULL DEFAULT 'full',  -- 'full' | 'partial'
  from_time     TEXT,
  to_time       TEXT,
  reason        TEXT DEFAULT '',
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── CLIENTS (CRM) ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS clients (
  id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  name        TEXT NOT NULL,
  phone       TEXT DEFAULT '',
  email       TEXT DEFAULT '',
  city        TEXT DEFAULT '',
  address     TEXT DEFAULT '',
  notes       TEXT DEFAULT '',
  archived    BOOLEAN NOT NULL DEFAULT false,
  archived_at TIMESTAMPTZ,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ═══════════════════════════════════════════════════════════════
-- ROW LEVEL SECURITY
-- ═══════════════════════════════════════════════════════════════

ALTER TABLE tenants     ENABLE ROW LEVEL SECURITY;
ALTER TABLE users       ENABLE ROW LEVEL SECURITY;
ALTER TABLE technicians ENABLE ROW LEVEL SECURITY;
ALTER TABLE zones       ENABLE ROW LEVEL SECURITY;
ALTER TABLE categories  ENABLE ROW LEVEL SECURITY;
ALTER TABLE packages    ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks       ENABLE ROW LEVEL SECURITY;
ALTER TABLE day_offs    ENABLE ROW LEVEL SECURITY;
ALTER TABLE clients     ENABLE ROW LEVEL SECURITY;

-- Resolves the calling user's tenant_id (SECURITY DEFINER bypasses RLS on users table)
CREATE OR REPLACE FUNCTION get_tenant_id()
RETURNS UUID LANGUAGE sql SECURITY DEFINER STABLE AS $$
  SELECT tenant_id FROM users WHERE id = auth.uid();
$$;

-- Returns true if the calling user has super_admin = true
CREATE OR REPLACE FUNCTION is_super_admin()
RETURNS BOOLEAN LANGUAGE sql SECURITY DEFINER STABLE AS $$
  SELECT COALESCE((SELECT super_admin FROM users WHERE id = auth.uid()), false);
$$;

-- Tenants: own row only, OR super_admin sees all
DROP POLICY IF EXISTS "tenant_select" ON tenants;
CREATE POLICY "tenant_select" ON tenants
  FOR SELECT USING (id = get_tenant_id() OR is_super_admin());

DROP POLICY IF EXISTS "tenant_update" ON tenants;
CREATE POLICY "tenant_update" ON tenants
  FOR UPDATE USING (id = get_tenant_id() OR is_super_admin());

DROP POLICY IF EXISTS "tenant_insert" ON tenants;
CREATE POLICY "tenant_insert" ON tenants
  FOR INSERT WITH CHECK (is_super_admin());

DROP POLICY IF EXISTS "tenant_delete" ON tenants;
CREATE POLICY "tenant_delete" ON tenants
  FOR DELETE USING (is_super_admin());

-- Users: own tenant, OR super_admin sees all
DROP POLICY IF EXISTS "users_all" ON users;
CREATE POLICY "users_all" ON users
  USING  (tenant_id = get_tenant_id() OR is_super_admin())
  WITH CHECK (tenant_id = get_tenant_id() OR is_super_admin());

-- All business tables: own tenant OR super_admin (for cross-tenant admin panel)
-- JS queries always filter by currentTenantId, so super_admin sees only the entered tenant's data
DROP POLICY IF EXISTS "techs_all"   ON technicians;
CREATE POLICY "techs_all"   ON technicians
  USING (tenant_id = get_tenant_id() OR is_super_admin())
  WITH CHECK (tenant_id = get_tenant_id() OR is_super_admin());

DROP POLICY IF EXISTS "zones_all"   ON zones;
CREATE POLICY "zones_all"   ON zones
  USING (tenant_id = get_tenant_id() OR is_super_admin())
  WITH CHECK (tenant_id = get_tenant_id() OR is_super_admin());

DROP POLICY IF EXISTS "cats_all"    ON categories;
CREATE POLICY "cats_all"    ON categories
  USING (tenant_id = get_tenant_id() OR is_super_admin())
  WITH CHECK (tenant_id = get_tenant_id() OR is_super_admin());

DROP POLICY IF EXISTS "pkgs_all"    ON packages;
CREATE POLICY "pkgs_all"    ON packages
  USING (tenant_id = get_tenant_id() OR is_super_admin())
  WITH CHECK (tenant_id = get_tenant_id() OR is_super_admin());

DROP POLICY IF EXISTS "tasks_all"   ON tasks;
CREATE POLICY "tasks_all"   ON tasks
  USING (tenant_id = get_tenant_id() OR is_super_admin())
  WITH CHECK (tenant_id = get_tenant_id() OR is_super_admin());

DROP POLICY IF EXISTS "dayoffs_all" ON day_offs;
CREATE POLICY "dayoffs_all" ON day_offs
  USING (tenant_id = get_tenant_id() OR is_super_admin())
  WITH CHECK (tenant_id = get_tenant_id() OR is_super_admin());

DROP POLICY IF EXISTS "clients_all" ON clients;
CREATE POLICY "clients_all" ON clients
  USING (tenant_id = get_tenant_id() OR is_super_admin())
  WITH CHECK (tenant_id = get_tenant_id() OR is_super_admin());

-- ═══════════════════════════════════════════════════════════════
-- GRANTS (required from May 2026 — Supabase no longer auto-grants)
-- RLS policies above still enforce all tenant isolation.
-- ═══════════════════════════════════════════════════════════════

GRANT USAGE ON SCHEMA public TO anon, authenticated, service_role;

GRANT ALL ON public.tenants     TO authenticated, service_role;
GRANT ALL ON public.users       TO authenticated, service_role;
GRANT ALL ON public.technicians TO authenticated, service_role;
GRANT ALL ON public.zones       TO authenticated, service_role;
GRANT ALL ON public.categories  TO authenticated, service_role;
GRANT ALL ON public.packages    TO authenticated, service_role;
GRANT ALL ON public.tasks       TO authenticated, service_role;
GRANT ALL ON public.day_offs    TO authenticated, service_role;
GRANT ALL ON public.clients     TO authenticated, service_role;

-- ═══════════════════════════════════════════════════════════════
-- INDEXES
-- ═══════════════════════════════════════════════════════════════

CREATE INDEX IF NOT EXISTS idx_tasks_tenant_date     ON tasks(tenant_id, scheduled_date);
CREATE INDEX IF NOT EXISTS idx_tasks_tenant_status   ON tasks(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_tasks_technician      ON tasks(technician_id);
CREATE INDEX IF NOT EXISTS idx_dayoffs_tech_date     ON day_offs(technician_id, date);
CREATE INDEX IF NOT EXISTS idx_technicians_tenant    ON technicians(tenant_id);
CREATE INDEX IF NOT EXISTS idx_clients_tenant        ON clients(tenant_id, archived);

-- ═══════════════════════════════════════════════════════════════
-- MIGRATION: run on existing databases to bring them up to date
-- All statements are idempotent (safe to re-run)
-- ═══════════════════════════════════════════════════════════════

ALTER TABLE tenants     ADD COLUMN IF NOT EXISTS plan        TEXT NOT NULL DEFAULT 'pilot';
ALTER TABLE tenants     ADD COLUMN IF NOT EXISTS config      JSONB NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE users       ADD COLUMN IF NOT EXISTS super_admin   BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE users       ADD COLUMN IF NOT EXISTS created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW();
ALTER TABLE users       ADD COLUMN IF NOT EXISTS email         TEXT NOT NULL DEFAULT '';
ALTER TABLE users       ADD COLUMN IF NOT EXISTS permissions   JSONB NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE technicians ADD COLUMN IF NOT EXISTS base_address   TEXT;
ALTER TABLE technicians ADD COLUMN IF NOT EXISTS return_city    TEXT NOT NULL DEFAULT '';
ALTER TABLE technicians ADD COLUMN IF NOT EXISTS user_id        UUID REFERENCES auth.users(id);
ALTER TABLE technicians ADD COLUMN IF NOT EXISTS cat_limits     JSONB NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE technicians ADD COLUMN IF NOT EXISTS rotation       JSONB NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE technicians ADD COLUMN IF NOT EXISTS skills          TEXT[] NOT NULL DEFAULT '{}';
ALTER TABLE technicians ADD COLUMN IF NOT EXISTS weekly_schedule JSONB NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE technicians ADD COLUMN IF NOT EXISTS blocked_cities TEXT[] NOT NULL DEFAULT '{}';
ALTER TABLE tasks       ADD COLUMN IF NOT EXISTS assign_id    TEXT;
ALTER TABLE tasks       ADD COLUMN IF NOT EXISTS cancelled_at TIMESTAMPTZ;
ALTER TABLE tasks       ADD COLUMN IF NOT EXISTS client_phone TEXT DEFAULT '';
ALTER TABLE clients     ADD COLUMN IF NOT EXISTS archived     BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE clients     ADD COLUMN IF NOT EXISTS archived_at  TIMESTAMPTZ;
ALTER TABLE tasks       ADD COLUMN IF NOT EXISTS preferred_windows JSONB NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE tasks       ADD COLUMN IF NOT EXISTS checklist_done   JSONB NOT NULL DEFAULT '{}'::jsonb;

-- ═══════════════════════════════════════════════════════════════
-- AUDIT LOG
-- Permanent record of every INSERT / UPDATE / DELETE on all
-- critical tables. Lives inside Supabase — unaffected by client
-- cache, JS bugs, or app restarts. Use it to answer:
-- "what happened to that zone / technician / task and when?"
--
-- Query example (find recent zone changes for Israel):
--   SELECT created_at, operation,
--          old_data->'cities' AS before,
--          new_data->'cities' AS after
--   FROM   audit_log
--   WHERE  table_name = 'zones'
--     AND  tenant_id  = '00000000-0000-0000-0000-000000000001'
--   ORDER  BY created_at DESC LIMIT 20;
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS audit_log (
  id          UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  tenant_id   UUID,
  table_name  TEXT        NOT NULL,
  operation   TEXT        NOT NULL,  -- INSERT | UPDATE | DELETE
  record_id   UUID,
  old_data    JSONB,
  new_data    JSONB
);

-- Index for fast per-tenant lookups
CREATE INDEX IF NOT EXISTS idx_audit_tenant_table ON audit_log(tenant_id, table_name, created_at DESC);

-- RLS: each tenant sees only their own audit rows; super_admin sees all
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "audit_read" ON audit_log;
CREATE POLICY "audit_read" ON audit_log
  FOR SELECT USING (tenant_id = get_tenant_id() OR is_super_admin());

-- Grant read access to authenticated users (writes come only from the trigger, as SECURITY DEFINER)
GRANT SELECT ON public.audit_log TO authenticated;
GRANT ALL    ON public.audit_log TO service_role;

-- Trigger function — runs as SECURITY DEFINER so it bypasses RLS on write
CREATE OR REPLACE FUNCTION _maslul_audit_trigger()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
  INSERT INTO public.audit_log (tenant_id, table_name, operation, record_id, old_data, new_data)
  VALUES (
    COALESCE(
      (CASE WHEN TG_OP = 'DELETE' THEN OLD.tenant_id ELSE NEW.tenant_id END),
      NULL
    ),
    TG_TABLE_NAME,
    TG_OP,
    COALESCE(
      (CASE WHEN TG_OP = 'DELETE' THEN OLD.id ELSE NEW.id END),
      NULL
    ),
    CASE WHEN TG_OP = 'INSERT' THEN NULL ELSE to_jsonb(OLD) END,
    CASE WHEN TG_OP = 'DELETE' THEN NULL ELSE to_jsonb(NEW) END
  );
  RETURN COALESCE(NEW, OLD);
END;
$$;

-- Apply to all critical tables (idempotent — DROP IF EXISTS before CREATE)
DROP TRIGGER IF EXISTS _audit_technicians ON technicians;
CREATE TRIGGER _audit_technicians
  AFTER INSERT OR UPDATE OR DELETE ON technicians
  FOR EACH ROW EXECUTE FUNCTION _maslul_audit_trigger();

DROP TRIGGER IF EXISTS _audit_tasks ON tasks;
CREATE TRIGGER _audit_tasks
  AFTER INSERT OR UPDATE OR DELETE ON tasks
  FOR EACH ROW EXECUTE FUNCTION _maslul_audit_trigger();

DROP TRIGGER IF EXISTS _audit_zones ON zones;
CREATE TRIGGER _audit_zones
  AFTER INSERT OR UPDATE OR DELETE ON zones
  FOR EACH ROW EXECUTE FUNCTION _maslul_audit_trigger();

DROP TRIGGER IF EXISTS _audit_categories ON categories;
CREATE TRIGGER _audit_categories
  AFTER INSERT OR UPDATE OR DELETE ON categories
  FOR EACH ROW EXECUTE FUNCTION _maslul_audit_trigger();

DROP TRIGGER IF EXISTS _audit_packages ON packages;
CREATE TRIGGER _audit_packages
  AFTER INSERT OR UPDATE OR DELETE ON packages
  FOR EACH ROW EXECUTE FUNCTION _maslul_audit_trigger();

DROP TRIGGER IF EXISTS _audit_day_offs ON day_offs;
CREATE TRIGGER _audit_day_offs
  AFTER INSERT OR UPDATE OR DELETE ON day_offs
  FOR EACH ROW EXECUTE FUNCTION _maslul_audit_trigger();

-- ═══════════════════════════════════════════════════════════════
-- ONBOARD A NEW CLIENT (use the Master Admin panel in-app,
-- or run this SQL manually)
-- ═══════════════════════════════════════════════════════════════

/*
-- STEP 1: Create tenant row (app does this via Master Admin panel)
INSERT INTO tenants (name, plan, config) VALUES (
  'Company Name',
  'pilot',
  '{
    "labels":   { "worker":"טכנאי","workers":"טכנאים","task":"קריאה","tasks":"קריאות",
                  "zone":"אזור","zones":"אזורים","dispatch":"שיבוץ קריאה" },
    "defaults": { "regularTime":30,"packageTime":45,"window":3,"maxDaily":9,
                  "lookahead":30,"monthlyVolume":300,"startTime":"07:00","endTime":"18:00" },
    "features": { "whatsapp_enabled":false,"crm_enabled":false,"files_enabled":false,
                  "checklists_enabled":false,"reports_enabled":false,
                  "demo_mode":false,"google_maps_enabled":false,"odoo_integration":false }
  }'::jsonb
) RETURNING id;

-- STEP 2: Create Auth user in Supabase Dashboard → Authentication → Users → Add user
-- Copy the UUID shown after creation.

-- STEP 3: Link auth user to tenant
INSERT INTO users (id, tenant_id, role, name, super_admin) VALUES (
  '<auth-user-uuid>',
  '<tenant-uuid-from-step-1>',
  'admin',
  'Contact Name',
  false
);
*/

-- ═══════════════════════════════════════════════════════════════
-- CLIENTS (existing deployments)
-- Israel / PureWater — tenant_id: 00000000-0000-0000-0000-000000000001
-- Eran Zivo (super_admin) — auth UID: 9659f0bd-c8ad-4241-b8f7-a3d5e5375de6
-- Israel        (admin)   — auth UID: 285c6497-37ad-4ec9-84b8-1f51df285956
-- ═══════════════════════════════════════════════════════════════
