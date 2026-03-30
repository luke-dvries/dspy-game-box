"""Unit tests for the research logger."""

import os
import tempfile
import pytest

from gamesage.research.logger import ResearchLogger


@pytest.fixture
def tmp_logger(tmp_path):
    """Logger backed by a temporary DB file."""
    db = str(tmp_path / "test.db")
    logger = ResearchLogger(db_path=db)
    yield logger
    logger.close()


class TestResearchLogger:

    def test_start_session_returns_id(self, tmp_logger):
        sid = tmp_logger.start_session("Chess", "beginner", "play")
        assert isinstance(sid, str)
        assert len(sid) == 36  # UUID

    def test_log_move(self, tmp_logger):
        tmp_logger.start_session("Chess", "beginner", "play")
        mid = tmp_logger.log_move(
            player="White",
            move_played="e4",
            board_state_before="...",
            llm_recommended_move="e4",
            llm_explanation="Good opening move.",
            llm_reasoning="Controls the center.",
            followed_advice=True,
            time_taken_seconds=1.23,
        )
        assert isinstance(mid, int)

    def test_log_multiple_moves(self, tmp_logger):
        tmp_logger.start_session("Chess", "intermediate", "coach")
        ids = []
        for move in ["e4", "e5", "Nf3"]:
            mid = tmp_logger.log_move(player="White", move_played=move, board_state_before="...")
            ids.append(mid)
        assert len(set(ids)) == 3  # all unique IDs

    def test_log_rating(self, tmp_logger):
        tmp_logger.start_session("Go", "beginner", "play")
        mid = tmp_logger.log_move(player="Black", move_played="D5", board_state_before="...")
        tmp_logger.log_rating(move_id=mid, clarity=4, helpfulness=5, comments="Great!")

    def test_end_session(self, tmp_logger):
        tmp_logger.start_session("Sudoku", "easy", "puzzle")
        tmp_logger.end_session()
        # Verify the row has an ended_at value
        conn = tmp_logger._get_conn()
        row = conn.execute(
            "SELECT ended_at FROM sessions WHERE id = ?", (tmp_logger._session_id,)
        ).fetchone()
        assert row is not None
        assert row["ended_at"] is not None

    def test_context_manager(self, tmp_path):
        db = str(tmp_path / "ctx.db")
        with ResearchLogger(db_path=db) as logger:
            logger.start_session("Checkers", "advanced", "analyze")
            logger.log_move(player="Red", move_played="5,2→4,3", board_state_before="...")

    def test_disabled_logger_does_not_write(self, monkeypatch, tmp_path):
        monkeypatch.setattr("gamesage.config.RESEARCH_LOGGING_ENABLED", False)
        db = str(tmp_path / "disabled.db")
        logger = ResearchLogger(db_path=db)
        sid = logger.start_session("Chess", "beginner", "play")
        logger.log_move(player="White", move_played="e4", board_state_before="...")
        logger.close()
        # DB file should NOT have been created
        assert not os.path.exists(db)
