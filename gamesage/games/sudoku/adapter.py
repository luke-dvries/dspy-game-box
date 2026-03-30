"""Sudoku game adapter."""

from __future__ import annotations

from gamesage.core.adapter import GameAdapter
from gamesage.games.sudoku.engine import SudokuEngine


RULES_SUMMARY = """\
Sudoku is a logic puzzle on a 9x9 grid divided into nine 3x3 boxes.
Fill every empty cell with a digit 1-9 such that each row, each column,
and each 3x3 box contains every digit exactly once.  Clue cells (given at
the start) cannot be changed.  There is always exactly one solution.
Move notation: "row,col,digit" (1-indexed), e.g. "3,5,7" places 7 in row 3
column 5.  The AI suggests one cell at a time using elimination logic.
"""


class SudokuAdapter(GameAdapter):

    def __init__(self, difficulty: str = "easy") -> None:
        self._engine = SudokuEngine()
        self._engine.new_puzzle(difficulty)
        self._move_history: list[str] = []

    # ------------------------------------------------------------------
    # GameAdapter interface
    # ------------------------------------------------------------------

    def get_game_name(self) -> str:
        return f"Sudoku ({self._engine.difficulty})"

    def get_board_state(self) -> dict:
        filled = self._engine.count_filled()
        given = self._engine.count_given()
        return {
            "board": [row[:] for row in self._engine.board],
            "current_player": "Solver",
            "move_count": self._engine.move_count,
            "game_phase": self._get_phase(filled),
            "extra": {
                "difficulty": self._engine.difficulty,
                "cells_filled": filled,
                "cells_given": given,
                "cells_remaining": 81 - filled,
            },
        }

    def _get_phase(self, filled: int) -> str:
        if filled < 40:
            return "early"
        if filled < 65:
            return "midgame"
        return "endgame"

    def get_legal_moves(self) -> list[str]:
        return self._engine.get_legal_moves()

    def apply_move(self, move: str) -> bool:
        ok = self._engine.apply_move(move)
        if ok:
            self._move_history.append(move)
        return ok

    def undo_move(self) -> bool:
        ok = self._engine.undo_move()
        if ok and self._move_history:
            self._move_history.pop()
        return ok

    def is_game_over(self) -> tuple[bool, str]:
        return self._engine.is_game_over()

    def serialize_board(self) -> str:
        state = self.get_board_state()
        extra = state["extra"]
        lines = [
            f"Game: {self.get_game_name()}",
            f"Progress: {extra['cells_filled']}/81 filled  |  "
            f"{extra['cells_remaining']} cells remaining  |  Move: {state['move_count']}",
            "",
            self._engine.to_text(),
            "",
            "Note: '.' = empty cell, digits = filled cells (clues are fixed).",
        ]
        return "\n".join(lines)

    def get_game_rules_summary(self) -> str:
        return RULES_SUMMARY

    def get_move_history(self) -> list[str]:
        return list(self._move_history)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def new_puzzle(self, difficulty: str = "easy") -> None:
        self._engine.new_puzzle(difficulty)
        self._move_history = []

    def is_move_legal(self, move: str) -> bool:
        return move in self.get_legal_moves()
