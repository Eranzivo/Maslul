-- Global drive-time cache (tenant-independent). Backend-only (service key); frontend never reads it.
CREATE TABLE IF NOT EXISTS public.route_cache (
  from_key      TEXT NOT NULL,           -- normalized "lat,lon" (4 dp) or city name
  to_key        TEXT NOT NULL,           -- directional: A→B may differ from B→A
  drive_minutes INTEGER NOT NULL,
  drive_meters  INTEGER,
  source        TEXT NOT NULL DEFAULT 'google',  -- 'google' | 'haversine'
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (from_key, to_key)
);
-- Lock it down: only the service role (backend) touches it. No anon/authenticated access.
ALTER TABLE public.route_cache ENABLE ROW LEVEL SECURITY;
-- (No policies → RLS denies all non-service-role access. Service key bypasses RLS.)
