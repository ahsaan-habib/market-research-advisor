"""News from RSS/Atom feeds you choose (feeds.yaml). Filtered by keyword and
by age: news older than MAX_NEWS_AGE_H is dropped, not just flagged."""
from __future__ import annotations

import asyncio
from calendar import timegm
from datetime import datetime, timezone
from pathlib import Path

import feedparser
import httpx
import yaml

from .. import config
from ..evidence import Evidence


def feeds() -> list[dict]:
    p = Path(config.FEEDS_FILE)
    return yaml.safe_load(p.read_text()).get("feeds", []) if p.exists() else []


async def _one(feed: dict, client: httpx.AsyncClient) -> list[Evidence]:
    try:
        r = await client.get(feed["url"])
        r.raise_for_status()
    except httpx.HTTPError:
        return []
    parsed = await asyncio.to_thread(feedparser.parse, r.content)
    out = []
    for e in parsed.entries:
        ts = e.get("published_parsed") or e.get("updated_parsed")
        when = datetime.fromtimestamp(timegm(ts), tz=timezone.utc) if ts else None
        out.append(Evidence(source_type="news", title=f"{feed['name']}: {e.get('title', '')}",
                            content=(e.get("summary") or "")[:600], url=e.get("link", ""), published_at=when))
    return out


async def fetch(topics: list[str], client: httpx.AsyncClient, k: int = 6) -> list[Evidence]:
    batches = await asyncio.gather(*(_one(f, client) for f in feeds()))
    words = [w.lower() for t in topics for w in t.split() if len(w) > 3]
    items = []
    for ev in (e for b in batches for e in b):
        age = ev.age_hours()
        if age is None or age > config.MAX_NEWS_AGE_H:
            continue
        text = f"{ev.title} {ev.content}".lower()
        score = sum(w in text for w in words)
        if score:
            items.append((score, ev))
    items.sort(key=lambda x: (x[0], x[1].published_at), reverse=True)
    return [ev for _, ev in items[:k]]
