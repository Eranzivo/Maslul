# outputs/archive — superseded artifacts (kept, never deleted)

- **migrations/** — ALL applied SQL migrations (history; never delete an applied migration). Context docs reference them at `outputs/archive/migrations/...`.
- Root of archive/ — superseded plans/designs whose work shipped (the living state lives in `context/`); kept for provenance.
- Active docs stay in `outputs/`: worklog.md (parked ideas + triggers), task queues, requirement sources (israel-handover*, product reviews, ways-of-working), infra/vision roadmaps, CSV inputs for the future geo-alias pass, backups (*.json).
- `outputs/purewater-review_2026-06-29/` is **gitignored client data — never commit** (now also holds the demand-dashboard PDF + the Fable-review handoff).

Cleanup executed 2026-07-08 (rules: memory `workspace-cleanup-for-opus` + backlog Foundations item).
