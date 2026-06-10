-- PureWater: re-link technician rotations to CURRENT zone IDs (by name).
-- Why this exists: rotations store zone IDs. When zones are re-created (zones-polygons
-- work, June 2026) the IDs change and the stored rotation orphans → the rotation grid
-- shows "—". This re-resolves zone + tech IDs by NAME at run-time, so it always targets
-- the live rows. Safe & idempotent. Division confirmed by Israel (WhatsApp, 2026-06-10).
-- Run in Supabase SQL editor.

DO $$
DECLARE
  pw_id UUID := '00000000-0000-0000-0000-000000000001';
  z_darom UUID; z_lod UUID; z_nahariya UUID; z_tlv UUID; z_rosh UUID;
  z_jeru UUID; z_zichron UUID; z_yoqneam UUID; z_katzir UUID;
  t_aliran UUID; t_benny UUID; t_michael UUID;
BEGIN
  SELECT id INTO z_darom    FROM zones WHERE tenant_id=pw_id AND name='דרום'             LIMIT 1;
  SELECT id INTO z_lod      FROM zones WHERE tenant_id=pw_id AND name='לוד-אשדוד'        LIMIT 1;
  SELECT id INTO z_nahariya FROM zones WHERE tenant_id=pw_id AND name='נהריה-חיפה'       LIMIT 1;
  SELECT id INTO z_tlv      FROM zones WHERE tenant_id=pw_id AND name='תל אביב והסביבה'  LIMIT 1;
  SELECT id INTO z_rosh     FROM zones WHERE tenant_id=pw_id AND name='ראש העין והסביבה' LIMIT 1;
  SELECT id INTO z_jeru     FROM zones WHERE tenant_id=pw_id AND name='ירושלים'           LIMIT 1;
  SELECT id INTO z_zichron  FROM zones WHERE tenant_id=pw_id AND name='זכרון-הרצליה'      LIMIT 1;
  SELECT id INTO z_yoqneam  FROM zones WHERE tenant_id=pw_id AND name='יקנעם-נתניה'       LIMIT 1;
  SELECT id INTO z_katzir   FROM zones WHERE tenant_id=pw_id AND name='קריית שמונה-עפולה' LIMIT 1;

  SELECT id INTO t_aliran  FROM technicians WHERE tenant_id=pw_id AND name ILIKE '%אלירן%' LIMIT 1;
  SELECT id INTO t_benny   FROM technicians WHERE tenant_id=pw_id AND name ILIKE '%בני%'   LIMIT 1;
  SELECT id INTO t_michael FROM technicians WHERE tenant_id=pw_id AND name ILIKE '%מיכאל%' LIMIT 1;

  -- Keys: 0=Sun 1=Mon 2=Tue 3=Wed 4=Thu 5=Fri('' = off)
  UPDATE technicians SET rotation = jsonb_build_object(
    '0', z_darom::text, '1', z_lod::text, '2', z_nahariya::text,
    '3', z_tlv::text,   '4', z_rosh::text, '5', '') WHERE id = t_aliran;

  UPDATE technicians SET rotation = jsonb_build_object(
    '0', z_tlv::text,   '1', z_jeru::text, '2', z_zichron::text,
    '3', z_lod::text,   '4', z_nahariya::text, '5', '') WHERE id = t_benny;

  UPDATE technicians SET rotation = jsonb_build_object(
    '0', z_yoqneam::text, '1', z_zichron::text, '2', z_katzir::text,
    '3', z_darom::text,   '4', z_jeru::text, '5', '') WHERE id = t_michael;

  RAISE NOTICE 'Rotations re-linked: אלירן=%, בני=%, מיכאל=%', t_aliran, t_benny, t_michael;
END $$;

-- Verify:
SELECT name, rotation FROM technicians
WHERE tenant_id='00000000-0000-0000-0000-000000000001';
