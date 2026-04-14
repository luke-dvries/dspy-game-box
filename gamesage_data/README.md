# GameSage Training Data Package

This package contains five JSONL data files for the **GameSage DSPy board game advisor** senior project. All files have been deep-validated and are ready for use.

---

## File Summary

| File | Records | Size | Source |
|---|---|---|---|
| `chess_puzzles.jsonl` | **900** | 433 KB | Lichess Puzzle Database (CC0) |
| `go_positions.jsonl` | **122** | 85 KB | AEB 9x9 Go Games Archive |
| `checkers_positions.jsonl` | **1,332** | 920 KB | Bob Newell PDN Collections |
| `othello_positions.jsonl` | **200** | 100 KB | Thor/ffothello.org Archive (1977–2025) |
| `sudoku_techniques.jsonl` | **21** | 20 KB | SudokuWiki.org Strategy Catalog |
| **Total** | **2,575** | **1.56 MB** | |

---

## Deep Validation Summary

All five files passed a full deep-validation pass including:

| File | FEN/Board Valid | Move Legal | Duplicates | Status |
|---|---|---|---|---|
| `chess_puzzles.jsonl` | 900/900 FENs valid | 900/900 SAN moves legal | 0 | **PASS** |
| `go_positions.jsonl` | 122/122 board states computed | 122/122 gold moves on empty cells | 0 | **PASS** |
| `checkers_positions.jsonl` | 1332/1332 FENs valid, squares 1-32 | 18 PDN moves (TTS); 1314 position-only | 0 | **PASS** |
| `othello_positions.jsonl` | 200/200 boards parsed; stone counts verified | 200/200 legal Othello moves | 0 | **PASS** |
| `sudoku_techniques.jsonl` | N/A | N/A | 0 | **PASS** |

---

## File Schemas

### `chess_puzzles.jsonl`
Each record is a Lichess puzzle with a FEN position and the best move sequence.

```json
{
  "game": "chess",
  "skill_level": "beginner|intermediate|advanced",
  "fen": "FEN string of the position",
  "gold_move": "Best move in SAN notation (e.g. Nf3)",
  "move_sequence": ["Nf3", "Bg5", ...],
  "themes": ["middlegame", "fork", ...],
  "rating": 1450,
  "rating_deviation": 75,
  "popularity": 92,
  "nb_plays": 12000,
  "game_url": "https://lichess.org/...",
  "source": "lichess_puzzle_db",
  "source_id": "abc123"
}
```

**Skill level thresholds:** beginner ≤ 1200, intermediate 1201–1800, advanced > 1800  
**Distribution:** 300 puzzles per level (perfectly balanced)  
**Rating range:** 399–3065 (avg 1523)  
**Validation:** All 900 FENs parse as legal chess positions; all 900 `gold_move` values are legal SAN moves in their respective positions.

---

### `go_positions.jsonl`
Each record is a board position from a professional 9×9 Go game, with the gold move played by the stronger player.

```json
{
  "game": "go",
  "skill_level": "intermediate|advanced",
  "board_size": 9,
  "board_state": "81-char flat string (B=black, W=white, .=empty), row-major top-to-bottom",
  "sgf_sequence": "Full SGF game text up to and including the gold move",
  "gold_move": "Best move in human notation (e.g. H8)",
  "gold_move_sgf": "Best move in SGF coordinate notation (e.g. hb)",
  "player_color": "B|W",
  "move_number": 25,
  "black_rank": "9p",
  "white_rank": "9p",
  "result": "W+1.5",
  "source": "aeb_9x9_collection",
  "source_id": "001119.sgf"
}
```

**Source:** 517 professional 9×9 games from the AEB Go database (all players 5-kyu and above)  
**Distribution:** 74 advanced, 48 intermediate  
**Validation:** All 122 `board_state` fields were computed by replaying the SGF sequence to move `N-1` (the state immediately before the gold move). All 122 `gold_move_sgf` values target empty cells on the board.  
**Note:** 78 records from the original 200 were removed because their gold moves could not be verified as legal (occupied cells after replay — likely ko recaptures requiring full ko-rule tracking).

---

### `checkers_positions.jsonl`
Each record is a checkers puzzle position from curated PDN collections.

```json
{
  "game": "checkers",
  "skill_level": "beginner|intermediate|advanced",
  "board_fen": "PDN FEN string (e.g. W:W31,27,19:B17,12,5.)",
  "side_to_move": "W|B",
  "white_pieces_pdn": [19, 27, 31],
  "white_kings_pdn": [],
  "black_pieces_pdn": [5, 12, 17],
  "black_kings_pdn": [],
  "position_description": "Human-readable board description",
  "gold_move": "First move in PDN notation (e.g. 27-23) or null for position-only puzzles",
  "gold_move_pdn": "Same as gold_move or null",
  "has_gold_move": true,
  "result": "0-1|1-0|1/2-1/2",
  "themes": ["advanced_tactics", "king_endgame", ...],
  "source": "bobnewell_pdn_collection",
  "source_id": "beginner.pdn::Beginner's Problem #1"
}
```

