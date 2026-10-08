"""
Movies & Series — The Movie Database (TMDB) API
Free API key: https://www.themoviedb.org/settings/api
Docs: https://developer.themoviedb.org/reference/intro/getting-started
"""
import httpx
from config import TMDB_API_KEY, FREE_LEGAL_STREAMING_HINTS

BASE_URL = "https://api.themoviedb.org/3"
IMG_BASE = "https://image.tmdb.org/t/p/w500"


def _headers():
    return {"Authorization": f"Bearer {TMDB_API_KEY}"}


async def search(query: str, media_type: str = "multi", limit: int = 20):
    """media_type: 'movie', 'tv', or 'multi'"""
    if not TMDB_API_KEY:
        return {"error": "TMDB_API_KEY not set. Add it to backend/.env"}

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/search/{media_type}",
            params={"api_key": TMDB_API_KEY, "query": query, "include_adult": "false"},
        )
        resp.raise_for_status()
        data = resp.json()

    return [_format_item(r) for r in data.get("results", [])[:limit]]


async def trending(media_type: str = "all", window: str = "week", limit: int = 40):
    if not TMDB_API_KEY:
        return {"error": "TMDB_API_KEY not set. Add it to backend/.env"}

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/trending/{media_type}/{window}",
            params={"api_key": TMDB_API_KEY},
        )
        resp.raise_for_status()
        data = resp.json()

    return [_format_item(r) for r in data.get("results", [])[:limit]]


async def discover_by_genre(genre_ids: list[int], media_type: str = "movie", limit: int = 40):
    """genre_ids: TMDB numeric genre ids the user prefers"""
    if not TMDB_API_KEY:
        return {"error": "TMDB_API_KEY not set. Add it to backend/.env"}

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/discover/{media_type}",
            params={
                "api_key": TMDB_API_KEY,
                "with_genres": ",".join(str(g) for g in genre_ids),
                "sort_by": "popularity.desc",
            },
        )
        resp.raise_for_status()
        data = resp.json()

    return [_format_item(r) for r in data.get("results", [])[:limit]]


async def get_watch_providers(item_id: int, media_type: str, country: str = "US"):
    """Returns where a title is legally available to watch (subscription/free/rent)."""
    if not TMDB_API_KEY:
        return []

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/{media_type}/{item_id}/watch/providers",
            params={"api_key": TMDB_API_KEY},
        )
        resp.raise_for_status()
        data = resp.json().get("results", {}).get(country, {})

    providers = []
    for category in ("flatrate", "free", "ads"):
        for p in data.get(category, []):
            providers.append({"name": p["provider_name"], "type": category})
    return providers


def _format_item(r: dict):
    title = r.get("title") or r.get("name")
    media_type = r.get("media_type") or ("movie" if "title" in r else "tv")
    item_id = r.get("id")
    return {
        "id": item_id,
        "domain": "movies" if media_type == "movie" else "series",
        "title": title,
        "overview": r.get("overview"),
        "image": f"{IMG_BASE}{r['poster_path']}" if r.get("poster_path") else None,
        "rating": r.get("vote_average"),
        "genre_ids": r.get("genre_ids", []),
        "tmdb_media_type": media_type,
        "free_legal_hint": FREE_LEGAL_STREAMING_HINTS,
        # Guaranteed clickable link to the title's TMDB page
        "site_url": f"https://www.themoviedb.org/{media_type}/{item_id}" if item_id else None,
    }