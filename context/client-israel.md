# Client Context — PureWater Israel (Pilot Client)

## Business Details
- **tenant_id:** `00000000-0000-0000-0000-000000000001`
- **Business type:** Garbage disposal units + hot/cold water tap installation
- **Active technicians:** 4
- **Current workflow:** Odoo v19 mobile app (mark completed, upload photo, attach warranty certificate)
- **Maslul's role:** Scheduling only — not replacing Odoo

## Odoo
- Client uses Odoo v19 for job execution (tech marks completed, uploads photo, attaches warranty)
- Maslul generates `MSL-XXXXX` assignment IDs — coordinator copies to Odoo manually
- **Odoo integration is Israel's decision to make, not Maslul's scope** — we schedule, they execute
- No API integration planned from our side; if Israel wants it later, it's an add-on

## Service Categories
| Hebrew | Type | Duration |
|---|---|---|
| טוחן אשפה | Garbage disposal unit | 30 min |
| מערכת מים | Water system (hot/cold tap) | 30 min |
| מרכך אבנית | Water softener | 30 min |
| קריאת שירות | Service call | 30 min |
| Package (bundled) | — | 45 min |

## Technician Details
- 4 technicians, each with their own zone rotation
- Each tech has a base city that determines far-to-near ordering within their zone
- Skills and category limits are set per technician

## What Maslul Handles for This Client
- Dispatch: coordinator enters city + category → system assigns tech + time
- Zone enforcement: each tech only covers their assigned zone per day of week
- Route optimization: far-to-near ordering within zone
- Day-off management: full-day and partial-day blocks
- Task lifecycle: ממתין → שובץ → בדרך → הגיע → הושלם / תקלה
- Cancel + smart replacement: system suggests pending calls from same zone to fill freed slot
- WhatsApp message to client after dispatch (click-to-send, zero cost)
- Export/import settings as JSON (backup)

## Current Status (May 2026)
- Pilot stage — not yet paying
- Coordinator using the app for real dispatching
- Techs logging in via individual accounts to see their daily schedule
- Odoo handoff: manual MSL-XXXXX copy

## Notes
- Client uses Hebrew exclusively
- Interface must be RTL and mobile-friendly (techs are in the field on phones)
- WhatsApp is the primary communication channel with end-customers
