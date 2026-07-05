"""Geo Slice B — shared address-level KB ("City cords"). Spec:
outputs/geo-one-source-design_2026-07-05.md §Slice B.
Every geocoded street is stored once in the global geo_addresses cache (PII-free:
street+city+coords only); repeat addresses cost zero Google spend; a same-street
different-number query reuses the nearest known house (never a cross-street guess)."""
import sys, os, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import geo_addresses as ga


# ── key normalization ─────────────────────────────────────────────────────────

def test_street_keys_parse_hebrew_with_number():
    full, name, num = ga.street_keys('אלי סיני 7')
    assert full == 'אלי סיני 7'
    assert name == 'אלי סיני'
    assert num == 7

def test_street_keys_strip_noise_and_no_number():
    full, name, num = ga.street_keys('  הרצל-המלך  ')
    assert full == 'הרצל המלך'
    assert name == 'הרצל המלך'
    assert num is None

def test_street_keys_empty_safe():
    assert ga.street_keys('') == ('', '', None)
    assert ga.street_keys(None) == ('', '', None)


def test_plausible_il_bbox():
    assert ga.plausible_il(31.697962, 34.579152) is True   # Ashkelon depot
    assert ga.plausible_il(48.85, 2.35) is False            # Paris — a bad geocode
    assert ga.plausible_il(None, None) is False


# ── lookup tiers (fake rows via monkeypatched fetch) ─────────────────────────

def _install_rows(monkeypatch, rows):
    def fake_fetch(params, key):
        # exact tier filters on street_key; street tier on street_name_key
        if "street_key" in params:
            v = params["street_key"][3:]  # strip "eq."
            return [r for r in rows if r["street_key"] == v]
        v = params["street_name_key"][3:]
        return [r for r in rows if r["street_name_key"] == v]
    monkeypatch.setattr(ga, "_fetch", fake_fetch)

_ROWS = [
    {"street_key": "הרצל 5", "street_name_key": "הרצל", "house_number": 5,
     "lat": 31.66, "lon": 34.57, "city_key": "אשקלון"},
    {"street_key": "הרצל 40", "street_name_key": "הרצל", "house_number": 40,
     "lat": 31.67, "lon": 34.58, "city_key": "אשקלון"},
]

def test_lookup_exact_hit(monkeypatch):
    _install_rows(monkeypatch, _ROWS)
    hit = ga.lookup("הרצל 5", "אשקלון", "svc")
    assert hit == (31.66, 34.57, "exact")

def test_lookup_street_tier_picks_nearest_house_number(monkeypatch):
    _install_rows(monkeypatch, _ROWS)
    hit = ga.lookup("הרצל 9", "אשקלון", "svc")
    assert hit == (31.66, 34.57, "street"), "house 9 is nearer to 5 than to 40"

def test_lookup_miss_returns_none(monkeypatch):
    _install_rows(monkeypatch, _ROWS)
    assert ga.lookup("ביאליק 3", "אשקלון", "svc") is None

def test_lookup_fail_open(monkeypatch):
    def boom(params, key): raise RuntimeError("db down")
    monkeypatch.setattr(ga, "_fetch", boom)
    assert ga.lookup("הרצל 5", "אשקלון", "svc") is None

def test_lookup_no_key_short_circuits():
    assert ga.lookup("הרצל 5", "אשקלון", "") is None


# ── /geocode endpoint flow (cache-first, meter only real Google spend) ───────

def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

def test_geocode_endpoint_cache_hit_skips_google_and_quota(monkeypatch):
    import main
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "k")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "svc")
    monkeypatch.setattr(main, "_gmaps_quota_ok", lambda *a, **k: (_ for _ in ()).throw(AssertionError("quota must not be touched on cache hit")))
    async def noop(key, force=False): return None
    monkeypatch.setattr(main.geo_resolver, "ensure_loaded", noop, raising=False)
    monkeypatch.setattr(ga, "lookup", lambda s, c, k: (31.66, 34.57, "exact"))
    r = _run(main.geocode(main.GeocodeRequest(street="הרצל 5", city="אשקלון")))
    assert r["lat"] == 31.66 and r["lon"] == 34.57
    assert r.get("source") == "cache-exact"

def test_geocode_endpoint_miss_calls_google_and_stores(monkeypatch):
    import main
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "k")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "svc")
    charged = []
    monkeypatch.setattr(main, "_gmaps_quota_ok", lambda n, charge=True: charged.append(n) or True)
    async def noop(key, force=False): return None
    monkeypatch.setattr(main.geo_resolver, "ensure_loaded", noop, raising=False)
    monkeypatch.setattr(ga, "lookup", lambda s, c, k: None)
    async def fake_google(street, city, api_key):
        return (31.7, 34.6)
    monkeypatch.setattr(ga, "google_geocode", fake_google)
    stored = []
    monkeypatch.setattr(ga, "store", lambda *a, **kw: stored.append(a))
    r = _run(main.geocode(main.GeocodeRequest(street="ביאליק 3", city="אשקלון")))
    assert r["lat"] == 31.7 and charged == [10] and len(stored) == 1

def test_geocode_endpoint_paris_result_not_stored(monkeypatch):
    import main
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "k")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "svc")
    monkeypatch.setattr(main, "_gmaps_quota_ok", lambda n, charge=True: True)
    async def noop(key, force=False): return None
    monkeypatch.setattr(main.geo_resolver, "ensure_loaded", noop, raising=False)
    monkeypatch.setattr(ga, "lookup", lambda s, c, k: None)
    async def fake_google(street, city, api_key): return (48.85, 2.35)
    monkeypatch.setattr(ga, "google_geocode", fake_google)
    stored = []
    monkeypatch.setattr(ga, "store", lambda *a, **kw: stored.append(a))
    r = _run(main.geocode(main.GeocodeRequest(street="rue x", city="paris")))
    assert stored == [], "implausible (outside IL) coords must never poison the shared KB"
    assert r["lat"] == 48.85, "still returned to the caller (fail-open) — just not cached"
