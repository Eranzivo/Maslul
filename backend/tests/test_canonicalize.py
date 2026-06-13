import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from canonicalize import normalize_place_key, resolve_place_key


def test_strips_gershayim_geresh_and_quotes():
    # ת"א with straight quote, Hebrew gershayim ״, and apostrophe forms all collapse the same
    assert normalize_place_key('ת"א') == 'תא'
    assert normalize_place_key('ת״א') == 'תא'      # U+05F4 gershayim
    assert normalize_place_key('ב"ש') == 'בש'
    assert normalize_place_key('ראשל"צ') == 'ראשלצ'
    assert normalize_place_key("רח'") == 'רח'           # geresh/apostrophe


def test_collapses_whitespace_hyphen_maqaf():
    assert normalize_place_key('קרית-גת') == 'קרית גת'
    assert normalize_place_key('קרית־גת') == 'קרית גת'   # maqaf
    assert normalize_place_key('  תל   אביב  ') == 'תל אביב'


def test_empty_and_none_safe():
    assert normalize_place_key('') == ''
    assert normalize_place_key(None) == ''


def test_does_NOT_merge_genuine_spelling_variants():
    # The normalizer must be conservative: different spellings stay different here.
    # Merging נהריה/נהרייה is the alias/coordinate layer's job, never the normalizer's.
    assert normalize_place_key('נהריה') != normalize_place_key('נהרייה')
    # and it must NOT collapse a real place into a substring of another
    assert normalize_place_key('בלפוריה') != normalize_place_key('פוריה')


def test_resolve_applies_curated_alias_after_normalizing():
    aliases = {'תא': 'תל אביב', 'בש': 'באר שבע', 'נהרייה': 'נהריה', 'יפו': 'תל אביב'}
    assert resolve_place_key('ת"א', aliases) == 'תל אביב'
    assert resolve_place_key('ב"ש', aliases) == 'באר שבע'
    assert resolve_place_key('נהרייה', aliases) == 'נהריה'
    assert resolve_place_key('יפו', aliases) == 'תל אביב'
    # no alias → returns the normalized key unchanged (never guesses)
    assert resolve_place_key('דימונה', aliases) == 'דימונה'
    assert resolve_place_key('חרב', aliases) == 'חרב'
