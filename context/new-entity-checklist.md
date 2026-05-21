# New Entity / New Table Checklist

Run this checklist every time a new Supabase table or entity type is added to Maslul.
Missing any step is the root cause of every data-loss bug we've fixed.

---

## 8 Required Steps (all must be done before shipping)

### 1. schema.sql
- [ ] New table added with `id UUID PRIMARY KEY DEFAULT gen_random_uuid()`
- [ ] `tenant_id UUID NOT NULL REFERENCES tenants(id)`
- [ ] RLS enabled: `ALTER TABLE <table> ENABLE ROW LEVEL SECURITY`
- [ ] RLS policy: `USING (get_tenant_id() = tenant_id)` on SELECT/INSERT/UPDATE/DELETE
- [ ] All columns have explicit NOT NULL or defaults (no silent nulls)

### 2. loadFromSupabase — load mapping
- [ ] Table fetched in the `Promise.all([...])` block
- [ ] Every column mapped from snake_case DB name to camelCase JS name
- [ ] `_dbId: row.id` set so updates go to the correct row
- [ ] Fallback defaults on nullable fields: `|| []`, `|| {}`, `|| ''`

### 3. saveXToSupabase — save function
- [ ] Uses `dbUpsert` (if `entity._dbId` is set) or `dbInsert` (new record)
- [ ] Every column that was loaded is also written back (load↔save symmetry)
- [ ] After `dbInsert`, `entity._dbId = data.id` AND `entity.id = data.id`
- [ ] If the entity has child references (e.g., tasks referencing a tech), update them too

### 4. Save caller — honest toast
- [ ] Shows "שומר…" toast BEFORE the async call (or uses save-indicator)
- [ ] Shows "נשמר ✓" toast ONLY inside `.then(ok => { if(ok !== false) ... })` — not synchronously
- [ ] Never shows success before the Supabase round-trip completes

### 5. currentTenantId guard
- [ ] `if (!currentTenantId) return;` is the FIRST line of the save function
- [ ] OR covered by `dbUpsert` / `dbInsert` (which already guard)

### 6. Schema validator update
- [ ] Add the new entity to the `check(...)` calls inside `_validateSchema()` in `loadFromSupabase`
- [ ] List the required fields that must never be null on an existing record

### 7. Smoke test update
- [ ] Add a new test block in `test/smoke.html` for the new entity
- [ ] Test: insert → read back → update a field → verify → delete
- [ ] Run the smoke test against staging before merging

### 8. context/architecture.md update
- [ ] Add new table to the Supabase Tables section
- [ ] Document any non-obvious fields or constraints

---

## Common Mistakes (don't repeat these)

| Mistake | Consequence | Fix |
|---|---|---|
| Column in `loadFromSupabase` but not in save row | Field silently lost on next refresh | Add to save row |
| `showToast('נשמר')` before `await` | False success even on network failure | Move toast into `.then()` |
| No `currentTenantId` guard | Saves as null tenant, blocked by RLS silently | Add guard or use `dbUpsert` |
| `parseInt()` on a UUID tech ID | NaN, wrong row updated | Use `String(a) === String(b)` |
| `onclick="fn(${id})"` without quotes | UUID parsed as arithmetic, NaN | Always `onclick="fn('${id}')"` |
| Insert/update split logic | Race condition on rapid saves | Always use `dbUpsert` with `onConflict:'id'` |
