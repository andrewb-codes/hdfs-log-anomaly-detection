import pandas as pd


def make_lstm_windows(
    sequences_df: pd.DataFrame,
    window_size: int,
    stride: int,
    target_mode: str,
) -> pd.DataFrame:
    if target_mode not in {"one_step", "many_to_many"}:
        raise ValueError("target_mode must be one of: one_step, many_to_many")

    rows = []
    for _, row in sequences_df.iterrows():
        block_id = row["block_id"]
        sequence = row["sequence"]
        if len(sequence) <= window_size:
            continue

        for start in range(0, len(sequence) - window_size, stride):
            window = sequence[start : start + window_size]
            if target_mode == "one_step":
                target = sequence[start + window_size]
            else:
                target = sequence[start + 1 : start + window_size + 1]
            rows.append({"block_id": block_id, "window": window, "target": target})

    return pd.DataFrame(rows, columns=["block_id", "window", "target"])
