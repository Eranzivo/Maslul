import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
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


# ── Models ────────────────────────────────────────────────────────────────────

class Task(BaseModel):
    id: str
    city: str
    address: Optional[str] = None
    duration_minutes: int = 30
    scheduled_time: Optional[str] = None


class Technician(BaseModel):
    id: str
    name: str
    base_city: str
    start_time: str = "07:00"
    end_time: str = "18:00"
    tasks: list[Task] = []


class SchedulingConfig(BaseModel):
    mode: str = "zone"           # "zone" | "open" | "radius"
    zone_strict: bool = True
    fill_first: bool = True
    route_logic: bool = True

class OptimizeRequest(BaseModel):
    date: str
    technicians: list[Technician]
    scheduling: Optional[SchedulingConfig] = None  # forwarded for future solver hints


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    gmaps_key = os.getenv("GOOGLE_MAPS_API_KEY")
    return {
        "status": "ok",
        "service": "maslul-optimizer",
        "version": "1.0.0",
        "gmaps": "configured" if gmaps_key else "missing — using haversine fallback",
    }


@app.post("/optimize")
async def optimize(req: OptimizeRequest):
    if not req.technicians:
        raise HTTPException(status_code=400, detail="No technicians provided")

    google_maps_key = os.getenv("GOOGLE_MAPS_API_KEY") or None
    result = await optimize_routes(req.technicians, google_maps_key)

    return {
        "date": req.date,
        "mode": "gmaps" if google_maps_key else "local",
        "optimized": result,
    }
