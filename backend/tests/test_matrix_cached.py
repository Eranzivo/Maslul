import sys, os, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import optimizer
import route_cache as rc

# Two real cities ~? apart + coords are resolved via cities.py / _parse_loc.
LOCS = ["תל אביב", "חיפה"]


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_warm_cache_uses_hits_and_never_calls_google(monkeypatch):
    hits = {("תל אביב", "חיפה"): 64, ("חיפה", "תל אביב"): 70}
    monkeypatch.setattr(rc, "get_cached", lambda pairs, key, bucket="static": dict(hits))
    stored = []
    monkeypatch.setattr(rc, "put_cached", lambda rows, key, bucket="static": stored.extend(rows))

    async def boom(locations, api_key):
        raise AssertionError("Google must not be called on a fully warm cache")
    monkeypatch.setattr(optimizer, "build_matrix_gmaps", boom)

    m = _run(optimizer.build_matrix_cached(LOCS, api_key="fake", service_key="x"))
    assert m[0][1] == 64 and m[1][0] == 70
    assert stored == []  # nothing new to store


def test_cold_cache_fetches_google_and_stores_trusted(monkeypatch):
    monkeypatch.setattr(rc, "get_cached", lambda pairs, key, bucket="static": {})
    stored = []
    monkeypatch.setattr(rc, "put_cached", lambda rows, key, bucket="static": stored.extend(rows))

    async def fake_gmaps(locations, api_key):
        # plausible drive times (haversine TLV→Haifa ≈ 85km ≈ 145 min floor at 35km/h → ~? )
        return [[0, 75], [80, 0]]
    monkeypatch.setattr(optimizer, "build_matrix_gmaps", fake_gmaps)

    m = _run(optimizer.build_matrix_cached(LOCS, api_key="fake", service_key="x"))
    assert m[0][1] == 75 and m[1][0] == 80
    assert {(r["from_key"], r["to_key"]) for r in stored} == {("תל אביב", "חיפה"), ("חיפה", "תל אביב")}
    assert all(r["source"] == "google" for r in stored)


def test_untrusted_google_leg_falls_back_to_haversine_and_not_stored(monkeypatch):
    monkeypatch.setattr(rc, "get_cached", lambda pairs, key, bucket="static": {})
    stored = []
    monkeypatch.setattr(rc, "put_cached", lambda rows, key, bucket="static": stored.extend(rows))

    async def fake_gmaps(locations, api_key):
        return [[0, 1], [1, 0]]  # 1 minute TLV→Haifa — absurd, must be distrusted
    monkeypatch.setattr(optimizer, "build_matrix_gmaps", fake_gmaps)

    m = _run(optimizer.build_matrix_cached(LOCS, api_key="fake", service_key="x"))
    assert m[0][1] > 30  # haversine floor, not the bogus 1
    assert stored == []  # poison row not cached


def test_no_api_key_uses_hits_plus_haversine(monkeypatch):
    hits = {("תל אביב", "חיפה"): 64}
    monkeypatch.setattr(rc, "get_cached", lambda pairs, key, bucket="static": dict(hits))
    monkeypatch.setattr(rc, "put_cached", lambda rows, key, bucket="static": None)

    m = _run(optimizer.build_matrix_cached(LOCS, api_key=None, service_key="x"))
    assert m[0][1] == 64       # cached leg reused even without Google
    assert m[1][0] > 30        # missing reverse leg → haversine
