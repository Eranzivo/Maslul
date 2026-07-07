# Opus Task Queue (from Fable, 2026-07-06) — ordered, spec'd, token-conscious

> Companion to `outputs/opus-handoff-best-practices_2026-07-06.md` (read that FIRST).
> These are tasks Opus is well-suited for: UI ports, mechanical multi-file work, forms,
> test-writing against existing specs. Each has its spec source — don't re-derive.
> Scenario catalog: `context/scheduling-scenarios.md` (check every task against it).
>
> **Progress (Opus session 2026-07-07):** #5 DONE (`backend/tests/test_israel_scenarios.py`
> — far→near ordering + window stacking anchors). #6 CAPACITY PORTION DONE
> (`confirmCapacityDrop` + `route_strict` knob on all 3 manual paths; deeper travel-time
> infeasibility still open). Also NEW (Eran live request, not originally queued): dispatch
> slot-picker now shows the tech's full existing day (scenarios A11) — shipped.

1. ✅ **DONE 2026-07-07** — Explainability + ONE primary recommendation (handover §9; gap-map #3/#4)
   Pure `explainCandidate(sig)` in `<sched-logic>` → Hebrew {headline, chips[]} from signals the
   engine already scored on (consolidation → zone rotation → headroom → earliest → window fit →
   route direction). `candidateSignals(c)` reshapes a built candidate. Best card leads with the
   headline (`.md-rc-why`); detail card shows headline + `.sr-why-chip`s. UI-only, no solver
   change. sched.test.js suite (119 passed). Scenario A12. See git log.
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
5. ✅ **DONE 2026-07-07** — Three-city + stacking golden anchors in
   `backend/tests/test_israel_scenarios.py`. NB: the depot-distance physics made a literal
   "Dimona 07:00 from an Ashkelon depot" fabricated day infeasible (correct engine behavior),
   so the stacking test uses a Be'er-Sheva-based tech + same-city cluster. If you want the
   literal worked example, model the tech starting AT the far point.
6. **Partially done 2026-07-07** — capacity guard shipped (`confirmCapacityDrop`,
   `route_strict`). STILL OPEN: travel-time infeasibility (a low count can still be
   route-late) — e.g. reuse `calcOptimalTime`===null as the signal in the manual paths.
7. **Mandatory tech completeness** (handover §6, backlog #2.10): block tech creation
   without skills/hours/base/return/max_daily; wizard-style completeness meter.
8. ✅ **DONE 2026-07-07** — Constraints no longer intake-only. `queueAssign(id)` (the
   re-dispatch/edit path) now loads a call's saved `preferredWindows` + date constraints
   into the intake components (prefWindows/dateCons) so they're visible + editable AND
   applied to the candidate search — also fixes a latent stale-globals bug (an edited call
   could inherit the previous dispatch's windows). Read-only summary in the task-detail
   modal via pure `describeConstraintsHe(t)`. sched.test.js (133 passed). Scenarios E8/E9.
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
