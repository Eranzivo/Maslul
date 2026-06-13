import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from batch_schedule import optimize_day, resolve_route_strategy

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
