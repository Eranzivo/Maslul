import math
import httpx
from typing import Optional
from ortools.constraint_solver import routing_enums_pb2, pywrapcp
from cities import get_coords
import route_cache
import geo_resolver
import route_health


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
    hit = geo_resolver.resolve(loc)   # shared brain (geo_places + aliases) → cities.py
    if hit is not None:
        return hit
    return get_coords(loc)             # TLV last-resort keeps the matrix solvable


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


# Telemetry: elements actually fetched from Google by the LAST optimize_routes call.
# Read by main.py to charge the daily quota for real spend only (cache hits are free).
# Single-worker telemetry — a concurrent-request race only skews the count, never spend.
LAST_GOOGLE_ELEMENTS = 0


async def build_matrix_cached(locations: list[str], api_key: str, service_key: str) -> list[list[int]]:
    """Cache-first travel matrix: reuse cached legs, fetch only misses from Google
    (trust-checked before storing), fall back to haversine for anything still missing.
    A fully-warm cache performs zero Google calls."""
    global LAST_GOOGLE_ELEMENTS
    keys = [route_cache.norm_key(l) for l in locations]
    hits, misses = route_cache.split_hits_misses(locations, service_key)
    n = len(locations)
    matrix = [[0] * n for _ in range(n)]
    new_rows = []
    # Fetch a Google matrix only when something is actually missing.
    gmatrix = None
    if misses and api_key:
        gmatrix = await build_matrix_gmaps(locations, api_key)
        LAST_GOOGLE_ELEMENTS += n * n
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            pair = (keys[i], keys[j])
            if pair in hits:
                matrix[i][j] = hits[pair]
                continue
            lat1, lon1 = _parse_loc(locations[i])
            lat2, lon2 = _parse_loc(locations[j])
            straight_km = haversine_km(lat1, lon1, lat2, lon2)
            hav = km_to_minutes(straight_km)
            if gmatrix is not None and route_cache.is_trustworthy(gmatrix[i][j], straight_km):
                matrix[i][j] = gmatrix[i][j]
                new_rows.append({"from_key": keys[i], "to_key": keys[j],
                                 "drive_minutes": gmatrix[i][j], "source": "google"})
            else:
                matrix[i][j] = hav
    route_cache.put_cached(new_rows, service_key)
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

    if two_depot:
        manager = pywrapcp.RoutingIndexManager(n_nodes, 1, [0], [end_node])
    else:
        manager = pywrapcp.RoutingIndexManager(n_nodes, 1, 0)
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


