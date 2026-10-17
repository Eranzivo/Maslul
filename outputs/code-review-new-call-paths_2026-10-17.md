# Code review: new-call persistence (commit ab7dfd7 + follow-up), 2026-10-17

`/code-review` (high) on ab7dfd7 against Maslul's principles: data persistence (await saves; the
WAL does not cover new inserts; success only after a confirmed write; no phantom or duplicate
records), generic Hebrew errors, fail-open external calls, demo-mode guard, and scale-readiness.
Each finding was **verified against the code before acting**.

| # | Finding | Verdict | Action |
|---|---|---|---|
| 1 | The new `!currentTenantId` guard breaks "+ קריאה" in **demo mode** | ✅ valid | Fixed. Demo goes through `insertNewTaskConfirmed`, which stays local and makes zero Supabase calls. |
| 2 | No idempotency: commit-succeeded-but-response-lost → the retry creates a duplicate | ✅ valid, rare | **Deferred** to the backlog ("Idempotent new-call insert"). It changes the shared write layer. |
| 3 | `dbInsert` has no try/catch, so `_savesInFlight` leaks when the client throws | ✅ valid | Fixed. Now mirrors `dbUpsert` (try/catch, counter always decremented, returns null). |
| 4 | `geoSuggestCity` fetch has no timeout while the save button is locked, so a hung backend freezes the UI | ✅ valid | Fixed. `_fetchTimeout` (AbortController): geo-suggest 4s, geocode 8s. Covers dispatch confirm, save-pending and add-call. |
| 5 | Cancel/reopen during a save: a late result closes the NEW modal or leaves it on "שומר…" | ✅ valid | Fixed. Per-opening session token: cancel or reopen bumps it, a late result never touches the new modal, and a saved-after-cancel call gets an honest "נשמרה ✓" toast. |
| 6 | Double error toast + double Sentry | ⚠️ partly wrong | No double Sentry: `dbInsert` captures returned errors and the caller captures throws, so the same failure is never captured twice. Toast + inline error kept on purpose (the inline one says what to do). No change. |
| 7 | "street before city prompt" test never asserted that geo wasn't called | ✅ valid | Fixed. The test now runs with geo ON and asserts `geoAsked === 0`. |
| 8 | **Altitude: the same phantom-call bug in the other create-call doors** | ✅ valid (except `confirmReplace`, which is an update to an existing row) | **Fixed at the root.** One create path `insertNewTaskConfirmed()` is used by dispatch confirm, call drawer, save-pending, add-call, recurring series and CSV import. Plus a structural guard test that fails if any `tasks.push(` appears outside the allow-list (mutation-tested: planting the old bug fails with function + line). |
| 9 | Redundant double `save()` on add | ✅ valid, negligible | No change (micro-perf on a ~100-call tenant). |

**Found while fixing #8 (not in the review):**
- **CSV import** counted every row as "✓ נוספו בהצלחה" even when the insert failed, and sent
  `category_id: ''` (rejected by the uuid column) whenever a row's category name didn't match
  exactly. Those rows were silently lost. Fixed: `category_id || null` in `saveTaskToSupabase`
  (protects every door), honest ok/fail counts, and failed rows are named in the result.
- **Dispatch confirm** showed the success screen for an unsaved call, and on a failed
  queue-reassign it dropped the queue link, so a retry would create a duplicate. Fixed: it stays
  on the result with an error, and the link is kept on failure.
- **Save-pending (💾 שמור ללא שיבוץ)** showed "נשמר מקומית" and then the green success toast
  and cleared the form, though new inserts are not kept anywhere. Fixed: the form is kept, with an
  honest error.
- WAL vs rollback conflict on a failed queue-reassign → backlog.

**Verification:** `tests/addtask.test.js` 22/22 (helper ×4, add-call ×17, structural guard),
zones 65/65, sched 282/282, parse OK. Backend untouched (209 pytest from earlier today stand).
