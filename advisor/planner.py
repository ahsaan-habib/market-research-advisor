"""The planner is what makes this agentic rather than a fixed pipeline: it
decides which sources *this* question needs. A channel-strategy question
needs internal performance data and search, not stock prices; a portfolio
question needs prices and news."""
from __future__ import annotations

import json
import re
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from . import llm


class Plan(BaseModel):
    kind: Literal["marketing", "investment", "market_summary", "other"]
    symbols: list[str] = Field(default_factory=list, description="market data symbols, e.g. aapl.us")
    search_queries: list[str] = Field(default_factory=list)
    news_topics: list[str] = Field(default_factory=list)
    internal_query: str | None = Field(None, description="what to look up in our own documents, or null")


SYSTEM = """You plan research for a question. Do not answer it.
Choose only the sources this question needs:
- symbols: price data, only for questions about specific listed securities or indices
  (Stooq format, e.g. aapl.us, msft.us, ^spx). Max 5.
- search_queries: up to 3 web searches for current facts.
- news_topics: up to 3 topics to look for in recent news.
- internal_query: what to search in the company's own documents (past campaigns,
  channel performance, customer research), or null if irrelevant.
Reply as JSON."""

_SYMBOL = re.compile(r"^\^?[a-z0-9.\-]{1,15}$")


async def plan(question: str) -> Plan:
    raw = await llm.chat([{"role": "system", "content": SYSTEM}, {"role": "user", "content": question}],
                         fmt=Plan.model_json_schema())
    try:
        p = Plan.model_validate_json(raw)
    except (ValidationError, json.JSONDecodeError):
        # a broken plan shouldn't mean no research: fall back to a plain search
        return Plan(kind="other", search_queries=[question[:200]], internal_query=question[:200])
    p.symbols = [s.lower() for s in p.symbols if _SYMBOL.match(s.lower())][:5]
    p.search_queries, p.news_topics = p.search_queries[:3], p.news_topics[:3]
    return p
