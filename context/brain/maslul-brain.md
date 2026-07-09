# 🧠 Maslul Brain — Mermaid mirror (GENERATED)

> **Do not edit.** Source: [maslul-brain.canvas](maslul-brain.canvas) (open the repo as an Obsidian vault for the rich view). Regenerate with `python tools/brain_mermaid.py` — same commit as any canvas change.
> Renders natively on GitHub; in VS Code install the *Markdown Preview Mermaid Support* extension and hit Ctrl+Shift+V.

```mermaid
flowchart TD
  subgraph G0["🎯 Product"]
    n0["Maslul — Hebrew-first AI dispatch cockpit for Israeli SMB field teams."]
    n1["Clients"]
  end
  subgraph G1["📚 Context spine — read before work"]
    n2["📄 README.md"]
    n3["📄 architecture.md"]
    n4["📄 scheduling-rules.md"]
    n5["📄 scheduling-scenarios.md"]
    n6["📄 knobs.md"]
    n7["📄 auth-users.md"]
    n8["📄 design-system.md"]
    n9["📄 purewater.md"]
  end
  subgraph G2["🧠 Scheduling engine — TWO doors, ONE rule set"]
    n10["Live JS door — index.html ‹sched-logic›"]
    n11["Batch door — backend/batch_schedule.py"]
    n12["Solver — backend/optimizer.py"]
    n13["Auto-sequence seam"]
  end
  subgraph G3["🌍 Shared geo brain — global Layer-A, tenant-free"]
    n15["geo_places (1,310) + place_aliases → geo_resolver (city → coords). Cur…"]
    n16["geo_addresses — street-level KB; /geocode is cache-first, IL-bbox-trus…"]
    n17["route_cache — drive-minutes matrix. Google hard caps: 680 elements/day…"]
  end
  subgraph G4["🩺 Route Intelligence — P1 shipped 2026-07-09"]
    n18["route_health.py — Python-ONLY score 0–100 (excess drive vs solver best…"]
    n19["route_audits table + /audit-day + nightly sweep 02:30 UTC. Per-tenant …"]
    n20["UI: מסלול chip + Hebrew findings panel (display-only)."]
  end
  subgraph G5["🔐 Tenancy & auth"]
    n21["RLS everywhere — current_tenant_id() / current_user_role() / is_super_…"]
    n22["Roles: admin · coordinator (view-only settings) · technician."]
  end
  subgraph G6["🖥️ App"]
    n23["index.html — ONE file, vanilla JS, no build step. GitHub Pages, RTL He…"]
    n24["Redesign Round 1 — 3 Home directions artifact with Eran."]
  end
  subgraph G7["✅ Parity & tests"]
    n25["Golden fixtures = the two-door contract: duration · policy · prefwindo…"]
    n26["196 sched + 65 zones (node) · 178 pytest."]
  end
  n14["⚙️ Knob registry — context/knobs.md"]
  n14 -->|"reads tenants.config"| n10
  n14 -->|"same knobs, batch reader"| n11
  n10 -->|"markDayDirty"| n13
  n13 -->|"/optimize"| n12
  n11 -->|"solve_day_with_existing"| n12
  n17 -->|"travel matrix"| n12
  n15 -->|"coords"| n11
  n12 -->|"same solve, diffed = audit"| n18
  n18 -->|"stores"| n19
  n19 -->|"renders (RLS read)"| n20
  n25 -->|"pins parity"| n11
  n21 -->|"gates every table"| n13
  n23 -->|"hosts"| n10
  n1 -->|"philosophy → knobs"| n14
  n0 -->|"documented in"| n2
  click n2 "../../context/README.md"
  click n3 "../../context/architecture.md"
  click n4 "../../context/scheduling-rules.md"
  click n5 "../../context/scheduling-scenarios.md"
  click n6 "../../context/knobs.md"
  click n7 "../../context/auth-users.md"
  click n8 "../../context/design-system.md"
  click n9 "../../context/clients/purewater.md"
```
