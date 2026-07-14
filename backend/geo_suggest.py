"""Fuzzy place suggestion — Slice 2 of the self-healing geo brain.

Backend-only BY DESIGN (single resolution authority — the frontend NEVER re-implements this;
the data-entry doors call the endpoint). Given a raw city string that did NOT resolve exactly,
propose the most likely real place with a confidence, split into three actionable outcomes:

  resolved — exact / curated-alias / coords hit (no fuzz needed).
  suggest  — a near match. `auto_ok=True` ⇒ near-certain: a coordinator door may auto-apply the
             fix (still reversible; the new alias stays APPROVAL-GATED before it enters the shared
             brain). `auto_ok=False` ⇒ "did you mean X?" — a human picks.
  fail     — nothing close enough ⇒ the door asks the user to re-enter (e.g. קרת שמה).

Deliberately NOT mirrored in JS (unlike the engine parity pairs): resolution lives in ONE place.
Thresholds are NAMED constants here (auditable/tunable), never scattered magic numbers.
Design: outputs/geo-selfheal-design_2026-07-14.md.
"""
from canonicalize import normalize_place_key, resolve_place_key

# ── Confidence thresholds (the one place they live) ───────────────────────────
AUTO_MAX_DIST = 1     # edit distance ≤ this ⇒ eligible for auto-fix …
MIN_AUTO_LEN = 4      # … but only when both strings are this long (short names collide: גת≠גן)
SUGGEST_MAX_DIST = 2  # edit distance ≤ this ⇒ offered as "did you mean?"


def levenshtein(a: str, b: str) -> int:
    """Classic edit distance (character-level; Hebrew letters are single NFKC code points)."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[-1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def suggest(raw, candidate_keys) -> dict:
    """Best fuzzy candidate for `raw` among `candidate_keys` (canonical brain keys).

    Returns ``{status, match, confidence, auto_ok}``. Pure, no network. `auto_ok` requires a
    UNIQUE nearest candidate within AUTO_MAX_DIST and both strings ≥ MIN_AUTO_LEN — a tie (two
    equally-near places) is never auto-applied; it downgrades to a human "did you mean?"."""
    nkey = normalize_place_key(raw)
    if not nkey or not candidate_keys:
        return {"status": "fail", "match": None, "confidence": 0.0, "auto_ok": False}
    best, best_d, ties = None, 10 ** 9, 0
    for c in candidate_keys:
        d = levenshtein(nkey, c)
        if d < best_d:
            best, best_d, ties = c, d, 1
        elif d == best_d:
            ties += 1
    length = max(len(nkey), len(best)) or 1
    conf = round(1 - best_d / length, 3)
    auto = (best_d <= AUTO_MAX_DIST and ties == 1
            and len(nkey) >= MIN_AUTO_LEN and len(best) >= MIN_AUTO_LEN)
    if best_d <= SUGGEST_MAX_DIST:
        return {"status": "suggest", "match": best, "confidence": conf, "auto_ok": auto}
    return {"status": "fail", "match": best, "confidence": conf, "auto_ok": False}


def resolve_or_suggest(raw, candidate_keys, alias_map, resolve_fn) -> dict:
    """Full ladder: authoritative exact/alias/coords resolve → else fuzzy suggest.

    `resolve_fn(raw) -> (lat,lon) | None` is the authoritative resolver (`geo_resolver.resolve`).
    On a hard hit returns ``status='resolved'`` (+ coords); otherwise the `suggest()` shape."""
    coords = resolve_fn(raw)
    if coords is not None:
        return {"status": "resolved", "match": resolve_place_key(raw, alias_map),
                "confidence": 1.0, "auto_ok": True, "coords": list(coords)}
    return suggest(raw, candidate_keys)
