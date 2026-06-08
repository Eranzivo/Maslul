# Maslul — Backlog & History

## 🟠 Next
- [ ] Israel fills in client details on 108 tasks (via ✏️ edit button)
- [ ] Israel testing — real dispatch scenarios, feedback collection
- [ ] Equal city distribution — config flag `scheduling.equal_city_distribution` to spread same-city tasks across techs
- [ ] Admin panel chips redesign — plan at `.claude/plans/ancient-plotting-prism.md`
- [ ] Web Push notifications — alert tech when task assigned

## 🟡 After Israel stabilizes
- [ ] Tech view redesign
- [ ] Dashboard & analytics — charts, KPIs (like timing.tech)
- [ ] Customer ETA portal — SMS/WhatsApp link → customer sees tech ETA + can rate

## 🟡 After Client #2
- [ ] Custom domain (maslul.co.il) + Cloudflare
- [ ] Client #2 onboarding — `context/clients/[name].md` + SQL script
- [ ] SMS auto-send (Twilio, ~$5/mo for 100 msgs)

## 🔵 Future
- [ ] AI call summary in tech view
- [ ] Customer self-booking portal
- [ ] Native mobile app (PWA first)
- [ ] WAL tenant isolation on replay

---

## Milestone Log
| Date | What shipped |
|---|---|
| 2026-05-27 | GPS tracking, photo upload, job history, polygon zone drawing, digital signature |
| 2026-05-28 | WhatsApp template, tenant separation (Eran ↔ Israel impersonation) |
| 2026-06-01 | Configurable scheduling engine (modes, route_strategy, duration overrides), recurring jobs, pending queue, cities autocomplete, Maps quota, break time, code review |
| 2026-06-04 | UI/UX overhaul — SVG sidebar, KPI cards, tech cards, two-column dispatch |
| 2026-06-06 | PureWater zone setup — 9 zones, 3-tech rotation, city normalization |
| 2026-06-07 | Dispatch UX, task edit modal, 108 tasks seeded, polygon fix, 255 cities, geo-intelligence layer |
| 2026-06-08 | Service windows (DB + dispatch), 72/48/24h slot release (PureWater config), backtrack detection, return_city OR-Tools end depot, calendar rebuilt (absolute grid, one-tech, all tasks visible), auth-users + zones-polygons context files, 108 real tasks seeded |
