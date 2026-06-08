-- PureWater: Populate zone cities arrays + set technician base city
-- All 3 technicians depart from Ashkelon (אשקלון). Cities ordered far → near from Ashkelon.
-- Run in Supabase SQL Editor. Safe to re-run: replaces existing arrays.

DO $$
DECLARE
  pw_id UUID := '00000000-0000-0000-0000-000000000001';
  ma_id UUID := '642ad6e6-a093-46a4-8489-ce49a966d77c';
BEGIN

  -- 1. Set base_city = Ashkelon for all PureWater technicians (only if not already set)
  UPDATE technicians SET base_city = 'אשקלון'
  WHERE tenant_id = pw_id AND (base_city IS NULL OR base_city = '');
  RAISE NOTICE 'Set base_city=אשקלון for PureWater technicians';

  -- 2. Zone cities arrays (far → near from Ashkelon)
  --    Index 0 = farthest city. getCityIndexInZone() uses this for far-to-near route ordering.

  UPDATE zones SET cities = ARRAY[
    'ירוחם','דימונה','ערד','באר שבע','אופקים','שדרות','נתיבות',
    'קרית גת','קרית מלאכי','בני דקלים','כפר אחים','אשקלון'
  ] WHERE tenant_id=pw_id AND name='דרום';

  UPDATE zones SET cities = ARRAY[
    'שוהם','מודיעין','כפר בן נון','לוד','רמלה',
    'ראשון לציון','רחובות','נס ציונה','יבנה','גדרה','אשדוד'
  ] WHERE tenant_id=pw_id AND name='לוד-אשדוד';

  UPDATE zones SET cities = ARRAY[
    'נהריה','כרמיאל','עכו','קרית ים','קרית מוצקין','קרית ביאליק','קרית חיים','חיפה'
  ] WHERE tenant_id=pw_id AND name='נהריה-חיפה';

  UPDATE zones SET cities = ARRAY[
    'הוד השרון','רעננה','כפר סבא','פתח תקווה','בני ברק',
    'רמת גן','גבעת שמואל','גבעתיים','תל אביב','חולון','בת ים'
  ] WHERE tenant_id=pw_id AND name='תל אביב והסביבה';

  UPDATE zones SET cities = ARRAY[
    'ראש העין','אלעד','יהוד','אור יהודה'
  ] WHERE tenant_id=pw_id AND name='ראש העין והסביבה';

  UPDATE zones SET cities = ARRAY[
    'טלמון','מעלה אדומים','ירושלים','ביתר עילית','בית שמש'
  ] WHERE tenant_id=pw_id AND name='ירושלים';

  UPDATE zones SET cities = ARRAY[
    'זכרון יעקב','בנימינה','פרדס חנה','חדרה','סלעית','קיסריה','הרצליה'
  ] WHERE tenant_id=pw_id AND name='זכרון-הרצליה';
  -- סלעית: moshav east of Herzliya-Netanya corridor (~75km from Ashkelon)

  UPDATE zones SET cities = ARRAY[
    'חרב','יקנעם','בארותיים','כפר נטר','נתניה'
  ] WHERE tenant_id=pw_id AND name='יקנעם-נתניה';

  UPDATE zones SET cities = ARRAY[
    'קריית שמונה','צפת','טבריה','נצרת','שמשית','עפולה',
    'מגדל העמק','בלפוריה','מרחביה'
  ] WHERE tenant_id=pw_id AND name='קריית שמונה-עפולה';

  -- 3. Mirror all zone cities to Maslul Admin tenant (for QA / Eran testing)
  UPDATE zones ma SET cities = pw.cities
  FROM zones pw
  WHERE ma.tenant_id=ma_id AND pw.tenant_id=pw_id AND ma.name=pw.name;

  RAISE NOTICE '✅ Done. 9 zones populated for PureWater + mirrored to Maslul Admin.';
END $$;

-- Verify (run separately after the DO block):
SELECT name, array_length(cities,1) AS city_count, cities
FROM zones WHERE tenant_id='00000000-0000-0000-0000-000000000001'
ORDER BY name;
