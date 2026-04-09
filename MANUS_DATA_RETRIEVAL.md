# GameSage — Data Retrieval Task for Manus

## What This Project Is

GameSage is a DSPy-powered board game advisor (Chess, Checkers, Go, Sudoku).
It uses a DSPy `ChainOfThought` module called `GameSageAdvisor` that, given a
board state, outputs:
- `recommended_move` — the best move in the game's notation
- `explanation` — plain-English explanation for the player
- `strategic_reasoning` — internal step-by-step analysis
- `alternative_moves` — 2–3 other viable moves
- `key_concepts` — strategic themes demonstrated (e.g. "fork", "pin", "center control")

To **optimize this module with DSPy**, we need labeled training examples.
Each example must contain the *inputs* to the model plus a **gold `recommended_move`**
(the objectively correct move from an authoritative source).

---

## Data Needed Per Game

### 1. CHESS (highest priority)

**Source: Lichess Open Puzzle Database**
- URL: https://database.lichess.org/#puzzles
- File: `lichess_db_puzzle.csv.zst` (the latest monthly export, ~300 MB compressed)
- License: Creative Commons CC0 (public domain — free to use)

**CSV columns** (already documented by Lichess):
```
PuzzleId, FEN, Moves, Rating, RatingDeviation, Popularity, NbPlays, Themes, GameUrl, OpeningTags
```

**What we care about:**
| Column | How we use it |
|--------|---------------|
| `FEN` | Board position — load into `ChessAdapter.load_fen()` to get `board_state` and `legal_moves` |
| `Moves` | Space-separated UCI moves; the **first move** is the opponent's (already played), the **second move** is the correct answer (our gold label for `recommended_move`) |
| `Themes` | Space-separated tags — maps directly to `key_concepts` (e.g. `fork`, `pin`, `mateIn1`, `endgame`) |
| `Rating` | Use to stratify by skill level: ≤1200=beginner, 1200–1800=intermediate, ≥1800=advanced |
| `OpeningTags` | Optional context for opening-phase puzzles |

