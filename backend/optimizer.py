import math
import httpx
from typing import Optional
from ortools.constraint_solver import routing_enums_pb2, pywrapcp
from cities import get_coords


# ── Distance helpers ──────────────────────────────────────────────────────────

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def km_to_minutes(km: float, speed_kmh: float = 35.0) -> int:
    """Convert km to drive minutes. 35 km/h is realistic for Israeli city driving."""
    return max(3, int(km / speed_kmh * 60))


def _parse_loc(loc: str) -> tuple[float, float]:
    """Parse a location string into (lat, lon).

    Accepts 'lat,lon' coordinate strings (from geocoded tasks) or city names.
    """
    parts = loc.split(',', 1)
    if len(parts) == 2:
        try:
            return float(parts[0].strip()), float(parts[1].strip())
        except ValueError:
            pass
    return get_coords(loc)


def _task_location(t) -> str:
    """Return the best available location string for a task."""
    if t.lat and t.lon:
        return f"{t.lat},{t.lon}"
    if t.address:
        return f"{t.address}, {t.city}"
    return t.city


def build_matrix_local(locations: list[str]) -> list[list[int]]:
    """Build travel-time matrix (minutes) using city coordinates + haversine."""
    n = len(locations)
    matrix = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i != j:
                lat1, lon1 = _parse_loc(locations[i])
                lat2, lon2 = _parse_loc(locations[j])
                matrix[i][j] = km_to_minutes(haversine_km(lat1, lon1, lat2, lon2))
    return matrix


