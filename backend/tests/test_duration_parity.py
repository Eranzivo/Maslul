"""Job-duration chain parity: batch _effective_duration must match the live JS
effectiveDuration for every case in the shared golden fixture, so the two engine
doors can never drift. Chain: tech override > category time > tenant regular > 30.
There is NO per-call override by design (durations are a per-tenant category-level
setup decision).
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import batch_schedule as bs  # noqa: E402

_FX = json.load(io.open(
    os.path.join(os.path.dirname(__file__), "..", "..", "tests", "fixtures", "duration-cases.json"),
    encoding="utf-8",
))


def test_effective_duration_matches_shared_fixture():
    for c in _FX["cases"]:
        tech = {"duration_overrides": c["techOverrides"]}
        config = {"defaults": {"regular_job_minutes": c["regular"]}}
        got = bs._effective_duration(c["catId"], tech, c["catTimes"], config)
        assert got == c["expect"], f'{c["why"]}: expected {c["expect"]}, got {got}'


def test_effective_duration_safe_on_missing_config():
    # No config at all → absolute floor 30 (never throws in the batch loop).
    assert bs._effective_duration("c1", {}, {}, None) == 30
