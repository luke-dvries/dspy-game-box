#!/usr/bin/env python3
"""Convert raw gamesage_data JSONL files into training-ready examples.

For each raw example this script:
  1. Loads the board position into the appropriate game adapter
  2. Populates board_state_text and legal_moves_text
  3. Validates the gold_move is actually legal
  4. Writes cleaned records to gamesage_data/processed/<game>_examples.jsonl

Usage (from repo root, with venv active):
    python -m gamesage.data.process_raw
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR   = REPO_ROOT / "gamesage_data"
OUT_DIR   = RAW_DIR / "processed"
OUT_DIR.mkdir(exist_ok=True)

_COL_LETTERS = "ABCDEFGHJKLMNOPQRST"  # Go column letters — I is skipped


# ---------------------------------------------------------------------------
# Chess
# ---------------------------------------------------------------------------

def process_chess() -> None:
    from gamesage.games.chess.adapter import ChessAdapter

    in_path  = RAW_DIR / "chess_puzzles.jsonl"
    out_path = OUT_DIR / "chess_examples.jsonl"

    ok = skipped = 0
    with open(in_path) as fin, open(out_path, "w") as fout:
        for raw in fin:
            ex = json.loads(raw)
            adapter = ChessAdapter()
            try:
                adapter.load_fen(ex["fen"])
            except Exception:
                skipped += 1
                continue

            legal = adapter.get_legal_moves()
            gold  = ex["gold_move"].strip()

            if gold not in legal:
                skipped += 1
                continue

            ex["board_state_text"] = adapter.serialize_board()
            ex["legal_moves_text"] = ", ".join(legal)
            ok += 1
            fout.write(json.dumps(ex) + "\n")

    print(f"Chess:    {ok:4d} ok  |  {skipped:4d} skipped  →  {out_path.name}")


# ---------------------------------------------------------------------------
# Go helpers
# ---------------------------------------------------------------------------

def _sgf_coord_to_notation(sgf_col: str, sgf_row: str, board_size: int = 9) -> str | None:
    """Convert SGF letter pair to our Go notation (e.g. 'hb' → 'H8')."""
    col_idx = ord(sgf_col) - ord("a")
    row_num  = board_size - (ord(sgf_row) - ord("a"))
    if not (0 <= col_idx < board_size and 1 <= row_num <= board_size):
        return None
    return f"{_COL_LETTERS[col_idx]}{row_num}"


def _parse_sgf_moves(sgf: str) -> list[tuple[str, str]]:
    """Return list of (color, sgf_coord) from a SGF sequence string.

    Empty coord string means 'pass'.
    """
    return re.findall(r";([BW])\[([a-s]*)\]", sgf)


# ---------------------------------------------------------------------------
# Go
# ---------------------------------------------------------------------------

def process_go() -> None:
    from gamesage.games.go.adapter import GoAdapter

    in_path  = RAW_DIR / "go_positions.jsonl"
    out_path = OUT_DIR / "go_examples.jsonl"

    ok = skipped = 0
    with open(in_path) as fin, open(out_path, "w") as fout:
        for raw in fin:
            ex         = json.loads(raw)
            board_size = ex.get("board_size", 9)
            move_num   = ex["move_number"]   # 1-indexed: this is the gold move's position
            gold_move  = ex["gold_move"]

            moves = _parse_sgf_moves(ex["sgf_sequence"])

            if len(moves) < move_num:
                skipped += 1
                continue

            # Verify the move at position move_num matches the declared gold_move
            _, last_coord = moves[move_num - 1]
            if last_coord:
                converted = _sgf_coord_to_notation(last_coord[0], last_coord[1], board_size)
                if converted != gold_move:
                    skipped += 1
                    continue
            elif gold_move != "pass":
                skipped += 1
                continue

            # Replay all moves before the gold move
            adapter  = GoAdapter(board_size=board_size)
            replay_ok = True
            for _, coord in moves[: move_num - 1]:
                move = "pass" if not coord else _sgf_coord_to_notation(coord[0], coord[1], board_size)
                if move is None or not adapter.apply_move(move):
                    replay_ok = False
                    break

            if not replay_ok:
                skipped += 1
                continue

            legal = adapter.get_legal_moves()
            if gold_move not in legal:
                skipped += 1
                continue

            ex["board_state_text"] = adapter.serialize_board()
            ex["legal_moves_text"] = ", ".join(legal)
            ok += 1
            fout.write(json.dumps(ex) + "\n")

    print(f"Go:       {ok:4d} ok  |  {skipped:4d} skipped  →  {out_path.name}")


# ---------------------------------------------------------------------------
# Checkers helpers
# ---------------------------------------------------------------------------

def _pdn_square_to_rowcol(pdn_sq: int) -> tuple[int, int]:
    """Convert a PDN square number (1–32) to (row, col) 0-indexed.

    PDN layout (8x8, dark squares only, dark = (row+col) is odd):
      Row 0 (top)  — squares  1– 4 at cols 1,3,5,7  (even row → odd col)
      Row 1        — squares  5– 8 at cols 0,2,4,6  (odd  row → even col)
      ...
      Row 7 (bot)  — squares 29–32 at cols 0,2,4,6
    """
    idx    = int(pdn_sq) - 1       # 0-indexed (0–31)
    row    = idx // 4
    offset = idx % 4
    col    = offset * 2 + (1 if row % 2 == 0 else 0)
    return row, col


def _pdn_move_to_notation(pdn_move: str) -> str | None:
    """Convert a PDN move string like '27-23' or '11x4' to our engine notation.

    Simple move  '27-23'    → '6,5→5,4'
    Single jump  '11x4'     → '2,6→0,4'
    Multi-jump   '9x25x18'  → '2,1→6,1→...' (each square in path)

    Returns None if any square is unparseable.
    """
    try:
        parts   = re.split(r"[-x×]", pdn_move.strip())
        squares = [int(p) for p in parts]
        coords  = [_pdn_square_to_rowcol(sq) for sq in squares]
        return "→".join(f"{r},{c}" for r, c in coords)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Checkers
# ---------------------------------------------------------------------------

def process_checkers() -> None:
    from gamesage.games.checkers.adapter import CheckersAdapter
    from gamesage.games.checkers.engine  import RED, BLACK, RED_K, BLK_K, EMPTY

    in_path  = RAW_DIR / "checkers_positions.jsonl"
    out_path = OUT_DIR / "checkers_examples.jsonl"

    ok = skipped = 0
    with open(in_path) as fin, open(out_path, "w") as fout:
        for raw in fin:
            ex      = json.loads(raw)
            pdn_mv  = ex.get("gold_move_pdn")

            # Skip examples with no PDN move (pre-computed gold_move was wrong)
            if not pdn_mv:
                skipped += 1
                continue

            # Re-derive gold_move from gold_move_pdn using our correct formula
            gold = _pdn_move_to_notation(pdn_mv)
            if gold is None:
                skipped += 1
                continue

            # Build an 8×8 board from PDN piece lists
            try:
                board: list[list[str]] = [[EMPTY] * 8 for _ in range(8)]
                for sq in ex.get("white_pieces_pdn", []):
                    r, c = _pdn_square_to_rowcol(sq)
                    board[r][c] = RED        # PDN White ↔ engine Red (moves first)
                for sq in ex.get("white_kings_pdn", []):
                    r, c = _pdn_square_to_rowcol(sq)
                    board[r][c] = RED_K
                for sq in ex.get("black_pieces_pdn", []):
                    r, c = _pdn_square_to_rowcol(sq)
                    board[r][c] = BLACK
                for sq in ex.get("black_kings_pdn", []):
                    r, c = _pdn_square_to_rowcol(sq)
                    board[r][c] = BLK_K
            except Exception:
                skipped += 1
                continue

            # Inject board state directly into a fresh adapter
            adapter = CheckersAdapter()
            adapter._engine.board          = board
            adapter._engine.current_player = RED if ex.get("side_to_move") == "W" else BLACK
            adapter._engine._history       = []
            adapter._engine.move_count     = 0

            legal = adapter.get_legal_moves()
            if gold not in legal:
                skipped += 1
                continue

            ex["gold_move"]        = gold   # overwrite Manus's incorrect value
            ex["board_state_text"] = adapter.serialize_board()
            ex["legal_moves_text"] = ", ".join(legal)
            ok += 1
            fout.write(json.dumps(ex) + "\n")

    print(f"Checkers: {ok:4d} ok  |  {skipped:4d} skipped  →  {out_path.name}")


# ---------------------------------------------------------------------------
# Sudoku techniques (reference data — copy as-is)
# ---------------------------------------------------------------------------

def process_sudoku_techniques() -> None:
    src = RAW_DIR / "sudoku_techniques.jsonl"
    dst = OUT_DIR / "sudoku_techniques.jsonl"
    shutil.copy(src, dst)
    count = sum(1 for _ in open(src))
    print(f"Sudoku:   {count:4d} techniques copied  →  {dst.name}")


# ---------------------------------------------------------------------------
# Othello
# ---------------------------------------------------------------------------

def process_othello() -> None:
    from gamesage.games.othello.adapter import OthelloAdapter

    in_path  = RAW_DIR / "othello_positions.jsonl"
    out_path = OUT_DIR / "othello_examples.jsonl"

    ok = skipped = 0
    with open(in_path) as fin, open(out_path, "w") as fout:
        for raw in fin:
            ex = json.loads(raw)
            adapter = OthelloAdapter()
            try:
                adapter._engine.load_position(ex["board_state"], ex["player_to_move"])
            except Exception:
                skipped += 1
                continue

            legal = adapter.get_legal_moves()
            gold  = ex["gold_move"].strip().upper()

            if gold not in legal:
                skipped += 1
                continue

            ex["gold_move"]        = gold
            ex["board_state_text"] = adapter.serialize_board()
            ex["legal_moves_text"] = ", ".join(legal)
            ex["skill_level"]      = ex.get("skill_level", "intermediate")
            ok += 1
            fout.write(json.dumps(ex) + "\n")

    print(f"Othello:  {ok:4d} ok  |  {skipped:4d} skipped  →  {out_path.name}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    print("Processing raw data files...\n")
    process_chess()
    process_go()
    process_checkers()
    process_othello()
    process_sudoku_techniques()
    print(f"\nAll done. Processed files in: {OUT_DIR}")


if __name__ == "__main__":
    main()
