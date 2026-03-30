# GameSage

**AI-powered board game advisor** — play and learn Chess, Checkers, Go, and Sudoku
with move recommendations and explainability powered by [DSPy](https://github.com/stanfordnlp/dspy).

---

## Features

| Game     | Engine                          | Explainability focus                             |
|----------|---------------------------------|--------------------------------------------------|
| Chess    | `python-chess` (full rules)     | Openings, tactics, material balance              |
| Checkers | Custom 8×8 engine               | Forced captures, king strategy, multi-jumps      |
| Go       | Custom 9–19×19 engine           | Influence, liberties, joseki, sente/gote         |
| Sudoku   | Custom generator + solver       | Naked singles, hidden pairs, box/row elimination |

---

## Installation

```bash
# Create a virtual environment (recommended)
python -m venv .venv && source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"
```

### Ollama (default backend)

```bash
# Install Ollama: https://ollama.com/download
ollama pull llama3.1    # or: ollama pull qwen2.5 / mistral
```

---

## Running GameSage

### Interactive menu

```bash
python -m gamesage.main
```

### Directly start a game

```bash
# Chess, beginner, play mode
python -m gamesage.main --game chess --skill beginner --mode play

# Go 13x13, coach mode
python -m gamesage.main --game go --go-size 13 --mode coach

# Sudoku hard, puzzle mode
python -m gamesage.main --game sudoku --sudoku-difficulty hard --mode puzzle

# Chess from a specific FEN, analysis mode
python -m gamesage.main --game chess --mode analyze \
  --fen "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
```

### Dry-run (no API calls)

```bash
python -m gamesage.main --dry-run --game chess
```

---

## Game Modes

| Mode      | Description                                                           |
|-----------|-----------------------------------------------------------------------|
| `play`    | Human vs AI — the LLM plays one side and explains its moves           |
| `coach`   | Human plays both sides; AI comments after every move                  |
| `analyze` | Input/paste a board state for full AI position analysis               |
| `puzzle`  | Step-by-step AI guidance (Chess and Sudoku)                           |

### In-game commands

| Command   | Effect                                              |
|-----------|-----------------------------------------------------|
| `hint`    | Ask for a move recommendation without playing it    |
| `explain` | Explain the last move that was played               |
| `eval`    | Evaluate the current board position                 |
| `moves`   | List all legal moves                                |
| `undo`    | Undo the last move                                  |
| `quit`    | End the session (offers optional rating prompt)     |

---

## Swapping LLM Backends

Edit `config.py` or set environment variables:

```bash
# Ollama — local, free, no API key (default)
export GAMESAGE_LLM_BACKEND=ollama
export GAMESAGE_OLLAMA_MODEL=llama3.1      # or qwen2.5, mistral, llama3.3, etc.
export GAMESAGE_OLLAMA_BASE_URL=http://localhost:11434

# OpenAI — GPT-4o recommended
export GAMESAGE_LLM_BACKEND=openai
export GAMESAGE_OPENAI_MODEL=gpt-4o        # or gpt-4o-mini for cheaper runs
export OPENAI_API_KEY=sk-...

# Anthropic — Claude
export GAMESAGE_LLM_BACKEND=anthropic
export GAMESAGE_ANTHROPIC_MODEL=claude-sonnet-4-6   # or claude-haiku-4-5-20251001
export ANTHROPIC_API_KEY=sk-ant-...

# Google Gemini
export GAMESAGE_LLM_BACKEND=gemini
export GAMESAGE_GEMINI_MODEL=gemini/gemini-2.0-flash   # or gemini/gemini-2.5-pro
export GEMINI_API_KEY=AIza...
```

### Model recommendations by use case

| Goal | Recommended model |
|---|---|
| Free / offline | `ollama` + `llama3.1` or `qwen2.5` |
| Best explanations | `anthropic` + `claude-sonnet-4-6` |
| Best reasoning / chess | `openai` + `gpt-4o` |
| Fast & cheap cloud | `gemini` + `gemini-2.0-flash` |
| Research paper (consistent) | Pin a versioned model tag, e.g. `llama3.1:8b` |

---

## Research Logging

Every session is automatically logged to `gamesage_research.db` (SQLite).

### Schema

#### `sessions`
| Column       | Type | Description                         |
|--------------|------|-------------------------------------|
| id           | TEXT | UUID primary key                    |
| game         | TEXT | Game name                           |
| skill_level  | TEXT | beginner / intermediate / advanced  |
| mode         | TEXT | play / coach / analyze / puzzle     |
| started_at   | TEXT | ISO-8601 UTC timestamp              |
| ended_at     | TEXT | ISO-8601 UTC timestamp (nullable)   |

#### `moves`
| Column                | Type    | Description                                  |
|-----------------------|---------|----------------------------------------------|
| id                    | INTEGER | Auto-increment PK                            |
| session_id            | TEXT    | FK → sessions.id                             |
| move_number           | INTEGER | Sequential move number in session            |
| player                | TEXT    | Who moved (White/Black/Red/Solver etc.)      |
| move_played           | TEXT    | The actual move in game notation             |
| board_state_before    | TEXT    | Serialized board before the move             |
| llm_recommended_move  | TEXT    | What the LLM suggested (nullable)            |
| llm_explanation       | TEXT    | LLM's plain-English explanation (nullable)   |
| llm_reasoning         | TEXT    | LLM's internal reasoning chain (nullable)    |
| followed_advice       | INTEGER | 1 if human played the recommended move       |
| time_taken_seconds    | REAL    | Wall-clock time for the move                 |

#### `ratings`
| Column                  | Type    | Description                     |
|-------------------------|---------|---------------------------------|
| id                      | INTEGER | Auto-increment PK               |
| session_id              | TEXT    | FK → sessions.id                |
| move_id                 | INTEGER | FK → moves.id (or -1 for game)  |
| explanation_clarity     | INTEGER | 1–5 user rating                 |
| explanation_helpfulness | INTEGER | 1–5 user rating                 |
| comments                | TEXT    | Free-form user comments         |

### Disabling logging

```bash
export GAMESAGE_RESEARCH_LOGGING=false
```

### Querying the database

```bash
sqlite3 gamesage_research.db \
  "SELECT game, skill_level, COUNT(*) as sessions FROM sessions GROUP BY game, skill_level;"
```

---

## Running Tests

```bash
pytest gamesage/tests/ -v
```

Tests cover board serialization and legal move generation for every game engine
**without touching the LLM**.

---

## Project Structure

```
gamesage/
├── main.py              Entry point and CLI argument parsing
├── config.py            LLM backend selection, DSPy configuration
├── core/
│   ├── adapter.py       Abstract GameAdapter base class
│   ├── serializer.py    Shared board-to-text utilities
│   └── explainer.py     DSPy signatures and modules (MoveAdvisor, GameSageCoach)
├── games/
│   ├── chess/           python-chess wrapper, Rich renderer
│   ├── checkers/        Custom 8×8 engine, renderer
│   ├── go/              Custom Go engine, renderer
│   └── sudoku/          Puzzle generator + validator, renderer
├── ui/
│   └── cli.py           Rich-powered interactive CLI
├── research/
│   └── logger.py        SQLite research logger
└── tests/               Pytest unit tests (one per game + logger)
```

---

## Architecture Notes

* **LLM vs engine separation**: The LLM *never* validates moves — that is always done by the game engine. The LLM only produces reasoning and natural-language explanations.
* **Illegal-move retry**: If the LLM suggests an illegal move, `GameSageAdvisor` retries up to 3 times with negative feedback, then falls back to a random legal move.
* **DSPy `ChainOfThought`**: `GameSageAdvisor` uses `dspy.ChainOfThought(MoveAdvisor)` to encourage step-by-step strategic reasoning before committing to a move recommendation.
* **Modular adapters**: Add a new game by implementing the 7-method `GameAdapter` ABC and registering it in `main.py`.
