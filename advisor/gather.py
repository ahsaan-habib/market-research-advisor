"""Fan out to every source the plan asked for, in parallel, each with its own
timeout. A source that fails is recorded as a gap — the brief has to say what
it couldn't check, not quietly answer without it."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

import httpx

from .evidence import Evidence
from .planner import Plan
from .sources import internal, news, quotes, search

TIMEOUT_S = 15.0


@dataclass
class Gathered:
    evidence: list[Evidence] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)


async def _guard(label: str, coro, out: Gathered) -> None:
    try:
        res = await asyncio.wait_for(coro, TIMEOUT_S)
    except Exception as e:  # timeout, http error, provider down
        out.gaps.append(f"{label}: unavailable ({type(e).__name__})")
        return
    items = res if isinstance(res, list) else [res]
    if not items:
        out.gaps.append(f"{label}: nothing found")
    out.evidence.extend(items)


async def gather(plan: Plan) -> Gathered:
    out = Gathered()
    async with httpx.AsyncClient(timeout=TIMEOUT_S, follow_redirects=True,
                                 headers={"User-Agent": "market-research-advisor/0.1"}) as client:
        jobs = [_guard(f"prices {s}", quotes.fetch(s, client), out) for s in plan.symbols]
        jobs += [_guard(f"web search '{q}'", search.fetch(q, client), out) for q in plan.search_queries]
        if plan.news_topics:
            jobs.append(_guard("news", news.fetch(plan.news_topics, client), out))
        if plan.internal_query:
            jobs.append(_guard("internal docs", internal.fetch(plan.internal_query), out))
        await asyncio.gather(*jobs)
    for ev in out.evidence:
        if ev.stale:
            out.gaps.append(f"{ev.title}: stale data ({ev.note})")
    return out
