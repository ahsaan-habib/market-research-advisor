"""uvicorn advisor.api:app --port 8050"""
from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from .research import research

app = FastAPI(title="market-research-advisor")


class Ask(BaseModel):
    question: str


@app.post("/research")
async def post_research(body: Ask) -> dict:
    r = await research(body.question)
    return {"brief": r.brief, "plan": r.plan.model_dump(),
            "evidence": [e.model_dump(mode="json") for e in r.gathered.evidence], "gaps": r.gathered.gaps}
