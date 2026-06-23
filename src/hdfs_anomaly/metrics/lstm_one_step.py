from collections.abc import Iterable
from typing import cast

import numpy as np
import pandas as pd
import torch


def predict_next_event_logits(
    model: torch.nn.Module,
    x: np.ndarray,
    device: str,
    batch_size: int = 1024,
) -> np.ndarray:
    """Return next-event logits for fixed-size event windows."""
    model.eval()
    if x.size == 0:
        return np.empty((0, 0), dtype=np.float32)

    logits_batches = []
    with torch.no_grad():
        for start in range(0, len(x), batch_size):
            xb = torch.as_tensor(x[start : start + batch_size], dtype=torch.long, device=device)
            logits = model(xb)
            logits_batches.append(logits.detach().cpu().numpy())
    return cast(np.ndarray, np.vstack(logits_batches))


def topk_miss_from_logits(logits: np.ndarray, y: np.ndarray, top_k: int) -> np.ndarray:
    """Return 1 when the true next event is missing from model top-k predictions."""
    if top_k < 1:
        raise ValueError("top_k must be >= 1")
    if logits.size == 0 or y.size == 0:
        return np.array([], dtype=np.int32)

    k = min(top_k, logits.shape[1])
    topk = np.argpartition(logits, kth=logits.shape[1] - k, axis=1)[:, -k:]
    hit = (topk == y.reshape(-1, 1)).any(axis=1)
    return cast(np.ndarray, (~hit).astype(np.int32))


def block_miss_rate_frame(
    miss: np.ndarray,
    block_ids: Iterable,
    labels: Iterable,
) -> pd.DataFrame:
    """Aggregate window-level top-k misses into block-level anomaly scores."""
    frame = pd.DataFrame(
        {
            "block_id": np.asarray(block_ids).astype(str),
            "miss": miss.astype(int),
            "y_true": np.asarray(labels).astype(int),
        }
    )
    if frame.empty:
        return pd.DataFrame(columns=["block_id", "y_true", "score", "num_windows", "num_misses"])

    return (
        frame.groupby("block_id", as_index=False)
        .agg(
            y_true=("y_true", "max"),
            score=("miss", "mean"),
            num_windows=("miss", "size"),
            num_misses=("miss", "sum"),
        )
        .sort_values("block_id")
        .reset_index(drop=True)
    )