**How `Moves` works:**
The FEN is the position BEFORE the opponent's move. The `Moves` field is in UCI notation
(e.g., `e2e4 d7d5`). To get the puzzle position:
1. Load the FEN into a `chess.Board`
2. Apply the **first** move in `Moves` (the opponent's move that creates the puzzle)
3. The correct answer is the **second** move in `Moves` — convert from UCI to SAN for our system

**How many examples to retrieve:**
- Aim for ~500–1000 puzzles, stratified:
  - ~300 beginner (Rating ≤ 1200), themes including: `mateIn1`, `fork`, `hangingPiece`, `endgame`
  - ~300 intermediate (1200–1800), themes including: `pin`, `skewer`, `discoveredAttack`, `mateIn2`
  - ~300 advanced (≥1800), themes including: `crushing`, `quietMove`, `zugzwang`, `sacrifice`

**Do NOT download all 4 million rows.** Filter on retrieval or sample after.

---

### 2. CHECKERS

**No authoritative public puzzle database exists for checkers.**

Instead, retrieve the following reference material so we can generate scenarios
programmatically:

**A. Checkerboard endgame positions (PDN format)**
- Search for: "checkers endgame database PDN" or "draughts problem collection"
- Target sites: `CheckerBoard.com`, `EdwardK.com` (Jim Loy checkers problems), or
  any site hosting `.pdn` puzzle files
- PDN (Portable Draughts Notation) is the checkers equivalent of PGN
- We want positions with known forced wins (king vs. pieces, 2-vs-1 endgames)

**B. Checkers strategy articles to extract positions from:**
- Key concepts we need scenarios for: mandatory captures, multi-jump chains, king
  promotion, corner traps, "the bridge" endgame technique
- Retrieve any plain-text or HTML articles describing these with board diagrams

**C. Fallback — self-play generation:**
If no structured data is found, retrieve documentation on how the
**Chinook** checkers engine works (it solved checkers in 2007).
Chinook's opening book is public. Retrieve any available opening book data.

---

### 3. GO

**Source: KGS Game Archive (SGF files)**
- URL: https://www.gokgs.com/archives.jsp
- Download 9x9 game SGF files (our engine defaults to 9x9)
- Target: games rated 5-kyu and above (stronger players = better moves)
- We need ~200 SGF game files

**What we extract from SGF:**
- Board positions at each move (can reconstruct with `sgfmill`, which is already a
  project dependency)
- The move played (gold label for `recommended_move` in Go notation like "D5", "Q16")
- The player's rank (maps to skill level)

**Alternative source: GoGoD (Go Games on DVD) free samples**
- Search for "GoGoD SGF free sample" — they publish free batches of professional games

**Key concepts for Go we need scenarios covering:**
- Joseki (corner sequences) — retrieve a joseki reference list
- Atari (capturing threats)
- Influence vs. territory
- Ko fights
- Life and death (two eyes)

---

### 4. SUDOKU

**Sudoku does NOT need an external dataset.**

The `SudokuEngine` already generates valid puzzles internally and knows the full
solution. The gold `recommended_move` for any cell is simply the correct digit from
`_solution[row][col]`.

However, retrieve the following to enrich `key_concepts` explanations:

**Sudoku solving technique catalog:**
- Retrieve a comprehensive list of named Sudoku techniques with definitions:
  - Naked Single, Hidden Single
  - Naked Pair / Triple / Quad
  - Hidden Pair / Triple
  - Pointing Pairs, Box/Line Reduction
  - X-Wing, Swordfish
  - Simple Coloring
- Good sources: https://www.sudokuwiki.org/Strategy_Families or similar strategy pages
- We need the **name** of each technique + a **plain-English description** of when it applies

---

## Output Format Requested from Manus

For each game, produce a **JSON Lines file** (`.jsonl`) where each line is one
training example in this structure:

```jsonc
// Chess example
{
  "game": "chess",
  "skill_level": "beginner",           // "beginner" | "intermediate" | "advanced"
  "fen": "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4",
  "board_state_text": "...",           // leave blank — we will generate this with ChessAdapter
  "legal_moves_text": "...",           // leave blank — we will generate this with ChessAdapter
  "gold_move": "Ng5",                  // the correct move in SAN notation
  "gold_move_uci": "f3g5",            // original UCI for verification
  "themes": ["fork", "attackingF7"],   // from Lichess Themes column
  "source": "lichess_puzzle",
  "source_id": "00sHx"                 // Lichess PuzzleId
}
```

```jsonc
// Go example
{
  "game": "go",
  "skill_level": "intermediate",
  "board_size": 9,
  "sgf_sequence": "(;GM[1]FF[4]SZ[9]...)",  // SGF up to the position of interest
  "move_number": 14,
  "gold_move": "D5",                          // in our notation (col letter + row number)
  "gold_move_sgf": "dd",                      // original SGF coordinates
  "source": "kgs_archive",
  "source_id": "game_filename.sgf"
}
```

```jsonc
// Checkers example
{
  "game": "checkers",
  "skill_level": "intermediate",
  "board_fen": "...",              // PDN or a custom board string if no standard exists
  "position_description": "...",  // human description of the position if no machine format
  "gold_move": "2,3→3,4",        // our notation: "from_row,from_col→to_row,to_col"
  "themes": ["mandatory_capture", "multi_jump"],
  "source": "pdn_collection",
  "source_id": "problem_042"
}
```

```jsonc
// Sudoku technique reference (separate file: sudoku_techniques.jsonl)
{
  "technique_name": "Naked Single",
  "difficulty": "beginner",
  "description": "A cell where only one digit is possible given the constraints of its row, column, and box.",
  "when_to_apply": "When all other 8 digits appear in the same row, column, or 3x3 box as an empty cell.",
  "example": "optional"
}
```

---

## File Names to Deliver

```
data/
├── chess_puzzles.jsonl         # ~900 chess puzzles
├── go_positions.jsonl          # ~200 go positions
├── checkers_positions.jsonl    # however many can be found
└── sudoku_techniques.jsonl     # complete technique catalog
```

---

## Important Technical Notes

### Chess move conversion (UCI → SAN)
The Lichess data is in UCI (e.g. `f3g5`). Our system uses SAN (e.g. `Ng5`).
To convert: apply the FEN + opponent's first move to a `chess.Board`, then convert
the answer move from UCI to SAN using `board.san(chess.Move.from_uci(uci_str))`.

**If Manus cannot run Python**, record both the raw UCI move AND the FEN so we can
convert locally. Do not guess SAN — leave `gold_move` as the UCI string and set
`gold_move_uci` to the same value; we will convert.

### Chess skill level mapping from puzzle rating
```
Rating < 1200          → skill_level = "beginner"
1200 <= Rating < 1800  → skill_level = "intermediate"
Rating >= 1800         → skill_level = "advanced"
```

### Go coordinate conversion (SGF → our notation)
SGF uses letter pairs from top-left: `aa` = top-left, `ia` = 9th column, top row.
Our system uses `A1` = bottom-left (Go convention), with I skipped.
Column mapping: `a→A, b→B, c→C, d→D, e→E, f→F, g→G, h→H, i→J` (i skips to J)
Row mapping: SGF row `a` = our row 9 (top), SGF row `i` = our row 1 (bottom) for 9x9

### Checkers notation
Our engine uses: `"from_row,from_col→to_row,to_col"` (0-indexed, `→` separator).
PDN uses numeric square labels (1–32). If retrieving PDN, record the PDN square numbers
and we will convert locally.

---

## What NOT to Retrieve

- Do not retrieve Stockfish binaries or engine executables
- Do not retrieve copyrighted chess databases (e.g. ChessBase)
- Do not retrieve entire Lichess game databases (only the puzzle CSV)
- Do not retrieve full GoGoD paid collections
- Keep checkers and Go data to free/open sources only
