"""
Anime provider with resilient fallbacks.

Primary: AniList GraphQL (no API key).
Fallback: Jikan REST API v4 (no API key).
Successful results are cached briefly so a temporary provider outage does not
immediately make the Anime category unavailable.
"""
import asyncio
import logging
import re
import time

import httpx

BASE_URL = "https://graphql.anilist.co"
JIKAN_URL = "https://api.jikan.moe/v4"
TIMEOUT = httpx.Timeout(18.0, connect=8.0)
HEADERS = {
    "Accept": "application/json",
    "User-Agent": "EntertainmentRecommender/1.0",
}
CACHE_SECONDS = 300
logger = logging.getLogger(__name__)
_CACHE = {}

_SEARCH_QUERY = """
query ($search: String, $perPage: Int) {
  Page(page: 1, perPage: $perPage) {
    media(search: $search, type: ANIME) {
      id
      title { romaji english }
      description(asHtml: false)
      genres
      averageScore
      coverImage { large }
      siteUrl
    }
  }
}
"""

_TOP_QUERY = """
query ($perPage: Int) {
  Page(page: 1, perPage: $perPage) {
    media(type: ANIME, sort: POPULARITY_DESC) {
      id
      title { romaji english }
      description(asHtml: false)
      genres
      averageScore
      coverImage { large }
      siteUrl
    }
  }
}
"""

_GENRE_QUERY = """
query ($genres: [String], $perPage: Int) {
  Page(page: 1, perPage: $perPage) {
    media(type: ANIME, genre_in: $genres, sort: POPULARITY_DESC) {
      id
      title { romaji english }
      description(asHtml: false)
      genres
      averageScore
      coverImage { large }
      siteUrl
    }
  }
}
"""

# MAL/Jikan genre IDs. Unknown genres remain supported by AniList; the Jikan
# fallback uses its top list when it cannot translate a selected genre.
_JIKAN_GENRES = {
    "action": 1,
    "adventure": 2,
    "comedy": 4,
    "mystery": 7,
    "drama": 8,
    "fantasy": 10,
    "horror": 14,
    "romance": 22,
    "sci fi": 24,
    "science fiction": 24,
    "slice of life": 36,
    "supernatural": 37,
    "psychological": 40,
    "thriller": 41,
    "seinen": 42,
    "josei": 43,
    "award winning": 46,
    "gourmet": 47,
    "workplace": 48,
}


def _normalize(value):
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def _cache_read(key, fresh_only=True):
    entry = _CACHE.get(key)
    if not entry:
        return None
    expires_at, items = entry
    if fresh_only and expires_at < time.monotonic():
        return None
    return [dict(item) for item in items]


def _cache_write(key, items):
    _CACHE[key] = (time.monotonic() + CACHE_SECONDS, [dict(item) for item in items])


async def _run(query: str, variables: dict):
    """Run AniList GraphQL with a short retry and explicit timeout."""
    last_error = None
    for attempt in range(2):
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT, headers=HEADERS) as client:
                response = await client.post(
                    BASE_URL,
                    json={"query": query, "variables": variables},
                )
                response.raise_for_status()
                payload = response.json()
            if payload.get("errors"):
                raise ValueError("AniList returned a GraphQL error")
            media = payload.get("data", {}).get("Page", {}).get("media", [])
            if not isinstance(media, list):
                raise ValueError("AniList returned an invalid media list")
            return media
        except (httpx.HTTPError, ValueError, TypeError, AttributeError) as exc:
            last_error = exc
            if attempt == 0:
                await asyncio.sleep(0.35)
    raise last_error or RuntimeError("AniList request failed")


async def _jikan(path: str, params: dict):
    async with httpx.AsyncClient(timeout=TIMEOUT, headers=HEADERS) as client:
        response = await client.get(f"{JIKAN_URL}/{path.lstrip('/')}", params=params)
        response.raise_for_status()
        payload = response.json()
    data = payload.get("data", [])
    if not isinstance(data, list):
        raise ValueError("Jikan returned an invalid media list")
    return data


