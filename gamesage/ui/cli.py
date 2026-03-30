"""GameSage main CLI loop — Rich-powered interactive interface."""

from __future__ import annotations

import time
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt
from rich.table import Table
from rich import box
from rich.text import Text

from gamesage.core.adapter import GameAdapter
from gamesage.core.explainer import GameSageAdvisor, GameSageCoach
from gamesage.research.logger import ResearchLogger

console = Console()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _print_header(title: str) -> None:
    console.print(Panel(f"[bold cyan]{title}[/]", border_style="bright_blue"))


def _print_explanation(
    recommended_move: str,
    explanation: str,
    key_concepts: str,
    alternative_moves: str,
    strategic_reasoning: str,
    skill_level: str,
) -> None:
    table = Table(show_header=False, box=box.ROUNDED, border_style="cyan", expand=True)
    table.add_column("Key", style="bold yellow", min_width=22)
    table.add_column("Value")
    table.add_row("Recommended Move", f"[bold green]{recommended_move}[/]")
    table.add_row("Explanation", explanation)
    if alternative_moves:
        table.add_row("Alternatives", alternative_moves)
    if key_concepts:
        table.add_row("Key Concepts", f"[italic cyan]{key_concepts}[/]")
    if skill_level == "advanced" and strategic_reasoning:
        table.add_row("Strategic Reasoning", f"[dim]{strategic_reasoning}[/]")
    console.print(table)


def _print_coaching(pred) -> None:
    table = Table(show_header=False, box=box.ROUNDED, border_style="magenta", expand=True)
    table.add_column("Key", style="bold yellow", min_width=22)
    table.add_column("Value")
    table.add_row("Position Summary", pred.position_summary)
    table.add_row("Your Advantages", pred.advantages)
    table.add_row("Threats", pred.threats)
    table.add_row("Focus", pred.suggested_focus)
    table.add_row("Move Explanation", pred.explanation)
    table.add_row("What It Sets Up", pred.what_it_sets_up)
    table.add_row("What It Prevents", pred.what_it_prevents)
    console.print(Panel(table, title="[bold magenta]Coach Analysis[/]", border_style="magenta"))


# ---------------------------------------------------------------------------
# Renderer dispatch
# ---------------------------------------------------------------------------

def _render_board(adapter: GameAdapter) -> None:
    """Delegate board rendering to the appropriate game renderer."""
    name = adapter.get_game_name().lower()
    if "chess" in name:
        from gamesage.games.chess.renderer import render_board
        from gamesage.games.chess.adapter import ChessAdapter
        assert isinstance(adapter, ChessAdapter)
        render_board(adapter._engine.board, console)
    elif "checkers" in name:
        from gamesage.games.checkers.renderer import render_board
        render_board(adapter._engine.board, console)  # type: ignore[arg-type]
    elif "go" in name:
        from gamesage.games.go.renderer import render_board
        render_board(adapter._engine.board, console)  # type: ignore[arg-type]
    elif "sudoku" in name:
        from gamesage.games.sudoku.renderer import render_board
        board = adapter._engine.board  # type: ignore[attr-defined]
        given = adapter._engine._given  # type: ignore[attr-defined]
        render_board(board, given, console)
    else:
        console.print(adapter.serialize_board())


# ---------------------------------------------------------------------------
# Game loop
# ---------------------------------------------------------------------------

