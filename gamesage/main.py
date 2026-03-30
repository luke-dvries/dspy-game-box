#!/usr/bin/env python3
"""GameSage — entry point.

Usage
-----
    python -m gamesage.main            # interactive menu
    python -m gamesage.main --dry-run  # mock LLM, no API calls
    python -m gamesage.main --game chess --skill intermediate --mode play
"""

from __future__ import annotations

import argparse
import sys

from rich.console import Console

console = Console()


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="gamesage",
        description="GameSage — AI-powered board game advisor",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Use a mock LLM — no API calls required",
    )
    p.add_argument(
        "--game",
        choices=["chess", "checkers", "go", "sudoku"],
        help="Skip the menu and start a specific game",
    )
    p.add_argument(
        "--skill",
        choices=["beginner", "intermediate", "advanced"],
        default="beginner",
        help="Skill level (default: beginner)",
    )
    p.add_argument(
        "--mode",
        choices=["play", "coach", "analyze", "puzzle"],
        default="play",
        help="Game mode (default: play)",
    )
    p.add_argument(
        "--sudoku-difficulty",
        choices=["easy", "medium", "hard"],
        default="easy",
        help="Sudoku difficulty (default: easy)",
    )
    p.add_argument(
        "--go-size",
        type=int,
        default=None,
        help="Go board size (default from config, typically 9)",
    )
    p.add_argument(
        "--fen",
        type=str,
        default=None,
        help="Chess: load a position from FEN string",
    )
    return p


def _make_adapter(game: str, args: argparse.Namespace):
    """Instantiate the correct adapter based on game name."""
    g = game.lower()
    if g == "chess":
        from gamesage.games.chess.adapter import ChessAdapter
        adapter = ChessAdapter()
        if args.fen:
            adapter.load_fen(args.fen)
        return adapter
    if g == "checkers":
        from gamesage.games.checkers.adapter import CheckersAdapter
        return CheckersAdapter()
    if g == "go":
        from gamesage.games.go.adapter import GoAdapter
        return GoAdapter(board_size=args.go_size)
    if g == "sudoku":
        from gamesage.games.sudoku.adapter import SudokuAdapter
        return SudokuAdapter(difficulty=args.sudoku_difficulty)
    raise ValueError(f"Unknown game: {game!r}")


def main() -> None:
    args = _build_parser().parse_args()

    # Configure DSPy (must happen before importing modules that use it)
    from gamesage import config
    config.configure_dspy(dry_run=args.dry_run)

    from gamesage.research.logger import ResearchLogger
    from gamesage.ui.cli import main_menu, GameSession

    # Determine game / skill / mode
    if args.game:
        game, skill, mode = args.game.capitalize(), args.skill, args.mode
    else:
        game, skill, mode = main_menu()

    adapter = _make_adapter(game, args)

    with ResearchLogger() as logger:
        session = GameSession(
            adapter=adapter,
            skill_level=skill,
            mode=mode,
            logger=logger,
            dry_run=args.dry_run,
        )
        session.run()


if __name__ == "__main__":
    main()
