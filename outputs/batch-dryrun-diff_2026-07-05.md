# Batch Correctness Pack — offline dry-run vs REAL PureWater data (2026-07-05)

> New engine (`batch-correctness` branch) run OFFLINE against the real exported tenant state
> (tasks/zones/techs/config/geo brain via read-only MCP export). dry_run — zero live writes.

## Run A — June week (2026-06-07…11): 88 existing seeded + 20 pending
- assigned: **2** · unassigned: **18** · retimed existing: **0**
- city_not_in_zone (2): חרב, כפר בן נון
- day_over_capacity (1): טבריה
- no_slot_in_range (15): באר יעקב, גדרה, גן יבנה, חולון, לוד, נס ציונה, קרית אונו, שדרות, תל אביב

**בני**

- 2026-06-09: 1 — קיסריה

**מיכאל**

- 2026-06-11: 1 — מודיעין

## Run B — forward window (2026-07-05…16): empty calendar, 20 pending
- assigned: **18** · unassigned: **2** · retimed existing: **0**
- city_not_in_zone (2): חרב, כפר בן נון

**אלירן**

- 2026-07-05: 1 — שדרות
- 2026-07-06: 2 — לוד, גדרה
- 2026-07-08: 2 — תל אביב, חולון
- 2026-07-09: 1 — קרית אונו
- 2026-07-13: 1 — נס ציונה
- 2026-07-15: 2 — תל אביב, תל אביב

**בני**

- 2026-07-05: 2 — תל אביב, חולון
- 2026-07-06: 1 — מודיעין
- 2026-07-08: 1 — גן יבנה
- 2026-07-12: 2 — תל אביב, חולון
- 2026-07-15: 1 — באר יעקב

**מיכאל**

- 2026-07-05: 1 — קיסריה
- 2026-07-07: 1 — טבריה

---
patches captured (should be 0 — dry_run): 0

## Interpretation (verified findings)

1. **No overbooking — the headline fix.** Run A seeds the 88 real June calls: the Dan/Shfela covering days are genuinely full (9/9/9 on 06-07/08/10), so the engine places only what truly fits (2) and reports the rest honestly. The OLD engine was blind to the 88 and would have stacked up to 9 MORE calls on already-full days.
2. **cat_limits enforced on real data.** אלירן has a live `cat_limits` of ≤2 service-calls/day (a knob the old batch ignored entirely). Run B shows he never receives more than 2 per day; in Run A his full days accept none.
3. **Retry works.** טבריה tried its only covering day (מיכאל, Tue), didn't fit the time budget (אשקלון→טבריה round trip), and only then flagged `day_over_capacity` — not a silent drop.
4. **Existing calls untouched.** 0 retimes proposed (the June days were sequenced by the same solver/strategy, so re-solving reproduces their times); 0 write patches — dry-run is airtight.
5. **Known leftovers reproduce:** חרב (junk city) + כפר בן נון (not in the rebuilt 8 zones) fail as `city_not_in_zone` — matches the 2026-06-30 zone-rebuild notes, not a new defect.
6. **Balance-on spread is visible** in Run B (calls thinly spread across two weeks). That is the live `balance.enabled:true` semantics — the consolidate-vs-spread decision (placement-policy unification, Slice 3) is still pending with Israel.

Method note: no service key exists locally, so the run used a read-only MCP export of the real tenant state (tasks, zones, techs, config, geo brain 423/28) executed fully offline against the new engine — zero live access, zero writes.
