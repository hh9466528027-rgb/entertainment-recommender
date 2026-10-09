"""
Comics — Comic Vine API
Free API key: https://comicvine.gamespot.com/api/
"""
import httpx
from config import COMICVINE_API_KEY

BASE_URL = "https://comicvine.gamespot.com/api"
HEADERS = {"User-Agent": "EntertainmentRecommender/1.0"}


async def search(query: str, limit: int = 40):
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


async def search_page(query: str, page: int = 1):
    if not COMICVINE_API_KEY:
        return {"error": "COMICVINE_API_KEY not set. Add it to backend/.env"}
    page_size = 10
    async with httpx.AsyncClient(headers=HEADERS) as client:
        response = await client.get(
            f"{BASE_URL}/search/",
            params={
                "api_key": COMICVINE_API_KEY,
                "query": query,
                "resources": "volume",
                "format": "json",
                "limit": page_size,
                "page": page,
            },
        )
        response.raise_for_status()
        data = response.json()
    rows = data.get("results", [])
    total = int(data.get("number_of_total_results") or 0)
    return {
        "items": [_format_item(row) for row in rows if isinstance(row, dict)],
        "page": page,
        "has_more": page * page_size < total,
        "total_results": total,
        "source": "comicvine",
    }


def _format_item(r: dict):
    item_id = r.get("id")
    link = r.get("site_detail_url") or (f"https://comicvine.gamespot.com/volume/4050-{item_id}/" if item_id else None)
    return {
        "id": item_id,
        "domain": "comics",
        "title": r.get("name"),
        "overview": r.get("description"),
        "image": (r.get("image") or {}).get("medium_url"),
        "publisher": (r.get("publisher") or {}).get("name"),
        "start_year": r.get("start_year"),
        # Guaranteed clickable link
        "site_url": link,
    }
