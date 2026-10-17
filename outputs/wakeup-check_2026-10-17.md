# Wake-Up Check — 2026-10-17 (after ~2.5 months idle)

**Goal:** verify everything still works so the PureWater/Israel feedback-session loop can resume
from the same point. Last commit `1a87cf4` = 2026-08-02 (76 days ago). Last Israel sign-in = 2026-07-30.

**Verdict: the system is intact and operational. Nothing is broken.** One ops safeguard has
silently died (keepalive), and one product blocker needs your decision (the calendar is 4 months
stale). No code or data was changed by this check — it was read-only apart from a rolled-back
RLS simulation.

> **Resolution log (same day):** ✅ Google billing restored (new paid ILS billing account; the old
> one was an expired free trial and can't be reopened) and re-verified live: geocode returns
> `source:"google"`, אשקלון→קרית שמונה **159 min**, אשקלון→עפולה **108 min** (both real).
> ✅ 28 poisoned `route_cache` rows purged (10 genuine remain). ✅ Key restricted to DM + Geocoding;
> Geocoding v4 methods capped at 0; ₪75 alert budget; Railway hard limit $10 / alert $5.
> ✅ `geo_suggest` QA'd and kept ON (`outputs/geo-suggest-qa_2026-10-17.md`).
> ⏳ **Still open:** keepalive Action (still `disabled_inactivity`), leaked-password protection,
> and the code hardening in §2.0 step 3.

---

## 1. Green — verified working

| Layer | Check | Result |
|---|---|---|
| Supabase project | status | **ACTIVE_HEALTHY** (never paused) — PG 17.6 |
| Supabase auth | `auth/v1/health` with the shipped anon key | **200** GoTrue v2.197.0 |
| Israel's login | `auth.users` row | confirmed, **not banned**, last sign-in 2026-07-30 |
| Israel's data path | RLS simulated under his JWT | tenant resolves, role `admin`, sees **109 tasks / 3 techs / 8 zones / 4 cats / 1 tenant** |
| Tenant isolation | same simulation | sees **1** tenant, not 2 ✅ |
| SECURITY DEFINER invariant | all 4 RLS helper fns | `search_path=""` **with** `public.users` prefix, **no bare `users`** ✅ |
| Railway optimizer | `/health` | **200**, v1.3.0, `gmaps:configured`, `route_cache:configured` |
| GitHub Pages | `https://eranzivo.github.io/Maslul/` | **200**, 668 KB, Last-Modified 2026-08-02 |
| supabase-js pin | in `index.html` | `2.49.4` (correct, unchanged) |
| Git | working tree | clean; **0 unpushed** commits; 1 untracked doc (`agents/building-back-office-agents.md`) |
| PureWater config | `tenants.config` vs `purewater.md` | **exact match** — `zone`/`city_list`/`far_to_near`/`consolidate`/`arrive`/`zone_strict`, slot_release 72-48-24, `work_days [0,1,2,3,4]`, break off, max 9 |
| Zone rotation | 15 covering tech-days resolved by ID | **0 orphans**, matches the documented grid exactly |
| Geo brain | `geo_places` row count | **1,310** (matches the post-national-import expectation) |

### Test suite — all four gates green
| Suite | Result |
|---|---|
| `node tests/zones.test.js` | **65 passed, 0 failed** |
| `node tests/sched.test.js` | **282 passed, 0 failed** |
| `backend/ python -m pytest tests/ -q` | **209 passed** (288 s), 2 benign deprecation warnings |
| inline-JS parse check on `index.html` | **parse OK** |

### Supabase advisors
- **Security:** 3 × INFO `rls_enabled_no_policy` on `geo_addresses`, `route_cache`,
  `place_resolution_log` — **by design** (backend-only Layer-A tables, deny-all RLS).
  4 × WARN SECURITY DEFINER callable by `authenticated` — **inherent to the RLS design**
  (the policies call them); each returns only the caller's own tenant/role. 1 × WARN
  **leaked-password protection disabled** → the one genuinely actionable item (see §2.3).
- **Performance:** all INFO — 8 unused indexes + 1 unindexed FK on `route_audits`. Expected at
  pilot scale (114 rows total). **No action.**

### Note on the anon 401 (investigated, benign)
A pre-login REST probe as `anon` returns `401 / 42501 permission denied for function
current_tenant_id`. Cause: `EXECUTE` is revoked from `anon` on all four helper functions
(`authenticated` and `service_role` retain it). This is **hardening, not a regression** — the app
makes no table reads before sign-in, and the authenticated path is proven working above. Worth
knowing so it isn't misdiagnosed as a dead anon key later: **the key is valid** (role `anon`,
exp 2036, identical to the one in the keepalive workflow).

