# Free Tools, Capabilities & Polygon Q&A
_Generated: 2026-05-27_

---

## 1. What We're Using Today — Full Stack Audit

| Layer | Tool | Cost | Notes |
|---|---|---|---|
| **Hosting** | GitHub Pages | ✅ Free forever | Static HTML only |
| **Database + Auth** | Supabase (Free tier) | ✅ Free (500MB, 50k MAU) | Upgrade at ~$25/mo when needed |
| **Optimizer backend** | Railway (Trial) | ⚠️ Free trial → **expires June 12** | Upgrade to Hobby $5/mo |
| **Maps** | Leaflet.js + OpenStreetMap | ✅ Free forever | No API key, no limits |
| **GPS tracking** | Browser Geolocation API | ✅ Free forever | Built into every browser |
| **Realtime (GPS push)** | Supabase Realtime | ✅ Free (200 concurrent) | WebSocket, included in Supabase |
| **Error tracking** | Sentry (EU) | ✅ Free (5k events/mo) | Already integrated |
| **Uptime monitoring** | UptimeRobot | ✅ Free (50 monitors) | Already configured |
| **Fonts** | Google Fonts (Heebo) | ✅ Free forever | CDN |
| **AI assistant** | Claude Code (this) | Paid by you | VSCode extension |
| **MCP → Supabase** | @supabase/mcp-server | ✅ Free | Just set up — direct SQL access |
| **Polygon drawing** | Leaflet.draw | ✅ Free forever | Just added — draw zones visually |

**Total monthly infrastructure cost today: ~$0**  
**After June 12 (Railway upgrade): $5/mo**

---

## 2. Free Capabilities We Have (Complete List)

### Scheduling Engine
- ✅ Zone-based scheduling (city list assignment)
- ✅ Route optimization — OR-Tools TSP solver (5s time limit)
- ✅ Haversine distance fallback (no Google Maps key needed)
- ✅ Category limits per tech per day
- ✅ Min/max daily jobs enforcement
- ✅ Far-to-near route ordering within zone
- ✅ Fill existing days before opening new days

