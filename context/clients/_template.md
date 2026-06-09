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

## Runtime config (mirrors `tenants.config`)
| Key | Value | Notes |
|---|---|---|
| `scheduling.mode` | `zone` / `open` / `radius` | assignment strategy |
| `scheduling.zone_match` | `city_list` / `polygon` | how a zone is matched (only when mode=zone) |
| `scheduling.route_strategy` | `far_to_near` / `nearest_first` / `flexible` | day-route ordering |
| `defaults.arrival_window_hours` | [hours] | customer service window |
| `defaults.max_daily_jobs` | [n] | per tech per day |
| `defaults.work_start` / `work_end` | [hh:mm] / [hh:mm] | default day hours |
| Features enabled | [whatsapp / google_maps / geocoding / odoo / …] | `tenants.config.features` |

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
