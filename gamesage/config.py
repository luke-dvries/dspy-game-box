"""GameSage configuration — LLM backend, model selection, and global settings.

Override any setting via environment variables:
  GAMESAGE_LLM_BACKEND, GAMESAGE_OLLAMA_MODEL, GAMESAGE_OLLAMA_BASE_URL,
  GAMESAGE_OPENAI_MODEL, GAMESAGE_ANTHROPIC_MODEL, GAMESAGE_GEMINI_MODEL,
  GAMESAGE_SKILL_LEVEL, GAMESAGE_GO_BOARD_SIZE, GAMESAGE_RESEARCH_LOGGING,
  GAMESAGE_DB_PATH
"""

import os
import dspy

# ---------------------------------------------------------------------------
# Backend selection
# ---------------------------------------------------------------------------

LLM_BACKEND: str = os.environ.get("GAMESAGE_LLM_BACKEND", "ollama")  # ollama | openai | anthropic | gemini

OLLAMA_MODEL: str = os.environ.get("GAMESAGE_OLLAMA_MODEL", "llama3.1")
OLLAMA_BASE_URL: str = os.environ.get("GAMESAGE_OLLAMA_BASE_URL", "http://localhost:11434")

OPENAI_MODEL: str = os.environ.get("GAMESAGE_OPENAI_MODEL", "gpt-4o")
ANTHROPIC_MODEL: str = os.environ.get("GAMESAGE_ANTHROPIC_MODEL", "claude-sonnet-4-6")
GEMINI_MODEL: str = os.environ.get("GAMESAGE_GEMINI_MODEL", "gemini/gemini-2.0-flash")

# ---------------------------------------------------------------------------
# Gameplay defaults
# ---------------------------------------------------------------------------

DEFAULT_SKILL_LEVEL: str = os.environ.get("GAMESAGE_SKILL_LEVEL", "beginner")
DEFAULT_BOARD_SIZE_GO: int = int(os.environ.get("GAMESAGE_GO_BOARD_SIZE", "9"))

# ---------------------------------------------------------------------------
# Research logging
# ---------------------------------------------------------------------------

RESEARCH_LOGGING_ENABLED: bool = os.environ.get("GAMESAGE_RESEARCH_LOGGING", "true").lower() == "true"
DB_PATH: str = os.environ.get("GAMESAGE_DB_PATH", "gamesage_research.db")

# ---------------------------------------------------------------------------
# LLM retry settings
# ---------------------------------------------------------------------------

LLM_MAX_RETRIES: int = 3


# ---------------------------------------------------------------------------
# DSPy configuration
# ---------------------------------------------------------------------------

def configure_dspy(dry_run: bool = False) -> None:
    """Configure DSPy with the selected backend.

    Parameters
    ----------
    dry_run:
        When True a lightweight stub LM is used so the full pipeline can
        be exercised without any real API calls.
    """
    if dry_run:
        lm = _make_dry_run_lm()
    elif LLM_BACKEND == "ollama":
        lm = dspy.LM(
            model=f"ollama/{OLLAMA_MODEL}",
            api_base=OLLAMA_BASE_URL,
            api_key="ollama",          # Ollama ignores the key
        )
    elif LLM_BACKEND == "openai":
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError("OPENAI_API_KEY environment variable is not set.")
        lm = dspy.LM(model=f"openai/{OPENAI_MODEL}", api_key=api_key)
    elif LLM_BACKEND == "anthropic":
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError("ANTHROPIC_API_KEY environment variable is not set.")
        lm = dspy.LM(model=f"anthropic/{ANTHROPIC_MODEL}", api_key=api_key)
    elif LLM_BACKEND == "gemini":
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise EnvironmentError("GEMINI_API_KEY environment variable is not set.")
        lm = dspy.LM(model=GEMINI_MODEL, api_key=api_key, num_retries=8)
    else:
        raise ValueError(
            f"Unknown LLM_BACKEND: {LLM_BACKEND!r}. "
            "Choose ollama, openai, anthropic, or gemini."
        )

    dspy.configure(lm=lm)


# ---------------------------------------------------------------------------
# Dry-run stub
# ---------------------------------------------------------------------------

class _DryRunLM(dspy.LM):
    """Minimal stub that returns canned responses without any network call."""

    def __init__(self) -> None:
        # We call the parent __init__ with a dummy model string.  DSPy uses
        # this only for display purposes when a real backend isn't configured.
        super().__init__(model="dry-run/stub", api_key="dry-run")

    def __call__(self, prompt=None, messages=None, **kwargs):  # noqa: D401
        """Return a deterministic JSON stub completion (DSPy 3.x JSONAdapter format)."""
        import json
        stub = json.dumps({
            "reasoning":          "Dry-run stub — no LLM call was made.",
            "strategic_reasoning": "Dry-run stub — no LLM call was made.",
            "recommended_move":   "e4",
            "explanation":        "Dry-run mode — no LLM call was made.",
            "alternative_moves":  "d4, Nf3",
            "key_concepts":       "dry-run, testing",
            "position_summary":   "Dry-run position.",
            "advantages":         "none",
            "threats":            "none",
            "suggested_focus":    "testing",
            "what_it_sets_up":    "nothing",
            "what_it_prevents":   "nothing",
        })
        return [{"text": stub, "finish_reason": "stop"}]


def _make_dry_run_lm() -> _DryRunLM:
    return _DryRunLM()
