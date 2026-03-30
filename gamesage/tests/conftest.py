"""Shared pytest configuration for GameSage tests."""

import pytest


@pytest.fixture(autouse=True)
def no_llm(monkeypatch):
    """Prevent any test from accidentally calling a real LLM."""
    # We don't configure DSPy in tests — the adapters/engines are tested
    # without touching the LLM pipeline.
    pass
