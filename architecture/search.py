from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class SearchQuery:
    text: str
    source: str | None = None
    limit: int = 50
    offset: int = 0

    def __post_init__(self):
        if not self.text.strip(): raise ValueError("search text cannot be empty")
        if not 1 <= self.limit <= 200: raise ValueError("limit must be 1..200")
        if self.offset < 0: raise ValueError("offset cannot be negative")
