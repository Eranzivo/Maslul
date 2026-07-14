-- Cross-tenant brain Phase 0 — time-of-day bucketing on the global route brain
-- (applied via Supabase MCP 2026-07-14). Existing rows become 'static' (today's behavior);
-- PK extended so rush/live buckets coexist per leg. Default traffic_mode 'off' always resolves
-- to 'static' ⇒ zero behavior change until a tenant opts in. Deny-all RLS unchanged (global brain).
-- Design: outputs/cross-tenant-brain-design_2026-07-14.md
ALTER TABLE route_cache ADD COLUMN IF NOT EXISTS time_bucket TEXT NOT NULL DEFAULT 'static';
ALTER TABLE route_cache DROP CONSTRAINT route_cache_pkey;
ALTER TABLE route_cache ADD CONSTRAINT route_cache_pkey PRIMARY KEY (from_key, to_key, time_bucket);
