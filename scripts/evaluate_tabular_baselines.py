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
from hdfs_anomaly.models.tabular import TABULAR_MODEL_NAMES


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Select thresholds and evaluate tabular HDFS anomaly baselines."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "configs" / "tabular_baselines.yaml",
        help="YAML config with experiment settings.",
    )
    return parser.parse_args()


def build_run_config(args: argparse.Namespace) -> dict:
    config = load_config(args.config)
    config["reports_dir"] = resolve_project_path(config["reports_dir"], ROOT)
    config["tables_dir"] = config["reports_dir"] / "tables"
    return config


def selected_model_names(config: dict) -> tuple[str, ...]:
    requested_model_names = tuple(config["run"]["models"])
    unknown_model_names = sorted(set(requested_model_names) - set(TABULAR_MODEL_NAMES))
    if unknown_model_names:
        raise ValueError(f"Unknown tabular models in config: {unknown_model_names}")

    model_names = tuple(
        model_name
        for model_name in requested_model_names
        if config["models"].get(model_name, {}).get("enabled", True)
    )
    if not model_names:
        raise ValueError("No tabular models selected. Check config run.models and models.*.enabled.")
    return model_names


def load_scores(reports_dir: Path, split_name: str, model_name: str) -> pd.DataFrame:
    path = reports_dir / f"scores_{split_name}_{model_name}.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"Scores not found: {path}. Run scripts/train_tabular_baseline.py first."
        )
    return pd.read_csv(path)


def evaluate_one_model(model_name: str, config: dict) -> tuple[dict, dict, dict]:
    tables_dir = config["tables_dir"]
    validation_scores = load_scores(tables_dir, "validation", model_name)
    test_scores = load_scores(tables_dir, "test", model_name)

    threshold, validation_best_f1 = find_threshold_for_max_f1(
        validation_scores["y_true"],
        validation_scores["score"],
    )

    validation_pred = (validation_scores["score"] >= threshold).astype(int)
    test_pred = (test_scores["score"] >= threshold).astype(int)

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
    threshold_summary = {
        "model": model_name,
        "strategy": "max_f1",
        "threshold": threshold,
        "validation_best_f1": validation_best_f1,
    }
    return threshold_summary, validation_summary, test_summary


def save_metrics(config: dict, threshold_rows: list[dict], val_rows: list[dict], test_rows: list[dict]) -> None:
    reports_dir = config["tables_dir"]
    reports_dir.mkdir(parents=True, exist_ok=True)
    thresholds_df = pd.DataFrame(threshold_rows)
    validation_df = pd.DataFrame(val_rows)
    test_df = pd.DataFrame(test_rows)

    thresholds_df.to_csv(reports_dir / "tabular_thresholds.csv", index=False)
    validation_df.to_csv(reports_dir / "tabular_validation_metrics.csv", index=False)
    test_df.to_csv(reports_dir / "tabular_test_metrics.csv", index=False)

    for row in val_rows:
        pd.DataFrame([row]).to_csv(
            reports_dir / f"validation_metrics_{row['model']}.csv",
            index=False,
        )
    for row in test_rows:
        pd.DataFrame([row]).to_csv(
            reports_dir / f"test_metrics_{row['model']}.csv",
            index=False,
        )


def print_metrics(title: str, rows: list[dict]) -> None:
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
    df = pd.DataFrame(rows)
    print(f"\n{title}")
    print(df[display_columns].round(4).to_string(index=False))


def main() -> None:
    args = parse_args()
    config = build_run_config(args)
    model_names = selected_model_names(config)

    threshold_rows = []
    val_rows = []
    test_rows = []
    for model_name in model_names:
        threshold_summary, validation_summary, test_summary = evaluate_one_model(model_name, config)
        threshold_rows.append(threshold_summary)
        val_rows.append(validation_summary)
        test_rows.append(test_summary)

    save_metrics(config, threshold_rows, val_rows, test_rows)
    print("Config:", args.config)
    print("Thresholds and metrics saved to:", config["tables_dir"])
    print_metrics("Validation metrics", val_rows)
    print_metrics("Test metrics", test_rows)


if __name__ == "__main__":
    main()
