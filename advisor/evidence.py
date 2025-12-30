"""Every piece of gathered data is Evidence: what it says, where it came from,
when it was published and when we fetched it. A market summary built on
week-old prices is dangerous, so the timestamps are part of the data, not
decoration."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

SourceType = Literal["market_data", "web", "news", "internal"]


def now() -> datetime:
    return datetime.now(timezone.utc)


class Evidence(BaseModel):
    source_type: SourceType
    title: str
    content: str
    url: str = ""
    published_at: datetime | None = None    # when the source says it's from
    fetched_at: datetime = Field(default_factory=now)
    stale: bool = False
    note: str = ""

    def age_hours(self) -> float | None:
        if self.published_at is None:
            return None
        return (now() - self.published_at).total_seconds() / 3600

    def stamp(self) -> str:
        pub = self.published_at.strftime("%Y-%m-%d %H:%M UTC") if self.published_at else "date unknown"
        return f"{pub}{' — STALE' if self.stale else ''}"
