from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
import torch

from hdfs_anomaly.models.lstm_many_to_many import ManyToManyLSTMModel
from hdfs_anomaly.utils.experiment import load_config, resolve_project_path

ROOT = Path(__file__).resolve().parents[4]


@dataclass
class InferenceResources:
    model: ManyToManyLSTMModel
    transformer: Any
    threshold: float
    scoring_strategy: str
    window_size: int
    stride: int
    device: str


def load_threshold(path: Path, strategy: str) -> float:
    """Load the validation-selected anomaly threshold for a scoring strategy."""
    thresholds = pd.read_csv(path)
    row = thresholds[thresholds["strategy"] == strategy]
    if row.empty:
        raise ValueError(f"Threshold for strategy '{strategy}' not found in {path}")
    return float(row.iloc[0]["threshold"])


def load_resources(config_path: Path | None = None) -> InferenceResources:
    """Load model, parser, threshold, and sequence settings for API inference."""
    config_path = config_path or ROOT / "configs" / "api.yaml"
    config = load_config(config_path)

    checkpoint_path = resolve_project_path(config["model"]["checkpoint_path"], ROOT)
    threshold_path = resolve_project_path(config["threshold"]["path"], ROOT)
    transformer_path = resolve_project_path(config["transformer"]["path"], ROOT)

    checkpoint = torch.load(checkpoint_path, map_location="cpu")
    model = ManyToManyLSTMModel(vocab_size=checkpoint["vocab_size"], **checkpoint["model_config"])
    model.load_state_dict(checkpoint["state_dict"])
    model.eval()

    transformer = joblib.load(transformer_path)
    strategy = config["scoring"]["strategy"]
    threshold = load_threshold(threshold_path, strategy)

    return InferenceResources(
        model=model,
        transformer=transformer,
        threshold=threshold,
        scoring_strategy=strategy,
        window_size=int(config["sequence"]["window_size"]),
        stride=int(config["sequence"]["stride"]),
        device="cpu",
    )
