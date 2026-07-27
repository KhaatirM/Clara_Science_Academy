# React + Tailwind Migration Plan

Summer 2026 hybrid migration: Flask backend stays; management UI moves to React + Tailwind incrementally.

## Timeline

| Phase | Dates | Action |
|-------|-------|--------|
| Branch work | Jun 15 → Jun 29 | All migration work on `feature/react-tailwind-migration` |
| Steady merges | Jun 30 → Aug 2 | Merge completed slices to `main` |
| Cutover | Aug 3 | Final merge; management fully on React |

## Branch strategy

- **Branch:** `feature/react-tailwind-migration`
- **No merges to `main` before Jun 30** (report card period)
- **Jun 30+:** one merge per completed slice (infrastructure, then pages)

## August 3 scope

### Migrate to React (must-have)

- Shared layout shell (sidebar, auth, permissions)
- Teachers & Staff
- Classes
- Students (management)
- Report Cards (list + generate)
- Family Portal admin hub
- Settings
- Management dashboard home

### Stay on Jinja until fall

- Parent login dashboard (already polished)
- Student portal (Jinja refresh)
- Teacher flows
- Tech dashboard
- Quiz / discussion / submission flows
- PDF templates

## Merge schedule (starting Jun 30)

| # | Target | What merges |
|---|--------|-------------|
| 1 | Jun 30 | Frontend scaffold + Flask `/app` serving + `/api/spa` (no route cutover) |
| 2 | Jul 3–5 | Teachers & Staff in React |
| 3 | Jul 8–10 | Classes |
| 4 | Jul 14–16 | Students (management) |
| 5 | Jul 18–20 | Report Cards |
| 6 | Jul 22–24 | Family Portal admin |
| 7 | Jul 26–28 | Settings + management home |
| 8 | Jul 29–31 | Stretch: Attendance or Calendar v1 |
| 9 | Aug 1–2 | QA, feature flags, fixes |
| 10 | Aug 3 | Final cleanup |

## Architecture

```
frontend/          Vite + React + TypeScript + Tailwind
static/spa/        Production build output (gitignored)
api_spa/           JSON session API for React
spa_routes.py      Serves /app/* from static/spa
templates/         Legacy Jinja until each page cut over
```

## Development commands

```powershell
# Flask
python app.py

# React (hot reload)
cd frontend
npm run dev
# → http://localhost:5173/app/

# Production build
cd frontend
npm run build
# → http://127.0.0.1:5000/app/
```

## Per-page parity checklist

When migrating a page:

- [ ] List/view matches legacy data
- [ ] Create/edit forms work
- [ ] Server-side permissions enforced on all new API routes
- [ ] CSRF on mutating requests
- [ ] Flash/error states in UI
- [ ] Mobile layout acceptable
- [ ] Legacy route still works behind feature flag until sign-off

## Future: App Store

This migration supports a later Capacitor wrap (parent/student mobile). Build JSON APIs as pages migrate; do not block summer work on mobile.

## Status

- [x] Branch created
- [x] Vite + React + Tailwind scaffold
- [x] Flask serves `/app/*` when `REACT_SPA_ENABLED`
- [x] `/api/spa/me` session endpoint
- [x] Layout shell + placeholder routes
- [x] Teachers & Staff list (search, view, remove; add/edit via legacy forms)
- [x] Calendar slice (calendar, school years, closure dashboard)
- [x] Students (management): list, detail/edit modals, add form, CSV, redirects
- [x] Management dashboard home (legacy mgmt-home shell, quick actions, feeds API)
- [x] Family Portal admin (Tailwind SPA — hub, stats, bulk provision)
- [x] Classes (Tailwind SPA — hub, filters, cards, create modal, view/edit/roster/grades/core-setup)
- [x] Attendance (Tailwind SPA — school day save, class period hub, reports, analytics)
- [x] Report Cards (Tailwind SPA — hub, category rosters, recent list; generate/view/PDF remain legacy)
- [ ] Remaining management pages (Settings)
