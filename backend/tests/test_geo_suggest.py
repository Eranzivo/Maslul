"""Tests for geo_suggest (Slice 2). Golden fixture drives the confidence tiers; unit tests
cover the resolve→fuzz ladder and edge cases. Run: `python -m pytest tests/test_geo_suggest.py -q`."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import geo_suggest  # noqa: E402

_FIX = os.path.join(os.path.dirname(__file__), "fixtures", "geo-suggest-cases.json")


def _load():
    with open(_FIX, encoding="utf-8") as f:
        return json.load(f)


def test_golden_suggest_cases():
    data = _load()
    cands = data["candidates"]
    for c in data["cases"]:
        r = geo_suggest.suggest(c["raw"], cands)
        assert r["status"] == c["status"], (c["raw"], r)
        assert r["auto_ok"] == c["auto_ok"], (c["raw"], r)
        if "match" in c:
            assert r["match"] == c["match"], (c["raw"], r)


def test_resolve_short_circuits_before_fuzz():
    # An authoritative hit is 'resolved' and never fuzzed.
    r = geo_suggest.resolve_or_suggest("תל אביב", ["נהריה"], {}, lambda n: (32.07, 34.78))
    assert r["status"] == "resolved"
    assert r["coords"] == [32.07, 34.78]
    assert r["auto_ok"] is True


def test_resolve_miss_falls_to_suggest():
    r = geo_suggest.resolve_or_suggest("נהרייה", ["נהריה"], {}, lambda n: None)
    assert r["status"] == "suggest" and r["match"] == "נהריה" and r["auto_ok"] is True


def test_empty_raw_and_empty_candidates_fail():
    assert geo_suggest.suggest("", ["נהריה"])["status"] == "fail"
    assert geo_suggest.suggest("נהריה", [])["status"] == "fail"


def test_tie_blocks_auto():
    # Two equally-near candidates (both dist 1, both len≥4) ⇒ never auto (ambiguous).
    r = geo_suggest.suggest("אבגדה", ["אבגדו", "אבגדי"])
    assert r["status"] == "suggest"
    assert r["auto_ok"] is False


def test_levenshtein_basic():
    assert geo_suggest.levenshtein("abc", "abc") == 0
    assert geo_suggest.levenshtein("abc", "abd") == 1
    assert geo_suggest.levenshtein("", "abc") == 3
    assert geo_suggest.levenshtein("kitten", "sitting") == 3
