# PureWater Zone Merge / Minimization Plan — 2026-06-27

> Goal (Eran): merge zones to the minimum, dedupe cities that live in multiple zones,
> empty a zone to 0 → delete it. Cities I'm unsure of are flagged for manual check.
> Source: live DB query (orphan↔rotation city overlap + task counts).

## Verdict: 14 → 9 zones (delete the 5 orphans). Zero task risk.

The 9 **rotation** zones are structurally fixed (one per tech-day slot) — they can't be merged
further without redesigning the rotation. The 5 **orphan** zones (in NO rotation) are pure
duplication and the source of the misroute ambiguity. Deleting them IS the minimization.

**Why it's safe:** every orphan city that actually has tasks (24 of them) *also* exists in a real
rotation zone — so no live task loses coverage. Deleting the orphans just forces each city to
resolve to the zone a tech actually covers.

| Orphan zone (id) | Cities | All task-cities covered by a rotation zone? |
|---|---|---|
| גוש דן `ce8a4939…` | 13 | ✅ (תל אביב/לוד-אשדוד/ראש העין) |
| גליל `6a9cc7dc…` | 11 | ✅ (נהריה-חיפה/קש-עפולה) |
| חיפה וקריות `371b2fc7…` | 8 | ✅ (נהריה-חיפה/יקנעם-נתניה/זכרון) |
| שפלה `907b0566…` | 6 | ✅ (לוד-אשדוד) |
| שרון `e888433b…` | 11 | ✅ (תל אביב/זכרון/יקנעם-נתניה) |

## Step 1 (recommended first) — re-home the geographically-clear "orphan-only" cities

16 cities live ONLY in an orphan zone (0 tasks today). Before deleting the orphans, fold the
**confident** ones into the right rotation zone so future calls there route correctly:

| → Rotation zone | Add cities |
|---|---|
| נהריה-חיפה `f648f739…` | טירת כרמל · קרית אתא · בוסתן הגליל · קיבוץ מצובה · כפר מסריק |
| זכרון-הרצליה `ae3a57f5…` | אור עקיבא · פרדס חנה כרכור |
| קריית שמונה-עפולה `f088f618…` | נוף הגליל · גן נר · קיבוץ דן |

## Step 2 — delete the 5 orphan zones (14 → 9)

## ⚠ Manual check — I'm NOT certain where these belong (left for you/Israel)

| City | Plausible zone | Why uncertain |
|---|---|---|
| עתלית | נהריה-חיפה *or* זכרון-הרצליה | sits between חיפה and זכרון on the coast |
| בת חפר | יקנעם-נתניה *or* זכרון-הרצליה | Sharon plain near נתניה/חדרה |
| מושב הודיה | דרום *or* לוד-אשדוד | far south near אשקלון/קרית מלאכי |
| עילבון | קריית שמונה-עפולה? | Lower Galilee near טבריה |
| צופים | (none clean) | Samaria/West Bank near קלקיליה — no zone covers it cleanly |
| שעיר אפרים | (verify name) | spelling looks off — confirm the real settlement first |

These 5–6 have 0 tasks, so if they're dropped with the orphan they simply have "no zone" until a
real call arrives — at which point the normal add-city-with-zone flow catches them. No urgency.

## Sequencing
Enrich (Step 1) → delete orphans (Step 2) → re-run `resolveZone` sanity on the 108 task cities →
only then the recalc. Live zone deletes are not reversible → run each step on explicit go.
