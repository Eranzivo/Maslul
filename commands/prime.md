# Command: /prime

## What it does
Bootstrap command — loads the full project context into Claude at the start of every new conversation.

## When to use
Run `/prime` at the start of every new Claude Code session before giving any task.

## How it works
Claude reads these files in order:
1. `CLAUDE.md` — working rules, architecture principles, invariants
2. `context/business.md` — product description, target audience, goal
3. `context/architecture.md` — tech stack, file map, hard rules, gotchas
4. `context/scheduling-rules.md` — scheduling logic (do not break)
5. `context/client-israel.md` — current pilot client details

Claude then confirms understanding in 3–5 sentences before any work begins.

## Note
The actual slash command lives in `.claude/commands/prime.md` — that's what Claude Code invokes when you type `/prime`.
This file is just documentation.
