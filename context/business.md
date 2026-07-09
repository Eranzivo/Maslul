# Business Context — Maslul

## About the Product
**Name:** Maslul (מסלול)
**What it does:** A smart scheduling engine for small Israeli businesses with field workers. Replaces manual management via WhatsApp and Google Sheets. The coordinator enters a city and category — the system calculates who the technician is, when, and why.
**Target audience:** Small Israeli businesses with 2–20 field workers — installers, technicians, delivery drivers, cleaners.
**First client:** Israel (PureWater) — garbage disposal + hot/cold water tap installer. 3 technicians (אלירן, בני, מיכאל). Uses Odoo v19.
**Main marketing channel:** Facebook groups for small Israeli businesses, direct outreach.

## Tone
Hebrew-first. Simple, direct, professional. Minimal and clean interface. No unnecessary complexity.

## Quarterly Goal
Turn the prototype into a first paying client. Build real multi-tenant infrastructure with Supabase so multiple businesses can use the same product independently.

## Business Model
- SaaS subscription per tenant (target: ₪150–300/month per business)
- Each new client gets their own tenant_id, Supabase user, and config
- Scalable: adding a client = 1 SQL insert into tenants + 1 Supabase Auth user + 1 insert into users
- Feature flags per tenant (CRM, Reports, WhatsApp, Google Maps, Odoo integration)

## Scalability Principle
The product is built for Israel first but must remain configurable for any business type:
- All labels are tenant-configurable (טכנאי / שליח / מנקה)
- All scheduling rules are param-driven, not hardcoded
- New client = new config, same codebase, no code changes

## Competitive Position (vs Timing.tech)
Timing.tech (timing.tech) is the end-goal vision for this product — AI-powered field service management with customer portal, native apps, digital signatures, payment processing. Maslul wins by:
1. **Price** — targeting 2–20 worker Israeli SMBs at ₪150–300/mo vs enterprise pricing
2. **Hebrew-first** — genuine RTL, Hebrew UI, Israeli city/zone logic built-in
3. **WhatsApp-native** — Israeli SMBs live in WhatsApp; competitors treat it as an add-on
4. **Simplicity** — new client live in minutes, not a 3-day setup
5. **Local ERP bridge** — Odoo, Priority, QuickBooks Israel integrations as optional modules

## Product Roadmap Summary
- **Now:** Stabilize pilot (Israel), get first paying client, find Client #2
- **Short-term:** CRM, SMS auto-send, recurring jobs, GPS tracking
- **Long-term:** Customer self-booking portal, native mobile app, AI zone optimizer, in-app billing

## Multi-Client Strategy
Each client gets a `context/client-[name].md` file with their business config.
No git branches — same codebase serves all clients via tenant config + labels.
When adding Client #2, provide: business type, team size, terminology, zones, categories, any special rules.

---
> 🧠 [[maslul-brain.canvas|Brain map]] · Related: [[purewater]] · [[design-system]] · [[scheduling-rules]]
