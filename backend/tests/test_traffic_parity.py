"""routing.traffic_mode + time-bucket parity (cross-tenant brain P0): the batch
resolve_traffic_mode/traffic_bucket must match the live JS resolveTrafficMode/trafficBucket
for every case in the shared golden fixture, so any future bucket-aware optimization behaves
identically on both engine doors. Default 'off' ⇒ 'static' ⇒ zero behavior change today.
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import batch_schedule as bs  # noqa: E402

_FX = json.load(io.open(
    os.path.join(os.path.dirname(__file__), "..", "..", "tests", "fixtures", "traffic-cases.json"),
    encoding="utf-8",
))


def test_traffic_mode_matches_shared_fixture():
    for c in _FX["mode_cases"]:
        got = bs.resolve_traffic_mode(c["config"])
        assert got == c["expect"], f'mode {c["config"]}: expected {c["expect"]}, got {got}'


def test_traffic_bucket_matches_shared_fixture():
    for c in _FX["bucket_cases"]:
        got = bs.traffic_bucket(c["mode"], c["hhmm"])
        assert got == c["expect"], f'bucket {c["mode"]}@{c["hhmm"]}: expected {c["expect"]}, got {got}'
