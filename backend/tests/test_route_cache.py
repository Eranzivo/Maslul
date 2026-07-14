import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import route_cache as rc


def test_norm_key_rounds_coords_to_4dp():
    assert rc.norm_key("32.1234567,34.7654321") == "32.1235,34.7654"


def test_norm_key_passes_city_names_through_trimmed():
    assert rc.norm_key("  תל אביב ") == "תל אביב"


def test_trust_rejects_below_physical_floor():
    # 2 minutes for 20 straight-line km would require >600 km/h → distrust
    assert rc.is_trustworthy(google_min=2, straight_km=20) is False


def test_trust_rejects_absurdly_high():
    # 20 km: cap = (20/35*60)*10 ≈ 340 min → 400 is a bad API row
    assert rc.is_trustworthy(google_min=400, straight_km=20) is False


def test_trust_accepts_plausible():
    assert rc.is_trustworthy(google_min=40, straight_km=20) is True


def test_trust_accepts_fast_intercity_highway_leg():
    # TLV→Haifa: ~85 straight km, Google ~70-80 min — much faster than the 35 km/h
    # heuristic (~145 min) but entirely real. Must NOT be rejected.
    assert rc.is_trustworthy(google_min=75, straight_km=85) is True


def test_assemble_matrix_uses_cache_then_marks_misses(monkeypatch):
    # cache has only A→B; the rest are misses
    cached = {("A", "B"): 12}
    def fake_get_cached(pairs, key, bucket="static"):
        return {p: cached[p] for p in pairs if p in cached}
    monkeypatch.setattr(rc, "get_cached", fake_get_cached)
    hits, misses = rc.split_hits_misses(["A", "B", "C"], service_key="x")
    assert hits[("A", "B")] == 12
    assert ("A", "C") in misses and ("B", "A") in misses  # directional
    assert ("A", "A") not in misses  # self-pairs excluded
    assert len(misses) == 5  # 6 directional pairs minus 1 hit


def test_norm_key_applied_inside_split(monkeypatch):
    seen = {}
    def fake_get_cached(pairs, key, bucket="static"):
        seen["pairs"] = pairs
        return {}
    monkeypatch.setattr(rc, "get_cached", fake_get_cached)
    rc.split_hits_misses(["32.1234567,34.7654321", "חיפה "], service_key="x")
    assert ("32.1235,34.7654", "חיפה") in seen["pairs"]
