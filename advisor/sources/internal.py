"""RAG over your own documents — the context public sources don't have
(what your last campaigns returned, who your customers are)."""
from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

from .. import config
from ..evidence import Evidence

QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


@lru_cache(maxsize=1)
def _embed() -> SentenceTransformer:
    return SentenceTransformer(config.EMBED_MODEL)


@lru_cache(maxsize=1)
def _col():
    return chromadb.PersistentClient(path=config.INDEX_DIR).get_or_create_collection(
        "internal", metadata={"hnsw:space": "cosine"})


def index(root: str = config.DOCS_DIR) -> int:
    ids, docs, metas = [], [], []
    for path in sorted(Path(root).glob("*.*")):
        if path.name.lower() == "readme.md" or path.suffix not in (".md", ".txt"):
            continue
        raw = path.read_text(encoding="utf-8", errors="ignore")
        m = re.match(r"date:\s*(\d{4}-\d{2}-\d{2})\s*\n", raw)
        date = m.group(1) if m else datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).strftime("%Y-%m-%d")
        for i, part in enumerate(re.split(r"^## ", raw, flags=re.M)):
            part = part.strip()
            if len(part.split()) < 15:
                continue
            title = part.splitlines()[0][:80]
            ids.append(f"{path.stem}-{i}")
            docs.append(part[:2500])
            metas.append({"file": path.name, "title": title, "date": date})
    if ids:
        _col().upsert(ids=ids, documents=docs, metadatas=metas,
                      embeddings=_embed().encode(docs, normalize_embeddings=True).tolist())
    return len(ids)


def _search(query: str, k: int) -> list[Evidence]:
    if not _col().count():
        return []
    vec = _embed().encode(QUERY_PREFIX + query, normalize_embeddings=True).tolist()
    res = _col().query(query_embeddings=[vec], n_results=min(k, _col().count()))
    out = []
    for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
        if 1 - dist < 0.5:
            continue
        when = datetime.strptime(meta["date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        out.append(Evidence(source_type="internal", title=f"{meta['file']}: {meta['title']}",
                            content=doc[:800], url=f"internal://{meta['file']}", published_at=when))
    return out


async def fetch(query: str, k: int = 4) -> list[Evidence]:
    return await asyncio.to_thread(_search, query, k)
