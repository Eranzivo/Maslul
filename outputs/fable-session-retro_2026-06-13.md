# Fable Session Retrospective — Scheduling Engine B1→B3

**Date:** 2026-06-09 → 2026-06-13
**Model:** Claude Fable 5 (the work below), reviewed/logged by Opus 4.8
**Scope:** Drive-time cache, authoritative auto-sequencing, route-strategy physics, full product audit
**Outcome:** Scheduling-engine workstream code-complete end to end; B1 cache verified live in production.

---

## 1. What shipped (on top of what we built before together)

The earlier sessions built the *configurable* scheduling engine: modes, `route_strategy` as a label,
duration overrides, zones/polygons, service windows, slot-release, the batch scheduler, the calendar
rebuild. Fable's session took that foundation and made the **engine itself authoritative and cheap to run**.

| Plan | What it added | Why it matters |
|---|---|---|
| **B1 — Drive-time cache** | Global (tenant-independent) `route_cache` table, deny-all RLS, cache-first matrix builder (`build_matrix_cached`), physics-based trust bounds, honest quota accounting (`gmaps-cached` mode) | Same routes get priced from cache → near-zero Google spend on repeat days. **Verified live: 2nd identical `/optimize` consumed 0 quota.** |
| **B2 — Auto-sequencing** | `markDayDirty → debounced(1s) → epoch-guarded sequenceDay → awaited persists`, all behind `features.auto_sequence` | The app now *re-optimises a day on every mutation* instead of leaving the coordinator's manual order. No-op when the flag is absent → PureWater untouched. |
| **B3 — Strategy physics + safety** | `route_strategy` modelled as real physics (separate cost/time callbacks so far→near *emerges* from the drive-home cost, not a hardcoded rule), weekly balance bias, gap-fill on cancel, **shadow-compare modal** (current vs proposed route, read-only), optimistic versioning (concurrent-edit guard) | Turns "far-to-near" from a label into solver behaviour; shadow-compare is the **PureWater go/no-go gate** — Israel sees the fuel delta before we flip anything on. |

**Plus a full fresh-eyes product audit** (`outputs/product-review-fable_2026-06-12.md`) with live DB verification,
which found real defects the original builders had missed (see §2).

---

## 2. Bugs the audit / TDD caught (the real value)

These were found **before** they could hurt a client — most by the act of writing an honest test or auditing with fresh eyes:

1. **WAL cross-tenant write bug** 🔴 — `_replayWAL` stamped the *live* `currentTenantId` onto replayed rows.
   Under super-admin impersonation a PureWater row could be rewritten under Maslul Admin (RLS bypassed).
   Fixed by capturing the tenant at write time and replaying with the stored value.
2. **`/geocode` was unmetered** 🔴 — a Google-billed endpoint with no quota guard. Now metered.
3. **RLS policies re-evaluated `auth.uid()` per row** 🟡 — wrapped as `(SELECT auth.uid())` (perf).
4. **B1 trust-bound floor was wrong** — a 35 km/h haversine heuristic rejected genuine highway legs
   (Google's real 75-min TLV→Haifa vs a 145-min heuristic floor). The *test with real coordinates* exposed it →
   rebuilt the floor on physics (straight-km at 110 km/h).
5. **B3 arc-bias was mathematically impossible** — with end-at-last-client semantics, "far-first" is never a tie,
   so an arc-bias could never trigger. Writing the test with honest matrices killed the bad design →
   replaced with the cost/time-callback split that's actually correct.

---

## 3. Reusable process lessons (do this next time)

These are the transferable habits — applicable to any future engine/back-office work:

1. **Write the test with *realistic* data before coding optimizer logic.** Twice, the test is where a
   bad assumption died cheaply (B1 floor, B3 arc-bias). Toy matrices hide design errors; real-distance
   matrices reveal them. The optimizer is the one place to never skip TDD.

2. **Do a fresh-eyes full audit before piling more onto a foundation.** A new perspective auditing the
   *whole* product — with live DB verification (Supabase advisors + integrity SQL), not just reading code —
   surfaced a cross-tenant data bug and an unmetered billing endpoint. Budget an audit pass at each milestone.

3. **Ship a diagnostic before guessing at a deploy gremlin.** The "`mode:gmaps` not `gmaps-cached`" mystery
   was settled not by poking Railway repeatedly but by adding a one-line `/health` field
   (`route_cache: configured | missing …`) that *named the exact cause*. When a remote state is ambiguous,
   the cheapest fix is to make the system report its own state.

4. **Flag-gate every new behaviour so "absent config = today's behaviour."** B1/B2/B3 all merged to `main`
   while PureWater stayed byte-for-byte unchanged, because every new path is gated on a tenant-config key
   that PureWater doesn't have yet. This is what makes aggressive engine changes safe to ship continuously.

5. **Honest accounting + fail-open.** Cache hits cost nothing and only real Google fetches charge quota
   (peek-then-charge). Every cache path fails open — a cache outage can never break the optimiser. Model the
   *physics/economics truthfully* rather than approximating, then degrade gracefully.

6. **Verify post-cutoff claims by searching, don't deny from stale memory.** (The "does Fable exist?" episode.)
   A model's training cutoff is a hard wall; when a user asserts something newer, search before contradicting.

7. **Keep the living-docs + `outputs/` discipline.** Every code change updated its one doc in the same commit;
   every artifact (plans, migrations, this retro) lands in `outputs/[task]_[date]`. Future-you reconstructs
   the "why" from these, not from chat history.

---

## 4. State at end of session

- **Live & verified:** B1 cache (`route_cache: configured`, 0-quota cache hit confirmed), v1.1.0 on Railway.
- **Built, flag-off:** B2 auto-sequencing + B3 strategy/balance/gap-fill/shadow-compare — all gated, PureWater untouched.
- **Pending one migration:** `outputs/migration-tasks-updated-at_2026-06-12.sql` (activates the concurrent-edit guard; dormant until run).
- **Next:** enable `auto_sequence` on the Maslul Admin test tenant → live QA → shadow-compare on 2–3 real
  PureWater days (impersonated, read-only) → Israel sign-off → enable for PureWater.
