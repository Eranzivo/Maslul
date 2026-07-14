"""Cross-tenant brain P2 — tenant-learned leg aggregation (route_observations → median per leg,
gated by min_samples). Pure aggregation is tested directly; the REST fetch is fail-open."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import route_observations as ro


def test_median_per_leg_with_enough_samples():
    rows = [
        {"from_key": "עכו", "to_key": "חיפה", "observed_min": 20},
        {"from_key": "עכו", "to_key": "חיפה", "observed_min": 30},
        {"from_key": "עכו", "to_key": "חיפה", "observed_min": 25},
    ]
    assert ro.aggregate_legs(rows, min_samples=3) == {("עכו", "חיפה"): 25}


def test_below_min_samples_excluded():
    rows = [
        {"from_key": "עכו", "to_key": "חיפה", "observed_min": 20},
        {"from_key": "עכו", "to_key": "חיפה", "observed_min": 30},
    ]
    assert ro.aggregate_legs(rows, min_samples=3) == {}


def test_median_robust_to_outlier():
    rows = [{"from_key": "A", "to_key": "B", "observed_min": m} for m in (18, 20, 22, 240)]
    # median of [18,20,22,240] = 21 → outlier does not blow up the learned duration
    assert ro.aggregate_legs(rows, min_samples=3) == {("A", "B"): 21}


def test_skips_self_and_bad_rows():
    rows = [
        {"from_key": "A", "to_key": "A", "observed_min": 10},   # self-leg
        {"from_key": "A", "to_key": "B", "observed_min": 0},    # non-positive
        {"from_key": "A", "to_key": "B", "observed_min": "x"},  # unparseable
        {"to_key": "B", "observed_min": 10},                    # missing from_key
    ]
    assert ro.aggregate_legs(rows, min_samples=1) == {}


def test_get_learned_legs_fail_open_without_key():
    assert ro.get_learned_legs("tenant-1", "") == {}
    assert ro.get_learned_legs("", "svc") == {}
