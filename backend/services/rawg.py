"""
Games — RAWG Video Games Database API
Free API key: https://rawg.io/apidocs
"""
import httpx
from config import RAWG_API_KEY

BASE_URL = "https://api.rawg.io/api"


async def search(query: str, limit: int = 10):
    if not RAWG_API_KEY:
        return {"error": "RAWG_API_KEY not set. Add it to backend/.env"}

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/games", params={"key": RAWG_API_KEY, "search": query, "page_size": limit}
        )
        resp.raise_for_status()
        data = resp.json()
    return [_format_item(r) for r in data.get("results", [])]


async def popular(limit: int = 20):
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


async def by_genre(genre_slugs: list[str], limit: int = 20):
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


def _format_item(r: dict):
    return {
        "id": r.get("id"),
        "domain": "games",
        "title": r.get("name"),
        "image": r.get("background_image"),
        "rating": r.get("rating"),
        "genres": [g["name"] for g in r.get("genres", [])],
        "genre_slugs": [g["slug"] for g in r.get("genres", [])],
        "platforms": [p["platform"]["name"] for p in r.get("platforms", []) or []],
        "stores": [s["store"]["name"] for s in r.get("stores", []) or []],
    }
