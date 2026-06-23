import re
from pathlib import Path

import pandas as pd
from drain3 import TemplateMiner
from drain3.file_persistence import FilePersistence
from drain3.template_miner_config import TemplateMinerConfig
from sklearn.base import BaseEstimator, TransformerMixin


class DrainEventSequenceTransformer(BaseEstimator, TransformerMixin):
    """Convert raw HDFS log lines into per-block sequences of Drain event ids."""

    def __init__(
        self,
        drain_state,
        drain_config,
        message_col="original_message",
        timestamp_format="%y%m%d %H%M%S",
        block_id_regex=r"(blk_[A-Za-z0-9_-]+)",
        min_sequence_len=2,
        update_drain_on_fit=True,
        drop_unknown_block=True,
        unknown_block_token="unknown_block",
    ):
        self.drain_state = drain_state
        self.drain_config = drain_config
        self.message_col = message_col
        self.timestamp_format = timestamp_format
        self.block_id_regex = block_id_regex
        self.min_sequence_len = min_sequence_len
        self.update_drain_on_fit = update_drain_on_fit
        self.drop_unknown_block = drop_unknown_block
        self.unknown_block_token = unknown_block_token

        Path(self.drain_state).parent.mkdir(parents=True, exist_ok=True)
        persistence = FilePersistence(self.drain_state)
        config = TemplateMinerConfig()
        config.load(self.drain_config)
        self.template_miner = TemplateMiner(persistence_handler=persistence, config=config)

        self.pattern = re.compile(
            r"^(?P<Date>.+?)\s+(?P<Time>.+?)\s+(?P<Pid>.+?)\s+"
            r"(?P<Level>.+?)\s+(?P<Component>.+?):\s+(?P<Content>.+?)$",
            re.IGNORECASE,
        )
        self.block_id_re = re.compile(self.block_id_regex)
        self.template_list_ = None
        self.event_to_id_ = None

    def fit(self, X, y=None):
        if self.update_drain_on_fit:
            for row in X[self.message_col]:
                self.template_miner.add_log_message(self.get_content(row))

        self.template_list_ = [cluster.cluster_id for cluster in self.template_miner.drain.clusters]
        self.template_list_.append("unknown")
        self.event_to_id_ = {cluster_id: idx for idx, cluster_id in enumerate(self.template_list_)}
        return self

    def transform(self, X):
        messages = X[self.message_col].astype(str)
        df = pd.DataFrame(index=X.index)
        df["date"] = messages.apply(self.get_date)
        df["time"] = messages.apply(self.get_time)
        df["timestamp"] = pd.to_datetime(
            df["date"].astype(str) + " " + df["time"].astype(str),
            format=self.timestamp_format,
            errors="coerce",
        )
        df["block_id"] = messages.apply(self.get_block_id)
        df["cluster_id"] = messages.apply(self.get_cluster_id)

        if self.drop_unknown_block:
            df = df[df["block_id"].notna()]

        df = df.dropna(subset=["timestamp"])
        if self.event_to_id_ is None:
            raise RuntimeError("DrainEventSequenceTransformer must be fitted before transform().")
        event_to_id = self.event_to_id_
        df["event_id"] = df["cluster_id"].apply(
            lambda cluster_id: event_to_id.get(cluster_id, event_to_id["unknown"])
        )
        df = df.sort_values(["block_id", "timestamp"])

        rows = []
        for block_id, group in df.groupby("block_id"):
            events = group["event_id"].tolist()
            if len(events) >= self.min_sequence_len:
                rows.append({"block_id": block_id, "sequence": events})
        return pd.DataFrame(rows)

    def get_cluster_id(self, row):
        content = self.get_content(row)
        cluster = self.template_miner.match(content)
        return cluster.cluster_id if cluster else "unknown"

    def get_date(self, row):
        match = self._match(row)
        return match["Date"] if match else None

    def get_time(self, row):
        match = self._match(row)
        return match["Time"] if match else None

    def get_content(self, row):
        match = self._match(row)
        return match["Content"] if match else str(row).strip()

    def get_block_id(self, row):
        content = self.get_content(row)
        match = self.block_id_re.search(content)
        if match:
            return match.group(1)
        if self.drop_unknown_block:
            return None
        return self.unknown_block_token

    def _match(self, row):
        return self.pattern.match(str(row).strip())

    def __reduce__(self):
        return (
            self.__class__,
            (
                self.drain_state,
                self.drain_config,
                self.message_col,
                self.timestamp_format,
                self.block_id_regex,
                self.min_sequence_len,
                self.update_drain_on_fit,
                self.drop_unknown_block,
                self.unknown_block_token,
            ),
            self.__dict__,
        )
