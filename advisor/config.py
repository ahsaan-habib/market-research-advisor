import os


def env(name: str, default: str) -> str:
    return os.environ.get(f"ADVISOR_{name}", default)


OLLAMA_URL = env("OLLAMA_URL", "http://localhost:11434")
MODEL = env("MODEL", "qwen3:4b-instruct")
SEARXNG_URL = env("SEARXNG_URL", "http://localhost:8888")
QUOTES_URL = env("QUOTES_URL", "https://stooq.com/q/d/l/")
FEEDS_FILE = env("FEEDS_FILE", "feeds.yaml")
DOCS_DIR = env("DOCS_DIR", "internal_docs")
INDEX_DIR = env("INDEX_DIR", ".chroma")
EMBED_MODEL = env("EMBED_MODEL", "BAAI/bge-small-en-v1.5")
# market data older than this (in hours, counting weekends) is flagged stale
MAX_QUOTE_AGE_H = float(env("MAX_QUOTE_AGE_H", "96"))
MAX_NEWS_AGE_H = float(env("MAX_NEWS_AGE_H", "168"))
