from __future__ import annotations

import httpx

from . import config


async def chat(messages: list[dict], fmt: str | dict | None = None, timeout: float = 180) -> str:
    body = {"model": config.MODEL, "messages": messages, "stream": False, "think": False,
            "options": {"temperature": 0.0}}
    if fmt is not None:
        body["format"] = fmt
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(f"{config.OLLAMA_URL}/api/chat", json=body)
        r.raise_for_status()
        return r.json()["message"]["content"]
