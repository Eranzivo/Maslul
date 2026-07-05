---
description: Audit JS↔Python dual-engine parity — run on every engine diff and monthly
---
Maslul has one brain implemented twice (live JS in `index.html`, batch Python in `backend/`). A knob or helper that behaves differently by door mis-schedules real calls. Audit:

**1. Run the golden fixtures (drift = failing test):**
- `node tests/zones.test.js` — includes the `geo-cases.json` suite (JS `cityMatchKey`)
- `backend`: `python -m pytest tests/test_geo_fixture.py tests/test_batch_correctness.py -q` (Py `_match_key` on the SAME fixture + rule-enforcement mirrors)

**2. Walk the parity pairs** — for each, read BOTH implementations and confirm identical semantics (cite line numbers in your report):
| JS (index.html) | Python (backend/) |
|---|---|
| `cityMatchKey` (+`canonicalCity`/`normalizePlaceKeyJS`) | `_match_key` (+`_norm`/`canonicalize.resolve_place_key`) |
| `isTenantWorkDay` | `tenant_works_day` |
| `resolveRouteStrategy` | `resolve_route_strategy` |
| `resolveZone` (city_list branch) | `find_zone` |
| `techHasSkill` / `getCatLimitOk` / `isCityBlocked` / blockedZones | `tech_has_skill` / `cat_limit_ok` / `city_blocked` / `zone_blocked` |
| `getTechPartialBlocks` | `tech_breaks` (+`_clamp_blocks`) |
| duration chain in `calcOptimalTime`/`_postOptimize`/`_candidatesOpen`/`_candidatesRadius` | `_effective_duration` |
| `isTechAvailable` (day_offs full) | `tech_is_working` |
| live placement scoring (`fillScore`+`balanceAdjust`+equal_city) | `_assignment_score` — ⚠ KNOWN divergent semantics (Slice 3, pending Israel) |

**3. Check `context/knobs.md`:** every knob row still names a real reader on both sides (grep the function names). Flag any row whose reader moved/renamed, and any NEW config key read in code but missing from the registry.

**4. Report:** confirmed-in-sync list + divergences (with failure scenario each) + registry corrections. Apply fixes only with TDD (add the fixture case FIRST).
