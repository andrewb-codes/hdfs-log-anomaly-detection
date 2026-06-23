#!/usr/bin/env python
import argparse
from pathlib import Path

import pandas as pd

from hdfs_anomaly.metrics.classification import classification_summary, find_threshold_for_max_f1
from hdfs_anomaly.metrics.lstm_many_to_many import MANY_TO_MANY_SCORING_STRATEGIES
from hdfs_anomaly.utils.experiment import load_config, resolve_project_path

ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Select thresholds and evaluate many-to-many LSTM anomaly scores."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "configs" / "lstm_many_to_many.yaml",
        help="YAML config with report paths and scoring settings.",
    )
    return parser.parse_args()


def build_run_config(args: argparse.Namespace) -> dict:
    config = load_config(args.config)
    run_name = config.get("run_name")
    if not run_name:
        raise ValueError("Config must define a non-empty run_name.")

    config["reports_dir"] = resolve_project_path(config["reports_dir"], ROOT)
    config["run_reports_dir"] = config["reports_dir"] / run_name
    config["tables_dir"] = config["run_reports_dir"] / "tables"
    return config


def selected_scoring_strategies(config: dict) -> tuple[str, ...]:
    strategies = tuple(config["scoring"].get("strategies", ("topk_last",)))
    unknown_strategies = sorted(set(strategies) - set(MANY_TO_MANY_SCORING_STRATEGIES))
    if unknown_strategies:
        raise ValueError(f"Unknown many-to-many scoring strategies: {unknown_strategies}")
    return strategies


def load_scores(tables_dir: Path, split_name: str, strategy: str) -> pd.DataFrame:
    path = tables_dir / f"scores_{split_name}_{strategy}_lstm_many_to_many.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"Scores not found: {path}. Run scripts/train_lstm_many_to_many.py first."
        )
    return pd.read_csv(path)


def evaluate_one_strategy(strategy: str, config: dict) -> tuple[dict, dict, dict]:
    validation_scores = load_scores(config["tables_dir"], "val", strategy)
    test_scores = load_scores(config["tables_dir"], "test", strategy)

    threshold, validation_best_f1 = find_threshold_for_max_f1(
        validation_scores["y_true"],
        validation_scores["score"],
    )

    validation_pred = (validation_scores["score"] >= threshold).astype(int)
    test_pred = (test_scores["score"] >= threshold).astype(int)
    model_name = f"lstm_many_to_many_{strategy}"

    validation_summary = classification_summary(
        model_name,
        validation_scores["y_true"],
        validation_pred,
        scores=validation_scores["score"],
        threshold=threshold,
    )
    test_summary = classification_summary(
        model_name,
        test_scores["y_true"],
        test_pred,
        scores=test_scores["score"],
        threshold=threshold,
    )
    for row in (validation_summary, test_summary):
        row["strategy"] = strategy

    threshold_summary = {
        "model": model_name,
        "strategy": strategy,
        "threshold_strategy": "max_f1",
        "threshold": threshold,
        "validation_best_f1": validation_best_f1,
    }
    return threshold_summary, validation_summary, test_summary


def save_metrics(
    config: dict,
    threshold_rows: list[dict],
    validation_rows: list[dict],
    test_rows: list[dict],
) -> None:
    tables_dir = config["tables_dir"]
    tables_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(threshold_rows).to_csv(
        tables_dir / "lstm_many_to_many_thresholds.csv", index=False
    )
    pd.DataFrame(validation_rows).to_csv(
        tables_dir / "lstm_many_to_many_validation_metrics.csv",
        index=False,
    )
    pd.DataFrame(test_rows).to_csv(tables_dir / "lstm_many_to_many_test_metrics.csv", index=False)


def print_metrics(title: str, rows: list[dict]) -> None:
    display_columns = [
        "strategy",
        "threshold",
        "f1",
        "precision",
        "recall",
        "fpr",
        "average_precision",
        "tn",
        "fp",
        "fn",
        "tp",
    ]
    df = pd.DataFrame(rows)
    print(f"\n{title}")
    print(df[display_columns].round(4).to_string(index=False))


def main() -> None:
    args = parse_args()
    config = build_run_config(args)
    strategies = selected_scoring_strategies(config)

    threshold_rows = []
    validation_rows = []
    test_rows = []
    for strategy in strategies:
        threshold_summary, validation_summary, test_summary = evaluate_one_strategy(
            strategy, config
        )
        threshold_rows.append(threshold_summary)
        validation_rows.append(validation_summary)
        test_rows.append(test_summary)

    save_metrics(config, threshold_rows, validation_rows, test_rows)
    print("Config:", args.config)
    print("Run:", config["run_name"])
    print("Thresholds and metrics saved to:", config["tables_dir"])
    print_metrics("Validation metrics", validation_rows)
    print_metrics("Test metrics", test_rows)


if __name__ == "__main__":
    main()
