# React + Tailwind management SPA

Hybrid migration frontend for Clara Science Academy. Flask remains the backend; this app is served at `/app/*`.

## Prerequisites

- Node.js 20+
- Flask app running on `http://127.0.0.1:5000`

## Development

**Terminal 1 — Flask**

```powershell
python app.py
```

**Terminal 2 — Vite (hot reload)**

```powershell
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173/app/](http://localhost:5173/app/) (proxies API to Flask).

Log in via Flask first at `/login`, then open the Vite URL in the same browser so session cookies apply.

## Production build

```powershell
cd frontend
npm run build
```

Output: `static/spa/` (served by Flask when `REACT_SPA_ENABLED=true`).

Then visit [http://127.0.0.1:5000/app/](http://127.0.0.1:5000/app/).

## Environment

| Variable | Default (dev) | Description |
|----------|---------------|-------------|
| `REACT_SPA_ENABLED` | `true` in DevelopmentConfig | Serve `/app/*` from `static/spa` |

## API

- `GET /api/spa/me` — session + permissions + CSRF token
- `GET /api/spa/health` — health check
