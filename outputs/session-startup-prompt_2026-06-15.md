# Next-session startup prompt (paste this to begin)

> Copy everything in the code block below into a fresh Claude Code session. It loads full context
> (no reliance on `/prime`), is design-aware, and ends by asking where we are + the next step.
> Keep it; update the "Where we are" line as work ships (or just trust the files — they're the truth).

```
You're resuming work on **Maslul** — a Hebrew-first, RTL SaaS field-scheduling app for Israeli SMBs
(single `index.html`, vanilla JS, no build; Supabase + RLS; FastAPI + OR-Tools optimizer on Railway;
GitHub Pages deploys on push to main). Before doing ANYTHING, load context:

1. Read CLAUDE.md and ALL of context/ — especially:
   - context/design-system.md  ← the LIVING DESIGN DOC: rules, source-of-truth map, which
     skill/superpower to use for design work, and the design change log. READ THIS FIRST for any
     UI/design task (restyle, move a block/page, new screen).
   - context/style.md (tokens) · context/architecture.md · context/scheduling-rules.md
   - context/backlog.md (the todo board — current state + Phase-2 items)
   - context/clients/purewater.md (the pilot's live config + change log)
2. Read mockups/DESIGN-LOG.md (8 approved screens + Phase-2 IA) and
   outputs/ui-port-plan_2026-06-15.md (mockup → index.html function → engine wiring map).
3. Read your memory index MEMORY.md, then the memories: ui-redesign-port, ui-design-northstar,
   product-philosophy, ai-dispatcher-northstar, feedback_engine-work-process.

WHERE WE ARE (as of 2026-06-15): the 8-screen UI redesign is ported (md-* namespaced foundation +
detail panel, weekly/daily grids, coordinator 3-card chooser, home, sidebar). Bulk-import now feeds
the batch decision engine (⚡ שבץ אוטומטית → dry-run preview → commit; backend accepts the user's own
Supabase JWT and forces their tenant). Calls-tab action row decluttered. PureWater Friday set
explicitly off (Sun–Thu only). All pushed live. Next on the board = Phase-2 IA:
move חופשות → Technicians view; compact top-nav; re-order pages by area (תפעול/CRM/הגדרות);
configurable working-days in Settings/tech-level (NOT a vacations-style feature).

HOW TO WORK:
- DESIGN/UI change → first read context/design-system.md and follow its hard rules: namespace new
  CSS md-*, never break existing handlers/IDs (grep to confirm), keep daily-grid geometry (PX=1,
  60px/hour), RTL time = direction:ltr + tnum, run the UI-testing rule (click every button),
  parse-check inline JS, commit per slice. After the change, append a row to the design change log.
- Small contained restyle (move/relabel a block) → do it INLINE.
- New screen or big redesign → use brainstorming → writing-plans → subagent-driven-development
  (fresh subagent per slice, spec-review then code-quality-review). For fresh mockups use
  claude.ai/design (web tool), hand off HTML, port onto md-* + tokens.
- HARD GUARDRAIL: the engine is a generic "brain"; ALL per-client behavior lives in tenants.config.
  Nothing may break for Clients #2–5 with completely different config. UI = git-reversible; live DB
  data = NOT reversible (dry-run/preview before any live write; Supabase is Free tier, no backups).
- Deploy = push to main (GitHub Pages + Railway). Confirm pushes; QA live in incognito (?clearall=1).

Start by telling me: where we are on the todos (read backlog.md), and your recommended next step +
which skills/superpowers you'll activate for it. Then WAIT for my go before building.
```

## If the task is specifically "change a design / move a block to another place"
Add this line to the prompt: *"I want to redesign/move <name the block or page>. Read
context/design-system.md, propose the change (location, before/after, which md-* classes, what stays
wired), and confirm it's a contained restyle (inline) vs a new-screen job (brainstorm→plan→subagents)
before touching index.html."*
