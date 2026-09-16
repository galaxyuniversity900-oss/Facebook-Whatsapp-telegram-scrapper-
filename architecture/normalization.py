import html
import re
import unicodedata

URL_RE = re.compile(r"https?://[^\s<>]+", re.I)
WS_RE = re.compile(r"\s+")

def normalize_text(value: str | None, max_length: int = 100000) -> str:
    if not value: return ""
    value = unicodedata.normalize("NFKC", value)
    value = html.unescape(value)
    value = WS_RE.sub(" ", value).strip()
    return value[:max_length]

def extract_urls(value: str) -> list[str]:
    return URL_RE.findall(value or "")
