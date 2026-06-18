#!/usr/bin/env python
import argparse
import copy
import json
import sys
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from hdfs_anomaly.metrics.lstm_one_step import (
    block_miss_rate_frame,
    predict_next_event_logits,
    topk_miss_from_logits,
)
from hdfs_anomaly.utils.experiment import load_config, resolve_project_path, select_device, set_seed
from hdfs_anomaly.models.lstm_one_step import OneStepLSTMModel


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train one-step LSTM next-event baseline.")
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "configs" / "lstm_one_step.yaml",
        help="YAML config with dataset, model, training, and scoring settings.",
    )
    return parser.parse_args()


def build_run_config(args: argparse.Namespace) -> dict:
    config = load_config(args.config)
    run_name = config.get("run_name")
    if not run_name:
        raise ValueError("Config must define a non-empty run_name.")

    config["dataset_path"] = resolve_project_path(config["dataset_path"], ROOT)
    config["reports_dir"] = resolve_project_path(config["reports_dir"], ROOT)
    config["artifacts_dir"] = resolve_project_path(config["artifacts_dir"], ROOT)
    config["run_reports_dir"] = config["reports_dir"] / run_name
    config["tables_dir"] = config["run_reports_dir"] / "tables"
    config["run_artifacts_dir"] = config["artifacts_dir"] / run_name
    return config

def load_one_step_dataset(dataset_path: Path) -> dict[str, np.ndarray]:
    if not dataset_path.exists():
        raise FileNotFoundError(
            f"Dataset not found: {dataset_path}. "
            "Run scripts/prepare_lstm_data.py with configs/lstm_one_step_data.yaml first."
        )
    data = np.load(dataset_path, allow_pickle=True)
    required_keys = {
        "X_train",
        "y_train",
        "X_val",
        "y_val",
        "X_test",
        "y_test",
        "val_labels",
        "val_block_ids",
        "test_labels",
        "test_block_ids",
    }
    missing_keys = sorted(required_keys - set(data.files))
    if missing_keys:
        raise ValueError(f"Dataset is missing required arrays: {missing_keys}")

    arrays = {key: data[key] for key in required_keys}
    if arrays["X_train"].size == 0:
        raise ValueError("X_train is empty")
    if arrays["y_train"].ndim != 1:
        raise ValueError("Expected one-step targets with shape (n_windows,).")
    return arrays


def infer_vocab_size(arrays: dict[str, np.ndarray]) -> int:
    max_event_id = max(
        int(arrays[name].max())
        for name in ("X_train", "y_train", "X_val", "y_val", "X_test", "y_test")
        if arrays[name].size
    )
    return max_event_id + 1


def make_train_loader(x_train: np.ndarray, y_train: np.ndarray, batch_size: int) -> DataLoader:
    dataset = TensorDataset(
        torch.as_tensor(x_train, dtype=torch.long),
        torch.as_tensor(y_train, dtype=torch.long),
    )
    return DataLoader(dataset, batch_size=batch_size, shuffle=True)


def compute_loss(
    model: torch.nn.Module,
    criterion,
    x: np.ndarray,
    y: np.ndarray,
    device: str,
    batch_size: int,
) -> float:
    if x.size == 0:
        return 0.0

    model.eval()
    total_loss = 0.0
    total_count = 0
    with torch.no_grad():
        for start in range(0, len(x), batch_size):
            xb = torch.as_tensor(x[start : start + batch_size], dtype=torch.long, device=device)
            yb = torch.as_tensor(y[start : start + batch_size], dtype=torch.long, device=device)
            loss = criterion(model(xb), yb)
            total_loss += loss.item() * yb.size(0)
            total_count += yb.size(0)
    return total_loss / total_count if total_count else 0.0


def train_model(
    model: torch.nn.Module,
    arrays: dict[str, np.ndarray],
    config: dict,
    device: str,
) -> tuple[dict[str, list[float]], dict[str, torch.Tensor], int, float]:
    training_config = config["training"]
    early_stopping_config = config.get("early_stopping", {})
    early_stopping_enabled = early_stopping_config.get("enabled", False)
    patience = early_stopping_config.get("patience", 1)
    min_delta = early_stopping_config.get("min_delta", 0.0)

    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=training_config["lr"],
        weight_decay=training_config.get("weight_decay", 0.0),
    )
    train_loader = make_train_loader(
        arrays["X_train"],
        arrays["y_train"],
        training_config["batch_size"],
    )

    history = {"epoch": [], "train_loss": [], "val_loss": [], "is_best": []}
    best_state_dict = copy.deepcopy(model.state_dict())
    best_epoch = 0
    best_val_loss = float("inf")
    epochs_without_improvement = 0

    for epoch in range(1, training_config["epochs"] + 1):
        model.train()
        total_loss = 0.0
        total_count = 0

        for xb, yb in train_loader:
            xb = xb.to(device)
            yb = yb.to(device)
            optimizer.zero_grad()
            loss = criterion(model(xb), yb)
            loss.backward()
            optimizer.step()

            total_loss += loss.item() * yb.size(0)
            total_count += yb.size(0)

        train_loss = total_loss / total_count if total_count else 0.0
        val_loss = compute_loss(
            model,
            criterion,
            arrays["X_val"],
            arrays["y_val"],
            device,
            training_config["batch_size"],
        )

        is_best = val_loss < best_val_loss - min_delta
        if is_best:
            best_state_dict = copy.deepcopy(model.state_dict())
            best_epoch = epoch
            best_val_loss = float(val_loss)
            epochs_without_improvement = 0
        else:
            epochs_without_improvement += 1

        history["epoch"].append(epoch)
        history["train_loss"].append(float(train_loss))
        history["val_loss"].append(float(val_loss))
        history["is_best"].append(bool(is_best))

        print(
            f"Epoch {epoch}/{training_config['epochs']} | "
            f"train_loss={train_loss:.4f} | "
            f"val_loss={val_loss:.4f}"
            f"{' | best' if is_best else ''}"
        )

        if early_stopping_enabled and epochs_without_improvement >= patience:
            print(
                "Early stopping:",
                f"no validation loss improvement for {epochs_without_improvement} epoch(s).",
            )
            break

    return history, best_state_dict, best_epoch, best_val_loss


