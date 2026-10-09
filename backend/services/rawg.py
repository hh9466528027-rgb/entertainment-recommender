"""
Games — RAWG Video Games Database API
Free API key: https://rawg.io/apidocs
"""
import httpx
from config import RAWG_API_KEY

BASE_URL = "https://api.rawg.io/api"


async def search(query: str, limit: int = 20):
    if not RAWG_API_KEY:
        return {"error": "RAWG_API_KEY not set. Add it to backend/.env"}

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/games", params={"key": RAWG_API_KEY, "search": query, "page_size": limit}
        )
        resp.raise_for_status()
        data = resp.json()
    return [_format_item(r) for r in data.get("results", [])]


async def popular(limit: int = 40):
    if not RAWG_API_KEY:
        return {"error": "RAWG_API_KEY not set. Add it to backend/.env"}

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/games",
            params={"key": RAWG_API_KEY, "ordering": "-added", "page_size": limit},
        )
        resp.raise_for_status()
        data = resp.json()
    return [_format_item(r) for r in data.get("results", [])]


async def by_genre(genre_slugs: list[str], limit: int = 40):
    if not RAWG_API_KEY:
        return {"error": "RAWG_API_KEY not set. Add it to backend/.env"}

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/games",
            params={
                "key": RAWG_API_KEY,
                "genres": ",".join(genre_slugs),
                "ordering": "-rating",
                "page_size": limit,
            },
        )
        resp.raise_for_status()
        data = resp.json()
    return [_format_item(r) for r in data.get("results", [])]


async def _games_page(params: dict, page: int, page_size: int = 40):
    if not RAWG_API_KEY:
        return {"error": "RAWG_API_KEY not set. Add it to backend/.env"}
    page_size = max(1, min(int(page_size), 40))
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/games",
            params={"key": RAWG_API_KEY, "page": page, "page_size": page_size, **params},
        )
        response.raise_for_status()
        data = response.json()
    rows = data.get("results", [])
    return {
        "items": [_format_item(row) for row in rows if isinstance(row, dict)],
        "page": page,
        "has_more": bool(data.get("next")),
        "total_results": data.get("count"),
        "source": "rawg",
    }


async def search_page(query: str, page: int = 1):
    return await _games_page({"search": query}, page)


async def popular_page(page: int = 1):
    return await _games_page({"ordering": "-added"}, page)


async def by_genre_page(genre_slugs: list[str], page: int = 1):
    return await _games_page(
        {"genres": ",".join(genre_slugs), "ordering": "-rating"}, page
    )


def _format_item(r: dict):
    item_id = r.get("id")
    slug = r.get("slug")
    return {
        "id": item_id,
        "domain": "games",
        "title": r.get("name"),
        "image": r.get("background_image"),
        "rating": r.get("rating"),
        "genres": [g["name"] for g in r.get("genres", [])],
        "genre_slugs": [g["slug"] for g in r.get("genres", [])],
        "platforms": [p["platform"]["name"] for p in r.get("platforms", []) or []],
        "stores": [s["store"]["name"] for s in r.get("stores", []) or []],
        # Guaranteed clickable link to the game's RAWG page
        "site_url": f"https://rawg.io/games/{slug or item_id}" if (slug or item_id) else None,
    }
