import streamlit as st

from hdfs_anomaly.app.frontend.core.api import request, show_error
from hdfs_anomaly.app.frontend.core.session import login


def render_auth() -> None:
    _, content, _ = st.columns([1, 1, 1])

    with content:
        st.title("HDFS Log Anomaly Detection")
        login_tab, registration_tab = st.tabs(["Sign in", "Register"])

        with login_tab:
            with st.form("login_form"):
                email = st.text_input("Email", key="login_email")
                password = st.text_input("Password", type="password", key="login_password")
                submitted = st.form_submit_button("Sign in")

            if submitted:
                response = request(
                    "POST",
                    "/api/v1/auth/login",
                    json={"email": email, "password": password},
                )
                if response is None:
                    return
                if response.is_success:
                    login(response.json()["access_token"])
                else:
                    show_error(response)

        with registration_tab:
            with st.form("registration_form"):
                email = st.text_input("Email", key="registration_email")
                password = st.text_input("Password", type="password", key="registration_password")
                submitted = st.form_submit_button("Create account")

            if submitted:
                response = request(
                    "POST",
                    "/api/v1/registration",
                    json={"email": email, "password": password},
                )
                if response is None:
                    return
                if response.is_success:
                    st.success("Account created")
                else:
                    show_error(response)
