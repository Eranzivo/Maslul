import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from batch_schedule import optimize_day, resolve_route_strategy, _assignment_score
from cities import resolve_coords, get_coords


def test_resolve_coords_locates_known_and_flags_unknown():
    # real settlements must resolve (they were silently TLV-guessed before)
    assert resolve_coords('יקנעם') is not None
    assert resolve_coords('באר יעקב') is not None
    assert resolve_coords('קרית חיים') is not None
    # genuinely unlocatable → None so the caller can flag it (never guess)
    assert resolve_coords('חרב') is None
    assert resolve_coords('עיר דמיונית 999') is None
    assert resolve_coords('') is None


def test_added_settlements_are_not_tel_aviv_fallback():
    tlv = (32.0853, 34.7818)
    for c in ['יקנעם', 'קרית חיים', 'מרחביה', 'נווה דניאל', 'בני דקלים', 'שמשית']:
        assert get_coords(c) != tlv, f'{c} still falls back to Tel Aviv'


# ── Fluid workload balance ────────────────────────────────────────────────────
# Greedy simulation that mirrors run_batch_schedule's pick: each task goes to the
# covering tech-day with the highest _assignment_score. All tasks here are the same
# city (the "8 jobs in one city" case), spread across `n_days` covering tech-days.
def _simulate(n_tasks, n_days, balance_conf, max_daily=9):
    load = [0] * n_days
    city = [0] * n_days
    for _ in range(n_tasks):
        best, best_score = None, None
        for d in range(n_days):
            if load[d] >= max_daily:
                continue
            s = _assignment_score(load[d], city[d], balance_conf)
            if best_score is None or s > best_score:
                best_score, best = s, d
        load[best] += 1
        city[best] += 1
    return sorted(load, reverse=True)


def test_balance_off_packs_same_city_onto_one_day():
    # Default behavior must be unchanged: fill-first packs the first covering day.
    assert _simulate(8, 2, None) == [8, 0]
    assert _simulate(8, 2, {"enabled": False}) == [8, 0]


def test_balance_on_splits_evenly_and_fluidly():
    # Fluid even spread that adapts to the week's count — Israel's examples exactly.
    assert _simulate(8, 2, {"enabled": True}) == [4, 4]
    assert _simulate(7, 2, {"enabled": True}) == [4, 3]
    assert _simulate(6, 2, {"enabled": True}) == [3, 3]


def test_balance_on_spreads_across_three_covering_days():
    assert _simulate(9, 3, {"enabled": True}) == [3, 3, 3]
    assert _simulate(8, 3, {"enabled": True}) == [3, 3, 2]


def test_balance_respects_max_daily_cap():
    # Even with balance off, a day can't exceed max_daily — overflow lands on day 2.
    assert _simulate(12, 2, None, max_daily=9) == [9, 3]


# 0=depot, 1=A (near, depot dist 10), 2=B (far, depot dist 30).
# Closed-tour costs are direction-symmetric (10+20+30 == 30+20+10), so the
# strategy alone decides the order. This is the exact PureWater far→near case.
M = [[0, 10, 30], [10, 0, 20], [30, 20, 0]]


def test_far_to_near_orders_far_first():
    # task index 1 = node 2 = farthest from depot → must come first under far_to_near
    ordered, arrivals, dropped = optimize_day(M, [30, 30], "07:00", "18:00",
                                              return_node=False, route_strategy="far_to_near")
    assert ordered[0] == 1
    assert dropped == []
    assert len(arrivals) == 2


def test_flexible_orders_near_first():
    # flexible ends at the last client → near-first is the cheaper open tour
    ordered, _, _ = optimize_day(M, [30, 30], "07:00", "18:00",
                                 return_node=False, route_strategy="flexible")
    assert ordered[0] == 0


def test_overfull_day_drops_not_fails():
    # 60-min day, two 45-min jobs → only one fits; batch must drop, never crash
    ordered, _, dropped = optimize_day(M, [45, 45], "07:00", "08:00",
                                       return_node=False, route_strategy="flexible")
    assert len(ordered) == 1
    assert len(dropped) == 1


def test_resolve_route_strategy_defaults_to_flexible():
    # Absent config must NEVER default to far_to_near (that is PureWater-specific).
    assert resolve_route_strategy(None) == "flexible"
    assert resolve_route_strategy({}) == "flexible"
    assert resolve_route_strategy({"scheduling": {}}) == "flexible"


def test_resolve_route_strategy_honors_explicit_and_legacy():
    assert resolve_route_strategy({"scheduling": {"route_strategy": "far_to_near"}}) == "far_to_near"
    assert resolve_route_strategy({"scheduling": {"route_strategy": "nearest_first"}}) == "nearest_first"
    assert resolve_route_strategy({"scheduling": {"route_logic": True}}) == "far_to_near"
    assert resolve_route_strategy({"scheduling": {"route_logic": False}}) == "flexible"
