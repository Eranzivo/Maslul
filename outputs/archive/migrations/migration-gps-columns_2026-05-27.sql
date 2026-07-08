-- GPS location columns for technicians
-- Run in Supabase SQL Editor: https://app.supabase.com → SQL Editor

ALTER TABLE technicians
  ADD COLUMN IF NOT EXISTS last_lat  FLOAT,
  ADD COLUMN IF NOT EXISTS last_lon  FLOAT,
  ADD COLUMN IF NOT EXISTS last_seen TIMESTAMPTZ;

-- No RLS change needed — existing technician RLS already covers these columns.
-- Techs update their own row via dbUpsert; coordinator reads via existing SELECT policy.

COMMENT ON COLUMN technicians.last_lat  IS 'Last known GPS latitude from field worker app';
COMMENT ON COLUMN technicians.last_lon  IS 'Last known GPS longitude from field worker app';
COMMENT ON COLUMN technicians.last_seen IS 'Timestamp of last GPS update';
