"""Research logger — records every GameSage session to SQLite.

Schema
------
sessions  — one row per game session
moves     — one row per move (human or AI)
ratings   — optional per-move explanation quality ratings
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from gamesage import config


# ---------------------------------------------------------------------------
# DDL
# ---------------------------------------------------------------------------

_DDL = """
CREATE TABLE IF NOT EXISTS sessions (
    id           TEXT PRIMARY KEY,
    game         TEXT NOT NULL,
    skill_level  TEXT NOT NULL,
    mode         TEXT NOT NULL,
    started_at   TEXT NOT NULL,
    ended_at     TEXT
);

CREATE TABLE IF NOT EXISTS moves (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id            TEXT NOT NULL,
    move_number           INTEGER NOT NULL,
    player                TEXT NOT NULL,
    move_played           TEXT NOT NULL,
    board_state_before    TEXT NOT NULL,
    llm_recommended_move  TEXT,
    llm_explanation       TEXT,
    llm_reasoning         TEXT,
    followed_advice       INTEGER,
    time_taken_seconds    REAL,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS ratings (
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id               TEXT NOT NULL,
    move_id                  INTEGER NOT NULL,
    explanation_clarity      INTEGER,
    explanation_helpfulness  INTEGER,
    comments                 TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions(id),
    FOREIGN KEY (move_id)    REFERENCES moves(id)
);
"""


# ---------------------------------------------------------------------------
# Logger class
# ---------------------------------------------------------------------------

class ResearchLogger:
    """Thread-safe (single-connection) research logger."""

    def __init__(self, db_path: str | None = None) -> None:
        self._path = db_path or config.DB_PATH
        self._conn: sqlite3.Connection | None = None
        self._session_id: str | None = None
        self._move_counter: int = 0
        self._enabled = config.RESEARCH_LOGGING_ENABLED

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            Path(self._path).parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(self._path)
            self._conn.row_factory = sqlite3.Row
            self._conn.executescript(_DDL)
            self._conn.commit()
        return self._conn

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def start_session(self, game: str, skill_level: str, mode: str) -> str:
        """Open a new session and return its ID."""
        if not self._enabled:
            self._session_id = str(uuid.uuid4())
            return self._session_id

        self._session_id = str(uuid.uuid4())
        self._move_counter = 0
        now = datetime.now(timezone.utc).isoformat()
        self._get_conn().execute(
            "INSERT INTO sessions (id, game, skill_level, mode, started_at) VALUES (?,?,?,?,?)",
            (self._session_id, game, skill_level, mode, now),
        )
        self._get_conn().commit()
        return self._session_id

    def end_session(self) -> None:
        """Mark the current session as ended."""
        if not self._enabled or not self._session_id:
            return
        now = datetime.now(timezone.utc).isoformat()
        self._get_conn().execute(
            "UPDATE sessions SET ended_at = ? WHERE id = ?",
            (now, self._session_id),
        )
        self._get_conn().commit()

    # ------------------------------------------------------------------
    # Move logging
    # ------------------------------------------------------------------

    def log_move(
        self,
        player: str,
        move_played: str,
        board_state_before: str,
        llm_recommended_move: Optional[str] = None,
        llm_explanation: Optional[str] = None,
        llm_reasoning: Optional[str] = None,
        followed_advice: Optional[bool] = None,
        time_taken_seconds: Optional[float] = None,
    ) -> int:
        """Insert a move record.  Returns the new move row id."""
        self._move_counter += 1
        if not self._enabled or not self._session_id:
            return self._move_counter

        followed_int = (1 if followed_advice else 0) if followed_advice is not None else None
        cur = self._get_conn().execute(
            """INSERT INTO moves
               (session_id, move_number, player, move_played, board_state_before,
                llm_recommended_move, llm_explanation, llm_reasoning,
                followed_advice, time_taken_seconds)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                self._session_id, self._move_counter, player, move_played, board_state_before,
                llm_recommended_move, llm_explanation, llm_reasoning,
                followed_int, time_taken_seconds,
            ),
        )
        self._get_conn().commit()
        return cur.lastrowid  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Ratings
    # ------------------------------------------------------------------

    def log_rating(
        self,
        move_id: int,
        clarity: int,
        helpfulness: int,
        comments: str = "",
    ) -> None:
        """Record a user rating for a specific move's explanation."""
        if not self._enabled or not self._session_id:
            return
        self._get_conn().execute(
            """INSERT INTO ratings
               (session_id, move_id, explanation_clarity, explanation_helpfulness, comments)
               VALUES (?,?,?,?,?)""",
            (self._session_id, move_id, clarity, helpfulness, comments),
        )
        self._get_conn().commit()

    # ------------------------------------------------------------------
    # End-of-game summary rating
    # ------------------------------------------------------------------

    def prompt_end_of_game_rating(self, console=None) -> None:
        """Interactively ask the user to rate the session's explanation quality."""
        from rich.console import Console
        from rich.prompt import IntPrompt, Prompt

        if console is None:
            console = Console()

        console.print("\n[bold yellow]Please rate this session's AI explanations (optional):[/]")
        try:
            clarity = IntPrompt.ask("Clarity (1=poor, 5=excellent)", default=0, console=console)
            helpfulness = IntPrompt.ask("Helpfulness (1=poor, 5=excellent)", default=0, console=console)
            comments = Prompt.ask("Any comments?", default="", console=console)
        except (KeyboardInterrupt, EOFError):
            return

        if clarity or helpfulness:
            self.log_rating(move_id=-1, clarity=clarity, helpfulness=helpfulness, comments=comments)
            console.print("[green]Rating saved — thank you![/]")

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> "ResearchLogger":
        return self

    def __exit__(self, *_) -> None:
        self.end_session()
        self.close()
