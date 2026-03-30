"""Chess engine wrapper around python-chess.

All move validation, board management, and state queries go through this
module.  The LLM never calls python-chess directly.
"""

from __future__ import annotations

import chess
import chess.pgn


PIECE_VALUES: dict[chess.PieceType, int] = {
    chess.PAWN: 1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.ROOK: 5,
    chess.QUEEN: 9,
    chess.KING: 0,
}

PHASE_THRESHOLDS = {
    "opening": 10,   # first 10 half-moves
    "midgame": 40,   # half-moves 11-40
}


class ChessEngine:
    """Thin wrapper around a ``chess.Board`` with helper queries."""

    def __init__(self) -> None:
        self.board = chess.Board()
        self._move_stack: list[str] = []  # SAN history

    # ------------------------------------------------------------------
    # State queries
    # ------------------------------------------------------------------

    def get_fen(self) -> str:
        return self.board.fen()

    def get_current_player(self) -> str:
        return "White" if self.board.turn == chess.WHITE else "Black"

    def get_move_count(self) -> int:
        return self.board.fullmove_number

    def get_half_move_clock(self) -> int:
        return self.board.halfmove_clock

    def get_game_phase(self) -> str:
        hm = len(self.board.move_stack)
        if hm <= PHASE_THRESHOLDS["opening"]:
            return "opening"
        if hm <= PHASE_THRESHOLDS["midgame"]:
            return "midgame"
        return "endgame"

    def get_legal_moves_san(self) -> list[str]:
        return sorted(self.board.san(m) for m in self.board.legal_moves)

    def get_material_counts(self) -> dict[str, int]:
        white = sum(
            PIECE_VALUES[p.piece_type]
            for p in self.board.piece_map().values()
            if p.color == chess.WHITE
        )
        black = sum(
            PIECE_VALUES[p.piece_type]
            for p in self.board.piece_map().values()
            if p.color == chess.BLACK
        )
        return {"White": white, "Black": black}

    def is_in_check(self) -> bool:
        return self.board.is_check()

    def get_castling_rights(self) -> dict[str, bool]:
        return {
            "White kingside": self.board.has_kingside_castling_rights(chess.WHITE),
            "White queenside": self.board.has_queenside_castling_rights(chess.WHITE),
            "Black kingside": self.board.has_kingside_castling_rights(chess.BLACK),
            "Black queenside": self.board.has_queenside_castling_rights(chess.BLACK),
        }

    def get_move_history(self) -> list[str]:
        return list(self._move_stack)

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def apply_move_san(self, san: str) -> bool:
        """Apply a move given in SAN.  Returns True on success."""
        try:
            move = self.board.parse_san(san)
        except (chess.InvalidMoveError, chess.IllegalMoveError, chess.AmbiguousMoveError, ValueError):
            return False
        if move not in self.board.legal_moves:
            return False
        self._move_stack.append(san)
        self.board.push(move)
        return True

    def undo_move(self) -> bool:
        if not self.board.move_stack:
            return False
        self.board.pop()
        if self._move_stack:
            self._move_stack.pop()
        return True

    # ------------------------------------------------------------------
    # Terminal conditions
    # ------------------------------------------------------------------

    def is_game_over(self) -> tuple[bool, str]:
        if not self.board.is_game_over():
            return False, ""
        outcome = self.board.outcome()
        if outcome is None:
            return True, "Game over (unknown reason)"
        termination = outcome.termination.name.replace("_", " ").title()
        if outcome.winner is None:
            return True, f"Draw by {termination}"
        winner = "White" if outcome.winner == chess.WHITE else "Black"
        return True, f"{winner} wins by {termination}"

    # ------------------------------------------------------------------
    # Board rendering (ASCII)
    # ------------------------------------------------------------------

    def to_ascii(self) -> str:
        """Return a labeled ASCII board (files a-h, ranks 8-1)."""
        lines = ["  a b c d e f g h"]
        for rank in range(7, -1, -1):
            row = [str(rank + 1)]
            for file in range(8):
                sq = chess.square(file, rank)
                piece = self.board.piece_at(sq)
                if piece is None:
                    row.append(".")
                else:
                    row.append(piece.symbol())
            lines.append(" ".join(row))
        lines.append("  a b c d e f g h")
        return "\n".join(lines)

    def load_fen(self, fen: str) -> None:
        self.board = chess.Board(fen)
        self._move_stack = []
