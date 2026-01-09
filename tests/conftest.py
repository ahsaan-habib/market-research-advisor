"""Offline by default: fake embedder, temp index, every HTTP source served by
httpx.MockTransport, scripted model. test_smoke_ollama.py is opt-in."""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
os.environ.setdefault("ADVISOR_INDEX_DIR", os.path.join(tempfile.mkdtemp(prefix="advisor-test-"), "chroma"))

import fake_st  # noqa: E402

fake_st.install()

import pytest  # noqa: E402


class ScriptedLLM:
    def __init__(self, *replies):
        self.replies, self.calls = list(replies), []

    async def __call__(self, messages, fmt=None, timeout=180):
        self.calls.append({"messages": messages, "fmt": fmt})
        return self.replies.pop(0)


@pytest.fixture
def llm(monkeypatch):
    def install(*replies):
        fake = ScriptedLLM(*replies)
        monkeypatch.setattr("advisor.llm.chat", fake)
        return fake
    return install
