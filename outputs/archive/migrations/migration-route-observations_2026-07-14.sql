-- Cross-tenant brain Phase 1 — route_observations (applied via Supabase MCP 2026-07-14)
-- Tenant-scoped, append-only log of observed travel legs (from E4-lite execution timestamps).
-- Write-only from the app (logLegObservation, fire-and-forget); the Tier-2 supervisor reads it
-- cross-tenant via the service key to promote corroborated legs into route_cache. PII-free
-- (physical legs only). Design: outputs/cross-tenant-brain-design_2026-07-14.md
CREATE TABLE IF NOT EXISTS route_observations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  from_key TEXT NOT NULL,
  to_key TEXT NOT NULL,
  time_bucket TEXT NOT NULL DEFAULT 'static',
  observed_min INTEGER NOT NULL,
  source TEXT NOT NULL DEFAULT 'timestamps',
  task_id UUID,
  observed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS route_observations_leg_idx ON route_observations (from_key, to_key, time_bucket);
CREATE INDEX IF NOT EXISTS route_observations_tenant_idx ON route_observations (tenant_id);

ALTER TABLE route_observations ENABLE ROW LEVEL SECURITY;
-- Append-only: INSERT for any authenticated tenant member (coordinators AND technicians) +
-- super_admin; SELECT for the tenant + super_admin; NO update/delete ⇒ rows immutable via API.
CREATE POLICY route_obs_insert ON route_observations FOR INSERT
  WITH CHECK ((tenant_id = current_tenant_id()) OR is_super_admin());
CREATE POLICY route_obs_select ON route_observations FOR SELECT
  USING ((tenant_id = current_tenant_id()) OR is_super_admin());
