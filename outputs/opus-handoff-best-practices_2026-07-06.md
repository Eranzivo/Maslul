# Maslul — Handoff to Opus 4.8 (from Fable 5, 2026-07-06)

> Eran switches to Opus 4.8 starting 2026-07-07. This is the "how Fable worked on Maslul"
> playbook — the practices that caught real bugs and the ones that wasted tokens. Paste-point:
> tell Opus **"Read outputs/opus-handoff-best-practices_2026-07-06.md, then /prime"** at the
> start of the first session. After that, /prime alone is enough (CLAUDE.md carries the rules).

## 1. Session start (every session)
1. Run **/prime** (reads CLAUDE.md + the 4 core context files). `context/README.md` is the
   top-down map: product → engine → knobs → clients.
2. State ONE goal for the session (one slice / one bug / one decision). Don't let a session
   sprawl — Maslul's history shows multi-goal sessions burn context re-explaining state.
3. Auto-memory + `context/backlog.md` carry the queue; don't re-derive it.

## 2. Non-negotiable rules (each one exists because it caught a real bug)
- **Knob rule:** every per-tenant behavior = a row in `context/knobs.md` + a reader in BOTH
  engines (live JS `index.html` + batch Python) + a test, same commit. The June audit found
  flags that consolidated in one engine and spread in the other.
- **Parity fixtures:** shared golden fixtures in `tests/fixtures/*.json` are run by BOTH
  `node tests/*.test.js` and pytest. Any engine change → run `/test-all`; any knob/geo/policy
  logic change → extend the fixture, not just one side's test.
- **Never guess coordinates or Hebrew place spellings** — geocode or use a real data source
  (OSM/Google/gov). Model memory has produced wrong city placements before.
- **Tenant logic lives in `tenants.config`,** never in shared code. Far-to-near is
  PureWater-specific, not a default.
- **Security at every change:** after any schema/policy/function change run Supabase
  advisors; SECURITY DEFINER needs `REVOKE FROM PUBLIC` (not just anon); RLS policy
  expressions run with CALLER privileges. Repo is PUBLIC — no secrets, no client data
  (outputs/purewater-review_2026-06-29/ is local-only, never commit).
- **SQL for Eran = code block in chat**, never a file link.
- **Living docs same commit:** every code change updates its ONE relevant context/ doc.
  Artifacts → `outputs/[task]_[YYYY-MM-DD].[ext]`. Keep CLAUDE.md ~80 lines.
- **Data persistence:** always await Supabase saves; verify `public.users` row exists;
  never `Promise.race` on auth.

## 3. Patterns that worked (reuse them)
- **TDD with real tenant shapes:** the `FakeSB` harness in
  `backend/tests/test_batch_correctness.py` fakes Supabase with PureWater-shaped fixtures —
  extend it for any batch work.
- **MCP-export → offline replay:** no service key locally. To dry-run engine changes, export
  live state read-only via Supabase MCP, run the engine offline against it, diff the plan
  (`outputs/batch-dryrun-diff_2026-07-05.md` is the template). Zero live writes.
- **Optimizer tests need adversarial geometry:** a green test on single-cluster data proves
  nothing — ask "what geometry makes the WRONG behavior cheaper?" (the nearest_first fix
  passed its first tests without the fix; two-branch geometry exposed it).
- **Verify deploys by a field only the new build returns** (`/health` `version` /
  `geo_brain_places`); Railway ~60-90s, Pages ~60s + incognito.
- **Bulk data growth = check every reader's fetch limit.** PostgREST caps at 1000 rows;
  the geo brain (1,310 places) needed paged loaders on both sides. Any table you grow, grep
  who reads it unpaged.
- **Windows quirks:** Hebrew JSON via curl → write UTF-8 file, `--data-binary @file`;
  replace-scripts must assert match count (two silent no-op incidents); async tests: one
  persistent event loop, never bare `asyncio.run()` next to legacy suites.
- **Reversible data ops:** bulk inserts carry a `source` tag (one-DELETE rollback); back up
  before irreversible zone/config edits; readback-verify every config write.

## 4. Skills / process
- `/test-all` before claiming done; `/parity-audit` on any engine diff; `/rebatch-dryrun`
  before touching live schedules; `/onboard-client` for client #2.
- Slice flow: superpowers **brainstorming → writing-plans → executing-plans** (design doc to
  outputs/ BEFORE code), `/code-review` (high) before merge — the review on Slice 1 found 6
  real defects post-TDD.
- Log process learnings in `outputs/ways-of-working_2026-07-02.md` (append-only session log).

## 5. Priority queue (Fable's recommendation, engine-first per Eran's standing order)
1. **Per-task structured constraints** — backlog ⭐ item: earliest/latest/forbidden windows,
   fixed_date, priority, **+ preferred windows get a DAY option** (Eran 2026-07-06,
   intake-form screenshot). Why #1: it's the biggest live gap — the engine can't honor
   "רק ימי ראשון 10:00-13:00" and dispatchers work around it in free-text notes. Solver
   window infra already exists; this is intake fields + both-door readers + mapping.
2. **Explainability + ONE primary recommendation** (handover §8/§9) — engine already computes
   the signals; UI must lead with one best card + human-readable "why", alternatives on
   request. Why #2: it's Israel's core dispatcher-trust ask and needs no solver work.
3. **Override reason required + audited** (§15F) — small schema+UI; closes the audit trail.
4. **Mandatory tech completeness** (§6) — block tech creation without critical fields
   (silent skill-emptiness makes techs invisible to the engine today).
5. **RLS-perf migration** (wrap `auth.uid()`, tenant-FK indexes, consolidate permissive
   policies) — prepared, low-risk, run in a quiet window.
6. **Workspace cleanup** — assigned to Opus explicitly (memory + backlog rules: archive don't
   delete, keep applied migrations + requirement sources).
Later tracks: wizard catch-up to knobs.md, UI pass (timing.tech bar), dashboard, geo
curation follow-ups (ג'ת/גת collision, דיר אל אסד alias).

## 6. Token economy for Opus sessions (Eran asked)
- One slice per session; open with /prime + the goal + the file paths — never "look around".
- Point at docs instead of pasting: the context/ tree + outputs/ designs ARE the memory.
- Prefer editing over regenerating; prefer Grep/targeted Read over whole-file reads
  (`index.html` is ~8,700 lines — never read it whole).
- Batch Supabase MCP queries; export big data to files, not chat.
- Commit + update docs mid-session, so a crash/compact loses nothing.
- Compact (or start fresh) between slices, not mid-slice.

## 7. Connections — what's needed and what isn't (Eran asked)
- **Needed, already in place:** Supabase MCP (DB reads/writes/advisors), GitHub push→Pages,
  Railway auto-deploy, Google Maps key (capped 680/day app-side, 700 GCP), Sentry.
- **Worth adding (cheap, optional):** `RAILWAY_TOKEN` in root `.env` → the assistant can
  manage Railway env/deploys itself instead of walking Eran through the dashboard.
- **NOT needed now:** no new platforms for the decision engine (OR-Tools + route_cache +
  geo brain cover the pilot; live traffic is a non-goal per handover §17); no CRM/Odoo
  connection until PureWater defines the Odoo contract; onboarding agent = the
  `/onboard-client` skill + SQL, no external service. WhatsApp (GreenAPI creds already in
  .env) is the one future integration with real product value (tech notifications / customer
  ETA) — defer until Israel asks.
- **At go-live:** Supabase Pro (~$25/mo) — backups + no-pause; already planned.