---

## 2. Needs action

### 2.0 🔴🔴 GOOGLE MAPS BILLING IS DISABLED — silent haversine fallback + cache poisoning
**This is the most serious finding and it was invisible to every existing health signal.**

**Evidence chain:**
1. The `GOOGLE_MAPS_API_KEY` in the local `.env` returns, verbatim:
   `REQUEST_DENIED — "You must enable Billing on the Google Cloud Project"`.
2. Railway's key behaves identically in effect. A live `/optimize` probe
   (אשקלון base → אילת) returned **407 drive-minutes**. Real drive time is ~195 min.
   Haversine at the code's 35 km/h heuristic = **~407 min**. Every leg fetched today matches
   haversine within ±1 min (אשקלון→נהריה 267, →חיפה 224, →קרית ים 239, →קרית חיים 235,
   תל אביב→נתניה 48, →הרצליה 18).
3. **June's cached legs are genuinely Google** — אשקלון→דימונה **79** min (haversine would be
   ~140; real is ~75). So Google worked on 2026-06-13 and has lapsed since.
4. `/geocode` on a real, trivially-resolvable fresh address (`ויצמן 20, נתניה`) returns
   **404 "Address not found"** while still charging 10 quota elements — `google_geocode()`
   returned `None`, i.e. the Google call failed.

**Why nothing caught it:** `/health` reports `gmaps: "configured"`, and `/optimize` reports mode
`gmaps-cached` — both check only that the **key env var is present**, never that a call
*succeeded*. The frontend's `_triggerGeocode` does `if (!res.ok) return;` — a deliberate silent
fail-open. So the whole stack degrades quietly and reports itself healthy.

**Two distinct consequences:**
- **Capacity pessimism.** Long legs are ~2.1× reality. A far-flung day (the north from the
  Ashkelon depot) looks impossible, so the solver drops calls as `day_over_capacity` and
  under-books the day. This is very likely the mechanism behind the long-standing single
  **טבריה** `day_over_capacity` flag. Short intra-cluster legs are barely affected, and
  `far_to_near` direction is driven by zone index (not drive time), so **ordering stays correct** —
  it is the *day budget* that is wrong.
- **Permanent cache poisoning (the worse one).** `build_matrix_gmaps` substitutes a haversine
  estimate per element on failure (`optimizer.py:90-95`), and `build_matrix_cached` then writes
  that value to `route_cache` tagged **`source:'google'`** (`optimizer.py:144-147`).
  `is_trustworthy` cannot catch it: its cap is 10× the same 35 km/h estimate, so a haversine value
  always passes its own test. `route_cache` has **no TTL** — these wrong numbers are the Tier-2
  "brain" and will keep being served as real drive times *even after billing is restored*.

**Fix, in order:**
1. **Re-enable billing** on the Google Cloud project, then re-verify: a fresh `/geocode` must
   return `source:"google"`, and a long fresh leg must come back near reality, not haversine.
