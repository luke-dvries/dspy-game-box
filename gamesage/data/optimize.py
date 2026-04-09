#!/usr/bin/env python3
"""DSPy optimization pipeline for GameSageAdvisor.

Runs BootstrapFewShot (fast, good first pass) or MIPROv2 (slower, stronger)
on the chess puzzle dataset, evaluates before/after on a held-out dev set,
then saves the compiled module.

Usage
-----
    # Fast run with BootstrapFewShot (default):
    python -m gamesage.data.optimize

    # Stronger optimization with MIPROv2:
    python -m gamesage.data.optimize --optimizer mipro

    # Specific game, train on all skill levels:
    python -m gamesage.data.optimize --game go --optimizer bootstrap

    # Dry run (mock LLM, no API calls — confirms pipeline works):
    python -m gamesage.data.optimize --dry-run

Environment variables
---------------------
    GAMESAGE_LLM_BACKEND, GAMESAGE_OLLAMA_MODEL, etc. — same as main app.
    See config.py for full list.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO_ROOT    = Path(__file__).resolve().parents[2]
COMPILED_DIR = REPO_ROOT / "gamesage_data" / "compiled"
COMPILED_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="gamesage.data.optimize",
        description="Optimize GameSageAdvisor with DSPy",
    )
    p.add_argument(
        "--game",
        choices=["chess", "go", "checkers", "all"],
        default="chess",
        help="Which game's dataset to use (default: chess)",
    )
    p.add_argument(
        "--optimizer",
        choices=["bootstrap", "mipro"],
        default="bootstrap",
        help="DSPy optimizer to use (default: bootstrap)",
    )
    p.add_argument(
        "--train-size",
        type=int,
        default=200,
        help="Max training examples to use (default: 200)",
    )
    p.add_argument(
        "--dev-size",
        type=int,
        default=100,
        help="Max dev examples for evaluation (default: 100)",
    )
    p.add_argument(
        "--max-demos",
        type=int,
        default=4,
        help="Max bootstrapped demonstrations (BootstrapFewShot, default: 4)",
    )
    p.add_argument(
        "--mipro-trials",
        type=int,
        default=20,
        help="Number of MIPROv2 trials (default: 20)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Use mock LLM — no API calls (validates pipeline only)",
    )
    p.add_argument(
        "--threads",
        type=int,
        default=4,
        help="Parallel threads for evaluation (default: 4)",
    )
    return p


# ---------------------------------------------------------------------------
# Metric wrapper (DSPy 3.x expects (example, prediction, trace) -> float)
# ---------------------------------------------------------------------------

def _make_metric(dry_run: bool):
    """Return the appropriate metric.

    In dry-run mode we use move_in_legal because the stub LLM always returns
    'a1' which won't match any gold_move but may not be legal either — this
    at least exercises the full evaluation path without false failures.
    """
    from gamesage.data.metric import move_match, move_in_legal
    return move_in_legal if dry_run else move_match


# ---------------------------------------------------------------------------
# Dataset loading
# ---------------------------------------------------------------------------

def _load_dataset(game: str, train_size: int, dev_size: int):
    from gamesage.data.loader import load_examples, load_all

    if game == "all":
        trainset, devset = load_all()
    else:
        trainset, devset = load_examples(game)  # type: ignore[arg-type]

    trainset = trainset[:train_size]
    devset   = devset[:dev_size]

    print(f"  Training examples : {len(trainset)}")
    print(f"  Dev examples      : {len(devset)}")
    return trainset, devset


# ---------------------------------------------------------------------------
# Baseline evaluation
# ---------------------------------------------------------------------------

def _evaluate(module, devset, metric, threads: int, label: str) -> float:
    import dspy
    evaluator = dspy.Evaluate(
        devset=devset,
        metric=metric,
        num_threads=threads,
        display_progress=True,
        display_table=0,
    )
    result = evaluator(module)
    score  = float(result.score)
    print(f"  {label}: {score:.1f}%")
    return score


# ---------------------------------------------------------------------------
# Optimizers
# ---------------------------------------------------------------------------

def _run_bootstrap(module, trainset, metric, max_demos: int):
    import dspy
    print(f"\nRunning BootstrapFewShot (max_demos={max_demos})...")
    optimizer = dspy.BootstrapFewShot(
        metric=metric,
        max_bootstrapped_demos=max_demos,
        max_labeled_demos=max_demos * 4,
    )
    return optimizer.compile(module, trainset=trainset)


def _run_mipro(module, trainset, metric, num_trials: int, threads: int):
    import dspy
    print(f"\nRunning MIPROv2 (num_trials={num_trials})...")
    optimizer = dspy.MIPROv2(
        metric=metric,
        auto="medium",
        num_threads=threads,
        verbose=True,
    )
    return optimizer.compile(
        module,
        trainset=trainset,
        num_trials=num_trials,
        minibatch=True,
        minibatch_size=min(50, len(trainset)),
        minibatch_full_eval_steps=5,
    )


# ---------------------------------------------------------------------------
# Save / load helpers
# ---------------------------------------------------------------------------

def _save(compiled_module, game: str, optimizer_name: str) -> Path:
    out_path = COMPILED_DIR / f"{game}_{optimizer_name}_advisor.json"
    compiled_module.save(str(out_path))
    print(f"\nCompiled module saved → {out_path}")
    return out_path


def _save_results(results: dict, game: str, optimizer_name: str) -> None:
    out_path = COMPILED_DIR / f"{game}_{optimizer_name}_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Results summary saved → {out_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    args = _build_parser().parse_args()

    # Configure DSPy backend
    from gamesage import config
    config.configure_dspy(dry_run=args.dry_run)

    import dspy
    from gamesage.core.explainer import GameSageAdvisor

    print(f"\n{'='*60}")
    print(f"GameSage Optimizer")
    print(f"  Game      : {args.game}")
    print(f"  Optimizer : {args.optimizer}")
    print(f"  Dry run   : {args.dry_run}")
    print(f"{'='*60}\n")

    # Load data
    print("Loading dataset...")
    trainset, devset = _load_dataset(args.game, args.train_size, args.dev_size)

    metric = _make_metric(args.dry_run)

    # Baseline
    print("\nBaseline evaluation (uncompiled)...")
    baseline_module = GameSageAdvisor()
    baseline_score  = _evaluate(baseline_module, devset, metric, args.threads, "Baseline score")

    # Optimize
    fresh_module = GameSageAdvisor()
    t0 = time.time()

    if args.optimizer == "bootstrap":
        compiled = _run_bootstrap(fresh_module, trainset, metric, args.max_demos)
    else:
        compiled = _run_mipro(fresh_module, trainset, metric, args.mipro_trials, args.threads)

    elapsed = time.time() - t0
    print(f"\nOptimization completed in {elapsed:.1f}s")

    # Post-optimization evaluation
    print("\nPost-optimization evaluation...")
    optimized_score = _evaluate(compiled, devset, metric, args.threads, "Optimized score")

    delta = optimized_score - baseline_score
    print(f"\n  Improvement: {delta:+.1f}%")

    # Save
    _save(compiled, args.game, args.optimizer)
    _save_results(
        {
            "game":            args.game,
            "optimizer":       args.optimizer,
            "train_size":      len(trainset),
            "dev_size":        len(devset),
            "baseline_score":  baseline_score,
            "optimized_score": optimized_score,
            "delta":           delta,
            "elapsed_seconds": elapsed,
            "dry_run":         args.dry_run,
        },
        args.game,
        args.optimizer,
    )


if __name__ == "__main__":
    main()
