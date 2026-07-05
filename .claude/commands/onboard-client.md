---
description: Rules-catcher — turn a client discovery conversation into validated tenants.config + client doc + onboarding SQL, with nothing missed
---
You are onboarding a new Maslul tenant. The product promise: the engine holds EVERY business's own scheduling logic via per-tenant knobs — never hardcoded, nothing falling between the cracks. `context/knobs.md` is the contract; this flow walks it end-to-end.

**0. Read first:** `context/knobs.md`, `context/clients/README.md`, `context/clients/_template.md`, `context/scheduling-rules.md` (north star + priority order), and `context/clients/purewater.md` as a worked example (its knobs are PureWater-specific, NEVER defaults — especially far_to_near).

**1. Discovery (superpowers:brainstorming — one question at a time, in Eran's language with the client):**
- Business basics: what they do, team size, terminology (drives `labels`), monthly volume.
- **How do they arrange a driving day today?** Let them describe it freely, then map to `route_strategy` (far→near / near→far / no preference) — if their logic maps to NO existing strategy, STOP and flag: that's a new engine knob to design, not a forced fit.
- Geography: fixed territories (zone + city_list/polygon + rotation) vs anyone-anywhere (open) vs nearest (radius)? Sub-city splits ⇒ polygons + geocoding.
- Time promises: windows? length (fractional ok)? or exact-time call-by-call (future `none` — flag if needed)?
- Week shape: `work_days`, hours, breaks; per-tech exceptions.
- Load rules: max/min daily, per-category limits, skills, blocked areas, consolidation-vs-spread preference (placement policy), same-city splitting.
- Durations per category; packages.
- Features: whatsapp, geocoding, auto_sequence, CRM/reports…

**2. Produce (all four, consistent with each other):**
1. `tenants.config` JSON — EVERY knob in the registry gets an explicit value or an explicit "default (absent)" decision. Table of knob → value → the client's words that justify it.
2. `context/clients/[name].md` from `_template.md` — including the per-tech mandatory block.
3. Onboarding SQL → `outputs/[name]-onboarding_[date].sql`: tenant row + config + zones/cities (through the canonical guard) + categories + technicians (rotation, skills, hours) + admin user. Deliver as chat code block too.
4. Coverage checklist: for each registry section — covered / default / **NOT REPRESENTABLE** (the crack-catcher: anything not representable becomes a design task before go-live, per [[product-philosophy]]).

**3. Guardrails:** cities/zones through `cityMatchKey` canonical checks (geo brain); geocode-at-entry ON if polygon mode; security gate (RLS advisor run after any new rows/tables); dry-run `/batch-schedule` on sample data before first real dispatch; CLAUDE.md clients table updated; add the client row + docs in the same commit.
