# Vendored external skills — provenance & security record

> House rule: external skills are **vendored** (copied into git, pinned), never
> marketplace-auto-updated. Any upstream change must arrive as a reviewable diff
> in a commit. Read every file before vendoring; re-run the security pass on any
> update. Instruction-only skills only — anything that executes code (hooks,
> scripts) needs an explicit case-by-case decision with Eran.

| Skill | Source | Pinned commit | License | Security pass |
|---|---|---|---|---|
| `json-canvas` | github.com/kepano/obsidian-skills | `a1dc48e68138490d522c04cbf5822214c6eb1202` | MIT | 2026-07-09 (Fable): SKILL.md read in full + references grep-scanned — format documentation only; no shell/network/exec instructions; byte sizes match upstream |
| `obsidian-markdown` | github.com/kepano/obsidian-skills | `a1dc48e68138490d522c04cbf5822214c6eb1202` | MIT | 2026-07-09 (Fable): same — clean |

Not vendored (decided 2026-07-09): `obsidian-cli` (needs a CLI binary — no need),
`obsidian-bases` (no .base use yet), `defuddle` (web clipping — irrelevant),
`ponytail` (runs Node lifecycle hooks = code execution; its YAGNI/reuse ideas are
already in fable-mode + CLAUDE.md).
