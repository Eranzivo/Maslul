# Client Context — [Client Name]

> Human-readable mirror of this client's `tenants.config`. DB is the source of truth; keep this in lockstep. See `context/clients/README.md`.

## Identity
| Field | Value |
|---|---|
| tenant_id | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| Business type | [what they do] |
| Workers | [count] ([role label, e.g. טכנאי/שליח/מנקה]) |
| Stage | [pilot / paying / trial] |
| Onboarding SQL | `outputs/[name]-onboarding_[date].sql` |

## Runtime config (mirrors `tenants.config` — walk `context/knobs.md`, decide EVERY row)
| Key | Value | Notes |
|---|---|---|
| `scheduling.mode` | `zone` / `open` / `radius` | assignment strategy |
| `scheduling.zone_match` | `city_list` / `polygon` | how a zone is matched (only when mode=zone) |
| `scheduling.zone_strict` | true / false | hard cross-zone block (default true) |
| `scheduling.route_strategy` | `flexible` / `far_to_near` / `nearest_first` | day-route ordering — ask HOW they arrange a driving day |
| `scheduling.fill_first` | true / false | pack active days before opening new |
| `scheduling.balance` | `{enabled, weight}` | workload spread (see placement-policy note in knobs.md) |
| `scheduling.equal_city_distribution` | true / false | split same-city calls across techs |
| `scheduling.slot_release` | `{enabled, 72/48/24}` | hold early slots for far cities (far_to_near only) |
| `defaults.work_days` | e.g. `[0,1,2,3,4]` | operating weekdays (0=Sun) |
| `defaults.work_start` / `work_end` | [hh:mm] / [hh:mm] | default day hours |
| `defaults.arrival_window_hours` | [hours, fractional ok] | customer window; future: none = call-by-call |
| `defaults.regular_job_minutes` / `package_job_minutes` | [min] | default durations |
| `defaults.max_daily_jobs` | [n] | per tech per day |
| `defaults.break` | `{enabled, start, end}` | tenant default break |
| `depot` | `{lat, lon, address}` | routing origin |
| Features enabled | [whatsapp / geocoding / auto_sequence / crm / reports / …] | `tenants.config.features` |

## Per-tech setup (MANDATORY before first dispatch — backlog #2.10)
Per tech: `base_city`/`return_city` · `rotation` (zone per weekday) · `weekly_schedule` (hours + off-days) · `min/max_daily` · `skills[]` (empty = can take NO categorized call!) · `cat_limits` · `blocked_cities/zones` · `duration_overrides`.

## Zones & rotation
[How zones are defined for this client — city-list or polygon — and the weekday rotation per worker.]

| Day | [Worker 1] | [Worker 2] | … |
|---|---|---|---|
| Sun | [zone] | [zone] | |
| … | | | |

## Restrictions & preferences
- **Blocked zones/cities per worker:** [any]
- **Category limits:** [any per-category daily caps]
- **Special rules / preferences:** [anything unique to how this client works]

## Service categories
| Name | Type | Duration |
|---|---|---|
| [category] | | [min] |

## Integrations
[ERP / WhatsApp / Odoo / SMS — and whether API or manual.]

## Notes
[Language, communication channel, anything else worth context.]

## Change log
| Date | Change |
|---|---|
| [YYYY-MM-DD] | [what changed in config/behavior] |
