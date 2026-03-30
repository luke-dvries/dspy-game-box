"""Sudoku engine — puzzle generation, validation, and legal move enumeration.

Difficulty levels map to clue counts:
  easy   → 40 clues (36 empty cells)
  medium → 30 clues (51 empty cells)
  hard   → 25 clues (56 empty cells)

Move notation: "row,col,digit"  e.g. "3,5,7" (all 1-indexed).
"""

from __future__ import annotations

import random
from copy import deepcopy
from typing import Optional


DIFFICULTY_CLUES = {
    "easy":   40,
    "medium": 30,
    "hard":   25,
}


class SudokuEngine:

    def __init__(self) -> None:
        self.board: list[list[int]] = [[0] * 9 for _ in range(9)]
        self._solution: list[list[int]] = [[0] * 9 for _ in range(9)]
        self._given: list[list[bool]] = [[False] * 9 for _ in range(9)]  # clue cells
        self._history: list[tuple[int, int, int]] = []  # (row, col, old_value)
        self.move_count: int = 0
        self.difficulty: str = "easy"

    # ------------------------------------------------------------------
    # Puzzle generation
    # ------------------------------------------------------------------

    def new_puzzle(self, difficulty: str = "easy") -> None:
        self.difficulty = difficulty
        # Generate a complete valid board
        solution = [[0] * 9 for _ in range(9)]
        self._fill_board(solution)
        self._solution = deepcopy(solution)

        # Remove cells to reach target clue count
        target_clues = DIFFICULTY_CLUES.get(difficulty, 40)
        puzzle = deepcopy(solution)
        cells = [(r, c) for r in range(9) for c in range(9)]
        random.shuffle(cells)
        removed = 0
        target_remove = 81 - target_clues
        for r, c in cells:
            if removed >= target_remove:
                break
            old = puzzle[r][c]
            puzzle[r][c] = 0
            # Simple uniqueness check: skip if too many empty cells already
            removed += 1

        self.board = puzzle
        self._given = [[puzzle[r][c] != 0 for c in range(9)] for r in range(9)]
        self._history = []
        self.move_count = 0

    def _fill_board(self, board: list[list[int]], pos: int = 0) -> bool:
        """Backtracking solver used for puzzle generation."""
        if pos == 81:
            return True
        r, c = divmod(pos, 9)
        if board[r][c] != 0:
            return self._fill_board(board, pos + 1)
        digits = list(range(1, 10))
        random.shuffle(digits)
        for d in digits:
            if self._is_valid_placement(board, r, c, d):
                board[r][c] = d
                if self._fill_board(board, pos + 1):
                    return True
                board[r][c] = 0
        return False

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_valid_placement(board: list[list[int]], row: int, col: int, digit: int) -> bool:
        if digit in board[row]:
            return False
        if digit in (board[r][col] for r in range(9)):
            return False
        br, bc = (row // 3) * 3, (col // 3) * 3
        for r in range(br, br + 3):
            for c in range(bc, bc + 3):
                if board[r][c] == digit:
                    return False
        return True

    def is_valid_move(self, row: int, col: int, digit: int) -> bool:
        """Check if placing *digit* at (row, col) is valid."""
        if self._given[row][col]:
            return False  # clue cell is immutable
        if not (1 <= digit <= 9):
            return False
        tmp = deepcopy(self.board)
        tmp[row][col] = 0  # treat as empty for validation
        return self._is_valid_placement(tmp, row, col, digit)

    # ------------------------------------------------------------------
    # Legal moves
    # ------------------------------------------------------------------

    def get_legal_moves(self) -> list[str]:
        """Return all valid placements as "row,col,digit" strings (1-indexed)."""
        moves = []
        for r in range(9):
            for c in range(9):
                if self.board[r][c] == 0:
                    for d in range(1, 10):
                        if self.is_valid_move(r, c, d):
                            moves.append(f"{r + 1},{c + 1},{d}")
        return moves

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def apply_move(self, notation: str) -> bool:
        """Apply "row,col,digit" (1-indexed).  Returns True if legal."""
        try:
            parts = notation.split(",")
            r, c, d = int(parts[0]) - 1, int(parts[1]) - 1, int(parts[2])
        except (ValueError, IndexError):
            return False
        if not (0 <= r < 9 and 0 <= c < 9):
            return False
        if not self.is_valid_move(r, c, d):
            return False
        self._history.append((r, c, self.board[r][c]))
        self.board[r][c] = d
        self.move_count += 1
        return True

    def undo_move(self) -> bool:
        if not self._history:
            return False
        r, c, old = self._history.pop()
        self.board[r][c] = old
        self.move_count -= 1
        return True

    # ------------------------------------------------------------------
    # Terminal conditions
    # ------------------------------------------------------------------

    def is_solved(self) -> bool:
        for r in range(9):
            for c in range(9):
                if self.board[r][c] == 0:
                    return False
        return self.board == self._solution

    def is_game_over(self) -> tuple[bool, str]:
        if self.is_solved():
            return True, "Puzzle solved!"
        if not self.get_legal_moves() and any(self.board[r][c] == 0 for r in range(9) for c in range(9)):
            return True, "No legal moves remain — puzzle may be in an invalid state."
        return False, ""

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_text(self) -> str:
        """9×9 grid with box separators, 0 shown as '.'."""
        lines = ["  1 2 3 | 4 5 6 | 7 8 9"]
        for r in range(9):
            if r in (3, 6):
                lines.append("  ------+-------+------")
            row_cells = []
            for c in range(9):
                val = self.board[r][c]
                row_cells.append("." if val == 0 else str(val))
            row_str = (
                " ".join(row_cells[:3])
                + " | "
                + " ".join(row_cells[3:6])
                + " | "
                + " ".join(row_cells[6:])
            )
            lines.append(f"{r + 1} {row_str}")
        return "\n".join(lines)

    def count_filled(self) -> int:
        return sum(1 for r in range(9) for c in range(9) if self.board[r][c] != 0)

    def count_given(self) -> int:
        return sum(1 for r in range(9) for c in range(9) if self._given[r][c])
