# Timing.tech Competitive Analysis
_Last updated: 2026-06-01_

## What They Are
Israeli field service management platform. Founded 2015, developed with Tel Aviv University. 1,000+ service providers, 10,000+ daily visits. B2B SaaS, sales-led (no public pricing).

## Three Core Components
1. **Back office** — dynamic scheduling, smart dispatch, route optimization, real-time monitoring, shift management, analytics
2. **Technician mobile app** — full toolkit: call info, task management, AI assistant, AI call summaries, digital signature, barcode scanner, photo upload, payment processing, map navigation
3. **Customer portal** — ETA tracking via SMS/WhatsApp link, service rating, direct tech messaging, click-to-call support

## AI Claims
- AI-based dynamic polygons (territory auto-sizing by season/day/density)
- Smart time-window calculator (location + workload + traffic)
- 24/7 self-service booking
- Demand forecasting
- AI call summaries (voice reporting)

## Named Customers
Tornado, Newpan, OKD, Tapuz, Brimag — all appear to be Israeli mid-large companies.

## Pricing (from direct conversation with them, June 2026)
- No public pricing — demo-required
- Lowest tier for a ~4-tech business **without** technician app: **₪1,500/month (~$400)**
- Full package (with tech app): presumably higher

## Integrations / Partners
IBM Alpha Zone, Microsoft 365, TAU, E.ON, The Hive, Matrix, Bina

## Weaknesses / Gaps (inferred)
- Complex onboarding — emphasizes "professional consultancy" and "close accompaniment" → not self-serve
- Enterprise-leaning pricing → blocks true SMBs (1–5 techs)
- Sales-led → slow to try → high friction for small business owner
- "UI is a bit old" (one Capterra review noted this)
- Only 100+ Play Store downloads → suggests limited tech self-serve adoption
- No WhatsApp-native send (just a link to customer portal)

## How Maslul Compares

| Dimension | timing.tech | Maslul |
|---|---|---|
| Price (4-tech, no tech app) | ₪1,500/mo | Target: ₪750/mo |
| Setup | Consultancy-led, days | Self-serve, minutes |
| Hebrew-first | Translated UI | Built Hebrew-first, RTL |
| WhatsApp | Customer portal link | Click-to-send from coordinator |
| Technician app | Yes (full featured) | Tech view in browser (lightweight) |
| Customer self-booking | Yes | Not yet |
| Recurring jobs | Likely yes | Spec ready, not built yet |
| Target market | SMB to enterprise | True SMB (1–20 techs) |
| Israeli city/zone logic | Basic | Deep (cities.py, rotation, far-to-near) |
| Odoo/ERP | Unknown | Odoo handoff (manual, manual is ok for now) |

## Strategic Summary
Timing.tech is the "full enterprise" option at 2× Maslul's target price, with complex onboarding and a full tech app. Maslul wins by being **cheaper, simpler, and faster to try** for the 1–10 tech Israeli SMB who lives in WhatsApp. The gap to close: customer portal / ETA link (their strongest differentiator vs us) and eventually client self-booking.
