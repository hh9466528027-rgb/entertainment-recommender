# Afterglow — Cross-Domain Entertainment Recommender

Afterglow helps people discover entertainment across **movies, series, anime, music, games, novels, and comics** in one responsive website. Users can browse discovery feeds or personalize suggestions using favorite genres and artists.

- **Live website:** <https://entertainment-recommender-frontend.vercel.app/>
- **Backend API:** <https://entertainment-recommender.onrender.com/>
- **Interactive API docs:** <https://entertainment-recommender.onrender.com/docs>
- **Project report:** [Markdown](docs/PROJECT_DOCUMENTATION.md) · [PDF](docs/PROJECT_DOCUMENTATION.pdf)
- **Presentation Q&A handout:** [Anticipated questions and answers](docs/ANTICIPATED_QA.md)

## Features

- Seven entertainment categories with search and discovery views.
- Optional onboarding and editable taste preferences; preferences stay in the browser.
- Content-based personalized ranking with a human-readable reason for each suggestion.
- Search, genre and minimum-rating filters, sorting, and progressive **Load more** pagination.
- Clickable cards with available artwork, synopsis, metadata, ratings, and provider links.
- Music track previews when supplied by the catalog, plus listening and Gaana search links.
- Dark/light themes, responsive styling, and animated visual details.
- Provider adapters and fallbacks for selected categories.

Pagination fetches additional provider pages on demand. Results are not an unlimited download: every external catalog has its own coverage, rate limits, quotas, and maximum page range.

## Technology and data sources

| Layer | Technology | Responsibility |
|---|---|---|
| Frontend | HTML5, CSS3, vanilla JavaScript | UI, preferences, filters, rendering, and API calls |
| Backend | Python, FastAPI, Pydantic, HTTPX | Routes, provider calls, normalization, and recommendation scoring |
| Hosting | Vercel and Render | Static frontend and FastAPI backend |

Category adapters use TMDB for movies and series; AniList with Jikan fallback for anime; RAWG for games; Google Books, Gutendex, and Open Library for novels; Comic Vine for comics; and Deezer with Apple/iTunes fallback for music. Music searches do not require Spotify credentials; optional Spotify compatibility settings remain available in the backend. For TMDB authentication, the backend prefers `TMDB_BEARER_TOKEN` and falls back to `TMDB_API_KEY` when the bearer token is unset.

## Recommendation approach

The recommender is **rule-based**, not a trained machine-learning model. It rewards matching preferred genres, matching favorite/interest terms in descriptions, and favorite names found in titles or credits. Results include a short reason such as a matching genre or favorite artist. See the project report for the scoring formula and data flow.

## Run locally

### Backend

Python 3.10 or newer is recommended.

```bash
cd backend
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env
```

Add only the credentials you need to `backend/.env`. For TMDB, configure either the API Read Access Token (`TMDB_BEARER_TOKEN`, preferred) or the API key (`TMDB_API_KEY`). RAWG and Comic Vine credentials are used for their categories. A Google Books key is optional. AniList/Jikan, Deezer, and Apple/iTunes searches work without user credentials; Spotify credentials are optional for compatibility helpers.

Run the API from the `backend` directory:

```bash
uvicorn main:app --reload --port 8000
```

Open <http://127.0.0.1:8000/docs> for the interactive API documentation.

### Frontend

In a second terminal:

```bash
cd frontend
python -m http.server 5500
```

Open <http://127.0.0.1:5500>. The checked-in `frontend/config.js` uses the deployed Render API by default. To test against the local backend, change `API_BASE` to `http://127.0.0.1:8000`.

## API routes

- `GET /` — health check and supported categories.
- `GET /explore/{domain}?page=1` — popular or discovery results.
- `POST /for-me/{domain}?page=1` — personalized results.
- `GET /search/{domain}?q=...&page=1` — category search.

Supported domain slugs: `movies`, `series`, `anime`, `music`, `games`, `novels`, and `comics`. Some page continuations also accept a `source` parameter so the next request stays with the provider used on the first page.

## Project layout

```text
backend/
  main.py                 FastAPI routes and orchestration
  models.py               Preference request models
  recommender.py          Content scoring and explanations
  services/               Category-specific provider adapters
frontend/
  index.html               Application shell
  app.js                   UI state, requests, filters, and rendering
  style.css                Themes, layout, and animations
  config.js                Backend API base URL
docs/                      Project report and presentation Q&A
render.yaml                Render service configuration
DEPLOYMENT.md               Current hosting and deployment notes
```

## Security and privacy

- Do not put API keys in frontend code, README examples, or Git.
- Store production credentials in Render environment variables and local development credentials in the ignored `.env` file.
- `backend/.env.example` intentionally contains blank placeholders. Never replace them with real values before committing.
- Preferences and theme settings are stored in browser `localStorage`; there is no user account system or server-side preference database.
- If a credential is ever committed to a public repository, treat it as exposed and rotate/revoke it. Removing a value from the latest file does not remove it from older Git commits.

## Known limitations

Results depend on external service availability, rate limits, and metadata completeness. Ratings are not standardized across providers. Music genre searches use catalog search behavior and may be less exact than formal genre tags. The recommender does not learn from clicks or listening history. Free-streaming availability hints are suggestions, not guaranteed title-by-title checks.

The repository does not currently include a dedicated automated test suite; the project report includes a manual verification checklist and future testing recommendations.
