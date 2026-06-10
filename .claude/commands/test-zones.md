---
description: Run the zone-logic test suite and suggest coverage improvements
---
Run `node tests/zones.test.js` and report the pass/fail result.

Then review `tests/zones.test.js` against section 10 ("Testing") of `outputs/zones-polygons-design_2026-06-09.md` and the live logic inside the `// <zone-logic>` markers in `index.html`. List any coverage gaps as concrete, prioritized suggestions — for example:
- untested `resolveZone` reasons (`city_not_in_zone`, `outside_all_polygons`, `not_geocoded`)
- missing tenant-separation cases (two tenants with different `zone_match` resolving independently)
- `canonicalCity` edge cases (variant spellings, near-duplicate threshold, unknown city)
- any pure logic added inside the markers since the last test was written

Do NOT change any code unless I explicitly ask. Output: the test result, then a short prioritized list of suggested new test cases.
