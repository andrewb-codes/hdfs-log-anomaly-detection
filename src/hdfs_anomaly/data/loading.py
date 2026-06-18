from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class PreprocessedHdfsData:
    labels: pd.DataFrame
    occurrence: pd.DataFrame
    traces: pd.DataFrame
    templates: pd.DataFrame


def load_preprocessed_hdfs(data_dir: str | Path) -> PreprocessedHdfsData:
    """Load LogHub HDFS_v1 preprocessed files from a directory."""
    data_dir = Path(data_dir)
    return PreprocessedHdfsData(
        labels=pd.read_csv(data_dir / "anomaly_label.csv"),
        occurrence=pd.read_csv(data_dir / "Event_occurrence_matrix.csv"),
        traces=pd.read_csv(data_dir / "Event_traces.csv"),
        templates=pd.read_csv(data_dir / "HDFS.log_templates.csv"),
    )
