from typing import Any

import httpx
import streamlit as st

from hdfs_anomaly.app.frontend.core.config import frontend_settings

API_URL = frontend_settings.streamlit_api_url.rstrip("/")


def request(
    method: str,
    path: str,
    *,
    token: str | None = None,
    json: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
    timeout: float = 15,
) -> httpx.Response | None:
    headers = {"Authorization": f"Bearer {token}"} if token else None

    try:
        return httpx.request(
            method,
            f"{API_URL}{path}",
            headers=headers,
            json=json,
            params=params,
            timeout=timeout,
        )
    except httpx.RequestError:
        st.error("API is unavailable")
        return None


def error_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text or f"HTTP {response.status_code}"

    if isinstance(payload, dict):
        detail = payload.get("detail")
        if isinstance(detail, str):
            return detail
    return f"HTTP {response.status_code}"


def show_error(response: httpx.Response) -> None:
    st.error(error_detail(response))
