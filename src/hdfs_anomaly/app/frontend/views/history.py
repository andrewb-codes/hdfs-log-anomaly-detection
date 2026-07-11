from typing import Any

import streamlit as st

from hdfs_anomaly.app.frontend.core.api import request, show_error
from hdfs_anomaly.app.frontend.core.session import auth_token


def render_history(profile: dict[str, Any]) -> None:
    controls = st.columns([1, 1, 3])
    with controls[0]:
        page = st.number_input("Page", min_value=1, value=1, step=1)
    with controls[1]:
        page_size = st.selectbox("Page size", [10, 20, 50, 100], index=1)

    history_path = "/api/v1/history"
    stats_path = "/api/v1/history/stats"
    if profile["role"] == "ADMIN" and st.toggle("All profiles"):
        history_path = "/api/v1/history/all"
        stats_path = "/api/v1/history/stats/all"

    response = request(
        "GET",
        history_path,
        token=auth_token(),
        params={"page": int(page), "page_size": page_size},
    )
    if response is not None:
        if response.is_success:
            payload = response.json()
            st.dataframe(payload["items"], use_container_width=True, hide_index=True)
            st.caption("More results available" if payload["has_next"] else "Last page")
        else:
            show_error(response)

    stats_response = request("GET", stats_path, token=auth_token())
    if stats_response is not None:
        if stats_response.is_success:
            render_stats(stats_response.json())
        else:
            show_error(stats_response)

    if st.button("Clear history", type="secondary"):
        delete_response = request("DELETE", history_path, token=auth_token())
        if delete_response is None:
            return
        if delete_response.is_success:
            st.success(f"Deleted: {delete_response.json()['deleted']}")
            st.rerun()
        else:
            show_error(delete_response)


def render_stats(stats: dict[str, Any]) -> None:
    columns = st.columns(4)
    columns[0].metric("Requests", stats["total_requests"])
    columns[1].metric("Successful", stats["successful_requests"])
    columns[2].metric("Failed", stats["failed_requests"])
    columns[3].metric(
        "Mean latency",
        f"{stats['mean_processing_ms']:.1f} ms" if stats["mean_processing_ms"] is not None else "—",
    )
