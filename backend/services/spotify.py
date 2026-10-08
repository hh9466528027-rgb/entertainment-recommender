"""Music discovery using Spotify when configured, with Apple/iTunes fallback.

Apple's public Search API supplies track metadata, artwork, store links, and
30-second previews where available. Results are cached and calls are kept below
Apple's documented approximate per-IP request rate.
"""
import logging
import os
import re
import time

import httpx

from config import SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET

TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_URL = "https://api.spotify.com/v1"
APPLE_SEARCH_URL = "https://itunes.apple.com/search"
APPLE_COUNTRY = os.getenv("ITUNES_COUNTRY", "IN").upper()
APPLE_CACHE_SECONDS = 15 * 60
APPLE_RATE_WINDOW_SECONDS = 60
APPLE_MAX_REQUESTS_PER_WINDOW = 18  # Apple documents approximately 20/minute.
REQUEST_TIMEOUT = httpx.Timeout(14.0, connect=5.0)
HEADERS = {
    "Accept": "application/json",
    "User-Agent": "EntertainmentRecommender/1.0",
}

logger = logging.getLogger(__name__)
_token_cache = {"access_token": None, "expires_at": 0}
_apple_cache = {}
_apple_request_times = []


def _cache_read(key, allow_stale=False):
    entry = _apple_cache.get(key)
    if not entry:
        return None
    expires_at, items = entry
    if not allow_stale and expires_at < time.monotonic():
        return None
    return [dict(item) for item in items]


def _cache_write(key, items):
    _apple_cache[key] = (
        time.monotonic() + APPLE_CACHE_SECONDS,
        [dict(item) for item in items],
    )


def _apple_request_allowed():
    now = time.monotonic()
    cutoff = now - APPLE_RATE_WINDOW_SECONDS
    while _apple_request_times and _apple_request_times[0] <= cutoff:
        _apple_request_times.pop(0)
    if len(_apple_request_times) >= APPLE_MAX_REQUESTS_PER_WINDOW:
        return False
    _apple_request_times.append(now)
    return True


async def _get_token():
    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
        return None
    if _token_cache["access_token"] and _token_cache["expires_at"] > time.time():
        return _token_cache["access_token"]

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, headers=HEADERS) as client:
        response = await client.post(
            TOKEN_URL,
            data={"grant_type": "client_credentials"},
            auth=(SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET),
        )
        response.raise_for_status()
        data = response.json()

    _token_cache["access_token"] = data["access_token"]
    _token_cache["expires_at"] = time.time() + data.get("expires_in", 3600) - 60
    return _token_cache["access_token"]


async def _spotify_search(query, search_type, limit):
    token = await _get_token()
    if not token:
        return None

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, headers=HEADERS) as client:
        response = await client.get(
            f"{SPOTIFY_URL}/search",
            headers={"Authorization": f"Bearer {token}"},
            params={"q": query, "type": search_type, "limit": min(limit, 10)},
        )
        response.raise_for_status()
        payload = response.json()

    key = f"{search_type}s"
    items = payload.get(key, {}).get("items", [])
    if not isinstance(items, list):
        raise ValueError("Spotify returned an invalid search result")
    return [_format_spotify_item(item, search_type) for item in items]


