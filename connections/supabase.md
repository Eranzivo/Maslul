# Connection: Supabase

## What it is
PostgreSQL database + Auth + Row Level Security. Source of truth for all tenant data.

## When to use
- Any read/write to tenant data (technicians, tasks, zones, categories, day_offs)
- Auth (login, password reset, user creation)
- Checking schema or RLS policies

## Key details
- Dashboard: https://supabase.com (infomaslul@gmail.com)
- Credentials hardcoded in `index.html` (acceptable at current scale — revisit before adding devs)
- All tables have `tenant_id` with RLS enforced via `get_tenant_id()` SQL function

## Critical rule
`if (!currentTenantId) return` — this guard appears before every Supabase write.
If `currentTenantId` is null (demo mode or unauthenticated), all writes are blocked silently.

## Tables
tenants, users, technicians, tasks, zones, categories, packages, day_offs, clients
See `schema.sql` for full DDL and RLS policies.

## Secrets
SUPABASE_URL and SUPABASE_ANON_KEY — stored in `.env` (root), referenced in `index.html`
