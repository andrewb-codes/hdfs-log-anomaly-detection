#!/usr/bin/env python
import argparse
import sys
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from hdfs_anomaly.data.loading import load_preprocessed_hdfs
from hdfs_anomaly.utils.experiment import load_config, resolve_project_path
from hdfs_anomaly.features.tabular import build_tabular_feature_frame
from hdfs_anomaly.models.tabular import TABULAR_MODEL_NAMES, build_tabular_model


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train full-block tabular baselines for HDFS anomaly detection."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "configs" / "tabular_baselines.yaml",
        help="YAML config with data paths, split parameters, and model settings.",
    )
    return parser.parse_args()


def build_run_config(args: argparse.Namespace) -> dict:
    config = load_config(args.config)
    config["data_dir"] = resolve_project_path(config["data_dir"], ROOT)
    config["reports_dir"] = resolve_project_path(config["reports_dir"], ROOT)
    config["tables_dir"] = config["reports_dir"] / "tables"
    config["artifacts_dir"] = resolve_project_path(config["artifacts_dir"], ROOT)
    return config


def split_data(X: pd.DataFrame, y: pd.Series, config: dict):
    split_config = config["split"]
    X_train_full, X_test, y_train_full, y_test = train_test_split(
        X,
        y,
        test_size=split_config["test_size"],
        random_state=split_config["random_state"],
        stratify=y,
    )
    X_train, X_val, y_train, y_val = train_test_split(
        X_train_full,
        y_train_full,
        test_size=split_config["val_size"],
        random_state=split_config["random_state"],
        stratify=y_train_full,
    )
    return X_train, X_val, X_test, y_train, y_val, y_test


def model_scores(model_name: str, model, X):
    if model_name == "isolation_forest":
        return -model.score_samples(X)
    return model.predict_proba(X)[:, 1]


def fit_model(
    model_name: str,
    model,
    X_train: pd.DataFrame,
    y_train: pd.Series,
    model_config: dict,
):
    if model_name == "isolation_forest" and model_config.get("train_on_normal_only", True):
        model.fit(X_train[y_train == 0])
        return model
    model.fit(X_train, y_train)
    return model


def save_feature_importance(model_name: str, model, feature_names: list[str], output_dir: Path) -> None:
    if model_name == "random_forest":
        importance = (
            pd.DataFrame(
                {
                    "feature": feature_names,
                    "importance": model.feature_importances_,
                }
            )
            .sort_values("importance", ascending=False)
            .reset_index(drop=True)
        )
        importance.to_csv(output_dir / "feature_importance_random_forest.csv", index=False)
        return

    if model_name == "logistic_regression":
        classifier = model.named_steps["classifier"]
        coefficients = (
            pd.DataFrame(
                {
                    "feature": feature_names,
                    "coef": classifier.coef_.ravel(),
                }
            )
            .assign(abs_coef=lambda df: df["coef"].abs())
            .sort_values("abs_coef", ascending=False)
            .reset_index(drop=True)
        )
        coefficients.to_csv(output_dir / "feature_importance_logistic_regression.csv", index=False)


def save_scores(
    model_name: str,
    split_name: str,
    X: pd.DataFrame,
    y: pd.Series,
    scores,
    output_dir: Path,
) -> None:
    scores_df = pd.DataFrame(
        {
            "block_id": X.index,
            "y_true": y.to_numpy(),
            "score": scores,
        }
    )
    scores_df.to_csv(output_dir / f"scores_{split_name}_{model_name}.csv", index=False)


def train_one_model(
    model_name: str,
    X_train: pd.DataFrame,
    X_val: pd.DataFrame,
    X_test: pd.DataFrame,
    y_train: pd.Series,
    y_val: pd.Series,
    y_test: pd.Series,
    feature_names: list[str],
    config: dict,
) -> None:
    model_config = config["models"].get(model_name, {})
    model = build_tabular_model(
        model_name,
        random_state=config["split"]["random_state"],
        **model_config,
    )
    fit_model(model_name, model, X_train, y_train, model_config)

    val_scores = model_scores(model_name, model, X_val)
    test_scores = model_scores(model_name, model, X_test)

    save_feature_importance(model_name, model, feature_names, config["tables_dir"])
    save_scores(model_name, "validation", X_val, y_val, val_scores, config["tables_dir"])
    save_scores(model_name, "test", X_test, y_test, test_scores, config["tables_dir"])

    if config["save_model"]:
        import joblib

        config["artifacts_dir"].mkdir(parents=True, exist_ok=True)
        joblib.dump(model, config["artifacts_dir"] / f"{model_name}.joblib")


def main() -> None:
    args = parse_args()
    config = build_run_config(args)
    config["tables_dir"].mkdir(parents=True, exist_ok=True)

    data = load_preprocessed_hdfs(config["data_dir"])
    X, y, feature_names = build_tabular_feature_frame(
        labels=data.labels,
        occurrence=data.occurrence,
        traces=data.traces,
    )
    X_train, X_val, X_test, y_train, y_val, y_test = split_data(X, y, config)

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

    print("Config:", args.config)
    print(
        "Dataset split:",
        f"train={len(X_train)}",
        f"val={len(X_val)}",
        f"test={len(X_test)}",
    )
    print("Features:", len(feature_names))

    for model_name in model_names:
        print(f"Training {model_name}...")
        train_one_model(
            model_name=model_name,
            X_train=X_train,
            X_val=X_val,
            X_test=X_test,
            y_train=y_train,
            y_val=y_val,
            y_test=y_test,
            feature_names=feature_names,
            config=config,
        )

    print("\nSaved validation/test raw scores to:", config["tables_dir"])
    print("Run scripts/evaluate_tabular_baselines.py to select thresholds and compute metrics.")


if __name__ == "__main__":
    main()