2. **Purge the poisoned rows.** All **28** rows written today are haversine mislabelled as Google
   (**all 28 created by this session's diagnostic probes** — see §6); only the 6 rows from
   2026-06-13 are genuine. SQL is in §6.
3. **Code hardening (recommended, separate slice):** make the failure loud and unstorable —
   have `build_matrix_gmaps` return a per-element `ok/failed` marker instead of silently
   substituting haversine, never cache a non-Google value as `source:'google'` (tag it
   `haversine` or skip the write), and surface real API health in `/health`
   (`gmaps: "configured" | "failing"`) by checking the last call's status rather than key presence.

### 2.1 🔴 Keepalive GitHub Action is DISABLED — the pilot's pause-protection is gone
- Workflow state via the GitHub API: **`state=disabled_inactivity`**.
- Run history: ran reliably Mon/Thu through **2026-10-01 (last success)**, then stopped.
- Cause: exactly what `keepalive.yml`'s own comment predicted — **GitHub auto-disables scheduled
  workflows after 60 days with no repo commits.** Aug 2 + 60 days = Oct 1. 
- Current exposure: **16 days with no ping.** The project happens to still be ACTIVE_HEALTHY, so
  nothing was lost — but the safeguard protecting a free-tier project from the 7-day pause is
  currently off.
- **A new commit does NOT re-enable it.** It must be re-enabled explicitly:
  - GitHub → **Actions** tab → **keepalive** → *"This workflow was disabled… Enable workflow"*, or
  - `gh workflow enable keepalive.yml` (note: **`gh` is not installed on this machine**).
- Recommend also clicking **Run workflow** once afterwards to confirm it goes green.
- Longer-term fix: the real removal of this whole class of risk is **Supabase Pro at go-live**
  (already your stated plan — no pause + backups). Until then this Action is the only guard.

### 2.2 🟠 The calendar is 4 months stale — blocks a useful feedback session
- All **89 assigned** tasks sit in **2026-06-07 → 2026-06-21**. **0 tasks on or after today.**
- 20 remain `pending` (incl. the two known flags: **חרב** `needs_location`, **טבריה**
  `day_over_capacity`), plus a תל אביב(5)/חולון(3) cluster — the structural overflow already logged.
- If Israel logs in today he sees an **empty current week** and a history-only calendar. That is a
  poor surface for feedback, and it understates the engine.
- Compounding reason to re-batch: `purewater.md` (2026-06-15) already records that **those 89 rows
  were written by the OLD batch, before the `far_to_near` backtrack fix**, and are *not*
  auto-corrected. A re-batch is the pending action that both refreshes dates and applies the
  corrected engine.
- **Decision needed from Eran before anything is written** — see §3.

### 2.3 🟡 Enable leaked-password protection (2 minutes, free)
Supabase Auth → Settings → enable the HaveIBeenPwned check. Worth doing before a client-facing
feedback round; it is the only advisor finding that is both real and unaddressed.

### 2.4 🟡 Data realism for feedback sessions
Of PureWater's 109 tasks: **109 have a client name, 0 have a phone, 1 has a street, 1 has
coordinates.** 52 distinct cities. The data is **city-level only**. Scheduling works fine on it
(city-level haversine), but anything address-level — real geocoding precision, route-health
scores, the duration-accuracy insight, WhatsApp — can't be demonstrated honestly on it.

---

## 3. Decision required — how to restore a live calendar

| Option | What it gives | Cost / risk |
|---|---|---|
| **A. Re-batch the existing 109 into the coming weeks** | Fast; a full, live-looking calendar using the **fixed** far→near engine; also closes the pending 06-15 action | Follows `rebatch-dryrun`: backup → dry-run → diff → **your explicit approval** → write → verify. Data stays city-level (no phones/streets) |
| **B. Ask Israel for a fresh real export first** | Highest fidelity; real customers, addresses, phones; makes the feedback session about *his* current operation | Needs him to send a CSV before the session; slower |
| **C. Leave June as history; Israel dispatches fresh calls live in the session** | Zero risk; shows the dispatch flow exactly as he'd use it | Empty calendar at session start; no route/packing story to look at |

**Recommendation: A now, B next.** Re-batch so there is a live calendar to react to this week, and
ask Israel for a fresh export to make the *following* session address-level real. A and B are not
exclusive — A can be re-run on B's data when it arrives.

---

## 4. Doc drift found (no code impact)

1. **`features.geo_suggest` is `true` in live config**, but `context/architecture.md`, the geo
   roadmap and memory all describe Slices 2–3 as *"deployed DARK, default OFF, interactive — needs
   browser QA before flag-on."* Neither `outputs/worklog.md` nor `context/backlog.md` records the
   flip. It has been on through Israel's 2026-07-30 session with nothing reported. **Resolve
   deliberately:** either the QA happened (→ update the docs and mark the slices done) or it was
   enabled unverified (→ run the browser QA on the 4 doors: dispatch, add-task, bulk-import,
   zone-authoring). This is the only drift with a behavioral question attached.
2. **`place_resolution_log`** exists in the DB (RLS on, no policies — presumably another
   backend-only Layer-A table) but is **absent from the table list** in `context/architecture.md`.
3. **Railway is still described as "trial expires June 12 2026"** in `context/architecture.md`
   → it is plainly running and paid; update the line.
4. `/health` reports `daily_elements_limit: 680`, consistent with the 700/day provider hard caps in
   memory. Usage today: **0 elements**, 0 optimize calls. No quota concern.
5. `geo_brain_places: 0` on `/health` is **expected** on a cold process (lazy warm-up) — the
   comment in `backend/main.py:277` says so. Can't be warmed from here: `/geo-suggest` correctly
   requires a user session (returned **401**, auth guard working).

---

## 5. Suggested order of operations

1. **Re-enable the keepalive workflow** (Actions tab) + Run workflow once → confirm green. *(§2.1)*
2. Enable **leaked-password protection**. *(§2.3)*
3. **Decide §3** → if A, run the `rebatch-dryrun` procedure (backup → dry-run → diff → approve).
4. Resolve the **`geo_suggest`** question — QA the 4 doors, or mark them verified. *(§4.1)*
5. Commit the untracked `agents/building-back-office-agents.md` (or ignore it deliberately) — a
   commit also resets GitHub's 60-day inactivity clock, keeping the keepalive alive going forward.
6. Ask Israel for a **fresh export** to make the next session address-level real. *(§2.4)*

---

## 6. Cleanup SQL — poisoned `route_cache` rows (awaiting Eran's approval)

All 28 rows dated 2026-10-17 are haversine values mislabelled `source:'google'`; all were created
by this session's diagnostic probes. The 6 rows from 2026-06-13 are genuine Google data and must
be kept. Deleting these is safe and self-healing — any leg deleted is simply re-fetched on the
next solve (and will be correct once billing is restored).

Inspect first:
```sql
select from_key, to_key, drive_minutes, source, updated_at
from route_cache
order by updated_at desc;
```

Then purge only today's poisoned rows:
```sql
delete from route_cache
where updated_at >= '2026-10-17'::date;
-- expected: DELETE 28 ; leaves the 6 genuine rows from 2026-06-13
```

Verify:
```sql
select count(*) as remaining, min(updated_at)::date as oldest, max(updated_at)::date as newest
from route_cache;
-- expected: remaining = 6, oldest = newest = 2026-06-13
```

---

## Appendix — commands used
```
git log/status/branch                           # clean, 0 unpushed, 76 days since last commit
node tests/zones.test.js                        # 65 passed
node tests/sched.test.js                        # 282 passed
cd backend && python -m pytest tests/ -q        # 209 passed
node -e "<inline-JS parse check>"               # parse OK
GET  /health (Railway)                          # 200, route_cache configured
GET  / (GitHub Pages)                           # 200, 668 KB
POST /geo-suggest                               # 401 (auth guard — expected)
GET  auth/v1/health (Supabase, anon key)        # 200
GET  api.github.com/.../actions/workflows       # keepalive: disabled_inactivity
Supabase MCP: list_projects, get_advisors x2, execute_sql (read-only + rolled-back RLS sim)
```
