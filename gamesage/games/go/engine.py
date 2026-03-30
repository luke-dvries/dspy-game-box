"""Go engine — basic rules for NxN boards (default 9x9).

Rules implemented
-----------------
* Stone placement on empty intersections
* Capture detection (remove stones with zero liberties after placement)
* Ko rule (simple positional ko: disallow recreating the immediately prior board state)
* Pass (notation: "pass")
* Two consecutive passes end the game
* Territory estimation via flood-fill (simplified: empty regions surrounded by one color)

Move notation: column letter + row number, e.g. "D5", "A1", "J9" (using
the Go convention that the letter I is skipped).

References: sgfmill is used for SGF I/O only; the engine itself is pure Python.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Optional

import numpy as np

EMPTY = 0
BLACK = 1
WHITE = 2

_COL_LETTERS = "ABCDEFGHJKLMNOPQRST"  # I is skipped


def col_letter_to_idx(letter: str) -> int:
    return _COL_LETTERS.index(letter.upper())


def idx_to_col_letter(idx: int) -> str:
    return _COL_LETTERS[idx]


def move_to_coords(move: str, size: int) -> Optional[tuple[int, int]]:
    """Parse "D5" → (row, col) where row 0 is the top."""
    if move.lower() == "pass":
        return None
    col = col_letter_to_idx(move[0])
    row = size - int(move[1:])
    return row, col


def coords_to_move(row: int, col: int, size: int) -> str:
    return f"{idx_to_col_letter(col)}{size - row}"


class GoEngine:
    """Minimal Go engine with capture and ko detection."""

    def __init__(self, size: int = 9, komi: float = 6.5) -> None:
        self.size = size
        self.komi = komi
        self.board: np.ndarray = np.zeros((size, size), dtype=int)
        self.current_player: int = BLACK
        self.captures: dict[int, int] = {BLACK: 0, WHITE: 0}
        self._prev_board: Optional[np.ndarray] = None  # for ko detection
        self._history: list[tuple[np.ndarray, int, dict, Optional[np.ndarray]]] = []
        self.move_history: list[str] = []
        self._consecutive_passes: int = 0

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def current_player_name(self) -> str:
        return "Black" if self.current_player == BLACK else "White"

    def _get_group_and_liberties(
        self, row: int, col: int, board: np.ndarray
    ) -> tuple[set[tuple[int, int]], set[tuple[int, int]]]:
        color = board[row, col]
        group: set[tuple[int, int]] = set()
        liberties: set[tuple[int, int]] = set()
        stack = [(row, col)]
        while stack:
            r, c = stack.pop()
            if (r, c) in group:
                continue
            group.add((r, c))
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nr, nc = r + dr, c + dc
                if 0 <= nr < self.size and 0 <= nc < self.size:
                    if board[nr, nc] == EMPTY:
                        liberties.add((nr, nc))
                    elif board[nr, nc] == color and (nr, nc) not in group:
                        stack.append((nr, nc))
        return group, liberties

    def _remove_captured(
        self, board: np.ndarray, enemy: int
    ) -> int:
        """Remove all enemy groups with zero liberties.  Returns capture count."""
        captured = 0
        visited: set[tuple[int, int]] = set()
        for r in range(self.size):
            for c in range(self.size):
                if board[r, c] == enemy and (r, c) not in visited:
                    group, liberties = self._get_group_and_liberties(r, c, board)
                    visited |= group
                    if not liberties:
                        for gr, gc in group:
                            board[gr, gc] = EMPTY
                        captured += len(group)
        return captured

    def get_legal_moves(self) -> list[str]:
        """Return list of legal move strings (including 'pass')."""
        legal = ["pass"]
        enemy = WHITE if self.current_player == BLACK else BLACK
        for r in range(self.size):
            for c in range(self.size):
                if self.board[r, c] != EMPTY:
                    continue
                # Try placing
                tmp = self.board.copy()
                tmp[r, c] = self.current_player
                self._remove_captured(tmp, enemy)
                # Check suicide
                _, libs = self._get_group_and_liberties(r, c, tmp)
                if not libs:
                    continue
                # Ko check
                if self._prev_board is not None and np.array_equal(tmp, self._prev_board):
                    continue
                legal.append(coords_to_move(r, c, self.size))
        return legal

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def apply_move(self, move: str) -> bool:
        """Apply a move.  Returns True if legal."""
        if move.lower() == "pass":
            self._history.append(
                (self.board.copy(), self.current_player, dict(self.captures), self._prev_board)
            )
            self.move_history.append(move)
            self._consecutive_passes += 1
            self.current_player = WHITE if self.current_player == BLACK else BLACK
            return True

        coords = move_to_coords(move, self.size)
        if coords is None:
            return False
        r, c = coords
        if not (0 <= r < self.size and 0 <= c < self.size):
            return False
        if self.board[r, c] != EMPTY:
            return False

        enemy = WHITE if self.current_player == BLACK else BLACK
        tmp = self.board.copy()
        tmp[r, c] = self.current_player
        captured = self._remove_captured(tmp, enemy)

        # Suicide check
        _, libs = self._get_group_and_liberties(r, c, tmp)
        if not libs:
            return False

        # Ko check
        if self._prev_board is not None and np.array_equal(tmp, self._prev_board):
            return False

        # Commit
        self._history.append(
            (self.board.copy(), self.current_player, dict(self.captures), self._prev_board)
        )
        self._prev_board = self.board.copy()
        self.board = tmp
        self.captures[self.current_player] += captured
        self.current_player = WHITE if self.current_player == BLACK else BLACK
        self.move_history.append(move)
        self._consecutive_passes = 0
        return True

    def undo_move(self) -> bool:
        if not self._history:
            return False
        self.board, self.current_player, self.captures, self._prev_board = self._history.pop()
        if self.move_history:
            self.move_history.pop()
        self._consecutive_passes = 0
        return True

    # ------------------------------------------------------------------
    # Terminal conditions
    # ------------------------------------------------------------------

    def is_game_over(self) -> tuple[bool, str]:
        if self._consecutive_passes >= 2:
            b_score, w_score = self.estimate_score()
            w_score += self.komi
            if b_score > w_score:
                return True, f"Black wins (B: {b_score:.1f} vs W: {w_score:.1f})"
            elif w_score > b_score:
                return True, f"White wins (W: {w_score:.1f} vs B: {b_score:.1f})"
            else:
                return True, "Draw (equal score with komi)"
        return False, ""

    # ------------------------------------------------------------------
    # Territory estimation (simplified flood-fill)
    # ------------------------------------------------------------------

    def estimate_score(self) -> tuple[int, int]:
        """Return (black_score, white_score) including territory + captures."""
        black_territory = 0
        white_territory = 0
        visited: set[tuple[int, int]] = set()

        for r in range(self.size):
            for c in range(self.size):
                if self.board[r, c] == EMPTY and (r, c) not in visited:
                    region, border_colors = self._flood_empty(r, c)
                    visited |= region
                    if border_colors == {BLACK}:
                        black_territory += len(region)
                    elif border_colors == {WHITE}:
                        white_territory += len(region)

        black_stones = int(np.sum(self.board == BLACK))
        white_stones = int(np.sum(self.board == WHITE))
        return (
            black_territory + black_stones + self.captures[BLACK],
            white_territory + white_stones + self.captures[WHITE],
        )

    def _flood_empty(
        self, r: int, c: int
    ) -> tuple[set[tuple[int, int]], set[int]]:
        region: set[tuple[int, int]] = set()
        border: set[int] = set()
        stack = [(r, c)]
        while stack:
            cr, cc = stack.pop()
            if (cr, cc) in region:
                continue
            region.add((cr, cc))
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nr, nc = cr + dr, cc + dc
                if 0 <= nr < self.size and 0 <= nc < self.size:
                    if self.board[nr, nc] == EMPTY:
                        stack.append((nr, nc))
                    else:
                        border.add(int(self.board[nr, nc]))
        return region, border

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_text(self) -> str:
        symbols = {EMPTY: ".", BLACK: "B", WHITE: "W"}
        header = "   " + " ".join(
            idx_to_col_letter(c) for c in range(self.size)
        )
        lines = [header]
        for r in range(self.size):
            row_label = str(self.size - r).rjust(2)
            row_str = " ".join(symbols[int(self.board[r, c])] for c in range(self.size))
            lines.append(f"{row_label} {row_str}")
        return "\n".join(lines)

    def get_move_count(self) -> int:
        return len(self.move_history)

    def get_game_phase(self) -> str:
        moves = self.get_move_count()
        total = self.size * self.size
        if moves < total * 0.2:
            return "opening"
        if moves < total * 0.6:
            return "midgame"
        return "endgame"
