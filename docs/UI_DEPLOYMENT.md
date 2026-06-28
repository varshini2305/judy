# UI Deployment

This UI is currently a **static Vite + React app** living under `ui/`. Today it
does not require the Python API to render because it runs against mock data, so
the simplest production path is a static frontend host.

## Recommendation

- **Use Railway** as the default deployment path for Judy.
- **Use Firebase Hosting** only if you decide to live fully in the Google Cloud
  stack.
- **Use Vercel** only if you want the fastest frontend-only deployment and are
  comfortable with a likely platform split later.

Reasoning:

- The current app builds to static assets with `npm run build`.
- Railway works now for the static UI and still fits the future shape of the
  repo once the FastAPI backend becomes a real service.
- Firebase Hosting is a strong alternative when you want GCP alignment and an
  easy path to pair the frontend with Cloud Run later.
- Vercel is frictionless for the frontend alone, but it is a weaker "pick once"
  answer for this repo's planned backend-powered architecture.

## Option 1: Railway

Use this if you want a single platform now and do not want to rethink hosting
later when the backend is live.

This repo already includes:

- `ui/Dockerfile`
- `ui/Caddyfile`
- `ui/.dockerignore`

These let Railway build and serve the current static Vite app from the `ui/`
directory.

Setup:

1. Push the UI changes to GitHub.
2. In Railway, create a new **frontend** service from the GitHub repo.
3. Set the frontend service **Root Directory** to `ui`.
4. Let Railway build from the `ui/Dockerfile`.
5. Generate a public domain for the frontend service.

### Add the FastAPI backend service for `/api`

The `Preference Loop` needs the FastAPI backend. The static frontend alone will
not make `/api/preference/*` work on Railway.

This repo now includes:

- `judy/api/Dockerfile`

Backend setup:

1. In the same Railway project, create a second **backend** service from the
   same GitHub repo.
2. Set the backend service **Root Directory** to the repo root.
3. Set the backend service **Dockerfile Path** to `judy/api/Dockerfile`.
4. Add any required runtime secrets there, such as:
   - `GEMINI_API_KEY`
   - `OPENAI_API_KEY` (only if you want features that depend on it)
5. Generate a public or internal Railway domain for the backend service.

### Connect the frontend service to the backend service

The frontend Caddy config now proxies `/api/*` to a backend origin using the
`BACKEND_ORIGIN` environment variable.

On the **frontend** Railway service, set:

- `BACKEND_ORIGIN=https://<your-backend-service-domain>`

Example:

- `BACKEND_ORIGIN=https://judy-api-production.up.railway.app`

After redeploy, the frontend will:

- serve the SPA normally
- proxy `/api/*` to the FastAPI backend
- allow the `Preference Loop` page to work on Railway, not just locally

Why this is the default:

- It works with the UI today.
- It avoids a later platform migration when the FastAPI backend is added.
- You can keep the frontend and backend as separate services in the same Railway
  project once the API exists.

## Option 2: Firebase Hosting

Use this if you want the frontend hosted in the Google ecosystem.

1. Install the Firebase CLI.
2. From the repo root, build the UI:

   ```bash
   cd ui
   npm install
   npm run build
   ```

3. Initialize Hosting and point the public directory at `ui/dist`.
4. Enable SPA fallback so client-side routes resolve to `index.html`.
5. Deploy with the Firebase CLI.

Why this is a good GCP path:

- Firebase Hosting is optimized for static and single-page apps.
- It can later be paired cleanly with Cloud Run if the Judy API is deployed as a
  separate service.

## Option 3: Vercel

Use this if the goal is to get the UI live quickly with the least operational
overhead.

1. Import the GitHub repo into Vercel.
2. Set the **Root Directory** to `ui`.
3. Use the defaults or set them explicitly:
   - Build command: `npm run build`
   - Output directory: `dist`
4. Deploy.

Notes:

- No runtime environment variables are required for the current mock-driven UI.
- Once the UI talks to a live backend, add a `VITE_API_BASE_URL`-style variable
  and route API requests to the deployed backend rather than the local Vite
  proxy.

## Option 4: Cloud Run via Docker

If you want a single portable deployment artifact, use the container setup in
`ui/Dockerfile` and `ui/Caddyfile`.

What it does:

- Builds the Vite app in a Node stage.
- Serves the built assets from Caddy on port `8080`.
- Falls back to `index.html` so SPA navigation works.

### Cloud Run

1. Build the container from `ui/Dockerfile`.
2. Push it to Artifact Registry.
3. Deploy it to Cloud Run.

Cloud Run is viable, but for a frontend-only static app it is usually more
infrastructure than Firebase Hosting.

## Current limitation

Most of the main dashboard is still artifact-backed rather than fully live. The
important exception is the `Preference Loop`, which now depends on the FastAPI
backend being deployed and connected via the frontend proxy.

## Verified locally

- `cd ui && npm run build` succeeds.
- Current production build emits a large main JS chunk, so later UI polish
  should include code-splitting or lazy loading.
