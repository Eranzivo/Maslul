# Maslul — Security Hardening Plan (post-design-phase slice)

> Eran (2026-07-12): "I want to be sure we are safe and secure, and hackers cannot shut down or
> find any API keys in the browser… no rookie mistakes once the product works at scale."
> Scheduled to start when the design phase closes. This doc = the checklist we execute.

## The one thing to understand about our architecture
The browser talks to Supabase directly with the **anon (publishable) key — that key being visible
is BY DESIGN and is not a leak.** The entire security boundary is **RLS**: every table's policies
decide what a logged-in user may read/write. A hacker with our anon key and no valid user session
gets nothing; a logged-in user gets only their tenant's rows. The rookie mistake class to guard
against is *one table without RLS / one over-permissive policy* — which is why the standing rule
"run Supabase security advisors after every schema/policy change" already exists and stays.

## Already in place (verified, keep enforcing)
| Control | Where |
|---|---|
| RLS on all tables, single role-scoped policies (consolidated 2026-07) | Supabase; advisors run after changes |
| Server-side JWT introspection; client `tenant_id` NEVER trusted alone | `backend/main.py` `_introspect_user_token` → `resolve_effective_tenant` |
| Service key only in Railway env (never browser/git) | Railway vars; `.env` gitignored |
| Google Maps: hard daily caps 700/680 + $210 budget alert | Google Cloud console + backend counters |
| No raw backend errors to users (generic Hebrew; console+Sentry for Eran) | error-messages rule |
| Manual-override audit trail (`override_reason`, `_audit_tasks` trigger) | DB triggers |
| SECURITY DEFINER functions with pinned `search_path` | security-definer rules (memory) |

## Phase 1 — before/with next pilot client (≈ half a day)
1. **Supabase Auth hardening**: enable leaked-password protection; enforce MFA on Eran/admin
   accounts; review session expiry.
2. **Supabase Pro** (already planned at go-live): daily backups + PITR, no project pausing.
3. **Google Maps key restriction**: HTTP-referrer lock to our domains (Pages + future
   maslul.co.il); server key IP-locked to Railway.
4. **FastAPI**: CORS allowlist (Pages + custom domain only, not `*`); rate limiting
   (slowapi: e.g. 30/min per IP on `/optimize`, `/batch`, `/geocode`); request size limits.
5. **Secret hygiene sweep**: trufflehog/gitleaks over full git history (frontend + backend);
   rotate anything ever committed; confirm `.env` never tracked.
6. **Dependency audit**: `pip-audit` (backend) + review of the few frontend CDN pins
   (SRI hashes on script tags).
7. **RLS pen-check**: scripted `set local role authenticated` probes per table — stranger
   tenant reads must return 0 rows (we already do this ad-hoc; make it a repeatable script
   in `tests/`).

## Phase 2 — with custom domain + Cloudflare (already planned trigger: client #2)
- Cloudflare in front of Pages + Railway: **DDoS protection (the "shut down" concern), WAF,
  bot fight, TLS everywhere, HSTS + security headers (CSP, X-Frame-Options)**.
- Uptime monitoring + alerting (UptimeRobot free tier → Eran's phone).
- Sentry alert rules (error spike = notification, not silence).

## Phase 3 — scale (a few pilot clients live)
- OWASP Top-10 self-audit walkthrough; document in outputs/.
- Key-rotation schedule (service key, Maps keys — twice a year or on staff change).
- Incident runbook: who does what if a tenant reports wrong data / suspected breach
  (Supabase key revoke → Railway redeploy → advisor sweep → audit-log review).
- Privacy compliance (Israel): תקנות הגנת הפרטיות (אבטחת מידע) 2017 — classify our DB
  (customer names/phones/addresses = מאגר בסיסי most likely), data-retention policy,
  tenant data export/delete on request. Lightweight at our size but written down.
- Per-tenant data isolation test in CI (golden query set run as each role).

## Explicit non-issues (so we don't chase ghosts)
- Anon key visible in page source — by design (see top).
- GitHub Pages "shutdown" — static files on GitHub's CDN; the realistic availability risks are
  Supabase/Railway outages, mitigated by Pro tier + monitoring, not by hiding the frontend.
- Technician web-app (PWA) uses the same auth + RLS as coordinators — no new attack surface,
  just a new role with narrower policies (already modeled in auth-users.md).
