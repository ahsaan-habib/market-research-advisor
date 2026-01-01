"""Web search through a self-hosted SearXNG (open source metasearch, no API
key, no per-query bill). `docker compose up -d searxng`; JSON output must be
enabled in its settings (see searxng/settings.yml)."""
from __future__ import annotations

from datetime import datetime

import httpx

from .. import config
from ..evidence import Evidence


def _date(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


async def fetch(query: str, client: httpx.AsyncClient, k: int = 5) -> list[Evidence]:
    r = await client.get(f"{config.SEARXNG_URL}/search", params={"q": query, "format": "json"})
    r.raise_for_status()
    out = []
    for hit in r.json().get("results", [])[:k]:
        out.append(Evidence(source_type="web", title=hit.get("title", ""), content=hit.get("content", "")[:600],
                            url=hit.get("url", ""), published_at=_date(hit.get("publishedDate"))))
    return out
