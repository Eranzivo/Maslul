# geo_suggest QA — 2026-10-17

**Context:** `features.geo_suggest` was found **ON** for PureWater, while every doc described
Slices 2–3 as "deployed dark, needs browser QA before flag-on". No record of who turned it on or
when. Eran chose: QA the 4 doors now, then fix the docs to match reality.

**Verdict: safe to leave ON.** The safety guarantee holds against the real place data, and all
4 doors fail open, guard against loops and never write to the shared brain. There are 3 UX bugs
(none dangerous) and 1 unrelated data-persistence gap in the add-call path, listed below.

**Method / limits:** no browser in this session. (1) Ran the **real** `geo_suggest.py` +
`canonicalize.py` + `geo_resolver.resolve` (incl. the `cities.py` fallback) over the **real**
brain (1,310 `geo_places` + 29 `place_aliases`, pulled read-only), calling the exact function
`POST /geo-suggest` runs. (2) Read the code at all 4 call sites. Not covered: rendering, timing
of real clicks, and dialog stacking as a user experiences it. That still needs one manual
click-through.

---

## 1. Engine vs real data — 21/23 as expected

| Group | Inputs | Result |
|---|---|---|
| Exact + curated aliases | אשקלון · קריית גת · ת"א · נהרייה · ראשלצ | ✅ all `resolved` to the right canonical |
| Common real-world variants → silent auto-fix | פתח תקוה · נתנייה · הרצלייה · קריית ביאליק/אונו/ים/מוצקין · אשקלן · ירושליים · באר שבא | ✅ all auto-fixed to the correct city |
| Must never auto-apply | לד (short) · חרב (junk) · יבנא (tie) · Ashkelon · קריית ארבע (not in brain) · garbage | ✅ none auto-applied; "fail" matches are never offered |
| **Ties — wrong city offered** | **רחובת → offers רחוב** (not רחובות) · **גבעתים → offers גבעתי** (not גבעתיים) | ⚠️ safe (not auto-applied), but the prompt suggests a tiny settlement instead of the major city |

**Safety guarantee (verified):** an auto-fix can only land on the wrong town if the intended
place is missing from the brain or the user made ≥2 edits. A single typo always has the intended
town at distance 1, so any other town also at distance 1 makes a tie and downgrades to a prompt.
The real brain has **162** real-place pairs within one edit of each other (e.g. גדרה↔חדרה,
שדרות↔שחרות, יוקנעם↔יקנעם). Those are covered by the tie rule.

## 2. Door audit

| Door | Fail-open | Loop guard | Brain writes | Findings |
|---|---|---|---|---|
| **Dispatch** (`_trySuggestThenSearch`) | ✅ null ⇒ today's `showNoResult` | ✅ `_noSuggest` retries once | ✅ none | Fires only when the search returns zero slots. Tie prompt has the bug above. |
| **Add call** (`confirmAddTask`) | ✅ | n/a | ✅ none | **(a)** an accepted correction is **not written back to the `at-city` field**, so if the street check then fails, the fix is lost and the prompt repeats; **(b)** the city prompt fires *before* the street validation (wrong order). |
| **Bulk import** (`runBulkImport`) | ✅ | n/a | ✅ none | Auto-only, as designed. Ties / low-confidence rows go to "unmatched", correct. |
| **Zone authoring** (`confirmAddCity` + `suggestZoneForAddCity`) | ✅ | n/a | ✅ none (writes tenant zone only) | Can stack **up to 3 confirm dialogs** (local fix → brain fix → "not in national registry"). Noisy but safe. `/suggest-zone` never overrides a zone the user already picked. |

## 3. Unrelated finding in the add-call path (data persistence) — P1 before Israel's real week

`confirmAddTask` (`index.html` ~7822) calls `saveTaskToSupabase(newTask)` **without `await`**
and shows "הקריאה נרשמה ✓" **before the save resolves**. It also consumes `nextTaskId++` before a
confirmed insert. A **new** task is **not covered by the WAL** (architecture.md, persistence rule
#4). If the insert fails (network drop), the call exists only in that browser tab. `dbInsert`
does still raise an error toast, but it lands after a green success toast. This breaks
persistence rules #2–3 and sits in the exact path Israel uses to enter next week's real schedule.
(Correction: `confirmReplace` ~7783 is *not* the same risk. It reassigns an **existing** pending
call, which is an update and so WAL-covered.) The other non-awaited call sites are also updates.

**✅ FIXED same day (F1 + F3):** `confirmAddTask` now awaits the save, adds the call to local state
only after a confirmed insert (row UUID), keeps the modal open with a Hebrew error on failure,
blocks double-clicks (the old code turned a triple-click into **3 duplicate calls**), validates the
street before the city prompt, and writes an accepted geo fix back into the field. Regression
suite `tests/addtask.test.js`: old code **8/17**, new code **17/17**.

## 4. Recommended fixes

| # | Fix | Size |
|---|---|---|
| F1 | ✅ **done** — `confirmAddTask` awaits the save, success only on a confirmed insert, double-click guard. | done 2026-10-17 |
| F2 | Ties: backend returns the tied `candidates[]`; the door prefers the candidate that is in the tenant's zones, else offers a choice. Fixes רחובת/גבעתים. | small–medium · both ends + fixture case |
| F3 | ✅ **done** — street validated first; accepted correction written back into `at-city`. | done 2026-10-17 |
| F4 | Zone authoring: merge the stacked confirms into one decision dialog. | small · cosmetic, later |

Reproduce: `qa_geo_suggest.py` (session scratchpad; it loads the brain into `geo_resolver._brain`
and calls `geo_suggest.resolve_or_suggest` exactly as the endpoint does).
