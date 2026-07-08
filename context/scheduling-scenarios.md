# Scheduling Scenarios — the use-case & edge-case knowledge base

> Source: Israel's accumulated feedback (latest batch folded 2026-07-06) + Fable expansion.
> Purpose: every scheduling principle mapped to WHAT enforces it (feature/test), so any new
> engine work checks itself against this catalog. New scenario learned from a client ⇒ new
> row here (living doc). PureWater-specific values live in `tenants.config` — the CATALOG
> is global; the ANSWERS are per-tenant knobs (`context/knobs.md`).

## A. Principles Israel stated → already enforced (verify against these when touching the engine)
| # | Principle | Enforced by | Proof |
|---|---|---|---|
| A1 | Not a calendar — an optimal-route manager (farthest → closest, per-tech base/return) | `solve_route_v2` direction penalty + `return_city` end-depot; per-tech `base_city`/`return_city` | test_sequencing + test_optimizer |
| A2 | Staggered 3h windows (07-10, 08-11, 09-12…), customer gets a window, never an exact time | slot loop (hourly stagger × `defaults.arrival_window_hours`); `scheduled_window_*` vs internal `scheduled_time` | sched.test.js slot suites |
| A3 | Windows stack — multiple jobs inside one window when travel+duration fit | `slotCapacity` math + solver hard windows | Israel scenario E (handover §15) |
| A4 | Preserve early hours for FAR cities; release 72/48/24h as the day nears (aggressive at 24h) | `slot_release {72,48,24}` knob (far_to_near mode) | knobs.md row |
| A5 | Insert = full route impact (duration, travel, direction, window, load, finish time, buffer) — never "slot is free" | live candidate flow (optTime + slotCapacity + buffer 10min) & batch two-attempt day solve | test_batch_correctness e2e |
| A6 | Never far→close→far; never geographically backward | direction penalty (both strategies) + `wouldBacktrack` guard on manual paths | test_sequencing two-branch |
| A7 | No dead mid-day windows; full utilization | consolidate placement policy + fill-first | policy-cases fixture |
| A8 | Coordinator can't hand-pick any hour ignoring route logic | slot picker (computed slots only) + `zoneDropDecision` hard block + pref-window slot gating | zones.test.js |
| A9 | Priority order: route direction > utilization > delay prevention > fuel > right tech | scoring order in candidates + solver objective | scheduling-rules.md |
| A10 | Better to START LATER than zigzag | solver has no early-start reward — geometry wins over clock (documented invariant; keep it that way) | — |
| A11 | Coordinator sees the tech's FULL existing day before assigning (transparency) | `showCandidate` day-preview panel: every already-assigned call on that tech/day (status dot, window, city, category · client) + the new call in its far→near insertion slot; empty days say so explicitly | index.html `routeHtml` (2026-07-07) |
| A12 | Coordinator sees WHY a candidate is the recommendation (explainability, one primary rec) | `explainCandidate` builds a Hebrew {headline, chips[]} from signals the engine ALREADY scored on (consolidation→zone rotation→day headroom→earliest→customer-window fit→route direction), most-decisive first; UI-only, never changes ranking. Best card leads with the headline; detail card shows headline + supporting chips | index.html `explainCandidate`+`candidateSignals` (2026-07-07); sched.test.js |

