"""Rich-powered Go board renderer."""

from __future__ import annotations

import numpy as np
from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich import box

from gamesage.games.go.engine import EMPTY, BLACK, WHITE, idx_to_col_letter

CELL_STYLES = {
    EMPTY: ("·", "dim white on dark_goldenrod"),
    BLACK: ("●", "bold black on dark_goldenrod"),
    WHITE: ("○", "bold white on dark_goldenrod"),
}


def render_board(board: np.ndarray, console: Console | None = None) -> None:
    """Render a Go board with Rich."""
    if console is None:
        console = Console()

    size = board.shape[0]
    table = Table(show_header=False, show_edge=True, box=box.SQUARE, padding=(0, 0))
    for _ in range(size + 1):
        table.add_column(justify="center", min_width=3)

    for r in range(size):
        row_label = Text(str(size - r).rjust(2), style="bold yellow")
        cells: list[Text] = [row_label]
        for c in range(size):
            val = int(board[r, c])
            sym, style = CELL_STYLES[val]
            cells.append(Text(f" {sym} ", style=style))
        table.add_row(*cells)

    # Column labels
    col_labels = [Text("  ")] + [
        Text(f" {idx_to_col_letter(c)} ", style="bold yellow") for c in range(size)
    ]
    table.add_row(*col_labels)

    console.print(table)