def _format_item(media: dict):
    title_data = media.get("title")
    if isinstance(title_data, dict):
        title = title_data.get("english") or title_data.get("romaji")
    else:
        title = media.get("title_english") or title_data or media.get("title_japanese")

    raw_genres = media.get("genres") or []
    genres = [
        str(genre.get("name")) if isinstance(genre, dict) and genre.get("name")
        else str(genre)
        for genre in raw_genres
        if (isinstance(genre, dict) and genre.get("name")) or isinstance(genre, str)
    ]

    images = media.get("images") or {}
    jpg = images.get("jpg") or {}
    webp = images.get("webp") or {}
    cover = media.get("coverImage") or {}
    image = cover.get("large") or jpg.get("large_image_url") or webp.get("large_image_url") or jpg.get("image_url")

    score = media.get("averageScore")
    if score is not None:
        score = float(score) / 10
    else:
        score = media.get("score")
        score = float(score) if score is not None else None

    return {
        "id": media.get("id") or media.get("mal_id"),
        "domain": "anime",
        "title": title or "Untitled anime",
        "overview": media.get("description") or media.get("synopsis"),
        "image": image,
        "rating": score,
        "genres": genres,
        "genre_ids": genres,
        "site_url": media.get("siteUrl") or media.get("url"),
    }


async def _resolve(cache_key, query, variables, fallback_path, fallback_params):
    stale_items = _cache_read(cache_key, fresh_only=False)
    try:
        media = await _run(query, variables)
        items = [_format_item(item) for item in media if isinstance(item, dict)]
        if items:
            _cache_write(cache_key, items)
            return items
    except Exception as exc:
        logger.warning("AniList request failed (%s); trying Jikan fallback", type(exc).__name__)

    try:
        media = await _jikan(fallback_path, fallback_params)
        items = [_format_item(item) for item in media if isinstance(item, dict)]
        if items:
            _cache_write(cache_key, items)
            return items
    except Exception as exc:
        logger.warning("Jikan fallback failed (%s)", type(exc).__name__)

    if stale_items:
        return stale_items
    return {"error": "Anime suggestions are temporarily unavailable. Please try again shortly."}


async def search(query: str, limit: int = 20):
    clean_query = str(query or "").strip()
    if not clean_query:
        return {"error": "Enter a title to search for anime."}
    limit = max(1, min(int(limit), 40))
    key = f"search:{_normalize(clean_query)}:{limit}"
    params = {"q": clean_query, "limit": min(limit, 25)}
    return await _resolve(key, _SEARCH_QUERY, {"search": clean_query, "perPage": limit}, "anime", params)


async def top(limit: int = 40):
    limit = max(1, min(int(limit), 40))
    key = f"top:{limit}"
    params = {"limit": min(limit, 25), "order_by": "members", "sort": "desc"}
    return await _resolve(key, _TOP_QUERY, {"perPage": limit}, "top/anime", params)


async def by_genre(genre_names: list[str], limit: int = 40):
    genres = [str(name).strip() for name in (genre_names or []) if str(name).strip()]
    if not genres:
        return await top(limit)
    limit = max(1, min(int(limit), 40))
    key = f"genre:{','.join(sorted(_normalize(name) for name in genres))}:{limit}"
    ids = [_JIKAN_GENRES[_normalize(name)] for name in genres if _normalize(name) in _JIKAN_GENRES]
    if ids:
        fallback_path = "anime"
        params = {
            "genres": ",".join(map(str, sorted(set(ids)))),
            "order_by": "members",
            "sort": "desc",
            "limit": min(limit, 25),
        }
    else:
        fallback_path = "top/anime"
        params = {"limit": min(limit, 25), "order_by": "members", "sort": "desc"}
    return await _resolve(
        key,
        _GENRE_QUERY,
        {"genres": genres, "perPage": limit},
        fallback_path,
        params,
    )


_SEARCH_PAGE_QUERY = """
query ($page: Int, $perPage: Int, $search: String) {
  Page(page: $page, perPage: $perPage) {
    pageInfo { currentPage hasNextPage total }
    media(search: $search, type: ANIME) {
      id title { romaji english } description(asHtml: false) genres averageScore
      coverImage { large } siteUrl
    }
  }
}
"""
_TOP_PAGE_QUERY = """
query ($page: Int, $perPage: Int) {
  Page(page: $page, perPage: $perPage) {
    pageInfo { currentPage hasNextPage total }
    media(type: ANIME, sort: POPULARITY_DESC) {
      id title { romaji english } description(asHtml: false) genres averageScore
      coverImage { large } siteUrl
    }
  }
}
"""
_GENRE_PAGE_QUERY = """
query ($page: Int, $perPage: Int, $genres: [String]) {
  Page(page: $page, perPage: $perPage) {
    pageInfo { currentPage hasNextPage total }
    media(type: ANIME, genre_in: $genres, sort: POPULARITY_DESC) {
      id title { romaji english } description(asHtml: false) genres averageScore
      coverImage { large } siteUrl
    }
  }
}
"""


