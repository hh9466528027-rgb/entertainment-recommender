"""
Novels — Google Books API (metadata/purchase links) +
Project Gutenberg / Open Library (free, legal, public-domain full texts)
Google Books docs: https://developers.google.com/books
Gutenberg (via Gutendex, free, no key): https://gutendex.com/
Open Library docs: https://openlibrary.org/developers/api
"""
import httpx
from config import GOOGLE_BOOKS_API_KEY

GOOGLE_BOOKS_URL = "https://www.googleapis.com/books/v1/volumes"
GUTENDEX_URL = "https://gutendex.com/books/"
OPEN_LIBRARY_URL = "https://openlibrary.org/search.json"


async def search(query: str, limit: int = 10):
    params = {"q": query, "maxResults": limit}
    if GOOGLE_BOOKS_API_KEY:
        params["key"] = GOOGLE_BOOKS_API_KEY

    async with httpx.AsyncClient() as client:
        resp = await client.get(GOOGLE_BOOKS_URL, params=params)
        resp.raise_for_status()
        data = resp.json()
    return [_format_google_item(r) for r in data.get("items", [])]


async def by_genre(genre: str, limit: int = 20):
    """Google Books subject search doubles as genre-based discovery."""
    params = {"q": f"subject:{genre}", "maxResults": limit, "orderBy": "relevance"}
    if GOOGLE_BOOKS_API_KEY:
        params["key"] = GOOGLE_BOOKS_API_KEY

    async with httpx.AsyncClient() as client:
        resp = await client.get(GOOGLE_BOOKS_URL, params=params)
        resp.raise_for_status()
        data = resp.json()
    return [_format_google_item(r) for r in data.get("items", [])]


async def free_legal_search(query: str, limit: int = 10):
    """Public-domain / free-to-read full texts (legal) via Project Gutenberg."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(GUTENDEX_URL, params={"search": query})
        resp.raise_for_status()
        data = resp.json()
    return [_format_gutenberg_item(r) for r in data.get("results", [])[:limit]]


async def free_legal_popular(limit: int = 20):
    """Most-downloaded public domain books — better for a trending/explore feed."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(GUTENDEX_URL, params={"sort": "popular"})
        resp.raise_for_status()
        data = resp.json()
    return [_format_gutenberg_item(r) for r in data.get("results", [])[:limit]]


def _format_google_item(r: dict):
    info = r.get("volumeInfo", {})
    sale = r.get("saleInfo", {})
    return {
        "id": r.get("id"),
        "domain": "novels",
        "title": info.get("title"),
        "authors": info.get("authors", []),
        "overview": info.get("description"),
        "image": (info.get("imageLinks") or {}).get("thumbnail"),
        "rating": info.get("averageRating"),
        "genres": info.get("categories", []),
        "buy_link": sale.get("buyLink"),
        "preview_link": info.get("previewLink"),
        "is_free": sale.get("saleability") == "FREE",
    }


def _format_gutenberg_item(r: dict):
    return {
        "id": r.get("id"),
        "domain": "novels",
        "title": r.get("title"),
        "authors": [a["name"] for a in r.get("authors", [])],
        "genres": r.get("subjects", [])[:5],
        "image": r.get("formats", {}).get("image/jpeg"),
        "read_link": r.get("formats", {}).get("text/html")
        or r.get("formats", {}).get("application/epub+zip"),
        "is_free": True,
        "source": "Project Gutenberg (public domain, free & legal)",
    }