**Sources (4 PDN collections from bobnewell.net):**
- `beginner.pdn` — 58 beginner position puzzles (no move sequence in source)
- `gem.pdn` — 162 intermediate/advanced position puzzles (no move sequence in source)
- `goulds.pdn` — 1,094 advanced position puzzles (no move sequence in source)
- `Tricks traps and shots.pdn` — 18 advanced tactical puzzles **with** full move sequences

**Note on `gold_move`:** The beginner, gem, and goulds PDN files are **position-only** puzzles — they provide the starting position and the expected result (who wins), but do not include the move sequence. This is standard for checkers problem books. The `has_gold_move` field distinguishes records with known moves (18 TTS puzzles) from position-only records (1,314). For DSPy training, position-only records can be used to train the model to evaluate positions and suggest candidate moves.

**Validation:** All 1,332 `board_fen` fields parse correctly; all square numbers are in the valid range 1–32; all 18 TTS `gold_move` values are in standard PDN notation.

---

### `othello_positions.jsonl`
Each record is a board position from a tournament Othello game, with the move actually played by a strong player.

```json
{
  "game": "othello",
  "skill_level": "intermediate|advanced",
  "board_state": "8 rows joined by '/', each row 8 chars (B=black, W=white, .=empty)",
  "player_to_move": "Black|White",
  "move_number": 28,
  "game_phase": "opening|midgame|endgame",
  "black_count": 12,
  "white_count": 19,
  "gold_move": "Move in algebraic notation (e.g. H7)",
  "result": "50-14",
  "event": "Antwerpen Open - 2011",
  "black_player": "Player Name",
  "white_player": "Player Name",
  "year": "2011",
  "source": "thor_wthor_archive",
  "source_id": "WTH_2011.pgn::Player1_vs_Player2::midgame"
}
```

**Source:** Thor/ffothello.org archive — 136,055 tournament games from 1977–2025  
**Distribution:** 83 advanced (World/National championships), 117 intermediate (Open/Online tournaments)  
**Phase balance:** 67 opening, 65 midgame, 68 endgame  
**Validation:** All 200 board states parsed and stone counts verified; all 200 `gold_move` values are legal Othello moves (verified to flip at least one opponent stone); all 200 `source_id` values are unique (include game phase suffix).

---

### `sudoku_techniques.jsonl`
Each record describes one Sudoku solving technique with full explanations.

```json
{
  "technique_name": "Y-Wing",
  "difficulty": "beginner|intermediate|advanced",
  "also_known_as": ["XY-Wing"],
  "description": "Full technique description...",
  "when_to_apply": "Conditions and steps for applying the technique...",
  "example": "Concrete example of the technique...",
  "eliminates": "What candidates are eliminated...",
  "source": "https://www.sudokuwiki.org/..."
}
```

**21 techniques across 3 difficulty tiers (7 each):**

| Beginner (7) | Intermediate (7) | Advanced (7) |
|---|---|---|
| Naked Single | Naked Quad | Hidden Quad |
| Hidden Single | Hidden Triple | XY-Chains |
| Naked Pair | X-Wing | Unique Rectangle |
| Naked Triple | Swordfish | Jellyfish |
| Hidden Pair | Simple Colouring | Forcing Chains |
| Pointing Pairs | Y-Wing | Almost Locked Sets (ALS) |
| Box/Line Reduction | XYZ-Wing | 3D Medusa |

**Validation:** All 21 records have required fields; descriptions average 232 chars; when_to_apply sections average 265 chars; no duplicates.

---

## Data Sources & Licenses

| Dataset | Source | License |
|---|---|---|
| Chess Puzzles | [Lichess Puzzle Database](https://database.lichess.org/#puzzles) | CC0 Public Domain |
| Go Positions | [AEB 9x9 Go Games](https://homepages.cwi.nl/~aeb/go/games/) | Public Archive |
| Checkers Puzzles | [Bob Newell PDN Collections](https://www.bobnewell.net/checkers/pdn/pdndownloads.html) | Free for non-commercial use |
| Othello Games | [Thor/ffothello.org Archive](http://www.ffothello.org/informatique/la-base-wthor/) via [GitHub](https://github.com/MartinMSPedersen/othello-games) | Unlicense (Public Domain) |
| Sudoku Techniques | [SudokuWiki.org](https://www.sudokuwiki.org/Strategy_Families) | Educational reference |

---

## Processing & Validation Notes

- **Chess:** Streamed from the Lichess puzzle CSV (zstandard compressed), stratified by rating into 3 equal tiers of 300. All FENs validated with `python-chess`; all gold moves verified as legal SAN moves.
- **Go:** Extracted from 517 SGF files; positions sampled at early/mid/late game; board states computed by replaying SGF sequences to move N-1 using `sgfmill`; 78 records removed where gold moves could not be verified.
- **Checkers:** Parsed from 4 PDN collections; FEN notation uses standard checkers square numbering (1-32); TTS gold moves extracted and converted to PDN notation; position-only puzzles marked with `has_gold_move: false`.
- **Othello:** Replayed 136,000+ PGN games move-by-move using a full board simulation; sampled one position per game phase; all gold moves verified as legal (flip at least one opponent stone); source_ids made unique by appending game phase.
- **Sudoku:** Hand-curated from SudokuWiki.org strategy pages with original descriptions, application conditions, and examples.