## B. NEW from this batch (2026-07-06) — actionable
| # | Item | Status |
|---|---|---|
| B1 | **City-create-from-search flow:** coordinator searches an unknown city ⇒ inline "create city" with REQUIRED zone assignment; immediately schedulable | ✅ 2026-07-08: `showNoResult(city_not_in_zone)` → "⊕ שייך את X לאזור והמשך" opens `openAddCityModal(prefill)` (typeahead, required zone, `isKnownCity` gate on fuzzy suggestion, explicit confirm for brain-unknown cities — never guessed) → auto re-runs `findBestSlot` so the call schedules immediately. Zone writes are admin-only (RLS) → coordinators get a "פנה למנהל" message, not a silent failure. Alias curation stays super_admin (brain) |
| B2 | **"Already late at scheduling time" must be impossible** | Batch: solver-hard ✓. Live dispatch: optTime is route-aware ✓. GAP: manual calendar drag/tap-place checks zone but not time-feasibility of the receiving route → edge E5, candidate for a `routeFeasibleAt` guard (Opus queue #6) |
| B3 | **Mid-distance placement preserves room BOTH directions** (Dimona far / Ashkelon close / Kiryat Gat mid ⇒ mid gets mid-morning) | Emergent from A4+A6 today, but NOT asserted → add golden three-city fixture (Opus queue #5, test-only) |

## C. Edge-case catalog (Fable expansion — "ready for all", PureWater + future clients)
| # | Scenario | Today | Answer/owner |
|---|---|---|---|
| E1 | Two equally-far cities compete for 07:00 | arbitrary stable order | fine; document tie = insertion order |
| E2 | First call of the day is CLOSE (no far call exists yet) | slot_release holds early slots until 48/24h | verify release timing on real data after a month |
| E3 | Far call cancels after near calls took mid slots | `rankGapFill` suggests replacements; day re-sequences | freed-early-slot re-hold is NOT re-applied (accepted: rare + 24h aggressiveness covers it) |
| E4 | Job overruns live (30min → 90min real) | nothing recalculates downstream promises | FUTURE: tech "departed/finished" events → live ETA re-flow + proactive customer alert (pairs with WhatsApp integration; big item, after pilot) |
| E5 | Manual drag onto a day that can't absorb more work | ✅ zone-checked + **capacity-checked + route-fit-checked** (`confirmCapacityDrop` on all 3 manual paths, 2026-07-07): warns when the day is at the tech's max daily load OR has no route-valid insertion slot (`calcOptimalTime`===null), hard-blocks under `route_strict`. Task moving within its own tech+day is exempt. **Overriding a soft warn now REQUIRES an audited reason** (`guardManualPlacement`→`promptOverrideReason`→`overrideStamp`; `tasks.manually_overridden`+`override_reason`, captured by the `_audit_tasks` trigger; shown in task-detail) | knob `route_strict`; #4 override audit |
| E6 | Same city, opposite ends (city-center coords can't order 2 stops) | geo_addresses KB gives door-level coords when street entered | encourage street entry; already cache-first |
| E7 | Dual-zone city (אשקלון in דרום+שפלה by design) | resolveZone picks first match; rotation covers both | keep deliberate; flag NEW dual-memberships at onboarding (/onboard-client asks) |
| E8 | Customer available only specific days+hours | ✅ shipped 2026-07-06 (day-aware windows, hard both doors); **2026-07-07: no longer intake-only** — a call's windows are shown read-only in the task-detail modal (`describeConstraintsHe`) and loaded into the re-dispatch form (`queueAssign`) so they're visible + editable on EXISTING calls | prefwindow fixtures + sched.test.js |
| E9 | fixed_date on an uncovered day | ✅ reason `fixed_date_unavailable`; **2026-07-07: date constraints also visible (detail modal) + editable on re-dispatch** (was intake-only) | datecons fixtures + sched.test.js |
| E10 | Recurring weekly call vs zone rotation drift | recurring_templates exist; rotation is frozen | when rotation changes, re-validate recurring templates' day×zone fit (add to rotation-change checklist) |
| E11 | Tech sick morning-of | manual today (drag calls) | FUTURE "evacuate day" action: batch re-place one tech-day's calls (engine ready — place_task with tech excluded) |
| E12 | Two techs share a zone-day (busy zones, future 3rd covering day) | consolidate policy splits by score | fine; assert with a fixture when it first happens live |
| E13 | Rush-hour travel misestimates (יהוד→ת"א 09:00=60m vs 11:00=30m) | static durations; 3h window absorbs | traffic infra logged in backlog (time_bucket cache + learned durations from real timestamps; `live` mode for Gush-Dan client) |
| E14 | Client #2 wants nearest-first / no windows / open mode / spread | all per-tenant knobs, both doors | /onboard-client walks knobs.md — never copy PureWater |
| E15 | Priority/VIP customer | intake `priority` NOT built | BLOCKED on Israel: what does priority DO (earlier day? bump? overtime?) |
| E16 | Zero-capacity day mid-range (holiday, all-tech training) | day_offs full-day per tech | tenant-level holiday = set day_offs for all; FUTURE: tenant holidays knob |
| E17 | Call with no locatable city (typo, brand-new settlement) | `needs_location` flag, never guessed | ✅ B1 flow shipped 2026-07-08 closes the loop (brain-unknown cities need an explicit confirm; schedulable by name, coords pending curation) |
