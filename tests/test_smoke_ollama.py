"""Planner and brief from a real local model; sources are stubbed so no
network is needed besides Ollama. Opt-in:

    RUN_OLLAMA=1 pytest tests/test_smoke_ollama.py -s
"""
import asyncio
import os

import pytest

from advisor import brief
from advisor.evidence import Evidence
from advisor.gather import Gathered
from advisor.planner import plan

pytestmark = pytest.mark.skipif(os.environ.get("RUN_OLLAMA") != "1", reason="set RUN_OLLAMA=1 to run")


def test_plan_and_brief():
    p = asyncio.run(plan("Should we move budget from paid social to email for our spring campaign?"))
    print("\n", p)
    assert not p.symbols and (p.search_queries or p.internal_query)      # no stock prices for a budget question
    g = Gathered([Evidence(source_type="internal", title="q3.md: Paid social", url="internal://q3.md",
                           content="Paid social returned 2.1x on spend in Q3. Email returned 3.4x on a smaller budget.")])
    out = asyncio.run(brief.write("Should we move budget from paid social to email?", p, g))
    print(out)
    assert out.endswith(brief.DISCLOSURE)
