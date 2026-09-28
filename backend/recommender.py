"""
Lightweight, dependency-free recommendation scoring.

Approach: each domain service already returns items tagged with genres.
Given the user's stated preferences for a domain, we:
  1. fetch a pool of candidates (by genre if possible, else popular/trending)
  2. score each item by how many of its genres overlap the user's preferred genres
  3. attach a short, one-line explanation
No ML model needed for the MVP — this keeps it fast and dependency-light,
and can be swapped for embeddings-based scoring later without changing
the API surface.
"""


def _overlap(item_genres: list[str], preferred_genres: list[str]) -> list[str]:
    item_set = {g.lower() for g in item_genres if g}
    pref_set = {g.lower() for g in preferred_genres if g}
    return [g for g in item_genres if g and g.lower() in pref_set]


def score_and_explain(items: list[dict], preferences: dict) -> list[dict]:
    """
    preferences example:
      {"genres": ["Action", "Sci-Fi"], "favorites": ["Christopher Nolan"]}
    """
    preferred_genres = preferences.get("genres", []) or []
    favorites = [f.lower() for f in preferences.get("favorites", []) or []]

    scored = []
    for item in items:
        item_genres = item.get("genres") or item.get("genre_ids") or []
        item_genres = [str(g) for g in item_genres]
        matched = _overlap(item_genres, preferred_genres)

        favorite_hit = None
        haystack = " ".join(
            str(item.get(k, "")) for k in ("title", "artists", "authors", "publisher")
        ).lower()
        for fav in favorites:
            if fav and fav in haystack:
                favorite_hit = fav
                break

        score = len(matched) * 2 + (3 if favorite_hit else 0)

        if favorite_hit:
            reason = f"Because you like {favorite_hit.title()}"
        elif matched:
            reason = f"Matches your taste for {matched[0]}"
        else:
            reason = "Trending pick you might enjoy"

        item = {**item, "match_score": score, "why": reason}
        scored.append(item)

    scored.sort(key=lambda x: x["match_score"], reverse=True)
    return scored
