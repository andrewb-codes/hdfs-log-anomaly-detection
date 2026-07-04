import httpx
import streamlit as st

from hdfs_anomaly.frontend.config import frontend_settings

st.set_page_config(page_title="HDFS Anomaly Detection", layout="wide")

api_url = frontend_settings.streamlit_api_url.rstrip("/")

if "access_token" not in st.session_state:
    st.session_state.access_token = None

with st.sidebar:
    st.subheader("Admin login")
    username = st.text_input("Username", "admin")
    password = st.text_input("Password", "admin", type="password")

    if st.button("Login"):
        response = httpx.post(
            f"{api_url}/auth/login",
            json={"username": username, "password": password},
            timeout=10,
        )
        if response.is_success:
            st.session_state.access_token = response.json()["access_token"]
            st.success("Logged in")
        else:
            st.error(response.text)

headers = {}
if st.session_state.access_token:
    headers["Authorization"] = f"Bearer {st.session_state.access_token}"

tab_forward, tab_model, tab_history, tab_stats = st.tabs(["Forward", "Model", "History", "Stats"])

with tab_forward:
    block_id = st.text_input("Block ID", "blk_7503483334202473044")
    log_lines_text = st.text_area("Log lines", height=200)
    return_event_ids = st.checkbox("Return event ids", value=True)
    return_window_scores = st.checkbox("Return window scores")

    if st.button("Run inference"):
        log_lines = [line.strip() for line in log_lines_text.splitlines() if line.strip()]

        response = httpx.post(
            f"{api_url}/forward",
            json={
                "block_id": block_id,
                "log_lines": log_lines,
                "return_event_ids": return_event_ids,
                "return_window_scores": return_window_scores,
            },
            timeout=60,
        )

        if response.is_success:
            result = response.json()
            st.metric("Score", result["score"])
            st.metric("Threshold", result["threshold"])
            st.metric("Anomaly", result["is_anomaly"])
            st.json(result)
        else:
            st.error(response.text)

with tab_model:
    if st.button("Load model info"):
        response = httpx.get(f"{api_url}/model-info", headers=headers, timeout=10)
        st.json(response.json() if response.is_success else response.text)

with tab_history:
    if st.button("Load history"):
        response = httpx.get(f"{api_url}/history", headers=headers, timeout=10)
        st.json(response.json() if response.is_success else response.text)

with tab_stats:
    if st.button("Load stats"):
        response = httpx.get(f"{api_url}/stats", headers=headers, timeout=10)
        st.json(response.json() if response.is_success else response.text)
