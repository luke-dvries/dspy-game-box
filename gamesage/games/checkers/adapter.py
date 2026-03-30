"""Checkers game adapter."""

from __future__ import annotations

from gamesage.core.adapter import GameAdapter
from gamesage.games.checkers.engine import CheckersEngine, RED, BLACK


RULES_SUMMARY = """\
American Checkers is played on an 8x8 board.  Red moves first (toward lower
row numbers), Black second.  Pieces move diagonally forward.  Captures are
mandatory — you must jump an opponent piece if possible, landing in the empty
square beyond it.  Multi-jump chains are also mandatory.  A piece reaching
the opponent's back rank becomes a King (R/B) and can move in all four
diagonal directions.  The game ends when a player captures all opponent
pieces or leaves the opponent with no legal moves.
Move notation: row,col→row,col (e.g. 5,2→4,3).
"""


class CheckersAdapter(GameAdapter):

    def __init__(self) -> None:
        self._engine = CheckersEngine()
        self._move_history: list[str] = []

    # ------------------------------------------------------------------
    # GameAdapter interface
    # ------------------------------------------------------------------

    def get_game_name(self) -> str:
        return "Checkers"

    def get_board_state(self) -> dict:
        counts = self._engine.get_piece_counts()
        return {
            "board": self._engine.board,
            "current_player": "Red" if self._engine.current_player == RED else "Black",
            "move_count": self._engine.move_count,
            "game_phase": self._get_phase(),
            "extra": {
                "piece_counts": counts,
                "has_captures": any(m.captures for m in self._engine.get_legal_moves()),
            },
        }

    def _get_phase(self) -> str:
        counts = self._engine.get_piece_counts()
        total = sum(counts.values())
        if total >= 20:
            return "opening"
        if total >= 10:
            return "midgame"
        return "endgame"

    def get_legal_moves(self) -> list[str]:
        return self._engine.get_legal_moves_notation()

    def apply_move(self, move: str) -> bool:
        ok = self._engine.apply_move_notation(move)
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
        counts = state["extra"]["piece_counts"]
        has_caps = state["extra"]["has_captures"]
        lines = [
            f"Game: Checkers",
            f"Phase: {state['game_phase']}  |  Move: {state['move_count']}  |  Turn: {state['current_player']}",
            f"Red: {counts['red']} pieces + {counts['red_kings']} kings  |  "
            f"Black: {counts['black']} pieces + {counts['black_kings']} kings",
            f"Captures available: {has_caps}",
            "",
            self._engine.to_text(),
            "",
            "Legend: r=red, R=red king, b=black, B=black king, .=empty",
        ]
        return "\n".join(lines)

    def get_game_rules_summary(self) -> str:
        return RULES_SUMMARY

    def get_move_history(self) -> list[str]:
        return list(self._move_history)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def is_move_legal(self, move: str) -> bool:
        return move in self.get_legal_moves()
