#!/usr/bin/env python
import argparse
from pathlib import Path

import pandas as pd

from hdfs_anomaly.parsing.drain_transformer import DrainEventSequenceTransformer
from hdfs_anomaly.sequences.io import save_lstm_dataset
from hdfs_anomaly.sequences.split import (
    read_block_labels,
    split_blocks,
    split_log_lines_by_blocks,
)
from hdfs_anomaly.sequences.windows import make_lstm_windows
from hdfs_anomaly.utils.experiment import load_config, resolve_project_path

ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare HDFS event windows for LSTM sequence models."
    )
    parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="YAML config with paths, Drain settings, split settings, and window mode.",
    )
    return parser.parse_args()


def resolve_paths(config: dict) -> dict:
    config = dict(config)
    config["data"] = dict(config["data"])
    config["drain"] = dict(config["drain"])
    config["output"] = dict(config["output"])
    config["data"]["log_path"] = resolve_project_path(config["data"]["log_path"], ROOT)
    config["data"]["label_path"] = resolve_project_path(config["data"]["label_path"], ROOT)
    config["drain"]["config_path"] = resolve_project_path(config["drain"]["config_path"], ROOT)
    config["drain"]["state_path"] = resolve_project_path(config["drain"]["state_path"], ROOT)
    config["output"]["dir"] = resolve_project_path(config["output"]["dir"], ROOT)
    return config


def reset_drain_state_if_needed(config: dict) -> None:
    state_path = config["drain"]["state_path"]
    if config["drain"].get("reset_state", True) and state_path.exists():
        state_path.unlink()


def selected_raw_lines(config: dict):
    labels_df = read_block_labels(config["data"]["label_path"])
    split_config = config["split"]
    train_blocks, val_blocks, test_blocks = split_blocks(
        labels_df=labels_df,
        train_norm_ratio=split_config["train_norm_ratio"],
        val_norm_ratio=split_config["val_norm_ratio"],
        val_anom_ratio=split_config["val_anom_ratio"],
        seed=split_config["seed"],
    )
    parsing_config = config["parsing"]
    train_lines, val_lines, test_lines = split_log_lines_by_blocks(
        log_path=config["data"]["log_path"],
        train_blocks=train_blocks,
        val_blocks=val_blocks,
        test_blocks=test_blocks,
        block_id_regex=parsing_config["block_id_regex"],
        max_lines=parsing_config.get("max_lines"),
    )
    return (
        labels_df,
        {"train": train_blocks, "val": val_blocks, "test": test_blocks},
        train_lines,
        val_lines,
        test_lines,
    )


def build_transformer(config: dict) -> DrainEventSequenceTransformer:
    drain_config = config["drain"]
    parsing_config = config["parsing"]
    return DrainEventSequenceTransformer(
        drain_state=str(drain_config["state_path"]),
        drain_config=str(drain_config["config_path"]),
        timestamp_format=parsing_config.get("timestamp_format", "%y%m%d %H%M%S"),
        block_id_regex=parsing_config["block_id_regex"],
        min_sequence_len=config["window"].get("min_sequence_len", 2),
        update_drain_on_fit=True,
        drop_unknown_block=parsing_config.get("drop_unknown_block", True),
    )


def prepare_windows(transformer, config: dict, train_lines, val_lines, test_lines):
    train_raw = pd.DataFrame({"original_message": train_lines})
    val_raw = pd.DataFrame({"original_message": val_lines})
    test_raw = pd.DataFrame({"original_message": test_lines})

    transformer.fit(train_raw)
    train_sequences = transformer.transform(train_raw)
    val_sequences = transformer.transform(val_raw)
    test_sequences = transformer.transform(test_raw)

    window_config = config["window"]
    kwargs = {
        "window_size": window_config["size"],
        "stride": window_config["stride"],
        "target_mode": window_config["target_mode"],
    }
    return (
        make_lstm_windows(train_sequences, **kwargs),
        make_lstm_windows(val_sequences, **kwargs),
        make_lstm_windows(test_sequences, **kwargs),
    )


def main() -> None:
    args = parse_args()
    config = resolve_paths(load_config(args.config))
    reset_drain_state_if_needed(config)

    labels_df, split_block_sets, train_lines, val_lines, test_lines = selected_raw_lines(config)
    label_map = dict(zip(labels_df["block_id"], labels_df["is_anomaly"], strict=False))

    transformer = build_transformer(config)
    train_windows, val_windows, test_windows = prepare_windows(
        transformer,
        config,
        train_lines,
        val_lines,
        test_lines,
    )

    save_lstm_dataset(
        output_dir=config["output"]["dir"],
        transformer=transformer,
        train_windows=train_windows,
        val_windows=val_windows,
        test_windows=test_windows,
        label_map=label_map,
        split_blocks=split_block_sets,
        target_mode=config["window"]["target_mode"],
        window_size=config["window"]["size"],
        stride=config["window"]["stride"],
    )

    print("Config:", args.config)
    print("Output:", config["output"]["dir"])
    print("Target mode:", config["window"]["target_mode"])
    print(
        "Windows:",
        f"train={len(train_windows)}",
        f"val={len(val_windows)}",
        f"test={len(test_windows)}",
    )


if __name__ == "__main__":
    main()
