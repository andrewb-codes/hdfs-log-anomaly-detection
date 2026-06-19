import numpy as np
import pandas as pd
import torch

from hdfs_anomaly.api.resources import InferenceResources
from hdfs_anomaly.api.schemas import ForwardRequest, ForwardResponse
from hdfs_anomaly.metrics.lstm_many_to_many import batch_strategy_scores
from hdfs_anomaly.sequences.windows import make_lstm_windows


def parse_log_lines(request: ForwardRequest, resources: InferenceResources) -> list[int]:
    """Parse raw HDFS log lines into the internal EventId sequence for the requested block."""
    raw_logs = pd.DataFrame({"original_message": request.log_lines})
    sequences = resources.transformer.transform(raw_logs)

    if sequences.empty:
        raise RuntimeError("no valid block sequences parsed from log lines")

    block_sequences = sequences[sequences["block_id"] == request.block_id]
    if block_sequences.empty:
        raise RuntimeError(f"block_id '{request.block_id}' was not found in parsed log lines")

    return list(block_sequences.iloc[0]["sequence"])


def make_inference_windows(
        block_id: str,
        sequence: list[int],
        window_size: int,
        stride: int
) -> pd.DataFrame:
    """Convert one block event sequence into many-to-many LSTM inference windows."""
    sequences = pd.DataFrame(
        [
            {
                "block_id": block_id,
                "sequence": sequence
            }
        ]
    )
    windows = make_lstm_windows(
        sequences_df=sequences,
        window_size=window_size,
        stride=stride,
        target_mode="many_to_many"
    )

    if windows.empty:
        raise RuntimeError(f"not enough events for inference: got {len(sequence)}, need more then {window_size}")

    return windows


def score_windows(
        windows: pd.DataFrame,
        resources: InferenceResources
) -> tuple[float, list[float]]:
    """Score inference windows and aggregate them into a block-level anomaly score."""
    x = np.asarray(windows["window"].to_list(), dtype=np.int64)
    y = np.asarray(windows["target"].to_list(), dtype=np.int64)

    xb = torch.as_tensor(x, dtype=torch.long, device=resources.device)
    yb = torch.as_tensor(y, dtype=torch.long, device=resources.device)

    resources.model.eval()
    with torch.no_grad():
        logits = resources.model(xb)
        scores = batch_strategy_scores(
            logits=logits,
            y=yb,
            strategies=(resources.scoring_strategy,),
            top_k=3,
        )[resources.scoring_strategy]

    window_scores = scores.astype(float).tolist()

    if resources.scoring_strategy == "nll_max":
        block_score = float(np.max(scores))
    else:
        block_score = float(np.mean(scores))

    return block_score, window_scores


def run_inference(
        request: ForwardRequest,
        resources: InferenceResources
) -> ForwardResponse:
    """Run the full raw-log to block-level anomaly decision pipeline."""
    sequence = parse_log_lines(request, resources)
    windows = make_inference_windows(
        block_id=request.block_id,
        sequence=sequence,
        window_size=resources.window_size,
        stride=resources.stride
    )
    score, window_scores = score_windows(windows, resources)
    is_anomaly = score >= resources.threshold

    return ForwardResponse(
        block_id=request.block_id,
        score=score,
        threshold=resources.threshold,
        is_anomaly=is_anomaly,
        scoring_strategy=resources.scoring_strategy,
        num_log_lines=len(request.log_lines),
        num_events=len(sequence),
        num_windows=len(windows),
        event_ids=sequence if request.return_event_ids else None,
        window_scores=window_scores if request.return_window_scores else None,
    )
