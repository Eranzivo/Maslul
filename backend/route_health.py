"""Route Health — P1 of the route-intelligence workstream.

Pure arithmetic over a solve the engine already performed: the auditor never
re-implements a constraint (no third door). It compares the ACTUAL tech-day
(tasks + their scheduled times) against the solver's best answer for the same
day (`solve_route_v2` output: ordered/legs/dropped) and emits a 0-100 score,
per-component breakdown, and structured findings. Hebrew rendering happens at
the display layer (JS templates over finding types), keeping this module
pure-data.

This is the ONLY implementation of the health computation — the frontend
displays stored `route_audits` rows and never recomputes. Behavioral contract:
tests/fixtures/health-cases.json (golden fixture, pinned by
backend/tests/test_route_health.py).

Design + weights rationale: outputs/route-intelligence-design_2026-07-09.md.
Fail-open: malformed scheduled times degrade to a partial audit, never a crash;
an empty/unauditable day returns score None (chip hidden), never a fake 100.
"""
from typing import Optional

# System defaults. Tenant override: config.audit.health_weights (knob) — merged
# shallowly, unknown keys ignored. What COUNTS as a violation (window math,
# direction test) is a system invariant and deliberately not configurable.
DEFAULT_WEIGHTS = {
    "excess_drive_per_min": 1.5,
    "backtrack_per_violation": 8,
    "backtrack_cap": 24,
    "backtrack_jitter_min": 2,     # d_base increase <= this is same-area noise, not a zigzag
    "lateness_per_stop": 15,
    "idle_per_5min": 1,
    "idle_cap": 20,
    "idle_free_min": 15,           # per-gap slack below this is operational, not idle
    "overtime_base": 10,
    "overtime_per_min": 1,
    "window_violation_per_stop": 20,
    "reorder_min_saving": 10,      # don't report better_order_exists under this (noise -> trust)
}

BANDS = ((90, "healthy"), (70, "review"))


def band(score: Optional[int]) -> Optional[str]:
    if score is None:
        return None
    for floor, name in BANDS:
        if score >= floor:
            return name
    return "issues"


def _to_min(t) -> Optional[int]:
    """HH:MM -> absolute minutes; None on anything malformed (fail-open)."""
    try:
        h, m = str(t).split(":")
        return int(h) * 60 + int(m)
    except (ValueError, AttributeError, TypeError):
        return None


