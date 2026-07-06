# Workspace Setup — adopt my proven "way of working" (from my Maslul workspace)

You're joining an EXISTING project: HomeOS — a personal home-management app for me and my
wife (income/expenses, financial status, investments, document vault). First features are
already built. Your job this session: (1) install the working method below into this
workspace, (2) audit what exists, (3) then improve the product with me.

## Step 1 — Install the working infrastructure (do this first)
1. **`CLAUDE.md` (lean, ~80 lines max, always):** points to context/, holds only the rules
   below + a tiny "what this is / stack / urgent" section. Never let it bloat.
2. **`context/` folder — the living memory of the project:**
   - `README.md` — top-down map (what the product is → architecture → conventions → open work)
   - `vision.md` — what HomeOS is for, who uses it (2 users: me + wife), what "done well" means
   - `architecture.md` — stack, schema (every table: columns, RLS, who reads/writes), hard rules
   - `backlog.md` — prioritized queue + milestone log (dated)
   - `decisions.md` — dated log of product/tech decisions with the WHY
   Derive the initial content by READING THE ACTUAL CODE + DB, not by asking me.
3. **`.claude/commands/prime.md`** — a /prime skill: read CLAUDE.md + all context/ files,
   then confirm understanding in 3-4 sentences before any task.
4. **`outputs/` folder** — every artifact (plans, reports, migrations, designs) goes to
   `outputs/[task-name]_[YYYY-MM-DD].[ext]`. Never scatter files elsewhere.

## Step 2 — The standing rules (write them into CLAUDE.md verbatim-ish)
- **Context first:** read context/ before touching code, every session (/prime).
- **Living docs:** every code change updates its ONE relevant context/ doc in the same
  commit. Docs that rot are worse than no docs.
- **One slice per session:** state the goal, do it end-to-end (design → test → code → docs
  → deploy-verify), commit often. Design notes to outputs/ BEFORE code on anything non-trivial.
- **TDD:** failing test → minimal code → green → commit. Full test suite before claiming done.
- **DB discipline:** migrations are additive + reversible where possible; readback-verify
  every write; back up before destructive changes; SQL for me = code block in chat, never a
  file link. Dry-run risky changes (transaction + ROLLBACK with checks) before applying.
- **Security every step (financial data + document vault = highest sensitivity):**
  - repo must be PRIVATE (verify — this is not Maslul's public repo); secrets only in .env
  - run Supabase security + performance advisors after ANY schema/policy change
  - RLS on every table, household-scoped; test policy changes with role simulations
    (DO block + SET LOCAL ROLE authenticated + set_config jwt claims + row-count checks +
    RAISE EXCEPTION report = atomic rehearsal, zero risk)
  - doc vault: storage bucket policies verified same way; never public buckets
- **Data safety:** always await DB saves before UI success states; never show raw backend
  errors to users (generic message + console/log for me); plan for backups (free-tier
  Supabase has none — flag when the data becomes irreplaceable).
- **UI testing rule:** after any UI change, verify every button/link on affected pages
  actually works. Report what you tested.
- **Explanations:** plain language first, then technical, always with pros/cons — I'm
  learning the system as we build.
- **Proactive upgrades:** when you see a significant improvement, propose it: what, steps,
  cost. Don't silently skip opportunities.
- **Session end:** update context/ files + keep CLAUDE.md lean; log the session's lessons
  in outputs/ways-of-working_[date].md (append-only) so future sessions inherit the craft.
- **Verify deploys** by something only the new build can show, not by "it probably worked".

## Step 3 — First audit (this session, after setup)
Read the whole codebase + Supabase schema and produce
`outputs/homeos-review_[date].md`: what exists, what's fragile (security, data-loss risks,
missing RLS/backups FIRST — it's our family's financial data), what to improve next,
prioritized. Then we pick the first slice together.

Environment notes: Supabase project exists (find via MCP list_projects → "HomeOS").
Hebrew/RTL conventions apply if the UI is Hebrew — check the code, don't assume.
