# Building an Agent for Maslul

> **Status: living document.** Start here when we build Maslul's first agent. Read
> [`how-to-build-an-agent.md`](how-to-build-an-agent.md) first. And **before building**: brainstorm (use the
> brainstorming skill) + research the best methodology, connections, and integrations for the chosen agent.

## Maslul in one paragraph
Hebrew-first scheduling/dispatch SaaS for Israeli SMBs with field workers. Stack: single `index.html`
(vanilla JS) on GitHub Pages; Supabase (Postgres + Auth + RLS) direct from the browser; FastAPI + OR-Tools
optimizer on Railway. Multi-tenant: business logic lives in `tenants.config`, never hardcoded. North-star:
an **AI dispatch cockpit, not a calendar** - surface the engine's intelligence.

## Why Maslul is a strong fit for an agent
- It already has the hard part others fake: a real optimization engine + per-tenant config + RLS data
  isolation. An agent here is about **surfacing and operating** that intelligence, not inventing it.
- Per-tenant config = onboarding-as-config - exactly the playbook's "per-client config, not hardcoded" law.

## Candidate agents (brainstorm properly before choosing)
1. **Dispatcher Copilot (recommended first):** helps the owner/dispatcher understand and adjust the plan -
   "why is this task here?", "what if I move it?", explains overflow, opens/edits tasks - always respecting
   the tenant's scheduling rules. The optimizer API + Supabase are its tools.
2. **Tenant Onboarding agent:** walks a new business through setup (zones, technicians, rules) - literally
   automating onboarding.
3. **Field-tech / customer notifications agent:** ETAs, confirmations, reschedules over WhatsApp.

## Mapping the playbook to Maslul (Dispatcher Copilot example)
| Playbook element | Maslul instance |
|---|---|
| Knowledge base (RAG) | `context/scheduling-rules.md`, zones, per-tenant config, `PRODUCT_GUIDE.md` |
| Tools (read) | query Supabase (tasks/techs/zones), read route cache, get optimizer explanation |
| Tools (write, confirm) | create/move/lock a task, trigger a re-optimize run |
| Memory | Company = tenant config; Project = today's plan; per-dispatcher preferences |
| RBAC | tenant isolation via existing RLS; roles owner/dispatcher/technician; super_admin |
| Guardrails | never violate the tenant's scheduling rule; never fabricate an ETA; ground in engine output |
| Supervisor / human | cost- or SLA-impacting changes confirmed by the dispatcher |
| Per-client config | already the rule: scheduling logic is tenant config, not a default |
| Evals (adversarial) | try to make it double-book, break break-time, cross zones, ignore far-to-near |
| KPIs | % tasks placed vs overflow, dispatcher time saved, reschedule-acceptance rate |

## Before writing the prompt
- [ ] Brainstorm the chosen agent (skill): purpose, the exact user, success criteria.
- [ ] Research: best practice for scheduling/dispatch copilots; which optimizer outputs to expose; how to
      call the Railway API + Supabase safely from the agent runtime; data-sensitivity boundaries.
- [ ] Copy [`agent-prompt-template.md`](agent-prompt-template.md) and fill it for the chosen agent - with
      **its own tone**, not Dona's.

This doc is living - update the candidate list, mapping, and decisions as we go.
