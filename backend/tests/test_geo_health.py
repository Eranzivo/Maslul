"""Pure tests for the Geo Health report (Slice 1). No network — resolve/match_key are stubs
mirroring the real backend seams. Run: `python -m pytest tests/test_geo_health.py -q` in backend/."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import geo_health  # noqa: E402


def _resolve(known):
    """city -> coords|None, from a dict of known places."""
    return lambda c: known.get(c)


def _mk(mapping):
    """match_key stub: mapping.get(c, c) — identity unless a variant is declared."""
    return lambda c: mapping.get(c, c)


def test_unresolved_only():
    rep = geo_health.build_health_report(
        [("אשקלון", 3), ("חרב", 4)],
        {"אשקלון"}, _resolve({"אשקלון": (31.66, 34.57)}), _mk({}))
    assert rep["summary"]["unresolved"] == 1
    assert rep["summary"]["out_of_zone"] == 0
    assert rep["unresolved"][0] == {"city": "חרב", "calls": 4}


def test_out_of_zone_only():
    known = {"אשקלון": (31.66, 34.57), "טבריה": (32.79, 35.53)}
    rep = geo_health.build_health_report(
        [("אשקלון", 2), ("טבריה", 1)], {"אשקלון"}, _resolve(known), _mk({}))
    assert rep["summary"]["out_of_zone"] == 1
    assert rep["summary"]["unresolved"] == 0
    ooz = rep["out_of_zone"][0]
    assert ooz["city"] == "טבריה" and ooz["lat"] == 32.79 and ooz["lon"] == 35.53


def test_both_and_sorted_desc_by_calls():
    known = {"א": (1, 1), "ב": (2, 2)}  # ב resolves but is out of zone
    rep = geo_health.build_health_report(
        [("א", 1), ("ב", 5), ("חרב", 2), ("ריק", 9)],
        {"א"}, _resolve(known), _mk({}))
    assert [r["city"] for r in rep["unresolved"]] == ["ריק", "חרב"]   # 9, 2 desc
    assert rep["out_of_zone"][0]["city"] == "ב"
    assert rep["summary"]["attention"] == 3
    assert rep["summary"]["checked_cities"] == 4


def test_all_clear():
    rep = geo_health.build_health_report(
        [("אשקלון", 4)], {"אשקלון"}, _resolve({"אשקלון": (1, 1)}), _mk({}))
    assert rep["summary"]["attention"] == 0
    assert rep["summary"]["checked_cities"] == 1


def test_empty_zone_keys_skips_out_of_zone():
    # fail-open: coverage unknown ⇒ never invent an out-of-zone gap.
    rep = geo_health.build_health_report(
        [("טבריה", 1)], set(), _resolve({"טבריה": (32.79, 35.53)}), _mk({}))
    assert rep["summary"]["out_of_zone"] == 0
    assert rep["summary"]["unresolved"] == 0


def test_blank_cities_ignored():
    rep = geo_health.build_health_report(
        [("", 3), ("   ", 1)], {"x"}, _resolve({}), _mk({}))
    assert rep["summary"]["checked_cities"] == 0
    assert rep["summary"]["attention"] == 0


def test_match_key_used_for_zone_membership():
    # A spelling variant whose match_key lands in the zone must NOT flag out-of-zone.
    rep = geo_health.build_health_report(
        [("קריית שמונה", 2)], {"קרית שמונה"},
        _resolve({"קריית שמונה": (33.2, 35.57)}),
        _mk({"קריית שמונה": "קרית שמונה"}))
    assert rep["summary"]["out_of_zone"] == 0
    assert rep["summary"]["attention"] == 0
