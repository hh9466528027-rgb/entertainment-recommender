"""
Cross-Domain Entertainment Recommender — Backend
Run with: uvicorn main:app --reload --port 8000
Then open frontend/index.html in your browser (or serve it with any static server).
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from models import Preferences
from recommender import score_and_explain
from services import tmdb, anilist, rawg, books, comicvine, spotify

app = FastAPI(title="Entertainment Recommender API")

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


def _tag_explore(result, label: str):
    """Keep pagination metadata intact while explaining why Explore items appear."""
    if isinstance(result, dict) and "error" in result:
        return result
    if isinstance(result, dict) and isinstance(result.get("items"), list):
        for item in result["items"]:
            item.setdefault("why", f"Trending in {label} right now")
        return result
    return result


def _score_page(result, preferences: dict):
    if isinstance(result, dict) and "error" in result:
        return result
    if isinstance(result, dict) and isinstance(result.get("items"), list):
        result["items"] = score_and_explain(result["items"], preferences)
        return result
    return result


@app.get("/explore/{domain}")
async def explore(domain: str, page: int = Query(1, ge=1), source: str | None = None):
    if domain == "movies":
        return _tag_explore(await tmdb.trending_page(media_type="movie", page=page), "Movies")
    if domain == "series":
        return _tag_explore(await tmdb.trending_page(media_type="tv", page=page), "Series")
    if domain == "anime":
        return _tag_explore(await anilist.top_page(page, source), "Anime")
    if domain == "games":
        return _tag_explore(await rawg.popular_page(page), "Games")
    if domain == "novels":
        return _tag_explore(await books.free_legal_popular_page(page, source), "Novels")
    if domain == "comics":
        return _tag_explore(await comicvine.search_page("Batman", page), "Comics")
    if domain == "music":
        return _tag_explore(await spotify.explore_page(page, source), "Music")
    raise HTTPException(404, f"Unknown domain: {domain}")


@app.post("/for-me/{domain}")
async def for_me(
    domain: str,
    preferences: Preferences,
    page: int = Query(1, ge=1),
    source: str | None = None,
):
    prefs = preferences.model_dump()
    genres = prefs.get("genres") or []

    if domain == "movies":
        result = await tmdb.discover_page(_tmdb_genre_ids(genres), "movie", page) if genres else await tmdb.trending_page("movie", page=page)
    elif domain == "series":
        result = await tmdb.discover_page(_tmdb_genre_ids(genres), "tv", page) if genres else await tmdb.trending_page("tv", page=page)
    elif domain == "anime":
        result = await anilist.by_genre_page(genres, page, source) if genres else await anilist.top_page(page, source)
    elif domain == "games":
        result = await rawg.by_genre_page([g.lower() for g in genres], page) if genres else await rawg.popular_page(page)
    elif domain == "novels":
        result = await books.by_genre_page(genres[0], page, source) if genres else await books.free_legal_popular_page(page, source)
    elif domain == "comics":
        result = await comicvine.search_page(genres[0] if genres else "superhero", page)
    elif domain == "music":
        favorites = [str(value).strip() for value in (prefs.get("favorites") or []) if str(value).strip()]
        genre_seed = next((str(value).strip() for value in genres if str(value).strip()), "")
        seed = favorites[0] if favorites else genre_seed or "pop"
        result = await spotify.by_artist_or_genre_page(seed, page, source)
    else:
        raise HTTPException(404, f"Unknown domain: {domain}")

    return _score_page(result, prefs)


@app.get("/search/{domain}")
async def search(
    domain: str,
    q: str,
    page: int = Query(1, ge=1),
    source: str | None = None,
):
    if domain == "movies":
        return await tmdb.search_page(q, media_type="movie", page=page)
    if domain == "series":
        return await tmdb.search_page(q, media_type="tv", page=page)
    if domain == "anime":
        return await anilist.search_page(q, page, source)
    if domain == "games":
        return await rawg.search_page(q, page)
    if domain == "novels":
        return await books.search_page(q, page, source)
    if domain == "comics":
        return await comicvine.search_page(q, page)
    if domain == "music":
        return await spotify.search_page(q, page, source)
    raise HTTPException(404, f"Unknown domain: {domain}")


_TMDB_GENRES = {
    "action": 28, "adventure": 12, "animation": 16, "comedy": 35, "crime": 80,
    "documentary": 99, "drama": 18, "family": 10751, "fantasy": 14, "horror": 27,
    "mystery": 9648, "romance": 10749, "sci-fi": 878, "science fiction": 878,
    "thriller": 53, "war": 10752, "western": 37,
}


def _tmdb_genre_ids(genre_names: list[str]) -> list[int]:
    return [_TMDB_GENRES[g.lower()] for g in genre_names if g.lower() in _TMDB_GENRES]
