"""Rich-powered chess board renderer."""

from __future__ import annotations

import chess
from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich import box

LIGHT_SQ = "grey85"
DARK_SQ  = "grey30"
WHITE_PIECE_STYLE = "bold white"
BLACK_PIECE_STYLE = "bold bright_red"

UNICODE_PIECES = {
    (chess.KING,   True):  "♔",
    (chess.QUEEN,  True):  "♕",
    (chess.ROOK,   True):  "♖",
    (chess.BISHOP, True):  "♗",
    (chess.KNIGHT, True):  "♘",
    (chess.PAWN,   True):  "♙",
    (chess.KING,   False): "♚",
    (chess.QUEEN,  False): "♛",
    (chess.ROOK,   False): "♜",
    (chess.BISHOP, False): "♝",
    (chess.KNIGHT, False): "♞",
    (chess.PAWN,   False): "♟",
}


def render_board(board: chess.Board, console: Console | None = None) -> None:
    """Render *board* to the terminal using Rich colored cells."""
    if console is None:
        console = Console()

    table = Table(show_header=False, show_edge=True, box=box.SQUARE, padding=(0, 1))
    # rank label col + 8 file cols
    for _ in range(9):
        table.add_column(justify="center", min_width=2)

    for rank in range(7, -1, -1):
        cells: list[Text | str] = [Text(str(rank + 1), style="bold yellow")]
        for file in range(8):
            sq = chess.square(file, rank)
            is_light = (rank + file) % 2 == 1
            bg = LIGHT_SQ if is_light else DARK_SQ
            piece = board.piece_at(sq)
            if piece is None:
                symbol = " "
                style = f"on {bg}"
            else:
                symbol = UNICODE_PIECES.get((piece.piece_type, piece.color), "?")
                fg = WHITE_PIECE_STYLE if piece.color == chess.WHITE else BLACK_PIECE_STYLE
                style = f"{fg} on {bg}"
            cells.append(Text(symbol, style=style))
        table.add_row(*cells)

    # File labels row
    file_labels = [" "] + [Text(f"  {chr(ord('a') + f)}", style="bold yellow") for f in range(8)]
    table.add_row(*file_labels)

    console.print(table)


def render_move_list(moves: list[str], console: Console | None = None) -> None:
    """Print the move history in two-column pairs."""
    if console is None:
        console = Console()
    pairs = []
    for i in range(0, len(moves), 2):
        w = moves[i]
        b = moves[i + 1] if i + 1 < len(moves) else ""
        pairs.append(f"{i // 2 + 1:>3}. {w:<8} {b}")
    console.print("\n".join(pairs) or "(no moves yet)")
