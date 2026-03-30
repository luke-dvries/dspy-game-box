"""Checkers engine — implemented from scratch (no external library).

Rules implemented
-----------------
* Standard 8×8 American checkers
* Red moves first (towards lower row indices), Black second
* Mandatory captures (including multi-jump chains)
* Kings (created when reaching the opposite back rank)
* Move notation: "from_row,from_col→to_row,to_col"
  For multi-jumps: "r,c→r,c→r,c→..."
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import NamedTuple


EMPTY = "."
RED   = "r"   # red regular piece
BLACK = "b"   # black regular piece
RED_K = "R"   # red king
BLK_K = "B"   # black king


class Move(NamedTuple):
    path: list[tuple[int, int]]   # sequence of squares visited (start + landings)
    captures: list[tuple[int, int]]  # squares of captured pieces

    def to_notation(self) -> str:
        return "→".join(f"{r},{c}" for r, c in self.path)

    @staticmethod
    def from_notation(s: str) -> "Move":
        """Parse notation back to a Move (captures list is empty — for lookup only)."""
        parts = [tuple(int(x) for x in seg.split(",")) for seg in s.split("→")]
        return Move(path=parts, captures=[])  # type: ignore[arg-type]


@dataclass
class CheckersEngine:
    board: list[list[str]] = field(default_factory=list)
    current_player: str = RED      # RED or BLACK
    _history: list[tuple[list[list[str]], str]] = field(default_factory=list)
    move_count: int = 0

    def __post_init__(self) -> None:
        if not self.board:
            self.board = self._initial_board()

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    @staticmethod
    def _initial_board() -> list[list[str]]:
        b = [[EMPTY] * 8 for _ in range(8)]
        for row in range(8):
            for col in range(8):
                if (row + col) % 2 == 1:
                    if row < 3:
                        b[row][col] = BLACK
                    elif row > 4:
                        b[row][col] = RED
        return b

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_player_pieces(self, player: str) -> list[tuple[int, int]]:
        own = {RED, RED_K} if player == RED else {BLACK, BLK_K}
        return [
            (r, c)
            for r in range(8) for c in range(8)
            if self.board[r][c] in own
        ]

    def _is_king(self, row: int, col: int) -> bool:
        return self.board[row][col] in (RED_K, BLK_K)

    def _directions(self, row: int, col: int) -> list[tuple[int, int]]:
        piece = self.board[row][col]
        if piece == RED:
            return [(-1, -1), (-1, 1)]   # red moves toward row 0
        if piece == BLACK:
            return [(1, -1), (1, 1)]     # black moves toward row 7
        return [(-1, -1), (-1, 1), (1, -1), (1, 1)]  # kings move all dirs

    def _enemy(self, player: str) -> set[str]:
        return {BLACK, BLK_K} if player == RED else {RED, RED_K}

    def _get_captures_from(
        self,
        row: int, col: int,
        board: list[list[str]],
        player: str,
        path: list[tuple[int, int]],
        captured: list[tuple[int, int]],
    ) -> list[Move]:
        """Recursively find all capture chains from (row, col)."""
        piece = board[row][col]
        enemy = self._enemy(player)
        results: list[Move] = []

        for dr, dc in self._directions(row, col):
            mid_r, mid_c = row + dr, col + dc
            land_r, land_c = row + 2 * dr, col + 2 * dc
            if not (0 <= mid_r < 8 and 0 <= land_r < 8 and 0 <= mid_c < 8 and 0 <= land_c < 8):
                continue
            if board[mid_r][mid_c] not in enemy:
                continue
            if board[land_r][land_c] != EMPTY:
                continue
            if (mid_r, mid_c) in captured:
                continue  # already captured in this chain

            # Make the jump on a temporary board
            tmp = deepcopy(board)
            tmp[land_r][land_c] = piece
            tmp[row][col] = EMPTY
            tmp[mid_r][mid_c] = EMPTY
            # King promotion mid-jump (American rules: promote only at end)
            new_path = path + [(land_r, land_c)]
            new_captured = captured + [(mid_r, mid_c)]

            # Recurse
            sub_moves = self._get_captures_from(
                land_r, land_c, tmp, player, new_path, new_captured
            )
            if sub_moves:
                results.extend(sub_moves)
            else:
                results.append(Move(path=new_path, captures=new_captured))

        return results

    def get_legal_moves(self) -> list[Move]:
        """Return all legal moves.  Captures are mandatory and maximal."""
        pieces = self.get_player_pieces(self.current_player)
        captures: list[Move] = []
        for r, c in pieces:
            caps = self._get_captures_from(r, c, self.board, self.current_player, [(r, c)], [])
            captures.extend(caps)

        if captures:
            # Must capture; must take maximum captures (American rules)
            max_caps = max(len(m.captures) for m in captures)
            return [m for m in captures if len(m.captures) == max_caps]

        # No captures — simple moves
        simple: list[Move] = []
        enemy = self._enemy(self.current_player)
        for r, c in pieces:
            for dr, dc in self._directions(r, c):
                nr, nc = r + dr, c + dc
                if 0 <= nr < 8 and 0 <= nc < 8 and self.board[nr][nc] == EMPTY:
                    simple.append(Move(path=[(r, c), (nr, nc)], captures=[]))
        return simple

    def get_legal_moves_notation(self) -> list[str]:
        return [m.to_notation() for m in self.get_legal_moves()]

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def apply_move_notation(self, notation: str) -> bool:
        legal = self.get_legal_moves()
        legal_notations = {m.to_notation(): m for m in legal}
        if notation not in legal_notations:
            return False
        self._apply_move(legal_notations[notation])
        return True

    def _apply_move(self, move: Move) -> None:
        self._history.append((deepcopy(self.board), self.current_player))
        start_r, start_c = move.path[0]
        end_r, end_c = move.path[-1]
        piece = self.board[start_r][start_c]
        self.board[start_r][start_c] = EMPTY
        for cr, cc in move.captures:
            self.board[cr][cc] = EMPTY
        # King promotion
        if piece == RED and end_r == 0:
            piece = RED_K
        elif piece == BLACK and end_r == 7:
            piece = BLK_K
        self.board[end_r][end_c] = piece
        self.current_player = BLACK if self.current_player == RED else RED
        self.move_count += 1

    def undo_move(self) -> bool:
        if not self._history:
            return False
        self.board, self.current_player = self._history.pop()
        self.move_count -= 1
        return True

    # ------------------------------------------------------------------
    # Terminal conditions
    # ------------------------------------------------------------------

    def is_game_over(self) -> tuple[bool, str]:
        if not self.get_legal_moves():
            winner = BLACK if self.current_player == RED else RED
            name = "Black" if winner == BLACK else "Red"
            return True, f"{name} wins (opponent has no moves)"
        red_count = sum(1 for r in range(8) for c in range(8) if self.board[r][c] in {RED, RED_K})
        blk_count = sum(1 for r in range(8) for c in range(8) if self.board[r][c] in {BLACK, BLK_K})
        if red_count == 0:
            return True, "Black wins (all red pieces captured)"
        if blk_count == 0:
            return True, "Red wins (all black pieces captured)"
        return False, ""

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_text(self) -> str:
        lines = ["   0 1 2 3 4 5 6 7"]
        for r, row in enumerate(self.board):
            lines.append(f"{r}  " + " ".join(row))
        return "\n".join(lines)

    def get_piece_counts(self) -> dict[str, int]:
        red_reg = sum(1 for r in range(8) for c in range(8) if self.board[r][c] == RED)
        red_kin = sum(1 for r in range(8) for c in range(8) if self.board[r][c] == RED_K)
        blk_reg = sum(1 for r in range(8) for c in range(8) if self.board[r][c] == BLACK)
        blk_kin = sum(1 for r in range(8) for c in range(8) if self.board[r][c] == BLK_K)
        return {"red": red_reg, "red_kings": red_kin, "black": blk_reg, "black_kings": blk_kin}
