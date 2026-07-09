"""Route Health (P1 route-intelligence): compute_health is pinned to the golden
fixture tests/fixtures/health-cases.json. Python is the ONLY implementation —
the JS side displays stored route_audits rows and never recomputes — so this
fixture is the single behavioral contract (and becomes the parity contract if a
JS preview computation is ever added).

Score = 100 - weighted penalties (excess drive vs solver best, backtracking,
lateness risk, idle gaps, overtime, window violations), clamped [0,100].
Design: outputs/route-intelligence-design_2026-07-09.md.
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import route_health as rh  # noqa: E402

_FX = json.load(io.open(
    os.path.join(os.path.dirname(__file__), "..", "..", "tests", "fixtures", "health-cases.json"),
    encoding="utf-8",
))


def _run_case(c):
    return rh.compute_health(
        matrix=c.get("matrix", _FX["matrix_default"]),
        tasks=c["tasks"],
        start_time=c["start"],
        end_time=c["end"],
        breaks=c.get("breaks", []),
        route_strategy=c["route_strategy"],
        solver=c.get("solver", _FX["solver_default"]),
        weights=c.get("weights"),
    )


def test_fixture_scores_and_partial():
    for c in _FX["cases"]:
        got = _run_case(c)
        exp = c["expect"]
        assert got["score"] == exp["score"], \
            f'{c["name"]}: score {got["score"]} != {exp["score"]} ({c["why"]}) components={got["components"]}'
        assert got["partial"] == exp["partial"], \
            f'{c["name"]}: partial {got["partial"]} != {exp["partial"]}'


def test_fixture_finding_types():
    for c in _FX["cases"]:
        got = _run_case(c)
        got_types = sorted(f["type"] for f in got["findings"])
        assert got_types == sorted(c["expect"]["finding_types"]), \
            f'{c["name"]}: findings {got_types} != {sorted(c["expect"]["finding_types"])}'


def test_fixture_pinned_components():
    for c in _FX["cases"]:
        pins = c["expect"].get("components") or {}
        if not pins:
            continue
        got = _run_case(c)["components"]
        for k, v in pins.items():
            assert got.get(k) == v, f'{c["name"]}: components[{k}] {got.get(k)} != {v}'


def test_bands():
    assert rh.band(95) == "healthy"
    assert rh.band(90) == "healthy"
    assert rh.band(89) == "review"
    assert rh.band(70) == "review"
    assert rh.band(69) == "issues"
    assert rh.band(0) == "issues"
    assert rh.band(None) is None


def test_weights_merge_never_mutates_defaults():
    before = dict(rh.DEFAULT_WEIGHTS)
    rh.compute_health(matrix=_FX["matrix_default"], tasks=[], start_time="08:00",
                      end_time="17:00", breaks=[], route_strategy="flexible",
                      solver=_FX["solver_default"],
                      weights={"backtrack_cap": 1})
    assert rh.DEFAULT_WEIGHTS == before


def test_findings_reference_task_indices():
    # backtrack_and_excess: the backtrack finding must point at the offending stop
    # (task index 1 = B, the up-jump target), and better_order_exists carries the saving.
    c = next(x for x in _FX["cases"] if x["name"] == "backtrack_and_excess")
    got = _run_case(c)
    bt = [f for f in got["findings"] if f["type"] == "backtrack"]
    assert bt and bt[0]["stop"] == 1, f'backtrack stop: {bt}'
    bo = [f for f in got["findings"] if f["type"] == "better_order_exists"]
    assert bo and bo[0]["data"]["saving_min"] == 20
    assert bo[0]["data"]["solver_order"] == [0, 1, 2]


def test_malformed_inputs_fail_open():
    # A task with a junk scheduled_time must not crash the audit — it is treated
    # as unscheduled (partial), the day still gets a score from the valid subset.
    got = rh.compute_health(
        matrix=_FX["matrix_default"],
        tasks=[{"duration": 30, "scheduled_time": "08:40"},
               {"duration": 30, "scheduled_time": "garbage"},
               {"duration": 30, "scheduled_time": None}],
        start_time="08:00", end_time="17:00", breaks=[],
        route_strategy="far_to_near", solver=_FX["solver_default"])
    assert got["partial"] is True
    assert got["score"] is not None
