import sys, os
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import geo_resolver as gr


@pytest.fixture(autouse=True)
def _reset_brain():
    # _brain is a process-global cache by design; isolate tests so we don't pollute others.
    yield
    gr._brain = {"loaded_at": 0.0, "places": {}, "alias_to_key": {}}


def _set_brain():
    gr._brain = {
        "loaded_at": 1,
        "places": {"תל אביב": (32.08, 34.78), "קרית שמונה": (33.2, 35.5)},
        "alias_to_key": {"תא": "תל אביב", "קריית שמונה": "קרית שמונה"},
    }


def test_lookup_exact_alias_and_miss():
    _set_brain()
    assert gr.lookup('תל אביב') == (32.08, 34.78)        # exact normalized match
    assert gr.lookup('ת"א') == (32.08, 34.78)             # normalize → alias → place
    assert gr.lookup('קריית שמונה') == (33.2, 35.5)       # divergent spelling resolves via alias
    assert gr.lookup('עיר דמיונית') is None               # genuine miss → None (never guesses)
    assert gr.lookup('') is None


def test_resolve_falls_back_to_cities_when_brain_misses():
    # Empty brain → resolve must fall back to the static cities.py (fail-safe = current behavior)
    gr._brain = {"loaded_at": 0, "places": {}, "alias_to_key": {}}
    assert gr.resolve('נהריה') is not None                # known in cities.py
    assert gr.resolve('חרב') is None                       # unknown everywhere → flagged upstream


def test_resolve_prefers_brain_over_cities():
    gr._brain = {"loaded_at": 1, "places": {"תל אביב": (1.0, 2.0)}, "alias_to_key": {}}
    assert gr.resolve('תל אביב') == (1.0, 2.0)             # brain wins