def solve_route_v2(matrix, tasks, start_time_str, end_time_str, breaks,
                   return_node: bool = False, route_strategy: str = "flexible"):
    """Constraint-aware single-vehicle solver (Plan B2).

    matrix: (n_tasks+1[+1]) square travel-minutes matrix, node 0 = start depot,
            nodes 1..n = tasks (same order as `tasks`), optional last node = end depot.
    tasks:  [{duration, window_start, window_end, locked, scheduled_time}]
    breaks: [{"from": "12:00", "to": "13:00"}] — modeled as zero-travel pinned pseudo-tasks.

    Semantics:
      - locked + scheduled_time → pinned to that exact start time, never dropped
      - window_start/window_end → hard customer window; the solver may WAIT to honor it
      - flexible tasks get a disjunction: an over-full day DROPS them (returned in
        "dropped") instead of failing the whole solve
      - arrivals come from the Time dimension (includes solver-inserted waiting)

    Returns {"ordered": [task_idx...], "arrivals": [abs-minute...],
             "dropped": [task_idx...], "legs": [drive-min-from-prev-stop...],
             "conflict": bool (locked tasks were mutually infeasible)}.
    """
    n_tasks = len(tasks)
    start_min = time_to_min(start_time_str)
    end_min = time_to_min(end_time_str)
    if n_tasks == 0:
        return {"ordered": [], "arrivals": [], "dropped": [], "legs": [], "conflict": False}

    # ── Append break pseudo-nodes: zero travel to/from everywhere, pinned window ──
    brk_specs = [{"from_min": time_to_min(b["from"]), "to_min": time_to_min(b["to"])} for b in (breaks or [])]
    base_n = len(matrix)
    n_nodes = base_n + len(brk_specs)
    full = [row[:] + [0] * len(brk_specs) for row in matrix]
    for _ in brk_specs:
        full.append([0] * n_nodes)

    # ── Cost vs Time matrices ─────────────────────────────────────────────────
    # cost_m drives the objective (what we minimize); time_m drives the work-hours
    # dimension. They differ on the return-to-base leg:
    #   flexible/nearest_first, no return city → day ends at the last client:
    #       return arcs are zero in BOTH (current B2 behavior).
    #   far_to_near, no return city → the tech still DRIVES HOME (unpaid): the return
    #       leg counts in COST (so the tour naturally ends near base ⇒ far→near) but
    #       NOT in work-hours. Plus a tiny depot-departure bias to break exact ties
    #       toward starting far (closed-tour costs are direction-symmetric).
    time_m = [row[:] for row in full]
    cost_m = [row[:] for row in full]
    if not return_node:
        for r in range(n_nodes):
            time_m[r][0] = 0
        if route_strategy == "far_to_near":
            depot_d = [full[0][j] for j in range(1, n_tasks + 1)]
            max_d = max(depot_d) or 1
            for j in range(1, n_tasks + 1):
                closeness = (max_d - full[0][j]) / max_d  # 1 = nearest, 0 = farthest
                cost_m[0][j] += int(round(3 * closeness))  # ≤3 min nudge — tie-break only
        else:
            for r in range(n_nodes):
                cost_m[r][0] = 0

    # ── Direction enforcement (scheduling-rules.md priority #1 > fuel #4) ──────────
    # far_to_near must NEVER drive outward (farther from base) task→task; nearest_first
    # is the exact mirror — never drive back INWARD (closer to base) task→task. Either
    # violation is the backtrack/zigzag the rules forbid ("better to start later than to
    # far-near-far"). A dominant per-arc penalty makes a clean monotone order beat any
    # drive-time saving, so the knob is genuinely enforced for BOTH strategies (2026-07-05:
    # nearest_first was previously solver-cosmetic — min-drive could start far on
    # two-branch geometry). The penalty stays well below the 100000 disjunction drop
    # penalty, so direction never forces a task to be dropped — fail-open. Equal-distance
    # stops (same city) are unpenalized → they stay clustered. flexible is unaffected.
    if route_strategy in ("far_to_near", "nearest_first"):
        DIRECTION_PENALTY = 10000
        d_base = [full[0][k] for k in range(base_n)]  # node 0 = base depot
        for i in range(1, n_tasks + 1):
            for j in range(1, n_tasks + 1):
                if i == j:
                    continue
                violates = (d_base[j] > d_base[i]) if route_strategy == "far_to_near" \
                    else (d_base[j] < d_base[i])
                if violates:
                    cost_m[i][j] += DIRECTION_PENALTY

    if return_node:
        manager = pywrapcp.RoutingIndexManager(n_nodes, 1, [0], [base_n - 1])
    else:
        manager = pywrapcp.RoutingIndexManager(n_nodes, 1, 0)
    routing = pywrapcp.RoutingModel(manager)

    def node_duration(node):
        if 1 <= node <= n_tasks:
            return tasks[node - 1]["duration"]
        if node >= base_n:  # break pseudo-node
            spec = brk_specs[node - base_n]
            return spec["to_min"] - spec["from_min"]
        return 0

    def cost_cb(fi, ti):
        f, t = manager.IndexToNode(fi), manager.IndexToNode(ti)
        return node_duration(f) + cost_m[f][t]

    def time_cb(fi, ti):
        f, t = manager.IndexToNode(fi), manager.IndexToNode(ti)
        return node_duration(f) + time_m[f][t]

    cost_idx = routing.RegisterTransitCallback(cost_cb)
    routing.SetArcCostEvaluatorOfAllVehicles(cost_idx)
    time_idx = routing.RegisterTransitCallback(time_cb)
    horizon = max(1, end_min - start_min)
    routing.AddDimension(time_idx, horizon, horizon, False, 'Time')  # slack = waiting allowed
    time_dim = routing.GetDimensionOrDie('Time')

    # ── Per-task constraints (Time cumul is minutes-from-day-start) ──
    for i, t in enumerate(tasks):
        idx = manager.NodeToIndex(i + 1)
        lo, hi = 0, max(0, horizon - t["duration"])
        if t.get("window_start"):
            lo = max(lo, time_to_min(t["window_start"]) - start_min)
        if t.get("window_end"):
            # must START early enough to finish inside the window
            hi = min(hi, time_to_min(t["window_end"]) - start_min - t["duration"])
        if t.get("locked") and t.get("scheduled_time"):
            pin = time_to_min(t["scheduled_time"]) - start_min
            lo = hi = max(0, pin)
        if hi < lo:
            hi = lo  # impossible window → keep model solvable; disjunction drops it
        time_dim.CumulVar(idx).SetRange(lo, hi)
        if not (t.get("locked") and t.get("scheduled_time")):
            # Droppable: huge penalty so dropping is a last resort, never an unsolvable model
            routing.AddDisjunction([idx], 100000)

    # Break pseudo-nodes: mandatory, pinned to their window start
    for b_i, spec in enumerate(brk_specs):
        idx = manager.NodeToIndex(base_n + b_i)
        pin = max(0, spec["from_min"] - start_min)
        time_dim.CumulVar(idx).SetRange(pin, pin)

    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    params.time_limit.seconds = 5
    solution = routing.SolveWithParameters(params)

    if not solution:
        # Rare with disjunctions — e.g. two locked tasks that physically conflict.
        locked_idx = [i for i, t in enumerate(tasks) if t.get("locked") and t.get("scheduled_time")]
        flex_idx = [i for i in range(n_tasks) if i not in locked_idx]
        return {"ordered": locked_idx,
                "arrivals": [time_to_min(tasks[i]["scheduled_time"]) for i in locked_idx],
                "dropped": flex_idx, "legs": [0] * len(locked_idx), "conflict": True}

    ordered, arrivals, legs = [], [], []
    index = routing.Start(0)
    prev_node = manager.IndexToNode(index)
    while not routing.IsEnd(index):
        node = manager.IndexToNode(index)
        if 1 <= node <= n_tasks:
            ordered.append(node - 1)
            # Arrival from the Time dimension — includes solver-inserted waiting
            arrivals.append(start_min + solution.Value(time_dim.CumulVar(index)))
            legs.append(full[prev_node][node])
            prev_node = node
        index = solution.Value(routing.NextVar(index))

    visited = set(ordered)
    dropped = [i for i in range(n_tasks) if i not in visited]
    return {"ordered": ordered, "arrivals": arrivals, "dropped": dropped, "legs": legs, "conflict": False}


