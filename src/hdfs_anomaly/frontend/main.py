import streamlit as st

from hdfs_anomaly.frontend.core.session import load_profile, logout
from hdfs_anomaly.frontend.views.admin import render_admin
from hdfs_anomaly.frontend.views.auth import render_auth
from hdfs_anomaly.frontend.views.history import render_history
from hdfs_anomaly.frontend.views.predict import render_prediction
from hdfs_anomaly.frontend.views.profile import render_profile


def render_app() -> None:
    profile = load_profile()
    if profile is None:
        render_auth()
        return

    with st.sidebar:
        st.title("HDFS Anomaly")
        st.write(profile["email"])
        st.caption(f"{profile['role']} · {profile['status']}")
        if st.button("Sign out", use_container_width=True):
            logout()

    st.title("HDFS Log Anomaly Detection")

    tab_names = ["Predict", "History", "Profile"]
    if profile["role"] == "ADMIN":
        tab_names.append("Admin")

    tabs = st.tabs(tab_names)
    with tabs[0]:
        render_prediction()
    with tabs[1]:
        render_history(profile)
    with tabs[2]:
        render_profile(profile)
    if profile["role"] == "ADMIN":
        with tabs[3]:
            render_admin(profile)


st.set_page_config(
    page_title="HDFS Anomaly Detection",
    page_icon=":material/monitoring:",
    layout="wide",
)
render_app()
