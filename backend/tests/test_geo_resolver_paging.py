"""ensure_loaded must page through geo_places: PostgREST caps every response at 1000
rows and the brain holds 1,300+ places since the national OSM import (2026-07-06).
Without paging the loader silently drops every place after row 1000 — exactly the
class of bug that made polygon capture miss small settlements."""
import asyncio
import sys, os
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import geo_resolver as gr


@pytest.fixture(autouse=True)
def _reset_brain():
    gr._brain = {"loaded_at": 0.0, "places": {}, "alias_to_key": {}}
    yield
    gr._brain = {"loaded_at": 0.0, "places": {}, "alias_to_key": {}}


class _FakeResponse:
    def __init__(self, rows):
        self._rows = rows

    def raise_for_status(self):
        pass

    def json(self):
        return self._rows


class _FakeClient:
    """Serves geo_places in 1000-row pages honoring the Range header; place_aliases in one go."""
    def __init__(self, n_places):
        self.rows = [{"normalized_key": f"עיר {i}", "lat": 31.0 + i * 1e-4, "lon": 34.5}
                     for i in range(n_places)]
        self.range_headers = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def get(self, url, headers=None, params=None):
        if url.endswith("/geo_places"):
            rng = (headers or {}).get("Range", "0-999")
            self.range_headers.append(rng)
            start, end = (int(x) for x in rng.split("-"))
            return _FakeResponse(self.rows[start:end + 1])
        return _FakeResponse([{"normalized_variant": "תא",
                               "geo_places": {"normalized_key": "עיר 0"}}])


def test_ensure_loaded_pages_past_1000(monkeypatch):
    fake = _FakeClient(1310)
    monkeypatch.setattr(gr.httpx, "AsyncClient", lambda **kw: fake)
    asyncio.new_event_loop().run_until_complete(gr.ensure_loaded("svc-key", force=True))
    assert len(gr._brain["places"]) == 1310          # nothing truncated
    assert gr._brain["alias_to_key"] == {"תא": "עיר 0"}
    assert fake.range_headers == ["0-999", "1000-1999"]  # paged exactly as PostgREST expects


def test_ensure_loaded_single_short_page(monkeypatch):
    fake = _FakeClient(505)
    monkeypatch.setattr(gr.httpx, "AsyncClient", lambda **kw: fake)
    asyncio.new_event_loop().run_until_complete(gr.ensure_loaded("svc-key", force=True))
    assert len(gr._brain["places"]) == 505
    assert fake.range_headers == ["0-999"]           # short first page → no extra round-trip
