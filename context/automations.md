# Maslul — Automations Registry

> Living list of external-tool automations for Maslul (and adjacent). Started 2026-07-15.
> Convention: keep secrets on Railway/backend; automation tools only orchestrate + summarize.

## Priority
| # | Automation | Status | Notes |
|---|---|---|---|
| 1 | Weekly "State of Maslul" digest | **Feasible now — recommended first** | Low effort, high value; one small backend endpoint + a low-code scenario |
| 2 | Government document filler (MoD/NDA) | **Recorded for reference — Eran develops externally** | Not a Maslul feature; local-only for security |

---

## Automation 1 — Weekly "State of Maslul" digest

**Goal:** a Monday-morning email that surfaces what the raw backlog can't — proactive early
warning, not a status mirror. Grounded in live signal; one AI step writes the summary.

**Why feasible now:** all data sources already exist (git history, Railway `/health`,
`/geo-health`); the only code is a tiny read-only `/digest` endpoint. No secret leaves Railway —
the automation only calls authenticated endpoints, summarizes, and emails.

### Stage 0 — pick the tool (½ hour to set up an account)
- **n8n (recommended)** — self-hostable next to Railway; most secure; free; HTTP + AI + email nodes.
- **Make** — visual, easiest, generous free tier, built-in AI module.
- **Zapier** — most recognizable on a CV; built-in AI ("AI by Zapier"); pricier.
- Decision: n8n if you want control/security; Make if you want fastest visual build.

### Stage 1 — backend `/digest` endpoint (the ONLY code; ~30–45 min — I can build it)
- **Route:** `GET /digest` on the Railway backend.
- **Auth:** mirror `/geo-health` — service-key Bearer OR user-JWT forced to the caller's tenant
  (`resolve_effective_tenant`); techs denied. So the automation calls it with one limited token.
- **Returns** (for the effective tenant), reusing `batch_schedule._sb_get`:
  ```json
  {
    "tenant_id": "...",
    "task_status": {"pending":12,"assigned":40,"en_route":2,"arrived":1,"completed":33,"cancelled":5},
    "unassigned": {"count":12, "oldest_age_days":9},
    "needs_location": 1
  }
  ```
- **Fail-open:** any error ⇒ zeroed payload, never a 500 (same pattern as `/geo-health`).
- Quota + geo attention already come from `/health` + `/geo-health`, so `/digest` stays this small.

### Stage 2 — automation: trigger
- Node: **Schedule** → weekly, **Monday 08:00 Asia/Jerusalem**.

### Stage 3 — gather signals (four HTTP nodes; can run in parallel)
- **3a · What shipped** — HTTP `GET https://api.github.com/repos/Eranzivo/Maslul/commits?since={{7 days ago ISO}}`.
  Public repo ⇒ token optional (add a read-only PAT to avoid rate limits). Keep `commit.message` fields.
- **3b · System health + cost** — HTTP `GET https://maslul-production-77fa.up.railway.app/health` →
  `gmaps` status, `daily_elements_remaining` (quota), version.
- **3c · Geo attention** — HTTP `POST …/geo-health`, body `{"tenant_id":"00000000-…-0001"}`,
  header `Authorization: Bearer <limited token>` → `summary.attention`, `unresolved[]`, `out_of_zone[]`.
- **3d · Ops health** — HTTP `GET …/digest` (same auth) → task-status counts, unassigned, needs_location.

### Stage 4 — AI synthesis (one node)
- Node: n8n/Make AI (or Claude/OpenAI). Feed the merged JSON from 3a–3d.
- **Prompt:** *"You are my product-ops assistant for Maslul. From this JSON write a ~150-word
  email with four headers — **Shipped this week / System health / ⚠ Needs action / Next up**.
  Flag anything urgent: Google Maps quota < 200, geo attention rising, unassigned oldest > 7 days,
  Railway version not matching the latest commit. Plain, direct, Hebrew or English."*
- Output → email subject + body.

### Stage 5 — deliver
- Node: **Email** (Gmail / SMTP) → to Eran. Subject e.g. `Maslul — שבועי {{date}}`.

### Stage 6 — test + activate
- Run the scenario once manually → confirm the email reads well and numbers are right →
  enable the schedule. Iterate the prompt.

**Secrets the automation holds:** a read-only GitHub PAT, one limited backend token, email creds.
The Supabase **service key never leaves Railway**.

**Effort:** endpoint ~½ day incl. tests; scenario ~an afternoon.

**Role-pitch mapping (Moon Active CX role):** "AI tools to spot operational bottlenecks and
proactively resolve before they scale" + "measure operational efficiency / KPIs" — this is a
literal, demonstrable instance.

---

## Automation 2 — Government document filler (MoD / NDA) — EXTERNAL, reference only

> Not a Maslul feature. Recorded here because it was designed in-session; Eran develops it
> externally on his own machine. **Security-first: do NOT route through any cloud tool.**

**Security principle:** Ministry-of-Defense + NDA ⇒ no Zapier/Make/Google-Docs/cloud-LLM.
Build **local-only**. Classified fields **never enter the pipeline** — they stay as manual
placeholders completed by hand.

**Steps**
1. **Answers file (once)** — one YAML/JSON holding only the REUSABLE, non-classified content
   (company blurb, product description, standard Q&A), extracted from the "ready" reference doc.
   Source of truth, reused across all 3 document types.
2. **Templatize each of the 3 blank docs:**
   - Word `.docx` → **`docxtpl`** (Jinja tags `{{ company_description }}` at safe fields; classified
     fields marked `«MANUAL — NDA»`).
   - Fillable PDF (AcroForm) → map field names → answers, fill with a PDF lib; classified left blank+flagged.
   - Flat/scanned PDF → overlay text at coordinates, or rebuild as Word.
3. **Local merge script (Python, offline)** → renders one draft per document, classified parts flagged TODO.
4. **Finish manually** — fill NDA/classified fields by hand, review, submit.

**Optional AI (safe):** draft/polish the reusable non-classified prose with a **local LLM**
(Ollama + Llama/Mistral) so nothing leaves the machine. A cloud model, if ever, only for generic
company/product boilerplate — never form content.

**Security checklist:** encrypted disk · answers file holds zero classified data · classified fields
handled only manually · no NDA data to any SaaS · drafts in one controlled folder.

**Open question that decides the tooling:** are the 3 docs **Word**, **fillable PDF**, or
**flat/scanned PDF**? That picks the library + starter script.
