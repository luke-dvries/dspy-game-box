"""Go game adapter."""

from __future__ import annotations

from gamesage.core.adapter import GameAdapter
from gamesage.games.go.engine import GoEngine, BLACK, WHITE
from gamesage import config


RULES_SUMMARY = """\
Go is an abstract strategy board game.  Black plays first.  Players
alternate placing stones on intersections.  A group of stones with no
liberties (adjacent empty points) is captured and removed.  The ko rule
prevents immediately recreating the prior board position.  Players may
pass; two consecutive passes end the game.  Territory (empty intersections
surrounded by one color) and captures determine the winner.  White receives
komi (6.5 points) to compensate for Black's first-move advantage.
Move notation: column letter (A-T, skip I) + row number, e.g. D5, A1.
"""


class GoAdapter(GameAdapter):

    def __init__(self, board_size: int | None = None) -> None:
        size = board_size or config.DEFAULT_BOARD_SIZE_GO
        self._engine = GoEngine(size=size)

    # ------------------------------------------------------------------
    # GameAdapter interface
    # ------------------------------------------------------------------

    def get_game_name(self) -> str:
        return f"Go ({self._engine.size}x{self._engine.size})"

    def get_board_state(self) -> dict:
        b_score, w_score = self._engine.estimate_score()
        return {
            "board": self._engine.board.tolist(),
            "current_player": self._engine.current_player_name(),
            "move_count": self._engine.get_move_count(),
            "game_phase": self._engine.get_game_phase(),
            "extra": {
                "captures_black": self._engine.captures[BLACK],
                "captures_white": self._engine.captures[WHITE],
                "estimated_score_black": b_score,
                "estimated_score_white": w_score + self._engine.komi,
                "komi": self._engine.komi,
                "board_size": self._engine.size,
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
            f"Game: {self.get_game_name()}",
            f"Phase: {state['game_phase']}  |  Move: {state['move_count']}  |  Turn: {state['current_player']}",
            f"Captures — Black: {extra['captures_black']}  White: {extra['captures_white']}",
            f"Estimated score — Black: {extra['estimated_score_black']}  "
            f"White: {extra['estimated_score_white']:.1f} (includes komi {extra['komi']})",
            "",
            self._engine.to_text(),
            "",
            "Legend: B=Black stone, W=White stone, .=empty intersection",
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
