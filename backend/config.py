import os
from dotenv import load_dotenv

load_dotenv()

TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
TMDB_BEARER_TOKEN = os.getenv("TMDB_BEARER_TOKEN", "")
RAWG_API_KEY = os.getenv("RAWG_API_KEY", "")
GOOGLE_BOOKS_API_KEY = os.getenv("GOOGLE_BOOKS_API_KEY", "")
COMICVINE_API_KEY = os.getenv("COMICVINE_API_KEY", "")
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "")

# Legal free-to-watch platforms we surface as "available on" suggestions
# for movies/series when a title is ad-supported / free legally.
FREE_LEGAL_STREAMING_HINTS = ["Tubi", "Pluto TV", "Crackle"]

# Legal free/public-domain novel sources
FREE_LEGAL_NOVEL_SOURCES = ["Project Gutenberg", "Open Library", "Royal Road"]
