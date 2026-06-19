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

## 💰 Cost-runaway protection (do before Client #2) — 2026-06-16
A SaaS like ours can be billed thousands overnight if a loop hits the API with **no hard cap at Google's side**. Our app cap (`GMAPS_DAILY_ELEMENT_LIMIT`, default 1200) is **soft** — per-process, resets on restart, multiplies across Railway workers. Defense in depth:

1. **GCP → APIs & Services → Quotas (the real loop-killer):**
   - Distance Matrix: **Elements/day = 3000**, **Elements/minute = 100**
   - Geocoding: **Requests/day = 1000**, **Requests/minute = 60**
   - The **per-minute** cap bounds a runaway loop to ~that/min (instant 429); per-day bounds the total.
2. **GCP → Billing → Budgets & alerts:** budget **$25/mo**, alerts 50/90/100% (alerts notify; quotas stop — set both).
3. **Restrict the key:** only Distance Matrix + Geocoding APIs; IP-restrict to Railway egress if possible.
4. **Align app cap:** Railway `GMAPS_DAILY_ELEMENT_LIMIT=2000` (just below the 3000 GCP cap → graceful haversine fallback before Google hard-429s).

Sizing for **PureWater + 1 client**: warm `route_cache` ⇒ near-zero real spend; cold worst-case ~2400 elem/day. 3000/day cap bounds catastrophe to ~$15/day while staying within the $200/mo free tier in normal use. Our code has no retry/loop bombs (haversine fallback not retry, bounded batch loops, debounced auto-sequence, metered `/geocode`). See [[google-maps-quota-review]].
