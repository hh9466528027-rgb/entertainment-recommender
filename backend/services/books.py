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

# Free public APIs can be slow or briefly down — fail fast and gracefully
# instead of hanging the request or crashing the whole endpoint.
TIMEOUT = httpx.Timeout(12.0, connect=8.0)


async def search(query: str, limit: int = 20):
    params = {"q": query, "maxResults": limit}
    if GOOGLE_BOOKS_API_KEY:
        params["key"] = GOOGLE_BOOKS_API_KEY

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(GOOGLE_BOOKS_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
        return [_format_google_item(r) for r in data.get("items", [])]
    except httpx.HTTPError:
        return {"error": "Google Books is temporarily unreachable. Try again in a moment."}


async def by_genre(genre: str, limit: int = 40):
    """Google Books subject search doubles as genre-based discovery."""
    params = {"q": f"subject:{genre}", "maxResults": min(limit, 40), "orderBy": "relevance"}
    if GOOGLE_BOOKS_API_KEY:
        params["key"] = GOOGLE_BOOKS_API_KEY

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(GOOGLE_BOOKS_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
        items = [_format_google_item(r) for r in data.get("items", [])]
        if items:
            return items
    except httpx.HTTPError:
        pass

    # Fall back to free/legal public-domain results if the genre search
    # comes back empty or Google Books is unreachable.
    return await free_legal_popular(limit)


async def free_legal_search(query: str, limit: int = 20):
    """Public-domain / free-to-read full texts (legal) via Project Gutenberg."""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(GUTENDEX_URL, params={"search": query})
            resp.raise_for_status()
            data = resp.json()
        return [_format_gutenberg_item(r) for r in data.get("results", [])[:limit]]
    except httpx.HTTPError:
        return {"error": "Project Gutenberg is temporarily unreachable. Try again in a moment."}


async def free_legal_popular(limit: int = 40):
    """Most-downloaded public domain books — better for a trending/explore feed."""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(GUTENDEX_URL, params={"sort": "popular"})
            resp.raise_for_status()
            data = resp.json()
        return [_format_gutenberg_item(r) for r in data.get("results", [])[:limit]]
    except httpx.HTTPError:
        return {"error": "Project Gutenberg is temporarily unreachable. Try again in a moment."}


def _format_google_item(r: dict):
    info = r.get("volumeInfo", {})
    sale = r.get("saleInfo", {})
    book_id = r.get("id")
    link = sale.get("buyLink") or info.get("previewLink") or info.get("infoLink") \
        or (f"https://books.google.com/books?id={book_id}" if book_id else None)
    return {
        "id": book_id,
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
        "site_url": link,
    }


def _format_gutenberg_item(r: dict):
    gid = r.get("id")
    read_link = r.get("formats", {}).get("text/html") \
        or r.get("formats", {}).get("application/epub+zip") \
        or (f"https://www.gutenberg.org/ebooks/{gid}" if gid else None)
    return {
        "id": gid,
        "domain": "novels",
        "title": r.get("title"),
        "authors": [a["name"] for a in r.get("authors", [])],
        "genres": r.get("subjects", [])[:5],
        "image": r.get("formats", {}).get("image/jpeg"),
        "read_link": read_link,
        "is_free": True,
        "source": "Project Gutenberg (public domain, free & legal)",
    }