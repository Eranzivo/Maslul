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
| `scheduling.balance.enabled` | **`false`** | **OFF since 2026-06-14** — Israel wants fill-first *consolidation* (pack one tech's day to max before opening another), not even-spread. Reverses the 2026-06-13 balance-ON trial. See feedback #1.5/2.3/2.7. |
| `scheduling.slot_release` | enabled (72/48/24h) | hold early slots for farther cities |
| `defaults.arrival_window_hours` | 3 | customers get a 3-hour service window |
| `defaults.max_daily_jobs` | 9 | per tech per day. Per-tech `max_daily` also set to **9** for all 3 (was 15/12/9, normalized 2026-06-14 per Israel's stated rule). |
| `defaults.work_start` / `work_end` | 07:00 / 18:00 | per-tech `weekly_schedule` can override |
| Features | whatsapp, google_maps (distance matrix), geocoding (enabled 2026-06-07) | `tenants.config.features` |
| `features.auto_sequence` | **ON** (verified live 2026-06-13) | Authoritative auto-sequencing — drop or edit a call and the day re-sequences via OR-Tools. Turned on after the B3 shadow-compare gate; the extra optimizer calls are cheap (drive-time cache, `route_cache:configured`) |

## Zones & rotation
9 city-list zones covering Israel (דרום · לוד-אשדוד · נהריה-חיפה · תל אביב והסביבה · ראש העין והסביבה · ירושלים · זכרון-הרצליה · יקנעם-נתניה · קריית שמונה-עפולה); all 3 techs start from the Ashkelon depot (`base_city = אשקלון`). Day-of-week rotation (0=Sun … 4=Thu; Fri/Sat off):

| Day | אלירן | בני | מיכאל |
|---|---|---|---|
| Sun | דרום | תל אביב והסביבה | יקנעם-נתניה |
| Mon | לוד-אשדוד | ירושלים | זכרון-הרצליה |
| Tue | נהריה-חיפה | זכרון-הרצליה | קריית שמונה-עפולה |
| Wed | תל אביב והסביבה | לוד-אשדוד | דרום |
| Thu | ראש העין והסביבה | נהריה-חיפה | ירושלים |

Setup SQL: `outputs/migration-purewater-zones-rotation_2026-06-05.sql` (original). **Rotation stores zone IDs — if zones are re-created the IDs change and the rotation orphans (grid shows "—"). Re-link with `outputs/migration-purewater-rotation_2026-06-11.sql`** (resolves zone+tech IDs by name; ran 2026-06-11 to fix the orphaned grids).

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
| 2026-06-27 | **Zones cleaned 14→9.** Deleted 5 orphan/duplicate zones not in any rotation (גוש דן, גליל, חיפה וקריות, שפלה, שרון) — they overlapped real zones and caused `resolveZone` misroute ambiguity (a city could resolve to a no-coverage zone). Zero task loss (every task-city already in a rotation zone). Coordinate-verified strays re-homed into rotation zones (נהריה-חיפה/זכרון-הרצליה/קש-עפולה/דרום). Backup `outputs/zones-orphan-backup_2026-06-27.json`; plan `outputs/zone-merge-plan_2026-06-27.md`. **Method note:** city→zone placement must be coordinate-driven (`cities.py`/geocode), not from memory. Surfaced ~10 orphan-only settlements with NO coords → **all geocoded same day** via `/geocode` and added to `cities.py` (all 10 placed via **nearest-member-city** method — see `outputs/zone-assignment-method_2026-06-27.md`). ⚠ Open for Israel: **צופים + סלעית** are a Samaria-fringe pair (צופים's nearest neighbor is the mis-zoned סלעית, 3.2km) — review together, likely both → ראש העין; **עילבון** is a קש-עפולה/נהריה-חיפה near-tie. Long-term: polygon zones for fuzzy fringes. |
| 2026-06-15 | **far_to_near backtrack fixed (engine).** Eran flagged a זיג-זג on אלירן's Tue north day (חיפה→קרית ים→נהריה→קרית ים→קרית חיים). Root cause: `far_to_near` was a soft min-drive bias, not enforced → for PureWater's far-base+clustered-zone geometry the solver picked the marginally-cheapest tour, violating direction (priority #1 > fuel). Fixed in `solve_route_v2` with a dominant outward-arc penalty (fail-open, same-city stays adjacent). Now routes נהריה→…→חיפה (far→near, no revisit). Backend only; **the live 88 assigned tasks were written by the OLD batch and are NOT auto-corrected** — needs a dry-run re-batch to refresh the calendar. See `context/scheduling-rules.md` 2026-06-15 note. |
| 2026-06-15 | **Friday made explicitly off.** All 3 techs' `weekly_schedule[5].work` set `true`→`false` (Fri was only avoided implicitly via an empty Friday rotation slot). PureWater operates **Sun–Thu, Fri+Sat off, always**. Saturday already hardcoded-skipped in both paths. Verified live schedule is clean (Sun 6/7→Thu 6/11, 23/24/12/27/2 = 88, no Fri/Sat); historical assignment left as-is (Eran's call). Explicit per-tenant **working-days config** queued in backlog (the real fix). |
| 2026-06-14 | **Israel demo feedback** (3 docs) triaged → `outputs/israel-feedback-triage_2026-06-14.md` + backlog. Live config: `balance.enabled` → **OFF** (fill-first consolidation, #1.5); per-tech `max_daily` normalized to **9** (was 15/12/9). 108 tasks re-calculated by the engine (fill-first, 9/9/9): **88 assigned / 20 pending** written to the tenant for Jun 7–11. 20 pending = structural תל אביב overflow (27 calls vs 2 covering tech-days, #2.2) + 1 needs-location (חרב). All UI-flow + engine-capability feedback queued (NOT engine-hardcoded — generic config knobs). |
| 2026-06-13 | `auto_sequence` turned **ON** (live-verified); `balance.enabled` ON (trial — reversed 2026-06-14); editable calendar shipped (weekly + daily-grid drag, lock/unlock pin). Geo foundation wired (fail-safe). |
| 2026-06-10 | Engine default `route_strategy` flipped to `flexible` (far_to_near is PureWater-specific). **Audit required**: confirm `tenants.config` sets `route_strategy:far_to_near` explicitly before this ships to main. |
| 2026-06-09 | Standardized to client template; recorded `zone_match = city_list`; flagged far-to-near as PureWater-specific |
| 2026-06-08 | 108 tasks batch-scheduled; service windows live |
| 2026-06-06 | 9 zones + 3-tech rotation + city normalization |
