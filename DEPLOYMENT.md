# Deploying to Free Hosting (Render + Vercel)

This gets your project onto a real public URL — no computer needs to stay
running, anyone can visit it.

---

## Part 1 — Push the project to GitHub

Both Render and Vercel deploy from a GitHub repo.

1. Go to https://github.com → New repository → name it `entertainment-recommender` → Create
2. In your project folder (the unzipped one), run:
```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/entertainment-recommender.git
git push -u origin main
```
(Replace `YOUR_USERNAME` with your actual GitHub username. If `git` isn't
installed, download it from https://git-scm.com first.)

---

## Part 2 — Deploy the backend (Render)

1. Go to https://render.com → sign up (free, can use GitHub login)
2. Click **New +** → **Web Service**
3. Connect your GitHub account, select the `entertainment-recommender` repo
4. Render should detect `render.yaml` automatically and pre-fill settings.
   If not, set manually:
   - **Root Directory**: `backend`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Under **Environment Variables**, add each of your API keys:
   - `TMDB_API_KEY`
   - `RAWG_API_KEY`
   - `COMICVINE_API_KEY`
   - `SPOTIFY_CLIENT_ID`
   - `SPOTIFY_CLIENT_SECRET`
   - `GOOGLE_BOOKS_API_KEY` (optional)
6. Click **Create Web Service**. Wait for the build (2-5 min).
7. Once live, copy your URL — looks like `https://entertainment-recommender-api.onrender.com`
8. Test it: open `https://your-url.onrender.com/docs` in a browser — you
   should see the API docs page.

> **Free tier note**: the backend "sleeps" after ~15 min of no traffic.
> The first request after that takes 30-50 seconds to wake up — normal,
> not a bug.

---

## Part 3 — Deploy the frontend (Vercel)

1. Open `frontend/config.js` and change the `API_BASE` line to your Render URL:
   ```js
   const API_BASE = "https://entertainment-recommender-api.onrender.com";
   ```
2. Commit and push this change:
   ```bash
   git add frontend/config.js
   git commit -m "Point frontend to deployed backend"
   git push
   ```
3. Go to https://vercel.com → sign up (free, can use GitHub login)
4. Click **Add New** → **Project** → import your `entertainment-recommender` repo
5. Set **Root Directory** to `frontend`
6. Framework Preset: choose **Other** (it's plain HTML/JS, no build step needed)
7. Click **Deploy**. Wait ~1 min.
8. You'll get a live URL like `https://entertainment-recommender.vercel.app`

---

## Part 4 — Test the live site

Visit your Vercel URL. It should load the onboarding screen, and Explore/For
Me should pull real data from your Render-hosted backend.

If something doesn't load, open your browser's developer console (F12) →
Network tab → look for failed requests to your Render URL. Common causes:
- Backend still "waking up" (wait 30-50 sec, refresh)
- A typo in `API_BASE` in `config.js`
- A missing API key in Render's environment variables

---

## Updating the site later

Any time you change code and push to GitHub (`git push`), both Render and
Vercel automatically redeploy. No manual redeploy step needed.
