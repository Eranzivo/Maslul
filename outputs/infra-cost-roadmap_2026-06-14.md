# Infrastructure & Cost Roadmap (2026-06-14)

> **Eran's framing:** two cost classes —
> 1. **Foundations ("on me")** — reliability/data-safety the business depends on regardless of
>    client count. Must be solid. *These are the priority.*
> 2. **Client-driven ("on the way")** — added as a client needs the feature, and **passed through
>    in the price they pay**. No need to pre-spend.
>
> Pricing/limits are current to mid-2026 — confirm on each provider's pricing page before acting.

## Current stack & spend
| Layer | Provider | Plan | Cost |
|---|---|---|---|
| Frontend | GitHub Pages | — | free |
| Optimizer API | Railway | Hobby | $5/mo (incl. $5 usage credit) |
| DB / Auth / RLS / Storage | Supabase | **Free** (assumed) | $0 |
| Maps (distance matrix, geocoding) | Google Maps | $200/mo free credit | $0 (cache-backed) |
| Errors | Sentry | free | $0 |

## Railway $5 Hobby — what it gives
- $5/mo subscription **including $5 of usage credit**; low-traffic optimizer (idle most of the time,
  `route_cache` keeps Google calls near-zero) likely sits at the base for a long time.
- Always-on (no sleep), 8 GB RAM / 8 vCPU per service, custom domains, usage dashboard.
- **Outgrow trigger:** usage > ~$5/mo across many concurrent optimizations, or need team/>8GB →
  Railway Pro ($20/mo + usage). Not soon — just watch the meter as clients are added.

## FOUNDATIONS ("on me") — priority

### ⭐ Supabase Free → Pro (~$25/mo) — the next real spend
Driver is **not** size — it's **reliability + data safety**:
- **Free projects pause after 7 days of inactivity** → a live client could hit an outage needing
  manual restore.
- **Free has no automatic backups** (Pro = daily + PITR). We have **already had data-loss incidents**
  with Israel — backups directly de-risk that.
- **Trigger: before PureWater goes truly live / paying.** This is the single most important infra move.

Free-tier ceilings to monitor (not urgent): 500 MB DB (tasks + `route_cache` + `geo_places` grow);
50k MAU (irrelevant — tiny teams).

## CLIENT-DRIVEN ("on the way", pass-through pricing)
Add only when a client needs it; cost is covered by their plan.
- **File storage (photos)** — tech done-call photo uploads eat the 1 GB free fast. Pro's 100 GB covers
  it; otherwise upgrade when photo upload is used heavily.
- **Custom SMTP** (Resend/SendGrid, ~free–$20) — when onboarding many users (auth emails outgrow
  Supabase's built-in ~few/hour limit).
- **Twilio / WhatsApp Business API** (~$5–20/mo) — when customer ETA/notifications ship.
- **Cloudflare + domain** (maslul.co.il, ~$10/yr, Cloudflare free) — after Client #2. See [[cloudflare-custom-domain]].
- **Google Maps budget** — $200 credit + 0-quota cache scales well; revisit only at high first-time
  lookup volume across many clients. See [[google-maps-quota-review]].

## Sequence
1. **Supabase Pro** → at PureWater go-live (backups + no-pause). ⭐ foundation
2. **Storage / SMTP** → at heavy photo use / user-onboarding scale.
3. **Twilio/WhatsApp** → when notifications ship.
4. **Cloudflare/domain** → Client #2.
5. **Railway Pro / higher Maps budget** → only when multi-client load demands it (likely last).

**Bottom line:** pilot is well-covered on $5 Railway + Supabase Free. The first foundational spend to
plan is **Supabase Pro at go-live**, chiefly for data safety.
