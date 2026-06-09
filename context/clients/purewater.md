# Client Context — PureWater Israel (Pilot)

> Human-readable mirror of PureWater's `tenants.config`. DB is the source of truth; keep this in lockstep. See `context/clients/README.md`.

## Identity
| Field | Value |
|---|---|
| tenant_id | `00000000-0000-0000-0000-000000000001` |
| Business type | Garbage disposal units + hot/cold water tap installation |
| Workers | 3 technicians (טכנאי) — אלירן, בני, מיכאל |
| Stage | Pilot (not yet paying, as of Jun 2026) |
| Depot | אלי סיני 7, אשקלון — `31.697962, 34.579152` (in `tenants.config.depot`) |
| Onboarding SQL | `outputs/migration-purewater-zone-cities_2026-06-06.sql` (+ zones-rotation) |

## Runtime config (mirrors `tenants.config`)
| Key | Value | Notes |
|---|---|---|
| `scheduling.mode` | `zone` | zone-strict assignment |
| `scheduling.zone_match` | `city_list` | matches by city list (not polygon) |
| `scheduling.route_strategy` | `far_to_near` | **PureWater/Israel-specific** — not a global default |
| `scheduling.fill_first` | `true` | fill active zone-days before opening new ones |
| `scheduling.slot_release` | enabled (72/48/24h) | hold early slots for farther cities |
| `defaults.arrival_window_hours` | 3 | customers get a 3-hour service window |
| `defaults.max_daily_jobs` | 9 | per tech per day |
| `defaults.work_start` / `work_end` | 07:00 / 18:00 | per-tech `weekly_schedule` can override |
| Features | whatsapp, google_maps (distance matrix), geocoding (enabled 2026-06-07) | `tenants.config.features` |

## Zones & rotation
9 city-list zones covering Israel; all 3 techs start from the Ashkelon depot (`base_city = אשקלון`). Day-of-week rotation (0=Sun … 4=Thu; Saturday off):

| Day | אלירן | בני | מיכאל |
|---|---|---|---|
| Sun | שפלה | שרון | ירושלים |
| Mon | ירושלים | שפלה | שרון |
| Tue | שרון | ירושלים | שפלה |
| Wed | נגב | מרכז | דן |
| Thu | דן | נגב | מרכז |

Setup SQL: `outputs/migration-purewater-zones-rotation_2026-06-05.sql`.

## Restrictions & preferences
- **Far-to-near routing** is PureWater's chosen logic (route_strategy). True route order should come from the OR-Tools TSP with real drive times — far-to-near is the heuristic, not the goal.
- **Slot release (72/48/24h):** near cities can't hold the earliest slots far in advance, reserving them for farther jobs that may still come in.
- No per-tech blocked zones/cities configured yet.

## Service categories
| Hebrew | Type | Duration |
|---|---|---|
| טוחן אשפה | Garbage disposal unit | 30 min |
| מערכת מים | Water system (hot/cold tap) | 30 min |
| מרכך אבנית | Water softener | 30 min |
| קריאת שירות | Service call | 30 min |
| Package (bundled) | — | 45 min |

## Integrations
- **Odoo v19** — Maslul generates `MSL-XXXXX` IDs; coordinator copies them into Odoo manually. No API integration planned (optional add-on later).
- Maslul's role is **scheduling only** — it does not replace Odoo.

## Notes
- Hebrew exclusively; RTL, mobile-first.
- WhatsApp is the primary customer communication channel.
- 108 real tasks seeded Jun 2026 (status=pending, city-only; client details filled via ✏️).

## Change log
| Date | Change |
|---|---|
| 2026-06-09 | Standardized to client template; recorded `zone_match = city_list`; flagged far-to-near as PureWater-specific |
| 2026-06-08 | 108 tasks batch-scheduled; service windows live |
| 2026-06-06 | 9 zones + 3-tech rotation + city normalization |
