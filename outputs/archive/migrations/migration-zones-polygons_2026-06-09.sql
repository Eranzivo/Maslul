-- Zones & Polygons foundation (additive, reversible)
-- Apply via Supabase SQL editor.

ALTER TABLE public.zones
  ADD COLUMN IF NOT EXISTS polygons JSONB;            -- array of [{lat,lng}, …] rings

-- Migrate existing single polygon → polygons[0]
UPDATE public.zones
  SET polygons = jsonb_build_array(polygon)
  WHERE polygon IS NOT NULL AND polygons IS NULL;

ALTER TABLE public.technicians
  ADD COLUMN IF NOT EXISTS blocked_zones TEXT[] NOT NULL DEFAULT '{}';

-- Verify
SELECT 'zones.polygons' AS col, count(*) FILTER (WHERE polygons IS NOT NULL) AS populated FROM public.zones
UNION ALL
SELECT 'tech.blocked_zones', count(*) FROM public.technicians WHERE array_length(blocked_zones,1) > 0;
