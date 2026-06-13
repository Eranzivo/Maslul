# UI/UX References — Phase 3+ Design Pass

**Goal:** a clean, friendly, professional SaaS that a **non-technical coordinator/owner can
operate with minimal effort**. Hebrew-first, RTL, mobile-first. Not a copy of the references —
adopt the *feel*. Keep `context/style.md` tokens.

## Reference 1 — SaaS appointment calendar
- Week grid with **colour-coded event blocks** (colour = tech / category / status).
- **KPI strip on top**: total appointments, completed, no-show, avg time — at-a-glance health.
- Overlapping events sit **side-by-side** (we just shipped this via `layoutColumns`).
- Compact, dense but readable; clear time gutter; "today" emphasis.

## Reference 2 — Clean left side-panel
- Search at top; grouped nav (Inbox / Assigned / Created by me / lists).
- Lots of whitespace, light dividers, friendly type, minimal chrome.
- Low cognitive load — obvious affordances, nothing cluttered.

## Principles to apply
1. **Colour conveys meaning** — tech colour + status dot, consistent everywhere.
2. **Obvious affordances** — a non-tech user should never wonder what's clickable/draggable.
3. **Professional framing** — bold-but-tasteful borders, consistent radius/shadow, aligned grids.
4. **Progressive disclosure** — show the essentials; detail on tap. KPI strip → drill in.
5. **Forgiving** — every action reversible/visible (toasts, undo), no silent data loss.

## When
After the editable-calendar engine slices (re-sequence-on-move, lock/unlock). Tracked in
[[ui-design-northstar]] memory and `context/backlog.md`.
