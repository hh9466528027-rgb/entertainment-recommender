"""
Novel discovery through Google Books, Project Gutenberg (Gutendex), and
Open Library. Provider failures are handled here so the API returns usable
fallback results or a clear error instead of an unhandled HTTP 500.
"""
import logging

import httpx
from config import GOOGLE_BOOKS_API_KEY

GOOGLE_BOOKS_URL = "https://www.googleapis.com/books/v1/volumes"
GUTENDEX_URL = "https://gutendex.com/books/"
OPEN_LIBRARY_URL = "https://openlibrary.org/search.json"
TIMEOUT = httpx.Timeout(18.0, connect=8.0)
HEADERS = {
    "Accept": "application/json",
    "User-Agent": "EntertainmentRecommender/1.0",
}
OPEN_LIBRARY_FIELDS = (
    "key,title,author_name,cover_i,first_publish_year,public_scan_b,has_fulltext,subject"
)
logger = logging.getLogger(__name__)


async def _get_json(url: str, params: dict):
    async with httpx.AsyncClient(timeout=TIMEOUT, headers=HEADERS) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response.json()


def _log_provider_failure(provider: str, exc: Exception):
    # Avoid logging full request URLs because Google Books API keys may appear
    # in query parameters.
    logger.warning("%s request failed (%s)", provider, type(exc).__name__)


def _google_params(query: str, limit: int, **extra):
    params = {"q": query, "maxResults": min(max(1, int(limit)), 40), **extra}
    if GOOGLE_BOOKS_API_KEY:
        params["key"] = GOOGLE_BOOKS_API_KEY
    return params


async def _google_search(query: str, limit: int = 20, **extra):
    data = await _get_json(GOOGLE_BOOKS_URL, _google_params(query, limit, **extra))
    return [_format_google_item(row) for row in data.get("items", []) if isinstance(row, dict)]


async def _gutendex_search(query: str, limit: int = 20):
    data = await _get_json(GUTENDEX_URL, {"search": query})
    rows = data.get("results", [])
    return [_format_gutenberg_item(row) for row in rows[:limit] if isinstance(row, dict)]


async def _gutendex_topic(topic: str, limit: int = 20):
    data = await _get_json(GUTENDEX_URL, {"topic": topic})
    rows = data.get("results", [])
    return [_format_gutenberg_item(row) for row in rows[:limit] if isinstance(row, dict)]


async def _open_library_search(query: str, limit: int = 20, public_only: bool = False):
    params = {
        "q": query,
        "limit": min(max(1, int(limit)) * 2, 100),
        "fields": OPEN_LIBRARY_FIELDS,
    }
    data = await _get_json(OPEN_LIBRARY_URL, params)
    rows = data.get("docs", [])
    items = [_format_open_library_item(row) for row in rows if isinstance(row, dict)]
    if public_only:
        items = [item for item in items if item.get("is_free")]
    return items[:limit]


async def search(query: str, limit: int = 20):
    query = str(query or "").strip()
    if not query:
        return {"error": "Enter a title or author to search for novels."}

    try:
        items = await _google_search(query, limit)
        if items:
            return items
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        _log_provider_failure("Google Books", exc)

    try:
        items = await _gutendex_search(query, limit)
        if items:
            return items
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        _log_provider_failure("Project Gutenberg", exc)

    try:
        return await _open_library_search(query, limit)
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        _log_provider_failure("Open Library", exc)
        return {"error": "Book search is temporarily unavailable. Please try again shortly."}


async def by_genre(genre: str, limit: int = 40):
    genre = str(genre or "fiction").strip() or "fiction"
    try:
        items = await _google_search(f"subject:{genre}", limit, orderBy="relevance")
        if items:
            return items
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        _log_provider_failure("Google Books", exc)

    try:
        items = await _gutendex_topic(genre, limit)
        if items:
            return items
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        _log_provider_failure("Project Gutenberg", exc)

    try:
        items = await _open_library_search(f"subject:{genre}", limit)
        if items:
            return items
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        _log_provider_failure("Open Library", exc)

    return await free_legal_popular(limit)


async def free_legal_search(query: str, limit: int = 20):
    """Public-domain/full-text results, with Open Library public scans as backup."""
    try:
        items = await _gutendex_search(query, limit)
        if items:
            return items
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        _log_provider_failure("Project Gutenberg", exc)

    try:
        items = await _open_library_search(query, limit, public_only=True)
        if items:
            return items
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        _log_provider_failure("Open Library", exc)
        return {"error": "Free book search is temporarily unavailable. Please try again shortly."}
    return []


async def free_legal_popular(limit: int = 40):
    """Popular public-domain books; fall back to public scans in Open Library."""
    try:
        data = await _get_json(GUTENDEX_URL, {"sort": "popular"})
        rows = data.get("results", [])
        items = [_format_gutenberg_item(row) for row in rows[:limit] if isinstance(row, dict)]
        if items:
            return items
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        _log_provider_failure("Project Gutenberg", exc)

    try:
        items = await _open_library_search("subject:fiction", limit, public_only=True)
        if items:
            return items
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        _log_provider_failure("Open Library", exc)
        return {"error": "Novel suggestions are temporarily unavailable. Please try again shortly."}
    return []


def _book_page(items, page, has_more, total_results=None, source=None):
    return {
        "items": items,
        "page": page,
        "has_more": bool(has_more),
        "total_results": total_results,
        "source": source,
    }


