"""Daily prices from Stooq's CSV download endpoint. Symbols use Stooq's own
format (e.g. `aapl.us`, `^spx`); check the symbol on stooq.com first.
Swap ADVISOR_QUOTES_URL / this module for your own market data provider.

Returns a compact summary rather than raw rows: the model needs the last
close, the recent change and the date of the last bar, not 250 lines of CSV.
"""
from __future__ import annotations

import csv
import io
from datetime import datetime, timezone

import httpx

from .. import config
from ..evidence import Evidence


def _pct(a: float, b: float) -> str:
    return f"{(a / b - 1) * 100:+.1f}%" if b else "n/a"


async def fetch(symbol: str, client: httpx.AsyncClient) -> Evidence | list:
    r = await client.get(config.QUOTES_URL, params={"s": symbol.lower(), "i": "d"})
    r.raise_for_status()
    rows = [row for row in csv.DictReader(io.StringIO(r.text)) if row.get("Close")]
    if not rows:
        # unknown symbol or provider returned nothing: a gap for the brief, not evidence to cite
        return []
    rows = rows[-70:]
    last = rows[-1]
    close = float(last["Close"])
    closes = [float(x["Close"]) for x in rows]
    when = datetime.strptime(last["Date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    content = (f"{symbol.upper()} last close {close:g} on {last['Date']}. "
               f"1d {_pct(close, closes[-2]) if len(closes) > 1 else 'n/a'}, "
               f"5d {_pct(close, closes[-6]) if len(closes) > 5 else 'n/a'}, "
               f"1m {_pct(close, closes[-22]) if len(closes) > 21 else 'n/a'}, "
               f"3m {_pct(close, closes[0])}. "
               f"Range over the period {min(closes):g}–{max(closes):g}.")
    ev = Evidence(source_type="market_data", title=f"{symbol.upper()} daily prices (Stooq)",
                  content=content, url=str(r.url), published_at=when)
    age = ev.age_hours()
    if age is not None and age > config.MAX_QUOTE_AGE_H:
        ev.stale, ev.note = True, f"last bar is {age / 24:.0f} days old"
    return ev
