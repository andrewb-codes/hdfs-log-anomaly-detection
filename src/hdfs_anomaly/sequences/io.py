import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd


def labels_for_windows(windows_df: pd.DataFrame, label_map: dict[str, int]) -> np.ndarray:
    if windows_df.empty:
        return np.empty((0,), dtype=np.int64)
    return windows_df["block_id"].map(label_map).fillna(0).astype(int).to_numpy()


def windows_to_array(windows_df: pd.DataFrame, window_size: int) -> np.ndarray:
    if windows_df.empty:
        return np.empty((0, window_size), dtype=np.int64)
    return np.asarray(windows_df["window"].tolist(), dtype=np.int64)


def targets_to_array(windows_df: pd.DataFrame, target_mode: str, window_size: int) -> np.ndarray:
    if windows_df.empty:
        if target_mode == "one_step":
            return np.empty((0,), dtype=np.int64)
        return np.empty((0, window_size), dtype=np.int64)
    return np.asarray(windows_df["target"].tolist(), dtype=np.int64)


def save_lstm_dataset(
    output_dir: str | Path,
    transformer,
    train_windows: pd.DataFrame,
    val_windows: pd.DataFrame,
    test_windows: pd.DataFrame,
    label_map: dict[str, int],
    split_blocks: dict[str, set[str]],
    target_mode: str,
    window_size: int,
    stride: int,
) -> None:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    joblib.dump(transformer, output_dir / "drain_event_sequence_transformer.joblib")

    arrays = {
        "X_train": windows_to_array(train_windows, window_size),
        "y_train": targets_to_array(train_windows, target_mode, window_size),
        "X_val": windows_to_array(val_windows, window_size),
        "y_val": targets_to_array(val_windows, target_mode, window_size),
        "X_test": windows_to_array(test_windows, window_size),
        "y_test": targets_to_array(test_windows, target_mode, window_size),
        "train_labels": labels_for_windows(train_windows, label_map),
        "val_labels": labels_for_windows(val_windows, label_map),
        "test_labels": labels_for_windows(test_windows, label_map),
        "train_block_ids": train_windows["block_id"].astype(str).to_numpy(),
        "val_block_ids": val_windows["block_id"].astype(str).to_numpy(),
        "test_block_ids": test_windows["block_id"].astype(str).to_numpy(),
    }
    np.savez_compressed(output_dir / "dataset.npz", **arrays)  # type: ignore[arg-type]

    anomaly_blocks = {block_id for block_id, is_anomaly in label_map.items() if is_anomaly == 1}
    meta = {
        "target_mode": target_mode,
        "window_size": window_size,
        "stride": stride,
        "train_windows": int(arrays["X_train"].shape[0]),
        "val_windows": int(arrays["X_val"].shape[0]),
        "test_windows": int(arrays["X_test"].shape[0]),
        "event_vocab_size": len(transformer.template_list_ or []),
        "unknown_event_id": transformer.event_to_id_.get("unknown", -1)
        if transformer.event_to_id_
        else -1,
        "train_blocks": len(split_blocks["train"]),
        "val_blocks": len(split_blocks["val"]),
        "test_blocks": len(split_blocks["test"]),
        "val_anomaly_blocks": len(split_blocks["val"] & anomaly_blocks),
        "test_anomaly_blocks": len(split_blocks["test"] & anomaly_blocks),
    }
    with (output_dir / "meta.json").open("w", encoding="utf-8") as file:
        json.dump(meta, file, ensure_ascii=False, indent=2)
