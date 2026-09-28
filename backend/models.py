from pydantic import BaseModel
from typing import Optional


class Preferences(BaseModel):
    genres: Optional[list[str]] = []
    favorites: Optional[list[str]] = []  # favorite artists/authors/directors etc.
