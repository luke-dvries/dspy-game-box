"""Unit tests for the Sudoku adapter (no LLM required)."""

import pytest

from gamesage.games.sudoku.engine import SudokuEngine
from gamesage.games.sudoku.adapter import SudokuAdapter


class TestSudokuEngine:

    def _make_engine(self, difficulty="easy") -> SudokuEngine:
        engine = SudokuEngine()
        engine.new_puzzle(difficulty)
        return engine

    def test_puzzle_has_correct_clue_count(self):
        from gamesage.games.sudoku.engine import DIFFICULTY_CLUES
        for diff, target in DIFFICULTY_CLUES.items():
            engine = self._make_engine(diff)
            filled = engine.count_given()
            # Allow ±3 slack due to uniqueness-preservation skipping
            assert abs(filled - target) <= 3, f"{diff}: got {filled}, expected ~{target}"

    def test_no_duplicates_in_rows(self):
        engine = self._make_engine()
        for r in range(9):
            vals = [v for v in engine.board[r] if v != 0]
            assert len(vals) == len(set(vals))

    def test_no_duplicates_in_cols(self):
        engine = self._make_engine()
        for c in range(9):
            vals = [engine.board[r][c] for r in range(9) if engine.board[r][c] != 0]
            assert len(vals) == len(set(vals))

    def test_no_duplicates_in_boxes(self):
        engine = self._make_engine()
        for br in range(3):
            for bc in range(3):
                vals = [
                    engine.board[br * 3 + r][bc * 3 + c]
                    for r in range(3) for c in range(3)
                    if engine.board[br * 3 + r][bc * 3 + c] != 0
                ]
                assert len(vals) == len(set(vals))

    def test_legal_moves_not_empty(self):
        engine = self._make_engine()
        assert len(engine.get_legal_moves()) > 0

    def test_legal_moves_format(self):
        engine = self._make_engine()
        for move in engine.get_legal_moves()[:5]:
            parts = move.split(",")
            assert len(parts) == 3
            r, c, d = int(parts[0]), int(parts[1]), int(parts[2])
            assert 1 <= r <= 9
            assert 1 <= c <= 9
            assert 1 <= d <= 9

    def test_apply_valid_move(self):
        engine = self._make_engine()
        moves = engine.get_legal_moves()
        first = moves[0]
        ok = engine.apply_move(first)
        assert ok is True
        assert engine.move_count == 1

    def test_apply_invalid_move_format(self):
        engine = self._make_engine()
        ok = engine.apply_move("bad,input")
        assert ok is False

    def test_apply_to_clue_cell_fails(self):
        engine = self._make_engine()
        # Find a clue cell
        for r in range(9):
            for c in range(9):
                if engine._given[r][c]:
                    ok = engine.apply_move(f"{r+1},{c+1},{engine.board[r][c]}")
                    assert ok is False
                    return

    def test_undo_move(self):
        engine = self._make_engine()
        moves = engine.get_legal_moves()
        engine.apply_move(moves[0])
        ok = engine.undo_move()
        assert ok is True
        assert engine.move_count == 0

    def test_undo_at_start(self):
        engine = self._make_engine()
        assert engine.undo_move() is False

    def test_game_not_solved_at_start(self):
        engine = self._make_engine()
        assert engine.is_solved() is False

    def test_serialization_format(self):
        engine = self._make_engine()
        text = engine.to_text()
        assert "|" in text    # box separators
        assert "---" in text  # row separators
        lines = text.strip().split("\n")
        assert len(lines) == 12  # 1 header + 9 rows + 2 box-separator lines

    def test_solution_is_valid(self):
        """Verify the internally stored solution passes Sudoku constraints."""
        engine = self._make_engine()
        sol = engine._solution
        for r in range(9):
            assert sorted(sol[r]) == list(range(1, 10))
        for c in range(9):
            assert sorted(sol[r][c] for r in range(9)) == list(range(1, 10))
        for br in range(3):
            for bc in range(3):
                box = [sol[br*3+r][bc*3+c] for r in range(3) for c in range(3)]
                assert sorted(box) == list(range(1, 10))


class TestSudokuAdapter:

    def test_get_game_name(self):
        adapter = SudokuAdapter(difficulty="easy")
        assert "Sudoku" in adapter.get_game_name()

    def test_board_state_keys(self):
        adapter = SudokuAdapter()
        state = adapter.get_board_state()
        assert "board" in state
        assert "current_player" in state
        assert "extra" in state

    def test_serialize_board(self):
        adapter = SudokuAdapter()
        serialized = adapter.serialize_board()
        assert "Sudoku" in serialized
        assert "filled" in serialized

    def test_apply_and_undo(self):
        adapter = SudokuAdapter()
        moves = adapter.get_legal_moves()
        ok = adapter.apply_move(moves[0])
        assert ok is True
        ok2 = adapter.undo_move()
        assert ok2 is True

    def test_rules_summary_not_empty(self):
        adapter = SudokuAdapter()
        assert len(adapter.get_game_rules_summary()) > 50

    def test_move_history(self):
        adapter = SudokuAdapter()
        moves = adapter.get_legal_moves()
        adapter.apply_move(moves[0])
        assert len(adapter.get_move_history()) == 1
