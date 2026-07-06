# Opus Task Queue (from Fable, 2026-07-06) — ordered, spec'd, token-conscious

> Companion to `outputs/opus-handoff-best-practices_2026-07-06.md` (read that FIRST).
> These are tasks Opus is well-suited for: UI ports, mechanical multi-file work, forms,
> test-writing against existing specs. Each has its spec source — don't re-derive.
> Scenario catalog: `context/scheduling-scenarios.md` (check every task against it).

1. **Explainability + ONE primary recommendation** (handover §9; gap-map #3/#4)
   Lead with one best candidate card + human-readable Hebrew reason built from signals the
   engine ALREADY computes (existingInZone, load, drive context, window fit, zone). Cards
   on request ("מצא מועד אחר" exists). UI-only; no solver change. Pairs with task 2.
2. **Design-system port, then screens** (memory: ui-redesign-port; mockups/claude-design/
   + DESIGN-LOG + port plan). Slice 1 = tokens/components only (md-* namespace), then one
   screen per session in plan order. NEVER regenerate a design — port the approved mockups.
   Read context/design-system.md before ANY UI work; UI-testing rule after each screen.
3. **City-create-from-search flow** (Israel, scenarios B1): unknown city in dispatch search
   ⇒ inline create: geocode via /geocode (never guess coords), REQUIRED zone pick
   (dual-membership allowed with confirm), writes zone.cities via canonical dedup
   (cityMatchKey), optional place_aliases variant. Instantly schedulable after create.
4. **Override reason required + audited** (handover §15F): `manually_overridden` +
   `override_reason` on tasks (additive migration), required prompt on the 3 manual
   placement paths + lock action; audit_log entry. Small.
5. **Three-city golden fixture** (scenarios B3): far/mid/close (e.g. דימונה/קרית גת/אשקלון
   geometry, synthetic matrix) asserting mid-distance calls get mid-morning slots and both
   direction+release invariants hold. Test-only, both suites if the logic seam allows;
   FakeSB e2e otherwise. Also encode Israel's worked example (Dimona 07:00 + BS 08:00 +
   new BS call ⇒ all three inside 07-10) as a batch e2e.
6. **`routeFeasibleAt` guard on manual placement** (scenarios B2/E5): drag/tap-place onto a
   day must reject (or warn per tenant strictness) when travel+durations make the receiving
   route late. Mirror whatever check lands into batch notes (batch is already solver-hard).
7. **Mandatory tech completeness** (handover §6, backlog #2.10): block tech creation
   without skills/hours/base/return/max_daily; wizard-style completeness meter.
8. **Constraints in the EDIT modal**: preferred windows day-chips + date constraints on
   existing calls (intake-only today). Reuse renderPrefWindows + dateCons pattern.
9. **Workspace cleanup** (memory: workspace-cleanup-for-opus — safety rules there).
10. **Job-level duration override** (handover §5): per-task minutes field folded into the
    duration chain (task > tech > category > tenant > 30) — both doors + knobs row note.

## Blocked / waiting (don't start)
- `priority` semantics — Israel must define behavior (E15).
- Traffic `live` mode — Client #2 (Gush Dan) trigger; infra design in backlog.
- E4 live ETA re-flow + customer alerts — after pilot, with WhatsApp integration.
- Supabase Pro upgrade, custom domain — go-live/Client-#2 triggers (Eran).

## Standing rules Opus must keep (cheat-sheet)
Engine-first priority order; knob rule (both doors + test, same commit); never guess
coordinates; SQL as chat code block; outputs/[task]_[date]; living-docs sync same commit;
advisors after any schema/policy change; DO-block role-sim technique for any RLS change
(see outputs/rls-consolidation-plan_2026-07-06.md outcome); PUBLIC repo — no secrets or
client data; Eran smoke-test request after anything auth/RLS/UI-critical.
