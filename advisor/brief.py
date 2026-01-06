"""Synthesis. The model writes the analysis; the code writes the frame:
'data as of', what couldn't be checked, and the risk disclosure. The human
owns the decision, so the brief lays out options and trade-offs and never
tells anyone to buy, sell or spend."""
from __future__ import annotations

import re

from . import llm
from .evidence import now
from .gather import Gathered
from .planner import Plan

DISCLOSURE = ("Informational only — not financial, investment or professional advice. Figures come from "
              "the listed sources at the times shown and may be delayed, incomplete or wrong. Verify before "
              "acting; the decision and its risk are yours.")

SYSTEM = """You write a short research brief from numbered evidence.

Rules:
- Use ONLY the evidence. Cite it like [3] after every fact or figure.
- When you use a price or market figure, say the date it is from.
- If evidence is marked STALE, say so where you use it.
- Structure: Summary (2-3 sentences) · What the evidence shows · Options and
  trade-offs (2-4 options, each with what would make it right or wrong) ·
  What's missing or uncertain.
- Never instruct the reader to buy, sell, hold, invest, or spend. Present
  options; the reader decides.
- No price targets or predictions."""

_ADVICE = re.compile(r"\b(you should|we recommend|i recommend|(strong )?(buy|sell)\b(?! side)|"
                     r"go long|go short|price target|will (rise|fall|reach))", re.I)


def _evidence_block(g: Gathered) -> str:
    return "\n\n".join(f"[{i}] ({ev.source_type}, {ev.stamp()}) {ev.title}\n{ev.content}"
                       for i, ev in enumerate(g.evidence, 1))


async def write(question: str, plan: Plan, g: Gathered) -> str:
    if not g.evidence:
        body = "I couldn't gather any evidence for this question, so there's nothing to analyse."
    else:
        user = f"Question: {question}\n\nEvidence:\n{_evidence_block(g)}"
        body = await llm.chat([{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}])
        if _ADVICE.search(body):
            body = await llm.chat([{"role": "system", "content": SYSTEM}, {"role": "user", "content": user
                                   + "\n\nYour previous draft gave a direct recommendation or prediction. "
                                     "Rewrite it as options and trade-offs only."}])
        if _ADVICE.search(body):
            body = "[Analysis withheld: the draft kept giving direct recommendations.]"

    sources = "\n".join(f"[{i}] {ev.title} — {ev.url or 'n/a'} — {ev.stamp()}, fetched "
                        f"{ev.fetched_at:%Y-%m-%d %H:%M UTC}" for i, ev in enumerate(g.evidence, 1))
    parts = [f"Research brief · generated {now():%Y-%m-%d %H:%M UTC}", body.strip()]
    if g.gaps:
        parts.append("Not checked / caveats:\n" + "\n".join(f"- {x}" for x in g.gaps))
    if sources:
        parts.append("Sources:\n" + sources)
    parts.append(DISCLOSURE)
    return "\n\n".join(parts)
