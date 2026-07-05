"""Batch correctness pack (Slice 1) — spec: outputs/batch-correctness-design_2026-07-05.md.

The batch scheduler must read the live calendar and enforce the same tenant rules as
the live JS path. Helper semantics MIRROR the JS functions (techHasSkill, getCatLimitOk,
getTechPartialBlocks, isCityBlocked, blockedZones) — parity is the point.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from batch_schedule import (  # noqa: E402
    _arrival_window_hours,
    _effective_duration,
    tech_has_skill,
    cat_limit_ok,
    city_blocked,
    zone_blocked,
)


# ── Task 1: config + eligibility helpers ─────────────────────────────────────

def test_arrival_window_reads_defaults_path():
    assert _arrival_window_hours({"defaults": {"arrival_window_hours": 2}}) == 2

def test_arrival_window_absent_defaults_to_3():
    assert _arrival_window_hours({}) == 3
    assert _arrival_window_hours(None) == 3

def test_arrival_window_legacy_toplevel_still_honored_as_fallback():
    # Old (buggy) location — keep as fallback so any tenant that was set that way keeps working.
    assert _arrival_window_hours({"arrival_window_hours": 4}) == 4
    # defaults wins over top-level
    assert _arrival_window_hours({"arrival_window_hours": 4,
                                  "defaults": {"arrival_window_hours": 2}}) == 2


def test_duration_chain_override_then_category_then_config_then_30():
    cat_duration = {"c1": 45}
    tech = {"duration_overrides": {"c1": 60}}
    config = {"defaults": {"regular_job_minutes": 25}}
    # tech override wins
    assert _effective_duration("c1", tech, cat_duration, config) == 60
    # category default next
    assert _effective_duration("c1", {}, cat_duration, config) == 45
    # tenant regular_job_minutes next
    assert _effective_duration("c2", {}, cat_duration, config) == 25
    # hardcoded 30 last
    assert _effective_duration("c2", {}, cat_duration, {}) == 30
    assert _effective_duration(None, {}, cat_duration, {}) == 30


def test_skill_semantics_mirror_js():
    # JS: if(!catId)return true; return (tech.skills||[]).includes(catId)
    assert tech_has_skill({}, None) is True
    assert tech_has_skill({"skills": ["c1"]}, "c1") is True
    assert tech_has_skill({"skills": ["c1"]}, "c2") is False
    # empty/absent skills with a category ⇒ False (exact JS mirror)
    assert tech_has_skill({}, "c1") is False
    assert tech_has_skill({"skills": []}, "c1") is False
    assert tech_has_skill({"skills": None}, "c1") is False


def test_cat_limit_ok_mirrors_js():
    # JS: no catId → ok; no limit for cat → ok; count < limit → ok
    assert cat_limit_ok({}, None, 5) is True
    assert cat_limit_ok({"cat_limits": {}}, "c1", 5) is True
    assert cat_limit_ok({"cat_limits": {"c1": 3}}, "c1", 2) is True
    assert cat_limit_ok({"cat_limits": {"c1": 3}}, "c1", 3) is False
    # string limits (JSONB from UI may hold strings — JS parseInt's them)
    assert cat_limit_ok({"cat_limits": {"c1": "2"}}, "c1", 2) is False


def test_city_and_zone_blocked():
    assert city_blocked({"blocked_cities": ["באר שבע"]}, "באר שבע") is True
    assert city_blocked({"blocked_cities": []}, "באר שבע") is False
    assert city_blocked({}, "באר שבע") is False
    assert zone_blocked({"blocked_zones": ["z1"]}, "z1") is True
    assert zone_blocked({}, "z1") is False
    assert zone_blocked({"blocked_zones": None}, "z1") is False
