# ᖳᖰ

# ᯤ Spotify Playlist Bulk Transfer Manager

A full-stack web app for selecting arbitrary groups of songs from a Spotify playlist and copying or moving them to another playlist in bulk.

## Folder Structure

```text
.
├── backend/
│   ├── app/
│   │   ├── api/              # FastAPI route modules
│   │   ├── core/             # settings, security, error handling
│   │   ├── models/           # SQLAlchemy and Pydantic models
│   │   └── services/         # Spotify and transfer logic
│   ├── tests/                # Pytest tests
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── api/              # Axios client and API wrappers
│   │   ├── components/       # Reusable UI components
│   │   ├── context/          # Auth and toast providers
│   │   ├── pages/            # Login, dashboard, playlist manager
│   │   ├── types/            # TypeScript domain types
│   │   └── utils/            # Formatting and export helpers
│   ├── tests/                # React/Vitest tests
│   ├── Dockerfile
│   └── .env.example
├── docker-compose.yml
└── README.md
```

## Features

- Spotify OAuth Authorization Code Flow with signed HTTP-only session cookies.
- Server-side Spotify token storage, refresh, logout, and CSRF validation for mutations.
- Playlist dashboard with profile image, display name, total playlists, playlist cards, owners, images, and track counts.
- Lazy-loaded playlist track table with search, sorting, pagination, artist/album filters, and duration range filters.
- Multi-select, select visible, deselect all, select by artist, select by album, select duplicate tracks, and select recently added tracks.
- Copy or move selected tracks to an existing or newly created playlist.
- Duplicate detection before transfer, default skip-duplicates behavior, progress feedback, toasts, undo of the last transfer, CSV export, and JSON export.
- SQLite development database through SQLAlchemy, with a `DATABASE_URL` setting ready for PostgreSQL.
- Dockerfiles and Docker Compose for one-command local startup.

## Architecture

The frontend is a Vite React TypeScript app styled with Tailwind CSS. It talks to the backend through Axios with `withCredentials` enabled. The Spotify client secret never reaches the browser.

The backend is FastAPI. OAuth tokens are stored in the database inside a server-side `UserSession` record. The browser receives only a signed session cookie and a CSRF token returned by `/api/me`. Spotify calls are wrapped with retry handling for rate limits and transient server errors.

## Spotify Developer Setup

1. Create an app at the Spotify Developer Dashboard.
2. Add this redirect URI:

```text
http://localhost:8000/api/auth/callback
```

3. Copy the client ID and client secret into `backend/.env`.
4. Required scopes:

```text
playlist-read-private
playlist-read-collaborative
playlist-modify-private
playlist-modify-public
user-read-private
```

## Environment Variables

Copy examples and edit values:

```powershell
Copy-Item backend\.env.example backend\.env
Copy-Item frontend\.env.example frontend\.env
```

Backend:

```text
APP_ENV=development
FRONTEND_URL=http://localhost:5173
BACKEND_URL=http://localhost:8000
SESSION_SECRET=replace-with-a-long-random-string
COOKIE_SECURE=false
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
SPOTIFY_REDIRECT_URI=http://localhost:8000/api/auth/callback
DATABASE_URL=sqlite:///./spotify_transfer.db
```

Frontend:

```text
VITE_API_URL=http://localhost:8000
```

## Local Installation

Backend:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Frontend:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## Docker

```powershell
Copy-Item backend\.env.example backend\.env
# Edit backend\.env with Spotify credentials first.
docker compose up --build
```

Frontend: `http://localhost:5173`  
Backend: `http://localhost:8000`

## API Documentation

FastAPI docs are available at:

```text
http://localhost:8000/docs
```

Main endpoints:

```text
GET  /api/auth/login
GET  /api/auth/callback
POST /api/auth/logout
GET  /api/me
GET  /api/playlists
GET  /api/playlists/{id}/tracks
POST /api/playlists/create
POST /api/tracks/duplicates
POST /api/tracks/copy
POST /api/tracks/move
POST /api/tracks/undo
GET  /api/export/csv
GET  /api/export/json
```

Structured errors use:

```json
{
  "error": {
    "code": "spotify_error",
    "message": "Spotify API request failed",
    "details": {}
  }
}
```

## Testing

Backend:

```powershell
cd backend
pytest
```

Frontend:

```powershell
cd frontend
npm test
```

Build:

```powershell
cd frontend
npm run build
```

## Screenshots

Place screenshots here after the app is connected to a Spotify account:

- `docs/screenshots/login.png`
- `docs/screenshots/dashboard.png`
- `docs/screenshots/playlist-manager.png`
- `docs/screenshots/transfer-modal.png`

## Deployment Notes

- Use HTTPS in production and set `COOKIE_SECURE=true`.
- Use a long random `SESSION_SECRET`.
- Set exact production `CORS_ORIGINS` and `FRONTEND_URL`.
- Replace SQLite with PostgreSQL by changing `DATABASE_URL`, for example:

```text
DATABASE_URL=postgresql+psycopg://user:password@db:5432/spotify_transfer
```

- Store secrets in the deployment platform’s secret manager.
