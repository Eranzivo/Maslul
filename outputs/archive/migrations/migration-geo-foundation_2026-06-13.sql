-- Geo foundation — Layer A shared "brain" schema (applied 2026-06-13 via MCP).
-- Design: outputs/geo-foundation-design_2026-06-13.md. Deny-all RLS like route_cache
-- (service-key only; resolution lives in the backend, the frontend defers). PII-free.

CREATE TABLE IF NOT EXISTS geo_places (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  canonical_name text NOT NULL,
  normalized_key text NOT NULL UNIQUE,   -- from canonicalize.normalize_place_key
  lat double precision,
  lon double precision,
  source text DEFAULT 'seed',            -- seed | geocoded | manual
  confidence text DEFAULT 'high',
  created_at timestamptz DEFAULT now()
);
CREATE TABLE IF NOT EXISTS place_aliases (
  normalized_variant text PRIMARY KEY,   -- normalized spelling variant
  place_id uuid REFERENCES geo_places(id) ON DELETE CASCADE,
  source text DEFAULT 'seed',            -- seed | seed-fix | confirmed
  confirmed_by text,
  created_at timestamptz DEFAULT now()
);
CREATE TABLE IF NOT EXISTS place_resolution_log (   -- monitoring (Layer-A behavior)
  id bigserial PRIMARY KEY,
  raw_input text, normalized_key text, resolved_place_id uuid,
  method text,                           -- exact | alias | geocode | fuzzy_suggested | failed
  tenant_id uuid, created_at timestamptz DEFAULT now()
);
ALTER TABLE geo_places ENABLE ROW LEVEL SECURITY;
ALTER TABLE place_aliases ENABLE ROW LEVEL SECURITY;
ALTER TABLE place_resolution_log ENABLE ROW LEVEL SECURITY;

-- Seed (applied): geo_places ← cities.py CITY_COORDS deduped by normalized_key (157 rows);
-- place_aliases ← _CITY_ALIASES normalized (8) + corrective 'seed-fix' aliases mapping the
-- divergent zone/alias spellings to the place that actually exists:
--   נהרייה→נהריה ; קש/קריית שמונה→קרית שמונה ; זכרון/זיכרון/זכרון יעקב→זיכרון יעקב
-- Verified: every PureWater city (tasks + zones) resolves except חרב (genuine typo → needs_location).
-- NO live behavior change yet — the running optimizer still reads cities.py until resolution is
-- wired through canonicalize.py + geo_places (next, deliberate step).
