# Cross-Domain Entertainment Recommender

Recommends movies, series, anime, music, games, novels, and comics from real,
live external APIs — with a short "why this was suggested" line and
availability links per item.

No database, no background jobs — everything is fetched on-demand. Your
genre preferences are kept in the browser (localStorage) and sent to the
backend with each request.

---

## 1. Get free API keys (5–10 min, all free tiers)

| Service | Used for | Get key at |
|---|---|---|
| TMDB | Movies & Series | https://www.themoviedb.org/settings/api |
| RAWG | Games | https://rawg.io/apidocs |
| Comic Vine | Comics | https://comicvine.gamespot.com/api/ |
| Spotify | Music | https://developer.spotify.com/dashboard (create an app, use Client ID + Secret) |
| Jikan (anime) | — | **No key needed** |
| Google Books / Gutenberg (novels) | — | **No key needed** for basic use |

## 2. Backend setup

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# open .env and paste in your API keys

uvicorn main:app --reload --port 8000
```

Backend now running at `http://127.0.0.1:8000`. Visit `/docs` in your
browser for interactive API docs (Swagger UI) — good for testing endpoints
directly before touching the frontend.

## 3. Frontend setup

No build step needed — plain HTML/CSS/JS.

```bash
cd frontend
python -m http.server 5500
```

Open `http://127.0.0.1:5500` in your browser.

> If your backend runs on a different host/port, edit `frontend/config.js`.

## 4. Using the app

1. **Onboarding** — pick favorite genres per domain (all optional). Music
   asks for favorite artists instead of genres. Skip entirely to land on
   **Explore**.
2. **For Me tab** — sub-tabs per domain, personalized using your saved
   preferences. Click **"Edit genres"** (top right) anytime to change them.
3. **Explore tab** — trending/popular items per domain, no personalization.

## 5. Project structure

```
backend/
  main.py              FastAPI app — all routes
  config.py            Loads API keys from .env
  models.py            Request schemas
  recommender.py        Genre-overlap scoring + "why" explanation logic
  services/
    tmdb.py            Movies & series
    jikan.py           Anime & manga
    rawg.py            Games
    books.py           Novels (Google Books + Project Gutenberg)
    comicvine.py       Comics
    spotify.py         Music
frontend/
  index.html
  app.js               All UI logic (onboarding, tabs, rendering)
  style.css
  config.js            API_BASE URL — change if needed
```

## 6. Notes & known limitations

- **No piracy sources**: Pikashow / NovelBin were intentionally excluded —
  see `free_legal_hint` in movie/series results pointing to legal free
  options (Tubi, Pluto TV, Crackle) instead.
- **No official free public API for those apps' catalogs** — the
  `free_legal_hint` is a static suggestion list, not a live catalog check.
  If you want real per-title free-platform matching, JustWatch's unofficial
  API is the closest option, but it's community-maintained and can break.
- **Spotify** currently uses the Client Credentials flow (app-level search,
  no personal login). To pull an actual user's listening history you'd
  switch to the Authorization Code flow — that requires a user-facing OAuth
  login screen, which can be added later.
- **Recommendation logic** is straightforward genre-overlap scoring — easy
  to understand and extend. Swapping in embeddings-based similarity later
  is possible without changing the API shape.
