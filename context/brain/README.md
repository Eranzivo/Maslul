# 🧠 The Maslul Brain — visual product map

**What this is:** `maslul-brain.canvas` is the one-glance neuron map of the whole
product — product goal → engine doors → knobs → geo brain → route intelligence →
auth → app → tests — with clickable file nodes into the real `context/` docs.

## How to open (Eran, one-time, ~2 minutes)
1. Install [Obsidian](https://obsidian.md) (free).
2. **Open folder as vault** → pick `My Workspace` (this repo's root).
3. Open `context/brain/maslul-brain.canvas` → the map. Click any 📄 node to jump
   into the real doc. Pin it as a tab.
4. Bonus: the **graph view** (Ctrl+G) shows every `[[wikilink]]` connection across
   the docs automatically — nothing to maintain, it reads the markdown as-is.

`.obsidian/` (your local UI state) is gitignored — open/rearrange freely, nothing
you do in Obsidian's UI touches the repo.

## Maintenance rule (living-docs, same commit)
The brain follows the living-docs rule: **an architecture-level change updates its
brain node in the same commit** — new subsystem = new node/group; retired thing =
node removed. Detail stays in `context/` docs (the brain links to them); the canvas
holds only the one-sentence truth per neuron. Any Claude session (Fable or Opus)
edits the canvas via the vendored `json-canvas` skill (validation checklist included).

## Conventions
- Canvas file nodes use **repo-root-relative paths** (`context/knobs.md`) — the
  vault root IS the repo root; moving the vault breaks nothing else.
- Wikilinks in `context/` + memory docs (`[[knob-registry-parity]]` style) power
  the graph view; keep using them liberally.
- Colors: purple=product · yellow=docs · cyan=engine/app · green=geo/tests ·
  red=route-intelligence · orange=auth.

## Vendored skills powering this
`.claude/skills/json-canvas` + `.claude/skills/obsidian-markdown` — instruction-only,
security-read + pinned (provenance in `.claude/skills/VENDORED.md`).
