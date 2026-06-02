# Competitor Analysis — Field Service Scheduling
_Last updated: 2026-06-01_

## Overview
All three are US/international, English-first, trade-focused (HVAC, plumbing, electrical). None are built for the Israeli market or Hebrew. All are SaaS with no public pricing.

---

## Housecall Pro (housecallpro.com)
**Scale:** 200K+ users, 100M+ jobs completed
**Target:** US home service trades (HVAC, plumbing, electrical, cleaning, pest, landscaping)

**Dispatch/Scheduling:**
- Drag-and-drop calendar
- Color-coded job status
- Route optimization with GPS tracking
- Auto reminders + "On my way" texts to customers
- GPS-powered ETA notifications
- Multi-tech assignment per job

**What they don't show:** Constraint-based rules (skills, zones, blocked cities, category limits). No geographic zone logic. Manual drag-and-drop is their core UX — the *coordinator decides*, the system just visualizes.

**Key gap vs Maslul:** No decision engine. Human does the dispatching, system just shows the calendar.

---

## Jobber (getjobber.com)
**Scale:** 400,000+ home service pros
**Target:** Residential/commercial service (plumbing, HVAC, cleaning)

**Dispatch/Scheduling:**
- "Find a Time" — suggests calendar openings based on availability + drive time
- Route optimization (daily/weekly)
- Conflict/gap/overlap detection
- Live fleet GPS tracking
- Drag-and-drop

**What they don't show:** No zone-based routing, no technician constraint rules (beyond availability). "Find a Time" is the closest thing to automated decision-making but it's basically "what slots are open" not "who should get this job and why."

**Key gap vs Maslul:** Availability-aware but not rule-aware. Cannot enforce: zone rotation, category limits, far-to-near routing, min_daily enforcement.

---

## Workiz (workiz.com)
**Target:** US field service trades (HVAC, garage door, locksmith, appliance repair)

**Dispatch/Scheduling:**
- "Genius Scheduling" — AI suggests optimal time slots based on availability
- Skill-based assignment (mentioned)
- Proximity-based recommendations
- Nearest-tech for emergency jobs
- Recurring jobs ✓
- Online booking ✓

**Additional:** CRM, invoicing, payments, QuickBooks, inventory, equipment tracking, Google Calendar integration.

**Key gap vs Maslul:** "Genius Scheduling" is availability + proximity. No explicit zone rotation system, no far-to-near geographic ordering, no category-limit enforcement per technician per day. Also English-only, US-centric.

---

## What All Three Share (and Maslul Doesn't Have Yet)
| Feature | HCP | Jobber | Workiz | Maslul |
|---|---|---|---|---|
| Drag-and-drop calendar | ✓ | ✓ | ✓ | — |
| Customer ETA / "On my way" | ✓ | ✓ | ✓ | WhatsApp text only |
| Mobile tech app (native) | ✓ | ✓ | ✓ | Browser tech view |
| Recurring jobs | ✓ | ✓ | ✓ | Spec ready |
| Online self-booking | ✓ | ✓ | ✓ | — |
| Payments | ✓ | ✓ | ✓ | — |
| CRM | ✓ | ✓ | ✓ | Basic (clients table) |
| Invoicing | — | ✓ | ✓ | — |

## What Maslul Has That None of Them Do
| Feature | Why it matters |
|---|---|
| Zone-strict rotation scheduling | Tech only covers assigned zone per weekday — enforced, not manual |
| Far-to-near geographic ordering | Algorithm enforces route direction, rejects backtrack slots |
| Category limits per tech per day | Hard cap on job types per tech per day |
| Fill-existing-days-first logic | Avoids opening new days when existing days can be filled |
| Hebrew-first + Israeli city logic | Built-in city→coordinates for ~200 Israeli cities |
| WhatsApp-native send | Coordinator sends WhatsApp in 1 click — not just SMS/email |
| Multi-tenant from day 1 | Clean tenant separation, RLS-enforced |

## Strategic Conclusion
The US competitors win on **UX, CRM depth, and integrations**. Maslul wins on **decision quality** — the engine knows *who should get this job and why*, not just *who is available*. That's the defensible moat. The UI/UX gap is real and needs closing, but the engine is the product.

---

## Also see
- [timing-tech-analysis_2026-06-01.md](timing-tech-analysis_2026-06-01.md) — Israeli direct competitor