def _page_result(items, page, has_more, total_results=None, source="anilist"):
    return {
        "items": items,
        "page": page,
        "has_more": bool(has_more),
        "total_results": total_results,
        "source": source,
    }


async def _run_page(query: str, variables: dict):
    last_error = None
    for attempt in range(2):
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT, headers=HEADERS) as client:
                response = await client.post(BASE_URL, json={"query": query, "variables": variables})
                response.raise_for_status()
                payload = response.json()
            if payload.get("errors"):
                raise ValueError("AniList returned a GraphQL error")
            page_data = payload.get("data", {}).get("Page", {})
            media = page_data.get("media", [])
            if not isinstance(media, list):
                raise ValueError("AniList returned an invalid media list")
            return page_data
        except (httpx.HTTPError, ValueError, TypeError, AttributeError) as exc:
            last_error = exc
            if attempt == 0:
                await asyncio.sleep(0.35)
    raise last_error or RuntimeError("AniList request failed")


async def _jikan_page(path: str, params: dict, page: int):
    async with httpx.AsyncClient(timeout=TIMEOUT, headers=HEADERS) as client:
        response = await client.get(
            f"{JIKAN_URL}/{path.lstrip('/')}",
            params={**params, "page": page, "limit": min(int(params.get("limit", 25)), 25)},
        )
        response.raise_for_status()
        payload = response.json()
    rows = payload.get("data", [])
    pagination = payload.get("pagination", {}) or {}
    counts = pagination.get("items", {}) or {}
    items = [_format_item(row) for row in rows if isinstance(row, dict)]
    return _page_result(
        items,
        page,
        pagination.get("has_next_page", False),
        counts.get("total"),
        source="jikan",
    )


async def _resolve_page(query, variables, fallback_path, fallback_params, page, source=None):
    if source != "jikan":
        try:
            page_data = await _run_page(query, {**variables, "page": page, "perPage": 50})
            page_info = page_data.get("pageInfo", {}) or {}
            items = [_format_item(row) for row in page_data.get("media", []) if isinstance(row, dict)]
            has_more = bool(page_info.get("hasNextPage"))
            if items or has_more or source == "anilist":
                return _page_result(items, page, has_more, page_info.get("total"), "anilist")
        except Exception as exc:
            if source == "anilist":
                logger.warning("AniList page failed (%s)", type(exc).__name__)
                return {"error": "Anime suggestions are temporarily unavailable. Please try again shortly."}
            logger.warning("AniList page failed (%s); trying Jikan fallback", type(exc).__name__)
    try:
        return await _jikan_page(fallback_path, fallback_params, page)
    except Exception as exc:
        logger.warning("Jikan page failed (%s)", type(exc).__name__)
        return {"error": "Anime suggestions are temporarily unavailable. Please try again shortly."}


async def search_page(query: str, page: int = 1, source=None):
    clean_query = str(query or "").strip()
    if not clean_query:
        return {"error": "Enter a title to search for anime."}
    return await _resolve_page(
        _SEARCH_PAGE_QUERY,
        {"search": clean_query},
        "anime",
        {"q": clean_query, "limit": 25},
        page,
        source,
    )


async def top_page(page: int = 1, source=None):
    return await _resolve_page(
        _TOP_PAGE_QUERY,
        {},
        "top/anime",
        {"order_by": "members", "sort": "desc", "limit": 25},
        page,
        source,
    )


async def by_genre_page(genre_names: list[str], page: int = 1, source=None):
    genres = [str(name).strip() for name in (genre_names or []) if str(name).strip()]
    if not genres:
        return await top_page(page, source)
    ids = [_JIKAN_GENRES[_normalize(name)] for name in genres if _normalize(name) in _JIKAN_GENRES]
    fallback_path = "anime" if ids else "top/anime"
    fallback_params = (
        {"genres": ",".join(map(str, sorted(set(ids)))), "order_by": "members", "sort": "desc", "limit": 25}
        if ids else {"order_by": "members", "sort": "desc", "limit": 25}
    )
    return await _resolve_page(
        _GENRE_PAGE_QUERY,
        {"genres": genres},
        fallback_path,
        fallback_params,
        page,
        source,
    )
