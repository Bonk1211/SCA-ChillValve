"""Tests for backend/explainer.py — operator-facing LLM narration.

Runs without a Gemini API key: the explainer's fallback path is deterministic
and asserted directly. If GEMINI_API_KEY is set, the live call is exercised
via test_real_call_returns_nonempty_string (gated on the env var).
"""
from __future__ import annotations

import asyncio
import os

import pytest

from backend.explainer import Explainer


def test_fallback_used_when_no_api_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    e = Explainer()
    assert e._enabled is False
    text = asyncio.run(
        e.explain_leader_change("A", "A1", "A2", "killed", 35.0)
    )
    assert "A1" in text and "A2" in text
    assert "Branch A" in text


def test_fallback_boot_message(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    e = Explainer()
    text = asyncio.run(e.explain_leader_change("B", None, "B1", "boot", 0.0))
    assert "B1" in text
    assert "boot" in text.lower() or "initial" in text.lower()


def test_cache_hits_avoid_duplicate_calls(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    e = Explainer()
    t1 = asyncio.run(e.explain_leader_change("A", "A1", "A2", "killed", 0.0))
    t2 = asyncio.run(e.explain_leader_change("A", "A1", "A2", "killed", 999.0))
    assert t1 == t2
    # Cache has one entry — same key.
    assert len(e.cache) == 1


@pytest.mark.skipif(
    not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")),
    reason="no Gemini API key configured",
)
def test_real_call_returns_nonempty_string():
    e = Explainer()
    assert e._enabled is True
    text = asyncio.run(
        e.explain_leader_change("A", "A1", "A2", "killed", 35.0)
    )
    assert isinstance(text, str)
    assert len(text) > 10
