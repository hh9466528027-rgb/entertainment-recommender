"""
Movies & Series — The Movie Database (TMDB) API.

Authentication can use the preferred API Read Access Token as a Bearer token,
or the legacy v3 API key as a fallback.
"""
import httpx
from config import TMDB_API_KEY, TMDB_BEARER_TOKEN, FREE_LEGAL_STREAMING_HINTS

BASE_URL = "https://api.themoviedb.org/3"
IMG_BASE = "https://image.tmdb.org/t/p/w500"


def _auth_headers():
    if TMDB_BEARER_TOKEN:
        return {"Authorization": f"Bearer {TMDB_BEARER_TOKEN}"}
    return {}


def _auth_params():
    if TMDB_BEARER_TOKEN:
        return {}
    return {"api_key": TMDB_API_KEY} if TMDB_API_KEY else {}


def _has_auth():
    return bool(TMDB_BEARER_TOKEN or TMDB_API_KEY)


def _auth_error():
    return {"error": "Set TMDB_BEARER_TOKEN or TMDB_API_KEY in the backend environment."}


async def _get_json(path: str, params: dict | None = None):
    query = {**_auth_params(), **(params or {})}
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/{path.lstrip('/')}",
            params=query,
            headers=_auth_headers(),
        )
        response.raise_for_status()
        return response.json()


async def search(query: str, media_type: str = "multi", limit: int = 20):
    """media_type: 'movie', 'tv', or 'multi'"""
    if not _has_auth():
        return _auth_error()

    data = await _get_json(
        f"search/{media_type}", {"query": query, "include_adult": "false"}
    )
    return [_format_item(row) for row in data.get("results", [])[:limit]]


async def trending(media_type: str = "all", window: str = "week", limit: int = 40):
    if not _has_auth():
        return _auth_error()

    data = await _get_json(f"trending/{media_type}/{window}")
    return [_format_item(row) for row in data.get("results", [])[:limit]]


async def discover_by_genre(genre_ids: list[int], media_type: str = "movie", limit: int = 40):
    """genre_ids: TMDB numeric genre ids the user prefers"""
    if not _has_auth():
        return _auth_error()

    data = await _get_json(
        f"discover/{media_type}",
        {
            "with_genres": ",".join(str(g) for g in genre_ids),
            "sort_by": "popularity.desc",
        },
    )
    return [_format_item(row) for row in data.get("results", [])[:limit]]


def _page_result(data: dict, page: int, max_pages: int = 500):
    results = data.get("results", [])
    total_pages = max(0, int(data.get("total_pages") or 0))
    reachable_pages = min(total_pages, max_pages)
    return {
        "items": [_format_item(row) for row in results if isinstance(row, dict)],
        "page": page,
        "has_more": page < reachable_pages,
        "total_pages": reachable_pages,
        "total_results": data.get("total_results"),
        "source": "tmdb",
    }


async def _get_page(path: str, params: dict, page: int, max_pages: int = 500):
    if not _has_auth():
        return _auth_error()
    if page > max_pages:
        return {"items": [], "page": page, "has_more": False, "total_pages": max_pages, "source": "tmdb"}

    data = await _get_json(path, {**params, "page": page})
    return _page_result(data, page, max_pages)


async def search_page(query: str, media_type: str = "movie", page: int = 1):
    return await _get_page(
        f"search/{media_type}", {"query": query, "include_adult": "false"}, page
    )


async def trending_page(media_type: str = "all", window: str = "week", page: int = 1):
    return await _get_page(f"trending/{media_type}/{window}", {}, page, max_pages=1000)


async def discover_page(genre_ids: list[int], media_type: str = "movie", page: int = 1):
    return await _get_page(
        f"discover/{media_type}",
        {
            "with_genres": ",".join(str(genre_id) for genre_id in genre_ids),
            "sort_by": "popularity.desc",
        },
        page,
    )


async def get_watch_providers(item_id: int, media_type: str, country: str = "US"):
    """Returns where a title is legally available to watch (subscription/free/rent)."""
    if not _has_auth():
        return []

    data = (await _get_json(f"{media_type}/{item_id}/watch/providers")).get("results", {}).get(country, {})
    providers = []
    for category in ("flatrate", "free", "ads"):
        for provider in data.get(category, []):
            providers.append({"name": provider["provider_name"], "type": category})
    return providers


def _format_item(row: dict):
    title = row.get("title") or row.get("name")
    media_type = row.get("media_type") or ("movie" if "title" in row else "tv")
    item_id = row.get("id")
    return {
        "id": item_id,
        "domain": "movies" if media_type == "movie" else "series",
        "title": title,
        "overview": row.get("overview"),
        "image": f"{IMG_BASE}{row['poster_path']}" if row.get("poster_path") else None,
        "rating": row.get("vote_average"),
        "genre_ids": row.get("genre_ids", []),
        "tmdb_media_type": media_type,
        "free_legal_hint": FREE_LEGAL_STREAMING_HINTS,
        "site_url": f"https://www.themoviedb.org/{media_type}/{item_id}" if item_id else None,
    }
