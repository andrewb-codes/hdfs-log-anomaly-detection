import re
from pathlib import Path

import numpy as np
import pandas as pd


def read_block_labels(label_path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(label_path, usecols=["BlockId", "Label"])
    df = df.rename(columns={"BlockId": "block_id", "Label": "label"})
    df["block_id"] = df["block_id"].astype(str)
    df["is_anomaly"] = df["label"].astype(str).str.strip().str.lower().eq("anomaly").astype(int)
    return df


def split_blocks(
    labels_df: pd.DataFrame,
    train_norm_ratio: float,
    val_norm_ratio: float,
    val_anom_ratio: float,
    seed: int,
) -> tuple[set[str], set[str], set[str]]:
    if train_norm_ratio + val_norm_ratio >= 1.0:
        raise ValueError("train_norm_ratio + val_norm_ratio must be less than 1.0")
    if not 0.0 <= val_anom_ratio <= 1.0:
        raise ValueError("val_anom_ratio must be between 0.0 and 1.0")

    normal_blocks = labels_df[labels_df["is_anomaly"] == 0]["block_id"].to_numpy()
    anomaly_blocks = labels_df[labels_df["is_anomaly"] == 1]["block_id"].to_numpy()

    rng = np.random.default_rng(seed)
    rng.shuffle(normal_blocks)
    rng.shuffle(anomaly_blocks)

    train_size = int(len(normal_blocks) * train_norm_ratio)
    val_size = int(len(normal_blocks) * val_norm_ratio)
    val_end = train_size + val_size

    train_blocks = set(normal_blocks[:train_size])
    val_blocks = set(normal_blocks[train_size:val_end])
    test_blocks = set(normal_blocks[val_end:])

    val_anom_size = int(len(anomaly_blocks) * val_anom_ratio)
    val_blocks |= set(anomaly_blocks[:val_anom_size])
    test_blocks |= set(anomaly_blocks[val_anom_size:])

    return train_blocks, val_blocks, test_blocks


def split_log_lines_by_blocks(
    log_path: str | Path,
    train_blocks: set[str],
    val_blocks: set[str],
    test_blocks: set[str],
    block_id_regex: str,
    max_lines: int | None = None,
) -> tuple[list[str], list[str], list[str]]:
    block_re = re.compile(block_id_regex)
    train_lines = []
    val_lines = []
    test_lines = []
    seen = 0

    with Path(log_path).open("r", errors="ignore") as file:
        for line in file:
            if max_lines is not None and seen >= max_lines:
                break
            seen += 1
            match = block_re.search(line)
            if not match:
                continue

            block_id = match.group(1)
            line = line.rstrip("\n")
            if block_id in train_blocks:
                train_lines.append(line)
            elif block_id in val_blocks:
                val_lines.append(line)
            elif block_id in test_blocks:
                test_lines.append(line)

    return train_lines, val_lines, test_lines
