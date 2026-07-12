# Worklog — parked ideas & their trigger

> Short + precise. Each item = idea · why · WHEN to resurface. Eran asked to keep
> deferred ideas here so they surface at the right time, not before.
> Numbered engine/UI tasks live in `outputs/opus-task-queue_2026-07-06.md`.

## Geo / Google-Maps cost (geocoding is currently ON for PureWater)
- **In-app usage meter** — `geo_usage(month,count)` incremented on real (cache-miss) Google calls, admin banner "גאוקוד החודש: N". *Why:* see the trend before the 700/day cap blocks a dispatch. *Trigger:* first paying client whose usage we watch / client #2. (~1–2h)
- **Opt-in address-level knob** — door-level geocoding per-tenant, **city-centroid default**. *Why:* city-zone tenants (PureWater) drop geocode spend to ~0; precision only where density needs it. *Trigger:* client #2 / scale. (~2–3h)
- **/geocode soft-cap + circuit-breaker** — app-level daily limit mirroring DM `GMAPS_DAILY_ELEMENT_LIMIT=680` + abnormal-rate cutoff. *Why:* day cap bounds COST (~$3.50) but a loop can still exhaust it and DOS our own geocoding. *Trigger:* before scaling geocoding. (~1–2h)  · Cost guarantee already in place: 700/day caps + $210 budget alert (50/90/100%).
- **GCP console walkthrough** — confirm caps/budget match the post-2025 per-SKU free tier. *Trigger:* Eran asked to be reminded at geocoding-enable.

## Call entry / data integrity
- ✅ **DONE 2026-07-07** — Unified call entry. "💾 שמור ללא שיבוץ" on the full dispatch form (`savePendingFromDispatch`) creates/updates a PENDING call with every field (street/floor/apt/entrance/windows/dates); "+ הוסף קריאה" → `startNewCall()` opens the same full form. Thin "רישום קריאה ממתינה" modal retired (code kept, no entry point). CSV + bulk import buttons hidden (code kept). One full-fidelity entry point; queueAssign reloads all fields at assign time.

## Permissions — Phase 2 (deferred to client #2 onboarding)
- **Coordinator EDIT grants for settings areas** — let an admin grant a specific coordinator *edit* (not just view) rights to Zones/Categories/Technicians/Settings/Users. Needs RLS surgery: a `current_user_can_edit(area)` SECURITY DEFINER helper reading `permissions.edit[]`, rewrite the write policies on ~5 settings tables to `admin OR can_edit(area)`, dry-run role-sim + advisors, frontend edit-gating. *Trigger:* a client wants to shift settings responsibility to a coordinator (client #2). Phase 1 (view-access matrix + read-only settings) shipped 2026-07-07.

## UI verifications pending (Eran, in-app — later today 2026-07-08)
- **Monthly calendar block heights** now reflect true category durations (duration-chain fix) — visible change, confirm it reads right.
- **Schedule/calendar UI pass** — go through the schedule screens together; part of the broader UI work.
- **Permissions Phase 1** — grant a coordinator a settings area, confirm read-only banner + hidden edit controls.
- **Zones editor** — typeahead add (אחיהוד silent now), badge אזור, narrow input.
- **Unified call entry** — "שמור ללא שיבוץ" saves a complete pending call; assign later keeps all details.

## Bigger deferred (from opus-task-queue)
- **#2 design-system UI port** — on hold until the product fully functions (Eran).
- **#3 city-create-from-search** — needs geocode greenlight + zone pick; scenarios B1.
- **#10 job-level duration override** — do as ONE DRY refactor (pure `effectiveDuration` + fixture), never piecemeal.

## Route Intelligence P1 follow-ups (2026-07-09)
- [ ] **Eran smoke test → enable audit for PureWater** (SQL in chat 07-09): move a call in the daily view → chip "מסלול NN" appears → click → Hebrew findings panel.
- [ ] Partial audits on 9-call days: haversine speeds overfill the solver (drops → excess comparison skipped). Real cached Google times fix most; if partials persist live, add a relaxed comparison-only solve (no drop penalty).
- [ ] Equal-cost backtrack flag (06-07 מיכאל 292=292): solver found an equally-cheap different order — flag reads "equally-cheap cleaner order exists". Watch dispatcher signal/noise.
- [ ] Solver-vs-ops window asymmetry: solver places finish-inside-window, Israel operates arrive-by-window-end. Worth an Eran/Israel decision whether the SOLVER should also adopt arrival semantics (would open ~30 min of extra capacity per window) — engine change, separate slice, both doors + fixtures.
- [ ] Health-cache staleness: session-open while nightly sweep writes → chip shows older score until re-render/reload. Acceptable P1; revisit with P2 panel.
- [ ] P2 (awaiting Eran): recommendations table + accept/reject workflow + stability knob `audit.min_saving_per_disturbed_min` (default 15, calibrate from replay histogram).

## Window-overrun confirmation ✅ BUILT 2026-07-12 (Eran spec 2026-07-11 + his 07-12 decision)
Refines the shipped `window_semantics: arrive` knob. **Eran's build-time decision:** automatic
paths may book an overrun of **up to 15 minutes**; beyond that → next-best window/day.
- **Live dispatch door:** arrival fits but service spills past window end → NEVER silent.
  `confirmAssign` gate (`overrunMinutes`/`overrunDecision`) → `mo-overrun` popup with facts
  (window/arrival/finish/spill) + THREE actions: שבץ בכל זאת (audited `overrideReason`
  "אישור גלישת חלון…") · מצא חלון אחר (slot added to `window._excludedSlots`, `findBestSlot(true)`
  re-runs with it disabled "הוחרג") · ביטול. Exclusions clear on fresh search / clearDispatch.
- **Automatic door (batch — no coordinator):** knob **`scheduling.auto_overrun_min`** (default 15,
  0 = strict). Pref-window new calls: `narrow_window_for_overrun` (solver-hard, start ≤ end−dur+tol,
  never below window start). Free new calls: `promote_spilled_window` — spill > tol promises the
  NEXT window (fail-open on the day's last slot). **Existing calls' promises never re-broken**
  (sequencer unchanged — it re-times within already-promised windows; that's B5 organic lateness,
  not a booking decision).
- **Approved-overrun tail shipped** (board 3): daily-view window block extends by the spill with a
  dashed window-end line + striped zone + tag "גולש X דק׳ · אושר ע״י המתאם"; lanes account for the
  full extent so neighbors never move/cover. Keyed off the audited override stamp — organic
  lateness stays unsurfaced. (Weekly-view tail = future polish.)
- **Deliberate scope note:** manual DRAG placements don't popup — the dropped call re-sequences
  and route-health audits flag lateness; revisit if coordinators ask.
- Parity: `tests/fixtures/overrun-cases.json` in BOTH suites + `backend/tests/test_overrun.py` (11).
