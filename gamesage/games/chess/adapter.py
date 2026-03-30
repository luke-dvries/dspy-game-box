"""Chess game adapter — bridges the chess engine to the GameSage core."""

from __future__ import annotations

from gamesage.core.adapter import GameAdapter
from gamesage.games.chess.engine import ChessEngine


RULES_SUMMARY = """\
Chess is a two-player strategy game played on an 8x8 board.
Each player starts with 16 pieces: 1 king, 1 queen, 2 rooks, 2 bishops,
2 knights, and 8 pawns.  Players alternate turns.  The goal is to
checkmate the opponent's king (threaten it with no escape).
Special moves: castling (king + rook swap), en passant (pawn capture),
pawn promotion (pawn reaching the 8th rank becomes any piece).
Draws occur by stalemate, insufficient material, threefold repetition,
or the 50-move rule.
"""


class ChessAdapter(GameAdapter):

    def __init__(self) -> None:
        self._engine = ChessEngine()

    # ------------------------------------------------------------------
    # GameAdapter interface
    # ------------------------------------------------------------------

    def get_game_name(self) -> str:
        return "Chess"

    def get_board_state(self) -> dict:
        material = self._engine.get_material_counts()
        castling = self._engine.get_castling_rights()
        return {
            "board": self._engine.to_ascii(),
            "current_player": self._engine.get_current_player(),
            "move_count": self._engine.get_move_count(),
            "game_phase": self._engine.get_game_phase(),
            "extra": {
                "fen": self._engine.get_fen(),
                "in_check": self._engine.is_in_check(),
                "material_white": material["White"],
                "material_black": material["Black"],
                "material_advantage": material["White"] - material["Black"],
                "castling_rights": castling,
                "half_move_clock": self._engine.get_half_move_clock(),
            },
        }

    def get_legal_moves(self) -> list[str]:
        return self._engine.get_legal_moves_san()

    def apply_move(self, move: str) -> bool:
        return self._engine.apply_move_san(move)

    def undo_move(self) -> bool:
        return self._engine.undo_move()

    def is_game_over(self) -> tuple[bool, str]:
        return self._engine.is_game_over()

    def serialize_board(self) -> str:
        state = self.get_board_state()
        extra = state["extra"]
        lines = [
            f"Game: Chess",
            f"Phase: {state['game_phase']}  |  Move: {state['move_count']}  |  Turn: {state['current_player']}",
            f"FEN: {extra['fen']}",
            "",
            state["board"],
            "",
            f"Material — White: {extra['material_white']}  Black: {extra['material_black']}"
            f"  (advantage: {extra['material_advantage']:+d})",
            f"In check: {extra['in_check']}",
            "Castling rights: "
            + ", ".join(k for k, v in extra["castling_rights"].items() if v),
        ]
        return "\n".join(lines)

    def get_game_rules_summary(self) -> str:
        return RULES_SUMMARY

    def get_move_history(self) -> list[str]:
        return self._engine.get_move_history()

    # ------------------------------------------------------------------
    # Extra helpers
    # ------------------------------------------------------------------

    def load_fen(self, fen: str) -> None:
        """Load a position from FEN (e.g. for Analyze mode)."""
        self._engine.load_fen(fen)

    def is_move_legal(self, move: str) -> bool:
        """Check legality without applying the move."""
        return move in self.get_legal_moves()
