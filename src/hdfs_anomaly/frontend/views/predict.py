import streamlit as st

from hdfs_anomaly.frontend.core.api import request, show_error
from hdfs_anomaly.frontend.core.session import auth_token


def render_prediction() -> None:
    with st.form("prediction_form"):
        block_id = st.text_input("Block ID", "blk_7503483334202473044")
        log_lines_text = st.text_area("Log lines", height=260)
        left, right = st.columns(2)
        with left:
            return_event_ids = st.checkbox("Return event IDs", value=True)
        with right:
            return_window_scores = st.checkbox("Return window scores")
        submitted = st.form_submit_button("Run inference")

    if not submitted:
        return

    log_lines = [line.strip() for line in log_lines_text.splitlines() if line.strip()]
    if not log_lines:
        st.warning("Log lines are required")
        return

    with st.spinner("Running inference"):
        response = request(
            "POST",
            "/api/v1/model/predict",
            token=auth_token(),
            json={
                "block_id": block_id,
                "log_lines": log_lines,
                "return_event_ids": return_event_ids,
                "return_window_scores": return_window_scores,
            },
            timeout=60,
        )

    if response is None:
        return
    if not response.is_success:
        show_error(response)
        return

    result = response.json()
    columns = st.columns(4)
    columns[0].metric("Score", f"{result['score']:.4f}")
    columns[1].metric("Threshold", f"{result['threshold']:.4f}")
    columns[2].metric("Decision", "Anomaly" if result["is_anomaly"] else "Normal")
    columns[3].metric("Windows", result["num_windows"])
    st.json(result)
