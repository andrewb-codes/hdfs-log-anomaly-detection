from collections.abc import Sequence

import numpy as np

from hdfs_anomaly.app.models.history import RequestHistory
from hdfs_anomaly.app.schemas.history import StatsResponse


def calculate_request_stats(rows: Sequence[RequestHistory]) -> StatsResponse:
    total_requests = len(rows)
    successful_requests = sum(row.status_code == 200 for row in rows)
    failed_requests = total_requests - successful_requests

    processing_times = [row.processing_ms for row in rows if row.processing_ms is not None]

    num_log_lines = [row.num_log_lines for row in rows if row.num_log_lines is not None]

    if processing_times:
        processing_array = np.asarray(processing_times, dtype=float)
        mean_processing_ms = float(processing_array.mean())
        p50_processing_ms = float(np.quantile(processing_array, 0.50))
        p95_processing_ms = float(np.quantile(processing_array, 0.95))
        p99_processing_ms = float(np.quantile(processing_array, 0.99))
    else:
        mean_processing_ms = None
        p50_processing_ms = None
        p95_processing_ms = None
        p99_processing_ms = None

    if num_log_lines:
        num_log_lines_array = np.asarray(num_log_lines, dtype=float)
        mean_num_log_lines = float(num_log_lines_array.mean())
        min_num_log_lines = int(num_log_lines_array.min())
        max_num_log_lines = int(num_log_lines_array.max())
    else:
        mean_num_log_lines = None
        min_num_log_lines = None
        max_num_log_lines = None

    return StatsResponse(
        total_requests=total_requests,
        successful_requests=successful_requests,
        failed_requests=failed_requests,
        mean_processing_ms=mean_processing_ms,
        p50_processing_ms=p50_processing_ms,
        p95_processing_ms=p95_processing_ms,
        p99_processing_ms=p99_processing_ms,
        mean_num_log_lines=mean_num_log_lines,
        min_num_log_lines=min_num_log_lines,
        max_num_log_lines=max_num_log_lines,
    )
