"""
Run locally to verify the optimizer works before deploying to Railway.
No API key required — uses local city coordinates.

Usage:
    pip install -r requirements.txt
    python test_optimizer.py
"""
import asyncio
from optimizer import optimize_routes
from pydantic import BaseModel
from typing import Optional


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


async def main():
    technicians = [
        Technician(
            id="tech-1",
            name="ישראל כהן",
            base_city="תל אביב",
            start_time="07:00",
            end_time="17:00",
            tasks=[
                Task(id="t1", city="רמת גן", duration_minutes=30),
                Task(id="t2", city="נתניה", duration_minutes=45),
                Task(id="t3", city="הרצליה", duration_minutes=30),
                Task(id="t4", city="כפר סבא", duration_minutes=60),
                Task(id="t5", city="רעננה", duration_minutes=30),
            ],
        ),
        Technician(
            id="tech-2",
            name="דני לוי",
            base_city="ראשון לציון",
            start_time="08:00",
            end_time="17:00",
            tasks=[
                Task(id="t6", city="אשדוד", duration_minutes=45),
                Task(id="t7", city="רחובות", duration_minutes=30),
                Task(id="t8", city="יבנה", duration_minutes=30),
            ],
        ),
    ]

    print("Running optimizer (local mode — no Google Maps key)...\n")
    results = await optimize_routes(technicians, google_maps_api_key=None)

    for r in results:
        tech = next(t for t in technicians if t.id == r["technician_id"])
        print(f"Technician: {tech.name} (base: {tech.base_city})")
        print(f"  Mode: {r['mode']}")
        print(f"  Total drive: {r['total_drive_minutes']} minutes")
        print(f"  Optimized order:")
        for task_id in r["ordered_tasks"]:
            task = next(t for t in tech.tasks if t.id == task_id)
            arrival = r["estimated_times"].get(task_id, "?")
            print(f"    {arrival}  →  {task.city} ({task.duration_minutes} min)")
        print()


if __name__ == "__main__":
    asyncio.run(main())
