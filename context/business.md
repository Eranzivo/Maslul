# Business Context — Maslul

## About the Product
**Name:** Maslul (מסלול)
**What it does:** A smart scheduling engine for small Israeli businesses with field workers. Replaces manual management via WhatsApp and Google Sheets. The coordinator enters a city and category — the system calculates who the technician is, when, and why.
**Target audience:** Small Israeli businesses with 2–20 field workers — installers, technicians, delivery drivers, cleaners.
**First client:** Israel (PureWater) — garbage disposal + hot/cold water tap installer. 4 technicians. Uses Odoo v19.
**Main marketing channel:** Facebook groups for small Israeli businesses, direct outreach.

## Tone
Hebrew-first. Simple, direct, professional. Minimal and clean interface. No unnecessary complexity.

## Quarterly Goal
Turn the prototype into a first paying client. Build real multi-tenant infrastructure with Supabase so multiple businesses can use the same product independently.

## Business Model
- SaaS subscription per tenant
- Each new client gets their own tenant_id, Supabase user, and config
- Scalable: adding a client = 1 SQL insert into tenants + 1 Supabase Auth user + 1 insert into users
- Feature flags per tenant (CRM, Reports, WhatsApp, Google Maps, Odoo integration)

## Scalability Principle
The product is built for Israel first but must remain configurable for any business type:
- All labels are tenant-configurable (טכנאי / שליח / מנקה)
- All scheduling rules are param-driven, not hardcoded
- New client = new config, same codebase, no code changes
