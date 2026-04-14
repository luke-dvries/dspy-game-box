"""Rich-powered Othello board renderer."""

from __future__ import annotations

from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich import box

from gamesage.games.othello.engine import EMPTY, BLACK, WHITE, _COL_LETTERS

CELL_STYLES = {
    EMPTY: ("·", "dim white on green4"),
    BLACK: ("●", "bold black on green4"),
    WHITE: ("○", "bold white on green4"),
}


def render_board(board: list[list[int]], console: Console | None = None) -> None:
    """Render an Othello board with Rich."""
    if console is None:
        console = Console()

    table = Table(show_header=False, show_edge=True, box=box.SQUARE, padding=(0, 0))
    for _ in range(9):
        table.add_column(justify="center", min_width=3)

    for r in range(8):
        row_label = Text(str(r + 1).rjust(2), style="bold yellow")
        cells: list[Text] = [row_label]
        for c in range(8):
            val = board[r][c]
            sym, style = CELL_STYLES[val]
            cells.append(Text(f" {sym} ", style=style))
        table.add_row(*cells)

    col_labels = [Text("  ")] + [
        Text(f" {ch} ", style="bold yellow") for ch in _COL_LETTERS
    ]
    table.add_row(*col_labels)

    console.print(table)
