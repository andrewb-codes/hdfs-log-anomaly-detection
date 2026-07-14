import pytest
from pydantic import ValidationError

from hdfs_anomaly.app.schemas.auth import LoginRequest, RegistrationRequest

pytestmark = pytest.mark.no_db


def test_registration_request_accepts_valid_payload() -> None:
    request = RegistrationRequest(email="user@example.com", password="123456")

    assert str(request.email) == "user@example.com"
    assert request.password == "123456"


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "not-an-email", "password": "123456"},
        {"email": "user@example.com", "password": "short"},
    ],
)
def test_registration_request_rejects_invalid_payload(
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        RegistrationRequest.model_validate(payload)


def test_login_request_accepts_empty_password_for_authentication_failure_path() -> None:
    request = LoginRequest(email="user@example.com", password="")

    assert str(request.email) == "user@example.com"
    assert request.password == ""


def test_login_request_rejects_invalid_email() -> None:
    with pytest.raises(ValidationError):
        LoginRequest.model_validate({"email": "not-an-email", "password": "password"})