# ── Public entry point ────────────────────────────────────────────────────────

def _health_for_tech(tech, v2_tasks, matrix, r, route_strategy, weights):
    """Route Health from the solve we ALREADY did — pure arithmetic, no extra
    API cost (route-intelligence P1). Index-based findings/orders are mapped to
    task ids here (this is the only place that knows both). Fail-open: any error
    returns None rather than breaking the optimize path."""
    try:
        h = route_health.compute_health(
            matrix, v2_tasks, tech.start_time, tech.end_time,
            breaks=getattr(tech, "breaks", []) or [],
            route_strategy=route_strategy,
            solver={"ordered": r["ordered"], "legs": r["legs"], "dropped": r["dropped"]},
            weights=weights)
        ids = [t.id for t in tech.tasks]
        for f in h["findings"]:
            if f.get("stop") is not None:
                f["task_id"] = ids[f["stop"]]
            so = (f.get("data") or {}).get("solver_order")
            if so:
                f["data"]["solver_order"] = [ids[i] for i in so]
        h["actual_order_ids"] = [ids[i] for i in h["actual_order"]]
        return h
    except Exception as e:
        print(f"[health] compute failed for tech {tech.id}: {e}")
        return None


async def optimize_routes(technicians: list, google_maps_api_key: Optional[str], service_key: str = "",
                          route_strategy: str = "flexible", health_weights: Optional[dict] = None) -> list[dict]:
    global LAST_GOOGLE_ELEMENTS
    LAST_GOOGLE_ELEMENTS = 0
    await geo_resolver.ensure_loaded(service_key)  # load the shared brain once (fail-open)
    results = []

    for tech in technicians:
        if not tech.tasks:
            results.append({
                'technician_id': tech.id,
                'ordered_tasks': [],
                'estimated_times': {},
                'total_drive_minutes': 0,
                'mode': 'none',
                'health': None,
            })
            continue

        return_loc = tech.return_city if (tech.return_city and tech.return_city != tech.base_city) else ''
        task_locs = [_task_location(t) for t in tech.tasks]
        locations = [tech.base_city] + task_locs + ([return_loc] if return_loc else [])
        durations = [t.duration_minutes for t in tech.tasks]

        if service_key:
            # Cache-first: cached legs are reused even when Google is unavailable/quota-blocked
            # (api_key None → misses fall back to haversine, hits still use real drive times).
            matrix = await build_matrix_cached(locations, google_maps_api_key, service_key)
            mode = 'gmaps-cached' if google_maps_api_key else 'local-cached'
        elif google_maps_api_key:
            matrix = await build_matrix_gmaps(locations, google_maps_api_key)
            mode = 'gmaps'
        else:
            matrix = build_matrix_local(locations)
            mode = 'local'

        v2_tasks = [{
            "duration": t.duration_minutes,
            "window_start": getattr(t, "window_start", None),
            "window_end": getattr(t, "window_end", None),
            "locked": getattr(t, "locked", False),
            "scheduled_time": t.scheduled_time,
        } for t in tech.tasks]
        r = solve_route_v2(matrix, v2_tasks, tech.start_time, tech.end_time,
                           breaks=getattr(tech, "breaks", []) or [],
                           return_node=bool(return_loc),
                           route_strategy=route_strategy)
        ordered_idx, arrivals = r["ordered"], r["arrivals"]

        ordered_task_ids = [tech.tasks[i].id for i in ordered_idx]
        time_map = {tech.tasks[i].id: min_to_time(arr) for i, arr in zip(ordered_idx, arrivals)}

        # Per-stop decision trace: where the tech came from + how long the drive was.
        trace = {}
        for k, i in enumerate(ordered_idx):
            prev_city = tech.tasks[ordered_idx[k - 1]].city if k > 0 else tech.base_city
            trace[tech.tasks[i].id] = {"prev": prev_city, "drive_minutes": r["legs"][k]}

        results.append({
            'technician_id': tech.id,
            'ordered_tasks': ordered_task_ids,
            'estimated_times': time_map,
            'dropped_tasks': [tech.tasks[i].id for i in r["dropped"]],
            'conflict': r.get("conflict", False),
            'trace': trace,
            'total_drive_minutes': sum(r["legs"]),
            'mode': mode,
            'health': _health_for_tech(tech, v2_tasks, matrix, r, route_strategy, health_weights),
        })

    return results
