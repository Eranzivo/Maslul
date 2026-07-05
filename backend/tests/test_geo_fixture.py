"""Golden geo parity fixture — the SAME cases tests/zones.test.js asserts on the JS
cityMatchKey run here against the Python _match_key. A JS↔Python drift becomes a
failing test on whichever side broke, instead of a mis-zoned call in a client's calendar."""
import io
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from batch_schedule import _match_key  # noqa: E402

_FX = json.load(io.open(os.path.join(os.path.dirname(__file__), "..", "..",
                                     "tests", "fixtures", "geo-cases.json"),
                        encoding="utf-8"))
_ALIASES = _FX["brain"]["aliases"]


def test_equal_groups_resolve_to_one_key():
    for group in _FX["equal_groups"]:
        keys = {_match_key(n, _ALIASES) for n in group}
        assert len(keys) == 1, f"group {group} split into {keys}"


def test_distinct_pairs_never_merge():
    for a, b in _FX["distinct"]:
        assert _match_key(a, _ALIASES) != _match_key(b, _ALIASES), f"{a} merged with {b}"


def test_no_brain_still_deterministic():
    assert _match_key("תל-אביב", {}) == _match_key("תל אביב", {})
