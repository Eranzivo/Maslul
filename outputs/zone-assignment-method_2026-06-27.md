# Zone-assignment method (coordinate-driven) — 2026-06-27

> Eran asked me to review/feedback the method for placing a city into a zone. This is the
> agreed approach going forward. Replaces "nearest zone *namesake*" eyeballing (unreliable).

## The rule
A zone is a **spread of cities**, not a point. To place an unzoned city:
1. Get its real coords from `backend/cities.py` (geocode + add it first if missing — never guess).
2. Compute haversine distance to **every city that already belongs to a zone**.
3. Assign to the zone of the **nearest member city** (look at the top-3 for transparency / ties).
4. If the top-2 straddle two zones within a few km, it's a genuine boundary case → flag for the
   tenant to confirm, don't force it.

## Why it's better than nearest-namesake
- Uses each zone's actual spatial extent, so a city near a zone's *far edge* still maps correctly
  (handles the "far city of a zone" case Eran described).
- Deterministic, reproducible, evidence-backed (distances + which city won).
- Surfaces data bugs: צופים's nearest neighbor came back as **סלעית (3.2km)** — and סלעית is itself
  mis-zoned (a Samaria settlement parked in זכרון-הרצליה). The method flagged the cluster instead of
  hiding it. → review **צופים + סלעית** together with Israel (likely both → ראש העין).

## Long-term (the real fix for fuzzy fringes)
**Polygon zones** (`scheduling.zone_match: polygon`, already supported by `resolveZone`). City-lists
are inherently ambiguous on boundaries like the Sharon-east / Samaria edge; a drawn polygon per zone
resolves them by point-in-polygon. Promote PureWater's dense/contested edges to polygons when Israel
has time to draw them. See `context/zones-polygons.md` + [[geo-foundation-vision]].

## Results applied (2026-06-27)
| City | Nearest member | Zone | Confidence |
|---|---|---|---|
| מושב הודיה | אשקלון 6.2km | דרום | ✅ |
| קיבוץ דן | צפת 33.9km | קש-עפולה | ✅ (far-north zone) |
| גן נר | מרחביה 8.5km | קש-עפולה | ✅ |
| בוסתן הגליל | עכו 2.9km | נהריה-חיפה | ✅ |
| קיבוץ מצובה | נהריה 8.6km | נהריה-חיפה | ✅ |
| כפר מסריק | עכו 4.1km | נהריה-חיפה | ✅ |
| שער אפרים | בארותיים 5.1km | יקנעם-נתניה | ✅ |
| בת חפר | בארותיים 7.8km | יקנעם-נתניה | ✅ |
| עילבון | טבריה 12.8 / כרמיאל 13.6km | **נהריה-חיפה** | Eran broke the tie west (קש-עפולה = eastern spine) |
| צופים | סלעית 3.2km | **ראש העין** | + סלעית moved here too (Samaria pair, eastern catchment) |

> **2026-06-27 finalization (Eran):** עילבון → נהריה-חיפה (domain tie-break: קש-עפולה covers the
> eastern spine Afula→Kiryat Shmona; עילבון leans west to כרמיאל/Haifa). צופים + the previously
> mis-zoned **סלעית** → ראש העין (no better-matching zone for the Samaria fringe; ראש העין is the
> closest sensible eastern catchment). The "כפר סבא" mention was a landmark, not the computed nearest —
> ignored. This is a good example of the method giving a candidate, then **domain knowledge breaking a
> genuine tie** — both belong in the loop.

Reusable script: `scratchpad/nn.py` (haversine vs all zone members; feed it the live zone→cities map).