### Dispatcher (Coordinator)
- ✅ Task dispatch (assign by city + category → auto-find best tech)
- ✅ Home dashboard with tech workload cards
- ✅ Live coordinator map (techs + today's tasks, GPS updates in real-time)
- ✅ Planner (week/month view, drag-reschedule)
- ✅ Reports (date range, per-tech, CSV export, chart)
- ✅ Route optimizer button ("🔀 מסלול מיטבי") — OR-Tools TSP per tech
- ✅ CSV import for bulk task upload
- ✅ Audit log (every DB change recorded)
- ✅ WhatsApp click-to-send per task

### Tech (Field Worker) View
- ✅ Today's tasks with status progression (assigned → en route → arrived → completed)
- ✅ Tomorrow's tasks preview
- ✅ GPS sharing (📡 שתף מיקום — broadcast location to coordinator map)
- ✅ Route map (numbered stop pins, home base, dashed route line)
- ✅ Waze link per task (opens navigation)
- ✅ Call + WhatsApp per task client
- ✅ **NEW: Job history (📋 היסטוריה)** — past completed tasks, grouped by date, stats

### Zone Configuration
- ✅ City-list zones (paste city names, order = route order)
- ✅ **NEW: Polygon zone drawing (🗺️ צייר)** — draw on map, auto-detect cities inside
- ✅ 200+ Israeli city coordinates in CITY_COORDS_JS

### Multi-Tenant SaaS
- ✅ Full RLS isolation (Supabase row-level security)
- ✅ Per-tenant labels (worker/task/zone terminology)
- ✅ Per-tenant feature flags
- ✅ Demo mode (3 types: general, cleaning, delivery)
- ✅ WAL (write-ahead log) — offline resilience
- ✅ Connection health monitor

---

## 3. Free Capabilities We DON'T Have Yet

| Missing Feature | Effort | How to Add Free | Priority |
|---|---|---|---|
| **Photo upload on task completion** | Medium | Supabase Storage (1GB free) — `<input type="file">` + `supabase.storage.upload()` | HIGH |
| **Digital signature capture** | Small-Medium | HTML Canvas — `canvas.toDataURL()` → save to Supabase Storage | HIGH |
| **Recurring jobs** | Medium | `recurring_tasks` table + `repeat_interval` field, generate next task on completion | Medium |
| **Customer self-booking portal** | Large | New HTML page, public Supabase RLS, booking form | Future |
| **Push notifications (mobile)** | Medium | Web Push API (free via service workers) or OneSignal free tier | Medium |
| **Break time management** | Small | Block 1hr slot in tech schedule, `day_offs` table already supports it | Low |
| **Offline mode (full)** | Large | Service Worker + IndexedDB — PWA approach | Future |
| **Polygon AI auto-optimize** | Large | Clustering algorithm (k-means on task coords) — no external API needed | Future |
| **SMS auto-send** | Small | Twilio free credits (then ~$0.05/msg) — NOT free long term | Near-term |
| **WhatsApp API auto-send** | Medium | WhatsApp Business API — NOT free (₪0.5-3/conversation) | Near-term |

---

## 4. Cheap Tools Worth Adding ($5-15/mo)

| Tool | Cost | What It Adds |
|---|---|---|
| **Railway Hobby** | $5/mo | Keeps optimizer backend alive (MUST do before June 12) |
| **Supabase Pro** | $25/mo | When >500MB or >50k MAU — not needed yet |
| **Twilio** | Pay-per-use | SMS reminders — ~$5/mo for 100 messages |
| **Google Maps** | $200/mo free credit | Replace haversine with real drive-time distances in optimizer |

---

## 5. Polygons — Full Q&A

### Why does Timing.tech use polygons?
Timing.tech serves businesses **globally** — delivery zones in London, service areas in New York. They can't rely on city names because:
- City names differ by language/country
- Service territories don't align with city boundaries (e.g., "north Tel Aviv only, not south")
- Global product needs universal geographic input that doesn't require knowing local city names

### When should YOU use polygons?
✅ **Use polygons when:**
- A client's zone boundary cuts through a city (e.g., "only the industrial zone of Petah Tikva")
- The business has irregular territories that don't map to city lists (e.g., concentric radius zones)
- You have a client with no strong "city thinking" — they define territory visually, not by list
- Future: AI polygon auto-optimizer — cluster past job locations and auto-draw optimal zone boundaries

### When should you use city lists (current approach)?
✅ **City lists are better when:**
- The business thinks in cities — **this is almost every Israeli business**
  - "הטכנאי שלנו עובד בחולון, בת ים, ראשון לציון" — they say this naturally
- The scheduling logic is city-based (zone rotation by city, far-to-near route ordering)
- Configuration is done by non-technical operators — typing "חולון" is simpler than drawing a polygon
- The territories align cleanly with city boundaries (>90% of Israeli SMBs)

### Can you have BOTH at the same time?
**YES — and that's exactly what we built.**

The new "🗺️ צייר" button draws a polygon on the map, then:
1. **Checks all 200+ Israeli cities in CITY_COORDS_JS** against the polygon boundary (ray-casting algorithm)
2. **Adds the matching cities** to the zone's city list
3. The zone now has a normal city list — **all existing scheduling logic unchanged**

So the polygon is just a **better input UI**. Under the hood it's still city lists. This is the right architecture because:
- The scheduling engine (zone rotation, far-to-near, fill score) works on cities
- You don't need to rewrite anything
- The coordinator can mix approaches: draw for geographic territories, type for known city lists

### When NOT to use the draw-polygon approach?
- When a zone territory falls between known cities (polygon captures nothing from CITY_COORDS_JS)
- When precision matters at the neighborhood level (we only have city centroids, not neighborhoods)
- Solution: add more granular coordinates to CITY_COORDS_JS for neighborhoods if a client needs it

---

## 6. What We Built This Session

| Feature | Status |
|---|---|
| MCP → Supabase connection | ✅ Done |
| GPS migration (last_lat, last_lon, last_seen) | ✅ Applied directly to DB |
| Polygon zone drawing (Leaflet.draw) | ✅ Live in index.html |
| Tech job history view | ✅ Live in index.html |
| Railway billing reminders (June 9, 10, 11) | ✅ Scheduled via RemoteTrigger |
| GPS + Live coordinator map | ✅ Done (previous session) |
| Landing page Hebrew/English toggle | ✅ Done (previous session) |
| Timing.tech gap analysis | ✅ `outputs/timing-tech-analysis_2026-05-27.md` |

---

## 7. What's Still Open (Honest Checklist)

- [ ] **Run GPS migration** — ✅ DONE via MCP
- [ ] **Railway upgrade** — do on June 9-11 (reminders set)
- [ ] **Photo upload** on task completion — next up
- [ ] **Digital signature** capture — next up
- [ ] **Break time management** — low effort, low priority
- [ ] **pytest** — `cd backend && pytest tests/ -v`
- [ ] **Polygon AI auto-optimizer** — cluster past jobs → suggest zone boundaries
- [ ] **Client #2 prospecting** — no code needed, sales effort

---

## 8. Superpowers / Extensions Prioritization

| Priority | Tool | What It Does | How to Get |
|---|---|---|---|
| ✅ Done | **Claude Code** VSCode | AI-powered coding assistant | Installed |
| ✅ Done | **MCP Supabase** | Direct DB access from Claude | Done this session |
| 🔜 Next | **MCP GitHub** | PR creation, code review from Claude | `/web-setup` at claude.ai |
| Consider | **Google Drive MCP** | Attach screenshots/docs to Claude context | Connected (see deferred tools) |
| Future | **Gmail MCP** | Draft client communications | Connected (see deferred tools) |
| N/A | **Sentry** | Error tracking | Already in app via SDK (no MCP needed) |
