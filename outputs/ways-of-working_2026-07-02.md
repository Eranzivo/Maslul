# Ways of Working — Agents / Skills / Process for Maslul (Fable, started 2026-07-05)

> Purpose (per Eran): a log of the way of thinking, findings, and methodology used in this broad review — so future likewise sessions can replay the approach. Part 1 = the agents/skills proposal (for Eran's decision). Part 2 = the session log itself (how the review was actually done, updated as work continues). Durable parts get folded into `context/` once agreed.

---

## Part 1 — Proposal: how we should work in this repo

### The core call: tenant rules are DATA, not agents

Eran's instinct — "a per-tenant agent that catches all of a tenant's rules" — names a real need but the wrong container. A per-tenant *agent* would be a second, drifting copy of what `tenants.config` + `context/clients/[name].md` already are (and the repo already has a hard-won rule that the DB is the single source of truth with the doc as mirror). Agents also start cold, cost tokens per invocation, and can't be diffed/reviewed in git the way a skill can.

**What varies per tenant is config. What repeats across tenants is the *process* of eliciting, validating, and wiring that config. Processes belong in skills.**

So: **no per-tenant agents.** One reusable *rules-catcher skill* that produces each tenant's artifacts, plus a small set of recurring-operation skills. Details:

### Skills to author (priority order)

1. **`/onboard-client` — the rules-catcher.** Turns a discovery conversation into: validated `tenants.config` JSON (checked against a knob registry so nothing is missed), `context/clients/[name].md` from `_template.md`, onboarding SQL, and a per-tech setup checklist (rotation/skills/hours/limits — backlog #2.10's "mandatory tech config"). Its checklist IS the knob matrix from the 2026-07-05 review (A4/C1) — the "nothing falls between the cracks" guarantee, versioned in git. This is the highest-leverage skill because it encodes the product's core promise (full business-logic configurator) before the wizard UI catches up.
2. **`/parity-audit` — dual-engine drift check.** Runs the golden shared fixtures (see below) + walks the parity-pair list (`normalizeCity↔_CITY_ALIASES`, `isTenantWorkDay↔tenant_works_day`, `resolveRouteStrategy↔resolve_route_strategy`, `resolveZone↔find_zone`, live scoring ↔ `_assignment_score`). Run it on every engine diff and periodically. The 07-05 review found live drift in the first pair — this pays for itself immediately.
3. **`/rebatch-dryrun` — the safe re-batch operation.** Backup → `dry_run=true` → diff vs live calendar → human-readable report → explicit approval gate → write → verify. This is the recurring op most likely to hurt live data if done ad-hoc; today it lives in heads and old outputs docs.
4. **`/demand-coverage`** — formalizes the recurring per-zone demand-vs-covering-tech-days deliverable ([zone-demand-coverage-habit]); re-run on every new client export / schedule cycle.
5. **Extend `/test-zones` → `/test-all`** — zones + sched harnesses + backend pytest in one command (the exact trio used to baseline this review).

### Structural drift prevention (better than any reviewer)

- **Golden shared fixtures:** one `tests/fixtures/*.json` set consumed by BOTH `tests/*.test.js` and `backend/tests/` — same inputs, assert identical decisions (strategy resolution, work-day, zone matching, placement semantics once unified). A parity break then fails CI-style on `node`/`pytest` instead of surfacing in a client's calendar.
- **`context/knobs.md` registry** (the "neurons brain" lite, buildable now): one table — config key → JS reader (fn:line) → Python reader → enforcing test → wizard field. The A4 matrix from the review is its seed. Every new knob adds a row in the same commit (living-docs rule).
- Later, optional: a settings.json hook that fires on edits touching parity-pair functions and prints the pair list (the backlog's impact-map idea, cheapest version).

### Agents: keep light

- Use the built-in **Explore / Plan / general-purpose** subagents situationally (fan-out searches, plan drafting) — no standing custom fleet.
- At most ONE custom agent definition is justified: `.claude/agents/engine-reviewer.md` — a review persona primed with `context/scheduling-rules.md`, the knob registry, and the parity list, for reviewing engine diffs. Trade-off: the `/code-review` skill + `/parity-audit` cover ~90% of this in-session at lower cost; recommend deferring the custom agent until diffs get big enough that main-session review dilutes context.
- **subagent-driven-development** stays the pattern for multi-slice UI work (proven on the 06-15 port).

### Process skills (keep, already the culture)
`brainstorming` before features → `writing-plans` for multi-step → `test-driven-development` with REAL tenant data for engine work → `systematic-debugging` for bugs → `code-review` on diffs → `verification-before-completion` before "done". Plus repo rules: branch for code, dry-run before live writes, SQL as chat blocks, living docs in the same commit, frozen PureWater config untouched without approval.

### Trade-offs stated honestly
- Skills are checklists — they only help if invoked; hooks/fixtures are enforced. That's why the fixtures + registry rank above another reviewer persona.
- The rules-catcher skill duplicates what the wizard will eventually do in-product. Deliberate: the skill is the spec the wizard gets built from (C1), and it serves Client #2 before the wizard is complete.
- Cost: skills ≈ free (repo files); custom agents cost tokens per cold start; hooks cost a little friction per edit. Recommended mix is skills-first for that reason.

---

## Part 2 — Session methodology log (how this review was done)

### 2026-07-05 — Review pass (no code changes yet)
1. **Primed via `/prime`**, then read ALL of §0 in order (context/, roadmap/design docs, prior Fable review + retro) before touching code — per CLAUDE.md rule.
2. **Deep-read the backend** (optimizer, batch_schedule, geo_resolver, canonicalize, route_cache, main + test inventory) and the **frontend scheduling path** (candidates engine, resolveZone, sequenceDay/_postOptimize, polygon draw flow) — locating functions by grep, reading full bodies, never trusting docs' claims without the code.
3. **Verified against the live DB (read-only MCP):** PureWater `tenants.config` (confirmed `far_to_near` explicit, balance+equal_city on, `defaults.arrival_window_hours=3` with top-level NULL — which *proved* the batch config-path bug), zones (8, city-list, 0 polygons), geo_places=423/aliases=28, route_cache=6 rows, 89 assigned/20 pending.
4. **Baselined the test suites** before claiming anything about them: 79 pytest + 35 + 61 node — green.
5. **Knob audit method:** for each `tenants.config`/technician field, traced config key → reader in each engine path → whether output changes. Produced the enforcement matrix (review doc A4). This method is reusable — it becomes `/parity-audit` + the knob registry.
6. **Polygon bug:** root-caused by reading the draw flow (`_detectCitiesInPolygon` scans static `CITY_COORDS_JS` only) + checking `geo_places` RLS (deny-all → frontend can't see the brain) + verifying live zones hold no polygons (fix needs no data migration). Systematic-debugging applied at the *reading* stage — no fix attempted before the root cause was proven.
7. Findings written to `outputs/product-review-fable_2026-07-05.md` with file:line evidence for every claim.

### Code-review methodology (to apply on upcoming diffs — logged per §5)
- Review each diff for: knob enforcement symmetry (both engines), absent-config = unchanged behavior, fail-open on external services, awaited persists, no client-specific hardcoding, living-doc updated in the same commit.
- Run `/code-review` skill on the branch diff; then `/test-all`; then dry-run against real PureWater data before any live write; log what was found here.

### Pending fold-into-context (once Eran approves)
- `context/knobs.md` (registry) — new file.
- `_template.md` refresh (C2) + wizard/knob contract note in `context/clients/README.md`.
- Skills: `.claude/skills/` for onboard-client, parity-audit, rebatch-dryrun, demand-coverage, test-all.
- CLAUDE.md: one line pointing to the knob registry + parity rule (keep lean).
