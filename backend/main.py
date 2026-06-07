import os
from datetime import date
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv
from optimizer import optimize_routes

load_dotenv()

app = FastAPI(title="Maslul Optimizer", version="1.0.0")

allowed_origins = os.getenv("ALLOWED_ORIGINS", "https://eranzivo.github.io").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type"],
)

# ── Daily element counter ─────────────────────────────────────────────────────
# Prevents runaway Google Maps spend. Resets automatically each UTC day.
# Limit is configurable via GMAPS_DAILY_ELEMENT_LIMIT env var (default 1 200).
# 1 200 elements/day ≈ 15 full-team optimizations (4 techs × 7 stops = 196 elements each).
# Free tier is 40 000 elements/month → 1 200/day uses at most ~36 000/month, well within free.

_DAILY_LIMIT = int(os.getenv("GMAPS_DAILY_ELEMENT_LIMIT", "1200"))
_counter: dict = {"day": None, "elements": 0}
# NOTE: _counter is per-process. With multiple Railway workers each worker enforces
# the limit independently, so effective daily limit = _DAILY_LIMIT × worker_count.
# Hobby plan runs 1 worker by default; set RAILWAY_NUMREPLICAS=1 to be explicit.

def _gmaps_quota_ok(elements_needed: int) -> bool:
    today = str(date.today())
    if _counter["day"] != today:
        _counter["day"] = today
        _counter["elements"] = 0
    if _counter["elements"] + elements_needed > _DAILY_LIMIT:
        return False
    _counter["elements"] += elements_needed
    return True

def _total_elements(technicians) -> int:
    """N locations per tech → N² elements in the distance matrix."""
    total = 0
    for tech in technicians:
        n = len(tech.tasks) + 1  # tasks + base city
        total += n * n
    return total


# ── Models ────────────────────────────────────────────────────────────────────

class Task(BaseModel):
    id: str
    city: str
    address: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    duration_minutes: int = 30
    scheduled_time: Optional[str] = None


class Technician(BaseModel):
    id: str
    name: str
    base_city: str
    start_time: str = "07:00"
    end_time: str = "18:00"
    tasks: list[Task] = []


class GeocodeRequest(BaseModel):
    street: str
    city: str


class SchedulingConfig(BaseModel):
    mode: str = "zone"
    zone_strict: bool = True
    fill_first: bool = True
    route_logic: bool = True

class OptimizeRequest(BaseModel):
    date: str
    technicians: list[Technician]
    scheduling: Optional[SchedulingConfig] = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    gmaps_key = os.getenv("GOOGLE_MAPS_API_KEY")
    today = str(date.today())
    used = _counter["elements"] if _counter["day"] == today else 0
    return {
        "status": "ok",
        "service": "maslul-optimizer",
        "version": "1.0.0",
        "gmaps": "configured" if gmaps_key else "missing — using haversine fallback",
        "daily_elements_used": used,
        "daily_elements_limit": _DAILY_LIMIT,
        "daily_elements_remaining": max(0, _DAILY_LIMIT - used),
    }


@app.post("/geocode")
async def geocode(req: GeocodeRequest):
    """Geocode a street address using Google Geocoding API. Returns {lat, lon}."""
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="Maps key not configured")
    full_address = f"{req.street}, {req.city}, ישראל"
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(
                "https://maps.googleapis.com/maps/api/geocode/json",
                params={"address": full_address, "key": api_key, "region": "il", "language": "he"},
            )
        data = resp.json()
    except Exception:
        raise HTTPException(status_code=503, detail="Geocoding service unavailable")
    if data.get("status") == "OK":
        loc = data["results"][0]["geometry"]["location"]
        return {"lat": loc["lat"], "lon": loc["lng"]}
    raise HTTPException(status_code=404, detail=f"Address not found: {data.get('status')}")


@app.post("/optimize")
async def optimize(req: OptimizeRequest):
    if not req.technicians:
        raise HTTPException(status_code=400, detail="No technicians provided")

    google_maps_key = os.getenv("GOOGLE_MAPS_API_KEY") or None

    # Only use Google Maps if key is set AND daily quota has headroom
    use_gmaps = False
    if google_maps_key:
        needed = _total_elements(req.technicians)
        use_gmaps = _gmaps_quota_ok(needed)
        if not use_gmaps:
            print(f"[quota] daily limit reached ({_DAILY_LIMIT} elements) — falling back to haversine")

    result = await optimize_routes(req.technicians, google_maps_key if use_gmaps else None)

    return {
        "date": req.date,
        "mode": "gmaps" if use_gmaps else "local",
        "optimized": result,
    }