def compute_health(matrix, tasks, start_time, end_time, breaks=None,
                   route_strategy: str = "flexible", solver=None, weights=None) -> dict:
    """Audit one tech-day. See module docstring.

    matrix: travel-minutes, node 0 = depot, node i+1 = tasks[i] (extra trailing
            return-depot node, if present, is ignored — legs exclude the return
            leg on both the actual and solver sides, keeping totals comparable).
    tasks:  [{duration, window_start, window_end, locked, scheduled_time}] —
            the same v2 shape optimize_routes builds.
    solver: {"ordered": [task idx...], "legs": [min...], "dropped": [idx...]}.

    Returns {"score", "band", "partial", "components", "findings", "actual_order"}.
    """
    w = dict(DEFAULT_WEIGHTS)
    if weights:
        w.update({k: v for k, v in weights.items() if k in DEFAULT_WEIGHTS})
    solver = solver or {}
    breaks = breaks or []
    start_min = _to_min(start_time)
    end_min = _to_min(end_time)

    # ── Actual order = scheduled tasks sorted by time; the rest make it partial ──
    scheduled = []
    for i, t in enumerate(tasks):
        sm = _to_min(t.get("scheduled_time"))
        if sm is not None:
            scheduled.append((sm, i))
    scheduled.sort()
    actual_order = [i for _, i in scheduled]
    partial = len(actual_order) < len(tasks)

    if not actual_order or start_min is None or end_min is None:
        return {"score": None, "band": None, "partial": partial,
                "components": {}, "findings": [], "actual_order": actual_order}

    findings = []
    comp = {}
    brk_windows = [(a, b) for a, b in
                   ((_to_min(x.get("from")), _to_min(x.get("to"))) for x in breaks)
                   if a is not None and b is not None and b > a]

    # ── Walk the actual route: physics vs plan ────────────────────────────────
    # arrival_k = prev completion + travel; the tech honors the plan when it is
    # reachable (service_start = max(arrival, scheduled)), physics wins when not.
    actual_drive = 0
    idle_total = 0
    lateness_stops = 0
    window_violations = 0
    prev_node = 0
    prev_completion = start_min
    last_end = start_min
    for sched_min, i in scheduled:
        node = i + 1
        leg = matrix[prev_node][node]
        actual_drive += leg
        arrival = prev_completion + leg
        service_start = max(arrival, sched_min)
        dur = int(t.get("duration") or 0) if (t := tasks[i]) else 0

        # Idle: plan-imposed wait beyond the free allowance, minus break overlap.
        if sched_min > arrival:
            gap_a, gap_b = arrival, sched_min
            overlap = sum(max(0, min(gap_b, b2) - max(gap_a, b1)) for b1, b2 in brk_windows)
            idle = (gap_b - gap_a) - overlap
            if idle > w["idle_free_min"]:
                idle_total += idle
                findings.append({"type": "idle_gap", "stop": i,
                                 "data": {"idle_min": idle}})

        # Customer-window checks — ARRIVAL semantics: the promise is "the tech
        # arrives between window_start and window_end"; service may run past the
        # end. (The solver is deliberately stricter when PLACING — it requires
        # finishing inside the window — but the auditor must not flag real
        # schedules that keep the arrival promise: Israel's replay showed 10/89
        # legitimate stops flagged under finish-inside semantics, 2026-07-09.)
        ws, we = _to_min(tasks[i].get("window_start")), _to_min(tasks[i].get("window_end"))
        latest_start = we
        violated = ((ws is not None and sched_min < ws) or
                    (latest_start is not None and sched_min > latest_start))
        if violated:
            # The PLAN promises outside the window — a data bug, not a physics risk.
            window_violations += 1
            findings.append({"type": "window_violation", "stop": i,
                             "data": {"scheduled": tasks[i].get("scheduled_time"),
                                      "window_start": tasks[i].get("window_start"),
                                      "window_end": tasks[i].get("window_end")}})
        elif latest_start is not None and service_start > latest_start:
            # Plan looks fine but travel/service physics pushes the start too late.
            lateness_stops += 1
            findings.append({"type": "lateness_risk", "stop": i,
                             "data": {"late_by_min": service_start - latest_start}})

        prev_completion = service_start + dur
        last_end = prev_completion
        prev_node = node

    # ── Backtracking on the ACTUAL order (mirror of the solver's monotone test) ──
    backtrack_count = 0
    if route_strategy in ("far_to_near", "nearest_first"):
        d_base = [matrix[0][i + 1] for i in range(len(tasks))]
        for k in range(1, len(actual_order)):
            a, b = actual_order[k - 1], actual_order[k]
            delta = d_base[b] - d_base[a]
            outward = delta > w["backtrack_jitter_min"]
            inward = delta < -w["backtrack_jitter_min"]
            if (route_strategy == "far_to_near" and outward) or \
               (route_strategy == "nearest_first" and inward):
                backtrack_count += 1
                findings.append({"type": "backtrack", "stop": b,
                                 "data": {"from_base_min": d_base[a], "to_base_min": d_base[b]}})

    # ── Solver comparison (skipped when routes aren't comparable) ─────────────
    solver_drive = None
    excess = 0
    dropped = solver.get("dropped") or []
    comparable = (not dropped) and not partial and \
        len(solver.get("ordered") or []) == len(actual_order)
    if comparable:
        solver_drive = sum(solver.get("legs") or [])
        excess = max(0, actual_drive - solver_drive)
        if excess >= w["reorder_min_saving"]:
            findings.append({"type": "better_order_exists", "stop": None,
                             "data": {"saving_min": excess,
                                      "solver_order": list(solver["ordered"])}})
        # Solver-endorsed order: when the actual order IS the solver's best, any
        # zigzag in it was forced by windows/locks — no better direction-respecting
        # order exists, so flagging it is noise (Israel replay 2026-07-09: the
        # engine's own auto-sequenced days were flagging their unavoidable jumps).
        if backtrack_count and list(solver.get("ordered") or []) == actual_order:
            findings = [f for f in findings if f["type"] != "backtrack"]
            backtrack_count = 0
    else:
        partial = True

    # ── Overtime ──────────────────────────────────────────────────────────────
    overtime_min = max(0, last_end - end_min)
    if overtime_min:
        findings.append({"type": "overtime", "stop": None,
                         "data": {"overtime_min": overtime_min}})

    # ── Score ─────────────────────────────────────────────────────────────────
    excess_pts = excess * w["excess_drive_per_min"]
    backtrack_pts = min(backtrack_count * w["backtrack_per_violation"], w["backtrack_cap"])
    lateness_pts = lateness_stops * w["lateness_per_stop"]
    idle_pts = min((idle_total // 5) * w["idle_per_5min"], w["idle_cap"])
    overtime_pts = (w["overtime_base"] + overtime_min * w["overtime_per_min"]) if overtime_min else 0
    window_pts = window_violations * w["window_violation_per_stop"]
    total = excess_pts + backtrack_pts + lateness_pts + idle_pts + overtime_pts + window_pts
    score = max(0, min(100, int(100 - total + 0.5)))

    comp.update({
        "actual_drive_min": actual_drive,
        "solver_drive_min": solver_drive,
        "excess_drive_min": excess, "excess_drive_pts": excess_pts,
        "backtrack_count": backtrack_count, "backtrack_pts": backtrack_pts,
        "lateness_stops": lateness_stops, "lateness_pts": lateness_pts,
        "idle_min": idle_total, "idle_pts": idle_pts,
        "overtime_min": overtime_min, "overtime_pts": overtime_pts,
        "window_violations": window_violations, "window_pts": window_pts,
    })
    return {"score": score, "band": band(score), "partial": partial,
            "components": comp, "findings": findings, "actual_order": actual_order}


def build_audit_rows(tenant_id: str, date_str: str, techs, results, trigger: str) -> list:
    """Package optimize_routes results into route_audits rows (pure, duck-typed:
    techs need .id and .tasks[.id/.city/.scheduled_time] — pydantic or namespace).
    Unauditable days (health None / score None) get NO row — an empty day is not
    stored as a fake signal. tenant_id must already be VERIFIED by the caller
    (JWT-resolved, never client-supplied)."""
    if trigger not in ("change", "nightly", "manual"):
        trigger = "manual"
    rows = []
    for tech, res in zip(techs, results):
        h = res.get("health")
        if not h or h.get("score") is None:
            continue
        by_id = {str(t.id): t for t in tech.tasks}
        snapshot = [{"task_id": tid,
                     "city": getattr(by_id[tid], "city", None),
                     "time": getattr(by_id[tid], "scheduled_time", None)}
                    for tid in h.get("actual_order_ids", []) if tid in by_id]
        rows.append({
            "tenant_id": tenant_id,
            "technician_id": str(tech.id),
            "date": date_str,
            "score": h["score"],
            "band": h["band"],
            "partial": h["partial"],
            "components": h["components"],
            "findings": h["findings"],
            "route_snapshot": snapshot,
            "solver_best": {"order": res.get("ordered_tasks", []),
                            "drive_min": res.get("total_drive_minutes")},
            "trigger": trigger,
        })
    return rows
