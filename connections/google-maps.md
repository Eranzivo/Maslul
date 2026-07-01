# Connection: Google Maps

## What it is
Distance Matrix API — provides real drive times between Israeli cities for route optimization.

## When to use
- The optimizer backend uses this automatically when `GOOGLE_MAPS_API_KEY` env var is set
- Falls back to haversine (straight-line distance) if key is missing

## Key details
- API: Distance Matrix API (not Maps JS API)
- Account: Google Cloud — infomaslul@gmail.com
- Enabled on: Google Cloud Console → APIs & Services

## How it's used
The Railway backend (`backend/optimizer.py`) builds a distance matrix by calling this API for each pair of cities in the day's route, then feeds it into the OR-Tools TSP solver.

## Secrets
GOOGLE_MAPS_API_KEY — stored in `.env` (root) and in Railway env vars
- **Server-side only** — verified NOT present in `index.html` (frontend loads only Google *Fonts*). Never put the Maps key in the frontend.

## 💰 Cost caps & budget — LIVE (set by Eran in GCP, 2026-07-01)
Hard "circuit-breaker" quotas configured in GCP (via Cloud Shell) so that even a code bug or a leaked key **physically cannot** exceed a safe threshold — usage just stops (429) at the cap.

| API | Hard daily cap | ~Monthly cost at cap |
|---|---|---|
| Distance Matrix | **700 elements/day** | ~$105/mo |
| Geocoding | **700 requests/day** | ~$105/mo |

- **Worst-case total ≈ $210/mo**, offset by Google's **$200/mo free credit** → **~$10 (₪37) real out-of-pocket** max.
- **Budget & alerts:** GCP Billing budget **$210/mo**, email alerts at **50% / 90% / 100%**.
- Pricing basis: both APIs ≈ $5 / 1,000 calls → 700/day × 30 ≈ 21,000/mo × $5 ≈ $105 each.
- **Key security:** restrict to only Distance Matrix + Geocoding APIs; server-side only (`.env` + Railway); never frontend.

### ⚠️ Monitoring directive (Eran, 2026-07-01)
Watch usage for patterns approaching these caps, or events needing more headroom (new client onboarding, address-level routing). **When I see it coming, flag it proactively** with the cause + options (raise cap / warm cache / stagger) so we plan the response *before* it bites. Standing task.

### What to watch (my read)
- **Distance Matrix 700/day is the binding constraint.** Steady-state PureWater is fine — `route_cache` serves repeat city-pairs, so daily *new* elements are near-zero once warm.
- **Cold-start risk (Client #2 onboarding):** a new tenant's FIRST full batch has a cold cache; many unique city-pairs at once can exceed 700 elements in a day (~26 unique stops ⇒ 26² ≈ 676, right at the edge; more ⇒ over → premature haversine fallback / 429s). → On onboarding day, temporarily raise the DM cap or seed the cache incrementally.
- **Address-level KB (future, [[geo-foundation-vision]]):** routing on street addresses multiplies unique points ⇒ more unique pairs (DM) **and** a burst of geocoding on import (a >700-address import hits the Geocoding cap). Flag when we build it.
- **⚠️ App soft-cap now INVERTED — verify & fix:** the app's `GMAPS_DAILY_ELEMENT_LIMIT` (default 1200) should sit **just below 700** so we degrade to haversine *before* Google hard-429s. It's currently *above* the new 700 cap → graceful-fallback is backwards. **Action:** set the Railway env var to **680** (not 600 — PureWater's absolute-capacity peak is only ~300 elem/day (3 techs × max_daily 9 ⇒ (9+1)²×3), so 680 keeps the full buffer for fallback without wasting headroom; the sub-700 margin only covers multi-worker slop, and hobby = 1 worker).
- **Scale reality (2026-07-01):** the soft cap gates on *theoretical* matrix size (peek `Σ(stops+1)² per tech`), then charges only cache-miss pairs. **PureWater peak ≈ 300 elem/day; real spend ≈ $0/mo** (route_cache warm) — worst-case no-cache ~$18/mo, both inside the $200 credit. Saturating 700/day needs ~7+ techs (≈2.3× their team). Binding risk stays **Client #2 cold-start**.

Our code has no retry/loop bombs (haversine fallback is not a retry; bounded batch loops; debounced auto-sequence; metered `/geocode`). See [[google-maps-quota-review]].
