"""Othello game adapter."""

from __future__ import annotations

from gamesage.core.adapter import GameAdapter
from gamesage.games.othello.engine import OthelloEngine, BLACK, WHITE


RULES_SUMMARY = """\
Othello (Reversi) is played on an 8x8 board.  Black moves first.  Players
alternate placing discs of their color on empty squares.  A move is legal
only if it flanks one or more of the opponent's discs (in any of the 8
directions) between the new disc and another disc of the player's color —
all flanked discs are then flipped to the player's color.  If a player has
no legal move they must pass; if neither player can move the game ends.
The player with more discs at the end wins.
Move notation: column letter (A-H) + row number (1-8, top to bottom), e.g. H7, D3.
"""


class OthelloAdapter(GameAdapter):

    def __init__(self) -> None:
        self._engine = OthelloEngine()

    # ------------------------------------------------------------------
    # GameAdapter interface
    # ------------------------------------------------------------------

    def get_game_name(self) -> str:
        return "Othello"

    def get_board_state(self) -> dict:
        black, white = self._engine.get_counts()
        return {
            "board": [row[:] for row in self._engine.board],
            "current_player": self._engine.current_player_name(),
            "move_count": self._engine.move_count,
            "game_phase": self._engine.get_game_phase(),
            "extra": {
                "black_count": black,
                "white_count": white,
            },
        }

    def get_legal_moves(self) -> list[str]:
        return self._engine.get_legal_moves()

    def apply_move(self, move: str) -> bool:
        return self._engine.apply_move(move)

    def undo_move(self) -> bool:
        return self._engine.undo_move()

    def is_game_over(self) -> tuple[bool, str]:
        return self._engine.is_game_over()

    def serialize_board(self) -> str:
        state = self.get_board_state()
        extra = state["extra"]
        lines = [
            "Game: Othello",
            f"Phase: {state['game_phase']}  |  Move: {state['move_count']}  |  Turn: {state['current_player']}",
            f"Black: {extra['black_count']} discs  |  White: {extra['white_count']} discs",
            "",
            self._engine.to_text(),
            "",
            "Legend: B=Black disc, W=White disc, .=empty",
        ]
        return "\n".join(lines)

    def get_game_rules_summary(self) -> str:
        return RULES_SUMMARY

    def get_move_history(self) -> list[str]:
        return list(self._engine.move_history)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def is_move_legal(self, move: str) -> bool:
        return move in self.get_legal_moves()
