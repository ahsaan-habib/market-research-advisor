import asyncio
import json

from fastapi.testclient import TestClient

from advisor import api, brief, gather as gather_mod
from advisor.evidence import Evidence
from advisor.gather import Gathered, gather
from advisor.planner import Plan, plan


def test_plan_is_cleaned_and_falls_back(llm):
    llm(json.dumps({"kind": "investment", "symbols": ["AAPL.US", "drop table;", "^spx", "a", "b", "c", "d"],
                    "search_queries": ["1", "2", "3", "4"], "news_topics": [], "internal_query": None}))
    p = asyncio.run(plan("should I worry about apple?"))
    assert p.symbols == ["aapl.us", "^spx", "a", "b", "c"] and len(p.search_queries) == 3
    llm("not json")
    p = asyncio.run(plan("q"))
    assert p.kind == "other" and p.search_queries == ["q"] and p.internal_query == "q"


def test_gather_records_failures_and_empties_as_gaps(monkeypatch):
    async def ok(q, client):
        return [Evidence(source_type="web", title="hit", content="c")]

    async def boom(s, client):
        raise RuntimeError("provider down")

    async def stale(topics, client):
        return [Evidence(source_type="news", title="old news", content="c", stale=True, note="9 days old")]

    async def empty(q):
        return []

    monkeypatch.setattr(gather_mod.search, "fetch", ok)
    monkeypatch.setattr(gather_mod.quotes, "fetch", boom)
    monkeypatch.setattr(gather_mod.news, "fetch", stale)
    monkeypatch.setattr(gather_mod.internal, "fetch", empty)
    g = asyncio.run(gather(Plan(kind="other", symbols=["x.us"], search_queries=["q"], news_topics=["t"],
                                internal_query="i")))
    assert {e.title for e in g.evidence} == {"hit", "old news"}
    assert sorted(g.gaps) == ["internal docs: nothing found", "old news: stale data (9 days old)",
                              "prices x.us: unavailable (RuntimeError)"]


def test_brief_frames_and_blocks_advice(llm):
    g = Gathered([Evidence(source_type="web", title="T", content="c", url="https://t")], ["news: unavailable"])
    p = Plan(kind="marketing")
    llm("Summary: email CPMs rose [1].")
    out = asyncio.run(brief.write("q", p, g))
    assert "Summary: email CPMs rose [1]." in out and "Not checked / caveats:\n- news: unavailable" in out
    assert "[1] T — https://t" in out and out.endswith(brief.DISCLOSURE)
    fake = llm("You should buy more ads.", "Option A trades reach for cost [1].")
    assert "Option A" in asyncio.run(brief.write("q", p, g)) and len(fake.calls) == 2
    llm("We recommend X.", "Strong buy.")
    assert "[Analysis withheld" in asyncio.run(brief.write("q", p, g))
    assert "couldn't gather any evidence" in asyncio.run(brief.write("q", p, Gathered()))


def test_api_research(llm, monkeypatch):
    llm(json.dumps({"kind": "other"}))

    async def nothing(p):
        return Gathered(gaps=["web: unavailable"])
    monkeypatch.setattr("advisor.research.gather", nothing)
    r = TestClient(api.app).post("/research", json={"question": "q"}).json()
    assert r["plan"]["kind"] == "other" and r["gaps"] == ["web: unavailable"] and r["evidence"] == []
