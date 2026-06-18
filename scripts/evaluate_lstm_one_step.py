#!/usr/bin/env python
import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from hdfs_anomaly.utils.experiment import load_config, resolve_project_path
from hdfs_anomaly.metrics.classification import classification_summary, find_threshold_for_max_f1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Select threshold and evaluate one-step LSTM block anomaly scores."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "configs" / "lstm_one_step.yaml",
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


def load_scores(tables_dir: Path, split_name: str) -> pd.DataFrame:
    path = tables_dir / f"scores_{split_name}_lstm_one_step.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"Scores not found: {path}. Run scripts/train_lstm_one_step.py first."
        )
    return pd.read_csv(path)


def evaluate(config: dict) -> tuple[dict, dict, dict]:
    validation_scores = load_scores(config["tables_dir"], "val")
    test_scores = load_scores(config["tables_dir"], "test")

    threshold, validation_best_f1 = find_threshold_for_max_f1(
        validation_scores["y_true"],
        validation_scores["score"],
    )

    validation_pred = (validation_scores["score"] >= threshold).astype(int)
    test_pred = (test_scores["score"] >= threshold).astype(int)

    validation_summary = classification_summary(
        "lstm_one_step",
        validation_scores["y_true"],
        validation_pred,
        scores=validation_scores["score"],
        threshold=threshold,
    )
    test_summary = classification_summary(
        "lstm_one_step",
        test_scores["y_true"],
        test_pred,
        scores=test_scores["score"],
        threshold=threshold,
    )
    threshold_summary = {
        "model": "lstm_one_step",
        "strategy": "max_f1",
        "threshold": threshold,
        "validation_best_f1": validation_best_f1,
    }
    return threshold_summary, validation_summary, test_summary


def print_metrics(title: str, row: dict) -> None:
    display_columns = [
        "model",
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
    print(f"\n{title}")
    print(pd.DataFrame([row])[display_columns].round(4).to_string(index=False))


def main() -> None:
    args = parse_args()
    config = build_run_config(args)
    config["tables_dir"].mkdir(parents=True, exist_ok=True)

    threshold_summary, validation_summary, test_summary = evaluate(config)

    pd.DataFrame([threshold_summary]).to_csv(
        config["tables_dir"] / "lstm_one_step_thresholds.csv",
        index=False,
    )
    pd.DataFrame([validation_summary]).to_csv(
        config["tables_dir"] / "lstm_one_step_validation_metrics.csv",
        index=False,
    )
    pd.DataFrame([test_summary]).to_csv(
        config["tables_dir"] / "lstm_one_step_test_metrics.csv",
        index=False,
    )

    print("Config:", args.config)
    print("Run:", config["run_name"])
    print("Threshold and metrics saved to:", config["tables_dir"])
    print_metrics("Validation metrics", validation_summary)
    print_metrics("Test metrics", test_summary)


if __name__ == "__main__":
    main()
