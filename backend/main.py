"""
Cross-Domain Entertainment Recommender — Backend
Run with: uvicorn main:app --reload --port 8000
Then open frontend/index.html in your browser (or serve it with any static server).
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from models import Preferences
from recommender import score_and_explain
from services import tmdb, anilist, rawg, books, comicvine, spotify

app = FastAPI(title="Entertainment Recommender API")

# Allow the frontend (served from file:// or localhost:*) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DOMAINS = ["movies", "series", "anime", "music", "games", "novels", "comics"]


@app.get("/")
async def root():
    return {"status": "ok", "domains": DOMAINS}


def _tag_explore(items, label: str):
    """Explore is non-personalized, but every item should still say *why*
    it's showing up, instead of leaving the card blank."""
    if isinstance(items, dict):  # error dict (missing key, etc.)
        return items
    for it in items:
        it.setdefault("why", f"🔥 Trending in {label} right now")
    return items


# ---------------------------------------------------------------------------
# EXPLORE — trending / popular, no personalization required
# ---------------------------------------------------------------------------
@app.get("/explore/{domain}")
async def explore(domain: str):
    if domain == "movies":
        return _tag_explore(await tmdb.trending(media_type="movie"), "Movies")
    if domain == "series":
        return _tag_explore(await tmdb.trending(media_type="tv"), "Series")
    if domain == "anime":
        return _tag_explore(await anilist.top(), "Anime")
    if domain == "games":
        return _tag_explore(await rawg.popular(), "Games")
    if domain == "novels":
        return _tag_explore(await books.free_legal_popular(), "Novels")
    if domain == "comics":
        return _tag_explore(await comicvine.search("Batman"), "Comics")  # seed query; Comic Vine has no generic "trending"
    if domain == "music":
        return await spotify.explore()
    raise HTTPException(404, f"Unknown domain: {domain}")


# ---------------------------------------------------------------------------
# FOR ME — personalized, using stated preferences (sent from frontend each call —
# no server-side account/database needed; frontend keeps preferences in
# localStorage and passes them along)
# ---------------------------------------------------------------------------
@app.post("/for-me/{domain}")
async def for_me(domain: str, preferences: Preferences):
    prefs = preferences.model_dump()
    genres = prefs.get("genres") or []

    if domain == "movies":
        pool = await tmdb.discover_by_genre(_tmdb_genre_ids(genres), media_type="movie") if genres else await tmdb.trending(media_type="movie")
    elif domain == "series":
        pool = await tmdb.discover_by_genre(_tmdb_genre_ids(genres), media_type="tv") if genres else await tmdb.trending(media_type="tv")
    elif domain == "anime":
        pool = await anilist.by_genre(genres) if genres else await anilist.top()
    elif domain == "games":
        pool = await rawg.by_genre([g.lower() for g in genres]) if genres else await rawg.popular()
    elif domain == "novels":
        pool = await books.by_genre(genres[0]) if genres else await books.free_legal_popular()
    elif domain == "comics":
        pool = await comicvine.search(genres[0] if genres else "superhero")
    elif domain == "music":
        favorites = [str(value).strip() for value in (prefs.get("favorites") or []) if str(value).strip()]
        genre_seed = next((str(value).strip() for value in genres if str(value).strip()), "")
        seed = favorites[0] if favorites else genre_seed or "pop"
        pool = await spotify.by_artist_or_genre(seed, limit=200)
    else:
        raise HTTPException(404, f"Unknown domain: {domain}")

    if isinstance(pool, dict) and "error" in pool:
        return pool

    return score_and_explain(pool, prefs)


@app.get("/search/{domain}")
async def search(domain: str, q: str, limit: int = 200):
    if domain == "movies":
        return await tmdb.search(q, media_type="movie")
    if domain == "series":
        return await tmdb.search(q, media_type="tv")
    if domain == "anime":
        return await anilist.search(q)
    if domain == "games":
        return await rawg.search(q)
    if domain == "novels":
        return await books.search(q)
    if domain == "comics":
        return await comicvine.search(q)
    if domain == "music":
        return await spotify.search(q, search_type="track", limit=limit)
    raise HTTPException(404, f"Unknown domain: {domain}")


# ---------------------------------------------------------------------------
# Genre name -> id mapping helper (TMDB uses numeric genre ids; AniList
# takes genre names directly, no mapping needed)
# ---------------------------------------------------------------------------
_TMDB_GENRES = {
    "action": 28, "adventure": 12, "animation": 16, "comedy": 35, "crime": 80,
    "documentary": 99, "drama": 18, "family": 10751, "fantasy": 14, "horror": 27,
    "mystery": 9648, "romance": 10749, "sci-fi": 878, "science fiction": 878,
    "thriller": 53, "war": 10752, "western": 37,
}


def _tmdb_genre_ids(genre_names: list[str]) -> list[int]:
    return [_TMDB_GENRES[g.lower()] for g in genre_names if g.lower() in _TMDB_GENRES]
