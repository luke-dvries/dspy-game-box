"""Rich-powered checkers board renderer."""

from __future__ import annotations

from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich import box

from gamesage.games.checkers.engine import RED, BLACK, RED_K, BLK_K, EMPTY

LIGHT_SQ = "grey85"
DARK_SQ  = "grey30"

PIECE_STYLES = {
    RED:   ("r", "bold red on grey30"),
    RED_K: ("R", "bold red on grey30"),
    BLACK: ("b", "bold blue on grey30"),
    BLK_K: ("B", "bold blue on grey30"),
    EMPTY: (" ", "on grey30"),
}

LIGHT_EMPTY_STYLE = "on grey85"


def render_board(board: list[list[str]], console: Console | None = None) -> None:
    """Render a checkers board with Rich colors."""
    if console is None:
        console = Console()

    table = Table(show_header=False, show_edge=True, box=box.SQUARE, padding=(0, 1))
    for _ in range(9):
        table.add_column(justify="center", min_width=2)

    for r, row in enumerate(board):
        cells: list[Text | str] = [Text(str(r), style="bold yellow")]
        for c, cell in enumerate(row):
            is_dark = (r + c) % 2 == 1
            if is_dark:
                sym, style = PIECE_STYLES.get(cell, (" ", "on grey30"))
                cells.append(Text(sym, style=style))
            else:
                cells.append(Text(" ", style=LIGHT_EMPTY_STYLE))
        table.add_row(*cells)

    col_labels = [" "] + [Text(str(c), style="bold yellow") for c in range(8)]
    table.add_row(*col_labels)

    console.print(table)
