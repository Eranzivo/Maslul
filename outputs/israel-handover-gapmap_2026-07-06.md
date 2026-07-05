# Israel's 2-Month Handover → Gap Map (2026-07-06)

> Source: Eran's consolidated handover prompt (Israel's feedback, May–Jul 2026), delivered in-chat 2026-07-06. Team-size (4 vs 3) and similar detail diffs ignored per Eran. This map lists only MAJOR items, each verified against the code.

## ✅ Already implemented (the handover confirms the built direction)
- Core split engine-vs-tenant-config (§3) = `tenants.config` + `context/knobs.md` registry. No `if tenant==` anywhere.
- Route-as-workday, far→near toward return city, backtrack penalized (§4) = `solve_route_v2` direction enforcement + `return_city` end-depot.
- 3h windows as stackable capacity, not one-job blocks (§5) = window model + `slotCapacity` + solver hard windows.
- Durations: 30/45 defaults + overrides by type/tech/tenant (§5) = duration chain (all modes + batch). *Job-level override missing — see gaps.*
- Daily region assignment ≠ permanent N/S (§7) = rotation (weekday→zone) + zones city_list/polygon, both doors.
- Hard constraints (§8): skills, hours incl. per-day early finish (weekly_schedule — Scenario B), capacity, region policy, overlap, day-offs — enforced live + batch since the correctness pack.
- Consolidation principle (§7/Scenario D) = fill-first scoring — NOW formalized as `placement_policy` (Slice 3, this change).
- Dispatcher flow search→recommendation→confirm (§10) = dispatch form + candidate cards + confirm.
- Draft-vs-confirmed distinction (§11) = pending tray/needs-attention vs assigned calendar.
- Manual override allowed + engine recalculates downstream (§15F) = locks + `markDayDirty` re-sequencing. *Reason-required missing — see gaps.*
- Non-goals (§17) match: no Odoo sync, no portal, no mobile app built.

## 🔴 Major gaps → the priority queue (engine-relevant first)
1. **Placement policy** (§7, Scenario D) — ANSWERED by this handover: consolidate. → **Slice 3 implemented now** (one `scheduling.placement_policy` knob, identical in both doors; legacy `balance`/`equal_city` flags map onto it). Remaining: flip PureWater config to `consolidate` (Eran approval — changes live placement behavior).
2. **Per-task structured constraints** (§8 "customer availability", §10 intake fields, §13 Job.customer_preferences/priority/requested_window) — today free-text notes only. The engine can't honor "לא יכולה בשעה 07:00" / fixed dates / priority. Next engine slice after 3: add `earliest/latest/forbidden_windows/fixed_date/priority` columns + intake fields + solver window mapping (infra exists — `window_start/end` already hard).
3. **Explainability / recommendation reasons** (§8 output, §9, §16.7-8) — engine computes the signals (trace, drive minutes, fill context) but the UI doesn't say "why this tech" and rejected-candidate logging doesn't exist. = roadmap "Explainability v1", now upgraded to a handover requirement.
4. **One primary recommendation by default** (§9) — current UI leads with 3 equal cards; handover wants ONE best + reasons, alternatives only on request ("Find Another Date" exists). UI change, pairs with #3.
5. **Override reason required + audited** (§15F, §16.11) — locks/manual placement don't capture WHY. Small schema+UI addition (`manually_overridden`, `override_reason`), audit_log already exists.
6. **Mandatory tech completeness** (§6: "cannot be created without all critical fields") — backlog #2.10; skills-empty currently silently makes a tech ineligible rather than blocking creation.
7. **Rotation variety/fairness engine** (§7: ≤5 weekly regions, fair auto-rotation) — rotation is manual (and PureWater's is frozen by choice). A rotation-suggestion engine = later (backlog #2.2); not blocking.
8. **Job-level duration override** (§5) — chain stops at tech/category; per-job minutes field missing. Small.
9. **Odoo coexistence mapping** (§2, §13 ExternalIntegrationMapping) — `assign_id` (MSL-xxx) exists; field mapping undefined — explicitly waiting on real Odoo contract, keep parked.

## Resolutions this handover settles (context updated accordingly)
- **Consolidate wins** — reverses the 2026-06-27 balance-ON trial; the 5-same-city pile-up concern is handled as a soft same-city penalty inside spread policy only; grouping same-area is a PLUS per §8.
- 3h windows confirmed as the standard PureWater model (variable window length stays backlog, real cards showed exceptions).
- One-recommendation-first resolves the June "3 cards" vs "1 best" tension: 1 best default, cards on request.