class GameSession:
    """Encapsulates a single game session."""

    def __init__(
        self,
        adapter: GameAdapter,
        skill_level: str,
        mode: str,
        logger: ResearchLogger,
        dry_run: bool = False,
    ) -> None:
        self.adapter = adapter
        self.skill_level = skill_level
        self.mode = mode
        self.logger = logger
        self.dry_run = dry_run
        self.advisor = GameSageAdvisor()
        self.coach = GameSageCoach()
        self._last_board_before: str = ""
        self._last_move_played: str = ""
        self._last_move_id: int = 0

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(self) -> None:
        self.logger.start_session(
            self.adapter.get_game_name(), self.skill_level, self.mode
        )
        _print_header(
            f"GameSage — {self.adapter.get_game_name()} | "
            f"Mode: {self.mode} | Skill: {self.skill_level}"
        )
        console.print(
            "[dim]Commands: [bold]hint[/], [bold]explain[/], [bold]eval[/], "
            "[bold]undo[/], [bold]quit[/][/]"
        )

        try:
            if self.mode == "play":
                self._play_loop()
            elif self.mode == "coach":
                self._coach_loop()
            elif self.mode == "analyze":
                self._analyze_loop()
            elif self.mode == "puzzle":
                self._puzzle_loop()
            else:
                console.print(f"[red]Unknown mode: {self.mode}[/]")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Session interrupted.[/]")
        finally:
            self.logger.end_session()
            if not self.dry_run:
                self.logger.prompt_end_of_game_rating(console)

    # ------------------------------------------------------------------
    # Mode: Play (Human vs AI)
    # ------------------------------------------------------------------

    def _play_loop(self) -> None:
        human_player = self._pick_human_color()
        while True:
            over, result = self.adapter.is_game_over()
            if over:
                _render_board(self.adapter)
                console.print(Panel(f"[bold green]Game Over: {result}[/]", border_style="green"))
                break

            _render_board(self.adapter)
            current = self.adapter.get_board_state()["current_player"]

            if current == human_player:
                move = self._human_move()
            else:
                move = self._ai_move()

            if move is None:
                break

    # ------------------------------------------------------------------
    # Mode: Coach (Human plays both sides, AI comments)
    # ------------------------------------------------------------------

    def _coach_loop(self) -> None:
        while True:
            over, result = self.adapter.is_game_over()
            if over:
                _render_board(self.adapter)
                console.print(Panel(f"[bold green]Game Over: {result}[/]", border_style="green"))
                break

            _render_board(self.adapter)
            state = self.adapter.get_board_state()
            console.print(f"[bold cyan]Turn: {state['current_player']}[/]")

            board_before = self.adapter.serialize_board()
            move = self._get_human_input()
            if move is None:
                break
            if self._handle_command(move, board_before):
                continue

            start = time.time()
            ok = self.adapter.apply_move(move)
            elapsed = time.time() - start
            if not ok:
                console.print(f"[red]Illegal move: {move!r}[/]")
                continue

            board_after = self.adapter.serialize_board()
            self._last_board_before = board_before
            self._last_move_played = move

            # Get AI coaching comment
            console.print("[bold magenta]Coach is analysing...[/]")
            try:
                pred = self.coach.forward(
                    game_name=self.adapter.get_game_name(),
                    board_before=board_before,
                    move_played=move,
                    board_after=board_after,
                    current_player=state["current_player"],
                    player_skill_level=self.skill_level,
                )
                _print_coaching(pred)
                explanation = pred.explanation
                reasoning = pred.position_summary
            except Exception as e:
                console.print(f"[dim red]Coach error: {e}[/]")
                explanation = ""
                reasoning = ""

            self._last_move_id = self.logger.log_move(
                player=state["current_player"],
                move_played=move,
                board_state_before=board_before,
                llm_explanation=explanation,
                llm_reasoning=reasoning,
                time_taken_seconds=elapsed,
            )

    # ------------------------------------------------------------------
    # Mode: Analyze
    # ------------------------------------------------------------------

    def _analyze_loop(self) -> None:
        console.print("[cyan]Analyze mode — the AI will evaluate the current position.[/]")
        while True:
            _render_board(self.adapter)
            board_state = self.adapter.serialize_board()
            current = self.adapter.get_board_state()["current_player"]

            console.print("[bold magenta]Evaluating position...[/]")
            try:
                pred = self.coach.evaluate_position(
                    game_name=self.adapter.get_game_name(),
                    board_state=board_state,
                    current_player=current,
                )
                table = Table(show_header=False, box=box.ROUNDED, border_style="cyan")
                table.add_column("Key", style="bold yellow", min_width=20)
                table.add_column("Value")
                table.add_row("Position Summary", pred.position_summary)
                table.add_row("Advantages", pred.advantages)
                table.add_row("Threats", pred.threats)
                table.add_row("Suggested Focus", pred.suggested_focus)
                console.print(Panel(table, title="[bold cyan]Position Analysis[/]"))
            except Exception as e:
                console.print(f"[red]Analysis error: {e}[/]")

            cmd = Prompt.ask(
                "\nEnter a move to play, or [bold]quit[/]", console=console
            ).strip()
            if cmd.lower() in ("quit", "q", "exit"):
                break
            if not self.adapter.apply_move(cmd):
                console.print(f"[red]Illegal move: {cmd!r}[/]")

    # ------------------------------------------------------------------
    # Mode: Puzzle (step-by-step AI guidance)
    # ------------------------------------------------------------------

    def _puzzle_loop(self) -> None:
        console.print("[cyan]Puzzle mode — follow the AI's hints to solve the puzzle.[/]")
        while True:
            over, result = self.adapter.is_game_over()
            if over:
                _render_board(self.adapter)
                console.print(Panel(f"[bold green]{result}[/]", border_style="green"))
                break

            _render_board(self.adapter)
            board_state = self.adapter.serialize_board()
            legal = self.adapter.get_legal_moves()

            # Always show AI hint in puzzle mode
            console.print("[bold magenta]Getting hint...[/]")
            try:
                pred = self.advisor.forward(
                    game_name=self.adapter.get_game_name(),
                    rules_summary=self.adapter.get_game_rules_summary(),
                    board_state=board_state,
                    legal_moves=legal,
                    move_history=self.adapter.get_move_history(),
                    player_skill_level=self.skill_level,
                    validate_move_fn=self.adapter.is_move_legal if hasattr(self.adapter, "is_move_legal") else None,
                )
                _print_explanation(
                    recommended_move=pred.recommended_move,
                    explanation=pred.explanation,
                    key_concepts=pred.key_concepts,
                    alternative_moves=pred.alternative_moves,
                    strategic_reasoning=pred.strategic_reasoning,
                    skill_level=self.skill_level,
                )
            except Exception as e:
                console.print(f"[red]Advisor error: {e}[/]")
                pred = None

            move = self._get_human_input(prompt="Play a move (or 'hint' to use AI's suggestion)")
            if move is None:
                break

            if move.lower() == "hint" and pred:
                move = pred.recommended_move.strip()
                console.print(f"[green]Playing AI suggestion: {move}[/]")

            if self._handle_command(move, board_state):
                continue

            if not self.adapter.apply_move(move):
                console.print(f"[red]Illegal move: {move!r}[/]")

    # ------------------------------------------------------------------
    # Human move helpers
    # ------------------------------------------------------------------

    def _human_move(self) -> Optional[str]:
        board_before = self.adapter.serialize_board()
        state = self.adapter.get_board_state()
        console.print(f"[bold cyan]Your turn ({state['current_player']})[/]")

        while True:
            raw = self._get_human_input()
            if raw is None:
                return None
            if self._handle_command(raw, board_before):
                continue

            start = time.time()
            ok = self.adapter.apply_move(raw)
            elapsed = time.time() - start
            if not ok:
                console.print(f"[red]Illegal move: {raw!r}. Try again.[/]")
                continue

            self._last_board_before = board_before
            self._last_move_played = raw
            self._last_move_id = self.logger.log_move(
                player=state["current_player"],
                move_played=raw,
                board_state_before=board_before,
                time_taken_seconds=elapsed,
            )
            return raw

    def _ai_move(self) -> Optional[str]:
        state = self.adapter.get_board_state()
        board_before = self.adapter.serialize_board()
        console.print(f"[bold magenta]AI is thinking ({state['current_player']})...[/]")

        legal = self.adapter.get_legal_moves()
        if not legal:
            console.print("[red]No legal moves for AI.[/]")
            return None

        try:
            start = time.time()
            pred = self.advisor.forward(
                game_name=self.adapter.get_game_name(),
                rules_summary=self.adapter.get_game_rules_summary(),
                board_state=board_before,
                legal_moves=legal,
                move_history=self.adapter.get_move_history(),
                player_skill_level=self.skill_level,
                validate_move_fn=self.adapter.is_move_legal if hasattr(self.adapter, "is_move_legal") else None,
            )
            elapsed = time.time() - start
            move = pred.recommended_move.strip()

            _print_explanation(
                recommended_move=move,
                explanation=pred.explanation,
                key_concepts=pred.key_concepts,
                alternative_moves=pred.alternative_moves,
                strategic_reasoning=pred.strategic_reasoning,
                skill_level=self.skill_level,
            )

            if not self.adapter.apply_move(move):
                console.print(f"[red]AI returned an unplayable move: {move!r}[/]")
                return None

            self._last_board_before = board_before
            self._last_move_played = move
            self._last_move_id = self.logger.log_move(
                player=state["current_player"],
                move_played=move,
                board_state_before=board_before,
                llm_recommended_move=move,
                llm_explanation=pred.explanation,
                llm_reasoning=pred.strategic_reasoning,
                time_taken_seconds=elapsed,
            )
        except Exception as e:
            console.print(f"[red]AI error: {e}[/]")
            import random
            move = random.choice(legal)
            self.adapter.apply_move(move)
            console.print(f"[yellow]Fell back to random move: {move}[/]")

        return move

    # ------------------------------------------------------------------
    # Command handling
    # ------------------------------------------------------------------

    def _get_human_input(self, prompt: str = "Enter move") -> Optional[str]:
        try:
            return Prompt.ask(f"\n[bold yellow]{prompt}[/]", console=console).strip()
        except (KeyboardInterrupt, EOFError):
            return None

    def _handle_command(self, cmd: str, board_before: str) -> bool:
        """Process special commands.  Returns True if cmd was a command (not a move)."""
        lower = cmd.lower()

        if lower in ("quit", "q", "exit"):
            console.print("[yellow]Quitting session.[/]")
            raise KeyboardInterrupt

        if lower == "undo":
            if self.adapter.undo_move():
                console.print("[green]Move undone.[/]")
            else:
                console.print("[red]Nothing to undo.[/]")
            return True

        if lower == "hint":
            self._show_hint()
            return True

        if lower == "explain":
            self._explain_last_move()
            return True

        if lower == "eval":
            self._evaluate_position()
            return True

        if lower == "moves":
            legal = self.adapter.get_legal_moves()
            console.print(f"[cyan]Legal moves ({len(legal)}): {', '.join(legal[:30])}"
                          + (" ..." if len(legal) > 30 else "") + "[/]")
            return True

        return False

    def _show_hint(self) -> None:
        legal = self.adapter.get_legal_moves()
        if not legal:
            console.print("[red]No legal moves available.[/]")
            return
        board_state = self.adapter.serialize_board()
        console.print("[magenta]Thinking...[/]")
        try:
            pred = self.advisor.forward(
                game_name=self.adapter.get_game_name(),
                rules_summary=self.adapter.get_game_rules_summary(),
                board_state=board_state,
                legal_moves=legal,
                move_history=self.adapter.get_move_history(),
                player_skill_level=self.skill_level,
            )
            _print_explanation(
                recommended_move=pred.recommended_move,
                explanation=pred.explanation,
                key_concepts=pred.key_concepts,
                alternative_moves=pred.alternative_moves,
                strategic_reasoning=pred.strategic_reasoning,
                skill_level=self.skill_level,
            )
        except Exception as e:
            console.print(f"[red]Hint error: {e}[/]")

    def _explain_last_move(self) -> None:
        if not self._last_move_played:
            console.print("[yellow]No move to explain yet.[/]")
            return
        board_after = self.adapter.serialize_board()
        console.print("[magenta]Explaining...[/]")
        try:
            pred = self.coach.explain_move(
                game_name=self.adapter.get_game_name(),
                board_before=self._last_board_before,
                move_played=self._last_move_played,
                board_after=board_after,
                player_skill_level=self.skill_level,
            )
            table = Table(show_header=False, box=box.ROUNDED, border_style="cyan")
            table.add_column("Key", style="bold yellow", min_width=22)
            table.add_column("Value")
            table.add_row("Move", f"[bold green]{self._last_move_played}[/]")
            table.add_row("Explanation", pred.explanation)
            table.add_row("Sets Up", pred.what_it_sets_up)
            table.add_row("Prevents", pred.what_it_prevents)
            console.print(Panel(table, title="[bold cyan]Move Explanation[/]"))
        except Exception as e:
            console.print(f"[red]Explain error: {e}[/]")

    def _evaluate_position(self) -> None:
        board_state = self.adapter.serialize_board()
        current = self.adapter.get_board_state()["current_player"]
        console.print("[magenta]Evaluating...[/]")
        try:
            pred = self.coach.evaluate_position(
                game_name=self.adapter.get_game_name(),
                board_state=board_state,
                current_player=current,
            )
            table = Table(show_header=False, box=box.ROUNDED, border_style="magenta")
            table.add_column("Key", style="bold yellow", min_width=22)
            table.add_column("Value")
            table.add_row("Position Summary", pred.position_summary)
            table.add_row("Advantages", pred.advantages)
            table.add_row("Threats", pred.threats)
            table.add_row("Suggested Focus", pred.suggested_focus)
            console.print(Panel(table, title="[bold magenta]Position Evaluation[/]"))
        except Exception as e:
            console.print(f"[red]Eval error: {e}[/]")

    def _pick_human_color(self) -> str:
        game = self.adapter.get_game_name().lower()
        if "chess" in game:
            choice = Prompt.ask(
                "Play as [bold]White[/] or [bold]Black[/]?",
                choices=["White", "Black"],
                default="White",
                console=console,
            )
            return choice
        if "checkers" in game:
            choice = Prompt.ask(
                "Play as [bold]Red[/] or [bold]Black[/]?",
                choices=["Red", "Black"],
                default="Red",
                console=console,
            )
            return choice
        if "go" in game:
            choice = Prompt.ask(
                "Play as [bold]Black[/] or [bold]White[/]?",
                choices=["Black", "White"],
                default="Black",
                console=console,
            )
            return choice
        return "Solver"


