# context/ — Read-Me-First Map

> The context layer is organized **top-down**: what the product IS → how it decides → what
> is configurable → who the clients are and their specific rules. Read in this order; each
> layer only assumes the ones above it. (Requested by Eran 2026-07-06: "catch the general
> context of the product, down to the PureWater rules/logic".)

## Layer 0 — Ground rules (repo root)
| File | What it holds |
|---|---|
| `CLAUDE.md` | Working rules, stack, tenants, deployment checklist. Lean (~60 lines) — details live below. |
| `brain/maslul-brain.canvas` | 🧠 **The visual neuron map** of everything below (open the repo as an Obsidian vault — `brain/README.md` has the 2-minute setup). Living-docs rule: architecture-level changes update their brain node in the same commit. |

## Layer 1 — What the product is
| File | What it holds |
|---|---|
| `business.md` | Vision, target clients, pricing, competitive position (timing.tech = the bar). |
| `scheduling-rules.md` (top section) | **The product's brain in words**: expert-dispatcher north star, the 5-step priority order (route direction → utilization → no lateness → fuel → tech choice), what must never happen. Universal for every tenant. |

## Layer 2 — How it's built
| File | What it holds |
|---|---|
| `architecture.md` | Stack, file map, hard rules, schema, auth flow, safety stack, geo brain. |
| `scheduling-rules.md` (rest) | Engine mechanics: candidate modes, batch, solver, windows, breaks, sequencing. |
| `zones-polygons.md` | Zone system: city-list + polygon axes, the geo one-source seam, draw flow. |
| `auth-users.md` | Roles, RLS, impersonation, technician↔user linkage. |
| `style.md` + `design-system.md` | CSS tokens, RTL, md-* components; read design-system before ANY UI work. |
| `new-entity-checklist.md` | Mandatory steps before any new Supabase table. |
| `impact-map.md` | **The dual-engine parity / coupling map** ("Neurons brain") — read BEFORE changing any rule that runs in both engines, any shared `tenants.config` knob, or any shared DB column. The JS↔Py pairs that must agree + "change X → verify Y". |
| `automations.md` | External-tool automations registry (n8n/Make/Zapier). #1 weekly "State of Maslul" digest (feasible now, needs a small `/digest` endpoint); #2 gov-doc filler (external, MoD/NDA local-only reference). |

## Layer 3 — What is configurable (the tenant contract)
| File | What it holds |
|---|---|
| **`knobs.md`** | **The registry: every per-tenant rule → its live-JS reader → its batch reader → its test.** A business rule exists only if it has a row here, enforced on BOTH engine doors. This is what "nothing falls between the cracks" means operationally. |

## Layer 4 — Who the clients are (per-tenant instantiation)
| File | What it holds |
|---|---|
| `clients/README.md` | The source-of-truth rule: `tenants.config` (DB) is runtime truth; these files mirror it. |
| `clients/_template.md` | The onboarding contract — a full knob walk + mandatory per-tech setup. |
| `clients/purewater.md` | The pilot: PureWater's chosen knob values, zones/rotation, restrictions, change log. **PureWater's choices (far_to_near, 3h windows, consolidate) are THEIR config — never defaults.** |

## Living state
| File | What it holds |
|---|---|
| `backlog.md` | Backlog + milestone log. |

Primary requirement sources in `outputs/`: `israel-handover_2026-07-06.md` (Israel's consolidated
2-month feedback — the PureWater requirements document) + `israel-handover-gapmap_2026-07-06.md`
(what of it is built vs open), `product-review-fable_2026-07-05.md` (engine audit),
`ways-of-working_2026-07-02.md` (process, security gate, session methodology).

---
> 🧠 [[maslul-brain.canvas|Brain map]] · Related: [[knobs]] · [[architecture]] · [[scheduling-rules]] · [[business]]
