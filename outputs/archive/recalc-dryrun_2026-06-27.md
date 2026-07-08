# 108-task recalc — DRY RUN on cleaned zones (2026-06-27)

> Greedy fill-first simulation (batch engine's assignment logic), max_daily 9/9/9, week Sun 06-28→Thu 07-02.
> **Zero live writes** — the 89 currently-assigned tasks (computed on the OLD dirty zones) are untouched.
> 109 non-cancelled tasks total.

## Result: 91 placed / 18 overflow / 1 needs-address (חרב)

Aggregate weekly capacity = 15 tech-day slots × 9 = **135 ≥ 109** → the problem is **distribution, not total
capacity.** The rotation gives the 3 dense zones only 2 covering days each, while low-demand zone-days sit idle.

### Per-zone demand vs weekly capacity
| Zone | Demand | Covering days × 9 | Result |
|---|---|---|---|
| תל אביב והסביבה | 28 | 18 (2d) | **overflow +10** |
| לוד-אשדוד | 25 | 18 (2d) | **overflow +7** |
| דרום | 19 | 18 (2d) | **overflow +1** |
| זכרון-הרצליה | 9 | 18 (2d) | fits (9 idle) |
| ירושלים | 7 | 18 (2d) | fits (11 idle) |
| קריית שמונה-עפולה | 7 | 9 (1d) | fits |
| יקנעם-נתניה | 6 | 9 (1d) | fits (incl. חרב → needs address) |
| נהריה-חיפה | 5 | 18 (2d) | fits (13 idle) |
| ראש העין והסביבה | 3 | 9 (1d) | fits |

### Per tech-day load (fill-first preview)
| Day | אלירן | בני | מיכאל |
|---|---|---|---|
| Sun | דרום 9/9 | תל אביב 9/9 | יקנעם-נתניה 6/9 |
| Mon | לוד-אשדוד 9/9 | ירושלים 7/9 | זכרון-הרצליה 9/9 |
| Tue | נהריה-חיפה 5/9 | **זכרון 0/9 (idle)** | קש-עפולה 7/9 |
| Wed | תל אביב 9/9 | לוד-אשדוד 9/9 | דרום 9/9 |
| Thu | ראש העין 3/9 | **נהריה 0/9 (idle)** | **ירושלים 0/9 (idle)** |

**The 27 idle slots are in the WRONG zones** — Tue-בני (זכרון), Thu-בני (נהריה), Thu-מיכאל (ירושלים) are
empty but those zones are already satisfied, while TLV/לוד-אשדוד/דרום overflow.

## Why it fit "a week ago" and not now
Before 2026-06-14 max_daily was **15/12/9**. With cap 15, TLV's 2 covering days = 30 ≥ 28 → fit. The
9/9/9 normalization (2×9=18) is exactly what broke single-week fit for the 3 dense zones.

## Balance principle (Eran 2026-06-27) — separate from overflow
Eran flagged: don't pile 6-10 of one city on one tech in a row. **Confirmed:** with `balance.enabled=false`
(current setting, fill-first consolidation chosen 06-14) the sim piles **באר שבע ×5 on אלירן Sun, הרצליה ×5,
ירושלים ×5**. With `balance.enabled=true` the worst same-city-per-tech-day drops to **3**. **But total overflow
is identical (18) in both modes** — balance redistributes *within* a zone's covering days, it cannot add
capacity, so it does not change single-week fit. → Re-enabling balance is a **quality** fix (reverses the 06-14
consolidation choice — confirm w/ Israel); the 18 overflow still needs a capacity lever below.

## Options to fit all 109 in one week (Eran/Israel decision)
- **A — restore higher max_daily on dense days** (e.g. 14): TLV 28≤2×14, לוד 25≤28, דרום 19≤28 → all fit in
  the **current rotation**, mirrors the pre-06-14 behavior. Cost: longer tech days; reverses the 9-normalization.
- **B — rotation rebalance** (no cap change): reassign the 3 idle covering-days (Tue-בני / Thu-בני / Thu-מיכאל)
  from their satisfied zones to TLV ×2 + לוד-אשדוד ×1. Fits with 9-cap. Cost: changes Israel's *permanent* rotation.
- **C — spill** the ~18 overflow to the following week (keep 9-cap + current rotation).

**Recommendation:** A for an immediate one-week fit (closest to the proven prior behavior, rotation untouched);
B is the better *structural* fix (even utilization) but needs Israel to agree to rotation changes. TLV (28 calls,
~26% of all demand) is the true bottleneck either way. חרב needs a real address regardless.
