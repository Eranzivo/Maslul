-- Migration: geocoding columns on tasks + polygon on zones
-- Date: 2026-06-07
-- Run in: Supabase SQL editor (project: pxpqcdfxogaajwstwdtk)

-- ── tasks: street-level geocoding cache ────────────────────────────────────────
ALTER TABLE tasks
  ADD COLUMN IF NOT EXISTS lat  DOUBLE PRECISION,
  ADD COLUMN IF NOT EXISTS lon  DOUBLE PRECISION,
  ADD COLUMN IF NOT EXISTS geocoded_at TIMESTAMPTZ;

-- ── zones: polygon vertices from the Leaflet draw tool ────────────────────────
-- Array of {lat, lng} objects. NULL = city-list zone (no drawn polygon).
ALTER TABLE zones
  ADD COLUMN IF NOT EXISTS polygon JSONB;
