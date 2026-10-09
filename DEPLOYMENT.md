# Deployment and operations

## Current production deployment

- **Frontend:** <https://entertainment-recommender-frontend.vercel.app/> (Vercel, static HTML/CSS/JavaScript; no build step).
- **Backend:** <https://entertainment-recommender.onrender.com/> (Render FastAPI service).
- **API documentation:** <https://entertainment-recommender.onrender.com/docs>.
- **Source repository:** <https://github.com/hh9466528027-rgb/entertainment-recommender>.

The Render service uses `backend/` as its root directory, installs `backend/requirements.txt`, and starts Uvicorn using the host-provided `$PORT`. Its current GitHub integration is configured for the `main` branch. `frontend/config.js` points the website at the production Render API by default.

## Required provider credentials

Set credentials in **Render → the backend web service → Environment**. Never put values in frontend code, GitHub, or this document.

| Environment variable | Used for | Required? |
|---|---|---|
| `TMDB_BEARER_TOKEN` | TMDB API Read Access Token; preferred | Use this or `TMDB_API_KEY` |
| `TMDB_API_KEY` | TMDB v3 API key; fallback | Use this or `TMDB_BEARER_TOKEN` |
| `RAWG_API_KEY` | Games | Yes for RAWG-backed results |
| `COMICVINE_API_KEY` | Comics | Yes for Comic Vine results |
| `GOOGLE_BOOKS_API_KEY` | Google Books quota | Optional |
| `SPOTIFY_CLIENT_ID` | Optional Spotify compatibility helpers | Optional |
| `SPOTIFY_CLIENT_SECRET` | Optional Spotify compatibility helpers | Optional |

AniList/Jikan, Deezer, and Apple/iTunes searches used by the app do not require a user login. The `.env.example` file contains blank placeholders. For local development, copy it to `backend/.env`; `.env` is ignored by Git.

## Normal deployment updates

1. Make and validate the intended source or documentation changes locally.
2. Commit and push to the repository's `main` branch.
3. Let the connected hosting services process the commit. Render is configured for automatic deploys; Vercel serves the static frontend from the repository's frontend project configuration.
4. Verify the frontend URL, backend `/` health response, `/docs`, and affected category routes. For frontend changes, reload with a cache-busting query or hard refresh if a browser has cached older JavaScript.

Documentation-only changes do not alter application behavior. Avoid changing `frontend/config.js`, `render.yaml`, or Render environment variables unless the deployment target or backend configuration actually needs to change.

## Safe credential rotation without planned downtime

A previously exposed credential should be considered compromised. **Rewriting Git history does not invalidate a leaked key.** To minimize impact on the live website:

1. For each affected provider, create or obtain a replacement key while the old key is still valid, if that provider permits two active keys.
2. Update the corresponding Render environment variable to the replacement and allow the backend to restart/deploy.
3. Verify the affected production category and the API health route with the new key.
4. Only then revoke the old key.
5. If a provider invalidates the old key immediately when a replacement is issued, a zero-interruption rotation cannot be guaranteed by the application alone. Coordinate a maintenance window or confirm the provider’s overlap/rotation behavior before changing it.

Do not send credentials in chat or add them to GitHub. If a credential is missing, keep the relevant category's current production value unchanged until a replacement can be entered securely.

## Removing old values from Git history

The current example file is sanitized, but past commits may still contain its earlier contents. Removing those historical copies requires rewriting Git history and force-pushing. That changes commit IDs and can require collaborators to re-clone; old clones, forks, and cached GitHub references may still retain the data. Rotate/revoke the actual credentials first, then decide whether to rewrite history and contact GitHub Support for cached references. Do not treat a history rewrite as a substitute for credential rotation.
