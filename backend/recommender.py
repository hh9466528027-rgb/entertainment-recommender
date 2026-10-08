"""
Content-based recommendation scoring.

Three signals, combined:
  1. Genre overlap — how many of the item's genres match the user's chosen
     genres, with an extra bonus once 2+ genres overlap (a much stronger
     taste signal than a single shared genre).
  2. Description overlap — the user's genre/favorite keywords checked
     against the item's own overview/description text. Catches matches
     genre tags alone miss (e.g. a "Drama" that's actually a heist story).
  3. Favorite match — user's favorite artist/author/director name found in
     the item's title/authors/artists/publisher.

No external ML library needed — this is plain text matching, fast enough
to run per-request with no training step or stored history required.
"""
import re


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9\s]", " ", (text or "").lower())


def _genre_overlap(item_genres: list[str], preferred_genres: list[str]) -> list[str]:
    pref_set = {g.lower() for g in preferred_genres if g}
    return [g for g in item_genres if g and g.lower() in pref_set]


def _description_overlap(item: dict, preferred_genres: list[str], favorites: list[str]) -> int:
    text = _normalize(item.get("overview") or item.get("description") or "")
    if not text:
        return 0
    keywords = {g.lower() for g in preferred_genres if g} | {f for f in favorites if f}
    return sum(1 for kw in keywords if kw and kw in text)


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
        matched = _genre_overlap(item_genres, preferred_genres)
        genre_count = len(matched)

        favorite_hit = None
        haystack = " ".join(
            str(item.get(k, "")) for k in ("title", "artists", "authors", "publisher")
        ).lower()
        for fav in favorites:
            if fav and fav in haystack:
                favorite_hit = fav
                break

        desc_hits = _description_overlap(item, preferred_genres, favorites)

        # --- Scoring ---
        score = genre_count * 3
        if genre_count >= 2:
            score += 4  # multi-genre overlap bonus — stronger signal than one match
        score += desc_hits * 1.5
        score += 5 if favorite_hit else 0

        # --- Explanation — reflects whichever signal actually drove the match ---
        if favorite_hit:
            reason = f"Because you like {favorite_hit.title()}"
        elif genre_count >= 2:
            reason = f"Matches {genre_count} of your genres: {', '.join(matched[:3])}"
        elif matched:
            reason = f"Matches your taste for {matched[0]}"
        elif desc_hits:
            reason = "Its description matches what you're into"
        else:
            reason = "Trending pick you might enjoy"

        scored.append({**item, "match_score": score, "why": reason})

    scored.sort(key=lambda x: x["match_score"], reverse=True)
    return scored