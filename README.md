# market-research-advisor

Blueprint 4 from *Designing AI Automation for Your Business*: a question that
needs current data from several places — a marketing channel strategy, a
market or portfolio summary — answered as a sourced, timestamped brief.

> Informational only, not financial or investment advice. The system gathers
> and lays out options; the decision stays with the person.

```
question ─▶ PLANNER (local model): which sources does *this* question need?
              │
              ├─▶ prices    Stooq daily CSV            ┐
              ├─▶ web       self-hosted SearXNG         │ in parallel,
              ├─▶ news      your RSS feeds (feeds.yaml) │ each with a timeout
              └─▶ internal  RAG over internal_docs/     ┘
              │
          evidence, every item with published + fetched timestamps;
          stale prices and failed sources become named gaps
              │
          BRIEF: cited analysis as options & trade-offs (no buy/sell, no targets)
                 + as-of time + "not checked" list + sources + disclosure (in code)
```

## Why it's agentic and not a pipeline

The planner decides the fan-out per question. A channel-mix question pulls
internal campaign data and search, not stock prices; a sector question pulls
prices and news. Each source is a plain async function; adding one is adding
a branch in `gather.py`.

## Guardrails

- **Timestamped data.** Every evidence item carries when it's from and when
  it was fetched. Prices whose last bar is older than
  `ADVISOR_MAX_QUOTE_AGE_H` (default 96 h, weekends included) are marked
  STALE and listed as a caveat; news older than a week is dropped.
- **Say what wasn't checked.** A source that times out or errors is reported
  in the brief, never silently skipped.
- **Options, not instructions.** The brief is checked for direct
  recommendations and predictions; one rewrite, otherwise the analysis is
  withheld and only the evidence is shown.
- **The disclosure is code, not prompt.**

## Run it

```bash
ollama pull qwen3:4b-instruct   # not plain qwen3:4b: that tag is now a thinking-only build
docker compose up -d searxng          # web search on :8888
python -m venv .venv && .venv/bin/pip install -e . && source .venv/bin/activate
$EDITOR feeds.yaml                    # feeds you trust
cp your-reports/*.md internal_docs/ && advisor index
advisor ask "Should we shift budget from paid social to search for our B2B product?" --show-plan
advisor ask "Summarise how ^spx and msft.us have moved this quarter and what's in the news"
```

Swap `advisor/sources/quotes.py` for your own market data provider if you
have one; Stooq is used because it needs no key.
