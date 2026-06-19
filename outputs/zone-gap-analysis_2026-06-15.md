# PureWater Zone Gap Analysis — PAUSED 2026-06-15 (resume here)

> Eran set this aside mid-session ("still seems off, we need to get back to it"). This captures
> the full state so we can resume without re-deriving. Nothing was written to live data.

## What's confirmed
- **Task data is clean & complete.** Israel's authoritative weekly list = **108 tasks**, matches the
  DB 100% (every city + count). Only abbreviation diffs (ב״ש=באר שבע, ראשל״צ=ראשון לציון,
  קריית ים=קרית ים, סילעית=סלעית); DB already stores canonical forms.
- **Rotation matches Israel's WhatsApp exactly** (verified vs DB):
  | Tech | Sun | Mon | Tue | Wed | Thu |
  |---|---|---|---|---|---|
  | אלירן | דרום | לוד-אשדוד | נהריה-חיפה | תל אביב | ראש העין |
  | בני | תל אביב | ירושלים | זכרון-הרצליה | לוד-אשדוד | נהריה-חיפה |
  | מיכאל | יקנעם-נתניה | זכרון-הרצליה | קש-עפולה | דרום | ירושלים |
- **All 52 task-cities already map to a rotation zone** — no "city without a zone" gap.
- **Geo-verification (all 52 via `cities.resolve_coords`): only חרב returns None.** No silent TLV
  fallbacks. (`זכרון יעקב` also has no coords — latent, no task this week.)

## The gaps
**1. Geography mismatches (→ pending per "if not certain → pending"):**
- **חרב (1)** — no coordinates → can't route → pending until real address (Israel's "create city" case).
- **סלעית (1)** — in זכרון-הרצליה, but resolves to (32.21, 35.04) = inland Samaria, ~30 km E of the
  coastal זכרון/חדרה/קיסריה (≈32.5, 34.9). Doesn't fit → pending, or move to ראש העין/תל אביב.
- **זכרון יעקב** — zone namesake, no coords in `cities.py`. Add before a task lands there.

**2. Capacity vs coverage (max_daily = 9 fixed) — the real gap:**
| Zone | Demand | Covering days | Capacity (×9) | Over |
|---|---|---|---|---|
| תל אביב והסביבה | 27 | 2 | 18 | **+9** |
| לוד-אשדוד | 25 | 2 | 18 | **+7** |
| דרום | 19 | 2 | 18 | **+1** |
| all others | — | — | — | fit |

~17 overflow + חרב + סלעית ≈ the 20 pending. **Root tension:** the rotation (2 covering days for these
zones) fit a week ago *only because max_daily was 15/12/9*; with the **9/9/9** rule it set on 2026-06-14,
2×9=18 < 27 — rotation and cap are now mathematically inconsistent for these 3 zones. **PureWater decision
needed:** (a) 3rd covering day for the 3 busy zones (spare exists: נהריה-חיפה 5/18, ירושלים 7/18,
ראש העין 2/9), (b) spill overflow to next week, or (c) revisit the 9 cap for dense urban days.

**3. Orphan/duplicate zones (data integrity) — still to clean:**
6 orphans not in any rotation, overlapping the real zones, causing `find_zone` misroutes:
**גוש דן, גליל, חיפה וקריות, שפלה, שרון, + empty אזור חדש**. Should be deleted.

## Resume plan (each step = explicit go; live zone edits not reversible)
1. Delete the 6 orphan zones.
2. Fix סלעית (move/pending) + add זכרון יעקב/חרב coords or leave pending.
3. Israel decides the capacity resolution (3rd day vs spill).
4. Deploy the committed far→near fix to Railway → dry-run re-batch → show Israel the preview.

## Why a re-batch was NOT run now
Backend still has the OLD engine deployed (far→near fix committed `995bc28`, not pushed) and orphan
zones still live — a dry-run today would reproduce the mess. Do steps 1–4 in order first.
