"""Load processed JSONL examples into dspy.Example objects for training/evaluation.

Usage
-----
    from gamesage.data.loader import load_examples, load_all

    trainset, devset = load_examples("chess")          # 80/20 split
    all_examples     = load_all()                      # chess + go + checkers combined
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Literal

import dspy

PROCESSED_DIR = Path(__file__).resolve().parents[2] / "gamesage_data" / "processed"

Game = Literal["chess", "go", "checkers"]

# Import rules summaries once (no adapter instantiation needed)
from gamesage.games.chess.adapter    import RULES_SUMMARY as _CHESS_RULES
from gamesage.games.go.adapter       import RULES_SUMMARY as _GO_RULES
from gamesage.games.checkers.adapter import RULES_SUMMARY as _CHECKERS_RULES

_RULES: dict[str, str] = {
    "chess":    _CHESS_RULES,
    "go":       _GO_RULES,
    "checkers": _CHECKERS_RULES,
}


def _raw_to_example(record: dict) -> dspy.Example:
    """Convert one processed JSONL record to a dspy.Example.

    Input fields  (fed to MoveAdvisor):
        game_name, rules_summary, board_state,
        legal_moves, move_history, player_skill_level

    Label field (used by the metric):
        gold_move
    """
    game = record["game"]
    return dspy.Example(
        game_name=_game_display_name(game),
        rules_summary=_RULES.get(game, ""),        # injected from adapter constant
        board_state=record["board_state_text"],
        legal_moves=record["legal_moves_text"],
        move_history="",
        player_skill_level=record["skill_level"],
        # --- label ---
        gold_move=record["gold_move"],
        # --- extra metadata (not fed to LLM, useful for analysis) ---
        themes=record.get("themes", []),
        source=record.get("source", ""),
        source_id=record.get("source_id", ""),
    ).with_inputs(
        "game_name", "rules_summary", "board_state",
        "legal_moves", "move_history", "player_skill_level",
    )


def _game_display_name(game: str) -> str:
    return {"chess": "Chess", "go": "Go", "checkers": "Checkers"}.get(game, game.title())


def _load_jsonl(path: Path) -> list[dict]:
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def load_examples(
    game: Game,
    *,
    seed: int = 42,
    train_ratio: float = 0.8,
) -> tuple[list[dspy.Example], list[dspy.Example]]:
    """Return (trainset, devset) for a single game.

    Parameters
    ----------
    game        : "chess", "go", or "checkers"
    seed        : random seed for reproducible splits
    train_ratio : fraction of data used for training (default 0.8)
    """
    path = PROCESSED_DIR / f"{game}_examples.jsonl"
    if not path.exists():
        raise FileNotFoundError(
            f"Processed data not found: {path}\n"
            "Run: python -m gamesage.data.process_raw"
        )

    records  = _load_jsonl(path)
    examples = [_raw_to_example(r) for r in records]

    rng = random.Random(seed)
    rng.shuffle(examples)

    split = int(len(examples) * train_ratio)
    return examples[:split], examples[split:]


def load_all(
    *,
    seed: int = 42,
    train_ratio: float = 0.8,
) -> tuple[list[dspy.Example], list[dspy.Example]]:
    """Return (trainset, devset) combining chess + go + checkers."""
    all_train: list[dspy.Example] = []
    all_dev:   list[dspy.Example] = []

    for game in ("chess", "go", "checkers"):
        path = PROCESSED_DIR / f"{game}_examples.jsonl"
        if not path.exists():
            continue
        train, dev = load_examples(game, seed=seed, train_ratio=train_ratio)  # type: ignore[arg-type]
        all_train.extend(train)
        all_dev.extend(dev)

    rng = random.Random(seed)
    rng.shuffle(all_train)
    rng.shuffle(all_dev)
    return all_train, all_dev


def load_by_skill(
    game: Game,
    skill_level: Literal["beginner", "intermediate", "advanced"],
    *,
    seed: int = 42,
    train_ratio: float = 0.8,
) -> tuple[list[dspy.Example], list[dspy.Example]]:
    """Return train/dev split filtered to a single skill level."""
    path = PROCESSED_DIR / f"{game}_examples.jsonl"
    if not path.exists():
        raise FileNotFoundError(f"Processed data not found: {path}")

    records  = [r for r in _load_jsonl(path) if r.get("skill_level") == skill_level]
    examples = [_raw_to_example(r) for r in records]

    rng = random.Random(seed)
    rng.shuffle(examples)
    split = int(len(examples) * train_ratio)
    return examples[:split], examples[split:]


def dataset_stats() -> None:
    """Print a summary of available processed examples."""
    for game in ("chess", "go", "checkers"):
        path = PROCESSED_DIR / f"{game}_examples.jsonl"
        if not path.exists():
            print(f"{game:10s}  — not found (run process_raw.py)")
            continue
        records = _load_jsonl(path)
        by_skill: dict[str, int] = {}
        for r in records:
            by_skill[r.get("skill_level", "unknown")] = (
                by_skill.get(r.get("skill_level", "unknown"), 0) + 1
            )
        skill_str = "  ".join(f"{k}: {v}" for k, v in sorted(by_skill.items()))
        print(f"{game:10s}  {len(records):4d} examples  [{skill_str}]")


if __name__ == "__main__":
    dataset_stats()
