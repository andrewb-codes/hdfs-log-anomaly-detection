import pytest
from pydantic import ValidationError

from hdfs_anomaly.app.models.profile import Role, Status
from hdfs_anomaly.app.schemas.profile import (
    AdminProfileRoleUpdateRequest,
    AdminProfileStatusUpdateRequest,
    EmailChangeRequest,
    PasswordChangeRequest,
)

pytestmark = pytest.mark.no_db


def test_email_change_accepts_valid_payload() -> None:
    request = EmailChangeRequest(
        new_email="new@example.com",
        current_password="password",
        version=0,
    )

    assert str(request.new_email) == "new@example.com"
    assert request.current_password == "password"
    assert request.version == 0


@pytest.mark.parametrize(
    "payload",
    [
        {"new_email": "new@example.com", "current_password": "", "version": 0},
        {"new_email": "not-an-email", "current_password": "password", "version": 0},
    ],
)
def test_email_change_rejects_invalid_payload(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        EmailChangeRequest.model_validate(payload)


def test_password_change_accepts_valid_payload_with_minimum_new_password_length() -> None:
    request = PasswordChangeRequest(
        current_password="password",
        new_password="123456",
        version=0,
    )

    assert request.current_password == "password"
    assert request.new_password == "123456"
    assert request.version == 0


@pytest.mark.parametrize(
    "payload",
    [
        {"current_password": "", "new_password": "new-password", "version": 0},
        {"current_password": "password", "new_password": "short", "version": 0},
    ],
)
def test_password_change_rejects_invalid_payload(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        PasswordChangeRequest.model_validate(payload)


@pytest.mark.parametrize(
    "request_cls, payload",
    [
        (
            EmailChangeRequest,
            {
                "new_email": "new@example.com",
                "current_password": "password",
                "version": -1,
            },
        ),
        (
            PasswordChangeRequest,
            {
                "current_password": "password",
                "new_password": "123456",
                "version": -1,
            },
        ),
    ],
)
def test_profile_write_requests_reject_negative_version(
    request_cls: type[EmailChangeRequest | PasswordChangeRequest],
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        request_cls.model_validate(payload)


def test_admin_profile_status_update_accepts_valid_payload() -> None:
    request = AdminProfileStatusUpdateRequest(status=Status.ACTIVE, version=0)

    assert request.status == Status.ACTIVE
    assert request.version == 0


def test_admin_profile_role_update_accepts_valid_payload() -> None:
    request = AdminProfileRoleUpdateRequest(role=Role.ADMIN, version=0)

    assert request.role == Role.ADMIN
    assert request.version == 0


@pytest.mark.parametrize(
    "request_cls",
    [
        AdminProfileStatusUpdateRequest,
        AdminProfileRoleUpdateRequest,
    ],
)
def test_admin_profile_update_rejects_negative_version(
    request_cls: type[AdminProfileStatusUpdateRequest | AdminProfileRoleUpdateRequest],
) -> None:
    payload: dict[str, object] = {"version": -1}

    if request_cls is AdminProfileStatusUpdateRequest:
        payload["status"] = Status.ACTIVE
    else:
        payload["role"] = Role.ADMIN

    with pytest.raises(ValidationError):
        request_cls.model_validate(payload)
