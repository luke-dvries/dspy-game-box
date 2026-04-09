"""Evaluation metrics for GameSage DSPy optimization.

Primary metric: move_match
    Returns 1.0 if the model's recommended_move matches the gold_move,
    0.0 otherwise.  Normalization strips check (+) and mate (#) suffixes
    and surrounding whitespace so "Nf3+" == "Nf3".

Secondary metric: move_in_legal
    Returns 1.0 if the model's recommended_move appears anywhere in the
    legal_moves input field.  Weaker but useful as a sanity check that
    the model is not hallucinating illegal moves.
"""

from __future__ import annotations

import re


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize(move: str) -> str:
    """Strip check/mate suffixes and whitespace; lowercase file/rank only."""
    return move.strip().rstrip("+#").strip()


def _extract_move(prediction) -> str:
    """Safely pull recommended_move from a DSPy Prediction or dict."""
    if hasattr(prediction, "recommended_move"):
        return prediction.recommended_move or ""
    if isinstance(prediction, dict):
        return prediction.get("recommended_move", "")
    return str(prediction)


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def move_match(example, prediction, trace=None) -> float:
    """1.0 if predicted move == gold move (normalized), else 0.0.

    This is the primary optimization target.  For Lichess chess puzzles
    and SGF-sourced Go positions, there is exactly one correct answer.
    """
    gold = _normalize(example.gold_move)
    pred = _normalize(_extract_move(prediction))
    return 1.0 if pred == gold else 0.0


def move_in_legal(example, prediction, trace=None) -> float:
    """1.0 if predicted move appears in the legal_moves list, else 0.0.

    Useful for detecting hallucinated illegal moves independently of
    whether the move is the objectively best one.
    """
    pred  = _normalize(_extract_move(prediction))
    legal = {_normalize(m) for m in re.split(r",\s*", example.legal_moves)}
    return 1.0 if pred in legal else 0.0


def combined(example, prediction, trace=None) -> float:
    """Weighted combination: 0.8 * move_match + 0.2 * move_in_legal.

    Rewards the exact correct move but gives partial credit for any
    legal move (better than a completely hallucinated move).
    """
    return 0.8 * move_match(example, prediction, trace) + \
           0.2 * move_in_legal(example, prediction, trace)
