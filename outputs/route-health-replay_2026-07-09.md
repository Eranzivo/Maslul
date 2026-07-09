# Route Health — replay validation over Israel's real schedule (P1 step 7)

**Verdict: the auditor says true things.** Run over all 89 assigned calls / 14 tech-days
in the live DB (Israel's imported June schedule, 2026-06-07 → 06-21), offline with real
geo-brain coordinates for all 46 cities (no TLV fallback — asserted). Matrix = haversine
(local mode); production uses cached Google times, so absolute minutes shift slightly but
structural findings (backtracks, gaps, order deltas) hold.

## Two calibration fixes the replay itself forced (both shipped + fixture-pinned)

1. **Arrival-window semantics.** First pass flagged 10/89 real stops as
   `window_violation` under "must finish inside the window" (the solver's placement
   rule). Israel's operational truth: the window bounds the ARRIVAL — באר שבע at 09:34
   in a 07:00–10:00 window is a kept promise. Audit rule changed to start-inside-window;
   the 10 false flags vanished. (The solver stays stricter when placing — deliberate,
   documented in knobs.md.)
2. **Solver-endorsed zigzag suppression.** Days whose actual order IS the solver's own
   best were still flagged for the direction jumps their windows forced. If no better
   order exists, the flag is noise → suppressed when actual order == solver order
   (06-09 אלירן went 84 → an honest 100).

## Final distribution (after calibration)

| date | tech | calls | score | band | findings |
|---|---|---|---|---|---|
| 06-07 | אלירן | 9 | 84* | review | backtrack |
| 06-07 | בני | 9 | 92* | healthy | backtrack |
| 06-07 | מיכאל | 5 | 92 | healthy | backtrack |
| 06-08 | אלירן | 9 | 76* | review | backtrack |
| 06-08 | בני | 7 | 92* | healthy | backtrack |
| 06-08 | מיכאל | 8 | 92* | healthy | backtrack |
| 06-09 | אלירן | 5 | 100 | healthy | — |
| 06-09 | בני | 6 | 100* | healthy | — |
| 06-09 | מיכאל | 1 | 100 | healthy | — |
| 06-10 | בני | 9 | 84* | review | backtrack |
| 06-10 | אלירן | 9 | 76* | review | backtrack |
| 06-10 | מיכאל | 9 | 92* | healthy | backtrack |
| 06-11 | אלירן | 2 | 100 | healthy | — |
| 06-21 | בני | 1 | 80 | review | idle_gap |

`*` = partial (solver dropped a stop under haversine speeds on 9-call days, so
actual-vs-best comparison was skipped there; with production cached Google times most
become comparable).

- **Scores: min 76 / median 92 / max 100 — bands: 9 healthy, 5 review, 0 issues.**
  A real, engine-built schedule audits as fundamentally sound — no invented crises.
- **15 backtrack findings** — real direction jumps (e.g. 06-07 אלירן: נתיבות 07:46 →
  כפר מימון 08:28 is an outward jump; far→near says start with כפר מימון). These are
  exactly the "worth a look" items the score should surface.
- **Self-consistency check passed:** on every fully-comparable day, actual drive ==
  solver best (887 = 887 min). The auditor confirms the engine's own output is optimal
  instead of manufacturing findings against it — the strongest evidence the shared-
  implementation invariant holds.
- **1 idle_gap** (06-21 בני, single future call placed mid-morning) — correct.

## Follow-ups parked (worklog)
- 9-call days at haversine speeds overfill the solver (drops → partial audits). Real
  drive times fix most; if partials persist in production, consider a relaxed audit
  solve (no drop penalty) for comparison-only purposes.
- One equal-cost case (06-07 מיכאל 292=292 with a backtrack flag) — solver found an
  equally-cheap order; the flag then reads "an equally-cheap cleaner order exists,"
  which is informative. Watch whether dispatchers find it useful or noisy.

Replay harness: scratchpad `run_replay.py` + `replay-bundle.json` (real rows, real
geo-brain coords, monkeypatched resolver, count-asserted 89).
