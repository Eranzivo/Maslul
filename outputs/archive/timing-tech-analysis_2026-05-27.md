# Timing.tech Gap Analysis & Maslul Re-Prioritization
_Generated: 2026-05-27_

---

## What Timing.tech Has (End-Goal Product)

| Capability | Timing.tech | Maslul Today |
|---|---|---|
| **Scheduling engine** | AI-powered, dynamic polygons | ✅ Zone-based + OR-Tools optimizer |
| **Back office web app** | ✅ Full dispatcher UI | ✅ index.html |
| **Field worker app** | ✅ Native iOS/Android app | ⚠️ Web (mobile-friendly, not native) |
| **Customer portal** | ✅ Self-service booking + tracking | ❌ Not built |
| **Automated booking** | ✅ Customer books online, auto-assigned | ❌ Manual dispatcher only |
| **Digital signatures** | ✅ In-field sign-off | ❌ Not built |
| **Payment processing** | ✅ Integrated billing | ❌ Not built |
| **AI dynamic polygons** | ✅ Auto-optimize zone boundaries | ⚠️ Manual zone assignment |
| **Multi-language** | ✅ | ✅ Hebrew-first, config-driven labels |
| **Multi-tenant SaaS** | ✅ | ✅ Supabase RLS, tenant_id |
| **WhatsApp integration** | ✅ | ✅ Click-to-send |
| **Route optimization** | ✅ | ✅ OR-Tools TSP + haversine |
| **Day-off / availability** | ✅ | ✅ day_offs table |
| **Category limits per tech** | ❓ | ✅ cat_limits JSONB |
| **Reports + CSV export** | ✅ | ✅ Built |
| **Audit log** | ✅ | ✅ DB triggers |
| **WAL / offline resilience** | ❓ | ✅ ml_wal_v1 |
| **CRM (client records)** | ✅ | ⚠️ Basic client fields on tasks |
| **Pricing** | ~$50-200/mo per business | Target: ₪150-300/mo |

---

## Honest Gap Assessment

### Gaps that block Client #2 **right now**
None. The current stack is sufficient to onboard a second client with a different business type (different labels, zones, categories). Zero code changes needed.

### Gaps that hurt product-market fit in 6 months
1. **No customer-facing portal** — clients must call/WhatsApp to book. Timing.tech owns this flow end-to-end.
2. **No native mobile app** — field techs use a web page. Works but feels "less" than a native app.
3. **No in-app payment** — billing happens offline. Not blocking for Israeli SMBs right now.
4. **Manual zone boundaries** — AI auto-polygon is a premium differentiator, not a day-1 need.

### Where Maslul can win vs Timing.tech
1. **Price** — Timing.tech targets larger businesses; Maslul targets 2–20 worker SMBs at ₪150-300/mo
2. **Hebrew-first** — genuine RTL, Hebrew UI, Israeli city/zone logic built-in
3. **Simplicity** — onboarding a new client takes minutes, not a 3-day setup
4. **WhatsApp-native** — Israeli SMBs live in WhatsApp; Timing.tech treats it as an add-on
5. **Odoo/local ERP bridge** — Israeli businesses use Odoo, QuickBooks local, Priority; Maslul can bridge without replacing

---

## Task Re-Prioritization Table

### IMMEDIATE (while waiting for Israel to go paying + searching for Client #2)

| # | Task | Why Now | Effort |
|---|---|---|---|
| 1 | **Stabilize & validate with Israel** | Turn pilot → paying. Get their real feedback. Everything else waits on this. | 0 (ongoing) |
| 2 | **Client #2 prospecting** | Target: cleaning co, pest control, AC installer. Demo mode already supports these. | Sales effort |
| 3 | **Polish demo mode** | First impression for cold prospects. Should be flawless. | Small |
| 4 | **WhatsApp message templates** | Israel asked for this. Quick win. Copy-paste message with MSL ID + arrival time. | Small |
| 5 | **Planner UX polish** | Techs use this daily on mobile. Any friction = complaints. | Small |
| 6 | **Upgrade Railway → Hobby $5/mo** | Must happen before June 12. Reminder set. | 2 min |

### NEAR-TERM (after first paying client confirmed)

| # | Task | Why | Effort |
|---|---|---|---|
| 7 | **CRM: client history** | "Who called before? What did we install?" — asked by every service business. | Medium |
| 8 | **SMS/WhatsApp auto-send** | Remove the "click-to-send" friction; automate after dispatch. | Medium |
| 9 | **Recurring jobs** | Maintenance contracts: "come every 3 months". High value for water systems. | Medium |
| 10 | **Tech GPS / live tracking** | Real-time location on the dispatcher map. Major trust signal for clients. | Medium–Large |
| 11 | **Odoo API sync** | Israel specifically — auto-push MSL-XXXXX assignments to Odoo. Optional module. | Large |

### FUTURE (after 2+ paying clients, pre-Series-A thinking)

| # | Task | Why | Effort |
|---|---|---|---|
| 12 | **Customer portal** | Self-service booking. Closes the biggest gap vs Timing.tech. | Large |
| 13 | **Native mobile app** | PWA first (wraps index.html), then React Native if needed. | Large |
| 14 | **AI zone auto-optimizer** | Replaces manual zone drawing. Timing.tech's moat. | Large |
| 15 | **In-app billing** | Stripe or local Israeli payment. Completes the loop. | Large |
| 16 | **Modular frontend** | Split index.html → ES modules. Trigger: 2nd dev or 2+ paying clients. | Large |

---

## Client #2 Folder Strategy

### Recommendation: folders inside `context/`, NOT git branches

**Why not branches:**
- Client-specific code → you'd maintain diverging forks. Nightmare.
- Business logic is param-driven; only the config/labels differ per client.
- Git branches are for code versions, not customer configs.

**Correct pattern:**

```
context/
  business.md              ← product-wide
  architecture.md          ← product-wide
  scheduling-rules.md      ← product-wide
  new-entity-checklist.md  ← product-wide
  client-israel.md         ← Israel-specific (current)
  client-[name].md         ← Client #2-specific (when added)
```

**What goes in each `client-[name].md`:**
- Business type, industry, team size
- Custom labels (worker/task/zone terminology)
- Zone structure + technician names/cities
- Service categories + durations
- Special scheduling rules (if any)
- tenant_id
- Odoo / ERP integration notes
- Any edge cases or constraints

**What does NOT go there:**
- Secrets (tenant passwords, API keys) → `.env` only
- Code — the same `index.html` serves all clients via tenant config

**When onboarding Client #2, tell me:**
> "New client: [business name]. They are a [type] company, [N] workers, based in [city]. Their terminology: workers are called [X], jobs are called [Y]. Their zones are [zones]. Categories: [list]. Any special rules: [describe]."

That's all. I create the `context/client-[name].md`, run the SQL onboarding script (1 `tenants` insert + 1 `users` insert), and the product is live for them.
