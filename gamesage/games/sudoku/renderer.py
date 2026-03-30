"""Rich-powered Sudoku board renderer."""

from __future__ import annotations

from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich import box


GIVEN_STYLE  = "bold cyan"
FILLED_STYLE = "bold green"
EMPTY_STYLE  = "dim white"
BOX_BORDER   = "bold yellow"


def render_board(
    board: list[list[int]],
    given: list[list[bool]] | None = None,
    console: Console | None = None,
) -> None:
    """Render a Sudoku board with Rich.

    Parameters
    ----------
    board : 9x9 list of ints (0 = empty)
    given : 9x9 bool grid — True if the cell is a puzzle clue
    """
    if console is None:
        console = Console()

    # We render as a Rich table with 11 columns:
    # row label | col1 col2 col3 | col4 col5 col6 | col7 col8 col9
    table = Table(show_header=True, show_edge=True, box=box.HEAVY_HEAD, padding=(0, 1))
    table.add_column(" ", style="bold yellow", justify="right")
    for c in range(9):
        table.add_column(str(c + 1), justify="center", min_width=2)

    for r in range(9):
        if r in (3, 6):
            # Visual separator: insert a dummy row styled as divider
            table.add_section()

        cells: list[Text | str] = [Text(str(r + 1), style="bold yellow")]
        for c in range(9):
            val = board[r][c]
            if val == 0:
                cells.append(Text(".", style=EMPTY_STYLE))
            else:
                is_given = given[r][c] if given else False
                style = GIVEN_STYLE if is_given else FILLED_STYLE
                cells.append(Text(str(val), style=style))
        table.add_row(*cells)

    console.print(table)
