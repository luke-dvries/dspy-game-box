"""DSPy signatures and modules for GameSage.

Pipeline hierarchy
------------------
GameSageAdvisor  — ChainOfThought on MoveAdvisor
                   Recommends the best next move with full reasoning.

GameSageCoach    — Wraps PositionEvaluator + MoveExplainer
                   Provides post-move coaching commentary.
"""

from __future__ import annotations

import random
import logging

import dspy

from gamesage.config import LLM_MAX_RETRIES
from gamesage.core.serializer import format_move_history

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Signatures
# ---------------------------------------------------------------------------

class MoveAdvisor(dspy.Signature):
    """Analyze a board game state and recommend the best move with a full explanation."""

    game_name: str = dspy.InputField(desc="Name of the game being played")
    rules_summary: str = dspy.InputField(desc="Short rules blurb for context")
    board_state: str = dspy.InputField(desc="Board serialized as structured text")
    legal_moves: str = dspy.InputField(desc="Comma-separated list of legal moves")
    move_history: str = dspy.InputField(desc="Recent move history for context")
    player_skill_level: str = dspy.InputField(desc="beginner, intermediate, or advanced")

    strategic_reasoning: str = dspy.OutputField(desc="Internal step-by-step strategic analysis")
    recommended_move: str = dspy.OutputField(desc="The single best move in the game's standard notation")
    explanation: str = dspy.OutputField(desc="Plain English explanation tailored to the player's skill level")
    alternative_moves: str = dspy.OutputField(desc="2-3 alternative moves with brief tradeoff notes")
    key_concepts: str = dspy.OutputField(desc="1-3 strategic concepts this position demonstrates, e.g. 'center control', 'forced capture'")


class PositionEvaluator(dspy.Signature):
    """Evaluate a board position and describe what is happening strategically."""

    game_name: str = dspy.InputField(desc="Name of the game being played")
    board_state: str = dspy.InputField(desc="Board serialized as structured text")
    current_player: str = dspy.InputField(desc="Which player is to move")

    position_summary: str = dspy.OutputField(desc="Overall assessment of the position")
    advantages: str = dspy.OutputField(desc="What advantages does the current player have?")
    threats: str = dspy.OutputField(desc="What threats or dangers exist?")
    suggested_focus: str = dspy.OutputField(desc="What area or goal should the player focus on?")


class MoveExplainer(dspy.Signature):
    """Explain why a specific move was played after the fact."""

    game_name: str = dspy.InputField(desc="Name of the game being played")
    board_before: str = dspy.InputField(desc="Board state before the move")
    move_played: str = dspy.InputField(desc="The move that was played")
    board_after: str = dspy.InputField(desc="Board state after the move")
    player_skill_level: str = dspy.InputField(desc="beginner, intermediate, or advanced")

    explanation: str = dspy.OutputField(desc="Why this move was good, bad, or interesting")
    what_it_sets_up: str = dspy.OutputField(desc="What future possibilities does this move create?")
    what_it_prevents: str = dspy.OutputField(desc="What did this move block or neutralize?")


# ---------------------------------------------------------------------------
# Modules
# ---------------------------------------------------------------------------

class GameSageAdvisor(dspy.Module):
    """Recommend the next move using chain-of-thought reasoning.

    If the model returns an illegal move it is retried up to
    ``config.LLM_MAX_RETRIES`` times with negative feedback appended,
    then falls back to a random legal move.

    If a compiled module exists at ``gamesage_data/compiled/<game>_*_advisor.json``
    it can be loaded via ``GameSageAdvisor.from_compiled(path)`` to use
    optimized few-shot demonstrations.
    """

    def __init__(self) -> None:
        super().__init__()
        self.cot = dspy.ChainOfThought(MoveAdvisor)

    @classmethod
    def from_compiled(cls, path: str) -> "GameSageAdvisor":
        """Load a compiled (optimized) advisor from a saved JSON file."""
        instance = cls()
        instance.load(path)
        logger.info("Loaded compiled GameSageAdvisor from %s", path)
        return instance

    def forward(
        self,
        game_name: str,
        rules_summary: str,
        board_state: str,
        legal_moves: list[str],
        move_history: list[str],
        player_skill_level: str,
        validate_move_fn=None,
    ) -> dspy.Prediction:
        """Run the advisor pipeline.

        Parameters
        ----------
        validate_move_fn:
            Optional callable ``(move: str) -> bool`` provided by the game
            adapter to validate the model's suggestion without mutating state.
            When not provided, no legality check is performed.
        """
        legal_moves_str = ", ".join(legal_moves)
        history_str = format_move_history(move_history)
        illegal_feedback: list[str] = []

        for attempt in range(LLM_MAX_RETRIES + 1):
            extra = ""
            if illegal_feedback:
                extra = (
                    "\n\nNOTE: The following moves are ILLEGAL and must NOT be played: "
                    + ", ".join(illegal_feedback)
                    + ". Choose a different move from the legal moves list."
                )

            prediction = self.cot(
                game_name=game_name,
                rules_summary=rules_summary,
                board_state=board_state + extra,
                legal_moves=legal_moves_str,
                move_history=history_str,
                player_skill_level=player_skill_level,
            )

            move = prediction.recommended_move.strip()

            # Legality check
            if validate_move_fn is None or validate_move_fn(move):
                return prediction

            logger.warning(
                "Advisor returned illegal move %r on attempt %d/%d",
                move, attempt + 1, LLM_MAX_RETRIES,
            )
            illegal_feedback.append(move)

        # Fallback: random legal move
        fallback = random.choice(legal_moves) if legal_moves else ""
        logger.warning("Falling back to random legal move: %r", fallback)
        return dspy.Prediction(
            strategic_reasoning="(LLM repeatedly returned illegal moves; using random fallback)",
            recommended_move=fallback,
            explanation="I had trouble finding a legal move — here is a random legal option.",
            alternative_moves="",
            key_concepts="",
        )


class GameSageCoach(dspy.Module):
    """Post-move coaching that combines position evaluation and move explanation."""

    def __init__(self) -> None:
        super().__init__()
        self.evaluator = dspy.Predict(PositionEvaluator)
        self.explainer = dspy.Predict(MoveExplainer)

    def evaluate_position(
        self,
        game_name: str,
        board_state: str,
        current_player: str,
    ) -> dspy.Prediction:
        """Evaluate the current position."""
        return self.evaluator(
            game_name=game_name,
            board_state=board_state,
            current_player=current_player,
        )

    def explain_move(
        self,
        game_name: str,
        board_before: str,
        move_played: str,
        board_after: str,
        player_skill_level: str,
    ) -> dspy.Prediction:
        """Explain a move that was just played."""
        return self.explainer(
            game_name=game_name,
            board_before=board_before,
            move_played=move_played,
            board_after=board_after,
            player_skill_level=player_skill_level,
        )

    def forward(
        self,
        game_name: str,
        board_before: str,
        move_played: str,
        board_after: str,
        current_player: str,
        player_skill_level: str,
    ) -> dspy.Prediction:
        """Run both evaluator and explainer and merge results."""
        eval_result = self.evaluate_position(game_name, board_after, current_player)
        explain_result = self.explain_move(
            game_name, board_before, move_played, board_after, player_skill_level
        )
        return dspy.Prediction(
            position_summary=eval_result.position_summary,
            advantages=eval_result.advantages,
            threats=eval_result.threats,
            suggested_focus=eval_result.suggested_focus,
            explanation=explain_result.explanation,
            what_it_sets_up=explain_result.what_it_sets_up,
            what_it_prevents=explain_result.what_it_prevents,
        )
