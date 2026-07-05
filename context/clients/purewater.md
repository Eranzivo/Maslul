# Client Context — PureWater Israel (Pilot)

> Human-readable mirror of PureWater's `tenants.config`. DB is the source of truth; keep this in lockstep. See `context/clients/README.md`.

## Identity
| Field | Value |
|---|---|
| tenant_id | `00000000-0000-0000-0000-000000000001` |
| Business type | Garbage disposal units + hot/cold water tap installation |
| Workers | 3 technicians (טכנאי) — אלירן, בני, מיכאל |
| Stage | Pilot (not yet paying, as of Jun 2026) |
| Depot | אלי סיני 7, אשקלון — `31.697962, 34.579152` (in `tenants.config.depot`) |
| Onboarding SQL | `outputs/migration-purewater-zone-cities_2026-06-06.sql` (+ zones-rotation) |

## Runtime config (mirrors `tenants.config`)
| Key | Value | Notes |
|---|---|---|
| `scheduling.mode` | `zone` | zone-strict assignment |
| `scheduling.zone_match` | `city_list` | matches by city list (not polygon) |
| `scheduling.route_strategy` | `far_to_near` | **PureWater/Israel-specific — set explicitly.** Engine default is now `flexible` (`resolveRouteStrategy`); far_to_near is never the global fallback. |
| `scheduling.fill_first` | `true` | fill active zone-days before opening new ones |
| `scheduling.placement_policy` | **PENDING config write: `consolidate`** | **RESOLVED by Israel's handover 2026-07-06** (Scenario D: fill the best nearby route first, avoid half-empty days). Until the config is written, the legacy `balance.enabled:true` maps to `spread` on BOTH doors (consistent since Slice 3 — no more live/batch contradiction). Eran to approve the one-line config change. |
| `scheduling.slot_release` | enabled (72/48/24h) | hold early slots for farther cities |
| `scheduling.equal_city_distribution` | **`true`** | **live (verified 2026-06-29).** ⚠ **Half-wired:** honored only in live dispatch (`_candidatesZone`, [index.html:5478]) and there mostly a tie-breaker (−50 vs the +100 fill-first base); the **batch scheduler ignores it**. Does NOT truly enforce. **Decision + fix pending.** |
| `scheduling.balance.enabled` (behavior caveat) | **`true`** | ⚠ **Contradictory across engines (found 2026-06-29):** ON ⇒ batch `_assignment_score` **spreads** (8→4-4) but live `balanceAdjust` **consolidates** (rewards active days). Same flag, opposite effect by path → inconsistent placement + re-batch churn. See `outputs/purewater-review_2026-06-29/meeting-packet.md` Sec. 5B. Collapse to one shared `placement_policy`. |
| `defaults.arrival_window_hours` | 3 | customers get a 3-hour service window |
| `defaults.max_daily_jobs` | 9 | per tech per day. Per-tech `max_daily` also set to **9** for all 3 (was 15/12/9, normalized 2026-06-14 per Israel's stated rule). |
| `defaults.work_days` | **`[0,1,2,3,4]`** (Sun–Thu) | **set 2026-06-29.** Was absent → Friday-off relied only on per-tech `weekly_schedule[5].work=false`. Now explicit; honored live (`isTenantWorkDay`) + batch (`tenant_works_day`). |
| `defaults.break` | **`{enabled:false}`** | set 2026-06-29 to match current behavior (no break). **Confirm with Israel** whether techs take a fixed daily break. |
| `defaults.work_start` / `work_end` | 07:00 / 18:00 (tenant fallback) | **inert** — all 3 techs have explicit `weekly_schedule`: אלירן & בני **07:00–17:00**, מיכאל **08:00–16:00** (these take precedence). |
| Features | **whatsapp ✓, geocoding ✓, auto_sequence ✓, crm ✓, reports ✓, files ✓, checklists ✓** ; google_maps **off**, odoo **off** | `tenants.config.features` — verified live 2026-06-29. CRM/Reports/Files/Checklists are ON (were undocumented). |
| `features.auto_sequence` | **ON** (verified live 2026-06-13) | Authoritative auto-sequencing — drop or edit a call and the day re-sequences via OR-Tools. Turned on after the B3 shadow-compare gate; the extra optimizer calls are cheap (drive-time cache, `route_cache:configured`) |

## Zones & rotation
**8 city-list zones — REBUILT 2026-06-30** from Israel's authoritative 20-month export (`outputs/purewater-review_2026-06-29/Last 20 month calls.csv`, 405 cities), replacing the old 9 (which had been manually manipulated over time). Verified faithful via per-zone content hash (all 8 match source; 405 total; 0 duplicate cities). Zones (cities): **שפלה אשקלון ומודיעין** (94) · **שרון זכרון עד הרצליה** (77) · **גוש דן** (15) · **חיפה קריות נהריה** (38) · **דרום** (35) · **ראש העין אריאל והסביבה** (26) · **ירושלים והסביבה** (29) · **צפון מזרח כנרת וגליל** (91). All 3 techs start from the Ashkelon depot (`base_city = אשקלון`).

✅ **Rotation WIRED 2026-06-30** (Israel's grid, resolved by zone name; verified by readback). Stayed at **8 zones** — Israel's rotation label "יקנעם-נתניה" (אזור 7) maps to the existing **שרון זכרון עד הרצליה** zone (no 9th zone created). **מתקין 3 = מיכאל.**

| Day | אלירן | בני | מיכאל |
|---|---|---|---|
| Sun | דרום | גוש דן | שרון זכרון עד הרצליה |
| Mon | שפלה אשקלון ומודיעין | ירושלים והסביבה | שרון זכרון עד הרצליה |
| Tue | חיפה קריות נהריה | שרון זכרון עד הרצליה | צפון מזרח כנרת וגליל |
| Wed | גוש דן | שפלה אשקלון ומודיעין | דרום |
| Thu | ראש העין אריאל והסביבה | חיפה קריות נהריה | ירושלים והסביבה |
| Fri/Sat | off | off | off |

**City moves (2026-06-30, per Israel):** מודיעין moved שפלה→ירושלים והסביבה (his אזור 2 = "ירושלים עד מודיעין"); **אשקלון now in BOTH דרום + שפלה** — deliberate depot dual-membership. ⚠ **Dual-membership caveat:** dispatch/batch resolve in-zone against the tech's day-zone so it works fine, but a single-answer `resolveZone` returns the first match, and demand analytics (`city = ANY(z.cities)`) double-count אשקלון. Counts now: שפלה **93** · ירושלים **30** · דרום **36**.

**Covering days/wk (final):** שרון **3** · דרום/שפלה/חיפה/גוש דן/ירושלים **2** · ראש העין/צפון **1** = 15 total. ⚠ **מרכז לוד-אשדוד (שפלה, ~1,885 calls after מודיעין left) gets 2 covering days but demand ≈ 2.6** → still mildly under-covered; candidate for a 3rd day (shift from over-covered חיפה/דרום). **Naming:** zones keep the CSV/file names; Israel's rotation labels (מרכז לוד-אשדוד = שפלה, ת״א והסביבה = גוש דן, נהריה חיפה = חיפה קריות נהריה, קרית שמונה-עפולה = צפון מזרח כנרת וגליל) are the same zones — optional rename pending his OK.

Migration: `outputs/purewater-review_2026-06-29/migration-purewater-zones-rebuild_2026-06-30.sql`. Backup (old 9 zones + rotation): `outputs/purewater-review_2026-06-29/zones-rotation-backup_before_2026-06-30.json`. Clean source map: `zone-rebuild-source_2026-06-30.json`. **`geo_places` (157 coords) + `place_aliases` were NOT touched** — but ~250 of the 405 new cities lack coordinates and will flag `needs_location` until geocoded. **Follow-ons:** (1) ✅ rotation wired 2026-06-30 (Israel's grid); (2) geocode the ~250 new cities; (3) aliases יקנעם→יוקנעם, קיבוץ שובל→שובל; (4) order each zone far→near once geocoded; (5) 7 old-task settlements not in the list (בארותיים / בלפוריה / בני דקלים / כפר אחים / כפר בן נון / כפר מימון / כפר נטר) — add to a zone or ignore. **Re-link mechanism unchanged:** rotation stores zone IDs; if zones are re-created the IDs change and the grid orphans — re-link by name (cf. `outputs/migration-purewater-rotation_2026-06-11.sql`).

## Restrictions & preferences
Israel's full dispatcher spec is captured in `context/scheduling-rules.md` (north star + priority order + must-never-do + window purpose). PureWater's instantiation:
- **Far-to-near routing** is PureWater's chosen logic (route_strategy). True route order should come from the OR-Tools TSP with real drive times — far-to-near is the heuristic, not the goal.
- **3-hour windows = insertion flexibility.** A 07:00–10:00 promise lets the optimizer add 1–2 more nearby jobs into that window (or visit someone first) without breaking the commitment. Windows must show in the calendar AND in slot placement.
- **Slot release (72/48/24h):** near cities can't hold the earliest slots far in advance, reserving them for farther jobs that may still come in.
- **Fill before opening:** prefer adding to a tech's partial/active day over opening another tech's empty future day (e.g. add a Netanya job to Michael's partial Sunday rather than Eliran's empty Thursday) — unless the customer asked for a specific date/window.
- **No unrestricted manual time selection** — coordinators shouldn't freely pick times that break routes; manual override (locks) is constrained/optional for PureWater.
- Worker example for base/return: depart אשקלון, could return קרית גת — routing is relative to each tech's own start.
- No per-tech blocked zones/cities configured yet.

## Signals from Israel's real calendar (screenshots, 2026-06-10)
Israel's live task cards reveal structure currently buried in free-text `notes`:
- **Per-task scheduling constraints** the optimizer must honor (beyond geography): customer time limits ("לא יכולה בשעה 07:00"), fixed/known dates, approval gates ("באישור ישראל"), contact-person-first ("לדבר עם הבן/האישה"). → future structured fields: `earliest`/`latest`/`forbidden_times`, `fixed_date`, `requires_approval`, `contact_person`.
- **"Call 30 min before arrival"** ("חצי שעה התראה לפני") → a per-task notification rule (WhatsApp), not a routing constraint.
- **Variable window length** — not always 3h (saw 1.5h, 3h, 4h). Window length should be configurable per task, not hardcoded.
- **CRM data in the description**: product model (טוחן 750/1000/2200, גריינדמאסטר, HC2200), price/quote (₪350–1150), action type (לקחת/לספק/להתקין/לתקן), contact + phone. → structured `product`, `price`, `job_type`, `contact` fields (the "basic CRM" direction). See [product-philosophy].

## Service categories
| Hebrew | Type | Duration |
|---|---|---|
| טוחן אשפה | Garbage disposal unit | 30 min |
| מערכת מים | Water system (hot/cold tap) | 30 min |
| מרכך אבנית | Water softener | 30 min |
| קריאת שירות | Service call | 30 min |
| Package (bundled) | — | 45 min |

## Integrations
- **Odoo v19** — Maslul generates `MSL-XXXXX` IDs; coordinator copies them into Odoo manually. No API integration planned (optional add-on later).
- Maslul's role is **scheduling only** — it does not replace Odoo.

## Notes
- Hebrew exclusively; RTL, mobile-first.
- WhatsApp is the primary customer communication channel.
- 108 real tasks seeded Jun 2026 (status=pending, city-only; client details filled via ✏️).

## Change log
| Date | Change |
|---|---|
| 2026-07-01 | **Geocoding closed to 100%.** Israel hand-verified the remaining **34** flagged cities in Google Maps and supplied exact coords → **33 inserted** into `geo_places` (`source='human_confirmed'`, `confidence='high'`, overriding robot values on the DISAGREE rows) + **7 spelling-variant aliases** (הר הדר→הר אדר, כפר הרואה→כפר הראה, מכמנים→מכמונים, מוצא עילית→מוצא עלית, גבעת אלה→גבעת האלה, כפר אורנים→כפר האורנים, בני עיש→בני עייש). **All 405 zone cities now resolve (100%).** `geo_places`=423 rows, `place_aliases`=28. Verified by alias-resolution readback. Confirmed the fixed ⚠ ones (בית אריה 32.038,35.049; בית אל 31.939,35.223). Next precision step is address-level (below). |
| 2026-07-01 | **Rotation frozen (hold decision).** Keep the current permanent day-of-week rotation as-is; do **not** tune it until PureWater supplies more real schedules/examples to learn from. Israel to decide whether rotation stays strictly permanent or becomes **"fluid"** — e.g. permanent zones but allowing a day to *overflow* on start/end hours, 3-hour call blocks, etc. (mechanism TBD by Israel). No code/config change today. |
| 2026-06-30 | **Gap cities geocoded (Google + OSM 2-source).** 274 zone cities that couldn't resolve via `cities.py` geocoded with Google (IL-biased, `language=he`) cross-checked against OSM Nominatim; auto-accept only on ≤2 km agreement + inside-IL bbox + no `partial_match`. **233 inserted** into `geo_places` (`source='google_osm'`, high) + **7 coord-match aliases** into `place_aliases` (prefix/spelling variants whose Google coord exactly matched a validated city: מושב אמונים/ביצרון/שחר, קיבוץ מגל/מורן/אפק, יבניאל). **Coverage 371/405 (92%).** 34 flagged for Israel's confirmation (mostly WB/Jerusalem-periphery long-tail) → `outputs/purewater-review_2026-06-29/geocode-review_2026-06-30.md` (Bucket A ready-SQL 26 Google-correct; B 2 both-wrong; C 6 partial-match). Nothing uncertain auto-written. Backend brain refreshes from DB on next solve (TTL 600s). Key used server-side only from `.env`; never printed. Setup uses city-center coords — swap to exact addresses later for true route precision. |
| 2026-06-30 | **Rotation wired + city moves** (live review, after Israel's clarifications). "יקנעם-נתניה" (his אזור 7) → maps to existing **שרון זכרון עד הרצליה** (no 9th zone; stays 8). **מודיעין** moved שפלה→ירושלים; **אשקלון** added to דרום (now in both דרום + שפלה — deliberate depot dual-membership). Rotation JSON set for all 3 techs via name-resolved zone IDs, verified by readback (15 covering tech-days, no NULLs). מתקין3=מיכאל. **Scheduling operational again.** ⚠ open: מרכז לוד-אשדוד (שפלה ~1,885 calls) has 2 covering days vs ~2.6 needed; optional rename of zones to Israel's rotation labels; ~250 cities still need geocoding. |
| 2026-06-30 | **Zones rebuilt 9→8 from Israel's real 20-month export** (live, during the pre-pilot review call). Deleted the old 9 (manually manipulated over time) and created Israel's authoritative 8 zones / 405 cities from `outputs/purewater-review_2026-06-29/Last 20 month calls.csv`. Verified faithful via per-zone MD5 (all 8 match source; 405 total; 0 duplicate cities). `geo_places`/`place_aliases` untouched. Coverage: all 52 live task-cities covered except 10 old-seed leftovers (2 spelling variants יקנעם/קיבוץ שובל, 1 junk חרב, 7 tiny settlements w/ 1 seed task each). **Rotation now orphaned — awaiting Israel's new per-tech allocation.** Backup + migration + clean source in the review folder. The CSV also doubles as a real demand map (8,531 calls/20mo) → see zones section for tech-days/wk sizing. |
| 2026-06-29 | **Product-review stop (pre-Israel meeting).** Mapped every section from `index.html` + audited live config via Supabase MCP. **Doc drift found & reconciled here:** `defaults` block was entirely **absent** in the DB (running on code fallbacks), CRM/Reports/Files/Checklists features were ON but undocumented, `equal_city_distribution:true` was live but only in backlog. **Fix applied (behavior-preserving):** wrote `labels` + `defaults` block — `work_days=[0,1,2,3,4]`, window 3h, durations 30/45, max 9, lookahead 30, `break:{enabled:false}`. Per-tenant safe (engine reads via `isTenantWorkDay`/`tenant_works_day` with absent⇒Sat-off fallback; no shared code changed). Backup + change-log in `outputs/purewater-review_2026-06-29/`. **Verified healthy:** rotation grid correctly linked, 9 zones clean, skills/cat-limits map to real categories. **Pending Israel decisions:** consolidation vs spread (balance+equal_city both on), תל אביב/לוד-אשדוד overflow (16/20 pending), keep/hide ON features, 45-min package. `PRODUCT_GUIDE.md` rewritten to current state. |
| 2026-06-27 | **Zones cleaned 14→9.** Deleted 5 orphan/duplicate zones not in any rotation (גוש דן, גליל, חיפה וקריות, שפלה, שרון) — they overlapped real zones and caused `resolveZone` misroute ambiguity (a city could resolve to a no-coverage zone). Zero task loss (every task-city already in a rotation zone). Coordinate-verified strays re-homed into rotation zones (נהריה-חיפה/זכרון-הרצליה/קש-עפולה/דרום). Backup `outputs/zones-orphan-backup_2026-06-27.json`; plan `outputs/zone-merge-plan_2026-06-27.md`. **Method note:** city→zone placement must be coordinate-driven (`cities.py`/geocode), not from memory. Surfaced ~10 orphan-only settlements with NO coords → **all geocoded same day** via `/geocode` and added to `cities.py` (all 10 placed via **nearest-member-city** method — see `outputs/zone-assignment-method_2026-06-27.md`). Finalized w/ Eran: **צופים + סלעית → ראש העין** (Samaria fringe, eastern catchment — closed the long-standing סלעית mis-zone); **עילבון → נהריה-חיפה** (domain tie-break: קש-עפולה = eastern spine Afula→קרית שמונה). Long-term: polygon zones for fuzzy fringes. |
| 2026-06-15 | **far_to_near backtrack fixed (engine).** Eran flagged a זיג-זג on אלירן's Tue north day (חיפה→קרית ים→נהריה→קרית ים→קרית חיים). Root cause: `far_to_near` was a soft min-drive bias, not enforced → for PureWater's far-base+clustered-zone geometry the solver picked the marginally-cheapest tour, violating direction (priority #1 > fuel). Fixed in `solve_route_v2` with a dominant outward-arc penalty (fail-open, same-city stays adjacent). Now routes נהריה→…→חיפה (far→near, no revisit). Backend only; **the live 88 assigned tasks were written by the OLD batch and are NOT auto-corrected** — needs a dry-run re-batch to refresh the calendar. See `context/scheduling-rules.md` 2026-06-15 note. |
| 2026-06-15 | **Friday made explicitly off.** All 3 techs' `weekly_schedule[5].work` set `true`→`false` (Fri was only avoided implicitly via an empty Friday rotation slot). PureWater operates **Sun–Thu, Fri+Sat off, always**. Saturday already hardcoded-skipped in both paths. Verified live schedule is clean (Sun 6/7→Thu 6/11, 23/24/12/27/2 = 88, no Fri/Sat); historical assignment left as-is (Eran's call). Explicit per-tenant **working-days config** queued in backlog (the real fix). |
| 2026-06-14 | **Israel demo feedback** (3 docs) triaged → `outputs/israel-feedback-triage_2026-06-14.md` + backlog. Live config: `balance.enabled` → **OFF** (fill-first consolidation, #1.5); per-tech `max_daily` normalized to **9** (was 15/12/9). 108 tasks re-calculated by the engine (fill-first, 9/9/9): **88 assigned / 20 pending** written to the tenant for Jun 7–11. 20 pending = structural תל אביב overflow (27 calls vs 2 covering tech-days, #2.2) + 1 needs-location (חרב). All UI-flow + engine-capability feedback queued (NOT engine-hardcoded — generic config knobs). |
| 2026-06-13 | `auto_sequence` turned **ON** (live-verified); `balance.enabled` ON (trial — reversed 2026-06-14); editable calendar shipped (weekly + daily-grid drag, lock/unlock pin). Geo foundation wired (fail-safe). |
| 2026-06-10 | Engine default `route_strategy` flipped to `flexible` (far_to_near is PureWater-specific). **Audit required**: confirm `tenants.config` sets `route_strategy:far_to_near` explicitly before this ships to main. |
| 2026-06-09 | Standardized to client template; recorded `zone_match = city_list`; flagged far-to-near as PureWater-specific |
| 2026-06-08 | 108 tasks batch-scheduled; service windows live |
| 2026-06-06 | 9 zones + 3-tech rotation + city normalization |
