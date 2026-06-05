-- PureWater: Zone setup + technician rotation + copy to Maslul Admin
-- Run in Supabase SQL editor (Dashboard → SQL Editor → New query)
-- Safe to re-run: all inserts are guarded by WHERE NOT EXISTS

DO $$
DECLARE
  pw_id  UUID := '00000000-0000-0000-0000-000000000001'; -- PureWater tenant
  ma_id  UUID := '642ad6e6-a093-46a4-8489-ce49a966d77c'; -- Maslul Admin tenant

  -- Zone IDs (resolved after insert)
  z_darom         UUID;
  z_lod           UUID;
  z_nahariya      UUID;
  z_tlv           UUID;
  z_rosh_ha_ayin  UUID;
  z_jerusalem     UUID;
  z_zichron       UUID;
  z_yoqneam       UUID;
  z_katzir        UUID;

  -- Technician IDs
  t_aliran  UUID;
  t_benny   UUID;
  t_michael UUID;
BEGIN

  -- ── 1. Insert missing zones for PureWater ──────────────────────────────
  -- Skips zones that already exist by name for this tenant
  INSERT INTO zones (tenant_id, name, cities)
    SELECT pw_id, 'דרום', '{}'::text[]
    WHERE NOT EXISTS (SELECT 1 FROM zones WHERE tenant_id=pw_id AND name='דרום');

  INSERT INTO zones (tenant_id, name, cities)
    SELECT pw_id, 'לוד-אשדוד', '{}'::text[]
    WHERE NOT EXISTS (SELECT 1 FROM zones WHERE tenant_id=pw_id AND name='לוד-אשדוד');

  INSERT INTO zones (tenant_id, name, cities)
    SELECT pw_id, 'נהריה-חיפה', '{}'::text[]
    WHERE NOT EXISTS (SELECT 1 FROM zones WHERE tenant_id=pw_id AND name='נהריה-חיפה');

  INSERT INTO zones (tenant_id, name, cities)
    SELECT pw_id, 'תל אביב והסביבה', '{}'::text[]
    WHERE NOT EXISTS (SELECT 1 FROM zones WHERE tenant_id=pw_id AND name='תל אביב והסביבה');

  INSERT INTO zones (tenant_id, name, cities)
    SELECT pw_id, 'ראש העין והסביבה', '{}'::text[]
    WHERE NOT EXISTS (SELECT 1 FROM zones WHERE tenant_id=pw_id AND name='ראש העין והסביבה');

  INSERT INTO zones (tenant_id, name, cities)
    SELECT pw_id, 'ירושלים', '{}'::text[]
    WHERE NOT EXISTS (SELECT 1 FROM zones WHERE tenant_id=pw_id AND name='ירושלים');

  INSERT INTO zones (tenant_id, name, cities)
    SELECT pw_id, 'זכרון-הרצליה', '{}'::text[]
    WHERE NOT EXISTS (SELECT 1 FROM zones WHERE tenant_id=pw_id AND name='זכרון-הרצליה');

  INSERT INTO zones (tenant_id, name, cities)
    SELECT pw_id, 'יקנעם-נתניה', '{}'::text[]
    WHERE NOT EXISTS (SELECT 1 FROM zones WHERE tenant_id=pw_id AND name='יקנעם-נתניה');

  -- NOTE: "קריית שמונה-עפולה" — keeping Israel's exact name; rename via app if needed
  INSERT INTO zones (tenant_id, name, cities)
    SELECT pw_id, 'קריית שמונה-עפולה', '{}'::text[]
    WHERE NOT EXISTS (SELECT 1 FROM zones WHERE tenant_id=pw_id AND name='קריית שמונה-עפולה');

  -- ── 2. Resolve zone IDs ────────────────────────────────────────────────
  SELECT id INTO z_darom        FROM zones WHERE tenant_id=pw_id AND name='דרום'              LIMIT 1;
  SELECT id INTO z_lod          FROM zones WHERE tenant_id=pw_id AND name='לוד-אשדוד'         LIMIT 1;
  SELECT id INTO z_nahariya     FROM zones WHERE tenant_id=pw_id AND name='נהריה-חיפה'        LIMIT 1;
  SELECT id INTO z_tlv          FROM zones WHERE tenant_id=pw_id AND name='תל אביב והסביבה'   LIMIT 1;
  SELECT id INTO z_rosh_ha_ayin FROM zones WHERE tenant_id=pw_id AND name='ראש העין והסביבה'  LIMIT 1;
  SELECT id INTO z_jerusalem    FROM zones WHERE tenant_id=pw_id AND name='ירושלים'            LIMIT 1;
  SELECT id INTO z_zichron      FROM zones WHERE tenant_id=pw_id AND name='זכרון-הרצליה'       LIMIT 1;
  SELECT id INTO z_yoqneam      FROM zones WHERE tenant_id=pw_id AND name='יקנעם-נתניה'        LIMIT 1;
  SELECT id INTO z_katzir       FROM zones WHERE tenant_id=pw_id AND name='קריית שמונה-עפולה'           LIMIT 1;

  -- ── 3. Resolve technician IDs (match by first name) ───────────────────
  SELECT id INTO t_aliran  FROM technicians WHERE tenant_id=pw_id AND name ILIKE '%אלירן%'  LIMIT 1;
  SELECT id INTO t_benny   FROM technicians WHERE tenant_id=pw_id AND name ILIKE '%בני%'    LIMIT 1;
  SELECT id INTO t_michael FROM technicians WHERE tenant_id=pw_id AND name ILIKE '%מיכאל%'  LIMIT 1;

  RAISE NOTICE 'Resolved: אלירן=%, בני=%, מיכאל=%', t_aliran, t_benny, t_michael;
  RAISE NOTICE 'Zones: דרום=%, לוד=%, נהריה=%, תל אביב=%, ראש העין=%, ירושלים=%, זכרון=%, יקנעם=%, קש=%',
    z_darom, z_lod, z_nahariya, z_tlv, z_rosh_ha_ayin, z_jerusalem, z_zichron, z_yoqneam, z_katzir;

  -- ── 4. Set rotations ───────────────────────────────────────────────────
  -- Keys: 0=Sun, 1=Mon, 2=Tue, 3=Wed, 4=Thu, 5=Fri
  -- Empty string '' = no zone / day off

  -- אלירן: Sun=דרום, Mon=לוד-אשדוד, Tue=נהריה-חיפה, Wed=תל אביב והסביבה, Thu=ראש העין והסביבה
  IF t_aliran IS NOT NULL THEN
    UPDATE technicians SET rotation = jsonb_build_object(
      '0', z_darom::text,
      '1', z_lod::text,
      '2', z_nahariya::text,
      '3', z_tlv::text,
      '4', z_rosh_ha_ayin::text,
      '5', ''
    ) WHERE id = t_aliran;
    RAISE NOTICE 'Updated rotation for אלירן';
  ELSE
    RAISE WARNING 'אלירן not found in PureWater technicians!';
  END IF;

  -- בני: Sun=תל אביב, Mon=ירושלים, Tue=זכרון-הרצליה, Wed=לוד-אשדוד, Thu=נהריה-חיפה
  IF t_benny IS NOT NULL THEN
    UPDATE technicians SET rotation = jsonb_build_object(
      '0', z_tlv::text,
      '1', z_jerusalem::text,
      '2', z_zichron::text,
      '3', z_lod::text,
      '4', z_nahariya::text,
      '5', ''
    ) WHERE id = t_benny;
    RAISE NOTICE 'Updated rotation for בני';
  ELSE
    RAISE WARNING 'בני not found in PureWater technicians!';
  END IF;

  -- מיכאל: Sun=יקנעם-נתניה, Mon=זכרון-הרצליה, Tue=קריית שמונה-עפולה, Wed=דרום, Thu=ירושלים
  IF t_michael IS NOT NULL THEN
    UPDATE technicians SET rotation = jsonb_build_object(
      '0', z_yoqneam::text,
      '1', z_zichron::text,
      '2', z_katzir::text,
      '3', z_darom::text,
      '4', z_jerusalem::text,
      '5', ''
    ) WHERE id = t_michael;
    RAISE NOTICE 'Updated rotation for מיכאל';
  ELSE
    RAISE WARNING 'מיכאל not found in PureWater technicians!';
  END IF;

  -- ── 5. Copy all PureWater zones → Maslul Admin ────────────────────────
  -- Skips zones that already exist by name in Maslul Admin
  INSERT INTO zones (tenant_id, name, cities)
  SELECT ma_id, pw.name, pw.cities
  FROM zones pw
  WHERE pw.tenant_id = pw_id
    AND NOT EXISTS (
      SELECT 1 FROM zones ma
      WHERE ma.tenant_id = ma_id AND ma.name = pw.name
    );
  RAISE NOTICE 'Copied PureWater zones to Maslul Admin (skipped existing)';

  -- ── 6. Copy all PureWater categories → Maslul Admin ──────────────────
  -- Skips categories that already exist by name in Maslul Admin
  INSERT INTO categories (tenant_id, name, duration_minutes)
  SELECT ma_id, c.name, c.duration_minutes
  FROM categories c
  WHERE c.tenant_id = pw_id
    AND NOT EXISTS (
      SELECT 1 FROM categories ma
      WHERE ma.tenant_id = ma_id AND ma.name = c.name
    );
  RAISE NOTICE 'Copied PureWater categories to Maslul Admin (skipped existing)';

  RAISE NOTICE '✅ Done. Run SELECT id, name FROM zones WHERE tenant_id=''%'' to verify.', pw_id;
END $$;
