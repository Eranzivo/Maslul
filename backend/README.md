# Maslul Optimizer — Backend

FastAPI service that optimizes technician routes using OR-Tools.
Works offline with city coordinates. Activates Google Maps for real drive times when API key is set.

---

## Local Development

```bash
cd backend
pip install -r requirements.txt
python test_optimizer.py      # verify optimizer works
uvicorn main:app --reload     # start dev server on http://localhost:8000
```

Test endpoints:
- `GET  http://localhost:8000/health`
- `POST http://localhost:8000/optimize`

---

## Deploy to Railway

### Step 1 — Create Railway project
1. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub repo
2. Select the `Maslul` repo
3. Set **Root Directory** to `backend`
4. Railway auto-detects the config from `railway.toml` and deploys

### Step 2 — Set environment variables
In Railway → your service → Variables, add:

| Variable | Value |
|---|---|
| `GOOGLE_MAPS_API_KEY` | your key (see below) |
| `ALLOWED_ORIGINS` | `https://eranzivo.github.io` |

### Step 3 — Connect frontend
In `index.html`, update:
```js
OPTIMIZER_URL: 'https://your-service.up.railway.app',
```

---

## Google Maps API Key Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project (or use existing)
3. APIs & Services → Enable APIs → search and enable:
   - **Distance Matrix API**
   - *(optional later)* **Geocoding API** — for full street addresses
4. APIs & Services → Credentials → Create API Key
5. Restrict the key: API restrictions → Distance Matrix API only
6. Copy the key → paste into Railway environment variables

**Cost:** Google gives $200/month free credit. At Maslul's scale (10 techs × 10 stops × 22 days = ~22,000 matrix elements/month = ~$0.11), you stay well within the free tier indefinitely at early stage.

---

## API Reference

### `POST /optimize`

Request:
```json
{
  "date": "2026-05-13",
  "technicians": [
    {
      "id": "uuid",
      "name": "ישראל כהן",
      "base_city": "תל אביב",
      "start_time": "07:00",
      "end_time": "17:00",
      "tasks": [
        { "id": "task-uuid", "city": "רמת גן", "duration_minutes": 30 },
        { "id": "task-uuid", "city": "הרצליה", "duration_minutes": 45 }
      ]
    }
  ]
}
```

Response:
```json
{
  "date": "2026-05-13",
  "mode": "gmaps",
  "optimized": [
    {
      "technician_id": "uuid",
      "ordered_tasks": ["task-uuid-2", "task-uuid-1"],
      "estimated_times": { "task-uuid-2": "07:35", "task-uuid-1": "09:10" },
      "total_drive_minutes": 42,
      "mode": "gmaps"
    }
  ]
}
```

`mode` is `"gmaps"` when using real Google Maps data, `"local"` when using city coordinate fallback.

---

## How It Works

1. **Distance matrix** — either Google Maps Distance Matrix API (real drive times) or haversine between city coordinates × speed factor (35 km/h average, Israeli city driving)
2. **OR-Tools TSP solver** — single-vehicle routing with time dimension, respects working hours and job durations
3. **Result** — ordered task list with estimated arrival time per stop
