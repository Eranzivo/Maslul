# PureWater Zone Gap Analysis — PAUSED 2026-06-15 (resume here)

> Eran set this aside mid-session ("still seems off, we need to get back to it"). This captures
> the full state so we can resume without re-deriving. Nothing was written to live data.

> **⚠️ STATUS UPDATE 2026-06-24:** the far→near fix `995bc28` (+ `79dd2fb` work_days) is now **pushed to
> `origin/main` and Railway is live at v1.2.0** — the "not pushed / OLD engine still deployed" lines below
> were a mid-session snapshot and are now stale. Net effect on the resume plan: **step 4 no longer needs a
> deploy**, just a positive confirmation that the running build is the far→near one (dry-run a known north day
> → expect נהריה→…→חיפה, no קרית ים revisit). Orphan-zone cleanup + Israel's capacity decision still stand.

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

**3. Orphan/duplicate zones (data integrity) — ✅ CLEANED 2026-06-27:**
The 5 orphans (**גוש דן, גליל, חיפה וקריות, שפלה, שרון**; the empty אזור חדש was already gone)
were deleted — 14→9 zones. Every task-bearing orphan city already resolved to a rotation zone, so
zero task loss. Coordinate-verified strays re-homed first (נהריה-חיפה +טירת כרמל/קרית אתא/עתלית;
זכרון-הרצליה +אור עקיבא/פרדס חנה כרכור; קש-עפולה +נוף הגליל; דרום +מושב הודיה). Backup:
`outputs/zones-orphan-backup_2026-06-27.json`. Plan: `outputs/zone-merge-plan_2026-06-27.md`.
**↳ Still TODO (no coords in `cities.py`, were 0-task orphan-only cities — geocode then place):**
מושב הודיה*, בת חפר, עילבון, צופים, שעיר אפרים(verify name), בוסתן הגליל, קיבוץ מצובה, כפר מסריק,
גן נר, קיבוץ דן. (*מושב הודיה is now in דרום's list but still needs a coordinate to route.)

## End-goal (Eran, 2026-06-24)
The target is to **fit all 108 in one week again** — which it did before the 06-14 `max_daily` 15/12/9 → 9/9/9
change (that normalization is the regression; 2×9=18 < the dense-zone demand). Eran will **re-coordinate exact
zones with Israel and collect real call addresses** first, so optimizing runs on geocoded points instead of
city-only coords. Only then re-calculate. So the capacity decision (step 3 below) is explicitly biased toward
**restoring single-week fit** (higher caps and/or a 3rd covering day for the dense zones), not just placing what fits.

## Resume plan (each step = explicit go; live zone edits not reversible)
1. Delete the 6 orphan zones.
2. Fix סלעית (move/pending) + add זכרון יעקב/חרב coords or leave pending.
3. Israel decides the capacity resolution (3rd day vs spill).
4. Deploy the committed far→near fix to Railway → dry-run re-batch → show Israel the preview.

## Why a re-batch was NOT run now
Backend still has the OLD engine deployed (far→near fix committed `995bc28`, not pushed) and orphan
zones still live — a dry-run today would reproduce the mess. Do steps 1–4 in order first.
