"""Abstract base class every game adapter must implement."""

from abc import ABC, abstractmethod


class GameAdapter(ABC):
    """Contract that every game adapter must fulfil.

    The adapter is the single source of truth for game state.  The LLM pipeline
    (core/explainer.py) calls only these methods — it never inspects internal
    engine state directly.
    """

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    @abstractmethod
    def get_game_name(self) -> str:
        """Return the human-readable game name, e.g. 'Chess'."""

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    @abstractmethod
    def get_board_state(self) -> dict:
        """Return a structured snapshot of the current game state.

        Required keys
        -------------
        board         : 2-D list or structured dict representing the board
        current_player: str — whose turn it is
        move_count    : int — total moves played so far
        game_phase    : str — e.g. 'opening', 'midgame', 'endgame'
        extra         : dict — game-specific metadata (material, captures, etc.)
        """

    @abstractmethod
    def get_legal_moves(self) -> list[str]:
        """Return every legal move in human-readable notation.

        Examples: ['e4', 'Nf3'] for chess; ['3,5,7'] for sudoku.
        """

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    @abstractmethod
    def apply_move(self, move: str) -> bool:
        """Apply *move* to the board.

        Returns
        -------
        True  if the move was valid and applied.
        False if the move was illegal (board state unchanged).
        """

    @abstractmethod
    def undo_move(self) -> bool:
        """Undo the last move.

        Returns
        -------
        True  if there was a move to undo.
        False if the game is at its initial state.
        """

    # ------------------------------------------------------------------
    # Terminal conditions
    # ------------------------------------------------------------------

    @abstractmethod
    def is_game_over(self) -> tuple[bool, str]:
        """Check whether the game has ended.

        Returns
        -------
        (True,  result_description) — e.g. ('White wins by checkmate')
        (False, '')                 — game is still in progress
        """

    # ------------------------------------------------------------------
    # Serialisation (consumed by the LLM)
    # ------------------------------------------------------------------

    @abstractmethod
    def serialize_board(self) -> str:
        """Return a plain-text, LLM-readable representation of the board."""

    @abstractmethod
    def get_game_rules_summary(self) -> str:
        """Return a short rules blurb injected into every LLM prompt."""

    # ------------------------------------------------------------------
    # Move history (optional helper — adapters may track this internally)
    # ------------------------------------------------------------------

    def get_move_history(self) -> list[str]:
        """Return the list of moves played so far (most-recent last).

        The default implementation returns an empty list.  Override if
        your engine tracks move history.
        """
        return []
