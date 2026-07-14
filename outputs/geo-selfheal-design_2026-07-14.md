# Geo Self-Healing — Design (Health view + correction loop)

> **Status:** Design / spec — 2026-07-14. Builds on the live geo foundation
> (`geo_places` 1,310 · `place_aliases` 29 · `geo_resolver.py` · `canonicalize.py`) and the
> corrections-loop design (`outputs/geo-corrections-loop-design_2026-06-13.md`). Chosen entry
> point: **read-only Health view first (Option A)**, then the correction loop Eran specified.

## Goal
Turn the geo brain from *safe-but-dumb* into *safe-and-self-improving*, **without touching the
routing hot path**:
1. **See** unresolved / out-of-zone cities the moment real calls land (integrity: nothing routes
   on a silent bad guess).
2. **Auto-fix** near-certain typos (`נהרייה`, `באר ש בע`, `קרית שמנה`) so coordinators don't fight
   spelling; **ask** when the entry is genuinely messy (`קרת שמה`).
3. **Add** a real new city → pick its zone (nearest-zone pre-suggested) → learn it forever.
4. **Seed** the real small-settlement long-tail Eran supplies, auto-associated to zones by nearest
   existing member.

## Hard constraints (inherited, non-negotiable)
- **Single resolution authority = backend** (`canonicalize.py` + `geo_resolver.py`). The frontend
  NEVER re-implements resolution — that split caused the original `נהריה/נהרייה` false-flag.
- **Approval-gate doctrine** — a fuzzy/learned decision may auto-apply *to a call* for flow, but a
  new permanent shared-brain alias enters only after human approval (or recurrence auto-promotion).
- **Fail-open** — every new read/log/suggest path degrades to today's behavior on error; geography
  never blocks a call.
- **PII-free Layer A** — `geo_places`/`place_aliases` stay global, place-only, service-key/super_admin.
- **Per-tenant rule = `knobs.md` row + both readers + test/fixture, same commit** (only if a real
  tenant knob is introduced; thresholds below are code constants, documented, not tenant knobs).

