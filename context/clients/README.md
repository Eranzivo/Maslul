# Clients — Per-Tenant Context Layer

This folder holds a one-page, human-readable profile per client. It exists so you (and Claude) can see at a glance how each client is set up — without reading the database or the code.

## The single rule that prevents contradictions

> **`tenants.config` (JSONB in the Supabase DB) is the single source of truth for runtime behavior.**
> The files here are a **human-readable mirror** of that config — updated in lockstep with any change. If a file and the DB ever disagree, **the DB wins** and the file must be corrected.

These files are *never* read by the app. They are documentation.

## What lives where

| Layer | Where | Same for all clients? |
|---|---|---|
| Scheduling engine, UI, safety logic | `index.html`, `backend/` | ✅ shared code |
| Engine concepts & rules | `context/architecture.md`, `context/scheduling-rules.md`, `context/zones-polygons.md`, `context/style.md` | ✅ shared docs |
| **Runtime per-tenant config** (labels, defaults, scheduling mode, features) | **`tenants.config` in the DB** | ❌ per-tenant — source of truth |
| **Per-tenant human profile** (this folder) | `context/clients/[name].md` | ❌ per-tenant — mirror of config |
| Per-tenant onboarding SQL | `outputs/*onboarding*.sql` | ❌ per-tenant |

Anything a client does differently lives in their `tenants.config` and is described in their file here — **never hardcoded in shared code**.

## Adding a client

1. Copy `_template.md` → `context/clients/[name].md`, fill every section.
2. Write the onboarding SQL (tenant row + `tenants.config` + admin user) → `outputs/[name]-onboarding_[date].sql`.
3. Add the client to the table in `CLAUDE.md`.
4. Keep the file in lockstep with `tenants.config` from then on (the doc-sync rule).

## Files

| File | Purpose |
|---|---|
| `_template.md` | Fill-in-the-blanks profile for a new client |
| `purewater.md` | Pilot client (PureWater Israel) |
