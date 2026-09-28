"""
Comics — Comic Vine API
Free API key: https://comicvine.gamespot.com/api/
"""
import httpx
from config import COMICVINE_API_KEY

BASE_URL = "https://comicvine.gamespot.com/api"
HEADERS = {"User-Agent": "EntertainmentRecommender/1.0"}


async def search(query: str, limit: int = 20):
    if not COMICVINE_API_KEY:
        return {"error": "COMICVINE_API_KEY not set. Add it to backend/.env"}

    async with httpx.AsyncClient(headers=HEADERS) as client:
        resp = await client.get(
            f"{BASE_URL}/search/",
            params={
                "api_key": COMICVINE_API_KEY,
                "query": query,
                "resources": "volume",
                "format": "json",
                "limit": limit,
            },
        )
        resp.raise_for_status()
        data = resp.json()
    return [_format_item(r) for r in data.get("results", [])]


def _format_item(r: dict):
    return {
        "id": r.get("id"),
        "domain": "comics",
        "title": r.get("name"),
        "overview": r.get("description"),
        "image": (r.get("image") or {}).get("medium_url"),
        "publisher": (r.get("publisher") or {}).get("name"),
        "start_year": r.get("start_year"),
        "site_url": r.get("site_detail_url"),
    }