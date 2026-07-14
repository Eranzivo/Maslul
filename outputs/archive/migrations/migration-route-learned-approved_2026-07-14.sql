-- Cross-tenant brain P2 APPROVAL GATE (applied via Supabase MCP 2026-07-14)
-- Learned durations NEVER auto-apply to routing. A trend from route_observations must be explicitly
-- APPROVED (business-owner decision, in the 🧠 מוח המערכת view) before the optimizer uses it.
-- get_learned_legs reads ONLY this table. Reversible (revoke = delete). Design:
-- outputs/cross-tenant-brain-design_2026-07-14.md
CREATE TABLE IF NOT EXISTS route_learned_approved (
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  from_key TEXT NOT NULL,
  to_key TEXT NOT NULL,
  time_bucket TEXT NOT NULL DEFAULT 'static',
  approved_min INTEGER NOT NULL,
  sample_count INTEGER NOT NULL DEFAULT 0,
  approved_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  approved_by UUID,
  PRIMARY KEY (tenant_id, from_key, to_key, time_bucket)
);
ALTER TABLE route_learned_approved ENABLE ROW LEVEL SECURITY;
CREATE POLICY rla_select ON route_learned_approved FOR SELECT
  USING ((tenant_id = current_tenant_id()) OR is_super_admin());
CREATE POLICY rla_insert ON route_learned_approved FOR INSERT
  WITH CHECK (is_super_admin() OR (tenant_id = current_tenant_id() AND current_user_role() = 'admin'));
CREATE POLICY rla_update ON route_learned_approved FOR UPDATE
  USING (is_super_admin() OR (tenant_id = current_tenant_id() AND current_user_role() = 'admin'));
CREATE POLICY rla_delete ON route_learned_approved FOR DELETE
  USING (is_super_admin() OR (tenant_id = current_tenant_id() AND current_user_role() = 'admin'));