async def build_matrix_gmaps(locations: list[str], api_key: str) -> list[list[int]]:
    """Build travel-time matrix using Google Maps Distance Matrix API."""
    joined = '|'.join(locations)
    params = {
        'origins': joined,
        'destinations': joined,
        'key': api_key,
        'mode': 'driving',
        'language': 'he',
        'region': 'il',
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get('https://maps.googleapis.com/maps/api/distancematrix/json', params=params)
        data = resp.json()
    except Exception:
        return build_matrix_local(locations)

    if data.get('status') != 'OK':
        return build_matrix_local(locations)

    n = len(locations)
    matrix = [[0] * n for _ in range(n)]
    for i, row in enumerate(data.get('rows', [])):
        for j, element in enumerate(row.get('elements', [])):
            if element.get('status') == 'OK':
                matrix[i][j] = element['duration']['value'] // 60  # seconds → minutes
            else:
                lat1, lon1 = _parse_loc(locations[i])
                lat2, lon2 = _parse_loc(locations[j])
                matrix[i][j] = km_to_minutes(haversine_km(lat1, lon1, lat2, lon2))
    return matrix


# ── Time helpers ──────────────────────────────────────────────────────────────

def time_to_min(t: str) -> int:
    h, m = map(int, t.split(':'))
    return h * 60 + m


def min_to_time(m: int) -> str:
    m = max(0, min(m, 23 * 60 + 59))
    return f"{m // 60:02d}:{m % 60:02d}"


# ── OR-Tools TSP solver ───────────────────────────────────────────────────────

def solve_route(
    base_city: str,
    task_cities: list[str],
    task_durations: list[int],
    matrix: list[list[int]],
    start_time_str: str,
    end_time_str: str,
    return_city: str = '',
) -> tuple[list[int], list[int]]:
    """
    Solve a single-vehicle TSP with time windows.

    When return_city differs from base_city the matrix must include the return
    location as its last row/column (appended by the caller).

    Returns:
        ordered_indices: task indices in visit order
        arrival_minutes: absolute minute-of-day for each visit
    """
    n_tasks = len(task_cities)
    two_depot = bool(return_city and return_city != base_city)

    if n_tasks == 0:
        return [], []
    if n_tasks == 1:
        return [0], [time_to_min(start_time_str)]

    # Nodes: 0=start depot, 1..n=tasks, (n+1=end depot when two_depot)
    n_nodes = n_tasks + 1 + (1 if two_depot else 0)
    end_node = n_nodes - 1 if two_depot else 0
    start_min = time_to_min(start_time_str)
    end_min = time_to_min(end_time_str)
    horizon = end_min - start_min  # total working minutes

    manager = pywrapcp.RoutingIndexManager(n_nodes, 1, 0, end_node)
    routing = pywrapcp.RoutingModel(manager)

    # Travel-time callback (matrix already offset: row/col 0 = depot)
    def travel_cb(from_idx, to_idx):
        return matrix[manager.IndexToNode(from_idx)][manager.IndexToNode(to_idx)]

    travel_idx = routing.RegisterTransitCallback(travel_cb)
    routing.SetArcCostEvaluatorOfAllVehicles(travel_idx)

    # Service-time callback: job duration at each node (0 at start/end depots)
    service_times = [0] + task_durations + ([0] if two_depot else [])

    def service_cb(from_idx, to_idx):
        node = manager.IndexToNode(from_idx)
        return service_times[node] + matrix[node][manager.IndexToNode(to_idx)]

    full_idx = routing.RegisterTransitCallback(service_cb)

    routing.AddDimension(
        full_idx,
        60,       # max wait slack per stop
        horizon,  # vehicle capacity (total time budget)
        True,     # cumulative from zero
        'Time',
    )
    time_dim = routing.GetDimensionOrDie('Time')
    time_dim.SetGlobalSpanCostCoefficient(10)

    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    params.time_limit.seconds = 5

    solution = routing.SolveWithParameters(params)

    if not solution:
        # Fallback: return original order with correct node-indexed travel times.
        # Nodes: 0=start depot, 1=task0, …, n_tasks=task_{n-1}, (n_tasks+1=end depot)
        arrivals = []
        t = start_min + matrix[0][1]  # start depot → first task travel
        n_task_nodes = n_tasks + 1    # task nodes are 1..n_tasks
        for i, dur in enumerate(task_durations):
            arrivals.append(t)
            next_node = i + 2
            travel = matrix[i + 1][next_node] if next_node <= n_tasks else 0
            t += dur + travel
        return list(range(n_tasks)), arrivals

    # Extract ordered route
    ordered = []
    arrivals = []
    index = routing.Start(0)
    current = start_min

    while not routing.IsEnd(index):
        node = manager.IndexToNode(index)
        if node != 0:
            task_idx = node - 1
            ordered.append(task_idx)
            arrivals.append(current)
            current += task_durations[task_idx]
        next_index = solution.Value(routing.NextVar(index))
        if not routing.IsEnd(next_index):
            next_node = manager.IndexToNode(next_index)
            current += matrix[node][next_node]
        index = next_index

    return ordered, arrivals


# ── Public entry point ────────────────────────────────────────────────────────

async def optimize_routes(technicians: list, google_maps_api_key: Optional[str]) -> list[dict]:
    results = []

    for tech in technicians:
        if not tech.tasks:
            results.append({
                'technician_id': tech.id,
                'ordered_tasks': [],
                'estimated_times': {},
                'total_drive_minutes': 0,
                'mode': 'none',
            })
            continue

        return_loc = tech.return_city if (tech.return_city and tech.return_city != tech.base_city) else ''
        task_locs = [_task_location(t) for t in tech.tasks]
        locations = [tech.base_city] + task_locs + ([return_loc] if return_loc else [])
        durations = [t.duration_minutes for t in tech.tasks]

        if google_maps_api_key:
            matrix = await build_matrix_gmaps(locations, google_maps_api_key)
            mode = 'gmaps'
        else:
            matrix = build_matrix_local(locations)
            mode = 'local'

        ordered_idx, arrivals = solve_route(
            base_city=tech.base_city,
            task_cities=[t.city for t in tech.tasks],
            task_durations=durations,
            matrix=matrix,
            start_time_str=tech.start_time,
            end_time_str=tech.end_time,
            return_city=return_loc,
        )

        ordered_task_ids = [tech.tasks[i].id for i in ordered_idx]
        time_map = {tech.tasks[i].id: min_to_time(arr) for i, arr in zip(ordered_idx, arrivals)}

        # Total drive time (start depot → tasks → end depot)
        total_drive = 0
        prev_node = 0
        for idx in ordered_idx:
            total_drive += matrix[prev_node][idx + 1]
            prev_node = idx + 1
        if return_loc and ordered_idx:
            end_node_idx = len(tech.tasks) + 1  # last row in matrix = return city
            total_drive += matrix[prev_node][end_node_idx]

        results.append({
            'technician_id': tech.id,
            'ordered_tasks': ordered_task_ids,
            'estimated_times': time_map,
            'total_drive_minutes': total_drive,
            'mode': mode,
        })

    return results
