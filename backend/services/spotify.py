"""
Music — Spotify Web API
Free developer account: https://developer.spotify.com/dashboard
Uses the Client Credentials flow (app-level access, no user login needed
for search/browse). User account linking for personalized listening
history would use the Authorization Code flow instead (see README).
"""
import time
import httpx
from config import SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET

TOKEN_URL = "https://accounts.spotify.com/api/token"
BASE_URL = "https://api.spotify.com/v1"

_token_cache = {"access_token": None, "expires_at": 0}


async def _get_token():
    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
        return None
    if _token_cache["access_token"] and _token_cache["expires_at"] > time.time():
        return _token_cache["access_token"]

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            TOKEN_URL,
            data={"grant_type": "client_credentials"},
            auth=(SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET),
        )
        resp.raise_for_status()
        data = resp.json()

    _token_cache["access_token"] = data["access_token"]
    _token_cache["expires_at"] = time.time() + data.get("expires_in", 3600) - 60
    return _token_cache["access_token"]


async def search(query: str, search_type: str = "track", limit: int = 10):
    token = await _get_token()
    if not token:
        return {"error": "SPOTIFY_CLIENT_ID / SECRET not set. Add them to backend/.env"}

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/search",
            headers={"Authorization": f"Bearer {token}"},
            params={"q": query, "type": search_type, "limit": limit},
        )
        resp.raise_for_status()
        data = resp.json()

    key = f"{search_type}s"
    return [_format_item(r, search_type) for r in data.get(key, {}).get("items", [])]


async def by_artist_or_genre(seed: str, limit: int = 20):
    """Search-based discovery seeded by a favorite artist or genre name."""
    return await search(seed, search_type="track", limit=limit)


def _format_item(r: dict, search_type: str):
    if search_type == "track":
        return {
            "id": r.get("id"),
            "domain": "music",
            "title": r.get("name"),
            "artists": [a["name"] for a in r.get("artists", [])],
            "image": (r.get("album", {}).get("images") or [{}])[0].get("url"),
            "listen_link": r.get("external_urls", {}).get("spotify"),
            "preview_url": r.get("preview_url"),
        }
    return {
        "id": r.get("id"),
        "domain": "music",
        "title": r.get("name"),
        "image": (r.get("images") or [{}])[0].get("url") if r.get("images") else None,
        "listen_link": r.get("external_urls", {}).get("spotify"),
    }
