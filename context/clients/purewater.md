# Client Context — PureWater Israel (Pilot Client)

## Business Details
- **tenant_id:** `00000000-0000-0000-0000-000000000001`
- **Business type:** Garbage disposal units + hot/cold water tap installation
- **Active technicians:** 3 (אלירן, בני, מיכאל)
- **Depot address:** אלי סיני 7, אשקלון — coords 31.697962, 34.579152 (stored in `tenants.config.depot`)
- **Current workflow:** Odoo v19 mobile app (mark completed, upload photo, attach warranty)
- **Maslul's role:** Scheduling only — not replacing Odoo

## Scheduling Config (in `tenants.config.scheduling`)
```json
{
  "mode": "zone",
  "zone_strict": true,
  "fill_first": true,
  "route_strategy": "far_to_near",
  "slot_release": { "enabled": true, "conservative_hours": 72, "moderate_hours": 48, "aggressive_hours": 24 }
}
```
- 9 zones, each tech has a day-of-week rotation (Sun–Fri)
- All 3 techs start from Ashkelon depot; `base_city = אשקלון`
- `arrival_window_hours = 3` — customers get 3-hour service windows, not exact times

## Service Categories
| Hebrew | Type | Duration |
|---|---|---|
| טוחן אשפה | Garbage disposal unit | 30 min |
| מערכת מים | Water system (hot/cold tap) | 30 min |
| מרכך אבנית | Water softener | 30 min |
| קריאת שירות | Service call | 30 min |
| Package (bundled) | — | 45 min |

## Odoo Integration
- Maslul generates `MSL-XXXXX` IDs; coordinator copies to Odoo manually
- No API integration planned; if Israel wants it later it's an add-on

## Notes
- Client uses Hebrew exclusively; RTL and mobile-first
- WhatsApp is primary customer communication channel
- Pilot stage — not yet paying (as of Jun 2026)
- 108 real tasks seeded Jun 2026 (status=pending, city-only, client details to be filled via ✏️)
