from __future__ import annotations

from urllib.parse import quote_plus

DEFAULT_SEARCH_URL = "https://duckduckgo.com/?q={query}"


def normalize_user_input(raw_text: str) -> str:
    text = (raw_text or "").strip()
    if not text:
        return ""
    if text.startswith("about:") or "://" in text:
        return text
    if _should_treat_as_search(text):
        return DEFAULT_SEARCH_URL.format(query=quote_plus(text))
    return f"http://{text}"


def normalize_start_url(raw_text: str, fallback: str) -> str:
    normalized = normalize_user_input(raw_text)
    return normalized or fallback


def _should_treat_as_search(text: str) -> bool:
    if " " in text:
        return True
    if text.startswith("localhost"):
        return False
    if "." in text:
        return False
    if ":" in text:
        host, _, port = text.rpartition(":")
        if host and port.isdigit():
            return False
    return True
