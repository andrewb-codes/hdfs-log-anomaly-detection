from typing import Any

import streamlit as st

from hdfs_anomaly.app.frontend.core.api import request, show_error
from hdfs_anomaly.app.frontend.core.session import auth_token, logout


def render_profile(profile: dict[str, Any]) -> None:
    columns = st.columns(3)
    columns[0].metric("Role", profile["role"])
    columns[1].metric("Status", profile["status"])
    columns[2].metric("Version", profile["version"])

    email_tab, password_tab, delete_tab = st.tabs(["Email", "Password", "Delete"])
    with email_tab:
        render_email_form(profile)
    with password_tab:
        render_password_form(profile)
    with delete_tab:
        render_delete_form()


def render_email_form(profile: dict[str, Any]) -> None:
    with st.form("email_form"):
        new_email = st.text_input("New email", value=profile["email"])
        current_password = st.text_input("Current password", type="password")
        submitted = st.form_submit_button("Change email")

    if submitted:
        response = request(
            "PATCH",
            "/api/v1/profile/email",
            token=auth_token(),
            json={
                "new_email": new_email,
                "current_password": current_password,
                "version": profile["version"],
            },
        )
        if response is None:
            return
        if response.is_success:
            st.success("Email changed")
            st.rerun()
        else:
            show_error(response)


def render_password_form(profile: dict[str, Any]) -> None:
    with st.form("password_form"):
        current_password = st.text_input(
            "Current password", type="password", key="password_current"
        )
        new_password = st.text_input("New password", type="password")
        submitted = st.form_submit_button("Change password")

    if submitted:
        response = request(
            "PATCH",
            "/api/v1/profile/password",
            token=auth_token(),
            json={
                "current_password": current_password,
                "new_password": new_password,
                "version": profile["version"],
            },
        )
        if response is None:
            return
        if response.is_success:
            st.success("Password changed")
            st.rerun()
        else:
            show_error(response)


def render_delete_form() -> None:
    confirmed = st.checkbox("Confirm account deletion")
    if st.button("Delete account", disabled=not confirmed):
        response = request("DELETE", "/api/v1/profile", token=auth_token())
        if response is None:
            return
        if response.is_success:
            logout()
        else:
            show_error(response)