async def _google_page(query: str, page: int, **extra):
    page_size = 40
    start = (page - 1) * page_size
    data = await _get_json(
        GOOGLE_BOOKS_URL,
        _google_params(query, page_size, startIndex=start, **extra),
    )
    rows = data.get("items", [])
    total = int(data.get("totalItems") or 0)
    return _book_page(
        [_format_google_item(row) for row in rows if isinstance(row, dict)],
        page,
        start + len(rows) < min(total, 1000),
        total,
        "google_books",
    )


async def _gutendex_page(params: dict, page: int):
    data = await _get_json(GUTENDEX_URL, {**params, "page": page})
    rows = data.get("results", [])
    return _book_page(
        [_format_gutenberg_item(row) for row in rows if isinstance(row, dict)],
        page,
        bool(data.get("next")),
        data.get("count"),
        "gutendex",
    )


async def _open_library_page(query: str, page: int, public_only: bool = False):
    page_size = 40
    offset = (page - 1) * page_size
    data = await _get_json(
        OPEN_LIBRARY_URL,
        {"q": query, "offset": offset, "limit": page_size, "fields": OPEN_LIBRARY_FIELDS},
    )
    rows = data.get("docs", [])
    items = [_format_open_library_item(row) for row in rows if isinstance(row, dict)]
    if public_only:
        items = [item for item in items if item.get("is_free")]
    total = int(data.get("numFound", data.get("num_found", 0)) or 0)
    return _book_page(items, page, offset + len(rows) < total, total, "open_library")


async def _novel_page(query, page, source, mode, public_only=False):
    if source:
        providers = [source]
    elif mode == "popular":
        providers = ["gutendex", "open_library"]
    else:
        providers = ["google_books", "gutendex", "open_library"]
    for provider in providers:
        try:
            if provider == "google_books" and mode != "popular":
                google_query = f"subject:{query}" if mode == "genre" else query
                result = await _google_page(google_query, page, orderBy="relevance")
            elif provider == "gutendex":
                params = {"sort": "popular"} if mode == "popular" else ({"topic": query} if mode == "genre" else {"search": query})
                result = await _gutendex_page(params, page)
            elif provider == "open_library":
                ol_query = "subject:fiction" if mode == "popular" else (f"subject:{query}" if mode == "genre" else query)
                result = await _open_library_page(ol_query, page, public_only=public_only)
            else:
                continue
            if result["items"] or source:
                return result
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            _log_provider_failure(provider, exc)
            if source:
                break
    return _book_page([], page, False, 0, source or providers[-1])


async def search_page(query: str, page: int = 1, source=None):
    query = str(query or "").strip()
    if not query:
        return {"error": "Enter a title or author to search for novels."}
    return await _novel_page(query, page, source, "search")


async def by_genre_page(genre: str, page: int = 1, source=None):
    genre = str(genre or "fiction").strip() or "fiction"
    return await _novel_page(genre, page, source, "genre")


async def free_legal_popular_page(page: int = 1, source=None):
    return await _novel_page("fiction", page, source, "popular", public_only=True)


def _format_google_item(row: dict):
    info = row.get("volumeInfo") or {}
    sale = row.get("saleInfo") or {}
    book_id = row.get("id")
    link = (
        sale.get("buyLink")
        or info.get("previewLink")
        or info.get("infoLink")
        or (f"https://books.google.com/books?id={book_id}" if book_id else None)
    )
    image_links = info.get("imageLinks") or {}
    image = image_links.get("thumbnail") or image_links.get("smallThumbnail")
    return {
        "id": book_id,
        "domain": "novels",
        "title": info.get("title") or "Untitled book",
        "authors": info.get("authors", []),
        "overview": info.get("description"),
        "image": image,
        "rating": info.get("averageRating"),
        "genres": info.get("categories", []),
        "buy_link": sale.get("buyLink"),
        "preview_link": info.get("previewLink"),
        "is_free": sale.get("saleability") == "FREE",
        "site_url": link,
        "source": "Google Books",
    }


def _format_gutenberg_item(row: dict):
    book_id = row.get("id")
    formats = row.get("formats") or {}
    authors = [
        author.get("name") for author in row.get("authors", [])
        if isinstance(author, dict) and author.get("name")
    ]
    read_link = (
        formats.get("text/html")
        or formats.get("application/epub+zip")
        or (f"https://www.gutenberg.org/ebooks/{book_id}" if book_id else None)
    )
    return {
        "id": book_id,
        "domain": "novels",
        "title": row.get("title") or "Untitled book",
        "authors": authors,
        "genres": (row.get("subjects") or [])[:5],
        "image": formats.get("image/jpeg"),
        "read_link": read_link,
        "site_url": read_link,
        "is_free": True,
        "source": "Project Gutenberg (public domain, free & legal)",
    }


def _format_open_library_item(row: dict):
    key = row.get("key")
    site_url = f"https://openlibrary.org{key}" if key else "https://openlibrary.org"
    cover_id = row.get("cover_i")
    public_scan = bool(row.get("public_scan_b"))
    return {
        "id": key or row.get("title"),
        "domain": "novels",
        "title": row.get("title") or "Untitled book",
        "authors": row.get("author_name") or [],
        "overview": None,
        "image": f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg" if cover_id else None,
        "rating": None,
        "genres": (row.get("subject") or [])[:5],
        "is_free": public_scan,
        "read_link": site_url if public_scan else None,
        "site_url": site_url,
        "source": "Open Library",
        "first_publish_year": row.get("first_publish_year"),
    }
