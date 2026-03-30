"""Unit tests for the Chess adapter (no LLM required)."""

import pytest

from gamesage.games.chess.adapter import ChessAdapter
from gamesage.games.chess.engine import ChessEngine


class TestChessEngine:

    def test_initial_legal_moves(self):
        engine = ChessEngine()
        moves = engine.get_legal_moves_san()
        # Standard chess has 20 opening moves (16 pawn + 4 knight)
        assert len(moves) == 20

    def test_apply_valid_move(self):
        engine = ChessEngine()
        assert engine.apply_move_san("e4") is True
        assert engine.board.fullmove_number == 1

    def test_apply_invalid_move(self):
        engine = ChessEngine()
        assert engine.apply_move_san("z9") is False

    def test_undo_move(self):
        engine = ChessEngine()
        engine.apply_move_san("e4")
        assert engine.undo_move() is True
        assert len(engine.board.move_stack) == 0

    def test_undo_nothing(self):
        engine = ChessEngine()
        assert engine.undo_move() is False

    def test_game_not_over_at_start(self):
        engine = ChessEngine()
        over, _ = engine.is_game_over()
        assert over is False

    def test_material_count_initial(self):
        engine = ChessEngine()
        counts = engine.get_material_counts()
        # Both sides start equal: 1Q(9) + 2R(10) + 2B(6) + 2N(6) + 8P(8) = 39
        assert counts["White"] == counts["Black"] == 39

    def test_game_phase_opening(self):
        engine = ChessEngine()
        assert engine.get_game_phase() == "opening"

    def test_ascii_board(self):
        engine = ChessEngine()
        board_str = engine.to_ascii()
        assert "a b c d e f g h" in board_str
        assert "r" in board_str  # black rook

    def test_move_history(self):
        engine = ChessEngine()
        engine.apply_move_san("e4")
        engine.apply_move_san("e5")
        assert engine.get_move_history() == ["e4", "e5"]


class TestChessAdapter:

    def test_get_game_name(self):
        adapter = ChessAdapter()
        assert adapter.get_game_name() == "Chess"

    def test_board_state_keys(self):
        adapter = ChessAdapter()
        state = adapter.get_board_state()
        assert "board" in state
        assert "current_player" in state
        assert "move_count" in state
        assert "game_phase" in state
        assert "extra" in state

    def test_serialize_board_contains_fen(self):
        adapter = ChessAdapter()
        serialized = adapter.serialize_board()
        assert "FEN:" in serialized
        assert "Chess" in serialized

    def test_legal_moves_not_empty(self):
        adapter = ChessAdapter()
        assert len(adapter.get_legal_moves()) == 20

    def test_apply_and_undo(self):
        adapter = ChessAdapter()
        ok = adapter.apply_move("e4")
        assert ok is True
        ok2 = adapter.undo_move()
        assert ok2 is True

    def test_is_move_legal(self):
        adapter = ChessAdapter()
        assert adapter.is_move_legal("e4") is True
        assert adapter.is_move_legal("z9") is False

    def test_load_fen(self):
        adapter = ChessAdapter()
        # Scholar's mate position (White to play)
        fen = "rnb1kbnr/pppp1ppp/8/4p3/2B1P3/5Q2/PPPP1PPP/RNB1K1NR b KQkq - 3 3"
        adapter.load_fen(fen)
        state = adapter.get_board_state()
        assert state["current_player"] == "Black"

    def test_rules_summary_not_empty(self):
        adapter = ChessAdapter()
        rules = adapter.get_game_rules_summary()
        assert len(rules) > 50
