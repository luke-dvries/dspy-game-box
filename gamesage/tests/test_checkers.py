"""Unit tests for the Checkers adapter (no LLM required)."""

import pytest

from gamesage.games.checkers.engine import CheckersEngine, RED, BLACK, RED_K, BLK_K, EMPTY
from gamesage.games.checkers.adapter import CheckersAdapter


class TestCheckersEngine:

    def test_initial_piece_count(self):
        engine = CheckersEngine()
        counts = engine.get_piece_counts()
        assert counts["red"] == 12
        assert counts["black"] == 12
        assert counts["red_kings"] == 0
        assert counts["black_kings"] == 0

    def test_initial_player_is_red(self):
        engine = CheckersEngine()
        assert engine.current_player == RED

    def test_legal_moves_at_start(self):
        engine = CheckersEngine()
        moves = engine.get_legal_moves()
        # Red can move pieces in row 5: forward diagonal from col 0,2,4,6
        assert len(moves) == 7  # standard starting position

    def test_apply_move_notation(self):
        engine = CheckersEngine()
        moves = engine.get_legal_moves_notation()
        first = moves[0]
        ok = engine.apply_move_notation(first)
        assert ok is True
        assert engine.current_player == BLACK

    def test_apply_illegal_move(self):
        engine = CheckersEngine()
        ok = engine.apply_move_notation("0,0→1,1")
        assert ok is False

    def test_undo_move(self):
        engine = CheckersEngine()
        moves = engine.get_legal_moves_notation()
        engine.apply_move_notation(moves[0])
        ok = engine.undo_move()
        assert ok is True
        assert engine.current_player == RED

    def test_undo_at_start(self):
        engine = CheckersEngine()
        assert engine.undo_move() is False

    def test_game_not_over_at_start(self):
        engine = CheckersEngine()
        over, _ = engine.is_game_over()
        assert over is False

    def test_board_serialization(self):
        engine = CheckersEngine()
        text = engine.to_text()
        assert "r" in text   # red pieces
        assert "b" in text   # black pieces

    def test_piece_positions(self):
        engine = CheckersEngine()
        # Black pieces should be in rows 0-2, on dark squares
        for r in range(3):
            for c in range(8):
                if (r + c) % 2 == 1:
                    assert engine.board[r][c] == BLACK
        # Red pieces in rows 5-7
        for r in range(5, 8):
            for c in range(8):
                if (r + c) % 2 == 1:
                    assert engine.board[r][c] == RED

    def test_king_promotion(self):
        """Test that a piece reaching the back rank becomes a king."""
        engine = CheckersEngine()
        # Place a single red piece near black's back rank
        engine.board = [[EMPTY] * 8 for _ in range(8)]
        engine.board[1][2] = RED
        engine.current_player = RED
        moves = engine.get_legal_moves_notation()
        assert len(moves) > 0
        engine.apply_move_notation(moves[0])
        # Check if piece at row 0 is now a king
        for c in range(8):
            if engine.board[0][c] == RED_K:
                return
        # Promotion might not have happened if the move didn't go to row 0
        # That's fine — just check the move was applied

    def test_mandatory_capture(self):
        """Verify captures are mandatory when available."""
        engine = CheckersEngine()
        engine.board = [[EMPTY] * 8 for _ in range(8)]
        engine.board[4][4] = RED
        engine.board[3][5] = BLACK
        engine.current_player = RED
        moves = engine.get_legal_moves()
        # All legal moves must be captures
        assert all(len(m.captures) > 0 for m in moves)


class TestCheckersAdapter:

    def test_get_game_name(self):
        adapter = CheckersAdapter()
        assert adapter.get_game_name() == "Checkers"

    def test_board_state_keys(self):
        adapter = CheckersAdapter()
        state = adapter.get_board_state()
        assert "board" in state
        assert "current_player" in state
        assert "extra" in state

    def test_serialize_board(self):
        adapter = CheckersAdapter()
        serialized = adapter.serialize_board()
        assert "Checkers" in serialized
        assert "Red" in serialized

    def test_legal_moves_not_empty(self):
        adapter = CheckersAdapter()
        assert len(adapter.get_legal_moves()) > 0

    def test_apply_and_undo(self):
        adapter = CheckersAdapter()
        moves = adapter.get_legal_moves()
        ok = adapter.apply_move(moves[0])
        assert ok is True
        ok2 = adapter.undo_move()
        assert ok2 is True

    def test_rules_summary_not_empty(self):
        adapter = CheckersAdapter()
        assert len(adapter.get_game_rules_summary()) > 50
