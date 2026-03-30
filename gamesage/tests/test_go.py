"""Unit tests for the Go adapter (no LLM required)."""

import pytest
import numpy as np

from gamesage.games.go.engine import GoEngine, BLACK, WHITE, EMPTY, move_to_coords, coords_to_move
from gamesage.games.go.adapter import GoAdapter


class TestGoEngine:

    def test_initial_board_is_empty(self):
        engine = GoEngine(size=9)
        assert np.all(engine.board == EMPTY)

    def test_initial_player_is_black(self):
        engine = GoEngine(size=9)
        assert engine.current_player == BLACK

    def test_legal_moves_at_start(self):
        engine = GoEngine(size=9)
        moves = engine.get_legal_moves()
        # 81 intersections + 1 pass
        assert len(moves) == 82
        assert "pass" in moves

    def test_apply_valid_move(self):
        engine = GoEngine(size=9)
        ok = engine.apply_move("A9")
        assert ok is True
        assert engine.board[0, 0] == BLACK

    def test_apply_pass(self):
        engine = GoEngine(size=9)
        ok = engine.apply_move("pass")
        assert ok is True
        assert engine.current_player == WHITE

    def test_apply_illegal_move_occupied(self):
        engine = GoEngine(size=9)
        engine.apply_move("A9")
        ok = engine.apply_move("A9")
        assert ok is False

    def test_player_alternates(self):
        engine = GoEngine(size=9)
        assert engine.current_player == BLACK
        engine.apply_move("A9")
        assert engine.current_player == WHITE
        engine.apply_move("B9")
        assert engine.current_player == BLACK

    def test_undo_move(self):
        engine = GoEngine(size=9)
        engine.apply_move("A9")
        ok = engine.undo_move()
        assert ok is True
        assert engine.board[0, 0] == EMPTY
        assert engine.current_player == BLACK

    def test_undo_at_start(self):
        engine = GoEngine(size=9)
        assert engine.undo_move() is False

    def test_capture(self):
        """Surround a single stone and verify it is captured."""
        engine = GoEngine(size=9)
        # Black plays A9 (top-left corner)
        engine.apply_move("A9")   # Black at (0,0)
        # White surrounds: B9
        engine.apply_move("B9")   # White at (0,1)
        # Black plays elsewhere
        engine.apply_move("C9")
        # White plays A8 — now A9 has no liberties
        engine.apply_move("A8")   # White at (1,0)
        assert engine.board[0, 0] == EMPTY  # Black stone captured
        assert engine.captures[WHITE] == 1

    def test_two_passes_end_game(self):
        engine = GoEngine(size=9)
        engine.apply_move("pass")
        engine.apply_move("pass")
        over, result = engine.is_game_over()
        assert over is True
        assert "wins" in result or "Draw" in result

    def test_game_not_over_at_start(self):
        engine = GoEngine(size=9)
        over, _ = engine.is_game_over()
        assert over is False

    def test_serialization(self):
        engine = GoEngine(size=9)
        text = engine.to_text()
        assert "A" in text   # column labels
        assert "9" in text   # row label
        assert "." in text   # empty cells

    def test_move_notation_roundtrip(self):
        for r in range(9):
            for c in range(9):
                move = coords_to_move(r, c, 9)
                r2, c2 = move_to_coords(move, 9)
                assert (r, c) == (r2, c2)


class TestGoAdapter:

    def test_get_game_name(self):
        adapter = GoAdapter(board_size=9)
        assert "Go" in adapter.get_game_name()
        assert "9x9" in adapter.get_game_name()

    def test_board_state_keys(self):
        adapter = GoAdapter(board_size=9)
        state = adapter.get_board_state()
        assert "board" in state
        assert "current_player" in state
        assert "extra" in state

    def test_serialize_board(self):
        adapter = GoAdapter(board_size=9)
        serialized = adapter.serialize_board()
        assert "Go" in serialized
        assert "Black" in serialized

    def test_legal_moves_include_pass(self):
        adapter = GoAdapter(board_size=9)
        assert "pass" in adapter.get_legal_moves()

    def test_apply_and_undo(self):
        adapter = GoAdapter(board_size=9)
        ok = adapter.apply_move("D5")
        assert ok is True
        ok2 = adapter.undo_move()
        assert ok2 is True

    def test_rules_summary_not_empty(self):
        adapter = GoAdapter(board_size=9)
        assert len(adapter.get_game_rules_summary()) > 50