## Correction tiers (the core model — corrected for what normalization actually does)
| Tier | Example | Handled by | Behavior |
|---|---|---|---|
| **Noise** | `ת"א`→`תא`, `קרית-גת`, double spaces | `normalize_place_key` (exists) | silent, always — not a guess |
| **Curated alias** | human-blessed variant→canonical | `place_aliases` (exists) | silent |
| **High-confidence fuzzy** | `נהרייה`→`נהריה`, `באר ש בע`→`באר שבע`, `קרית שמנה`→`קרית שמונה` | **NEW** fuzzy matcher (Slice 2) | auto-fix the CALL (shown, reversible); alias to brain **approval-gated** |
| **Messy / no match** | `קרת שמה` | fuzzy matcher returns `fail` | reject at door → "עיר לא נמצאה, הזן שוב" |
| **Real new city, not in zones** | a genuine settlement we lack | add-city→zone flow (Slice 4) | geocode → pick zone → learn |
| **Unlocatable** | `חרב` (junk / can't geocode) | flag only | `needs_location`, never guessed |

Thresholds live in ONE named constant module (backend), auditable/tunable.

---

## Slice plan (build order 1 → 2 → 4 → 3 → 5)

### Slice 1 — `/geo-health` endpoint + super_admin home tile (READ-ONLY, decision-independent)
**Backend** `GET/POST /geo-health` (auth mirrors `/batch-schedule`: service-key Bearer OR user-JWT
introspected → tenant forced to caller via `resolve_effective_tenant`; techs denied; super_admin may
impersonate). For the effective tenant it fetches active tasks (`status in pending/assigned/en_route/
arrived`) + zones with the service key, then per DISTINCT city:
- `geo_resolver.resolve(city)` is `None` → **unresolved**.
- resolves to coords but city not a member of any zone's `cities[]` (canonical-compared via the
  brain's alias map, same seam the batch uses) → **out_of_zone**.

Returns:
```json
{ "tenant_id": "...",
  "unresolved":  [{"city":"חרב","calls":4}],
  "out_of_zone": [{"city":"טבריה","calls":1,"lat":..,"lon":..}],
  "summary": {"unresolved":1,"out_of_zone":1,"attention":2,"checked_cities":37} }
```
Pure computation (`geo_health.py`: `build_health_report(cities_with_counts, zones, resolve, alias_map)`)
unit-tested offline; the endpoint is the thin network shell. Fail-open: any error → `{summary:{...0}}`,
never 500 into the UI.

**Frontend** super_admin-only home tile "🧠 בריאות גאוגרפית · ⚠ N דורשות טיפול" (hidden when
super_admin is false or `attention===0` shows a quiet ✓ state). Fetched async **after** home paints
(never blocks). Click → modal listing city · #calls · reason (`לא זוהתה` / `לא באזור`). Read-only in
Slice 1 (fix buttons arrive with Slices 3–4). Zone-mode aware (out_of_zone only meaningful for zone
tenants).

### Slice 2 — backend `resolve_or_suggest(raw, ...)` with confidence
Pure function returning `{status: "resolved"|"suggest"|"fail", match, key, coords, confidence}`:
1. noise-normalize → exact brain/`cities.py` hit ⇒ `resolved` (conf 1.0).
2. curated alias hit ⇒ `resolved`.
3. else fuzzy over known keys (normalized edit-distance / token-set; Hebrew-aware) → best candidate:
   - `conf ≥ AUTO` (near-certain, e.g. edit-distance ≤1 on a key of len ≥4, or a single
     extra/removed space/yod) ⇒ `suggest` flagged `auto_ok:true`.
   - `LOW ≤ conf < AUTO` ⇒ `suggest` (needs human pick).
   - `conf < LOW` ⇒ `fail`.
Constants `AUTO`, `LOW` in the named module. Tested with a golden fixture incl. all four of Eran's
examples. **No door wiring in this slice** — pure engine + tests only.

### Slice 3 — data-entry door guard (auto-fix + ask)
Wire ② into the city-entry doors (dispatch `s-city`, add-task `at-city`, bulk import, zone authoring).
On an unknown city the door calls the backend:
- `auto_ok` suggestion ⇒ auto-correct the field to `match`, show "תוקן ל־<match> ↩" (one-tap revert),
  and record the alias suggestion into the **approval queue** (Geo Health) — **not** written to the
  brain yet (default; see Open decision).
- non-auto suggestion ⇒ inline "האם התכוונת ל־X?" chooser.
- `fail` ⇒ block with "עיר לא נמצאה — הזן מחדש או הוסף עיר" (→ Slice 4).
Fail-open: backend unreachable ⇒ today's behavior (free-text city), never blocks entry.

### Slice 4 — add-city → pick-zone flow
When the user chooses "add city": backend geocodes it (reuse `/geocode`, cache-first). On success show
a zone picker of the tenant's existing zones, **pre-selecting the zone whose nearest member city is
closest to the new coords** (nearest-member heuristic, the method used 2026-06-27). Confirm →
`geo_places` insert (source `human_confirmed`, high) + append canonical city to `zone.cities[]`
(+ alias for the raw variant). Unlocatable (geocode fails) ⇒ flag `needs_location`, do NOT add.
Reversible; logged.

### Slice 5 — small-settlement seeding
Eran supplies coords for the real settlements from the task list (candidate inputs already in repo:
`outputs/purewater-review_2026-06-29/israeli-settlements-master_2026-07-06.csv`,
`settlements-gap-missing_2026-07-06.csv`). Reusable helper: for each (name, coords) → insert into
`geo_places` + auto-suggest zone by nearest existing member; Eran confirms the batch; SQL delivered as
a chat code block. Backfills the exact long-tail that flags today.

---

## Open decision (affects Slice 3 only)
**When a high-confidence fuzzy fix fires, does the alias write to the shared brain immediately, or wait
for one-click approval in the Geo Health view?** Default in this spec = **approval-gated** (consistent
with the durations P2 gate and the "high bar to enter the brain" rule). Eran may switch to
immediate-write if he wants zero friction; the call is auto-fixed either way, so routing is unaffected.

## Testing
- Slice 1: `backend/tests/test_geo_health.py` (pure report: unresolved-only, out-of-zone-only, both,
  all-clear, counts, alias-canonical membership). Frontend: parse-check + manual home-tile QA.
- Slice 2: golden fixture `backend/tests/fixtures/geo-suggest-cases.json` (Eran's 4 examples + negatives).
- Both JS suites + backend pytest green before each commit; deploy-verify per CLAUDE.md checklist.

## Non-goals (this spec)
Routing/optimizer changes; low-confidence "verify me" audit of existing `geo_places`; GPS ground-truth
healing (design phase 6); automatic quorum promotion. All remain deferred/documented.
