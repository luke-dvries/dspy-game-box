"""Board → structured text serialization utilities.

Each game adapter calls ``serialize_board()`` on its own, but the functions
here provide shared helpers for formatting common patterns (grids, tables,
labelled rows/columns) that multiple adapters may reuse.
"""

from typing import Any


# ---------------------------------------------------------------------------
# Generic 2-D grid formatter
# ---------------------------------------------------------------------------

def grid_to_text(
    board: list[list[Any]],
    *,
    row_labels: list[str] | None = None,
    col_labels: list[str] | None = None,
    cell_width: int = 2,
    separator: str = " ",
    box_size: int | None = None,
    box_separator: str = " | ",
    row_box_separator: str = "-",
) -> str:
    """Render a 2-D list as a human-readable text grid.

    Parameters
    ----------
    board         : 2-D list of cell values (converted to str).
    row_labels    : Labels for each row (printed on the left).
    col_labels    : Labels for each column (printed on top).
    cell_width    : Minimum width for each cell (right-padded).
    separator     : Separator between cells within the same box.
    box_size      : If given, draw box-separator lines every N rows/cols.
    box_separator : Separator between boxes on the same row.
    row_box_separator : Character used to draw horizontal box-divider lines.
    """
    rows = len(board)
    cols = len(board[0]) if rows else 0

    # Column header
    lines: list[str] = []
    if col_labels:
        prefix = " " * (len(row_labels[0]) + 1) if row_labels else ""
        col_row_parts = []
        for c, label in enumerate(col_labels):
            col_row_parts.append(label.center(cell_width))
            if box_size and (c + 1) % box_size == 0 and c + 1 < cols:
                col_row_parts.append(box_separator)
        lines.append(prefix + separator.join(col_row_parts))

    for r, row in enumerate(board):
        # Horizontal box separator
        if box_size and r > 0 and r % box_size == 0:
            row_width = len(lines[-1])
            lines.append(row_box_separator * row_width)

        parts: list[str] = []
        for c, cell in enumerate(row):
            parts.append(str(cell).center(cell_width))
            if box_size and (c + 1) % box_size == 0 and c + 1 < cols:
                parts.append(box_separator)

        row_str = separator.join(parts)
        if row_labels:
            row_str = f"{row_labels[r]} {row_str}"
        lines.append(row_str)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Key–value block
# ---------------------------------------------------------------------------

def kv_block(data: dict[str, Any], title: str = "") -> str:
    """Format a dict as a labelled block of key: value lines."""
    lines: list[str] = []
    if title:
        lines.append(f"=== {title} ===")
    for k, v in data.items():
        lines.append(f"  {k}: {v}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Move-history formatter
# ---------------------------------------------------------------------------

def format_move_history(moves: list[str], max_recent: int = 10) -> str:
    """Return a compact move-history string for injection into prompts."""
    recent = moves[-max_recent:]
    if not recent:
        return "(no moves yet)"
    numbered = [f"{i + 1}. {m}" for i, m in enumerate(recent, start=len(moves) - len(recent))]
    return "  ".join(numbered)