async def _apple_search(query, search_type="track", limit=20):
    query = str(query or "").strip()
    if not query:
        return {"error": "Enter a song, artist, or genre to search for music."}

    limit = max(1, min(int(limit), 50))
    entity = {"track": "song", "artist": "musicArtist", "album": "album"}.get(search_type, "song")
    key = (query.casefold(), entity, limit, APPLE_COUNTRY)
    cached = _cache_read(key)
    if cached is not None:
        return cached

    if not _apple_request_allowed():
        stale = _cache_read(key, allow_stale=True)
        if stale is not None:
            return stale
        return {"error": "Music search is busy right now. Please try again shortly."}

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, headers=HEADERS) as client:
            response = await client.get(
                APPLE_SEARCH_URL,
                params={
                    "term": query,
                    "entity": entity,
                    "limit": limit,
                    "country": APPLE_COUNTRY.lower(),
                },
            )
            response.raise_for_status()
            payload = response.json()
        results = payload.get("results", [])
        if not isinstance(results, list):
            raise ValueError("Apple returned an invalid search result")
        items = []
        for result in results:
            if not isinstance(result, dict):
                continue
            item = _format_apple_item(result, search_type)
            if item is not None:
                items.append(item)
        _cache_write(key, items)
        return items
    except (httpx.HTTPError, ValueError, TypeError, KeyError) as exc:
        logger.warning("Apple Music search failed (%s)", type(exc).__name__)
        stale = _cache_read(key, allow_stale=True)
        if stale is not None:
            return stale
        return {"error": "Music recommendations are temporarily unavailable. Please try again shortly."}


async def search(query: str, search_type: str = "track", limit: int = 20):
    """Search Spotify first when configured; otherwise use Apple's public catalog."""
    query = str(query or "").strip()
    if not query:
        return {"error": "Enter a song, artist, or genre to search for music."}

    limit = max(1, min(int(limit), 50))
    normalized_type = search_type if search_type in {"track", "artist", "album"} else "track"
    try:
        spotify_items = await _spotify_search(query, normalized_type, limit)
        if spotify_items:
            return spotify_items
    except Exception as exc:
        # Spotify development-mode access may be restricted; never let it block
        # the public Apple catalog fallback.
        logger.info("Spotify unavailable (%s); using Apple fallback", type(exc).__name__)

    return await _apple_search(query, normalized_type, limit)


async def explore(limit: int = 20):
    """Offer a broad pop starting shelf when the user has not supplied favorites."""
    items = await search("pop", search_type="track", limit=limit)
    if isinstance(items, list):
        for item in items:
            item.setdefault("why", "A pop pick to explore")
    return items


async def by_artist_or_genre(seed: str, limit: int = 20):
    """Search from a favorite artist or music preference."""
    return await search(str(seed or "pop"), search_type="track", limit=limit)


def _format_spotify_item(item: dict, search_type: str):
    if search_type == "track":
        album = item.get("album", {}) or {}
        images = album.get("images") or []
        return {
            "id": item.get("id"),
            "domain": "music",
            "title": item.get("name"),
            "artists": [artist.get("name") for artist in item.get("artists", []) if artist.get("name")],
            "album": album.get("name"),
            "image": images[0].get("url") if images else None,
            "listen_link": item.get("external_urls", {}).get("spotify"),
            "preview_url": item.get("preview_url"),
            "provider": "Spotify",
        }
    images = item.get("images") or []
    return {
        "id": item.get("id"),
        "domain": "music",
        "title": item.get("name"),
        "image": images[0].get("url") if images else None,
        "listen_link": item.get("external_urls", {}).get("spotify"),
        "provider": "Spotify",
    }


def _format_apple_item(item: dict, search_type: str):
    title = item.get("trackName") or item.get("collectionName") or item.get("artistName")
    if not title:
        return None

    artwork = item.get("artworkUrl100") or item.get("artworkUrl60")
    if artwork:
        artwork = re.sub(r"\d{2,4}x\d{2,4}", "600x600", artwork, count=1)

    artists = [item["artistName"]] if item.get("artistName") else []
    genre = item.get("primaryGenreName")
    return {
        "id": item.get("trackId") or item.get("collectionId") or item.get("artistId"),
        "domain": "music",
        "title": title,
        "artists": artists,
        "album": item.get("collectionName"),
        "image": artwork,
        "rating": None,
        "genres": [genre] if genre else [],
        "genre_ids": [],
        "release_year": (item.get("releaseDate") or "")[:4] or None,
        "listen_link": item.get("trackViewUrl") or item.get("collectionViewUrl") or item.get("artistViewUrl"),
        "preview_url": item.get("previewUrl"),
        "provider": "Apple Music / iTunes",
    }
