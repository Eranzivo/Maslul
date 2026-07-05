---
description: Safe re-batch procedure — backup → dry-run → diff → explicit approval → write → verify
---
Re-batching writes to the live calendar. This procedure is the ONLY way to run it (data-persistence + engine-first rules; live DB is not git-revertible).

1. **Snapshot first:** `CREATE TABLE tasks_backup_[yyyymmdd] AS SELECT * FROM tasks WHERE tenant_id='...'` (deliver SQL as chat block; Eran runs or approves MCP). Record the backup name in the report. Drop old stale backups only with explicit approval.
2. **Dry-run:** POST `/batch-schedule` with `dry_run: true` (authorized: service key on Railway, or coordinator user-JWT from the bulk-import UI). If no key is available locally, use the MCP-export → offline-replay pattern (see `outputs/ways-of-working_2026-07-02.md`, 2026-07-05 entry).
3. **Diff report** → `outputs/rebatch-dryrun_[date].md`: proposed vs current per tech-day (counts + cities), `retimed_existing`, every `unassigned` with reason (`needs_location` / `city_not_in_zone` / `day_over_capacity` / `no_slot_in_range`), and anything surprising (a full day gaining calls, a tech at 0, a zone with no coverage).
4. **Sanity gates before asking approval:** existing calls never lose tech/date/window (the engine guarantees it — verify in the diff anyway); no Fri/Sat placements; per-tech caps respected; flagged reasons are explainable (known junk cities etc.).
5. **Explicit approval from Eran** on the diff — then run with `dry_run: false`.
6. **Verify after write:** re-query per-day counts vs the approved diff; spot-check 3 calls (window/time/tech); confirm the app renders the week (deployment checklist if code also shipped). Log the run in the client doc's change log.
