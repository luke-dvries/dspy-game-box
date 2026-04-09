# GameSage Training Data Package

This package contains five JSONL data files for the **GameSage DSPy board game advisor** senior project. All files passed schema validation and are ready for use.

---

## File Summary

| File | Records | Size | Source |
|---|---|---|---|
| `chess_puzzles.jsonl` | 900 | 432 KB | Lichess Puzzle Database (CC0) |
| `go_positions.jsonl` | 200 | 119 KB | AEB 9x9 Go Games Archive |
| `checkers_positions.jsonl` | 1,332 | 786 KB | Bob Newell PDN Collections |
| `othello_positions.jsonl` | 200 | 97 KB | Thor/ffothello.org Archive (1977–2025) |
| `sudoku_techniques.jsonl` | 21 | 20 KB | SudokuWiki.org Strategy Catalog |
| **Total** | **2,653** | **1.45 MB** | |

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

---

### `go_positions.jsonl`
Each record is a board position from a professional 9×9 Go game, with the gold move played by the stronger player.

```json
{
  "game": "go",
  "skill_level": "intermediate|advanced",
  "board_size": 9,
  "board_state": "9x9 board as flat 81-char string (B=black, W=white, .=empty)",
  "sgf_sequence": "SGF move sequence up to this position",
  "gold_move": "Best move in SGF notation (e.g. ee)",
  "player_color": "B|W",
  "move_number": 15,
  "black_rank": "5k",
  "white_rank": "3d",
  "result": "B+3.5",
  "source": "aeb_9x9_collection",
  "source_id": "filename::game_index"
}
```

**Source:** 517 professional 9×9 games from the AEB Go database (all players 5-kyu and above)  
**Distribution:** 115 advanced, 85 intermediate

---

### `checkers_positions.jsonl`
Each record is a checkers puzzle position from curated PDN collections.

```json
{
  "game": "checkers",
  "skill_level": "beginner|intermediate|advanced",
  "board_fen": "FEN-like board representation",
  "side_to_move": "W|B",
  "result": "Expected outcome (e.g. White wins)",
  "themes": ["advanced_tactics", "king_endgame", ...],
  "event": "Puzzle collection name",
  "source": "bob_newell_pdn",
  "source_id": "collection::puzzle_id"
}
```

**Sources (4 PDN collections from bobnewell.net):**
- `beginner.pdn` — 58 beginner problems
- `intermediate.pdn` — 18 intermediate problems
- `tts/` (Tricks, Traps & Shots) — 1,256 advanced tactical puzzles

**Distribution:** 58 beginner, 18 intermediate, 1,256 advanced

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
  "source_id": "WTH_2011.pgn::Player1_vs_Player2"
}
```

**Source:** Thor/ffothello.org archive — 136,055 tournament games from 1977–2025  
**Distribution:** 83 advanced (World/National championships), 117 intermediate (Open/Online tournaments)  
**Phase balance:** 67 opening, 65 midgame, 68 endgame

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
| Pointing Pairs | Y-Wing | Almost Locked Sets |
| Box/Line Reduction | XYZ-Wing | 3D Medusa |

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

## Processing Notes

- **Chess:** Streamed from the Lichess puzzle CSV (zstandard compressed), stratified by rating into 3 equal tiers of 300.
- **Go:** Extracted from 517 SGF files; positions sampled at move 10, 20, and 30 per game; filtered to players rated 5-kyu and above.
- **Checkers:** Parsed from 4 PDN collections; FEN notation encodes piece positions using standard checkers square numbering.
- **Othello:** Replayed 136,000+ PGN games move-by-move using a full board simulation; sampled one position per game phase (opening/midgame/endgame).
- **Sudoku:** Hand-curated from SudokuWiki.org strategy pages with original descriptions, application conditions, and examples.
