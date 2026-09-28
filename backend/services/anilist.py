"""
Anime & Manga — AniList API (GraphQL, no API key required)
Docs: https://docs.anilist.co/
"""
import httpx

BASE_URL = "https://graphql.anilist.co"

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


async def _run(query: str, variables: dict):
    async with httpx.AsyncClient() as client:
        resp = await client.post(BASE_URL, json={"query": query, "variables": variables})
        resp.raise_for_status()
        data = resp.json()
    return data.get("data", {}).get("Page", {}).get("media", [])


async def search(query: str, limit: int = 10):
    media = await _run(_SEARCH_QUERY, {"search": query, "perPage": limit})
    return [_format_item(m) for m in media]


async def top(limit: int = 20):
    media = await _run(_TOP_QUERY, {"perPage": limit})
    return [_format_item(m) for m in media]


async def by_genre(genre_names: list[str], limit: int = 20):
    # AniList genre names match ours directly (Action, Comedy, Drama, Fantasy,
    # Romance, Sci-Fi, Slice of Life, Supernatural, etc.) — no id mapping needed.
    media = await _run(_GENRE_QUERY, {"genres": genre_names, "perPage": limit})
    return [_format_item(m) for m in media]


def _format_item(m: dict):
    title = m.get("title", {})
    return {
        "id": m.get("id"),
        "domain": "anime",
        "title": title.get("english") or title.get("romaji"),
        "overview": m.get("description"),
        "image": (m.get("coverImage") or {}).get("large"),
        "rating": (m.get("averageScore") or 0) / 10 if m.get("averageScore") else None,
        "genres": m.get("genres", []),
        "genre_ids": m.get("genres", []),  # AniList uses names, not numeric ids
        "url": m.get("siteUrl"),
    }