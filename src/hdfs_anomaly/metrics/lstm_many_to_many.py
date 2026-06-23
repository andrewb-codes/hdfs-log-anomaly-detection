from collections.abc import Iterable

import numpy as np
import pandas as pd
import torch

MANY_TO_MANY_SCORING_STRATEGIES = (
    "topk_last",
    "topk_all",
    "topk_last3",
    "nll_mean",
    "nll_p95",
    "nll_max",
)


def batch_strategy_scores(
    logits: torch.Tensor,
    y: torch.Tensor,
    strategies: Iterable[str],
    top_k: int,
) -> dict[str, np.ndarray]:
    """Compute per-window anomaly scores for many-to-many next-token logits."""
    if top_k < 1:
        raise ValueError("top_k must be >= 1")

    unknown_strategies = sorted(set(strategies) - set(MANY_TO_MANY_SCORING_STRATEGIES))
    if unknown_strategies:
        raise ValueError(f"Unknown many-to-many scoring strategies: {unknown_strategies}")

    scores = {}
    strategies = tuple(strategies)

    if any(strategy.startswith("topk_") for strategy in strategies):
        k = min(top_k, logits.shape[-1])
        topk = torch.topk(logits, k=k, dim=-1).indices
        miss = ~(topk == y.unsqueeze(-1)).any(dim=-1)

        if "topk_last" in strategies:
            scores["topk_last"] = miss[:, -1].float().cpu().numpy()
        if "topk_all" in strategies:
            scores["topk_all"] = miss.float().mean(dim=1).cpu().numpy()
        if "topk_last3" in strategies:
            scores["topk_last3"] = miss[:, -3:].float().mean(dim=1).cpu().numpy()

    if any(strategy.startswith("nll_") for strategy in strategies):
        log_probs = torch.log_softmax(logits, dim=-1)
        nll = -log_probs.gather(dim=-1, index=y.unsqueeze(-1)).squeeze(-1)

        if "nll_mean" in strategies:
            scores["nll_mean"] = nll.mean(dim=1).cpu().numpy()
        if "nll_p95" in strategies:
            scores["nll_p95"] = nll.cpu().numpy()
        if "nll_max" in strategies:
            scores["nll_max"] = nll.max(dim=1).values.cpu().numpy()

    return scores


def aggregate_window_scores_by_block(
    window_scores: dict[str, list[np.ndarray]],
    block_ids: list[np.ndarray],
    labels: list[np.ndarray],
) -> dict[str, pd.DataFrame]:
    """Aggregate per-window strategy scores into block-level anomaly scores."""
    block_ids_array = np.concatenate(block_ids).astype(str)
    labels_array = np.concatenate(labels).astype(int)
    base_frame = pd.DataFrame(
        {
            "block_id": block_ids_array,
            "y_true": labels_array,
        }
    )
    base_summary = (
        base_frame.groupby("block_id", as_index=False)
        .agg(
            y_true=("y_true", "max"),
            num_windows=("y_true", "size"),
        )
        .sort_values("block_id")
        .reset_index(drop=True)
    )

    result = {}

    for strategy, chunks in window_scores.items():
        scores_array = np.concatenate(chunks, axis=0).astype(float)

        if strategy == "nll_p95":
            position_scores = scores_array.reshape(-1)
            repeated_block_ids = np.repeat(block_ids_array, scores_array.shape[1])
            frame = pd.DataFrame(
                {
                    "block_id": repeated_block_ids,
                    "position_score": position_scores,
                }
            )
            strategy_summary = (
                frame.groupby("block_id", as_index=False)
                .agg(
                    score=("position_score", lambda values: values.quantile(0.95)),
                    window_score_max=("position_score", "max"),
                )
                .sort_values("block_id")
                .reset_index(drop=True)
            )
        else:
            frame = pd.DataFrame(
                {
                    "block_id": block_ids_array,
                    "window_score": scores_array,
                }
            )
            score_agg = "max" if strategy == "nll_max" else "mean"
            strategy_summary = (
                frame.groupby("block_id", as_index=False)
                .agg(
                    score=("window_score", score_agg),
                    window_score_max=("window_score", "max"),
                )
                .sort_values("block_id")
                .reset_index(drop=True)
            )

        result[strategy] = base_summary.merge(strategy_summary, on="block_id", how="inner")

    return result


def empty_window_score_buffer(strategies: Iterable[str]) -> dict[str, list[np.ndarray]]:
    return {strategy: [] for strategy in strategies}
