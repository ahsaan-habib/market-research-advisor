from __future__ import annotations

from dataclasses import dataclass

from .brief import write
from .gather import Gathered, gather
from .planner import Plan, plan


@dataclass
class Research:
    question: str
    plan: Plan
    gathered: Gathered
    brief: str


async def research(question: str) -> Research:
    p = await plan(question)
    g = await gather(p)
    return Research(question, p, g, await write(question, p, g))
