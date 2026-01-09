import asyncio
from datetime import datetime, timedelta, timezone

import httpx

from advisor import config
from advisor.sources import internal, news, quotes, search


def client(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=True)


def run(coro):
    return asyncio.run(coro)


def csv_rows(last: datetime, n: int = 30):
    lines = ["Date,Open,High,Low,Close,Volume"]
    for i in range(n):
        d = last - timedelta(days=n - 1 - i)
        lines.append(f"{d:%Y-%m-%d},1,1,1,{100 + i},10")
    return "\n".join(lines)


def test_quotes_summary_and_staleness():
    today = datetime.now(timezone.utc)

    async def go(text):
        async with client(lambda r: httpx.Response(200, text=text)) as c:
            return await quotes.fetch("AAPL.US", c)

    ev = run(go(csv_rows(today)))
    assert ev.content.startswith("AAPL.US last close 129") and "1d +0.8%" in ev.content and not ev.stale
    old = run(go(csv_rows(today - timedelta(days=10))))
    assert old.stale and "days old" in old.note


def test_quotes_no_data_is_a_gap_not_evidence():
    async def go():
        async with client(lambda r: httpx.Response(200, text="No data")) as c:
            return await quotes.fetch("nope.us", c)
    assert run(go()) == []


def test_search_dates_are_timezone_aware():
    hits = {"results": [{"title": "T", "content": "C", "url": "https://x", "publishedDate": "2026-01-02T10:00:00"},
                        {"title": "U", "content": "D", "url": "https://y", "publishedDate": "2026-01-02T10:00:00Z"},
                        {"title": "V", "content": "E", "url": "https://z", "publishedDate": "yesterday"}]}

    async def go():
        async with client(lambda r: httpx.Response(200, json=hits)) as c:
            return await search.fetch("q", c)
    evs = run(go())
    assert [e.published_at.tzinfo is not None for e in evs[:2]] == [True, True] and evs[2].published_at is None
    assert all(e.age_hours() is None or e.age_hours() > 0 for e in evs)       # no naive/aware TypeError


def test_news_filters_by_topic_and_age(tmp_path, monkeypatch):
    fresh = datetime.now(timezone.utc) - timedelta(hours=3)
    rss = f"""<?xml version="1.0"?><rss version="2.0"><channel><title>N</title>
      <item><title>Email marketing costs rise</title><link>https://n/1</link>
        <pubDate>{fresh:%a, %d %b %Y %H:%M:%S +0000}</pubDate><description>CPMs up</description></item>
      <item><title>Email marketing in 2019</title><link>https://n/2</link>
        <pubDate>Mon, 01 Apr 2019 10:00:00 +0000</pubDate><description>old</description></item>
      <item><title>Football results</title><link>https://n/3</link>
        <pubDate>{fresh:%a, %d %b %Y %H:%M:%S +0000}</pubDate><description>x</description></item>
    </channel></rss>"""
    feeds = tmp_path / "feeds.yaml"
    feeds.write_text("feeds:\n  - name: Biz\n    url: https://feeds/biz\n  - name: Down\n    url: https://feeds/down\n")
    monkeypatch.setattr(config, "FEEDS_FILE", str(feeds))

    def handler(r):
        return httpx.Response(200, text=rss) if r.url.path == "/biz" else httpx.Response(503)

    async def go():
        async with client(handler) as c:
            return await news.fetch(["email marketing"], c)
    evs = run(go())
    assert [e.url for e in evs] == ["https://n/1"] and evs[0].title == "Biz: Email marketing costs rise"


def test_internal_docs_index_and_search(tmp_path, monkeypatch):
    (tmp_path / "q3.md").write_text("date: 2025-10-01\n## Q3 paid social\n" + "Paid social returned 2.1x on "
                                    "spend for the spring campaign with strongest results from retargeting. " * 3)
    (tmp_path / "notes.txt").write_text("too short")
    monkeypatch.setattr(config, "DOCS_DIR", str(tmp_path))
    assert internal.index(str(tmp_path)) == 1
    evs = run(internal.fetch("paid social campaign retargeting results spend"))
    assert evs and evs[0].url == "internal://q3.md" and evs[0].published_at.year == 2025
