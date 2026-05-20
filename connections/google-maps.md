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
