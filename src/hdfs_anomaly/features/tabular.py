import numpy as np
import pandas as pd

from hdfs_anomaly.features.parsing import parse_event_sequence, parse_time_intervals

TABULAR_EXTRA_FEATURES = [
    "sequence_len",
    "Latency",
    "ti_mean",
    "ti_max",
    "ti_std",
    "ti_zeros",
]


def get_event_columns(occurrence: pd.DataFrame) -> list[str]:
    """Return EventId count columns E1...E29 from an occurrence matrix."""
    return [column for column in occurrence.columns if column.startswith("E")]


def time_interval_stats(value: str) -> pd.Series:
    intervals = np.array(parse_time_intervals(value), dtype=float)
    if intervals.size == 0:
        return pd.Series(
            {
                "ti_mean": 0.0,
                "ti_max": 0.0,
                "ti_std": 0.0,
                "ti_zeros": 0.0,
            }
        )

    return pd.Series(
        {
            "ti_mean": intervals.mean(),
            "ti_max": intervals.max(),
            "ti_std": intervals.std(ddof=0),
            "ti_zeros": (intervals == 0).mean(),
        }
    )


def build_tabular_feature_frame(
    labels: pd.DataFrame,
    occurrence: pd.DataFrame,
    traces: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.Series, list[str]]:
    """Build full-block tabular baseline features for HDFS block classification.

    The returned features intentionally describe the whole block_id trace. This is
    useful as a supervised baseline, but it is not equivalent to online inference
    where events arrive sequentially.
    """
    labels = labels.copy()
    labels["y"] = labels["Label"].map({"Normal": 0, "Anomaly": 1}).astype(int)

    traces_features = traces[["BlockId", "Features", "TimeInterval", "Latency"]].copy()
    traces_features["sequence_len"] = traces_features["Features"].map(
        lambda value: len(parse_event_sequence(value))
    )
    interval_stats = traces_features["TimeInterval"].apply(time_interval_stats)
    traces_features = pd.concat(
        [traces_features[["BlockId", "Latency", "sequence_len"]], interval_stats],
        axis=1,
    )

    event_columns = get_event_columns(occurrence)
    feature_columns = event_columns + TABULAR_EXTRA_FEATURES

    dataset = (
        occurrence[["BlockId"] + event_columns]
        .merge(traces_features, on="BlockId", how="inner")
        .merge(labels[["BlockId", "y"]], on="BlockId", how="inner")
    )

    X = dataset[feature_columns].fillna(0.0)
    X.index = dataset["BlockId"]
    X.index.name = "BlockId"
    y = dataset["y"]
    y.index = X.index
    return X, y, feature_columns
