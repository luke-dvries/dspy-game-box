"""Othello (Reversi) engine — standard 8x8 rules.

Move notation: column letter (A-H) + row number (1-8, top to bottom).
Example: "H7" = column H, row 7.
"""

from __future__ import annotations

EMPTY = 0
BLACK = 1
WHITE = 2

_COL_LETTERS = "ABCDEFGH"
_DIRECTIONS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def move_to_coords(move: str) -> tuple[int, int] | None:
    """Parse "H7" -> (row=6, col=7). Returns None on invalid input."""
    if len(move) < 2:
        return None
    col_str = move[0].upper()
    if col_str not in _COL_LETTERS:
        return None
    col = _COL_LETTERS.index(col_str)
    try:
        row = int(move[1:]) - 1
    except ValueError:
        return None
    if not (0 <= row < 8 and 0 <= col < 8):
        return None
    return row, col


def coords_to_move(row: int, col: int) -> str:
    return f"{_COL_LETTERS[col]}{row + 1}"


class OthelloEngine:
    """Standard Othello/Reversi engine."""

    def __init__(self) -> None:
        self.board: list[list[int]] = [[EMPTY] * 8 for _ in range(8)]
        self.current_player: int = BLACK
        self._history: list[tuple[list[list[int]], int]] = []
        self.move_history: list[str] = []
        self.move_count: int = 0
        self._init_board()

    def _init_board(self) -> None:
        self.board[3][3] = WHITE
        self.board[3][4] = BLACK
        self.board[4][3] = BLACK
        self.board[4][4] = WHITE

    def load_position(self, board_str: str, player_to_move: str) -> None:
        """Load board from raw data string like '...BB.../....BB.../...' (rows sep by /).

        '.' = empty, 'B' = Black, 'W' = White.
        player_to_move: 'Black' or 'White' (case-insensitive).
        """
        self.board = [[EMPTY] * 8 for _ in range(8)]
        rows = board_str.split("/")
        for r, row in enumerate(rows[:8]):
            for c, ch in enumerate(row[:8]):
                if ch == "B":
                    self.board[r][c] = BLACK
                elif ch == "W":
                    self.board[r][c] = WHITE
        self.current_player = BLACK if player_to_move.lower() == "black" else WHITE
        self.move_history = []
        self.move_count = 0
        self._history = []

    # ------------------------------------------------------------------
    # Move generation
    # ------------------------------------------------------------------

    def _get_flips(self, row: int, col: int, player: int) -> list[tuple[int, int]]:
        """Return squares that would be flipped by placing player at (row, col)."""
        if self.board[row][col] != EMPTY:
            return []
        opponent = WHITE if player == BLACK else BLACK
        flips: list[tuple[int, int]] = []
        for dr, dc in _DIRECTIONS:
            line: list[tuple[int, int]] = []
            r, c = row + dr, col + dc
            while 0 <= r < 8 and 0 <= c < 8 and self.board[r][c] == opponent:
                line.append((r, c))
                r += dr
                c += dc
            if line and 0 <= r < 8 and 0 <= c < 8 and self.board[r][c] == player:
                flips.extend(line)
        return flips

    def get_legal_moves(self) -> list[str]:
        moves = []
        for r in range(8):
            for c in range(8):
                if self._get_flips(r, c, self.current_player):
                    moves.append(coords_to_move(r, c))
        return moves

    def has_legal_moves(self, player: int) -> bool:
        for r in range(8):
            for c in range(8):
                if self._get_flips(r, c, player):
                    return True
        return False

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def apply_move(self, move: str) -> bool:
        coords = move_to_coords(move)
        if coords is None:
            return False
        r, c = coords
        flips = self._get_flips(r, c, self.current_player)
        if not flips:
            return False

        # Save state for undo
        self._history.append(([row[:] for row in self.board], self.current_player))

        # Place piece and flip
        self.board[r][c] = self.current_player
        for fr, fc in flips:
            self.board[fr][fc] = self.current_player
        self.move_history.append(move)
        self.move_count += 1

        # Switch players; if opponent has no moves, current player goes again
        opponent = WHITE if self.current_player == BLACK else BLACK
        if self.has_legal_moves(opponent):
            self.current_player = opponent
        # else current player keeps turn (or game is over)
        return True

    def undo_move(self) -> bool:
        if not self._history:
            return False
        self.board, self.current_player = self._history.pop()
        if self.move_history:
            self.move_history.pop()
        self.move_count = max(0, self.move_count - 1)
        return True

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_counts(self) -> tuple[int, int]:
        """Return (black_count, white_count)."""
        black = sum(self.board[r][c] == BLACK for r in range(8) for c in range(8))
        white = sum(self.board[r][c] == WHITE for r in range(8) for c in range(8))
        return black, white

    def current_player_name(self) -> str:
        return "Black" if self.current_player == BLACK else "White"

    def get_game_phase(self) -> str:
        black, white = self.get_counts()
        total = black + white
        if total <= 20:
            return "opening"
        if total <= 50:
            return "midgame"
        return "endgame"

    def is_game_over(self) -> tuple[bool, str]:
        if self.has_legal_moves(BLACK) or self.has_legal_moves(WHITE):
            return False, ""
        black, white = self.get_counts()
        if black > white:
            return True, f"Black wins ({black}-{white})"
        elif white > black:
            return True, f"White wins ({white}-{black})"
        else:
            return True, f"Draw ({black}-{white})"

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def to_text(self) -> str:
        symbols = {EMPTY: ".", BLACK: "B", WHITE: "W"}
        header = "   " + " ".join(_COL_LETTERS)
        lines = [header]
        for r in range(8):
            row_str = " ".join(symbols[self.board[r][c]] for c in range(8))
            lines.append(f"{r + 1:2} {row_str}")
        return "\n".join(lines)