def save_block_scores(
    model: torch.nn.Module,
    arrays: dict[str, np.ndarray],
    split_name: str,
    config: dict,
    device: str,
) -> None:
    training_config = config["training"]
    scoring_config = config["scoring"]

    logits = predict_next_event_logits(
        model,
        arrays[f"X_{split_name}"],
        device,
        training_config["batch_size"],
    )
    miss = topk_miss_from_logits(logits, arrays[f"y_{split_name}"], scoring_config["top_k"])
    scores = block_miss_rate_frame(
        miss=miss,
        block_ids=arrays[f"{split_name}_block_ids"],
        labels=arrays[f"{split_name}_labels"],
    )
    scores.to_csv(config["tables_dir"] / f"scores_{split_name}_lstm_one_step.csv", index=False)


def save_model(
    model: torch.nn.Module,
    vocab_size: int,
    config: dict,
    device: str,
    best_epoch: int,
    best_val_loss: float,
) -> None:
    config["run_artifacts_dir"].mkdir(parents=True, exist_ok=True)
    output_path = config["run_artifacts_dir"] / "model.pt"
    checkpoint = {
        "model_name": "one_step_lstm",
        "run_name": config["run_name"],
        "state_dict": model.state_dict(),
        "vocab_size": vocab_size,
        "model_config": config["model"],
        "scoring_config": config["scoring"],
        "early_stopping_config": config.get("early_stopping", {}),
        "best_epoch": best_epoch,
        "best_val_loss": best_val_loss,
        "device": device,
    }
    torch.save(checkpoint, output_path)


def save_history(history: dict[str, list[float]], config: dict) -> None:
    config["tables_dir"].mkdir(parents=True, exist_ok=True)
    with (config["tables_dir"] / "lstm_one_step_history.json").open("w", encoding="utf-8") as file:
        json.dump(history, file, indent=2)


def main() -> None:
    args = parse_args()
    config = build_run_config(args)
    config["tables_dir"].mkdir(parents=True, exist_ok=True)
    config["artifacts_dir"].mkdir(parents=True, exist_ok=True)

    set_seed(config["training"].get("seed", 42))
    device = select_device(config["training"].get("device", "auto"))
    arrays = load_one_step_dataset(config["dataset_path"])
    vocab_size = infer_vocab_size(arrays)

    model = OneStepLSTMModel(vocab_size=vocab_size, **config["model"]).to(device)
    print("Config:", args.config)
    print("Run:", config["run_name"])
    print("Dataset:", config["dataset_path"])
    print("Device:", device)
    print(
        "Windows:",
        f"train={len(arrays['X_train'])}",
        f"val={len(arrays['X_val'])}",
        f"test={len(arrays['X_test'])}",
    )
    print("Vocab size:", vocab_size)

    history, best_state_dict, best_epoch, best_val_loss = train_model(model, arrays, config, device)
    model.load_state_dict(best_state_dict)
    history["best_epoch"] = best_epoch
    history["best_val_loss"] = best_val_loss

    save_history(history, config)
    save_block_scores(model, arrays, "val", config, device)
    save_block_scores(model, arrays, "test", config, device)

    model_path = config["run_artifacts_dir"] / "model.pt"
    if config.get("save_model", True):
        save_model(model, vocab_size, config, device, best_epoch, best_val_loss)

    if config.get("save_model", True):
        print("\nSaved model to:", model_path)
    else:
        print("\nModel saving disabled in config.")
    print("Best epoch:", best_epoch, f"(val_loss={best_val_loss:.4f})")
    print("Saved raw block scores and history to:", config["tables_dir"])
    print("Run scripts/evaluate_lstm_one_step.py to select threshold and compute metrics.")


if __name__ == "__main__":
    main()