# ---------------------------------------------------------------------------
# Main menu
# ---------------------------------------------------------------------------

def main_menu() -> tuple[str, str, str]:
    """Display main menu.  Returns (game_choice, skill_level, mode)."""
    _print_header("Welcome to GameSage — AI-Powered Board Game Coach")

    game_table = Table(title="Select a Game", box=box.ROUNDED, border_style="cyan")
    game_table.add_column("No.", style="bold yellow", justify="right")
    game_table.add_column("Game")
    for i, g in enumerate(["Chess", "Checkers", "Go", "Sudoku"], 1):
        game_table.add_row(str(i), g)
    console.print(game_table)

    game_choice = Prompt.ask(
        "Game",
        choices=["1", "2", "3", "4", "Chess", "Checkers", "Go", "Sudoku"],
        default="1",
        console=console,
    )
    game_map = {"1": "Chess", "2": "Checkers", "3": "Go", "4": "Sudoku"}
    game = game_map.get(game_choice, game_choice)

    skill = Prompt.ask(
        "Skill level",
        choices=["beginner", "intermediate", "advanced"],
        default="beginner",
        console=console,
    )

    available_modes = ["play", "coach", "analyze"]
    if game in ("Sudoku", "Chess"):
        available_modes.append("puzzle")

    mode = Prompt.ask(
        "Mode",
        choices=available_modes,
        default="play",
        console=console,
    )

    return game, skill, mode
