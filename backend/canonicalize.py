"""Place-name canonicalization — the SINGLE authority for matching spelling variants.

Design: `outputs/geo-foundation-design_2026-06-13.md`. The golden rule is *eager to
normalize noise, conservative about merging*: this module's deterministic layer only
removes punctuation/whitespace noise — it NEVER decides that two genuinely different
spellings are the same place. Real merges come from curated aliases (`resolve_place_key`)
or, ultimately, geocoded coordinates (handled elsewhere). Fuzzy matches are suggest-only.

Keep this as the one place resolution happens; the frontend defers to it. Duplicating the
logic in JS is exactly what caused the נהריה/נהרייה false-flag.
"""
import re
import unicodedata

# Gershayim ״, geresh ׳, straight/curly quotes and apostrophes — all dropped (ת"א → תא).
_MARKS = '"״“”‟' + "'׳‘’′"
_MARK_RE = re.compile('[' + re.escape(_MARKS) + ']')
# Whitespace, ASCII hyphen, Hebrew maqaf ־, and the Unicode dash range — collapse to one space.
_SEP_RE = re.compile(r'[\s\-־‐-―]+')


def normalize_place_key(name) -> str:
    """Deterministic, lossless-of-meaning key for variant matching.

    Collapses punctuation/whitespace noise only:
      ת"א / ת״א → תא ; קרית-גת / קרית־גת → קרית גת ; "  תל   אביב " → תל אביב
    It deliberately does NOT merge different spellings (נהריה ≠ נהרייה) or substrings
    (בלפוריה ≠ פוריה) — those decisions belong to the alias/coordinate layers.
    """
    if not name:
        return ''
    s = unicodedata.normalize('NFKC', str(name)).strip()
    s = _MARK_RE.sub('', s)
    s = _SEP_RE.sub(' ', s).strip()
    return s


def resolve_place_key(name, alias_map) -> str:
    """normalize → curated-alias lookup. Returns the canonical key, or the normalized key
    when no human-blessed alias exists. Never fuzzy-merges (that requires confirmation)."""
    key = normalize_place_key(name)
    return (alias_map or {}).get(key, key)
