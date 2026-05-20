# Connection: Railway

## What it is
Hosts the FastAPI optimizer backend. Auto-deploys from `backend/` on every push to main.

## When to use
- Route optimization requests (POST /optimize)
- Health checks (GET /health)
- Debugging backend errors or slow responses

## Key details
- Live URL: https://maslul-production-77fa.up.railway.app
- Dashboard: railway.app (infomaslul@gmail.com)
- Auto-deploys from `backend/` subfolder on every push to main (~2–3 min, OR-Tools is large)
- **Trial expires June 12 2026** — upgrade to Hobby plan ($5/mo) before then

## Environment variables (set in Railway dashboard)
| Variable | Value |
|---|---|
| PORT | 8080 |
| ALLOWED_ORIGINS | https://eranzivo.github.io |
| GOOGLE_MAPS_API_KEY | set — Distance Matrix API enabled |

## Notes
- Port must be 8080 — if 502, check Networking → domain → pencil icon in Railway dashboard
- First deploy after OR-Tools change takes 2–3 min (large library)
- Health check endpoint: GET /health

## Secrets
GOOGLE_MAPS_API_KEY — stored in `.env` (root) and set in Railway dashboard
