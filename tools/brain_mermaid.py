"""Generate context/brain/maslul-brain.md (Mermaid mirror) from maslul-brain.canvas.

The .canvas is the SOURCE (rich editing in Obsidian); the .md is a generated
mirror so the brain renders in VS Code preview and directly on GitHub. Never
edit the .md by hand — edit the canvas, then run:

    python tools/brain_mermaid.py

Living-docs rule: canvas change + regenerated mirror land in the SAME commit.
"""
import io
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CANVAS = os.path.join(ROOT, "context", "brain", "maslul-brain.canvas")
OUT = os.path.join(ROOT, "context", "brain", "maslul-brain.md")


def _label(node) -> str:
    if node["type"] == "file":
        return os.path.basename(node["file"])
    if node["type"] == "group":
        return node.get("label", "group")
    text = node.get("text", "")
    first = next((l for l in text.split("\n") if l.strip()), "")
    first = re.sub(r"[*`#]", "", first).strip()
    # Mermaid labels render as HTML — literal angle brackets break/parse as tags.
    first = first.replace("<", "‹").replace(">", "›")
    return first[:70] + ("…" if len(first) > 70 else "")


def _inside(n, g) -> bool:
    return (g["x"] <= n["x"] and n["x"] + n["width"] <= g["x"] + g["width"]
            and g["y"] <= n["y"] and n["y"] + n["height"] <= g["y"] + g["height"])


def main():
    c = json.load(io.open(CANVAS, encoding="utf-8"))
    nodes = [n for n in c["nodes"] if n["type"] != "group"]
    groups = [n for n in c["nodes"] if n["type"] == "group"]
    mid = {n["id"]: f"n{i}" for i, n in enumerate(nodes)}

    def render(n) -> str:
        lab = _label(n).replace('"', "'")
        if n["type"] == "file":
            return f'{mid[n["id"]]}["📄 {lab}"]'
        return f'{mid[n["id"]]}["{lab}"]'

    lines = ["flowchart TD"]
    placed = set()
    for gi, g in enumerate(groups):
        glabel = (g.get("label") or "group").replace('"', "'")
        lines.append(f'  subgraph G{gi}["{glabel}"]')
        for n in nodes:
            if n["id"] not in placed and _inside(n, g):
                lines.append(f"    {render(n)}")
                placed.add(n["id"])
        lines.append("  end")
    for n in nodes:
        if n["id"] not in placed:
            lines.append(f"  {render(n)}")
    for e in c.get("edges", []):
        f, t = mid.get(e["fromNode"]), mid.get(e["toNode"])
        if not f or not t:
            continue
        lab = (e.get("label") or "").replace('"', "'")
        lines.append(f'  {f} -->|"{lab}"| {t}' if lab else f"  {f} --> {t}")
    for n in nodes:  # clickable file nodes (GitHub + VS Code resolve repo-relative)
        if n["type"] == "file":
            lines.append(f'  click {mid[n["id"]]} "../../{n["file"]}"')

    body = "\n".join(lines)
    md = (
        "# 🧠 Maslul Brain — Mermaid mirror (GENERATED)\n\n"
        "> **Do not edit.** Source: [maslul-brain.canvas](maslul-brain.canvas) "
        "(open the repo as an Obsidian vault for the rich view). Regenerate with "
        "`python tools/brain_mermaid.py` — same commit as any canvas change.\n"
        "> Renders natively on GitHub; in VS Code install the *Markdown Preview "
        "Mermaid Support* extension and hit Ctrl+Shift+V.\n\n"
        "```mermaid\n" + body + "\n```\n"
    )
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(md)
    print(f"wrote {OUT}: {len(nodes)} nodes, {len(groups)} groups, {len(c.get('edges', []))} edges")


if __name__ == "__main__":
    main()
