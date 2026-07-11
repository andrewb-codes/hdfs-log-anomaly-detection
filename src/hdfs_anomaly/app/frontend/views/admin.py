from typing import Any

import streamlit as st

from hdfs_anomaly.app.frontend.core.api import request, show_error
from hdfs_anomaly.app.frontend.core.session import auth_token


def render_admin(current_profile: dict[str, Any]) -> None:
    render_model_info()

    filters = st.columns(4)
    with filters[0]:
        email = st.text_input("Email prefix")
    with filters[1]:
        role = st.selectbox("Role", ["ALL", "ADMIN", "USER"])
    with filters[2]:
        status = st.selectbox("Status", ["ALL", "ACTIVE", "INACTIVE"])
    with filters[3]:
        page = st.number_input("Page", min_value=1, value=1, key="admin_page")

    params: dict[str, Any] = {"page": int(page), "page_size": 20}
    if email:
        params["email_starts_with"] = email
    if role != "ALL":
        params["role"] = role
    if status != "ALL":
        params["status"] = status

    response = request("GET", "/api/v1/admin/profiles", token=auth_token(), params=params)
    if response is None:
        return
    if not response.is_success:
        show_error(response)
        return

    payload = response.json()
    profiles = payload["items"]
    st.dataframe(profiles, use_container_width=True, hide_index=True)

    editable = [item for item in profiles if item["id"] != current_profile["id"]]
    if not editable:
        return

    profile_by_label = {f"{item['email']} · #{item['id']}": item for item in editable}
    label = st.selectbox("Profile", list(profile_by_label))
    render_profile_controls(profile_by_label[label])


def render_model_info() -> None:
    response = request("GET", "/api/v1/model/info", token=auth_token())
    if response is None:
        return
    if not response.is_success:
        show_error(response)
        return

    model = response.json()
    columns = st.columns(4)
    columns[0].metric("Model", model["model_type"])
    columns[1].metric("Strategy", model["scoring_strategy"])
    columns[2].metric("Window", model["window_size"])
    columns[3].metric("Stride", model["stride"])


def render_profile_controls(profile: dict[str, Any]) -> None:
    left, right = st.columns(2)
    with left:
        statuses = ["ACTIVE", "INACTIVE"]
        status = st.selectbox(
            "New status",
            statuses,
            index=statuses.index(profile["status"]),
        )
        if st.button("Update status"):
            update_profile(profile, "status", status)

    with right:
        roles = ["ADMIN", "USER"]
        role = st.selectbox(
            "New role",
            roles,
            index=roles.index(profile["role"]),
        )
        if st.button("Update role"):
            update_profile(profile, "role", role)


def update_profile(profile: dict[str, Any], field: str, value: str) -> None:
    response = request(
        "PATCH",
        f"/api/v1/admin/profiles/{profile['id']}/{field}",
        token=auth_token(),
        json={field: value, "version": profile["version"]},
    )
    if response is None:
        return
    if response.is_success:
        st.success(f"{field.title()} updated")
        st.rerun()
    else:
        show_error(response)
